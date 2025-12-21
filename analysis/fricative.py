# analysis/fricatives.py
from __future__ import annotations

import math
from typing import Dict, Optional, Tuple, Any

import numpy as np
import scipy.signal
import parselmouth


# ============================================================
# 0) Metadata
# ============================================================

FRICATIVE_META = {
    "사": {"fricative": "s"},
    "싸": {"fricative": "ss"},
    "하": {"fricative": "h"},
}
FRICATIVE_SET = set(FRICATIVE_META.keys())


# ============================================================
# 1) Reference targets (heuristic, Korean-friendly)
# ============================================================

REF_CENTROID_HZ = {
    "s":  4800.0,
    "ss": 6000.0,
    "h":  2800.0,
}
REF_CENTROID_SIGMA = 1700.0

# 🔴 NEW: HF contrast (log scale)
# log(E[4–8k] / E[0.5–1.5k])
REF_HF_CONTRAST_DB = {
    "h": 5.0,
    "s": 15.0,
    "ss": 20.0,
}
REF_HF_CONTRAST_DB_SIGMA = 8.0

REF_DURATION_MS = {
    "s":  120.0,
    "ss": 160.0,
    "h":  90.0,
}
REF_DUR_SIGMA = 80.0

SPECTRAL_WEIGHT = 0.85
DURATION_WEIGHT = 0.15


# ============================================================
# 2) Audio utilities
# ============================================================

def load_sound(path: str) -> Tuple[parselmouth.Sound, np.ndarray, int]:
    snd = parselmouth.Sound(path)
    y = snd.values.T.flatten().astype(np.float64)
    sr = int(round(snd.sampling_frequency))
    return snd, y, sr


def bandpass(sig: np.ndarray, sr: int, low: float, high: float, order: int = 4) -> np.ndarray:
    nyq = sr / 2.0
    lo = max(low / nyq, 1e-4)
    hi = min(high / nyq, 0.999)
    b, a = scipy.signal.butter(order, [lo, hi], btype="band")
    return scipy.signal.lfilter(b, a, sig)


def preemphasis(sig: np.ndarray, coef: float = 0.97) -> np.ndarray:
    if sig.size < 2:
        return sig
    return np.append(sig[0], sig[1:] - coef * sig[:-1])


# ============================================================
# 3) Silence trim (Intensity-based)
# ============================================================

def trim_by_intensity(
    snd: parselmouth.Sound,
    y: np.ndarray,
    sr: int,
    silence_db_below_peak: float = 30.0,
    pad_s: float = 0.05,
) -> Tuple[np.ndarray, float]:
    try:
        intensity = snd.to_intensity(time_step=0.01)
        vals = intensity.values.T.flatten()
        times = np.array(
            [intensity.get_time_from_frame_number(i + 1) for i in range(len(vals))],
            dtype=np.float64,
        )

        vmax = float(np.max(vals)) if vals.size else 0.0
        if vmax <= 1e-6:
            return y, 0.0

        thr = vmax - silence_db_below_peak
        active = np.where(vals >= thr)[0]
        if active.size == 0:
            return y, 0.0

        t0 = max(0.0, float(times[active[0]]) - pad_s)
        t1 = min(float(snd.get_total_duration()), float(times[active[-1]]) + pad_s)

        a = int(max(0, math.floor(t0 * sr)))
        b = int(min(len(y), math.ceil(t1 * sr)))
        if b <= a:
            return y, 0.0

        return y[a:b].copy(), float(t0)
    except Exception:
        return y, 0.0


# ============================================================
# 4) Frication detection (HF-energy peak)
# ============================================================

def _rms_envelope(sig: np.ndarray, sr: int, win_s: float = 0.025, hop_s: float = 0.010):
    win = max(int(win_s * sr), 32)
    hop = max(int(hop_s * sr), 16)

    if sig.size < win:
        return np.zeros(0), win, hop

    n_frames = 1 + (sig.size - win) // hop
    rms = np.zeros(n_frames)
    for i in range(n_frames):
        a = i * hop
        seg = sig[a:a + win]
        rms[i] = math.sqrt(float(np.mean(seg * seg)) + 1e-12)
    return rms, win, hop


def detect_frication_region_peak(
    y: np.ndarray,
    sr: int,
    max_len_ms: float = 220.0,
    rel_thr: float = 0.35,
) -> Tuple[float, float]:

    # HF = hiss band, LF = breath/vowel band
    y_hf = bandpass(y, sr, 1500.0, 8000.0)
    y_lf = bandpass(y, sr, 300.0, 1500.0)

    rms_hf, win, hop = _rms_envelope(y_hf, sr)
    rms_lf, _, _ = _rms_envelope(y_lf, sr)

    if rms_hf.size == 0 or rms_lf.size == 0:
        return 0.0, 0.0

    ratio = rms_hf / (rms_lf + 1e-12)

    peak_idx = int(np.argmax(ratio))
    peak_val = float(ratio[peak_idx])
    if peak_val <= 1e-9:
        return 0.0, 0.0

    thr = rel_thr * peak_val

    left = peak_idx
    while left > 0 and ratio[left] >= thr:
        left -= 1

    right = peak_idx
    while right < ratio.size - 1 and ratio[right] >= thr:
        right += 1

    t_start = (left * hop) / sr
    t_end = (right * hop + win) / sr

    max_len_s = max_len_ms / 1000.0
    if (t_end - t_start) > max_len_s:
        t_end = t_start + max_len_s

    return float(t_start), float(t_end)


# ============================================================
# 5) Spectral features (with HF contrast)
# ============================================================

def compute_spectral_features(
    y: np.ndarray,
    sr: int,
    t_start: float,
    t_end: float
) -> Dict[str, Optional[float]]:

    if t_end <= t_start:
        return {"centroid": None, "hf_contrast": None}

    a = int(max(0, math.floor(t_start * sr)))
    b = int(min(len(y), math.ceil(t_end * sr)))
    seg = y[a:b].astype(np.float64)
    if seg.size < int(0.02 * sr):
        return {"centroid": None, "hf_contrast": None}

    seg = preemphasis(seg, 0.97)
    seg = seg - float(np.mean(seg))

    freqs, pxx = scipy.signal.welch(seg, fs=sr, nperseg=min(1024, seg.size))
    pxx = np.maximum(pxx, 1e-18)

    # centroid (0.5–8k)
    band = (freqs >= 500.0) & (freqs <= 8000.0)
    freqs_b = freqs[band]
    p_b = pxx[band]
    w = p_b / float(np.sum(p_b))
    centroid = float(np.sum(freqs_b * w))

    # 🔴 HF contrast
    e_low = float(np.sum(pxx[(freqs >= 500.0) & (freqs < 1500.0)]))
    e_high = float(np.sum(pxx[(freqs >= 4000.0) & (freqs <= 8000.0)]))
    #hf_contrast = float(math.log((e_high + 1e-12) / (e_low + 1e-12)))
    ratio = (e_high + 1e-12) / (e_low + 1e-12)
    hf_contrast_db = 10.0 * math.log10(ratio)
    hf_contrast_db = float(np.clip(hf_contrast_db, -20.0, 40.0))

    return {"centroid": centroid, "hf_contrast_db": hf_contrast_db}


# ============================================================
# 6) Scoring
# ============================================================

def gaussian_score(x: float, mu: float, sigma: float) -> float:
    return float(100.0 * math.exp(-((x - mu) ** 2) / (2.0 * sigma * sigma)))


def score_spectral(centroid, hf_contrast, target):
    if centroid is None or hf_contrast is None:
        return None
    sc1 = gaussian_score(centroid, REF_CENTROID_HZ[target], REF_CENTROID_SIGMA)
    sc2 = gaussian_score(hf_contrast, REF_HF_CONTRAST_DB[target], REF_HF_CONTRAST_DB_SIGMA)
    return 0.6 * sc1 + 0.4 * sc2


def score_duration(dur_ms, target):
    if dur_ms is None:
        return None
    return gaussian_score(dur_ms, REF_DURATION_MS[target], REF_DUR_SIGMA)


def final_score(spec, dur):
    if spec is None and dur is None:
        return None
    if dur is None:
        return spec
    if spec is None:
        return dur
    return SPECTRAL_WEIGHT * spec + DURATION_WEIGHT * dur

def generate_feedback(target: str, detected: str, centroid: float | None, hf_contrast: float | None) -> str:
    # If we couldn't compute features
    if centroid is None or hf_contrast is None:
        return "I couldn't clearly capture the fricative noise. Try again: speak closer to the mic and keep the hiss steady."

    # Correct
    if detected == target:
        if target == "s":
            return "Good. Your 'ㅅ' hiss is clear. Keep it light and steady (no extra breath from the throat)."
        if target == "ss":
            return "Good. Your 'ㅆ' is sharp and tense. Keep the tongue constriction tight and the hiss strong."
        if target == "h":
            return "Good. Your 'ㅎ' is breathy. Keep the throat open and avoid making an 'ㅅ' hiss."
        return "Good."

    # Mismatch coaching
    if target in ("s", "ss") and detected == "h":
        return ("It sounds breathy like 'ㅎ'. For 'ㅅ/ㅆ', bring the tongue close to the ridge behind the upper teeth "
                "and make a clear hiss (more high-frequency sound).")

    if target == "h" and detected in ("s", "ss"):
        return ("It sounds like an 'ㅅ' hiss. For 'ㅎ', keep the throat open and let air flow gently—no tongue hiss.")

    # s vs ss confusion
    if target == "ss" and detected == "s":
        return ("It sounds like 'ㅅ' (too soft). For 'ㅆ', make the constriction tighter and the hiss sharper—"
                "think 'stronger, higher' without adding extra breath from the throat.")
    if target == "s" and detected == "ss":
        return ("It sounds too tense/sharp like 'ㅆ'. For 'ㅅ', relax slightly and make a lighter hiss.")

    return f"Detected as '{detected}'. Try again with a clearer sound."


# ============================================================
# 7) Main API
# ============================================================

def analyze_fricative(wav_path: str, syllable: str) -> Dict[str, Any]:
    if syllable not in FRICATIVE_SET:
        return {"error": "Unsupported fricative syllable"}

    target = FRICATIVE_META[syllable]["fricative"]

    snd, y, sr = load_sound(wav_path)
    y_trim, offset_s = trim_by_intensity(snd, y, sr)

    fric_start_t, fric_end_t = detect_frication_region_peak(y_trim, sr)

    feats = compute_spectral_features(y_trim, sr, fric_start_t, fric_end_t)
    duration_ms = (fric_end_t - fric_start_t) * 1000.0

    spec_score = score_spectral(feats["centroid"], feats["hf_contrast_db"], target)
    dur_score = score_duration(duration_ms, target)
    fs = final_score(spec_score, dur_score)

    soft = {}
    for lab in ("s", "ss", "h"):
        soft[lab] = final_score(
            score_spectral(feats["centroid"], feats["hf_contrast_db"], lab),
            score_duration(duration_ms, lab),
        ) or 0.0

    detected = max(soft, key=soft.get)

    # Confidence: gap between best and second-best
    sorted_scores = sorted(soft.items(), key=lambda kv: kv[1], reverse=True)
    conf = float(sorted_scores[0][1] - sorted_scores[1][1]) / 100.0 if len(sorted_scores) >= 2 else 0.0
    conf = max(0.0, min(1.0, conf))

    feedback_text = generate_feedback(target, detected, feats["centroid"], feats["hf_contrast_db"])

    return {
        "syllable": syllable,
        "type": "fricative",
        "targets": {"fricative": target},
        "features": {
            "spectral_centroid_hz": feats["centroid"],
            "hf_contrast": feats["hf_contrast_db"],
            "duration_ms": duration_ms,
            "trim_offset_s": offset_s,
            "fric_start_t": fric_start_t + offset_s,
            "fric_end_t": fric_end_t + offset_s,
        },
        "evaluation": {
            "detected_fricative": detected,
            "spectral_score": spec_score,
            "duration_score": dur_score,
            "final_score": fs,
            "softscores": soft,
            "confidence": conf,
        },
        "feedback": {
            "text": feedback_text, 
        },
    }

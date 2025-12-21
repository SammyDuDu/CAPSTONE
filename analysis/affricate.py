# analysis/affricate.py
from __future__ import annotations

import math
from typing import Dict, Optional, Tuple, Any

import numpy as np
import scipy.signal
import parselmouth


# ============================================================
# 0) Metadata
# ============================================================

AFFRICATE_META = {
    "자": {"affricate": "lenis"},
    "짜": {"affricate": "fortis"},
    "차": {"affricate": "aspirated"},
}
AFFRICATE_SET = set(AFFRICATE_META.keys())


# ============================================================
# 1) Reference targets (heuristic, literature-based)
# ============================================================

# ---- VOT (ms) ----
REF_VOT_MS = {
    "fortis": 15.0,
    "lenis": 40.0,
    "aspirated": 80.0,
}
REF_VOT_SIGMA = 25.0

# ---- Frication duration (ms) ----
REF_FRIC_DUR_MS = {
    "fortis": 80.0,
    "lenis": 110.0,
    "aspirated": 150.0,
}
REF_FRIC_DUR_SIGMA = 60.0

# ---- Spectral centroid (Hz) ----
REF_CENTROID_HZ = {
    "fortis": 6200.0,
    "lenis": 5000.0,
    "aspirated": 4200.0,
}
REF_CENTROID_SIGMA = 1700.0

# ---- HF contrast (dB) ----
REF_HF_CONTRAST_DB = {
    "fortis": 22.0,
    "lenis": 15.0,
    "aspirated": 10.0,
}
REF_HF_CONTRAST_SIGMA = 8.0

# ---- Weights ----
W_VOT = 0.45
W_SPEC = 0.35
W_FRIC_DUR = 0.20


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
# 3) Silence trim (reuse from others)
# ============================================================

def trim_by_intensity(
    snd: parselmouth.Sound,
    y: np.ndarray,
    sr: int,
    silence_db_below_peak: float = 40.0,
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
# 4) VOT estimation (simple & robust)
# ============================================================

def estimate_vot_ms(y: np.ndarray, sr: int) -> Optional[float]:
    y_hp = bandpass(y, sr, 200.0, 3000.0)
    env = np.abs(y_hp)

    thr = 0.1 * np.max(env)
    idx = np.where(env > thr)[0]
    if idx.size < 10:
        return None

    burst = idx[0]
    voiced = idx[min(10, idx.size - 1)]
    vot = (voiced - burst) / sr * 1000.0
    return max(0.0, vot)


# ============================================================
# 5) Frication detection & features (reuse logic)
# ============================================================

def _rms_envelope(sig: np.ndarray, sr: int, win_s: float = 0.025, hop_s: float = 0.010):
    win = max(int(win_s * sr), 32)
    hop = max(int(hop_s * sr), 16)
    n = 1 + max(0, sig.size - win) // hop
    rms = np.zeros(n)
    for i in range(n):
        seg = sig[i * hop:i * hop + win]
        rms[i] = math.sqrt(np.mean(seg * seg) + 1e-12)
    return rms, win, hop


def detect_frication_region(y: np.ndarray, sr: int) -> Tuple[float, float]:
    y_hf = bandpass(y, sr, 1500.0, 8000.0)
    y_lf = bandpass(y, sr, 300.0, 1500.0)

    rms_hf, win, hop = _rms_envelope(y_hf, sr)
    rms_lf, _, _ = _rms_envelope(y_lf, sr)
    ratio = rms_hf / (rms_lf + 1e-12)

    idx = int(np.argmax(ratio))
    t0 = idx * hop / sr
    t1 = t0 + 0.18  # cap frication length
    return t0, t1


def compute_frication_features(
    y: np.ndarray, sr: int, t0: float, t1: float
) -> Tuple[Optional[float], Optional[float]]:
    a = int(t0 * sr)
    b = int(t1 * sr)
    seg = y[a:b]
    if seg.size < int(0.02 * sr):
        return None, None

    seg = preemphasis(seg)
    freqs, pxx = scipy.signal.welch(seg, fs=sr, nperseg=min(1024, seg.size))
    pxx = np.maximum(pxx, 1e-18)

    band = (freqs >= 500) & (freqs <= 8000)
    centroid = float(np.sum(freqs[band] * pxx[band]) / np.sum(pxx[band]))

    e_low = np.sum(pxx[(freqs >= 500) & (freqs < 1500)])
    e_high = np.sum(pxx[(freqs >= 4000) & (freqs <= 8000)])
    hf_db = 10.0 * math.log10((e_high + 1e-12) / (e_low + 1e-12))
    hf_db = float(np.clip(hf_db, -20, 40))

    return centroid, hf_db


# ============================================================
# 6) Scoring
# ============================================================

def gaussian_score(x, mu, sigma):
    if x is None:
        return None
    return 100.0 * math.exp(-((x - mu) ** 2) / (2 * sigma ** 2))


# ============================================================
# 7) Feedback
# ============================================================

def generate_feedback(target: str, detected: str) -> str:
    if target == detected:
        if target == "fortis":
            return "Good. Your sound is tense and sharp. Release quickly without extra breath."
        if target == "lenis":
            return "Good. Your affricate is balanced. Keep the release gentle and controlled."
        if target == "aspirated":
            return "Good. You released with enough breath. Keep the airflow after the release."

    if target == "aspirated":
        return "Try adding more breath after the release. Do not stop the airflow too quickly."
    if target == "fortis":
        return "Release faster and reduce breath. Keep the tongue constriction tight."
    if target == "lenis":
        return "Relax slightly after the release. Avoid sounding too tense or too breathy."

    return "Try again with a clearer release and short hiss."


# ============================================================
# 8) Main API
# ============================================================

def analyze_affricate(wav_path: str, syllable: str) -> Dict[str, Any]:
    if syllable not in AFFRICATE_SET:
        return {"error": "Unsupported affricate syllable"}

    target = AFFRICATE_META[syllable]["affricate"]

    snd, y, sr = load_sound(wav_path)
    y_trim, offset = trim_by_intensity(snd, y, sr)

    vot = estimate_vot_ms(y_trim, sr)
    fric_t0, fric_t1 = detect_frication_region(y_trim, sr)
    fric_dur = (fric_t1 - fric_t0) * 1000.0

    centroid, hf_db = compute_frication_features(y_trim, sr, fric_t0, fric_t1)

    scores = {}
    for lab in ("fortis", "lenis", "aspirated"):
        s_vot = gaussian_score(vot, REF_VOT_MS[lab], REF_VOT_SIGMA)
        s_dur = gaussian_score(fric_dur, REF_FRIC_DUR_MS[lab], REF_FRIC_DUR_SIGMA)
        s_cent = gaussian_score(centroid, REF_CENTROID_HZ[lab], REF_CENTROID_SIGMA)
        s_hf = gaussian_score(hf_db, REF_HF_CONTRAST_DB[lab], REF_HF_CONTRAST_SIGMA)

        s_spec = 0.6 * s_cent + 0.4 * s_hf if s_cent and s_hf else None
        final = (
            W_VOT * s_vot +
            W_SPEC * s_spec +
            W_FRIC_DUR * s_dur
        ) if (s_vot and s_spec and s_dur) else 0.0

        scores[lab] = final

    detected = max(scores, key=scores.get)

    return {
        "syllable": syllable,
        "type": "affricate",
        "targets": {"affricate": target},
        "features": {
            "vot_ms": vot,
            "frication_duration_ms": fric_dur,
            "spectral_centroid_hz": centroid,
            "hf_contrast_db": hf_db,
        },
        "evaluation": {
            "detected_affricate": detected,
            "softscores": scores,
            "final_score": scores[target],
        },
        "feedback": {
            "text": generate_feedback(target, detected)
        }
    }

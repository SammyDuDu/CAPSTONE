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

# ---- Weights (PATCH: reduce VOT dominance for affricates) ----
W_VOT = 0.30
W_SPEC = 0.45
W_FRIC_DUR = 0.25

# ---- Safety caps (PATCH) ----
VOT_CAP_MS = 160.0   # clamp extreme VOT caused by late voicing detection


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


def _moving_average(x: np.ndarray, win: int) -> np.ndarray:
    if win <= 1 or x.size < 2:
        return x
    win = int(win)
    win = max(3, win)
    if win % 2 == 0:
        win += 1
    k = np.ones(win, dtype=np.float64) / float(win)
    return np.convolve(x, k, mode="same")


# ============================================================
# 3) Silence trim
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
# 4) Voicing / periodicity helper (ACF)
# ============================================================

def _acf_periodicity_score(x: np.ndarray, sr: int, fmin: float = 60.0, fmax: float = 500.0) -> float:
    """
    Lightweight periodicity check using normalized autocorrelation.
    Returns [0,1]-ish score: higher = more periodic/voiced.
    """
    if x.size < int(0.02 * sr):
        return 0.0

    x = x.astype(np.float64)
    x = x - np.mean(x)
    denom = np.sum(x * x) + 1e-12
    if denom <= 0:
        return 0.0

    lag_min = int(sr / fmax) if fmax > 0 else 1
    lag_max = int(sr / fmin) if fmin > 0 else lag_min + 1
    lag_min = max(lag_min, 1)
    lag_max = max(lag_max, lag_min + 1)

    n = int(2 ** math.ceil(math.log2(2 * x.size)))
    X = np.fft.rfft(x, n=n)
    acf = np.fft.irfft(X * np.conj(X), n=n)
    acf = acf[:x.size]
    acf = acf / denom

    seg = acf[lag_min:min(lag_max, acf.size)]
    if seg.size == 0:
        return 0.0

    peak = float(np.max(seg))
    return float(np.clip(peak, 0.0, 1.0))


# ============================================================
# 5) VOT estimation (burst tied to frication start + pitch + periodicity)
# ============================================================

def estimate_vot_ms(
    y: np.ndarray,
    sr: int,
    burst_hint_t: Optional[float] = None,
) -> Optional[float]:
    """
    VOT = (stable voicing onset) - (burst)

    - burst is anchored to frication start (burst_hint_t) if provided
    - voicing onset uses Pitch frames + ACF gate
    """
    if y.size < int(0.06 * sr):
        return None

    total = y.size / sr

    # ---- burst time
    if burst_hint_t is not None and np.isfinite(burst_hint_t):
        burst_t = float(burst_hint_t) - 0.010
        burst_t = float(np.clip(burst_t, 0.0, max(0.0, total - 0.02)))
    else:
        y_hf = bandpass(y, sr, 1500.0, 8000.0)
        env = np.abs(y_hf)
        peak = float(np.max(env)) if env.size else 0.0
        if peak <= 0.0:
            return None
        smooth_win = max(5, int(0.005 * sr))
        env_s = _moving_average(env, smooth_win)
        d = np.diff(env_s, prepend=env_s[0])
        thr_d = float(np.quantile(d, 0.995))
        thr_env = 0.02 * peak
        cand = np.where((d >= thr_d) & (env_s >= thr_env))[0]
        burst_i = int(cand[0]) if cand.size else int(np.argmax(d))
        burst_t = burst_i / sr

    # ---- voicing onset via Pitch (with stronger stability)
    snd = parselmouth.Sound(y.astype(np.float64), sampling_frequency=sr)
    pitch = snd.to_pitch(time_step=0.005, pitch_floor=60, pitch_ceiling=500)
    f0 = pitch.selected_array["frequency"]
    if f0.size == 0:
        return None

    times = np.array(
        [pitch.get_time_from_frame_number(i + 1) for i in range(f0.size)],
        dtype=np.float64,
    )
    after = np.where(times >= burst_t)[0]
    if after.size == 0:
        return None

    voiced = f0 > 0.0
    win_s = 0.030
    win_n = int(win_s * sr)

    voiced_t: Optional[float] = None

    for i in after:
        if i + 2 >= f0.size:
            break
        if voiced[i] and voiced[i + 1] and voiced[i + 2]:
            f = f0[i:i + 3]
            if (np.max(f) - np.min(f)) > 80.0:
                continue

            t = float(times[i])
            a = int(max(0, (t - win_s / 2) * sr))
            b = int(min(y.size, a + win_n))
            seg = y[a:b]
            per = _acf_periodicity_score(seg, sr, fmin=60.0, fmax=500.0)
            if per >= 0.35:
                voiced_t = t
                break

    if voiced_t is None:
        for i in after:
            if not voiced[i]:
                continue
            t = float(times[i])
            a = int(max(0, (t - win_s / 2) * sr))
            b = int(min(y.size, a + win_n))
            per = _acf_periodicity_score(y[a:b], sr, 60.0, 500.0)
            if per >= 0.35:
                voiced_t = t
                break

    if voiced_t is None:
        return None

    vot_ms = (voiced_t - burst_t) * 1000.0
    vot_ms = float(max(0.0, vot_ms))
    return vot_ms


# ============================================================
# 6) Frication detection & features
# ============================================================

def _rms_envelope(sig: np.ndarray, sr: int, win_s: float = 0.025, hop_s: float = 0.010):
    win = max(int(win_s * sr), 32)
    hop = max(int(hop_s * sr), 16)
    n = 1 + max(0, sig.size - win) // hop
    rms = np.zeros(n, dtype=np.float64)
    for i in range(n):
        seg = sig[i * hop:i * hop + win]
        rms[i] = math.sqrt(np.mean(seg * seg) + 1e-12)
    return rms, win, hop


def detect_frication_region(y: np.ndarray, sr: int) -> Tuple[float, float]:
    """
    Detect frication region using HF/LF RMS ratio.
    - backtrack start, forward end
    - cap 180 ms
    """
    y_hf = bandpass(y, sr, 1500.0, 8000.0)
    y_lf = bandpass(y, sr, 300.0, 1500.0)

    rms_hf, win, hop = _rms_envelope(y_hf, sr)
    rms_lf, _, _ = _rms_envelope(y_lf, sr)
    ratio = rms_hf / (rms_lf + 1e-12)

    if ratio.size == 0:
        return 0.0, min(0.18, y.size / sr)

    ratio_s = _moving_average(ratio, win=5)

    idx_peak = int(np.argmax(ratio_s))
    peak = float(ratio_s[idx_peak])
    if not np.isfinite(peak) or peak <= 0.0:
        return 0.0, min(0.18, y.size / sr)

    start_frac = 0.45
    end_frac = 0.20
    start_thr = start_frac * peak
    end_thr = end_frac * peak

    i0 = idx_peak
    while i0 > 0 and ratio_s[i0] >= start_thr:
        i0 -= 1

    i1 = idx_peak
    while i1 < ratio_s.size - 1 and ratio_s[i1] >= end_thr:
        i1 += 1

    t0 = (i0 * hop) / sr
    t1 = (i1 * hop) / sr

    if t1 <= t0:
        t1 = t0 + 0.08

    t1 = min(t1, t0 + 0.18)

    total = y.size / sr
    t0 = float(np.clip(t0, 0.0, max(0.0, total - 0.02)))
    t1 = float(np.clip(t1, t0 + 0.02, total))
    return t0, t1


def compute_frication_features(
    y: np.ndarray, sr: int, t0: float, t1: float
) -> Tuple[Optional[float], Optional[float]]:
    """
    Use an early 50 ms slice after t0 to reduce vowel contamination.
    """
    if t1 <= t0:
        return None, None

    total = y.size / sr

    seg_t0 = float(t0 + 0.010)
    seg_t1 = float(t0 + 0.060)

    seg_t0 = float(np.clip(seg_t0, 0.0, max(0.0, total - 0.02)))
    seg_t1 = float(np.clip(seg_t1, seg_t0 + 0.02, total))
    if seg_t1 > t1:
        seg_t1 = float(max(t0 + 0.02, t1))
    if seg_t1 <= seg_t0:
        seg_t0, seg_t1 = t0, t1

    a = int(seg_t0 * sr)
    b = int(seg_t1 * sr)
    seg_raw = y[a:b]

    if seg_raw.size < int(0.02 * sr):
        return None, None

    seg_cent = preemphasis(seg_raw.copy())
    freqs_c, pxx_c = scipy.signal.welch(seg_cent, fs=sr, nperseg=min(1024, seg_cent.size))
    pxx_c = np.maximum(pxx_c, 1e-18)
    band = (freqs_c >= 500) & (freqs_c <= 8000)
    if not np.any(band):
        return None, None
    denom = float(np.sum(pxx_c[band]))
    if denom <= 0.0 or not np.isfinite(denom):
        return None, None
    centroid = float(np.sum(freqs_c[band] * pxx_c[band]) / denom)

    freqs_h, pxx_h = scipy.signal.welch(seg_raw, fs=sr, nperseg=min(1024, seg_raw.size))
    pxx_h = np.maximum(pxx_h, 1e-18)

    e_low = float(np.sum(pxx_h[(freqs_h >= 500) & (freqs_h < 2000)]))
    e_high = float(np.sum(pxx_h[(freqs_h >= 3500) & (freqs_h <= 8000)]))
    hf_db = 10.0 * math.log10((e_high + 1e-12) / (e_low + 1e-12))
    hf_db = float(np.clip(hf_db, -30.0, 60.0))

    return centroid, hf_db


# ============================================================
# 7) Scoring
# ============================================================

def gaussian_score(x, mu, sigma):
    if x is None:
        return None
    return 100.0 * math.exp(-((x - mu) ** 2) / (2 * sigma ** 2))


# ============================================================
# 8) Feedback (PATCH: score-aware messaging)
# ============================================================

def _quality_label(score: Optional[float]) -> str:
    if score is None:
        return "Unknown"
    if score >= 80:
        return "Excellent"
    if score >= 65:
        return "Good"
    if score >= 45:
        return "Close"
    return "Needs practice"


def generate_feedback(target: str, detected: str, target_score: Optional[float]) -> str:
    """
    User-friendly English feedback for Korean affricates.
    Korean syllables (자 / 짜 / 차) are kept as-is for clarity.

    PATCH:
      - If target==detected but score is low, say "Close" rather than "Good job!"
    """
    quality = _quality_label(target_score)

    # ✅ Correct class
    if target == detected:
        if target == "fortis":
            if quality in ("Excellent", "Good"):
                return (
                    f"{quality}! This sounds like '짜'. "
                    "Keep your tongue tight and release it quickly. "
                    "Do not let extra air come out."
                )
            return (
                f"{quality}. It is basically '짜', but not consistent yet. "
                "Make it shorter and tighter, and reduce extra airflow."
            )

        if target == "lenis":
            if quality in ("Excellent", "Good"):
                return (
                    f"{quality}! This sounds like '자'. "
                    "Start comfortably and naturally. "
                    "Do not tense your tongue too much, and do not push out extra air."
                )
            return (
                f"{quality}. It is close to '자', but it drifts. "
                "Relax a bit and keep the airflow moderate (not too tight, not too airy)."
            )

        if target == "aspirated":
            if quality in ("Excellent", "Good"):
                return (
                    f"{quality}! This sounds like '차'. "
                    "When you release your tongue, let a small puff of air follow. "
                    "(Light 'ha' feeling.)"
                )
            return (
                f"{quality}. It is basically '차', but the timing is off. "
                "Try to release and move into the vowel a little sooner (do not hold the hiss too long)."
            )

    # ❌ Not correct – targeted advice (based on target & detected)
    if target == "aspirated":
        if detected == "fortis":
            return (
                "Right now it sounds more like '짜'. "
                "Add more air at the release so '차' has a clear puff of breath."
            )
        if detected == "lenis":
            return (
                "Right now it sounds closer to '자'. "
                "Push a bit more air at the release to make it sound like '차'."
            )
        return (
            "'차' needs audible air after the release. "
            "Release your tongue and let the air flow out together."
        )

    if target == "fortis":
        if detected == "aspirated":
            return (
                "Right now it sounds like '차' because too much air is coming out. "
                "Reduce the air and keep your tongue tighter for '짜'."
            )
        if detected == "lenis":
            return (
                "Right now it sounds like '자'. "
                "Tighten your tongue more and release it quickly to make a strong '짜'."
            )
        return (
            "'짜' should be short and tense. "
            "Hold the tongue firmly and release it fast, with almost no extra air."
        )

    if target == "lenis":
        if detected == "fortis":
            return (
                "Right now it sounds too strong, like '짜'. "
                "Relax your tongue a little and make the start more comfortable for '자'."
            )
        if detected == "aspirated":
            return (
                "Right now it sounds like '차' with too much air. "
                "Reduce the airflow and aim for a softer, more relaxed '자'."
            )
        return (
            "'자' should be balanced. "
            "Do not tense too much and do not add extra air—just start naturally."
        )

    return (
        "Focus on how you release your tongue. "
        "Think clearly about whether you want '짜' (tight), '자' (comfortable), or '차' (with air)."
    )


# ============================================================
# 9) Main API
# ============================================================

def analyze_affricate(wav_path: str, syllable: str) -> Dict[str, Any]:
    if syllable not in AFFRICATE_SET:
        return {"error": "Unsupported affricate syllable"}

    target = AFFRICATE_META[syllable]["affricate"]

    snd, y, sr = load_sound(wav_path)
    y_trim, offset = trim_by_intensity(snd, y, sr)

    # detect frication FIRST
    fric_t0, fric_t1 = detect_frication_region(y_trim, sr)
    fric_dur = (fric_t1 - fric_t0) * 1000.0

    vot = estimate_vot_ms(y_trim, sr, burst_hint_t=fric_t0)

    # PATCH: clamp extreme VOT (late voicing detection -> unrealistic scores)
    if vot is not None:
        vot = float(min(vot, VOT_CAP_MS))

    centroid, hf_db = compute_frication_features(y_trim, sr, fric_t0, fric_t1)

    scores: Dict[str, float] = {}
    for lab in ("fortis", "lenis", "aspirated"):
        s_vot = gaussian_score(vot, REF_VOT_MS[lab], REF_VOT_SIGMA)
        s_dur = gaussian_score(fric_dur, REF_FRIC_DUR_MS[lab], REF_FRIC_DUR_SIGMA)
        s_cent = gaussian_score(centroid, REF_CENTROID_HZ[lab], REF_CENTROID_SIGMA)
        s_hf = gaussian_score(hf_db, REF_HF_CONTRAST_DB[lab], REF_HF_CONTRAST_SIGMA)

        s_spec = None
        if (s_cent is not None) and (s_hf is not None):
            s_spec = 0.6 * s_cent + 0.4 * s_hf

        final = 0.0
        if (s_vot is not None) and (s_spec is not None) and (s_dur is not None):
            final = (
                W_VOT * s_vot +
                W_SPEC * s_spec +
                W_FRIC_DUR * s_dur
            )

        scores[lab] = float(final)

    detected = max(scores, key=scores.get)
    target_score = float(scores[target])

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
            "final_score": target_score,
        },
        "feedback": {
            "text": generate_feedback(target, detected, target_score)
        }
    }

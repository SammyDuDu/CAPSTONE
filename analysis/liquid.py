# analysis/liquid.py
from __future__ import annotations

import math
from typing import Dict, Optional, Tuple, Any

import numpy as np
import scipy.signal
import parselmouth


# ============================================================
# 0) Metadata
# ============================================================

LIQUID_META = {
    # 최소 세트: ㄹ을 대표하는 CV
    "라": {"place": "alveolar", "liquid": True},  # ㄹ
}
LIQUID_SET = set(LIQUID_META.keys())


# ============================================================
# 1) Reference targets (heuristic)
#    Korean ㄹ (syllable-initial in '라') is often realized like a light flap/tap or liquid-like onset.
#    We use simple acoustic heuristics:
#      - brief energy dip (tap-like constriction) early after onset
#      - relatively low F3 compared to "pure vowel start" (liquid cue)
#      - low spectral centroid (avoid frication/noisy onset)
# ============================================================

# ---- F3 onset (Hz) : liquid cue ----
REF_F3_ONSET_HZ = {
    "liquid": 2500.0,
}
REF_F3_SIGMA = 650.0

# ---- Closure depth (dB) : tap-like brief constriction cue ----
# closure_depth_db = 10*log10(median_energy / min_energy) over first ~80ms
REF_CLOSURE_DEPTH_DB = {
    "liquid": 10.0,  # moderate dip
}
REF_CLOSURE_DEPTH_SIGMA = 6.0

# ---- Spectral centroid (Hz) on early onset window: should be low (smooth, not fricative) ----
REF_CENTROID_HZ = {
    "liquid": 900.0,
}
REF_CENTROID_SIGMA = 650.0

# ---- Weights ----
W_F3 = 0.45
W_CLOSURE = 0.35
W_CENTROID = 0.20


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
# 4) Onset detection (no burst needed)
# ============================================================

def estimate_onset_t(y: np.ndarray, sr: int) -> Optional[float]:
    """
    Approx onset for '라': find first meaningful rise in broadband envelope.
    """
    if y.size < int(0.05 * sr):
        return None

    y_bp = bandpass(y, sr, 80.0, 4000.0)
    env = np.abs(y_bp)
    peak = float(np.max(env)) if env.size else 0.0
    if peak <= 0.0:
        return None

    env_s = _moving_average(env, win=max(5, int(0.005 * sr)))
    thr = 0.06 * peak
    idx = np.where(env_s >= thr)[0]
    if idx.size == 0:
        return None
    return float(int(idx[0]) / sr)


def _safe_segment(y: np.ndarray, sr: int, t0: float, dur_s: float) -> Optional[np.ndarray]:
    a = int(max(0, round(t0 * sr)))
    b = int(min(y.size, round((t0 + dur_s) * sr)))
    if b - a < int(0.02 * sr):
        return None
    return y[a:b].copy()


# ============================================================
# 5) Feature extraction
# ============================================================

def estimate_f3_onset_hz(y: np.ndarray, sr: int, onset_t: float) -> Optional[float]:
    """
    Use Praat Burg formants, sample near onset+60ms (into vowel transition).
    """
    if not np.isfinite(onset_t):
        return None

    snd = parselmouth.Sound(y.astype(np.float64), sampling_frequency=sr)
    total = float(snd.get_total_duration())

    t = float(onset_t + 0.060)
    t = float(np.clip(t, 0.0, max(0.0, total - 0.01)))

    try:
        formant = snd.to_formant_burg(
            time_step=0.005, max_number_of_formants=5, maximum_formant=5500
        )
        f3 = float(formant.get_value_at_time(3, t))
        if not np.isfinite(f3) or f3 <= 0:
            return None
        return float(np.clip(f3, 1200.0, 4500.0))
    except Exception:
        return None


def compute_closure_depth_db(y: np.ndarray, sr: int, onset_t: float) -> Optional[float]:
    """
    Tap-like cue: find a brief energy dip early after onset.
    Compute RMS energy over frames in first ~80ms window after onset,
    then closure_depth_db = 10*log10(median_energy / min_energy).
    """
    seg = _safe_segment(y, sr, onset_t, 0.090)  # 90 ms
    if seg is None:
        return None

    win = max(int(0.010 * sr), 128)  # 10ms
    hop = max(int(0.005 * sr), 64)   # 5ms
    n = 1 + max(0, (seg.size - win) // hop)
    if n <= 3:
        return None

    e = np.zeros(n, dtype=np.float64)
    for i in range(n):
        a = i * hop
        b = a + win
        x = seg[a:b]
        e[i] = float(np.mean(x * x) + 1e-12)

    med = float(np.median(e))
    mn = float(np.min(e))
    if med <= 0.0 or mn <= 0.0:
        return None

    depth_db = 10.0 * math.log10((med + 1e-12) / (mn + 1e-12))
    return float(np.clip(depth_db, 0.0, 30.0))


def compute_centroid_hz(y: np.ndarray, sr: int, onset_t: float) -> Optional[float]:
    """
    Smooth onset cue: centroid should not be too high (avoid frication-like noise).
    Use early window onset+10ms ~ +70ms (60ms slice).
    """
    seg = _safe_segment(y, sr, onset_t + 0.010, 0.060)
    if seg is None:
        return None

    seg = seg.astype(np.float64)
    seg = seg - float(np.mean(seg))

    freqs, pxx = scipy.signal.welch(seg, fs=sr, nperseg=min(1024, seg.size))
    pxx = np.maximum(pxx, 1e-18)

    band = (freqs >= 0) & (freqs <= 3000)
    denom = float(np.sum(pxx[band]))
    if denom <= 0.0 or not np.isfinite(denom):
        return None

    centroid = float(np.sum(freqs[band] * pxx[band]) / denom)
    return float(np.clip(centroid, 0.0, 5000.0))


# ============================================================
# 6) Scoring
# ============================================================

def gaussian_score(x: Optional[float], mu: float, sigma: float) -> Optional[float]:
    if x is None:
        return None
    return 100.0 * math.exp(-((x - mu) ** 2) / (2 * sigma ** 2))


# ============================================================
# 7) Feedback (English, keep Korean syllables)
# ============================================================

def generate_feedback(
    syllable: str,
    final_score: float,
    f3: Optional[float],
    closure_depth_db: Optional[float],
    centroid: Optional[float],
) -> str:
    """
    User-friendly feedback for Korean 'ㄹ' (라).
    Focus on tongue movement and timing.
    """

    # ---------------------------
    # Very good
    # ---------------------------
    if final_score >= 75.0:
        return (
            "Good job! This sounds like '라'. "
            "Touch your tongue quickly to the ridge behind your teeth, "
            "then move smoothly into the vowel."
        )

    tips = []

    # ---------------------------
    # Tongue contact clarity
    # ---------------------------
    if closure_depth_db is None or closure_depth_db < 5.0:
        tips.append(
            "Your tongue is not touching clearly enough. "
            "Try a quick, light tongue touch before saying '아'."
        )
    elif closure_depth_db > 18.0:
        tips.append(
            "Your tongue is pressing too strongly. "
            "Make the touch lighter and shorter."
        )

    # ---------------------------
    # Smoothness (avoid noise)
    # ---------------------------
    if centroid is not None and centroid > 1600.0:
        tips.append(
            "There is too much air noise. "
            "Say it smoothly—do not blow air when starting '라'."
        )

    # ---------------------------
    # ㄹ quality hint (optional fine-tuning)
    # ---------------------------
    if f3 is not None:
        if f3 > 3300.0:
            tips.append(
                "It sounds too much like a vowel. "
                "Make sure your tongue actually touches before moving into '아'."
            )
        elif f3 < 1700.0:
            tips.append(
                "It sounds too heavy. "
                "Release your tongue faster and move into the vowel sooner."
            )

    # ---------------------------
    # Compose message
    # ---------------------------
    if final_score >= 60.0:
        return "Close! " + " ".join(tips)

    return "Not quite yet. " + " ".join(tips)


# ============================================================
# 8) Main API
# ============================================================

def analyze_liquid(wav_path: str, syllable: str) -> Dict[str, Any]:
    """
    Minimal liquid analyzer for ㄹ using '라'.
    Returns JSON compatible with other analyzers.
    """
    if syllable not in LIQUID_SET:
        return {"error": "Unsupported liquid syllable (supported: 라)"}

    target_place = LIQUID_META[syllable]["place"]

    snd, y, sr = load_sound(wav_path)
    y_trim, offset = trim_by_intensity(snd, y, sr)

    onset_t = estimate_onset_t(y_trim, sr)
    if onset_t is None:
        return {
            "syllable": syllable,
            "type": "liquid",
            "targets": {"place": target_place, "liquid": True},
            "features": {
                "onset_t": None,
                "f3_onset_hz": None,
                "closure_depth_db": None,
                "spectral_centroid_hz": None,
            },
            "evaluation": {
                "softscores": {},
                "final_score": 0.0,
            },
            "feedback": {
                "text": "I couldn't find a clear onset. Try recording again closer to the mic with less background noise."
            },
        }

    f3 = estimate_f3_onset_hz(y_trim, sr, onset_t)
    depth_db = compute_closure_depth_db(y_trim, sr, onset_t)
    centroid = compute_centroid_hz(y_trim, sr, onset_t)

    s_f3 = gaussian_score(f3, REF_F3_ONSET_HZ["liquid"], REF_F3_SIGMA)
    s_depth = gaussian_score(depth_db, REF_CLOSURE_DEPTH_DB["liquid"], REF_CLOSURE_DEPTH_SIGMA)
    s_cent = gaussian_score(centroid, REF_CENTROID_HZ["liquid"], REF_CENTROID_SIGMA)

    # If any score missing, treat missing as 0 (robust for varied recordings)
    s_f3_v = float(s_f3) if s_f3 is not None else 0.0
    s_depth_v = float(s_depth) if s_depth is not None else 0.0
    s_cent_v = float(s_cent) if s_cent is not None else 0.0

    final_score = float(W_F3 * s_f3_v + W_CLOSURE * s_depth_v + W_CENTROID * s_cent_v)

    return {
        "syllable": syllable,
        "type": "liquid",
        "targets": {"place": target_place, "liquid": True},
        "features": {
            "onset_t": float(onset_t),
            "f3_onset_hz": f3,
            "closure_depth_db": depth_db,
            "spectral_centroid_hz": centroid,
        },
        "evaluation": {
            "softscores": {
                "f3": s_f3_v,
                "closure_depth": s_depth_v,
                "smoothness": s_cent_v,
            },
            "final_score": float(final_score),
        },
        "feedback": {
            "text": generate_feedback(
                syllable=syllable,
                final_score=final_score,
                f3=f3,
                closure_depth_db=depth_db,
                centroid=centroid,
            )
        },
    }

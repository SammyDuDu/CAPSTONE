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
    "라": {"place": "alveolar", "liquid": True},  # ㄹ
}
LIQUID_SET = set(LIQUID_META.keys())


# ============================================================
# 1) Reference targets (heuristic)
# ============================================================

# Note: F3 is vowel-influenced, so keep weight moderate and rely on gates.
REF_F3_ONSET_HZ = {"liquid": 2500.0}
REF_F3_SIGMA = 650.0

# Tongue contact depth: 0 too smooth (like '아'), too deep (like '나/다')
REF_CLOSURE_DEPTH_DB = {"liquid": 10.0}
REF_CLOSURE_DEPTH_SIGMA = 6.0

# Smoothness / no hiss
REF_CENTROID_HZ = {"liquid": 900.0}
REF_CENTROID_SIGMA = 650.0

# NEW: frication gate feature (HF/LF ratio peak)
REF_FRIC_RATIO_PEAK = {"liquid": 1.2}   # liquid should be low
REF_FRIC_RATIO_SIGMA = 0.7

# NEW: voicing gate feature (periodicity / voiced fraction)
REF_VOICED_FRAC = {"liquid": 0.70}      # should be mostly voiced
REF_VOICED_FRAC_SIGMA = 0.20

# weights (sum=1.0)
W_F3 = 0.25
W_CLOSURE = 0.35
W_CENTROID = 0.20
W_FRIC = 0.10
W_VOICED = 0.10


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


def _safe_segment(y: np.ndarray, sr: int, t0: float, dur_s: float) -> Optional[np.ndarray]:
    a = int(max(0, round(t0 * sr)))
    b = int(min(y.size, round((t0 + dur_s) * sr)))
    if b - a < int(0.02 * sr):
        return None
    return y[a:b].copy()


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
# 4) Onset detection
# ============================================================

def estimate_onset_t(y: np.ndarray, sr: int) -> Optional[float]:
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


# ============================================================
# 5) Feature extraction
# ============================================================

def estimate_f3_onset_hz(y: np.ndarray, sr: int, onset_t: float) -> Optional[float]:
    snd = parselmouth.Sound(y.astype(np.float64), sampling_frequency=sr)
    total = float(snd.get_total_duration())

    t = float(onset_t + 0.060)
    t = float(np.clip(t, 0.0, max(0.0, total - 0.01)))

    try:
        formant = snd.to_formant_burg(time_step=0.005, max_number_of_formants=5, maximum_formant=5500)
        f3 = float(formant.get_value_at_time(3, t))
        if not np.isfinite(f3) or f3 <= 0:
            return None
        return float(np.clip(f3, 1200.0, 4500.0))
    except Exception:
        return None


def compute_closure_depth_db(y: np.ndarray, sr: int, onset_t: float) -> Optional[float]:
    # 90ms from onset
    seg = _safe_segment(y, sr, onset_t, 0.090)
    if seg is None:
        return None

    win = max(int(0.010 * sr), 128)
    hop = max(int(0.005 * sr), 64)
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
    # early 60ms slice
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


def compute_frication_ratio_peak(y: np.ndarray, sr: int, onset_t: float) -> Optional[float]:
    """
    Strong /s/ has high HF energy near onset.
    HF: 3000-8000, LF: 300-2000.
    Return peak HF/LF RMS ratio in first 120ms.
    """
    seg = _safe_segment(y, sr, onset_t, 0.120)
    if seg is None:
        return None

    hf = bandpass(seg, sr, 3000.0, 8000.0)
    lf = bandpass(seg, sr, 300.0, 2000.0)

    win = max(int(0.020 * sr), 256)
    hop = max(int(0.010 * sr), 128)
    n = 1 + max(0, (seg.size - win) // hop)
    if n <= 2:
        return None

    ratios = []
    for i in range(n):
        a = i * hop
        b = a + win
        h = hf[a:b]
        l = lf[a:b]
        rh = math.sqrt(float(np.mean(h * h) + 1e-12))
        rl = math.sqrt(float(np.mean(l * l) + 1e-12))
        ratios.append(rh / (rl + 1e-12))

    rpk = float(np.max(ratios)) if ratios else None
    if rpk is None or not np.isfinite(rpk):
        return None
    return float(np.clip(rpk, 0.0, 10.0))


def compute_voiced_fraction(y: np.ndarray, sr: int, onset_t: float) -> Optional[float]:
    """
    Liquid should be voiced. Estimate voiced fraction in 200ms after onset using Pitch.
    """
    seg = _safe_segment(y, sr, onset_t, 0.200)
    if seg is None:
        return None

    snd = parselmouth.Sound(seg.astype(np.float64), sampling_frequency=sr)
    pitch = snd.to_pitch(time_step=0.01, pitch_floor=60, pitch_ceiling=500)
    f0 = pitch.selected_array["frequency"]
    if f0.size == 0:
        return None

    voiced = np.mean((f0 > 0.0).astype(np.float64))
    return float(np.clip(voiced, 0.0, 1.0))


# ============================================================
# 6) Scoring + reject
# ============================================================

def gaussian_score(x: Optional[float], mu: float, sigma: float) -> Optional[float]:
    if x is None:
        return None
    return 100.0 * math.exp(-((x - mu) ** 2) / (2 * sigma ** 2))


def _confidence_from_softscores(scores: Dict[str, float]) -> float:
    """
    Simple confidence from score sharpness.
    """
    vals = np.array(list(scores.values()), dtype=np.float64)
    if vals.size == 0:
        return 0.0
    # squash to 0..1
    return float(np.clip((np.max(vals) - np.median(vals)) / 60.0, 0.0, 1.0))


# ============================================================
# 7) Feedback
# ============================================================

def generate_feedback(is_rejected: bool, reject_reason: str, final_score: float) -> str:
    if is_rejected:
        if reject_reason == "too_fricative":
            return (
                "This sounds too hissy (like '사'). "
                "For '라', do NOT blow air. Lightly tap your tongue once behind your teeth, then go straight into '아'."
            )
        if reject_reason == "too_unvoiced":
            return (
                "This sounds too unvoiced. "
                "For '라', keep your voice on (a gentle hum) while you tap your tongue, then move into '아'."
            )
        if reject_reason == "no_tongue_contact":
            return (
                "It sounds too smooth, like it skipped the tongue touch. "
                "For '라', make one quick tongue tap behind your teeth before the vowel."
            )
        return "Try again: tap your tongue lightly behind your teeth and move into the vowel smoothly."

    if final_score >= 75.0:
        return (
            "Good job! This sounds like '라'. "
            "Touch your tongue quickly to the ridge behind your teeth, then move smoothly into the vowel."
        )

    if final_score >= 60.0:
        return (
            "Close! Make the tongue touch clearer but still quick. "
            "Do not add a hiss—go straight into the vowel."
        )

    return (
        "Not quite yet. For '라', avoid a hissy start. "
        "Tap your tongue lightly behind your teeth and move into '아' immediately."
    )


# ============================================================
# 8) Main API
# ============================================================

def analyze_liquid(wav_path: str, syllable: str) -> Dict[str, Any]:
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
            "features": {},
            "evaluation": {"final_score": 0.0, "is_rejected": True, "reject_reason": "no_onset"},
            "feedback": {"text": "I couldn't find a clear onset. Try recording again closer to the mic with less background noise."},
        }

    f3 = estimate_f3_onset_hz(y_trim, sr, onset_t)
    depth_db = compute_closure_depth_db(y_trim, sr, onset_t)
    centroid = compute_centroid_hz(y_trim, sr, onset_t)
    fric_pk = compute_frication_ratio_peak(y_trim, sr, onset_t)
    voiced_frac = compute_voiced_fraction(y_trim, sr, onset_t)

    s_f3 = gaussian_score(f3, REF_F3_ONSET_HZ["liquid"], REF_F3_SIGMA)
    s_depth = gaussian_score(depth_db, REF_CLOSURE_DEPTH_DB["liquid"], REF_CLOSURE_DEPTH_SIGMA)
    s_cent = gaussian_score(centroid, REF_CENTROID_HZ["liquid"], REF_CENTROID_SIGMA)
    s_fric = gaussian_score(fric_pk, REF_FRIC_RATIO_PEAK["liquid"], REF_FRIC_RATIO_SIGMA)
    s_voiced = gaussian_score(voiced_frac, REF_VOICED_FRAC["liquid"], REF_VOICED_FRAC_SIGMA)

    s_f3_v = float(s_f3) if s_f3 is not None else 0.0
    s_depth_v = float(s_depth) if s_depth is not None else 0.0
    s_cent_v = float(s_cent) if s_cent is not None else 0.0
    s_fric_v = float(s_fric) if s_fric is not None else 0.0
    s_voiced_v = float(s_voiced) if s_voiced is not None else 0.0

    softscores = {
        "f3": s_f3_v,
        "closure_depth": s_depth_v,
        "smoothness": s_cent_v,
        "non_fricative": s_fric_v,
        "voicing": s_voiced_v,
    }

    final_score = float(
        W_F3 * s_f3_v +
        W_CLOSURE * s_depth_v +
        W_CENTROID * s_cent_v +
        W_FRIC * s_fric_v +
        W_VOICED * s_voiced_v
    )

    # ---------------------------
    # REJECT GATES (critical!)
    # ---------------------------
    is_rejected = False
    reject_reason = ""

    # 1) too fricative -> likely '사'
    if fric_pk is not None and fric_pk >= 2.6:
        is_rejected = True
        reject_reason = "too_fricative"

    # 2) too unvoiced -> likely fricative / noise
    if (not is_rejected) and (voiced_frac is not None) and (voiced_frac <= 0.35):
        is_rejected = True
        reject_reason = "too_unvoiced"

    # 3) no tongue contact -> likely '아' / vowel-like
    if (not is_rejected) and (depth_db is not None) and (depth_db <= 3.5):
        is_rejected = True
        reject_reason = "no_tongue_contact"

    # If rejected, cap final score hard (prevents false positives)
    if is_rejected:
        final_score = min(final_score, 35.0)

    confidence = _confidence_from_softscores(softscores)

    return {
        "syllable": syllable,
        "type": "liquid",
        "targets": {"place": target_place, "liquid": True},
        "features": {
            "onset_t": float(onset_t),
            "f3_onset_hz": f3,
            "closure_depth_db": depth_db,
            "spectral_centroid_hz": centroid,
            "frication_ratio_peak": fric_pk,
            "voiced_fraction": voiced_frac,
        },
        "evaluation": {
            "softscores": softscores,
            "final_score": float(final_score),
            "confidence": float(confidence),
            "is_rejected": bool(is_rejected),
            "reject_reason": reject_reason,
        },
        "feedback": {"text": generate_feedback(is_rejected, reject_reason, float(final_score))},
    }

# analysis/nasal.py
from __future__ import annotations

import math
from typing import Dict, Optional, Tuple, Any

import numpy as np
import scipy.signal
import parselmouth


# ============================================================
# 0) Metadata
# ============================================================

NASAL_META = {
    "마": {"place": "labial", "nasal": True},    # ㅁ
    "나": {"place": "alveolar", "nasal": True},  # ㄴ
}
NASAL_SET = set(NASAL_META.keys())


# ============================================================
# 1) Reference targets (heuristic)
# ============================================================

# ---- F2 onset (Hz) : place cue ----
REF_F2_ONSET_HZ = {
    "labial": 1200.0,   # ㅁ
    "alveolar": 1700.0, # ㄴ
}
REF_F2_SIGMA = 350.0

# ---- Low-frequency dominance (ratio, 0~1) ----
# 기존 0.55는 너 샘플(마≈0.62, 나≈0.84) 기준으로 너무 낮아서
# 비음인데도 점수가 떨어지는 문제가 있었음 → 평균을 올리고 sigma도 약간 키움
REF_LOW_RATIO = {
    "nasal": 0.72,
}
REF_LOW_RATIO_SIGMA = 0.22

# ---- Spectral centroid (Hz) on nasal murmur window ----
# 너 샘플 centroid(마≈451, 나≈347)가 훨씬 낮게 나와서
# 기존 900은 비음인데도 점수가 떨어질 수 있음 → target을 낮추고 sigma도 조정
REF_CENTROID_HZ = {
    "nasal": 500.0,
}
REF_CENTROID_SIGMA = 350.0

# ---- Weights ----
W_PLACE = 0.55
W_NASALITY = 0.45


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
# 4) Onset detection for nasals
# ============================================================

def estimate_onset_t(y: np.ndarray, sr: int) -> Optional[float]:
    """
    Nasal은 burst가 없으므로 broadband(80~4000) envelope 상승을 onset으로 잡는다.
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


# ============================================================
# 5) Feature extraction
# ============================================================

def _safe_segment(y: np.ndarray, sr: int, t0: float, dur_s: float) -> Optional[np.ndarray]:
    a = int(max(0, round(t0 * sr)))
    b = int(min(y.size, round((t0 + dur_s) * sr)))
    if b - a < int(0.02 * sr):
        return None
    return y[a:b].copy()


def compute_nasal_window_features(
    y: np.ndarray,
    sr: int,
    onset_t: float,
) -> Tuple[Optional[float], Optional[float]]:
    """
    Nasal murmur 특징:
    - low_ratio: E(0~500) / E(0~2000)
    - centroid: spectral centroid (0~3000) on early nasal window
    """
    seg = _safe_segment(y, sr, onset_t + 0.010, 0.070)  # 10ms~80ms
    if seg is None:
        return None, None

    seg = seg.astype(np.float64)
    seg = seg - float(np.mean(seg))

    freqs, pxx = scipy.signal.welch(seg, fs=sr, nperseg=min(1024, seg.size))
    pxx = np.maximum(pxx, 1e-18)

    e_0_500 = float(np.sum(pxx[(freqs >= 0) & (freqs < 500)]))
    e_0_2000 = float(np.sum(pxx[(freqs >= 0) & (freqs <= 2000)]))
    low_ratio = e_0_500 / (e_0_2000 + 1e-12)
    low_ratio = float(np.clip(low_ratio, 0.0, 1.0))

    band = (freqs >= 0) & (freqs <= 3000)
    denom = float(np.sum(pxx[band]))
    centroid = None
    if denom > 0.0 and np.isfinite(denom):
        centroid = float(np.sum(freqs[band] * pxx[band]) / denom)

    return low_ratio, centroid


def estimate_f2_onset_hz(
    y: np.ndarray,
    sr: int,
    onset_t: float,
) -> Optional[float]:
    """
    Place cue: onset+60ms 지점의 F2
    """
    if not np.isfinite(onset_t):
        return None

    snd = parselmouth.Sound(y.astype(np.float64), sampling_frequency=sr)
    total = float(snd.get_total_duration())

    t = float(onset_t + 0.060)
    t = float(np.clip(t, 0.0, max(0.0, total - 0.01)))

    try:
        formant = snd.to_formant_burg(time_step=0.005, max_number_of_formants=5, maximum_formant=5500)
        f2 = float(formant.get_value_at_time(2, t))
        if not np.isfinite(f2) or f2 <= 0:
            return None
        return float(np.clip(f2, 500.0, 3500.0))
    except Exception:
        return None


# ============================================================
# 6) Scoring
# ============================================================

def gaussian_score(x: Optional[float], mu: float, sigma: float) -> Optional[float]:
    if x is None:
        return None
    return 100.0 * math.exp(-((x - mu) ** 2) / (2 * sigma ** 2))


def _score_nasality(low_ratio: Optional[float], centroid: Optional[float]) -> Optional[float]:
    s_lr = gaussian_score(low_ratio, REF_LOW_RATIO["nasal"], REF_LOW_RATIO_SIGMA)
    s_c = gaussian_score(centroid, REF_CENTROID_HZ["nasal"], REF_CENTROID_SIGMA)
    if s_lr is None or s_c is None:
        return None
    return 0.55 * s_lr + 0.45 * s_c


def _confidence_from_scores(place_target: float, place_other: float, nasality: float) -> Dict[str, float]:
    """
    confidence는 UI/디버그용:
    - place_margin: target - other (클수록 place 확신 ↑)
    - overall_confidence: [0,1]로 대충 정규화
    """
    place_margin = float(place_target - place_other)
    # 간단 정규화(휴리스틱): place 60↑ + nasality 50↑이면 confidence가 커지도록
    c_place = float(np.clip((place_target - 50.0) / 50.0, 0.0, 1.0))
    c_nasal = float(np.clip((nasality - 40.0) / 60.0, 0.0, 1.0))
    overall = float(np.clip(0.6 * c_place + 0.4 * c_nasal, 0.0, 1.0))
    return {
        "place_margin": place_margin,
        "overall_confidence": overall,
    }


# ============================================================
# 7) Feedback (English, keep Korean syllables)
#    - "Good job"은 점수/확신이 충분할 때만
# ============================================================

def generate_feedback(
    syllable: str,
    target_place: str,
    detected_place: str,
    final_score: float,
    place_target_score: float,
    place_other_score: float,
    nasality_score: float,
) -> str:
    """
    Rules:
      - final_score >= 75 and place_margin >= 10 -> Good job
      - else if detected==target -> Close / Almost
      - else -> correction
    """
    place_margin = place_target_score - place_other_score

    # map for text
    target_word = "마" if target_place == "labial" else "나"
    detected_word = "마" if detected_place == "labial" else "나"

    is_correct = (target_place == detected_place)

    # Tiered praise
    if is_correct and final_score >= 75.0 and place_margin >= 10.0 and nasality_score >= 55.0:
        if target_place == "labial":
            return (
                "Good job! This sounds like '마'. "
                "Start with fully closed lips, then open smoothly while keeping a nasal hum."
            )
        return (
            "Good job! This sounds like '나'. "
            "Touch your tongue lightly to the ridge behind your teeth and keep the sound nasal and smooth."
        )

    if is_correct:
        # correct place but not confident / nasalness weak
        msgs = []
        msgs.append(f"Close. It is basically '{target_word}', but not very strong/clear yet.")
        if nasality_score < 55.0:
            msgs.append("Try to keep a steady nasal hum (feel vibration around the nose) before you move into the vowel.")
        if place_margin < 10.0:
            if target_place == "labial":
                msgs.append("Make sure the sound starts with the lips (m). Do not start with the tongue.")
            else:
                msgs.append("Make sure the sound starts with the tongue touching behind the teeth (n). Keep lips relaxed.")
        if final_score < 60.0:
            msgs.append("Record a bit closer to the mic and keep the start clean (no breathy onset).")
        return " ".join(msgs)

    # Incorrect place -> correction
    if target_place == "labial":
        # wanted ㅁ but got ㄴ
        return (
            f"It sounds closer to '{detected_word}'. For '마', start with your lips closed (m). "
            "Do NOT start with the tongue; let it hum through your nose, then open into '아'."
        )

    # wanted ㄴ but got ㅁ
    return (
        f"It sounds closer to '{detected_word}'. For '나', use your tongue: "
        "touch the ridge behind your upper teeth (n) while keeping your lips relaxed, then move into '아'."
    )


# ============================================================
# 8) Main API
# ============================================================

def analyze_nasal(wav_path: str, syllable: str) -> Dict[str, Any]:
    if syllable not in NASAL_SET:
        return {"error": "Unsupported nasal syllable (supported: 마, 나)"}

    target_place = NASAL_META[syllable]["place"]

    snd, y, sr = load_sound(wav_path)
    y_trim, offset = trim_by_intensity(snd, y, sr)

    onset_t = estimate_onset_t(y_trim, sr)
    if onset_t is None:
        return {
            "syllable": syllable,
            "type": "nasal",
            "targets": {"place": target_place, "nasal": True},
            "features": {
                "onset_t": None,
                "f2_onset_hz": None,
                "low_ratio_0_500_over_0_2000": None,
                "spectral_centroid_hz": None,
            },
            "evaluation": {
                "detected_place": None,
                "softscores": {},
                "final_score": 0.0,
                "confidence": {"place_margin": 0.0, "overall_confidence": 0.0},
            },
            "feedback": {
                "text": "I couldn't find a clear nasal onset. Try recording again closer to the mic with less background noise."
            },
        }

    low_ratio, centroid = compute_nasal_window_features(y_trim, sr, onset_t)
    f2 = estimate_f2_onset_hz(y_trim, sr, onset_t)

    # place scores
    place_scores: Dict[str, float] = {}
    for place in ("labial", "alveolar"):
        s_f2 = gaussian_score(f2, REF_F2_ONSET_HZ[place], REF_F2_SIGMA)
        place_scores[place] = float(s_f2 if s_f2 is not None else 0.0)

    detected_place = max(place_scores, key=place_scores.get) if place_scores else target_place

    # nasality
    s_nasal = _score_nasality(low_ratio, centroid)
    s_nasal = float(s_nasal) if s_nasal is not None else 0.0

    # final score (target-based)
    s_place_target = float(place_scores.get(target_place, 0.0))
    other_place = "alveolar" if target_place == "labial" else "labial"
    s_place_other = float(place_scores.get(other_place, 0.0))

    final_score = float(W_PLACE * s_place_target + W_NASALITY * s_nasal)

    confidence = _confidence_from_scores(s_place_target, s_place_other, s_nasal)

    feedback_text = generate_feedback(
        syllable=syllable,
        target_place=target_place,
        detected_place=detected_place,
        final_score=final_score,
        place_target_score=s_place_target,
        place_other_score=s_place_other,
        nasality_score=s_nasal,
    )

    return {
        "syllable": syllable,
        "type": "nasal",
        "targets": {"place": target_place, "nasal": True},
        "features": {
            "onset_t": float(onset_t),
            "f2_onset_hz": f2,
            "low_ratio_0_500_over_0_2000": low_ratio,
            "spectral_centroid_hz": centroid,
        },
        "evaluation": {
            "detected_place": detected_place,
            "softscores": {
                "place_labial": float(place_scores.get("labial", 0.0)),
                "place_alveolar": float(place_scores.get("alveolar", 0.0)),
                "nasality": float(s_nasal),
            },
            "final_score": float(final_score),
            "confidence": confidence,
        },
        "feedback": {"text": feedback_text},
    }

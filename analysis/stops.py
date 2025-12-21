from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, Optional, Tuple, Any

import numpy as np
import scipy.signal
import parselmouth

# ============================================================
# 0) Stop metadata (target place / target phonation)
# ============================================================

STOP_META = {
    # Velar group
    "가": {"place": "velar", "phonation": "lenis"},
    "까": {"place": "velar", "phonation": "fortis"},
    "카": {"place": "velar", "phonation": "aspirated"},
    # Alveolar (ㄷ-series)
    "다": {"place": "alveolar", "phonation": "lenis"},
    "따": {"place": "alveolar", "phonation": "fortis"},
    "타": {"place": "alveolar", "phonation": "aspirated"},
    # Labial (ㅂ-series)
    "바": {"place": "labial", "phonation": "lenis"},
    "빠": {"place": "labial", "phonation": "fortis"},
    "파": {"place": "labial", "phonation": "aspirated"},
}

STOP_SET = set(STOP_META.keys())

# ============================================================
# 1) Reference design constants (tunable)
# ============================================================

# --- Place (F2 onset) ---
PLACE_F2_CENTERS_HZ = {
    "labial":   1200.0,
    "alveolar": 1700.0,
    "velar":    2200.0,
}
PLACE_TOLERANCE_HZ = 600.0

PLACE_SIGMA_HZ = 700.0   # 넓게(=성별/개인차/측정오차 흡수)
PLACE_CONF_MARGIN_EPS = 1e-9
PLACE_LOW_CONF_THRESH = 0.20

# --- VOT ranges (unified) ---
VOT_RANGES_MS = {
    "fortis":    (0.0, 20.0, 10.0),
    "lenis":     (20.0, 50.0, 35.0),
    "aspirated": (60.0, 100.0, 80.0),
}
VOT_SOFT_MARGIN_MS = 15.0

# --- F0 z-score targets (speaker-normalized) ---
F0Z_TARGETS = {
    "lenis":     (-0.5, 0.7),  # (center, tolerance)
    "fortis":    ( 1.0, 0.7),
    "aspirated": ( 0.6, 0.7),
}

# --- Weighting ---
PLACE_WEIGHT = 0.40
PHONATION_WEIGHT = 0.60

# Adaptive weighting: when VOT is near a boundary, weight F0 more
VOT_BOUNDARIES_MS = [20.0, 50.0, 60.0, 100.0]
VOT_BOUNDARY_NEAR_MS = 6.0


# ============================================================
# 2) Utility: audio loading and simple filters
# ============================================================

def load_sound(path: str) -> Tuple[parselmouth.Sound, np.ndarray, int]:
    snd = parselmouth.Sound(path)
    y = snd.values.T.flatten().astype(np.float64)
    sr = int(round(snd.sampling_frequency))
    return snd, y, sr

def bandpass(sig: np.ndarray, sr: int, low: float, high: float, order: int = 4) -> np.ndarray:
    nyq = sr / 2.0
    lo = max(low / nyq, 0.0001)
    hi = min(high / nyq, 0.9999)
    b, a = scipy.signal.butter(order, [lo, hi], btype="band")
    return scipy.signal.lfilter(b, a, sig)


# ============================================================
# 3) Feature extraction for stop
# ============================================================

def detect_burst_time(snd: parselmouth.Sound) -> float:
    """
    Estimate the burst time using Praat Intensity.
    We take the first frame that exceeds (max - 30 dB).
    """
    intensity = snd.to_intensity(minimum_pitch=100.0)
    int_vals = intensity.values[0]
    if len(int_vals) == 0:
        return 0.0
    int_max = float(np.max(int_vals))
    cands = np.where(int_vals > (int_max - 30.0))[0]
    if cands.size == 0:
        t = intensity.get_time_from_frame_number(1)
        return float(max(0.0, t))
    idx = int(cands[0])
    return float(intensity.get_time_from_frame_number(idx + 1))

def estimate_vot_ms(snd: parselmouth.Sound, aspirated_mode: bool) -> Tuple[Optional[float], float, Optional[float]]:
    """
    Returns (vot_ms, burst_t, voiced_t).
    - aspirated_mode=True uses a stricter criterion for voiced onset.
    """
    burst_t = detect_burst_time(snd)
    end_t = min(burst_t + 0.18, snd.xmax)
    if end_t <= burst_t:
        return None, burst_t, None

    snd_after = snd.extract_part(from_time=burst_t, to_time=end_t, preserve_times=False)

    pitch = snd_after.to_pitch(time_step=0.001)
    f0 = pitch.selected_array["frequency"]  # 0 if unvoiced
    t_f0 = np.array([pitch.get_time_from_frame_number(i + 1) for i in range(len(f0))])

    harm = snd_after.to_harmonicity_cc(time_step=0.001)
    hnr = harm.values[0] if harm is not None and harm.values is not None else np.array([])
    t_hnr = np.array([harm.get_time_from_frame_number(i + 1) for i in range(len(hnr))]) if len(hnr) > 0 else np.array([])

    intensity = snd_after.to_intensity(minimum_pitch=100.0)
    iv = intensity.values[0] if intensity is not None and len(intensity.values) > 0 else np.array([])
    t_iv = np.array([intensity.get_time_from_frame_number(i + 1) for i in range(len(iv))]) if len(iv) > 0 else np.array([])
    iv_max = float(np.max(iv)) if len(iv) > 0 else -200.0

    voiced_rel = None
    for i in range(len(f0)):
        hz = float(f0[i])
        if hz <= 70.0 or hz >= 400.0:
            continue
        tc = float(t_f0[i])

        # Nearest HNR
        hnr_db = -100.0
        if len(t_hnr) > 0:
            hi = int(np.argmin(np.abs(t_hnr - tc)))
            hnr_db = float(hnr[hi])

        # Nearest intensity
        this_int = -200.0
        if len(t_iv) > 0:
            ii = int(np.argmin(np.abs(t_iv - tc)))
            this_int = float(iv[ii])

        if aspirated_mode:
            # Clearer periodicity after aspiration
            if (hnr_db > 5.0) and (this_int > (iv_max - 40.0)):
                voiced_rel = tc
                break
        else:
            # Lenis/fortis: allow earlier, weaker voicing
            if this_int > (iv_max - 50.0):
                voiced_rel = tc
                break

    if voiced_rel is None:
        idx = np.where((f0 > 70.0) & (f0 < 400.0))[0]
        if idx.size == 0:
            return None, burst_t, None
        voiced_rel = float(t_f0[int(idx[0])])

    voiced_t = float(burst_t + voiced_rel)
    vot_ms = max(0.0, (voiced_t - burst_t) * 1000.0)
    return float(vot_ms), float(burst_t), float(voiced_t)

def estimate_f2_onset_hz(
    snd_full: parselmouth.Sound,
    voiced_t: Optional[float],
    offset_ms: float = 20.0,
    max_formant: float = 5500.0
) -> Optional[float]:
    """
    Estimate F2 at (voiced onset + offset), used for stop place cues.
    """
    if voiced_t is None:
        return None
    t = voiced_t + offset_ms / 1000.0
    t = min(max(t, snd_full.xmin), snd_full.xmax)

    formant = snd_full.to_formant_burg(
        time_step=0.005,
        max_number_of_formants=5,
        maximum_formant=max_formant
    )
    f2 = formant.get_value_at_time(2, t)
    if f2 is None or np.isnan(f2) or f2 <= 0:
        return None
    return float(f2)

def estimate_vowel_onset_f0_hz(
    snd_full: parselmouth.Sound,
    voiced_t: Optional[float],
    onset_win_ms: float = 30.0,
    pitch_floor: float = 100.0,
    pitch_ceiling: float = 500.0
) -> Optional[float]:
    """
    Estimate a single F0 value near vowel onset:
    take the median F0 in [voiced_t, voiced_t + onset_win].
    """
    if voiced_t is None:
        return None
    start = voiced_t
    end = min(voiced_t + onset_win_ms / 1000.0, snd_full.xmax)
    if end <= start:
        return None
    seg = snd_full.extract_part(from_time=start, to_time=end, preserve_times=False)
    pitch = seg.to_pitch(time_step=0.005, pitch_floor=pitch_floor, pitch_ceiling=pitch_ceiling)
    f0 = pitch.selected_array["frequency"]
    vf0 = f0[f0 > 0]
    if vf0.size == 0:
        return None
    return float(np.median(vf0))


# ============================================================
# 4) F0 calibration (speaker-normalized)
# ============================================================

@dataclass
class F0Calibration:
    """
    Speaker habitual pitch statistics (per user).
    mean_hz / sd_hz should come from DB calibration.
    """
    mean_hz: float
    sd_hz: float

def compute_f0_z(f0_onset_hz: Optional[float], calib: Optional[F0Calibration]) -> Optional[float]:
    if f0_onset_hz is None or calib is None:
        return None
    if calib.sd_hz <= 1e-6:
        return None
    return float((f0_onset_hz - calib.mean_hz) / calib.sd_hz)


# ============================================================
# 5) Scoring & classification helpers
# ============================================================

def gaussian_distance_score(value: float, center: float, sigma: float) -> float:
    """
    Soft distance-based score in [0, 100].
    sigma controls tolerance (larger = more forgiving).
    """
    if sigma <= 0:
        sigma = 1.0
    d = value - center
    s = 100.0 * math.exp(-(d * d) / (2.0 * sigma * sigma))
    return float(max(0.0, min(100.0, s)))

def linear_distance_score(value: float, center: float, tol: float) -> float:
    d = abs(value - center)
    s = 100.0 * (1.0 - (d / tol))
    return float(max(0.0, min(100.0, s)))

def classify_place(f2_onset_hz: Optional[float]) -> str:
    if f2_onset_hz is None:
        return "unknown"
    best = None
    best_d = 1e18
    for place, c in PLACE_F2_CENTERS_HZ.items():
        d = abs(f2_onset_hz - c)
        if d < best_d:
            best_d = d
            best = place
    return best or "unknown"

def compute_place_score(f2_onset_hz: Optional[float], target_place: str) -> Optional[float]:
    if f2_onset_hz is None or target_place not in PLACE_F2_CENTERS_HZ:
        return None
    center = PLACE_F2_CENTERS_HZ[target_place]
    #return linear_distance_score(f2_onset_hz, center, PLACE_TOLERANCE_HZ)
    return gaussian_distance_score(f2_onset_hz, center, PLACE_SIGMA_HZ)

def compute_place_softscores_and_confidence(f2_onset_hz: Optional[float]) -> Tuple[str, Optional[float], Dict[str, float]]:
    """
    Returns:
      detected_place: argmax soft score
      confidence: (best - second) / best  in [0, 1], or None if unknown
      soft_scores: dict place->score(0..100)
    """
    if f2_onset_hz is None:
        return "unknown", None, {}

    soft_scores: Dict[str, float] = {}
    for place, c in PLACE_F2_CENTERS_HZ.items():
        soft_scores[place] = gaussian_distance_score(f2_onset_hz, c, PLACE_SIGMA_HZ)

    # detected = highest score
    sorted_places = sorted(soft_scores.items(), key=lambda kv: kv[1], reverse=True)
    best_place, best_s = sorted_places[0]
    second_s = sorted_places[1][1] if len(sorted_places) > 1 else 0.0

    # confidence: how clearly best beats second
    conf = (best_s - second_s) / (best_s + PLACE_CONF_MARGIN_EPS)
    conf = float(max(0.0, min(1.0, conf)))

    return best_place, conf, soft_scores

def vot_status(vot_ms: Optional[float]) -> str:
    if vot_ms is None:
        return "unknown"
    if vot_ms < 20:
        return "fortis-like"
    elif vot_ms < 50:
        return "lenis-like"
    elif vot_ms < 100:
        return "aspirated-like"
    else:
        return "over-aspirated"

def classify_phonation_by_vot(vot_ms: Optional[float]) -> str:
    if vot_ms is None:
        return "unknown"
    if vot_ms < 20.0:
        return "fortis"
    if vot_ms < 50.0:
        return "lenis"
    if vot_ms < 100.0:
        return "aspirated"
    return "over-aspirated"

def compute_vot_score(vot_ms: Optional[float], target_phonation: str) -> Optional[float]:
    if vot_ms is None:
        return None
    if target_phonation not in VOT_RANGES_MS:
        return None

    lo, hi, center = VOT_RANGES_MS[target_phonation]

    # Inside the reference range: distance-based scoring toward the center
    if lo <= vot_ms <= hi:
        tol = max((hi - lo) / 2.0, 1.0)
        return linear_distance_score(vot_ms, center, tol)

    # Outside the reference range: decay with a soft margin
    d = (lo - vot_ms) if vot_ms < lo else (vot_ms - hi)
    s = 70.0 * math.exp(-d/25.0)
    return float(max(0.0, min(70.0, s)))

F0Z_SIGMA = 0.8
def compute_f0_score(f0_z: Optional[float], target_phonation: str) -> Optional[float]:
    """
    NOTE:
    - The user's (f0_mean, f0_std) from the DB are already applied in compute_f0_z().
    - Here we only score the speaker-normalized z-score against target (center, tolerance).
    """
    if f0_z is None:
        return None
    if target_phonation not in F0Z_TARGETS:
        return None
    center, tol = F0Z_TARGETS[target_phonation]
    #return linear_distance_score(f0_z, center, tol)
    return gaussian_distance_score(f0_z, center, F0Z_SIGMA)

def distance_to_nearest_boundary(vot_ms: Optional[float]) -> Optional[float]:
    if vot_ms is None:
        return None
    return float(min(abs(vot_ms - b) for b in VOT_BOUNDARIES_MS))

def compute_phonation_score(
    vot_score: Optional[float],
    f0_score: Optional[float],
    vot_ms: Optional[float]
) -> Optional[float]:
    """
    Primary cue: VOT
    Secondary cue: F0 z-score
    Adaptive weighting: when VOT is near a boundary, increase F0 weight.
    """
    if vot_score is None and f0_score is None:
        return None
    if vot_score is None:
        return f0_score
    if f0_score is None:
        return vot_score

    d = distance_to_nearest_boundary(vot_ms)
    if d is None:
        w_f0 = 0.25
    else:
        w_f0 = 0.45 if d <= VOT_BOUNDARY_NEAR_MS else 0.20

    w_vot = 1.0 - w_f0
    return float(w_vot * vot_score + w_f0 * f0_score)

def compute_final_score(place_score: Optional[float], phonation_score: Optional[float]) -> Optional[float]:
    if place_score is None and phonation_score is None:
        return None
    if place_score is None:
        return phonation_score
    if phonation_score is None:
        return place_score
    return float(PLACE_WEIGHT * place_score + PHONATION_WEIGHT * phonation_score)


# ============================================================
# 6) Feedback generation (short, backend-side)
# ============================================================
'''
def generate_stop_feedback(
    syllable: str,
    target_place: str, detected_place: str,
    target_phonation: str, detected_phonation: str,
    place_score: Optional[float],
    phonation_score: Optional[float],
    place_confidence: Optional[float] = None,
) -> str:
    # Style goal: short, actionable coaching. Example:
    # "You practiced 가, but it sounds closer to 다. Move your tongue slightly back."

    place_hint = ""

    if detected_place != "unknown" and detected_place != target_place:
        if target_place == "velar":
            place_hint = (
                "Press the back of your tongue against the roof of your mouth "
                "one more time before releasing."
            )
        elif target_place == "alveolar":
            place_hint = (
                "Touch just behind your upper teeth with the tip of your tongue, "
                "then release."
            )
        elif target_place == "labial":
            place_hint = (
                "Press your lips together clearly, "
                "then release them smoothly."
            )
    else:
        if place_confidence is not None and place_confidence < PLACE_LOW_CONF_THRESH:
            if target_place == "velar":
                place_hint = (
                    "Almost there! "
                    "Try pulling the back of your tongue slightly farther "
                    "back and holding the closure a bit more firmly before release."
                )
            elif target_place == "alveolar":
                place_hint = (
                    "Almost there! "
                    "Try making a clearer contact with the tip of your tongue "
                    "just behind the upper teeth before releasing."
                )
            elif target_place == "labial":
                place_hint = (
                    "Almost there! "
                    "Try pressing your lips together a bit more firmly and "
                    "keeping the closure slightly longer before releasing."
                )

        else:
            place_hint = (
                "Good job. Keep using the same mouth position."
            )

    phon_hint = ""
    if detected_phonation != "unknown" and detected_phonation != target_phonation:
        if target_phonation == "fortis":
            phon_hint = (
                "Make it short and tight. "
                "Do not let air escape. "
                "Start the voice immediately."
            )
        elif target_phonation == "lenis":
            phon_hint = (
                "Start more gently. "
                "Do not push out air too strongly."
            )
        elif target_phonation == "aspirated":
            phon_hint = (
                "Release with a clear puff of air, "
                "like a soft breath right after opening."
            )

    parts = []
    if place_score is not None:
        parts.append(f"place {place_score:.0f}")
    if phonation_score is not None:
        parts.append(f"phonation {phonation_score:.0f}")

    score_str = ", ".join(parts) if parts else "score N/A"
    base = f"({score_str}) "

    if place_hint and phon_hint:
        return place_hint + " " + phon_hint
    if place_hint:
        return place_hint
    if phon_hint:
        return phon_hint
    return "Good overall. Try to repeat the same feeling again."
'''
def generate_stop_feedback(
    syllable: str,
    target_place: str, detected_place: str,
    target_phonation: str, detected_phonation: str,
    place_score: Optional[float],
    phonation_score: Optional[float],
    place_confidence: Optional[float] = None,
) -> str:
    # Goal: short, intuitive, action-first coaching.
    # In practice mode, the target is known. So:
    # - If phonation is off, address that first (it drives perceived correctness).
    # - Praise should be specific ("lip position is good"), not global ("good job").

    # -------------------------
    # Place hint (mouth/tongue position)
    # -------------------------
    # --- Guard: if we couldn't measure anything, don't praise ---
    # If both main subscores are missing, analysis likely failed (no clear burst/voicing).
    if place_score is None and phonation_score is None:
        return (
            "I couldn't measure this recording clearly. "
            "Please record again."
        )

    place_hint = ""

    if detected_place != "unknown" and detected_place != target_place:
        # Direct correction (one clear action)
        if target_place == "velar":
            place_hint = "Press the back of your tongue against the roof of your mouth, then release."
        elif target_place == "alveolar":
            place_hint = "Touch just behind your upper teeth with your tongue tip, then release."
        elif target_place == "labial":
            place_hint = "Close your lips firmly, then release smoothly."
    else:
        # Place is basically right → refine only if cue is weak
        if place_confidence is not None and place_confidence < PLACE_LOW_CONF_THRESH:
            if target_place == "velar":
                place_hint = "Almost there. Press the back of your tongue a bit more firmly, then release."
            elif target_place == "alveolar":
                place_hint = "Almost there. Let your tongue tip touch a bit more firmly, then release."
            elif target_place == "labial":
                place_hint = "Almost there. Close your lips a little more firmly before opening."
        else:
            # Keep praise specific to place
            if target_place == "labial":
                place_hint = "Your lip position is good."
            elif target_place == "alveolar":
                place_hint = "Your tongue position is good."
            elif target_place == "velar":
                place_hint = "Your tongue-back position is good."
            else:
                place_hint = "Your mouth position is good."

    # -------------------------
    # Phonation hint (timing / airflow)
    # -------------------------
    phon_hint = ""
    phon_mismatch = (detected_phonation != "unknown" and detected_phonation != target_phonation)

    if phon_mismatch:
        # Give "compare-to" feedback; users understand contrast better.
        # Also keep each hint short and physical.
        if target_phonation == "fortis":
            # ㅃ/ㄸ/ㄲ : short, tight, no breath
            phon_hint = (
                "It sounds too soft (like the plain sound). "
                "Say it very short and hard with NO puff of air. "
                "Start the voice right away."
            )
        elif target_phonation == "lenis":
            # ㅂ/ㄷ/ㄱ : gentle, not breathy, not too strong
            phon_hint = (
                "It sounds too tense or too breathy. "
                "Say it gently—do NOT burst air."
            )
        elif target_phonation == "aspirated":
            # ㅍ/ㅌ/ㅋ : clear puff + delayed voicing
            phon_hint = (
                "It needs more air. "
                "Release with a clear puff of breath, then start the voice."
            )

    # -------------------------
    # Score string (optional)
    # -------------------------
    parts = []
    if place_score is not None:
        parts.append(f"place {place_score:.0f}")
    if phonation_score is not None:
        parts.append(f"phonation {phonation_score:.0f}")
    score_str = ", ".join(parts) if parts else "score N/A"
    base = f"({score_str}) "

    # -------------------------
    # Combine: prioritize phonation if it's the main error
    # -------------------------
    # In practice mode, if phonation is wrong, lead with phonation coaching.
    if phon_hint and place_hint:
        return phon_hint + " " + place_hint
    if phon_hint:
        return phon_hint
    if place_hint:
        return place_hint
    return "Good overall. Try to repeat the same feeling again."

# ============================================================
# 7) Core: evaluate_stop
# ============================================================

def evaluate_stop(
    f2_onset_hz: Optional[float],
    vot_ms: Optional[float],
    f0_z: Optional[float],
    target_place: str,
    target_phonation: str
) -> Dict[str, Any]:

    #detected_place = classify_place(f2_onset_hz)
    #place_score = compute_place_score(f2_onset_hz, target_place)

    detected_place, place_conf, place_softscores = compute_place_softscores_and_confidence(f2_onset_hz)
    place_score = compute_place_score(f2_onset_hz, target_place)

    detected_phonation = classify_phonation_by_vot(vot_ms)
    vot_sc = compute_vot_score(vot_ms, target_phonation)

    f0_sc = compute_f0_score(f0_z, target_phonation)
    phonation_sc = compute_phonation_score(vot_sc, f0_sc, vot_ms)

    final_sc = compute_final_score(place_score, phonation_sc)
    vot_diag = vot_status(vot_ms)

    return {
        "detected_place": detected_place,
        "detected_phonation": detected_phonation,
        "place_score": place_score,
        "place_confidence": place_conf,                 
        "place_softscores": place_softscores,    
        "vot_score": vot_sc,
        "f0_score": f0_sc,
        "phonation_score": phonation_sc,
        "final_score": final_sc,
        "diagnostics": {
            "vot_status": vot_diag,
            "near_boundary_ms": distance_to_nearest_boundary(vot_ms),
        },
        "plots": {
            "f2_centers_hz": PLACE_F2_CENTERS_HZ,
            "f2_tolerance_hz": PLACE_TOLERANCE_HZ,
            "f2_user_hz": f2_onset_hz,
            "vot_f0_point": {"x_vot_ms": vot_ms, "y_f0_z": f0_z},
            "vot_reference_ranges_ms": {
                k: {"low": lo, "high": hi, "center": c}
                for k, (lo, hi, c) in VOT_RANGES_MS.items()
            },
            "f0z_reference_targets": {
                k: {"center": F0Z_TARGETS[k][0], "tol": F0Z_TARGETS[k][1]}
                for k in F0Z_TARGETS
            },
        }
    }


# ============================================================
# 8) End-to-end stop analysis
# ============================================================

def analyze_stop(wav_path: str, syllable: str, f0_calibration: Optional[F0Calibration] = None) -> Dict[str, Any]:
    if syllable not in STOP_SET:
        return {"error": f"'{syllable}' is not a supported stop syllable in this module."}

    target_place = STOP_META[syllable]["place"]
    target_phonation = STOP_META[syllable]["phonation"]

    snd, y, sr = load_sound(wav_path)

    aspirated_mode = (target_phonation == "aspirated")
    vot_ms, burst_t, voiced_t = estimate_vot_ms(snd, aspirated_mode=aspirated_mode)

    f2_onset = estimate_f2_onset_hz(snd, voiced_t, offset_ms=20.0)
    f0_onset_hz = estimate_vowel_onset_f0_hz(snd, voiced_t, onset_win_ms=30.0)

    # Use per-user calibration (mean/std) from DB to compute speaker-normalized z-score
    f0_z = compute_f0_z(f0_onset_hz, f0_calibration)

    eval_result = evaluate_stop(
        f2_onset_hz=f2_onset,
        vot_ms=vot_ms,
        f0_z=f0_z,
        target_place=target_place,
        target_phonation=target_phonation
    )

    feedback_text = generate_stop_feedback(
        syllable=syllable,
        target_place=target_place,
        detected_place=eval_result["detected_place"],
        target_phonation=target_phonation,
        detected_phonation=eval_result["detected_phonation"],
        place_score=eval_result["place_score"],
        phonation_score=eval_result["phonation_score"],
        place_confidence=eval_result.get("place_confidence"),
    )

    return {
        "syllable": syllable,
        "type": "stop",
        "targets": {"place": target_place, "phonation": target_phonation},
        "features": {
            "vot_ms": vot_ms,
            "f2_onset_hz": f2_onset,
            "f0_onset_hz": f0_onset_hz,
            "f0_z": f0_z,
        },
        "evaluation": eval_result,
        "feedback": {"text": feedback_text},
    }

# kospa_core.py
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import subprocess
import tempfile
import uuid
import numpy as np
import parselmouth
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Ellipse

# Korean font (helps render labels cleanly when available)
try:
    plt.rc("font", family="NanumGothic")
except Exception:
    pass

#########################################
# 1. Reference Formant Tables           #
#########################################
# Adult Korean vowels - All 21 vowels including monophthongs and diphthongs
# f1_sd and f2_sd indicate how far we can deviate before flagging an issue.
# Data based on Korean phonetics research and acoustic measurements
STANDARD_MALE_FORMANTS = {
    # Basic 6 monophthongs (단모음)
    'a (아)':  {'f1': 651, 'f2': 1156, 'f3': 2500, 'f1_sd': 136, 'f2_sd':  77},
    'eo (어)': {'f1': 445, 'f2':  845, 'f3': 2500, 'f1_sd': 103, 'f2_sd': 149},
    'o (오)':  {'f1': 320, 'f2':  587, 'f3': 2300, 'f1_sd':  56, 'f2_sd': 132},
    'u (우)':  {'f1': 324, 'f2':  595, 'f3': 2400, 'f1_sd':  43, 'f2_sd': 140},
    'eu (으)': {'f1': 317, 'f2': 1218, 'f3': 2600, 'f1_sd':  27, 'f2_sd': 155},
    'i (이)':  {'f1': 236, 'f2': 2183, 'f3': 3010, 'f1_sd':  30, 'f2_sd': 136},

    # Y-vowels (ㅣ-모음계) - F2 increased due to palatal glide
    'ya (야)':  {'f1': 600, 'f2': 1650, 'f3': 2750, 'f1_sd': 120, 'f2_sd': 140},
    'yeo (여)': {'f1': 410, 'f2': 1550, 'f3': 2650, 'f1_sd':  95, 'f2_sd': 135},
    'yo (요)':  {'f1': 300, 'f2': 1350, 'f3': 2500, 'f1_sd':  60, 'f2_sd': 125},
    'yu (유)':  {'f1': 305, 'f2': 1450, 'f3': 2600, 'f1_sd':  50, 'f2_sd': 130},

    # Front vowels (전설 모음)
    'ae (애)':  {'f1': 700, 'f2': 1800, 'f3': 2650, 'f1_sd': 130, 'f2_sd': 160},
    'yae (얘)': {'f1': 650, 'f2': 2000, 'f3': 2800, 'f1_sd': 120, 'f2_sd': 170},
    'e (에)':   {'f1': 550, 'f2': 1900, 'f3': 2700, 'f1_sd': 110, 'f2_sd': 150},
    'ye (예)':  {'f1': 500, 'f2': 2100, 'f3': 2800, 'f1_sd': 100, 'f2_sd': 160},

    # Complex vowels (이중 모음)
    'wa (와)':  {'f1': 485, 'f2':  870, 'f3': 2400, 'f1_sd': 100, 'f2_sd': 140},
    'wae (왜)': {'f1': 575, 'f2': 1400, 'f3': 2550, 'f1_sd': 110, 'f2_sd': 150},
    'oe (외)':  {'f1': 450, 'f2': 1500, 'f3': 2600, 'f1_sd':  95, 'f2_sd': 145},
    'wo (워)':  {'f1': 385, 'f2':  880, 'f3': 2550, 'f1_sd':  85, 'f2_sd': 135},
    'we (웨)':  {'f1': 470, 'f2': 1450, 'f3': 2650, 'f1_sd':  90, 'f2_sd': 140},
    'wi (위)':  {'f1': 280, 'f2': 1800, 'f3': 2700, 'f1_sd':  55, 'f2_sd': 150},
    'ui (의)':  {'f1': 305, 'f2': 1700, 'f3': 2750, 'f1_sd':  60, 'f2_sd': 155},
}

STANDARD_FEMALE_FORMANTS = {
    # Basic 6 monophthongs (단모음)
    'a (아)':  {'f1': 945, 'f2': 1582, 'f3': 3200, 'f1_sd':  83, 'f2_sd': 141},
    'eo (어)': {'f1': 576, 'f2':  961, 'f3': 2700, 'f1_sd':  78, 'f2_sd':  87},
    'o (오)':  {'f1': 371, 'f2':  700, 'f3': 2600, 'f1_sd':  25, 'f2_sd':  72},
    'u (우)':  {'f1': 346, 'f2':  810, 'f3': 2700, 'f1_sd':  28, 'f2_sd': 106},
    'eu (으)': {'f1': 390, 'f2': 1752, 'f3': 2900, 'f1_sd':  34, 'f2_sd': 191},
    'i (이)':  {'f1': 273, 'f2': 2864, 'f3': 3400, 'f1_sd':  22, 'f2_sd': 109},

    # Y-vowels (ㅣ-모음계) - F2 increased due to palatal glide
    'ya (야)':  {'f1': 870, 'f2': 2100, 'f3': 3300, 'f1_sd':  90, 'f2_sd': 160},
    'yeo (여)': {'f1': 540, 'f2': 1800, 'f3': 3000, 'f1_sd':  85, 'f2_sd': 145},
    'yo (요)':  {'f1': 350, 'f2': 1600, 'f3': 2800, 'f1_sd':  40, 'f2_sd': 120},
    'yu (유)':  {'f1': 330, 'f2': 1700, 'f3': 2900, 'f1_sd':  45, 'f2_sd': 130},

    # Front vowels (전설 모음) - measured 애 + estimates
    'ae (애)':  {'f1': 621, 'f2': 1914, 'f3': 2732, 'f1_sd':  95, 'f2_sd': 170},  # Measured from sample
    'yae (얘)': {'f1': 920, 'f2': 2200, 'f3': 3350, 'f1_sd':  90, 'f2_sd': 180},
    'e (에)':   {'f1': 700, 'f2': 2100, 'f3': 3100, 'f1_sd':  85, 'f2_sd': 160},
    'ye (예)':  {'f1': 650, 'f2': 2300, 'f3': 3200, 'f1_sd':  80, 'f2_sd': 170},

    # Complex vowels (이중 모음)
    'wa (와)':  {'f1': 660, 'f2': 1100, 'f3': 2750, 'f1_sd':  80, 'f2_sd': 130},
    'wae (왜)': {'f1': 750, 'f2': 1650, 'f3': 2900, 'f1_sd':  90, 'f2_sd': 150},
    'oe (외)':  {'f1': 570, 'f2': 1700, 'f3': 2850, 'f1_sd':  75, 'f2_sd': 145},
    'wo (워)':  {'f1': 500, 'f2': 1050, 'f3': 2800, 'f1_sd':  70, 'f2_sd': 125},
    'we (웨)':  {'f1': 600, 'f2': 1650, 'f3': 2950, 'f1_sd':  75, 'f2_sd': 140},
    'wi (위)':  {'f1': 310, 'f2': 2000, 'f3': 3100, 'f1_sd':  40, 'f2_sd': 160},
    'ui (의)':  {'f1': 340, 'f2': 2100, 'f3': 3050, 'f1_sd':  50, 'f2_sd': 165},
}

# Import gender threshold from config
from .config import F0_GENDER_THRESHOLD


#####################################
# 2. ffmpeg conversion (m4a/mp3 -> wav) #
#####################################
def convert_to_wav(input_file: str, output_file: str) -> bool:
    try:
        subprocess.run(
            [
                "ffmpeg", "-i", input_file,
                "-y",
                "-ac", "1",
                "-ar", "44100",
                output_file
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        return True
    except Exception as e:
        print(f"[convert_to_wav] Error: {e}")
        return False


###############################################
# 3. Extract a stable window (~0.12s with strong RMS)
###############################################
def _stable_window(sound: parselmouth.Sound, min_len=0.12):
    """
    Returns the highest-energy, most stable segment (≈0.12s).
    Also estimates a noise ratio to provide recording quality hints.
    """
    duration = sound.get_total_duration()
    snd_values = sound.values[0]  # mono
    sr = sound.sampling_frequency

    win_size = int(min_len * sr)
    if win_size < 1 or len(snd_values) < win_size:
        # If the audio is too short, use the entire clip
        return sound, 0.01, 0.005, 999.0, duration

    rms_list = []
    hop = max(win_size // 4, 1)
    for start_idx in range(0, len(snd_values) - win_size + 1, hop):
        seg = snd_values[start_idx:start_idx+win_size]
        rms = float(np.sqrt(np.mean(seg**2)))
        rms_list.append((rms, start_idx))

    if not rms_list:
        return sound, 0.01, 0.005, 999.0, duration

    # Pick the window with the highest energy
    rms_list.sort(key=lambda x: x[0], reverse=True)
    best_rms, best_idx = rms_list[0]

    noise_floor = float(np.median([r for r, _ in rms_list]))
    snr_ratio = (best_rms + 1e-9) / (noise_floor + 1e-9)

    start_t = best_idx / sr
    end_t = min((best_idx + win_size) / sr, duration)

    sub = sound.extract_part(from_time=start_t, to_time=end_t)
    seg_len = end_t - start_t
    return sub, best_rms, noise_floor, snr_ratio, seg_len


###############################################
# 4. Formant & pitch extraction
###############################################
def analyze_vowel_and_pitch(wav_file_path: str):
    """
    return:
        f1_mean, f2_mean, f3_mean, f0_mean, quality_hint
    """
    try:
        snd_full = parselmouth.Sound(wav_file_path)
        full_dur = snd_full.get_total_duration()

        if full_dur < 0.2:
            return None, None, None, None, "Audio too short (<0.2s). Hold the vowel a bit longer."

        stable, peak_rms, noise_rms, snr_ratio, seg_len = _stable_window(
            snd_full, min_len=0.12
        )

        # Recording quality hints
        quality_msgs = []
        if seg_len < 0.08:
            quality_msgs.append("Too short; hold ~0.3s.")
        if peak_rms < 0.01:
            quality_msgs.append("Volume too low; speak louder.")
        if snr_ratio < 1.5:
            quality_msgs.append("Background noise high; quieter place please.")

        # pitch → f0
        pitch = stable.to_pitch(pitch_floor=75.0, pitch_ceiling=500.0)
        pitch_values = pitch.selected_array["frequency"]
        voiced = [f for f in pitch_values if f > 0]
        f0_mean = float(np.mean(voiced)) if voiced else np.nan

        # formants via Burg
        formant = stable.to_formant_burg(maximum_formant=5500.0)
        f1_vals, f2_vals, f3_vals = [], [], []
        for frame_idx in range(1, formant.n_frames + 1):
            t = formant.get_time_from_frame_number(frame_idx)
            f1_vals.append(formant.get_value_at_time(1, t))
            f2_vals.append(formant.get_value_at_time(2, t))
            f3_vals.append(formant.get_value_at_time(3, t))

        f1_mean = float(np.nanmedian(f1_vals))
        f2_mean = float(np.nanmedian(f2_vals))
        f3_mean = float(np.nanmedian(f3_vals))

        if any(np.isnan(v) for v in [f0_mean, f1_mean, f2_mean]):
            return None, None, None, None, "Could not get stable formants. Try a clearer vowel."

        quality_hint = " ".join(quality_msgs) if quality_msgs else None
        return f1_mean, f2_mean, f3_mean, f0_mean, quality_hint

    except Exception as e:
        return None, None, None, None, f"Analysis error: {e}"


###############################################
# 5. Scoring
###############################################
def compute_score(f1, f2, f3, vowel_key, ref_table):
    std = ref_table[vowel_key]
    f1_z = abs(f1 - std["f1"]) / std["f1_sd"]
    f2_z = abs(f2 - std["f2"]) / std["f2_sd"]
    z_avg = (f1_z + f2_z) / 2.0

    # Give F3 a stronger weight (default sigma 250 Hz when not provided)
    if "f3" in std and f3:
        f3_sd = std.get("f3_sd", 250.0)
        f3_z = abs(f3 - std["f3"]) / f3_sd
        z_avg = (z_avg * 0.75) + (f3_z * 0.25)

    if z_avg <= 1.5:
        return 100

    penalty = (z_avg - 1.5) * 60.0
    raw_score = 100.0 - penalty
    return int(max(0, min(100, raw_score)))


###############################################
# 6. Feedback generation
###############################################
def get_feedback(vowel_key, f1, f2, ref_table, quality_hint=None):
    std = ref_table[vowel_key]
    msgs = []

    f1_tol = std["f1_sd"] * 0.5
    f2_tol = std["f2_sd"] * 0.5

    # High F1 → mouth too open / tongue too low
    if f1 > std["f1"] + f1_tol:
        msgs.append("Mouth too open / tongue too low → raise tongue slightly.")
    elif f1 < std["f1"] - f1_tol:
        msgs.append("Mouth too closed / tongue too high → lower tongue slightly.")

    # High F2 → tongue too far forward
    if f2 > std["f2"] + f2_tol:
        msgs.append("Tongue too front → pull it slightly back.")
    elif f2 < std["f2"] - f2_tol:
        msgs.append("Tongue too back → move it slightly forward.")

    if not msgs:
        msgs = ["Excellent! 👏 Very close to the target placement."]

    if quality_hint:
        msgs.append(f"(Recording note: {quality_hint})")

    return " ".join(msgs)


###############################################
# 7. High-level: analyze a single sample
###############################################
def analyze_single_audio(
    audio_path: str,
    vowel_key: str,
    *,
    return_reason: bool = False,
    custom_ref_table: dict = None
):
    """
    Analyze vowel formants from audio file.

    1) Convert with ffmpeg
    2) Extract F0/F1/F2/F3 from the stable window
    3) Guess gender and pull the matching reference table (or use custom_ref_table)
    4) Return scores and feedback as a dictionary

    Args:
        audio_path: Path to audio file
        vowel_key: Vowel identifier (e.g., 'a (아)')
        return_reason: If True, return (result, error) tuple
        custom_ref_table: Optional personalized reference table (overrides standard)

    Returns:
        Analysis result dict or (None, error_msg) if return_reason=True
    """
    if not os.path.exists(audio_path):
        msg = "Audio file not found."
        if return_reason:
            return None, msg
        return None

    try:
        original_size = os.path.getsize(audio_path)
    except OSError:
        original_size = -1

    # Create unique temporary file to avoid race conditions
    tmp_wav = os.path.join(tempfile.gettempdir(), f"kospa_temp_{uuid.uuid4().hex}.wav")

    if not convert_to_wav(audio_path, tmp_wav):
        msg = f"Failed to convert input audio (size={original_size})."
        print(f"[analyze_single_audio] {msg}")
        if return_reason:
            return None, msg
        return None

    try:
        wav_size = os.path.getsize(tmp_wav)
    except OSError:
        wav_size = -1
    print(f"[analyze_single_audio] Converted sizes input={original_size}, wav={wav_size}")

    f1, f2, f3, f0, qhint = analyze_vowel_and_pitch(tmp_wav)

    # Clean up temporary file
    try:
        os.remove(tmp_wav)
    except OSError:
        pass

    if f1 is None or f2 is None or f0 is None:
        msg = qhint or "Could not extract stable formants."
        if return_reason:
            return None, msg
        print(f"[analyze_single_audio] {msg}")
        return None

    gender_guess = "Male" if f0 < F0_GENDER_THRESHOLD else "Female"

    # Use custom reference table if provided, otherwise use standard
    if custom_ref_table:
        ref_table = custom_ref_table
    else:
        ref_table = STANDARD_MALE_FORMANTS if gender_guess == "Male" else STANDARD_FEMALE_FORMANTS

    if vowel_key not in ref_table:
        msg = "Requested vowel key is not supported by reference table."
        if return_reason:
            return None, msg
        print(f"[analyze_single_audio] {msg}")
        return None

    score = compute_score(f1, f2, f3, vowel_key, ref_table)
    feedback = get_feedback(vowel_key, f1, f2, ref_table, quality_hint=qhint)

    result = {
        "vowel_key": vowel_key,
        "audio_path": audio_path,
        "gender": gender_guess,
        "f0": f0,
        "f1": f1,
        "f2": f2,
        "f3": f3,
        "score": score,
        "feedback": feedback,
        "quality_hint": qhint,
    }
    if return_reason:
        return result, None
    return result


###############################################
# 8. (Optional) visualize a single vowel
###############################################
def plot_single_vowel_space(f1, f2, vowel_key, gender_guess, out_path):
    ref_table = STANDARD_MALE_FORMANTS if gender_guess == "Male" else STANDARD_FEMALE_FORMANTS
    tgt = ref_table[vowel_key]

    fig, ax = plt.subplots(figsize=(6, 5))

    # Reference vowels
    for k, ref in ref_table.items():
        ax.scatter(ref["f2"], ref["f1"], c="lightgray", marker="x", s=60, zorder=2)
        ax.text(ref["f2"]+10, ref["f1"]+10, k, color="gray", fontsize=8)

    # Target vowel
    ax.scatter(tgt["f2"], tgt["f1"], c="green", s=200, alpha=0.7, label=f"Target {vowel_key}")
    ellipse = Ellipse(
        (tgt["f2"], tgt["f1"]),
        width=tgt["f2_sd"] * 2.0,
        height=tgt["f1_sd"] * 2.0,
        angle=0,
        color="green",
        alpha=0.18,
        label="Target 1σ"
    )
    ax.add_patch(ellipse)

    ellipse_2 = Ellipse(
        (tgt["f2"], tgt["f1"]),
        width=tgt["f2_sd"] * 4.0,
        height=tgt["f1_sd"] * 4.0,
        angle=0,
        color="green",
        alpha=0.07,
        linestyle="--",
        linewidth=1.0,
        label="Target 2σ"
    )
    ax.add_patch(ellipse_2)

    # Measured point
    ax.scatter(f2, f1, c="red", s=200, alpha=0.8, label="You")

    ax.set_title(f"{vowel_key} / gender={gender_guess}")
    ax.set_xlabel("F2 (Hz) ← front ... back →")
    ax.set_ylabel("F1 (Hz) ← high ... low →")
    ax.invert_yaxis()
    ax.invert_xaxis()
    ax.grid(True, linestyle="--", alpha=0.5)
    ax.legend(fontsize=8, loc="best")

    plt.tight_layout()
    plt.savefig(out_path)
    plt.close(fig)


###############################################
# 9. Time-series formant extraction for diphthongs
###############################################
def extract_formant_trajectory(
    wav_file_path: str,
    window_length: float = 0.025,  # 25ms window
    hop_length: float = 0.010,     # 10ms hop
    min_frames: int = 5
):
    """
    Extract formant trajectory over time for diphthong analysis.

    Args:
        wav_file_path: Path to WAV file
        window_length: Analysis window length in seconds (default 25ms)
        hop_length: Hop between frames in seconds (default 10ms)
        min_frames: Minimum number of frames required

    Returns:
        dict with:
            'trajectory': List of {'time': float, 'f1': float, 'f2': float, 'f3': float}
            'duration': Total duration in seconds
            'success': Boolean
            'error': Error message if failed

    Example:
        >>> result = extract_formant_trajectory('audio.wav')
        >>> for frame in result['trajectory']:
        ...     print(f"t={frame['time']:.3f}s: F1={frame['f1']:.0f}, F2={frame['f2']:.0f}")
    """
    # Convert to WAV if needed
    if not wav_file_path.lower().endswith('.wav'):
        temp_wav = tempfile.NamedTemporaryFile(delete=False, suffix='.wav').name
        if not convert_to_wav(wav_file_path, temp_wav):
            return {
                'success': False,
                'error': 'Failed to convert audio to WAV',
                'trajectory': [],
                'duration': 0
            }
        wav_file_path = temp_wav

    try:
        sound = parselmouth.Sound(wav_file_path)
        duration = sound.duration

        if duration < window_length:
            return {
                'success': False,
                'error': f'Audio too short ({duration:.3f}s < {window_length}s)',
                'trajectory': [],
                'duration': duration
            }

        # Generate time points
        num_frames = int((duration - window_length) / hop_length) + 1

        if num_frames < min_frames:
            return {
                'success': False,
                'error': f'Too few frames ({num_frames} < {min_frames})',
                'trajectory': [],
                'duration': duration
            }

        trajectory = []

        for i in range(num_frames):
            t_center = window_length / 2 + i * hop_length

            # Extract window
            t_start = max(0, t_center - window_length / 2)
            t_end = min(duration, t_center + window_length / 2)

            try:
                # Extract formants at this time point
                formants = sound.to_formant_burg(
                    time_step=hop_length,
                    max_number_of_formants=5,
                    maximum_formant=5500
                )

                f1 = formants.get_value_at_time(1, t_center)
                f2 = formants.get_value_at_time(2, t_center)
                f3 = formants.get_value_at_time(3, t_center)

                # Filter out NaN/undefined values
                if f1 and not np.isnan(f1) and f2 and not np.isnan(f2):
                    trajectory.append({
                        'time': t_center,
                        'f1': float(f1),
                        'f2': float(f2),
                        'f3': float(f3) if f3 and not np.isnan(f3) else 2500.0
                    })
            except Exception as e:
                # Skip problematic frames
                continue

        if len(trajectory) < min_frames:
            return {
                'success': False,
                'error': f'Too few valid frames ({len(trajectory)} < {min_frames})',
                'trajectory': [],
                'duration': duration
            }

        return {
            'success': True,
            'trajectory': trajectory,
            'duration': duration,
            'num_frames': len(trajectory),
            'error': None
        }

    except Exception as e:
        return {
            'success': False,
            'error': f'Trajectory extraction failed: {str(e)}',
            'trajectory': [],
            'duration': 0
        }


def score_diphthong_trajectory(
    trajectory: list,
    vowel_key: str,
    ref_table: dict
):
    """
    Score a diphthong trajectory based on start/end positions and direction.

    Args:
        trajectory: List of {'time', 'f1', 'f2', 'f3'} from extract_formant_trajectory()
        vowel_key: Diphthong key (e.g., 'wa (와)')
        ref_table: Reference formant table

    Returns:
        dict with:
            'score': Overall score (0-100)
            'start_score': Starting position score
            'end_score': Ending position score
            'direction_score': Movement direction score
            'feedback': List of feedback strings
            'details': Additional metrics

    Example:
        >>> result = extract_formant_trajectory('wa.wav')
        >>> score_result = score_diphthong_trajectory(result['trajectory'], 'wa (와)', ref_table)
        >>> print(f"Score: {score_result['score']}")
    """
    from config import DIPHTHONG_TRAJECTORIES, VOWEL_ARTICULATORY_MAP

    if vowel_key not in DIPHTHONG_TRAJECTORIES:
        # Fallback: treat as monophthong (use middle frames)
        mid_idx = len(trajectory) // 2
        mid_frames = trajectory[max(0, mid_idx-2):min(len(trajectory), mid_idx+3)]

        f1_avg = np.mean([f['f1'] for f in mid_frames])
        f2_avg = np.mean([f['f2'] for f in mid_frames])
        f3_avg = np.mean([f['f3'] for f in mid_frames])

        mono_score = compute_score(f1_avg, f2_avg, f3_avg, vowel_key, ref_table)

        return {
            'score': mono_score,
            'start_score': None,
            'end_score': None,
            'direction_score': None,
            'feedback': [f"Treated as monophthong (score: {mono_score})"],
            'details': {
                'f1_avg': f1_avg,
                'f2_avg': f2_avg,
                'is_diphthong': False
            }
        }

    # Get diphthong trajectory definition
    diphthong_def = DIPHTHONG_TRAJECTORIES[vowel_key]
    start_vowel_key = diphthong_def['start']
    end_vowel_key = diphthong_def['end']

    if start_vowel_key not in ref_table or end_vowel_key not in ref_table:
        return {
            'score': 50,
            'error': f'Missing reference for {start_vowel_key} or {end_vowel_key}',
            'feedback': ['Reference vowels not found'],
            'details': {}
        }

    # Extract start and end portions (first/last 30%)
    n = len(trajectory)
    start_portion = trajectory[:max(1, n//3)]
    end_portion = trajectory[max(1, 2*n//3):]

    # Average formants for start and end
    start_f1 = np.mean([f['f1'] for f in start_portion])
    start_f2 = np.mean([f['f2'] for f in start_portion])
    end_f1 = np.mean([f['f1'] for f in end_portion])
    end_f2 = np.mean([f['f2'] for f in end_portion])

    # Score start position
    start_ref = ref_table[start_vowel_key]
    start_z1 = abs(start_f1 - start_ref['f1']) / start_ref['f1_sd']
    start_z2 = abs(start_f2 - start_ref['f2']) / start_ref['f2_sd']
    start_score = max(0, 100 - 10 * (start_z1 + start_z2))

    # Score end position
    end_ref = ref_table[end_vowel_key]
    end_z1 = abs(end_f1 - end_ref['f1']) / end_ref['f1_sd']
    end_z2 = abs(end_f2 - end_ref['f2']) / end_ref['f2_sd']
    end_score = max(0, 100 - 10 * (end_z1 + end_z2))

    # Score direction (cosine similarity)
    user_vector = np.array([end_f2 - start_f2, end_f1 - start_f1])
    target_vector = np.array([
        end_ref['f2'] - start_ref['f2'],
        end_ref['f1'] - start_ref['f1']
    ])

    user_norm = np.linalg.norm(user_vector)
    target_norm = np.linalg.norm(target_vector)

    if user_norm > 0 and target_norm > 0:
        cos_sim = np.dot(user_vector, target_vector) / (user_norm * target_norm)
        cos_sim = max(-1, min(1, cos_sim))  # Clamp
        direction_score = (cos_sim + 1) * 50  # Map [-1,1] to [0,100]
    else:
        direction_score = 0

    # Overall score (weighted average)
    overall_score = (start_score * 0.35 + end_score * 0.35 + direction_score * 0.30)

    # Generate feedback
    feedback = []
    if start_score < 70:
        feedback.append(f"Starting position deviates from '{start_vowel_key}'")
    if end_score < 70:
        feedback.append(f"Ending position deviates from '{end_vowel_key}'")
    if direction_score < 60:
        feedback.append(f"Movement direction differs from expected '{diphthong_def['direction']}'")

    if overall_score >= 85:
        feedback.insert(0, "Excellent diphthong trajectory!")
    elif overall_score >= 70:
        feedback.insert(0, "Good trajectory, minor adjustments needed")

    return {
        'score': round(overall_score, 1),
        'start_score': round(start_score, 1),
        'end_score': round(end_score, 1),
        'direction_score': round(direction_score, 1),
        'feedback': feedback,
        'details': {
            'start': {'f1': start_f1, 'f2': start_f2},
            'end': {'f1': end_f1, 'f2': end_f2},
            'start_ref': start_vowel_key,
            'end_ref': end_vowel_key,
            'is_diphthong': True,
            'num_frames': n
        }
    }

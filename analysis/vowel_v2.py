# kospa_core.py
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os, subprocess
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
# Adult Korean monophthongs (a, eo, o, u, eu, i)
# f1_sd and f2_sd indicate how far we can deviate before flagging an issue.
STANDARD_MALE_FORMANTS = {
    'a (아)':  {'f1': 651, 'f2': 1156, 'f3': 2500, 'f1_sd': 136, 'f2_sd':  77},
    'eo (어)': {'f1': 445, 'f2':  845, 'f3': 2500, 'f1_sd': 103, 'f2_sd': 149},
    'o (오)':  {'f1': 320, 'f2':  587, 'f3': 2300, 'f1_sd':  56, 'f2_sd': 132},
    'u (우)':  {'f1': 324, 'f2':  595, 'f3': 2400, 'f1_sd':  43, 'f2_sd': 140},
    'eu (으)': {'f1': 317, 'f2': 1218, 'f3': 2600, 'f1_sd':  27, 'f2_sd': 155},
    'i (이)':  {'f1': 236, 'f2': 2183, 'f3': 3010, 'f1_sd':  30, 'f2_sd': 136},
}

STANDARD_FEMALE_FORMANTS = {
    'a (아)':  {'f1': 945, 'f2': 1582, 'f3': 3200, 'f1_sd':  83, 'f2_sd': 141},
    'eo (어)': {'f1': 576, 'f2':  961, 'f3': 2700, 'f1_sd':  78, 'f2_sd':  87},
    'o (오)':  {'f1': 371, 'f2':  700, 'f3': 2600, 'f1_sd':  25, 'f2_sd':  72},
    'u (우)':  {'f1': 346, 'f2':  810, 'f3': 2700, 'f1_sd':  28, 'f2_sd': 106},
    'eu (으)': {'f1': 390, 'f2': 1752, 'f3': 2900, 'f1_sd':  34, 'f2_sd': 191},
    'i (이)':  {'f1': 273, 'f2': 2864, 'f3': 3400, 'f1_sd':  22, 'f2_sd': 109},
}

# Gender guess threshold (Hz). Lower pitch usually means male.
F0_GENDER_THRESHOLD = 165.0


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

    # Give F3 an optional ~10% weight
    if "f3" in std and f3:
        f3_z = abs(f3 - std["f3"]) / 400.0
        z_avg = (z_avg * 0.9) + (f3_z * 0.1)

    raw_score = 100 - (z_avg * 33.0)
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
def analyze_single_audio(audio_path: str, vowel_key: str):
    """
    1) Convert with ffmpeg
    2) Extract F0/F1/F2/F3 from the stable window
    3) Guess gender and pull the matching reference table
    4) Return scores and feedback as a dictionary
    """
    if not os.path.exists(audio_path):
        return None

    tmp_wav = "kospa_temp.wav"
    if not convert_to_wav(audio_path, tmp_wav):
        return None

    f1, f2, f3, f0, qhint = analyze_vowel_and_pitch(tmp_wav)

    try:
        os.remove(tmp_wav)
    except OSError:
        pass

    if f1 is None or f2 is None or f0 is None:
        return None

    gender_guess = "Male" if f0 < F0_GENDER_THRESHOLD else "Female"
    ref_table = STANDARD_MALE_FORMANTS if gender_guess == "Male" else STANDARD_FEMALE_FORMANTS

    if vowel_key not in ref_table:
        # Skip vowels outside the supported set
        return None

    score = compute_score(f1, f2, f3, vowel_key, ref_table)
    feedback = get_feedback(vowel_key, f1, f2, ref_table, quality_hint=qhint)

    return {
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

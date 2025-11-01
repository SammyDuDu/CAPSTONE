#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
KoSPA: Korean Speech Pronunciation Analyzer
Improved version with quantitative scoring and F3 metric support.
"""

import parselmouth
import numpy as np
import os
import sys
import subprocess
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Ellipse

# --- 0. Korean Font Setup ---
try:
    plt.rc('font', family='NanumGothic')
    print("✅ Korean font (NanumGothic) found.")
except:
    print("⚠️ Korean font not found. Labels may not display properly.")
    pass

# --- 1. Baseline Formant Data ---
STANDARD_MALE_FORMANTS = {
    'a (아)': {'f1': 651, 'f2': 1156, 'f3': 2500, 'f1_sd': 136, 'f2_sd': 77},
    'i (이)': {'f1': 236, 'f2': 2183, 'f3': 3010, 'f1_sd': 30,  'f2_sd': 136},
    'u (우)': {'f1': 324, 'f2': 595,  'f3': 2400, 'f1_sd': 43,  'f2_sd': 140},
    'o (오)': {'f1': 320, 'f2': 587,  'f3': 2300, 'f1_sd': 56,  'f2_sd': 132},
    'eu (으)': {'f1': 317, 'f2': 1218, 'f3': 2600, 'f1_sd': 27,  'f2_sd': 155},
    'eo (어)': {'f1': 445, 'f2': 845,  'f3': 2500, 'f1_sd': 103, 'f2_sd': 149},
    'ae (애)': {'f1': 415, 'f2': 1848, 'f3': 2800, 'f1_sd': 56,  'f2_sd': 99}
}

STANDARD_FEMALE_FORMANTS = {
    'a (아)': {'f1': 945, 'f2': 1582, 'f3': 3200, 'f1_sd': 83, 'f2_sd': 141},
    'i (이)': {'f1': 273, 'f2': 2864, 'f3': 3400, 'f1_sd': 22, 'f2_sd': 109},
    'u (우)': {'f1': 346, 'f2': 810,  'f3': 2700, 'f1_sd': 28, 'f2_sd': 106},
    'o (오)': {'f1': 371, 'f2': 700,  'f3': 2600, 'f1_sd': 25, 'f2_sd': 72},
    'eu (으)': {'f1': 390, 'f2': 1752, 'f3': 2900, 'f1_sd': 34, 'f2_sd': 191},
    'eo (어)': {'f1': 576, 'f2': 961,  'f3': 2700, 'f1_sd': 78, 'f2_sd': 87},
    'ae (애)': {'f1': 545, 'f2': 2436, 'f3': 3100, 'f1_sd': 21, 'f2_sd': 95}
}

F0_GENDER_THRESHOLD = 165.0  # Hz

# --- 2. Audio Conversion ---
def convert_to_wav(input_file, output_file):
    try:
        subprocess.run(
            ['ffmpeg', '-i', input_file, '-y', '-ac', '1', '-ar', '44100', output_file],
            check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        return True
    except Exception as e:
        print(f"Error converting file: {e}")
        return False

# --- 3. Formant & Pitch Analysis ---
def analyze_vowel_and_pitch(wav_file_path):
    try:
        snd = parselmouth.Sound(wav_file_path)
        duration = snd.get_total_duration()
        if duration < 0.2:
            print(f"Audio too short ({duration:.2f}s)")
            return None, None, None, None

        snd_part = snd.extract_part(from_time=duration*0.25, to_time=duration*0.75)
        pitch = snd_part.to_pitch(pitch_floor=75.0, pitch_ceiling=500.0)
        pitch_values = pitch.selected_array['frequency']
        f0_mean = np.mean([f for f in pitch_values if f > 0]) or np.nan

        formant = snd_part.to_formant_burg(maximum_formant=5500.0)
        f1_values, f2_values, f3_values = [], [], []
        for frame in range(1, formant.n_frames + 1):
            t = formant.get_time_from_frame_number(frame)
            f1_values.append(formant.get_value_at_time(1, t))
            f2_values.append(formant.get_value_at_time(2, t))
            f3_values.append(formant.get_value_at_time(3, t))

        f1_mean = np.nanmean(f1_values)
        f2_mean = np.nanmean(f2_values)
        f3_mean = np.nanmean(f3_values)

        if any(np.isnan(v) for v in [f0_mean, f1_mean, f2_mean]):
            return None, None, None, None

        return f1_mean, f2_mean, f3_mean, f0_mean
    except Exception as e:
        print(f"Error: {e}")
        return None, None, None, None

# --- 4. Scoring Function ---
def compute_score(measured_f1, measured_f2, measured_f3, intended_vowel, standard_data):
    std = standard_data[intended_vowel]
    f1_z = abs(measured_f1 - std['f1']) / std['f1_sd']
    f2_z = abs(measured_f2 - std['f2']) / std['f2_sd']
    z_avg = (f1_z + f2_z) / 2.0
    # Optional F3 weight (10% influence)
    if 'f3' in std and measured_f3:
        f3_z = abs(measured_f3 - std['f3']) / 400.0  # normalize
        z_avg = (z_avg * 0.9) + (f3_z * 0.1)
    score = max(0, min(100, int(100 - (z_avg * 33))))
    return score

# --- 5. Feedback ---
def get_feedback(vowel, f1, f2, std_data):
    std = std_data[vowel]
    fb = []
    tol1, tol2 = std['f1_sd']*0.5, std['f2_sd']*0.5
    if f1 > std['f1'] + tol1:
        fb.append("Tongue lower than standard → try raising it.")
    elif f1 < std['f1'] - tol1:
        fb.append("Tongue too high → try lowering it.")
    if f2 > std['f2'] + tol2:
        fb.append("Tongue too front → pull it back slightly.")
    elif f2 < std['f2'] - tol2:
        fb.append("Tongue too back → move it forward.")
    if not fb:
        return "Excellent! 👏 Very close to standard pronunciation."
    return " ".join(fb)

# --- 6. Visualization ---
def plot_vowel_space(f1, f2, vowel, std_data, gender, out_img):
    fig, ax = plt.subplots(figsize=(10,8))
    for v, c in std_data.items():
        ax.scatter(c['f2'], c['f1'], c='lightgray', marker='x', s=100)
        ax.text(c['f2']+10, c['f1']+10, v, color='gray')
    t = std_data[vowel]
    ax.scatter(t['f2'], t['f1'], c='green', s=250, label='Target Vowel')
    ellipse = Ellipse((t['f2'], t['f1']), t['f2_sd']*2, t['f1_sd']*2, color='green', alpha=0.2)
    ax.add_patch(ellipse)
    ax.scatter(f2, f1, c='red', s=250, label='Measured')
    ax.set_title(f"KoSPA Vowel Space (Gender: {gender})")
    ax.set_xlabel("F2 (Hz) ← Front / Back →")
    ax.set_ylabel("F1 (Hz) ← High / Low →")
    ax.invert_yaxis(); ax.invert_xaxis()
    ax.legend(); ax.grid(True, linestyle='--', alpha=0.5)
    plt.savefig(out_img); plt.close(fig)
    print(f"Chart saved: {out_img}")

# --- 7. Main ---
if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: python vowel_analyzer.py <input_audio> <vowel> <output_image>")
        sys.exit(1)
    input_file, vowel, out_img = sys.argv[1], sys.argv[2], sys.argv[3]
    if not os.path.exists(input_file):
        print("File not found."); sys.exit(1)
    tmp = "temp.wav"
    if not convert_to_wav(input_file, tmp):
        print("Conversion failed."); sys.exit(1)
    f1, f2, f3, f0 = analyze_vowel_and_pitch(tmp)
    os.remove(tmp)
    if not all([f1, f2, f0]):
        print("Analysis failed."); sys.exit(1)

    gender = "Male" if f0 < F0_GENDER_THRESHOLD else "Female"
    std_data = STANDARD_MALE_FORMANTS if gender=="Male" else STANDARD_FEMALE_FORMANTS
    if vowel not in std_data:
        print(f"Vowel {vowel} not found."); sys.exit(1)

    score = compute_score(f1, f2, f3, vowel, std_data)
    feedback = get_feedback(vowel, f1, f2, std_data)
    plot_vowel_space(f1, f2, vowel, std_data, gender, out_img)

    print(f"\n--- 🧩 Results ---")
    print(f"F0={f0:.2f}Hz, F1={f1:.1f}Hz, F2={f2:.1f}Hz, F3={f3:.1f}Hz")
    print(f"Gender: {gender}")
    print(f"Score: {score}/100")
    print("Feedback:", feedback)
    print("\n---ANALYSIS_RESULT---")
    print({"score": score, "feedback": feedback, "gender": gender})

import parselmouth
import numpy as np
import os
import sys
import subprocess
import matplotlib
# 🌟 [MODIFIED] Use 'Agg' backend for non-GUI server environments
matplotlib.use('Agg') 
import matplotlib.pyplot as plt
from matplotlib.patches import Ellipse
import matplotlib.font_manager as fm # For Korean font detection

# --- 0. Korean Font Setup (for bilingual chart labels) ---
# This block tries to find a Korean font (NanumGothic) installed on the system (e.g., in the Docker container).
# If found, it uses it to display 'a (아)'. If not, it defaults to English fonts.
try:
    plt.rc('font', family='NanumGothic')
    # 🌟 [MODIFIED] All printouts are in English.
    print("Korean font (NanumGothic) found. Using for bilingual labels.")
except:
    print("Korean font not found. Chart labels may not display Korean characters.")
    pass # If font is not found, it will use the default English font.

# --- 1. Baseline Formant Data (Based on Table 2) ---
# These dictionaries store the average (f1, f2) and standard deviation (f1_sd, f2_sd)
# for standard Korean vowels, separated by male and female speakers.
# The keys are bilingual (Romanization + Korean) for clarity.

STANDARD_MALE_FORMANTS = {
    'a (아)': {'f1': 651, 'f2': 1156, 'f1_sd': 136, 'f2_sd': 77},
    'i (이)': {'f1': 236, 'f2': 2183, 'f1_sd': 30,  'f2_sd': 136},
    'u (우)': {'f1': 324, 'f2': 595,  'f1_sd': 43,  'f2_sd': 140},
    'o (오)': {'f1': 320, 'f2': 587,  'f1_sd': 56,  'f2_sd': 132},
    'eu (으)': {'f1': 317, 'f2': 1218, 'f1_sd': 27,  'f2_sd': 155},
    'eo (어)': {'f1': 445, 'f2': 845,  'f1_sd': 103, 'f2_sd': 149},
    'ae (애)': {'f1': 415, 'f2': 1848, 'f1_sd': 56,  'f2_sd': 99}
}

STANDARD_FEMALE_FORMANTS = {
    'a (아)': {'f1': 945, 'f2': 1582, 'f1_sd': 83, 'f2_sd': 141},
    'i (이)': {'f1': 273, 'f2': 2864, 'f1_sd': 22, 'f2_sd': 109},
    'u (우)': {'f1': 346, 'f2': 810,  'f1_sd': 28, 'f2_sd': 106},
    'o (오)': {'f1': 371, 'f2': 700,  'f1_sd': 25, 'f2_sd': 72},
    'eu (으)': {'f1': 390, 'f2': 1752, 'f1_sd': 34, 'f2_sd': 191},
    'eo (어)': {'f1': 576, 'f2': 961,  'f1_sd': 78, 'f2_sd': 87},
    'ae (애)': {'f1': 545, 'f2': 2436, 'f1_sd': 21, 'f2_sd': 95}
}

# F0 (Pitch) threshold to guess gender. (1650 was a typo, 165 is correct)
# F0 > 165 Hz is generally classified as Female.
# F0 < 165 Hz is generally classified as Male.
F0_GENDER_THRESHOLD = 165.0 # Hz

# --- 2. Audio Conversion Function ---
def convert_to_wav(input_file, output_file):
    """
    Converts any audio file (like .m4a) to a mono, 44.1kHz WAV file using ffmpeg.
    ffmpeg must be installed in the server/Docker environment.
    """
    try:
        # Command: ffmpeg -i <input> -y (overwrite) -ac 1 (mono) -ar 44100 (sample rate) <output>
        subprocess.run(['ffmpeg', '-i', input_file, '-y', '-ac', '1', '-ar', '44100', output_file], 
                       check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except Exception as e:
        print(f"Error converting file with ffmpeg: {e}")
        return False

# --- 3. Core Audio Analysis Function ---
def analyze_vowel_and_pitch(wav_file_path):
    """
    Analyzes a WAV file and extracts the average F0 (pitch), F1, and F2 (formants).
    """
    try:
        snd = parselmouth.Sound(wav_file_path)
        duration = snd.get_total_duration()
        if duration < 0.2: 
            print(f"Error: Audio file is too short (< 0.2s) - {duration:.2f}s")
            return None, None, None
            
        # Analyze the middle 50% of the sound to avoid unstable start/end sounds
        start_time = duration * 0.25
        end_time = duration * 0.75
        snd_part = snd.extract_part(from_time=start_time, to_time=end_time)

        # 1. Extract F0 (Pitch)
        pitch = snd_part.to_pitch(pitch_floor=75.0, pitch_ceiling=500.0)
        pitch_values = pitch.selected_array['frequency']
        # Calculate mean, ignoring unvoiced (0 Hz) frames
        f0_mean = np.mean([f for f in pitch_values if f > 0])
        
        # If no pitch is found in the middle part, try the whole audio
        if np.isnan(f0_mean) or f0_mean == 0: 
            pitch_full = snd.to_pitch(pitch_floor=75.0, pitch_ceiling=500.0)
            pitch_values_full = pitch_full.selected_array['frequency']
            f0_mean = np.mean([f for f in pitch_values_full if f > 0])
            
        # 2. Extract F1 & F2 (Formants)
        formant = snd_part.to_formant_burg(maximum_formant=5500.0)
        
        f1_values = []
        f2_values = []
        # Iterate over all time frames in the Formant object
        for frame in range(1, formant.n_frames + 1):
            time = formant.get_time_from_frame_number(frame)
            # Get F1 (formant 1) and F2 (formant 2) at that specific time
            f1_val = formant.get_value_at_time(formant_number=1, time=time)
            f1_values.append(f1_val)
            f2_val = formant.get_value_at_time(formant_number=2, time=time)
            f2_values.append(f2_val)

        # Calculate mean, ignoring NaN (Not a Number) values
        f1_mean = np.nanmean(f1_values)
        f2_mean = np.nanmean(f2_values)

        if np.isnan(f0_mean) or np.isnan(f1_mean) or np.isnan(f2_mean) or f0_mean == 0:
            print("Error: Could not extract valid F0/F1/F2.")
            return None, None, None

        return f1_mean, f2_mean, f0_mean
    except Exception as e:
        print(f"Error during analysis: {e}")
        return None, None, None

# --- 4. Feedback Generation Function ---
def get_feedback(intended_vowel, measured_f1, measured_f2, standard_data):
    """
    Compares measured formants to standard data and generates English feedback.
    """
    if intended_vowel not in standard_data:
        return f"Error: No standard data for '{intended_vowel}'. Make sure vowel is specified like 'a (아)'."
        
    standard = standard_data[intended_vowel]
    std_f1, std_f2 = standard['f1'], standard['f2']
    # Set tolerance to 50% of the standard deviation
    f1_tolerance, f2_tolerance = standard['f1_sd'] * 0.5, standard['f2_sd'] * 0.5
    feedback = []

    # F1 (Tongue Height): High F1 = Low Tongue
    if measured_f1 > std_f1 + f1_tolerance:
        feedback.append(f"Tongue position is lower (more open) than standard '{intended_vowel}'. Try raising your tongue.")
    elif measured_f1 < std_f1 - f1_tolerance:
        feedback.append(f"Tongue position is higher (more closed) than standard '{intended_vowel}'. Try lowering your tongue.")

    # F2 (Tongue Backness): High F2 = Front Tongue
    if measured_f2 > std_f2 + f2_tolerance:
        feedback.append(f"Tongue position is more front than standard '{intended_vowel}'. Try pulling your tongue back slightly.")
    elif measured_f2 < std_f2 - f2_tolerance:
        feedback.append(f"Tongue position is more back than standard '{intended_vowel}'. Try pushing your tongue forward.")

    if not feedback:
        return "Excellent! 👏 Your pronunciation is very close to the standard."

    return " ".join(feedback)

# --- 5. Chart Plotting Function ---
def plot_vowel_space(measured_f1, measured_f2, intended_vowel, standard_data, gender_text, output_image_path):
    """
    Generates the F1/F2 vowel space chart and saves it to a file.
    All labels and titles are in English, but vowel keys are bilingual.
    """
    fig, ax = plt.subplots(figsize=(10, 8))
    
    # 1. Plot all standard vowels as a grey 'x' background
    for vowel, coords in standard_data.items():
        ax.scatter(coords['f2'], coords['f1'], s=100, c='lightgray', marker='x')
        ax.text(coords['f2'] + 10, coords['f1'] + 10, vowel, color='gray', fontsize=12)

    # 2. Plot the target vowel (green circle)
    target_coords = standard_data[intended_vowel]
    ax.scatter(target_coords['f2'], target_coords['f1'], s=250, c='green', alpha=0.7, label=f"Target '{intended_vowel}' Vowel")
    
    # 3. Plot the 1-Sigma Ellipse (visual target area)
    std_f1, std_f2 = target_coords['f1_sd'], target_coords['f2_sd']
    ellipse = Ellipse((target_coords['f2'], target_coords['f1']), width=std_f2 * 2, height=std_f1 * 2, angle=0, color='green', alpha=0.15, zorder=0, label="1-Sigma Range (Target)")
    ax.add_patch(ellipse)
    
    # 4. Plot the measured vowel (red circle)
    ax.scatter(measured_f2, measured_f1, s=250, c='red', alpha=0.7, label="Measured Vowel (You)")
    
    # 5. Set chart titles and labels (All English)
    ax.set_title(f"Vowel Space Analysis (Assumed Gender: {gender_text})", fontsize=16)
    ax.set_xlabel("F2 (Hz) - Tongue Backness (← Front / Back →)", fontsize=12)
    ax.set_ylabel("F1 (Hz) - Tongue Height (← High / Low →)", fontsize=12)
    
    # Invert axes to match phonetic standards
    ax.invert_yaxis() # Low F1 (High Tongue) is at the top
    ax.invert_xaxis() # High F2 (Front Tongue) is at the left
    
    ax.legend(fontsize=12)
    ax.grid(True, linestyle='--', alpha=0.6)
    
    # 6. Save figure and close
    plt.savefig(output_image_path)
    plt.close(fig) # Close figure to free up memory
    print(f"Chart saved to {output_image_path}")

# --- 6. Main Execution Block ---
if __name__ == "__main__":
    
    # This script is run from the command line with 3 arguments
    if len(sys.argv) != 4:
        print("Usage: python vowel_analyzer_server.py <input_audio_file> <intended_vowel> <output_image_path>")
        print("Example: python vowel_analyzer_server.py input/아.m4a \"a (아)\" output/result.png")
        print("Available vowels: 'a (아)', 'i (이)', 'u (우)', 'o (오)', 'eu (으)', 'eo (어)', 'ae (애)'")
        sys.exit(1)
    
    input_file = sys.argv[1]
    intended_vowel = sys.argv[2] # e.g., "a (아)" (must be in quotes if it has a space)
    output_image_path = sys.argv[3] # e.g., "output/result.png"
    
    # 1. Check if input file exists
    if not os.path.exists(input_file):
        print(f"Error: Input file not found at {input_file}")
        sys.exit(1)
        
    # 2. Convert audio to a temporary WAV file
    temp_wav = "temp_analysis.wav"
    if not convert_to_wav(input_file, temp_wav):
        print("Error: Failed to convert audio to WAV.")
        sys.exit(1)

    # 3. Analyze the WAV file
    f1, f2, f0 = analyze_vowel_and_pitch(temp_wav)
    os.remove(temp_wav) # Clean up temporary file
    
    if not (f1 and f2 and f0):
        print("Error: Analysis failed.")
        sys.exit(1)
        
    print(f"Measured F0: {f0:.2f} Hz, F1: {f1:.2f} Hz, F2: {f2:.2f} Hz")

    # 4. Guess gender based on F0 and get feedback
    if f0 < F0_GENDER_THRESHOLD:
        gender_text = "Male"
        standard_data_to_use = STANDARD_MALE_FORMANTS
    else:
        gender_text = "Female"
        standard_data_to_use = STANDARD_FEMALE_FORMANTS
    print(f"Applying {gender_text} standard.")
    
    # 5. Check if the intended vowel is valid before proceeding
    if intended_vowel not in standard_data_to_use:
        print(f"Error: Vowel '{intended_vowel}' not found in standard data. Check spelling and format.")
        print("Available vowels: 'a (아)', 'i (이)', 'u (우)', 'o (오)', 'eu (으)', 'eo (어)', 'ae (애)'")
        sys.exit(1)
        
    feedback = get_feedback(intended_vowel, f1, f2, standard_data_to_use)
    
    # 6. Generate plot
    plot_vowel_space(f1, f2, intended_vowel, standard_data_to_use, gender_text, output_image_path)
    
    # 7. Print final feedback for the server to capture
    print("\n--- 📝 Analysis & Feedback ---")
    print(feedback)
    
    # 8. Print a simple, parsable result for the server
    print("\n---ANALYSIS_RESULT---")
    print(feedback)
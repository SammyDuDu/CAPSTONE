import parselmouth
import numpy as np
import sys
import os
import subprocess

# --- 1. Consonant Baseline Data (VOT, Fricative, Nasal, Liquid) ---
# 🌟 [UPGRADED] Added 'NASAL' and 'LIQUID' analysis types
CONSONANT_STANDARDS = {
    # --- Type 1: VOT Analysis ---
    'g': {'type': 'VOT', 'min': 20, 'max': 60, 'label': 'g (ㄱ)'},
    'd': {'type': 'VOT', 'min': 20, 'max': 60, 'label': 'd (ㄷ)'},
    'b': {'type': 'VOT', 'min': 20, 'max': 60, 'label': 'b (ㅂ)'},
    'j': {'type': 'VOT', 'min': 25, 'max': 65, 'label': 'j (ㅈ)'},
    'k': {'type': 'VOT', 'min': 70, 'max': 120, 'label': 'k (ㅋ)'},
    't': {'type': 'VOT', 'min': 70, 'max': 120, 'label': 't (ㅌ)'},
    'p': {'type': 'VOT', 'min': 70, 'max': 120, 'label': 'p (ㅍ)'},
    'ch': {'type': 'VOT', 'min': 75, 'max': 130, 'label': 'ch (ㅊ)'},
    
    # --- Type 2: Fricative (Spectral Centroid) Analysis ---
    's': {'type': 'FRICATIVE', 'threshold': 4000, 'direction': 'above', 'label': 's (ㅅ)'},
    'h': {'type': 'FRICATIVE', 'threshold': 3000, 'direction': 'below', 'label': 'h (ㅎ)'},

    # --- Type 3: Nasal (Resonance) Analysis ---
    # 🌟 [NEW] Checks for strong low-frequency (0-500Hz) energy before the vowel.
    'n': {'type': 'NASAL', 'min_resonance_db': 50, 'label': 'n (ㄴ) - Nasal'},
    'm': {'type': 'NASAL', 'min_resonance_db': 50, 'label': 'm (ㅁ) - Nasal'},
    
    # --- Type 4: Liquid (F3 Dip) Analysis ---
    # 🌟 [NEW] Checks for a significant dip in the third formant (F3).
    'r': {'type': 'LIQUID', 'min_f3_dip_hz': 300, 'label': 'r (ㄹ) - Liquid'}
}

# --- 2. Audio Conversion Function ---
def convert_to_wav(input_file, output_file):
    # (Same as before)
    try:
        subprocess.run(['ffmpeg', '-i', input_file, '-y', '-ac', '1', '-ar', '44100', output_file], 
                       check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except Exception as e:
        print(f"Error converting file with ffmpeg: {e}")
        return False

# --- 3. Analysis Function (VOT) ---
def analyze_vot(snd):
    # (Same as before)
    try:
        intensity = snd.to_intensity(minimum_pitch=100.0)
        intensity_threshold = np.max(intensity.values) - 30
        burst_frame_indices = np.where(intensity.values[0] > intensity_threshold)[0]
        
        if not burst_frame_indices.any():
             intensity_obj = snd.to_intensity()
             burst_time = intensity_obj.get_time_from_frame_number(1)
             if burst_time < 0: burst_time = 0
        else:
             burst_time = intensity.get_time_from_frame_number(burst_frame_indices[0])

        pitch = snd.to_pitch(time_step=0.001)
        pitch_values = pitch.selected_array['frequency']
        voiced_frames = np.where(pitch_values > 0)[0]
        if not voiced_frames.any():
            print("Error: No voiced vowel found.")
            return None

        frames_after_burst = voiced_frames[voiced_frames > pitch.get_frame_number_from_time(burst_time)]
        if not frames_after_burst.any():
            print("Error: No voicing found *after* the burst.")
            return None
            
        first_voiced_frame = frames_after_burst[0]
        vowel_start_time = pitch.get_time_from_frame_number(first_voiced_frame)
        vot_ms = (vowel_start_time - burst_time) * 1000.0
        return vot_ms if vot_ms > 0 else 0
    except Exception as e:
        print(f"Error during VOT analysis: {e}")
        return None

# --- 4. Analysis Function (Fricative) ---
def analyze_fricative_centroid(snd):
    # (Same as before)
    try:
        pitch = snd.to_pitch(time_step=0.001)
        pitch_values = pitch.selected_array['frequency']
        voiced_frames = np.where(pitch_values > 0)[0]
        if not voiced_frames.any():
            print("Error: No voiced vowel found.")
            return None
        
        vowel_start_time = pitch.get_time_from_frame_number(voiced_frames[0])
        noise_duration = 0.1 
        noise_start_time = vowel_start_time - noise_duration
        if noise_start_time < 0: noise_start_time = 0
        noise_end_time = vowel_start_time - 0.01 
        if noise_end_time <= noise_start_time:
             print("Error: Could not isolate fricative noise.")
             return None

        noise_part = snd.extract_part(from_time=noise_start_time, to_time=noise_end_time)
        spectrum = noise_part.to_spectrum()
        centroid = spectrum.get_centre_of_gravity()
        return centroid
    except Exception as e:
        print(f"Error during Fricative analysis: {e}")
        return None

# --- 5. 🌟 NEW Analysis Function (Nasal) ---
def analyze_nasal_resonance(snd):
    """
    Analyzes the strength of the nasal murmur (low-frequency resonance).
    """
    try:
        # 1. Find the start of the vowel (voicing)
        pitch = snd.to_pitch(time_step=0.001)
        pitch_values = pitch.selected_array['frequency']
        voiced_frames = np.where(pitch_values > 0)[0]
        if not voiced_frames.any():
            print("Error: No voiced vowel found.")
            return None
        vowel_start_time = pitch.get_time_from_frame_number(voiced_frames[0])

        # 2. Extract the nasal part (50ms *before* the vowel)
        nasal_start_time = vowel_start_time - 0.05
        if nasal_start_time < 0: nasal_start_time = 0
        nasal_end_time = vowel_start_time - 0.01
        if nasal_end_time <= nasal_start_time:
            print("Error: Could not isolate nasal segment.")
            return None
            
        nasal_part = snd.extract_part(from_time=nasal_start_time, to_time=nasal_end_time)
        
        # 3. Get the power in the low-frequency band (0-500 Hz)
        spectrum = nasal_part.to_spectrum()
        # Get mean power in dB in the nasal murmur band
        mean_power_db = spectrum.get_mean(0, 500, "dB")
        
        return mean_power_db
    except Exception as e:
        print(f"Error during Nasal analysis: {e}")
        return None

# --- 6. 🌟 NEW Analysis Function (Liquid) ---
def analyze_liquid_f3_dip(snd):
    """
    Analyzes the movement of the 3rd Formant (F3) for 'r'.
    Looks for a dip in F3 during the transition.
    """
    try:
        # 1. Get F3 track for the whole sound
        formant = snd.to_formant_burg(maximum_formant=5500.0, time_step=0.005)
        
        # 2. Find the F3 of the stable vowel (last 25% of the sound)
        vowel_start_time = snd.get_total_duration() * 0.75
        vowel_f3 = formant.get_value_at_time(formant_number=3, time=vowel_start_time)

        # 3. Find the minimum F3 during the transition (first 75%)
        transition_end_time = snd.get_total_duration() * 0.75
        transition_frames = int(transition_end_time / formant.time_step)
        if transition_frames < 1: transition_frames = 1
        
        f3_values = []
        for frame in range(1, transition_frames + 1):
             time = formant.get_time_from_frame_number(frame)
             f3_val = formant.get_value_at_time(formant_number=3, time=time)
             if not np.isnan(f3_val):
                 f3_values.append(f3_val)

        if not f3_values:
            print("Error: Could not find F3 track.")
            return None
            
        min_f3_in_transition = np.min(f3_values)

        # 4. The metric is the difference (dip)
        f3_dip = vowel_f3 - min_f3_in_transition
        
        return f3_dip
    except Exception as e:
        print(f"Error during Liquid (F3) analysis: {e}")
        return None


# --- 7. Feedback Generation Functions (Upgraded Router) ---
def get_feedback(measured_value, intended_consonant_key):
    """
    Main feedback function (Router).
    Calls the correct sub-feedback function based on analysis type.
    """
    if intended_consonant_key not in CONSONANT_STANDARDS:
        return f"Error: No standard data for '{intended_consonant_key}'."
        
    standard = CONSONANT_STANDARDS[intended_consonant_key]
    label = standard['label']
    analysis_type = standard['type']

    if analysis_type == 'VOT':
        return get_vot_feedback_internal(measured_value, standard, label)
    elif analysis_type == 'FRICATIVE':
        return get_fricative_feedback_internal(measured_value, standard, label)
    # 🌟 [NEW] Add routing for Nasal and Liquid
    elif analysis_type == 'NASAL':
        return get_nasal_feedback_internal(measured_value, standard, label)
    elif analysis_type == 'LIQUID':
        return get_liquid_feedback_internal(measured_value, standard, label)
    elif analysis_type == 'UNSUPPORTED':
        return f"Error: Analysis for {label} ({intended_consonant_key}) is not supported."
    else:
        return f"Error: Unknown analysis type '{analysis_type}'."

def get_vot_feedback_internal(measured_vot, standard, label):
    min_vot, max_vot = standard['min'], standard['max']
    print(f"Target VOT Range for {label}: {min_vot}-{max_vot} ms")
    if measured_vot < min_vot:
        return f"VOT is too short. Try to release more air (aspirate) *before* starting the vowel sound."
    elif measured_vot > max_vot:
        return f"VOT is too long. Try to start the vowel sound (voicing) *sooner* after the initial 'pop'."
    else:
        return f"Excellent! 👏 The VOT is within the standard range for {label}."

def get_fricative_feedback_internal(measured_centroid, standard, label):
    threshold = standard['threshold']
    direction = standard['direction']
    print(f"Target Spectral Centroid for {label}: {direction} {threshold} Hz")
    if direction == 'above': # For 's (ㅅ)'
        if measured_centroid < threshold:
            return f"Noise frequency is too low (measured: {measured_centroid:.0f} Hz). " + \
                   f"Try raising the tip of your tongue closer to the roof of your mouth to make a sharper 's' sound."
        else:
            return f"Excellent! 👏 The noise frequency is high and sharp, typical for {label}."
    elif direction == 'below': # For 'h (ㅎ)'
        if measured_centroid > threshold:
            return f"Noise frequency is too high (measured: {measured_centroid:.0f} Hz). " + \
                   f"This sounds more like 's' than 'h'. Try relaxing your throat and making a breathier 'h' sound."
        else:
            return f"Excellent! 👏 The noise frequency is low and breathy, typical for {label}."

# --- 8. 🌟 NEW Feedback Functions (Nasal, Liquid) ---
def get_nasal_feedback_internal(measured_resonance, standard, label):
    min_resonance = standard['min_resonance_db']
    print(f"Target Nasal Resonance for {label}: above {min_resonance} dB (in 0-500Hz band)")
    
    if measured_resonance < min_resonance:
        return f"Nasal resonance is too weak (measured: {measured_resonance:.0f} dB). " + \
               f"Ensure you are letting the sound resonate through your nose *before* opening your mouth for the vowel."
    else:
        return f"Excellent! 👏 Strong nasal resonance detected, typical for {label}."

def get_liquid_feedback_internal(measured_f3_dip, standard, label):
    min_dip = standard['min_f3_dip_hz']
    print(f"Target F3 Dip for {label} ('ra'): at least {min_dip} Hz")
    
    if measured_f3_dip < min_dip:
        return f"The F3 dip is too shallow (measured: {measured_f3_dip:.0f} Hz). " + \
               f"This suggests the tongue-tip tap for 'ㄹ' was not clear or was too slow. Try a quicker 'tap' motion."
    else:
        return f"Excellent! 👏 A clear F3 dip was detected"
    
# --- 9. Main Execution Block (Upgraded Router) ---
if __name__ == "__main__":
    
    if len(sys.argv) != 3:
        print("Usage: python consonant_analyzer.py <input_audio_file> <intended_consonant_key>")
        print("Example (for '가'): python consonant_analyzer.py input/가.m4a g")
        print("Example (for '사'): python consonant_analyzer.py input/사.m4a s")
        print("Example (for '나'): python consonant_analyzer.py input/나.m4a n")
        print("Example (for '라'): python consonant_analyzer.py input/라.m4a r")
        # 🌟 [수정됨] 사용 가능한 키 목록 업데이트
        print("Available keys: g, d, b, j, k, t, p, ch, s, h, n, m, r")
        sys.exit(1)
    
    input_file = sys.argv[1]
    intended_consonant_key = sys.argv[2].lower()
    
    if not os.path.exists(input_file):
        print(f"Error: Input file not found at {input_file}")
        sys.exit(1)
        
    temp_wav = "temp_consonant.wav"
    if not convert_to_wav(input_file, temp_wav):
        print("Error: Failed to convert audio to WAV.")
        sys.exit(1)

    if intended_consonant_key not in CONSONANT_STANDARDS:
        print(f"Error: Key '{intended_consonant_key}' is not defined in CONSONANT_STANDARDS.")
        os.remove(temp_wav)
        sys.exit(1)

    standard = CONSONANT_STANDARDS[intended_consonant_key]
    analysis_type = standard['type']
    
    measured_value = None
    
    # 1. Load sound object once
    snd = parselmouth.Sound(temp_wav)
    os.remove(temp_wav) # Clean up temp file

    # 2. Route to the correct analysis function
    if analysis_type == 'VOT':
        measured_value = analyze_vot(snd)
        if measured_value is not None:
             print(f"Measured VOT: {measured_value:.2f} ms")
    elif analysis_type == 'FRICATIVE':
        measured_value = analyze_fricative_centroid(snd)
        if measured_value is not None:
             print(f"Measured Spectral Centroid: {measured_value:.2f} Hz")
    elif analysis_type == 'NASAL':
        measured_value = analyze_nasal_resonance(snd)
        if measured_value is not None:
             print(f"Measured Nasal Resonance: {measured_value:.2f} dB (0-500Hz)")
    elif analysis_type == 'LIQUID':
        measured_value = analyze_liquid_f3_dip(snd)
        if measured_value is not None:
            print(f"Measured F3 Dip: {measured_value:.2f} Hz")
    elif analysis_type == 'UNSUPPORTED':
        measured_value = 0 # Dummy value, get_feedback will handle it
    else:
        print(f"Error: Unknown analysis type '{analysis_type}' for key '{intended_consonant_key}'")
        sys.exit(1)
    
    if measured_value is None:
        print("Error: Analysis failed.")
        sys.exit(1)
        
    # 3. Get and print feedback
    feedback = get_feedback(measured_value, intended_consonant_key)
    
    print("\n--- 📝 Analysis & Feedback ---")
    print(feedback)
    
    print("\n---ANALYSIS_RESULT---")
    print(feedback)
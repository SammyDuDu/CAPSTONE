#!/bin/bash

# --- Configuration ---
# This script tests all 14 consonants from '가' to '하'.
# It maps the Korean filename to the English key required by the Python script.

# 1. Python script to execute
PYTHON_SCRIPT="consonant_v1.py"

# 2. Input directory containing the audio files
# (Based on screenshot: sample/consonant is in the parent directory)
AUDIO_DIR="../sample/consonant"

# --- Script Start ---
echo "================================================="
echo "Starting Full Consonant Analysis Test Script..."
echo "================================================="

# 1. Define the mapping from Korean filename to the English analysis key
#    We use a bash associative array for this.
declare -A FILE_KEY_MAP
FILE_KEY_MAP=(
    ["가.m4a"]="g"  # Plosive (VOT)
    ["나.m4a"]="n"  # Nasal (Resonance)
    ["다.m4a"]="d"  # Plosive (VOT)
    ["라.m4a"]="r"  # Liquid (F3 Dip)
    ["마.m4a"]="m"  # Nasal (Resonance)
    ["바.m4a"]="b"  # Plosive (VOT)
    ["사.m4a"]="s"  # Fricative (Centroid)
    ["아.m4a"]="vowel" # '아' is a vowel, not a consonant. We will skip it.
    ["자.m4a"]="j"  # Affricate (VOT)
    ["차.m4a"]="ch" # Affricate (VOT)
    ["카.m4a"]="k"  # Plosive (VOT)
    ["타.m4a"]="t"  # Plosive (VOT)
    ["파.m4a"]="p"  # Plosive (VOT)
    ["하.m4a"]="h"  # Fricative (Centroid)
)

# 2. Loop through each file in the map
for file in "${!FILE_KEY_MAP[@]}"
do
    TARGET_KEY="${FILE_KEY_MAP[$file]}"
    INPUT_FILE="$AUDIO_DIR/$file"

    echo "-------------------------------------------------"
    echo "Testing File: $file (Target Key: $TARGET_KEY)"
    echo "-------------------------------------------------"

    # 3. Check if the input file exists
    if [ ! -f "$INPUT_FILE" ]; then
        echo "Error: Input file not found at $INPUT_FILE. Skipping."
        continue
    fi

    # 4. Skip '아.m4a' as it is a vowel and cannot be analyzed by this script
    if [ "$TARGET_KEY" == "vowel" ]; then
        echo "Skipping '아.m4a' as it is a vowel. (Use vowel_v1.py for this)."
        continue
    fi

    # 5. Execute the Python script
    #    python <script.py> <input_file_path> <consonant_key>
    python "$PYTHON_SCRIPT" "$INPUT_FILE" "$TARGET_KEY"
    
    echo " " # Add a blank line for readability
done

echo "================================================="
echo "All consonant tests finished."
echo "================================================="

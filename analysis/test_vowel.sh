#!/bin/bash

# --- Configuration ---

# 1. Python script to execute
# (Assumes vowel_analyzer_server.py is in the same 'analysis' folder)
PYTHON_SCRIPT="vowel_v1.py"

# 2. Input directory containing the audio files
# (Assumes 'sample/vowel_man' is in the parent directory)
AUDIO_DIR="../sample/vowel_man"

# 3. Output directory to save the resulting images
OUTPUT_DIR="./output"

# --- Script Start ---

echo "Starting vowel analysis test script..."

# 1. Create the output directory if it doesn't exist
mkdir -p "$OUTPUT_DIR"
echo "Output directory ensured at: $OUTPUT_DIR"

# 2. List of files to test (Korean filenames)
# (Ensure these files actually exist at the AUDIO_DIR path)
FILES=("아.wav" "이.wav" "우.wav" "오.wav" "으.wav" "어.wav" "애.wav")

# 3. Loop through each file and run the Python script
for file in "${FILES[@]}"
do
    # Based on the filename (e.g., "아.wav"), determine the
    # Python argument ("a (아)") and the output filename ("a").
    case "$file" in
        "아.wav")
            base_name="a"
            vowel_key="a (아)"
            ;;
        "이.wav")
            base_name="i"
            vowel_key="i (이)"
            ;;
        "우.wav")
            base_name="u"
            vowel_key="u (우)"
            ;;
        "오.wav")
            base_name="o"
            vowel_key="o (오)"
            ;;
        "으.wav")
            base_name="eu"
            vowel_key="eu (으)"
            ;;
        "어.wav")
            base_name="eo"
            vowel_key="eo (어)"
            ;;
        "애.wav")
            base_name="ae"
            vowel_key="ae (애)"
            ;;
        *)
            echo "Skipping unknown file: $file"
            continue
            ;;
    esac

    # 4. Define command arguments
    INPUT_FILE="$AUDIO_DIR/$file"
    INTENDED_VOWEL="$vowel_key" # 🌟 Pass the vowel key in quotes to handle spaces and parentheses
    OUTPUT_IMAGE="$OUTPUT_DIR/${base_name}_result.png" # Example: ./output/a_result.png

    # 5. Check if the input file exists
    if [ ! -f "$INPUT_FILE" ]; then
        echo "Error: Input file not found at $INPUT_FILE. Skipping."
        continue
    fi

    # 6. Execute the Python script
    echo "-------------------------------------"
    echo "Testing: $file (Target: $INTENDED_VOWEL)"
    
    python "$PYTHON_SCRIPT" "$INPUT_FILE" "$INTENDED_VOWEL" "$OUTPUT_IMAGE"
    
    echo "Test for $file complete. Image saved to $OUTPUT_IMAGE"
    echo "-------------------------------------"
done

echo "All tests finished."
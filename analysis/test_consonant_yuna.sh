#!/bin/bash

# --- Configuration ---

# 1. Python script to execute
PYTHON_SCRIPT="consonant.py"

# 2. Input directory containing the audio files
# (Your recorded consonant+ㅏ samples live here, e.g. 다.wav 따.wav 타.wav ...)
AUDIO_DIR="../sample/consonant_yuna"

# 3. Output directory to save the text results for each file
OUTPUT_DIR="./consonant_yuna_output"

# --- Script Start ---

echo "Starting consonant analysis batch script..."

# 1. Create the output directory if it doesn't exist
mkdir -p "$OUTPUT_DIR"
echo "Output directory ensured at: $OUTPUT_DIR"
echo

# 2. List of test syllables (must match both filename and the syllable key in your Python 'reference' dict)
# Add or remove items as you get more recordings
FILES=("가.wav" "까.wav" "카.wav" \
       "다.wav" "따.wav" "타.wav" \
       "바.wav" "빠.wav" "파.wav" \
       "사.wav" "싸.wav" "하.wav" \
       "자.wav" "짜.wav" "차.wav" \
       "마.wav" "나.wav" "라.wav")

# 4. Loop over each file and run analysis
for FILE in "${FILES[@]}"; do
    SYLLABLE="${FILE%.wav}"              # strip ".wav" -> e.g. "다"
    INPUT_PATH="$AUDIO_DIR/$FILE"
    OUTPUT_PATH="$OUTPUT_DIR/${SYLLABLE}_result.txt"

    echo "Analyzing $SYLLABLE ($INPUT_PATH)..."

    if [ ! -f "$INPUT_PATH" ]; then
        echo "  [WARN] File not found: $INPUT_PATH"
        echo "[ERROR] Missing audio for $SYLLABLE ($INPUT_PATH)" > "$OUTPUT_PATH"
        echo
        continue
    fi

    # Call the python script in batch mode
    # NOTE: this assumes consonant.py supports these CLI args now:
    #   --syllable <SYLLABLE>
    #   --sex <male|female>
    #   --file <path/to/audio.wav>
    python "$PYTHON_SCRIPT" \
        --syllable "$SYLLABLE" \
        --file "$INPUT_PATH" \
        > "$OUTPUT_PATH"

    echo "  Saved result to $OUTPUT_PATH"
    echo
done

echo "Batch consonant analysis complete."

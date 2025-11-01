#!/bin/bash

# --- Configuration ---

# 1. Python script to execute
# (update this to match your actual filename)
PYTHON_SCRIPT="vowel_v2.py"

# 2. Input directory containing the audio files
# Pass a different directory as the first argument if needed
DEFAULT_AUDIO_DIR="../sample/check_vowel"
AUDIO_DIR="${1:-$DEFAULT_AUDIO_DIR}"

# 3. Output directory to save the resulting images
OUTPUT_DIR="./output"

echo "Starting KoSPA vowel batch test..."
echo "Using audio directory: $AUDIO_DIR"

# Create output dir
mkdir -p "$OUTPUT_DIR"
echo "Output directory ensured at: $OUTPUT_DIR"

# 4. List of vowel recordings to process.
# ⚠ Update these names to match the actual (possibly Korean) filenames in your folder.
FILES=("아" "어" "오" "우" "으" "이" "애" "에" "외" "위")

for file in "${FILES[@]}"; do
    # Map: filename (Korean) -> model argument key + output prefix
    case "$file" in
        "아")
            base_name="a"
            vowel_key="a (아)"
            ;;
        "어")
            base_name="eo"
            vowel_key="eo (어)"
            ;;
        "오")
            base_name="o"
            vowel_key="o (오)"
            ;;
        "우")
            base_name="u"
            vowel_key="u (우)"
            ;;
        "으")
            base_name="eu"
            vowel_key="eu (으)"
            ;;
        "이")
            base_name="i"
            vowel_key="i (이)"
            ;;
        "애")
            base_name="ae"
            vowel_key="ae (애)"
            ;;
        "에")
            base_name="e"
            vowel_key="e (에)"
            ;;
        "외")
            base_name="oe"
            vowel_key="oe (외)"
            ;;
        "위")
            base_name="wi"
            vowel_key="wi (위)"
            ;;
        *)
            echo "Skipping unknown file key: $file"
            continue
            ;;
    esac

    # 5. Locate the actual audio file (supports .wav / .m4a / .mp3)
    INPUT_FILE=""
    for ext in wav m4a mp3; do
        candidate="$AUDIO_DIR/$file.$ext"
        if [ -f "$candidate" ]; then
            INPUT_FILE="$candidate"
            break
        fi
    done

    if [ -z "$INPUT_FILE" ]; then
        echo "❌ Error: No audio found for '$file' in $AUDIO_DIR (tried .wav .m4a .mp3). Skipping."
        continue
    fi

    OUTPUT_IMAGE="$OUTPUT_DIR/${base_name}_result.png"

    echo "-------------------------------------"
    echo "▶ Testing: $(basename "$INPUT_FILE") (Target: $vowel_key)"

    python "$PYTHON_SCRIPT" "$INPUT_FILE" "$vowel_key" "$OUTPUT_IMAGE"

    echo "✅ Done: $file -> $OUTPUT_IMAGE"
    echo "-------------------------------------"
done

echo "All tests finished."

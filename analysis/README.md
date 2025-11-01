# Analysis Toolkit Overview

This folder contains the standalone analysis utilities used to evaluate Korean vowel
and consonant recordings. Everything is Python 3.11 compatible and designed to run
headless (matplotlib uses the `Agg` backend).

---

## Core vowel engine (`vowel_v2.py`)

`vowel_v2.py` exposes everything needed to analyse a single vowel file.

| Function | Purpose |
| --- | --- |
| `convert_to_wav(input_file, output_file)` | Uses `ffmpeg` to convert any audio (m4a/mp3/wav) into a mono 44.1 kHz WAV file. |
| `_stable_window(sound, min_len=0.12)` | Finds a high-energy, low-noise segment (≈0.12 s) so formant extraction is stable. |
| `analyze_vowel_and_pitch(wav_path)` | Extracts F0, F1, F2 and F3 from the stable window. Returns the measurements plus a recording-quality hint. |
| `compute_score(f1, f2, f3, vowel_key, ref_table)` | Converts the deviation from the reference tables into a 0–100 score (F1/F2 dominate, optional F3 weight ≈10 %). |
| `get_feedback(vowel_key, f1, f2, ref_table, quality_hint=None)` | Produces a short text feedback message in English (e.g., “Tongue too front → pull it slightly back.”). |
| `analyze_single_audio(audio_path, vowel_key)` | High-level wrapper: converts, extracts, guesses gender (F0 < 165 Hz → male), scores and returns a dict with all fields. |
| `plot_single_vowel_space(f1, f2, vowel_key, gender, out_img)` | Saves a PNG showing the target formant ellipse and the measured point. |

Run it directly to analyse one file and emit the plot plus JSON-like summary:

```bash
python vowel_v2.py ../sample/check_vowel/아.m4a "a (아)" ./output/a_result.png
```

`vowel_v3.py` is the same engine but with the male reference table aligned to the
latest sample averages. Import whichever version you need.

---

## Batch helpers

### `voweltest.py`
Python CLI that walks a dataset directory structure (`<root>/아/*.m4a`, etc.), runs
`analyze_single_audio`, and generates:

- Per-vowel reports (`<vowel>_report.txt`)
- Individual F1/F2 scatter plots (`*_distribution*.png`)
- Overall map (`overall_vowel_map.png`)
- Optional blended comparison plot (`--blend 0.3` inserts intermediate reference points)

Example:

```bash
python voweltest.py ../sample/10sample_vowel ./batch_output_v2 --blend 0.3
```

### `test_vowel.sh`
Simple Bash wrapper that iterates over a hard-coded list of vowel files, searches for
matching `.wav/.m4a/.mp3`, and calls `vowel_v2.py`. Update the `FILES=()` list to
match your filenames.

```bash
bash test_vowel.sh ../sample/check_vowel
```

### `plot_vowel_space.py`
Lightweight script to drop multiple recordings onto a single vowel chart (labels only,
no scoring). Useful for a quick visual check.

```bash
python plot_vowel_space.py ../sample/check_vowel --output ./output/combined_vowel_space.png
```

### `feedback_demo.py`
Reads `summary_all.txt` (produced by `voweltest.py`) and prints out the feedback text
that the engine would return. Handy when iterating on prompt wording.

```bash
python feedback_demo.py --summary ./batch_output_v2/summary_all.txt
```

### `test_consonant.sh` / `consonant_v1.py`
Parallel tooling for consonants. `test_consonant.sh` maps Korean filenames to the
English keys expected by `consonant_v1.py`; the Python module itself follows the same
convert → extract → score pattern but targets plosives, nasals, fricatives, etc.

---

## Quick smoke test

```bash
cd CAPSTONE/analysis
python -m pip install -r ../requirements.txt      # ensure praat-parselmouth, ffmpeg, etc.
python voweltest.py ../sample/10sample_vowel ./batch_output_v2
python feedback_demo.py --summary ./batch_output_v2/summary_all.txt
```

Check `./batch_output_v2/overall_vowel_map.png` and the printed feedback to confirm
everything is wired correctly.

---

## Using the engine from other code

```python
from vowel_v2 import analyze_single_audio

result = analyze_single_audio("../sample/check_vowel/아.m4a", "a (아)")
if result:
    print(result["score"], result["feedback"])
```

Return schema:

```python
{
    "vowel_key": "a (아)",
    "audio_path": "...",
    "gender": "Male",
    "f0": 150.2,
    "f1": 640.5,
    "f2": 1180.4,
    "f3": 2505.0,
    "score": 72,
    "feedback": "Tongue too front → pull it slightly back.",
    "quality_hint": "Background noise high; quieter place please."
}
```

Feed the dict straight into your API response or reporting layer.

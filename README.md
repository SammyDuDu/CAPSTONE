# KoSPA Integrated Speech Trainer

KoSPA is a FastAPI application that serves the web SPA and performs real-time
Korean vowel and consonant analysis. Users record directly in the browser,
upload the audio to the backend, and immediately receive scoring plus targeted
feedback.

## Features
- **Single deployment** – FastAPI delivers templates/static assets and exposes
  the analysis API in one process.
- **2-second web recording** – `MediaRecorder` captures `audio/webm`, streamed
  to the server with `FormData`.
- **Vowel engine** – `analysis/vowel_v2.py` extracts formants (F1–F3), pitch,
  quality hints, and keeps a perfect score within ±2.5σ of the target formant
  distribution.
- **Consonant engine** – `analysis/consonant.py` measures VOT, frication, nasal
  energy, etc., also rewarding 100 points up to ±2.5σ.
- **Visual feedback** – vowel analysis renders a formant plot that overlays the
  learner’s sample on the native target region.
- **Database integration** – progress and calibration formants are stored in a
  Render PostgreSQL instance (`DB_URL` in `main.py`).

## Prerequisites
1. **Python** 3.10+ (development was on 3.12).
2. **ffmpeg** in PATH – required by `convert_to_wav`.
   - Ubuntu: `sudo apt install ffmpeg`
3. **Python dependencies** – install via `requirements.txt` (FastAPI, numpy,
   parselmouth, scipy, etc.).
4. **PostgreSQL access** – either use the default Render database or replace
   `DB_URL` with your own credentials/environment variable.

## Setup
```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt
```

## Running the app
### Option 1 – helper script
```bash
./run.sh
```
Runs `uvicorn main:app --host 0.0.0.0 --port 8000`.

### Option 2 – manual command
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Open `http://127.0.0.1:8000`, pick a Hangul symbol, and record for analysis.

## Project layout
```
CAPSTONE/
├── main.py              # FastAPI app, routes, analysis endpoints
├── analysis/            # Vowel/consonant analysis engines
├── static/              # Front-end JS, CSS, images
├── templates/           # Jinja templates (base/index/sound)
├── requirements.txt
└── run.sh               # Convenience wrapper for uvicorn
```

## Scoring & feedback
- **Vowels** – F1/F2/F3 deviations are converted to σ units. Average z ≤ 2.5
  scores 100; beyond that, the score decreases linearly (≈40 points per σ).
- **Consonants** – the mean absolute z across all measured features uses the
  same threshold/penalty.
- **Front-end UX** – cards display the numeric comparison to the target, while
  actionable advice appears as a bullet list. Vowel plots highlight how close
  the sample is to the native target ellipse.

## Production notes
- Externalize `DB_URL`, enable HTTPS, hash passwords, and add cleanup for the
  generated analysis plots before deploying broadly.
- Combined vowels or consonants without reference data currently return HTTP
  400; adjust the UI or add new reference datasets as needed.

For deeper engine details see `analysis/README.md`.

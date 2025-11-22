# KoSPA - Korean Speech Pronunciation Analyzer
## Complete Project Documentation

**Version**: 2.0.0
**Last Updated**: 2025-11-22
**Python Version**: 3.11.0
**License**: MIT

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [System Architecture](#2-system-architecture)
3. [Tech Stack](#3-tech-stack)
4. [Analysis Engine Details](#4-analysis-engine-details)
5. [API Reference](#5-api-reference)
6. [Database Schema](#6-database-schema)
7. [Frontend Structure](#7-frontend-structure)
8. [Deployment Guide](#8-deployment-guide)
9. [Known Issues & Solutions](#9-known-issues--solutions)
10. [Development Guide](#10-development-guide)

---

## 1. Project Overview

### 1.1 Purpose
A real-time pronunciation analysis and feedback system for Korean language learners. Based on phonetic analysis algorithms, it objectively evaluates vowel and consonant accuracy and provides specific correction methods.

### 1.2 Key Features
- **Browser-based 2-second voice recording** (MediaRecorder API)
- **Dual analysis engines**:
  - Vowels: Formant (F1, F2, F3) analysis
  - Consonants: VOT, frication, nasal energy measurement
- **Visual feedback**: Formant space plot generation
- **Personal calibration**: User-specific reference value settings
- **Progress tracking**: PostgreSQL-based learning history management

### 1.3 Supported Phonemes
- **Vowels (6)**: ㅏ, ㅓ, ㅗ, ㅜ, ㅡ, ㅣ
- **Consonants (18)**:
  - Plain: ㄱ, ㄴ, ㄷ, ㄹ, ㅁ, ㅂ, ㅅ, ㅈ, ㅎ
  - Tense: ㄲ, ㄸ, ㅃ, ㅆ, ㅉ
  - Aspirated: ㅋ, ㅌ, ㅍ, ㅊ

---

## 2. System Architecture

### 2.1 Overall Structure

```
┌─────────────────────────────────────────────────────────────┐
│                    USER (Web Browser)                       │
│  MediaRecorder API → FormData → Fetch API                  │
└────────────────────────┬────────────────────────────────────┘
                         │ HTTPS
                         ▼
┌─────────────────────────────────────────────────────────────┐
│              FastAPI Application (main.py)                  │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Web Layer: Jinja2 Templates + Static Files          │   │
│  └─────────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ API Layer: /api/analyze-sound, /api/auth/*, etc    │   │
│  └─────────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Audio Pipeline: Upload → FFmpeg → WAV conversion   │   │
│  └────────────┬─────────────────────────┬──────────────┘   │
│               │                         │                   │
│    ┌──────────▼──────────┐   ┌─────────▼──────────┐       │
│    │  Vowel Engine       │   │ Consonant Engine   │       │
│    │  (vowel_v2.py)      │   │ (consonant.py)     │       │
│    │  - Formant Analysis │   │ - VOT Measurement  │       │
│    │  - Gender Detection │   │ - Aspiration Ratio │       │
│    │  - Plot Generation  │   │ - Frication Stats  │       │
│    └─────────────────────┘   └────────────────────┘       │
└─────────────────────────────────────────────────────────────┘
                         │
        ┌────────────────┼────────────────┐
        ▼                ▼                ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│ PostgreSQL   │ │ Static FS    │ │   FFmpeg     │
│ (Docker/RDS) │ │ (Ephemeral)  │ │  (System)    │
└──────────────┘ └──────────────┘ └──────────────┘
```

### 2.2 Directory Structure

```
CAPSTONE/
├── main.py                # FastAPI app initialization (123 lines)
├── config.py              # Configuration, constants, Korean mappings
├── database.py            # PostgreSQL connection and queries
├── utils.py               # Audio processing, analysis orchestration
├── requirements.txt       # Python dependencies
├── run.sh                 # Uvicorn startup script
│
├── routes/                # API endpoint modules
│   ├── __init__.py        # Router exports
│   ├── pages.py           # HTML page routes (/, /sound, /health)
│   ├── auth.py            # Authentication endpoints
│   └── analysis.py        # Sound analysis endpoints
│
├── analysis/              # Speech analysis engines
│   ├── vowel_v2.py        # Vowel analysis (formant extraction)
│   ├── consonant.py       # Consonant analysis (VOT, frication)
│   ├── config.py          # Analysis parameters
│   └── README.md          # Engine documentation
│
├── templates/             # Jinja2 HTML templates
│   ├── base.html          # Base layout
│   ├── index.html         # Main page (phoneme selection)
│   └── sound.html         # Recording and analysis page
│
├── static/                # Static files
│   ├── scripts/
│   │   ├── ui.js          # User interface logic
│   │   └── sound.js       # Recording and API communication
│   ├── styles/
│   │   └── style.css      # Tailwind CSS
│   └── images/
│       └── analysis/      # Generated formant plots
│
├── Dockerfile             # Container image definition
├── docker-compose.yml     # Multi-container setup (app + PostgreSQL)
├── init.sql               # Database schema initialization
├── .env.docker            # Environment variables template
│
└── sample/                # Test audio samples
    ├── vowel_man/         # Vowel samples
    └── consonant/         # Consonant samples
```

---

## 3. Tech Stack

### 3.1 Backend
| Technology | Version | Purpose |
|------------|---------|---------|
| **Python** | 3.11.0 | Runtime environment |
| **FastAPI** | latest | Web framework |
| **Uvicorn** | latest | ASGI server |
| **Praat-Parselmouth** | latest | Speech analysis (Praat wrapper) |
| **NumPy** | latest | Numerical operations |
| **SciPy** | latest | Signal processing |
| **Matplotlib** | latest | Formant plot generation |
| **psycopg2-binary** | latest | PostgreSQL driver |
| **python-multipart** | latest | File upload handling |
| **Jinja2** | latest | HTML template rendering |

### 3.2 Frontend
| Technology | Description |
|------------|-------------|
| **Vanilla JavaScript** | Pure JS (No React/Vue/Angular) |
| **MediaRecorder API** | Browser recording (WebM container, Opus codec) |
| **Fetch API** | AJAX communication |
| **Tailwind CSS** | Utility-first CSS framework |
| **Jinja2 Templates** | Server-side rendering |

### 3.3 System Dependencies
| Tool | Purpose |
|------|---------|
| **FFmpeg** | WebM/M4A → WAV conversion (required) |
| **PostgreSQL** | User data and progress storage |
| **Docker** | Containerized deployment |

### 3.4 Infrastructure
- **Docker Compose**: App + PostgreSQL containers
- **AWS EC2**: Production deployment (Ubuntu 22.04)
- **Optional**: AWS RDS for production database

---

## 4. Analysis Engine Details

### 4.1 Vowel Analysis Engine (vowel_v2.py)

#### 4.1.1 Core Algorithm

```python
# 1. Stable Window Selection (0.12 seconds)
stable_window = find_highest_rms_segment(audio, duration=0.12s)

# 2. F0 (Pitch) Extraction
f0_median = extract_pitch_median(stable_window)
gender = "Male" if f0_median < 165 Hz else "Female"

# 3. Formant Extraction (Praat Burg Algorithm)
formant_object = sound.to_formant_burg(
    time_step=0.01,
    max_number_of_formants=5,
    maximum_formant=5500 (Female) or 5000 (Male),
    window_length=0.025,
    pre_emphasis_from=50.0
)

f1 = formant.get_value_at_time(1, time_point)  # Tongue height
f2 = formant.get_value_at_time(2, time_point)  # Front-back position
f3 = formant.get_value_at_time(3, time_point)  # Lip rounding

# 4. Z-score Calculation
z1 = abs(f1 - reference_f1) / reference_f1_sd
z2 = abs(f2 - reference_f2) / reference_f2_sd
avg_z = (z1 + z2) / 2

# 5. Scoring (±2.5σ threshold)
if avg_z <= 2.5:
    score = 100
else:
    penalty = (avg_z - 2.5) * 40  # 40 points per σ
    score = max(0, 100 - penalty)
```

#### 4.1.2 Reference Data (Formants)

**Adult Male (Hz)**
| Vowel | F1 | F1 SD | F2 | F2 SD | F3 |
|-------|-------|-------|----------|-------|------|
| ㅏ (a) | 651 | 136 | 1156 | 77 | 2500 |
| ㅓ (eo) | 445 | 103 | 845 | 149 | 2500 |
| ㅗ (o) | 320 | 56 | 587 | 132 | 2300 |
| ㅜ (u) | 324 | 43 | 595 | 140 | 2400 |
| ㅡ (eu) | 317 | 27 | 1218 | 155 | 2600 |
| ㅣ (i) | 236 | 30 | 2183 | 136 | 3010 |

**Adult Female (Hz)**
| Vowel | F1 | F1 SD | F2 | F2 SD | F3 |
|-------|-------|-------|----------|-------|------|
| ㅏ (a) | 945 | 83 | 1582 | 141 | 3200 |
| ㅓ (eo) | 576 | 78 | 961 | 87 | 2700 |
| ㅗ (o) | 371 | 25 | 700 | 72 | 2600 |
| ㅜ (u) | 346 | 28 | 810 | 106 | 2700 |
| ㅡ (eu) | 390 | 34 | 1752 | 191 | 2900 |
| ㅣ (i) | 273 | 22 | 2864 | 109 | 3400 |

#### 4.1.3 Feedback Generation

```python
# F1 feedback (tongue height)
if f1 > reference_f1:
    feedback += "Mouth too open / tongue too low → raise tongue slightly."
else:
    feedback += "Mouth too closed / tongue too high → lower tongue slightly."

# F2 feedback (front-back position)
if f2 > reference_f2:
    feedback += "Tongue too front → pull it slightly back."
else:
    feedback += "Tongue too back → move it slightly forward."
```

---

### 4.2 Consonant Analysis Engine (consonant.py)

#### 4.2.1 Supported Consonant Types

```python
# 1. Stop (plosives): ㄱ, ㄷ, ㅂ, ㄲ, ㄸ, ㅃ, ㅋ, ㅌ, ㅍ
# 2. Fricative: ㅅ, ㅆ, ㅎ
# 3. Affricate: ㅈ, ㅉ, ㅊ
# 4. Sonorant: ㄴ, ㄹ, ㅁ
```

#### 4.2.2 Measured Features

**Stops**
- `VOT_ms` (Voice Onset Time): Time from release to voicing onset (ms)
- `asp_ratio` (Aspiration Ratio): VOT segment energy / total energy
- `burst_dB`: Burst energy (dB)

**Fricatives**
- `fric_dur_ms`: Frication duration (ms)
- `centroid_kHz`: Spectral centroid frequency (kHz)

**Affricates**
- Combination of VOT + Frication features

**Sonorants**
- `seg_dur_ms`: Consonant segment duration (ms)
- `nasal_lowFreq_amp`: Low-frequency nasal energy ratio

#### 4.2.3 Scoring

```python
def score_against_reference(measured_feats, ref_feats, sex):
    z_list = []

    for feat_name, (mean, sd) in ref_feats.items():
        measured_val = measured_feats.get(feat_name)
        z = abs((measured_val - mean) / sd)
        z_list.append(min(z, 3.0))  # Cap at 3σ

    avg_z = sum(z_list) / len(z_list)

    if avg_z <= 1.5:
        score = 100
    else:
        penalty = (avg_z - 1.5) * 60  # 60 points per σ
        score = max(0, 100 - penalty)

    return score, advice_list
```

---

## 5. API Reference

### 5.1 Authentication API

#### POST `/api/auth/signup`
Create a new user account.

**Request Body**:
```json
{
  "username": "string",
  "password": "string"
}
```

**Response**:
```json
{
  "ok": true,
  "message": "User created"
}
```

---

#### POST `/api/auth/login`
Authenticate user.

**Request Body**:
```json
{
  "username": "string",
  "password": "string"
}
```

**Response**:
```json
{
  "ok": true,
  "message": "Login successful",
  "user": "username",
  "userid": 123,
  "calibration_complete": false
}
```

---

#### POST `/api/auth/change-password`
Change user password.

**Request Body**:
```json
{
  "username": "string",
  "new_password": "string"
}
```

---

### 5.2 Analysis API

#### POST `/api/analyze-sound`
Analyze pronunciation for logged-in user (saves progress).

**Request** (multipart/form-data):
```
audio: File (WebM/M4A/MP3)
userid: int
sound: string (Korean phoneme, e.g., "ㅏ", "ㄱ")
```

**Response**:
```json
{
  "userid": 123,
  "sound": "ㅏ",
  "analysis_type": "vowel",
  "score": 85,
  "feedback": "Mouth too closed / tongue too high → lower tongue slightly.",
  "details": {
    "symbol": "ㅏ",
    "vowel_key": "a (아)",
    "gender": "Female",
    "formants": {
      "f0": 220.5,
      "f1": 920.3,
      "f2": 1550.2,
      "f3": 2600.1
    },
    "reference": {
      "f1": 945,
      "f1_sd": 83,
      "f2": 1582,
      "f2_sd": 141
    },
    "plot_url": "/static/images/analysis/abc123.png"
  }
}
```

---

#### POST `/api/analyze-sound-guest`
Analyze pronunciation without login.

**Request** (multipart/form-data):
```
audio: File
sound: string
```

**Response**: Same as `/api/analyze-sound` but without `userid`

---

### 5.3 Calibration API

#### POST `/api/calibration`
Save personal formant calibration.

**Request** (multipart/form-data):
```
audio: File
sound: string ('a', 'e', or 'u')
userid: int
```

**Response**:
```json
{
  "ok": true,
  "message": "Calibration recording for 'a' saved",
  "sound": "a",
  "userid": 123
}
```

---

#### GET `/api/formants?userid={id}`
Get user calibration data.

**Response**:
```json
{
  "userid": 123,
  "formants": {
    "a": {
      "f1_mean": 650.5,
      "f1_std": 80.2,
      "f2_mean": 1200.3,
      "f2_std": 120.5
    }
  }
}
```

---

### 5.4 Progress API

#### GET `/api/progress?username={name}`
Get user learning progress.

**Response**:
```json
{
  "progress": {
    "ㅏ": 85,
    "ㅓ": 70,
    "ㄱ": 90
  }
}
```

---

### 5.5 Other APIs

#### GET `/health`
Health check endpoint.

**Response**:
```json
{
  "status": "ok",
  "message": "FastAPI server is running!"
}
```

#### GET `/api/info`
API information and available endpoints.

---

## 6. Database Schema

### 6.1 Connection

**Docker Compose**: Automatically configured via `DATABASE_URL` environment variable.

```
postgresql://kospa:kospa123@db:5432/kospa_db
```

---

### 6.2 Table Structure

#### `users`
User account information.

```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(255) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

#### `progress`
Learning progress tracking.

```sql
CREATE TABLE progress (
    id SERIAL PRIMARY KEY,
    userid INTEGER REFERENCES users(id) ON DELETE CASCADE,
    sound VARCHAR(10) NOT NULL,
    progress INTEGER DEFAULT 0,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(userid, sound)
);
```

---

#### `formants`
Personal calibration data.

```sql
CREATE TABLE formants (
    id SERIAL PRIMARY KEY,
    userid INTEGER REFERENCES users(id) ON DELETE CASCADE,
    sound VARCHAR(10) NOT NULL,
    f1_mean FLOAT,
    f1_std FLOAT,
    f2_mean FLOAT,
    f2_std FLOAT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(userid, sound)
);
```

---

## 7. Frontend Structure

### 7.1 Tech Stack

- **Framework**: None (Vanilla JavaScript)
- **Template Engine**: Jinja2 (server-side)
- **CSS**: Tailwind CSS

### 7.2 Key Files

#### `static/scripts/sound.js`
Recording and analysis logic.

```javascript
// 1. Initialize MediaRecorder
const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
mediaRecorder = new MediaRecorder(stream);

// 2. Record for 2 seconds
mediaRecorder.start();
setTimeout(() => mediaRecorder.stop(), 2000);

// 3. Blob → FormData
const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
const formData = new FormData();
formData.append('audio', audioBlob, 'recording.webm');
formData.append('sound', soundSymbol);
formData.append('userid', userId);

// 4. API call
const response = await fetch('/api/analyze-sound', {
    method: 'POST',
    body: formData
});

// 5. Display results
const data = await response.json();
updateScoreCard(data.score);
updateFeedback(data.feedback);
```

---

## 8. Deployment Guide

### 8.1 Docker Deployment (Recommended)

#### Prerequisites
- Docker and Docker Compose installed
- Git

#### Steps

```bash
# 1. Clone repository
git clone https://github.com/GunwoongP/CAPSTONE.git
cd CAPSTONE

# 2. Copy environment configuration
cp .env.docker .env

# 3. Build and run
docker compose up --build

# 4. Access application
# http://localhost:8000
```

#### Useful Commands

```bash
# Run in background
docker compose up -d --build

# View logs
docker compose logs -f app

# Stop containers
docker compose down

# Reset database
docker compose down -v
```

---

### 8.2 AWS EC2 Deployment

#### 1. Launch EC2 Instance
- AMI: Ubuntu 22.04 LTS
- Instance type: t2.small or larger
- Storage: 20GB+

#### 2. Install Docker

```bash
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
newgrp docker
```

#### 3. Deploy Application

```bash
git clone https://github.com/GunwoongP/CAPSTONE.git
cd CAPSTONE
cp .env.docker .env
docker compose up -d --build
```

#### 4. Configure Security Group
- Allow inbound TCP port 8000 (or 80/443 with reverse proxy)

#### 5. Access
- `http://<EC2-Public-IP>:8000`

---

### 8.3 Local Development

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Install ffmpeg (Ubuntu)
sudo apt install ffmpeg

# Run server
./run.sh
# or
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

---

### 8.4 Production Checklist

#### Security
- [ ] Set specific CORS origins (replace `"*"`)
- [ ] Implement password hashing (bcrypt/argon2)
- [ ] Configure HTTPS (nginx + Let's Encrypt)
- [ ] Add API rate limiting

#### Performance
- [ ] Move plot storage to S3 or persistent volume
- [ ] Add caching for static files
- [ ] Optimize database indexes

#### Monitoring
- [ ] Set up logging
- [ ] Add error tracking (Sentry)
- [ ] Monitor server resources

---

## 9. Known Issues & Solutions

### 9.1 Security Vulnerabilities

#### Plain Text Passwords
**Issue**: Passwords stored without hashing.

**Solution**:
```python
import bcrypt

# Signup
hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

# Login
if bcrypt.checkpw(password.encode('utf-8'), stored_hash.encode('utf-8')):
    # Success
```

#### CORS Configuration
**Issue**: All origins allowed (`"*"`).

**Solution**: Set specific origins in `main.py`:
```python
allow_origins=["https://yourdomain.com"]
```

---

### 9.2 Calibration Not Implemented

**Location**: `routes/analysis.py`

**Current**: Saves dummy formant values.

**TODO**: Implement actual formant extraction from calibration recordings.

---

### 9.3 Ephemeral Filesystem

**Issue**: Generated plots lost on container restart.

**Solutions**:
1. **AWS S3**: Upload plots to S3
2. **Docker Volume**: Mount persistent volume
3. **Accept limitation**: Plots are session-only

---

## 10. Development Guide

### 10.1 Adding New Phonemes

#### Adding a Vowel

**1. Add reference data** (`analysis/vowel_v2.py`):
```python
STANDARD_MALE_FORMANTS = {
    'ae (애)': {'f1': 800, 'f2': 1800, 'f3': 2700, 'f1_sd': 90, 'f2_sd': 120},
}
```

**2. Add symbol mapping** (`config.py`):
```python
VOWEL_SYMBOL_TO_KEY = {
    "ㅐ": "ae (애)",
}
```

**3. Add frontend card** (`templates/index.html`)

---

#### Adding a Consonant

**1. Add reference data** (`analysis/consonant.py`):
```python
reference = {
    "빠": {
        "type": "stop",
        "features": {
            "VOT_ms": {"male": (8.5, 4.0), "female": (9.0, 4.5)},
        },
        "coaching": "Press lips firmly..."
    },
}
```

**2. Add symbol mapping** (`config.py`):
```python
CONSONANT_SYMBOL_TO_SYLLABLE = {
    "ㅃ": "빠",
}
```

---

### 10.2 Debugging Tips

#### Analysis Failures

1. **Check FFmpeg**: `ffmpeg -version`
2. **Check temp file permissions**: `ls -la /tmp/tmp*.wav`
3. **Enable debug logs**: `uvicorn main:app --log-level debug`

#### Database Connection Issues

```python
import psycopg2
conn = psycopg2.connect(os.getenv("DATABASE_URL"))
print("DB connection successful!")
conn.close()
```

---

## Appendix

### A. Glossary

| Term | Description |
|------|-------------|
| **Formant** | Resonance frequencies of the vocal tract. F1 (tongue height), F2 (front-back position), F3 (lip rounding) |
| **VOT** | Voice Onset Time. Time from stop release to voicing onset |
| **Z-score** | Difference from mean in standard deviation units |
| **Aspiration** | Breathy release in aspirated consonants (ㅋ, ㅌ, ㅍ) |
| **Frication** | Turbulent airflow in fricatives (ㅅ, ㅆ, ㅎ) |
| **Parselmouth** | Python wrapper for Praat |
| **Praat** | Phonetic analysis software (University of Amsterdam) |

---

### B. References

- **Praat Documentation**: https://www.fon.hum.uva.nl/praat/
- **Parselmouth**: https://parselmouth.readthedocs.io/
- **FastAPI**: https://fastapi.tiangolo.com/
- **Docker**: https://docs.docker.com/

---

### C. License & Contributors

**Project License**: MIT

**Contributors**:
- Speech analysis engine development
- Frontend development
- Documentation: Built with assistance from Claude Code

---

**Document Version**: 2.0.0
**Last Updated**: 2025-11-22
**Author**: KoSPA Development Team

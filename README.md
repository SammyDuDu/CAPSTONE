# KoSPA - Korean Speech Pronunciation Analyzer

KoSPA is a modular FastAPI application for real-time Korean pronunciation analysis.
Users record directly in the browser, upload audio to the backend, and receive
instant scoring with targeted feedback.

## Features

- **Modular architecture** – Clean separation of concerns with dedicated modules for config, database, utilities, and routes
- **Docker deployment** – One-command deployment with PostgreSQL included
- **Real-time analysis** – 2-second recordings analyzed instantly via `MediaRecorder` API
- **Vowel engine** – Extracts formants (F1–F3), compares against native speaker references, scores within ±2.5σ
- **Consonant engine** – Measures VOT, frication, nasal energy with same scoring threshold
- **Visual feedback** – Vowel space plots overlay learner samples on native target regions
- **User progress** – Track improvement over time with personal calibration

## Prerequisites

### Option A – Docker (Recommended)
1. **Docker** and **Docker Compose** installed
   - Windows/Mac: [Docker Desktop](https://www.docker.com/products/docker-desktop/)
   - Linux: `curl -fsSL https://get.docker.com | sh`

### Option B – Local Development
1. **Python** 3.10+ (tested on 3.11/3.12)
2. **ffmpeg** – `sudo apt install ffmpeg`
3. **Python packages** – `pip install -r requirements.txt`
4. **PostgreSQL** – Local instance or cloud database

## Running the App

### Option 1 – Docker (Recommended)

```bash
# Copy environment configuration
cp .env.docker .env

# Build and run containers
docker compose up --build

# Run in background
docker compose up -d --build
```

Open http://localhost:8000 in your browser.

**Useful commands:**
```bash
docker compose logs -f app     # View logs
docker compose down            # Stop containers
docker compose down -v         # Reset database
```

### Option 2 – Local Development

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
./run.sh
```

Or: `uvicorn main:app --reload --host 0.0.0.0 --port 8000`

## Project Structure

```
CAPSTONE/
├── main.py              # FastAPI app initialization, router registration
├── config.py            # Environment variables, constants, Korean mappings
├── database.py          # PostgreSQL connection and query functions
├── utils.py             # Audio processing, analysis orchestration
├── routes/              # API endpoint modules
│   ├── __init__.py      # Router exports
│   ├── pages.py         # HTML pages (/, /sound, /health)
│   ├── auth.py          # Authentication (/api/auth/*, /api/progress)
│   └── analysis.py      # Sound analysis (/api/analyze-sound*)
├── analysis/            # Pronunciation analysis engines
│   ├── vowel_v2.py      # Vowel formant extraction and scoring
│   ├── consonant.py     # Consonant feature analysis
│   ├── config.py        # Analysis parameters
│   └── README.md        # Engine documentation
├── static/              # Frontend assets (CSS, JS, images)
├── templates/           # Jinja2 HTML templates
├── Dockerfile           # Container image definition
├── docker-compose.yml   # Multi-container setup (app + PostgreSQL)
├── init.sql             # Database schema initialization
├── .env.docker          # Environment variables template
├── requirements.txt     # Python dependencies
└── run.sh               # Development server script
```

## API Endpoints

### Pages
- `GET /` – Home page with sound selection grid
- `GET /sound?s=ㅏ` – Sound practice page
- `GET /health` – Health check for monitoring

### Authentication
- `POST /api/auth/signup` – Create account
- `POST /api/auth/login` – Login and get session
- `POST /api/auth/change-password` – Update password
- `GET /api/progress?username=...` – Get user's scores
- `GET /api/formants?userid=...` – Get calibration data

### Analysis
- `POST /api/calibration` – Save calibration recording
- `POST /api/analyze-sound` – Analyze with progress tracking
- `POST /api/analyze-sound-guest` – Analyze without login
- `GET /api/info` – API information and endpoints

## Module Descriptions

### config.py
Central configuration including:
- `DB_URL` – Database connection string from environment
- `VOWEL_SYMBOL_TO_KEY` – Maps Hangul jamo to analysis keys
- `CONSONANT_SYMBOL_TO_SYLLABLE` – Maps jamo to example syllables
- `SOUND_DESCRIPTIONS` – Pronunciation guidance for each sound

### database.py
PostgreSQL operations with context-managed connections:
- User CRUD (create, authenticate, update password)
- Progress tracking (get/update high scores)
- Calibration data (formant storage)

### utils.py
Audio processing and analysis orchestration:
- File handling (temp files, cleanup)
- Type conversions (safe_float, normalise_score)
- Analysis functions (vowel/consonant analysis)
- Main entry point: `analyse_uploaded_audio()`

### routes/
Organized API endpoints:
- **pages.py** – HTML rendering with Jinja2 templates
- **auth.py** – User authentication and data retrieval
- **analysis.py** – Sound analysis and calibration

## Scoring System

- **Threshold**: ±2.5σ (standard deviations) from native speaker mean
- **Perfect score**: 100 points when within threshold
- **Penalty**: ~40 points per σ beyond threshold
- **Vowels**: Based on F1/F2/F3 formant deviations
- **Consonants**: Based on VOT, frication, nasal energy, etc.

## AWS EC2 Deployment

### Option 1 – Development (HTTP only)

1. Launch EC2 instance (Ubuntu 22.04, t2.small or larger)
2. Install Docker:
   ```bash
   curl -fsSL https://get.docker.com | sh
   sudo usermod -aG docker $USER
   newgrp docker
   ```
3. Clone and run:
   ```bash
   git clone <repository-url>
   cd CAPSTONE
   docker compose up -d --build
   ```
4. Configure Security Group: Allow inbound TCP port 8000
5. Access via: `http://<EC2-Public-IP>:8000`

### Option 2 – Production (HTTPS with Nginx + SSL)

**Required for microphone access** - browsers require HTTPS for `getUserMedia()`.

1. **Setup DuckDNS (free domain)**
   - Go to https://www.duckdns.org and create a subdomain
   - Point it to your EC2 Public IP

2. **Install Docker on EC2:**
   ```bash
   sudo apt-get update
   sudo apt-get install -y docker.io docker-compose-v2
   sudo systemctl start docker && sudo systemctl enable docker
   sudo usermod -aG docker $USER
   newgrp docker
   ```

3. **Configure Security Group:**
   - Allow inbound TCP port **80** (HTTP - for Let's Encrypt)
   - Allow inbound TCP port **443** (HTTPS)

4. **Clone and setup:**
   ```bash
   git clone <repository-url>
   cd CAPSTONE
   ```

5. **Get SSL Certificate:**
   ```bash
   chmod +x init-ssl.sh
   ./init-ssl.sh your-domain.duckdns.org your-email@example.com
   ```

6. **Start production server:**
   ```bash
   docker compose -f docker-compose.prod.yml up -d --build
   ```

7. Access via: `https://your-domain.duckdns.org`

### Manual Update Steps

1. **Commit and Push** code changes to your `main` branch on GitHub
2. **SSH** into EC2 instance
3. **Pull changes** and restart:
   ```bash
   cd ~/CAPSTONE
   git pull origin main
   # For development:
   docker compose up -d --build
   # For production (HTTPS):
   docker compose -f docker-compose.prod.yml up -d --build
   ```

## Production Files

| File | Description |
|------|-------------|
| `docker-compose.prod.yml` | Production setup with Nginx + Certbot |
| `nginx/nginx.prod.conf` | HTTPS reverse proxy configuration |
| `init-ssl.sh` | SSL certificate initialization script |

## Production Notes

- Microphone requires HTTPS - use production deployment for full functionality
- SSL certificates auto-renew via Certbot (90-day validity)
- Set specific CORS origins in `main.py` (replace `"*"`)
- Implement password hashing (bcrypt/argon2) in `database.py`
- Add plot cleanup cron job for `/static/images/analysis/`

## Documentation

- [Engine Analysis Details](ENGINE_ANALYSIS.md) – Detailed scoring algorithms
- [Full Documentation](DOCUMENTATION.md) – Complete system documentation
- [Roadmap](ROADMAP.md) – Future development plans
- [Analysis Engine README](analysis/README.md) – Vowel/consonant engine details

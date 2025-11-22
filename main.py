"""
KoSPA - Korean Speech Pronunciation Analyzer
============================================
Main FastAPI application entry point.

This is the central application file that:
- Initializes the FastAPI application
- Configures middleware (CORS)
- Mounts static files
- Registers all route modules

Project Structure:
    main.py         - This file (app initialization)
    config.py       - Configuration and constants
    database.py     - Database operations
    utils.py        - Utility functions
    routes/         - API endpoint modules
        pages.py    - HTML page routes
        auth.py     - Authentication endpoints
        analysis.py - Sound analysis endpoints
    analysis/       - Pronunciation analysis engines
        vowel_v2.py - Vowel formant analysis
        consonant.py- Consonant feature analysis

Usage:
    uvicorn main:app --host 0.0.0.0 --port 8000

    Or with Docker:
    docker compose up --build
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from routes import pages_router, auth_router, analysis_router


# =============================================================================
# APPLICATION INITIALIZATION
# =============================================================================

app = FastAPI(
    title="KoSPA - Korean Speech Pronunciation Analyzer",
    description=(
        "Real-time Korean pronunciation analysis service. "
        "Analyzes vowel formants and consonant acoustic features "
        "to provide detailed feedback and scoring."
    ),
    version="2.0.0",
)


# =============================================================================
# MIDDLEWARE CONFIGURATION
# =============================================================================

# CORS middleware for cross-origin requests
# Configure for production: replace "*" with specific origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],        # TODO: Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =============================================================================
# STATIC FILES
# =============================================================================

# Mount static directory for CSS, JavaScript, and images
# Accessible at: /static/styles/style.css, /static/scripts/ui.js, etc.
app.mount("/static", StaticFiles(directory="static"), name="static")


# =============================================================================
# ROUTE REGISTRATION
# =============================================================================

# Page routes (/, /sound, /health)
app.include_router(pages_router)

# Authentication routes (/api/auth/*, /api/progress, /api/formants)
app.include_router(auth_router)

# Analysis routes (/api/calibration, /api/analyze-sound, /api/analyze-sound-guest)
app.include_router(analysis_router)


# =============================================================================
# APPLICATION INFO
# =============================================================================

@app.get("/api/info")
async def app_info():
    """
    Get application information.

    Returns version and available endpoints for API discovery.
    """
    return {
        "name": "KoSPA",
        "version": "2.0.0",
        "description": "Korean Speech Pronunciation Analyzer",
        "endpoints": {
            "pages": ["/", "/sound", "/health"],
            "auth": [
                "/api/auth/signup",
                "/api/auth/login",
                "/api/auth/change-password",
                "/api/progress",
                "/api/formants"
            ],
            "analysis": [
                "/api/calibration",
                "/api/analyze-sound",
                "/api/analyze-sound-guest"
            ]
        }
    }

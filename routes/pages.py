"""
KoSPA Page Routes
=================
Routes for rendering HTML pages.

Endpoints:
- GET /       : Home page with sound selection grid
- GET /sound  : Individual sound practice page
- GET /health : Health check endpoint for monitoring
"""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from config import SOUND_DESCRIPTIONS


# Initialize router
router = APIRouter(tags=["Pages"])

# Template configuration
templates = Jinja2Templates(directory="templates")


# =============================================================================
# PAGE ROUTES
# =============================================================================

@router.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """
    Render the main home page.

    Displays a grid of Korean sounds (vowels and consonants)
    for users to select and practice.

    Args:
        request: FastAPI request object

    Returns:
        Rendered index.html template
    """
    return templates.TemplateResponse("index.html", {"request": request})


@router.get("/sound", response_class=HTMLResponse)
async def sound_page(request: Request):
    """
    Render the sound practice page.

    Shows recording interface and pronunciation guidance
    for a specific Hangul symbol.

    Query Parameters:
        s: Hangul symbol to practice (e.g., 'ㅏ', 'ㄱ')

    Args:
        request: FastAPI request object

    Returns:
        Rendered sound.html template with:
        - sound: The Hangul symbol
        - description: Pronunciation guidance text
    """
    sound = request.query_params.get("s", "")

    return templates.TemplateResponse(
        "sound.html",
        {
            "request": request,
            "sound": sound,
            "description": SOUND_DESCRIPTIONS.get(sound, "")
        }
    )


# =============================================================================
# HEALTH CHECK
# =============================================================================

@router.get("/health")
async def health_check():
    """
    Health check endpoint for monitoring.

    Used by:
    - Docker health checks
    - Load balancers
    - Monitoring systems

    Returns:
        JSON with status and message
    """
    return {
        "status": "ok",
        "message": "FastAPI server is running!"
    }

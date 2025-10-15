import os
import random
import time
from typing import Annotated

from fastapi import FastAPI, UploadFile, Form, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse

# Initialize the FastAPI application
app = FastAPI(
    title="Korean Vowel Analysis API",
    description="Unified service hosting both frontend and backend."
)

# --- Template and Static File Configuration ---
# Point templates to the 'templates' directory
templates = Jinja2Templates(directory="templates")

# Mount static files (CSS, JS) from the 'static' directory
# Assets will be accessible at http://your-app.com/static/styles/style.css
app.mount("/static", StaticFiles(directory="static"), name="static")

# --- CORS Configuration ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Route to Serve the Main HTML Page ---
@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """
    Serves the index.html template when the root URL is accessed.
    """
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/health")
async def health_check():
    """Simple health check endpoint."""
    return {"status": "ok", "message": "FastAPI server is running!"}


@app.post("/api/analyze-vowel")
async def analyze_vowel(
    audio: UploadFile,
    target: Annotated[str, Form()]
):
    """
    Handles the audio file upload (UploadFile) and target vowel (Form data).
    This function currently mocks the acoustic analysis.
    """
    
    if not audio.filename:
        raise HTTPException(status_code=400, detail="No audio file provided.")
    
    # --- MOCK ANALYSIS ---
    time.sleep(1) # Simulate processing time
    simulated_score = random.randint(50, 99)
    
    # Return the result in a JSON package
    return {
        "score": simulated_score,
        "target_vowel": target,
        "feedback": f"Mock analysis complete. Target vowel was '{target}'.",
    }

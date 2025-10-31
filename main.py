import os
import random
import time
from typing import Annotated

from fastapi import FastAPI, UploadFile, Form, HTTPException, Request
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from psycopg2 import connect

DB_URL = "postgresql://capstone_itcd_user:2XLTwuuR3pJw4epFlT7lo71WnsmzuDFU@dpg-d411ot1r0fns739sc58g-a.singapore-postgres.render.com/capstone_itcd"

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

# --- Sound page ---
@app.get("/sound", response_class=HTMLResponse)
async def sound_page(request: Request):
    """Render sound page for a selected Hangul symbol, provided via query param 's'."""
    sound = request.query_params.get("s", "")
    descriptions = {
        "ㅏ": "Say 'a' like 'father'. Tongue low, mouth open wide, breath steady.",
        "ㅑ": "Say 'ya' like 'yacht'. Tongue low, lips slightly spread, quick breath.",
        "ㅓ": "Say 'eo' like 'uh'. Tongue mid-back, mouth slightly open, exhale softly.",
        "ㅕ": "Say 'yeo' like 'yuh'. Tongue mid-back, lift middle of tongue slightly, soft breath.",
        "ㅗ": "Say 'o' like 'go'. Round lips, tongue mid-back, push air gently.",
        "ㅛ": "Say 'yo' like 'yo-yo'. Round lips, tongue mid-back, start with 'y' sound, gentle breath.",
        "ㅜ": "Say 'u' like 'zoo'. Round lips tightly, tongue back, steady breath.",
        "ㅠ": "Say 'yu' like 'you'. Round lips tightly, tongue back, start with 'y' sound, gentle exhale.",
        "ㅡ": "Say 'eu' like 'put' without rounding. Tongue flat, back raised slightly, lips unrounded, controlled breath.",
        "ㅣ": "Say 'i' like 'see'. Tongue high front, lips spread, push air steadily.",
        "ㅐ": "Say 'ae' like 'cat'. Tongue mid-front, mouth slightly open, exhale gently.",
        "ㅒ": "Say 'yae' like 'yeah'. Tongue mid-front, mouth open, start with 'y', soft breath.",
        "ㅔ": "Say 'e' like 'bed'. Tongue mid-front, lips relaxed, steady airflow.",
        "ㅖ": "Say 'ye' like 'yes'. Tongue mid-front, start with 'y', lips relaxed, exhale gently.",
        "ㅘ": "Say 'wa' like 'water'. Tongue low-back for 'a', round lips for 'o', smooth blend, steady breath.",
        "ㅙ": "Say 'wae' like 'wet'. Tongue mid-back to mid-front, lips slightly rounded, exhale gently.",
        "ㅚ": "Say 'oe' like 'we'. Tongue mid, lips slightly rounded, push air lightly.",
        "ㅝ": "Say 'wo' like 'wonder'. Tongue back, round lips for 'o', soft breath, smooth transition.",
        "ㅞ": "Say 'we' like 'wet'. Tongue mid-back, lips slightly rounded, gentle exhale.",
        "ㅟ": "Say 'wi' like 'week'. Tongue back, lips tightly rounded, push air steadily.",
        "ㅢ": "Say 'ui'. Start 'eu' (tongue back, lips unrounded), glide to 'i' (tongue high-front), controlled breath.",
        "ㄱ": "Say 'g' like 'go'. Back of tongue touches soft palate, release air slightly at start.",
        "ㄴ": "Say 'n' like 'no'. Tongue tip touches upper gum, exhale steadily.",
        "ㄷ": "Say 'd' like 'dog'. Tongue tip touches upper gum, release air slightly, soft at start.",
        "ㄹ": "Say 'r/l'. Tongue tip taps ridge behind upper teeth once, light flick, end as 'l' if at word end.",
        "ㅁ": "Say 'm' like 'mom'. Lips closed, nasal breath.",
        "ㅂ": "Say 'b' like 'boy'. Lips together, release with soft burst, steady breath.",
        "ㅅ": "Say 's' like 'see'. Tongue tip near upper front teeth, exhale sharply but softly.",
        "ㅇ": "Silent at start, 'ng' at end like 'song'. Back of tongue raised to soft palate for 'ng'.",
        "ㅈ": "Say 'j' like 'jam'. Tongue tip touches ridge behind upper teeth, release with soft burst.",
        "ㅊ": "Say 'ch' like 'chop'. Tongue tip touches ridge, release with strong burst, add aspiration.",
        "ㅋ": "Say 'k' like 'kite'. Back of tongue touches soft palate, release strongly with breath.",
        "ㅌ": "Say 't' like 'top'. Tongue tip at ridge, release strongly with breath.",
        "ㅍ": "Say 'p' like 'pop'. Lips together, release strongly with breath.",
        "ㅎ": "Say 'h' like 'hat'. Breath out gently, vocal cords relaxed.",
        "ㄲ": "Say 'kk' tense. Back of tongue touches soft palate, push air hard, keep throat tight.",
        "ㄸ": "Say 'tt' tense. Tongue tip at ridge, push air hard, keep throat tight.",
        "ㅃ": "Say 'pp' tense. Lips together, push air hard, tight throat.",
        "ㅆ": "Say 'ss' tense. Tongue tip at ridge, exhale hard, keep mouth firm.",
        "ㅉ": "Say 'jj' tense. Tongue tip at ridge, release with strong burst, tight throat.",
    }

    return templates.TemplateResponse(
        "sound.html",
        {"request": request, "sound": sound, "description": descriptions.get(sound, "")}
    )


@app.get("/health")
async def health_check():
    """Simple health check endpoint."""
    return {"status": "ok", "message": "FastAPI server is running!"}


# ------------------------------
# AUTH API (SKELETON ENDPOINTS)
# ------------------------------

class AuthCredentials(BaseModel):
    username: str
    password: str


@app.post("/api/auth/signup")
async def auth_signup(creds: AuthCredentials):
    with connect(DB_URL, sslmode="require") as conn:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO users (username, password) VALUES (%s, %s)", (creds.username, creds.password))
            conn.commit()
    return {"ok": True, "message": "User created"}


@app.post("/api/auth/login")
async def auth_login(creds: AuthCredentials):
    with connect(DB_URL, sslmode="require") as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id, username FROM users WHERE username = %s AND password = %s", (creds.username, creds.password))
            user = cur.fetchone()
            if user is None:
                raise HTTPException(status_code=401, detail="Invalid credentials")
    return {"ok": True, "message": "Login successful", "user": user[1]}


class ChangePasswordPayload(BaseModel):
    username: str
    new_password: str


@app.post("/api/auth/change-password")
async def change_password(payload: ChangePasswordPayload):
    with connect(DB_URL, sslmode="require") as conn:
        with conn.cursor() as cur:
            cur.execute("UPDATE users SET password = %s WHERE username = %s", (payload.new_password, payload.username))
            if cur.rowcount == 0:
                raise HTTPException(status_code=404, detail="User not found")
            conn.commit()
    return {"ok": True, "message": "Password updated"}


@app.get("/api/progress")
async def get_progress(username: str):
    with connect(DB_URL, sslmode="require") as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM users WHERE username = %s", (username,))
            row = cur.fetchone()
            if row is None:
                return {"progress": {}}
            user_id = row[0]
            cur.execute("SELECT sound, progress FROM progress WHERE userid = %s", (user_id,))
            items = cur.fetchall() or []
            result = {s.strip(): int(p) for (s, p) in items}
    return {"progress": result}


class UpdateProgressPayload(BaseModel):
    username: str
    sound: str  # single bpchar(1)
    progress: int  # 0..100


@app.post("/api/update-progress")
async def update_progress(payload: UpdateProgressPayload):
    """Upsert user's progress for a sound. Keeps the maximum progress value.
    If user or sound is invalid, returns 404.
    """
    sound = (payload.sound or "").strip()
    if not payload.username or not sound or not isinstance(payload.progress, int):
        raise HTTPException(status_code=400, detail="Invalid payload")
    value = max(0, min(100, int(payload.progress)))

    with connect(DB_URL, sslmode="require") as conn:
        with conn.cursor() as cur:
            # Find user id
            cur.execute("SELECT id FROM users WHERE username = %s", (payload.username,))
            row = cur.fetchone()
            if row is None:
                raise HTTPException(status_code=404, detail="User not found")
            user_id = row[0]

            # Try update first
            cur.execute(
                "UPDATE progress SET progress = GREATEST(progress, %s) WHERE userid = %s AND sound = %s",
                (value, user_id, sound)
            )
            if cur.rowcount == 0:
                # Insert if no existing row
                cur.execute(
                    "INSERT INTO progress (userid, sound, progress) VALUES (%s, %s, %s)",
                    (user_id, sound, value)
                )
            conn.commit()
    return {"ok": True, "message": "Progress updated", "sound": sound, "progress": value}


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

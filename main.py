import os
from tempfile import NamedTemporaryFile
from typing import Annotated, Dict, Optional
from uuid import uuid4

from fastapi import FastAPI, UploadFile, Form, HTTPException, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from psycopg2 import connect

from analysis import consonant as consonant_analysis
from analysis.vowel_v2 import (
    analyze_single_audio,
    convert_to_wav,
    STANDARD_MALE_FORMANTS,
    STANDARD_FEMALE_FORMANTS,
    plot_single_vowel_space,
)

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

VOWEL_SYMBOL_TO_KEY: Dict[str, str] = {
    "ㅏ": "a (아)",
    "ㅓ": "eo (어)",
    "ㅗ": "o (오)",
    "ㅜ": "u (우)",
    "ㅡ": "eu (으)",
    "ㅣ": "i (이)",
}

CONSONANT_SYMBOL_TO_SYLLABLE: Dict[str, str] = {
    "ㄱ": "가",
    "ㄴ": "나",
    "ㄷ": "다",
    "ㄹ": "라",
    "ㅁ": "마",
    "ㅂ": "바",
    "ㅅ": "사",
    "ㅈ": "자",
    "ㅊ": "차",
    "ㅋ": "카",
    "ㅌ": "타",
    "ㅍ": "파",
    "ㅎ": "하",
    "ㄲ": "까",
    "ㄸ": "따",
    "ㅃ": "빠",
    "ㅆ": "싸",
    "ㅉ": "짜",
}

PLOT_OUTPUT_DIR = os.path.join("static", "images", "analysis")
os.makedirs(PLOT_OUTPUT_DIR, exist_ok=True)


def resolve_sound_symbol(symbol: str) -> str:
    if symbol in VOWEL_SYMBOL_TO_KEY:
        return "vowel"
    if symbol in CONSONANT_SYMBOL_TO_SYLLABLE:
        return "consonant"
    raise HTTPException(status_code=400, detail=f"Unsupported sound symbol: {symbol}")


def _safe_float(value):
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return value


def cleanup_temp_file(path: Optional[str]):
    if not path:
        return
    try:
        os.remove(path)
    except OSError:
        pass


async def save_upload_to_temp(upload: UploadFile) -> str:
    suffix = os.path.splitext(upload.filename or "")[1]
    if not suffix:
        suffix = ".webm"
    tmp = NamedTemporaryFile(delete=False, suffix=suffix)
    try:
        content = await upload.read()
        if not content:
            raise HTTPException(status_code=400, detail="Empty audio file.")
        tmp.write(content)
    finally:
        tmp.close()
    return tmp.name


def run_vowel_analysis(audio_path: str, symbol: str):
    vowel_key = VOWEL_SYMBOL_TO_KEY[symbol]
    result, error = analyze_single_audio(audio_path, vowel_key, return_reason=True)
    if error:
        raise ValueError(error)
    ref_table = STANDARD_MALE_FORMANTS if result.get("gender") == "Male" else STANDARD_FEMALE_FORMANTS
    plot_url = None
    try:
        f1_val = result.get("f1")
        f2_val = result.get("f2")
        gender_guess = result.get("gender")
        if f1_val and f2_val and gender_guess:
            filename = f"{uuid4().hex}.png"
            abs_path = os.path.join(PLOT_OUTPUT_DIR, filename)
            plot_single_vowel_space(f1_val, f2_val, vowel_key, gender_guess, abs_path)
            plot_url = "/" + abs_path.replace(os.sep, "/")
    except Exception:
        plot_url = None
    return {
        "analysis_type": "vowel",
        "score": _safe_float(result.get("score")),
        "feedback": result.get("feedback"),
        "details": {
            "symbol": symbol,
            "vowel_key": vowel_key,
            "gender": result.get("gender"),
            "formants": {
                "f0": _safe_float(result.get("f0")),
                "f1": _safe_float(result.get("f1")),
                "f2": _safe_float(result.get("f2")),
                "f3": _safe_float(result.get("f3")),
            },
            "quality_hint": result.get("quality_hint"),
            "reference": {
                "f1": _safe_float(ref_table.get(vowel_key, {}).get("f1")),
                "f1_sd": _safe_float(ref_table.get(vowel_key, {}).get("f1_sd")),
                "f2": _safe_float(ref_table.get(vowel_key, {}).get("f2")),
                "f2_sd": _safe_float(ref_table.get(vowel_key, {}).get("f2_sd")),
                "f3": _safe_float(ref_table.get(vowel_key, {}).get("f3")),
            },
            "plot_url": plot_url,
        },
    }


def run_consonant_analysis(audio_path: str, symbol: str):
    syllable = CONSONANT_SYMBOL_TO_SYLLABLE[symbol]
    info = consonant_analysis.reference.get(syllable)
    if info is None:
        raise ValueError(f"{symbol} ({syllable}) is not supported.")

    tmp_out = NamedTemporaryFile(delete=False, suffix=".wav")
    try:
        wav_path = tmp_out.name
    finally:
        tmp_out.close()

    try:
        if not convert_to_wav(audio_path, wav_path):
            raise ValueError("Audio conversion failed.")

        snd, y, sr = consonant_analysis.load_sound(wav_path)
        measured_feats = consonant_analysis.extract_features_for_syllable(snd, y, sr, syllable, info)
        vot_for_pitch = measured_feats.get("VOT_ms")
        f0_est, sex_guess = consonant_analysis.estimate_speaker_f0_and_sex(
            wav_path=wav_path,
            vot_ms=vot_for_pitch
        )
        sex_for_scoring = sex_guess if sex_guess != "unknown" else "female"
        per_feature_report, overall_score, advice_list = consonant_analysis.score_against_reference(
            measured_feats,
            info["features"],
            sex_for_scoring
        )

        features_serialized = {
            name: {k: _safe_float(v) for k, v in data.items()}
            for name, data in per_feature_report.items()
        }
        measured_serialized = {k: _safe_float(v) for k, v in measured_feats.items()}
        extras = {}
        if "burst_dB" in measured_feats:
            extras["burst_dB"] = _safe_float(measured_feats["burst_dB"])

        score = _safe_float(overall_score) or 0.0
        feedback_text = " ".join(advice_list) if advice_list else info.get("coaching")

        return {
            "analysis_type": "consonant",
            "score": score,
            "feedback": feedback_text,
            "details": {
                "symbol": symbol,
                "syllable": syllable,
                "gender": sex_guess,
                "f0": _safe_float(f0_est),
                "features": features_serialized,
                "advice_list": advice_list,
                "coaching": info.get("coaching"),
                "measured": measured_serialized,
                "extras": extras,
            },
        }
    finally:
        cleanup_temp_file(wav_path)


async def analyse_uploaded_audio(audio: UploadFile, symbol: str):
    analysis_kind = resolve_sound_symbol(symbol)
    temp_path = await save_upload_to_temp(audio)
    try:
        if analysis_kind == "vowel":
            return await run_in_threadpool(run_vowel_analysis, temp_path, symbol)
        return await run_in_threadpool(run_consonant_analysis, temp_path, symbol)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    finally:
        cleanup_temp_file(temp_path)


def normalise_score(score_value) -> int:
    try:
        return max(0, min(100, int(round(float(score_value)))))
    except (TypeError, ValueError):
        return 0


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
            user_id = user[0]
            username = user[1]
            # Check if calibration is complete (has all 3 sounds: 'a', 'e', 'u')
            cur.execute("SELECT COUNT(DISTINCT sound) FROM formants WHERE userid = %s AND sound IN ('a', 'e', 'u')", (user_id,))
            cal_count = cur.fetchone()[0] or 0
            calibration_complete = (cal_count >= 3)
    return {"ok": True, "message": "Login successful", "user": username, "userid": user_id, "calibration_complete": calibration_complete}


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


@app.get("/api/formants")
async def get_formants(userid: int):
    with connect(DB_URL, sslmode="require") as conn:
        with conn.cursor() as cur:
            # Verify user exists
            cur.execute("SELECT id FROM users WHERE id = %s", (userid,))
            if cur.fetchone() is None:
                raise HTTPException(status_code=404, detail="User not found")
            
            # Get formants for all sounds for this user
            cur.execute(
                "SELECT sound, f1_mean, f1_std, f2_mean, f2_std FROM formants WHERE userid = %s",
                (userid,)
            )
            items = cur.fetchall() or []
            
            # Format as dictionary: { sound: { f1_mean, f1_std, f2_mean, f2_std }, ... }
            result = {}
            for row in items:
                sound = row[0].strip() if row[0] else None
                if sound:
                    result[sound] = {
                        "f1_mean": float(row[1]) if row[1] is not None else None,
                        "f1_std": float(row[2]) if row[2] is not None else None,
                        "f2_mean": float(row[3]) if row[3] is not None else None,
                        "f2_std": float(row[4]) if row[4] is not None else None
                    }
    
    return {"userid": userid, "formants": result}


# Removed /api/update-progress - progress is now updated in the analysis endpoints


@app.post("/api/calibration")
async def calibration_upload(
    audio: UploadFile,
    sound: Annotated[str, Form()],
    userid: Annotated[int, Form()]
):
    if not audio.filename:
        raise HTTPException(status_code=400, detail="No audio file provided.")
    
    # Validate sound is one of the expected calibration sounds
    if sound not in ['a', 'e', 'u']:
        raise HTTPException(status_code=400, detail="Invalid calibration sound. Expected: 'a', 'e', or 'u'")
    
    # TODO: Store calibration audio file for this user
    # For now, store a record that calibration was completed for this sound
    # You may want to save the actual audio file to disk or store as blob
    with connect(DB_URL, sslmode="require") as conn:
        with conn.cursor() as cur:
            # Check if user exists
            cur.execute("SELECT id FROM users WHERE id = %s", (userid,))
            if cur.fetchone() is None:
                raise HTTPException(status_code=404, detail="User not found")
            
            # Read audio file content
            audio_content = await audio.read()

            #TODO: analyze the recording and get the formants
            f1mean = 500
            f2mean = 1500
            f1std = 100
            f2std = 200
            
            # Upsert calibration record
            # Note: If table has constraint, use ON CONFLICT; otherwise use DELETE + INSERT
            cur.execute("DELETE FROM formants WHERE userid = %s AND sound = %s", (userid, sound))
            cur.execute(
                "INSERT INTO formants (userid, sound, f1_mean, f2_mean, f1_std, f2_std) VALUES (%s, %s, %s, %s, %s, %s)",
                (userid, sound, f1mean, f2mean, f1std, f2std)
            )
            conn.commit()
    
    return {
        "ok": True,
        "message": f"Calibration recording for '{sound}' saved",
        "sound": sound,
        "userid": userid
    }


@app.post("/api/analyze-sound")
async def analyze_sound(
    audio: UploadFile,
    userid: Annotated[int, Form()],
    sound: Annotated[str, Form()]
):
    if not audio.filename:
        raise HTTPException(status_code=400, detail="No audio file provided.")

    # Validate user exists
    with connect(DB_URL, sslmode="require") as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM users WHERE id = %s", (userid,))
            if cur.fetchone() is None:
                raise HTTPException(status_code=404, detail="User not found")

    analysis_result = await analyse_uploaded_audio(audio, sound.strip())
    score_value = normalise_score(analysis_result.get("score"))

    # Update progress in database with the analysis result
    with connect(DB_URL, sslmode="require") as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE progress SET progress = GREATEST(progress, %s) WHERE userid = %s AND sound = %s",
                (score_value, userid, sound)
            )
            if cur.rowcount == 0:
                # Insert if no existing row
                cur.execute(
                    "INSERT INTO progress (userid, sound, progress) VALUES (%s, %s, %s)",
                    (userid, sound, score_value)
                )
            conn.commit()

    return {
        "userid": userid,
        "sound": sound,
        "analysis_type": analysis_result.get("analysis_type"),
        "score": score_value,
        "result": score_value,
        "feedback": analysis_result.get("feedback"),
        "details": analysis_result.get("details"),
    }


@app.post("/api/analyze-sound-guest")
async def analyze_sound_guest(
    audio: UploadFile,
    sound: Annotated[str, Form()]
):
    if not audio.filename:
        raise HTTPException(status_code=400, detail="No audio file provided.")

    analysis_result = await analyse_uploaded_audio(audio, sound.strip())
    score_value = normalise_score(analysis_result.get("score"))

    return {
        "sound": sound,
        "analysis_type": analysis_result.get("analysis_type"),
        "score": score_value,
        "result": score_value,
        "feedback": analysis_result.get("feedback"),
        "details": analysis_result.get("details"),
    }

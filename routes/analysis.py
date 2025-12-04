"""
KoSPA Analysis Routes
=====================
Sound analysis and calibration API endpoints.

Endpoints:
- POST /api/calibration        : Save user calibration recording
- POST /api/analyze-sound      : Analyze sound for logged-in user
- POST /api/analyze-sound-guest: Analyze sound without login

These endpoints handle audio file uploads and return detailed
pronunciation analysis with scores and feedback.
"""

from typing import Annotated

from fastapi import APIRouter, UploadFile, Form, HTTPException

from database import (
    user_exists,
    save_calibration,
    update_progress,
)
from utils import (
    analyse_uploaded_audio,
    normalise_score,
    save_upload_to_temp,
    cleanup_temp_file,
    run_vowel_analysis,
)


# Initialize router
router = APIRouter(prefix="/api", tags=["Analysis"])


# =============================================================================
# CALIBRATION ENDPOINT
# =============================================================================

@router.post("/calibration")
async def calibration_upload(
    audio: UploadFile,
    sound: Annotated[str, Form()],
    userid: Annotated[int, Form()]
):
    """
    Save calibration recording for personalized analysis.

    Calibration captures the user's voice characteristics for
    better scoring accuracy. Requires 3 sounds: 'a', 'e', 'u'.

    Args:
        audio: Audio file (webm/wav)
        sound: Calibration sound ('a', 'e', or 'u')
        userid: User's database ID

    Returns:
        - ok: Success status
        - message: Status message
        - sound: The calibration sound
        - userid: User ID

    Raises:
        HTTPException 400: If no audio or invalid sound
        HTTPException 404: If user not found
    """
    if not audio.filename:
        raise HTTPException(status_code=400, detail="No audio file provided.")

    # Validate calibration sound
    if sound not in ['a', 'e', 'u']:
        raise HTTPException(
            status_code=400,
            detail="Invalid calibration sound. Expected: 'a', 'e', or 'u'"
        )

    # Verify user exists
    if not user_exists(userid):
        raise HTTPException(status_code=404, detail="User not found")

    # Save to temporary file
    temp_audio = await save_upload_to_temp(audio)

    try:
        # Convert sound symbol to vowel key
        # 'a' -> 'a (아)', 'e' -> 'eo (어)', 'u' -> 'o (오)'
        # Note: 'e' is mapped to 'eo' and 'u' to 'o' for backward compatibility
        sound_map = {
            'a': 'a (아)',
            'e': 'eo (어)',  # 'e' represents 'ㅓ' (eo)
            'u': 'o (오)',   # 'u' represents 'ㅗ' (o)
        }
        vowel_key = sound_map.get(sound)

        # Run vowel analysis to extract actual formants
        # Note: We use the symbol directly without error checking since we validated it
        symbol_map = {'a': 'ㅏ', 'e': 'ㅓ', 'u': 'ㅗ'}
        symbol = symbol_map.get(sound)
        result = run_vowel_analysis(temp_audio, symbol)

        if result.get('error'):
            raise HTTPException(
                status_code=422,
                detail=f"Calibration analysis failed: {result['error']}"
            )

        # Extract formant values from analysis
        details = result.get('details', {})
        formants = details.get('formants', {})

        f1_mean = formants.get('f1', 500)  # fallback to 500 if missing
        f2_mean = formants.get('f2', 1500)  # fallback to 1500 if missing

        # Use conservative standard deviations for calibration
        # (will be refined if we collect multiple samples per vowel)
        f1_std = 80
        f2_std = 120

        # Save calibration data
        save_calibration(userid, sound, f1_mean, f2_mean, f1_std, f2_std)

        return {
            "ok": True,
            "message": f"Calibration recording for '{sound}' saved",
            "sound": sound,
            "userid": userid,
            "measured": {
                "f1": round(f1_mean, 1),
                "f2": round(f2_mean, 1),
                "gender": details.get('gender', 'Unknown'),
                "f0": round(formants.get('f0', 0), 1) if formants.get('f0') else None
            }
        }

    finally:
        # Clean up temporary file
        cleanup_temp_file(temp_audio)


# =============================================================================
# ANALYSIS ENDPOINTS
# =============================================================================

@router.post("/analyze-sound")
async def analyze_sound(
    audio: UploadFile,
    userid: Annotated[int, Form()],
    sound: Annotated[str, Form()]
):
    """
    Analyze pronunciation for a logged-in user.

    Performs acoustic analysis and updates user's progress
    if the new score is higher than their previous best.

    Args:
        audio: Audio file (webm/wav)
        userid: User's database ID
        sound: Hangul symbol being analyzed (e.g., 'ㅏ', 'ㄱ')

    Returns:
        - userid: User ID
        - sound: The analyzed sound
        - analysis_type: 'vowel' or 'consonant'
        - score: Normalized score (0-100)
        - feedback: Text feedback
        - details: Detailed analysis data

    Raises:
        HTTPException 400: If no audio provided
        HTTPException 404: If user not found
        HTTPException 422: If analysis fails
    """
    if not audio.filename:
        raise HTTPException(status_code=400, detail="No audio file provided.")

    # Verify user exists
    if not user_exists(userid):
        raise HTTPException(status_code=404, detail="User not found")

    # Perform analysis (with personalization if calibration complete)
    analysis_result = await analyse_uploaded_audio(audio, sound.strip(), userid=userid)
    score_value = normalise_score(analysis_result.get("score"))

    # Update user's progress (keeps highest score)
    update_progress(userid, sound, score_value)

    return {
        "userid": userid,
        "sound": sound,
        "analysis_type": analysis_result.get("analysis_type"),
        "score": score_value,
        "result": score_value,
        "feedback": analysis_result.get("feedback"),
        "details": analysis_result.get("details"),
    }


@router.post("/analyze-sound-guest")
async def analyze_sound_guest(
    audio: UploadFile,
    sound: Annotated[str, Form()]
):
    """
    Analyze pronunciation without user login.

    Same analysis as /analyze-sound but doesn't save progress.
    Useful for demo/trial purposes.

    Args:
        audio: Audio file (webm/wav)
        sound: Hangul symbol being analyzed (e.g., 'ㅏ', 'ㄱ')

    Returns:
        - sound: The analyzed sound
        - analysis_type: 'vowel' or 'consonant'
        - score: Normalized score (0-100)
        - feedback: Text feedback
        - details: Detailed analysis data

    Raises:
        HTTPException 400: If no audio provided
        HTTPException 422: If analysis fails
    """
    if not audio.filename:
        raise HTTPException(status_code=400, detail="No audio file provided.")

    # Perform analysis
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

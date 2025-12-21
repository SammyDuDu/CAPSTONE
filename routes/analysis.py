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
    save_calibration_sample,
    get_calibration_samples,
    finalize_calibration_sound,
    get_calibration_count,
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
    userid: Annotated[int, Form()],
    sample_num: Annotated[int, Form()] = 1
):
    """
    Save calibration recording for personalized analysis.

    Calibration captures the user's voice characteristics for
    better scoring accuracy. Requires 2 sounds with 3 samples each:
    'i' (ㅣ) - front-high vowel, 'u' (ㅜ) - back-high vowel

    These two extreme vowels provide robust vocal tract scaling estimation.

    Args:
        audio: Audio file (webm/wav)
        sound: Calibration sound ('a', 'i', 'u', 'eo', 'e')
        userid: User's database ID
        sample_num: Sample number (1, 2, or 3)

    Returns:
        - ok: Success status
        - message: Status message
        - sound: The calibration sound
        - sample_num: Current sample number
        - samples_completed: Number of samples for this sound
        - sound_complete: Whether all 3 samples collected
        - calibration_complete: Whether all 5 sounds calibrated
        - measured: Formant measurements

    Raises:
        HTTPException 400: If no audio or invalid sound
        HTTPException 404: If user not found
    """
    if not audio.filename:
        raise HTTPException(status_code=400, detail="No audio file provided.")

    # Validate calibration sound (2 extreme vowels for robust scaling)
    valid_sounds = ['i', 'u']  # ㅣ (front-high) and ㅜ (back-high)
    if sound not in valid_sounds:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid calibration sound. Expected one of: {valid_sounds}"
        )

    # Validate sample number
    if sample_num not in [1, 2, 3]:
        raise HTTPException(
            status_code=400,
            detail="Invalid sample number. Expected: 1, 2, or 3"
        )

    # Verify user exists
    if not user_exists(userid):
        raise HTTPException(status_code=404, detail="User not found")

    # Save to temporary file
    temp_audio = await save_upload_to_temp(audio)

    try:
        # Map sound codes to vowel keys and symbols (2 calibration vowels)
        sound_map = {
            'i': ('i (이)', 'ㅣ'),   # Front-high (highest F2)
            'u': ('u (우)', 'ㅜ'),   # Back-high (lowest F2)
        }
        vowel_key, symbol = sound_map.get(sound)

        # Run vowel analysis to extract formants
        result = run_vowel_analysis(temp_audio, symbol)

        if result.get('error'):
            raise HTTPException(
                status_code=422,
                detail=f"Calibration analysis failed: {result['error']}"
            )

        # Extract formant values
        details = result.get('details', {})
        formants = details.get('formants', {})

        f1 = formants.get('f1')
        f2 = formants.get('f2')
        f0 = formants.get('f0')  # Pitch

        if f1 is None or f2 is None:
            raise HTTPException(
                status_code=422,
                detail="Could not extract formants. Please try again with clearer audio."
            )

        # Save this sample (including F0)
        save_calibration_sample(userid, sound, sample_num, f1, f2, f0)

        # Check how many samples we have for this sound
        samples = get_calibration_samples(userid, sound)
        samples_completed = len(samples)
        sound_complete = samples_completed >= 3

        # If we have 3 samples, finalize this sound's calibration
        final_stats = None
        if sound_complete:
            final_stats = finalize_calibration_sound(userid, sound)

        # Check overall calibration progress (need 2 sounds: i and u)
        calibration_count = get_calibration_count(userid)
        calibration_complete = calibration_count >= 2

        return {
            "ok": True,
            "message": f"Sample {sample_num} for '{sound}' saved",
            "sound": sound,
            "sample_num": sample_num,
            "samples_completed": samples_completed,
            "sound_complete": sound_complete,
            "calibration_count": calibration_count,
            "calibration_complete": calibration_complete,
            "userid": userid,
            "measured": {
                "f1": round(f1, 1),
                "f2": round(f2, 1),
                "gender": details.get('gender', 'Unknown'),
                "f0": round(formants.get('f0', 0), 1) if formants.get('f0') else None
            },
            "final_stats": final_stats  # Mean/SD if sound complete
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

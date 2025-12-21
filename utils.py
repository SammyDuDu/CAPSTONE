"""
KoSPA Utilities Module
======================
Common utility functions for audio processing and data handling.

This module provides:
- File handling utilities
- Audio processing helpers
- Data type conversions
- Analysis orchestration

Usage:
    from utils import save_upload_to_temp, normalise_score, analyse_uploaded_audio
"""

import os
from tempfile import NamedTemporaryFile
from typing import Optional
from uuid import uuid4

from fastapi import UploadFile, HTTPException
from fastapi.concurrency import run_in_threadpool

from config import (
    VOWEL_SYMBOL_TO_KEY,
    CONSONANT_SYMBOL_TO_SYLLABLE,
    PLOT_OUTPUT_DIR,
)
from analysis import consonant as consonant_analysis
from analysis.stops import analyze_stop, STOP_SET, F0Calibration
from database import get_user_formants  # 너희 DB 모듈에 이 함수가 있다고 했었지

from analysis.vowel_v2 import (
    analyze_single_audio,
    convert_to_wav,
    STANDARD_MALE_FORMANTS,
    STANDARD_FEMALE_FORMANTS,
    plot_single_vowel_space,
)


# =============================================================================
# TYPE CONVERSION UTILITIES
# =============================================================================

def safe_float(value) -> Optional[float]:
    """
    Safely convert a value to float.

    Args:
        value: Any value to convert

    Returns:
        Float value or None if conversion fails
    """
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return value


def normalise_score(score_value) -> int:
    """
    Normalize a score to 0-100 range.

    Args:
        score_value: Raw score value

    Returns:
        Integer score clamped between 0 and 100
    """
    try:
        return max(0, min(100, int(round(float(score_value)))))
    except (TypeError, ValueError):
        return 0


# =============================================================================
# FILE HANDLING UTILITIES
# =============================================================================

def cleanup_temp_file(path: Optional[str]) -> None:
    """
    Safely delete a temporary file.

    Args:
        path: File path to delete (can be None)
    """
    if not path:
        return
    try:
        os.remove(path)
    except OSError:
        pass


async def save_upload_to_temp(upload: UploadFile) -> str:
    """
    Save an uploaded file to a temporary location.

    Args:
        upload: FastAPI UploadFile object

    Returns:
        Path to the temporary file

    Raises:
        HTTPException: If the uploaded file is empty
    """
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


# =============================================================================
# SOUND SYMBOL UTILITIES
# =============================================================================

def resolve_sound_symbol(symbol: str) -> str:
    """
    Determine if a Hangul symbol is a vowel or consonant.

    Args:
        symbol: Hangul jamo character

    Returns:
        'vowel' or 'consonant'

    Raises:
        HTTPException: If symbol is not supported
    """
    if symbol in VOWEL_SYMBOL_TO_KEY:
        return "vowel"
    if symbol in CONSONANT_SYMBOL_TO_SYLLABLE:
        return "consonant"
    raise HTTPException(
        status_code=400,
        detail=f"Unsupported sound symbol: {symbol}"
    )


# =============================================================================
# ANALYSIS FUNCTIONS
# =============================================================================

def run_vowel_analysis(audio_path: str, symbol: str, userid: int = None) -> dict:
    """
    Perform vowel formant analysis on an audio file.

    Analyzes F1, F2, F3 formants and compares against reference values.
    Uses personalized reference if user has completed calibration.
    Generates a vowel space plot if analysis is successful.

    **NEW**: Supports diphthong trajectory analysis (wa, weo, wi, ya, yeo, ui, eui)

    Args:
        audio_path: Path to the audio file
        symbol: Hangul vowel symbol (e.g., 'ㅏ', 'ㅘ')
        userid: Optional user ID for personalized analysis

    Returns:
        Analysis result dictionary containing:
        - analysis_type: 'vowel'
        - score: 0-100 score
        - feedback: Text feedback
        - details: Detailed formant data and plot URL
          - For diphthongs: includes trajectory, start_score, end_score, direction_score

    Raises:
        ValueError: If analysis fails
    """
    from personalization import get_personalized_reference
    from config import DIPHTHONG_TRAJECTORIES
    from analysis.vowel_v2 import extract_formant_trajectory, score_diphthong_trajectory

    vowel_key = VOWEL_SYMBOL_TO_KEY[symbol]

    # Determine if this is a diphthong
    is_diphthong = vowel_key in DIPHTHONG_TRAJECTORIES

    # For diphthongs, skip monophthong analysis and go straight to trajectory
    if is_diphthong:
        # Use default gender (will be estimated from formants later if needed)
        gender = "Female"  # Default, can be refined

        # Try to get personalized reference for this user
        personalized_ref = None
        if userid:
            personalized_ref = get_personalized_reference(userid, gender)

        ref_table = personalized_ref if personalized_ref else STANDARD_FEMALE_FORMANTS
    else:
        # First pass: analyze with standard reference to get gender (monophthongs only)
        result, error = analyze_single_audio(audio_path, vowel_key, return_reason=True)

        if error:
            raise ValueError(error)

        gender = result.get("gender", "Female")

        # Try to get personalized reference for this user (for monophthongs)
        personalized_ref = None
        if userid:
            personalized_ref = get_personalized_reference(userid, gender)

        # Get reference table for analysis
        # Use personalized reference if available, otherwise use standard
        if personalized_ref:
            ref_table = personalized_ref
        else:
            ref_table = (
                STANDARD_MALE_FORMANTS
                if gender == "Male"
                else STANDARD_FEMALE_FORMANTS
            )

    # === DIPHTHONG TRAJECTORY ANALYSIS ===
    if is_diphthong:
        # Extract time-series formant trajectory
        traj_result = extract_formant_trajectory(audio_path)

        if not traj_result.get('success'):
            error_msg = traj_result.get('error', 'Trajectory extraction failed')
            raise ValueError(error_msg)

        # Score the trajectory
        score_result = score_diphthong_trajectory(
            traj_result['trajectory'],
            vowel_key,
            ref_table
        )

        # Extract trajectory data for response
        trajectory_list = traj_result['trajectory']
        start_formants = score_result['details']['start']
        end_formants = score_result['details']['end']

        # Generate vowel space plot (use middle point for gender estimation)
        plot_url = None
        try:
            mid_idx = len(trajectory_list) // 2
            mid_f1 = trajectory_list[mid_idx]['f1']
            mid_f2 = trajectory_list[mid_idx]['f2']

            filename = f"{uuid4().hex}.png"
            abs_path = os.path.join(PLOT_OUTPUT_DIR, filename)
            plot_single_vowel_space(mid_f1, mid_f2, vowel_key, gender, abs_path)
            plot_url = "/" + abs_path.replace(os.sep, "/")
        except Exception:
            plot_url = None

        # Get start/end vowel reference data for frontend rendering
        start_vowel_key = DIPHTHONG_TRAJECTORIES[vowel_key]['start']
        end_vowel_key = DIPHTHONG_TRAJECTORIES[vowel_key]['end']

        start_ref_data = ref_table.get(start_vowel_key, {})
        end_ref_data = ref_table.get(end_vowel_key, {})

        # Return diphthong analysis result
        return {
            "analysis_type": "vowel",
            "score": safe_float(score_result['score']),
            "feedback": "\n".join(score_result['feedback']),
            "details": {
                "symbol": symbol,
                "vowel_key": vowel_key,
                "gender": gender,
                "is_diphthong": True,
                "trajectory": {
                    "points": trajectory_list,
                    "duration": traj_result['duration'],
                    "num_frames": traj_result['num_frames'],
                },
                "scores": {
                    "total": safe_float(score_result['score']),
                    "start": safe_float(score_result['start_score']),
                    "end": safe_float(score_result['end_score']),
                    "direction": safe_float(score_result['direction_score']),
                },
                "formants": {
                    "start_f1": safe_float(start_formants['f1']),
                    "start_f2": safe_float(start_formants['f2']),
                    "end_f1": safe_float(end_formants['f1']),
                    "end_f2": safe_float(end_formants['f2']),
                },
                "reference": {
                    "start_vowel": start_vowel_key,
                    "end_vowel": end_vowel_key,
                    "direction": DIPHTHONG_TRAJECTORIES[vowel_key]['direction'],
                },
                # Start/End reference points with formants and SD for frontend ellipse drawing
                "start_ref": {
                    "f1": safe_float(start_ref_data.get('f1')),
                    "f2": safe_float(start_ref_data.get('f2')),
                    "f1_sd": safe_float(start_ref_data.get('f1_sd')),
                    "f2_sd": safe_float(start_ref_data.get('f2_sd')),
                    "label": start_vowel_key.split(' ')[0],  # e.g., "o" from "o (오)"
                },
                "end_ref": {
                    "f1": safe_float(end_ref_data.get('f1')),
                    "f2": safe_float(end_ref_data.get('f2')),
                    "f1_sd": safe_float(end_ref_data.get('f1_sd')),
                    "f2_sd": safe_float(end_ref_data.get('f2_sd')),
                    "label": end_vowel_key.split(' ')[0],  # e.g., "a" from "a (아)"
                },
                "plot_url": plot_url,
            },
        }

    # === MONOPHTHONG ANALYSIS (existing logic) ===
    # Second pass: re-analyze with personalized reference if available
    if personalized_ref:
        result, error = analyze_single_audio(
            audio_path,
            vowel_key,
            return_reason=True,
            custom_ref_table=personalized_ref
        )
        if error:
            raise ValueError(error)

    # Generate vowel space plot
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
        "score": safe_float(result.get("score")),
        "feedback": result.get("feedback"),
        "details": {
            "symbol": symbol,
            "vowel_key": vowel_key,
            "gender": result.get("gender"),
            "formants": {
                "f0": safe_float(result.get("f0")),
                "f1": safe_float(result.get("f1")),
                "f2": safe_float(result.get("f2")),
                "f3": safe_float(result.get("f3")),
            },
            "quality_hint": result.get("quality_hint"),
            "reference": {
                "f1": safe_float(ref_table.get(vowel_key, {}).get("f1")),
                "f1_sd": safe_float(ref_table.get(vowel_key, {}).get("f1_sd")),
                "f2": safe_float(ref_table.get(vowel_key, {}).get("f2")),
                "f2_sd": safe_float(ref_table.get(vowel_key, {}).get("f2_sd")),
                "f3": safe_float(ref_table.get(vowel_key, {}).get("f3")),
            },
            "plot_url": plot_url,
        },
    }

def run_consonant_analysis(audio_path: str, symbol: str, userid: int = None) -> dict:
    """
    Perform consonant acoustic analysis on an audio file.

    Uses the new modular consonant analysis system:
    - stops.py: VOT, F0z, F2 onset analysis for ㄱㄲㅋ, ㄷㄸㅌ, ㅂㅃㅍ
    - fricative.py: Spectral centroid, HF contrast for ㅅㅆㅎ
    - affricate.py: VOT, frication duration for ㅈㅉㅊ

    Args:
        audio_path: Path to the audio file
        symbol: Hangul consonant symbol (e.g., 'ㄱ')
        userid: Optional user ID for F0 calibration

    Returns:
        Analysis result dictionary containing:
        - analysis_type: 'consonant'
        - score: 0-100 score
        - feedback: Text feedback
        - details: Measured features, evaluation, and plot data

    Raises:
        ValueError: If analysis fails or consonant not supported
    """
    from analysis.consonant import analyze_consonant
    from analysis.stops import F0Calibration

    syllable = CONSONANT_SYMBOL_TO_SYLLABLE.get(symbol)
    if syllable is None:
        raise ValueError(f"Unknown consonant symbol: {symbol}")

    # Get F0 calibration data if user is logged in
    f0_calibration = None
    if userid:
        from database import get_user_formants
        user_formants = get_user_formants(userid)
        # Use average F0 from calibration vowels (i, u)
        f0_values = []
        for sound in ['i', 'u']:
            if sound in user_formants:
                f0_mean = user_formants[sound].get('f0_mean')
                f0_std = user_formants[sound].get('f0_std')
                if f0_mean is not None:
                    f0_values.append({'mean': f0_mean, 'std': f0_std})
        if f0_values:
            avg_f0_mean = sum(v['mean'] for v in f0_values) / len(f0_values)
            avg_f0_std = sum(v['std'] for v in f0_values if v['std']) / len([v for v in f0_values if v['std']]) if any(v['std'] for v in f0_values) else 20.0
            f0_calibration = F0Calibration(mean_hz=avg_f0_mean, sd_hz=avg_f0_std)

    # Create temporary WAV file for analysis
    tmp_out = NamedTemporaryFile(delete=False, suffix=".wav")
    try:
        wav_path = tmp_out.name
    finally:
        tmp_out.close()

    try:
        # Convert to WAV format
        if not convert_to_wav(audio_path, wav_path):
            raise ValueError("Audio conversion failed.")

        # Run new consonant analysis (stops/fricatives/affricates)
        result = analyze_consonant(wav_path=wav_path, syllable=syllable, f0_calibration=f0_calibration)

        if "error" in result:
            raise ValueError(result["error"])

        # Extract score and feedback
        evaluation = result.get("evaluation", {})
        score = safe_float(evaluation.get("final_score", 0))
        feedback_text = result.get("feedback", {}).get("text", "")

        # Return structured response for frontend
        return {
            "analysis_type": "consonant",
            "consonant_type": result.get("type", "unknown"),  # stop, fricative, affricate
            "score": score,
            "feedback": feedback_text,
            "details": {
                "type": result.get("type", "unknown"),  # For frontend plot rendering
                "symbol": symbol,
                "syllable": syllable,
                "targets": result.get("targets", {}),
                "features": result.get("features", {}),
                "evaluation": evaluation,
                "plots": evaluation.get("plots", {}),
            },
        }
    finally:
        cleanup_temp_file(wav_path)


async def analyse_uploaded_audio(audio: UploadFile, symbol: str, userid: int = None) -> dict:
    """
    Main entry point for analyzing uploaded audio.

    Determines the analysis type (vowel/consonant) and runs appropriate
    analysis in a thread pool to avoid blocking.

    Args:
        audio: Uploaded audio file
        symbol: Hangul symbol being analyzed
        userid: Optional user ID for personalized analysis

    Returns:
        Analysis result dictionary

    Raises:
        HTTPException: If analysis fails
    """
    analysis_kind = resolve_sound_symbol(symbol)
    temp_path = await save_upload_to_temp(audio)

    try:
        if analysis_kind == "vowel":
            return await run_in_threadpool(run_vowel_analysis, temp_path, symbol, userid)
        return await run_in_threadpool(run_consonant_analysis, temp_path, symbol, userid)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    finally:
        cleanup_temp_file(temp_path)

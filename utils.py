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

def run_vowel_analysis(audio_path: str, symbol: str) -> dict:
    """
    Perform vowel formant analysis on an audio file.

    Analyzes F1, F2, F3 formants and compares against reference values.
    Generates a vowel space plot if analysis is successful.

    Args:
        audio_path: Path to the audio file
        symbol: Hangul vowel symbol (e.g., 'ㅏ')

    Returns:
        Analysis result dictionary containing:
        - analysis_type: 'vowel'
        - score: 0-100 score
        - feedback: Text feedback
        - details: Detailed formant data and plot URL

    Raises:
        ValueError: If analysis fails
    """
    vowel_key = VOWEL_SYMBOL_TO_KEY[symbol]
    result, error = analyze_single_audio(audio_path, vowel_key, return_reason=True)

    if error:
        raise ValueError(error)

    # Get reference table based on detected gender
    ref_table = (
        STANDARD_MALE_FORMANTS
        if result.get("gender") == "Male"
        else STANDARD_FEMALE_FORMANTS
    )

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


def run_consonant_analysis(audio_path: str, symbol: str) -> dict:
    """
    Perform consonant acoustic analysis on an audio file.

    Analyzes features like VOT, frication, and nasal energy depending
    on the consonant type.

    Args:
        audio_path: Path to the audio file
        symbol: Hangul consonant symbol (e.g., 'ㄱ')

    Returns:
        Analysis result dictionary containing:
        - analysis_type: 'consonant'
        - score: 0-100 score
        - feedback: Text feedback
        - details: Measured features and reference comparisons

    Raises:
        ValueError: If analysis fails or consonant not supported
    """
    syllable = CONSONANT_SYMBOL_TO_SYLLABLE[symbol]
    info = consonant_analysis.reference.get(syllable)

    if info is None:
        raise ValueError(f"{symbol} ({syllable}) is not supported.")

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

        # Load and analyze audio
        snd, y, sr = consonant_analysis.load_sound(wav_path)
        measured_feats = consonant_analysis.extract_features_for_syllable(
            snd, y, sr, syllable, info
        )

        # Estimate speaker characteristics
        vot_for_pitch = measured_feats.get("VOT_ms")
        f0_est, sex_guess = consonant_analysis.estimate_speaker_f0_and_sex(
            wav_path=wav_path,
            vot_ms=vot_for_pitch
        )

        # Score against reference
        sex_for_scoring = sex_guess if sex_guess != "unknown" else "female"
        per_feature_report, overall_score, advice_list = consonant_analysis.score_against_reference(
            measured_feats,
            info["features"],
            sex_for_scoring
        )

        # Serialize results
        features_serialized = {
            name: {k: safe_float(v) for k, v in data.items()}
            for name, data in per_feature_report.items()
        }
        measured_serialized = {
            k: safe_float(v) for k, v in measured_feats.items()
        }

        extras = {}
        if "burst_dB" in measured_feats:
            extras["burst_dB"] = safe_float(measured_feats["burst_dB"])

        score = safe_float(overall_score) or 0.0
        feedback_text = " ".join(advice_list) if advice_list else info.get("coaching")

        return {
            "analysis_type": "consonant",
            "score": score,
            "feedback": feedback_text,
            "details": {
                "symbol": symbol,
                "syllable": syllable,
                "gender": sex_guess,
                "f0": safe_float(f0_est),
                "features": features_serialized,
                "advice_list": advice_list,
                "coaching": info.get("coaching"),
                "measured": measured_serialized,
                "extras": extras,
            },
        }
    finally:
        cleanup_temp_file(wav_path)


async def analyse_uploaded_audio(audio: UploadFile, symbol: str) -> dict:
    """
    Main entry point for analyzing uploaded audio.

    Determines the analysis type (vowel/consonant) and runs appropriate
    analysis in a thread pool to avoid blocking.

    Args:
        audio: Uploaded audio file
        symbol: Hangul symbol being analyzed

    Returns:
        Analysis result dictionary

    Raises:
        HTTPException: If analysis fails
    """
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

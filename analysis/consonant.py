# analysis/consonant.py
from __future__ import annotations
from typing import Optional, Dict, Any

from analysis.stops import analyze_stop, STOP_SET, F0Calibration
from analysis.fricative import analyze_fricative, FRICATIVE_SET
from analysis.affricate import analyze_affricate, AFFRICATE_SET

def analyze_consonant(
    wav_path: str,
    syllable: str,
    f0_calibration: Optional[F0Calibration] = None,
) -> Dict[str, Any]:
    """
    Consonant dispatcher.
    For now: stop consonants only.
    """
    if syllable in STOP_SET:
        return analyze_stop(wav_path=wav_path, syllable=syllable, f0_calibration=f0_calibration)
    elif syllable in FRICATIVE_SET:
         return analyze_fricative(wav_path=wav_path, syllable=syllable)
    elif syllable in AFFRICATE_SET:
        return analyze_affricate(wav_path=wav_path, syllable=syllable)
    # elif syllable in NASAL_SET:
    #     return analyze_nasal(wav_path=wav_path, syllable=syllable)
    # elif syllable in LIQUID_SET:
    #     return analyze_liquid(wav_path=wav_path, syllable=syllable)

    return {
        "type": "consonant",
    }

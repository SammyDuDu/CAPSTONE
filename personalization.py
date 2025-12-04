"""
Personalization Module
======================
Provides personalized formant reference values based on user calibration data.

This module adjusts standard formant targets to match each user's vocal characteristics,
improving pronunciation scoring accuracy.

Key Functions:
    - get_personalized_reference(): Returns adjusted formant targets for a user (scaling)
    - calculate_scaling_factors(): Computes scaling factors from calibration data
    - calibrate_affine(): Computes Affine transform F1,F2 → x,y (for diphthongs)
    - formants_to_articulatory(): Converts Hz formants to normalized (x,y)
"""

from typing import Dict, Optional, Tuple
import numpy as np
from database import get_user_formants
from analysis.vowel_v2 import STANDARD_MALE_FORMANTS, STANDARD_FEMALE_FORMANTS
from config import VOWEL_ARTICULATORY_MAP


def calculate_scaling_factors(
    user_calib: Dict[str, Dict[str, float]],
    standard_ref: Dict[str, Dict[str, float]]
) -> Tuple[float, float]:
    """
    Calculate F1 and F2 scaling factors from calibration data.

    Compares user's measured formants against standard references
    to determine how their vocal tract differs from the average.

    Args:
        user_calib: User calibration data
            {'a': {'f1_mean': 920, 'f2_mean': 1550, ...}, ...}
        standard_ref: Standard reference formants
            {'a (아)': {'f1': 945, 'f2': 1582, ...}, ...}

    Returns:
        (f1_scale, f2_scale): Scaling factors for F1 and F2
            Values typically range from 0.9 to 1.1

    Example:
        >>> user_calib = {'a': {'f1_mean': 930, 'f2_mean': 1550}}
        >>> standard = {'a (아)': {'f1': 945, 'f2': 1582}}
        >>> calculate_scaling_factors(user_calib, standard)
        (0.984, 0.980)
    """
    # Map calibration sounds to vowel keys
    # 'a' -> 'a (아)', 'e' -> 'eo (어)', 'u' -> 'o (오)'
    sound_to_key = {
        'a': 'a (아)',
        'e': 'eo (어)',
        'u': 'o (오)'
    }

    f1_ratios = []
    f2_ratios = []

    for sound, calib_data in user_calib.items():
        vowel_key = sound_to_key.get(sound)
        if not vowel_key or vowel_key not in standard_ref:
            continue

        std = standard_ref[vowel_key]

        # Calculate ratio: user_value / standard_value
        if calib_data.get('f1_mean') and std.get('f1'):
            f1_ratio = calib_data['f1_mean'] / std['f1']
            f1_ratios.append(f1_ratio)

        if calib_data.get('f2_mean') and std.get('f2'):
            f2_ratio = calib_data['f2_mean'] / std['f2']
            f2_ratios.append(f2_ratio)

    # Average the ratios
    f1_scale = sum(f1_ratios) / len(f1_ratios) if f1_ratios else 1.0
    f2_scale = sum(f2_ratios) / len(f2_ratios) if f2_ratios else 1.0

    # Clamp to reasonable range (0.85 - 1.15)
    # Prevents extreme adjustments from noisy calibration
    f1_scale = max(0.85, min(1.15, f1_scale))
    f2_scale = max(0.85, min(1.15, f2_scale))

    return f1_scale, f2_scale


def get_personalized_reference(
    userid: int,
    gender: str = "Female"
) -> Optional[Dict[str, Dict[str, float]]]:
    """
    Get personalized formant references for a user.

    Uses calibration data to adjust standard formant targets
    to match the user's vocal characteristics.

    Args:
        userid: User's database ID
        gender: "Male" or "Female" (determines base reference table)

    Returns:
        Personalized reference table (same structure as STANDARD_*_FORMANTS)
        or None if calibration is incomplete

    Process:
        1. Fetch user's calibration data from database
        2. Calculate global scaling factors
        3. Apply scaling to all vowels in standard reference
        4. Replace calibration vowels with actual measured values

    Example:
        >>> ref = get_personalized_reference(userid=123, gender="Female")
        >>> ref['a (아)']
        {'f1': 930, 'f2': 1550, 'f1_sd': 85, 'f2_sd': 138, ...}
    """
    # Fetch user calibration data
    user_calib = get_user_formants(userid)

    # Check if calibration is complete (need all 3: a, e, u)
    required_sounds = {'a', 'e', 'u'}
    if not user_calib or not required_sounds.issubset(user_calib.keys()):
        return None  # Calibration incomplete

    # Select base reference table
    standard_ref = (
        STANDARD_MALE_FORMANTS if gender == "Male"
        else STANDARD_FEMALE_FORMANTS
    )

    # Calculate scaling factors
    f1_scale, f2_scale = calculate_scaling_factors(user_calib, standard_ref)

    # Build personalized reference table
    personalized_ref = {}

    for vowel_key, ref_data in standard_ref.items():
        # Apply global scaling
        personalized_ref[vowel_key] = {
            'f1': ref_data['f1'] * f1_scale,
            'f2': ref_data['f2'] * f2_scale,
            'f3': ref_data.get('f3', 2700),  # F3 not personalized (less critical)
            'f1_sd': ref_data['f1_sd'] * f1_scale,
            'f2_sd': ref_data['f2_sd'] * f2_scale,
        }

    # Override with actual calibration values (more accurate)
    sound_to_key = {
        'a': 'a (아)',
        'e': 'eo (어)',
        'u': 'o (오)'
    }

    for sound, calib_data in user_calib.items():
        vowel_key = sound_to_key.get(sound)
        if vowel_key and vowel_key in personalized_ref:
            # Use measured values directly for calibration vowels
            personalized_ref[vowel_key]['f1'] = calib_data['f1_mean']
            personalized_ref[vowel_key]['f2'] = calib_data['f2_mean']
            personalized_ref[vowel_key]['f1_sd'] = calib_data['f1_std']
            personalized_ref[vowel_key]['f2_sd'] = calib_data['f2_std']

    return personalized_ref


def get_reference_for_user(userid: int, gender: str) -> Dict[str, Dict[str, float]]:
    """
    Get appropriate reference table for a user.

    Attempts to return personalized reference if calibration is complete,
    otherwise falls back to standard reference.

    Args:
        userid: User's database ID (0 or None for guest users)
        gender: "Male" or "Female"

    Returns:
        Reference formant table

    Usage:
        >>> ref = get_reference_for_user(userid=123, gender="Female")
        >>> # Use ref for scoring
        >>> score = compute_score(f1, f2, f3, 'a (아)', ref)
    """
    # Guest user or no userid -> use standard reference
    if not userid:
        return (
            STANDARD_MALE_FORMANTS if gender == "Male"
            else STANDARD_FEMALE_FORMANTS
        )

    # Try personalized reference
    personalized = get_personalized_reference(userid, gender)

    if personalized:
        return personalized

    # Fallback to standard
    return (
        STANDARD_MALE_FORMANTS if gender == "Male"
        else STANDARD_FEMALE_FORMANTS
    )


# =============================================================================
# AFFINE TRANSFORM (for Hybrid Coordinate System)
# =============================================================================

def calibrate_affine(
    user_calib: Dict[str, Dict[str, float]]
) -> Tuple[Optional[np.ndarray], Optional[np.ndarray]]:
    """
    Compute Affine transform matrix A and bias b for F1,F2 → x,y conversion.

    Solves: [x, y]ᵀ ≈ A · [F1, F2]ᵀ + b

    Args:
        user_calib: User calibration data
            {'a': {'f1_mean': 920, 'f2_mean': 1550, ...}, ...}

    Returns:
        (A, b): A is 2×2 matrix, b is 2×1 vector
        Returns (None, None) if calibration incomplete

    Example:
        >>> A, b = calibrate_affine(user_calib)
        >>> x, y = A @ [f1, f2] + b
    """
    # Need at least 3 calibration vowels for robust estimation
    sound_to_key = {
        'a': 'a (아)',
        'e': 'eo (어)',
        'u': 'o (오)'
    }

    F_matrix = []  # [[F1, F2], ...]
    X_matrix = []  # [[x, y], ...]

    for sound, calib_data in user_calib.items():
        vowel_key = sound_to_key.get(sound)
        if not vowel_key or vowel_key not in VOWEL_ARTICULATORY_MAP:
            continue

        target = VOWEL_ARTICULATORY_MAP[vowel_key]

        # User's measured formants
        f1 = calib_data.get('f1_mean')
        f2 = calib_data.get('f2_mean')

        if f1 is None or f2 is None:
            continue

        F_matrix.append([f1, f2])
        X_matrix.append([target['x'], target['y']])

    if len(F_matrix) < 3:
        return None, None  # Insufficient calibration

    # Convert to numpy arrays
    F = np.array(F_matrix)  # Shape: (n, 2)
    X = np.array(X_matrix)  # Shape: (n, 2)

    # Augment F with ones for bias: F_aug = [F1, F2, 1]
    F_aug = np.hstack([F, np.ones((len(F), 1))])  # Shape: (n, 3)

    # Solve X = F_aug @ params  =>  params = (F_augᵀ F_aug)⁻¹ F_augᵀ X
    params, _, _, _ = np.linalg.lstsq(F_aug, X, rcond=None)

    # Extract A and b
    A = params[:2, :].T  # Shape: (2, 2) - first 2 rows transposed
    b = params[2, :]     # Shape: (2,) - last row

    return A, b


def formants_to_articulatory(
    f1: float,
    f2: float,
    A: Optional[np.ndarray] = None,
    b: Optional[np.ndarray] = None
) -> Tuple[float, float]:
    """
    Convert formants (Hz) to articulatory coordinates (x, y).

    Args:
        f1, f2: Formant frequencies in Hz
        A, b: Affine transform parameters (if None, use generic transform)

    Returns:
        (x, y): Normalized coordinates in [0, 1] range
            x: front (0) ↔ back (1)
            y: low (0) ↔ high (1)

    Example:
        >>> x, y = formants_to_articulatory(700, 1800, A, b)
        >>> # (x, y) can be used for trajectory plot
    """
    F = np.array([f1, f2])

    if A is not None and b is not None:
        # Use personalized transform
        X = A @ F + b
    else:
        # Use generic transform (approximate)
        # Based on typical formant ranges:
        # F1: 200-1000 Hz (high → low)
        # F2: 500-3000 Hz (back → front)
        x = 1 - (f2 - 500) / (3000 - 500)  # Invert: high F2 = front = low x
        y = 1 - (f1 - 200) / (1000 - 200)  # Invert: high F1 = low = low y

        # Clamp to [0, 1]
        x = max(0, min(1, x))
        y = max(0, min(1, y))

        return x, y

    # Clamp to [0, 1]
    x = float(max(0, min(1, X[0])))
    y = float(max(0, min(1, X[1])))

    return x, y


def get_affine_transform_for_user(
    userid: int
) -> Tuple[Optional[np.ndarray], Optional[np.ndarray]]:
    """
    Get Affine transform for a specific user.

    Args:
        userid: User's database ID

    Returns:
        (A, b): Transform parameters, or (None, None) if calibration incomplete

    Usage:
        >>> A, b = get_affine_transform_for_user(userid=123)
        >>> x, y = formants_to_articulatory(f1, f2, A, b)
    """
    if not userid:
        return None, None

    user_calib = get_user_formants(userid)

    if not user_calib:
        return None, None

    return calibrate_affine(user_calib)


# =============================================================================
# EXAMPLE USAGE
# =============================================================================

if __name__ == "__main__":
    # Example 1: Calculate scaling for a user
    user_calibration = {
        'a': {'f1_mean': 930, 'f2_mean': 1550, 'f1_std': 85, 'f2_std': 140},
        'e': {'f1_mean': 565, 'f2_mean': 945, 'f1_std': 75, 'f2_std': 85},
        'u': {'f1_mean': 365, 'f2_mean': 690, 'f1_std': 25, 'f2_std': 70},
    }

    f1_scale, f2_scale = calculate_scaling_factors(
        user_calibration,
        STANDARD_FEMALE_FORMANTS
    )

    print(f"Scaling factors: F1={f1_scale:.3f}, F2={f2_scale:.3f}")
    print(f"User's F1 is {(f1_scale-1)*100:+.1f}% compared to standard")
    print(f"User's F2 is {(f2_scale-1)*100:+.1f}% compared to standard")

    # Example 2: Affine transform
    A, b = calibrate_affine(user_calibration)

    if A is not None:
        print(f"\nAffine transform matrix A:\n{A}")
        print(f"Bias vector b: {b}")

        # Test conversion
        x, y = formants_to_articulatory(930, 1550, A, b)
        print(f"\nF1=930, F2=1550 → x={x:.3f}, y={y:.3f}")
        print(f"  (Expected near 'a (아)' at x=0.5, y=0.2)")

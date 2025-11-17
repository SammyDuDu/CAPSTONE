"""
KoSPA Analysis Engine Configuration
Common constants and settings for vowel and consonant analysis engines.
"""

# Gender Detection
# F0 (pitch) threshold for male/female classification
# Based on typical adult Korean speaker pitch ranges:
#   - Male: ~100-150 Hz
#   - Female: ~180-250 Hz
#   - Boundary: 165 Hz (conservative estimate)
F0_GENDER_THRESHOLD = 165.0  # Hz

# Scoring Parameters
# Perfect score threshold (in standard deviations from reference)
PERFECT_SCORE_THRESHOLD = 1.5  # sigma

# Penalty per sigma beyond perfect threshold
PENALTY_PER_SIGMA = 60.0  # points

# Audio Quality Thresholds
MIN_SEGMENT_LENGTH = 0.08  # seconds
MIN_RMS_THRESHOLD = 0.01   # amplitude
MIN_SNR_RATIO = 1.5        # signal-to-noise ratio

# Consonant Analysis
MIN_FRICATION_DURATION_MS = 10.0  # milliseconds
MIN_CENTROID_HZ = 100.0           # Hz

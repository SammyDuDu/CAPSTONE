"""
KoSPA Configuration Module
==========================
Central configuration for the Korean Speech Pronunciation Analyzer.

This module contains:
- Environment variables and settings
- Korean character mapping tables
- Application constants

Usage:
    from config import DB_URL, VOWEL_SYMBOL_TO_KEY, PLOT_OUTPUT_DIR
"""

import os

# =============================================================================
# DATABASE CONFIGURATION
# =============================================================================

# Database URL from environment variable
# Falls back to Render PostgreSQL for backward compatibility
DB_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://capstone_itcd_user:2XLTwuuR3pJw4epFlT7lo71WnsmzuDFU@dpg-d411ot1r0fns739sc58g-a.singapore-postgres.render.com/capstone_itcd"
)

print(f"DEBUG: Using DB_URL: {DB_URL}")

# =============================================================================
# APPLICATION SETTINGS
# =============================================================================

# Directory for storing generated analysis plots
PLOT_OUTPUT_DIR = os.path.join("static", "images", "analysis")

# Ensure plot directory exists
os.makedirs(PLOT_OUTPUT_DIR, exist_ok=True)

# =============================================================================
# KOREAN CHARACTER MAPPINGS
# =============================================================================

# Vowel symbols to analysis keys
# Maps Hangul jamo to the format used by the vowel analysis engine
# All 21 Korean vowels supported
VOWEL_SYMBOL_TO_KEY: dict[str, str] = {
    # Basic 6 monophthongs (단모음)
    "ㅏ": "a (아)",    # 'ah' sound
    "ㅓ": "eo (어)",   # 'uh' sound
    "ㅗ": "o (오)",    # 'oh' sound
    "ㅜ": "u (우)",    # 'oo' sound
    "ㅡ": "eu (으)",   # unrounded 'u'
    "ㅣ": "i (이)",    # 'ee' sound

    # Y-vowels (ㅣ-모음계)
    "ㅑ": "ya (야)",   # 'ya' sound
    "ㅕ": "yeo (여)",  # 'yuh' sound
    "ㅛ": "yo (요)",   # 'yo' sound
    "ㅠ": "yu (유)",   # 'yu' sound

    # Front vowels (전설 모음)
    "ㅐ": "ae (애)",   # 'ae' sound (like 'cat')
    "ㅒ": "yae (얘)",  # 'yae' sound
    "ㅔ": "e (에)",    # 'eh' sound (like 'bed')
    "ㅖ": "ye (예)",   # 'yeh' sound

    # Complex/diphthong vowels (이중 모음)
    "ㅘ": "wa (와)",   # 'wa' sound
    "ㅙ": "wae (왜)",  # 'wae' sound
    "ㅚ": "oe (외)",   # 'oe' sound
    "ㅝ": "wo (워)",   # 'wo' sound
    "ㅞ": "we (웨)",   # 'we' sound
    "ㅟ": "wi (위)",   # 'wi' sound
    "ㅢ": "ui (의)",   # 'ui' sound
}

# Consonant symbols to syllable examples
# Maps Hangul jamo to example syllables for consonant analysis
CONSONANT_SYMBOL_TO_SYLLABLE: dict[str, str] = {
    # Plain consonants (예사소리)
    "ㄱ": "가",  # g/k
    "ㄴ": "나",  # n
    "ㄷ": "다",  # d/t
    "ㄹ": "라",  # r/l
    "ㅁ": "마",  # m
    "ㅂ": "바",  # b/p
    "ㅅ": "사",  # s
    "ㅈ": "자",  # j
    "ㅊ": "차",  # ch (aspirated)
    "ㅋ": "카",  # k (aspirated)
    "ㅌ": "타",  # t (aspirated)
    "ㅍ": "파",  # p (aspirated)
    "ㅎ": "하",  # h

    # Tense consonants (된소리)
    "ㄲ": "까",  # kk
    "ㄸ": "따",  # tt
    "ㅃ": "빠",  # pp
    "ㅆ": "싸",  # ss
    "ㅉ": "짜",  # jj
}

# =============================================================================
# SOUND DESCRIPTIONS
# =============================================================================

# Pronunciation guidance for each Hangul character
# Used in the sound.html template to help users
SOUND_DESCRIPTIONS: dict[str, str] = {
    # Vowels
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

    # Consonants
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

# =============================================================================
# ARTICULATORY COORDINATE SYSTEM (for Hybrid Plot)
# =============================================================================

# Normalized (x, y) coordinates for vowels in articulatory space
# x ∈ [0, 1]: front (0) ↔ back (1)
# y ∈ [0, 1]: low (0) ↔ high (1)
# Used for diphthong trajectory analysis and optional articulatory map display

VOWEL_ARTICULATORY_MAP: dict[str, dict] = {
    # Basic 6 monophthongs
    'i (이)':  {'x': 0.15, 'y': 0.90, 'rx': 0.08, 'ry': 0.08},  # front-high
    'e (에)':  {'x': 0.20, 'y': 0.70, 'rx': 0.10, 'ry': 0.10},  # front-mid-high
    'ae (애)': {'x': 0.25, 'y': 0.55, 'rx': 0.12, 'ry': 0.12},  # front-mid (wider zone)
    'a (아)':  {'x': 0.50, 'y': 0.20, 'rx': 0.10, 'ry': 0.10},  # central-low
    'eo (어)': {'x': 0.70, 'y': 0.50, 'rx': 0.10, 'ry': 0.10},  # back-mid
    'o (오)':  {'x': 0.80, 'y': 0.45, 'rx': 0.10, 'ry': 0.10},  # back-mid-round
    'u (우)':  {'x': 0.90, 'y': 0.85, 'rx': 0.08, 'ry': 0.08},  # back-high-round
    'eu (으)': {'x': 0.60, 'y': 0.75, 'rx': 0.10, 'ry': 0.10},  # central-high

    # Y-vowels (front shifted versions)
    'ya (야)':  {'x': 0.45, 'y': 0.25, 'rx': 0.10, 'ry': 0.10},  # like 'a' but fronter
    'yeo (여)': {'x': 0.65, 'y': 0.55, 'rx': 0.10, 'ry': 0.10},  # like 'eo' but fronter
    'yo (요)':  {'x': 0.75, 'y': 0.50, 'rx': 0.10, 'ry': 0.10},  # like 'o' but fronter
    'yu (유)':  {'x': 0.85, 'y': 0.80, 'rx': 0.08, 'ry': 0.08},  # like 'u' but fronter

    'yae (얘)': {'x': 0.22, 'y': 0.60, 'rx': 0.12, 'ry': 0.12},  # like 'ae' fronter
    'ye (예)':  {'x': 0.18, 'y': 0.75, 'rx': 0.10, 'ry': 0.10},  # like 'e' fronter

    # Complex/diphthong vowels (approximate centers for single-point fallback)
    'wa (와)':  {'x': 0.65, 'y': 0.30, 'rx': 0.12, 'ry': 0.12},  # o→a trajectory
    'wae (왜)': {'x': 0.55, 'y': 0.45, 'rx': 0.12, 'ry': 0.12},  # o→ae
    'oe (외)':  {'x': 0.50, 'y': 0.60, 'rx': 0.12, 'ry': 0.12},  # o→e (merged with 'we')
    'wo (워)':  {'x': 0.80, 'y': 0.50, 'rx': 0.12, 'ry': 0.12},  # u→eo
    'we (웨)':  {'x': 0.50, 'y': 0.60, 'rx': 0.12, 'ry': 0.12},  # u→e
    'wi (위)':  {'x': 0.55, 'y': 0.85, 'rx': 0.10, 'ry': 0.10},  # u→i
    'ui (의)':  {'x': 0.40, 'y': 0.80, 'rx': 0.12, 'ry': 0.12},  # eu→i
}

# Diphthong trajectory definitions
# start: starting vowel zone, end: ending vowel zone
# direction: expected movement vector (for scoring)
DIPHTHONG_TRAJECTORIES: dict[str, dict] = {
    'wa (와)': {
        'start': 'o (오)',    # or near 'u'
        'end': 'a (아)',
        'direction': 'front-down',  # back-mid → central-low
    },
    'wae (왜)': {
        'start': 'o (오)',
        'end': 'ae (애)',
        'direction': 'front-up',    # back-mid → front-mid
    },
    'oe (외)': {
        'start': 'o (오)',
        'end': 'e (에)',
        'direction': 'front-up',    # back-mid → front-high
    },
    'wo (워)': {
        'start': 'u (우)',
        'end': 'eo (어)',
        'direction': 'front-down',  # back-high → back-mid
    },
    'we (웨)': {
        'start': 'u (우)',
        'end': 'e (에)',
        'direction': 'front-down',  # back-high → front-mid
    },
    'wi (위)': {
        'start': 'u (우)',
        'end': 'i (이)',
        'direction': 'front-stable', # back-high → front-high
    },
    'ui (의)': {
        'start': 'eu (으)',
        'end': 'i (이)',
        'direction': 'front-up',     # central-high → front-high
    },
}


"""
KoSPA Database Module
=====================
Database connection and query utilities for PostgreSQL.

This module provides:
- Connection management using context managers
- Reusable query functions for common operations

Usage:
    from database import get_connection, get_user_by_credentials

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM users")
"""

from contextlib import contextmanager
from psycopg2 import connect
import bcrypt
from config import DB_URL


# =============================================================================
# CONNECTION MANAGEMENT
# =============================================================================

@contextmanager
def get_connection():
    """
    Get a database connection with automatic cleanup.

    Uses SSL for secure connections to remote databases.

    Usage:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")

    Yields:
        psycopg2.connection: Database connection object
    """
    # Use sslmode="prefer" for Docker environment (SSL optional)
    # Change to sslmode="require" for production with SSL-enabled PostgreSQL
    conn = connect(DB_URL, sslmode="prefer")
    try:
        yield conn
    finally:
        conn.close()


# =============================================================================
# USER OPERATIONS
# =============================================================================

def create_user(username: str, password: str) -> None:
    """
    Create a new user in the database.

    Args:
        username: Unique username
        password: User password (will be hashed with bcrypt)

    Raises:
        psycopg2.IntegrityError: If username already exists
    """
    # Hash password with bcrypt
    hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO users (username, password) VALUES (%s, %s)",
                (username, hashed.decode('utf-8'))
            )
            conn.commit()


def get_user_by_credentials(username: str, password: str) -> tuple | None:
    """
    Authenticate user and return user info.

    Args:
        username: User's username
        password: User's password

    Returns:
        Tuple of (user_id, username) if valid, None otherwise
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, username, password FROM users WHERE username = %s",
                (username,)
            )
            row = cur.fetchone()
            if row is None:
                return None

            user_id, db_username, hashed_password = row

            # Verify password with bcrypt
            if bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8')):
                return (user_id, db_username)
            return None


def update_user_password(username: str, new_password: str) -> bool:
    """
    Update a user's password.

    Args:
        username: User's username
        new_password: New password to set (will be hashed with bcrypt)

    Returns:
        True if user was found and updated, False otherwise
    """
    # Hash new password with bcrypt
    hashed = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt())

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE users SET password = %s WHERE username = %s",
                (hashed.decode('utf-8'), username)
            )
            updated = cur.rowcount > 0
            conn.commit()
            return updated


def user_exists(user_id: int) -> bool:
    """
    Check if a user exists by ID.

    Args:
        user_id: User's database ID

    Returns:
        True if user exists, False otherwise
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM users WHERE id = %s", (user_id,))
            return cur.fetchone() is not None


# =============================================================================
# PROGRESS OPERATIONS
# =============================================================================

def get_user_progress(username: str) -> dict[str, int]:
    """
    Get all progress records for a user.

    Args:
        username: User's username

    Returns:
        Dictionary mapping sound symbols to progress scores
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM users WHERE username = %s", (username,))
            row = cur.fetchone()
            if row is None:
                return {}

            user_id = row[0]
            cur.execute(
                "SELECT sound, progress FROM progress WHERE userid = %s",
                (user_id,)
            )
            items = cur.fetchall() or []
            return {s.strip(): int(p) for (s, p) in items}


def update_progress(user_id: int, sound: str, score: int) -> None:
    """
    Update or insert progress for a sound.

    Only updates if new score is higher than existing score.

    Args:
        user_id: User's database ID
        sound: Sound symbol (e.g., 'ㅏ')
        score: New score (0-100)
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            # Try to update existing record (only if new score is higher)
            cur.execute(
                "UPDATE progress SET progress = GREATEST(progress, %s) "
                "WHERE userid = %s AND sound = %s",
                (score, user_id, sound)
            )

            # Insert if no existing record
            if cur.rowcount == 0:
                cur.execute(
                    "INSERT INTO progress (userid, sound, progress) VALUES (%s, %s, %s)",
                    (user_id, sound, score)
                )
            conn.commit()


# =============================================================================
# CALIBRATION/FORMANTS OPERATIONS
# =============================================================================

def get_calibration_count(user_id: int) -> int:
    """
    Get number of completed calibration sounds for a user.

    Calibration requires 5 sounds: 'a', 'i', 'u', 'eo', 'e'
    (ㅏ, ㅣ, ㅜ, ㅓ, ㅔ)

    Args:
        user_id: User's database ID

    Returns:
        Count of distinct calibration sounds (0-5)
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT COUNT(DISTINCT sound) FROM formants "
                "WHERE userid = %s AND sound IN ('a', 'i', 'u', 'eo', 'e')",
                (user_id,)
            )
            return cur.fetchone()[0] or 0


def get_user_formants(user_id: int) -> dict:
    """
    Get all formant calibration data for a user.

    Args:
        user_id: User's database ID

    Returns:
        Dictionary mapping sounds to formant data:
        {
            'a': {'f1_mean': 700, 'f1_std': 50, 'f2_mean': 1200, 'f2_std': 80},
            ...
        }
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT sound, f1_mean, f1_std, f2_mean, f2_std "
                "FROM formants WHERE userid = %s",
                (user_id,)
            )
            items = cur.fetchall() or []

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
            return result


def save_calibration(user_id: int, sound: str, f1_mean: float, f2_mean: float,
                     f1_std: float, f2_std: float) -> None:
    """
    Save or update calibration formant data.

    Args:
        user_id: User's database ID
        sound: Calibration sound ('a', 'i', 'u', 'eo', 'e')
        f1_mean: Mean F1 formant frequency
        f2_mean: Mean F2 formant frequency
        f1_std: Standard deviation of F1
        f2_std: Standard deviation of F2
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            # Delete existing calibration for this sound
            cur.execute(
                "DELETE FROM formants WHERE userid = %s AND sound = %s",
                (user_id, sound)
            )

            # Insert new calibration data
            cur.execute(
                "INSERT INTO formants (userid, sound, f1_mean, f2_mean, f1_std, f2_std) "
                "VALUES (%s, %s, %s, %s, %s, %s)",
                (user_id, sound, f1_mean, f2_mean, f1_std, f2_std)
            )
            conn.commit()


def save_calibration_sample(user_id: int, sound: str, sample_num: int,
                            f1: float, f2: float) -> None:
    """
    Save individual calibration sample (for 3-repeat calibration).

    Args:
        user_id: User's database ID
        sound: Calibration sound ('a', 'i', 'u', 'eo', 'e')
        sample_num: Sample number (1, 2, or 3)
        f1: F1 formant frequency
        f2: F2 formant frequency
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            # Upsert sample data
            cur.execute(
                """
                INSERT INTO formant_samples (userid, sound, sample_num, f1, f2)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (userid, sound, sample_num)
                DO UPDATE SET f1 = EXCLUDED.f1, f2 = EXCLUDED.f2
                """,
                (user_id, sound, sample_num, f1, f2)
            )
            conn.commit()


def get_calibration_samples(user_id: int, sound: str) -> list:
    """
    Get all calibration samples for a sound.

    Returns:
        List of {'sample_num': int, 'f1': float, 'f2': float}
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT sample_num, f1, f2 FROM formant_samples "
                "WHERE userid = %s AND sound = %s ORDER BY sample_num",
                (user_id, sound)
            )
            rows = cur.fetchall() or []
            return [{'sample_num': r[0], 'f1': r[1], 'f2': r[2]} for r in rows]


def finalize_calibration_sound(user_id: int, sound: str) -> dict:
    """
    Calculate mean and std from 3 samples and save to formants table.

    Returns:
        {'f1_mean': float, 'f2_mean': float, 'f1_std': float, 'f2_std': float}
        or None if not enough samples
    """
    import numpy as np

    samples = get_calibration_samples(user_id, sound)
    if len(samples) < 3:
        return None

    f1_values = [s['f1'] for s in samples]
    f2_values = [s['f2'] for s in samples]

    f1_mean = float(np.mean(f1_values))
    f2_mean = float(np.mean(f2_values))
    f1_std = float(np.std(f1_values, ddof=1))  # Sample std
    f2_std = float(np.std(f2_values, ddof=1))

    # Ensure minimum std (avoid division by zero)
    f1_std = max(f1_std, 20.0)
    f2_std = max(f2_std, 30.0)

    save_calibration(user_id, sound, f1_mean, f2_mean, f1_std, f2_std)

    return {
        'f1_mean': f1_mean,
        'f2_mean': f2_mean,
        'f1_std': f1_std,
        'f2_std': f2_std
    }

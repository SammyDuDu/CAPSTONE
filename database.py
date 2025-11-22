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
    conn = connect(DB_URL, sslmode="require")
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
        password: User password (should be hashed in production)

    Raises:
        psycopg2.IntegrityError: If username already exists
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO users (username, password) VALUES (%s, %s)",
                (username, password)
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
                "SELECT id, username FROM users WHERE username = %s AND password = %s",
                (username, password)
            )
            return cur.fetchone()


def update_user_password(username: str, new_password: str) -> bool:
    """
    Update a user's password.

    Args:
        username: User's username
        new_password: New password to set

    Returns:
        True if user was found and updated, False otherwise
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE users SET password = %s WHERE username = %s",
                (new_password, username)
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

    Calibration requires 3 sounds: 'a', 'e', 'u'

    Args:
        user_id: User's database ID

    Returns:
        Count of distinct calibration sounds (0-3)
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT COUNT(DISTINCT sound) FROM formants "
                "WHERE userid = %s AND sound IN ('a', 'e', 'u')",
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
        sound: Calibration sound ('a', 'e', or 'u')
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

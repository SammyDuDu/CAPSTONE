"""
KoSPA Authentication Routes
===========================
User authentication and account management endpoints.

Endpoints:
- POST /api/auth/signup          : Create new user account
- POST /api/auth/login           : Authenticate user
- POST /api/auth/change-password : Update user password
- GET  /api/progress             : Get user's practice progress
- GET  /api/formants             : Get user's calibration data

Security Note:
    Passwords are currently stored in plain text.
    For production, implement proper password hashing (bcrypt/argon2).
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from database import (
    create_user,
    get_user_by_credentials,
    update_user_password,
    get_calibration_count,
    get_user_progress,
    get_user_formants,
    user_exists,
)


# Initialize router
router = APIRouter(prefix="/api", tags=["Authentication"])


# =============================================================================
# REQUEST MODELS
# =============================================================================

class AuthCredentials(BaseModel):
    """Login/Signup credentials."""
    username: str
    password: str


class ChangePasswordPayload(BaseModel):
    """Password change request."""
    username: str
    new_password: str


# =============================================================================
# AUTHENTICATION ENDPOINTS
# =============================================================================

@router.post("/auth/signup")
async def auth_signup(creds: AuthCredentials):
    """
    Create a new user account.

    Args:
        creds: Username and password

    Returns:
        Success message

    Raises:
        HTTPException 400: If username already exists
    """
    try:
        create_user(creds.username, creds.password)
    except Exception as e:
        # Handle duplicate username
        if "duplicate" in str(e).lower() or "unique" in str(e).lower():
            raise HTTPException(status_code=400, detail="Username already exists")
        raise

    return {"ok": True, "message": "User created"}


@router.post("/auth/login")
async def auth_login(creds: AuthCredentials):
    """
    Authenticate user and return session info.

    Also checks if user has completed calibration (3 sounds: a, e, u).

    Args:
        creds: Username and password

    Returns:
        - ok: Success status
        - message: Status message
        - user: Username
        - userid: User's database ID
        - calibration_complete: Whether calibration is done

    Raises:
        HTTPException 401: If credentials are invalid
    """
    user = get_user_by_credentials(creds.username, creds.password)

    if user is None:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    user_id = user[0]
    username = user[1]

    # Check calibration status (need all 5 vowels: a, i, u, eo, e)
    cal_count = get_calibration_count(user_id)
    calibration_complete = (cal_count >= 5)

    return {
        "ok": True,
        "message": "Login successful",
        "user": username,
        "userid": user_id,
        "calibration_complete": calibration_complete
    }


@router.post("/auth/change-password")
async def change_password(payload: ChangePasswordPayload):
    """
    Update a user's password.

    Args:
        payload: Username and new password

    Returns:
        Success message

    Raises:
        HTTPException 404: If user not found
    """
    updated = update_user_password(payload.username, payload.new_password)

    if not updated:
        raise HTTPException(status_code=404, detail="User not found")

    return {"ok": True, "message": "Password updated"}


# =============================================================================
# USER DATA ENDPOINTS
# =============================================================================

@router.get("/progress")
async def get_progress(username: str):
    """
    Get user's practice progress for all sounds.

    Query Parameters:
        username: User's username

    Returns:
        Dictionary mapping sound symbols to highest scores:
        {
            "progress": {
                "ㅏ": 85,
                "ㄱ": 72,
                ...
            }
        }
    """
    progress = get_user_progress(username)
    return {"progress": progress}


@router.get("/formants")
async def get_formants(userid: int):
    """
    Get user's calibration formant data and Affine transform.

    Query Parameters:
        userid: User's database ID

    Returns:
        - userid: User ID
        - formants: Dictionary of calibration data per sound
        - affine_transform: Personalized F1/F2 → x/y transform matrix
          - A: 2×2 transformation matrix
          - b: 2×1 bias vector

    Raises:
        HTTPException 404: If user not found
    """
    from personalization import calibrate_affine

    if not user_exists(userid):
        raise HTTPException(status_code=404, detail="User not found")

    formants = get_user_formants(userid)

    # Calculate Affine transform for articulatory mapping
    A, b = calibrate_affine(formants)

    affine_data = None
    if A is not None and b is not None:
        affine_data = {
            "A": A.tolist(),  # Convert numpy array to list for JSON
            "b": b.tolist()
        }

    return {
        "userid": userid,
        "formants": formants,
        "affine_transform": affine_data
    }

"""
dependencies.py — FastAPI "Depends(...)" helpers for authentication.

A lot of CrimeVision endpoints need one of two pieces of information
about the calling user:
    1) "Just give me their username (from the JWT)"
    2) "Give me the full user record from the database"

Instead of every route re-implementing JWT decoding + DB lookup, those
two needs are encapsulated in `get_username_from_token` and
`get_current_user`. Routes then declare them via FastAPI's `Depends(...)`
syntax, e.g.:

    @router.get("/me")
    def me(user: dict = Depends(get_current_user)):
        ...

If the token is missing or invalid, FastAPI automatically converts the
HTTPException raised here into a 401 response — the route function never
even runs. That keeps every protected route boilerplate-free.
"""
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional, Dict, Any, cast
import logging

from .auth_updated import verify_token
from app.core.database import get_db_connection

logger = logging.getLogger(__name__)

# `HTTPBearer` is a FastAPI security scheme that:
#   - Reads the `Authorization: Bearer <token>` header automatically
#   - Adds the lock icon to Swagger UI so the API can be tested with a
#     real token
#   - Returns the parsed credentials object to whichever dependency
#     declares it
security = HTTPBearer()

def get_username_from_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    """Decode the JWT and return ONLY the username (string).

    Use this dependency in endpoints that just need to know "who is
    asking" but don't need any other profile data — it's the cheapest
    of the two helpers because it never touches the database.
    """
    token = credentials.credentials
    username = verify_token(token)
    if username is None:
        # 401 (not 403) — the token is missing or unreadable, the
        # client should re-authenticate.
        raise HTTPException(status_code=401, detail="Invalid token")
    return username

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """Decode the JWT, look the user up in `users_info`, return their record.

    Most "/me" style endpoints want the full user dict (id, email, name,
    etc.) so they can render a profile or filter rows by user_id. This
    helper does both the JWT decode AND the DB fetch in one step.

    Raises:
        401 — token missing/invalid OR username has no matching DB row
              (which would happen if the user was deleted but their
              token is still valid).
        500 — DB error while fetching the user row.
    """
    token = credentials.credentials
    username = verify_token(token)
    if username is None:
        raise HTTPException(status_code=401, detail="Invalid token")

    # Fresh DB lookup on every request: keeps the response in sync with
    # the latest profile edits and lets us reject deleted/disabled users
    # immediately instead of trusting whatever the JWT was issued with.
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT id, username, email, first_name, last_name FROM users_info WHERE username = %s", (username,))
        result = cursor.fetchone()
        if not result:
            raise HTTPException(status_code=401, detail="User not found")
        user = cast(Dict[str, Any], result)
        return {
            "id": user["id"],
            "username": user["username"],
            "email": user["email"],
            "first_name": user["first_name"],
            "last_name": user["last_name"]
        }
    except Exception as e:
        logger.error(f"Database error getting user details: {e}")
        raise HTTPException(status_code=500, detail="Database error")
    finally:
        cursor.close()
        conn.close()

def get_user_id_from_username(username: str) -> Optional[int]:
    """Plain helper (NOT a FastAPI dependency) to translate a username → id.

    Used by background jobs, alert workers, and routes that already have
    a username on hand and just need the numeric primary key for joins.

    Returns None on either "no such user" or any DB error, so callers
    can treat both cases the same way.
    """
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT id FROM users_info WHERE username = %s", (username,))
        result = cursor.fetchone()
        if result:
            user = cast(Dict[str, Any], result)
            return user['id']
        return None
    except Exception as e:
        logger.error(f"Database error getting user ID: {e}")
        return None
    finally:
        cursor.close()
        conn.close()

from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional, Dict, Any, cast
import logging

from .auth_updated import verify_token
from app.core.database import get_db_connection

logger = logging.getLogger(__name__)
security = HTTPBearer()

def get_username_from_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    """Get current user from JWT token"""
    token = credentials.credentials
    username = verify_token(token)
    if username is None:
        raise HTTPException(status_code=401, detail="Invalid token")
    return username

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """Get current user from JWT token - FIXED VERSION"""
    token = credentials.credentials
    username = verify_token(token)
    if username is None:
        raise HTTPException(status_code=401, detail="Invalid token")

    # Get user details from database
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
    """Get user ID from username - FIXED VERSION"""
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

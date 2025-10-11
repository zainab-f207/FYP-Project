import pyotp
import secrets
from fastapi import HTTPException
from app.core.database import get_db_connection
from app.core.config import get_logger
from typing import cast, Dict, Any

logger = get_logger(__name__)

def generate_2fa_secret():
    """Generate a random secret for 2FA"""
    return pyotp.random_base32()

def get_totp(secret):
    """Get TOTP object for secret"""
    return pyotp.TOTP(secret)

def verify_2fa_code(secret, code):
    """Verify a 2FA code"""
    totp = get_totp(secret)
    return totp.verify(code)

def get_2fa_uri(secret, username, issuer="CrimeVision"):
    """Get the provisioning URI for QR code"""
    totp = get_totp(secret)
    return totp.provisioning_uri(name=username, issuer_name=issuer)

def setup_2fa(user_id, secret):
    """Setup 2FA secret for a user (store but don't enable yet)"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "UPDATE users_info SET two_factor_secret = %s WHERE id = %s",
            (secret, user_id)
        )
        conn.commit()
        logger.info(f"2FA secret set up for user {user_id}")
    except Exception as e:
        logger.error(f"Error setting up 2FA secret for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to setup 2FA")
    finally:
        cursor.close()
        conn.close()

def enable_2fa(user_id, secret):
    """Enable 2FA for a user"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "UPDATE users_info SET two_factor_secret = %s, two_factor_enabled = TRUE WHERE id = %s",
            (secret, user_id)
        )
        conn.commit()
        logger.info(f"2FA enabled for user {user_id}")
    except Exception as e:
        logger.error(f"Error enabling 2FA for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to enable 2FA")
    finally:
        cursor.close()
        conn.close()

def disable_2fa(user_id):
    """Disable 2FA for a user"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "UPDATE users_info SET two_factor_secret = NULL, two_factor_enabled = FALSE WHERE id = %s",
            (user_id,)
        )
        conn.commit()
        logger.info(f"2FA disabled for user {user_id}")
    except Exception as e:
        logger.error(f"Error disabling 2FA for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to disable 2FA")
    finally:
        cursor.close()
        conn.close()

def is_2fa_enabled(user_id):
    """Check if 2FA is enabled for user"""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT two_factor_enabled FROM users_info WHERE id = %s", (user_id,))
        user = cursor.fetchone()
        return user and cast(Dict[str, Any], user).get('two_factor_enabled', False)
    except Exception as e:
        logger.error(f"Error checking 2FA status for user {user_id}: {e}")
        return False
    finally:
        cursor.close()
        conn.close()

def get_user_2fa_secret(user_id):
    """Get user's 2FA secret"""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT two_factor_secret FROM users_info WHERE id = %s", (user_id,))
        user = cursor.fetchone()
        return cast(Dict[str, Any], user).get('two_factor_secret') if user else None
    except Exception as e:
        logger.error(f"Error getting 2FA secret for user {user_id}: {e}")
        return None
    finally:
        cursor.close()
        conn.close()

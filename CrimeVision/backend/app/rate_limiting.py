"""
Login Rate Limiting Module
Tracks failed login attempts and locks accounts after too many failures.
"""

import logging
from datetime import datetime, timedelta
from typing import Tuple

from app.core.database import get_db_connection

logger = logging.getLogger(__name__)

# Fallback defaults (overridden by system_settings table when available)
_DEFAULT_MAX_ATTEMPTS = 5
_DEFAULT_LOCKOUT_MINUTES = 30
_DEFAULT_ATTEMPT_WINDOW_MINUTES = 30


def _get_dynamic_config():
    """Read rate-limiting config from system_settings table, falling back to defaults."""
    try:
        from app.routes.admin import get_setting
        max_attempts = int(get_setting("max_login_attempts", str(_DEFAULT_MAX_ATTEMPTS)))
        lockout_minutes = int(get_setting("lockout_duration", str(_DEFAULT_LOCKOUT_MINUTES)))
    except Exception:
        max_attempts = _DEFAULT_MAX_ATTEMPTS
        lockout_minutes = _DEFAULT_LOCKOUT_MINUTES
    return max_attempts, lockout_minutes


def check_rate_limit(email: str, ip_address: str | None = None) -> Tuple[bool, int, int]:
    """
    Check if a login attempt is allowed.

    Returns:
        Tuple of (is_allowed, remaining_attempts, lockout_seconds_remaining)
    """
    MAX_ATTEMPTS, LOCKOUT_MINUTES = _get_dynamic_config()
    ATTEMPT_WINDOW_MINUTES = LOCKOUT_MINUTES  # Use same window as lockout

    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        window_start = datetime.now() - timedelta(minutes=ATTEMPT_WINDOW_MINUTES)

        # Count recent failed attempts for this email
        cursor.execute(
            """SELECT COUNT(*) as fail_count, MAX(attempt_time) as last_attempt
               FROM login_attempts
               WHERE email = %s AND success = FALSE AND attempt_time > %s""",
            (email, window_start),
        )
        row = cursor.fetchone()
        cursor.close()

        if not row or row["fail_count"] is None:
            return (True, MAX_ATTEMPTS, 0)

        fail_count = int(row["fail_count"])

        if fail_count >= MAX_ATTEMPTS:
            # Account is locked – calculate remaining lockout time
            last_attempt = row["last_attempt"]
            if last_attempt:
                unlock_time = last_attempt + timedelta(minutes=LOCKOUT_MINUTES)
                remaining = (unlock_time - datetime.now()).total_seconds()
                if remaining > 0:
                    return (False, 0, int(remaining))
            # Lockout expired
            return (True, MAX_ATTEMPTS, 0)

        remaining_attempts = MAX_ATTEMPTS - fail_count
        return (True, remaining_attempts, 0)

    except Exception as e:
        logger.error(f"Rate limit check failed: {e}")
        # Fail open – allow the attempt if check errors
        return (True, MAX_ATTEMPTS, 0)
    finally:
        if conn and conn.is_connected():
            conn.close()


def record_login_attempt(email: str, ip_address: str | None, success: bool) -> None:
    """Record a login attempt (successful or failed).

    On a failed attempt that crosses the lockout threshold, write an audit_logs
    row so superadmin notifications surface it (and email is already used by the
    rate-limit gate to return 429 to the client).
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO login_attempts (email, ip_address, attempt_time, success)
               VALUES (%s, %s, %s, %s)""",
            (email, ip_address, datetime.now(), success),
        )
        conn.commit()
        cursor.close()

        if not success:
            try:
                max_attempts, lockout_minutes = _get_dynamic_config()
                window_start = datetime.now() - timedelta(minutes=lockout_minutes)
                count_cursor = conn.cursor(dictionary=True)
                count_cursor.execute(
                    """SELECT COUNT(*) AS fail_count FROM login_attempts
                       WHERE email = %s AND success = FALSE AND attempt_time > %s""",
                    (email, window_start),
                )
                row = count_cursor.fetchone() or {}
                fail_count = int(row.get("fail_count") or 0)
                count_cursor.close()

                # Only emit on the attempt that *just* crossed the threshold
                # to avoid duplicating one lockout into many notifications.
                if fail_count == max_attempts:
                    try:
                        import json as _json
                        audit_cursor = conn.cursor()
                        audit_cursor.execute(
                            """INSERT INTO audit_logs
                                (admin_username, action, target_type, target_id, details, ip_address, created_at)
                               VALUES (%s, %s, %s, %s, %s, %s, NOW())""",
                            (
                                "system",
                                "account_locked",
                                "user",
                                None,
                                _json.dumps(
                                    {
                                        "email": email,
                                        "fail_count": fail_count,
                                        "lockout_minutes": lockout_minutes,
                                    }
                                ),
                                ip_address,
                            ),
                        )
                        conn.commit()
                        audit_cursor.close()
                    except Exception as audit_err:
                        logger.warning(f"audit_logs insert (account_locked) failed: {audit_err}")
            except Exception as count_err:
                logger.warning(f"lockout-threshold check failed: {count_err}")
    except Exception as e:
        logger.error(f"Failed to record login attempt: {e}")
    finally:
        if conn and conn.is_connected():
            conn.close()


def reset_login_attempts(email: str) -> None:
    """Clear failed attempts after a successful login."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "DELETE FROM login_attempts WHERE email = %s AND success = FALSE",
            (email,),
        )
        conn.commit()
        cursor.close()
    except Exception as e:
        logger.error(f"Failed to reset login attempts: {e}")
    finally:
        if conn and conn.is_connected():
            conn.close()


def get_failed_attempt_count(email: str) -> int:
    """Get the number of recent failed attempts for an email."""
    _, lockout_minutes = _get_dynamic_config()
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        window_start = datetime.now() - timedelta(minutes=lockout_minutes)
        cursor.execute(
            """SELECT COUNT(*) as fail_count FROM login_attempts
               WHERE email = %s AND success = FALSE AND attempt_time > %s""",
            (email, window_start),
        )
        row = cursor.fetchone()
        cursor.close()
        return int(row["fail_count"]) if row else 0
    except Exception as e:
        logger.error(f"Failed to get attempt count: {e}")
        return 0
    finally:
        if conn and conn.is_connected():
            conn.close()


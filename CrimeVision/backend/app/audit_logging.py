"""
Audit Logging Module for Admin Actions
Logs all admin operations to the audit_logs table for security tracking.
"""

import json
import logging
from datetime import datetime
from typing import Optional, Any
from fastapi import Request

from app.core.database import get_db_connection

logger = logging.getLogger(__name__)


def log_admin_action(
    admin_username: str,
    action: str,
    target_type: str,
    target_id: Optional[int] = None,
    details: Optional[dict] = None,
    request: Optional[Request] = None,
) -> bool:
    """
    Log an admin action to the audit_logs table.

    Args:
        admin_username: Username of the admin performing the action
        action: Description of the action (e.g., 'delete_user', 'bulk_suspend')
        target_type: Type of target (e.g., 'user', 'system', 'alert')
        target_id: ID of the target entity (optional)
        details: Additional details as a dict (optional)
        request: FastAPI Request object for extracting IP and user agent (optional)

    Returns:
        True if logging succeeded, False otherwise
    """
    ip_address = None
    user_agent = None

    if request:
        # Extract IP address (handle proxied requests)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            ip_address = forwarded_for.split(",")[0].strip()
        else:
            ip_address = request.client.host if request.client else None

        user_agent = request.headers.get("User-Agent", "")[:255]

    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO audit_logs
               (admin_username, action, target_type, target_id, details, ip_address, user_agent, created_at)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
            (
                admin_username,
                action,
                target_type,
                target_id,
                json.dumps(details) if details else None,
                ip_address,
                user_agent,
                datetime.now(),
            ),
        )
        conn.commit()
        cursor.close()
        logger.info(
            f"Audit log: {admin_username} performed '{action}' on {target_type}"
            f"{f' (id={target_id})' if target_id else ''}"
        )
        return True
    except Exception as e:
        logger.error(f"Failed to write audit log: {e}")
        if conn:
            conn.rollback()
        return False
    finally:
        if conn and conn.is_connected():
            conn.close()


def get_audit_logs_for_admin(
    admin_username: str,
    limit: int = 50,
) -> list:
    """Get recent audit logs for a specific admin."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            """SELECT * FROM audit_logs
               WHERE admin_username = %s
               ORDER BY created_at DESC
               LIMIT %s""",
            (admin_username, limit),
        )
        rows = cursor.fetchall()
        cursor.close()
        return rows
    except Exception as e:
        logger.error(f"Failed to read audit logs: {e}")
        return []
    finally:
        if conn and conn.is_connected():
            conn.close()


"""Unverified-account cleanup logic.

Used by the APScheduler job in main.py and by the manual-trigger admin endpoint.
"""
from __future__ import annotations

import json
import logging
from typing import Any, Dict, Optional

from app.core.database import get_db_connection
from app.email_verification import (
    send_admin_notification_email,
    send_unverified_deleted_email,
    send_unverified_warning_email,
)

logger = logging.getLogger(__name__)


def _read_ttl_from_settings() -> tuple[int, int]:
    """Read warn-after / delete-after day counts from system_settings.

    Defaults: warn at 6 days, delete at 7 days.
    """
    warning_after_days = 6
    delete_after_days = 7
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(dictionary=True)
        cur.execute(
            "SELECT setting_key, setting_value FROM system_settings "
            "WHERE setting_key IN ('unverified_warning_after_days', 'unverified_delete_after_days')"
        )
        for row in cur.fetchall():
            try:
                v = int(row.get("setting_value") or 0)
            except Exception:
                v = 0
            if v >= 0:
                if row["setting_key"] == "unverified_warning_after_days":
                    warning_after_days = v
                elif row["setting_key"] == "unverified_delete_after_days":
                    delete_after_days = v
        cur.close()
    except Exception as e:
        logger.warning(f"Could not read unverified-cleanup TTL from system_settings: {e}")
    finally:
        try:
            if conn:
                conn.close()
        except Exception:
            pass
    return warning_after_days, delete_after_days


def run_unverified_cleanup(
    warning_after_days: Optional[int] = None,
    delete_after_days: Optional[int] = None,
    notify_admins: bool = True,
) -> Dict[str, Any]:
    """Send warnings + delete unverified accounts past the configured TTL.

    If `warning_after_days` / `delete_after_days` are passed, they override the
    system_settings values for THIS run only — useful for manual test triggers.
    Pass 0 to process every unverified account regardless of age.

    Returns a summary dict:
        {
            "warning_after_days": int,
            "delete_after_days": int,
            "warned": [{...}, ...],
            "deleted": [{...}, ...],
            "warned_count": int,
            "deleted_count": int,
        }
    """
    cfg_warn, cfg_delete = _read_ttl_from_settings()
    warning_after = cfg_warn if warning_after_days is None else int(warning_after_days)
    delete_after = cfg_delete if delete_after_days is None else int(delete_after_days)

    # Floor at 0 (allow "delete everything unverified right now")
    warning_after = max(0, warning_after)
    delete_after = max(0, delete_after)

    # Allow equal values (test mode); only flip them if the warning would never fire
    if delete_after < warning_after and delete_after > 0:
        warning_after = max(0, delete_after - 1)

    # Warning email text uses the *system_settings* values, NOT the override.
    # In test mode (override 0/0) the email should still tell the user the
    # real production timing, so they can preview what their config produces.
    settings_gap_hours = max(1, (cfg_delete - cfg_warn) * 24)

    summary: Dict[str, Any] = {
        "warning_after_days": warning_after,
        "delete_after_days": delete_after,
        "warned": [],
        "deleted": [],
        "warned_count": 0,
        "deleted_count": 0,
    }

    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(dictionary=True)

        # 1) Send warning emails (idempotent via deletion_warning_sent_at flag)
        cur.execute(
            """
            SELECT id, username, first_name, email, created_at
            FROM users_info
            WHERE COALESCE(is_verified, FALSE) = FALSE
              AND COALESCE(role, 'user') = 'user'
              AND deletion_warning_sent_at IS NULL
              AND created_at <= (NOW() - INTERVAL %s DAY)
            """,
            (warning_after,),
        )
        to_warn = cur.fetchall() or []

        for u in to_warn:
            try:
                send_unverified_warning_email(
                    u["email"], u.get("first_name") or "", settings_gap_hours
                )
                cur.execute(
                    "UPDATE users_info SET deletion_warning_sent_at = NOW() WHERE id = %s",
                    (u["id"],),
                )
                conn.commit()
                summary["warned"].append(
                    {
                        "id": u.get("id"),
                        "username": u.get("username"),
                        "email": u.get("email"),
                    }
                )
            except Exception as warn_err:
                logger.error(
                    f"unverified-warning failed for user {u.get('id')}: {warn_err}"
                )

        # 2) Delete accounts past the delete TTL
        cur.execute(
            """
            SELECT id, username, first_name, last_name, email, created_at
            FROM users_info
            WHERE COALESCE(is_verified, FALSE) = FALSE
              AND COALESCE(role, 'user') = 'user'
              AND created_at <= (NOW() - INTERVAL %s DAY)
            """,
            (delete_after,),
        )
        to_delete = cur.fetchall() or []

        deleted_summary_for_email = []
        for u in to_delete:
            try:
                # Best-effort goodbye email
                try:
                    send_unverified_deleted_email(u["email"], u.get("first_name") or "")
                except Exception:
                    pass

                cur.execute("DELETE FROM users_info WHERE id = %s", (u["id"],))

                try:
                    cur.execute(
                        """
                        INSERT INTO audit_logs
                            (admin_username, action, target_type, target_id, details, ip_address, created_at)
                        VALUES (%s, %s, %s, %s, %s, %s, NOW())
                        """,
                        (
                            "system",
                            "auto_delete_unverified_user",
                            "user",
                            u["id"],
                            json.dumps(
                                {
                                    "email": u.get("email"),
                                    "username": u.get("username"),
                                }
                            ),
                            "system",
                        ),
                    )
                except Exception:
                    pass

                conn.commit()

                summary["deleted"].append(
                    {
                        "id": u.get("id"),
                        "username": u.get("username"),
                        "email": u.get("email"),
                    }
                )
                deleted_summary_for_email.append(
                    {
                        "username": u.get("username"),
                        "email": u.get("email"),
                        "name": f"{u.get('first_name') or ''} {u.get('last_name') or ''}".strip(),
                        "created_at": (
                            u.get("created_at").isoformat() if u.get("created_at") else None
                        ),
                        "token_expired_at": "expired",
                    }
                )
            except Exception as del_err:
                logger.error(
                    f"unverified-delete failed for user {u.get('id')}: {del_err}"
                )

        # 3) Notify superadmins (best-effort)
        if notify_admins and deleted_summary_for_email:
            try:
                cur.execute(
                    "SELECT email FROM users_info "
                    "WHERE role = 'superadmin' AND email IS NOT NULL AND email <> ''"
                )
                for r in cur.fetchall():
                    try:
                        send_admin_notification_email(
                            r["email"], deleted_summary_for_email
                        )
                    except Exception:
                        pass
            except Exception:
                pass

        cur.close()
    except Exception as e:
        logger.error(f"run_unverified_cleanup error: {e}")
    finally:
        try:
            if conn:
                conn.close()
        except Exception:
            pass

    summary["warned_count"] = len(summary["warned"])
    summary["deleted_count"] = len(summary["deleted"])
    logger.info(
        f"unverified-cleanup: warned={summary['warned_count']} "
        f"deleted={summary['deleted_count']} "
        f"(warn_after={warning_after}, delete_after={delete_after})"
    )
    return summary

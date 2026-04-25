from fastapi import APIRouter, Body, Depends, HTTPException, Query, Request
import asyncio
from fastapi.responses import StreamingResponse
from typing import List, Optional, Dict, Any, cast
import logging
import json
from datetime import datetime, timedelta

from app.core.database import get_db_connection, log_user_activity
from app.auth_updated import get_password_hash
from app.utils.validation import generate_username
from app.dependencies import get_username_from_token
from app.models.schemas import AdminRegister, AdminResponse, AlertCreate
from app.audit_logging import log_admin_action
from app.routes.auth import validate_password_strength
from app.approval_workflow import (
    create_approval_request,
    get_pending_approvals,
    get_approval_requests_for_admin,
    get_approval_request_by_id,
    review_approval_request,
    is_sensitive_action,
    get_required_permission,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/admin", tags=["admin"])

# Helper function to ensure admins table schema exists
def ensure_admins_table_schema(cursor):
    """Ensure the admins table exists with required columns."""
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS admins (
            id INT AUTO_INCREMENT PRIMARY KEY,
            username VARCHAR(100) NOT NULL UNIQUE,
            first_name VARCHAR(50),
            last_name VARCHAR(50),
            email VARCHAR(100) NOT NULL UNIQUE,
            password_hash VARCHAR(255) NOT NULL,
            role VARCHAR(20) NOT NULL DEFAULT 'admin',
            department VARCHAR(100),
            permissions TEXT,
            phone VARCHAR(20),
            address VARCHAR(255),
            created_at DATETIME NOT NULL,
            status VARCHAR(20) DEFAULT 'active'
        )
    """)
    # Ensure department column is wide enough for values like "Emergency Response"
    try:
        cursor.execute("ALTER TABLE admins MODIFY COLUMN department VARCHAR(100)")
    except Exception:
        pass

@router.post("/register", response_model=AdminResponse)
def register_admin(admin: AdminRegister, request: Request, current_user: str = Depends(get_username_from_token)):
    """Register a new admin with permissions"""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        # Check if current user is super admin
        cursor.execute("SELECT role FROM users_info WHERE username = %s", (current_user,))
        user = cast(Optional[Dict[str, Any]], cursor.fetchone())
        if not user or user.get("role") != "superadmin":
            raise HTTPException(status_code=403, detail="Only super admins can register new admins")

        ensure_admins_table_schema(cursor)

        # Check if email already exists in users_info or admins table
        cursor.execute("SELECT id FROM users_info WHERE email = %s", (admin.email,))
        if cursor.fetchone():
            raise HTTPException(status_code=400, detail="Email already exists")
        cursor.execute("SELECT id FROM admins WHERE email = %s", (admin.email,))
        if cursor.fetchone():
            raise HTTPException(status_code=400, detail="Email already exists")

        # Generate username from name
        first_name, last_name = admin.name.split(" ", 1) if " " in admin.name else (admin.name, "")
        username = generate_username(first_name, last_name)

        # Validate password strength for admin role
        pw_error = validate_password_strength(admin.password, "admin")
        if pw_error:
            raise HTTPException(status_code=400, detail=pw_error)

        # Hash password
        password_hash = get_password_hash(admin.password)

        # Insert admin user into users_info table (pre-verified since registered by superadmin)
        # password_must_change = TRUE forces admin to change password on first login
        cursor.execute(
            """INSERT INTO users_info
               (username, first_name, last_name, email, password_hash, role, permissions, home_area, work_area, alert_radius, activity_logs, created_at, is_verified, verification_status, verified_at, password_must_change)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
            (username, first_name, last_name, admin.email, password_hash, "admin",
             json.dumps(admin.permissions), None, None, 5, json.dumps([]), datetime.now(),
             True, 'verified', datetime.now(), True)
        )

        # Insert admin user into admins table
        cursor.execute(
            """INSERT INTO admins
               (username, first_name, last_name, email, password_hash, role, department, permissions, phone, address, created_at)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
            (username, first_name, last_name, admin.email, password_hash, "admin",
             admin.department, json.dumps(admin.permissions), admin.phone, admin.address, datetime.now())
        )
        admin_id = cursor.lastrowid
        conn.commit()

        if admin_id is None:
            raise HTTPException(status_code=500, detail="Failed to create admin")

        # Audit log: admin registration
        log_admin_action(
            admin_username=current_user,
            action="register_admin",
            target_type="admin",
            target_id=admin_id,
            details={"new_admin_username": username, "email": admin.email, "department": admin.department},
            request=request,
        )

        return AdminResponse(
            id=admin_id,
            username=username,
            name=admin.name,
            email=admin.email,
            department=admin.department,
            permissions=admin.permissions,
            phone=admin.phone,
            address=admin.address,
            created_at=datetime.now().isoformat(),
            status="active"
        )

    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        logger.error(f"Database error during admin registration: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    finally:
        cursor.close()
        conn.close()

@router.get("/list")
def get_admins(current_user: str = Depends(get_username_from_token)):
    """Get list of all admins"""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        # Check if current user is super admin
        cursor.execute("SELECT role FROM users_info WHERE username = %s", (current_user,))
        user = cast(Optional[Dict[str, Any]], cursor.fetchone())
        role_value = user.get("role") if user else None
        if role_value != "superadmin":
            raise HTTPException(status_code=403, detail="Only super admins can view admin list")

        ensure_admins_table_schema(cursor)

        cursor.execute(
            """SELECT id, username, first_name, last_name, email,
                      role, department, permissions, phone, address, created_at, status
               FROM admins
               ORDER BY created_at DESC"""
        )
        admins = cursor.fetchall()

        admin_list = []
        for admin_row in admins:
            admin = cast(Dict[str, Any], admin_row)
            raw_permissions = admin.get("permissions")
            if isinstance(raw_permissions, list):
                permissions = raw_permissions
            elif isinstance(raw_permissions, str) and raw_permissions.strip():
                try:
                    permissions = json.loads(raw_permissions)
                except (json.JSONDecodeError, TypeError):
                    permissions = []
            else:
                permissions = []

            created_at_value = admin.get("created_at")
            if created_at_value is not None and hasattr(created_at_value, "isoformat"):
                created_at_str = created_at_value.isoformat()
            elif isinstance(created_at_value, str):
                created_at_str = created_at_value
            else:
                created_at_str = None

            admin_list.append({
                "id": admin["id"],
                "username": admin["username"],
                "first_name": admin.get("first_name") or "",
                "last_name": admin.get("last_name") or "",
                "name": f'{admin.get("first_name") or ""} {admin.get("last_name") or ""}'.strip(),
                "email": admin["email"],
                "department": admin.get("department") or "—",
                "permissions": permissions,
                "phone": admin.get("phone"),
                "address": admin.get("address"),
                "created_at": created_at_str,
                "status": admin.get("status") or "active"
            })

        return {"admins": admin_list}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Database error getting admins: {e}")
        raise HTTPException(status_code=500, detail="Database error")
    finally:
        cursor.close()
        conn.close()

# ─── System Settings ────────────────────────────────────────────────
SYSTEM_SETTINGS_DEFAULTS = {
    "session_timeout": {"value": "15", "category": "security"},
    "user_session_timeout": {"value": "43200", "category": "security"},
    "admin_session_timeout": {"value": "60", "category": "security"},
    "superadmin_session_timeout": {"value": "60", "category": "security"},
    "max_login_attempts": {"value": "5", "category": "security"},
    "lockout_duration": {"value": "30", "category": "security"},
    # Separate password minimums per role
    "password_min_length": {"value": "8", "category": "security"},            # regular users
    "admin_password_min_length": {"value": "10", "category": "security"},     # admin role
    "superadmin_password_min_length": {"value": "12", "category": "security"},# superadmin role
    "require_two_factor": {"value": "false", "category": "security"},
    "alert_threshold": {"value": "medium", "category": "notifications"},
    "notification_radius": {"value": "5", "category": "notifications"},
    "auto_alert_generation": {"value": "true", "category": "alerts"},
    "alert_cooldown_minutes": {"value": "60", "category": "alerts"},
    "high_risk_threshold": {"value": "70", "category": "alerts"},
    "medium_risk_threshold": {"value": "40", "category": "alerts"},
    "alert_last_30_window_days": {"value": "30", "category": "alerts"},
    "alert_last_90_window_days": {"value": "90", "category": "alerts"},
    "alert_recent_half_window_days": {"value": "182", "category": "alerts"},
    "alert_history_window_days": {"value": "365", "category": "alerts"},
    "default_map_zoom": {"value": "12", "category": "map"},
    "map_min_zoom": {"value": "11", "category": "map"},
    "map_max_zoom": {"value": "18", "category": "map"},
    "map_default_center_lat": {"value": "31.5204", "category": "map"},
    "map_default_center_lng": {"value": "74.3587", "category": "map"},
    "map_bounds_south": {"value": "31.30", "category": "map"},
    "map_bounds_west": {"value": "74.15", "category": "map"},
    "map_bounds_north": {"value": "31.75", "category": "map"},
    "map_bounds_east": {"value": "74.60", "category": "map"},
    "map_bounds_viscosity": {"value": "1.0", "category": "map"},
    "map_fitbounds_padding_px": {"value": "20", "category": "map"},
    "map_fitbounds_max_zoom": {"value": "14", "category": "map"},
    "map_provider_default": {"value": "maptiler", "category": "map"},
    "maptiler_enabled": {"value": "true", "category": "map"},
    "maptiler_api_key": {"value": "JKSv1djb3YWDL4sjZtTB", "category": "map"},
    "map_default_style": {"value": "streets", "category": "map"},
    "heatmap_radius": {"value": "20", "category": "map"},
    "heatmap_intensity": {"value": "0.5", "category": "map"},
    "heatmap_blur_multiplier": {"value": "25", "category": "map"},
    "heatmap_layer_max_zoom": {"value": "17", "category": "map"},
    "map_default_record_limit": {"value": "1000", "category": "map"},
    "map_hotspot_min_incidents": {"value": "2", "category": "map"},
    "map_alert_visibility_threshold": {"value": "low", "category": "map"},
    "monitor_saved_locations_interval_minutes": {"value": "1", "category": "system"},
    "monitor_job_max_instances": {"value": "1", "category": "system"},
    "incident_poll_interval_minutes": {"value": "1", "category": "system"},
    "incident_poll_job_max_instances": {"value": "1", "category": "system"},
    "model_watcher_retrain_threshold_new_crimes": {"value": "500", "category": "system"},
    "model_watcher_retrain_threshold_new_areas": {"value": "5", "category": "system"},
    "model_watcher_retrain_threshold_new_crime_types": {"value": "10", "category": "system"},
    "model_watcher_check_interval_seconds": {"value": "3600", "category": "system"},
    "model_watcher_retrain_timeout_seconds": {"value": "600", "category": "system"},
    "auto_retrain_oov_pair_threshold": {"value": "20", "category": "system"},
    "auto_retrain_new_record_threshold": {"value": "50", "category": "system"},
    "auto_retrain_min_interval_seconds": {"value": "3600", "category": "system"},
    "run_initial_monitor_on_startup": {"value": "true", "category": "system"},
    "weekly_reports_enabled": {"value": "true", "category": "system"},
    "weekly_reports_day_of_week": {"value": "sun", "category": "system"},
    "weekly_reports_hour": {"value": "17", "category": "system"},
    "weekly_reports_minute": {"value": "5", "category": "system"},
    "weekly_reports_timezone": {"value": "Asia/Karachi", "category": "system"},
    "location_accuracy_threshold_meters": {"value": "50000", "category": "system"},
    "low_accuracy_location_policy": {"value": "accept_warn", "category": "system"},
    "ocr_transliteration_timeout_seconds": {"value": "8", "category": "system"},
    "data_retention_days": {"value": "90", "category": "system"},
    "log_level": {"value": "info", "category": "system"},
    "maintenance_mode": {"value": "false", "category": "system"},
}

def ensure_system_settings_table(cursor):
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS system_settings (
            setting_key VARCHAR(100) PRIMARY KEY,
            setting_value TEXT NOT NULL,
            category VARCHAR(50) NOT NULL DEFAULT 'general',
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            updated_by VARCHAR(100)
        )
    """)


def get_setting(key: str, default: str | None = None) -> str | None:
    """Read a single system setting from the database (for use by other backend modules)."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        ensure_system_settings_table(cursor)
        conn.commit()
        cursor.execute("SELECT setting_value FROM system_settings WHERE setting_key = %s", (key,))
        row = cursor.fetchone()
        cursor.close()
        if row:
            return cast(Dict[str, Any], row)["setting_value"]
        # Fall back to defaults
        meta = SYSTEM_SETTINGS_DEFAULTS.get(key)
        return meta["value"] if meta else default
    except Exception as e:
        logger.error(f"get_setting({key}) failed: {e}")
        meta = SYSTEM_SETTINGS_DEFAULTS.get(key)
        return meta["value"] if meta else default
    finally:
        if conn and conn.is_connected():
            conn.close()


def get_all_public_settings() -> dict:
    """Return non-sensitive settings (map, alerts) for any authenticated/public use."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        ensure_system_settings_table(cursor)
        conn.commit()
        cursor.execute("SELECT setting_key, setting_value FROM system_settings")
        rows = cursor.fetchall()
        cursor.close()

        settings = {}
        for key, meta in SYSTEM_SETTINGS_DEFAULTS.items():
            settings[key] = meta["value"]
        for row in rows:
            r = cast(Dict[str, Any], row)
            settings[r["setting_key"]] = r["setting_value"]
        return settings
    except Exception as e:
        logger.error(f"get_all_public_settings failed: {e}")
        return {k: v["value"] for k, v in SYSTEM_SETTINGS_DEFAULTS.items()}
    finally:
        if conn and conn.is_connected():
            conn.close()


@router.get("/public-settings")
def get_public_settings():
    """Return system settings without requiring authentication (used by map, frontend components)."""
    settings = get_all_public_settings()
    return {"settings": settings}


@router.get("/system-settings")
def get_system_settings(current_user: str = Depends(get_username_from_token)):
    """Get all system settings"""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT role FROM users_info WHERE username = %s", (current_user,))
        user = cast(Optional[Dict[str, Any]], cursor.fetchone())
        if not user or user.get("role") not in ["superadmin", "admin"]:
            raise HTTPException(status_code=403, detail="Access denied")

        ensure_system_settings_table(cursor)
        conn.commit()

        cursor.execute("SELECT setting_key, setting_value, category, updated_at, updated_by FROM system_settings")
        rows = cursor.fetchall()

        # Start with defaults, then overlay DB values
        settings = {}
        for key, meta in SYSTEM_SETTINGS_DEFAULTS.items():
            settings[key] = meta["value"]

        last_updated = None
        last_updated_by = None
        for row in rows:
            r = cast(Dict[str, Any], row)
            settings[r["setting_key"]] = r["setting_value"]
            if r.get("updated_at"):
                ts = r["updated_at"]
                if last_updated is None or (hasattr(ts, '__gt__') and ts > last_updated):
                    last_updated = ts
                    last_updated_by = r.get("updated_by")

        return {
            "settings": settings,
            "lastUpdated": last_updated.isoformat() if last_updated and hasattr(last_updated, 'isoformat') else None,
            "lastUpdatedBy": last_updated_by,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error loading system settings: {e}")
        raise HTTPException(status_code=500, detail="Failed to load system settings")
    finally:
        cursor.close()
        conn.close()

@router.post("/system-settings")
async def save_system_settings(request: Request, current_user: str = Depends(get_username_from_token)):
    """Save system settings"""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT role FROM users_info WHERE username = %s", (current_user,))
        user = cast(Optional[Dict[str, Any]], cursor.fetchone())
        if not user or user.get("role") != "superadmin":
            raise HTTPException(status_code=403, detail="Only super admins can modify system settings")

        ensure_system_settings_table(cursor)
        body = await request.json()
        settings_data = body if isinstance(body, dict) else {}

        changed = []
        for key, value in settings_data.items():
            if key in SYSTEM_SETTINGS_DEFAULTS or key in [
                "session_timeout", "user_session_timeout", "admin_session_timeout", "superadmin_session_timeout",
                "max_login_attempts", "lockout_duration",
                "password_min_length", "admin_password_min_length", "superadmin_password_min_length",
                "require_two_factor", "alert_threshold",
                "notification_radius", "auto_alert_generation", "alert_cooldown_minutes",
                "high_risk_threshold", "medium_risk_threshold", "default_map_zoom",
                "heatmap_radius", "heatmap_intensity", "map_default_record_limit",
                "map_hotspot_min_incidents", "map_alert_visibility_threshold", "data_retention_days",
                "monitor_saved_locations_interval_minutes", "incident_poll_interval_minutes",
                "weekly_reports_enabled", "weekly_reports_day_of_week", "weekly_reports_hour",
                "weekly_reports_minute", "weekly_reports_timezone", "location_accuracy_threshold_meters",
                "log_level", "maintenance_mode",
            ]:
                cat = SYSTEM_SETTINGS_DEFAULTS.get(key, {}).get("category", "general")
                cursor.execute(
                    """INSERT INTO system_settings (setting_key, setting_value, category, updated_by)
                       VALUES (%s, %s, %s, %s)
                       ON DUPLICATE KEY UPDATE setting_value = VALUES(setting_value),
                           category = VALUES(category), updated_by = VALUES(updated_by)""",
                    (key, str(value), cat, current_user)
                )
                changed.append(key)

        log_admin_action(
            admin_username=current_user,
            action="update_system_settings",
            target_type="system_settings",
            target_id=0,
            details={"changed_keys": changed},
            request=request,
        )

        conn.commit()
        return {"message": f"Settings saved successfully ({len(changed)} updated)", "changed": changed}
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        logger.error(f"Error saving system settings: {e}")
        raise HTTPException(status_code=500, detail="Failed to save system settings")
    finally:
        cursor.close()
        conn.close()


@router.post("/system-settings/apply-runtime")
async def apply_runtime_system_settings(request: Request, current_user: str = Depends(get_username_from_token)):
    """Apply scheduler/runtime-related system settings immediately (no backend restart)."""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT role FROM users_info WHERE username = %s", (current_user,))
        user = cast(Optional[Dict[str, Any]], cursor.fetchone())
        if not user or user.get("role") not in ["superadmin", "admin"]:
            raise HTTPException(status_code=403, detail="Access denied")

        # Lazy import to avoid module import cycles at startup.
        import main as app_main

        app_main.start_background_monitoring()

        jobs = []
        try:
            for job in app_main.scheduler.get_jobs():
                jobs.append({
                    "id": job.id,
                    "name": job.name,
                    "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None,
                })
        except Exception:
            jobs = []

        log_admin_action(
            admin_username=current_user,
            action="apply_runtime_system_settings",
            target_type="system_settings",
            target_id=0,
            details={"jobs": [j.get("id") for j in jobs]},
            request=request,
        )

        conn.commit()
        return {
            "message": "Runtime scheduler settings applied successfully",
            "jobs": jobs,
        }
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        logger.error(f"Error applying runtime settings: {e}")
        raise HTTPException(status_code=500, detail="Failed to apply runtime settings")
    finally:
        cursor.close()
        conn.close()


@router.put("/users/{user_id}")
async def update_user(user_id: int, request: Request, current_user: str = Depends(get_username_from_token)):
    """Update user details"""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        # Check if current user is super admin or admin
        cursor.execute("SELECT role FROM users_info WHERE username = %s", (current_user,))
        user = cast(Optional[Dict[str, Any]], cursor.fetchone())
        if not user or user.get("role") not in ["superadmin", "admin"]:
            raise HTTPException(status_code=403, detail="Access denied")

        body = await request.json()

        first_name = body.get("firstName", "").strip()
        last_name = body.get("lastName", "").strip()
        email = body.get("email", "").strip()
        role = body.get("role", "").strip()
        home_area = body.get("homeArea", "").strip()
        work_area = body.get("workArea", "").strip()
        alert_radius = body.get("alertRadius")
        new_username = body.get("username", "").strip()
        new_password = body.get("password", "").strip()

        if not email:
            raise HTTPException(status_code=400, detail="Email is required")

        # If username is being changed, check uniqueness
        if new_username:
            cursor.execute("SELECT id FROM users_info WHERE username = %s AND id != %s", (new_username, user_id))
            if cursor.fetchone():
                raise HTTPException(status_code=400, detail="Username already taken")

        # Build UPDATE query dynamically
        update_fields = "first_name = %s, last_name = %s, email = %s, role = %s, home_area = %s, work_area = %s, alert_radius = %s"
        params: list = [first_name, last_name, email, role or "user", home_area or None, work_area or None, alert_radius or None]

        if new_username:
            update_fields += ", username = %s"
            params.append(new_username)

        if new_password:
            # Validate password strength
            pw_error = validate_password_strength(new_password, role or "user")
            if pw_error:
                raise HTTPException(status_code=400, detail=pw_error)
            update_fields += ", password_hash = %s"
            params.append(get_password_hash(new_password))

        params.append(user_id)
        cursor.execute(f"UPDATE users_info SET {update_fields} WHERE id = %s", tuple(params))

        log_admin_action(
            admin_username=current_user,
            action="update_user",
            target_type="user",
            target_id=user_id,
            details={"firstName": first_name, "lastName": last_name, "email": email, "role": role,
                      "usernameChanged": bool(new_username), "passwordChanged": bool(new_password)},
            request=request,
        )

        conn.commit()
        return {"message": "User updated successfully", "id": user_id}

    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        logger.error(f"Database error updating user: {e}")
        raise HTTPException(status_code=500, detail="Database error")
    finally:
        cursor.close()
        conn.close()


@router.put("/{admin_id}")
async def update_admin(admin_id: int, request: Request, current_user: str = Depends(get_username_from_token)):
    """Update admin details"""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        # Check if current user is super admin
        cursor.execute("SELECT role FROM users_info WHERE username = %s", (current_user,))
        user = cast(Optional[Dict[str, Any]], cursor.fetchone())
        if not user or user.get("role") != "superadmin":
            raise HTTPException(status_code=403, detail="Only super admins can update admins")

        body = await request.json()

        first_name = body.get("firstName", "").strip()
        last_name = body.get("lastName", "").strip()
        email = body.get("email", "").strip()
        role = body.get("role", "").strip()
        department = body.get("department", "").strip()
        new_username = body.get("username", "").strip()
        new_password = body.get("password", "").strip()
        # Optional permissions update — only applied when key is present
        permissions_provided = "permissions" in body
        new_permissions = body.get("permissions") if permissions_provided else None
        if permissions_provided and not isinstance(new_permissions, list):
            raise HTTPException(status_code=400, detail="permissions must be a list of strings")

        if not email:
            raise HTTPException(status_code=400, detail="Email is required")

        # Get the current admin username for users_info update
        cursor.execute("SELECT username FROM admins WHERE id = %s", (admin_id,))
        admin_row = cursor.fetchone()
        old_username = cast(Dict[str, Any], admin_row)["username"] if admin_row else None

        # If username is being changed, check uniqueness
        if new_username and new_username != old_username:
            cursor.execute("SELECT id FROM users_info WHERE username = %s", (new_username,))
            if cursor.fetchone():
                raise HTTPException(status_code=400, detail="Username already taken")

        # Build admins table UPDATE dynamically
        admin_fields = "first_name = %s, last_name = %s, email = %s, role = %s, department = %s"
        admin_params: list = [first_name, last_name, email, role or "admin", department]

        if new_username:
            admin_fields += ", username = %s"
            admin_params.append(new_username)

        if new_password:
            pw_error = validate_password_strength(new_password, role or "admin")
            if pw_error:
                raise HTTPException(status_code=400, detail=pw_error)
            admin_fields += ", password_hash = %s"
            admin_params.append(get_password_hash(new_password))

        if permissions_provided:
            admin_fields += ", permissions = %s"
            admin_params.append(json.dumps(new_permissions))

        admin_params.append(admin_id)
        cursor.execute(f"UPDATE admins SET {admin_fields} WHERE id = %s", tuple(admin_params))

        # Also update users_info
        if old_username:
            ui_fields = "first_name = %s, last_name = %s, email = %s, role = %s"
            ui_params: list = [first_name, last_name, email, role or "admin"]

            if new_username:
                ui_fields += ", username = %s"
                ui_params.append(new_username)

            if new_password:
                ui_fields += ", password_hash = %s"
                ui_params.append(get_password_hash(new_password))

            if permissions_provided:
                ui_fields += ", permissions = %s"
                ui_params.append(json.dumps(new_permissions))

            ui_params.append(old_username)
            cursor.execute(f"UPDATE users_info SET {ui_fields} WHERE username = %s", tuple(ui_params))

        log_admin_action(
            admin_username=current_user,
            action="update_admin",
            target_type="admin",
            target_id=admin_id,
            details={"firstName": first_name, "lastName": last_name, "email": email, "role": role,
                      "department": department, "usernameChanged": bool(new_username), "passwordChanged": bool(new_password),
                      "permissionsUpdated": permissions_provided},
            request=request,
        )

        conn.commit()
        return {"message": "Admin updated successfully", "id": admin_id}

    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        logger.error(f"Database error updating admin: {e}")
        raise HTTPException(status_code=500, detail="Database error")
    finally:
        cursor.close()
        conn.close()


@router.get("/stats")
def get_admin_stats(current_user: str = Depends(get_username_from_token)):
    """Get admin dashboard statistics"""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        # Check if current user is admin or super admin
        cursor.execute("SELECT role FROM users_info WHERE username = %s", (current_user,))
        user = cast(Optional[Dict[str, Any]], cursor.fetchone())
        if not user or user.get("role") not in ("superadmin", "admin"):
            raise HTTPException(status_code=403, detail="Access denied")

        ensure_admins_table_schema(cursor)

        stats = {}

        # Total crimes
        cursor.execute("SELECT COUNT(*) as total_crimes FROM crimes")
        total_crimes_result = cast(Dict[str, Any], cursor.fetchone())
        stats["total_crimes"] = total_crimes_result["total_crimes"]

        # Crimes by risk level
        cursor.execute("SELECT risk_level, COUNT(*) as count FROM crimes GROUP BY risk_level")
        risk_stats = cursor.fetchall()
        stats["crimes_by_risk"] = {cast(Dict[str, Any], row)["risk_level"]: cast(Dict[str, Any], row)["count"] for row in risk_stats}

        # Total users
        cursor.execute("SELECT COUNT(*) as total_users FROM users_info WHERE role = 'user'")
        total_users_result = cast(Dict[str, Any], cursor.fetchone())
        stats["total_users"] = total_users_result["total_users"]

        # Total admins
        cursor.execute("SELECT COUNT(*) as total_admins FROM admins WHERE role = 'admin'")
        total_admins_result = cast(Dict[str, Any], cursor.fetchone())
        stats["total_admins"] = total_admins_result["total_admins"]

        # Recent crimes (last 30 days)
        thirty_days_ago = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        cursor.execute("SELECT COUNT(*) as recent_crimes FROM crimes WHERE crime_date >= %s", (thirty_days_ago,))
        recent_crimes_result = cast(Dict[str, Any], cursor.fetchone())
        stats["recent_crimes"] = recent_crimes_result["recent_crimes"]

        # Crimes by area (top 10)
        cursor.execute("""
            SELECT area, COUNT(*) as count
            FROM crimes
            GROUP BY area
            ORDER BY count DESC
            LIMIT 10
        """)
        area_stats = cursor.fetchall()
        stats["crimes_by_area"] = {cast(Dict[str, Any], row)["area"]: cast(Dict[str, Any], row)["count"] for row in area_stats}

        return stats

    except Exception as e:
        logger.error(f"Database error getting stats: {e}")
        raise HTTPException(status_code=500, detail="Database error")
    finally:
        cursor.close()
        conn.close()

@router.get("/notifications")
def get_admin_notifications(current_user: str = Depends(get_username_from_token)):
    """Get admin notifications"""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        # Check if current user is super admin or admin
        cursor.execute("SELECT role FROM users_info WHERE username = %s", (current_user,))
        user = cast(Optional[Dict[str, Any]], cursor.fetchone())
        if not user or user.get("role") not in ["superadmin", "admin"]:
            raise HTTPException(status_code=403, detail="Access denied")

        ensure_admins_table_schema(cursor)

        notifications = []

        # High risk crimes in last 24 hours
        yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        cursor.execute(
            "SELECT COUNT(*) as high_risk_count FROM crimes WHERE risk_level = 'High' AND crime_date >= %s",
            (yesterday,)
        )
        high_risk_result = cast(Dict[str, Any], cursor.fetchone())
        high_risk = high_risk_result["high_risk_count"]
        if high_risk > 0:
            notifications.append({
                "id": 1,
                "type": "warning",
                "title": "High Risk Crimes",
                "message": f"{high_risk} high-risk crimes reported in the last 24 hours",
                "timestamp": datetime.now().isoformat()
            })

        # New user registrations today
        today = datetime.now().strftime('%Y-%m-%d')
        cursor.execute(
            "SELECT COUNT(*) as new_users FROM users_info WHERE DATE(created_at) = %s AND role = 'user'",
            (today,)
        )
        new_users_result = cast(Dict[str, Any], cursor.fetchone())
        new_users = new_users_result["new_users"]
        if new_users > 0:
            notifications.append({
                "id": 2,
                "type": "info",
                "title": "New User Registrations",
                "message": f"{new_users} new users registered today",
                "timestamp": datetime.now().isoformat()
            })

        # System status
        notifications.append({
            "id": 3,
            "type": "success",
            "title": "System Status",
            "message": "All systems operational",
            "timestamp": datetime.now().isoformat()
        })

        return {"notifications": notifications}

    except Exception as e:
        logger.error(f"Database error getting notifications: {e}")
        raise HTTPException(status_code=500, detail="Database error")
    finally:
        cursor.close()
        conn.close()


@router.get("/notifications/stream")
async def stream_admin_notifications(current_user: str = Depends(get_username_from_token)):
    """Server-Sent Events endpoint that streams admin notifications in real-time.

    The endpoint polls the same notification logic and emits an event when the
    notifications payload changes. Clients should connect with EventSource.
    """

    async def event_generator():
        last_payload = None
        try:
            while True:
                # Build notifications payload (reuse same logic as get_admin_notifications)
                conn = get_db_connection()
                cursor = conn.cursor(dictionary=True)
                try:
                    # Verify permissions
                    cursor.execute("SELECT role FROM users_info WHERE username = %s", (current_user,))
                    user = cast(Optional[Dict[str, Any]], cursor.fetchone())
                    if not user or user.get("role") not in ["superadmin", "admin"]:
                        # Not authorized - send a message and close generator
                        payload = json.dumps({"error": "Access denied"})
                        yield f"data: {payload}\n\n"
                        return

                    notifications = []

                    # High risk crimes in last 24 hours
                    yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
                    cursor.execute(
                        "SELECT COUNT(*) as high_risk_count FROM crimes WHERE risk_level = 'High' AND crime_date >= %s",
                        (yesterday,)
                    )
                    high_risk_result = cast(Optional[Dict[str, Any]], cursor.fetchone()) or {"high_risk_count": 0}
                    high_risk = high_risk_result.get("high_risk_count", 0)
                    if high_risk > 0:
                        notifications.append({
                            "id": 1,
                            "type": "warning",
                            "title": "High Risk Crimes",
                            "message": f"{high_risk} high-risk crimes reported in the last 24 hours",
                            "timestamp": datetime.now().isoformat()
                        })

                    # New user registrations today
                    today = datetime.now().strftime('%Y-%m-%d')
                    cursor.execute(
                        "SELECT COUNT(*) as new_users FROM users_info WHERE DATE(created_at) = %s AND role = 'user'",
                        (today,)
                    )
                    new_users_result = cast(Optional[Dict[str, Any]], cursor.fetchone()) or {"new_users": 0}
                    new_users = new_users_result.get("new_users", 0)
                    if new_users > 0:
                        notifications.append({
                            "id": 2,
                            "type": "info",
                            "title": "New User Registrations",
                            "message": f"{new_users} new users registered today",
                            "timestamp": datetime.now().isoformat()
                        })

                    # System status
                    notifications.append({
                        "id": 3,
                        "type": "success",
                        "title": "System Status",
                        "message": "All systems operational",
                        "timestamp": datetime.now().isoformat()
                    })

                    payload = json.dumps({"notifications": notifications})
                    if payload != last_payload:
                        yield f"data: {payload}\n\n"
                        last_payload = payload

                except Exception:
                    # On error, send a small error event but continue
                    try:
                        err_payload = json.dumps({"error": "internal_error"})
                        yield f"data: {err_payload}\n\n"
                    except Exception:
                        pass
                finally:
                    try:
                        cursor.close()
                    except Exception:
                        pass
                    try:
                        conn.close()
                    except Exception:
                        pass

                # Poll interval — small to provide near-real-time updates
                await asyncio.sleep(5)

        except asyncio.CancelledError:
            # Client disconnected or task cancelled
            return

    return StreamingResponse(event_generator(), media_type="text/event-stream")

@router.get("/users")
def get_users(
    current_user: str = Depends(get_username_from_token),
    search: Optional[str] = Query(None, description="Search by username, first name, or email"),
    role: Optional[str] = Query(None, description="Filter by role"),
    limit: int = Query(50, description="Maximum number of records to return", ge=1, le=1000),
    offset: int = Query(0, description="Number of records to skip", ge=0)
):
    """Get list of users with filtering and pagination"""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        # Check if current user is super admin
        cursor.execute("SELECT role FROM users_info WHERE username = %s", (current_user,))
        user = cast(Optional[Dict[str, Any]], cursor.fetchone())
        if not user or user.get("role") not in ["superadmin", "admin"]:
            raise HTTPException(status_code=403, detail="Access denied")

        query = """
            SELECT id, username, first_name, last_name, email, role, permissions,
                   home_area, work_area, alert_radius, created_at, activity_logs
            FROM users_info
            WHERE 1=1
        """
        params = []

        if search:
            query += " AND (username LIKE %s OR first_name LIKE %s OR last_name LIKE %s OR email LIKE %s)"
            search_param = f"%{search}%"
            params.extend([search_param] * 4)

        if role:
            query += " AND role = %s"
            params.append(role)

        query += " ORDER BY created_at DESC LIMIT %s OFFSET %s"
        params.extend([limit, offset])

        cursor.execute(query, params)
        users = cursor.fetchall()

        # Get total count for pagination
        count_query = "SELECT COUNT(*) as total FROM users_info WHERE 1=1"
        count_params = []
        if search:
            count_query += " AND (username LIKE %s OR first_name LIKE %s OR last_name LIKE %s OR email LIKE %s)"
            count_params.extend([search_param] * 4)
        if role:
            count_query += " AND role = %s"
            count_params.append(role)

        cursor.execute(count_query, count_params)
        total_result = cast(Dict[str, Any], cursor.fetchone())
        total = total_result["total"]

        # Format users data
        users_list = []
        for user_row in users:
            user = cast(Dict[str, Any], user_row)
            raw_permissions = user.get("permissions")
            raw_activity_logs = user.get("activity_logs")

            if isinstance(raw_permissions, list):
                permissions = raw_permissions
            elif isinstance(raw_permissions, str) and raw_permissions.strip():
                try:
                    permissions = json.loads(raw_permissions)
                except (json.JSONDecodeError, TypeError):
                    permissions = []
            else:
                permissions = []

            if isinstance(raw_activity_logs, list):
                activity_logs = raw_activity_logs
            elif isinstance(raw_activity_logs, str) and raw_activity_logs.strip():
                try:
                    activity_logs = json.loads(raw_activity_logs)
                except (json.JSONDecodeError, TypeError):
                    activity_logs = []
            else:
                activity_logs = []

            users_list.append({
                "id": user["id"],
                "username": user["username"],
                "first_name": user["first_name"],
                "last_name": user["last_name"],
                "email": user["email"],
                "role": user["role"],
                "permissions": permissions,
                "home_area": user["home_area"],
                "work_area": user["work_area"],
                "alert_radius": user["alert_radius"],
                "created_at": user["created_at"].isoformat() if user["created_at"] is not None and hasattr(user["created_at"], "isoformat") else None,
                "activity_logs": activity_logs
            })

        return {
            "users": users_list,
            "total": total,
            "limit": limit,
            "offset": offset
        }

    except Exception as e:
        logger.error(f"Database error getting users: {e}")
        raise HTTPException(status_code=500, detail="Database error")
    finally:
        cursor.close()
        conn.close()

@router.post("/user-bulk")
def bulk_user_actions(
    request: Request,
    action: str = Query(..., description="Action to perform: suspend, activate, delete"),
    user_ids: List[int] = Query(..., description="List of user IDs to perform action on"),
    current_user: str = Depends(get_username_from_token)
):
    """Perform bulk actions on users (suspend, activate, delete)"""
    if action not in ["suspend", "activate", "delete"]:
        raise HTTPException(status_code=400, detail="Invalid action")

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        # Check if current user is super admin
        cursor.execute("SELECT role FROM users_info WHERE username = %s", (current_user,))
        user = cast(Optional[Dict[str, Any]], cursor.fetchone())
        if not user or user.get("role") != "superadmin":
            raise HTTPException(status_code=403, detail="Only super admins can perform bulk actions")

        if not user_ids:
            raise HTTPException(status_code=400, detail="No user IDs provided")

        # Audit log: bulk action
        log_admin_action(
            admin_username=current_user,
            action=f"bulk_{action}",
            target_type="user",
            details={"user_ids": user_ids, "count": len(user_ids)},
            request=request,
        )

        if action == "delete":
            # Delete users
            format_strings = ','.join(['%s'] * len(user_ids))
            cursor.execute(f"DELETE FROM users_info WHERE id IN ({format_strings})", user_ids)
        else:
            # Suspend or activate (set role to inactive/active)
            new_role = "inactive" if action == "suspend" else "user"
            format_strings = ','.join(['%s'] * len(user_ids))
            cursor.execute(f"UPDATE users_info SET role = %s WHERE id IN ({format_strings})", [new_role] + user_ids)

        conn.commit()

        return {"message": f"Successfully {action}d {len(user_ids)} users"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Database error in bulk action: {e}")
        raise HTTPException(status_code=500, detail="Database error")
    finally:
        cursor.close()
        conn.close()

@router.post("/admin-bulk")
def bulk_admin_actions(
    request: Request,
    action: str = Query(..., description="Action to perform: suspend, activate, delete"),
    admin_ids: List[int] = Query(..., description="List of admin IDs to perform action on"),
    current_user: str = Depends(get_username_from_token)
):
    """Perform bulk actions on admins (suspend, activate, delete)"""
    if action not in ["suspend", "activate", "delete"]:
        raise HTTPException(status_code=400, detail="Invalid action")

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        # Check if current user is super admin
        cursor.execute("SELECT role FROM users_info WHERE username = %s", (current_user,))
        user = cast(Optional[Dict[str, Any]], cursor.fetchone())
        if not user or user.get("role") != "superadmin":
            raise HTTPException(status_code=403, detail="Only super admins can perform bulk actions")

        if not admin_ids:
            raise HTTPException(status_code=400, detail="No admin IDs provided")

        # Audit log: bulk action
        log_admin_action(
            admin_username=current_user,
            action=f"bulk_{action}_admins",
            target_type="admin",
            details={"admin_ids": admin_ids, "count": len(admin_ids)},
            request=request,
        )

        format_strings = ','.join(['%s'] * len(admin_ids))

        if action == "delete":
            # Get emails of admins to delete (to also delete from users_info)
            cursor.execute(f"SELECT email FROM admins WHERE id IN ({format_strings})", admin_ids)
            emails = [cast(Dict[str, Any], row)["email"] for row in cursor.fetchall()]
            # Delete from admins table
            cursor.execute(f"DELETE FROM admins WHERE id IN ({format_strings})", admin_ids)
            # Also delete from users_info
            if emails:
                email_format = ','.join(['%s'] * len(emails))
                cursor.execute(f"DELETE FROM users_info WHERE email IN ({email_format}) AND role = 'admin'", emails)
        else:
            # Suspend or activate
            new_status = "inactive" if action == "suspend" else "active"
            cursor.execute(f"UPDATE admins SET status = %s WHERE id IN ({format_strings})", [new_status] + admin_ids)
            # Also update users_info role
            cursor.execute(f"SELECT email FROM admins WHERE id IN ({format_strings})", admin_ids)
            emails = [cast(Dict[str, Any], row)["email"] for row in cursor.fetchall()]
            if emails:
                new_role = "inactive" if action == "suspend" else "admin"
                email_format = ','.join(['%s'] * len(emails))
                cursor.execute(f"UPDATE users_info SET role = %s WHERE email IN ({email_format})", [new_role] + emails)

        conn.commit()

        return {"message": f"Successfully {action}d {len(admin_ids)} admin(s)"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Database error in admin bulk action: {e}")
        raise HTTPException(status_code=500, detail="Database error")
    finally:
        cursor.close()
        conn.close()

@router.put("/user-roles")
def update_user_roles(
    request: Request,
    user_id: int = Query(..., description="User ID to update"),
    permissions: List[str] = Query(..., description="New permissions list"),
    current_user: str = Depends(get_username_from_token)
):
    """Update user permissions"""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        # Check if current user is super admin
        cursor.execute("SELECT role FROM users_info WHERE username = %s", (current_user,))
        user = cast(Optional[Dict[str, Any]], cursor.fetchone())
        if not user or user.get("role") != "superadmin":
            raise HTTPException(status_code=403, detail="Only super admins can update user roles")

        # Update permissions
        cursor.execute(
            "UPDATE users_info SET permissions = %s WHERE id = %s",
            (json.dumps(permissions), user_id)
        )

        # Audit log: permission update
        log_admin_action(
            admin_username=current_user,
            action="update_permissions",
            target_type="user",
            target_id=user_id,
            details={"permissions": permissions},
            request=request,
        )

        conn.commit()

        return {"message": "User permissions updated successfully"}

    except Exception as e:
        logger.error(f"Database error updating user roles: {e}")
        raise HTTPException(status_code=500, detail="Database error")
    finally:
        cursor.close()
        conn.close()

@router.get("/audit-logs")
def get_audit_logs(
    current_user: str = Depends(get_username_from_token),
    action: Optional[str] = Query(None, description="Filter by action"),
    target_type: Optional[str] = Query(None, description="Filter by target type"),
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    limit: int = Query(100, description="Maximum number of records to return", ge=1, le=1000)
):
    """Get admin activity audit logs"""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        # Check if current user is super admin
        cursor.execute("SELECT role FROM users_info WHERE username = %s", (current_user,))
        user = cast(Optional[Dict[str, Any]], cursor.fetchone())
        if not user or user.get("role") != "superadmin":
            raise HTTPException(status_code=403, detail="Only super admins can view audit logs")

        query = "SELECT * FROM audit_logs WHERE 1=1"
        params = []

        if action:
            query += " AND action = %s"
            params.append(action)

        if target_type:
            query += " AND target_type = %s"
            params.append(target_type)

        if start_date:
            query += " AND DATE(created_at) >= %s"
            params.append(start_date)

        if end_date:
            query += " AND DATE(created_at) <= %s"
            params.append(end_date)

        query += " ORDER BY created_at DESC LIMIT %s"
        params.append(limit)

        cursor.execute(query, params)
        logs = cursor.fetchall()

        logs_list = []
        for log_row in logs:
            log = cast(Dict[str, Any], log_row)
            details = json.loads(log.get("details", "{}"))
            logs_list.append({
                "id": log["id"],
                "admin_username": log["admin_username"],
                "action": log["action"],
                "target_type": log["target_type"],
                "target_id": log["target_id"],
                "details": details,
                "ip_address": log["ip_address"],
                "user_agent": log["user_agent"],
                "created_at": log["created_at"].isoformat() if log["created_at"] is not None and hasattr(log["created_at"], "isoformat") else None
            })

        return {"audit_logs": logs_list}

    except Exception as e:
        logger.error(f"Database error getting audit logs: {e}")
        raise HTTPException(status_code=500, detail="Database error")
    finally:
        cursor.close()
        conn.close()

@router.post("/alerts/system")
def create_system_alert(
    alert_data: AlertCreate,
    request: Request,
    current_user: str = Depends(get_username_from_token)
):
    """Create a system-wide alert (admin only)"""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        # Check admin permissions
        cursor.execute("SELECT role FROM users_info WHERE username = %s", (current_user,))
        user = cast(Optional[Dict[str, Any]], cursor.fetchone())
        if not user or user.get("role") not in ["superadmin", "admin"]:
            raise HTTPException(status_code=403, detail="Admin access required")

        # Parse expiry date if provided
        expires_at = None
        if alert_data.expires_at:
            try:
                expires_at = datetime.fromisoformat(alert_data.expires_at.replace('Z', '+00:00'))
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid expiry date format")

        # Insert system alert
        cursor.execute("""
            INSERT INTO system_alerts
            (title, message, alert_type, area, severity, created_by, created_at, expires_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            alert_data.title,
            alert_data.message,
            alert_data.alert_type,
            alert_data.area,
            alert_data.severity,
            current_user,
            datetime.now(),
            expires_at
        ))

        alert_id = cursor.lastrowid
        conn.commit()

        # Audit log: system alert creation
        log_admin_action(
            admin_username=current_user,
            action="create_system_alert",
            target_type="alert",
            target_id=alert_id,
            details={
                "title": alert_data.title,
                "severity": alert_data.severity,
                "area": alert_data.area,
            },
            request=request,
        )

        return {"message": "System alert created", "alert_id": alert_id}

    except Exception as e:
        logger.error(f"Database error creating system alert: {e}")
        raise HTTPException(status_code=500, detail="Failed to create system alert")
    finally:
        cursor.close()
        conn.close()


# ============================================================
# Approval Workflow Endpoints
# ============================================================

@router.post("/approval-request")
def submit_approval_request(
    request: Request,
    action_type: str = Query(..., description="Action type, e.g. delete_user, bulk_delete"),
    target_type: str = Query("user", description="Target type"),
    target_id: Optional[int] = Query(None, description="Target entity ID"),
    request_body: Optional[Dict[str, Any]] = Body(None),
    current_user: str = Depends(get_username_from_token),
):
    """Admin submits a request for superadmin approval."""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        # Verify the current user is an admin and check permissions
        cursor.execute("SELECT role, permissions FROM users_info WHERE username = %s", (current_user,))
        user = cast(Optional[Dict[str, Any]], cursor.fetchone())
        if not user or user.get("role") not in ["admin", "superadmin"]:
            raise HTTPException(status_code=403, detail="Admin access required")

        # Check action-specific permission
        required_perm = get_required_permission(action_type)
        if required_perm and user.get("role") != "superadmin":
            raw_perms = user.get("permissions", "[]")
            if isinstance(raw_perms, str):
                try:
                    user_perms = json.loads(raw_perms)
                except (json.JSONDecodeError, TypeError):
                    user_perms = []
            elif isinstance(raw_perms, list):
                user_perms = raw_perms
            else:
                user_perms = []
            if required_perm not in user_perms:
                raise HTTPException(
                    status_code=403,
                    detail=f"You don't have the '{required_perm}' permission required for this action"
                )

        # Use the parsed JSON body (FastAPI's Body() handles this properly in sync endpoints)
        body = request_body if request_body else {}

        request_id = create_approval_request(
            admin_username=current_user,
            action_type=action_type,
            target_type=target_type,
            target_id=target_id,
            request_data=body if body else {"target_id": target_id},
        )

        if request_id is None:
            raise HTTPException(status_code=500, detail="Failed to create approval request")

        # Audit log
        log_admin_action(
            admin_username=current_user,
            action=f"approval_request_{action_type}",
            target_type=target_type,
            target_id=target_id,
            details={"request_id": request_id, "action_type": action_type},
            request=request,
        )

        return {
            "message": "Approval request submitted successfully",
            "request_id": request_id,
            "status": "pending",
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error submitting approval request: {e}")
        raise HTTPException(status_code=500, detail="Failed to submit approval request")
    finally:
        cursor.close()
        conn.close()


@router.get("/my-approval-requests")
def get_my_approval_requests(
    current_user: str = Depends(get_username_from_token),
    limit: int = Query(50, ge=1, le=200),
):
    """Get approval requests submitted by the current admin."""
    return {"requests": get_approval_requests_for_admin(current_user, limit)}


@router.get("/pending-approvals")
def get_pending_approval_requests(
    current_user: str = Depends(get_username_from_token),
    limit: int = Query(100, ge=1, le=500),
):
    """Get all pending approval requests (superadmin only)."""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT role FROM users_info WHERE username = %s", (current_user,))
        user = cast(Optional[Dict[str, Any]], cursor.fetchone())
        if not user or user.get("role") != "superadmin":
            raise HTTPException(status_code=403, detail="Only superadmins can review approval requests")
        return {"requests": get_pending_approvals(limit)}
    finally:
        cursor.close()
        conn.close()


@router.get("/approval-request/{request_id}")
def get_approval_request_detail(
    request_id: int,
    current_user: str = Depends(get_username_from_token),
):
    """Get a single approval request with full image data — superadmin only."""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT role FROM users_info WHERE username = %s", (current_user,))
        user = cast(Optional[Dict[str, Any]], cursor.fetchone())
        if not user or user.get("role") != "superadmin":
            raise HTTPException(status_code=403, detail="Only superadmins can view full approval details")
    finally:
        cursor.close()
        conn.close()
    req = get_approval_request_by_id(request_id)
    if not req:
        raise HTTPException(status_code=404, detail="Approval request not found")
    return req


@router.post("/review-approval/{request_id}")
def review_approval(
    request_id: int,
    request: Request,
    approved: bool = Query(..., description="True to approve, False to reject"),
    notes: Optional[str] = Query(None, description="Review notes"),
    request_body: Optional[Dict[str, Any]] = Body(None),
    current_user: str = Depends(get_username_from_token),
):
    """Superadmin approves or rejects an admin's approval request."""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT role FROM users_info WHERE username = %s", (current_user,))
        user = cast(Optional[Dict[str, Any]], cursor.fetchone())
        if not user or user.get("role") != "superadmin":
            raise HTTPException(status_code=403, detail="Only superadmins can review approval requests")

        # Use edited data from request body (SuperAdmin may edit FIR fields)
        edited_data = request_body if request_body and isinstance(request_body, dict) else None

        result = review_approval_request(request_id, current_user, approved, notes, edited_data=edited_data)

        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("message", "Review failed"))

        # Audit log
        log_admin_action(
            admin_username=current_user,
            action=f"approval_{'approved' if approved else 'rejected'}",
            target_type="approval_request",
            target_id=request_id,
            details={"approved": approved, "notes": notes, "edited": edited_data is not None},
            request=request,
        )

        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error reviewing approval: {e}")
        raise HTTPException(status_code=500, detail="Failed to review approval request")
    finally:
        cursor.close()
        conn.close()
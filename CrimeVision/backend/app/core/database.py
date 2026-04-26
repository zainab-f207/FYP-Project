"""Database connection helpers and schema initialization routines."""
from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional, cast

import mysql.connector
from mysql.connector import Error

from .config import get_db_config, get_logger

logger = get_logger("core.database")


def get_db_connection():
    """Create and return a new MySQL connection using shared configuration."""
    try:
        conn = mysql.connector.connect(**get_db_config())
        if conn.is_connected():
            return conn
        raise RuntimeError("MySQL connection reported as not connected")
    except Error as exc:  # pragma: no cover - relies on external DB
        logger.error("Database connection failed", exc_info=exc)
        raise


# --- Schema helpers -----------------------------------------------------

def _execute_statements(cursor, statements: Iterable[str]) -> None:
    for statement in statements:
        cursor.execute(statement)


def ensure_users_table(conn) -> None:
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS users_info (
                id INT AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(50) UNIQUE NOT NULL,
                first_name VARCHAR(50) NOT NULL,
                last_name VARCHAR(50) NOT NULL,
                email VARCHAR(100) UNIQUE NOT NULL,
                phone_number VARCHAR(20),
                password_hash VARCHAR(255) NOT NULL,
                profile_picture VARCHAR(255) DEFAULT NULL,
                home_area VARCHAR(100),
                home_latitude DECIMAL(10, 8),
                home_longitude DECIMAL(11, 8),
                work_area VARCHAR(100),
                work_latitude DECIMAL(10, 8),
                work_longitude DECIMAL(11, 8),
                alert_radius INT DEFAULT 5,
                sms_enabled BOOLEAN DEFAULT FALSE,
                email_alerts_enabled BOOLEAN DEFAULT TRUE,
                browser_notifications_enabled BOOLEAN DEFAULT TRUE,
                monitor_live_location BOOLEAN DEFAULT FALSE,
                weekly_reports_enabled BOOLEAN DEFAULT TRUE,
                incident_alerts_enabled BOOLEAN DEFAULT TRUE,
                live_alerts_enabled BOOLEAN DEFAULT TRUE,
                sms_carrier VARCHAR(50),
                role VARCHAR(20) DEFAULT 'user',
                permissions JSON DEFAULT NULL,
                activity_logs JSON DEFAULT NULL,
                verification_status ENUM('pending', 'verified', 'rejected') DEFAULT 'pending',
                verified_at TIMESTAMP NULL,
                verified_by VARCHAR(50),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.commit()

        updates = (
            "ALTER TABLE users_info ADD COLUMN email_alerts_enabled BOOLEAN DEFAULT TRUE",
            "ALTER TABLE users_info ADD COLUMN browser_notifications_enabled BOOLEAN DEFAULT TRUE",
            "ALTER TABLE users_info ADD COLUMN monitor_live_location BOOLEAN DEFAULT FALSE",
            "ALTER TABLE users_info ADD COLUMN weekly_reports_enabled BOOLEAN DEFAULT TRUE",
            "ALTER TABLE users_info ADD COLUMN incident_alerts_enabled BOOLEAN DEFAULT TRUE",
            "ALTER TABLE users_info ADD COLUMN live_alerts_enabled BOOLEAN DEFAULT TRUE",
            "ALTER TABLE users_info ADD COLUMN role VARCHAR(20) DEFAULT 'user'",
            "ALTER TABLE users_info ADD COLUMN permissions JSON DEFAULT NULL",
            "ALTER TABLE users_info ADD COLUMN activity_logs JSON DEFAULT NULL",
            "ALTER TABLE users_info ADD COLUMN verification_status ENUM('pending', 'verified', 'rejected') DEFAULT 'pending'",
            "ALTER TABLE users_info ADD COLUMN verified_at TIMESTAMP NULL",
            "ALTER TABLE users_info ADD COLUMN verified_by VARCHAR(50)",
            # OTP and security columns
            "ALTER TABLE users_info ADD COLUMN otp_code VARCHAR(10) NULL",
            "ALTER TABLE users_info ADD COLUMN otp_expires_at TIMESTAMP NULL",
            "ALTER TABLE users_info ADD COLUMN password_must_change BOOLEAN DEFAULT FALSE",
            # Active flag — referenced by alert queries (alerts.py:601, 2499, 2515)
            # and auth.py:1602. Default TRUE so existing users keep working.
            "ALTER TABLE users_info ADD COLUMN is_active BOOLEAN DEFAULT TRUE",
            # Login/session tracking — referenced by alert monitoring queries
            # and auth flows (auth.py:330, 412, 696, 773; alerts.py:603, 1919, 1948).
            "ALTER TABLE users_info ADD COLUMN is_logged_in BOOLEAN DEFAULT FALSE",
            "ALTER TABLE users_info ADD COLUMN last_login TIMESTAMP NULL",
            "ALTER TABLE users_info ADD COLUMN last_activity_at DATETIME NULL",
            # Verification + email verification — used by auth_updated.py and
            # cleanup_unverified_accounts.py.
            "ALTER TABLE users_info ADD COLUMN is_verified BOOLEAN DEFAULT FALSE",
            "ALTER TABLE users_info ADD COLUMN email_verified BOOLEAN DEFAULT FALSE",
            "ALTER TABLE users_info ADD COLUMN email_verification_token VARCHAR(255) DEFAULT NULL",
            "ALTER TABLE users_info ADD COLUMN token_expires_at TIMESTAMP NULL",
            # Password reset flow — used by password_reset.py / password_reset_fixed.py.
            "ALTER TABLE users_info ADD COLUMN password_reset_token VARCHAR(255) DEFAULT NULL",
            "ALTER TABLE users_info ADD COLUMN reset_token_expires_at TIMESTAMP NULL",
            # 2FA (TOTP) — used by two_factor.py and auth flows.
            "ALTER TABLE users_info ADD COLUMN two_factor_secret VARCHAR(32) DEFAULT NULL",
            "ALTER TABLE users_info ADD COLUMN two_factor_enabled BOOLEAN DEFAULT FALSE",
            # Brute-force protection counter (auth_updated.py).
            "ALTER TABLE users_info ADD COLUMN failed_attempts INT DEFAULT 0",
            # Google OAuth integration (auth_updated.py:442/452/474/509/528).
            "ALTER TABLE users_info ADD COLUMN google_id VARCHAR(255) DEFAULT NULL",
            # Notification + alert preference JSON blobs.
            "ALTER TABLE users_info ADD COLUMN alert_preferences JSON DEFAULT NULL",
            "ALTER TABLE users_info ADD COLUMN notification_preferences JSON DEFAULT NULL",
            # Location tracking source label (gps / network / manual).
            "ALTER TABLE users_info ADD COLUMN location_source VARCHAR(20) DEFAULT 'gps'",
        )
        for statement in updates:
            try:
                cursor.execute(statement)
                conn.commit()
            except Error:
                conn.rollback()
    finally:
        cursor.close()


def ensure_admins_table(conn) -> None:
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS admins (
                id INT AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(50) UNIQUE NOT NULL,
                first_name VARCHAR(50) NOT NULL,
                last_name VARCHAR(50) NOT NULL,
                email VARCHAR(100) UNIQUE NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                department VARCHAR(100),
                permissions JSON DEFAULT NULL,
                phone VARCHAR(20),
                address TEXT,
                role VARCHAR(20) DEFAULT 'admin',
                created_by VARCHAR(50),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status ENUM('active', 'inactive') DEFAULT 'active'
            )
            """
        )
        try:
            cursor.execute("ALTER TABLE admins ADD COLUMN role VARCHAR(20) DEFAULT 'admin'")
        except Error:
            conn.rollback()
        finally:
            conn.commit()
    finally:
        cursor.close()


def ensure_browser_notifications_tables():
    """Ensure browser notifications tables exist - FIXED VERSION"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Create browser_notifications table with proper schema
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS browser_notifications (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL,
                title VARCHAR(255) NOT NULL,
                message TEXT NOT NULL,
                alert_type VARCHAR(50) NOT NULL,
                notification_data JSON,
                is_read BOOLEAN DEFAULT FALSE,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users_info(id) ON DELETE CASCADE,
                INDEX idx_user_id (user_id),
                INDEX idx_created_at (created_at),
                INDEX idx_is_read (is_read)
            )
        """)
        
        # Create browser_push_subscriptions table with proper schema
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS browser_push_subscriptions (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL UNIQUE,
                endpoint TEXT NOT NULL,
                p256dh TEXT NOT NULL,
                auth TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users_info(id) ON DELETE CASCADE,
                INDEX idx_user_id (user_id)
            )
        """)
        
        # Add browser_notifications_enabled column to users_info if it doesn't exist
        try:
            cursor.execute("ALTER TABLE users_info ADD COLUMN browser_notifications_enabled BOOLEAN DEFAULT TRUE")
        except Exception:
            # Column already exists
            pass
            
        conn.commit()
        logger.info("✅ Browser notifications tables ensured with proper schema")
        
    except Exception as e:
        logger.error(f"Error creating browser notifications tables: {e}")
        conn.rollback()
    finally:
        cursor.close()
        conn.close()


def ensure_area_coordinates_table(conn) -> None:
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS area_coordinates (
                id INT AUTO_INCREMENT PRIMARY KEY,
                area_name VARCHAR(100) UNIQUE NOT NULL,
                latitude DECIMAL(10, 8) NOT NULL,
                longitude DECIMAL(11, 8) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_area_name (area_name)
            )
            """
        )
        conn.commit()
    finally:
        cursor.close()


def ensure_user_activity_table(conn) -> None:
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS user_activity_logs (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NULL,
                activity_type VARCHAR(100) NOT NULL,
                activity_details JSON NULL,
                metadata JSON NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_user_activity_user_id (user_id),
                INDEX idx_user_activity_type (activity_type),
                INDEX idx_user_activity_created_at (created_at)
            )
            """
        )
        conn.commit()
    finally:
        cursor.close()


def ensure_audit_logs_table(conn) -> None:
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS audit_logs (
                id INT AUTO_INCREMENT PRIMARY KEY,
                admin_username VARCHAR(50) NOT NULL,
                action VARCHAR(100) NOT NULL,
                target_type VARCHAR(50) NOT NULL,
                target_id INT NULL,
                details JSON,
                ip_address VARCHAR(45),
                user_agent VARCHAR(255),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.commit()
    finally:
        cursor.close()


def ensure_admin_sessions_table(conn) -> None:
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS admin_sessions (
                id INT AUTO_INCREMENT PRIMARY KEY,
                admin_id INT NOT NULL,
                session_token VARCHAR(255) UNIQUE NOT NULL,
                ip_address VARCHAR(45),
                user_agent VARCHAR(255),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT TRUE,
                FOREIGN KEY (admin_id) REFERENCES admins(id) ON DELETE CASCADE,
                INDEX idx_admin_sessions_admin_id (admin_id),
                INDEX idx_admin_sessions_token (session_token),
                INDEX idx_admin_sessions_active (is_active)
            )
            """
        )
        conn.commit()
    finally:
        cursor.close()


def ensure_login_attempts_table(conn) -> None:
    """Ensure login_attempts table exists for rate limiting."""
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS login_attempts (
                id INT AUTO_INCREMENT PRIMARY KEY,
                email VARCHAR(100) NOT NULL,
                ip_address VARCHAR(45),
                attempt_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                success BOOLEAN DEFAULT FALSE,
                INDEX idx_login_attempts_email (email),
                INDEX idx_login_attempts_time (attempt_time),
                INDEX idx_login_attempts_ip (ip_address)
            )
            """
        )
        conn.commit()
    finally:
        cursor.close()


def ensure_approval_requests_table(conn) -> None:
    """Ensure approval_requests table exists for admin action approval workflow."""
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS approval_requests (
                id INT AUTO_INCREMENT PRIMARY KEY,
                admin_username VARCHAR(50) NOT NULL,
                action_type VARCHAR(100) NOT NULL,
                target_type VARCHAR(50) NOT NULL,
                target_id INT NULL,
                request_data JSON,
                status ENUM('pending', 'approved', 'rejected') DEFAULT 'pending',
                requested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                reviewed_by VARCHAR(50) NULL,
                reviewed_at TIMESTAMP NULL,
                review_notes TEXT NULL,
                INDEX idx_approval_status (status),
                INDEX idx_approval_admin (admin_username),
                INDEX idx_approval_requested (requested_at)
            )
            """
        )
        conn.commit()
    finally:
        cursor.close()


def ensure_emergency_calls_table(conn) -> None:
    """Ensure emergency_calls table exists."""
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
           CREATE TABLE IF NOT EXISTS emergency_calls (
    id INT AUTO_INCREMENT PRIMARY KEY,
    contact_name VARCHAR(255) NOT NULL,
    contact_number VARCHAR(20) NOT NULL,
    caller_location_lat DECIMAL(10, 8),
    caller_location_lng DECIMAL(11, 8),
    caller_address TEXT,
    user_id INT,
    username VARCHAR(100),
    emergency_type VARCHAR(50) DEFAULT 'general',
    status VARCHAR(20) DEFAULT 'completed',
    call_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users_info(id) ON DELETE SET NULL
)
            """
        )
        conn.commit()
    finally:
        cursor.close()


def ensure_patrol_requests_table(conn) -> None:
    """Ensure patrol_requests table exists."""
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
          CREATE TABLE IF NOT EXISTS patrol_requests (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT,
    username VARCHAR(100),
    request_type VARCHAR(50) DEFAULT 'general_patrol',
    location_lat DECIMAL(10, 8),
    location_lng DECIMAL(11, 8),
    address TEXT,
    status VARCHAR(20) DEFAULT 'pending',
    urgency VARCHAR(20) DEFAULT 'medium',
    description TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users_info(id) ON DELETE SET NULL
)
            """
        )
        conn.commit()
    finally:
        cursor.close()


def ensure_community_tables(conn) -> None:
    """Ensure all community-related tables exist."""
    cursor = conn.cursor()
    try:
        # Neighborhood Watch Groups
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS neighborhood_watch_groups (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                description TEXT,
                area VARCHAR(100),
                latitude DECIMAL(10, 8),
                longitude DECIMAL(11, 8),
                radius_km DECIMAL(5, 2) DEFAULT 2.0,
                max_members INT DEFAULT 50,
                created_by INT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT TRUE,
                FOREIGN KEY (created_by) REFERENCES users_info(id) ON DELETE SET NULL,
                INDEX idx_groups_area (area),
                INDEX idx_groups_active (is_active)
            )
            """
        )

        # Group Members
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS group_members (
                id INT AUTO_INCREMENT PRIMARY KEY,
                group_id INT NOT NULL,
                user_id INT NOT NULL,
                role VARCHAR(20) DEFAULT 'member',
                joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT TRUE,
                FOREIGN KEY (group_id) REFERENCES neighborhood_watch_groups(id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES users_info(id) ON DELETE CASCADE,
                UNIQUE KEY unique_group_user (group_id, user_id),
                INDEX idx_members_group (group_id),
                INDEX idx_members_user (user_id),
                INDEX idx_members_active (is_active)
            )
            """
        )

        # Community Alerts
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS community_alerts (
                id INT AUTO_INCREMENT PRIMARY KEY,
                title VARCHAR(200) NOT NULL,
                message TEXT NOT NULL,
                alert_type VARCHAR(50) DEFAULT 'info',
                severity VARCHAR(20) DEFAULT 'medium',
                area VARCHAR(100),
                latitude DECIMAL(10, 8),
                longitude DECIMAL(11, 8),
                radius_km DECIMAL(5, 2) DEFAULT 5.0,
                created_by INT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP NULL,
                is_active BOOLEAN DEFAULT TRUE,
                FOREIGN KEY (created_by) REFERENCES users_info(id) ON DELETE SET NULL,
                INDEX idx_alerts_area (area),
                INDEX idx_alerts_type (alert_type),
                INDEX idx_alerts_active (is_active),
                INDEX idx_alerts_expires (expires_at)
            )
            """
        )

        # Alert Subscriptions
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS alert_subscriptions (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL,
                alert_types VARCHAR(50) DEFAULT 'all',
                area VARCHAR(100),
                latitude DECIMAL(10, 8),
                longitude DECIMAL(11, 8),
                radius_km DECIMAL(5, 2) DEFAULT 10.0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT TRUE,
                FOREIGN KEY (user_id) REFERENCES users_info(id) ON DELETE CASCADE,
                INDEX idx_subscriptions_user (user_id),
                INDEX idx_subscriptions_active (is_active)
            )
            """
        )

        # Safety Resources
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS safety_resources (
                id INT AUTO_INCREMENT PRIMARY KEY,
                title VARCHAR(200) NOT NULL,
                description TEXT,
                resource_type VARCHAR(50) DEFAULT 'guide',
                category VARCHAR(100),
                content TEXT,
                file_path VARCHAR(255),
                download_count INT DEFAULT 0,
                created_by INT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_public BOOLEAN DEFAULT TRUE,
                is_active BOOLEAN DEFAULT TRUE,
                FOREIGN KEY (created_by) REFERENCES users_info(id) ON DELETE SET NULL,
                INDEX idx_resources_type (resource_type),
                INDEX idx_resources_category (category),
                INDEX idx_resources_public (is_public),
                INDEX idx_resources_active (is_active)
            )
            """
        )

        # Resource Downloads
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS resource_downloads (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL,
                resource_id INT NOT NULL,
                downloaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users_info(id) ON DELETE CASCADE,
                FOREIGN KEY (resource_id) REFERENCES safety_resources(id) ON DELETE CASCADE,
                UNIQUE KEY unique_user_resource (user_id, resource_id),
                INDEX idx_downloads_user (user_id),
                INDEX idx_downloads_resource (resource_id)
            )
            """
        )

        # Safety Network Connections
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS safety_network_connections (
                id INT AUTO_INCREMENT PRIMARY KEY,
                requester_id INT NOT NULL,
                target_id INT NOT NULL,
                connection_type VARCHAR(50) DEFAULT 'neighbor',
                status VARCHAR(20) DEFAULT 'pending',
                requested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                responded_at TIMESTAMP NULL,
                notes TEXT,
                FOREIGN KEY (requester_id) REFERENCES users_info(id) ON DELETE CASCADE,
                FOREIGN KEY (target_id) REFERENCES users_info(id) ON DELETE CASCADE,
                INDEX idx_connections_requester (requester_id),
                INDEX idx_connections_target (target_id),
                INDEX idx_connections_status (status)
            )
            """
        )

        # Community Incident Reports
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS community_incident_reports (
                id INT AUTO_INCREMENT PRIMARY KEY,
                title VARCHAR(200) NOT NULL,
                description TEXT NOT NULL,
                incident_type VARCHAR(100) NOT NULL,
                severity VARCHAR(20) DEFAULT 'medium',
                area VARCHAR(100),
                latitude DECIMAL(10, 8),
                longitude DECIMAL(11, 8),
                reported_by INT,
                assigned_group_id INT,
                status VARCHAR(50) DEFAULT 'reported',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_anonymous BOOLEAN DEFAULT FALSE,
                FOREIGN KEY (reported_by) REFERENCES users_info(id) ON DELETE SET NULL,
                FOREIGN KEY (assigned_group_id) REFERENCES neighborhood_watch_groups(id) ON DELETE SET NULL,
                INDEX idx_incidents_area (area),
                INDEX idx_incidents_type (incident_type),
                INDEX idx_incidents_status (status),
                INDEX idx_incidents_reported_by (reported_by)
            )
            """
        )

        # Patrol Requests
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS patrol_requests (
                id INT AUTO_INCREMENT PRIMARY KEY,
                requested_by INT,
                latitude DECIMAL(10, 8) NOT NULL,
                longitude DECIMAL(11, 8) NOT NULL,
                urgency VARCHAR(20) DEFAULT 'medium',
                description TEXT NOT NULL,
                status VARCHAR(50) DEFAULT 'pending',
                assigned_to INT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (requested_by) REFERENCES users_info(id) ON DELETE SET NULL,
                FOREIGN KEY (assigned_to) REFERENCES users_info(id) ON DELETE SET NULL,
                INDEX idx_patrols_status (status),
                INDEX idx_patrols_urgency (urgency),
                INDEX idx_patrols_requested_by (requested_by)
            )
            """
        )

        # Community Activity Log
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS community_activity_log (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT,
                activity_type VARCHAR(100) NOT NULL,
                description TEXT,
                related_id INT,
                area VARCHAR(100),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users_info(id) ON DELETE CASCADE,
                INDEX idx_activity_user (user_id),
                INDEX idx_activity_type (activity_type),
                INDEX idx_activity_area (area),
                INDEX idx_activity_created (created_at)
            )
            """
        )

        conn.commit()
    finally:
        cursor.close()


def ensure_alert_subscriptions_table():
    """Ensure alert_subscriptions table exists"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS alert_subscriptions (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL,
                alert_types JSON NOT NULL,
                areas JSON NOT NULL,
                radius FLOAT DEFAULT 5.0,
                notification_types JSON NOT NULL,
                is_active BOOLEAN DEFAULT TRUE,
                monitor_live_location BOOLEAN DEFAULT FALSE,
                created_at DATETIME NOT NULL,
                updated_at DATETIME,
                FOREIGN KEY (user_id) REFERENCES users_info(id) ON DELETE CASCADE,
                INDEX idx_user_id (user_id),
                INDEX idx_is_active (is_active)
            )
        """)
        conn.commit()
        logger.info("Alert subscriptions table ensured")
    except Error as e:
        logger.error(f"Error creating alert_subscriptions table: {e}")
        raise
    finally:
        cursor.close()
        conn.close()
        
def ensure_alerts_tables_schema():
    """Ensure alerts related tables exist"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # User alerts table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_alerts (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT,
                title VARCHAR(255) NOT NULL,
                message TEXT NOT NULL,
                alert_type VARCHAR(50) NOT NULL DEFAULT 'info',
                area VARCHAR(100),
                severity VARCHAR(20) NOT NULL DEFAULT 'medium',
                is_read BOOLEAN NOT NULL DEFAULT FALSE,
                created_at DATETIME NOT NULL,
                expires_at DATETIME,
                FOREIGN KEY (user_id) REFERENCES users_info(id) ON DELETE CASCADE,
                INDEX idx_user_read (user_id, is_read),
                INDEX idx_user_created (user_id, created_at),
                INDEX idx_expires (expires_at)
            )
        """)
        
        # System alerts table (for community/broadcast alerts)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS system_alerts (
                id INT AUTO_INCREMENT PRIMARY KEY,
                title VARCHAR(255) NOT NULL,
                message TEXT NOT NULL,
                alert_type VARCHAR(50) NOT NULL DEFAULT 'info',
                area VARCHAR(100),
                severity VARCHAR(20) NOT NULL DEFAULT 'medium',
                target_audience VARCHAR(20) NOT NULL DEFAULT 'all', -- all, area_specific, role_based
                created_by VARCHAR(100),
                created_at DATETIME NOT NULL,
                expires_at DATETIME,
                is_active BOOLEAN NOT NULL DEFAULT TRUE,
                INDEX idx_area_active (area, is_active),
                INDEX idx_expires_active (expires_at, is_active)
            )
        """)
        
        # User alert preferences table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_alert_preferences (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL UNIQUE,
                email_alerts BOOLEAN NOT NULL DEFAULT TRUE,
                push_notifications BOOLEAN NOT NULL DEFAULT TRUE,
                sms_alerts BOOLEAN NOT NULL DEFAULT FALSE,
                alert_radius INT NOT NULL DEFAULT 5, -- in km
                preferred_areas JSON, -- JSON array of area names
                crime_type_filters JSON, -- JSON array of crime types to alert about
                risk_level_filters JSON, -- JSON array of risk levels to alert about
                quiet_hours_start TIME, -- 22:00
                quiet_hours_end TIME, -- 08:00
                created_at DATETIME NOT NULL,
                updated_at DATETIME NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users_info(id) ON DELETE CASCADE
            )
        """)
        
        conn.commit()
        logger.info("Alerts tables schema ensured")
    except Error as e:
        logger.error(f"Error creating alerts tables: {e}")
        raise
    finally:
        cursor.close()
        conn.close()

# Call this in your startup event

def log_user_activity(
    activity_type: str,
    username: Optional[str] = None,
    user_id: Optional[int] = None,
    activity_details: Optional[Dict[str, Any]] = None,
    metadata: Optional[Dict[str, Any]] = None,
    max_snapshot_entries: int = 50,
) -> None:
    """Persist a user activity event and update the legacy JSON snapshot."""
    timestamp = datetime.now().isoformat()
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        resolved_user_id = user_id
        resolved_username = username
        raw_logs: Any = None

        if resolved_user_id is not None:
            cursor.execute(
                "SELECT id, username, activity_logs FROM users_info WHERE id = %s",
                (resolved_user_id,)
            )
            user_row = cursor.fetchone()
            if user_row:
                user_row_dict = cast(Dict[str, Any], user_row)
                resolved_user_id = cast(int, user_row_dict.get("id"))
                resolved_username = resolved_username or cast(str, user_row_dict.get("username"))
                raw_logs = user_row_dict.get("activity_logs")
        elif resolved_username:
            cursor.execute(
                "SELECT id, username, activity_logs FROM users_info WHERE username = %s",
                (resolved_username,)
            )
            user_row = cursor.fetchone()
            if user_row:
                user_row_dict = cast(Dict[str, Any], user_row)
                resolved_user_id = cast(int, user_row_dict.get("id"))
                resolved_username = cast(str, user_row_dict.get("username"))
                raw_logs = user_row_dict.get("activity_logs")

        metadata_payload: Dict[str, Any] = metadata.copy() if metadata else {}
        if resolved_username:
            metadata_payload.setdefault("username", resolved_username)

        cursor.execute(
            "INSERT INTO user_activity_logs (user_id, activity_type, activity_details, metadata) VALUES (%s, %s, %s, %s)",
            (
                resolved_user_id,
                activity_type,
                json.dumps(activity_details or {}),
                json.dumps(metadata_payload),
            ),
        )

        if resolved_user_id:
            logs_list: List[Dict[str, Any]] = []
            if raw_logs:
                parsed_logs: Any = raw_logs
                if isinstance(parsed_logs, (bytes, bytearray)):
                    parsed_logs = parsed_logs.decode("utf-8")
                if isinstance(parsed_logs, str):
                    try:
                        decoded_logs = json.loads(parsed_logs)
                        if isinstance(decoded_logs, list):
                            logs_list = decoded_logs
                    except json.JSONDecodeError:
                        logs_list = []
                elif isinstance(parsed_logs, list):
                    logs_list = parsed_logs

            entry: Dict[str, Any] = {
                "activity_type": activity_type,
                "timestamp": timestamp,
                "details": activity_details or {},
                "metadata": metadata_payload,
            }
            if resolved_username:
                entry["username"] = resolved_username

            logs_list.append(entry)
            if len(logs_list) > max_snapshot_entries:
                logs_list = logs_list[-max_snapshot_entries:]

            cursor.execute(
                "UPDATE users_info SET activity_logs = %s WHERE id = %s",
                (json.dumps(logs_list), resolved_user_id),
            )

        conn.commit()
    except Error as exc:
        logger.error("Database error logging user activity", exc_info=exc)
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


def ensure_user_location_history_table(conn) -> None:
    """Ensure user_location_history table exists for real-time location tracking."""
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS user_location_history (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL,
                latitude DECIMAL(10, 8) NOT NULL,
                longitude DECIMAL(11, 8) NOT NULL,
                accuracy DECIMAL(6, 2),
                accuracy_score DECIMAL(5, 2),
                address TEXT,
                risk_level VARCHAR(20),
                safety_score DECIMAL(5, 2),
                location_source VARCHAR(20) DEFAULT 'gps',
                device_type VARCHAR(20) DEFAULT 'desktop',
                client_ip VARCHAR(45),
                alert_triggered BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users_info(id) ON DELETE CASCADE,
                INDEX idx_user_location_user_id (user_id),
                INDEX idx_user_location_created_at (created_at),
                INDEX idx_user_location_risk (risk_level),
                INDEX idx_user_location_coords (latitude, longitude),
                INDEX idx_user_location_source (location_source),
                INDEX idx_user_location_accuracy_score (accuracy_score),
                INDEX idx_user_location_device_type (device_type),
                INDEX idx_user_location_alert_triggered (alert_triggered)
            )
            """
        )

        # Add location tracking preferences to users_info table
        columns_to_add = [
            ("location_tracking_enabled", "BOOLEAN DEFAULT FALSE"),
            ("location_update_interval", "INT DEFAULT 30"),
            ("background_location_tracking", "BOOLEAN DEFAULT TRUE"),
            ("high_risk_alerts_only", "BOOLEAN DEFAULT FALSE"),
            ("last_location_update", "TIMESTAMP NULL")
        ]

        for column_name, column_def in columns_to_add:
            try:
                # Try to add the column - MySQL will ignore if it already exists
                cursor.execute(f"ALTER TABLE users_info ADD COLUMN {column_name} {column_def}")
                logger.info(f"✅ Added column {column_name} to users_info table")
            except Error as e:
                # Check if it's the "column already exists" error (Error code 1060)
                if e.errno == 1060:
                    logger.info(f"ℹ️ Column {column_name} already exists in users_info table")
                else:
                    logger.warning(f"⚠️ Error adding column {column_name}: {e}")
                    conn.rollback()
                    continue

        conn.commit()
        logger.info("✅ User location history table ensured")
    finally:
        cursor.close()


def initialize_schema() -> None:
    """Execute all schema guards to keep tables up to date."""
    conn = None
    try:
        conn = get_db_connection()
        ensure_users_table(conn)
        ensure_admins_table(conn)
        ensure_area_coordinates_table(conn)
        ensure_user_activity_table(conn)
        ensure_audit_logs_table(conn)
        ensure_admin_sessions_table(conn)
        ensure_emergency_calls_table(conn)
        ensure_community_tables(conn)
        ensure_user_location_history_table(conn)
        ensure_login_attempts_table(conn)
        ensure_approval_requests_table(conn)

        # Update superadmin email to the correct address
        cursor = conn.cursor()
        try:
            cursor.execute(
                "UPDATE users_info SET email = %s WHERE role = 'superadmin'",
                ("safevision.panel@gmail.com",)
            )
            cursor.execute(
                "UPDATE admins SET email = %s WHERE role = 'superadmin'",
                ("safevision.panel@gmail.com",)
            )
            conn.commit()
        except Error:
            conn.rollback()
        finally:
            cursor.close()
    except Error as exc:
        logger.error("Schema initialization failed", exc_info=exc)
        raise
    finally:
        if conn and conn.is_connected():
            conn.close()

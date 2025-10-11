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
                password_hash VARCHAR(255) NOT NULL,
                profile_picture VARCHAR(255) DEFAULT NULL,
                home_area VARCHAR(100),
                home_latitude DECIMAL(10, 8),
                home_longitude DECIMAL(11, 8),
                work_area VARCHAR(100),
                work_latitude DECIMAL(10, 8),
                work_longitude DECIMAL(11, 8),
                alert_radius INT DEFAULT 5,
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
            "ALTER TABLE users_info ADD COLUMN role VARCHAR(20) DEFAULT 'user'",
            "ALTER TABLE users_info ADD COLUMN permissions JSON DEFAULT NULL",
            "ALTER TABLE users_info ADD COLUMN activity_logs JSON DEFAULT NULL",
            "ALTER TABLE users_info ADD COLUMN verification_status ENUM('pending', 'verified', 'rejected') DEFAULT 'pending'",
            "ALTER TABLE users_info ADD COLUMN verified_at TIMESTAMP NULL",
            "ALTER TABLE users_info ADD COLUMN verified_by VARCHAR(50)",
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
    except Error as exc:
        logger.error("Schema initialization failed", exc_info=exc)
        raise
    finally:
        if conn and conn.is_connected():
            conn.close()

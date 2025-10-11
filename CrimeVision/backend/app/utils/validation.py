"""Input validation helper functions."""
from __future__ import annotations

import re
from datetime import datetime

from fastapi import HTTPException

from ..core.config import get_logger
from ..core.database import get_db_connection

logger = get_logger("utils.validation")


def validate_date_format(date_str: str) -> bool:
    if not date_str or len(date_str) != 10:
        return False
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", date_str):
        return False
    try:
        parsed_date = datetime.strptime(date_str, "%Y-%m-%d")
        current_year = datetime.now().year
        return 1900 <= parsed_date.year <= current_year + 1
    except ValueError:
        return False


def validate_crime_type(crime_type: str) -> str:
    sanitized = re.sub(r"[^\w\s\-_]", "", crime_type.strip())
    if not sanitized:
        raise HTTPException(status_code=400, detail="Invalid crime type format")
    return sanitized[:50]


def validate_name(name: str) -> str:
    sanitized = re.sub(r"[^\w\s\-_]", "", name.strip())
    if not sanitized:
        raise HTTPException(status_code=400, detail="Invalid name format")
    return sanitized[:50]


def generate_username(first_name: str, last_name: str) -> str:
    base_username = f"{first_name.lower()}.{last_name.lower()}".strip(".")
    username = base_username or (first_name.lower() or last_name.lower())

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        counter = 1
        while True:
            cursor.execute("SELECT id FROM users_info WHERE username = %s", (username,))
            if not cursor.fetchone():
                break
            username = f"{base_username}{counter}"
            counter += 1
    except Exception as exc:  # pragma: no cover - depends on DB
        logger.error("Database error checking username", exc_info=exc)
    finally:
        cursor.close()
        conn.close()
    return username
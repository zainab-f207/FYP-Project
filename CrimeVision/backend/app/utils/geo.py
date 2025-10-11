"""Geolocation and coordinate helper utilities."""
from __future__ import annotations

import requests
from typing import Optional, Tuple

from mysql.connector import Error

from ..core.config import get_logger
from ..core.database import get_db_connection

logger = get_logger("utils.geo")


def get_coordinates_from_api(area_name: str) -> Optional[Tuple[float, float]]:
    """Fetch coordinates via the Nominatim API."""
    try:
        response = requests.get(
            "https://nominatim.openstreetmap.org/search",
            params={
                "q": f"{area_name}, Pakistan",
                "format": "json",
                "limit": 1,
                "countrycodes": "pk",
            },
            headers={"User-Agent": "CrimeVision/1.0"},
            timeout=10,
        )
        response.raise_for_status()
        data = response.json()
        if data:
            return float(data[0]["lat"]), float(data[0]["lon"])
    except Exception as exc:  # pragma: no cover - depends on external API
        logger.warning("Geocoding API error for %s", area_name, exc_info=exc)
    return None


def get_coordinates_from_database(area_name: str) -> Optional[Tuple[float, float]]:
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT latitude, longitude FROM area_coordinates WHERE area_name = %s",
            (area_name,),
        )
        result = cursor.fetchone()
        if result:
            lat_val, lon_val = result
            if lat_val is not None and lon_val is not None:
                try:
                    return float(str(lat_val).strip()), float(str(lon_val).strip())
                except (ValueError, TypeError, AttributeError):
                    return None
    except Error as exc:
        logger.error("Database error getting coordinates", exc_info=exc)
    finally:
        cursor.close()
        conn.close()
    return None


def save_coordinates_to_database(area_name: str, lat: float, lon: float) -> None:
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO area_coordinates (area_name, latitude, longitude) VALUES (%s, %s, %s)",
            (area_name, lat, lon),
        )
        conn.commit()
    except Error as exc:
        logger.error("Error saving coordinates", exc_info=exc)
    finally:
        cursor.close()
        conn.close()


def get_coordinates(area_name: str) -> Optional[Tuple[float, float]]:
    if not area_name or not area_name.strip():
        return None
    area_name = area_name.strip()

    coords = get_coordinates_from_database(area_name)
    if coords:
        return coords

    coords = get_coordinates_from_api(area_name)
    if coords:
        save_coordinates_to_database(area_name, coords[0], coords[1])
        return coords
    return None
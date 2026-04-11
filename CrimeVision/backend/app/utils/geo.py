"""Geolocation and coordinate helper utilities."""
from __future__ import annotations

import requests
from typing import Optional, Tuple
from mysql.connector import Error

from ..core.config import get_logger
from ..core.database import get_db_connection

logger = get_logger("utils.geo")


# Lahore bounding box (approximate city limits)
LAHORE_BOUNDS = {
    "min_lat": 31.2,
    "max_lat": 31.8,
    "min_lon": 74.0,
    "max_lon": 74.6
}

def is_in_lahore(lat: float, lon: float) -> bool:
    """Check if coordinates are within the Lahore bounding box."""
    return (LAHORE_BOUNDS["min_lat"] <= lat <= LAHORE_BOUNDS["max_lat"] and 
           LAHORE_BOUNDS["min_lon"] <= lon <= LAHORE_BOUNDS["max_lon"])

def get_coordinates_from_api(area_name: str) -> Optional[Tuple[float, float]]:
    """
    Fetch coordinates from the OpenStreetMap Nominatim API.
    Enforces Lahore search and validates results are within city bounds.
    """
    try:
        # Check if user already typed 'Lahore'
        search_query = area_name
        if "lahore" not in area_name.lower():
            search_query = f"{area_name}, Lahore, Pakistan"
        else:
            if "pakistan" not in area_name.lower():
                search_query = f"{area_name}, Pakistan"

        response = requests.get(
            "https://nominatim.openstreetmap.org/search",
            params={
                "q": search_query,
                "format": "json",
                "addressdetails": 1,
                "limit": 1,
                "countrycodes": "pk"
            },
            headers={"User-Agent": "SafeVision/1.0 (safevision.contact@gmail.com)"},
            timeout=10,
        )
        response.raise_for_status()
        data = response.json()

        if not data:
            logger.warning("No results found on OpenStreetMap for area: %s", search_query)
            return None

        # Extract latitude and longitude
        result = data[0]
        lat, lon = float(result["lat"]), float(result["lon"])
        display_name = result.get("display_name", "Unknown Location").lower()

        # VALIDATION: Check if resolved location is actually in Lahore
        # Either coordinates must be in bounds OR 'lahore' must be in the display name
        if not is_in_lahore(lat, lon) and "lahore" not in display_name:
            logger.warning("Resolved location '%s' (%.5f, %.5f) is OUTSIDE Lahore bounds.", 
                           display_name, lat, lon)
            return None

        logger.info("OpenStreetMap resolved '%s' to '%s' (%.5f, %.5f)",
                    area_name, display_name, lat, lon)

        return lat, lon

    except Exception as exc:
        logger.warning("OpenStreetMap API error for '%s': %s", area_name, exc)
        return None


def get_coordinates_from_database(area_name: str) -> Optional[Tuple[float, float]]:
    """Fetch stored coordinates from the local database, if available."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT latitude, longitude FROM areas WHERE LOWER(area_name) = LOWER(%s)",
            (area_name.strip(),),
        )
        result = cursor.fetchone()
        if result and len(result) >= 2:
            lat_val, lon_val = result[0], result[1]
            if lat_val is not None and lon_val is not None:
                try:
                    lat, lon = float(lat_val), float(lon_val)
                    # Even if in DB, ensure it's in Lahore (in case bad data exists)
                    if is_in_lahore(lat, lon):
                        return lat, lon
                except (ValueError, TypeError):
                    pass
    except Error as exc:
        logger.error("Database error fetching coordinates for %s", area_name, exc_info=exc)
    finally:
        cursor.close()
        conn.close()
    return None


def save_coordinates_to_database(area_name: str, lat: float, lon: float) -> None:
    """Insert or update area coordinates in the database and mark as Lahore area."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            INSERT INTO areas (area_name, latitude, longitude)
            VALUES (%s, %s, %s)
            ON DUPLICATE KEY UPDATE latitude = VALUES(latitude), longitude = VALUES(longitude)
            """,
            (area_name.strip(), lat, lon),
        )
        conn.commit()
    except Error as exc:
        logger.error("Error saving coordinates for %s", area_name, exc_info=exc)
    finally:
        cursor.close()
        conn.close()


def get_coordinates(area_name: str) -> Optional[Tuple[float, float]]:
    """
    Unified function to get coordinates (Strictly within Lahore):
    1. Try from local DB
    2. If not found, use OpenStreetMap (restricted to Lahore)
    3. Save result for future lookups
    """
    if not area_name or not area_name.strip():
        return None

    area_name = area_name.strip()

    # Step 1: Try local database first
    coords = get_coordinates_from_database(area_name)
    if coords:
        return coords

    # Step 2: Fallback to OpenStreetMap (restricted to Lahore)
    coords = get_coordinates_from_api(area_name)
    if coords:
        save_coordinates_to_database(area_name, *coords)
        return coords

    return None

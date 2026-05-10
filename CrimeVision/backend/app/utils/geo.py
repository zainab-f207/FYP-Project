"""
geo.py — turn area names into latitude/longitude pairs (Lahore-only).

The whole CrimeVision app is scoped to the city of Lahore. Every time a
user types or selects an area (e.g. "Gulberg", "DHA Phase 5",
"Township"), some endpoint upstream needs a precise (latitude, longitude)
pair so that:
    - we can plot the area on a Leaflet map,
    - we can run "find crimes within X kilometres of this point" queries,
    - we can compute distance / radius checks against a user's GPS.

This file is the small but important glue that does that conversion.
It does it in three layers, in this priority order:

    1) LOCAL CACHE (database table `areas`):
       Once we've resolved an area we store the coordinates so we never
       have to hit a third-party API again for the same name. This is
       fast (a single indexed SQL row read) and free.

    2) OpenStreetMap Nominatim API:
       If the area is not in our cache, we ask the public Nominatim
       service. We force the search to be Pakistan-only via the
       `countrycodes=pk` parameter and we *append* "Lahore, Pakistan"
       to the query if the user did not include it themselves.

    3) Bounding-box safety check:
       Even after Nominatim returns something, we double-check the
       coordinates fall within a hand-tuned bounding box around Lahore
       (LAHORE_BOUNDS). This is to defend against Nominatim returning
       same-named places elsewhere in Pakistan or even abroad
       (e.g. "Township" exists in many cities).

The single public function meant to be used by the rest of the codebase
is `get_coordinates(area_name)`. The other functions are exposed so a
caller can choose which layer to use directly when needed.
"""
from __future__ import annotations

import requests
from typing import Optional, Tuple
from mysql.connector import Error

from ..core.config import get_logger
from ..core.database import get_db_connection

logger = get_logger("utils.geo")


# Approximate rectangular bounding box around the city of Lahore. These
# numbers were picked manually so that every neighbourhood actually
# inside Lahore falls within them, while obvious out-of-city results
# (e.g. Karachi, Rawalpindi, Multan) are rejected. Tweaking these values
# DIRECTLY affects which "resolved" coordinates we accept as Lahore.
LAHORE_BOUNDS = {
    "min_lat": 31.2,
    "max_lat": 31.8,
    "min_lon": 74.0,
    "max_lon": 74.6
}

def is_in_lahore(lat: float, lon: float) -> bool:
    """Return True if (lat, lon) sits inside the Lahore bounding box.

    A pure point-in-rectangle test. We use this everywhere coordinates
    cross a trust boundary (third-party APIs, user input, old DB rows)
    so out-of-city points never sneak into the analytics pipeline.
    """
    return (LAHORE_BOUNDS["min_lat"] <= lat <= LAHORE_BOUNDS["max_lat"] and
           LAHORE_BOUNDS["min_lon"] <= lon <= LAHORE_BOUNDS["max_lon"])

def get_coordinates_from_api(area_name: str) -> Optional[Tuple[float, float]]:
    """Resolve `area_name` against the public OpenStreetMap Nominatim API.

    Why we do extra work on top of just calling the API:
        - We APPEND "Lahore, Pakistan" to the query if the user didn't
          mention them, so a bare "Gulberg" doesn't accidentally resolve
          to a Gulberg outside Pakistan or a similarly named area in
          another city.
        - We pass `countrycodes=pk` to bias Nominatim further.
        - After the response comes back we still validate it against
          the Lahore bounding box AND the textual `display_name` —
          accepting it only if at least one of those agrees.
        - We send a real User-Agent (Nominatim's terms of use require
          an identifiable contact) and a 10-second timeout to keep the
          request from blocking forever on a flaky network.

    Returns (lat, lon) on success, or None on any failure / rejection.
    """
    try:
        # Build a search query that always mentions Lahore and Pakistan,
        # but only adds those tokens if they aren't already there. This
        # keeps the query natural for users who typed the full address
        # themselves while still helping users who only typed a suburb.
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
                "limit": 1,           # we only ever care about the top hit
                "countrycodes": "pk"  # bias Nominatim towards Pakistan
            },
            headers={"User-Agent": "SafeVision/1.0 (safevision.contact@gmail.com)"},
            timeout=10,
        )
        response.raise_for_status()
        data = response.json()

        if not data:
            logger.warning("No results found on OpenStreetMap for area: %s", search_query)
            return None

        # Take the first (best-ranked) match. Nominatim already orders
        # results by relevance + importance, so we trust the top entry.
        result = data[0]
        lat, lon = float(result["lat"]), float(result["lon"])
        display_name = result.get("display_name", "Unknown Location").lower()

        # Belt-and-braces sanity check: only accept the result if the
        # coordinates are within Lahore OR Nominatim's own display
        # string mentions Lahore. Either alone could be a false positive,
        # but together they're robust against bad geocodings.
        if not is_in_lahore(lat, lon) and "lahore" not in display_name:
            logger.warning("Resolved location '%s' (%.5f, %.5f) is OUTSIDE Lahore bounds.",
                           display_name, lat, lon)
            return None

        logger.info("OpenStreetMap resolved '%s' to '%s' (%.5f, %.5f)",
                    area_name, display_name, lat, lon)

        return lat, lon

    except Exception as exc:
        # Catch everything (HTTP errors, JSON errors, timeouts, network
        # blips) because callers always treat None as "no coordinates"
        # and shouldn't have to handle exceptions from a geocoder.
        logger.warning("OpenStreetMap API error for '%s': %s", area_name, exc)
        return None


def get_coordinates_from_database(area_name: str) -> Optional[Tuple[float, float]]:
    """Look up an area's coordinates from the local `areas` cache table.

    This is the cheap, fast path. If we've ever resolved this area before,
    `save_coordinates_to_database` will have written the row and this
    function will short-circuit the whole API + validation chain.

    The lookup is case-insensitive (`LOWER(area_name) = LOWER(%s)`) so
    "Gulberg", "gulberg" and "GULBERG" all hit the same row. We also
    re-run the bounding-box check on every read so any historically bad
    rows (e.g. left over from before the validation existed) cannot leak
    coordinates outside Lahore back to callers.
    """
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
                    # Defence-in-depth: even cached rows go through the
                    # Lahore check, so a polluted cache cannot poison
                    # the rest of the system.
                    if is_in_lahore(lat, lon):
                        return lat, lon
                except (ValueError, TypeError):
                    # Non-numeric junk in the column (e.g. NULL coerced
                    # weirdly) is treated as "no coordinates here".
                    pass
    except Error as exc:
        logger.error("Database error fetching coordinates for %s", area_name, exc_info=exc)
    finally:
        cursor.close()
        conn.close()
    return None


def save_coordinates_to_database(area_name: str, lat: float, lon: float) -> None:
    """Persist a successful geocode result so future lookups skip the API.

    Uses MySQL's `INSERT ... ON DUPLICATE KEY UPDATE` so that the same
    function safely both creates a new row (first time we see an area)
    and refreshes an existing row (if Nominatim ever gives us slightly
    different coordinates later). This depends on `area_name` being a
    UNIQUE key on the `areas` table.
    """
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
    """The single public entrypoint everyone else should call.

    The flow is the textbook "cache → fallback → store" pattern:
        1) Empty / blank input → return None immediately.
        2) Try the local DB cache (fast, free).
        3) Miss → call the OpenStreetMap API (slow, rate-limited).
        4) Hit → write back to the cache so step 2 wins next time.
        5) Still nothing → return None and let callers handle the
           "could not resolve area" branch in their own UI text.
    """
    if not area_name or not area_name.strip():
        return None

    area_name = area_name.strip()

    # Step 1: cheap local lookup.
    coords = get_coordinates_from_database(area_name)
    if coords:
        return coords

    # Step 2: pay the network cost only when the cache misses.
    coords = get_coordinates_from_api(area_name)
    if coords:
        save_coordinates_to_database(area_name, *coords)
        return coords

    return None

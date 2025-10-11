"""TypedDict definitions and other shared type hints."""
from __future__ import annotations

from typing import TypedDict


class CrimeRow(TypedDict):
    id: int
    area: str
    crime_type: str
    crime_date: str
    latitude: float
    longitude: float
    risk_level: str


class CrimeTypeRow(TypedDict):
    crime_type: str
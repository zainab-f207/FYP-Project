"""Centralized application configuration helpers."""
from __future__ import annotations

import logging
import os
from functools import lru_cache
from pathlib import Path
from typing import Dict, List

from dotenv import load_dotenv

# Load environment variables once the module is imported
load_dotenv()

# Configure global logging as early as possible
_LOG_LEVEL_NAME = os.getenv("LOG_LEVEL", "INFO").upper()
_LOG_LEVEL = getattr(logging, _LOG_LEVEL_NAME, logging.INFO)
logging.basicConfig(level=_LOG_LEVEL)
_logger = logging.getLogger("crimevision")

# Resolve important filesystem locations
_APP_ROOT = Path(__file__).resolve().parent.parent
MODEL_DIR = str(_APP_ROOT / "predict_risk_level" / "model")

# Default fallback values
_DEFAULT_ALLOWED_ORIGINS = (
    "http://localhost:5173, http://localhost:5174, "
    "http://127.0.0.1:5173, http://127.0.0.1:5174"
)
_API_TITLE_FALLBACK = "CrimeVision API"


def get_logger(name: str | None = None) -> logging.Logger:
    """Return a namespaced logger that inherits the base configuration."""
    if not name:
        return _logger
    return _logger.getChild(name)


def get_api_title() -> str:
    """Expose the API title used when instantiating FastAPI."""
    return os.getenv("API_TITLE", _API_TITLE_FALLBACK)


def _parse_allowed_origins(raw_origins: str) -> List[str]:
    return [origin.strip() for origin in raw_origins.split(",") if origin.strip()]


@lru_cache(maxsize=None)
def get_allowed_origins() -> List[str]:
    """Return the list of CORS origins, caching the parsed result."""
    raw_value = os.getenv("ALLOWED_ORIGINS", _DEFAULT_ALLOWED_ORIGINS)
    return _parse_allowed_origins(raw_value)


ALLOWED_ORIGINS = get_allowed_origins()


@lru_cache(maxsize=None)
def get_db_config() -> Dict[str, object]:
    """Collect database credentials in a reusable structure."""
    return {
        "host": os.getenv("DB_HOST", "localhost"),
        "user": os.getenv("DB_USER", "root"),
        "password": os.getenv("DB_PASSWORD", "hafsa555"),
        "database": os.getenv("DB_NAME", "crimevision_db"),
        "port": int(os.getenv("DB_PORT", "3306")),
    }
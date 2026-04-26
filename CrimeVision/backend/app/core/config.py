"""Centralized application configuration helpers."""
from __future__ import annotations

import logging
import os
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional

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
_DEFAULT_ALLOWED_ORIGINS = ",".join([
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:5174",
    "http://127.0.0.1:5174",
])
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


def _find_default_ca_bundle() -> Optional[str]:
    """Locate the system CA certificate bundle on common Linux distributions."""
    for path in (
        "/etc/ssl/certs/ca-certificates.crt",  # Debian/Ubuntu (Render)
        "/etc/pki/tls/certs/ca-bundle.crt",    # RHEL/CentOS/Fedora
        "/etc/ssl/ca-bundle.pem",              # SUSE
        "/etc/ssl/cert.pem",                   # Alpine, macOS
    ):
        if os.path.exists(path):
            return path
    return None


@lru_cache(maxsize=None)
def get_db_ssl_kwargs() -> Dict[str, Any]:
    """Return MySQL SSL kwargs based on env vars, or {} for plain connections.

    Set DB_SSL_DISABLED=false to enable TLS — required by hosts like TiDB
    Cloud Serverless, Aiven, PlanetScale-compatible providers, etc.
    The CA bundle is auto-detected on Linux; set DB_SSL_CA to override.
    """
    if os.getenv("DB_SSL_DISABLED", "true").strip().lower() not in {"false", "0", "no"}:
        return {}
    kwargs: Dict[str, Any] = {"ssl_disabled": False}
    ca_path = os.getenv("DB_SSL_CA") or _find_default_ca_bundle()
    if ca_path:
        kwargs["ssl_ca"] = ca_path
        kwargs["ssl_verify_cert"] = True
        kwargs["ssl_verify_identity"] = True
    return kwargs


@lru_cache(maxsize=None)
def get_db_config() -> Dict[str, Any]:
    """Collect database credentials (and SSL kwargs if configured)."""
    config: Dict[str, Any] = {
        "host": os.getenv("DB_HOST", "localhost"),
        "user": os.getenv("DB_USER", "root"),
        "password": os.getenv("DB_PASSWORD", ""),
        "database": os.getenv("DB_NAME", "crimevision_db"),
        "port": int(os.getenv("DB_PORT", "3306")),
    }
    config.update(get_db_ssl_kwargs())
    return config
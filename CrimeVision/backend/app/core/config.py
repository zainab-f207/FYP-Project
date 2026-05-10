"""
config.py — central place to read runtime configuration from the environment.

Every other backend module that needs to know "where is the database?",
"who is allowed to call our API?", "what log level should we use?", or
"where are model files stored?" goes through THIS file. Putting it all in
one place means:
    - The same defaults are used everywhere (no surprises in production).
    - Switching between local dev and a hosted DB (TiDB Cloud, Aiven,
      etc.) is a one-environment-variable flip.
    - Each lookup that's potentially expensive (parsing CSV-style env
      vars, finding a TLS CA bundle) is wrapped in `lru_cache` so it
      only runs once per process even if hundreds of requests need it.

Side effects on import (deliberate):
    1) `load_dotenv()` reads a local `.env` file (if present) so devs
       can keep secrets out of the shell environment.
    2) `logging.basicConfig` configures the root logger with the level
       from LOG_LEVEL (defaults to INFO). This must happen BEFORE any
       other module grabs a logger, which is why it lives at module top.
"""
from __future__ import annotations

import logging
import os
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv

# Pick up KEY=VALUE pairs from a `.env` file in the working directory if
# one exists. In production environment variables come from the host
# (Render, Docker, etc.) so this call simply does nothing.
load_dotenv()

# Configure logging once, as early as possible. Every other file should
# get its logger via `get_logger(...)` so they all inherit this config.
_LOG_LEVEL_NAME = os.getenv("LOG_LEVEL", "INFO").upper()
_LOG_LEVEL = getattr(logging, _LOG_LEVEL_NAME, logging.INFO)
logging.basicConfig(level=_LOG_LEVEL)
_logger = logging.getLogger("crimevision")

# Resolve filesystem paths relative to THIS file rather than the current
# working directory — this way the app behaves identically whether it is
# launched via uvicorn from `backend/`, from the project root, or from
# inside a Docker container with a different WORKDIR.
_APP_ROOT = Path(__file__).resolve().parent.parent
MODEL_DIR = str(_APP_ROOT / "predict_risk_level" / "model")

# Default fallback CORS origins covering all the local dev ports we
# commonly use (Vite default 5173, CRA default 3000, an alt 5174).
# In production this gets overridden by ALLOWED_ORIGINS in the env.
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
    """Return a logger that's a child of the global `crimevision` logger.

    Why we wrap `logging.getLogger` instead of letting modules call it
    directly: it guarantees every module's logs carry the "crimevision."
    prefix, which makes filtering and aggregation in production much
    easier.
    """
    if not name:
        return _logger
    return _logger.getChild(name)


def get_api_title() -> str:
    """The string shown in the FastAPI Swagger UI title bar."""
    return os.getenv("API_TITLE", _API_TITLE_FALLBACK)


def _parse_allowed_origins(raw_origins: str) -> List[str]:
    """Split a comma-separated origin string into a clean list, dropping blanks."""
    return [origin.strip() for origin in raw_origins.split(",") if origin.strip()]


@lru_cache(maxsize=None)
def get_allowed_origins() -> List[str]:
    """Return the CORS allow-list, parsing the env var only once per process.

    The `lru_cache` decorator means even if a hundred requests call this,
    we only do the string split work the first time. The result is then
    handed back instantly forever.
    """
    raw_value = os.getenv("ALLOWED_ORIGINS", _DEFAULT_ALLOWED_ORIGINS)
    return _parse_allowed_origins(raw_value)


# Module-level alias for callers that want the list at import time
# (e.g. `app.add_middleware(CORSMiddleware, allow_origins=ALLOWED_ORIGINS)`).
ALLOWED_ORIGINS = get_allowed_origins()


def _find_default_ca_bundle() -> Optional[str]:
    """Walk common Linux locations to find a usable CA certificate bundle.

    Different Linux distributions store their root certificate bundle in
    different places. We probe the four most common locations and use
    the first one that exists. If none do, we return None and the caller
    can fall back to a system default or skip TLS verification.
    """
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
    """Build the MySQL connector SSL keyword arguments from environment.

    Local dev usually points at a plain MySQL on localhost (no TLS),
    so we default to "SSL disabled". To talk to a hosted database that
    requires TLS (TiDB Cloud Serverless, Aiven, etc.) you set
    DB_SSL_DISABLED=false in your env and we then:
        - Find a CA bundle (DB_SSL_CA env var wins, otherwise we search
          the system).
        - Tell the connector to verify both the certificate and that
          the hostname matches the certificate.

    Returns an empty dict in the disabled case so the caller can simply
    `**kwargs` it into `mysql.connector.connect(...)` either way.
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
    """Bundle every connection parameter MySQL needs into one dict.

    All values can be overridden via DB_HOST / DB_USER / DB_PASSWORD /
    DB_NAME / DB_PORT environment variables — the defaults are only
    sensible for a freshly-installed local MySQL.
    """
    config: Dict[str, Any] = {
        "host": os.getenv("DB_HOST", "localhost"),
        "user": os.getenv("DB_USER", "root"),
        "password": os.getenv("DB_PASSWORD", ""),
        "database": os.getenv("DB_NAME", "crimevision_db"),
        "port": int(os.getenv("DB_PORT", "3306")),
    }
    # Merge in TLS settings only if the env says we should use them.
    config.update(get_db_ssl_kwargs())
    return config
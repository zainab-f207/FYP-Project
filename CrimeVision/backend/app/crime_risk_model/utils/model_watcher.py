"""
model_watcher.py
================
Background thread that monitors the crimes database for new data and
automatically retrains the Random Forest model when thresholds are exceeded.

Retraining triggers (ANY one is sufficient):
  • RETRAIN_THRESHOLD_NEW_CRIMES      — 500 new crime rows since last training
  • RETRAIN_THRESHOLD_NEW_AREAS       — 5 areas not seen during last training
  • RETRAIN_THRESHOLD_NEW_CRIME_TYPES — 10 crime types not seen during last training

After a successful retrain the model is hot-reloaded in memory without
restarting the server by calling all registered reload callbacks.

Usage in crimes.py:
    from utils.model_watcher import get_watcher, register_reload_callback

    def _reload():
        global _crm_model, _crm_scaler, _crm_artifacts
        _crm_model, _crm_scaler, _crm_artifacts = _crm_load_model(...)
    register_reload_callback(_reload)

    # After creating a crime:
    get_watcher().notify_new_crime(area, crime_type)

    # At startup:
    get_watcher().start()
"""

import os
import sys
import json
import logging
import threading
import subprocess
import time
from datetime import datetime
from typing import Any, Dict

from app.core.database import get_db_connection

logger = logging.getLogger(__name__)

# ── Thresholds ────────────────────────────────────────────────────────────────
DEFAULT_RETRAIN_THRESHOLD_NEW_CRIMES      = 500   # new rows since last training
DEFAULT_RETRAIN_THRESHOLD_NEW_AREAS       = 5     # brand-new areas
DEFAULT_RETRAIN_THRESHOLD_NEW_CRIME_TYPES = 10    # brand-new crime types
DEFAULT_CHECK_INTERVAL_SECONDS            = 3600  # periodic check every 60 min
DEFAULT_RETRAIN_TIMEOUT_SECONDS           = 600   # retrain subprocess timeout


def _load_system_setting_ints(defaults: Dict[str, int]) -> Dict[str, int]:
    """Load integer settings in one query and fall back to provided defaults."""
    conn = None
    cursor = None
    resolved = dict(defaults)
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        keys = list(defaults.keys())
        placeholders = ','.join(['%s'] * len(keys))
        cursor.execute(
            f"SELECT setting_key, setting_value FROM system_settings WHERE setting_key IN ({placeholders})",
            tuple(keys),
        )
        rows = cursor.fetchall() or []
        for row in rows:
            key = row.get('setting_key')
            if key in resolved:
                try:
                    resolved[key] = int(row.get('setting_value'))
                except Exception:
                    pass
    except Exception:
        pass
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()
    return resolved

# ── Paths ─────────────────────────────────────────────────────────────────────
_UTILS_DIR    = os.path.dirname(__file__)
_MODEL_DIR    = os.path.normpath(os.path.join(_UTILS_DIR, '..', 'models'))
_TRAIN_SCRIPT = os.path.normpath(os.path.join(_UTILS_DIR, '..', 'train_model.py'))
_ARTIFACTS    = os.path.join(_MODEL_DIR, 'model_artifacts.json')

# ── Callback registry ─────────────────────────────────────────────────────────
_reload_callbacks: list = []


def register_reload_callback(fn):
    """Register a callable that the watcher invokes after every successful retrain."""
    if fn not in _reload_callbacks:
        _reload_callbacks.append(fn)


# ── Singleton instance ────────────────────────────────────────────────────────
_watcher_instance = None
_watcher_lock     = threading.Lock()


def get_watcher() -> 'ModelWatcher':
    """Return the singleton ModelWatcher (creates it if needed)."""
    global _watcher_instance
    if _watcher_instance is None:
        with _watcher_lock:
            if _watcher_instance is None:
                _watcher_instance = ModelWatcher()
    return _watcher_instance


# ── Main class ────────────────────────────────────────────────────────────────

class ModelWatcher:
    """
    Thread-safe manager that:
      1. Tracks unseen areas/crime_types since last training.
      2. Periodically checks the DB for new crime rows.
      3. Triggers background retraining when thresholds are exceeded.
      4. Hot-reloads the model in the server process after retraining.
    """

    def __init__(self):
        self._lock          = threading.Lock()
        self._retraining    = False
        self._thread        = None
        self._stop_event    = threading.Event()
        self._runtime_config_cache: Dict[str, int] | None = None
        self._runtime_config_ts: float = 0.0

        # Counters (reset after successful retrain)
        self._new_crimes_since_train     = 0
        self._new_areas_since_train:     set = set()
        self._new_types_since_train:     set = set()

        # Load known sets from saved artifacts
        self._known_areas: set  = set()
        self._known_types: set  = set()
        self._training_sample_count: int = 0
        self._last_trained_at: datetime | None = None

        self._load_known_from_artifacts()

    def _get_runtime_config(self) -> Dict[str, int]:
        """Return runtime thresholds/intervals from system settings with a short cache TTL."""
        now = time.time()
        if self._runtime_config_cache and (now - self._runtime_config_ts) < 60:
            return self._runtime_config_cache

        values = _load_system_setting_ints({
            'model_watcher_retrain_threshold_new_crimes': DEFAULT_RETRAIN_THRESHOLD_NEW_CRIMES,
            'model_watcher_retrain_threshold_new_areas': DEFAULT_RETRAIN_THRESHOLD_NEW_AREAS,
            'model_watcher_retrain_threshold_new_crime_types': DEFAULT_RETRAIN_THRESHOLD_NEW_CRIME_TYPES,
            'model_watcher_check_interval_seconds': DEFAULT_CHECK_INTERVAL_SECONDS,
            'model_watcher_retrain_timeout_seconds': DEFAULT_RETRAIN_TIMEOUT_SECONDS,
        })

        cfg = {
            'retrain_threshold_new_crimes': max(1, min(1_000_000, int(values['model_watcher_retrain_threshold_new_crimes']))),
            'retrain_threshold_new_areas': max(1, min(100_000, int(values['model_watcher_retrain_threshold_new_areas']))),
            'retrain_threshold_new_crime_types': max(1, min(100_000, int(values['model_watcher_retrain_threshold_new_crime_types']))),
            'check_interval_seconds': max(10, min(86_400, int(values['model_watcher_check_interval_seconds']))),
            'retrain_timeout_seconds': max(30, min(7_200, int(values['model_watcher_retrain_timeout_seconds']))),
        }

        self._runtime_config_cache = cfg
        self._runtime_config_ts = now
        return cfg

    # ──────────────────────────────────────────────────────────────────────────

    def _load_known_from_artifacts(self):
        """Read model_artifacts.json to establish baseline known sets."""
        try:
            with open(_ARTIFACTS, 'r', encoding='utf-8') as f:
                arts = json.load(f)
            self._known_areas  = {
                str(area).strip().lower()
                for area in arts.get('area_freq_map', {}).keys()
                if str(area).strip()
            }
            self._known_types  = {
                str(crime_type).strip().lower()
                for crime_type in arts.get('combined_severity_map', {}).keys()
                if str(crime_type).strip()
            }
            self._training_sample_count = int(arts.get('n_training_samples', 0))
            ts = arts.get('trained_at')
            if ts:
                try:
                    self._last_trained_at = datetime.fromisoformat(ts)
                except Exception:
                    self._last_trained_at = None
            logger.info(
                "ModelWatcher: loaded %d known areas, %d known types from artifacts",
                len(self._known_areas), len(self._known_types),
            )
        except Exception as e:
            logger.warning("ModelWatcher: could not read artifacts (%s) — using empty baseline", e)

    # ──────────────────────────────────────────────────────────────────────────

    def notify_new_crime(self, area: str, crime_type: str):
        """
        Called after every new crime is inserted into the DB.
        Increments counters and triggers a retrain if thresholds are hit.
        """
        with self._lock:
            self._new_crimes_since_train += 1
            area_key = (area or '').lower().strip()
            type_key = (crime_type or '').lower().strip()
            if area_key and area_key not in self._known_areas:
                self._new_areas_since_train.add(area_key)
            if type_key and type_key not in self._known_types:
                self._new_types_since_train.add(type_key)

            should = self._should_retrain()

        if should:
            logger.info(
                "ModelWatcher: retrain threshold reached "
                "(+%d crimes, %d new areas, %d new types)",
                self._new_crimes_since_train,
                len(self._new_areas_since_train),
                len(self._new_types_since_train),
            )
            self._trigger_retrain()

    # ──────────────────────────────────────────────────────────────────────────

    def _should_retrain(self) -> bool:
        """Check whether any threshold has been crossed. Must be called under lock."""
        if self._retraining:
            return False
        cfg = self._get_runtime_config()
        return (
            self._new_crimes_since_train >= cfg['retrain_threshold_new_crimes']
            or len(self._new_areas_since_train) >= cfg['retrain_threshold_new_areas']
            or len(self._new_types_since_train) >= cfg['retrain_threshold_new_crime_types']
        )

    # ──────────────────────────────────────────────────────────────────────────

    def _trigger_retrain(self):
        """Spawn a background thread to retrain without blocking requests."""
        with self._lock:
            if self._retraining:
                return
            self._retraining = True
        t = threading.Thread(target=self._run_retrain, daemon=True,
                             name='ModelRetrainWorker')
        t.start()

    # ──────────────────────────────────────────────────────────────────────────

    def _run_retrain(self):
        """Execute train_model.py in a subprocess, then hot-reload."""
        logger.info("ModelWatcher: starting background retrain …")
        try:
            # Determine the Python executable (same one running the server)
            python_exe = sys.executable

            result = subprocess.run(
                [python_exe, _TRAIN_SCRIPT],
                capture_output=True,
                text=True,
                timeout=self._get_runtime_config()['retrain_timeout_seconds'],
                cwd=os.path.dirname(_TRAIN_SCRIPT),
            )

            if result.returncode != 0:
                logger.error(
                    "ModelWatcher: retrain subprocess failed (rc=%d):\n%s",
                    result.returncode, result.stderr[-2000:],
                )
                return

            logger.info("ModelWatcher: retrain subprocess succeeded.\n%s",
                        result.stdout[-1000:])

            # Hot-reload artifacts and update known sets
            self._load_known_from_artifacts()

            # Reset counters
            with self._lock:
                self._new_crimes_since_train = 0
                self._new_areas_since_train.clear()
                self._new_types_since_train.clear()

            # Call all registered reload callbacks (reload model in crimes.py etc.)
            for cb in list(_reload_callbacks):
                try:
                    cb()
                except Exception as e:
                    logger.error("ModelWatcher: reload callback %s raised: %s", cb, e)

            logger.info("ModelWatcher: model hot-reloaded successfully ✓")

        except subprocess.TimeoutExpired:
            logger.error(
                "ModelWatcher: retrain subprocess timed out after %s s",
                self._get_runtime_config()['retrain_timeout_seconds'],
            )
        except Exception as e:
            logger.error("ModelWatcher: retrain failed — %s", e, exc_info=True)
        finally:
            with self._lock:
                self._retraining = False

    # ──────────────────────────────────────────────────────────────────────────

    def _periodic_check(self):
        """
        Background thread body: periodically poll the DB for new crime count
        and fire retrain if thresholds are reached.
        """
        interval_seconds = self._get_runtime_config()['check_interval_seconds']
        logger.info("ModelWatcher: periodic check thread started (interval=%ds)", interval_seconds)
        while True:
            interval_seconds = self._get_runtime_config()['check_interval_seconds']
            if self._stop_event.wait(timeout=interval_seconds):
                break
            try:
                self._db_check()
            except Exception as e:
                logger.warning("ModelWatcher: periodic DB check error — %s", e)

    def _db_check(self):
        """Query DB for total crime count; trigger retrain if growth is large."""
        try:
            import mysql.connector
            from dotenv import load_dotenv
            load_dotenv()

            db_cfg = {
                'host':     os.getenv('DB_HOST', 'localhost'),
                'user':     os.getenv('DB_USER', 'root'),
                'password': os.getenv('DB_PASSWORD', 'hafsa555'),
                'database': os.getenv('DB_NAME', 'crimevision_db'),
                'port':     int(os.getenv('DB_PORT', 3306)),
            }
            conn   = mysql.connector.connect(**db_cfg)
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT COUNT(*) AS cnt FROM crimes")
            total  = cursor.fetchone()['cnt']

            # New areas since training
            cursor.execute("SELECT DISTINCT LOWER(area) AS a FROM crimes WHERE area IS NOT NULL")
            db_areas = {r['a'] for r in cursor.fetchall() if r['a']}

            # New crime types since training
            cursor.execute("SELECT DISTINCT LOWER(crime_type) AS t FROM crimes WHERE crime_type IS NOT NULL")
            db_types = {r['t'] for r in cursor.fetchall() if r['t']}

            cursor.close()
            conn.close()

            new_since_train = max(0, total - self._training_sample_count)
            new_areas       = db_areas - self._known_areas
            new_types       = db_types - self._known_types

            logger.debug(
                "ModelWatcher DB check: total=%d, +%d new crimes, %d new areas, %d new types",
                total, new_since_train, len(new_areas), len(new_types),
            )

            with self._lock:
                self._new_crimes_since_train     = new_since_train
                self._new_areas_since_train      = new_areas
                self._new_types_since_train      = new_types
                should = self._should_retrain()

            if should:
                logger.info(
                    "ModelWatcher: periodic check hit threshold — triggering retrain "
                    "(+%d crimes, %d areas, %d types)",
                    new_since_train, len(new_areas), len(new_types),
                )
                self._trigger_retrain()
            else:
                logger.info(
                    "ModelWatcher: periodic check found no retrain condition "
                    "(+%d crimes, %d areas, %d types)",
                    new_since_train, len(new_areas), len(new_types),
                )

        except Exception as e:
            raise RuntimeError(f"DB check failed: {e}") from e

    # ──────────────────────────────────────────────────────────────────────────

    def start(self):
        """Start the periodic background check thread (idempotent)."""
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._periodic_check,
            daemon=True,
            name='ModelWatcher',
        )
        self._thread.start()
        logger.info("ModelWatcher: started (check every %ds)", self._get_runtime_config()['check_interval_seconds'])

    def stop(self):
        """Signal the watcher thread to stop gracefully."""
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=5)

    def status(self) -> dict:
        """Return current watcher state (useful for health/debug endpoints)."""
        cfg = self._get_runtime_config()
        with self._lock:
            return {
                'retraining':               self._retraining,
                'new_crimes_since_train':   self._new_crimes_since_train,
                'new_areas_since_train':    list(self._new_areas_since_train),
                'new_types_since_train':    list(self._new_types_since_train),
                'known_areas_count':        len(self._known_areas),
                'known_types_count':        len(self._known_types),
                'training_sample_count':    self._training_sample_count,
                'thresholds': {
                    'crimes':      cfg['retrain_threshold_new_crimes'],
                    'areas':       cfg['retrain_threshold_new_areas'],
                    'crime_types': cfg['retrain_threshold_new_crime_types'],
                },
                'check_interval_seconds': cfg['check_interval_seconds'],
                'retrain_timeout_seconds': cfg['retrain_timeout_seconds'],
            }

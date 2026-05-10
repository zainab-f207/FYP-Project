"""
Auto-Retrain Guard for Crime Risk Models
==========================================
Solves the "new data breaks predictions" problem without manual intervention.

How it works
------------
1. Every time a new crime record is approved and written to the DB, call
   ``notify_new_record(area, crime_type)``.
2. This function checks whether those feature values were seen during the last
   training run.  Unseen values (OOV = Out-Of-Vocabulary) are tracked in a
   lightweight JSON counter file (``oov_counts.json`` in the models folder).
3. When the OOV counter crosses a configurable threshold (default: 20 new
   unseen area/crime_type combinations, OR 50 new records total since last
   retrain), a background thread silently retrains the model and calls the
   registered hot-reload callback so the live server picks up the new model
   within seconds — with zero downtime.

Why this is safe
----------------
* Retraining runs in a daemon thread — the API stays responsive.
* A file-lock prevents two concurrent retrains from clobbering each other.
* The hot-reload callback (registered in crimes.py) atomically swaps the
  in-memory model objects, so no request sees a half-loaded model.
* If retraining fails for any reason, the old model continues to serve
  predictions until the next successful retrain.

How the Poisson model handles OOV vs the Random Forest
-------------------------------------------------------
| Model          | New area | New crime_type | New date | New time |
|----------------|----------|----------------|----------|----------|
| Poisson        | Uses     | Uses global    | Normal-  | Hour     |
|                | global λ | λ fallback     | ises via | multi-   |
|                |          |                | month    | plier    |
| Random Forest  | UNKNOWN  | UNKNOWN        | Fine     | Fine     |
|                | class →  | class →        |          |          |
|                | fallback | fallback       |          |          |

The Poisson model degrades gracefully (Laplace-smoothed fallback to global
rate for unknowns) — it will NEVER crash on new areas/crime types.
The RF model uses ``_best_label_match`` so it does a substring match before
giving up.  After retraining it inherits the new vocabulary from the DB.
"""

import json
import logging
import os
import threading
import time
from typing import Callable, Dict, Optional, Set

from app.core.database import get_db_connection

logger = logging.getLogger(__name__)

# ── Config ────────────────────────────────────────────────────────────────────

# Path to the counter file — stored beside the model artifacts
_MODELS_DIR = os.path.join(os.path.dirname(__file__), '..', 'models')
_COUNTER_FILE = os.path.join(_MODELS_DIR, 'oov_counts.json')
_LOCK_FILE    = os.path.join(_MODELS_DIR, '_retrain.lock')

# Thresholds that trigger a retrain
DEFAULT_OOV_PAIR_THRESHOLD   = 10   # new unseen (area, crime_type) combos since last train
DEFAULT_NEW_RECORD_THRESHOLD = 10   # total new records since last retrain (even if no OOV)

# Minimum gap between automatic retrains (seconds) — avoids thrashing
DEFAULT_MIN_RETRAIN_INTERVAL = 3600  # 1 hour

# ── Module-level state ────────────────────────────────────────────────────────

_reload_callback: Optional[Callable] = None   # set by register_reload_callback()
_retrain_lock = threading.Lock()
_last_retrain_ts: float = 0.0
_runtime_config_cache: Optional[Dict[str, int]] = None
_runtime_config_ts: float = 0.0

# Known values cached in memory to avoid reading the JSON on every API call
_known_areas:        Optional[Set[str]] = None
_known_crime_types:  Optional[Set[str]] = None


def _load_system_setting_ints(defaults: Dict[str, int]) -> Dict[str, int]:
    """Load integer system settings in one query with default fallbacks."""
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


def _get_runtime_config() -> Dict[str, int]:
    """Return runtime auto-retrain thresholds with short-lived cache."""
    global _runtime_config_cache, _runtime_config_ts
    now = time.time()
    if _runtime_config_cache and (now - _runtime_config_ts) < 60:
        return _runtime_config_cache

    values = _load_system_setting_ints({
        'auto_retrain_oov_pair_threshold': DEFAULT_OOV_PAIR_THRESHOLD,
        'auto_retrain_new_record_threshold': DEFAULT_NEW_RECORD_THRESHOLD,
        'auto_retrain_min_interval_seconds': DEFAULT_MIN_RETRAIN_INTERVAL,
    })

    cfg = {
        'oov_pair_threshold': max(1, min(100_000, int(values['auto_retrain_oov_pair_threshold']))),
        'new_record_threshold': max(1, min(1_000_000, int(values['auto_retrain_new_record_threshold']))),
        'min_retrain_interval_seconds': max(30, min(86_400, int(values['auto_retrain_min_interval_seconds']))),
    }
    _runtime_config_cache = cfg
    _runtime_config_ts = now
    return cfg


# ── Public API ────────────────────────────────────────────────────────────────

def register_reload_callback(fn: Callable) -> None:
    """Call this at startup with the hot-reload function from crimes.py."""
    global _reload_callback
    _reload_callback = fn
    logger.info("[auto_retrain] hot-reload callback registered")


def notify_new_record(area: str, crime_type: str) -> None:
    """
    Should be called every time a new crime record enters the database.
    Non-blocking — all heavy work happens in a background thread.
    """
    threading.Thread(
        target=_check_and_maybe_retrain,
        args=(area, crime_type),
        daemon=True,
        name="auto-retrain-check",
    ).start()


def get_oov_status() -> dict:
    """Return current OOV counters — used by the admin endpoint."""
    return _load_counters()


# ── Internal helpers ──────────────────────────────────────────────────────────

def _load_known_sets() -> tuple[Set[str], Set[str]]:
    """
    Return (known_areas, known_crime_types) extracted from Poisson artifacts
    and RF label-encoder artifacts.  Cached after first load; refreshed after
    each retrain.
    """
    global _known_areas, _known_crime_types
    if _known_areas is not None:
        return _known_areas, _known_crime_types  # type: ignore[return-value]

    areas: Set[str] = set()
    crimes: Set[str] = set()

    # Try Poisson artifacts first (richest source)
    poisson_path = os.path.join(_MODELS_DIR, 'poisson_artifacts.json')
    if os.path.exists(poisson_path):
        try:
            with open(poisson_path, 'r', encoding='utf-8') as f:
                pa = json.load(f)
            for key in pa.get('pair_lambdas', {}):
                parts = key.split('|||')
                if len(parts) == 2:
                    areas.add(parts[0].strip().lower())
                    crimes.add(parts[1].strip().lower())
            for a in pa.get('known_areas', []):
                areas.add(a.strip().lower())
        except Exception as e:
            logger.warning("[auto_retrain] Could not read Poisson artifacts: %s", e)

    # Try RF artifacts (crime_type_map, area_map)
    artifacts_path = os.path.join(_MODELS_DIR, 'model_artifacts.json')
    if os.path.exists(artifacts_path):
        try:
            with open(artifacts_path, 'r', encoding='utf-8') as f:
                art = json.load(f)
            for a in art.get('area_map', {}).keys():
                areas.add(str(a).strip().lower())
            for c in art.get('crime_type_map', {}).keys():
                crimes.add(str(c).strip().lower())
        except Exception as e:
            logger.warning("[auto_retrain] Could not read RF artifacts: %s", e)

    _known_areas       = areas
    _known_crime_types = crimes
    logger.debug("[auto_retrain] Loaded %d known areas, %d known crime types",
                 len(areas), len(crimes))
    return areas, crimes


def _load_counters() -> dict:
    if os.path.exists(_COUNTER_FILE):
        try:
            with open(_COUNTER_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return {
        'oov_pairs': [],        # list of "area|||crime_type" strings not seen in training
        'new_records': 0,       # total new records since last retrain
        'last_retrain': 0.0,    # unix timestamp of last automatic retrain
        'retrain_count': 0,
    }


def _save_counters(data: dict) -> None:
    os.makedirs(_MODELS_DIR, exist_ok=True)
    try:
        with open(_COUNTER_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        logger.warning("[auto_retrain] Failed to save counters: %s", e)


def _is_oov(area: str, crime_type: str) -> bool:
    known_a, known_c = _load_known_sets()
    a = area.strip().lower()
    c = crime_type.strip().lower()
    # Exact match first
    if a in known_a and c in known_c:
        return False
    # Substring toleration (same logic as _best_label_match)
    area_found  = a in known_a or any(a in ka or ka in a for ka in known_a)
    crime_found = c in known_c or any(c in kc or kc in c for kc in known_c)
    return not (area_found and crime_found)


def _check_and_maybe_retrain(area: str, crime_type: str) -> None:
    """Runs in a background thread.  Updates counters and triggers retrain if needed."""
    global _last_retrain_ts, _known_areas, _known_crime_types

    if not _retrain_lock.acquire(blocking=False):
        return  # another check is already running

    try:
        counters = _load_counters()
        counters['new_records'] = counters.get('new_records', 0) + 1

        pair_key = f"{area.strip()}|||{crime_type.strip()}"
        is_new_oov = _is_oov(area, crime_type)

        if is_new_oov:
            oov_list: list = counters.get('oov_pairs', [])
            if pair_key not in oov_list:
                oov_list.append(pair_key)
                counters['oov_pairs'] = oov_list
                logger.info("[auto_retrain] OOV pair detected: %s  (total OOV: %d)",
                            pair_key, len(oov_list))

        _save_counters(counters)

        # Decide whether to retrain
        oov_count    = len(counters.get('oov_pairs', []))
        new_records  = counters.get('new_records', 0)
        last_retrain = counters.get('last_retrain', 0.0)
        now          = time.time()
        cfg = _get_runtime_config()
        time_ok      = (now - last_retrain) >= cfg['min_retrain_interval_seconds']

        should_retrain = time_ok and (
            oov_count  >= cfg['oov_pair_threshold'] or
            new_records >= cfg['new_record_threshold']
        )

        if should_retrain:
            logger.info(
                "[auto_retrain] Threshold crossed (OOV=%d/%d, new=%d/%d) — "
                "launching background retrain…",
                oov_count, cfg['oov_pair_threshold'], new_records, cfg['new_record_threshold'],
            )
            _run_retrain(counters)

    except Exception as e:
        logger.error("[auto_retrain] Unexpected error in check: %s", e, exc_info=True)
    finally:
        _retrain_lock.release()


def _run_retrain(counters: dict) -> None:
    """Execute the full training pipeline and hot-reload models."""
    global _known_areas, _known_crime_types, _last_retrain_ts

    # Prevent concurrent retrains via a file lock
    lock_acquired = False
    try:
        if os.path.exists(_LOCK_FILE):
            logger.warning("[auto_retrain] Another retrain is already running — skipping.")
            return
        with open(_LOCK_FILE, 'w') as lf:
            lf.write(str(os.getpid()))
        lock_acquired = True

        logger.info("[auto_retrain] ⚙️  Retraining models with latest DB data…")
        t0 = time.time()

        # Import and run the training pipeline
        import sys
        _crm_dir = os.path.join(os.path.dirname(__file__), '..')
        if _crm_dir not in sys.path:
            sys.path.insert(0, _crm_dir)

        from train_model import train_crime_risk_model  # type: ignore
        train_crime_risk_model()

        elapsed = time.time() - t0
        logger.info("[auto_retrain] ✅ Retrain complete in %.1f s", elapsed)

        # Reset counters
        counters['oov_pairs']     = []
        counters['new_records']   = 0
        counters['last_retrain']  = time.time()
        counters['retrain_count'] = counters.get('retrain_count', 0) + 1
        _save_counters(counters)

        # Invalidate in-memory known-sets caches so they reload from new artifacts
        _known_areas = None
        _known_crime_types = None
        _last_retrain_ts = time.time()

        # Hot-reload the in-memory model — zero downtime
        if _reload_callback:
            try:
                _reload_callback()
                logger.info("[auto_retrain] 🔄 In-memory models hot-reloaded successfully")
            except Exception as cb_err:
                logger.error("[auto_retrain] hot-reload callback failed: %s", cb_err)

    except Exception as e:
        logger.error("[auto_retrain] ❌ Retrain failed: %s", e, exc_info=True)
    finally:
        if lock_acquired and os.path.exists(_LOCK_FILE):
            os.remove(_LOCK_FILE)

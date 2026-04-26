"""
Crime Risk Model - Helpers
==========================
Feature engineering, rule-based label generation, model persistence,
and database utilities.

Why rule-based labels?
  The crimes table had no verified ground-truth risk labels (all defaulted
  to Medium from K-Means). We generate deterministic labels from a weighted
  scoring formula so the Random Forest has real signal to learn from.
"""

import os
import json
import logging

import numpy as np
import pandas as pd
import joblib
import mysql.connector
from mysql.connector import Error
from sklearn.preprocessing import MinMaxScaler
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)


# ── Severity map ─────────────────────────────────────────────────────────────

def load_severity_map(config_path=None):
    """Load the manual crime-type severity mapping (1-10 scale)."""
    if config_path is None:
        config_path = os.path.join(
            os.path.dirname(__file__), '..', 'config', 'severity_map.json'
        )
    with open(config_path, 'r') as f:
        data = json.load(f)
    return {k.lower(): v for k, v in data.items()}


def calculate_auto_severity(df):
    """
    Derive severity from rarity: rarer crime types get higher auto-severity
    because they are under-reported and likely under-policed.
    """
    crime_type_freq = df['crime_type'].str.lower().value_counts()
    crime_type_freq = crime_type_freq.replace(0, 1)
    rarity_series = 1.0 / crime_type_freq
    scaler = MinMaxScaler(feature_range=(2, 10))
    auto_severity_map = pd.Series(
        scaler.fit_transform(rarity_series.values.reshape(-1, 1)).flatten(),
        index=rarity_series.index
    ).to_dict()
    return auto_severity_map


def get_combined_severity_map(df, manual_map):
    """
    Merge auto-derived and manual severity maps.
    Manual values (human expert knowledge) always override auto values.
    """
    auto_map = calculate_auto_severity(df)
    combined = {**auto_map, **manual_map}
    return combined


# ── Keyword-based severity inference for unknown crime types ─────────────────
# Ordered from most severe to least — first matching keyword wins.
_KEYWORD_SEVERITY_RULES = [
    # Score 10 — life-threatening / extreme violence
    (10, ['murder', 'kill', 'homicide', 'qatl', 'massacre', 'slaughter',
          'genocide', 'acid', 'rape', 'gang rape', 'terrorist', 'terrorism',
          'bomb', 'explosion', 'blast', 'assassination', 'execution',
          'torture', 'beheading']),
    # Score 9 — serious violence / organised crime / causing death
    (9,  ['kidnap', 'abduct', 'trafficking', 'ransom', 'hostage',
          'armed robbery', 'dacoity', 'extortion', 'carjacking',
          'honour killing', 'forced marriage', 'sedition', 'waging war',
          'attempt to murder', 'attempted murder', 'causing death',
          'culpable homicide', 'rash driving causing death']),
    # Score 8 — violent assault / serious bodily harm / fire / weapons
    (8,  ['assault', 'attack', 'grievous hurt', 'grievous', 'stab',
          'shoot', 'shot', 'firing', 'gunshot', 'arson', 'fire',
          'blasphemy', 'religious', 'mutiny', 'riot', 'rioting',
          'armed', 'weapon', 'explosive', 'mischief by fire',
          'preparation for causing death']),
    # Score 7 — causing hurt / robbery / drugs / threats
    (7,  ['robbery', 'snatch', 'snatching', 'drug', 'narcotic',
          'smuggling', 'intimidate', 'intimidation',
          'threatening', 'blackmail', 'sexual harassment', 'harassment',
          'stalking', 'perjury', 'false evidence',
          'causing hurt', 'voluntarily causing hurt', 'simple hurt']),
    # Score 6 — burglary / corruption / fraud / force
    (6,  ['burglary', 'house breaking', 'break-in', 'trespass',
          'bribery', 'corruption', 'fraud', 'cyber', 'hacking', 'scam',
          'impersonation', 'domestic violence', 'outraging modesty',
          'attempt', 'criminal force', 'criminal intimidation',
          'lurking house trespass']),
    # Score 5 — property / financial crime
    (5,  ['theft', 'stealing', 'stolen', 'pickpocket', 'shoplifting',
          'cheating', 'forgery', 'counterfeit', 'embezzlement',
          'misappropriation', 'breach of trust',
          'dishonest', 'wrongful gain', 'wrongful loss']),
    # Score 4 — minor / personal liberty / petty offences
    (4,  ['vandalism', 'damage', 'mischief', 'defamation', 'slander',
          'nuisance', 'disorderly', 'loitering', 'trespassing',
          'begging', 'gambling',
          'wrongful restraint', 'wrongful confinement', 'restraint',
          'confinement', 'civil wrong', 'abetment', 'public nuisance']),
    # Score 3 — trivial / regulatory / administrative
    (3,  ['traffic', 'parking', 'signal', 'noise', 'littering',
          'violation', 'minor', 'petty', 'punishment for',
          'whoever commits', 'imprisonment for']),
]


def infer_severity_from_keywords(crime_type: str):
    """
    Infer a severity score for an unknown crime type using keyword matching.
    Returns a float score (1-10) if a keyword matches, or None if no match.
    """
    ct_lower = crime_type.lower().strip()
    for score, keywords in _KEYWORD_SEVERITY_RULES:
        if any(kw in ct_lower for kw in keywords):
            return float(score)
    return None


def _get_severity_config_path():
    return os.path.join(os.path.dirname(__file__), '..', 'config', 'severity_map.json')


def auto_save_new_severity(crime_type: str, score: float):
    """
    Persist a newly inferred crime type to severity_map.json so it is
    remembered on next training run and doesn't need keyword matching again.
    """
    config_path = _get_severity_config_path()
    try:
        with open(config_path, 'r') as f:
            data = json.load(f)
        key = crime_type.lower().strip()
        if key not in {k.lower() for k in data}:
            data[key] = score
            with open(config_path, 'w') as f:
                json.dump(data, f, indent=4)
            logger.info("Auto-saved new crime type '%s' with severity %.1f to severity_map.json", key, score)
    except Exception as e:
        logger.warning("Could not auto-save severity for '%s': %s", crime_type, e)


# ── Feature engineering ──────────────────────────────────────────────────────

def engineer_features(df, combined_severity_map=None, df_full=None,
                       area_freq_map=None, area_freq_median=None):
    """
    Build the feature matrix from raw crime records.

    Parameters
    ----------
    df                    : input DataFrame (may be a new-data subset)
    combined_severity_map : pre-built severity dict  (pass when predicting)
    df_full               : full training DataFrame  (used to build area map)
    area_freq_map         : pre-built area->frequency dict (pass when predicting)
    area_freq_median      : fallback for unknown areas (from training artifacts)

    Returns
    -------
    X   : DataFrame of feature columns ready for the scaler
    df  : processed DataFrame with all intermediate columns attached
    """
    df = df.copy()

    # 1. Crime severity --------------------------------------------------------
    if combined_severity_map is None:
        manual_map = load_severity_map()
        source_df = df_full if df_full is not None else df
        combined_severity_map = get_combined_severity_map(source_df, manual_map)

    # Load the manual map fresh so keyword overrides are always applied even
    # when predicting against artifacts built in an earlier training run.
    _manual_map_lower = {k.lower(): v for k, v in load_severity_map().items()}
    severity_median = float(np.median(list(combined_severity_map.values())))

    def _resolve_severity(crime_type_raw):
        ct = str(crime_type_raw).lower().strip()
        # 1. Manual severity map — human-reviewed PPC/keyword labels (highest priority)
        if ct in _manual_map_lower:
            return _manual_map_lower[ct]
        # 2. Keyword-based semantic inference — meaningful even for unseen long names
        #    (e.g. "Mischief by Fire..." → 8 via 'mischief by fire', 'explosive')
        inferred = infer_severity_from_keywords(ct)
        if inferred is not None:
            auto_save_new_severity(ct, inferred)
            return inferred
        # 3. Frequency-derived value from training data (treats rarity as danger proxy)
        #    Only reached for crime types that genuinely didn't match any keyword.
        if ct in combined_severity_map:
            return combined_severity_map[ct]
        # 4. Last resort: statistical median
        logger.warning("Unknown crime type '%s' — using severity median %.1f", ct, severity_median)
        return severity_median

    df['crime_severity'] = df['crime_type'].apply(_resolve_severity)

    # 2. Temporal features -----------------------------------------------------
    df['crime_date'] = pd.to_datetime(df['crime_date'], errors='coerce')

    # Prefer crime_hour (parsed from crime_time column) over the datetime hour,
    # because crime_date often stores only a date (hour = 0 in that case).
    if 'crime_hour' in df.columns:
        valid_mask = df['crime_hour'].between(0, 23)
        fallback_hour = df['crime_date'].dt.hour.fillna(12).astype(int)
        df['hour'] = df['crime_hour'].where(valid_mask, fallback_hour).astype(int)
    else:
        df['hour']    = df['crime_date'].dt.hour.fillna(12).astype(int)
    df['day_of_week'] = df['crime_date'].dt.dayofweek.fillna(0).astype(int)
    df['month']       = df['crime_date'].dt.month.fillna(6).astype(int)
    df['is_weekend']  = df['day_of_week'].isin([5, 6]).astype(int)

    # Night-time risk window: 10 pm - 4 am
    df['is_nighttime'] = df['hour'].apply(
        lambda h: 1 if h in [22, 23, 0, 1, 2, 3, 4] else 0
    )

    # Continuous time-of-day risk (cosine peaks at midnight)
    df['time_risk'] = np.cos(
        (df['hour'].astype(float) - 2.0) * (2 * np.pi / 24)
    ).clip(0, None)

    # 3. Area crime frequency --------------------------------------------------
    if area_freq_map is None:
        freq_source = df_full if df_full is not None else df
        raw_counts = freq_source['area'].value_counts().to_dict()
        total = max(sum(raw_counts.values()), 1)
        area_freq_map = {k: v / total for k, v in raw_counts.items()}

    if area_freq_median is None:
        area_freq_median = float(np.median(list(area_freq_map.values())))

    # Unknown areas -> median (not 0) so new areas get a sensible default
    df['area_crime_frequency'] = (
        df['area'].map(area_freq_map).fillna(area_freq_median)
    )

    # 4. Area percentile rank (0-100) ------------------------------------------
    all_freqs = sorted(area_freq_map.values())

    def _percentile(freq):
        if not all_freqs:
            return 50.0
        rank = sum(1 for x in all_freqs if x <= freq)
        return round(100.0 * rank / len(all_freqs), 1)

    df['area_freq_percentile'] = df['area_crime_frequency'].apply(_percentile)

    # 5. Final feature matrix --------------------------------------------------
    feature_columns = [
        'crime_severity',
        'hour',
        'day_of_week',
        'month',
        'is_weekend',
        'is_nighttime',
        'time_risk',
        'area_crime_frequency',
        'area_freq_percentile',
        'latitude',
        'longitude',
    ]
    return df[feature_columns], df


# ── Rule-based label generation ──────────────────────────────────────────────

def _risk_score_for_row(severity, hour, is_weekend, area_freq_percentile):
    """
    Normalized composite risk score in the range [0.0, 1.0].

    Each component is independently scaled to [0, 1] before weighting so that
    no single feature dominates by magnitude.

    Weights (sum to 1.0):
      0.40  crime severity     (normalized from 3-10 range)
      0.25  time of day        (night=1.0, evening=0.65, early-morning=0.35, day=0.0)
      0.25  area hotspot rank  (area_freq_percentile / 100)
      0.10  weekend            (weekend=0.10, weekday=0.0)

    Returns a float in [0.0, 1.0].
    """
    # -- component 1: severity (design range 3-10, but clamp to same)
    sev_norm = float(np.clip((severity - 3.0) / 7.0, 0.0, 1.0))

    # -- component 2: time of day (night is highest risk)
    if hour in [22, 23, 0, 1, 2, 3, 4]:
        time_norm = 1.0    # late night / small hours
    elif hour in [5, 20, 21]:
        time_norm = 0.65   # early morning / late evening
    elif hour in [6, 7, 18, 19]:
        time_norm = 0.35   # morning / evening commute
    else:
        time_norm = 0.0    # daytime

    # -- component 3: area hotspot rank
    area_norm = float(area_freq_percentile) / 100.0

    # -- component 4: weekend
    wknd_norm = 0.10 if is_weekend else 0.0

    # -- weighted composite
    score = (sev_norm * 0.40
             + time_norm * 0.25
             + area_norm * 0.25
             + wknd_norm)          # already 0.10 weight baked in

    return float(np.clip(score, 0.0, 1.0))


def compute_risk_labels(df):
    """
    Assign High / Medium / Low labels to a processed DataFrame.
    These become training targets for the Random Forest classifier.

    Thresholds are computed dynamically from the actual score distribution
    so each run produces a balanced label set regardless of dataset shifts:
      top 30% of scores     ->  High
      bottom 25% of scores  ->  Low
      remainder             ->  Medium

    The per-call percentile approach also means that as new severe/mild crime
    types are added the labels self-calibrate rather than drifting all-Medium.
    """
    scores = df.apply(
        lambda r: _risk_score_for_row(
            r['crime_severity'],
            r['hour'],
            r['is_weekend'],
            r['area_freq_percentile'],
        ),
        axis=1,
    )
    df = df.copy()
    df['risk_score'] = scores

    # Dynamic percentile thresholds
    high_thresh = float(np.percentile(scores, 70))   # top 30% → High
    low_thresh  = float(np.percentile(scores, 25))   # bottom 25% → Low
    # Guard: ensure at least a tiny gap between thresholds
    if high_thresh <= low_thresh:
        high_thresh = low_thresh + 1e-6

    logger.info(
        "Risk label thresholds — High: score > %.4f (p70), Low: score <= %.4f (p25)",
        high_thresh, low_thresh,
    )

    def _label(s):
        if s > high_thresh:
            return 'High'
        elif s <= low_thresh:
            return 'Low'
        else:
            return 'Medium'

    df['computed_risk'] = scores.apply(_label)
    return df


def compute_raw_risk_score(processed_row) -> float:
    """
    Return the raw composite risk score (0.0-1.0) for a single processed row.

    ``processed_row`` must be a pandas Series (or dict-like) with pre-computed
    columns: crime_severity, hour, is_weekend, area_freq_percentile.

    This score is used directly as the risk_percentage in the prediction
    response so that the displayed number reflects actual danger factors
    rather than just RF class confidence.
    """
    return _risk_score_for_row(
        float(processed_row['crime_severity']),
        int(processed_row['hour']),
        bool(processed_row['is_weekend']),
        float(processed_row['area_freq_percentile']),
    )


# ── Model persistence ─────────────────────────────────────────────────────────

def save_model(model, scaler, artifacts: dict, filepath=None):
    """
    Persist the RF model, StandardScaler, and training artifacts.

    artifacts must contain:
      combined_severity_map : dict[str, float]
      area_freq_map         : dict[str, float]
      area_freq_median      : float
      severity_median       : float
      label_classes         : list[str]  e.g. ['High', 'Low', 'Medium']
    """
    if filepath is None:
        filepath = os.path.join(os.path.dirname(__file__), '..', 'models')
    os.makedirs(filepath, exist_ok=True)

    joblib.dump(model,  os.path.join(filepath, 'rf_model.pkl'))
    joblib.dump(scaler, os.path.join(filepath, 'scaler.pkl'))
    with open(os.path.join(filepath, 'model_artifacts.json'), 'w') as f:
        json.dump(artifacts, f, indent=2)

    logger.info("Model, scaler and artifacts saved to %s", filepath)


def load_model(filepath=None):
    """
    Load the RF model, StandardScaler, and training artifacts.
    Returns (model, scaler, artifacts_dict).
    """
    if filepath is None:
        filepath = os.path.join(os.path.dirname(__file__), '..', 'models')

    model  = joblib.load(os.path.join(filepath, 'rf_model.pkl'))
    scaler = joblib.load(os.path.join(filepath, 'scaler.pkl'))
    with open(os.path.join(filepath, 'model_artifacts.json'), 'r') as f:
        artifacts = json.load(f)

    return model, scaler, artifacts


# ── Database helpers ──────────────────────────────────────────────────────────

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", ""),
    "database": os.getenv("DB_NAME", "crimevision_db"),
    "port": int(os.getenv("DB_PORT", "3306")),
}
try:
    from app.core.config import get_db_ssl_kwargs
    DB_CONFIG.update(get_db_ssl_kwargs())
except Exception:
    pass  # Standalone script execution outside the app package


def get_db_connection():
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        if conn.is_connected():
            return conn
        raise Exception("Connection object returned but is not connected")
    except Error as e:
        raise Exception(f"Database connection failed: {e}")


def _parse_hour(time_val) -> int:
    """Extract 0-23 hour from various DB time formats.

    Handles:
      "03:22 AM" / "08:53 PM"  → 12-hour with AM/PM
      "21:30:00" / "21:30"     → 24-hour
      datetime.time objects    → .hour attribute
      None / empty string      → returns -1 (unknown)
    """
    if time_val is None:
        return -1
    import datetime as _dt
    if isinstance(time_val, _dt.time):
        return time_val.hour
    s = str(time_val).strip()
    if not s:
        return -1
    # Try 12-hour format first (e.g. "03:22 AM")
    for fmt in ("%I:%M %p", "%I:%M:%S %p"):
        try:
            return _dt.datetime.strptime(s.upper(), fmt).hour
        except ValueError:
            pass
    # Try 24-hour format (e.g. "21:30:00" or "21:30")
    for fmt in ("%H:%M:%S", "%H:%M"):
        try:
            return _dt.datetime.strptime(s, fmt).hour
        except ValueError:
            pass
    return -1


def load_crimes_from_db():
    """Load all crime records from the database into a DataFrame.

    Also loads crime_time and derives a numeric 'hour' column (0-23) so the
    Poisson predictor can build hour-of-day multipliers.
    """
    conn = cursor = None
    try:
        conn   = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT id, area, crime_type, crime_date, crime_time,
                   latitude, longitude, risk_level
            FROM crimes
            ORDER BY id
        """)
        rows = cursor.fetchall()
        df = pd.DataFrame(rows)
        if not df.empty:
            df['crime_hour'] = df['crime_time'].apply(_parse_hour)
        return df
    finally:
        if cursor: cursor.close()
        if conn and conn.is_connected(): conn.close()


def update_risk_levels_in_db(risk_updates):
    """
    Bulk-update risk_level column.
    risk_updates: list of (risk_label, crime_id) tuples.
    """
    conn = cursor = None
    try:
        conn   = get_db_connection()
        cursor = conn.cursor()
        cursor.executemany(
            "UPDATE crimes SET risk_level = %s WHERE id = %s",
            risk_updates,
        )
        conn.commit()
        print(f"Updated {cursor.rowcount} records in database")
    except Exception:
        if conn: conn.rollback()
        raise
    finally:
        if cursor: cursor.close()
        if conn and conn.is_connected(): conn.close()


def update_new_crimes_risk():
    """
    Predict and update risk levels for crimes that still carry the
    placeholder 'Medium' label assigned at insert time.

    Uses the SAVED Random Forest + artifacts -- no re-training required.
    New areas / crime types are handled via median fallback from artifacts.
    """
    conn = cursor = None
    try:
        conn   = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT id, area, crime_type, crime_date, latitude, longitude
            FROM crimes
            WHERE risk_level IS NULL OR risk_level = 'medium' OR risk_level = 'Medium'
            ORDER BY id
        """)
        rows = cursor.fetchall()
        cursor.close()
        conn.close()

        if not rows:
            print("No new (placeholder) crimes found -- nothing to update.")
            return

        df_new = pd.DataFrame(rows)
        print(f"Predicting risk for {len(df_new)} new crime(s)...")

        # Load model and saved training artifacts
        model, scaler, artifacts = load_model()

        combined_severity_map = artifacts['combined_severity_map']
        area_freq_map         = artifacts['area_freq_map']
        area_freq_median      = artifacts['area_freq_median']

        # Engineer features using SAVED maps (not recomputed from new data)
        X_new, df_proc = engineer_features(
            df_new,
            combined_severity_map=combined_severity_map,
            area_freq_map=area_freq_map,
            area_freq_median=area_freq_median,
        )

        X_scaled    = scaler.transform(X_new)
        predictions = model.predict(X_scaled)   # Direct RF classification
        df_proc['final_risk'] = predictions

        risk_updates = list(zip(df_proc['final_risk'], df_proc['id']))
        update_risk_levels_in_db(risk_updates)
        print("New crime risk levels updated successfully.")

    except Exception as e:
        raise Exception(f"update_new_crimes_risk failed: {e}")

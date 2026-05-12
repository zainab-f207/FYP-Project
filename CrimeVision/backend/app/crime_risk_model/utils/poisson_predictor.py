"""
Poisson-based Crime Probability Predictor
==========================================
Replaces the rule-based RF classifier approach with a statistically grounded
probability model.

Why Poisson?
  Crime occurrences on a given day follow a Poisson process:
    P(≥1 crime) = 1 - e^(-λ)
  where λ (lambda) = expected number of that crime type per day in that area,
  adjusted for day-of-week and seasonal (month) effects observed in the data.

This means:
  - Different crime types in the same area → different historical λ → different %
  - Same crime in different areas → different historical density → different %
  - Same crime, same area, different date → different temporal multiplier → different %
  - "What is the SAFEST day to visit?" → compute λ for every upcoming day, pick lowest

All multipliers are Laplace-smoothed to avoid zero-probability artefacts for
combinations not observed in training data (sparsity is common for area×crime
pairs that occur only rarely).
"""

import json
import math
import logging
import os
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

DAY_NAMES   = ['Monday', 'Tuesday', 'Wednesday', 'Thursday',
               'Friday', 'Saturday', 'Sunday']
MONTH_NAMES = ['', 'January', 'February', 'March', 'April', 'May', 'June',
               'July', 'August', 'September', 'October', 'November', 'December']


def _to_12h(hour: int) -> str:
    """Convert 0-23 hour integer to a 12-hour AM/PM label, e.g. 13 → '1:00 PM'."""
    ampm = 'AM' if hour < 12 else 'PM'
    h12  = hour % 12 or 12
    return f'{h12}:00 {ampm}'

# Amplification exponent for hour multipliers.
# Raw Laplace-smoothed multipliers cluster near 1.0; raising them to this
# power spreads them out so that selecting a visit time visibly changes the
# risk estimate (values above 1.0 grow, values below 1.0 shrink).
_HOUR_AMP: float = 2.2

# ── Artefact paths ────────────────────────────────────────────────────────────

def _default_artifact_path():
    return os.path.join(
        os.path.dirname(__file__), '..', 'models', 'poisson_artifacts.json'
    )


# ── Build (called during training) ───────────────────────────────────────────

def build_artifacts(df: pd.DataFrame) -> dict:
    """
    Compute Poisson rate artifacts from historical crime records.

    Returns a JSON-serialisable dict that is saved alongside the RF model and
    loaded at prediction time.

    Computed quantities
    -------------------
    pair_lambdas          : (area|||crime_type) → avg crimes per day
    area_lambdas          : area → avg total crimes per day
    crime_type_fractions  : crime_type → fraction of all crimes
    global_lambda         : overall crimes per day (all areas combined)
    dow_multipliers       : (area|||crime_type) → {0..6: multiplier}
    month_multipliers     : (area|||crime_type) → {1..12: multiplier}
    area_dow_multipliers  : area → {0..6: multiplier}   (fallback)
    area_month_multipliers: area → {1..12: multiplier}  (fallback)
    known_areas           : list of areas present in training data
    known_crime_types     : list of crime types (lower-cased) in training data
    total_observation_days: number of distinct calendar dates in dataset
    """
    df = df.copy()
    df['crime_date'] = pd.to_datetime(df['crime_date'], errors='coerce')
    df = df.dropna(subset=['crime_date'])
    df['date_only']   = df['crime_date'].dt.date
    df['day_of_week'] = df['crime_date'].dt.dayofweek  # 0 = Monday
    df['month']       = df['crime_date'].dt.month

    total_dates = int(df['date_only'].nunique())
    # Per-area unique date counts (how many days did this area have any crime?)
    area_date_counts = df.groupby('area')['date_only'].nunique()

    # ── Base lambdas ──────────────────────────────────────────────────────────
    # pair_lambdas: (area, crime_type) → crimes per day  [keys lowercased]
    pair_counts  = df.groupby(['area', 'crime_type']).size()
    pair_lambdas = {}
    for (area, ct), cnt in pair_counts.items():
        n_days = int(area_date_counts.get(area, total_dates))
        pair_lambdas[f"{area.lower()}|||{ct.lower()}"] = float(cnt) / n_days

    # area_lambdas: area → total crimes per day  [keys lowercased]
    area_total  = df.groupby('area').size()
    area_lambdas = {
        area.lower(): float(cnt) / int(area_date_counts.get(area, total_dates))
        for area, cnt in area_total.items()
    }

    # global lambda
    global_lambda = float(len(df)) / total_dates

    # crime_type_fractions
    ct_counts = df.groupby('crime_type').size()
    crime_type_fractions = {
        ct.lower(): float(cnt) / len(df) for ct, cnt in ct_counts.items()
    }

    # ── Day-of-week multipliers ───────────────────────────────────────────────
    # multiplier = (smoothed rate on that DOW) / (baseline 1/7)
    # Laplace smoothing: add 1 pseudo-count to each DOW bucket

    def _dow_mult(group_df):
        counts = group_df.groupby('day_of_week').size()
        total  = len(group_df)
        result = {}
        for d in range(7):
            observed  = int(counts.get(d, 0))
            smoothed  = (observed + 1) / (total + 7)   # Laplace
            result[str(d)] = round(smoothed / (1.0 / 7), 4)
        return result

    dow_multipliers      = {}
    area_dow_multipliers = {}

    for (area, ct), grp in df.groupby(['area', 'crime_type']):
        dow_multipliers[f"{area.lower()}|||{ct.lower()}"] = _dow_mult(grp)

    for area, grp in df.groupby('area'):
        area_dow_multipliers[area.lower()] = _dow_mult(grp)

    # ── Month multipliers ─────────────────────────────────────────────────────
    def _month_mult(group_df):
        counts = group_df.groupby('month').size()
        # Weight by how many months the area was actually observed
        observed_months = group_df['month'].nunique()
        total = len(group_df)
        result = {}
        for m in range(1, 13):
            observed = int(counts.get(m, 0))
            smoothed = (observed + 1) / (total + 12)
            result[str(m)] = round(smoothed / (1.0 / 12), 4)
        return result

    month_multipliers       = {}
    area_month_multipliers  = {}

    for (area, ct), grp in df.groupby(['area', 'crime_type']):
        month_multipliers[f"{area.lower()}|||{ct.lower()}"] = _month_mult(grp)

    for area, grp in df.groupby('area'):
        area_month_multipliers[area.lower()] = _month_mult(grp)

    # ── Hour-of-day multipliers ───────────────────────────────────────────────
    # Only computed when crime_hour data is available (loaded from crime_time).
    # multiplier(h) = smoothed_fraction_at_h / (1/24)
    # Laplace smoothing: add 1 pseudo-count per hour bucket.
    hour_multipliers      = {}   # key: "area|||crime_type" → {0..23: mult}
    area_hour_multipliers = {}   # key: area               → {0..23: mult}

    # Check if any valid hour data exists (load_crimes_from_db sets crime_hour=-1 when unknown)
    if 'crime_hour' in df.columns:
        df_with_hour = df[df['crime_hour'].between(0, 23)]

        def _hour_mult(group_df):
            counts = group_df.groupby('crime_hour').size()
            total  = len(group_df)
            result = {}
            for h in range(24):
                observed = int(counts.get(h, 0))
                smoothed = (observed + 1) / (total + 24)   # Laplace
                result[str(h)] = round(smoothed / (1.0 / 24), 4)
            return result

        if not df_with_hour.empty:
            for (area, ct), grp in df_with_hour.groupby(['area', 'crime_type']):
                hour_multipliers[f"{area.lower()}|||{ct.lower()}"] = _hour_mult(grp)

            for area, grp in df_with_hour.groupby('area'):
                area_hour_multipliers[area.lower()] = _hour_mult(grp)

    known_areas = list(area_date_counts.index.tolist())
    known_cts   = [ct.lower() for ct in ct_counts.index.tolist()]

    logger.info(
        "Poisson artifacts built: %d area×crime pairs, %d areas, %d crime types, "
        "%d observation days, %d hour-multiplier pairs",
        len(pair_lambdas), len(known_areas), len(known_cts), total_dates,
        len(hour_multipliers),
    )

    return {
        "pair_lambdas":            pair_lambdas,
        "area_lambdas":            area_lambdas,
        "global_lambda":           global_lambda,
        "crime_type_fractions":    crime_type_fractions,
        "dow_multipliers":         dow_multipliers,
        "month_multipliers":       month_multipliers,
        "area_dow_multipliers":    area_dow_multipliers,
        "area_month_multipliers":  area_month_multipliers,
        "hour_multipliers":        hour_multipliers,
        "area_hour_multipliers":   area_hour_multipliers,
        "known_areas":             known_areas,
        "known_crime_types":       known_cts,
        "total_observation_days":  total_dates,
    }


def save_artifacts(artifacts: dict, path: str = None):
    path = path or _default_artifact_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w') as f:
        json.dump(artifacts, f, indent=2)
    logger.info("Poisson artifacts saved to %s", path)


def load_artifacts(path: str = None) -> dict:
    path = path or _default_artifact_path()
    with open(path, 'r') as f:
        return json.load(f)


# ── Predict (called at request time) ─────────────────────────────────────────

def predict(artifacts: dict, area: str, crime_type: str,
            date_str: str, keyword_severity: float = None,
            hour: int = None) -> dict:
    """
    Return a Poisson-based risk estimate for (area, crime_type, date[, hour]).

    Parameters
    ----------
    artifacts        : loaded from poisson_artifacts.json
    area             : e.g. "DHA Phase 6"
    crime_type       : e.g. "Vehicle Theft"
    date_str         : "YYYY-MM-DD" or "YYYY-MM-DD HH:MM:SS"
    keyword_severity : 1-10 from infer_severity_from_keywords (optional)
    hour             : 0-23 integer; when provided the result is the risk for
                       that specific hour, not the whole day.

    Returns (JSON-serialisable dict)
    ----------
    risk_level            : "High" / "Medium" / "Low"
    risk_percentage       : 1-99
    confidence            : 0-1 (data density indicator, NOT model probability)
    probability           : raw Poisson P(≥1 crime)
    time_period           : "Morning" / "Afternoon" / "Evening" / "Night" (if hour given)
    safest_hours          : list of 3 safest hours in [h, "HH:00", mult] format (if hour data available)
    safest_days_of_week   : top 3 day names with lowest historical crime rate
    riskiest_day_of_week  : day name with highest historical rate
    safest_months         : top 3 month names
    safest_upcoming_dates : 3 lowest-risk dates in next 30 days
    is_estimated          : True if fallback rates were used
    note                  : human-readable explanation of fallback
    """
    key_pair    = f"{area}|||{crime_type}"
    key_pair_lc = f"{area.lower()}|||{crime_type.lower()}"
    key_ct_low  = crime_type.lower().strip()

    # ── Parse date ────────────────────────────────────────────────────────────
    date_part = date_str.split(' ')[0] if ' ' in date_str else date_str
    try:
        dt = datetime.strptime(date_part, '%Y-%m-%d')
    except ValueError:
        dt = datetime.now()

    dow   = dt.weekday()   # 0 = Monday
    month = dt.month

    # ── Lookup tables ─────────────────────────────────────────────────────────
    pair_lambdas          = artifacts.get('pair_lambdas', {})
    area_lambdas          = artifacts.get('area_lambdas', {})
    global_lambda         = float(artifacts.get('global_lambda', 1.0))
    crime_type_fractions  = artifacts.get('crime_type_fractions', {})
    dow_multipliers       = artifacts.get('dow_multipliers', {})
    month_multipliers     = artifacts.get('month_multipliers', {})
    area_dow_mults        = artifacts.get('area_dow_multipliers', {})
    area_month_mults      = artifacts.get('area_month_multipliers', {})
    hour_mults_all        = artifacts.get('hour_multipliers', {})
    area_hour_mults       = artifacts.get('area_hour_multipliers', {})
    known_areas           = set(artifacts.get('known_areas', []))
    known_cts             = set(artifacts.get('known_crime_types', []))
    n_known_areas         = max(len(known_areas), 1)

    # Use lowercase key for case-insensitive pair lookup
    is_known_pair = key_pair_lc in pair_lambdas
    is_known_area = area.lower() in {k.lower() for k in known_areas}
    is_known_ct   = key_ct_low in known_cts
    is_estimated  = not is_known_pair
    note          = None

    # ── Base lambda (crimes per day for this area+crime_type combination) ─────
    if is_known_pair:
        base_lambda = float(pair_lambdas[key_pair_lc])
        confidence_val = 0.90

    elif is_known_area and is_known_ct:
        # Area in training data, crime type in training data, but unseen together
        area_rate  = float(area_lambdas.get(area.lower(), global_lambda / n_known_areas))
        ct_frac    = float(crime_type_fractions.get(key_ct_low, 1.0 / max(len(known_cts), 1)))
        base_lambda    = area_rate * ct_frac
        confidence_val = 0.65
        note = "This prediction is based on similar historical patterns as this exact crime type combination was not frequently observed in this area."

    elif is_known_area:
        # Known area, completely unknown crime type — scale by keyword severity
        area_rate  = float(area_lambdas.get(area.lower(), global_lambda / n_known_areas))
        sev_weight = float(keyword_severity or 5.0) / 10.0
        # Use ~5% of area's daily crime rate as the baseline for one unknown type
        base_lambda    = area_rate * 0.05 * sev_weight
        confidence_val = 0.45
        note = "This prediction is based on this area's overall historical crime patterns, as this specific crime type was rarely recorded here."

    elif is_known_ct:
        # Unknown area, known crime type
        global_per_area = global_lambda / n_known_areas
        ct_frac         = float(crime_type_fractions.get(key_ct_low, 1.0 / max(len(known_cts), 1)))
        base_lambda     = global_per_area * ct_frac
        confidence_val  = 0.35
        note = "This prediction is based on regional patterns for this crime type, as this area has limited historical data."

    else:
        # Both unknown
        base_lambda    = global_lambda / n_known_areas * 0.05
        confidence_val = 0.25
        note = "This prediction is based on similar historical patterns because this exact combination was rare in the dataset."

    # ── Select temporal multiplier tables ─────────────────────────────────────
    if key_pair_lc in dow_multipliers:
        dow_m   = dow_multipliers[key_pair_lc]
        month_m = month_multipliers.get(key_pair_lc, {str(m): 1.0 for m in range(1, 13)})
        hour_m  = hour_mults_all.get(key_pair_lc, {})
    elif area.lower() in area_dow_mults:
        dow_m   = area_dow_mults[area.lower()]
        month_m = area_month_mults.get(area.lower(), {str(m): 1.0 for m in range(1, 13)})
        hour_m  = area_hour_mults.get(area.lower(), {})
    else:
        dow_m   = {str(d): 1.0 for d in range(7)}
        month_m = {str(m): 1.0 for m in range(1, 13)}
        hour_m  = {}

    # ── Compute λ for the queried date (and optionally hour) ──────────────────
    dow_mult   = float(dow_m.get(str(dow),   1.0))
    month_mult = float(month_m.get(str(month), 1.0))

    # Hour multiplier: λ for a specific hour is base_λ scaled by how much more
    # (or less) criminal activity occurs in that hour versus the average hour.
    # When no hour data exists we fall back to 1.0 (neutral).
    # _HOUR_AMP power amplifies the raw smoothed multipliers so time selection
    # produces a meaningfully visible change in the predicted risk percentage.
    # Stored hour multipliers in artifacts are normalized as (smoothed_fraction / (1/24)),
    # i.e. roughly = 24 * fraction_of_day. To convert back to a per-hour fraction
    # we divide by 24. Apply the amplification exponent to the fraction so that
    # selecting a particular hour meaningfully changes the hourly λ while keeping
    # units consistent (base_lambda is crimes per day).
    if hour is not None and hour_m:
        _raw_hmult = float(hour_m.get(str(hour), 1.0))
        hour_mult = (max(_raw_hmult, 1e-9) ** _HOUR_AMP) / 24.0
    else:
        hour_mult = 1.0

    lam = base_lambda * dow_mult * month_mult * hour_mult

    # ── Poisson P(X ≥ 1) = 1 - e^(-λ) ───────────────────────────────────────
    probability = 1.0 - math.exp(-max(lam, 1e-9))
    risk_pct    = round(max(0.01, min(99.0, probability * 100)), 2)

    # ── Risk level thresholds ───────────────────────────────────────────────────
    # 0–25% → Low, 25–50% → Medium, 51–80% → High, 81–100% → Critical
    # Explicit inclusive upper-edge thresholds to match displayed risk buckets
    if probability >= 0.80:
        risk_level = 'Critical'
    elif probability >= 0.50:
        risk_level = 'High'
    elif probability >= 0.25:
        risk_level = 'Medium'
    else:
        risk_level = 'Low'

    # ── Time period label ───────────────────────────────────────────────────
    if hour is not None:
        if 5 <= hour <= 11:
            time_period = 'Morning'
        elif 12 <= hour <= 16:
            time_period = 'Afternoon'
        elif 17 <= hour <= 20:
            time_period = 'Evening'
        else:
            time_period = 'Night'
    else:
        time_period = None

    # ── Safest + riskiest hours, and hourly risk profile ─────────────────────
    safest_hours  = []
    riskiest_hours = []
    hourly_risk_profile = {}
    visit_time_comparison = []

    if hour_m:
        hour_risks = [(h, float(hour_m.get(str(h), 1.0))) for h in range(24)]
        safest_hours = [
            {"hour": h, "label": _to_12h(h), "relative_risk": round(mult, 3)}
            for h, mult in sorted(hour_risks, key=lambda x: x[1])[:3]
        ]
        riskiest_hours = [
            {"hour": h, "label": _to_12h(h), "relative_risk": round(mult, 3)}
            for h, mult in sorted(hour_risks, key=lambda x: -x[1])[:3]
        ]

        # Time-of-day risk profile (grouped by period)
        period_lambdas: dict = {"Morning": [], "Afternoon": [], "Evening": [], "Night": []}
        for h, mult in hour_risks:
            h_mult = (max(float(mult), 1e-9) ** _HOUR_AMP) / 24.0
            lam_h  = base_lambda * dow_mult * month_mult * h_mult
            if 5 <= h <= 11:
                period_lambdas["Morning"].append(lam_h)
            elif 12 <= h <= 16:
                period_lambdas["Afternoon"].append(lam_h)
            elif 17 <= h <= 20:
                period_lambdas["Evening"].append(lam_h)
            else:
                period_lambdas["Night"].append(lam_h)

        hourly_risk_profile = {
            k: round((1.0 - math.exp(-max(sum(v), 1e-9))) * 100, 1)
            for k, v in period_lambdas.items() if v
        }

        # Visit-time comparison: representative hours
        _visit_hours = [
            (8,  "8:00 AM",  "Morning"),
            (14, "2:00 PM",  "Afternoon"),
            (20, "8:00 PM",  "Evening"),
            (23, "11:00 PM", "Night"),
        ]
        for vh, vlabel, vperiod in _visit_hours:
            vm_raw = float(hour_m.get(str(vh), 1.0))
            vm_mult = (max(vm_raw, 1e-9) ** _HOUR_AMP) / 24.0
            vlam  = base_lambda * dow_mult * month_mult * vm_mult
            vprob = round((1.0 - math.exp(-max(vlam, 1e-9))) * 100, 2)
            visit_time_comparison.append({
                "hour": vh, "label": vlabel, "period": vperiod,
                "risk_percentage": vprob,
            })

    # ── Safest days of week ───────────────────────────────────────────────
    dow_risks = [(DAY_NAMES[d], float(dow_m.get(str(d), 1.0))) for d in range(7)]
    safest_days  = [day for day, _ in sorted(dow_risks, key=lambda x: x[1])[:3]]
    riskiest_day = max(dow_risks, key=lambda x: x[1])[0]

    # ── Safest months ─────────────────────────────────────────────────────────
    month_risks   = [(MONTH_NAMES[m], float(month_m.get(str(m), 1.0))) for m in range(1, 13)]
    safest_months = [mo for mo, _ in sorted(month_risks, key=lambda x: x[1])[:3]]

    # ── Best upcoming dates (next 30 days) ────────────────────────────────────
    upcoming = []
    for delta in range(1, 31):
        fd       = dt + timedelta(days=delta)
        fd_dow   = fd.weekday()
        fd_month = fd.month
        if hour is not None and hour_m:
            raw_h = float(hour_m.get(str(hour), 1.0))
            fd_hour_factor = (max(raw_h, 1e-9) ** _HOUR_AMP) / 24.0
        else:
            fd_hour_factor = 1.0

        fd_lam   = (base_lambda
                    * float(dow_m.get(str(fd_dow),   1.0))
                    * float(month_m.get(str(fd_month), 1.0))
                    * fd_hour_factor)
        fd_prob  = 1.0 - math.exp(-max(fd_lam, 1e-9))
        upcoming.append((fd.strftime('%Y-%m-%d'), DAY_NAMES[fd_dow], round(fd_prob * 100, 2)))

    safest_upcoming = sorted(upcoming, key=lambda x: x[2])[:3]

    result = {
        "risk_level":           risk_level,
        "risk_percentage":      risk_pct,
        "confidence":           round(confidence_val, 4),
        "probability":          round(probability, 4),
        "safest_days_of_week":  safest_days,
        "riskiest_day_of_week": riskiest_day,
        "safest_months":        safest_months,
        "safest_upcoming_dates": [
            {"date": d, "day": day, "risk_percentage": pct}
            for d, day, pct in safest_upcoming
        ],
        "is_estimated": is_estimated,
        "lambda": round(float(lam), 6),
    }
    if time_period:
        result["time_period"] = time_period
    if safest_hours:
        result["safest_hours"] = safest_hours
    if riskiest_hours:
        result["riskiest_hours"] = riskiest_hours
    if hourly_risk_profile:
        result["hourly_risk_profile"] = hourly_risk_profile
    if visit_time_comparison:
        result["visit_time_comparison"] = visit_time_comparison
    if note:
        result["note"] = note
    return result

# ── Batch safety analysis for one area across all crime types ─────────────────

def area_safety_profile(artifacts: dict, area: str, date_str: str, hour: int = None) -> dict:
    """
    For a given area and date, compute risk for ALL known crime types in that area.
    Returns overall risk + breakdown.  Used by the area details panel.
    """
    key_ct_low_list = [
        ct for key in artifacts.get('pair_lambdas', {})
        if key.startswith(f"{area.lower()}|||")
        for ct in [key.split('|||', 1)[1]]
    ]
    if not key_ct_low_list:
        key_ct_low_list = artifacts.get('known_crime_types', [])

    results = []
    for ct in key_ct_low_list:
        r = predict(artifacts, area, ct, date_str, hour=hour)
        results.append({'crime_type': ct, **r})

    if not results:
        return {'area': area, 'date': date_str, 'risk_level': 'Unknown',
                'risk_percentage': 0, 'crime_breakdown': []}

    # Aggregate: overall area risk = 1 - P(no crime of any type)
    total_prob = 1.0 - math.exp(
        -sum(r.get('lambda', 0.0) for r in results)
    )
    total_pct  = max(1, min(99, int(round(total_prob * 100))))

    if total_prob > 0.70:
        overall_level = 'High'
    elif total_prob > 0.35:
        overall_level = 'Medium'
    else:
        overall_level = 'Low'

    return {
        'area':            area,
        'date':            date_str,
        'risk_level':      overall_level,
        'risk_percentage': total_pct,
        'probability':     round(total_prob, 4),
        'crime_breakdown': sorted(
            [{'crime_type': r['crime_type'],
              'risk_level': r['risk_level'],
              'risk_percentage': r['risk_percentage']}
             for r in results],
            key=lambda x: -x['risk_percentage']
        ),
    }

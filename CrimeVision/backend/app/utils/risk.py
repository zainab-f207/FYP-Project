
import math
from datetime import datetime
from typing import Dict, Any, Optional, List


UNIFIED_WEIGHTS = {
    "volume": 0.35,
    "severity": 0.15,
    "recency": 0.30,
    "trend": 0.10,
    "time": 0.10,
}


def _clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(high, value))


def risk_label_from_risk_score(risk_score: float) -> str:
    rs = float(_clamp(risk_score))
    if rs <= 20:
        return "Low"
    if rs <= 50:
        return "Moderate"
    if rs <= 80:
        return "High"
    return "Critical"


def risk_action_label_from_score(risk_score: float) -> str:
    rs = float(_clamp(risk_score))
    if rs <= 20:
        return "Safe"
    if rs <= 50:
        return "Caution"
    if rs <= 80:
        return "Warning"
    return "Avoid"


def safety_grade_from_score(safety_score: float) -> str:
    ss = float(_clamp(safety_score))
    if ss >= 80:
        return "A"
    if ss >= 65:
        return "B"
    if ss >= 50:
        return "C"
    if ss >= 35:
        return "D"
    return "F"


def _confidence_from_volume(total_crimes: float) -> str:
    n = float(max(0.0, total_crimes))
    if n >= 120:
        return "high"
    if n >= 30:
        return "medium"
    return "low"


def _stabilize_for_sparse_data(risk_score: float, total_crimes: float, observation_days: int = 365) -> float:
    """Shrink extreme scores toward neutral for low-sample windows."""
    n = float(max(0.0, total_crimes))
    required_sample = max(3.0, (30.0 / 365.0) * float(max(1, observation_days)))
    
    if n >= required_sample:
        return float(_clamp(risk_score))

    # Blend with neutral baseline (which we'll set to 0 for a cleaner user experience when no data is found)
    # when n=0, alpha=0, stabilized = 0.
    alpha = n / required_sample
    stabilized = (alpha * float(risk_score)) + ((1.0 - alpha) * 0.0) 
    return float(_clamp(stabilized))



def _volume_score(total_crimes: float, observation_days: int = 365, baseline_daily: float = 0.35) -> float:
    """
    Incident-volume score with high-count sensitivity.

    The original Poisson-only formulation quickly saturates near 100 for large counts,
    which makes 2k and 6k incidents appear nearly identical. We blend:
    - Poisson probability (short-window event likelihood)
    - Log-scaled count ratio (relative incident burden)
    """
    tc = float(max(0.0, total_crimes))
    days = max(1, int(observation_days))

    # Component 1: event likelihood in the observation window.
    lam = tc / float(days)
    poisson_score = 100.0 * (1.0 - math.exp(-max(lam, 1e-9)))

    # Component 2: gradual scaling by absolute incident volume.
    # Use a broader reference so historical-heavy areas (e.g., 2k-6k incidents)
    # remain differentiated instead of saturating at the top.
    volume_ref = max(3000.0, float(days) * 30.0)
    count_scale = 100.0 * (math.log1p(tc) / math.log1p(volume_ref))

    # Keep compatibility with prior behavior while restoring differentiation.
    score = (0.60 * poisson_score) + (0.40 * count_scale)
    return float(_clamp(score))


def _severity_score(high_risk_count: float, medium_risk_count: float, total_crimes: float) -> float:
    tc = float(max(0.0, total_crimes))
    if tc <= 0.0:
        return 0.0

    hc = float(max(0.0, high_risk_count))
    mc = float(max(0.0, medium_risk_count))
    lc = float(max(0.0, tc - hc - mc))

    # Weighted average severity in [2..8] approximately.
    weighted = (hc * 8.0) + (mc * 5.0) + (lc * 2.0)
    avg = weighted / tc
    score = ((avg - 2.0) / 6.0) * 100.0
    return float(_clamp(score))


def _trend_from_recent_vs_older(recent_count: float, older_count: float) -> float:
    recent = float(max(0.0, recent_count))
    older = float(max(0.0, older_count))
    if older <= 0.0:
        return 50.0 if recent <= 0.0 else 5.0
    diff_pct = ((recent - older) / older) * 100.0
    return float(_clamp(50.0 - (diff_pct * 0.5)))


def _recency_from_last_30(last_30_days: float, expected_30_days: float) -> float:
    obs = float(max(0.0, last_30_days))
    exp = float(max(0.0, expected_30_days))
    if exp <= 0.0:
        return 50.0 if obs <= 0.0 else 95.0
    return float(_clamp((obs / exp) * 100.0))


def _recency_from_recent_windows(last_30_days: float, last_90_days: float) -> float:
    """Recency score from recent activity concentration (30d inside 90d)."""
    l30 = float(max(0.0, last_30_days))
    l90 = float(max(0.0, last_90_days))
    if l90 <= 0.0:
        return 50.0
    expected_30_from_90 = l90 / 3.0
    if expected_30_from_90 <= 0.0:
        return 50.0
    return float(_clamp((l30 / expected_30_from_90) * 100.0))

def compute_poisson_risk_pct(total_crimes: float, high_risk_count: float, 
                             medium_risk_count: float, observation_days: int = 365) -> float:
    """
    Computes a risk percentage based on Poisson probability of occurrence.
    Weights: High (8.0), Medium (3.0), Others (1.0)
    """
    # Cast to float to avoid decimal issues from DB
    hc = float(high_risk_count or 0)
    mc = float(medium_risk_count or 0)
    tc = float(total_crimes or 0)
    
    # Weight crimes significantly more for High Risk areas
    # If 10 high-risk crimes in a year: lambda = 80/365 = 0.22 -> Prob(>=1) = 20%
    # If 50 high-risk crimes: lambda = 400/365 = 1.1 -> Prob(>=1) = 66%
    weighted_crimes = (hc * 8.0) + (mc * 3.0) + max(0.0, tc - hc - mc) * 1.0
    
    # lambda = expected weighted crimes per day
    lam = weighted_crimes / max(observation_days, 1)
    
    # Poisson P(>=1 event) = 1 - e^(-lambda)
    probability = 1.0 - math.exp(-max(lam, 1e-9))
    
    # Convert to percentage [0, 99]
    return float(round(float(max(0.0, min(99.0, probability * 100.0))), 1))


def calculate_unified_risk_summary(stats: Optional[Dict[str, Any]], observation_days: int = 365) -> Dict[str, Any]:
    """
    Shared scoring engine used across dashboard, alerts, prediction, and admin views.

    Formula:
      risk = 0.35*volume + 0.15*severity + 0.30*recency + 0.10*trend + 0.10*time
      safety = 100 - risk

    Special handling:
      - No stats provided: returns 95% safety (Low risk)
      - Zero crimes found: returns 95% safety (Low risk)
      - This ensures consistent behavior across all interfaces

    Inputs are context-dependent via stats fields.
    """
    if not stats:
        return {
            "risk_score": 5.0,
            "safety_score": 95.0,
            "risk_level": "Low",
            "risk_label": "Safe",
            "safety_grade": "A",
            "score_components": {"volume": 5.0, "severity": 5.0, "recency": 5.0, "trend": 5.0, "time": 5.0},
            "data_confidence": "low",
            "weights": UNIFIED_WEIGHTS,
        }

    total_crimes = float(stats.get("total_crimes", 0) or 0)
    high_risk_count = float(stats.get("high_risk_count", 0) or 0)
    medium_risk_count = float(stats.get("medium_risk_count", 0) or 0)

    # Handle zero-crime areas consistently across all interfaces
    if total_crimes == 0:
        return {
            "risk_score": 5.0,
            "safety_score": 95.0,
            "risk_level": "Low",
            "risk_label": "Safe",
            "safety_grade": "A",
            "score_components": {"volume": 5.0, "severity": 5.0, "recency": 5.0, "trend": 5.0, "time": 5.0},
            "data_confidence": _confidence_from_volume(total_crimes),
            "weights": UNIFIED_WEIGHTS,
        }

    # Accept precomputed components where available (e.g., area profile endpoint).
    pre_volume = stats.get("volume_score")
    pre_severity = stats.get("severity_score")
    pre_recency = stats.get("recency_score")
    pre_trend = stats.get("trend_score")
    pre_time = stats.get("time_risk_score")

    volume_score = float(pre_volume) if pre_volume is not None else _volume_score(total_crimes, observation_days)
    severity_score = float(pre_severity) if pre_severity is not None else _severity_score(high_risk_count, medium_risk_count, total_crimes)

    if pre_recency is not None:
        recency_score = float(pre_recency)
    else:
        last_30 = float(stats.get("last_30_days", 0) or 0)
        last_90 = float(stats.get("last_90_days", 0) or 0)
        if last_90 > 0:
            recency_score = _recency_from_recent_windows(last_30, last_90)
        else:
            expected_30 = float(stats.get("expected_30_days", (total_crimes / max(1, observation_days)) * 30.0) or 0)
            recency_score = _recency_from_last_30(last_30, expected_30)

    if pre_trend is not None:
        trend_score = float(pre_trend)
    else:
        recent_count = float(stats.get("recent_count", stats.get("recent_half", 0)) or 0)
        older_count = float(stats.get("older_count", stats.get("older_half", 0)) or 0)
        trend_score = _trend_from_recent_vs_older(recent_count, older_count)

    time_risk_score = float(pre_time) if pre_time is not None else float(_clamp(float(stats.get("time_risk_score", 50.0) or 50.0)))

    raw_risk = (
        (UNIFIED_WEIGHTS["volume"] * volume_score)
        + (UNIFIED_WEIGHTS["severity"] * severity_score)
        + (UNIFIED_WEIGHTS["recency"] * recency_score)
        + (UNIFIED_WEIGHTS["trend"] * trend_score)
        + (UNIFIED_WEIGHTS["time"] * time_risk_score)
    )

    # Decay historical risk if recent activity is truly zero
    # BUT: Use context-aware decay — with strong historical evidence, decay less aggressively
    last_90 = float(stats.get("last_90_days", 0) or 0)
    if last_90 == 0:
        # Adaptive decay based on historical crime volume and severity:
        # - Minimal decay (0.85): Strong historical evidence (1000+ total crimes or 50+ high-risk)
        # - Standard decay (0.70): Moderate evidence (100-999 crimes)
        # - Aggressive decay (0.60): Weak evidence (0-99 crimes)
        # This preserves risk differentiation across areas while acknowledging stale data
        
        if total_crimes >= 1000 or high_risk_count >= 50:
            # Strong historical evidence => minimal decay (15% reduction)
            decay_factor = 0.85
        elif total_crimes >= 100:
            # Moderate evidence => standard decay (30% reduction)
            decay_factor = 0.70
        else:
            # Weak evidence => aggressive decay (40% reduction)
            decay_factor = 0.60
        
        raw_risk *= decay_factor
        
    risk_score = _stabilize_for_sparse_data(raw_risk, total_crimes, observation_days)
    safety_score = float(_clamp(100.0 - risk_score))
    risk_level = risk_label_from_risk_score(risk_score)

    return {
        "risk_score": float(round(risk_score, 1)),
        "safety_score": float(round(safety_score, 1)),
        "risk_level": risk_level,
        "risk_label": risk_action_label_from_score(risk_score),
        "safety_grade": safety_grade_from_score(safety_score),
        "score_components": {
            "volume": float(round(_clamp(volume_score), 1)),
            "severity": float(round(_clamp(severity_score), 1)),
            "recency": float(round(_clamp(recency_score), 1)),
            "trend": float(round(_clamp(trend_score), 1)),
            "time": float(round(_clamp(time_risk_score), 1)),
        },
        "data_confidence": _confidence_from_volume(total_crimes),
        "weights": UNIFIED_WEIGHTS,
    }

def calculate_safety_score(stats: Optional[Dict[str, Any]], observation_days: int = 365) -> float:
    """
    Standardizes safety score calculation across the app.
    Returns a score from 1.0 to 100.0.
    """
    summary = calculate_unified_risk_summary(stats, observation_days)
    return float(summary["safety_score"])

def calculate_breakdown(crime_counts: List[Dict[str, Any]], day_crimes: int, night_crimes: int) -> Dict[str, float]:
    """
    Standardizes the radar chart breakdown calculation.
    """
    violent_count: float = 0.0
    property_count: float = 0.0
    personal_count: float = 0.0
    
    for row in crime_counts:
        ctype = str(row.get('crime_type', '')).lower()
        count = float(row.get('count', 0))
        if any(x in ctype for x in ['murder', 'assault', 'kidnap', 'shoot', 'kill', 'weapon', 'robbery']):
            violent_count += count
        elif any(x in ctype for x in ['theft', 'burglary', 'snatch', 'steal', 'fraud', 'vehicle', 'car']):
            property_count += count
        elif any(x in ctype for x in ['harass', 'stalk', 'rape', 'abuse', 'kidnap']):
            personal_count += count
        else:
            property_count += count # Default to property for unknown types

    # Convert counts to safety scores (0-100, where 100 is perfectly safe)
    # Higher penalties for violent crime
    score_violent = float(max(1.0, 100.0 - (violent_count * 15.0)))
    score_property = float(max(1.0, 100.0 - (property_count * 5.0)))
    score_personal = float(max(1.0, 100.0 - (personal_count * 10.0)))
    score_day = float(max(1.0, 100.0 - (float(day_crimes) * 3.0)))
    score_night = float(max(1.0, 100.0 - (float(night_crimes) * 6.0)))
    
    return {
        "violent": float(round(score_violent, 1)),
        "property": float(round(score_property, 1)),
        "personal": float(round(score_personal, 1)),
        "day": float(round(score_day, 1)),
        "night": float(round(score_night, 1))
    }

def get_risk_level(safety_score: float) -> str:
    """
    Categorizes a safety score (1-100) into a qualitative risk level.
    """
    risk_score = 100.0 - float(_clamp(safety_score))
    return risk_label_from_risk_score(risk_score)

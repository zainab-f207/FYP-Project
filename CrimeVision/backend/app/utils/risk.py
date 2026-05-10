"""
risk.py — the single source of truth for "how risky is this area?"

Why this file exists in plain words:
    The CrimeVision app shows a "Safety Score" / "Risk Level" in many
    different places — the user dashboard headline, the Area Safety Profile,
    the alert engine, the admin panel, the prediction screen. If each of
    those screens calculated the score with its own slightly-different
    formula, the same area would show DIFFERENT numbers depending on which
    page you opened, which would destroy trust in the whole system.

    To prevent that, every screen funnels its raw stats through the
    `calculate_unified_risk_summary` function in this file. That function
    blends five components into one score:

        risk_score = 0.35*volume + 0.15*severity + 0.30*recency
                   + 0.10*trend  + 0.10*time
        safety_score = 100 - risk_score

    The five components answer five separate questions about the area:
        - volume   : how much crime happens here per day?
        - severity : how serious are those crimes (high vs. medium vs. low)?
        - recency  : is crime happening RIGHT NOW or only historically?
        - trend    : is it getting better or worse compared to the past?
        - time     : at the specific HOUR the user is asking about, is this
                     a riskier hour than average for this area?

    The weights (0.35, 0.15, ...) are deliberately conservative:
        - Volume gets the biggest weight because it is the most reliable
          signal (large samples don't lie).
        - Recency gets the second-biggest weight so a quiet area where
          something has just happened is not misclassified as safe.
        - Severity, trend and time each get small weights — they are
          informative but noisier signals.

What lives in this file:
    - Public scoring entrypoints used by the rest of the codebase:
        * calculate_unified_risk_summary  → returns the full risk dict
        * calculate_safety_score          → returns just the safety number
        * calculate_breakdown             → splits crimes by category for
                                            the radar / breakdown chart
        * compute_poisson_risk_pct        → standalone Poisson estimate
                                            used by older callers
        * get_risk_level / get_risk_label → string labels from a number
    - Helpers prefixed with _ (underscore) are internal building blocks for
      the components above and should not be called from outside this file.
"""

import math
from datetime import datetime
from typing import Dict, Any, Optional, List


# Component weights that define the entire risk formula. They MUST sum to
# 1.0 — if you change one, change another so the total stays at 1.0,
# otherwise the resulting risk_score will silently shift its scale.
UNIFIED_WEIGHTS = {
    "volume": 0.35,
    "severity": 0.15,
    "recency": 0.30,
    "trend": 0.10,
    "time": 0.10,
}


def _clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    """Squeeze a number into a [low, high] window.

    We use this everywhere because intermediate calculations (ratios,
    Poisson probabilities, percentage diffs) can naturally overshoot 100
    or go negative. Pinning them to [0, 100] stops one runaway component
    from making the whole formula nonsensical.
    """
    return max(low, min(high, value))


def risk_label_from_risk_score(risk_score: float) -> str:
    """Convert a numeric risk score into the user-facing severity label.

    The thresholds (20 / 50 / 80) match the colour bands the dashboard UI
    uses, so a "Moderate" badge always corresponds to an orange/yellow
    band on the score bar, never a green or red one.
    """
    rs = float(_clamp(risk_score))
    if rs <= 20:
        return "Low"
    if rs <= 50:
        return "Moderate"
    if rs <= 80:
        return "High"
    return "Critical"


def risk_action_label_from_score(risk_score: float) -> str:
    """Return the action-oriented label shown on visit/route advice cards.

    `risk_label_from_risk_score` answers "how bad is it?" while this answer
    "what should I do about it?" — the two labels appear in different parts
    of the UI (the badge vs. the recommendation strip) and we want them to
    align on the same thresholds.
    """
    rs = float(_clamp(risk_score))
    if rs <= 20:
        return "Safe"
    if rs <= 50:
        return "Caution"
    if rs <= 80:
        return "Warning"
    return "Avoid"


def safety_grade_from_score(safety_score: float) -> str:
    """Translate a 0-100 safety_score into a school-style letter grade.

    Drives the big A/B/C/D/F letter on the Area Safety Profile card. Note
    the grade is computed from SAFETY (high is good), while the labels
    above are computed from RISK (high is bad) — the two are exact
    complements (safety = 100 - risk), so the bands look mirrored.
    """
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
    """How much should the user trust the score for this area?

    A score computed from 5 incidents is statistically wobbly; one
    computed from 5,000 is rock solid. We expose this as a "high /
    medium / low" tag so the UI can show a small confidence chip
    next to the score and the user understands what they are looking at.
    """
    n = float(max(0.0, total_crimes))
    if n >= 120:
        return "high"
    if n >= 30:
        return "medium"
    return "low"


def _stabilize_for_sparse_data(risk_score: float, total_crimes: float, observation_days: int = 365) -> float:
    """Pull the risk score toward 0 (safe) when we barely have any data.

    Why this matters:
        Without this step a single high-severity incident in a 1-year
        window (lambda = 1/365) would still produce a non-trivial Poisson
        score and could push a peaceful area into "Moderate" or even
        "High". That is statistically dishonest because one data point
        cannot tell you about the long-term risk.

    How the blend works:
        - We compute a "required sample" that scales with the observation
          window — we want roughly one incident per ~12 days of history
          to start trusting the result.
        - If we already have enough samples we return the score unchanged.
        - Otherwise we linearly blend the score with 0.0 ("safe baseline")
          using alpha = (observed / required). With zero observations
          alpha=0 and the answer is 0.0; with exactly the required count
          alpha=1 and the answer is the full score.
    """
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
    """How "loud" is this area in raw incident count?

    The challenge:
        A pure Poisson-probability score saturates very quickly. Once an
        area averages a few incidents per day, the Poisson estimate
        rounds to ~100 and an area with 2,000 incidents looks identical
        to one with 6,000. That hides huge real-world differences.

    The fix used here — blend two viewpoints:
        Component 1 (Poisson, weight 0.60):
            Treats incidents as random events and asks "what's the
            probability of at least one event happening today?". This is
            statistically meaningful for small/medium counts.
        Component 2 (log-scaled volume, weight 0.40):
            log1p(count) / log1p(reference). The logarithm grows slowly,
            so it keeps producing small but meaningful differences even
            as raw counts get huge. We use a reference of `days * 30` so
            longer observation windows expect more incidents — that way
            "100 incidents in 1 month" and "100 incidents in 5 years"
            don't get the same volume score.

    The `baseline_daily` parameter is kept in the signature for backward
    compatibility with older callers but is no longer used internally —
    the log-scaled component already replaces what it was doing.
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
    """Penalise areas where the crime mix skews toward serious offences.

    Two areas can have the same number of incidents per day but very
    different victim impact: 100 pickpocketings vs. 100 armed assaults.
    We capture that by giving each incident a "severity weight" and
    averaging:
        High-risk crimes  → weight 8 (most serious)
        Medium-risk crimes → weight 5
        Low / unknown     → weight 2

    The weighted average then sits in [2, 8]. We linearly map it into
    [0, 100] using `((avg - 2) / 6) * 100` so 2 → 0 (purely low-risk
    crimes), 5 → 50 (entirely medium), 8 → 100 (entirely high-risk).
    """
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
    """Is this area getting BETTER or WORSE over time?

    We compare the most recent window against an equally-sized older
    window and express the difference as a percentage. Then we centre
    the score at 50 (no change) and pull it down when the recent count
    has grown (worse) and up when it has shrunk (better).

    Edge cases:
        - older == 0, recent == 0: nothing to compare — return 50 (neutral)
        - older == 0, recent > 0:  brand-new spike — return 5 (very high
          risk signal because it's all new activity)
    """
    recent = float(max(0.0, recent_count))
    older = float(max(0.0, older_count))
    if older <= 0.0:
        return 50.0 if recent <= 0.0 else 5.0
    diff_pct = ((recent - older) / older) * 100.0
    return float(_clamp(50.0 - (diff_pct * 0.5)))


def _recency_from_last_30(last_30_days: float, expected_30_days: float) -> float:
    """Compare actual incidents in the last 30 days vs. what we'd expect.

    "Expected" usually comes from the long-term daily average projected
    forward 30 days. If observed > expected the area is heating up;
    if observed << expected the area is cooling down. We express the
    ratio on a 0-100 scale where 100 means "exactly the long-term rate"
    and >100 (clamped) means "above long-term rate".
    """
    obs = float(max(0.0, last_30_days))
    exp = float(max(0.0, expected_30_days))
    if exp <= 0.0:
        return 50.0 if obs <= 0.0 else 95.0
    return float(_clamp((obs / exp) * 100.0))


def _recency_from_recent_windows(last_30_days: float, last_90_days: float) -> float:
    """Recency score that uses 30d-inside-90d concentration.

    If the last 30 days hold 1/3 of the last 90 days' incidents, activity
    is steady (score ≈ 100). If they hold MORE than 1/3, recent activity
    is intensifying (score > 100, clamped). If they hold LESS, the area
    is cooling. This is preferred over `_recency_from_last_30` whenever
    the caller already has the 90-day count handy because it avoids the
    "expected" estimate entirely — pure observed-vs-observed comparison.
    """
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
    """Standalone Poisson-only risk percentage.

    This is the ORIGINAL scoring function from earlier versions of the
    project. It still exists for two reasons:
        1) A handful of older endpoints / scripts call it directly and we
           don't want to break them.
        2) It is sometimes useful as a "second opinion" against the unified
           summary above when debugging.

    The math intuition:
        - Each crime is treated as an independent random event.
        - Severity tiers are turned into a single weighted count
          (high=8x, medium=3x, low=1x).
        - λ (lambda) = weighted count / observation days = expected
          weighted events per day.
        - The probability that AT LEAST ONE such event happens on any
          given day is 1 − e^(−λ).  We multiply by 100 to get a
          percentage and clamp at 99 so the UI never shows a misleading
          "100% certain crime tomorrow" badge.
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
    """The MAIN scoring entrypoint — every screen's safety score lands here.

    What this function does, step by step:
        1) Bail-out paths: if `stats` is None or `total_crimes` is 0,
           return a "Safe / 95" preset so empty/quiet areas show up as
           clearly safe everywhere in the UI.
        2) Honour pre-computed components: callers like the Area Profile
           endpoint already know the recency / trend / time scores from
           dedicated SQL queries, so they pass them in via
           `recency_score`, `trend_score`, `time_risk_score` keys. When
           present we use those directly; when missing we calculate them
           ourselves from raw counts (last_30_days, last_90_days, etc.).
        3) Combine the five components using the global UNIFIED_WEIGHTS.
        4) Apply a "no recent activity" decay: if the last 90 days are
           empty we shrink the score because the area has gone quiet —
           but the shrink amount depends on how strong the historical
           evidence is (we don't want to declare a known-bad area "Safe"
           after just one quiet quarter).
        5) Stabilise sparse data so a 1-incident sample cannot produce
           an alarming score.
        6) Build the final dict that every UI consumes — identical shape
           regardless of the input — including labels, grade, confidence
           and the breakdown of every component for transparency.

    The dict shape returned is THE contract every other module depends
    on. Adding new keys is safe; renaming or removing existing keys
    will silently break dashboards and admin pages that read them.
    """
    # Path 1: caller didn't even pass stats. Treat as "no data" → safe
    # default so no UI ever crashes when an upstream query returned None.
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

    # Path 2: stats exist but show zero incidents. Same safe preset as
    # path 1, but we keep the actual confidence label (low/medium/high)
    # since "we have a real query result of zero" is more meaningful than
    # "we got nothing at all".
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

    # Pull pre-computed component scores out of the stats dict if the
    # caller already calculated them (e.g. /area-safety-profile pre-runs
    # recency / trend / time queries because it has more context). Each
    # value defaults to None so the `is not None` check below distinguishes
    # "you didn't tell me" from "you told me zero".
    pre_volume = stats.get("volume_score")
    pre_severity = stats.get("severity_score")
    pre_recency = stats.get("recency_score")
    pre_trend = stats.get("trend_score")
    pre_time = stats.get("time_risk_score")

    # Volume + severity always default to the helper functions because
    # they only need information that's almost always present (total +
    # high/medium counts).
    volume_score = float(pre_volume) if pre_volume is not None else _volume_score(total_crimes, observation_days)
    severity_score = float(pre_severity) if pre_severity is not None else _severity_score(high_risk_count, medium_risk_count, total_crimes)

    # Recency: prefer the more accurate "30 inside 90" comparison when
    # we have last_90_days; otherwise fall back to "30 vs. expected" which
    # only needs last_30_days plus the long-term average. The fallback
    # `expected_30_days` is derived from total_crimes / observation_days
    # if the caller didn't pre-compute it.
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

    # Trend: needs two equally-sized windows worth of counts. We accept
    # the long-form names (recent_count / older_count) and the short
    # legacy names (recent_half / older_half) so older callers keep
    # working without a migration.
    if pre_trend is not None:
        trend_score = float(pre_trend)
    else:
        recent_count = float(stats.get("recent_count", stats.get("recent_half", 0)) or 0)
        older_count = float(stats.get("older_count", stats.get("older_half", 0)) or 0)
        trend_score = _trend_from_recent_vs_older(recent_count, older_count)

    # Time-of-day risk: only meaningful when the caller knows what hour
    # the user is asking about. If unknown we use the neutral 50.0 so
    # the time component contributes nothing to the score in either
    # direction.
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
    """Convenience wrapper that returns ONLY the safety_score number.

    Most call sites in the codebase only need the headline number for a
    badge or a score bar — they don't care about the full breakdown.
    Wrapping `calculate_unified_risk_summary` here keeps that simpler
    use case readable AND guarantees they're using the same scoring
    logic as everything else.
    """
    summary = calculate_unified_risk_summary(stats, observation_days)
    return float(summary["safety_score"])

def calculate_breakdown(crime_counts: List[Dict[str, Any]], day_crimes: int, night_crimes: int) -> Dict[str, float]:
    """Build the radar-chart breakdown shown on the dashboard's "Crime Mix" panel.

    The radar chart has five spokes — violent, property, personal,
    day, night — and each spoke needs a 0-100 SAFETY value (high = good).
    We:
        1) Bucket every crime_type string into one of three categories
           by simple keyword matching. Unknown types fall into "property"
           because that is statistically the most common bucket and the
           least dramatic default.
        2) Convert each bucket's RAW COUNT into a safety score by
           penalising it on a per-incident slope:
               violent  → 15 points lost per incident (steepest)
               personal → 10 points lost per incident
               property →  5 points lost per incident
               day      →  3 points lost per daytime incident
               night    →  6 points lost per nighttime incident
                          (night is treated as more dangerous)
        3) Floor every result at 1.0 so a single very-busy area can't
           push a spoke to 0 and make the radar chart collapse to a dot.
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
    """Convert a safety_score back to a Low/Moderate/High/Critical label.

    Used in places that only have the safety number on hand and need the
    matching text label without re-running the whole scoring formula.
    """
    risk_score = 100.0 - float(_clamp(safety_score))
    return risk_label_from_risk_score(risk_score)

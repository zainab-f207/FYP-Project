# Alert Generation vs Area Safety Profile Calculation Analysis

## Executive Summary

Both **alert generation** and **area safety profile** calculations use the **same unified risk scoring engine** (`calculate_unified_risk_summary`), BUT they differ in:
1. **Time windows** (90-day alerts vs 12-month profiles)
2. **Data aggregation** (coordinate-radius vs area-name queries)
3. **Context usage** (real-time events vs historical profiles)

---

## Part 1: Core Unified Risk Calculation

**File**: [app/utils/risk.py](app/utils/risk.py#L154)

### The Universal Formula

```python
def calculate_unified_risk_summary(stats: Optional[Dict[str, Any]], observation_days: int = 365) -> Dict[str, Any]:
    """
    Shared scoring engine used across dashboard, alerts, prediction, and admin views.

    Formula (fixed):
      risk = 0.35*volume + 0.25*severity + 0.20*recency + 0.10*trend + 0.10*time
      safety = 100 - risk
    """
    # Returns: risk_score (%), safety_score (%), risk_level, risk_label, safety_grade
```

### Key Component Functions:

| Component | Weight | Calculation | Use Case |
|-----------|--------|-------------|----------|
| **Volume** | 35% | Poisson P(≥1 crime) = 1 - e^(-λ) where λ = total_crimes/days | Crime frequency density |
| **Severity** | 25% | Weighted avg: High×8.0 + Medium×5.0 + Low×2.0 / total | Crime types/weights |
| **Recency** | 20% | Using 30-day vs 90-day windows: (last_30 / (last_90/3)) × 100 | Recent spike detection |
| **Trend** | 10% | Recent half vs older half: 50 - (diff_pct × 0.5) | Direction of change |
| **Time** | 10% | Hour-of-day risk: (crimes_at_hour / avg_hourly) × 50 | Time-of-day factor |

### Risk Level Mapping:
- **0-20**: Low (Grade A, "Safe")
- **21-50**: Moderate (Grade B-C, "Caution")
- **51-80**: High (Grade D, "Warning")
- **81-100**: Critical (Grade F, "Avoid")

---

## Part 2: Alert Generation (Live Location Checking)

### Entry Point: Alert Notification System
**File**: [app/alert_notifications.py](app/alert_notifications.py#L140)

```python
class AlertNotificationSystem:
    async def get_real_safety_data(self, latitude: float, longitude: float, radius_km: float = 1.0) -> Dict[str, Any]:
        """Real-time safety assessment for live locations"""
```

#### Query Window: **90 DAYS** (Last 90 Days)

```sql
/* From alert_notifications.py line 97 */
SELECT
    COUNT(*) as total_crimes,
    SUM(CASE WHEN latitude BETWEEN lat-r AND lat+r 
            AND longitude BETWEEN lng-r AND lng+r 
            AND crime_date >= (NOW() - INTERVAL 90 DAY) THEN 1 ELSE 0 END) as last_90_days,
    SUM(CASE WHEN crime_date >= (NOW() - INTERVAL 30 DAY) THEN 1 ELSE 0 END) as last_30_days,
    ...
```

#### Alert Data Aggregation:
```python
# Lines 145-175 in alert_notifications.py
risk_summary = calculate_unified_risk_summary({
    'total_crimes': total_crimes,           # 365-day count
    'high_risk_count': high_risk_count,     # from 365d
    'medium_risk_count': medium_risk_count, # from 365d
    'last_30_days': last_30_days,           # RECENCY: 30d window
    'last_90_days': last_90_days,           # RECENCY: 90d window
    'recent_count': recent_half,            # TREND: recent half of period
    'older_count': older_half,              # TREND: older half of period
    'time_risk_score': time_risk_score,     # TIME: hour-of-day factor
}, 365)  # ← observation_days = 365

risk_pct = risk_summary['risk_score']       # Overall risk %
safety_score = risk_summary['safety_score'] # Overall safety score
risk_level = risk_summary['risk_level']     # "Low", "Moderate", "High", "Critical"
```

#### Alert Severity Determination:
**File**: [app/routes/alerts.py](app/routes/alerts.py#L909-L950)

```python
# Risk bands: 0-20 Safe | 21-50 Caution | 51-80 Warning | 81-100 Avoid
# (Line 502 in alert_notifications.py)

if safety_score < 25 or high_risk_crimes >= 5:
    severity = "critical"
    alert_type = "critical_risk_zone"
elif safety_score < 40 or high_risk_crimes >= 3:
    severity = "high"
    alert_type = "high_risk_zone"
elif safety_score < 70:
    severity = "medium"
    alert_type = "medium_risk_zone"
else:
    severity = "low"
    alert_type = "safe_area"
```

#### Alert Trigger Message:
```python
# Lines 915-930 in alerts.py
if risk_level in ("High", "Critical") or severity in ("high", "critical"):
    alert_trigger_reason = (
        f"{high_risk_crimes} high-risk incident(s) recorded near your "
        f"{location_type} location in the last 90 days{_7d_bit}{_top_crime_bit}."
    )
```

---

## Part 3: Area Safety Profile (Historical Dashboard)

### Entry Point: Area Profile Endpoint
**File**: [app/routes/crimes.py](app/routes/crimes.py#L678-L690)

```python
@router.get("/area-safety-profile")
def get_area_safety_profile(
    area: str = Query(...),
    months: int = Query(12, ge=1, le=36),  # ← Configurable: default 12 months
    crime_type: Optional[str] = Query(None),
    date: Optional[str] = Query(None),
    visit_time: Optional[str] = Query(None),
):
```

#### Query Window: **12 MONTHS** (Configurable 1-36 months)

```sql
/* Lines 610-720 in crimes.py - Area Profile Queries */
cutoff_main = (analysis_anchor_dt - timedelta(days=months * 30)).strftime('%Y-%m-%d')
# Default: 12 * 30 = 360 days (≈ 12 months)

-- Volume & Severity
SELECT COUNT(*) FROM crimes
WHERE area = %s AND crime_date >= %s  -- months * 30 days back

-- Recency (recent vs older half)
SELECT 
  SUM(CASE WHEN crime_date >= HALF_CUTOFF THEN 1 ELSE 0 END) as recent,
  SUM(CASE WHEN crime_date >= MAIN_CUTOFF AND crime_date < HALF_CUTOFF THEN 1 ELSE 0 END) as older
FROM crimes
WHERE area = %s AND crime_date >= MAIN_CUTOFF
```

#### Profile Data Aggregation:
```python
# Lines 671-687 in crimes.py (Area Safety Profile endpoint)
score_summary = calculate_unified_risk_summary(
    {
        "total_crimes": total_crimes,              # Full months * 30 window
        "volume_score": volume_score,              # Precomputed
        "severity_score": severity_score,          # Precomputed
        "recency_score": recency_score,            # Recent vs half-window
        "trend_score": trend_score,                # Recent half vs older half
        "time_risk_score": time_risk_score,        # Hour-of-day factor
    },
    observation_days=max(30, months * 30),  # ← Scaled to selected period
)

risk_score = score_summary["risk_score"]       # Overall risk %
safety_score = score_summary["safety_score"]   # Safety score (100 - risk_score)
risk_level = score_summary["risk_level"]       # "Low", "Moderate", "High", "Critical"
safety_grade = score_summary["safety_grade"]   # Grade: A-F
```

#### Profile Output Example:
```json
{
  "area": "Gulberg",
  "safety_score": 65,           // X/100 format
  "risk_score": 35,
  "risk_level": "Moderate",
  "safety_grade": "B",
  "crime_pressure": "Moderate",
  "area_ranking": { "rank": 5, "safer_than_pct": 60 },
  "last_30_days": 8,
  "last_7_days": 2,
  "monthly_counts": [...],
  "hourly_distribution": [...],
  "top_crimes": [...],
  "sub_areas": [...]
}
```

---

## Part 4: Key Differences Summary

### 1. **Time Windows**

| Aspect | Alerts (Live Check) | Profiles (Historical) |
|--------|---------------------|----------------------|
| Default Window | 365 days (fixed) | 360 days (12 months, configurable 30-1080d) |
| Context Used in calc | 90-day + 30-day windows | Full period + half-period windows |
| Recency Window | last_30 / last_90 | recent_half / older_half |
| Update Frequency | Real-time on demand | On-demand dashboard query |
| Use Case | "Is this location safe RIGHT NOW?" | "What's the historical safety trend?" |

### 2. **Data Aggregation Method**

| Aspect | Alerts | Profiles |
|--------|--------|----------|
| Lookup Type | **Coordinate-based radius query** | **Area-name query** |
| Query Radius | 1.0 km (default) | Full area boundary |
| Data Source | Crimes within radius around coordinates | All crimes in named area |
| Sub-aggregates | Single point summary | Area breakdown + subareas |
| Example Query | WHERE SQRT(...) <= 1.0 km | WHERE area = 'Gulberg' |

### 3. **Calculation Components**

| Component | Alerts | Profiles |
|-----------|--------|----------|
| Volume | Crimes in radius over 365d | Crimes in area over months |
| Severity | High/Med/Low counts in radius | High/Med/Low counts in area |
| Recency | last_30 vs last_90 directly | recent_half vs older_half |
| Trend | Recent vs Older half | Recent vs Older half |
| Time Score | Hour-of-day at alert time | Hour-of-day analysis |

### 4. **Output Mapping**

| Output | Alerts | Profiles |
|--------|--------|----------|
| Primary Score | `risk_pct` (%) | `safety_score` (/100) |
| Risk Label | "High", "Critical" | "Moderate", "High" |
| Action Label | "Warning", "Avoid" | "Caution", "Warning" |
| Grade | N/A | "A", "B", "C" |
| Confidence | "low", "medium", "high" | Implicit in data volume |

---

## Part 5: File Locations & Key Functions

### Core Calculation Engine
- **[app/utils/risk.py (L154-280)](app/utils/risk.py#L154)** - Main unified risk calculation
  - `calculate_unified_risk_summary()` - Universal formula
  - `_volume_score()`, `_severity_score()`, `_recency_from_recent_windows()`
  - `risk_label_from_risk_score()`, `safety_grade_from_score()`

### Alert Generation
- **[app/alert_notifications.py (L140-180)](app/alert_notifications.py#L140)** - Alert notification system
  - `get_real_safety_data()` - Coordinates → 90-day window risk
- **[app/routes/alerts.py (L100-150)](app/routes/alerts.py#L100)** - Get safety stats by coordinates
  - `get_safety_stats_by_coords()` - Radius-based querying
- **[app/routes/alerts.py (L900-950)](app/routes/alerts.py#L900)** - Create and send alerts
  - Alert severity determination, trigger messages

### Area Safety Profile
- **[app/routes/crimes.py (L678-900)](app/routes/crimes.py#L678)** - Area safety profile endpoint
  - `/area-safety-profile` - Main profile calculation
  - 12-month default with configurable months parameter
  - Hourly/daily distributions, trend analysis

---

## Part 6: Endpoint Comparison

### Alert Endpoints
```
GET /alerts/get-safety-stats-by-coords?lat=X&lng=Y&radius_km=1.0
  → Uses 90-day window for recency
  → Returns: risk_pct, safety_score, risk_level

POST /alerts/check-location
  → Monitors saved home/work locations
  → Uses coordinated-radius approach

GET /alerts/check-risk?latitude=X&longitude=Y
  → Real-time risk check
  → High-risk threshold: safety_score < 40 OR high_risk_crimes >= 3
```

### Profile Endpoints
```
GET /crimes/area-safety-profile?area=Gulberg&months=12
  → Returns comprehensive historical profile
  → Hourly/daily/trend distributions
  → Sub-area breakdowns
  → Ranking among all Lahore areas

GET /crimes?area=Gulberg
  → Raw crime records
  → Optional filtering by type, date range
```

---

## Part 7: Practical Example

### Scenario: User checks "Gulberg at 9 PM"

#### Alert System (Real-time)
```
1. Call: GET /alerts/get-safety-stats-by-coords?lat=31.55&lng=74.33&radius_km=1.0
2. Query 90-day window + 30-day spike detection
3. Calculate risk = 0.35*(volume) + 0.25*(severity) + 0.20*(recent30/recent90) + 0.10*(trend) + 0.10*(night_penalty)
4. Result: risk_pct = 62%, safety_score = 38%, risk_level = "High"
5. Action: Send "HIGH RISK" alert because safety_score < 40
6. Message: "High risk detected - 4 high-risk incidents in last 90 days"
```

#### Profile System (Historical)
```
1. Call: GET /crimes/area-safety-profile?area=Gulberg&months=12&visit_time=21:00
2. Query 360-day window + 180-day half comparisons
3. Calculate risk components from year-long data
4. Result: safety_score = 62/100, risk_level = "Moderate", grade = "B"
5. Context: "Gulberg ranks #5 safer than 60% of Lahore"
6. Insight: "Evening (6-8 PM) is safest. Night (9 PM-4 AM) has 40% more incidents"
```

---

## Part 8: Time Window Implications

### Why 90-day window for alerts?
- **Real-time responsiveness**: Captures recent crime spikes
- **Recency calculation**: Uses `last_30 / (last_90/3)` ratio to detect acceleration
- **False positive reduction**: Avoids long-term noise when making immediate decisions

### Why 12-month window for profiles?
- **Historical trends**: Shows seasonal patterns (Eid, holidays, weather)
- **Reliability**: 360+ crimes provides high confidence
- **Comparability**: Full year allows fair ranking across areas
- **User insight**: Yearly perspective helps vacation/move decisions

---

## Part 9: Risk Level Banding

### Risk Labels by Score
```python
# Unified across both systems (app/utils/risk.py L21-32)

risk_score → risk_level → action_label
0-20    → "Low"       → "Safe"
21-50   → "Moderate"  → "Caution"
51-80   → "High"      → "Warning"
81-100  → "Critical"  → "Avoid"

safety_score (= 100 - risk_score) → safety_grade
80-100  → "A"
65-79   → "B"
50-64   → "C"
35-49   → "D"
<35     → "F"
```

### Alert Severity Mapping (app/alert_notifications.py L502-545)
```
Composite risk bands: 
  0-20 → Safe (green)     
  21-50 → Caution (yellow)
  51-80 → Warning (orange) 
  81-100 → Avoid (red)
```

---

## Conclusion

**Both systems use identical risk formulas, but differ critically in:**
- **Time scope**: 90-90 (alerts) vs 360 (profiles)
- **Spatial scope**: Radius query (alerts) vs named area (profiles)
- **Information goal**: "Is NOW safe?" vs "What's the TREND?"
- **Update cadence**: Real-time on-demand (alerts) vs dashboard query (profiles)

**Key insight**: The `observation_days` parameter in `calculate_unified_risk_summary()` is the primary differentiator — alerts pass 365, profiles pass `months*30`.

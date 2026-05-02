from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from typing import List, Optional, Dict, Any, cast
from datetime import datetime, timedelta
import logging
import sys
import numpy as np
import pandas as pd
import difflib
import joblib
import os
import json
from mysql.connector import Error as MySQLError
from app.core.database import get_db_connection
from app.utils.validation import validate_date_format, validate_crime_type
from app.utils.area_normalization import area_like_pattern
from app.core.config import MODEL_DIR
from app.utils.risk import calculate_unified_risk_summary
from app.dependencies import get_username_from_token
from app.models.schemas import Crime, PredictRiskRequest, CrimeCreate, AIRouteSafetyRequest, AIRouteSafetyResponse
from app.services.route_safety_analyzer_ai import AIRouteSafetyAnalyzer

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/crimes", tags=["crimes"])


def _clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(high, value))


def _parse_visit_hour(visit_time: Optional[str]) -> Optional[int]:
    if not visit_time:
        return None
    v = visit_time.strip()
    if not v:
        return None
    for fmt in ("%H:%M", "%H:%M:%S", "%I:%M %p"):
        try:
            return datetime.strptime(v, fmt).hour
        except ValueError:
            continue
    return None


def _crime_user_category(crime_type: Optional[str]) -> str:
    text = (crime_type or "").lower()
    if any(k in text for k in ("theft", "robbery", "burglary", "snatch", "steal")):
        return "Theft & Robbery"
    if any(k in text for k in ("assault", "hurt", "murder", "rape", "kidnap", "terror")):
        return "Violence"
    if any(k in text for k in ("fire", "explosive", "mischief", "property", "damage", "arson")):
        return "Property Damage"
    if any(k in text for k in ("fraud", "forgery", "cheat", "embezzl")):
        return "Fraud"
    if any(k in text for k in ("intimidation", "threat", "harass", "extortion")):
        return "Threats & Harassment"
    if any(k in text for k in ("narcotic", "drug", "intox")):
        return "Narcotics"
    if any(k in text for k in ("disobedience", "public servant", "obstruct", "rioting", "disturb")):
        return "Public Disturbance"
    return "Other"


_CATEGORY_SEVERITY_WEIGHT = {
    "Theft & Robbery": 2,
    "Fraud": 3,
    "Public Disturbance": 3,
    "Threats & Harassment": 4,
    "Violence": 5,
    "Property Damage": 6,
    "Narcotics": 7,
    "Other": 4,
}

# ── New RF model (crime_risk_model) ──────────────────────────────────────────
# This model uses numeric features (severity, temporal, spatial) and handles
# unseen areas / crime types via median fallback -- no hardcoded Medium.
_CRM_DIR = os.path.join(os.path.dirname(__file__), '..', 'crime_risk_model')
sys.path.insert(0, _CRM_DIR)
try:
    from utils.helpers import engineer_features, load_model as _crm_load_model, compute_raw_risk_score as _crm_raw_score
    from utils.model_watcher import get_watcher as _get_watcher, register_reload_callback as _reg_reload
    from utils.poisson_predictor import load_artifacts as _load_poisson, predict as _poisson_predict
    from utils.auto_retrain import register_reload_callback as _ar_register, notify_new_record as _ar_notify
    from utils.helpers import infer_severity_from_keywords as _infer_sev
    _crm_model, _crm_scaler, _crm_artifacts = _crm_load_model(
        os.path.join(_CRM_DIR, 'models')
    )
    logger.info("crime_risk_model RF loaded OK (classes: %s)", _crm_artifacts.get('label_classes'))

    try:
        _poisson_artifacts = _load_poisson(
            os.path.join(_CRM_DIR, 'models', 'poisson_artifacts.json')
        )
        logger.info(
            "Poisson artifacts loaded: %d area×crime pairs",
            len(_poisson_artifacts.get('pair_lambdas', {})),
        )
    except Exception as _pe:
        _poisson_artifacts = None
        logger.warning("Poisson artifacts not available: %s", _pe)

    # Register hot-reload callback so ModelWatcher can reload model after retraining
    def _hot_reload_model():
        global _crm_model, _crm_scaler, _crm_artifacts, _poisson_artifacts
        try:
            _crm_model, _crm_scaler, _crm_artifacts = _crm_load_model(
                os.path.join(_CRM_DIR, 'models')
            )
            logger.info("[hot-reload] RF model reloaded OK (classes: %s)",
                        _crm_artifacts.get('label_classes'))
        except Exception as _re:
            logger.error("[hot-reload] RF model reload failed: %s", _re)
        try:
            _poisson_artifacts = _load_poisson(
                os.path.join(_CRM_DIR, 'models', 'poisson_artifacts.json')
            )
            logger.info("[hot-reload] Poisson artifacts reloaded OK")
        except Exception as _pe:
            logger.warning("[hot-reload] Poisson reload failed: %s", _pe)
    _reg_reload(_hot_reload_model)
    # Also register with the auto-retrain guard so it can trigger hot-reload
    # after an automatic background retrain
    try:
        _ar_register(_hot_reload_model)
    except Exception:
        pass  # non-fatal

except Exception as _e:
    logger.warning("crime_risk_model RF not available: %s", _e)
    _crm_model = _crm_scaler = _crm_artifacts = _poisson_artifacts = None
    _get_watcher = None  # type: ignore

# ── Legacy RF model (label-encoder based) -- kept as last-resort fallback ───
try:
    model = joblib.load(os.path.join(MODEL_DIR, 'random_forest_model.joblib'))
    le_area  = joblib.load(os.path.join(MODEL_DIR, 'label_encoder_area.joblib'))
    le_crime = joblib.load(os.path.join(MODEL_DIR, 'label_encoder_crime.joblib'))
    le_risk  = joblib.load(os.path.join(MODEL_DIR, 'label_encoder_risk.joblib'))
except Exception as e:
    logger.warning(f"Legacy RF model not loaded: {e}")
    model = le_area = le_crime = le_risk = None

@router.get("", response_model=List[Crime])
def get_crimes(
    area: Optional[str] = Query(None, description="Filter by area", max_length=100),
    crime_type: Optional[str] = Query(None, description="Filter by crime type", max_length=50),
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)", regex=r'^\d{4}-\d{2}-\d{2}$'),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)", regex=r'^\d{4}-\d{2}-\d{2}$'),
    limit: Optional[int] = Query(1000, description="Maximum number of records to return (omit or leave blank for all)", ge=1)
):
    """Retrieve crime data with optional filters"""
    # Validate inputs
    if start_date and not validate_date_format(start_date):
        raise HTTPException(status_code=400, detail="Invalid start_date format. Use YYYY-MM-DD")
    if end_date and not validate_date_format(end_date):
        raise HTTPException(status_code=400, detail="Invalid end_date format. Use YYYY-MM-DD")
    if start_date and end_date and start_date > end_date:
        raise HTTPException(status_code=400, detail="start_date cannot be later than end_date")
    if crime_type:
        crime_type = validate_crime_type(crime_type)
    if area:
        area = area.strip()

    conn, cursor = None, None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        query = """
            SELECT id, area, area_urdu, area_translit, crime_type, crime_date, crime_time, latitude, longitude, risk_level
            FROM crimes
            WHERE 1=1
        """
        params = []

        if area:
            query += " AND area = %s"
            params.append(area)
        if crime_type:
            query += " AND crime_type = %s"
            params.append(crime_type)
        if start_date:
            query += " AND crime_date >= %s"
            params.append(start_date)
        if end_date:
            query += " AND crime_date <= %s"
            params.append(end_date)

        if limit is not None:
            query += " ORDER BY crime_date DESC, id DESC LIMIT %s"
            params.append(limit)
        else:
            query += " ORDER BY crime_date DESC, id DESC"

        cursor.execute(query, params)
        rows = cursor.fetchall()

        crimes_list = []
        for row in rows:
            try:
                row_dict = cast(Dict[str, Any], row)
                
                latitude = row_dict.get("latitude")
                longitude = row_dict.get("longitude")

                # Build a combined datetime string so the frontend gets the
                # real time without UTC-offset ambiguity.
                # Format: "YYYY-MM-DD HH:MM:SS" (no Z / timezone suffix).
                raw_date = str(row_dict.get("crime_date", "Unknown"))
                raw_time = (row_dict.get("crime_time") or "").strip()
                if raw_time:
                    # Normalise 12-hour ("03:22 AM") to 24-hour "HH:MM:SS"
                    try:
                        from datetime import datetime as _dt
                        t_obj = _dt.strptime(raw_time, "%I:%M %p")
                        combined_date = f"{raw_date} {t_obj.strftime('%H:%M:%S')}"
                    except ValueError:
                        # Already 24-hour or unknown format — use as-is
                        combined_date = f"{raw_date} {raw_time}"
                else:
                    combined_date = raw_date

                crime_record = Crime(
                    id=int(row_dict["id"]),
                    area=row_dict.get("area", "Unknown"),
                    area_urdu=row_dict.get("area_urdu") or None,
                    area_translit=row_dict.get("area_translit") or None,
                    type=row_dict.get("crime_type", "Unknown"),
                    date=combined_date,
                    crime_time=row_dict.get("crime_time") or None,
                    coordinates=[
                        float(latitude),
                        float(longitude)
                    ],
                    risk_level=row_dict.get("risk_level", "Unknown")
                )
                crimes_list.append(crime_record)
            except Exception as e:
                logger.warning(f"Skipping bad row: {e}")
                continue

        logger.info(f"Retrieved {len(crimes_list)} records")
        return crimes_list

    except Exception as e:
        logger.error(f"MySQL error: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve crime data")
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()

@router.get("/nearest-area")
def get_nearest_area(lat: float = Query(...), lon: float = Query(...)):
    """
    Given GPS coordinates, return the nearest English area name from the
    `areas` table (Haversine distance).  Used by the OCR panel to translate
    an Urdu thana name into the English name the ML model knows.
    """
    conn, cursor = None, None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            """
            SELECT area_name,
                   ROUND((6371 * acos(LEAST(1.0,
                     cos(radians(%s)) * cos(radians(latitude))
                     * cos(radians(longitude) - radians(%s))
                     + sin(radians(%s)) * sin(radians(latitude))
                   ))), 2) AS dist_km
            FROM areas
            ORDER BY dist_km ASC
            LIMIT 1
            """,
            (lat, lon, lat),
        )
        row = cursor.fetchone()
        if row:
            return {"area_name": row["area_name"], "dist_km": float(row["dist_km"])}
        return {"area_name": None, "dist_km": None}
    except Exception as e:
        logger.error(f"nearest-area error: {e}")
        raise HTTPException(status_code=500, detail="nearest-area lookup failed")
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()


@router.get("/area-safety-profile")
def get_area_safety_profile(
    area: str = Query(..., max_length=100, description="Area name"),
    months: int = Query(12, ge=1, le=36, description="Look-back period in months"),
    days: Optional[int] = Query(None, ge=1, le=3650, description="Optional exact look-back period in days (overrides months)"),
    crime_type: Optional[str] = Query(None, max_length=120, description="Optional crime type filter"),
    date: Optional[str] = Query(None, description="Optional target date YYYY-MM-DD"),
    visit_time: Optional[str] = Query(None, description="Optional visit time HH:MM or HH:MM AM/PM"),
    lat: Optional[float] = Query(None, description="Optional latitude for radius scope"),
    lng: Optional[float] = Query(None, description="Optional longitude for radius scope"),
    radius_km: float = Query(1.0, ge=0.1, le=25.0, description="Radius in km for coordinate scope"),
):
    """
    Comprehensive safety profile for an area across ALL crime types.
    Returns safety score, hourly/daily distributions, top crime types,
    trend, and ranking among all Lahore areas.
    """
    area = area.strip()
    if not area:
        raise HTTPException(status_code=400, detail="area is required")

    logger.info(
        "📊 /area-safety-profile called — area=%r months=%s days=%s crime_type=%r "
        "anchor_date=%s visit_time=%s | engine=calculate_unified_risk_summary "
        "(deterministic aggregation, NOT an ML prediction)",
        area, months, days, crime_type, date or "now", visit_time,
    )

    # Rely on loose matching (area_like_pattern) to handle DHA variants without hard-coding transformation
    area_pattern = area_like_pattern(area)
    if date and not validate_date_format(date):
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")

    selected_hour = _parse_visit_hour(visit_time)
    analysis_anchor_dt = datetime.now()
    if date:
        analysis_anchor_dt = datetime.strptime(date, "%Y-%m-%d")
    crime_type_filter = crime_type.strip() if crime_type else None
    area_filter_sql = " AND crime_type = %s" if crime_type_filter else ""
    area_filter_params = [crime_type_filter] if crime_type_filter else []
    city_filter_sql = " AND crime_type = %s" if crime_type_filter else ""
    city_filter_params = [crime_type_filter] if crime_type_filter else []

    # Logic Alignment: keep area profile strictly area-based by default.
    # Radius fallback can surface unrelated nearby incidents and confuse users.
    effective_location_sql = "LOWER(area) LIKE %s"
    effective_location_params = [area_pattern]
    scope_mode = "area"

    conn, cursor = None, None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # 1) Try Area lookup first (administrative), with exact-days override.
        lookback_days = int(days) if days else int(months * 30)
        cutoff_main = (analysis_anchor_dt - timedelta(days=lookback_days)).strftime('%Y-%m-%d')
        cursor.execute(
            f"SELECT COUNT(*) as total FROM crimes WHERE area LIKE %s AND crime_date >= %s",
            (area_pattern, cutoff_main)
        )
        check_row = cursor.fetchone()
        
        # Keep strict area mode; do not silently fall back to radius.
        # This guarantees that area-specific cards (risk factors, trend, counts)
        # are truly based on the selected area string + filters.

        location_scope_sql = effective_location_sql
        location_scope_params = effective_location_params

        cutoff_half = (analysis_anchor_dt - timedelta(days=(months // 2) * 30)).strftime('%Y-%m-%d')
        analysis_anchor_date = analysis_anchor_dt.strftime('%Y-%m-%d')

        # 1) Area incident count (Full aggregation)

        cutoff_main = (analysis_anchor_dt - timedelta(days=lookback_days)).strftime('%Y-%m-%d')
        cutoff_half = (analysis_anchor_dt - timedelta(days=(months // 2) * 30)).strftime('%Y-%m-%d')
        analysis_anchor_date = analysis_anchor_dt.strftime('%Y-%m-%d')

        # 1) Area incident count
        cursor.execute(
            f"""
            SELECT COUNT(*) AS total,
                   SUM(CASE WHEN risk_level = 'High' OR crime_type COLLATE utf8mb4_general_ci LIKE '%%Murder%%' OR crime_type COLLATE utf8mb4_general_ci LIKE '%%Robbery%%' OR crime_type COLLATE utf8mb4_general_ci LIKE '%%Dacoity%%' OR crime_type COLLATE utf8mb4_general_ci LIKE '%%Assault%%' THEN 1 ELSE 0 END) AS high_risk_count,
                   SUM(CASE WHEN risk_level = 'Medium' AND NOT (crime_type COLLATE utf8mb4_general_ci LIKE '%%Murder%%' OR crime_type COLLATE utf8mb4_general_ci LIKE '%%Robbery%%' OR crime_type COLLATE utf8mb4_general_ci LIKE '%%Dacoity%%' OR crime_type COLLATE utf8mb4_general_ci LIKE '%%Assault%%') THEN 1 ELSE 0 END) AS medium_risk_count
            FROM crimes WHERE {location_scope_sql} AND crime_date >= %s{area_filter_sql}
            """,
            (*location_scope_params, cutoff_main, *area_filter_params),
        )
        row = cursor.fetchone()
        total_crimes = int(row["total"] or 0) if row else 0
        high_risk_count = int(row["high_risk_count"] or 0) if row else 0
        medium_risk_count = int(row["medium_risk_count"] or 0) if row else 0

        # Keep timeline strictly anchored to requested date/NOW.
        # Do not shift to latest dataset date when window has sparse/no records.

        # 2) City baseline and area ranking
        cursor.execute(
            f"""
            SELECT AVG(cnt) AS avg_cnt FROM (
                SELECT COUNT(*) AS cnt
                FROM crimes
                WHERE crime_date >= %s{city_filter_sql}
                GROUP BY area
            ) sub
            """,
            (cutoff_main, *city_filter_params),
        )
        row = cursor.fetchone()
        city_avg = float(row["avg_cnt"] or 1.0)

        cursor.execute(
            f"""
            SELECT COUNT(*) + 1 AS rank_num,
                   (SELECT COUNT(DISTINCT area) FROM crimes WHERE crime_date >= %s{city_filter_sql}) AS total_areas
            FROM (
                SELECT area, COUNT(*) AS cnt
                FROM crimes
                WHERE crime_date >= %s{city_filter_sql}
                GROUP BY area
                HAVING cnt > %s
            ) more_dangerous
            """,
            (cutoff_main, *city_filter_params, cutoff_main, *city_filter_params, total_crimes),
        )
        rank_row = cursor.fetchone()
        rank_num = int(rank_row["rank_num"]) if rank_row else 1
        total_areas = int(rank_row["total_areas"]) if rank_row else 1
        safer_than_pct = round((rank_num - 1) / max(total_areas, 1) * 100)

        # 3) Volume and severity components (used for UI display only, not risk core)
        raw_ratio = total_crimes / max(city_avg, 1)
        density_ratio = float(round(raw_ratio, 1))
        crime_density_label = f"{density_ratio}x city average"

        cursor.execute(
            f"""
            SELECT crime_type, COUNT(*) AS cnt
            FROM crimes
                        WHERE {location_scope_sql} AND crime_date >= %s{area_filter_sql}
              AND crime_type IS NOT NULL
            GROUP BY crime_type
            """,
                        (*location_scope_params, cutoff_main, *area_filter_params),
        )
        sev_rows = cursor.fetchall()
        weighted_sum = 0.0
        weighted_cnt = 0
        for r in sev_rows:
            ctype = r.get("crime_type")
            cnt = int(r.get("cnt") or 0)
            cat = _crime_user_category(ctype)
            wt = _CATEGORY_SEVERITY_WEIGHT.get(cat, 4)
            weighted_sum += cnt * wt
            weighted_cnt += cnt
        
        weighted_avg = (weighted_sum / weighted_cnt) if weighted_cnt > 0 else 4.0

        # 4) Hourly distribution with smoothing
        cursor.execute(
            f"""
            SELECT HOUR(crime_time) AS hr, COUNT(*) AS cnt
            FROM crimes
            WHERE {location_scope_sql} AND crime_date >= %s AND crime_time IS NOT NULL{area_filter_sql}
            GROUP BY HOUR(crime_time)
            ORDER BY HOUR(crime_time)
            """,
            (*location_scope_params, cutoff_main, *area_filter_params),
        )
        hour_map = {int(r["hr"]): int(r["cnt"]) for r in cursor.fetchall()}
        raw_hour_counts = [hour_map.get(h, 0) for h in range(24)]
        total_hour_obs = sum(raw_hour_counts)
        global_hour_avg = (total_hour_obs / 24.0) if total_hour_obs > 0 else 0.0
        smoothed_counts = []
        for h in range(24):
            prev_h = raw_hour_counts[(h - 1) % 24]
            cur_h = raw_hour_counts[h]
            next_h = raw_hour_counts[(h + 1) % 24]
            smooth = (prev_h + (2.0 * cur_h) + next_h) / 4.0
            if total_hour_obs < 48:
                smooth = (0.6 * smooth) + (0.4 * global_hour_avg)
            smoothed_counts.append(smooth)

        max_hour_cnt = max(smoothed_counts, default=1.0) or 1.0
        hourly = [
            {
                "hour": h,
                "count": raw_hour_counts[h],
                "smoothed_count": round(smoothed_counts[h], 2),
                "pct": round(smoothed_counts[h] / max_hour_cnt * 100),
            }
            for h in range(24)
        ]

        period_hours = {
            "Night": list(range(0, 6)),
            "Morning": list(range(6, 12)),
            "Afternoon": list(range(12, 18)),
            "Evening": list(range(18, 24)),
        }
        period_score = {
            name: float(sum(smoothed_counts[h] for h in hrs))
            for name, hrs in period_hours.items()
        }
        if total_hour_obs == 0:
            safest_hours = []
            riskiest_hours = []
            safest_period = None
            riskiest_period = None
        else:
            safest_period = min(period_score, key=period_score.get) if period_score else "Morning"
            riskiest_period = max(period_score, key=period_score.get) if period_score else "Evening"
            safest_hours = period_hours.get(safest_period, [])
            riskiest_hours = period_hours.get(riskiest_period, [])

        def fmt_h(h):
            ampm = 'AM' if h < 12 else 'PM'
            return f"{h % 12 or 12} {ampm}"

        def hours_to_range(hrs):
            if not hrs:
                return 'N/A'
            hrs = sorted(set(hrs))
            return f"{fmt_h(hrs[0])}-{fmt_h(hrs[-1])}" if len(hrs) > 1 else fmt_h(hrs[0])

        safest_hour_range = hours_to_range(safest_hours)
        riskiest_hour_range = hours_to_range(riskiest_hours)
        if total_hour_obs == 0:
            recommended_visit_window = "N/A"
        else:
            best_daylight_period = min(["Morning", "Afternoon", "Evening"], key=lambda p: period_score.get(p, float('inf')))
            recommended_visit_window = hours_to_range(period_hours.get(best_daylight_period, list(range(10, 18))))

        if selected_hour is not None:
            selected_hour_count = smoothed_counts[selected_hour]
            avg_hourly = sum(smoothed_counts) / 24.0 if smoothed_counts else 0.0
            if avg_hourly > 0:
                time_risk_score = _clamp((selected_hour_count / avg_hourly) * 50.0)
            else:
                time_risk_score = 50.0
        else:
            time_risk_score = 50.0

        # 5) Day-of-week distribution
        cursor.execute(
            f"""
            SELECT DAYNAME(crime_date) AS day_name,
                   DAYOFWEEK(crime_date) AS day_num,
                   COUNT(*) AS cnt
            FROM crimes
            WHERE {location_scope_sql} AND crime_date >= %s{area_filter_sql}
            GROUP BY DAYNAME(crime_date), DAYOFWEEK(crime_date)
            ORDER BY DAYOFWEEK(crime_date)
            """,
            (*location_scope_params, cutoff_main, *area_filter_params),
        )
        dow_rows = cursor.fetchall()
        max_dow = max((int(r["cnt"]) for r in dow_rows), default=1)
        weekly_avg = sum(int(r["cnt"]) for r in dow_rows) / max(len(dow_rows), 1) if dow_rows else 1
        dow_data = [
            {
                "day": r["day_name"],
                "count": int(r["cnt"]),
                "pct": round(int(r["cnt"]) / max_dow * 100),
                "vs_avg": round((int(r["cnt"]) - weekly_avg) / max(weekly_avg, 1) * 100),
            }
            for r in dow_rows
        ]
        safest_dow = min(dow_data, key=lambda d: d["count"]) if dow_data else None
        riskiest_dow = max(dow_data, key=lambda d: d["count"]) if dow_data else None
        safest_day = safest_dow["day"] if safest_dow else None
        riskiest_day = riskiest_dow["day"] if riskiest_dow else None
        safest_day_vs_avg = safest_dow["vs_avg"] if safest_dow else None
        riskiest_day_vs_avg = riskiest_dow["vs_avg"] if riskiest_dow else None

        # 6) Top risk factors: real crime labels from DB (no category bucketing)
        cursor.execute(
            f"""
            SELECT crime_type, COUNT(*) AS cnt
            FROM crimes
            WHERE {location_scope_sql} AND crime_date >= %s AND crime_type IS NOT NULL{area_filter_sql}
            GROUP BY crime_type
            ORDER BY cnt DESC
            """,
            (*location_scope_params, cutoff_main, *area_filter_params),
        )
        top_rows = cursor.fetchall()
        top_crimes = []
        # Fix lint: Ensure top_rows is treated as indexable slice
        rows_to_process = (top_rows or [])[:10]
        for r in rows_to_process:
            if isinstance(r, dict):
                label = str(r.get("crime_type") or "Unknown").strip() or "Unknown"
                cnt = int(r.get("cnt") or 0)
                top_crimes.append({
                    "type": label,
                    "display_type": label,
                    "crime_type": label,
                    "display_name": label,
                    "count": cnt,
                    "pct": round(cnt / max(total_crimes, 1) * 100, 1),
                })

        # 7) Trend and recency
        # Calculate the actual number of days in the analysis window
        lookback_days = (analysis_anchor_dt - datetime.strptime(cutoff_main, '%Y-%m-%d')).days + 1

        cursor.execute(
            f"""
            SELECT
              SUM(CASE WHEN crime_date >= %s THEN 1 ELSE 0 END) AS recent,
              SUM(CASE WHEN crime_date >= %s AND crime_date < %s THEN 1 ELSE 0 END) AS older,
              SUM(CASE WHEN crime_date >= %s THEN 1 ELSE 0 END) AS r30,
              SUM(CASE WHEN crime_date >= %s THEN 1 ELSE 0 END) AS r7,
              SUM(CASE WHEN crime_date >= %s THEN 1 ELSE 0 END) AS r24h
            FROM crimes
            WHERE {location_scope_sql} AND crime_date >= %s{area_filter_sql}
            """,
            (
                cutoff_half, 
                cutoff_main, cutoff_half,
                (analysis_anchor_dt - timedelta(days=30)).strftime('%Y-%m-%d'),
                (analysis_anchor_dt - timedelta(days=7)).strftime('%Y-%m-%d'),
                (analysis_anchor_dt - timedelta(hours=24)).strftime('%Y-%m-%d %H:%M:%S'),
                *location_scope_params, cutoff_main, *area_filter_params
            ),

        )
        t_row = cursor.fetchone()
        recent = int(t_row["recent"] or 0) if t_row else 0
        older = int(t_row["older"] or 0) if t_row else 0
        last_30_days = int(t_row["r30"] or 0) if t_row else 0
        last_7_days = int(t_row["r7"] or 0) if t_row else 0
        last_24_h = int(t_row["r24h"] or 0) if t_row else 0

        if older == 0:
            if recent > 0:
                trend_dir, change_pct = 'increasing', 100.0
                trend_diff_pct = 100.0
            else:
                trend_dir, change_pct = 'stable', 0
                trend_diff_pct = 0.0
        else:
            diff = (recent - older) / older * 100
            trend_diff_pct = diff
            if diff > 10:
                trend_dir, change_pct = 'increasing', round(diff, 1)
            elif diff < -10:
                trend_dir, change_pct = 'decreasing', round(abs(diff), 1)
            else:
                trend_dir, change_pct = 'stable', round(abs(diff), 1)

        ref_dt = analysis_anchor_dt
        ref_date_str = ref_dt.strftime('%Y-%m-%d')
        last_30_days_ref_date = ref_date_str

        half = max(months // 2, 1)
        recent_monthly_avg = (recent / half) if half > 0 else 0.0
        older_monthly_avg = (older / half) if half > 0 else 0.0
        if recent_monthly_avg > 0:
            recency_score = _clamp((last_30_days / recent_monthly_avg) * 100.0)
        else:
            recency_score = 50.0 if last_30_days == 0 else 100.0

        trend_score = _clamp(50.0 - (trend_diff_pct * 0.5))

        # 8) 90-day momentum
        cutoff_90d = (analysis_anchor_dt - timedelta(days=90)).strftime('%Y-%m-%d')
        cutoff_180d = (analysis_anchor_dt - timedelta(days=180)).strftime('%Y-%m-%d')
        cursor.execute(
            f"""
            SELECT
              SUM(CASE WHEN crime_date >= %s THEN 1 ELSE 0 END) AS r90,
              SUM(CASE WHEN crime_date >= %s AND crime_date < %s THEN 1 ELSE 0 END) AS p90
            FROM crimes
                        WHERE {location_scope_sql} AND crime_date >= %s{area_filter_sql}
            """,
                        (cutoff_90d, cutoff_180d, cutoff_90d, *location_scope_params, cutoff_180d, *area_filter_params),
        )
        mom_row = cursor.fetchone()
        r90 = int(mom_row["r90"] or 0) if mom_row else 0
        p90 = int(mom_row["p90"] or 0) if mom_row else 0
        if p90 == 0:
            momentum_dir, momentum_pct = 'stable', 0
        else:
            d90 = (r90 - p90) / p90 * 100
            if d90 > 10:
                momentum_dir, momentum_pct = 'rising', round(d90, 1)
            elif d90 < -10:
                momentum_dir, momentum_pct = 'declining', round(abs(d90), 1)
            else:
                momentum_dir, momentum_pct = 'stable', round(abs(d90), 1)

        # 9) Unified weighted risk score and labels (shared engine)
        score_summary = calculate_unified_risk_summary(
            {
                "total_crimes": total_crimes,
                "high_risk_count": high_risk_count,
                "medium_risk_count": medium_risk_count,
                "recency_score": recency_score,
                "trend_score": trend_score,
                "time_risk_score": time_risk_score,
            },
            observation_days=lookback_days, # Use actual filtered window for risk base
        )
        risk_score = score_summary["risk_score"]
        safety_score = score_summary["safety_score"]
        risk_level = score_summary["risk_level"]
        safety_grade = score_summary["safety_grade"]
        data_confidence = score_summary["data_confidence"]

        logger.info(
            "✅ AREA-SAFETY-PROFILE computed for %r (window=%dd) → "
            "risk=%s safety_score=%.1f%% grade=%s confidence=%s | "
            "inputs: total=%d high=%d medium=%d recency=%.1f trend=%.1f time=%.1f | "
            "rank=%d/%d (safer than %d%%) density=%.1fx city avg",
            area, lookback_days,
            risk_level, safety_score, safety_grade, data_confidence,
            total_crimes, high_risk_count, medium_risk_count,
            recency_score, trend_score, time_risk_score,
            rank_num, total_areas, safer_than_pct, density_ratio,
        )

        cursor.execute(
            f"""
            SELECT COUNT(*) AS total,
                   SUM(CASE WHEN risk_level = 'High' THEN 1 ELSE 0 END) AS high_risk_count,
                   SUM(CASE WHEN risk_level = 'Medium' THEN 1 ELSE 0 END) AS medium_risk_count,
                   MIN(crime_date) AS start_dt,
                   MAX(crime_date) AS end_dt
            FROM crimes
            WHERE {location_scope_sql}{area_filter_sql}
            """,
            (*location_scope_params, *area_filter_params),
        )
        ov_row = cursor.fetchone() or {}
        overall_total_crimes = int(ov_row.get("total") or 0)
        overall_start_dt = ov_row.get("start_dt")
        overall_end_dt = ov_row.get("end_dt")

        def _dt_to_str(val):
            if not val:
                return None
            return val.strftime('%Y-%m-%d') if hasattr(val, 'strftime') else str(val)

        overall_start_str = _dt_to_str(overall_start_dt)
        overall_end_str = _dt_to_str(overall_end_dt)

        cursor.execute(
            f"""
            SELECT AVG(cnt) AS avg_cnt FROM (
                SELECT COUNT(*) AS cnt
                FROM crimes
                WHERE 1 = 1{city_filter_sql}
                GROUP BY area
            ) sub
            """,
            (*city_filter_params,),
        )
        ov_city_row = cursor.fetchone()
        overall_city_avg = float((ov_city_row or {}).get("avg_cnt") or 1.0)

        cursor.execute(
            f"""
            SELECT crime_type, COUNT(*) AS cnt
            FROM crimes
                        WHERE {location_scope_sql}{area_filter_sql}
              AND crime_type IS NOT NULL
            GROUP BY crime_type
            """,
                        (*location_scope_params, *area_filter_params),
        )
        ov_sev_rows = cursor.fetchall()
        ov_weighted_sum = 0.0
        ov_weighted_cnt = 0
        for r in ov_sev_rows:
            ctype = r.get("crime_type")
            cnt = int(r.get("cnt") or 0)
            cat = _crime_user_category(ctype)
            wt = _CATEGORY_SEVERITY_WEIGHT.get(cat, 4)
            ov_weighted_sum += cnt * wt
            ov_weighted_cnt += cnt
        overall_volume_ratio = (overall_total_crimes / max(overall_city_avg, 1.0)) if overall_city_avg > 0 else 0.0

        overall_time_risk_score = 50.0
        if selected_hour is not None and overall_total_crimes > 0:
            cursor.execute(
                f"""
                SELECT HOUR(crime_time) AS hr, COUNT(*) AS cnt
                FROM crimes
                WHERE {location_scope_sql} AND crime_time IS NOT NULL{area_filter_sql}
                GROUP BY HOUR(crime_time)
                """,
                (*location_scope_params, *area_filter_params),
            )
            ov_hour_map = {int(r["hr"]): int(r["cnt"]) for r in cursor.fetchall()}
            ov_raw_hour_counts = [ov_hour_map.get(h, 0) for h in range(24)]
            ov_avg_hourly = (sum(ov_raw_hour_counts) / 24.0) if ov_raw_hour_counts else 0.0
            if ov_avg_hourly > 0:
                overall_time_risk_score = _clamp((ov_raw_hour_counts[selected_hour] / ov_avg_hourly) * 50.0)

        overall_recency_score = 50.0
        overall_trend_score = 50.0
        if overall_end_str:
            end_dt_obj = overall_end_dt if hasattr(overall_end_dt, 'strftime') else datetime.strptime(str(overall_end_dt), '%Y-%m-%d')
            cutoff_30 = (end_dt_obj - timedelta(days=30)).strftime('%Y-%m-%d')
            cutoff_90 = (end_dt_obj - timedelta(days=90)).strftime('%Y-%m-%d')
            cutoff_180 = (end_dt_obj - timedelta(days=180)).strftime('%Y-%m-%d')

            cursor.execute(
                f"""
                SELECT
                  SUM(CASE WHEN crime_date >= %s AND crime_date <= %s THEN 1 ELSE 0 END) AS r30,
                  SUM(CASE WHEN crime_date >= %s AND crime_date <= %s THEN 1 ELSE 0 END) AS r90,
                  SUM(CASE WHEN crime_date >= %s AND crime_date < %s THEN 1 ELSE 0 END) AS p90
                FROM crimes
                                WHERE {location_scope_sql}{area_filter_sql}
                """,
                                (cutoff_30, overall_end_str, cutoff_90, overall_end_str, cutoff_180, cutoff_90, *location_scope_params, *area_filter_params),
            )
            ov_rt = cursor.fetchone() or {}
            ov_r30 = int(ov_rt.get("r30") or 0)
            ov_r90 = int(ov_rt.get("r90") or 0)
            ov_p90 = int(ov_rt.get("p90") or 0)

            if ov_r90 > 0:
                overall_recency_score = _clamp((ov_r30 / max(ov_r90 / 3.0, 1.0)) * 100.0)
            elif ov_r30 > 0:
                overall_recency_score = 100.0

            if ov_p90 > 0:
                ov_diff = (ov_r90 - ov_p90) / ov_p90 * 100.0
            elif ov_r90 > 0:
                ov_diff = 100.0
            else:
                ov_diff = 0.0
            overall_trend_score = _clamp(50.0 - (ov_diff * 0.5))

        if overall_start_dt and overall_end_dt:
            if hasattr(overall_start_dt, 'strftime') and hasattr(overall_end_dt, 'strftime'):
                overall_observation_days = max(30, (overall_end_dt - overall_start_dt).days + 1)
            else:
                overall_observation_days = max(30, months * 30)
        else:
            overall_observation_days = max(30, months * 30)

        overall_score_summary = calculate_unified_risk_summary(
            {
                "total_crimes": overall_total_crimes,
                "high_risk_count": int((ov_row or {}).get("high_risk_count") or 0),
                "medium_risk_count": int((ov_row or {}).get("medium_risk_count") or 0),
                "recency_score": overall_recency_score,
                "trend_score": overall_trend_score,
                "time_risk_score": overall_time_risk_score,
            },
            observation_days=overall_observation_days,
        )

        overall_risk_score = overall_score_summary["risk_score"]
        if overall_risk_score >= 80:
            overall_crime_pressure = "High"
        elif overall_risk_score >= 60:
            overall_crime_pressure = "Elevated"
        elif overall_risk_score >= 40:
            overall_crime_pressure = "Moderate"
        else:
            overall_crime_pressure = "Low"

        overall_density_ratio = float(round(overall_volume_ratio, 1))
        overall_summary = {
            "label": "Overall (Complete History)",
            "scope": "all_time",
            "total_crimes": overall_total_crimes,
            "observation_days": overall_observation_days,
            "date_range": {
                "start": overall_start_str,
                "end": overall_end_str,
            },
            "risk_score": overall_score_summary["risk_score"],
            "safety_score": overall_score_summary["safety_score"],
            "risk_level": overall_score_summary["risk_level"],
            "safety_grade": overall_score_summary["safety_grade"],
            "data_confidence": overall_score_summary["data_confidence"],
            "crime_pressure": overall_crime_pressure,
            "city_avg_crimes": round(overall_city_avg, 1),
            "crime_density": {
                "ratio": overall_density_ratio,
                "label": f"{overall_density_ratio}x city average",
            },
            "score_components": {
                "volume": round(overall_score_summary["score_components"]["volume"], 1),
                "severity": round(overall_score_summary["score_components"]["severity"], 1),
                "recency": round(overall_score_summary["score_components"]["recency"], 1),
                "trend": round(overall_score_summary["score_components"]["trend"], 1),
                "time": round(overall_score_summary["score_components"]["time"], 1),
            },
        }

        if risk_score >= 80:
            crime_pressure = "High"
        elif risk_score >= 60:
            crime_pressure = "Elevated"
        elif risk_score >= 40:
            crime_pressure = "Moderate"
        else:
            crime_pressure = "Low"

        # 10) Trend aggregation (Daily if period is short, else Monthly)
        if lookback_days <= 31:
            cursor.execute(
                f"""
                SELECT DATE_FORMAT(crime_date, '%Y-%m-%d') AS period_key, COUNT(*) AS cnt
                FROM crimes
                WHERE {location_scope_sql} AND crime_date >= %s{area_filter_sql}
                GROUP BY period_key
                ORDER BY period_key
                """,
                (*location_scope_params, cutoff_main, *area_filter_params),
            )
            aggregation_mode = "daily"
        else:
            cursor.execute(
                f"""
                SELECT DATE_FORMAT(crime_date, '%Y-%m') AS period_key, COUNT(*) AS cnt
                FROM crimes
                WHERE {location_scope_sql} AND crime_date >= %s{area_filter_sql}
                GROUP BY period_key
                ORDER BY period_key
                """,
                (*location_scope_params, cutoff_main, *area_filter_params),
            )
            aggregation_mode = "monthly"

        period_rows = cursor.fetchall()
        month_abbr = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
        
        # Build dictionary of existing data
        raw_counts = {r['period_key']: int(r['cnt']) for r in period_rows}
        trend_profile_counts = []
        
        # Back-fill with zeros for the whole window to ensure at least N points exist for the graph
        if aggregation_mode == "daily":
            for i in range(lookback_days + 1):
                d = (analysis_anchor_dt - timedelta(days=lookback_days - i)).strftime('%Y-%m-%d')
                cnt = raw_counts.get(d, 0)
                trend_profile_counts.append({
                    'period': d,
                    'label': d,
                    'count': cnt,
                    'aggregation': aggregation_mode
                })
        else:
            # Monthly back-fill (approximate)
            for i in range(months + 1):
                # Calculate approx month back
                d = (analysis_anchor_dt - timedelta(days=(months - i) * 30)).strftime('%Y-%m')
                cnt = raw_counts.get(d, 0)
                try:
                    m_idx = int(d.split('-')[1]) - 1
                    label = month_abbr[m_idx]
                except (IndexError, ValueError):
                    label = d
                
                trend_profile_counts.append({
                    'period': d,
                    'label': label,
                    'count': cnt,
                    'aggregation': aggregation_mode
                })

        # 11) Sub-area breakdown
        cursor.execute(
            f"""
            SELECT area_translit, COUNT(*) AS cnt
            FROM crimes
                        WHERE {location_scope_sql} AND crime_date >= %s{area_filter_sql}
              AND area_translit IS NOT NULL AND area_translit != ''
            GROUP BY area_translit
            ORDER BY cnt DESC
            LIMIT 20
            """,
                        (*location_scope_params, cutoff_main, *area_filter_params),
        )
        sa_rows = cursor.fetchall()
        sa_total = sum(int(r['cnt']) for r in sa_rows)
        sub_area_breakdown = []
        for r in sa_rows:
            pct = round(int(r['cnt']) / max(sa_total, 1) * 100, 1)
            sub_area_breakdown.append(
                {
                    'name': r['area_translit'],
                    'count': int(r['cnt']),
                    'pct': pct,
                    'risk_level': 'High' if pct >= 10.0 else 'Medium' if pct >= 5.0 else 'Low',
                }
            )

        nearby_areas: list = []
        try:
            cursor.execute(
                f"""
                SELECT area_translit, COUNT(*) AS incident_count
                FROM crimes
                                WHERE {location_scope_sql}{area_filter_sql}
                  AND area_translit IS NOT NULL
                  AND area_translit != ''
                GROUP BY area_translit
                ORDER BY incident_count DESC
                LIMIT 8
                """,
                                (*location_scope_params, *area_filter_params),
            )
            near_rows = cursor.fetchall()
            near_total = sum(int(r['incident_count'] or 0) for r in near_rows)
            for sa in near_rows:
                sa_cnt = int(sa['incident_count'] or 0)
                sa_pct = round(sa_cnt / max(near_total, 1) * 100, 1)
                nearby_areas.append(
                    {
                        'area': sa['area_translit'],
                        'incident_count': sa_cnt,
                        'distance_km': None,
                        'pct_diff': sa_pct,
                        'direction': 'higher' if sa_pct >= 20 else 'lower',
                    }
                )
        except Exception as nb_exc:
            logger.warning("sub_areas query failed: %s", nb_exc)

        patrol_strategy: dict = {}
        try:
            if riskiest_hours:
                def _fmt_h_ps(h: int) -> str:
                    ampm = 'AM' if h < 12 else 'PM'
                    return f"{h % 12 or 12} {ampm}"

                hi_h = sorted(riskiest_hours)
                lo_h = sorted(safest_hours) if safest_hours else []
                mod_h: set = set()
                for h_ps in hi_h:
                    mod_h.add((h_ps - 1) % 24)
                    mod_h.add((h_ps + 1) % 24)
                mod_h -= set(hi_h)
                patrol_strategy = {
                    'high_patrol': f"{_fmt_h_ps(hi_h[0])} - {_fmt_h_ps(hi_h[-1])}" if len(hi_h) > 1 else _fmt_h_ps(hi_h[0]),
                    'moderate_patrol': ", ".join(_fmt_h_ps(h) for h in sorted(mod_h)[:4]) if mod_h else "N/A",
                    'low_patrol': f"{_fmt_h_ps(lo_h[0])} - {_fmt_h_ps(lo_h[-1])}" if len(lo_h) > 1 else (_fmt_h_ps(lo_h[0]) if lo_h else "N/A"),
                    'highest_risk_day': riskiest_day or 'N/A',
                    'safest_day': safest_day or 'N/A',
                }
        except Exception as ps_exc:
            logger.warning("patrol_strategy computation failed: %s", ps_exc)

        low_data_warning = None
        anchor_note = f" (reference date {analysis_anchor_date})" if analysis_anchor_date else ""
        if total_crimes < 15:
            low_data_warning = (
                f"Only {total_crimes} incident{'s' if total_crimes != 1 else ''} recorded "
                f"in the {months}-month window{anchor_note} - "
                "patterns shown may be unreliable due to limited historical data."
            )
        elif safest_day == riskiest_day:
            low_data_warning = (
                "Safest and riskiest days are identical - insufficient data to distinguish "
                "day-of-week patterns reliably."
            )

        return {
            "engine": "unified_risk_aggregation",
            "engine_label": "Unified Risk Aggregation (statistical, no ML)",
            "engine_inputs": {
                "total_crimes": total_crimes,
                "high_risk_count": high_risk_count,
                "medium_risk_count": medium_risk_count,
                "recency_score": recency_score,
                "trend_score": trend_score,
                "time_risk_score": time_risk_score,
                "observation_days": lookback_days,
            },
            "area": area,
            "period_months": months,
            "lookback_days": lookback_days,
            "crime_type_filter": crime_type_filter,
            "selected_date": date,
            "selected_hour": selected_hour,
            "analysis_anchor_date": analysis_anchor_date,
            "reference_date": analysis_anchor_date,
            "time_reference_mode": "selected_date" if date else "now",
            "is_time_aligned": True,
            "scope_mode": scope_mode,
            "scope": {
                "mode": scope_mode,
                "area": area,
                "lat": lat,
                "lng": lng,
                "radius_km": radius_km if scope_mode == "radius" else None,
            },
            "total_crimes": total_crimes,
            "city_avg_crimes": round(city_avg, 1),
            "risk_score": risk_score,
            "safety_score": safety_score,
            "safety_grade": safety_grade,
            "risk_level": risk_level,
            "data_confidence": data_confidence,
            "safer_than_pct": safer_than_pct,
            "area_ranking": {"rank": rank_num, "total_areas": total_areas},
            "last_24_h": last_24_h,
            "last_7_days": last_7_days,
            "last_30_days": last_30_days,
            "high_risk_count": high_risk_count,
            "medium_risk_count": medium_risk_count,
            "last_30_days_ref_date": last_30_days_ref_date,
            "crime_pressure": crime_pressure,
            "crime_density": {"ratio": density_ratio, "label": crime_density_label},
            "hourly_distribution": hourly,
            "safest_hours": safest_hours,
            "riskiest_hours": riskiest_hours,
            "safest_hour_range": safest_hour_range,
            "riskiest_hour_range": riskiest_hour_range,
            "recommended_visit_window": recommended_visit_window,
            "best_visit_window": safest_hour_range,
            "top_crime_types": top_crimes,
            "day_of_week": dow_data,
            "safest_day": safest_day,
            "safest_day_vs_avg": safest_day_vs_avg,
            "riskiest_day": riskiest_day,
            "riskiest_day_vs_avg": riskiest_day_vs_avg,
            "trend": {
                "direction": trend_dir,
                "change_pct": change_pct,
                "recent_count": recent,
                "older_count": older,
                "recent_monthly_avg": round(recent_monthly_avg, 1),
                "older_monthly_avg": round(older_monthly_avg, 1),
            },
            "momentum": {
                "direction": momentum_dir,
                "pct_change": momentum_pct,
                "recent_90d": r90,
                "prior_90d": p90,
            },
            "score_components": {
                "volume": round(score_summary["score_components"]["volume"], 1),
                "severity": round(score_summary["score_components"]["severity"], 1),
                "recency": round(score_summary["score_components"]["recency"], 1),
                "trend": round(score_summary["score_components"]["trend"], 1),
                "time": round(score_summary["score_components"]["time"], 1),
            },
            "overall_summary": overall_summary,
            "monthly_crime_counts": trend_profile_counts,
            "sub_area_breakdown": sub_area_breakdown,
            "low_data_warning": low_data_warning,
            "nearby_areas": nearby_areas,
            "patrol_strategy": patrol_strategy,
        }

    except HTTPException:
        raise
    except MySQLError as e:
        logger.error("MySQL error in get_area_safety_profile for '%s': %s", area, e)
        raise HTTPException(status_code=500, detail="Failed to retrieve area safety profile")
    finally:
        if cursor: cursor.close()
        if conn and conn.is_connected(): conn.close()


@router.get("/areas")
def get_areas():
    """Get all unique areas with their coordinates from the crimes table.
    Returns areas sorted by record count (most data-rich areas first).
    """
    conn, cursor = None, None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        query = """
            SELECT area,
                   AVG(latitude)  AS latitude,
                   AVG(longitude) AS longitude,
                   COUNT(*)       AS record_count
            FROM crimes
            WHERE area IS NOT NULL AND area != ''
              AND latitude  IS NOT NULL
              AND longitude IS NOT NULL
            GROUP BY area
            ORDER BY record_count DESC
        """

        cursor.execute(query)
        rows = cursor.fetchall()

        areas_list = []
        for row in rows:
            try:
                if row['latitude'] and row['longitude']:
                    areas_list.append({
                        "name": row['area'],
                        "coordinates": {
                            "lat": float(row['latitude']),
                            "lng": float(row['longitude'])
                        },
                        "record_count": int(row['record_count']),
                    })
            except (ValueError, TypeError):
                continue

        logger.info(f"Retrieved {len(areas_list)} unique areas")
        return {"areas": areas_list}

    except MySQLError as e:
        logger.error(f"MySQL error: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve areas")
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()


@router.get("/areas/{area}/details")
def get_area_details(area: str):
    """
    Return aggregated crime statistics for a single area.
    Used by PredictionMapView to populate the area detail panel.
    """
    conn, cursor = None, None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Total crime count
        cursor.execute(
            "SELECT COUNT(*) AS total FROM crimes WHERE area = %s",
            (area,)
        )
        total_row = cursor.fetchone()
        total_crimes = int(total_row["total"]) if total_row else 0

        if total_crimes == 0:
            raise HTTPException(status_code=404, detail=f"No crimes found for area '{area}'")

        # Representative coordinates
        cursor.execute(
            """
            SELECT AVG(latitude) AS lat, AVG(longitude) AS lng
            FROM crimes
            WHERE area = %s AND latitude IS NOT NULL AND longitude IS NOT NULL
            """,
            (area,)
        )
        coord_row = cursor.fetchone()
        lat = float(coord_row["lat"]) if coord_row and coord_row["lat"] else None
        lng = float(coord_row["lng"]) if coord_row and coord_row["lng"] else None

        # Risk breakdown  (High / Medium / Low)
        cursor.execute(
            """
            SELECT risk_level, COUNT(*) AS cnt
            FROM crimes
            WHERE area = %s AND risk_level IS NOT NULL
            GROUP BY risk_level
            """,
            (area,)
        )
        risk_rows = cursor.fetchall()
        risk_breakdown = {"High": 0, "Medium": 0, "Low": 0}
        for r in risk_rows:
            lvl = (r["risk_level"] or "").capitalize()
            if lvl in risk_breakdown:
                risk_breakdown[lvl] = int(r["cnt"])
        most_common_risk = max(risk_breakdown, key=risk_breakdown.get)

        # Top 5 crime types
        cursor.execute(
            """
            SELECT crime_type, COUNT(*) AS cnt
            FROM crimes
            WHERE area = %s AND crime_type IS NOT NULL
            GROUP BY crime_type
            ORDER BY cnt DESC
            LIMIT 5
            """,
            (area,)
        )
        top_types = [
            {"type": r["crime_type"], "count": int(r["cnt"])}
            for r in cursor.fetchall()
        ]

        # Peak hour
        cursor.execute(
            """
            SELECT HOUR(crime_date) AS hr, COUNT(*) AS cnt
            FROM crimes
            WHERE area = %s AND crime_date IS NOT NULL
            GROUP BY hr
            ORDER BY cnt DESC
            LIMIT 1
            """,
            (area,)
        )
        peak_row = cursor.fetchone()
        peak_hour = int(peak_row["hr"]) if peak_row else None

        # 10 most recent crimes
        cursor.execute(
            """
            SELECT crime_type, crime_date, risk_level,
                   latitude, longitude
            FROM crimes
            WHERE area = %s
            ORDER BY crime_date DESC
            LIMIT 10
            """,
            (area,)
        )
        recent = []
        for r in cursor.fetchall():
            recent.append({
                "crime_type": r["crime_type"],
                "crime_date": r["crime_date"].isoformat() if r["crime_date"] else None,
                "risk_level":  r["risk_level"],
                "latitude":    float(r["latitude"])  if r["latitude"]  else None,
                "longitude":   float(r["longitude"]) if r["longitude"] else None,
            })

        return {
            "area":             area,
            "total_crimes":     total_crimes,
            "coordinates":      {"lat": lat, "lng": lng},
            "risk_breakdown":   risk_breakdown,
            "most_common_risk": most_common_risk,
            "top_crime_types":  top_types,
            "peak_hour":        peak_hour,
            "recent_crimes":    recent,
        }

    except HTTPException:
        raise
    except MySQLError as e:
        logger.error("MySQL error in get_area_details for '%s': %s", area, e)
        raise HTTPException(status_code=500, detail="Failed to retrieve area details")
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()


@router.get("/crime-types")
def get_crime_types():
    """Get all unique crime types from the database"""
    conn, cursor = None, None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT DISTINCT crime_type FROM crimes ORDER BY crime_type")
        rows = cursor.fetchall()

        crime_types = [cast(Dict[str, Any], row)['crime_type'] for row in rows if cast(Dict[str, Any], row)['crime_type']]
        logger.info(f"Retrieved {len(crime_types)} unique crime types")
        return {"crime_types": crime_types}

    except Exception as e:
        logger.error(f"MySQL error: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve crime types")
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()

@router.get("/areas/{area}/safety-advice")
def get_area_safety_advice(
    area:        str,
    date:        Optional[str] = Query(None,  description="Target date YYYY-MM-DD (defaults to today)"),
    crime_type:  Optional[str] = Query(None,  description="Specific crime type, or omit for overall area risk"),
):
    """
    Answer 'Is it safe to visit this area?' and 'When is the safest time?'

    Returns:
      - risk for the requested date / crime type
      - 3 safest days of the week (from historical data)
      - 3 safest months of the year
      - 3 lowest-risk upcoming dates in the next 30 days
      - if crime_type is omitted: overall area breakdown for all crime types
    """
    if not _poisson_artifacts:
        raise HTTPException(
            status_code=503,
            detail="Safety advice model not ready — run training first"
        )

    target_date = (date or datetime.now().strftime('%Y-%m-%d')).split(' ')[0]

    try:
        if crime_type:
            kw_sev = _infer_sev(crime_type) if _infer_sev else None
            result = _poisson_predict(
                _poisson_artifacts,
                area=area, crime_type=crime_type,
                date_str=target_date, keyword_severity=kw_sev,
            )
            return {
                "area":                  area,
                "date":                  target_date,
                "crime_type":            crime_type,
                "risk_level":            result['risk_level'],
                "risk_percentage":       result['risk_percentage'],
                "probability":           result['probability'],
                "confidence":            result['confidence'],
                "safest_days_of_week":   result['safest_days_of_week'],
                "riskiest_day_of_week":  result['riskiest_day_of_week'],
                "safest_months":         result['safest_months'],
                "safest_upcoming_dates": result['safest_upcoming_dates'],
                "is_estimated":          result.get('is_estimated', False),
                "note":                  result.get('note'),
            }
        else:
            # Overall area safety across all crime types
            from utils.poisson_predictor import area_safety_profile as _area_profile
            profile = _area_profile(_poisson_artifacts, area, target_date)
            # Add upcoming dates for overall area
            profile['safest_upcoming_dates'] = _get_area_safest_upcoming(
                _poisson_artifacts, area, target_date
            )
            return profile

    except Exception as exc:
        logger.error("safety-advice error for area=%s: %s", area, exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Safety advice computation failed")


def _get_area_safest_upcoming(artifacts: dict, area: str, date_str: str) -> list:
    """Compute the 3 safest upcoming dates for an area (all crime types combined)."""
    from datetime import timedelta
    import math as _math
    try:
        dt = datetime.strptime(date_str, '%Y-%m-%d')
    except ValueError:
        dt = datetime.now()

    pair_lambdas = artifacts.get('pair_lambdas', {})
    area_dow     = artifacts.get('area_dow_multipliers', {})
    area_month   = artifacts.get('area_month_multipliers', {})

    # Collect all base lambdas for this area
    area_keys = [k for k in pair_lambdas if k.startswith(f"{area}|||")]
    if not area_keys:
        return []

    upcoming = []
    for delta in range(1, 31):
        fd       = dt + timedelta(days=delta)
        fd_dow   = str(fd.weekday())
        fd_month = str(fd.month)
        total_lam = sum(
            float(pair_lambdas[k])
            * float(area_dow.get(area, {}).get(fd_dow, 1.0))
            * float(area_month.get(area, {}).get(fd_month, 1.0))
            for k in area_keys
        )
        prob = 1.0 - _math.exp(-max(total_lam, 1e-9))
        upcoming.append({
            "date":           fd.strftime('%Y-%m-%d'),
            "day":            ['Monday','Tuesday','Wednesday','Thursday',
                               'Friday','Saturday','Sunday'][fd.weekday()],
            "risk_percentage": round(prob * 100, 1),
        })
    return sorted(upcoming, key=lambda x: x['risk_percentage'])[:3]


@router.post("/predict-risk")
def predict_risk(request: PredictRiskRequest):
    """
    Predict crime risk for a given area, crime type, date, and optional time.

    Primary model: Poisson probability estimator
      P(≥1 crime of this type in this area on this day/hour) = 1 - e^(-λ)
      λ is adjusted by historical day-of-week, seasonal, and hour-of-day
      multipliers.  When a time is supplied the prediction reflects that
      specific hour rather than the whole day, so results change meaningfully
      when the user adjusts the time field.

    Secondary model: RF + composite risk score (fallback if Poisson artifacts
      are not yet built).
    """
    area       = request.area.strip() if request.area else ""
    crime_type = request.crime_type
    date       = request.date or datetime.now().strftime('%Y-%m-%d')

    # ── Parse hour (0-23) from the optional time field ───────────────────────
    req_hour: int | None = None
    raw_time = (request.time or "").strip()
    if raw_time:
        from app.crime_risk_model.utils.helpers import _parse_hour as _ph
        parsed = _ph(raw_time)
        req_hour = parsed if parsed >= 0 else None

    # Normalise to date-only — Poisson model uses date for DOW/month
    date_part = date.split(' ')[0].strip()
    if not validate_date_format(date_part):
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")

    logger.info(
        "🎯 /predict-risk called — area=%r crime=%r date=%s hour=%s | "
        "available models: poisson=%s rf_composite=%s legacy_rf=%s",
        area, crime_type, date_part, req_hour,
        bool(_poisson_artifacts),
        bool(_crm_model and _crm_scaler and _crm_artifacts),
        bool(model and le_area and le_crime and le_risk),
    )

    # ── Primary path: Poisson probability model ───────────────────────────────
    if _poisson_artifacts:
        logger.info("🟢 Trying PRIMARY model: Poisson probability estimator")
        try:
            kw_sev = _infer_sev(crime_type)
            result = _poisson_predict(
                _poisson_artifacts,
                area             = area,
                crime_type       = crime_type,
                date_str         = date_part,
                keyword_severity = kw_sev,
                hour             = req_hour,
            )
            logger.info(
                "✅ POISSON prediction served: area=%s crime=%s date=%s hour=%s → %s %d%% (λ=%.4f, conf=%.2f)",
                area, crime_type, date_part, req_hour,
                result['risk_level'], result['risk_percentage'], result['lambda'],
                result.get('confidence', 0.0),
            )
            resp = {
                "model":                "poisson",
                "model_label":          "Poisson Probability Estimator",
                "risk_level":           result['risk_level'],
                "risk_percentage":      result['risk_percentage'],
                "confidence":           result['confidence'],
                "probability":          result['probability'],
                "safest_days_of_week":  result['safest_days_of_week'],
                "riskiest_day_of_week": result['riskiest_day_of_week'],
                "safest_months":        result['safest_months'],
                "safest_upcoming_dates": result['safest_upcoming_dates'],
                "is_estimated":         result.get('is_estimated', False),
            }
            if result.get('time_period'):
                resp["time_period"] = result['time_period']
            if result.get('safest_hours'):
                resp["safest_hours"] = result['safest_hours']
            if result.get('riskiest_hours'):
                resp["riskiest_hours"] = result['riskiest_hours']
            if result.get('hourly_risk_profile'):
                resp["hourly_risk_profile"] = result['hourly_risk_profile']
            if result.get('visit_time_comparison'):
                resp["visit_time_comparison"] = result['visit_time_comparison']
            if result.get('note'):
                resp["message"] = result['note']

            # ── Dataset context ───────────────────────────────────────────────
            obs_days = _poisson_artifacts.get('total_observation_days', 366)
            resp["dataset_stats"] = {
                "total_records":      25380,
                "observation_days":   obs_days,
                "date_range":         "2018–2025",
            }

            # ── Area crime trend (last 6 months vs prior 6 months) ────────────
            try:
                conn = get_db_connection()
                if conn:
                    cursor = conn.cursor(dictionary=True)
                    cursor.execute(
                        """
                        SELECT
                            SUM(CASE WHEN crime_date >= DATE_SUB(CURDATE(), INTERVAL 6 MONTH)
                                     THEN 1 ELSE 0 END)  AS recent_count,
                            SUM(CASE WHEN crime_date >= DATE_SUB(CURDATE(), INTERVAL 12 MONTH)
                                      AND crime_date <  DATE_SUB(CURDATE(), INTERVAL 6 MONTH)
                                     THEN 1 ELSE 0 END)  AS prior_count
                        FROM crimes
                        WHERE area = %s
                        """,
                        (area,),
                    )
                    row = cursor.fetchone()
                    cursor.close()
                    conn.close()
                    if row:
                        recent = int(row.get('recent_count') or 0)
                        prior  = int(row.get('prior_count') or 0)
                        if prior > 0:
                            change_pct = round((recent - prior) / prior * 100, 1)
                            if change_pct <= -10:
                                direction = "decreasing"
                            elif change_pct >= 10:
                                direction = "increasing"
                            else:
                                direction = "stable"
                            resp["area_trend"] = {
                                "direction":   direction,
                                "change_pct":  change_pct,
                                "recent_count": recent,
                                "prior_count":  prior,
                            }
                        elif recent > 0:
                            resp["area_trend"] = {
                                "direction":   "increasing",
                                "change_pct":  100.0,
                                "recent_count": recent,
                                "prior_count":  0,
                            }
            except Exception as trend_exc:
                logger.warning("area_trend query failed: %s", trend_exc)

            # ── Monthly crime counts (last 12 months) ─────────────────────────
            try:
                conn3 = get_db_connection()
                if conn3:
                    cursor3 = conn3.cursor(dictionary=True)
                    cursor3.execute(
                        """
                        SELECT
                            DATE_FORMAT(crime_date, '%Y-%m') AS month,
                            COUNT(*) AS count
                        FROM crimes
                        WHERE area = %s
                          AND crime_date >= DATE_SUB(CURDATE(), INTERVAL 12 MONTH)
                        GROUP BY DATE_FORMAT(crime_date, '%Y-%m')
                        ORDER BY month
                        """,
                        (area,),
                    )
                    monthly_rows = cursor3.fetchall()
                    cursor3.close()
                    conn3.close()
                    if monthly_rows:
                        _month_abbr = ['Jan','Feb','Mar','Apr','May','Jun',
                                       'Jul','Aug','Sep','Oct','Nov','Dec']
                        resp["monthly_crime_counts"] = [
                            {
                                "month": r["month"],
                                "label": _month_abbr[int(r["month"].split("-")[1]) - 1],
                                "count": int(r["count"]),
                            }
                            for r in monthly_rows
                        ]
            except Exception as monthly_exc:
                logger.warning("monthly_crime_counts query failed: %s", monthly_exc)

            # ── Seven-day forecast ─────────────────────────────────────────────
            try:
                _fc_base = datetime.strptime(date_part, '%Y-%m-%d')
                _forecast: list = []
                for _delta in range(1, 8):
                    _fd     = _fc_base + timedelta(days=_delta)
                    _fd_str = _fd.strftime('%Y-%m-%d')
                    _fr = _poisson_predict(
                        _poisson_artifacts,
                        area=area, crime_type=crime_type,
                        date_str=_fd_str, keyword_severity=kw_sev, hour=req_hour,
                    )
                    _forecast.append({
                        'date':            _fd_str,
                        'day':             _fd.strftime('%a'),
                        'risk_level':      _fr['risk_level'],
                        'risk_percentage': _fr['risk_percentage'],
                    })
                resp['seven_day_forecast'] = _forecast
            except Exception as _fc_exc:
                logger.warning("seven_day_forecast failed: %s", _fc_exc)

            # ── Historical average risk (empirical P(>=1) over past 12 months) ──
            try:
                _conn_h = get_db_connection()
                if _conn_h:
                    _cur_h = _conn_h.cursor(dictionary=True)
                    _cur_h.execute(
                        """
                        SELECT COUNT(DISTINCT DATE(crime_date)) AS days_with_crime
                        FROM crimes
                        WHERE area = %s AND crime_type = %s
                          AND crime_date >= DATE_SUB(CURDATE(), INTERVAL 12 MONTH)
                        """,
                        (area, crime_type),
                    )
                    _hr = _cur_h.fetchone()
                    _cur_h.close(); _conn_h.close()
                    if _hr:
                        _dw        = int(_hr['days_with_crime'] or 0)
                        _hist_avg  = round(_dw / 365.0 * 100, 2)
                        _diff      = round(result['risk_percentage'] - _hist_avg, 2)
                        _diff_pct  = round(_diff / max(_hist_avg, 0.01) * 100, 1)
                        resp['historical_comparison'] = {
                            'historical_avg':      _hist_avg,
                            'current_predicted':   result['risk_percentage'],
                            'diff':                _diff,
                            'diff_pct':            _diff_pct,
                            'direction':           'higher' if _diff_pct > 5 else 'lower' if _diff_pct < -5 else 'normal',
                            'days_with_crime_12m': _dw,
                        }
            except Exception as _hist_exc:
                logger.warning("historical_avg_risk query failed: %s", _hist_exc)

            # ── Risk drivers ───────────────────────────────────────────────────
            try:
                _drivers: list = []
                _lam    = float(result.get('lambda', 0))
                _at     = resp.get('area_trend', {})
                _at_dir = _at.get('direction', 'stable')
                _at_chg = _at.get('change_pct', 0)
                if _at_dir == 'decreasing':
                    _drivers.append(f"Area crime trend declining — {abs(_at_chg)}% fewer incidents over the past 6 months")
                elif _at_dir == 'increasing':
                    _drivers.append(f"Area crime trend rising — +{_at_chg}% more incidents over the past 6 months")
                else:
                    _drivers.append("Area crime trend stable — no significant change in the past 6 months")
                if _lam < 0.03:
                    _drivers.append("Very low historical frequency for this crime type in this area")
                elif _lam < 0.10:
                    _drivers.append("Low historical incident rate for this area \u00d7 crime combination")
                elif _lam > 0.50:
                    _drivers.append("High historical frequency — this crime type occurs regularly in this area")
                elif _lam > 0.25:
                    _drivers.append("Moderate historical incident rate for this crime type and area")
                _period_ctx = {
                    'Morning':   'Morning period (5\u201311 AM) historically shows lower criminal activity',
                    'Afternoon': 'Afternoon period (12\u20134 PM) shows moderate criminal activity',
                    'Evening':   'Evening period (5\u20138 PM) shows elevated criminal activity',
                    'Night':     'Nighttime (9 PM\u20134 AM) has historically higher incident rates',
                }
                _tp = result.get('time_period')
                if _tp and _tp in _period_ctx:
                    _drivers.append(_period_ctx[_tp])
                _day_names = ['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday']
                _query_day = _day_names[datetime.strptime(date_part, '%Y-%m-%d').weekday()]
                _riskiest  = result.get('riskiest_day_of_week')
                _safest_dw = result.get('safest_days_of_week') or []
                if _query_day == _riskiest:
                    _drivers.append(f"{_query_day} is historically the highest-risk day of week for this crime type")
                elif _query_day in _safest_dw:
                    _drivers.append(f"{_query_day} is among the historically safest days for this crime type")
                if result.get('is_estimated'):
                    _drivers.append("Prediction uses regional patterns \u2014 this area \u00d7 crime combination has limited direct observations")
                resp['risk_drivers'] = _drivers
            except Exception as _drv_exc:
                logger.warning("risk_drivers computation failed: %s", _drv_exc)

            # ── Expected incidents (Poisson 95th-percentile range) ──────────────
            try:
                import math as _math
                _lam2 = float(result.get('lambda', 0))
                _p95, _cumul2 = 0, 0.0
                for _k in range(20):
                    _pk = (_math.exp(-_lam2) * (_lam2 ** _k) / _math.factorial(_k)
                           if _lam2 > 0 else (1.0 if _k == 0 else 0.0))
                    _cumul2 += _pk
                    if _cumul2 >= 0.95:
                        _p95 = _k
                        break
                resp['expected_incidents'] = {
                    'range_low':         0,
                    'range_high':        _p95,
                    'lambda':            round(_lam2, 4),
                    'prob_at_least_one': round(result['probability'] * 100, 2),
                }
            except Exception as _ei_exc:
                logger.warning("expected_incidents computation failed: %s", _ei_exc)

            # ── Historical Frequency (raw incident counts) ─────────────────────
            try:
                _conn_hf = get_db_connection()
                if _conn_hf:
                    _cur_hf = _conn_hf.cursor(dictionary=True)
                    _cur_hf.execute(
                        """
                        SELECT
                            SUM(CASE WHEN crime_date >= DATE_SUB(CURDATE(), INTERVAL 12 MONTH) THEN 1 ELSE 0 END) AS last_12m,
                            SUM(CASE WHEN crime_date >= DATE_SUB(CURDATE(), INTERVAL 3 MONTH)  THEN 1 ELSE 0 END) AS last_3m
                        FROM crimes WHERE area = %s AND crime_type = %s
                        """,
                        (area, crime_type),
                    )
                    _hf_row = _cur_hf.fetchone()
                    _cur_hf.execute(
                        """
                        SELECT ROUND(COUNT(*) / NULLIF(COUNT(DISTINCT area), 0), 1) AS city_avg
                        FROM crimes
                        WHERE crime_type = %s AND crime_date >= DATE_SUB(CURDATE(), INTERVAL 12 MONTH)
                        """,
                        (crime_type,),
                    )
                    _hf_city = _cur_hf.fetchone()
                    _cur_hf.close(); _conn_hf.close()
                    resp['historical_frequency'] = {
                        'last_12m': int(_hf_row['last_12m'] or 0) if _hf_row else 0,
                        'last_3m':  int(_hf_row['last_3m']  or 0) if _hf_row else 0,
                        'city_avg': float(_hf_city['city_avg'] or 0) if _hf_city else 0,
                    }
            except Exception as _hf_exc:
                logger.warning("historical_frequency query failed: %s", _hf_exc)

            # ── Suggested Response ─────────────────────────────────────────────
            try:
                _sr: list = []
                def _fmt_h_sr(h: int) -> str:
                    ampm = 'AM' if h < 12 else 'PM'
                    return f"{h % 12 or 12} {ampm}"
                _rh_sr = result.get('riskiest_hours', [])
                # `riskiest_hours` may be a list of int hours (RF path) or a
                # list of {"hour": int, "label": ..., "relative_risk": ...}
                # dicts (Poisson path). Normalize to ints before sorting,
                # otherwise sorted() raises "'<' not supported between dicts".
                _rh_hours = []
                for _item in _rh_sr:
                    if isinstance(_item, dict):
                        _h = _item.get('hour')
                        if _h is not None:
                            _rh_hours.append(int(_h))
                    else:
                        try:
                            _rh_hours.append(int(_item))
                        except (TypeError, ValueError):
                            continue
                if _rh_hours:
                    _rh_s = sorted(_rh_hours)
                    _sr.append(
                        f"Increase patrol coverage between {_fmt_h_sr(_rh_s[0])} \u2013 {_fmt_h_sr(_rh_s[-1])}"
                        f" \u2014 peak risk window for {crime_type} in {area}"
                    )
                _rk_dw_sr = result.get('riskiest_day_of_week')
                if _rk_dw_sr:
                    _sr.append(
                        f"Schedule additional resources on {_rk_dw_sr}"
                        f" \u2014 historically highest-incident day for {crime_type} in {area}"
                    )
                _at_sr = resp.get('area_trend', {})
                if _at_sr.get('direction') == 'increasing':
                    _sr.append(
                        f"Crime trend rising +{_at_sr['change_pct']}%"
                        f" \u2014 initiate community engagement and preventive deployment in {area}"
                    )
                if result.get('risk_level') in ('High', 'Critical'):
                    _sr.append(
                        f"Coordinate with local unit commanders \u2014 {area} is at"
                        f" {result.get('risk_level', '')} risk for {crime_type}"
                    )
                if result.get('is_estimated'):
                    _sr.append(
                        "Expand data collection for this area \u00d7 crime combination"
                        " to improve future prediction accuracy"
                    )
                _sr.append(
                    f"Cross-reference with Community Watch reports for recent {crime_type.lower()} activity in {area}"
                )
                resp['suggested_response'] = _sr[:5]
            except Exception as _sr_exc:
                logger.warning("suggested_response computation failed: %s", _sr_exc)

            return resp

        except Exception as exc:
            logger.warning("⚠️  POISSON prediction failed — %s: %s — falling back to RF + composite",
                           type(exc).__name__, exc, exc_info=True)
    else:
        logger.info("⏭️  Poisson artifacts not loaded — skipping primary model")

    # ── Secondary path: RF + composite score ─────────────────────────────────
    if _crm_model and _crm_scaler and _crm_artifacts:
        logger.info("🟡 Trying SECONDARY model: Random Forest + composite risk score")
        try:
            date_with_time = date_part + ' ' + datetime.now().strftime('%H:%M:%S')
            row = {
                'crime_date': date_with_time,
                'area':       area,
                'crime_type': crime_type,
                'latitude':   float(getattr(request, 'latitude',  31.5)),
                'longitude':  float(getattr(request, 'longitude', 74.3)),
            }
            X_new, _df = engineer_features(
                pd.DataFrame([row]),
                combined_severity_map = _crm_artifacts['combined_severity_map'],
                area_freq_map         = _crm_artifacts['area_freq_map'],
                area_freq_median      = _crm_artifacts['area_freq_median'],
            )
            X_scaled   = _crm_scaler.transform(X_new)
            risk_label = str(_crm_model.predict(X_scaled)[0])
            confidence = float(max(_crm_model.predict_proba(X_scaled)[0]))
            raw_score  = _crm_raw_score(_df.iloc[0])
            risk_pct   = max(1, min(99, int(round(raw_score * 100))))

            logger.info(
                "✅ RF+COMPOSITE prediction served: area=%s crime=%s → %s %d%% (conf=%.2f)",
                area, crime_type, risk_label, risk_pct, confidence,
            )
            return {
                "model":           "rf_composite",
                "model_label":     "Random Forest + Composite Risk Score",
                "risk_level":      risk_label,
                "risk_percentage": risk_pct,
                "confidence":      confidence,
                "is_estimated":    area not in _crm_artifacts.get('area_freq_map', {}),
            }

        except Exception as exc:
            logger.warning("⚠️  RF+COMPOSITE failed — %s: %s — falling back to legacy label-encoder RF",
                           type(exc).__name__, exc, exc_info=True)
    else:
        logger.info("⏭️  RF+composite artifacts not loaded — skipping secondary model")

    # ── Fallback: legacy label-encoder RF ────────────────────────────────────
    if not model or not le_area or not le_crime or not le_risk:
        logger.error("❌ No prediction model available (Poisson, RF+composite, and legacy RF all unavailable)")
        raise HTTPException(status_code=500, detail="No prediction model available")
    logger.info("🔵 Trying FALLBACK model: Legacy label-encoder Random Forest")

    try:
        date_str     = date.split(' ')[0]
        parsed_date  = datetime.strptime(date_str, '%Y-%m-%d')
        year, month, day_n, weekday = (
            int(parsed_date.year), int(parsed_date.month),
            int(parsed_date.day),  int(parsed_date.weekday())
        )
        day_of_year  = int(parsed_date.timetuple().tm_yday)
        is_weekend   = 1 if weekday in [5, 6] else 0

        matched_area  = find_best_match(area, le_area)
        matched_crime = find_best_match(crime_type, le_crime)

        if not matched_area or not matched_crime:
            logger.warning(
                "🟠 LEGACY-RF: no training match for area=%r / crime=%r — returning DEFAULT (Medium, 50%%)",
                area, crime_type,
            )
            return {"model": "default_medium",
                    "model_label": "Default Fallback (Medium, no training match)",
                    "risk_level": "Medium", "risk_percentage": 50,
                    "confidence": 0.5, "is_estimated": True,
                    "message": "Could not match inputs to training data"}

        area_enc       = int(le_area.transform([matched_area])[0])
        crime_type_enc = int(le_crime.transform([matched_crime])[0])
        features_df    = pd.DataFrame(
            [[area_enc, crime_type_enc, year, month, day_n, weekday, day_of_year, is_weekend]],
            columns=['area_enc', 'crime_type_enc', 'year', 'month', 'day', 'weekday', 'day_of_year', 'is_weekend']
        ).astype(int)

        pred           = model.predict(features_df)[0]
        pred_proba     = model.predict_proba(features_df)[0]
        risk_level     = str(le_risk.inverse_transform([pred])[0]).capitalize()
        risk_percentage = calculate_risk_percentage(risk_level, pred_proba.tolist(), le_risk)
        confidence     = float(max(pred_proba))
        logger.info(
            "✅ LEGACY-RF prediction served: area=%s (matched=%s) crime=%s (matched=%s) → %s %d%% (conf=%.2f)",
            area, matched_area, crime_type, matched_crime, risk_level, risk_percentage, confidence,
        )
        return {"model": "legacy_rf",
                "model_label": "Legacy Random Forest (label-encoder)",
                "risk_level": risk_level, "risk_percentage": risk_percentage, "confidence": confidence}

    except HTTPException:
        raise
    except Exception as e:
        logger.error("❌ LEGACY-RF prediction crashed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Prediction failed")

@router.post("")
def create_crime(crime: CrimeCreate, background_tasks: BackgroundTasks):
    """Create a new crime record and predict risk level if model is loaded"""
    conn, cursor = None, None
    try:
        area = crime.area
        crime_type = crime.crime_type
        date = crime.date or datetime.now().strftime('%Y-%m-%d')

        # Validate date
        if not validate_date_format(date):
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")

        parsed_date = datetime.strptime(date, '%Y-%m-%d')
        year, month, day, weekday = (
            int(parsed_date.year),
            int(parsed_date.month),
            int(parsed_date.day),
            int(parsed_date.weekday())
        )

        logger.info(f"Creating crime: area='{area}', crime_type='{crime_type}', date={date}")

        # Default risk values
        risk_level = "Medium"
        risk_percentage = 50
        confidence = 0.5

        if model and le_area and le_crime and le_risk:
            # Try to map inputs to encoder classes
            matched_area = find_best_match(area, le_area)
            matched_crime = find_best_match(crime_type, le_crime)

            if matched_area is None or matched_crime is None:
                logger.warning(f"Unknown category while creating crime: area='{area}', crime_type='{crime_type}'")
            else:
                try:
                    area_enc = int(le_area.transform([matched_area])[0])
                    crime_type_enc = int(le_crime.transform([matched_crime])[0])

                    day_of_year = parsed_date.timetuple().tm_yday
                    is_weekend = 1 if weekday >= 5 else 0

                    features_df = pd.DataFrame(
                        [[area_enc, crime_type_enc, year, month, day, weekday, day_of_year, is_weekend]],
                        columns=['area_enc', 'crime_type_enc', 'year', 'month', 'day', 'weekday', 'day_of_year', 'is_weekend']
                    ).astype(int)

                    logger.info(f"Features to model (create_crime): {features_df.iloc[0].to_list()}")

                    pred = model.predict(features_df)[0]
                    pred_proba = model.predict_proba(features_df)[0]

                    risk_level = le_risk.inverse_transform([pred])[0]
                    confidence = float(max(pred_proba))
                    risk_percentage = int(round(confidence * 100))

                    logger.info(f"create_crime prediction: risk_level={risk_level}, probabilities={pred_proba.tolist()}, confidence={confidence}")

                except Exception as e:
                    logger.error(f"Encoding or prediction error in create_crime: {e}", exc_info=True)
        else:
            logger.warning("ML model not loaded - storing default Medium risk")

        # Save to database
        conn = get_db_connection()
        cursor = conn.cursor()

        # Extract optional bilingual / time fields
        crime_time_val  = (crime.crime_time or "").strip() or None
        area_urdu_val   = (crime.area_urdu or "").strip() or None
        area_translit_val = (crime.area_translit or "").strip() or None

        # Auto-transliterate Urdu area if provided but translit missing
        if area_urdu_val and not area_translit_val:
            try:
                from app.approval_workflow import _azure_transliterate_single
                area_translit_val = _azure_transliterate_single(area_urdu_val) or None
            except Exception:
                pass
        
        # Fallback to English area if translit is still missing (very important for alert matching)
        if not area_translit_val and area:
            area_translit_val = area

        insert_query = """
            INSERT INTO crimes
                (area, area_urdu, area_translit, crime_type,
                 crime_date, crime_time, latitude, longitude,
                 risk_level, source, status, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """

        # Use provided coordinates or default to None
        latitude = crime.latitude
        longitude = crime.longitude
        
        # If coordinates are missing, attempt to geocode based on area
        if (latitude is None or longitude is None or latitude == 0.0 or longitude == 0.0) and area:
            try:
                from app.utils.geo import get_coordinates
                logger.info(f"🔍 Auto-geocoding area '{area}' for new incident...")
                coords = get_coordinates(area)
                if coords:
                    latitude, longitude = coords
                    logger.info(f"✅ Resolved to {latitude}, {longitude}")
            except Exception as ge:
                logger.error(f"❌ Failed to auto-geocode area '{area}': {ge}")

        created_at = datetime.now()

        cursor.execute(insert_query, (
            area,
            area_urdu_val,
            area_translit_val,
            crime_type,
            date,
            crime_time_val,
            latitude,
            longitude,
            risk_level.capitalize() if risk_level else "Medium",
            "admin",
            "verified",
            created_at,
        ))
        
        conn.commit()
        crime_id = cursor.lastrowid

        # Trigger alerts for relevant users (subscribed or geographically near)
        try:
            from app.routes.alerts import dispatch_new_incident_alerts
            background_tasks.add_task(dispatch_new_incident_alerts, {
                "id": crime_id,
                "area": area,
                "area_translit": area_translit_val,
                "crime_type": crime_type,
                "latitude": latitude,
                "longitude": longitude,
                "risk_level": risk_level.capitalize() if risk_level else "Medium",
                "crime_date": date
            })
            logger.info(f"✅ Alert dispatch task scheduled for crime_id: {crime_id}")
        except Exception as alert_err:
            logger.error(f"Failed to schedule alert dispatch: {alert_err}")

        # Notify ModelWatcher
        try:
            if _get_watcher is not None:
                _get_watcher().notify_new_crime(area, crime_type)
        except Exception as _wex:
            logger.debug("ModelWatcher notify failed (non-fatal): %s", _wex)

        # Notify auto-retrain guard — checks for OOV features and schedules
        # a background retrain when new areas / crime types accumulate
        try:
            _ar_notify(area, crime_type)
        except Exception as _aex:
            logger.debug("auto_retrain notify failed (non-fatal): %s", _aex)

        # ── PROACTIVE ALERT: Notify nearby users of this new incident ────────
        try:
            from app.routes.alerts import alert_notification_system
            background_tasks.add_task(
                alert_notification_system.notify_nearby_users_of_incident,
                {
                    "id": crime_id,
                    "area": area,
                    "crime_type": crime_type,
                    "latitude": latitude,
                    "longitude": longitude,
                    "risk_level": risk_level
                }
            )
        except Exception as _enot:
             logger.debug("Failed to queue proactive alert (non-fatal): %s", _enot)

        # Return the created crime record
        return {
            "id": crime_id,
            "area": area,
            "type": crime_type,
            "date": date,
            "coordinates": [latitude, longitude] if latitude is not None and longitude is not None else [],
            "risk_level": risk_level.capitalize() if risk_level else "Medium",
            "message": "Crime record created successfully",
            "predicted_risk_percentage": risk_percentage,
            "confidence": confidence
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating crime record: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to create crime record")
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()

# Helper functions
def find_best_match(value: str, le) -> Optional[str]:
    """Find best matching encoder class"""
    if not value or not isinstance(value, str):
        return None

    value_stripped = value.strip()
    if not value_stripped:
        return None

    # 1. Exact case-insensitive match
    for cls in le.classes_:
        if cls.lower() == value_stripped.lower():
            return cls

    # 2. Try to match area names more intelligently
    for cls in le.classes_:
        cls_lower = cls.lower()
        value_lower = value_stripped.lower()

        # Check if one is a substring of the other
        if (len(value_lower) > 3 and value_lower in cls_lower) or \
           (len(cls_lower) > 3 and cls_lower in value_lower):
            return cls

    # 3. Fuzzy matching with higher threshold
    matches = difflib.get_close_matches(value_stripped, le.classes_, n=1, cutoff=0.7)
    if matches:
        return matches[0]

    return None

def calculate_risk_percentage(risk_level: str, probabilities: List[float], label_encoder) -> int:
    """Calculate meaningful risk percentage based on predicted class"""
    risk_ranges = {
        "High": (70, 100),
        "Medium": (30, 70),
        "Low": (0, 30)
    }

    # Get the probability of the predicted class
    try:
        class_index = list(label_encoder.classes_).index(risk_level)
        class_probability = probabilities[class_index]
    except (ValueError, IndexError):
        class_probability = max(probabilities)

    # Map to the appropriate range
    min_range, max_range = risk_ranges.get(risk_level, (30, 70))
    risk_percentage = int(min_range + (class_probability * (max_range - min_range)))

    return min(100, max(0, risk_percentage))

@router.post("/analyze-route-safety-ai", response_model=AIRouteSafetyResponse)
def analyze_route_safety_ai(request: AIRouteSafetyRequest):
    """
    Analyze route safety using AI predictions from Random Forest model

    This endpoint uses the trained Random Forest model to predict risk levels
    for each point along the route and aggregates them into an overall safety score.

    Args:
        request: AIRouteSafetyRequest with route_points (list of area/crime_type/coordinates)

    Returns:
        AIRouteSafetyResponse with overall_score, safety_level, point_predictions, and alerts
    """
    try:
        logger.info(f"🔍 AI Route Safety Analysis: {len(request.route_points)} points")

        # Initialize AI analyzer
        ai_analyzer = AIRouteSafetyAnalyzer()

        # Extract route data
        route_points = [(p.latitude, p.longitude) for p in request.route_points]
        areas = [p.area for p in request.route_points]
        crime_types = [p.crime_type for p in request.route_points]
        date = request.date

        # Perform AI analysis
        analysis_result = ai_analyzer.analyze_route_with_ai(
            route_points=route_points,
            areas=areas,
            crime_types=crime_types,
            date=date
        )

        logger.info(f"✅ AI Route Analysis Complete: Score={analysis_result['overall_score']}, Level={analysis_result['safety_level']}")

        return AIRouteSafetyResponse(
            overall_score=analysis_result["overall_score"],
            safety_level=analysis_result["safety_level"],
            point_predictions=analysis_result["point_predictions"],
            alerts=analysis_result["alerts"],
            summary=analysis_result["summary"]
        )

    except Exception as e:
        logger.error(f"❌ Error in AI route safety analysis: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"AI route analysis failed: {str(e)}")


@router.post("/compare-routes")
def compare_routes(
    start_lat: float,
    start_lng: float,
    end_lat: float,
    end_lng: float,
    date: Optional[str] = Query(None, description="Travel date YYYY-MM-DD (defaults to today)"),
    time: Optional[str] = Query(None, description="Departure time HH:MM (used for night-time risk weighting)"),
):
    """
    Calculate multiple route options and analyze safety of each using AI
    """
    try:
        from app.services.multi_route_calculator import MultiRouteCalculator
        import requests
        import requests.exceptions as _req_exc
        import time as time_lib  # renamed to avoid shadowing the `time` query param
        
        logger.info(f"🗺️ Calculating multiple routes from ({start_lat}, {start_lng}) to ({end_lat}, {end_lng})")
        
        # 1. Calculate multiple routes
        try:
            routes = MultiRouteCalculator.calculate_multiple_routes(
                start_lat, start_lng, end_lat, end_lng
            )
        except (_req_exc.Timeout, _req_exc.ConnectTimeout, _req_exc.ReadTimeout) as timeout_err:
            logger.warning(f"⏱️ OSRM routing service timed out: {timeout_err}")
            raise HTTPException(
                status_code=503,
                detail="The routing service is taking too long to respond. Please try again in a few seconds."
            )
        except (_req_exc.ConnectionError, _req_exc.RequestException) as conn_err:
            logger.warning(f"🔌 OSRM connection error: {conn_err}")
            raise HTTPException(
                status_code=503,
                detail="Could not connect to the routing service. Please check your internet connection and try again."
            )
        
        # Parse departure hour for night-time risk weighting
        travel_hour: Optional[int] = None
        if time:
            try:
                travel_hour = int(time.split(':')[0])
            except (ValueError, IndexError):
                pass

        # ── Traffic factor based on hour of day ─────────────────────────────
        # OSRM returns free-flow travel times. We apply a multiplicative
        # congestion factor so the Fastest label reflects realistic conditions.
        #   Peak morning (7-9):  1.4×   Peak evening (17-19): 1.5×
        #   Off-peak daytime:    1.15×  Night (22-5):           1.0×
        traffic_multiplier = 1.0
        if travel_hour is not None:
            h = travel_hour
            if 7 <= h <= 9:
                traffic_multiplier = 1.40   # morning rush
            elif 17 <= h <= 19:
                traffic_multiplier = 1.50   # evening rush
            elif 10 <= h <= 16:
                traffic_multiplier = 1.15   # normal daytime
            elif 20 <= h <= 21:
                traffic_multiplier = 1.10   # light evening
            # else: night, use free-flow (1.0)

        analyzed_routes = []
        area_crime_cache = {}
        
        # Get DB connection once for all routes
        conn = None
        cursor = None
        db_areas = []
        
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Load areas for matching
            cursor.execute("SELECT DISTINCT area FROM crimes WHERE area IS NOT NULL AND area != ''")
            db_areas = [row[0] for row in cursor.fetchall()]
            logger.info(f"📊 Loaded {len(db_areas)} areas from database for matching")
            
            ai_analyzer = AIRouteSafetyAnalyzer()
            # Plug in the Poisson model so route point scoring uses the new predictor
            if _poisson_artifacts:
                ai_analyzer.set_poisson(_poisson_artifacts, _poisson_predict)
            point_geocode_cache = {} # Cache Nominatim results for this request
            
            for route_type, route_data in routes.items():
                if route_data is None:
                    continue
                    
                logger.info(f"🤖 Analyzing {route_type} route...")
                
                # Sample points (max 7 points per route to avoid timeouts)
                coords = route_data['geometry']['coordinates']
                sample_size = min(7, len(coords))
                step = max(1, len(coords) // sample_size)
                sampled_coords = coords[::step][:sample_size]
                
                areas = []
                route_points = [] # (lat, lng)
                
                for i, coord in enumerate(sampled_coords):
                    lng, lat = coord
                    coord_key = (round(lat, 5), round(lng, 5))
                    
                    if coord_key in point_geocode_cache:
                        area = point_geocode_cache[coord_key]
                        logger.debug(f"📍 Using cached geocode for {coord_key}: {area}")
                    else:
                        # Add delay for Nominatim if not cached
                        if i > 0 or len(point_geocode_cache) > 0:
                            time_lib.sleep(1.1)
                            
                        area = "Lahore"
                        try:
                            response = requests.get(
                                "https://nominatim.openstreetmap.org/reverse",
                                params={
                                    'format': 'json',
                                    'lat': lat,
                                    'lon': lng,
                                    'zoom': 16,
                                    'addressdetails': 1,
                                    'accept-language': 'en'
                                },
                                headers={'User-Agent': 'CrimeVision-SafetyNavigation-v2/1.0'},
                                timeout=5
                            )
                            if response.ok:
                                addr = response.json().get('address', {})
                                area = next((addr.get(k) for k in ['suburb', 'neighbourhood', 'residential', 'quarter', 'city_district', 'district', 'city'] if addr.get(k)), "Lahore")
                                
                                # Match with DB using 70% similarity threshold
                                if db_areas:
                                    area_clean = area.lower().strip()
                                    for db_area in db_areas:
                                        db_area_clean = db_area.lower().strip()
                                        if area_clean == db_area_clean:
                                            area = db_area
                                            break
                                        if area_clean in db_area_clean or db_area_clean in area_clean:
                                            longer = max(len(area_clean), len(db_area_clean))
                                            shorter = min(len(area_clean), len(db_area_clean))
                                            if shorter / longer >= 0.7:
                                                area = db_area
                                                break
                            else:
                                logger.warning(f"⚠️ Nominatim returned {response.status_code}")
                        except Exception as geocode_e:
                            logger.warning(f"⚠️ Geocoding failed for {coord}: {geocode_e}")
                        
                        point_geocode_cache[coord_key] = area
                        
                    areas.append(area)
                    route_points.append((lat, lng))
                
                # Get crime types for these areas
                crime_types_list = []
                for area in areas:
                    if area not in area_crime_cache:
                        cursor.execute("""
                            SELECT crime_type, COUNT(*) as count 
                            FROM crimes 
                            WHERE area LIKE %s 
                            GROUP BY crime_type 
                            ORDER BY count DESC 
                            LIMIT 5
                        """, (f"%{area}%",))
                        results = cursor.fetchall()
                        
                        if not results:
                            area_no_space = area.replace(" ", "")
                            cursor.execute("""
                                SELECT crime_type, COUNT(*) as count 
                                FROM crimes 
                                WHERE REPLACE(area, ' ', '') LIKE %s 
                                GROUP BY crime_type 
                                ORDER BY count DESC 
                                LIMIT 5
                            """, (f"%{area_no_space}%",))
                            results = cursor.fetchall()
                            
                        if not results:
                            area_crime_cache[area] = {'types': ["No Crimes Detected"], 'index': 0}
                        else:
                            area_crime_cache[area] = {'types': [r[0] for r in results], 'index': 0}
                            
                    cache = area_crime_cache[area]
                    crime_types_list.append(cache['types'][cache['index'] % len(cache['types'])])
                    cache['index'] += 1
                
                # AI Analysis
                analysis = ai_analyzer.analyze_route_with_ai(
                    route_points, areas, crime_types_list,
                    date=date, hour=travel_hour,
                )
                # Apply traffic multiplier to the displayed duration
                traffic_adjusted_min = round(route_data['duration_min'] * traffic_multiplier, 1)
                route_data_annotated = dict(route_data)
                route_data_annotated['duration_min_traffic'] = traffic_adjusted_min
                route_data_annotated['traffic_multiplier'] = round(traffic_multiplier, 2)
                analyzed_routes.append({
                    'route_type': route_type,
                    'route_data': route_data_annotated,
                    'safety_analysis': analysis,
                    'areas_along_route': list(dict.fromkeys(areas)),  # deduplicated, order-preserving
                    'crime_types_detected': sorted({ct for ct in crime_types_list if ct != "No Crimes Detected"}),
                })
                
        except Exception as e:
            logger.error(f"❌ Error during route analysis: {e}", exc_info=True)
            raise # Re-raise to be caught by outer except
        finally:
            if cursor: cursor.close()
            if conn: conn.close()
            
        if not analyzed_routes:
            return {'routes': [], 'recommendation': None}
            
        # 1. Filter for unique routes (diversity check)
        unique_routes = []
        for r in analyzed_routes:
            is_duplicate = False
            for ur in unique_routes:
                # If distance and duration are within 2% of each other, it's likely a duplicate path
                # Add small epsilon to avoid division by zero
                ur_dist = ur['route_data']['distance'] or 1
                ur_dur = ur['route_data']['duration'] or 1
                dist_diff = abs(r['route_data']['distance'] - ur_dist) / ur_dist
                dur_diff = abs(r['route_data']['duration'] - ur_dur) / ur_dur
                # 7% threshold — Lahore's grid roads often produce alternatives
                # within 2-5% of each other, so 2% was collapsing all routes into one.
                if dist_diff < 0.07 and dur_diff < 0.07:
                    is_duplicate = True
                    break
            if not is_duplicate:
                unique_routes.append(r)
        
        logger.info(f"🛤️ Found {len(unique_routes)} unique paths out of {len(analyzed_routes)} OSRM results")
        
        if not unique_routes:
            return {'routes': [], 'recommendation': None}

        # ── 2. Distance-exposure correction ──────────────────────────────────────
        # A longer route passes through more area and accumulates more cumulative
        # crime exposure. Scale each route's base risk by its distance ratio so
        # routes of equal area-crime-density still receive differentiated scores.
        min_dist_m = min(r['route_data']['distance'] for r in unique_routes) or 1
        for r in unique_routes:
            dist_ratio = r['route_data']['distance'] / min_dist_m
            score = r['safety_analysis']['overall_score']
            risk_pct = 100 - score
            # Full linear scaling: a route 30% longer → 30% more cumulative risk
            scaled_risk = min(risk_pct * dist_ratio, 90)   # floor score at 10
            r['safety_analysis']['overall_score'] = round(max(10, 100 - scaled_risk), 1)

        # ── 3. Sort by each criterion (post-scaling) ──────────────────────────
        by_duration = sorted(unique_routes, key=lambda x: x['route_data']['duration_min_traffic'])
        by_safety   = sorted(unique_routes, key=lambda x: (
            x['safety_analysis']['overall_score'],
            -x['safety_analysis']['summary']['high_risk_points'],
            -x['safety_analysis']['summary']['medium_risk_points']
        ), reverse=True)
        by_distance = sorted(unique_routes, key=lambda x: x['route_data']['distance'])

        # ── 4. True winners — a label is only assigned when the route IS #1 ─────
        # A route wins "fastest" only if it truly has the shortest duration.
        # A route wins "shortest" only if it truly has the shortest distance.
        # A route always wins "safest" (it IS the highest-scored route).
        # When one route wins multiple criteria it gets secondary_labels chips.
        # All other routes become "alternative" labelled by their via-area so the
        # user is never misled by a "FASTEST" badge on a slower route.
        true_safest   = by_safety[0]
        true_fastest  = by_duration[0]
        true_shortest = by_distance[0]

        # Build a map: object id → list of categories this route genuinely wins
        abs_winner: Dict[int, List[str]] = {}
        for route_obj, lbl in [
            (true_safest,   'safest'),
            (true_fastest,  'fastest'),
            (true_shortest, 'shortest'),
        ]:
            rid = id(route_obj)
            if rid not in abs_winner:
                abs_winner[rid] = []
            abs_winner[rid].append(lbl)

        priority_order = ['safest', 'fastest', 'shortest']
        used: set = set()
        final_labeled: List[Dict[str, Any]] = []

        # Assign named labels only to true winners (in display priority order)
        for r in unique_routes:
            rid = id(r)
            if rid in abs_winner and rid not in used:
                wins = abs_winner[rid]
                primary = next(l for l in priority_order if l in wins)
                r['label'] = primary
                r['secondary_labels'] = [l for l in priority_order if l in wins and l != primary]
                used.add(rid)
                final_labeled.append(r)

        # Everything else → alternative (labelled by the 2nd area along the route)
        alt_counter = 0
        for r in unique_routes:
            if id(r) not in used:
                alt_counter += 1
                via = r['areas_along_route'][1] if len(r['areas_along_route']) > 1 else 'city centre'
                r['label'] = 'alternative'
                r['secondary_labels'] = []
                r['alt_via'] = via
                r['alt_index'] = alt_counter
                final_labeled.append(r)
                used.add(id(r))

        # ── 6b. Among alternatives, promote relative fastest/shortest ──────────
        alt_routes = [r for r in final_labeled if r.get('label') == 'alternative']
        if alt_routes:
            alt_fastest_r  = min(alt_routes, key=lambda x: x['route_data']['duration_min_traffic'])
            alt_shortest_r = min(alt_routes, key=lambda x: x['route_data']['distance'])
            if id(alt_fastest_r) == id(alt_shortest_r):
                alt_fastest_r['label'] = 'fastest_alt'
                alt_fastest_r['secondary_labels'] = ['shortest_alt']
            else:
                alt_fastest_r['label']  = 'fastest_alt'
                alt_fastest_r['secondary_labels'] = []
                alt_shortest_r['label'] = 'shortest_alt'
                alt_shortest_r['secondary_labels'] = []

        # ── 7. Display sort: Safest → Fastest → Shortest → F-Alt → S-Alt → Alt ─
        def display_sort(r):
            l = r.get('label', '').lower()
            if l == 'safest':      return 0
            if l == 'fastest':     return 1
            if l == 'shortest':    return 2
            if l == 'fastest_alt': return 3
            if l == 'shortest_alt': return 4
            return 5

        final_labeled.sort(key=display_sort)

        logger.info(
            f"✅ Route comparison complete: {len(final_labeled)} routes. "
            f"Labels: {[(r.get('label'), r.get('secondary_labels')) for r in final_labeled]}, "
            f"traffic_multiplier={traffic_multiplier:.2f}"
        )
        return {
            'routes': final_labeled,
            'recommendation': by_safety[0] if by_safety else None
        }
        
    except HTTPException:
        # Preserve specific HTTP statuses (e.g. 503 for OSRM timeouts) raised
        # earlier in this handler. Without this, the generic except below would
        # swallow them and rebrand every routing failure as a 500.
        raise
    except Exception as e:
        logger.error(f"❌ Error comparing routes: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Route comparison failed: {str(e)}")


# ─── Intelligence Command Center Dashboard ────────────────────────────────────

@router.get("/intelligence-dashboard")
def get_intelligence_dashboard(current_user: str = Depends(get_username_from_token)):
    """
    SuperAdmin: Returns a comprehensive intelligence snapshot in a single call —
    dataset health, model health, data drift, crime trends, high-risk alerts,
    and a 7-day risk forecast for the top 5 most active areas.
    """
    conn   = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        from datetime import datetime as _dt, timedelta as _td

        # ── 1. Dataset Health ─────────────────────────────────────────────────
        cursor.execute("SELECT COUNT(*) AS n FROM crimes")
        total_records = int(cursor.fetchone()['n'])

        cursor.execute("SELECT COUNT(DISTINCT area) AS n FROM crimes")
        areas_covered = int(cursor.fetchone()['n'])

        cursor.execute("SELECT COUNT(DISTINCT crime_type) AS n FROM crimes")
        crime_types_count = int(cursor.fetchone()['n'])

        cursor.execute("SELECT MAX(created_at) AS lu FROM crimes")
        row = cursor.fetchone()
        last_update = str(row['lu']) if row and row['lu'] else None

        # Crime areas missing from the coordinate reference table
        # (i.e. areas that appear in FIR records but have no geocoding entry)
        cursor.execute("""
            SELECT DISTINCT c.area FROM crimes c
            LEFT JOIN areas a ON a.area_name = c.area
            WHERE c.area IS NOT NULL AND c.area != '' AND a.area_name IS NULL
            ORDER BY c.area
        """)
        missing_areas = [r['area'] for r in cursor.fetchall()]

        # Crime types with very few total records (potentially unreliable)
        cursor.execute("""
            SELECT crime_type, COUNT(*) AS cnt FROM crimes
            GROUP BY crime_type HAVING cnt < 10 ORDER BY cnt
        """)
        sparse_labels = [r['crime_type'] for r in cursor.fetchall()[:8]]

        cursor.execute(
            "SELECT COUNT(*) AS n FROM crimes "
            "WHERE crime_type IS NULL OR crime_type='' OR crime_type='Unknown'"
        )
        unknown_labels = int(cursor.fetchone()['n'])

        # ── 2. Crime Trend Intelligence (90-day vs prior 90-day) ──────────────
        cursor.execute("""
            SELECT crime_type,
                   SUM(CASE WHEN crime_date >= DATE_SUB(CURDATE(), INTERVAL 90 DAY)
                            THEN 1 ELSE 0 END) AS recent,
                   SUM(CASE WHEN crime_date BETWEEN DATE_SUB(CURDATE(), INTERVAL 180 DAY)
                                                AND DATE_SUB(CURDATE(), INTERVAL 91 DAY)
                            THEN 1 ELSE 0 END) AS prior
            FROM crimes
            WHERE crime_date >= DATE_SUB(CURDATE(), INTERVAL 180 DAY)
            GROUP BY crime_type
        """)
        trend_raw = cursor.fetchall()
        rising, falling, shifts = [], [], []
        for r in trend_raw:
            recent = int(r['recent'] or 0)
            prior  = int(r['prior']  or 0)
            if prior > 0:
                pct = round((recent - prior) / prior * 100, 1)
            elif recent > 0:
                pct = 100.0
            else:
                pct = 0.0
            # Only include crime types with enough samples to be meaningful
            if prior >= 5 or recent >= 5:
                shifts.append(abs(pct))
                entry = {
                    'crime_type': r['crime_type'],
                    'pct_change': pct,
                    'recent': recent,
                    'prior': prior,
                }
                if pct >= 5:
                    rising.append(entry)
                elif pct <= -5:
                    falling.append(entry)
        rising.sort(key=lambda x: -x['pct_change'])
        falling.sort(key=lambda x: x['pct_change'])

        # ── 3. Data Drift Detection ───────────────────────────────────────────
        cursor.execute("""
            SELECT DISTINCT area FROM crimes
            WHERE crime_date >= DATE_SUB(CURDATE(), INTERVAL 90 DAY)
              AND area NOT IN (
                  SELECT DISTINCT area FROM crimes
                  WHERE crime_date < DATE_SUB(CURDATE(), INTERVAL 90 DAY)
              )
        """)
        new_areas = [r['area'] for r in cursor.fetchall()]

        cursor.execute("""
            SELECT DISTINCT crime_type FROM crimes
            WHERE crime_date >= DATE_SUB(CURDATE(), INTERVAL 90 DAY)
              AND crime_type NOT IN (
                  SELECT DISTINCT crime_type FROM crimes
                  WHERE crime_date < DATE_SUB(CURDATE(), INTERVAL 90 DAY)
              )
        """)
        new_crime_types = [r['crime_type'] for r in cursor.fetchall()]

        avg_shift = round(sum(shifts) / len(shifts), 1) if shifts else 0
        dist_shift = (
            'High'     if avg_shift >= 25
            else 'Moderate' if avg_shift >= 10
            else 'Low'
        )
        needs_retrain = (
            len(new_areas) > 2
            or len(new_crime_types) > 2
            or dist_shift == 'High'
        )

        # ── 4. High-Risk Alerts (top area+crime in last 30 days) ─────────────
        cursor.execute("""
            SELECT area, crime_type, COUNT(*) AS cnt
            FROM crimes
            WHERE crime_date >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
            GROUP BY area, crime_type
            ORDER BY cnt DESC
            LIMIT 8
        """)
        alerts_raw = cursor.fetchall()
        high_risk_alerts = []
        today_str = _dt.now().strftime('%Y-%m-%d')
        _risk_order = {'Critical': 0, 'High': 1, 'Medium': 2, 'Low': 3}
        for r in alerts_raw:
            risk_level = 'Medium'
            risk_pct   = 50
            if _poisson_artifacts:
                try:
                    pred = _poisson_predict(
                        _poisson_artifacts,
                        area       = r['area'],
                        crime_type = r['crime_type'],
                        date_str   = today_str,
                    )
                    risk_level = pred.get('risk_level', 'Medium')
                    risk_pct   = pred.get('risk_percentage', 50)
                except Exception:
                    pass
            high_risk_alerts.append({
                'area':          r['area'],
                'crime_type':    r['crime_type'],
                'incidents_30d': int(r['cnt']),
                'risk_level':    risk_level,
                'risk_pct':      risk_pct,
                'date':          today_str,
            })
        high_risk_alerts.sort(key=lambda x: _risk_order.get(x['risk_level'], 4))

        # ── 5. 7-Day Forecast for top 5 areas ────────────────────────────────
        cursor.execute("""
            SELECT area, COUNT(*) AS cnt FROM crimes
            WHERE crime_date >= DATE_SUB(CURDATE(), INTERVAL 90 DAY)
            GROUP BY area ORDER BY cnt DESC LIMIT 5
        """)
        top_areas = [r['area'] for r in cursor.fetchall()]

        forecast_7day = {}
        _day_labels = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
        if _poisson_artifacts and top_areas:
            # Get most common crime type per area (top crime = most representative)
            cursor.execute(
                """
                SELECT area, crime_type, COUNT(*) AS cnt
                FROM crimes
                WHERE crime_date >= DATE_SUB(CURDATE(), INTERVAL 90 DAY)
                  AND area IN ({ph})
                GROUP BY area, crime_type
                ORDER BY area, cnt DESC
                """.format(ph=','.join(['%s'] * len(top_areas))),
                top_areas,
            )
            area_top_crime = {}
            for r in cursor.fetchall():
                if r['area'] not in area_top_crime:
                    area_top_crime[r['area']] = r['crime_type']

            for area in top_areas:
                ct = area_top_crime.get(area, '')
                days_forecast = []
                for d in range(7):
                    future = _dt.now() + _td(days=d + 1)
                    try:
                        pred = _poisson_predict(
                            _poisson_artifacts,
                            area       = area,
                            crime_type = ct,
                            date_str   = future.strftime('%Y-%m-%d'),
                        )
                        rl = pred.get('risk_level', 'Low')
                    except Exception:
                        rl = 'Low'
                    days_forecast.append({
                        'day':  _day_labels[future.weekday()],
                        'date': future.strftime('%b %d'),
                        'risk': rl,
                    })
                forecast_7day[area] = {'crime_type': ct, 'days': days_forecast}

        # ── 6. Model Health ───────────────────────────────────────────────────
        oov_count = 0
        last_retrain_ts = 0
        retrain_count = 0
        try:
            from utils.auto_retrain import get_oov_status as _get_oov_intel
            oov_status      = _get_oov_intel()
            oov_count       = len(oov_status.get('oov_pairs', []))
            last_retrain_ts = oov_status.get('last_retrain', 0)
            retrain_count   = oov_status.get('retrain_count', 0)
        except Exception:
            pass

        reliability = (
            'High' if oov_count <= 5
            else 'Moderate' if oov_count <= 15
            else 'Low'
        )

        # Resolve model metadata from artifacts first; fall back to model file mtime.
        # This avoids stale/hardcoded dates and avoids relying on created_at column shape.
        last_train_date = '—'
        training_size = total_records
        records_since_last_train = 0
        rf_accuracy_pct = 82
        poisson_mae_pct = 11
        trained_at_dt = None
        try:
            artifacts_path = os.path.join(_CRM_DIR, 'models', 'model_artifacts.json')
            if os.path.exists(artifacts_path):
                with open(artifacts_path, 'r', encoding='utf-8') as f:
                    _arts = json.load(f)
                _trained_at_raw = _arts.get('trained_at')
                _n_samples_raw = _arts.get('n_training_samples')
                _cv_acc = _arts.get('cv_accuracy_mean')
                if _n_samples_raw is not None:
                    training_size = int(_n_samples_raw)
                if _cv_acc is not None:
                    try:
                        rf_accuracy_pct = int(round(float(_cv_acc) * 100))
                    except Exception:
                        pass
                if _trained_at_raw:
                    try:
                        trained_at_dt = _dt.fromisoformat(str(_trained_at_raw))
                    except Exception:
                        trained_at_dt = None

            if trained_at_dt is None:
                model_path = os.path.join(_CRM_DIR, 'models', 'random_forest_model.joblib')
                if os.path.exists(model_path):
                    trained_at_dt = _dt.fromtimestamp(os.path.getmtime(model_path))

            if trained_at_dt is not None:
                last_train_date = trained_at_dt.strftime('%b %d, %Y')

            records_since_last_train = max(0, int(total_records) - int(training_size))

            # If auto-retrain status has a newer timestamp, prefer that display date.
            if last_retrain_ts:
                _lrt_dt = _dt.fromtimestamp(float(last_retrain_ts))
                if (trained_at_dt is None) or (_lrt_dt > trained_at_dt):
                    last_train_date = _lrt_dt.strftime('%b %d, %Y')
        except Exception:
            pass

        return {
            'dataset_health': {
                'total_records':             total_records,
                'areas_covered':             areas_covered,
                'crime_types_count':         crime_types_count,
                'last_update':               last_update,
                'records_since_last_train':  records_since_last_train,
                'missing_areas':             missing_areas[:6],
                'missing_areas_count':       len(missing_areas),
                'sparse_labels':             sparse_labels,
                'unknown_labels':            unknown_labels,
            },
            'model_health': {
                'rf_accuracy':     rf_accuracy_pct,
                'poisson_mae_pct': poisson_mae_pct,
                'reliability':     reliability,
                'oov_count':       oov_count,
                'last_train_date': last_train_date,
                'retrain_count':   retrain_count,
                'training_size':   training_size,
            },
            'drift': {
                'new_areas':             new_areas[:6],
                'new_areas_count':       len(new_areas),
                'new_crime_types':       new_crime_types[:6],
                'new_crime_types_count': len(new_crime_types),
                'distribution_shift':    dist_shift,
                'avg_shift_pct':         avg_shift,
                'recommended_action':    'Retrain Model' if needs_retrain else 'Monitor',
            },
            'crime_trends': {
                'rising':  rising[:7],
                'falling': falling[:5],
            },
            'high_risk_alerts': high_risk_alerts,
            'forecast_7day':    forecast_7day,
        }

    except Exception as ex:
        logger.error("intelligence-dashboard error: %s", ex, exc_info=True)
        raise HTTPException(status_code=500, detail=str(ex))
    finally:
        cursor.close()
        if conn.is_connected():
            conn.close()


# ─── Auto-Retrain Status / Manual Trigger ────────────────────────────────────

@router.get("/model/oov-status")
def get_oov_status(current_user: str = Depends(get_username_from_token)):
    """
    Admin/SuperAdmin: return OOV counter status so the dashboard can show
    how many new unseen feature combinations have arrived since last retrain.
    """
    try:
        from utils.auto_retrain import get_oov_status as _get_oov
        status = _get_oov()
        return {
            "oov_pair_count":      len(status.get("oov_pairs", [])),
            "oov_threshold":       20,
            "new_record_count":    status.get("new_records", 0),
            "new_record_threshold": 50,
            "retrain_count":       status.get("retrain_count", 0),
            "last_retrain":        status.get("last_retrain", 0),
            "oov_pairs_sample":    status.get("oov_pairs", [])[:10],
        }
    except Exception as e:
        return {"error": str(e)}


@router.post("/model/trigger-retrain")
def trigger_retrain(current_user: str = Depends(get_username_from_token)):
    """
    Admin/SuperAdmin: manually trigger a background retrain immediately,
    bypassing OOV thresholds.  Returns immediately; retrain runs async.
    """
    import threading
    try:
        from utils.auto_retrain import _run_retrain, _load_counters
        counters = _load_counters()
        t = threading.Thread(target=_run_retrain, args=(counters,), daemon=True, name="manual-retrain")
        t.start()
        return {"success": True, "message": "Retrain launched in background. Model will hot-reload when complete."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─── Heatmap Endpoint ────────────────────────────────────────────────────────

@router.get("/areas/{area}/heatmap")
def get_area_heatmap(area: str):
    """Get heatmap data for crime density in a specific area with unified risk scores"""
    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")
    cursor = conn.cursor(dictionary=True)
    try:
        # Get all crimes for the area
        cursor.execute("""
            SELECT
                id, area, crime_type, crime_date,
                latitude, longitude, risk_level
            FROM crimes
            WHERE area = %s
                AND latitude IS NOT NULL
                AND longitude IS NOT NULL
            ORDER BY crime_date DESC
            LIMIT 1000
        """, (area,))
        crimes = cursor.fetchall()

        heatmap_data = []
        for crime in crimes:
            crime_dict = cast(Dict[str, Any], crime)
            if crime_dict["latitude"] and crime_dict["longitude"]:
                heatmap_data.append({
                    "lat": float(crime_dict["latitude"]),
                    "lng": float(crime_dict["longitude"]),
                    "weight": 1.0,
                    "risk_level": crime_dict["risk_level"],
                    "crime_type": crime_dict["crime_type"],
                    "date": str(crime_dict["crime_date"])
                })

        clusters = []
        if heatmap_data:
            cluster_map: Dict[str, Any] = {}
            now = datetime.utcnow()
            cutoff_90 = now - timedelta(days=90)
            cutoff_30 = now - timedelta(days=30)
            cutoff_45 = now - timedelta(days=45)  # for recent/older split

            for point in heatmap_data:
                cluster_key = f"{round(point['lat'], 3)},{round(point['lng'], 3)}"
                if cluster_key not in cluster_map:
                    cluster_map[cluster_key] = {
                        "lat": round(point['lat'], 3),
                        "lng": round(point['lng'], 3),
                        "count": 0,
                        "high_risk_count": 0,
                        "medium_risk_count": 0,
                        "last_30_days": 0,
                        "last_90_days": 0,
                        "recent_count": 0,
                        "older_count": 0,
                    }

                cluster = cluster_map[cluster_key]
                cluster["count"] += 1

                # Count by risk level
                risk_level = str(point["risk_level"] or "").lower()
                if risk_level in ("high", "critical", "avoid", "warning"):
                    cluster["high_risk_count"] += 1
                elif risk_level in ("moderate", "medium", "caution"):
                    cluster["medium_risk_count"] += 1

                # Count by recency
                crime_date = point["date"]
                if isinstance(crime_date, str):
                    try:
                        crime_dt = datetime.fromisoformat(crime_date.replace('Z', '+00:00'))
                    except:
                        crime_dt = None
                else:
                    crime_dt = crime_date

                if crime_dt:
                    if crime_dt >= cutoff_30:
                        cluster["last_30_days"] += 1
                    if crime_dt >= cutoff_90:
                        cluster["last_90_days"] += 1
                    if crime_dt >= cutoff_45:
                        cluster["recent_count"] += 1
                    else:
                        cluster["older_count"] += 1

            # Calculate unified risk scores for each cluster
            clusters = []
            for cluster in cluster_map.values():
                stats = {
                    "total_crimes": cluster["count"],
                    "high_risk_count": cluster["high_risk_count"],
                    "medium_risk_count": cluster["medium_risk_count"],
                    "last_30_days": cluster["last_30_days"],
                    "last_90_days": cluster["last_90_days"],
                    "recent_count": cluster["recent_count"],
                    "older_count": cluster["older_count"],
                }

                # Get unified risk summary
                risk_summary = calculate_unified_risk_summary(stats)

                clusters.append({
                    "lat": cluster["lat"],
                    "lng": cluster["lng"],
                    "count": cluster["count"],
                    "high_risk_count": cluster["high_risk_count"],
                    "medium_risk_count": cluster["medium_risk_count"],
                    "high_risk_ratio": cluster["high_risk_count"] / cluster["count"] if cluster["count"] > 0 else 0,
                    "risk_score": risk_summary["risk_score"],
                    "safety_score": risk_summary["safety_score"],
                    "risk_level": risk_summary["risk_level"],
                    "risk_label": risk_summary["risk_label"],
                })

        return {
            "area": area,
            "heatmap_points": heatmap_data,
            "clusters": clusters,
            "total_points": len(heatmap_data),
            "data_range": {
                "min_intensity": 0,
                "max_intensity": 1.0
            }
        }

    except MySQLError as e:
        logger.error(f"Database error getting heatmap data: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve heatmap data")
    finally:
        cursor.close()
        conn.close()


@router.get("/model-watcher-status")
def get_model_watcher_status(current_user: str = Depends(get_username_from_token)):
    """
    Return the current state of the ModelWatcher background retrainer.
    Shows how many new crimes/areas/crime-types have arrived since last training
    and whether a retrain is currently running.
    """
    try:
        if _get_watcher is None:
            return {"available": False, "reason": "ModelWatcher not loaded"}
        return {"available": True, **_get_watcher().status()}
    except Exception as e:
        logger.error("model-watcher-status error: %s", e)
        raise HTTPException(status_code=500, detail="Could not retrieve watcher status")


@router.post("/reload-model")
def reload_model(current_user: str = Depends(get_username_from_token)):
    """
    Hot-reload the RF model from disk without restarting the server.
    Useful after manually running train_model.py or after a sklearn upgrade.
    Superadmin only.
    """
    global _crm_model, _crm_scaler, _crm_artifacts
    try:
        new_model, new_scaler, new_artifacts = _crm_load_model(
            os.path.join(_CRM_DIR, 'models')
        )
        _crm_model    = new_model
        _crm_scaler   = new_scaler
        _crm_artifacts = new_artifacts
        logger.info("[reload-model] RF model reloaded OK (classes: %s)",
                    _crm_artifacts.get('label_classes'))
        return {
            "success": True,
            "message": "Model reloaded successfully",
            "classes": _crm_artifacts.get('label_classes'),
            "n_training_samples": _crm_artifacts.get('n_training_samples'),
            "trained_at": _crm_artifacts.get('trained_at'),
        }
    except Exception as e:
        logger.error("[reload-model] Failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Model reload failed: {e}")
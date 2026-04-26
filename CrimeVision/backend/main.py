# main.py - Updated with proper database configuration
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union, cast
from fastapi import FastAPI, Query, HTTPException, Depends, Request, BackgroundTasks, File, UploadFile
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
import os
import sys
import glob
import shutil
import tempfile
import time

# Ensure parent directory is on sys.path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from pydantic import BaseModel, Field
import secrets
import string
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
import re
from app.core.database import ensure_alerts_tables_schema, ensure_alert_subscriptions_table, ensure_browser_notifications_tables

if TYPE_CHECKING:
    from fastapi import BackgroundTasks

# Add these imports at the top
from typing import Optional
import asyncio
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
import threading
import requests
import difflib
import json
import joblib
import numpy as np
import pandas as pd
import uvicorn

from fastapi.middleware.cors import CORSMiddleware

from mysql.connector import Error

# Add the backend directory to Python path for absolute imports
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from app.auth_updated import create_access_token, get_password_hash, verify_password, verify_token, create_refresh_token, verify_refresh_token
from app.core.database import get_db_connection, initialize_schema, log_user_activity
from app.auth_routes import router as auth_router

from app.core.config import ALLOWED_ORIGINS, MODEL_DIR, get_api_title, get_logger
from app.models.types import CrimeRow, CrimeTypeRow
from app.models.schemas import LocationRequest, LocationResponse, RiskZoneAlert, RouteData, SafetyResponse, Waypoint
from app.utils.geo import get_coordinates
# Include all routers
# Import routers that may depend on the app after it's created to avoid circular imports
from app.alert_notifications import AlertNotificationSystem
from app.routes.test_alerts import test_router
from app.alert_tester import AlertTester
from app.alert_routes import router as alert_router
from app.utils.validation import (
    generate_username,
    validate_crime_type,
    validate_date_format,
    validate_name,
)
from app.utils.area_normalization import area_like_pattern

# Import the new route safety analyzer
from app.services.route_safety_analyzer import RouteSafetyAnalyzer

# Import report generation functions
from app.reports import (
    generate_crime_summary_pdf,
    generate_crime_summary_excel,
    generate_crime_summary_csv,
    generate_user_activity_pdf,
    generate_user_activity_excel,
    generate_user_activity_csv,
    generate_system_health_pdf,
    generate_system_health_excel,
    generate_system_health_csv,
    get_crime_summary_data,
    get_system_health_data,
    get_user_activity_data,
    save_report_to_db,
    get_reports_from_db,
    get_scheduled_reports_from_db,
)

import logging
logger = logging.getLogger(__name__)

# Risk calculation utilities
from app.utils.risk import calculate_safety_score, calculate_breakdown, calculate_unified_risk_summary, compute_poisson_risk_pct, get_risk_level

# Import OCR modules for FIR extraction
from app.ocr.fir_specialized_ocr import FIRExtractor, load_areas_for_geocoding as _ocr_load_areas, geocode_crime_area as _ocr_geocode_area
from app.ocr.urdu_location_dictionary import correct_location_text, _normalize_text
from app.ocr.ppc_sections import get_crime_names

# Import password reset functions and models
from app.password_reset_fixed import forgot_password, reset_password, ForgotPasswordRequest, ResetPasswordRequest

# Import route modules
from app.routes.auth import router as auth_router_extended
from app.routes.alerts import VAPID_PRIVATE_KEY, VAPID_PUBLIC_KEY, router as alerts_router, monitor_saved_locations, dispatch_weekly_safety_reports, poll_new_incidents_for_alerts
from app.routes.crimes import router as crimes_router
from app.routes.emergency import router as emergency_router
from app.routes.admin import router as admin_router
from app.routes.reports import router as reports_router
from app.routes.community import router as community_router
from app.routes.user_profile import get_user_alerts, router as user_profile_router
from app.routes.location import router as location_router

# Import dependencies
from app.dependencies import security, get_username_from_token, get_current_user

# Add global variable for cooldown tracking
alert_cooldown_cache: Dict[str, datetime] = {}

security = HTTPBearer()
app = FastAPI(title=get_api_title())
app.add_middleware(
    CORSMiddleware,
    # Read from ALLOWED_ORIGINS env var (comma-separated). Defaults to local
    # dev origins. Production: set ALLOWED_ORIGINS to your Vercel URL.
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ========== OCR ENGINE INITIALIZATION ==========
def cleanup_temp_files():
    """Clean up temporary files to prevent storage issues"""
    try:
        debug_files = glob.glob('debug_*.png')
        for f in debug_files:
            try:
                if os.path.exists(f) and os.path.getmtime(f) < (time.time() - 3600):
                    os.remove(f)
            except:
                pass
        temp_dir = tempfile.gettempdir()
        tesseract_temp = os.path.join(temp_dir, 'tesseract*')
        for f in glob.glob(tesseract_temp):
            try:
                if os.path.isfile(f):
                    os.remove(f)
                elif os.path.isdir(f):
                    shutil.rmtree(f, ignore_errors=True)
            except:
                pass
    except Exception as e:
        logger.warning(f"Cleanup failed: {e}")

# Initialize OCR engine
try:
    fir_extractor = FIRExtractor()
    logger.info("✅ FIR OCR extractor initialized successfully")
except Exception as e:
    fir_extractor = None
    logger.warning(f"⚠️ FIR OCR extractor failed to initialize: {e}")

# ========== FORCE CORS MIDDLEWARE ==========
@app.middleware("http")
async def force_cors_middleware(request: Request, call_next):
    """Middleware to force CORS headers on all responses"""
    # Handle preflight requests
    if request.method == "OPTIONS":
        response = JSONResponse(content={"message": "OK"})
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, Accept, Origin, X-Requested-With, Cache-Control"
        response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers["Access-Control-Expose-Headers"] = "*"
        response.headers["Access-Control-Max-Age"] = "86400"
        return response
    else:
        response = await call_next(request)
    
    # Add CORS headers to every response
    origin = request.headers.get("origin")
    if origin in [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://192.168.0.104:5173",
        "http://192.168.56.1:5173",
    ]:
        response.headers["Access-Control-Allow-Origin"] = origin
    else:
        response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, Accept, Origin, X-Requested-With, Cache-Control"
    response.headers["Access-Control-Allow-Credentials"] = "true"
    response.headers["Access-Control-Expose-Headers"] = "*"
    
    return response

# Include all routers
app.include_router(alert_router)  # Include alert_router without prefix
app.include_router(auth_router_extended)
app.include_router(alerts_router, prefix="/api")
app.include_router(crimes_router, prefix="/api")
app.include_router(emergency_router, prefix="/api")
# Routers already declare their own prefixes; include them without adding duplicate prefixes
app.include_router(admin_router)
app.include_router(reports_router)
app.include_router(community_router, prefix="/api")
app.include_router(user_profile_router, prefix="/api")
app.include_router(location_router, prefix="/api")
app.include_router(test_router, prefix="/api")

# Import and include new analytics and admin reports routers
from app.routes.analytics import router as analytics_router
from app.routes.admin_reports import router as admin_reports_router
from app.routes.law_sections import router as law_sections_router

app.include_router(analytics_router)  # Prefix already defined in router
app.include_router(admin_reports_router)  # Prefix already defined in router
app.include_router(law_sections_router)  # Prefix already defined in router (/api/law-sections)

# Include original auth router for any remaining routes
app.include_router(auth_router)

# Flat alias endpoints expected by frontend
# /api/areas and /api/crime-types from crimes router
from app.routes.crimes import get_areas as crimes_get_areas, get_crime_types as crimes_get_crime_types

@app.get("/api/areas")
def api_areas_alias():
    return crimes_get_areas()

@app.get("/api/crime-types")
def api_crime_types_alias():
    return crimes_get_crime_types()

# /api/emergency-contacts and /api/emergency-stats from emergency router
from app.routes.emergency import get_emergency_contacts as emergency_get_contacts, get_emergency_stats as emergency_get_stats

@app.get("/api/emergency-contacts")
async def api_emergency_contacts_alias():
    return emergency_get_contacts()

@app.get("/api/emergency-stats")
async def api_emergency_stats_alias():
    return await emergency_get_stats()

# Flat alias for crimes predict-risk
from app.routes.crimes import predict_risk as crimes_predict_risk
from app.models.schemas import PredictRiskRequest

@app.post("/api/predict-risk")
def api_predict_risk_alias(request: PredictRiskRequest):
    return crimes_predict_risk(request)

# Flat alias for heatmap data
from app.routes.crimes import (
    get_area_heatmap as crimes_get_heatmap,
    get_area_details as crimes_get_area_details,
    get_area_safety_advice as crimes_get_safety_advice,
)

@app.get("/api/areas/{area}/heatmap")
def api_area_heatmap_alias(area: str):
    return crimes_get_heatmap(area)

@app.get("/api/areas/{area}/details")
def api_area_details_alias(area: str):
    return crimes_get_area_details(area)

@app.get("/api/areas/{area}/safety-advice")
def api_area_safety_advice_alias(
    area: str,
    date: Optional[str] = Query(None),
    crime_type: Optional[str] = Query(None),
):
    return crimes_get_safety_advice(area, date, crime_type)

# Flat alias for emergency public call logging
from app.routes.emergency import log_emergency_call_public as emergency_call_public
from app.models.schemas import EmergencyCallRequest

@app.post("/api/emergency-call/public")
async def api_emergency_call_public_alias(call_data: EmergencyCallRequest):
    return await emergency_call_public(call_data)

# Aliases for user-specific endpoints expected by frontend
from typing import Optional
from fastapi import Depends
from datetime import datetime, timedelta
from app.dependencies import get_username_from_token

@app.get("/api/auth/me/alerts")
def api_me_alerts_alias(
    current_user: str = Depends(get_username_from_token),
    limit: Optional[int] = Query(50, description="Maximum number of alerts to return", ge=1, le=100),
    offset: Optional[int] = Query(0, description="Number of alerts to skip", ge=0),
    unread_only: Optional[bool] = Query(False, description="Return only unread alerts"),
    alert_type: Optional[str] = Query(None, description="Filter by alert type"),
    severity: Optional[str] = Query(None, description="Filter by severity")
):
    return get_user_alerts(current_user, limit, offset, unread_only, alert_type, severity)

@app.get("/api/auth/me/stats")
def api_me_stats_alias(
    current_user: Optional[str] = Depends(get_username_from_token),
    latitude: Optional[float] = Query(None),
    longitude: Optional[float] = Query(None),
    area: Optional[str] = Query(None),
    time_filter: Optional[str] = Query('12m')
):
    conn = None
    cursor = None
    try:
        # Determine time delta based on filter
        logger.info(f"📊 Stats requested: lat={latitude}, lon={longitude}, area='{area}', filter={time_filter}")
        days_delta = 365

        if time_filter == '7d':
            days_delta = 7
        elif time_filter == '30d':
            days_delta = 30
        elif time_filter == '12m' or time_filter == '1y':
            days_delta = 365
        elif time_filter == 'all':
            days_delta = None  # No time restriction - get ALL historical data

        # Build date filter SQL fragment - only add if days_delta is specified
        if days_delta:
            date_filter_sql = f"AND crime_date >= DATE_SUB(NOW(), INTERVAL {days_delta} DAY)"
        else:
            date_filter_sql = ""  # No date restriction for "All Time"

        logger.info(f"📊 Dashboard stats: time_filter={time_filter}, days_delta={days_delta}, area={area}, lat={latitude}, lng={longitude}")
        logger.info(f"📊 Date filter SQL: {date_filter_sql}") 

        conn = get_db_connection()
        if conn is None:
            raise RuntimeError("Database connection not available")

        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT id, home_area, home_latitude, home_longitude FROM users_info WHERE username = %s", (current_user,))
        user = cursor.fetchone()
        
        if not user:
            return {
                "safety_score": 0,
                "weekly_alerts": 0,
                "safe_routes": 0,
                "nearest_safe_zone": 0,
                "safe_zone_name": "N/A"
            }
        
        user = cast(Dict[str, Any], user)
        user_id = user['id']
        home_area = user['home_area']
        
        lat = latitude if latitude is not None else user['home_latitude']
        lon = longitude if longitude is not None else user['home_longitude']
        
        safety_score = 0.0
        safety_score_change = 0.0
        resolved_area = home_area or "Unknown"
        confidence = "very_high" 
        
        crime_counts = []
        time_stats = None
        current_stats: Optional[Dict[str, Any]] = None
        explicit_area = area.strip() if isinstance(area, str) and area.strip() else None

        weekly_alerts = 0
        weekly_alerts_change = 0
        recent_7d_crimes = 0
        recent_30d_crimes = 0
        previous_7d_crimes = 0
        top_crimes_list: list[dict[str, Any]] = []
        trend_labels: list[str] = []
        scope_radius_meters = 1500

        # 1. Use EXACT STRING SEARCH with normalization first - USER PREFERRED "Simple"
        if explicit_area:
            search_pattern = area_like_pattern(explicit_area)
            cursor.execute(f"""
                SELECT 
                    COUNT(*) as total_crimes,
                    SUM(CASE WHEN risk_level = 'High' THEN 1 ELSE 0 END) as high_risk_count,
                    SUM(CASE WHEN risk_level = 'Medium' THEN 1 ELSE 0 END) as medium_risk_count,
                    SUM(CASE WHEN risk_level = 'Low' THEN 1 ELSE 0 END) as low_risk_count,
                    SUM(CASE WHEN risk_level IS NULL OR risk_level = 'Unknown' THEN 1 ELSE 0 END) as unknown_risk_count,
                    COUNT(DISTINCT crime_type) as unique_crime_types
                FROM crimes
                WHERE area LIKE %s
                {date_filter_sql}
            """, (search_pattern,))
            current_stats = cursor.fetchone()
            confidence = "medium"
            resolved_area = explicit_area

        # Step B: Fallback to Radius (1.5km) only when no explicit area is provided.
        # This prevents mixing strict area selection with nearby-radius data.
        if not explicit_area and (not current_stats or current_stats.get("total_crimes", 0) == 0) and lat and lon:
            cursor.execute(f"""
                SELECT 
                    COUNT(*) as total_crimes,
                    SUM(CASE WHEN risk_level = 'High' THEN 1 ELSE 0 END) as high_risk_count,
                    SUM(CASE WHEN risk_level = 'Medium' THEN 1 ELSE 0 END) as medium_risk_count,
                    SUM(CASE WHEN risk_level = 'Low' THEN 1 ELSE 0 END) as low_risk_count,
                    SUM(CASE WHEN risk_level IS NULL OR risk_level = 'Unknown' THEN 1 ELSE 0 END) as unknown_risk_count,
                    COUNT(DISTINCT crime_type) as unique_crime_types
                FROM crimes 
                WHERE ST_Distance_Sphere(point(longitude, latitude), point(%s, %s)) <= {scope_radius_meters}
                {date_filter_sql}
            """, (lon, lat))
            current_stats = cursor.fetchone()
            confidence = "high"
            
            # Resolve name for display
            cursor.execute("SELECT area_name FROM area_coordinates ORDER BY ST_Distance_Sphere(point(longitude, latitude), point(%s, %s)) ASC LIMIT 1", (lon, lat))
            nearest_row = cursor.fetchone()
            if nearest_row:
                resolved_area = nearest_row['area_name']

        if not explicit_area and (not current_stats or current_stats.get("total_crimes", 0) == 0) and home_area:
            search_pattern = area_like_pattern(home_area)
            cursor.execute(f"""
                SELECT 
                    COUNT(*) as total_crimes,
                    SUM(CASE WHEN risk_level = 'High' THEN 1 ELSE 0 END) as high_risk_count,
                    SUM(CASE WHEN risk_level = 'Medium' THEN 1 ELSE 0 END) as medium_risk_count,
                    SUM(CASE WHEN risk_level = 'Low' THEN 1 ELSE 0 END) as low_risk_count,
                    SUM(CASE WHEN risk_level IS NULL OR risk_level = 'Unknown' THEN 1 ELSE 0 END) as unknown_risk_count,
                    COUNT(DISTINCT crime_type) as unique_crime_types
                FROM crimes
                WHERE area LIKE %s
                {date_filter_sql}
            """, (search_pattern,))
            current_stats = cursor.fetchone()
            confidence = "low"
            resolved_area = home_area

        # 2. CALCULATE SCORES AND BREAKDOWNS (ONLY IF WE FOUND DATA)
        zero_incident_period = current_stats is not None and current_stats.get("total_crimes", 0) == 0
        logger.info(f"🔍 Safety calculation: current_stats={current_stats is not None}, total_crimes={current_stats.get('total_crimes', 0) if current_stats else 'N/A'}, zero_incident_period={zero_incident_period}")
        if current_stats and current_stats.get("total_crimes", 0) > 0:
            safety_score = float(calculate_safety_score(current_stats, days_delta))
            
            # Previous Period (Comparison) - only if we have a time window
            if days_delta and (confidence == "medium" or confidence == "low") and resolved_area:
                search_pattern = area_like_pattern(resolved_area)
                cursor.execute(f"""
                    SELECT
                        COUNT(*) as total_crimes,
                        SUM(CASE WHEN risk_level = 'High' THEN 1 ELSE 0 END) as high_risk_count,
                        SUM(CASE WHEN risk_level = 'Medium' THEN 1 ELSE 0 END) as medium_risk_count,
                        SUM(CASE WHEN risk_level = 'Low' THEN 1 ELSE 0 END) as low_risk_count,
                        SUM(CASE WHEN risk_level IS NULL OR risk_level = 'Unknown' THEN 1 ELSE 0 END) as unknown_risk_count,
                        COUNT(DISTINCT crime_type) as unique_crime_types
                    FROM crimes
                    WHERE area LIKE %s
                    AND crime_date >= DATE_SUB(NOW(), INTERVAL {2 * days_delta} DAY)
                    AND crime_date < DATE_SUB(NOW(), INTERVAL {days_delta} DAY)
                """, (search_pattern,))
                prev_stats = cursor.fetchone()
                prev_score = float(calculate_safety_score(prev_stats, days_delta))
                safety_score_change = float(round(safety_score - prev_score, 1))
            elif days_delta and confidence == "high" and lat and lon:  # radius comparison
                cursor.execute(f"""
                    SELECT
                        COUNT(*) as total_crimes,
                        SUM(CASE WHEN risk_level = 'High' THEN 1 ELSE 0 END) as high_risk_count,
                        SUM(CASE WHEN risk_level = 'Medium' THEN 1 ELSE 0 END) as medium_risk_count,
                        SUM(CASE WHEN risk_level = 'Low' THEN 1 ELSE 0 END) as low_risk_count,
                        SUM(CASE WHEN risk_level IS NULL OR risk_level = 'Unknown' THEN 1 ELSE 0 END) as unknown_risk_count,
                        COUNT(DISTINCT crime_type) as unique_crime_types
                    FROM crimes
                    WHERE ST_Distance_Sphere(point(longitude, latitude), point(%s, %s)) <= {scope_radius_meters}
                    AND crime_date >= DATE_SUB(NOW(), INTERVAL {2 * days_delta} DAY)
                    AND crime_date < DATE_SUB(NOW(), INTERVAL {days_delta} DAY)
                """, (lon, lat))
                prev_stats = cursor.fetchone()
                prev_score = float(calculate_safety_score(prev_stats, days_delta))
                safety_score_change = float(round(safety_score - prev_score, 1))
            else:
                # No previous period comparison for "All Time" or insufficient data
                safety_score_change = 0.0
            
            # Breakdown Stats
            if (confidence == "medium" or confidence == "low") and resolved_area:
                search_pattern = area_like_pattern(resolved_area)
                cursor.execute(f"SELECT crime_type, COUNT(*) as count FROM crimes WHERE area LIKE %s {date_filter_sql} GROUP BY crime_type", (search_pattern,))
                crime_counts = cursor.fetchall()
                cursor.execute(f"SELECT SUM(CASE WHEN HOUR(crime_date) BETWEEN 6 AND 18 THEN 1 ELSE 0 END) as day_crimes, SUM(CASE WHEN HOUR(crime_date) NOT BETWEEN 6 AND 18 THEN 1 ELSE 0 END) as night_crimes FROM crimes WHERE area LIKE %s {date_filter_sql}", (search_pattern,))
                time_stats = cursor.fetchone()
            else: # Radius breakdown
                cursor.execute(f"SELECT crime_type, COUNT(*) as count FROM crimes WHERE ST_Distance_Sphere(point(longitude, latitude), point(%s, %s)) <= {scope_radius_meters} {date_filter_sql} GROUP BY crime_type", (lon, lat))
                crime_counts = cursor.fetchall()
                cursor.execute(f"SELECT SUM(CASE WHEN HOUR(crime_date) BETWEEN 6 AND 18 THEN 1 ELSE 0 END) as day_crimes, SUM(CASE WHEN HOUR(crime_date) NOT BETWEEN 6 AND 18 THEN 1 ELSE 0 END) as night_crimes FROM crimes WHERE ST_Distance_Sphere(point(longitude, latitude), point(%s, %s)) <= {scope_radius_meters} {date_filter_sql}", (lon, lat))
                time_stats = cursor.fetchone()
                time_stats = cursor.fetchone()
        elif zero_incident_period:
            # Area found but ZERO incidents in selected window — this is VERY SAFE
            # Use a high base score (95) minus a small urban penalty (5%), reflecting genuinely quiet area
            safety_score = 95.0
            logger.info(f"✅ Zero incident period detected for {resolved_area} (time_filter={time_filter}) → safety_score set to 95.0")
            safety_score_change = 0.0
            crime_counts = []
            time_stats = None
        else: # NO DATA FOUND AT ALL (null stats)
            safety_score = 95.0  # Unknown area assumed safe until proven otherwise
            logger.info(f"✅ No data found → safety_score set to 95.0 (unknown area)")
            safety_score_change = 0.0
            crime_counts = []
            time_stats = None

        day_crimes = 0
        night_crimes = 0
        if time_stats:
            time_stats_dict = cast(Dict[str, Any], time_stats)
            day_crimes = time_stats_dict.get('day_crimes', 0) or 0
            night_crimes = time_stats_dict.get('night_crimes', 0) or 0
        breakdown = calculate_breakdown(crime_counts or [], day_crimes, night_crimes)

        # 2. Alerts for selected period + fixed windows (7d / 30d)
        weekly_alerts = 0
        weekly_alerts_change = 0
        if (confidence == "medium" or confidence == "low") and resolved_area:
            search_pattern = area_like_pattern(resolved_area)
            cursor.execute(f"SELECT COUNT(*) as count FROM crimes WHERE area LIKE %s {date_filter_sql}", (search_pattern,))
            weekly_alerts = cursor.fetchone()['count']

            # Previous period comparison - only if days_delta is specified
            if days_delta:
                cursor.execute(f"SELECT COUNT(*) as count FROM crimes WHERE area LIKE %s AND crime_date >= DATE_SUB(NOW(), INTERVAL {2*days_delta} DAY) AND crime_date < DATE_SUB(NOW(), INTERVAL {days_delta} DAY)", (search_pattern,))
                prev_alerts = cursor.fetchone()['count']
                weekly_alerts_change = weekly_alerts - prev_alerts
            else:
                # For "All Time", no previous period comparison
                weekly_alerts_change = 0

            cursor.execute("SELECT COUNT(*) as count FROM crimes WHERE area LIKE %s AND crime_date >= DATE_SUB(NOW(), INTERVAL 7 DAY)", (search_pattern,))
            recent_7d_crimes = cursor.fetchone()['count']
            cursor.execute("SELECT COUNT(*) as count FROM crimes WHERE area LIKE %s AND crime_date >= DATE_SUB(NOW(), INTERVAL 14 DAY) AND crime_date < DATE_SUB(NOW(), INTERVAL 7 DAY)", (search_pattern,))
            previous_7d_crimes = cursor.fetchone()['count']
            cursor.execute("SELECT COUNT(*) as count FROM crimes WHERE area LIKE %s AND crime_date >= DATE_SUB(NOW(), INTERVAL 30 DAY)", (search_pattern,))
            recent_30d_crimes = cursor.fetchone()['count']

            cursor.execute(f"""
                SELECT crime_type, COUNT(*) as count
                FROM crimes
                WHERE area LIKE %s {date_filter_sql}
                GROUP BY crime_type
                ORDER BY count DESC
                LIMIT 10
            """, (search_pattern,))
            top_rows = cursor.fetchall() or []
        elif lat and lon:
            cursor.execute(f"SELECT COUNT(*) as count FROM crimes WHERE ST_Distance_Sphere(point(longitude, latitude), point(%s, %s)) <= {scope_radius_meters} {date_filter_sql}", (lon, lat))
            weekly_alerts = cursor.fetchone()['count']

            # Previous period comparison - only if days_delta is specified
            if days_delta:
                cursor.execute(f"SELECT COUNT(*) as count FROM crimes WHERE ST_Distance_Sphere(point(longitude, latitude), point(%s, %s)) <= {scope_radius_meters} AND crime_date >= DATE_SUB(NOW(), INTERVAL {2*days_delta} DAY) AND crime_date < DATE_SUB(NOW(), INTERVAL {days_delta} DAY)", (lon, lat))
                prev_alerts = cursor.fetchone()['count']
                weekly_alerts_change = weekly_alerts - prev_alerts
            else:
                # For "All Time", no previous period comparison
                weekly_alerts_change = 0

            cursor.execute(f"SELECT COUNT(*) as count FROM crimes WHERE ST_Distance_Sphere(point(longitude, latitude), point(%s, %s)) <= {scope_radius_meters} AND crime_date >= DATE_SUB(NOW(), INTERVAL 7 DAY)", (lon, lat))
            recent_7d_crimes = cursor.fetchone()['count']
            cursor.execute(f"SELECT COUNT(*) as count FROM crimes WHERE ST_Distance_Sphere(point(longitude, latitude), point(%s, %s)) <= {scope_radius_meters} AND crime_date >= DATE_SUB(NOW(), INTERVAL 14 DAY) AND crime_date < DATE_SUB(NOW(), INTERVAL 7 DAY)", (lon, lat))
            previous_7d_crimes = cursor.fetchone()['count']
            cursor.execute(f"SELECT COUNT(*) as count FROM crimes WHERE ST_Distance_Sphere(point(longitude, latitude), point(%s, %s)) <= {scope_radius_meters} AND crime_date >= DATE_SUB(NOW(), INTERVAL 30 DAY)", (lon, lat))
            recent_30d_crimes = cursor.fetchone()['count']

            cursor.execute(f"""
                SELECT crime_type, COUNT(*) as count
                FROM crimes
                WHERE ST_Distance_Sphere(point(longitude, latitude), point(%s, %s)) <= {scope_radius_meters}
                {date_filter_sql}
                GROUP BY crime_type
                ORDER BY count DESC
                LIMIT 10
            """, (lon, lat))
            top_rows = cursor.fetchall() or []
        elif home_area:
            search_pattern = area_like_pattern(home_area)
            cursor.execute(f"SELECT COUNT(*) as count FROM crimes WHERE area LIKE %s {date_filter_sql}", (search_pattern,))
            weekly_alerts = cursor.fetchone()['count']
            if days_delta:
                cursor.execute(f"SELECT COUNT(*) as count FROM crimes WHERE area LIKE %s AND crime_date >= DATE_SUB(NOW(), INTERVAL {2*days_delta} DAY) AND crime_date < DATE_SUB(NOW(), INTERVAL {days_delta} DAY)", (search_pattern,))
                prev_alerts = cursor.fetchone()['count']
                weekly_alerts_change = weekly_alerts - prev_alerts
            else:
                weekly_alerts_change = 0

            cursor.execute("SELECT COUNT(*) as count FROM crimes WHERE area LIKE %s AND crime_date >= DATE_SUB(NOW(), INTERVAL 7 DAY)", (search_pattern,))
            recent_7d_crimes = cursor.fetchone()['count']
            cursor.execute("SELECT COUNT(*) as count FROM crimes WHERE area LIKE %s AND crime_date >= DATE_SUB(NOW(), INTERVAL 14 DAY) AND crime_date < DATE_SUB(NOW(), INTERVAL 7 DAY)", (search_pattern,))
            previous_7d_crimes = cursor.fetchone()['count']
            cursor.execute("SELECT COUNT(*) as count FROM crimes WHERE area LIKE %s AND crime_date >= DATE_SUB(NOW(), INTERVAL 30 DAY)", (search_pattern,))
            recent_30d_crimes = cursor.fetchone()['count']

            cursor.execute(f"""
                SELECT crime_type, COUNT(*) as count
                FROM crimes
                WHERE area LIKE %s {date_filter_sql}
                GROUP BY crime_type
                ORDER BY count DESC
                LIMIT 10
            """, (search_pattern,))
            top_rows = cursor.fetchall() or []
        else:
            top_rows = []

        from app.ocr.ppc_sections import get_crime_name

        def _normalize_crime_label(raw_value: Any) -> str:
            value = str(raw_value or '').strip()
            if not value:
                return 'unknown'
            return re.sub(r'\s+', ' ', value).lower()

        def _is_unknown_label(raw_value: Any) -> bool:
            normalized = _normalize_crime_label(raw_value)
            return normalized in {
                'unknown',
                'unknown crime',
                'unknown incident',
                'n/a',
                'na',
                '-',
                'nil'
            }

        # Consolidate duplicate labels caused by case/whitespace variants.
        consolidated_top: Dict[str, Dict[str, Any]] = {}
        for row in top_rows:
            count = int(row.get('count') or 0)
            if count <= 0:
                continue
            original_label = str(row.get('crime_type') or '').strip() or 'Unknown'
            normalized_label = _normalize_crime_label(original_label)
            if normalized_label not in consolidated_top:
                consolidated_top[normalized_label] = {
                    'crime_type': original_label,
                    'count': count,
                }
            else:
                consolidated_top[normalized_label]['count'] += count

        consolidated_rows = sorted(consolidated_top.values(), key=lambda r: int(r.get('count') or 0), reverse=True)
        known_rows = [r for r in consolidated_rows if not _is_unknown_label(r.get('crime_type'))]
        selected_rows = known_rows if known_rows else consolidated_rows

        top_total = max(1, sum(int(row.get('count') or 0) for row in selected_rows))
        for row in selected_rows[:10]:
            c = int(row.get('count') or 0)
            crime_type = str(row.get('crime_type') or 'Unknown').strip() or 'Unknown'
            display_name, law_type = get_crime_name(crime_type)

            # Keep backend-provided mapping, but never replace a non-empty raw value
            # with a generic "Unknown" label.
            if str(display_name or '').strip().lower() == 'unknown' and not _is_unknown_label(crime_type):
                display_name = crime_type

            top_crimes_list.append({
                "crime_type": crime_type,
                "display_name": display_name,
                "law_type": law_type,
                "count": c,
                "percentage": int(round((c / top_total) * 100))
            })

        # 3. Safe Zone
        nearest_safe_zone = 0
        safe_zone_name = "N/A"
        if lat is not None and lon is not None:
            try:
                cursor.execute(
                    """
                    SELECT COUNT(*) AS c
                    FROM information_schema.tables
                    WHERE table_schema = DATABASE() AND table_name = 'locations'
                    """
                )
                _locations_exists = int((cursor.fetchone() or {}).get('c', 0) or 0) > 0
                if _locations_exists:
                    cursor.execute("""
                        SELECT name, ST_Distance_Sphere(point(longitude, latitude), point(%s, %s)) / 1000 as dist
                        FROM locations WHERE location_type IN ('police_station', 'hospital')
                        ORDER BY dist ASC LIMIT 1
                    """, (lon, lat))
                    sz = cursor.fetchone()
                    if sz:
                        nearest_safe_zone = round(sz['dist'], 1)
                        safe_zone_name = sz['name']
                    else:
                        # Fallback if no locations in DB
                        safe_zone_name = "No secure zones in radius"
                else:
                    safe_zone_name = "N/A"
            except Exception as loc_err:
                logger.warning(f"Failed to fetch nearest safe zone: {loc_err}")
                safe_zone_name = "N/A"


        # 4. Safe Routes
        cursor.execute("SELECT COUNT(*) as c FROM user_activity_logs WHERE user_id = %s AND activity_type = 'route_analysis' AND created_at >= DATE_SUB(NOW(), INTERVAL 30 DAY)", (user_id,))
        safe_routes = cursor.fetchone()['c']

        # 5. Trend
        trend_data = []
        if time_filter in ('12m', '1y', 'all'):
            def _shift_months(base_dt: datetime, delta_months: int) -> datetime:
                month_index = (base_dt.month - 1) + delta_months
                year = base_dt.year + (month_index // 12)
                month = (month_index % 12) + 1
                return base_dt.replace(year=year, month=month, day=1)

            if (confidence == "medium" or confidence == "low") and resolved_area:
                search_pattern = area_like_pattern(resolved_area)
                cursor.execute("""
                    SELECT DATE_FORMAT(crime_date, '%Y-%m') as bucket, COUNT(*) as count
                    FROM crimes
                    WHERE area LIKE %s
                      AND crime_date >= DATE_SUB(NOW(), INTERVAL 12 MONTH)
                    GROUP BY DATE_FORMAT(crime_date, '%Y-%m')
                    ORDER BY bucket ASC
                """, (search_pattern,))
            elif lat and lon:
                cursor.execute(f"""
                    SELECT DATE_FORMAT(crime_date, '%Y-%m') as bucket, COUNT(*) as count
                    FROM crimes
                    WHERE ST_Distance_Sphere(point(longitude, latitude), point(%s, %s)) <= {scope_radius_meters}
                      AND crime_date >= DATE_SUB(NOW(), INTERVAL 12 MONTH)
                    GROUP BY DATE_FORMAT(crime_date, '%Y-%m')
                    ORDER BY bucket ASC
                """, (lon, lat))
            elif home_area:
                search_pattern = area_like_pattern(home_area)
                cursor.execute("""
                    SELECT DATE_FORMAT(crime_date, '%Y-%m') as bucket, COUNT(*) as count
                    FROM crimes
                    WHERE area LIKE %s
                      AND crime_date >= DATE_SUB(NOW(), INTERVAL 12 MONTH)
                    GROUP BY DATE_FORMAT(crime_date, '%Y-%m')
                    ORDER BY bucket ASC
                """, (search_pattern,))

            trows = cursor.fetchall() or []
            tmap = {str(r['bucket']): int(r['count'] or 0) for r in trows}
            month_base = datetime.now().replace(day=1)
            for i in range(11, -1, -1):
                month_dt = _shift_months(month_base, -i)
                month_key = month_dt.strftime('%Y-%m')
                trend_data.append(tmap.get(month_key, 0))
                trend_labels.append(month_dt.strftime('%b'))
        else:
            # Handle trend calculation for different time filters
            if time_filter == 'all':
                trend_days = 365  # Show full year trend for "All Time"
            elif time_filter == '12m':
                trend_days = 365
            elif time_filter == '30d':
                trend_days = 30
            else:  # 7d
                trend_days = 7

            if (confidence == "medium" or confidence == "low") and resolved_area:
                search_pattern = area_like_pattern(resolved_area)
                if time_filter == 'all':
                    # For "All Time", get trend data across entire history
                    cursor.execute("SELECT DATE(crime_date) as d, COUNT(*) as count FROM crimes WHERE area LIKE %s GROUP BY DATE(crime_date) ORDER BY d ASC", (search_pattern,))
                else:
                    cursor.execute(f"SELECT DATE(crime_date) as d, COUNT(*) as count FROM crimes WHERE area LIKE %s AND crime_date >= DATE_SUB(NOW(), INTERVAL {trend_days} DAY) GROUP BY DATE(crime_date) ORDER BY d ASC", (search_pattern,))
            elif lat and lon:
                if time_filter == 'all':
                    cursor.execute("SELECT DATE(crime_date) as d, COUNT(*) as count FROM crimes WHERE ST_Distance_Sphere(point(longitude, latitude), point(%s, %s)) <= {scope_radius_meters} GROUP BY DATE(crime_date) ORDER BY d ASC", (lon, lat))
                else:
                    cursor.execute(f"SELECT DATE(crime_date) as d, COUNT(*) as count FROM crimes WHERE ST_Distance_Sphere(point(longitude, latitude), point(%s, %s)) <= {scope_radius_meters} AND crime_date >= DATE_SUB(NOW(), INTERVAL {trend_days} DAY) GROUP BY DATE(crime_date) ORDER BY d ASC", (lon, lat))
            elif home_area:
                search_pattern = area_like_pattern(home_area)
                if time_filter == 'all':
                    cursor.execute("SELECT DATE(crime_date) as d, COUNT(*) as count FROM crimes WHERE area LIKE %s GROUP BY DATE(crime_date) ORDER BY d ASC", (search_pattern,))
                else:
                    cursor.execute(f"SELECT DATE(crime_date) as d, COUNT(*) as count FROM crimes WHERE area LIKE %s AND crime_date >= DATE_SUB(NOW(), INTERVAL {trend_days} DAY) GROUP BY DATE(crime_date) ORDER BY d ASC", (search_pattern,))

            trows = cursor.fetchall() or []
            tmap = {str(r['d']): int(r['count'] or 0) for r in trows}

            # Build trend data based on filter type
            if time_filter == 'all':
                # For "All Time", show recent trend (last 30 days) from available data
                for i in range(29, -1, -1):
                    dt = datetime.now() - timedelta(days=i)
                    ds = str(dt.date())
                    trend_data.append(tmap.get(ds, 0))
                    trend_labels.append(dt.strftime('%d %b'))
            else:
                # For specific time periods, show the full period
                for i in range(trend_days - 1, -1, -1):
                    dt = datetime.now() - timedelta(days=i)
                    ds = str(dt.date())
                    trend_data.append(tmap.get(ds, 0))
                    trend_labels.append(dt.strftime('%d %b') if trend_days > 7 else dt.strftime('%a'))

        # 6. Sub-areas
        sub_areas = []
        sub_rows = []
        if explicit_area:
            search_pattern = area_like_pattern(explicit_area)
            cursor.execute(f"""
                SELECT area_translit as name, COUNT(*) as total,
                COALESCE(SUM(CASE WHEN risk_level = 'High' THEN 1 ELSE 0 END), 0) as high,
                COALESCE(SUM(CASE WHEN risk_level = 'Medium' THEN 1 ELSE 0 END), 0) as medium
                FROM crimes WHERE area LIKE %s AND area_translit IS NOT NULL AND area_translit != ''
                {date_filter_sql} GROUP BY area_translit ORDER BY total DESC LIMIT 10
            """, (search_pattern,))

            sub_rows = cursor.fetchall() or []
        elif lat and lon:
            cursor.execute(f"""
                SELECT area_translit as name, COUNT(*) as total,
                COALESCE(SUM(CASE WHEN risk_level = 'High' THEN 1 ELSE 0 END), 0) as high,
                COALESCE(SUM(CASE WHEN risk_level = 'Medium' THEN 1 ELSE 0 END), 0) as medium
                FROM crimes WHERE ST_Distance_Sphere(point(longitude, latitude), point(%s, %s)) <= {scope_radius_meters}
                AND area_translit IS NOT NULL AND area_translit != ''
                {date_filter_sql} GROUP BY area_translit ORDER BY total DESC LIMIT 10
            """, (lon, lat))
            sub_rows = cursor.fetchall() or []
        elif home_area:
            search_pattern = area_like_pattern(home_area)
            cursor.execute(f"""
                SELECT area_translit as name, COUNT(*) as total,
                COALESCE(SUM(CASE WHEN risk_level = 'High' THEN 1 ELSE 0 END), 0) as high,
                COALESCE(SUM(CASE WHEN risk_level = 'Medium' THEN 1 ELSE 0 END), 0) as medium
                FROM crimes WHERE area LIKE %s AND area_translit IS NOT NULL AND area_translit != ''
                {date_filter_sql} GROUP BY area_translit ORDER BY total DESC LIMIT 10
            """, (search_pattern,))
            sub_rows = cursor.fetchall() or []

        for row in sub_rows:
            s_score = calculate_safety_score({
                "total_crimes": row['total'],
                "high_risk_count": row['high'],
                "medium_risk_count": row['medium'],
                "low_risk_count": row['total'] - row['high'] - row['medium'],
                "unknown_risk_count": 0
            }, days_delta)
            sub_areas.append({
                "name": row['name'],
                "total": row['total'],
                "safety_score": float(round(float(s_score), 1)),
                "risk_level": get_risk_level(s_score)
            })

        total_records_mapped = current_stats.get('total_crimes', 0) if current_stats else 0
        sync_msg = (
            f"Intelligence sync: {total_records_mapped} historical records mapped"
            if total_records_mapped > 0
            else "Intelligence sync: No incidents in selected window — area quiet"
        )
        system_status = [
            {"type": "info", "message": f"Security perimeter established for {resolved_area}", "time": datetime.now().isoformat()},
            {"type": "success", "message": sync_msg, "time": (datetime.now() - timedelta(minutes=2)).isoformat()},
            {"type": "info", "message": f"Block Analysis: {len(sub_areas)} micro-sectors verified in current radius", "time": (datetime.now() - timedelta(minutes=5)).isoformat()}
        ]
        
        if weekly_alerts > 0:
            change_str = f"({'+' if weekly_alerts_change > 0 else ''}{weekly_alerts_change})" if weekly_alerts_change != 0 else ""
            msg = f"Operational Alert: {weekly_alerts} incidents detected {change_str} in last {time_filter}"
            system_status.append({"type": "warning", "message": msg, "time": (datetime.now() - timedelta(minutes=8)).isoformat()})
        else:
            system_status.append({"type": "success", "message": "Zero critical incidents detected in tracking window", "time": (datetime.now() - timedelta(minutes=12)).isoformat()})

        # Build risk_summary for the response. Use a safe-zone score when zero incidents were found
        # in the selected period to avoid misleading 0% safe scores.
        if zero_incident_period:
            # Override: genuinely quiet period — show as Safe with high confidence
            risk_summary = {
                "risk_score": 5.0,
                "safety_score": 95.0,
                "risk_level": "Low",
                "data_confidence": confidence,
                "score_components": {}
            }
        else:
            risk_summary = calculate_unified_risk_summary(current_stats, days_delta)

        logger.info(f"📤 FINAL RESPONSE: safety_score={safety_score}, risk_level={risk_summary.get('risk_level')}, total_crimes={int((current_stats.get('total_crimes') or 0)) if current_stats else 0}, area={resolved_area}, time_filter={time_filter}")

        return {
            "safety_score": safety_score,
            "risk_score": risk_summary.get("risk_score", round(100.0 - safety_score, 1)),
            "safety_score_change": safety_score_change,
            "risk_level": risk_summary.get("risk_level", get_risk_level(safety_score)),
            "weekly_alerts": weekly_alerts,
            "weekly_alerts_change": weekly_alerts_change,
            "recent_7d_crimes": recent_7d_crimes,
            "recent_30d_crimes": recent_30d_crimes,
            "previous_7d_crimes": previous_7d_crimes,
            "safe_routes": safe_routes,
            "nearest_safe_zone": nearest_safe_zone,
            "safe_zone_name": safe_zone_name,
            "breakdown": breakdown,
            "total_crimes": int((current_stats.get("total_crimes") or 0)) if current_stats else 0,
            "high_risk_crimes": int((current_stats.get("high_risk_count") or 0)) if current_stats else 0,
            "medium_risk_crimes": int((current_stats.get("medium_risk_count") or 0)) if current_stats else 0,
            "unique_crime_types": int((current_stats.get("unique_crime_types") or 0)) if current_stats else 0,
            "top_crimes_list": top_crimes_list,
            "resolved_area": resolved_area,
            "confidence": confidence,
            "data_confidence": risk_summary.get("data_confidence", "low"),
            "score_components": risk_summary.get("score_components", {}),
            "trend_data": trend_data,
            "trend_labels": trend_labels,
            "sub_areas": sub_areas,
            "system_status": system_status,
            "time_filter": time_filter
        }
    except Exception as e:
        logger.error(f"Error in stats: {e}")
        try:
            with open("error_log.txt", "a") as f:
                import traceback
                f.write(f"Error in stats: {str(e)}\n")
                f.write(traceback.format_exc())
        except:
            pass
        return {
            "safety_score": 50.0,
            "risk_score": 50.0,
            "safety_score_change": 0.0,
            "risk_level": "Moderate",
            "weekly_alerts": 0,
            "weekly_alerts_change": 0,
            "recent_7d_crimes": 0,
            "recent_30d_crimes": 0,
            "previous_7d_crimes": 0,
            "safe_routes": 0,
            "nearest_safe_zone": 0,
            "safe_zone_name": "N/A",
            "breakdown": {"violent": 0, "property": 0, "personal": 0, "day": 0, "night": 0},
            "total_crimes": 0,
            "high_risk_crimes": 0,
            "top_crimes_list": [],
            "resolved_area": "Unknown",
            "confidence": "none",
            "data_confidence": "none",
            "trend_data": [],
            "trend_labels": [],
            "time_filter": time_filter
        }
    finally:
        if cursor is not None:
            cursor.close()
        if conn is not None:
            conn.close()


@app.get("/api/auth/me/activity")
def api_me_activity_alias(current_user: Optional[str] = Depends(get_username_from_token)):
    return {"activity": []}

# Mount static files for profile photos
app.mount("/profile_photos", StaticFiles(directory=os.path.join(os.path.dirname(__file__), "app", "profile_photos")), name="profile_photos")

# Add background task scheduler
scheduler = BackgroundScheduler()
scheduler.start()

# Email configuration for alerts
ALERT_EMAIL_CONFIG = {
    'smtp_server': 'smtp.gmail.com',
    'smtp_port': 587,
    'smtp_username': os.getenv('ALERTS_EMAIL_USERNAME', 'safevision.alerts@gmail.com'),
    'smtp_password': os.getenv('ALERTS_EMAIL_PASSWORD', '')
}

SAFE_AREA_ALERT_CONFIG = {
    'min_safety_score': int(os.getenv('SAFE_AREA_MIN_SCORE', '70')),
    'send_safe_alerts': os.getenv('SEND_SAFE_ALERTS', 'True').lower() == 'true',
    'cooldown_minutes': int(os.getenv('SAFE_ALERT_COOLDOWN', '60')),
}

# Initialize the alert notification system with VAPID keys
alert_notification_system = AlertNotificationSystem(
    ALERT_EMAIL_CONFIG,
    VAPID_PUBLIC_KEY,  # Using the keys defined above
    VAPID_PRIVATE_KEY  # Using the keys defined above
)

# Basic routes that don't fit in other modules
@app.get("/")
def root(request: Request):
    logger.info(f"Request received: {request.method} {request.url.path}")
    return {"message": "Welcome to SafeVision API. Go to /api/crimes"}

@app.get("/welcome")
def welcome(request: Request):
    logger.info(f"Request received: {request.method} {request.url.path}")
    return {"message": "Welcome to the SafeVision API Service!"}

@app.get("/api/welcome")
def api_welcome(request: Request):
    logger.info(f"Request received: {request.method} {request.url.path}")
    return {"message": "Welcome to the SafeVision API Service!"}

@app.get("/health")
def health_check():
    """Health check endpoint for API connectivity testing"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "SafeVision API"
    }

@app.get("/test-db")
def test_db():
    """Test database connection"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        return {"database": "connected", "result": result}
    except Error as e:
        logger.error(f"Database connection error: {e}")
        return {"database": "error", "message": str(e)}

# Password reset endpoints
@app.post("/auth/forgot-password")
async def api_forgot_password(request: ForgotPasswordRequest, background_tasks: BackgroundTasks):
    return await forgot_password(request, background_tasks)

@app.post("/auth/reset-password")
async def api_reset_password(request: ResetPasswordRequest, background_tasks: BackgroundTasks):
    return await reset_password(request, background_tasks)

# Location endpoints
@app.post("/api/get-coordinates")
def get_coordinates_endpoint(request: LocationRequest):
    """Get coordinates for an area name"""
    coords = get_coordinates(request.area)

    if not coords:
        raise HTTPException(status_code=404, detail="Could not find coordinates for this area")

    lat, lon = coords

    # Validate coordinates are within Pakistan
    if not (23.0 <= lat <= 37.0 and 60.0 <= lon <= 78.0):
        raise HTTPException(
            status_code=400,
            detail="Coordinates found are outside Pakistan boundaries. Please verify the area name."
        )

    return LocationResponse(
        area=request.area,
        latitude=lat,
        longitude=lon,
        source="api"
    )

@app.get("/api/areas/{area}/safety-score")
def get_area_safety_score(
    area: str,
    lookback_days: int = Query(3650, ge=30, le=3650, description="Look-back window for scoring"),
):
    """Calculate area safety score using crimes within a configurable look-back window."""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        # Create a search pattern for flexible matching
        # If area is "Model Town", pattern becomes "%Model Town%"
        search_pattern = f"%{area.strip()}%"
        
        logger.info(
            "🔍 Calculating safety score for area='%s' pattern='%s' lookback_days=%s",
            area,
            search_pattern,
            lookback_days,
        )

        # Get crime statistics for the area with proper risk level counting
        # Changed = to LIKE for flexible matching
        cursor.execute("""
            SELECT 
                COUNT(*) as total_crimes,
                SUM(CASE WHEN risk_level = 'High' THEN 1 ELSE 0 END) as high_risk_count,
                SUM(CASE WHEN risk_level = 'Medium' THEN 1 ELSE 0 END) as medium_risk_count,
                SUM(CASE WHEN risk_level = 'Low' THEN 1 ELSE 0 END) as low_risk_count,
                SUM(CASE WHEN risk_level IS NULL OR risk_level = 'Unknown' THEN 1 ELSE 0 END) as unknown_risk_count,
                COUNT(DISTINCT crime_type) as unique_crime_types,
                MIN(crime_date) as first_incident,
                MAX(crime_date) as last_incident
                        FROM crimes
                        WHERE area LIKE %s
                            AND crime_date >= DATE_SUB(NOW(), INTERVAL %s DAY)
                """, (search_pattern, lookback_days))
        
        stats = cast(Dict[str, Any], cursor.fetchone())
        
        if not stats or stats["total_crimes"] == 0:
            logger.warning(f"⚠️ No crimes found for area: '{area}' (Pattern: '{search_pattern}')")
            return {
                "area": area,
                "safety_score": 100,
                "risk_level": "Very Safe",
                "message": f"No crime data available in the last {lookback_days} days for this area",
                "confidence": "low",
                "analysis_window_days": lookback_days,
            }
            
        logger.info(f"✅ Found {stats['total_crimes']} crimes for area: '{area}'")

        total_crimes = stats["total_crimes"]
        high_risk_count = stats["high_risk_count"] or 0
        medium_risk_count = stats["medium_risk_count"] or 0
        low_risk_count = stats["low_risk_count"] or 0
        unknown_risk_count = stats["unknown_risk_count"] or 0
        
        # Keep this endpoint aligned with the same observation window used in the SQL filter.
        risk_summary = calculate_unified_risk_summary(stats, lookback_days)
        safety_score = float(risk_summary["safety_score"])
        risk_level = str(risk_summary["risk_level"])
        
        # Color mapping for frontend based on standardized risk level
        color_map = {
            "Very Safe": "green",
            "Generally Safe": "blue",
            "Moderate Risk": "orange",
            "High Risk": "red",
            "Very High Risk": "darkred"
        }
        color = color_map.get(risk_level, "gray")
        
        # Calculate confidence based on data volume and quality
        data_quality = 1.0
        if unknown_risk_count > total_crimes * 0.5:  # More than 50% unknown risk
            data_quality = 0.5
        elif unknown_risk_count > total_crimes * 0.2:  # More than 20% unknown risk
            data_quality = 0.8
            
        if total_crimes > 20:
            confidence = "high"
        elif total_crimes > 5:
            confidence = "medium"
        else:
            confidence = "low"
            
        if data_quality < 0.7:
            confidence = "low"
        
        return {
            "area": area,
            "safety_score": safety_score,
            "risk_score": risk_summary["risk_score"],
            "risk_level": risk_level,
            "color": color,
            "data_confidence": risk_summary["data_confidence"],
            "score_components": risk_summary["score_components"],
            "crime_statistics": {
                "total_crimes": total_crimes,
                "high_risk_crimes": high_risk_count,
                "medium_risk_crimes": medium_risk_count,
                "low_risk_crimes": low_risk_count,
                "unknown_risk_crimes": unknown_risk_count,
                "unique_crime_types": stats["unique_crime_types"],
                "data_period": {
                    "first_incident": str(stats["first_incident"]),
                    "last_incident": str(stats["last_incident"])
                }
            },
            "confidence": confidence,
            "data_quality": data_quality,
            "analysis_window_days": lookback_days,
            "factors_considered": [
                "Total crime count",
                "Crime severity distribution", 
                "Variety of crime types",
                "Historical data coverage",
                "Data recency",
                "Risk level completeness"
            ]
        }

    except Exception as e:
        logger.error(f"Database error calculating safety score for {area}: {e}")
        raise HTTPException(status_code=500, detail="Failed to calculate safety score")
    finally:
        cursor.close()
        conn.close()
        
@app.get("/api/areas/safety-scores")
def get_multiple_area_safety_scores(areas: List[str] = Query(...)):
    """Get safety scores for multiple areas at once"""
    results = {}
    
    for area in areas:
        try:
            # Reuse the single area function
            score_data = get_area_safety_score(area)
            results[area] = score_data
        except Exception as e:
            logger.error(f"Error getting safety score for {area}: {e}")
            results[area] = {
                "area": area,
                "safety_score": None,
                "risk_level": "Unknown",
                "error": str(e)
            }
    
    return {"safety_scores": results}

# Debug endpoint
@app.get("/debug/coordinates/{area}")
def debug_coordinates(area: str):
    """Debug endpoint to check coordinate fetching for an area"""
    try:
        logger.info(f"🔍 Debug: Fetching coordinates for area: {area}")
        coords = get_coordinates(area)
        
        if coords:
            lat, lon = coords
            return {
                "area": area,
                "coordinates_found": True,
                "latitude": lat,
                "longitude": lon,
                "message": "Coordinates successfully fetched"
            }
        else:
            return {
                "area": area,
                "coordinates_found": False,
                "latitude": None,
                "longitude": None,
                "message": "No coordinates found for this area"
            }
    except Exception as e:
        logger.error(f"❌ Debug coordinate error: {e}")
        return {
            "area": area,
            "coordinates_found": False,
            "latitude": None,
            "longitude": None,
            "error": str(e)
        }

# Monitoring functions (these would typically be in a services file)

def monitor_saved_locations_job():
    """Synchronous wrapper for the async function"""
    try:
        asyncio.run(monitor_saved_locations())
    except Exception as e:
        logger.error(f"Error in monitor_saved_locations_job: {e}")

def weekly_safety_report_job():
    """Synchronous wrapper for the weekly report dispatcher"""
    try:
        logger.info("🕒 Triggering scheduled weekly safety reports...")
        asyncio.run(dispatch_weekly_safety_reports())
    except Exception as e:
        logger.error(f"Error in weekly_safety_report_job: {e}")

def start_background_monitoring():
    """Start background monitoring tasks"""
    try:
        # Load operational scheduler settings (with safe fallbacks)
        try:
            from app.routes.admin import get_setting, SYSTEM_SETTINGS_DEFAULTS

            def _default_str(key: str) -> str:
                return str(SYSTEM_SETTINGS_DEFAULTS.get(key, {}).get("value", ""))

            def _setting_int(key: str, min_value: int, max_value: int) -> int:
                raw = get_setting(key)
                if raw is None or str(raw).strip() == "":
                    raw = _default_str(key)
                return max(min_value, min(max_value, int(raw)))

            monitor_interval = _setting_int("monitor_saved_locations_interval_minutes", 1, 60)
            poll_interval = _setting_int("incident_poll_interval_minutes", 1, 60)
            monitor_max_instances = _setting_int("monitor_job_max_instances", 1, 5)
            poll_max_instances = _setting_int("incident_poll_job_max_instances", 1, 5)

            weekly_enabled_raw = get_setting("weekly_reports_enabled")
            if weekly_enabled_raw is None:
                weekly_enabled_raw = _default_str("weekly_reports_enabled")
            weekly_enabled = str(weekly_enabled_raw).lower() == "true"

            weekly_day_raw = get_setting("weekly_reports_day_of_week")
            weekly_day = str(weekly_day_raw if weekly_day_raw else _default_str("weekly_reports_day_of_week")).strip().lower()
            weekly_hour = _setting_int("weekly_reports_hour", 0, 23)
            weekly_minute = _setting_int("weekly_reports_minute", 0, 59)

            weekly_timezone_raw = get_setting("weekly_reports_timezone")
            weekly_timezone = str(weekly_timezone_raw if weekly_timezone_raw else _default_str("weekly_reports_timezone")).strip()
        except Exception:
            monitor_interval = 1
            poll_interval = 1
            monitor_max_instances = 1
            poll_max_instances = 1
            weekly_enabled = True
            weekly_day = 'sun'
            weekly_hour = 17
            weekly_minute = 5
            weekly_timezone = 'Asia/Karachi'

        # Remove any existing jobs to avoid duplicates
        try:
            scheduler.remove_job('monitor_saved_locations')
        except Exception:
            pass
        try:
            scheduler.remove_job('weekly_safety_reports')
        except Exception:
            pass
        
        # Use the synchronous wrapper for APScheduler
        scheduler.add_job(
            monitor_saved_locations_job,
            trigger=IntervalTrigger(minutes=monitor_interval),
            id='monitor_saved_locations',
            name='Monitor saved locations for risk alerts',
            replace_existing=True,
            max_instances=monitor_max_instances
        )
        
        # Add weekly report job (Sundays at 6 PM)
        # scheduler.add_job(
        #     weekly_safety_report_job,
        #     trigger='cron',
        #     day_of_week='sun',
        #     hour=18,
        #     minute=0,
        #     id='weekly_safety_reports',
        #     name='Send weekly safety reports to all users',
        #     replace_existing=True
        # )

        if weekly_enabled:
            scheduler.add_job(
                weekly_safety_report_job,
                trigger='cron',
                day_of_week=weekly_day,
                hour=weekly_hour,
                minute=weekly_minute,
                id='weekly_safety_reports',
                name='Send weekly safety reports',
                replace_existing=True,
                timezone=weekly_timezone
            )

        # ── Incident polling interval is configured via system settings ──
        def poll_incidents_job():
            """Sync wrapper for APScheduler"""
            try:
                asyncio.run(poll_new_incidents_for_alerts())
            except Exception as _e:
                logger.error(f"poll_incidents_job error: {_e}")

        scheduler.add_job(
            poll_incidents_job,
            trigger=IntervalTrigger(minutes=poll_interval),
            id='poll_new_incidents',
            name='Poll DB for new incidents and dispatch alerts',
            replace_existing=True,
            max_instances=poll_max_instances
        )
        logger.info("✅ Background monitoring tasks started successfully")
        print("🕒 Scheduler started - monitoring jobs are active")
        
    except Exception as e:
        logger.error(f"❌ Error starting background monitoring: {e}")
        print(f"❌ Scheduler error: {e}")

@app.post("/api/test/trigger-monitoring")
async def trigger_monitoring_test():
    """Test endpoint to manually trigger saved location monitoring"""
    try:
        await monitor_saved_locations()
        return {"message": "✅ Saved location monitoring triggered successfully"}
    except Exception as e:
        logger.error(f"Test monitoring error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/test/trigger-weekly-reports")
async def trigger_weekly_reports_test(current_user: str = Depends(get_username_from_token)):
    """Admin-only test endpoint to manually trigger weekly safety reports."""
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT role FROM users_info WHERE username = %s", (current_user,))
        row = cursor.fetchone()
        if not row or row.get("role") not in ("superadmin", "admin"):
            raise HTTPException(status_code=403, detail="Admin access required")
    finally:
        if cursor: cursor.close()
        if conn and conn.is_connected(): conn.close()

    try:
        await dispatch_weekly_safety_reports()
        return {"message": "✅ Weekly safety reports triggered successfully"}
    except Exception as e:
        logger.error(f"Error triggering weekly reports: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/test/trigger-incident-poll")
async def trigger_incident_poll_test():
    """Test endpoint to manually trigger the incident polling job (detects DB-inserted crimes)"""
    try:
        await poll_new_incidents_for_alerts()
        return {"message": "✅ Incident poll triggered successfully"}
    except Exception as e:
        logger.error(f"Error triggering incident poll: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/monitor-saved-locations")
async def api_monitor_saved_locations():
    """API endpoint to manually trigger saved location monitoring"""
    try:
        await monitor_saved_locations()
        return {"message": "✅ Saved location monitoring completed successfully"}
    except Exception as e:
        logger.error(f"Monitor saved locations error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

def test_scheduler_job():
    """Test job to verify scheduler is working"""
    try:
        print(f"✅ Scheduler test job running at {datetime.now()}")
        logger.info("Scheduler test job executed successfully")
    except Exception as e:
        logger.error(f"Scheduler test job error: {e}")

# Call this function during startup
@app.on_event("startup")
async def on_startup():
    """Prepare database schema when the application starts."""
    try:
        initialize_schema()
        ensure_browser_notifications_tables()
        ensure_alert_subscriptions_table()
        ensure_alerts_tables_schema()
        print("✅ Database schema initialized successfully")

        # Start background monitoring
        start_background_monitoring()
        print("✅ Background monitoring started")

        # ---- Sync PPC/law-section severity scores into severity_map.json ----
        try:
            import sys as _sys, os as _os
            _crm_utils = _os.path.normpath(
                _os.path.join(_os.path.dirname(__file__), 'app', 'crime_risk_model', 'utils')
            )
            if _crm_utils not in _sys.path:
                _sys.path.insert(0, _crm_utils)
            from severity_sync import sync_severity_from_db as _sev_sync
            _summary = _sev_sync()
            print(f"✅ severity_sync: +{_summary['added']} new, {_summary['updated']} updated, {_summary['unchanged']} unchanged")
        except Exception as _se:
            print(f"⚠️  severity_sync skipped (non-fatal): {_se}")

        # ---- Load areas table into OCR geocoding cache (DB text-match) ----
        try:
            _areas_conn = get_db_connection()
            _ocr_load_areas(_areas_conn)
            _areas_conn.close()
            print("✅ OCR geocoding areas table loaded")
        except Exception as _area_err:
            print(f"⚠️  OCR geocoding areas table not loaded (non-fatal): {_area_err}")

        # ---- Start ModelWatcher (auto-retrain when new crimes/areas arrive) ----
        try:
            from model_watcher import get_watcher as _gw
            _gw().start()
            print("✅ ModelWatcher started — auto-retrain enabled")
            print("🔄 Running initial model check for new data...")
            try:
                _gw()._db_check()
                print("✅ Initial model check completed")
            except Exception as _initial_check_err:
                print(f"⚠️  Initial model check error (non-fatal): {_initial_check_err}")
        except Exception as _mwe:
            print(f"⚠️  ModelWatcher not started (non-fatal): {_mwe}")

        # Test the scheduler immediately
        scheduler.print_jobs()

        # Run initial monitoring check (configurable)
        try:
            from app.routes.admin import get_setting, SYSTEM_SETTINGS_DEFAULTS
            default_run_initial = str(SYSTEM_SETTINGS_DEFAULTS.get("run_initial_monitor_on_startup", {}).get("value", "true")).lower()
            run_initial_raw = get_setting("run_initial_monitor_on_startup")
            run_initial = str(run_initial_raw if run_initial_raw is not None else default_run_initial).lower() == "true"
        except Exception:
            run_initial = True

        if run_initial:
            print("🔄 Running initial saved locations monitoring...")
            await monitor_saved_locations()
            print("✅ Initial saved locations monitoring completed")
        else:
            print("ℹ️ Initial saved locations monitoring skipped by system setting")

    except Exception as exc:
        logger.error("Startup schema initialization failed", exc_info=exc)
        print(f"❌ Database initialization error: {exc}")

@app.post("/analyze_route_safety", response_model=SafetyResponse)
async def analyze_route_safety(route: RouteData):
    """
    Analyze route safety using comprehensive rule-based scoring

    Considers:
    - Crime data along the route
    - Emergency services proximity
    - Road type and traffic
    - Lighting conditions
    - Time-of-day adjustments
    """
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        # Initialize analyzer
        analyzer = RouteSafetyAnalyzer()

        # Prepare route points
        route_points = []
        if route.start_lat and route.start_lng:
            route_points.append((route.start_lat, route.start_lng))
        if route.end_lat and route.end_lng:
            route_points.append((route.end_lat, route.end_lng))

        if route.waypoints:
            for waypoint in route.waypoints:
                route_points.append((waypoint.lat, waypoint.lng))

        if not route_points:
            logger.warning("No route points provided for safety analysis")
            return SafetyResponse(
                overall_score=70.0,
                alerts=[{
                    "type": "Invalid Route",
                    "description": "No route points provided for analysis.",
                    "severity": "medium",
                    "location": "Unknown"
                }]
            )

        # Collect crime data for all route points
        all_crimes = []
        for lat, lng in route_points:
            cursor.execute("""
                SELECT
                    id, crime_type, risk_level, latitude, longitude,
                    ST_Distance_Sphere(
                        point(longitude, latitude),
                        point(%s, %s)
                    ) as distance_meters
                FROM crimes
                WHERE ST_Distance_Sphere(
                    point(longitude, latitude),
                    point(%s, %s)
                ) <= 1000
                AND crime_date >= DATE_SUB(NOW(), INTERVAL 90 DAY)
                ORDER BY distance_meters ASC
                LIMIT 20
            """, (lng, lat, lng, lat))

            crimes = cursor.fetchall()
            if crimes:
                all_crimes.extend([cast(Dict[str, Any], c) for c in crimes])

        # Collect infrastructure data
        infrastructure_data = {
            "nearest_police_distance": float('inf'),
            "nearest_hospital_distance": float('inf'),
            "has_lighting": False,
            "road_type": "secondary",
            "traffic_level": "moderate"
        }

        # Try to query for nearest police station (if locations table exists)
        if route_points:
            lat, lng = route_points[0]
            try:
                cursor.execute(
                    """
                    SELECT COUNT(*) AS c
                    FROM information_schema.tables
                    WHERE table_schema = DATABASE() AND table_name = 'locations'
                    """
                )
                _locations_exists = int((cursor.fetchone() or {}).get('c', 0) or 0) > 0
                if _locations_exists:
                    cursor.execute("""
                        SELECT
                            ST_Distance_Sphere(
                                point(longitude, latitude),
                                point(%s, %s)
                            ) as distance_meters
                        FROM locations
                        WHERE location_type = 'police_station'
                        ORDER BY distance_meters ASC
                        LIMIT 1
                    """, (lng, lat))

                    result = cursor.fetchone()
                    if result:
                        result_dict = cast(Dict[str, Any], result)
                        infrastructure_data["nearest_police_distance"] = result_dict.get("distance_meters", float('inf'))
                else:
                    infrastructure_data["nearest_police_distance"] = 1500
                    infrastructure_data["nearest_hospital_distance"] = 2000
            except Exception as e:
                logger.warning(f"Could not query locations table: {e}. Using default infrastructure data.")
                # Use default values if locations table doesn't exist
                infrastructure_data["nearest_police_distance"] = 1500
                infrastructure_data["nearest_hospital_distance"] = 2000

        # Calculate safety score using analyzer
        analysis_result = analyzer.calculate_safety_score(
            route_points=route_points,
            crime_data=all_crimes,
            infrastructure_data=infrastructure_data,
            route_distance=route.distance,
            route_duration=route.duration
        )

        logger.info(f"✅ Route safety analysis complete: Score={analysis_result['overall_score']}, Level={analysis_result['safety_level']}")

        return SafetyResponse(
            overall_score=analysis_result["overall_score"],
            alerts=analysis_result["alerts"],
            safety_level=analysis_result.get("safety_level", "medium"),
            factors=analysis_result.get("factors", {})
        )

    except Exception as e:
        logger.error(f"❌ Error analyzing route safety: {e}", exc_info=True)
        # Return safe default if analysis fails
        return SafetyResponse(
            overall_score=70.0,
            alerts=[{
                "type": "Analysis Unavailable",
                "description": "Safety analysis temporarily unavailable. Route shown is the fastest path.",
                "severity": "low",
                "location": "Unknown"
            }]
        )
    finally:
        cursor.close()
        conn.close()

# ========== OCR ENDPOINT ==========
@app.post("/api/ocr/extract")
async def extract_text_from_image(file: UploadFile = File(...)):
    """
    Extract FIR data using specialized OCR.
    Returns: crime_date, crime_area (thana), sections
    """
    if fir_extractor is None:
        return JSONResponse(
            content={
                "status": "failed",
                "error": "OCR engine not initialized. Please check server logs.",
                "text": "",
                "confidence": 0,
                "crime_date": "",
                "crime_area": "",
                "sections": []
            },
            status_code=503
        )

    try:
        cleanup_temp_files()

        logger.info(f"Received file: {file.filename}, Content-Type: {file.content_type}")

        # Validate file type
        allowed_types = ["image/png", "image/jpeg", "image/jpg", "image/webp", "image/x-png"]
        if file.content_type and file.content_type not in allowed_types:
            logger.error(f"Invalid file type: {file.content_type}")
            raise HTTPException(status_code=400, detail=f"Invalid file type: {file.content_type}. Allowed: {', '.join(allowed_types)}")

        contents = await file.read()
        original_size_mb = len(contents) / (1024 * 1024)

        logger.info(f"Processing FIR file: {file.filename} ({original_size_mb:.2f}MB)")
        logger.info("=" * 80)
        logger.info("STARTING SPECIALIZED FIR EXTRACTION")
        logger.info("=" * 80)

        try:
            result = fir_extractor.extract_fir_data(contents, filename=file.filename or "")

            if result["status"] == "success":
                # Map extracted sections to English crime names (PPC + ATA + CNSA + other laws)
                sections = result.get("sections", [])
                # Deduplicate while preserving order
                seen_secs: set = set()
                sections = [s for s in sections if not (s in seen_secs or seen_secs.add(s))]
                section_crimes = []
                if sections:
                    crime_mappings = get_crime_names(sections)
                    for sec, crime_name, law_type in crime_mappings:
                        section_crimes.append({
                            "section": sec,
                            "crime_name": crime_name,
                            "law_type": law_type
                        })

                result["section_crimes"] = section_crimes
                sections_str = ", ".join([str(s) for s in sections])
                result["text"] = f"Date: {result.get('crime_date', 'N/A')} | Time: {result.get('crime_time', 'N/A')} | Thana: {result.get('crime_area', 'N/A')} | Sections: {sections_str}"

                result["fields"] = {
                    "crime_date": result.get("crime_date", "Not found"),
                    "crime_time": result.get("crime_time", "Not found"),
                    "crime_area": result.get("crime_area", "Not found"),
                    "crime_type": ("Sections: " + ", ".join([str(s) for s in sections])) if sections else "Not found",
                    "section_crimes": section_crimes,
                    "location": result.get("location", {})
                }

                logger.info("=" * 80)
                logger.info("✓ FIR EXTRACTION COMPLETE")
                logger.info(f"  Crime Date: {result['crime_date']}")
                logger.info(f"  Crime Time: {result['crime_time']}")
                logger.info(f"  Crime Area (Thana): {result['crime_area']}")
                logger.info(f"  Sections: {', '.join(result['sections'])}")
                for sc in section_crimes:
                    logger.info(f"    → {sc['section']} {sc['law_type']}: {sc['crime_name']}")
                logger.info(f"  Confidence: {result['confidence']}%")
                logger.info("=" * 80)
            else:
                logger.error("=" * 80)
                logger.error("✗ FIR EXTRACTION FAILED")
                logger.error(f"  Error: {result.get('error', 'Unknown error')}")
                logger.error("=" * 80)

        except Exception as e:
            logger.error(f"FIR extraction crashed: {str(e)}")
            result = {
                "status": "failed",
                "error": f"FIR extraction failed: {str(e)}",
                "text": "",
                "confidence": 0,
                "crime_date": "",
                "crime_time": "",
                "crime_area": "",
                "sections": []
            }

        status_code = 500 if result["status"] == "failed" else 200
        return JSONResponse(content=result, status_code=status_code)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"CRITICAL: Unexpected error in OCR endpoint: {str(e)}")
        return JSONResponse(
            content={
                "status": "failed",
                "error": f"Server error: {str(e)}",
                "text": "",
                "confidence": 0,
                "crime_date": "",
                "crime_area": "",
                "sections": []
            },
            status_code=500
        )


# ── Re-geocode and transliterate helpers for admin crime-area corrections ─────
# The OCR review screen lets an admin fix Gemini's Urdu mistakes. When they do,
# the original lat/long (computed from the wrong Urdu) is stale. These two
# endpoints power (a) a "Re-geocode" button that recomputes coordinates from
# the corrected Urdu, and (b) a live English preview of the Urdu as the admin
# types so they can verify without reading Urdu script directly.


class _RegeocodeRequest(BaseModel):
    area: str = Field(..., min_length=1, max_length=400)


@app.post("/api/ocr/regeocode")
async def ocr_regeocode(payload: _RegeocodeRequest):
    """Re-run Nominatim geocoding for the supplied (admin-edited) crime area.

    Returns `{latitude, longitude, display_name, success}` matching the shape
    the OCR extract endpoint already uses inside `fields.location`, so the
    frontend can drop the result straight into state.
    """
    area = (payload.area or "").strip()
    if not area:
        return JSONResponse(
            content={"success": False, "error": "Empty area string"},
            status_code=400,
        )
    try:
        geo = _ocr_geocode_area(area)
        return {
            "latitude": geo.get("latitude"),
            "longitude": geo.get("longitude"),
            "display_name": geo.get("display_name", ""),
            "success": bool(geo.get("success")),
        }
    except Exception as e:
        logger.error(f"[regeocode] failed for area={area!r}: {e}")
        return JSONResponse(
            content={"success": False, "error": f"Geocode failed: {e}"},
            status_code=500,
        )


class _TransliterateRequest(BaseModel):
    urdu_text: str = Field(..., min_length=1, max_length=400)


@app.post("/api/ocr/transliterate")
async def ocr_transliterate(payload: _TransliterateRequest):
    """Convert an Urdu area string to English for the live admin preview.

    Uses the same keyword-first / MyMemory-fallback path already used during
    approval-time writes so the preview matches what will eventually be saved.
    """
    urdu = (payload.urdu_text or "").strip()
    if not urdu:
        return {"english": ""}
    try:
        # Import lazily — approval_workflow pulls in several DB helpers we
        # don't need on the hot startup path.
        from app.approval_workflow import _azure_transliterate_single
        english = _azure_transliterate_single(urdu) or ""
        return {"english": english}
    except Exception as e:
        logger.error(f"[transliterate] failed for urdu={urdu!r}: {e}")
        return JSONResponse(
            content={"english": "", "error": f"Transliterate failed: {e}"},
            status_code=500,
        )


class _RomanToUrduRequest(BaseModel):
    roman_text: str = Field(..., min_length=1, max_length=400)


# Common Lahore-area vocabulary. Google Input Tools is non-deterministic for
# short stems ("block" → sometimes "بلاک", sometimes "بلا"), so we override
# these explicitly and only fall back to Google for unknown words.
_ROMAN_URDU_OVERRIDES = {
    "block": "بلاک",
    "sub": "سب",
    "road": "روڈ",
    "rd": "روڈ",
    "street": "گلی",
    "gali": "گلی",
    "gate": "گیٹ",
    "town": "ٹاؤن",
    "phase": "فیز",
    "colony": "کالونی",
    "society": "سوسائٹی",
    "housing": "ہاؤسنگ",
    "scheme": "سکیم",
    "abad": "آباد",
    "bagh": "باغ",
    "park": "پارک",
    "chowk": "چوک",
    "nagar": "نگر",
    "pura": "پورہ",
    "mohalla": "محلّہ",
    "mohallah": "محلّہ",
    "bazaar": "بازار",
    "bazar": "بازار",
    "market": "مارکیٹ",
    "sector": "سیکٹر",
    "model": "ماڈل",
    "cantt": "کینٹ",
    "garden": "گارڈن",
    "city": "سٹی",
    "canal": "نہر",
    "main": "مین",
    "lane": "لین",
    "interchange": "انٹرچینج",
    "stop": "سٹاپ",
    "more": "موڑ",
    "mor": "موڑ",
    "eden": "ایڈن",
    "lohari": "لوہاری",
    "bhati": "بھاٹی",
    "delhi": "دہلی",
    "mochi": "موچی",
    "akbari": "اکبری",
    "shah": "شاہ",
    "alami": "عالمی",
    "data": "داتا",
    "darbar": "دربار",
    "anarkali": "انارکلی",
    "badami": "بادامی",
    "mazang": "مزنگ",
    "samanabad": "سمن آباد",
    "iqbal": "اقبال",
    "allama": "علامہ",
    "johar": "جوہر",
    "shalimar": "شالامار",
    "shahdara": "شاہدرہ",
    "ravi": "راوی",
    "askari": "عسکری",
    "defence": "ڈیفنس",
    "dha": "ڈی ایچ اے",
    "bahria": "بحریہ",
    "valencia": "والینشیا",
    "wapda": "واپڈا",
    "pia": "پی آئی اے",
    "thokar": "ٹھوکر",
    "niaz": "نیاز",
    "baig": "بیگ",
    "raiwind": "رائیونڈ",
    "multan": "ملتان",
    "ferozepur": "فیروزپور",
    "grand": "گرینڈ",
    "trunk": "ٹرنک",
    "gt": "جی ٹی",
    "mm": "ایم ایم",
    "alam": "عالم",
    "jail": "جیل",
    "mall": "مال",
    "walton": "والٹن",
    "lahore": "لاہور",
    "punjab": "پنجاب",
    "pakistan": "پاکستان",
}


@app.post("/api/ocr/roman-to-urdu")
async def ocr_roman_to_urdu(payload: _RomanToUrduRequest):
    """Convert Roman (English-letter) Urdu words to Urdu script.

    Local overrides handle common Lahore-area vocabulary (block, road, gate,
    town, named landmarks) with deterministic output. For everything else we
    proxy Google Input Tools — the same API that powers Gboard's Urdu
    transliteration keyboard. Single uppercase letters (e.g. "F", "A" for
    sub-block codes) are preserved as Roman on purpose — that's the local
    convention for how these are written on FIRs.
    """
    roman = (payload.roman_text or "").strip()
    if not roman:
        return {"urdu": ""}
    try:
        words = roman.split()
        url = "https://inputtools.google.com/request"
        urdu_parts = []
        trace = []
        for word in words:
            # Separate leading/trailing punctuation so overrides still match.
            m = re.match(r"^([^\w]*)(\w.*?\w|\w)([^\w]*)$", word, flags=re.UNICODE)
            if m:
                lead, core, trail = m.group(1), m.group(2), m.group(3)
            else:
                lead, core, trail = "", word, ""

            # Pure digit or non-alpha (already-Urdu, punctuation, numbers) → pass through
            if not core or not re.search(r"[A-Za-z]", core):
                urdu_parts.append(word)
                trace.append(f"{word!r}→passthrough")
                continue

            # Single uppercase letter like "F" / "A" → keep as Roman (sub-block codes)
            if re.fullmatch(r"[A-Z]", core):
                urdu_parts.append(word)
                trace.append(f"{word!r}→roman-letter")
                continue

            # Local override (case-insensitive)
            override = _ROMAN_URDU_OVERRIDES.get(core.lower())
            if override:
                urdu_parts.append(f"{lead}{override}{trail}")
                trace.append(f"{word!r}→override:{override}")
                continue

            # Fall back to Google Input Tools
            r = requests.get(
                url,
                params={
                    "text": core,
                    "itc": "ur-t-i0-und",
                    "num": "5",
                    "cp": "0",
                    "cs": "1",
                    "ie": "utf-8",
                    "oe": "utf-8",
                    "app": "demopage",
                },
                timeout=5,
            )
            r.raise_for_status()
            data = r.json()
            picked = core
            if (
                isinstance(data, list)
                and len(data) >= 2
                and data[0] == "SUCCESS"
                and isinstance(data[1], list)
                and data[1]
                and isinstance(data[1][0], list)
                and len(data[1][0]) >= 2
                and data[1][0][1]
            ):
                candidates = [c for c in data[1][0][1] if isinstance(c, str) and c]
                # Prefer the longest candidate — Google sometimes returns a
                # truncated form first ("بلا" before "بلاک"). Longer Urdu
                # renderings of short Roman stems are almost always correct.
                if candidates:
                    picked = max(candidates, key=len)
            urdu_parts.append(f"{lead}{picked}{trail}")
            trace.append(f"{word!r}→google:{picked}")
        result = " ".join(urdu_parts)
        logger.info(f"[roman-to-urdu] in={roman!r} out={result!r} trace={trace}")
        return {"urdu": result}
    except Exception as e:
        logger.error(f"[roman-to-urdu] failed for text={roman!r}: {e}")
        return JSONResponse(
            content={"urdu": "", "error": f"Roman→Urdu failed: {e}"},
            status_code=500,
        )


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
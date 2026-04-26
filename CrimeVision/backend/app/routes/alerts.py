import os, sys, logging, json, math
import re
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Body
from fastapi.responses import JSONResponse
from typing import Dict, Any, List, Optional, cast
import asyncio
from datetime import datetime, timedelta
import requests
from mysql.connector import Error

from app.core.database import get_db_connection, log_user_activity
from app.utils.geo import get_coordinates
from app.utils.area_normalization import area_like_pattern, normalize_area_name
from app.alert_notifications import AlertNotificationSystem
from app.dependencies import get_username_from_token, get_current_user
from app.utils.risk import calculate_unified_risk_summary
from .admin import get_setting
from app.models.schemas import (
    AlertSubscription, RiskZoneAlert, LocationAlertRequest,
    AlertCreate, UserAlertResponse
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/alerts", tags=["alerts"])

# Email configuration for alerts
# Prefer dedicated SMTP_* vars, but fall back to AUTH_EMAIL_* credentials used by verification/password reset
ALERT_EMAIL_CONFIG = {
    'smtp_server': os.getenv('SMTP_SERVER', 'smtp.gmail.com'),
    'smtp_port': int(os.getenv('SMTP_PORT', 587)),
    'smtp_username': os.getenv(
        'SMTP_USERNAME',
        os.getenv('ALERTS_EMAIL_USERNAME', os.getenv('AUTH_EMAIL_USERNAME', 'safevision.alerts@gmail.com')),
    ),
    'smtp_password': os.getenv(
        'SMTP_PASSWORD',
        os.getenv('ALERTS_EMAIL_PASSWORD', os.getenv('AUTH_EMAIL_PASSWORD', '')),
    )
}

# Warn if SMTP credentials are missing at startup (helps troubleshooting BadCredentials errors)
if not ALERT_EMAIL_CONFIG['smtp_password']:
    logger.warning("Alert email SMTP password is empty. Set SMTP_PASSWORD or AUTH_EMAIL_PASSWORD env var to enable sending alerts.")

SAFE_AREA_ALERT_CONFIG = {
    'min_safety_score': int(os.getenv('SAFE_AREA_MIN_SCORE', '70')),
    'send_safe_alerts': os.getenv('SEND_SAFE_ALERTS', 'True').lower() == 'true',
    'cooldown_minutes': int(os.getenv('SAFE_ALERT_COOLDOWN', '60')),
}

# VAPID keys for web push notifications
# Must be fetched from environment variables - no hardcoded defaults!
VAPID_PUBLIC_KEY = os.getenv('VAPID_PUBLIC_KEY')
VAPID_PRIVATE_KEY = os.getenv('VAPID_PRIVATE_KEY')

# Validate VAPID keys are configured
if not VAPID_PUBLIC_KEY or not VAPID_PRIVATE_KEY:
    logger.warning("⚠️ VAPID keys not configured! Browser push notifications will fail. Set VAPID_PUBLIC_KEY and VAPID_PRIVATE_KEY in .env file.")

alert_notification_system = AlertNotificationSystem(ALERT_EMAIL_CONFIG, VAPID_PUBLIC_KEY, VAPID_PRIVATE_KEY)
alert_cooldown_cache: Dict[str, datetime] = {}


def _resolve_alert_category(alert: RiskZoneAlert) -> str:
    """Map alert payloads to the three user-facing categories."""
    if alert.alert_type == "weekly_safety_report":
        return "weekly"
    if alert.alert_type == "new_incident_alert":
        return "incident"
    if alert.location_type == "current" or "live" in str(alert.alert_type or "").lower():
        return "live"
    return "incident"


def _default_channel_preferences(email_enabled: bool, browser_enabled: bool) -> Dict[str, Dict[str, bool]]:
    return {
        "incident": {"email": bool(email_enabled), "browser": bool(browser_enabled)},
        "live": {"email": bool(email_enabled), "browser": bool(browser_enabled)},
        "weekly": {"email": bool(email_enabled), "browser": bool(browser_enabled)},
    }


def _load_alert_channel_preferences(user_data: Dict[str, Any]) -> Dict[str, Dict[str, bool]]:
    defaults = _default_channel_preferences(
        bool(user_data.get("email_alerts_enabled", True)),
        bool(user_data.get("browser_notifications_enabled", False)),
    )

    raw_preferences = user_data.get("alert_preferences")
    if not raw_preferences:
        return defaults

    try:
        parsed = raw_preferences if isinstance(raw_preferences, dict) else json.loads(raw_preferences)
        stored = parsed.get("alert_channel_preferences", {}) if isinstance(parsed, dict) else {}
        for category in ("incident", "live", "weekly"):
            category_prefs = stored.get(category, {}) if isinstance(stored, dict) else {}
            if isinstance(category_prefs, dict):
                if "email" in category_prefs:
                    defaults[category]["email"] = bool(category_prefs.get("email"))
                if "browser" in category_prefs:
                    defaults[category]["browser"] = bool(category_prefs.get("browser"))
    except Exception as pref_error:
        logger.warning(f"Unable to parse alert channel preferences for user {user_data.get('id')}: {pref_error}")

    return defaults


def get_alert_threshold_policy() -> str:
    """Return the global alert threshold setting from admin policy."""
    value = (get_setting("alert_threshold", "medium") or "medium").strip().lower()
    return value if value in {"low", "medium", "high"} else "medium"


def get_global_notification_radius_km() -> float:
    """Return validated global alert radius in kilometers from system settings."""
    raw = get_setting("notification_radius", "5")
    try:
        radius = float(raw) if raw is not None else 5.0
    except (TypeError, ValueError):
        radius = 5.0
    return max(1.0, min(50.0, radius))


def meets_alert_threshold(risk_level: str, threshold: Optional[str] = None) -> bool:
    """Determine whether a risk label should produce an alert under the global policy."""
    policy = (threshold or get_alert_threshold_policy()).strip().lower()
    normalized_risk = (risk_level or "").strip().lower().split()[0]

    order = {"low": 0, "moderate": 1, "high": 2, "critical": 3}
    threshold_map = {
        "low": "moderate",
        "medium": "high",
        "high": "critical",
    }

    min_level = threshold_map.get(policy, "high")
    return order.get(normalized_risk, 0) >= order[min_level]

# These functions are now in app.utils.risk for consistency


@router.get("/get-safety-stats-by-coords")
async def get_safety_stats_by_coords(lat: float, lng: float, radius_km: float = 1.0) -> Dict[str, Any]:
    """Aggregate crime stats within a radius of given coordinates.
    Uses the unified shared risk scorer for consistent risk/safety outputs."""
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Convert km to degrees for bounding box — cast to float to avoid Decimal TypeError
        earth_radius = 6371.0  # km
        lat_f = float(lat)
        lng_f = float(lng)
        lat_range = (radius_km / earth_radius) * (180.0 / 3.14159)
        lng_range = (radius_km / (earth_radius * 3.14159 / 180.0 * abs(3.14159 / 180.0 * lat_f))) if lat_f != 0 else (radius_km / earth_radius) * (180.0 / 3.14159)

        # Query crimes in the last 90 days for lambda estimation
        cursor.execute(
            """
            SELECT
                COUNT(*) as total_crimes,
                SUM(CASE WHEN risk_level = 'High' THEN 1 ELSE 0 END) as high_risk_count,
                SUM(CASE WHEN risk_level = 'Medium' THEN 1 ELSE 0 END) as medium_risk_count,
                SUM(CASE WHEN crime_date >= (NOW() - INTERVAL 90 DAY) AND risk_level = 'High' THEN 1 ELSE 0 END) as high_risk_count_90d,
                SUM(CASE WHEN crime_date >= (NOW() - INTERVAL 90 DAY) AND risk_level = 'Medium' THEN 1 ELSE 0 END) as medium_risk_count_90d,
                SUM(CASE WHEN crime_date >= (NOW() - INTERVAL 90 DAY) THEN 1 ELSE 0 END) as last_90_days,
                COUNT(DISTINCT crime_type) as unique_crime_types,
                MAX(crime_type) as dominant_crime_type
            FROM crimes
            WHERE latitude BETWEEN %s AND %s
              AND longitude BETWEEN %s AND %s
              AND SQRT(POW(111.32 * (latitude - %s), 2) + POW(111.32 * (%s - longitude) * COS(latitude / 57.3), 2)) <= %s
              AND crime_date >= (NOW() - INTERVAL 365 DAY)
            """,
            (lat_f - lat_range, lat_f + lat_range, lng_f - lng_range, lng_f + lng_range, lat_f, lng_f, radius_km),
        )

        stats = cursor.fetchone() or {}
        stats_dict = cast(Dict[str, Any], stats)

        total_crimes = int(stats_dict.get('total_crimes', 0) or 0)
        high_risk_count = int(stats_dict.get('high_risk_count', 0) or 0)
        medium_risk_count = int(stats_dict.get('medium_risk_count', 0) or 0)
        high_risk_count_90d = int(stats_dict.get('high_risk_count_90d', 0) or 0)
        medium_risk_count_90d = int(stats_dict.get('medium_risk_count_90d', 0) or 0)
        last_90_days = int(stats_dict.get('last_90_days', 0) or 0)
        unique_crime_types = int(stats_dict.get('unique_crime_types', 0) or 0)
        dominant_crime_type = stats_dict.get('dominant_crime_type')

        # Get dominant (most frequent) crime type properly
        if total_crimes > 0:
            cursor.execute(
                """
                SELECT crime_type, COUNT(*) as cnt
                FROM crimes
                WHERE latitude BETWEEN %s AND %s
                  AND longitude BETWEEN %s AND %s
                  AND SQRT(POW(111.32 * (latitude - %s), 2) + POW(111.32 * (%s - longitude) * COS(latitude / 57.3), 2)) <= %s
                  AND crime_date >= (NOW() - INTERVAL 365 DAY)
                GROUP BY crime_type
                ORDER BY cnt DESC
                LIMIT 1
                """,
                (lat_f - lat_range, lat_f + lat_range, lng_f - lng_range, lng_f + lng_range, lat_f, lng_f, radius_km),
            )
            top_crime_row = cursor.fetchone()
            if top_crime_row:
                dominant_crime_type = cast(Dict[str, Any], top_crime_row).get('crime_type', dominant_crime_type)

        # Use centralized unified scoring formula for consistency with dashboard/prediction/admin
        risk_summary = calculate_unified_risk_summary(stats_dict, 365)
        safety_score = float(risk_summary["safety_score"])
        risk_pct = float(risk_summary["risk_score"])
        risk_level = str(risk_summary["risk_level"])

        # Only force very-safe fallback when there is no historical data at all.
        if total_crimes == 0 and last_90_days == 0 and high_risk_count == 0 and medium_risk_count == 0:
            risk_pct = 8.0
            safety_score = 92.0
            risk_level = 'Low'
            risk_summary['data_confidence'] = 'low'

        logger.info(
            f"✅ Unified risk: crimes={total_crimes} (last 365d), high={high_risk_count}, "
            f"medium={medium_risk_count}, risk_score={risk_pct}%, risk_level={risk_level}"
        )

        return {
            'total_crimes': total_crimes,
            'high_risk_count': high_risk_count,
            'medium_risk_count': medium_risk_count,
            'high_risk_count_90d': high_risk_count_90d,
            'medium_risk_count_90d': medium_risk_count_90d,
            'unique_crime_types': unique_crime_types,
            'dominant_crime_type': dominant_crime_type,
            'safety_score': safety_score,
            'risk_pct': risk_pct,          # Unified risk score (%)
            'risk_level': risk_level,
            'data_confidence': risk_summary.get('data_confidence', 'low'),
            'score_components': risk_summary.get('score_components', {}),
            'last_90_days': last_90_days,
            'reference_date': datetime.now().strftime('%Y-%m-%d'),
            'scope_mode': 'radius',
            'scope': {
                'mode': 'radius',
                'lat': float(lat),
                'lng': float(lng),
                'radius_km': float(radius_km),
            },
        }

    except Exception as e:
        logger.error(f"❌ Error aggregating safety stats by coords ({lat}, {lng}): {e}")
        logger.exception("Full traceback:")
        return {
            'total_crimes': 0, 'high_risk_count': 0, 'medium_risk_count': 0,
            'unique_crime_types': 0, 'dominant_crime_type': None,
            'safety_score': 90.0, 'risk_pct': 10.0, 'risk_level': 'Low',
            'data_confidence': 'low', 'score_components': {},
            'last_90_days': 0,
            'reference_date': datetime.now().strftime('%Y-%m-%d'),
            'scope_mode': 'radius',
            'scope': {
                'mode': 'radius',
                'lat': float(lat),
                'lng': float(lng),
                'radius_km': float(radius_km),
            },
        }
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()


@router.get("/vapid-public-key")
@router.get("/api/alerts/vapid-public-key")
async def get_vapid_public_key():
    """Return the VAPID public key used for browser push subscription (base64url string).

    The frontend will fetch this at runtime to avoid embedding sensitive or malformed keys in client code.
    """
    # Return as JSON object for easy consumption by the frontend
    # Include caching headers since the public key is stable
    return JSONResponse(content={"publicKey": VAPID_PUBLIC_KEY}, headers={"Cache-Control": "public, max-age=86400"})

@router.post("/community/subscribe")
async def subscribe_to_alerts(
    subscription_data: dict,
    current_user: str = Depends(get_current_user)
):
    """Subscribe to safety alerts"""
    conn = None
    cursor = None
    try:
        print(f"🔔 Subscription request from user: {current_user}")
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Get user info
        cursor.execute("SELECT id, email FROM users_info WHERE username = %s", (current_user,))
        user = cast(Optional[Dict[str, Any]], cursor.fetchone())
        
        if not user:
            print("❌ User not found")
            raise HTTPException(status_code=404, detail="User not found")
        
        user_id = user["id"]
        print(f"👤 User ID: {user_id}")
        
        # Extract and validate fields for new schema
        alert_types = subscription_data.get('alert_types', ['crime', 'safety', 'emergency'])
        areas = subscription_data.get('areas', ['General'])
        radius = float(subscription_data.get('radius', 5.0))
        notification_types = subscription_data.get('notification_types', ['email', 'browser'])
        is_active = bool(subscription_data.get('is_active', True))

        print(f"📊 Extracted data - alert_types: {alert_types}, areas: {areas}, radius: {radius}, notification_types: {notification_types}")

        # Validate required fields
        if not areas:
            print("❌ Areas is required")
            raise HTTPException(status_code=422, detail="Areas is required")

        # Check for existing subscription
        cursor.execute("""
            SELECT id FROM alert_subscriptions
            WHERE user_id = %s AND areas = %s AND is_active = TRUE
        """, (user_id, json.dumps(areas)))

        existing_subscription = cast(Optional[Dict[str, Any]], cursor.fetchone())

        if existing_subscription:
            # Update existing subscription
            cursor.execute("""
                UPDATE alert_subscriptions
                SET alert_types = %s, radius = %s, notification_types = %s, updated_at = %s
                WHERE id = %s
            """, (
                json.dumps(alert_types),
                radius,
                json.dumps(notification_types),
                datetime.now(),
                existing_subscription["id"]
            ))
            subscription_id = existing_subscription["id"]
            print(f"✅ Updated existing subscription: {subscription_id}")
        else:
            # Create new alert subscription record
            cursor.execute("""
                INSERT INTO alert_subscriptions 
                (user_id, alert_types, areas, radius, notification_types, is_active, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (
                user_id,
                json.dumps(alert_types),
                json.dumps(areas),
                radius,
                json.dumps(notification_types),
                is_active,
                datetime.now()
            ))

            subscription_id = cursor.lastrowid
            print(f"✅ Created new subscription with ID: {subscription_id}")
        
        conn.commit()
        
        # Log the activity
        log_user_activity(
            activity_type="alerts_subscribed",
            username=current_user,
            user_id=user_id,
            activity_details={
                "alert_types": alert_types,
                "area": areas,
                "radius": radius,
                "notification_types": notification_types,
                "subscription_id": subscription_id,
                "action": "updated" if existing_subscription else "created"
            }
        )
        
        return {
            "message": "✅ Successfully subscribed to safety alerts!",
            "subscription_id": subscription_id,
            "status": "active",
            "action": "updated" if existing_subscription else "created"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Unexpected error in subscribe_to_alerts: {e}")
        print(f"❌ Error type: {type(e)}")
        import traceback
        print(f"❌ Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()

@router.post("/check-location")
async def check_location_for_alerts(
    request: LocationAlertRequest,
    current_user: str = Depends(get_username_from_token)
):
    """Check location for immediate alerts"""
    try:
        print(f"📍 Checking location alerts for user: {current_user}")
        print(f"📌 Location: {request.latitude}, {request.longitude}")
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Get user info
        cursor.execute("""
            SELECT id, username, email, browser_notifications_enabled,
                   alert_radius, home_area, work_area
            FROM users_info WHERE username = %s
        """, (current_user,))
        user = cast(Optional[Dict[str, Any]], cursor.fetchone())
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        user_id = user["id"]
        alert_radius = get_global_notification_radius_km()
        
        # Check location risk using your existing function
        risk_assessment = await check_location_risk(
            user_id, 
            request.latitude, 
            request.longitude,
            alert_radius
        )
        
        print(f"📊 Risk assessment: {risk_assessment}")

        # Send immediate alert if high risk using normalized assessment
        if risk_assessment.get("is_high_risk") and request.check_immediate:
            alert = RiskZoneAlert(
                user_id=user_id,
                username=user.get("username") or "",
                email=user.get("email") or "",
                latitude=request.latitude,
                longitude=request.longitude,
                address=request.address or f"Current location ({request.latitude}, {request.longitude})",
                risk_level=risk_assessment["risk_level"],
                safety_score=risk_assessment["safety_score"],
                high_risk_crimes=risk_assessment.get("high_risk_crimes", 0),
                alert_type="live_high_risk_zone",
                message=f"🚨 High risk detected at your current location! Safety score: {risk_assessment['safety_score']}%"
            )

            print("🚨 High risk detected - sending immediate alert")
            await send_alert_notification(alert)

            return {
                "alert_sent": True,
                "risk_assessment": risk_assessment,
                "message": "High risk detected - alert sent"
            }

        return {
            "alert_sent": False,
            "risk_assessment": risk_assessment,
            "message": "Location checked - no alert needed"
        }
        
    except Exception as e:
        print(f"❌ Error in location alert check: {e}")
        logger.error(f"Error checking location for alerts: {e}")
        raise HTTPException(status_code=500, detail="Failed to check location for alerts")
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()

@router.get("/status")
async def get_alert_status(current_user: str = Depends(get_username_from_token)):
    """Get user's alert subscription status"""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT 
                u.alert_preferences,
                u.alert_radius,
                u.monitor_live_location,
                COUNT(DISTINCT s.id) as active_subscriptions
            FROM users_info u
            LEFT JOIN alert_subscriptions s ON u.id = s.user_id AND s.is_active = TRUE
            WHERE u.username = %s
            GROUP BY u.id
        """, (current_user,))
        
        result = cast(Optional[Dict[str, Any]], cursor.fetchone())
        
        if not result:
            raise HTTPException(status_code=404, detail="User not found")
        
        preferences = json.loads(result.get("alert_preferences") or "{}")
        
        return {
            "is_subscribed": result["active_subscriptions"] > 0,
            "preferences": preferences,
            "alert_radius": result["alert_radius"],
            "monitor_live_location": bool(result["monitor_live_location"]),
            "monitor_saved_locations": preferences.get('monitor_saved_locations', True)
        }
        
    except Exception as e:
        logger.error(f"Database error getting alert status: {e}")
        raise HTTPException(status_code=500, detail="Failed to get alert status")
    finally:
        cursor.close()
        conn.close()

@router.post("/unsubscribe")
async def unsubscribe_from_alerts(current_user: str = Depends(get_username_from_token)):
    """Unsubscribe from all alerts"""
    import traceback
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        # Get user ID
        cursor.execute("SELECT id FROM users_info WHERE username = %s", (current_user,))
        user = cast(Optional[Dict[str, Any]], cursor.fetchone())
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        user_id = user["id"]
        
        # Deactivate all subscriptions
        cursor.execute("""
            UPDATE alert_subscriptions 
            SET is_active = FALSE 
            WHERE user_id = %s
        """, (user_id,))
        
        # Update user preferences
        cursor.execute("""
            UPDATE users_info 
            SET monitor_live_location = FALSE,
                updated_at = %s
            WHERE id = %s
        """, (datetime.now(), user_id))
        
        conn.commit()
        
        log_user_activity(
            activity_type="alerts_unsubscribed",
            username=current_user,
            user_id=user_id,
            activity_details={"message": "User unsubscribed from all alerts"}
        )
        
        return {"message": "✅ Successfully unsubscribed from all alerts"}
        
    except Exception as e:
        tb_str = traceback.format_exc()
        print(f"❌ Exception traceback: {tb_str}")
        logger.error(f"Database error unsubscribing from alerts: {e}\nTraceback:\n{tb_str}")
        raise HTTPException(status_code=500, detail=f"Failed to unsubscribe: {str(e)}")
    finally:
        cursor.close()
        conn.close()

async def monitor_saved_locations():
     """Background task to check saved locations and send alerts - FIXED VERSION"""
     conn = None
     cursor = None
     try:
        logger.info("🔄 Starting enhanced saved locations monitoring...")
        global_radius_km = get_global_notification_radius_km()

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Get users with active alert subscriptions - IMPROVED QUERY
        cursor.execute(
            """
            SELECT DISTINCT u.id, u.username, u.email, 
                   u.home_area, u.work_area, 
                   u.home_latitude, u.home_longitude,
                   u.work_latitude, u.work_longitude, 
                   u.alert_radius, u.browser_notifications_enabled,
                   s.id as subscription_id, s.is_active as subscription_active
                        FROM users_info u
            LEFT JOIN alert_subscriptions s ON u.id = s.user_id AND s.is_active = TRUE
            WHERE u.is_active = TRUE 
            AND u.incident_alerts_enabled = TRUE
            AND u.is_logged_in = TRUE
            AND u.last_activity_at IS NOT NULL
            AND u.last_activity_at >= (NOW() - INTERVAL 20 MINUTE)
            AND (u.home_latitude IS NOT NULL OR u.work_latitude IS NOT NULL
                 OR u.home_area IS NOT NULL OR u.work_area IS NOT NULL)
            """,
        )

        users = cursor.fetchall()

        logger.info(f"📊 Monitoring {len(users)} users with active subscriptions")

        for user in users:
            try:
                user_id = cast(Dict[str, Any], user).get("id")

                if not user_id:
                    continue

                # Check home location
                home_lat = cast(Dict[str, Any], user).get("home_latitude")
                home_lng = cast(Dict[str, Any], user).get("home_longitude")
                home_area = cast(Dict[str, Any], user).get("home_area")

                # FIX: Better coordinate handling for home
                if home_area and (home_lat is None or home_lng is None):
                    try:
                        logger.info(f"🔍 Fetching missing coordinates for home area: {home_area}")
                        coords = get_coordinates(home_area)
                        if coords:
                            home_lat, home_lng = coords
                            # Update user coordinates in database
                            cursor.execute(
                                "UPDATE users_info SET home_latitude = %s, home_longitude = %s WHERE id = %s",
                                (home_lat, home_lng, user_id),
                            )
                            logger.info(f"✅ Updated home coordinates for user {user_id}")
                    except Exception as e:
                        logger.error(f"❌ Error fetching home coordinates: {e}")
                        continue  # Skip this location if coordinates can't be fetched

                # Only process home location if we have valid coordinates
                if home_lat is not None and home_lng is not None:
                    try:
                        logger.info(f"🏠 Processing HOME location for user {user_id}: {home_area} at ({home_lat}, {home_lng})")
                        
                        # Get REAL safety data for home location (coord-based)
                        safety_data = await get_real_safety_data_from_endpoints(
                            float(home_lat),
                            float(home_lng),
                            home_area or "Home Location",
                        )

                        # Create risk assessment
                        risk_assessment = {
                            "safety_score": safety_data['safety_score'],
                            "risk_level": safety_data['risk_level'],
                            "risk_pct": safety_data['risk_pct'],
                            "total_crimes": safety_data['total_crimes'],
                            "high_risk_crimes": safety_data['high_risk_crimes'],
                            "high_risk_crimes_90d": safety_data.get('high_risk_crimes_90d', 0),
                            "medium_risk_crimes_90d": safety_data.get('medium_risk_crimes_90d', 0),
                            "last_90_days": safety_data.get('last_90_days', 0),
                            "dominant_crime_type": safety_data.get('dominant_crime_type'),
                            "is_high_risk": safety_data.get('is_high_risk', False),
                            "precautions": safety_data.get('precautions', 'General safety precautions advised.'),
                        }

                        # Check for NEW incidents strictly within the last 1 hour to prevent redundant reports.
                        # Haversine in meters (TiDB Serverless does not support ST_Distance_Sphere/POINT).
                        cursor.execute("""
                            SELECT COUNT(*) as recent_count
                            FROM crimes
                            WHERE ((6371000 * 2 * ASIN(SQRT(
                                       POWER(SIN(RADIANS((latitude - %s) / 2)), 2) +
                                       COS(RADIANS(%s)) * COS(RADIANS(latitude)) *
                                       POWER(SIN(RADIANS((longitude - %s) / 2)), 2)
                                   ))) <= %s
                                OR (LOWER(area) LIKE %s))
                              AND crime_date >= (NOW() - INTERVAL 1 HOUR)
                              AND (risk_level = 'High' OR risk_level = 'Medium')
                        """, (home_lat, home_lat, home_lng, global_radius_km * 1000, f"%{(home_area or '').lower()}%"))
                        
                        recent_check = cursor.fetchone()
                        has_fresh_incident = int(recent_check['recent_count'] or 0) > 0

                        # Background monitor ONLY triggers alerts if:
                        # 1. Area is High/Critical Risk (initial discovery)
                        # 2. OR there is a NEW incident in the last hour
                        if risk_assessment['is_high_risk'] or has_fresh_incident:
                            # Send alert for home location
                            await create_and_send_alert(
                                user,
                                "home",
                                risk_assessment,
                                float(home_lat),
                                float(home_lng),
                            )
                            logger.info(f"✅ Alert dispatched for HOME area (User: {user_id})")
                        else:
                            logger.info(f"⚪ Home area {home_area} is stable (No new incidents / Low risk). Skipping background alert.")
                    except Exception as e:
                        logger.error(f"❌ Error processing home location for user {user_id}: {e}")

                # Check work location - FIXED: Better coordinate handling
                work_lat = cast(Dict[str, Any], user).get("work_latitude")
                work_lng = cast(Dict[str, Any], user).get("work_longitude")
                work_area = cast(Dict[str, Any], user).get("work_area")

                # FIX: Better coordinate validation for work area
                if work_area and (work_lat is None or work_lng is None or work_lat == 0.0 or work_lng == 0.0):
                    try:
                        logger.info(f"🔍 Fetching missing/invalid coordinates for work area: {work_area}")
                        coords = get_coordinates(work_area)
                        if coords and len(coords) == 2:
                            work_lat, work_lng = coords
                            
                            # Validate coordinates are reasonable (not 0,0 and within valid ranges)
                            if (work_lat is not None and work_lng is not None and
                                float(work_lat) != 0.0 and float(work_lng) != 0.0 and
                                -90.0 <= float(work_lat) <= 90.0 and -180.0 <= float(work_lng) <= 180.0):
                                
                                # Update user coordinates in database
                                cursor.execute(
                                    "UPDATE users_info SET work_latitude = %s, work_longitude = %s WHERE id = %s",
                                    (work_lat, work_lng, user_id),
                                )
                                logger.info(f"✅ Updated work coordinates for user {user_id}: {work_lat}, {work_lng}")
                            else:
                                logger.warning(f"❌ Invalid coordinates received for work area {work_area}: {work_lat}, {work_lng}")
                                continue
                        else:
                            logger.warning(f"❌ No coordinates found for work area: {work_area}")
                            continue
                    except Exception as e:
                        logger.error(f"❌ Error fetching work coordinates: {e}")
                        continue  # Skip this location if coordinates can't be fetched

                # Only process work location if we have valid coordinates
                if work_lat is not None and work_lng is not None:
                    try:
                        logger.info(f"💼 Processing WORK location for user {user_id}: {work_area} at ({work_lat}, {work_lng})")
                        
                        # Get REAL safety data for work location (coord-based)
                        safety_data = await get_real_safety_data_from_endpoints(
                            float(work_lat),
                            float(work_lng),
                            work_area or "Work Location",
                        )

                        # Create risk assessment
                        risk_assessment = {
                            "safety_score": safety_data['safety_score'],
                            "risk_level": safety_data['risk_level'],
                            "risk_pct": safety_data['risk_pct'],
                            "total_crimes": safety_data['total_crimes'],
                            "last_90_days": safety_data.get('last_90_days', 0),
                            "high_risk_crimes_90d": safety_data.get('high_risk_crimes_90d', 0),
                            "medium_risk_crimes_90d": safety_data.get('medium_risk_crimes_90d', 0),
                            "high_risk_crimes": safety_data['high_risk_crimes'],
                            "dominant_crime_type": safety_data.get('dominant_crime_type'),
                            "is_high_risk": safety_data.get('is_high_risk', False),
                            "precautions": safety_data.get('precautions', 'General safety precautions advised.'),
                        }

                        # Check for NEW incidents strictly within the last 1 hour
                        # (Haversine in meters; TiDB has no ST_Distance_Sphere.)
                        cursor.execute("""
                            SELECT COUNT(*) as recent_count
                            FROM crimes
                            WHERE ((6371000 * 2 * ASIN(SQRT(
                                       POWER(SIN(RADIANS((latitude - %s) / 2)), 2) +
                                       COS(RADIANS(%s)) * COS(RADIANS(latitude)) *
                                       POWER(SIN(RADIANS((longitude - %s) / 2)), 2)
                                   ))) <= %s
                                OR (LOWER(area) LIKE %s))
                              AND crime_date >= (NOW() - INTERVAL 1 HOUR)
                              AND (risk_level = 'High' OR risk_level = 'Medium')
                        """, (work_lat, work_lat, work_lng, global_radius_km * 1000, f"%{(work_area or '').lower()}%"))
                        
                        recent_check_work = cursor.fetchone()
                        has_fresh_incident_work = int(recent_check_work['recent_count'] or 0) > 0

                        if risk_assessment['is_high_risk'] or has_fresh_incident_work:
                            # Send alert for work location
                            await create_and_send_alert(
                                user,
                                "work", 
                                risk_assessment,
                                float(work_lat),
                                float(work_lng),
                            )
                            logger.info(f"✅ Alert dispatched for WORK area (User: {user_id})")
                        else:
                            logger.info(f"⚪ Work area {work_area} is stable. Skipping background alert.")
                    except Exception as e:
                        logger.error(f"❌ Error processing work location for user {user_id}: {e}")

            except Exception as e:
                logger.error(
                    f"❌ Error monitoring locations for user {cast(Dict[str, Any], user).get('username', 'unknown')}: {e}"
                )
                continue

        conn.commit()

     except Exception as e:
        logger.error(f"❌ Error in enhanced monitor_saved_locations: {e}")
        if conn:
            conn.rollback()
     finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()


async def get_real_safety_data_from_endpoints(latitude: float, longitude: float, address: Optional[str] = None, radius_km: Optional[float] = None) -> Dict[str, Any]:
    try:
        print(f"🔍 Fetching REAL safety data for: {latitude}, {longitude}")

        effective_radius_km = float(radius_km) if radius_km is not None else get_global_notification_radius_km()
        coord_stats = await get_safety_stats_by_coords(latitude, longitude, effective_radius_km)

        # ── Area Name Priority: Use provided address if valid, fallback to reverse geocode ──
        area_name = address if address and address != "Unknown" and address != "Work Location" and address != "Home Location" else None
        if not area_name:
            area_name = await get_area_name_from_coordinates(latitude, longitude)
        
        print(f"📍 Area identified: {area_name}")

        # Unified risk score from shared scorer
        risk_pct     = coord_stats.get('risk_pct', 50.0)
        safety_score = coord_stats.get('safety_score', 50.0)
        risk_level   = coord_stats.get('risk_level', 'Unknown')
        total_crimes = coord_stats.get('total_crimes', 0)
        high_risk_crimes = coord_stats.get('high_risk_count', 0)
        high_risk_crimes_90d = coord_stats.get('high_risk_count_90d', 0)
        medium_risk_crimes_90d = coord_stats.get('medium_risk_count_90d', 0)
        last_90_days = coord_stats.get('last_90_days', 0)
        dominant_crime_type = coord_stats.get('dominant_crime_type')

        risk_level_text = str(risk_level).lower()
        # Strictly follow the 51% risk score boundary for 'high risk' alerts
        is_high_risk = risk_pct >= 51 or ("critical" in risk_level_text)

        print(
            f"🎯 FINAL ASSESSMENT (Unified) - Area: {area_name}, "
            f"Risk: {risk_pct}%, Level: {risk_level}, Crimes (365d): {total_crimes}, "
            f"High-risk: {high_risk_crimes}, IsHighRisk: {is_high_risk}"
        )

        return {
            'safety_score': safety_score,
            'risk_pct': risk_pct,
            'risk_level': risk_level,
            'is_high_risk': is_high_risk,
            'total_crimes': total_crimes,
            'high_risk_crimes': high_risk_crimes,
            'high_risk_crimes_90d': high_risk_crimes_90d,
            'medium_risk_crimes_90d': medium_risk_crimes_90d,
            'last_90_days': last_90_days,
            'dominant_crime_type': dominant_crime_type,
            'area_name': area_name,
            'source': 'unified_coord_radius'
        }

    except Exception as e:
        print(f"❌ Error in safety data: {e}")
        return {
            'safety_score': 50.0,
            'risk_pct': 50.0,
            'risk_level': 'Unknown',
            'is_high_risk': False,
            'total_crimes': 0,
            'high_risk_crimes': 0,
            'dominant_crime_type': None,
            'area_name': 'Unknown',
            'source': 'error_fallback'
        }

async def create_and_send_alert(user_data, location_type, risk_assessment, lat, lng):
    conn = None
    cursor = None
    try:
        safety_score = risk_assessment["safety_score"]
        risk_level = risk_assessment["risk_level"]
        
        # Get area name: Prioritize saved area name for saved locations
        saved_area = user_data.get(f"{location_type}_area")
        current_area_hint = user_data.get("current_area")
        
        # If we have a hint from the sensor (like 'Rehman Villas' or 'DHA Phase 4') use it!
        if location_type == "current" and current_area_hint and current_area_hint != "Unknown":
            area_name = current_area_hint
        else:
            area_name = saved_area if saved_area and saved_area != "Unknown" else await get_area_name_from_coordinates(lat, lng)
        
        # Store a display name that keeps specific detail if available
        display_area_title = area_name
        
        # Apply Universal Normalization for radius/incidents query basis
        normalized_q_name = normalize_area_name(area_name)
        
        # ── Fetch sub-areas and richer notification data early to avoid NameError ──
        subareas_list: List[Dict[str, Any]] = []
        area_translit_val: Optional[str] = None
        area_urdu_val: Optional[str] = None
        
        # If display name is generic but we have subareas, pick the best subarea for the title
        if (not display_area_title or display_area_title == "Unknown") and subareas_list:
            display_area_title = subareas_list[0].get('name', display_area_title)
        
        # Final fallback for generic names
        if not display_area_title or display_area_title == "Unknown":
            display_area_title = f"{location_type.title()} Location"
            
        # Re-assign area_name to the specific title for templates
        area_name = display_area_title

        # --- Multi-Level Matching: Radius + Specific Name + Parent Discovery ---
        # 1. Spatial Search Params (honor global configured radius)
        effective_radius_km = get_global_notification_radius_km()
        spatial_radius_m = max(100, int(round(float(effective_radius_km) * 1000.0)))
        # Haversine in meters (TiDB Serverless doesn't support ST_Distance_Sphere/POINT).
        spatial_filter = (
            "(6371000 * 2 * ASIN(SQRT("
            "POWER(SIN(RADIANS((latitude - %s) / 2)), 2) + "
            "COS(RADIANS(%s)) * COS(RADIANS(latitude)) * "
            "POWER(SIN(RADIANS((longitude - %s) / 2)), 2)"
            "))) <= %s"
        )
        spatial_params = (float(lat), float(lat), float(lng), spatial_radius_m)
        
        # 2. Name Search Params (Specific + Phase Fallback)
        name_filters = ["LOWER(area) LIKE %s"]
        name_params = [area_like_pattern(area_name).lower()]
        
        # Extract Phase (e.g. 'Sec FF Ph 4' -> 'DHA Phase 4')
        an_lower = area_name.lower()
        if "sec " in an_lower and (" ph " in an_lower or " phase " in an_lower):
            phase_trigger = "phase" if "phase" in an_lower else "ph"
            try:
                # Find the number following 'ph' or 'phase'
                parts = an_lower.split(phase_trigger)
                if len(parts) > 1:
                    phase_num = parts[1].strip().split()[0].strip()
                    if phase_num:
                        name_filters.append("LOWER(area) LIKE %s")
                        name_params.append(f"%dha phase {phase_num}%")
                        name_filters.append("LOWER(area) LIKE %s")
                        name_params.append(f"%ph {phase_num}%")
            except Exception: pass

        name_filter_group = f"({' OR '.join(name_filters)})"
        
        # Determine if this is a radius-based match (common for Live Alerts)
        _was_radius = "radius" in str(risk_assessment.get('scope_mode', '')).lower() or location_type == "current"
        
        # Combined filter for contextual queries
        # For live current-location alerts, use SPATIAL-ONLY so radius actually controls results
        # For background home/work monitoring, use OR to include area names as fallback
        if location_type == "current":
            active_filter = spatial_filter
            active_params = tuple(spatial_params)
        else:
            active_filter = f"({spatial_filter} OR {name_filter_group})" if _was_radius else name_filter_group
            active_params = (spatial_params + tuple(name_params)) if _was_radius else tuple(name_params)

        # ── Fetch sub-areas and richer notification data ─────────────────────
        try:
            _translit_conn = get_db_connection()
            _translit_cursor = _translit_conn.cursor(dictionary=True)

            # Get main area translit/urdu
            _translit_cursor.execute(
                f"SELECT area_translit, area_urdu FROM crimes WHERE {name_filter_group} AND area_translit IS NOT NULL GROUP BY area_translit, area_urdu ORDER BY COUNT(*) DESC LIMIT 1",
                tuple(name_params)
            )
            _translit_row = _translit_cursor.fetchone()
            if _translit_row:
                area_translit_val = cast(Dict[str, Any], _translit_row).get('area_translit')
                area_urdu_val = cast(Dict[str, Any], _translit_row).get('area_urdu')
            
            # Fetch ALL sub-areas for this MAIN area
            _translit_cursor.execute(
                f"""SELECT area_translit, area_urdu, COUNT(*) as total_crimes, 
                           SUM(CASE WHEN risk_level = 'High' THEN 1 ELSE 0 END) as high_risk_count, 
                           SUM(CASE WHEN risk_level = 'Medium' THEN 1 ELSE 0 END) as medium_risk_count, 
                           COUNT(DISTINCT crime_type) as unique_crime_types 
                    FROM crimes WHERE {active_filter} AND area_translit IS NOT NULL AND area_translit != '' 
                      AND crime_date >= (NOW() - INTERVAL 365 DAY) 
                    GROUP BY area_translit, area_urdu 
                    ORDER BY high_risk_count DESC, total_crimes DESC LIMIT 10""",
                active_params
            )
            subarea_rows = _translit_cursor.fetchall()
            for row in subarea_rows:
                rd = cast(Dict[str, Any], row)
                _summary = calculate_unified_risk_summary({"total_crimes": rd['total_crimes'], "high_risk_count": rd['high_risk_count'], "medium_risk_count": rd['medium_risk_count']}, 365)
                subareas_list.append({
                    'name': rd.get('area_translit', 'Unknown'),
                    'urdu': rd.get('area_urdu'),
                    'total': int(rd.get('total_crimes', 0)),
                    'high_risk': int(rd.get('high_risk_count', 0)),
                    'risk_level': str(_summary.get('risk_level', 'Moderate')),
                    'risk_pct': float(_summary.get('risk_score', 50.0))
                })
            
            _translit_cursor.close()
            _translit_conn.close()
        except Exception as _te:
            logger.warning(f"Could not fetch subareas for '{area_name}': {_te}")

        # ── Fetch top crime types and consistent 90d/365d area counts ─────────
        top_crimes_list: List[Dict[str, Any]] = []
        recent_7d_crimes = 0
        incidents_90d = 0
        incidents_365d = 0
        high_risk_90d = 0
        medium_risk_90d = 0
        high_risk_365d = 0
        medium_risk_365d = 0
        unique_crime_types = 0

        try:
            _crimes_conn = get_db_connection()
            _crimes_cursor = _crimes_conn.cursor(dictionary=True)

            # Area counts (last 90 days)
            _crimes_cursor.execute(f"SELECT COUNT(*) as total_90d, SUM(CASE WHEN risk_level = 'High' THEN 1 ELSE 0 END) as high_90d, SUM(CASE WHEN risk_level = 'Medium' THEN 1 ELSE 0 END) as medium_90d FROM crimes WHERE {active_filter} AND crime_date >= (NOW() - INTERVAL 90 DAY)", active_params)
            _a90 = _crimes_cursor.fetchone()
            if _a90:
                incidents_90d = int(_a90.get('total_90d', 0) or 0)
                high_risk_90d = int(_a90.get('high_90d', 0) or 0)
                medium_risk_90d = int(_a90.get('medium_90d', 0) or 0)

            # Area counts (last 365 days)
            _crimes_cursor.execute(f"SELECT COUNT(*) as total_365d, SUM(CASE WHEN risk_level = 'High' THEN 1 ELSE 0 END) as high_365d, SUM(CASE WHEN risk_level = 'Medium' THEN 1 ELSE 0 END) as medium_365d FROM crimes WHERE {active_filter} AND crime_date >= (NOW() - INTERVAL 365 DAY)", active_params)
            _a365 = _crimes_cursor.fetchone()
            if _a365:
                incidents_365d = int(_a365.get('total_365d', 0) or 0)
                high_risk_365d = int(_a365.get('high_365d', 0) or 0)
                medium_risk_365d = int(_a365.get('medium_365d', 0) or 0)

            # Top crime types
            _crimes_cursor.execute(f"SELECT crime_type, COUNT(*) as total_count, SUM(CASE WHEN risk_level = 'High' THEN 1 ELSE 0 END) as high_count FROM crimes WHERE {active_filter} AND crime_date >= (NOW() - INTERVAL 90 DAY) GROUP BY crime_type ORDER BY high_count DESC, total_count DESC LIMIT 6", active_params)
            for tc_row in (_crimes_cursor.fetchall() or []):
                tc = cast(Dict[str, Any], tc_row)
                top_crimes_list.append({
                    'crime_type': tc.get('crime_type', 'Unknown'),
                    'count': int(tc.get('total_count', 0)),
                    'risk_contribution': "High" if int(tc.get('high_count', 0)) > 0 else "Medium"
                })

            # Recent 7-day spike count
            _crimes_cursor.execute(f"SELECT COUNT(*) as cnt FROM crimes WHERE {active_filter} AND crime_date >= (NOW() - INTERVAL 7 DAY)", active_params)
            _r7 = _crimes_cursor.fetchone()
            if _r7:
                recent_7d_crimes = int(cast(Dict[str, Any], _r7).get('cnt', 0) or 0)

            # Get unique crime types
            _crimes_cursor.execute(f"SELECT COUNT(DISTINCT crime_type) as cnt FROM crimes WHERE {active_filter}", active_params)
            _uct = _crimes_cursor.fetchone()
            unique_crime_types = int(cast(Dict[str, Any], _uct).get('cnt', 0) or 0) if _uct else 0

            _crimes_cursor.close()
            _crimes_conn.close()
        except Exception as _ce:
            logger.warning(f"Could not fetch stats for '{area_name}': {_ce}")

        # Recalculate unified score using broad area stats (Radius + Parent discovery)
        area_stats_dict = {
            'total_crimes': incidents_365d,
            'high_risk_count': high_risk_365d,
            'medium_risk_count': medium_risk_365d,
            'last_90_days': incidents_90d
        }
        unified_summary = calculate_unified_risk_summary(area_stats_dict, 365)
        safety_score = float(unified_summary.get('safety_score', 50.0))
        risk_level = str(unified_summary.get('risk_level', 'Moderate'))
        
        # ── Smart Risk Rule: Historical vs Active ──
        if incidents_90d == 0 and incidents_365d > 0:
            risk_level = f"{risk_level} (Historical)"
        elif incidents_90d > 0:
            risk_level = f"{risk_level} (Active)"

        risk_assessment['risk_score'] = float(unified_summary.get('risk_score', 50.0))
        no_recent_but_historical = (incidents_90d == 0 and incidents_365d > 0)

        # ── Time-of-day risk label ─────────────────────────────────────────────
        _current_hour = datetime.now().hour
        if 5 <= _current_hour <= 11:
            time_risk_label = "Morning (moderate risk)"
        elif 12 <= _current_hour <= 16:
            time_risk_label = "Afternoon (lower risk)"
        elif 17 <= _current_hour <= 20:
            time_risk_label = "Evening (elevated risk)"
        else:
            time_risk_label = "Night (highest risk period)"

        # Severity and alert_type logic
        severity = "low"
        alert_type = "safe_area"
        _rp = risk_assessment.get('risk_score', 100.0 - safety_score)

        if _rp > 20 or safety_score < 75:
            if safety_score < 25 or high_risk_365d >= 10 or _rp > 75:
                severity = "critical"
                alert_type = "critical_risk_zone"
            elif safety_score < 45 or high_risk_365d >= 5 or _rp > 50:
                severity = "high"
                alert_type = "high_risk_zone"
            else:
                severity = "medium"
                alert_type = "medium_risk_zone"
        
        # ── Human-readable alert trigger reason (Trigger Transparency) ─────────
        _trigger_method = f"Within {effective_radius_km:g} km radius" if _was_radius else "Area name match"
        _7d_bit = f", incl. {recent_7d_crimes} in the last 7 days" if recent_7d_crimes > 0 else ""
        _top_crime_bit = f" — {top_crimes_list[0]['crime_type']} is the most frequent" if top_crimes_list else ""
        
        # ── Proximity Risk Awareness ──
        riskiest_neighbor = None
        current_area_clean = area_name.strip().lower()
        if subareas_list:
            # Sort by high_risk incidents first, then total to find the most impactful neighbor
            sorted_neighbors = sorted(subareas_list, key=lambda x: (x.get('high_risk', 0), x.get('total', 0)), reverse=True)
            for sn in sorted_neighbors:
                sn_name_clean = str(sn.get('name', '')).strip().lower()
                # If they are a DIFFERENT area name, they are a good proximity candidate
                if current_area_clean != sn_name_clean and sn_name_clean not in current_area_clean:
                    if sn.get('risk_level', '').lower() in ('high', 'critical', 'moderate', 'medium') or sn.get('total', 0) > 10:
                        riskiest_neighbor = sn
                        break
        
        # If no distinct-name neighbor found, use the first high/moderate subarea regardless of name overlap 
        # (e.g. if we are in "Phase 4 Block F", its riskiest context might be "Phase 4" generally)
        if not riskiest_neighbor and subareas_list:
            sorted_by_risk = sorted(subareas_list, key=lambda x: (x.get('risk_pct', 0), x.get('total', 0)), reverse=True)
            if sorted_by_risk and sorted_by_risk[0].get('name').lower() != current_area_clean:
                riskiest_neighbor = sorted_by_risk[0]
        
        # If still no neighbor found but we identified a Phase-related name, use the Phase broad name as a logical neighbor
        if not riskiest_neighbor and ("phase" in an_lower or " ph " in an_lower or an_lower.endswith(" ph")):
            phase_trigger = "phase" if "phase" in an_lower else "ph"
            parts = an_lower.split(phase_trigger)
            if len(parts) > 1:
                phase_num_match = re.match(r'^(\d+)', parts[1].strip())
                if phase_num_match:
                    phase_num = phase_num_match.group(1)
                    riskiest_neighbor = {"name": f"DHA Phase {phase_num}", "total": incidents_365d}
        
        # LOG Neighbor discovery for debugging
        if riskiest_neighbor:
            logger.info(f"📍 Proximity Neighbor for {area_name}: {riskiest_neighbor.get('name')} (Total: {riskiest_neighbor.get('total')})")
        else:
            logger.info(f"📍 No distinct proximity neighbor found for {area_name} among {len(subareas_list)} subareas.")

        # ── Final Trigger Reason Logic ──
        if no_recent_but_historical:
            proximity_bit = ""
            if riskiest_neighbor:
                neighbor_name = riskiest_neighbor.get('name', 'N/A')
                proximity_bit = f" This area is near {neighbor_name}, which has a significant history of reported incidents ({incidents_365d} cases)."
            
            alert_trigger_reason = (
                f"{_trigger_method}: Elevated historical crime activity.{proximity_bit} "
                f"No recent incidents have been recorded in the last 90 days, but historical patterns indicate elevated risk."
            )
        elif riskiest_neighbor and incidents_90d == 0:
            alert_trigger_reason = (
                f"{_trigger_method}: Proximity Alert. While your immediate surroundings show low recent activity, "
                f"you are currently near {riskiest_neighbor['name']}, which has an elevated crime history ({riskiest_neighbor['total']} incidents)."
            )
        elif risk_level in ("High", "Critical") or severity in ("high", "critical"):
            proximity_context = ""
            if riskiest_neighbor and riskiest_neighbor.get('name'):
                proximity_context = f" (Nearby context: Observed patterns near {riskiest_neighbor['name']})"
            
            alert_trigger_reason = (
                f"{_trigger_method}: {high_risk_90d} high-risk incident(s) recorded near your "
                f"{location_type} location in the last 90 days{_7d_bit}{_top_crime_bit}{proximity_context}."
            )
        elif risk_level in ("Medium", "Moderate") or severity == "medium":
            alert_trigger_reason = (
                f"{_trigger_method}: Elevated crime activity ({incidents_90d} incident(s) "
                f"in the last 90 days{_7d_bit}) in your {location_type} area warrants caution{_top_crime_bit}."
            )
        else:
            alert_trigger_reason = (
                f"{_trigger_method}: No significant risk detected near your {location_type} location "
                f"({incidents_90d} routine incident(s) in 90 days)."
            )
        
        cooldown_key = f"{user_data['id']}_{location_type}"
        if severity == "low":
            if cooldown_key in alert_cooldown_cache:
                last_time = alert_cooldown_cache[cooldown_key]
                if (datetime.now() - last_time).total_seconds() < SAFE_AREA_ALERT_CONFIG['cooldown_minutes'] * 60:
                    return
            alert_cooldown_cache[cooldown_key] = datetime.now()
        else:
            alert_cooldown_cache.pop(cooldown_key, None)
        
        location_name = area_name
        address = f"{location_name} ({lat:.4f}, {lng:.4f})"
        
        alert_data = {
            "id": user_data.get("id"), "username": user_data.get("username"), "email": user_data.get("email"),
            "area_type": location_type, "area_name": area_name, "address": address,
            "safety_score": safety_score, "risk_pct": _rp, "risk_level": risk_level,
            "radius_km": effective_radius_km,
            "incidents_90d": incidents_90d, "high_risk_90d": high_risk_90d, "recent_7d_crimes": recent_7d_crimes,
            "total_crimes": incidents_90d, "total_crimes_365": incidents_365d,
            "high_risk_crimes": high_risk_90d, "medium_risk_crimes": medium_risk_90d,
            "unique_crime_types": unique_crime_types, "top_crimes_list": top_crimes_list,
            "dominant_crime": top_crimes_list[0]['crime_type'] if top_crimes_list else "Incidents of concern",
            "dominant_crime_type": top_crimes_list[0]['crime_type'] if top_crimes_list else "Incidents of concern",
            "time_risk_label": time_risk_label, "alert_trigger_reason": alert_trigger_reason,
            "no_recent_but_historical": no_recent_but_historical, "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "subareas": subareas_list
        }

        # Select template
        if location_type == "current" and severity != "low":
            template_data = alert_notification_system.email_templates.live_location_alert(alert_data)
        elif severity == "low":
            template_data = alert_notification_system.email_templates.safe_area_alert(alert_data)
        elif alert_type in ("high_risk_zone", "critical_risk_zone"):
            template_data = alert_notification_system.email_templates.high_risk_alert_enhanced(alert_data)
        else:
            template_data = alert_notification_system.email_templates.high_risk_alert(alert_data)
        # Create title and message based on severity
        title_prefix = "📍 LIVE ALERT: " if location_type == "current" else ""
        if severity == "low":
            title = f"{title_prefix}✅ Safe Area - {location_name}"
            message = f"Your {location_type} location is safe. Safety score: {safety_score}%. Risk level: {risk_level}."
        elif severity == "medium":
            title = f"{title_prefix}⚠️ Medium Risk Alert - {location_name}"
            message = f"Medium risk detected at your {location_type} location. Safety score: {safety_score}%. Risk level: {risk_level}. Stay alert."
        elif severity == "high":
            title = f"{title_prefix}🚨 High Risk Alert - {location_name}"
            message = f"High risk detected at your {location_type} location. Safety score: {safety_score}%. Risk level: {risk_level}."
        else:  # critical
            title = f"{title_prefix}🚨 CRITICAL Risk Alert - {location_name}"
            message = f"Critical risk detected at your {location_type} location. Safety score: {safety_score}%. Risk level: {risk_level}. Immediate caution advised!"

        # Persistence to MySQL
        _p_conn = get_db_connection()
        _p_cursor = _p_conn.cursor()
        _p_cursor.execute("""
            INSERT INTO user_alerts 
            (user_id, title, message, alert_type, area, severity, is_read, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            user_data["id"],
            title,
            message,
            alert_type,
            area_name,
            severity,
            0,
            datetime.now()
        ))
        _p_conn.commit()
        _p_cursor.close()
        _p_conn.close()
        
        # Compute overall area risk_pct from risk_assessment (Poisson-based)
        irp = risk_assessment.get('risk_pct')
        if irp is not None:
            area_risk_pct = float(irp)
        else:
            area_risk_pct = float(round(100.0 - float(safety_score)))

        alert = RiskZoneAlert(
            user_id=user_data["id"],
            username=user_data["username"],
            email=user_data["email"],
            phone=user_data.get("phone_number"),
            latitude=lat,
            longitude=lng,
            address=address,
            area_translit=None,
            area_urdu=None,
            risk_level=risk_level,
            safety_score=safety_score,
            risk_pct=area_risk_pct,
            high_risk_crimes=high_risk_90d,
            medium_risk_crimes=medium_risk_90d,
            high_risk_crimes_90d=high_risk_90d,
            medium_risk_crimes_90d=medium_risk_90d,
            last_90_days=incidents_90d,
            total_crimes=incidents_90d,
            total_crimes_365=incidents_365d,
            no_recent_but_historical=(incidents_90d == 0 and incidents_365d > 0),
            subareas=subareas_list if subareas_list else None,
            top_crimes_list=top_crimes_list if top_crimes_list else None,
            dominant_crime_type=top_crimes_list[0]['crime_type'] if top_crimes_list else "Incidents of concern",
            recent_7d_crimes=recent_7d_crimes,
            time_risk_label=time_risk_label,
            alert_trigger_reason=alert_trigger_reason,
            alert_type=alert_type,
            severity=severity,
            location_type=location_type,
            radius_km=effective_radius_km,
            message=message,
            precautions=risk_assessment.get("precautions", "Stay alert and aware of your surroundings.")
        )
        
        if severity == "low":
            logger.info(f"⚪ Skipping individual 'Safe Area' notification for user {user_data['username']} (deferred to weekly report)")
        else:
            await send_alert_notification(alert)
        
        logger.info(f"✅ {alert_type} alert created and sent for user {user_data['username']} - {location_name}")
        
    except Exception as e:
        logger.error(f"❌ Error creating alert for user {user_data.get('username', 'unknown')}: {e}")
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()

def reverse_geocode(latitude: float, longitude: float) -> Dict[str, Any]:
    try:
        response = requests.get(
            "https://nominatim.openstreetmap.org/reverse",
            params={
                "lat": latitude,
                "lon": longitude,
                "format": "json",
                "addressdetails": 1,
                "zoom": 18
            },
            timeout=10,
        )
        response.raise_for_status()
        return cast(Dict[str, Any], response.json())
    except Exception as e:
        logger.error(f"Error in reverse_geocode: {e}")
        return {}



async def get_area_name_from_coordinates(lat: float, lng: float) -> str:
    try:
        # Run the synchronous request in a thread pool
        from typing import Callable
        data = await asyncio.to_thread(cast(Callable[..., Dict[str, Any]], reverse_geocode), lat, lng)
        
        if not data or "error" in data:
            if data and data.get("display_name"):
                return data["display_name"]
            return "Unknown Area"
        
        # Extract area name from address components
        address = data.get('address', {})

        
        # Try to get the most specific location name
        area_name = (
            address.get('suburb') or
            address.get('neighbourhood') or
            address.get('quarter') or
            address.get('city_district') or
            address.get('town') or
            address.get('city') or
            address.get('county') or
            data.get('display_name', 'Unknown').split(',')[0]
        )
        
        print(f"Reverse geocoded ({lat}, {lng}) to: {area_name}")
        return area_name
        
    except Exception as e:
        print(f"Error getting area name from coordinates: {e}")
        return "Unknown Area"




async def get_crime_data_from_endpoint(lat: float, lng: float, area_name: str) -> Dict[str, Any]:
    """Get crime data in vicinity; remove area string OR condition to avoid over-counting."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        radius_km = 2.0
        # Calculate bounding box for the radius (same approach as risk checks)
        earth_radius = 6371
        lat_range = (radius_km / earth_radius) * (180 / 3.14159)
        lng_range = (radius_km / (earth_radius * 3.14159 / 180 * abs(3.14159/180 * lat))) if lat != 0 else (radius_km / earth_radius) * (180 / 3.14159)

        cursor.execute(
            """
            SELECT 
                COUNT(*) as total_crimes,
                SUM(CASE WHEN risk_level = 'High' THEN 1 ELSE 0 END) as high_risk_count,
                SUM(CASE WHEN risk_level = 'Medium' THEN 1 ELSE 0 END) as medium_risk_count,
                COUNT(DISTINCT crime_type) as unique_crime_types
            FROM crimes 
            WHERE latitude BETWEEN %s AND %s 
              AND longitude BETWEEN %s AND %s
              AND SQRT(POW(69.1 * (latitude - %s), 2) + POW(69.1 * (%s - longitude) * COS(latitude / 57.3), 2)) <= %s
            """,
            (lat - lat_range, lat + lat_range, lng - lng_range, lng + lng_range, lat, lng, radius_km),
        )

        result = cursor.fetchone()

        if result:
            result_dict = cast(Dict[str, Any], result)
            return {
                'total_crimes': result_dict.get('total_crimes', 0) or 0,
                'high_risk_count': result_dict.get('high_risk_count', 0) or 0,
                'medium_risk_count': result_dict.get('medium_risk_count', 0) or 0,
                'unique_crime_types': result_dict.get('unique_crime_types', 0) or 0,
            }

        return {'total_crimes': 0, 'high_risk_count': 0, 'medium_risk_count': 0}

    except Exception as e:
        print(f"Error getting crime data: {e}")
        return {'total_crimes': 0, 'high_risk_count': 0, 'medium_risk_count': 0}


async def get_area_safety_score_from_endpoint(area_name: str) -> Dict[str, Any]:
    """Deprecated: kept for compatibility; prefer get_safety_stats_by_coords."""
    try:
        print(f"⚠️ get_area_safety_score_from_endpoint called for {area_name} - returning placeholder to avoid inflated counts")
        return {'safety_score': 50.0, 'risk_level': 'Unknown', 'total_crimes': 0, 'high_risk_count': 0, 'medium_risk_count': 0}
    except Exception:
        return {'safety_score': 50.0, 'risk_level': 'Unknown'}


async def send_safe_area_notification(alert: RiskZoneAlert):
    """Send safe area notifications via email and browser push - UPDATED VERSION"""
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Get user notification preferences - REMOVE SMS FIELDS
        cursor.execute("""
            SELECT email, browser_notifications_enabled 
            FROM users_info 
            WHERE id = %s
        """, (alert.user_id,))
        
        user = cast(Optional[Dict[str, Any]], cursor.fetchone())
        
        if not user:
            logger.warning(f"User not found for safe area notification: {alert.user_id}")
            return
        
        user_email = cast(Dict[str, Any], user).get("email")
        # Respect independent toggles from users_info
        email_alerts_enabled = bool(cast(Dict[str, Any], user).get("email_alerts_enabled", True))
        browser_notifications_enabled = bool(cast(Dict[str, Any], user).get("browser_notifications_enabled", True))
        
        # Send formatted safe area email alert
        email_success = False
        if user_email and email_alerts_enabled:
            # Check if the method exists in your AlertNotificationSystem
            if hasattr(alert_notification_system, 'send_alert_email'):
                email_success = await alert_notification_system.send_alert_email(alert, user_email)
            else:
                logger.error("send_alert_email method not found in AlertNotificationSystem")
        
        # Send browser push notification instead of SMS
        browser_success = False
        if browser_notifications_enabled:
            # Check if the method exists in your AlertNotificationSystem
            if hasattr(alert_notification_system, 'send_browser_notification'):
                browser_success = await alert_notification_system.send_browser_notification(alert, cast(Dict[str, Any], user))
            else:
                logger.error("send_browser_notification method not found in AlertNotificationSystem")
        
        # Log the safe area alert - UPDATE SENT_VIA FIELD
        cursor.execute("""
            INSERT INTO alert_notifications 
            (user_id, alert_type, message, sent_via, created_at, success_status, safety_score)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (
            alert.user_id,
            alert.alert_type,
            alert.message,
            'both' if (email_success and browser_success) else 'email' if email_success else 'browser' if browser_success else 'none',
            datetime.now(),
            'success' if (email_success or browser_success) else 'failed',
            alert.safety_score
        ))
        
        conn.commit()
        logger.info(f"✅ Safe area notification sent for user {alert.user_id}")
        
    except Exception as e:
        logger.error(f"❌ Error sending safe area notification: {e}")
        if conn:
            conn.rollback()
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()


async def send_alert_notification(alert: RiskZoneAlert):
    """Send alert notifications via email and browser push - FIXED VERSION"""
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Get complete user data including id
        cursor.execute(
            """
            SELECT id, username, email, browser_notifications_enabled, email_alerts_enabled, alert_preferences
            FROM users_info 
            WHERE id = %s
            """,
            (alert.user_id,),
        )

        user_row = cursor.fetchone()

        if not user_row:
            print("❌ User not found for alert notification")
            return

        user_data = cast(Dict[str, Any], user_row)

        # Respect the system-wide alert policy for risk-based alerts.
        # Weekly reports are handled separately and should not be blocked here.
        if alert.alert_type not in {"weekly_safety_report", "safe_area"} and not meets_alert_threshold(str(alert.risk_level or "Low")):
            logger.info(
                f"⚪ Skipping alert for user {alert.user_id} due to global threshold policy "
                f"(alert_type={alert.alert_type}, risk_level={alert.risk_level}, policy={get_alert_threshold_policy()})"
            )
            return {
                "email_sent": False,
                "browser_sent": False,
                "alert_message": alert.message,
                "skipped_by_threshold": True,
            }

        category = _resolve_alert_category(alert)
        channel_prefs = _load_alert_channel_preferences(user_data)

        # Send email notification
        email_success = False
        user_email = user_data.get('email')
        email_alerts_enabled = bool(channel_prefs.get(category, {}).get('email', bool(user_data.get('email_alerts_enabled', True))))
        
        # CRITICAL REFINEMENT: Immediate email alerts are only sent for LIVE (current) locations 
        # OR for specific URGENT new incidents discovered near saved locations.
        # Periodic "status" updates for home/work locations are deferred to weekly reports.
        is_live_alert = alert.location_type == "current"
        is_new_incident = alert.alert_type == "new_incident_alert"
        
        if user_email and email_alerts_enabled and (is_live_alert or is_new_incident):
            if hasattr(alert_notification_system, 'send_alert_email'):
                email_success = await alert_notification_system.send_alert_email(alert, user_email)
                print(f"✅ Email notification sent: {email_success}")
        elif user_email and email_alerts_enabled and not is_live_alert and not is_new_incident:
            logger.info(f"⚪ Skipping immediate email for saved location ({alert.location_type}) for user {user_data.get('username')}. Deferred to weekly report.")
            email_success = False # Still False as it wasn't sent, but documented why.

        # Now call send_browser_notification with complete user_data
        browser_success = False
        browser_notifications_enabled = bool(channel_prefs.get(category, {}).get('browser', bool(user_data.get('browser_notifications_enabled', True))))
        if browser_notifications_enabled:
            try:
                print("🌐 Attempting to send browser push...")
                browser_success = await alert_notification_system.send_browser_notification(alert, user_data)
                print(f"✅ Browser notification sent: {browser_success}")
            except Exception as be:
                print(f"❌ Browser push error: {be}")
                logger.error(f"Browser push error: {be}")
                browser_success = False

        # Log the alert
        cursor.execute(
            """
            INSERT INTO alert_notifications 
            (user_id, alert_type, message, sent_via, created_at, success_status, safety_score, risk_level, high_risk_count)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                alert.user_id,
                alert.alert_type,
                alert.message,
                'both' if (email_success and browser_success) else 'email' if email_success else 'browser' if browser_success else 'none',
                datetime.now(),
                'success' if (email_success or browser_success) else 'failed',
                alert.safety_score,
                str(alert.risk_level)[:20],
                alert.high_risk_crimes,
            ),
        )

        conn.commit()
        print("✅ Enhanced alert notification completed successfully")

        return {
            "email_sent": email_success,
            "browser_sent": browser_success,
            "alert_message": alert.message,
        }

    except Exception as e:
        print(f"❌ Error sending enhanced alert notification: {e}")
        logger.error(f"Error sending enhanced alert notification: {e}")
        return {
            "email_sent": False,
            "browser_sent": False,
            "error": str(e),
        }
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()


# Browser Notification Endpoints
@router.post("/browser-notifications/subscribe")
async def subscribe_browser_notifications(
    subscription_data: dict = Body(...),
    current_user: str = Depends(get_username_from_token)
):
    """Subscribe to browser push notifications"""
    conn = None
    cursor = None
    try:
        print(f"🌐 Browser push subscription request from user: {current_user}")
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Get user info used for subscription defaults
        cursor.execute(
            """
            SELECT id, home_area, work_area, alert_radius
            FROM users_info
            WHERE username = %s
            """,
            (current_user,),
        )
        user = cursor.fetchone()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Type assertion: after None check, user is definitely a dict
        user_dict = cast(Dict[str, Any], user)
        user_id = user_dict["id"]
        
        # Validate subscription data
        if not subscription_data.get('endpoint'):
            raise HTTPException(status_code=400, detail="Missing subscription endpoint")
        
        if not subscription_data.get('keys') or not subscription_data['keys'].get('p256dh') or not subscription_data['keys'].get('auth'):
            raise HTTPException(status_code=400, detail="Invalid subscription keys")
        
        # Store browser push subscription in database
        cursor.execute("""
            INSERT INTO browser_push_subscriptions 
            (user_id, endpoint, p256dh, auth, created_at)
            VALUES (%s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
            endpoint = VALUES(endpoint),
            p256dh = VALUES(p256dh),
            auth = VALUES(auth),
            updated_at = VALUES(created_at)
        """, (
            user_id,
            subscription_data['endpoint'],
            subscription_data['keys']['p256dh'],
            subscription_data['keys']['auth'],
            datetime.now()
        ))

        # Ensure browser-only users are still eligible for monitored alerts.
        # If a subscription exists, enforce browser channel and active status.
        # If none exists, create a sensible default subscription.
        cursor.execute(
            """
            SELECT id, notification_types
            FROM alert_subscriptions
            WHERE user_id = %s
            ORDER BY is_active DESC, id DESC
            LIMIT 1
            """,
            (user_id,),
        )
        existing_alert_subscription = cursor.fetchone()

        if existing_alert_subscription:
            raw_notification_types = cast(Dict[str, Any], existing_alert_subscription).get("notification_types")
            notification_types = []

            if isinstance(raw_notification_types, list):
                notification_types = [str(x).strip() for x in raw_notification_types if str(x).strip()]
            elif isinstance(raw_notification_types, str):
                try:
                    parsed = json.loads(raw_notification_types)
                    if isinstance(parsed, list):
                        notification_types = [str(x).strip() for x in parsed if str(x).strip()]
                except Exception:
                    notification_types = ["email"]

            if "browser" not in notification_types:
                notification_types.append("browser")

            cursor.execute(
                """
                UPDATE alert_subscriptions
                SET notification_types = %s,
                    is_active = TRUE,
                    updated_at = %s
                WHERE id = %s
                """,
                (
                    json.dumps(notification_types or ["browser"]),
                    datetime.now(),
                    cast(Dict[str, Any], existing_alert_subscription)["id"],
                ),
            )
            subscription_action = "activated_existing"
        else:
            user_areas = []
            for area_key in ("home_area", "work_area"):
                area_value = cast(Dict[str, Any], user_dict).get(area_key)
                if isinstance(area_value, str):
                    cleaned = area_value.strip()
                    if cleaned and cleaned not in user_areas:
                        user_areas.append(cleaned)

            default_areas = user_areas or ["General"]
            default_radius = float(cast(Dict[str, Any], user_dict).get("alert_radius") or 5.0)

            cursor.execute(
                """
                INSERT INTO alert_subscriptions
                (user_id, alert_types, areas, radius, notification_types, is_active, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    user_id,
                    json.dumps(["crime", "safety", "emergency"]),
                    json.dumps(default_areas),
                    default_radius,
                    json.dumps(["browser"]),
                    True,
                    datetime.now(),
                ),
            )
            subscription_action = "created_default"
        
        conn.commit()
        
        print(f"✅ Browser push subscription saved for user {current_user}")
        
        return {
            "message": "Browser push notifications subscribed successfully",
            "subscription_action": subscription_action,
        }
        
    except Exception as e:
        print(f"❌ Error subscribing to browser notifications: {e}")
        if conn:
            conn.rollback()
        raise HTTPException(status_code=500, detail="Failed to subscribe to browser notifications")
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()

@router.get("/browser-notifications")
async def get_browser_notifications(
    current_user: str = Depends(get_username_from_token),
    limit: int = 50,
    offset: int = 0
):
    """Get browser notifications for user"""
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Get user ID
        cursor.execute("SELECT id FROM users_info WHERE username = %s", (current_user,))
        user = cursor.fetchone()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Type assertion: after None check, user is definitely a dict
        user_dict = cast(Dict[str, Any], user)
        user_id = user_dict["id"]
        
        cursor.execute("""
            SELECT id, title, message, alert_type, notification_data, is_read, created_at
            FROM browser_notifications 
            WHERE user_id = %s
            ORDER BY created_at DESC
            LIMIT %s OFFSET %s
        """, (user_id, limit, offset))
        
        notifications = cursor.fetchall()
        
        return {"notifications": notifications}
        
    except Exception as e:
        logger.error(f"Error getting browser notifications: {e}")
        raise HTTPException(status_code=500, detail="Failed to get browser notifications")
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()

@router.post("/browser-notifications/{notification_id}/read")
async def mark_browser_notification_read(
    notification_id: int,
    current_user: str = Depends(get_username_from_token)
):
    """Mark browser notification as read"""
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Get user ID
        cursor.execute("SELECT id FROM users_info WHERE username = %s", (current_user,))
        user = cursor.fetchone()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Type assertion: after None check, user is definitely a dict
        user_dict = cast(Dict[str, Any], user)
        user_id = user_dict["id"]
        
        cursor.execute("""
            UPDATE browser_notifications 
            SET is_read = TRUE 
            WHERE id = %s AND user_id = %s
        """, (notification_id, user_id))
        
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Notification not found")
        
        conn.commit()
        
        return {"message": "Notification marked as read"}
        
    except Exception as e:
        logger.error(f"Error marking notification as read: {e}")
        raise HTTPException(status_code=500, detail="Failed to mark notification as read")
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()

@router.post("/browser-notifications/read-all")
async def mark_all_browser_notifications_read(
    current_user: str = Depends(get_username_from_token)
):
    """Mark all browser notifications as read for the current user"""
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Get user ID
        cursor.execute("SELECT id FROM users_info WHERE username = %s", (current_user,))
        user = cursor.fetchone()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Type assertion: after None check, user is definitely a dict
        user_dict = cast(Dict[str, Any], user)
        user_id = user_dict["id"]

        # Mark all notifications as read
        cursor.execute(
            """
            UPDATE browser_notifications 
            SET is_read = TRUE 
            WHERE user_id = %s AND is_read = FALSE
            """,
            (user_id,),
        )

        updated_count = cursor.rowcount
        conn.commit()

        return {
            "message": f"Marked {updated_count} notifications as read",
            "updated_count": updated_count,
        }

    except Exception as e:
        logger.error(f"Database error marking all browser notifications as read: {e}")
        raise HTTPException(status_code=500, detail="Failed to update notifications")
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()


@router.post("/heartbeat")
async def heartbeat(current_user: str = Depends(get_username_from_token)):
    """Mark user as active (logged in) and update last activity timestamp."""
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE users_info
            SET is_logged_in = TRUE,
                last_activity_at = NOW()
            WHERE username = %s
            """,
            (current_user,),
        )
        conn.commit()
        return {"status": "ok", "message": "heartbeat recorded"}
    except Exception as e:
        logger.error(f"Heartbeat update failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to record heartbeat")
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()


@router.post("/logout")
async def alerts_logout(current_user: str = Depends(get_username_from_token)):
    """Mark user as logged out for scheduler gating."""
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE users_info
            SET is_logged_in = FALSE
            WHERE username = %s
            """,
            (current_user,),
        )
        conn.commit()
        return {"status": "ok", "message": "logged out for alerts"}
    except Exception as e:
        logger.error(f"Alerts logout failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to logout for alerts")
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()

# Test Endpoints
@router.post("/test/fix-alerts")
async def test_fixed_alerts(current_user: str = Depends(get_username_from_token)):
    """Test the fixed alert system"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Get user data
        cursor.execute("SELECT id, username, email FROM users_info WHERE username = %s", (current_user,))
        user_data = cursor.fetchone()
        
        if not user_data:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Type assertion: after None check, user_data is definitely a dict
        user_data = cast(Dict[str, Any], user_data)
        
        # Create a test alert with all required fields
        alert = RiskZoneAlert(
            user_id=user_data['id'],
            username=user_data['username'],
            email=user_data['email'],
            latitude=31.5204,
            longitude=74.3587,
            address="Test Location - Lahore",
            risk_level="High",
            safety_score=35.0,
            high_risk_crimes=3,
            precautions="Test precautions - stay alert and avoid area",
            alert_type="test_fixed_alert",
            message="TEST: This is a fixed alert test with all required fields."
        )
        
        print("🔔 Testing fixed alert system...")
        result = await send_alert_notification(alert)
        
        return {
            "message": "✅ Fixed alert test completed",
            "result": result,
            "alert_sent": True,
            "missing_fields_fixed": ["precautions"]
        }
        
    except Exception as e:
        logger.error(f"Fixed alert test error: {e}")
        raise HTTPException(status_code=500, detail=f"Test failed: {str(e)}")
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()

@router.post("/test/alert-system")
async def test_alert_system(current_user: str = Depends(get_username_from_token)):
    """Test the complete alert system with real data"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Get user data
        cursor.execute("""
            SELECT id, username, email, phone_number, sms_enabled, sms_carrier,
                   home_latitude, home_longitude, home_area
            FROM users_info WHERE username = %s
        """, (current_user,))
        
        user_data = cursor.fetchone()
        
        if not user_data:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Type assertion: after None check, user_data is definitely a dict
        user_data = cast(Dict[str, Any], user_data)
        
        # Use home location or default
        test_lat = user_data.get('home_latitude') or 31.5204
        test_lng = user_data.get('home_longitude') or 74.3587
        test_address = user_data.get('home_area') or "Test Location"
        
        # Create test alert
        alert = RiskZoneAlert(
            user_id=user_data['id'],
            username=user_data['username'],
            email=user_data['email'],
            phone=user_data.get('phone_number'),
            latitude=test_lat,
            longitude=test_lng,
            address=test_address,
            risk_level="High",
            safety_score=35.0,
            high_risk_crimes=3,
            alert_type="test_alert",
            precautions=None,
            message="TEST: This is a test alert from the SafeVision system.",
        )
        
        print(f"🔔 Testing alert system for user: {user_data['username']}")
        
        # Send the alert
        result = await send_alert_notification(alert)
        
        return {
            "message": "✅ Test alert completed successfully",
            "user": user_data['username'],
            "notification_result": result,
            "alert_details": {
                "location": f"{test_lat}, {test_lng}",
                "risk_level": "High",
                "safety_score": 35.0
            }
        }
        
    except Exception as e:
        logger.error(f"Test alert system error: {e}")
        raise HTTPException(status_code=500, detail=f"Test failed: {str(e)}")
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()

@router.post("/test/trigger-immediate")
async def trigger_immediate_alert_test(current_user: str = Depends(get_username_from_token)):
    """Test endpoint to trigger immediate alerts with REAL data from endpoints"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Get user data
        cursor.execute("""
            SELECT id, username, email, phone_number, sms_enabled, sms_carrier,
                   home_latitude, home_longitude, home_area
            FROM users_info WHERE username = %s
        """, (current_user,))
        
        user_data = cursor.fetchone()
        
        if not user_data:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Type assertion: after None check, user_data is definitely a dict
        user_data = cast(Dict[str, Any], user_data)
        
        # Use home location or default test location
        test_lat = user_data.get('home_latitude') or 31.5204
        test_lng = user_data.get('home_longitude') or 74.3587
        test_address = user_data.get('home_area') or "Test Location"
        
        # GET REAL SAFETY DATA FIRST
        safety_data = await get_real_safety_data_from_endpoints(test_lat, test_lng, test_address)
        print(f"📊 REAL safety data for test: {safety_data}")
        
        # Create a test alert with REAL data from endpoints
        alert = RiskZoneAlert(
            user_id=user_data['id'],
            username=user_data['username'],
            email=user_data['email'],
            phone=user_data.get('phone_number'),
            latitude=test_lat,
            longitude=test_lng,
            address=test_address,
            risk_level=safety_data['risk_level'],
            safety_score=safety_data['safety_score'],
            high_risk_crimes=safety_data['high_risk_crimes'],
            alert_type="test_immediate_alert",
            message=f"TEST: {safety_data['risk_level']} risk area. Safety score: {safety_data['safety_score']}%. {safety_data['high_risk_crimes']} high-risk incidents."
        )
        
        print(f"🔔 Testing immediate alert for user: {user_data['username']}")
        print(f"📊 Using REAL data - Score: {safety_data['safety_score']}%, Risk: {safety_data['risk_level']}, High-risk crimes: {safety_data['high_risk_crimes']}")
        
        # Send the alert with REAL data
        result = await send_alert_notification(alert)
        
        return {
            "message": "✅ Test alert triggered successfully with REAL data",
            "user": user_data['username'],
            "location": f"{test_lat}, {test_lng}",
            "safety_data": safety_data,
            "notification_result": result,
            "alert_type": "immediate_test_real_data"
        }
        
    except Exception as e:
        logger.error(f"Test alert error: {e}")
        raise HTTPException(status_code=500, detail=f"Test failed: {str(e)}")
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()


async def get_recent_incidents(lat: float, lng: float, radius_km: float = 2.0) -> Dict[str, Any]:
    """Get recent incidents in the area for alert details"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Get incidents from last 24 hours
        yesterday = datetime.now() - timedelta(hours=24)

        # Calculate bounding box for the radius
        earth_radius = 6371
        lat_range = (radius_km / earth_radius) * (180 / 3.14159)
        lng_range = (radius_km / (earth_radius * 3.14159 / 180 * abs(3.14159/180 * lat))) if lat != 0 else (radius_km / earth_radius) * (180 / 3.14159)

        cursor.execute(
            """
            SELECT 
                crime_type,
                risk_level,
                COUNT(*) as incident_count,
                MAX(crime_date) as latest_incident
            FROM crimes 
            WHERE latitude BETWEEN %s AND %s 
                AND longitude BETWEEN %s AND %s
                AND SQRT(POW(69.1 * (latitude - %s), 2) + POW(69.1 * (%s - longitude) * COS(latitude / 57.3), 2)) <= %s
                AND crime_date >= %s
            GROUP BY crime_type, risk_level
            ORDER BY latest_incident DESC
            LIMIT 5
            """,
            (lat - lat_range, lat + lat_range, lng - lng_range, lng + lng_range, lat, lng, radius_km, yesterday),
        )

        incidents = cast(List[Dict[str, Any]], cursor.fetchall())

        if not incidents:
            return {"recent_incidents": 0, "latest_incident_type": None}

        total_incidents = sum(incident['incident_count'] for incident in incidents)
        latest_incident = incidents[0]['crime_type'] if incidents else None

        # Generate precautions based on incident types
        precautions = generate_precautions([incident['crime_type'] for incident in incidents])

        return {
            "recent_incidents": total_incidents,
            "latest_incident_type": latest_incident,
            "precautions": precautions,
            "incidents_detail": incidents,
        }

    except Exception as e:
        logger.error(f"Error getting recent incidents: {e}")
        return {"recent_incidents": 0, "latest_incident_type": None, "precautions": [], "incidents_detail": []}
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()

def generate_precautions(incident_types: List[str]) -> str:
    """Generate specific precautions based on incident types"""
    precautions = []

    if any(crime in incident_types for crime in ['Robbery', 'Burglary', 'Street Crime']):
        precautions.extend([
            "Avoid displaying valuable items in public",
            "Keep bags and wallets secure and close to your body",
            "Be cautious when using ATMs or carrying cash",
        ])

    if 'Vehicle Theft' in incident_types:
        precautions.extend([
            "Park in well-lit, secure areas",
            "Never leave valuables in your vehicle",
            "Use steering wheel locks or anti-theft devices",
        ])

    if any(crime in incident_types for crime in ['Violent Crime', 'murder']):
        precautions.extend([
            "Travel in groups when possible",
            "Avoid confrontations and stay in public areas",
            "Have emergency numbers readily accessible",
        ])

    # Default precautions
    if not precautions:
        precautions = [
            "Stay alert to your surroundings",
            "Avoid isolated or poorly lit areas",
            "Keep emergency contacts handy",
        ]

    return ". ".join(precautions) + "."

async def is_in_cooldown(user_id: int, location_type: str) -> bool:
    """Check if safe area alert is in cooldown for this user and location"""
    cooldown_key = f"{user_id}_{location_type}_safe"
    if cooldown_key in alert_cooldown_cache:
        last_alert_time = alert_cooldown_cache[cooldown_key]
        cooldown_minutes = SAFE_AREA_ALERT_CONFIG['cooldown_minutes']
        if (datetime.now() - last_alert_time).total_seconds() < cooldown_minutes * 60:
            return True
    return False


async def check_location_risk(user_id: int, lat: float, lng: float, radius_km: float = 2.0, area_name: Optional[str] = None) -> Dict:
    # ── Area Normalization (Universal) ──
    if area_name:
        area_name = normalize_area_name(area_name)
    
    conn = None
    """Check if a location is in a high-risk zone.
    Uses coordinate radius + area-name fallback for accuracy.
    Area names stored in the DB (e.g. 'Bahria Town') are matched even when
    coordinate radius yields 0 results (GPS drift / wide area coverage)."""
    try:
        effective_radius_km = get_global_notification_radius_km()
        stats = await get_safety_stats_by_coords(lat, lng, effective_radius_km)
        safety_score = stats['safety_score']
        high_risk_count = stats['high_risk_count']
        total_crimes = stats['total_crimes']
        risk_pct = stats.get('risk_pct', round(100 - safety_score, 1))
        risk_level = stats.get('risk_level', 'Low')

        # If radius query returned no crimes but we have an area name,
        # fall back to name-based lookup to handle wide areas like 'Bahria Town'
        # where crimes are stored by area name but GPS coords may not cluster within 1-2 km.
        if total_crimes == 0 and area_name:
            name_stats = await get_safety_stats_by_coords(lat, lng, effective_radius_km)
            # Use full name-based query directly
            try:
                _conn = get_db_connection()
                _cur = _conn.cursor(dictionary=True)
                from app.utils.area_normalization import area_like_pattern
                _pattern = area_like_pattern(area_name)
                _cur.execute("""
                    SELECT
                        COUNT(*) as total_crimes,
                        SUM(CASE WHEN risk_level='High' THEN 1 ELSE 0 END) as high_risk_count,
                        SUM(CASE WHEN risk_level='Medium' THEN 1 ELSE 0 END) as medium_risk_count,
                        SUM(CASE WHEN crime_date >= (NOW() - INTERVAL 90 DAY) THEN 1 ELSE 0 END) as last_90_days
                    FROM crimes
                    WHERE LOWER(area) LIKE %s
                      AND crime_date >= (NOW() - INTERVAL 365 DAY)
                """, (_pattern,))
                _row = _cur.fetchone()
                _cur.close()
                _conn.close()
                if _row and int(_row.get('total_crimes', 0) or 0) > 0:
                    _total = int(_row['total_crimes'] or 0)
                    _high  = int(_row['high_risk_count'] or 0)
                    _med   = int(_row['medium_risk_count'] or 0)
                    _risk_summary = calculate_unified_risk_summary(
                        {'total_crimes': _total, 'high_risk_count': _high, 'medium_risk_count': _med},
                        365
                    )
                    safety_score  = float(_risk_summary['safety_score'])
                    risk_pct      = float(_risk_summary['risk_score'])
                    risk_level    = str(_risk_summary['risk_level'])
                    high_risk_count = _high
                    total_crimes    = _total
                    logger.info(f"📍 Area-name fallback for '{area_name}': {_total} crimes (365d), risk={risk_pct}%")
            except Exception as _ne:
                logger.warning(f"Area-name fallback lookup failed for '{area_name}': {_ne}")

        # Consistent with unified scoring thresholds
        is_high_risk = risk_pct >= 51 or safety_score < 40 or high_risk_count >= 3

        return {
            "is_high_risk": is_high_risk,
            "safety_score": safety_score,
            "risk_pct": risk_pct,
            "high_risk_crimes": high_risk_count,
            "total_crimes": total_crimes,
            "risk_level": risk_level,
            "scope_mode": "radius+name" if total_crimes > 0 else "radius"
        }
    except Exception as e:
        logger.error(f"Error checking location risk: {e}")
        return {"is_high_risk": False, "safety_score": 50, "high_risk_crimes": 0, "risk_level": "Low", "risk_pct": 50.0}


@router.post("/check-risk")
async def check_live_location_risk(
    request: LocationAlertRequest,
    current_user: str = Depends(get_username_from_token)
):
    """Check risk for live location and send immediate alerts"""
    try:
        print(f"📍 Live location check for user: {current_user}")
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Get user info
        cursor.execute("""
            SELECT id, username, email, phone_number, browser_notifications_enabled, alert_radius 
            FROM users_info WHERE username = %s
        """, (current_user,))
        user = cursor.fetchone()
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Cast to Dict to satisfy type checker since cursor(dictionary=True) returns dict
        user = cast(Dict[str, Any], user)
        
        user_id = user["id"]
        alert_radius = float(user.get("alert_radius", 5.0))
        
        # Check location risk with REAL data
        risk_assessment = await get_real_safety_data_from_endpoints(
            request.latitude, 
            request.longitude,
            request.address
        )
        
        print(f"📊 Real risk assessment: {risk_assessment}")
        
        # Send alert if high risk using normalized assessment
        if risk_assessment.get("is_high_risk", False) and request.check_immediate:
            alert = RiskZoneAlert(
                user_id=user_id,
                username=user.get("username", ""),
                email=user.get("email", ""),
                latitude=request.latitude,
                longitude=request.longitude,
                address=request.address or f"Current location ({request.latitude}, {request.longitude})",
                risk_level=risk_assessment["risk_level"],
                safety_score=risk_assessment["safety_score"],
                high_risk_crimes=risk_assessment["high_risk_crimes"],
                precautions=risk_assessment.get("precautions", "Stay alert and avoid the area if possible."),
                alert_type="live_high_risk_zone",
                message=f"🚨 {risk_assessment['risk_level']} risk detected at your current location! Safety score: {risk_assessment['safety_score']}%"
            )
            
            print("🚨 High risk detected - sending immediate alert")
            await send_alert_notification(alert)
            
            return {
                "alert_sent": True,
                "risk_assessment": risk_assessment,
                "message": "High risk detected - alert sent"
            }
        
        return {
            "alert_sent": False,
            "risk_assessment": risk_assessment,
            "message": "Location checked - no alert needed"
        }
        
    except Exception as e:
        print(f"❌ Error in live location check: {e}")
        logger.error(f"Error checking live location risk: {e}")
        raise HTTPException(status_code=500, detail="Failed to check location risk")
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()

async def dispatch_new_incident_alerts(crime_info: Dict[str, Any]):
    """
    Dispatch alerts with verification buffer and anti-spam grouping.
    """
    crime_id = int(crime_info.get("id") or 0)
    if crime_id:
        _manually_dispatched_ids.add(crime_id)
    crime_id = crime_info.get("id")
    area = crime_info.get("area", "")
    area_translit = crime_info.get("area_translit") or area
    crime_type = crime_info.get("crime_type", "Unknown Incident")
    risk_level = crime_info.get("risk_level", "Medium")
    lat = crime_info.get("latitude")
    lng = crime_info.get("longitude")
    
    # 👉 STEP 1: Verification + Buffer Window
    # High severity -> short wait, Medium -> slightly longer (allow grouping)
    # Note: when called from poller (not API), delays are kept short since crime is already in DB
    delay = 10 if risk_level == "High" else 30
    logger.info(f"⏳ Waiting {delay}s buffer window for incident verification: {crime_type} in {area_translit}")
    await asyncio.sleep(delay)

    logger.info(f"📣 Buffer complete. Processing alerts for {crime_type}...")
    
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Re-check if crime still exists (deduplication/validation)
        cursor.execute("SELECT * FROM crimes WHERE id = %s", (crime_id,))
        valid_crime = cursor.fetchone()
        if not valid_crime:
            logger.warning(f"⚠️ Incident {crime_id} no longer exists. Aborting alert.")
            return

        # Check for other nearby incidents in the same 10-min window to group them
        window_start = datetime.now() - timedelta(minutes=10)
        area_for_group = area_translit or area or ""
        cursor.execute(
            """SELECT crime_type, risk_level, crime_time, created_at FROM crimes 
               WHERE (area_translit = %s OR area LIKE %s)
                 AND created_at >= %s""",
            (area_for_group, f"%{area_for_group}%", window_start.strftime('%Y-%m-%d %H:%M:%S'))
        )
        recent_incidents = cursor.fetchall() or []
        recent_total = len(recent_incidents)
        incidents_list = [
            {
                "type": inc.get("crime_type", "Incident"),
                "time": inc.get("crime_time") or inc.get("created_at").strftime("%H:%M") if hasattr(inc.get("created_at"), "strftime") else "",
                "severity": inc.get("risk_level", "Medium")
            }
            for inc in recent_incidents
        ]
        
        # Build query pattern — use area_like_pattern if available for better fuzzy matching
        from app.utils.area_normalization import area_like_pattern as _alp
        area_search = area_translit or area or "Unknown"
        area_pattern = _alp(area_search)
        global_radius_km = get_global_notification_radius_km()

        # Get users whose home/work area matches this incident's area
        # Note: do NOT require incident_alerts_enabled in case column is unset
        if lat and lng:
            cursor.execute(
                """
                SELECT DISTINCT u.id, u.username, u.email, u.home_area, u.work_area,
                       u.browser_notifications_enabled, u.email_alerts_enabled
                FROM users_info u
                LEFT JOIN alert_subscriptions s ON u.id = s.user_id AND s.is_active = 1
                WHERE (
                    (u.home_area IS NOT NULL AND LOWER(%s) LIKE LOWER(CONCAT('%%', u.home_area, '%%'))) OR
                    (u.work_area IS NOT NULL AND LOWER(%s) LIKE LOWER(CONCAT('%%', u.work_area, '%%'))) OR
                    (s.areas IS NOT NULL AND s.areas LIKE %s) OR
                    (u.home_latitude IS NOT NULL AND u.home_longitude IS NOT NULL AND
                     SQRT(POW(111.32 * (u.home_latitude - %s), 2) + POW(111.32 * (%s - u.home_longitude) * COS(u.home_latitude / 57.3), 2)) <= %s)
                )
                AND u.is_active = TRUE AND u.email IS NOT NULL
                """,
                (area_search, area_search, area_pattern, lat, lng, global_radius_km)
            )
        else:
            cursor.execute(
                """
                SELECT DISTINCT u.id, u.username, u.email, u.home_area, u.work_area,
                       u.browser_notifications_enabled, u.email_alerts_enabled
                FROM users_info u
                LEFT JOIN alert_subscriptions s ON u.id = s.user_id AND s.is_active = 1
                WHERE (
                    (u.home_area IS NOT NULL AND LOWER(%s) LIKE LOWER(CONCAT('%%', u.home_area, '%%'))) OR
                    (u.work_area IS NOT NULL AND LOWER(%s) LIKE LOWER(CONCAT('%%', u.work_area, '%%'))) OR
                    (s.areas IS NOT NULL AND s.areas LIKE %s)
                )
                AND u.is_active = TRUE AND u.email IS NOT NULL
                """,
                (area_search, area_search, area_pattern)
            )
            
        recipients = cursor.fetchall() or []
        logger.info(f"👥 Incident alert recipients: {len(recipients)} user(s) matched for area '{area_search}'")
        if not recipients:
            logger.warning(f"⚠️ No recipients found for incident in '{area_search}'. Check home_area/work_area values in users_info.")
            return

        # Fetch summarized safety data for context - use slightly wider radius to avoid false-safe suppression
        from app.routes.alerts import get_safety_stats_by_coords
        stats = {}
        try:
            stats = await get_safety_stats_by_coords(lat, lng, radius_km=2.0) if (lat and lng) else {}
        except Exception:
            pass

        # Conditional trigger for Medium level
        risk_pct = cast(Dict[str, Any], stats).get('risk_pct', 0)
        is_high_risk_area = risk_pct > 50  # Use 51% threshold consistent with system
        
        for user_data in recipients:
            user_id = user_data["id"]
            
            # 👉 STEP 2: Conditional Trigger for Medium Severity
            # Send if: High, or (Medium + 2+ grouped incidents), or (Medium + already high-risk area)
            if risk_level == "Medium" and not is_high_risk_area and recent_total < 2:
                # Suppress isolated Medium alert in genuinely low-risk area
                logger.info(f"⚪ Suppressing isolated Medium alert for user {user_id} (area risk={risk_pct}%, grouped={recent_total})")
                continue

            # 👉 STEP 3: Cooldown System (Anti-Spam)
            # Bypass cooldown for High severity to ensure immediate delivery
            if risk_level != "High":
                try:
                    cursor.execute(
                        "SELECT COUNT(*) as recent_alerts FROM user_alerts WHERE user_id = %s AND alert_type = 'new_incident_alert' AND created_at > NOW() - INTERVAL 10 MINUTE",
                        (user_id,)
                    )
                    cooldown_res = cursor.fetchone()
                    if cooldown_res and int(cooldown_res.get('recent_alerts', 0) or 0) > 0:
                        logger.info(f"🚫 Cooldown active for user {user_id}. Skipping duplicate alert.")
                        continue
                except Exception as _cd_err:
                    logger.warning(f"Cooldown check failed (non-fatal): {_cd_err}")


            # Determine location type
            closest_type = "monitored"
            home_area = user_data.get("home_area", "").lower().replace(" ", "")
            work_area = user_data.get("work_area", "").lower().replace(" ", "")
            area_clean = area_translit.lower().replace(" ", "")
            
            if home_area and (area_clean in home_area or home_area in area_clean):
                closest_type = "home"
            elif work_area and (area_clean in work_area or work_area in area_clean):
                closest_type = "work"

            # Custom message based on grouping
            display_msg = f"🚨 {risk_level} Incident: {crime_type} reported at {area_translit}."
            if recent_total > 1:
                display_msg = f"🚨 MULTIPLE INCIDENTS ({recent_total}) reported at {area_translit}. Latest: {crime_type}."

            alert = RiskZoneAlert(
                user_id=user_id,
                username=user_data["username"],
                email=user_data["email"],
                latitude=lat or 0.0,
                longitude=lng or 0.0,
                address=area_translit,
            risk_level=risk_level,
            safety_score=cast(Dict[str, Any], stats).get('safety_score', 50.0),
                risk_pct=risk_pct,
                high_risk_crimes=cast(Dict[str, Any], stats).get('high_risk_count_90d', 0),
                medium_risk_crimes=cast(Dict[str, Any], stats).get('medium_risk_count_90d', 0),
                last_90_days=cast(Dict[str, Any], stats).get('last_90_days', 0),
                total_crimes=cast(Dict[str, Any], stats).get('total_crimes', 0),
                total_crimes_365=cast(Dict[str, Any], stats).get('total_crimes', 0),
                precautions=f"Take immediate precautions. {recent_total} incidents reported near your registered {closest_type} area.",
                alert_trigger_reason=f"New incident ({crime_type}) reported near your {closest_type} area.",
                alert_type="new_incident_alert",
                location_type=closest_type,
                message=display_msg
            )
            
            # Metadata for template
            unique_types_list = list(dict.fromkeys([i['type'] for i in incidents_list]))
            if len(unique_types_list) == 1:
                display_type = unique_types_list[0]
            elif len(unique_types_list) == 2:
                display_type = f"{unique_types_list[0]} & {unique_types_list[1]}"
            else:
                display_type = f"{unique_types_list[0]} and {len(unique_types_list)-1} others"

            setattr(alert, 'incident_type', display_type)
            setattr(alert, 'severity', risk_level)
            setattr(alert, 'location_type', closest_type)
            setattr(alert, 'incidents_list', incidents_list)
            # Use actual incident time for specific dispatch context if available
            latest_time = incidents_list[0]['time'] if incidents_list else datetime.now().strftime('%H:%M')
            setattr(alert, 'timestamp', latest_time)
            
            await send_alert_notification(alert)
            
    except Exception as e:
        logger.error(f"❌ Error in dispatch_new_incident_alerts: {e}")
        import traceback
        logger.error(traceback.format_exc())
    finally:
        if cursor: cursor.close()
        if conn and conn.is_connected(): conn.close()

async def dispatch_weekly_safety_reports():
    """Scheduled task to send high-fidelity weekly safety summaries for both Home and Work areas."""
    conn = None
    cursor = None
    try:
        logger.info("📅 Starting Weekly Safety Report dispatch...")
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Get all active users with registered home OR work areas
        cursor.execute("""
            SELECT id, email, username, first_name,
                   home_area, home_latitude, home_longitude,
                   work_area, work_latitude, work_longitude,
                 alert_radius, email_alerts_enabled, browser_notifications_enabled, alert_preferences
            FROM users_info
            WHERE is_active = TRUE AND email IS NOT NULL AND weekly_reports_enabled = TRUE
              AND (home_area IS NOT NULL OR work_area IS NOT NULL
                   OR (home_latitude IS NOT NULL AND home_longitude IS NOT NULL)
                   OR (work_latitude IS NOT NULL AND work_longitude IS NOT NULL))
        """)
        users = cursor.fetchall()
        logger.info(f"📊 Processing weekly reports for {len(users or [])} users")

        async def _send_area_report(user: Dict[str, Any], area_name: str, area_label: str):
            """
            Compute weekly stats for ONE specific area using name-only matching
            and send the report. Uses its own isolated DB connection.
            """
            _conn = None
            _cur  = None
            try:
                _conn = get_db_connection()
                _cur  = _conn.cursor(dictionary=True)

                user_id    = user['id']
                user_email = user['email']
                area_lc    = area_name.lower().strip()
                # Use area_like_pattern for consistent fuzzy matching
                from app.utils.area_normalization import area_like_pattern as _alp
                area_pat = _alp(area_name)

                # Dedupe: skip if a successful weekly report for this area was already
                # sent to this user in the last 24 hours (covers cron + manual triggers
                # + restarts within the same window). Cron only fires once a week,
                # so 24h cannot suppress a legitimate scheduled run.
                log_alert_type = f"weekly_report_{area_label.lower()}"
                _cur.execute(
                    """
                    SELECT 1 FROM notification_logs
                    WHERE user_id = %s
                      AND alert_type = %s
                      AND success = 1
                      AND created_at >= DATE_SUB(NOW(), INTERVAL 24 HOUR)
                    LIMIT 1
                    """,
                    (user_id, log_alert_type),
                )
                if _cur.fetchone():
                    logger.info(
                        f"⏭️ Skipping duplicate weekly {area_label} report for user {user_id} "
                        f"({user_email}) — already sent within last 24h"
                    )
                    return

                # Current 7-day stats — area-name ONLY (no radius to avoid cross-area pollution)
                _cur.execute("""
                    SELECT
                        COUNT(*) as total_7d,
                        SUM(CASE WHEN risk_level = 'High'   THEN 1 ELSE 0 END) as high_7d,
                        SUM(CASE WHEN risk_level = 'Medium' THEN 1 ELSE 0 END) as medium_7d
                    FROM crimes
                    WHERE (LOWER(area) LIKE %s OR LOWER(area_translit) LIKE %s)
                      AND crime_date >= DATE_SUB(NOW(), INTERVAL 7 DAY)
                """, (area_pat, area_pat))
                curr = _cur.fetchone() or {}

                # Previous 7-day stats (for trend)
                _cur.execute("""
                    SELECT
                        COUNT(*) as total_prev,
                        SUM(CASE WHEN risk_level = 'High' THEN 1 ELSE 0 END) as high_prev
                    FROM crimes
                    WHERE (LOWER(area) LIKE %s OR LOWER(area_translit) LIKE %s)
                      AND crime_date >= DATE_SUB(NOW(), INTERVAL 14 DAY)
                      AND crime_date <  DATE_SUB(NOW(), INTERVAL 7 DAY)
                """, (area_pat, area_pat))
                prev = _cur.fetchone() or {}

                total_curr = int(curr.get('total_7d', 0) or 0)
                total_prev = int(prev.get('total_prev', 0) or 0)
                high_7d    = int(curr.get('high_7d', 0) or 0)
                medium_7d  = int(curr.get('medium_7d', 0) or 0)

                # Trend label
                if total_curr > total_prev + 1:
                    trend, obs_trend = 'Increasing', "We've noticed an increase in reported activity this week compared to last."
                elif total_curr < total_prev - 1 and total_prev > 0:
                    trend, obs_trend = 'Decreasing', "Good news! There's been a noticeable decrease in reported incidents this week."
                else:
                    trend, obs_trend = 'Stable', "Safety levels in your area have remained consistent with last week's patterns."

                # Compute weekly-based safety score using actual 7-day counts
                week_risk_summary = calculate_unified_risk_summary(
                    {
                        'total_crimes':      total_curr,
                        'high_risk_count':   high_7d,
                        'medium_risk_count': medium_7d,
                    },
                    7  # 7-day window
                )
                weekly_safety_score = float(week_risk_summary['safety_score'])
                weekly_risk_level   = str(week_risk_summary['risk_level'])

                logger.info(
                    f"📊 Weekly report [{area_label}={area_name}] for user {user_id}: "
                    f"7d={total_curr} (high={high_7d}, med={medium_7d}), "
                    f"score={weekly_safety_score}%, level={weekly_risk_level}"
                )

                report_data = {
                    'user_id':       user_id,
                    'area_name':     area_name,
                    'area_label':    area_label,
                    'trend':         trend,
                    'obs_trend':     obs_trend,
                    'obs_frequency': f"{total_curr} incidents reported near your {area_label.lower()} area this week.",
                    'stats': {
                        'total_7d':     total_curr,
                        'total_prev':   total_prev,
                        'high_7d':      high_7d,
                        'safety_score': weekly_safety_score,
                        'risk_level':   weekly_risk_level,
                    }
                }

                channel_prefs = _load_alert_channel_preferences(user)
                weekly_email_enabled = bool(channel_prefs.get("weekly", {}).get("email", True))
                weekly_browser_enabled = bool(channel_prefs.get("weekly", {}).get("browser", False))

                if weekly_email_enabled:
                    await alert_notification_system.send_weekly_safety_report(user_email, report_data)
                    logger.info(f"✅ Weekly {area_label} email report sent to {user_email} ({area_name})")

                if weekly_browser_enabled:
                    weekly_summary_alert = RiskZoneAlert(
                        user_id=user_id,
                        username=user.get("username", ""),
                        email=user_email,
                        latitude=float(user.get("home_latitude") or 0.0),
                        longitude=float(user.get("home_longitude") or 0.0),
                        address=area_name,
                        risk_level=weekly_risk_level,
                        safety_score=weekly_safety_score,
                        high_risk_crimes=high_7d,
                        medium_risk_crimes=medium_7d,
                        total_crimes=total_curr,
                        alert_type="weekly_safety_report",
                        location_type=area_label.lower(),
                        message=f"📊 Weekly {area_label} Safety Summary: {total_curr} incidents, risk {weekly_risk_level}, score {weekly_safety_score:.1f}%"
                    )
                    await alert_notification_system.send_browser_notification(weekly_summary_alert, user)
                    logger.info(f"✅ Weekly {area_label} browser report sent to user {user_id} ({area_name})")

            except Exception as _ae:
                logger.error(f"❌ _send_area_report failed for {area_label}={area_name}: {_ae}")
                import traceback; logger.error(traceback.format_exc())
            finally:
                if _cur:  _cur.close()
                if _conn and _conn.is_connected(): _conn.close()

        for user in (users or []):
            try:
                home_area = (user.get('home_area') or '').strip()
                work_area = (user.get('work_area') or '').strip()

                # Send home report
                if home_area:
                    await _send_area_report(user, home_area, 'Home')

                # Send work report (only if different area from home — compare normalized).
                # Case- and whitespace-insensitive so "Gulshan " vs "gulshan" doesn't skip.
                if work_area and work_area.lower() != home_area.lower():
                    await _send_area_report(user, work_area, 'Work')

            except Exception as ue:
                logger.error(f"❌ Error generating weekly report for {user.get('username', 'unknown')}: {ue}")
                import traceback; logger.error(traceback.format_exc())
                continue

    except Exception as e:
        logger.error(f"❌ Critical error in weekly report dispatcher: {e}")
    finally:
        if cursor: cursor.close()
        if conn and conn.is_connected(): conn.close()


# ── In-memory tracker: last crime ID seen, for polling-based incident alerts ──
_last_polled_crime_id: int = 0
_manually_dispatched_ids: set = set() # Track IDs sent via API/Approval to avoid double-polling

async def poll_new_incidents_for_alerts():
    """
    Polling task run every ~2 minutes by the scheduler.
    Detects crimes inserted into the DB by ANY source (API, MySQL Workbench, admin bulk-upload)
    and dispatches incident-based alerts when new High or grouped Medium incidents are found.
    """
    global _last_polled_crime_id
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Initialise pointer on first run — anchor to current max so we don't re-alert on old data
        if _last_polled_crime_id == 0:
            cursor.execute("SELECT COALESCE(MAX(id), 0) as max_id FROM crimes")
            row = cursor.fetchone()
            _last_polled_crime_id = int(row['max_id'] or 0)
            logger.info(f"📍 Incident poll initialised — anchor id={_last_polled_crime_id}")
            return

        # Fetch any crimes added since last poll
        cursor.execute("""
            SELECT id, area, area_translit, crime_type, risk_level,
                   latitude, longitude, crime_date
            FROM crimes
            WHERE id > %s
            ORDER BY id ASC
            LIMIT 100
        """, (_last_polled_crime_id,))
        new_crimes = cursor.fetchall() or []

        if not new_crimes:
            return

        logger.info(f"📣 Incident poll: {len(new_crimes)} new crime(s) since id={_last_polled_crime_id}")

        # Advance pointer
        _last_polled_crime_id = int(new_crimes[-1]['id'])

        for crime in new_crimes:
            crime_id = int(crime['id'])
            
            # Skip if already dispatched via manual API trigger
            if crime_id in _manually_dispatched_ids:
                logger.info(f"⏭️ Skipping poll-alert for ID {crime_id} (already dispatched via code trigger)")
                continue

            risk_level = str(crime.get('risk_level', 'Medium'))
            # Only dispatch for High or Medium; skip Low
            if risk_level.lower() not in ('high', 'medium'):
                continue

            crime_info = {
                'id':           int(crime['id']),
                'area':         crime.get('area', ''),
                'area_translit': crime.get('area_translit') or crime.get('area', ''),
                'crime_type':   crime.get('crime_type', 'Unknown'),
                'risk_level':   risk_level,
                'latitude':     crime.get('latitude'),
                'longitude':    crime.get('longitude'),
                'crime_date':   str(crime.get('crime_date', '')),
            }

            # Spawn dispatch in its OWN thread + event loop.
            # asyncio.ensure_future() is killed when asyncio.run() in poll_incidents_job exits.
            # Threading ensures the sleep(10/30s) buffer runs to completion independently.
            import threading as _th
            def _dispatch_in_thread(info: Dict[str, Any]):
                try:
                    asyncio.run(dispatch_new_incident_alerts(info))
                except Exception as _te:
                    logger.error(f"❌ dispatch thread error: {_te}")
            _th.Thread(target=_dispatch_in_thread, args=(crime_info,), daemon=True).start()
            logger.info(
                f"✅ Dispatch thread started: id={crime_info['id']} "
                f"({crime_info['crime_type']}, {risk_level}) in {crime_info['area']}"
            )

        # Cleanup _manually_dispatched_ids: remove anything older than current poll anchor
        # to keep the memory footprint low.
        try:
            old_ids = {cid for cid in _manually_dispatched_ids if cid <= _last_polled_crime_id}
            for oid in old_ids:
                _manually_dispatched_ids.discard(oid)
        except Exception:
            pass

    except Exception as e:
        logger.error(f"❌ poll_new_incidents_for_alerts error: {e}")
    finally:
        if cursor: cursor.close()
        if conn and conn.is_connected(): conn.close()
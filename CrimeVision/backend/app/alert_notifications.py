# app/alert_notifications.py
from decimal import Decimal
import math
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Any, List, Optional, cast
import logging
from datetime import datetime, timedelta
import asyncio
import os
import sys
import json
import base64
import tempfile
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from app.email_templates import EmailTemplates
from app.core.database import get_db_connection
from app.utils.risk import calculate_unified_risk_summary
from app.utils.area_normalization import normalize_area_name
from mysql.connector import Error
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    NoEncryption,
    PrivateFormat,
    load_der_private_key,
)

logger = logging.getLogger(__name__)

class AlertNotificationSystem:
    """Enhanced alert notification system with real data integration and browser push notifications"""
    def safe_json_serialize(self, obj: Any) -> Any:
      if isinstance(obj, Decimal):
        return float(obj)
      elif isinstance(obj, datetime):
        return obj.isoformat()
      elif isinstance(obj, (int, float, str, bool)):
        return obj
      elif isinstance(obj, list):
        return [self.safe_json_serialize(item) for item in obj]
      elif isinstance(obj, dict):
        return {key: self.safe_json_serialize(value) for key, value in obj.items()}
      elif obj is None:
        return None
      else:
        return str(obj)  # Fallback to string representation

    def __init__(self, email_config: Dict[str, Any], vapid_public_key: Optional[str] = None, vapid_private_key: Optional[str] = None):
        self.email_config = email_config
        self.email_templates = EmailTemplates()
        self.vapid_public_key = vapid_public_key

        # Store VAPID keys for browser notifications (original format works with pywebpush)
        self.vapid_public_key = vapid_public_key
        self.vapid_private_key = self._normalize_vapid_private_key(vapid_private_key)
        self.vapid_private_key_for_webpush = self._prepare_vapid_private_key_for_webpush(self.vapid_private_key)

        if vapid_private_key:
            logger.info("✅ VAPID keys loaded for browser notifications")
        else:
            logger.warning("⚠️  No VAPID private key configured - browser notifications disabled")

    def _prepare_vapid_private_key_for_webpush(self, normalized_key: Optional[str]) -> Optional[str]:
        """Prepare VAPID key in a format pywebpush reliably accepts.

        py_vapid accepts PEM reliably via file path (from_file), but may fail when
        PEM text is provided as in-memory string (from_string).
        """
        if not normalized_key:
            return None

        if "BEGIN PRIVATE KEY" in normalized_key or "BEGIN EC PRIVATE KEY" in normalized_key:
            try:
                fd, pem_path = tempfile.mkstemp(prefix="safevision_vapid_", suffix=".pem")
                os.close(fd)
                with open(pem_path, "w", encoding="utf-8") as f:
                    f.write(normalized_key)
                logger.info("✅ Prepared VAPID PEM key file for pywebpush")
                return pem_path
            except Exception as exc:
                logger.warning("⚠️ Could not create temp PEM key file for pywebpush: %s", exc)

        return normalized_key

    def _normalize_vapid_private_key(self, raw_key: Optional[str]) -> Optional[str]:
        """Normalize VAPID private key for pywebpush.

        Accepts:
        - PEM string (already valid)
        - URL-safe/base64 encoded DER PKCS8 private key (common in env files)
        Returns PEM string where possible.
        """
        if not raw_key:
            return None

        key = raw_key.strip().strip('"').strip("'")
        if not key:
            return None

        # Already PEM formatted. Re-serialize to EC PRIVATE KEY format because
        # py_vapid/pywebpush can reject PKCS8 PEM in some environments.
        if "BEGIN PRIVATE KEY" in key or "BEGIN EC PRIVATE KEY" in key:
            try:
                from cryptography.hazmat.primitives.serialization import load_pem_private_key

                private_obj = load_pem_private_key(key.encode("utf-8"), password=None)
                pem_bytes = private_obj.private_bytes(
                    encoding=Encoding.PEM,
                    format=PrivateFormat.TraditionalOpenSSL,
                    encryption_algorithm=NoEncryption(),
                )
                return pem_bytes.decode("utf-8")
            except Exception:
                return key

        # Attempt to decode base64/urlsafe-base64 encoded key material.
        # Many deployments store PEM text itself as base64 in env vars.
        try:
            padded = key + ("=" * ((4 - len(key) % 4) % 4))
            der_bytes = base64.urlsafe_b64decode(padded.encode("utf-8"))

            # Case 1: Decoded payload is already PEM text.
            try:
                decoded_text = der_bytes.decode("utf-8")
                if "BEGIN PRIVATE KEY" in decoded_text or "BEGIN EC PRIVATE KEY" in decoded_text:
                    from cryptography.hazmat.primitives.serialization import load_pem_private_key

                    private_obj = load_pem_private_key(decoded_text.encode("utf-8"), password=None)
                    pem_bytes = private_obj.private_bytes(
                        encoding=Encoding.PEM,
                        format=PrivateFormat.TraditionalOpenSSL,
                        encryption_algorithm=NoEncryption(),
                    )
                    logger.info("✅ Normalized VAPID private key from base64 PEM text")
                    return pem_bytes.decode("utf-8")
            except Exception:
                # Not UTF-8 text; continue with DER parsing.
                pass

            # Case 2: Decoded payload is DER key bytes; convert to EC PEM for pywebpush.
            private_obj = load_der_private_key(der_bytes, password=None)
            pem_bytes = private_obj.private_bytes(
                encoding=Encoding.PEM,
                format=PrivateFormat.TraditionalOpenSSL,
                encryption_algorithm=NoEncryption(),
            )
            logger.info("✅ Normalized VAPID private key from base64 DER to PEM")
            return pem_bytes.decode("utf-8")
        except Exception as exc:
            logger.warning("⚠️ Could not normalize VAPID private key format: %s", exc)
            # Fall back to raw value so existing setups continue to work.
            return key

    async def get_real_user_data(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get real user data from database"""
        conn = None
        cursor = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)

            cursor.execute("""
                SELECT
                    u.id, u.username, u.first_name, u.last_name, u.email,
                    u.home_area, u.work_area, u.alert_radius,
                    u.home_latitude, u.home_longitude,
                    u.work_latitude, u.work_longitude,
                    COUNT(DISTINCT s.id) as active_subscriptions
                FROM users_info u
                LEFT JOIN alert_subscriptions s ON u.id = s.user_id AND s.is_active = TRUE
                WHERE u.id = %s
                GROUP BY u.id
            """, (user_id,))

            user_data = cursor.fetchone()
            return cast(Dict[str, Any], user_data) if user_data else None

        except Error as e:
            logger.error(f"Database error getting user data: {e}")
            return None
        finally:
            if cursor:
                cursor.close()
            if conn and conn.is_connected():
                conn.close()

    def _get_system_setting_int(self, key: str, default: int, min_value: int = 1, max_value: int = 3650) -> int:
        """Read an integer system setting with safe bounds and fallback."""
        conn = None
        cursor = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT setting_value FROM system_settings WHERE setting_key = %s", (key,))
            row = cast(Optional[Dict[str, Any]], cursor.fetchone())
            raw = row.get("setting_value") if row else default
            parsed = int(raw)
            return max(min_value, min(max_value, parsed))
        except Exception:
            return default
        finally:
            if cursor:
                cursor.close()
            if conn and conn.is_connected():
                conn.close()

    async def get_real_safety_data(self, latitude: float, longitude: float, radius_km: float = 1.0) -> Dict[str, Any]:
        conn = None
        cursor = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)

            alert_last_30_window_days = self._get_system_setting_int("alert_last_30_window_days", 30, min_value=1, max_value=3650)
            alert_last_90_window_days = self._get_system_setting_int("alert_last_90_window_days", 90, min_value=1, max_value=3650)
            alert_recent_half_window_days = self._get_system_setting_int("alert_recent_half_window_days", 182, min_value=1, max_value=3650)
            alert_history_window_days = self._get_system_setting_int("alert_history_window_days", 365, min_value=30, max_value=3650)

            now_utc = datetime.utcnow()
            cutoff_30 = now_utc - timedelta(days=alert_last_30_window_days)
            cutoff_90 = now_utc - timedelta(days=alert_last_90_window_days)
            cutoff_recent_half = now_utc - timedelta(days=alert_recent_half_window_days)
            cutoff_history = now_utc - timedelta(days=alert_history_window_days)

            # Convert ALL inputs to float
            lat_float = float(latitude)
            lon_float = float(longitude)
            radius_float = float(radius_km)

            cursor.execute("""
                SELECT
                    COUNT(*) as total_crimes,
                    SUM(CASE WHEN risk_level = 'High' THEN 1 ELSE 0 END) as high_risk_count,
                    SUM(CASE WHEN risk_level = 'Medium' THEN 1 ELSE 0 END) as medium_risk_count,
                    SUM(CASE WHEN crime_date >= %s AND risk_level = 'High' THEN 1 ELSE 0 END) as high_risk_count_90d,
                    SUM(CASE WHEN crime_date >= %s AND risk_level = 'Medium' THEN 1 ELSE 0 END) as medium_risk_count_90d,
                    COUNT(DISTINCT crime_type) as unique_crime_types,
                    SUM(CASE WHEN crime_date >= %s THEN 1 ELSE 0 END) as last_30_days,
                    SUM(CASE WHEN crime_date >= %s THEN 1 ELSE 0 END) as last_90_days,
                    SUM(CASE WHEN crime_date >= %s THEN 1 ELSE 0 END) as recent_half,
                    SUM(CASE WHEN crime_date <  %s THEN 1 ELSE 0 END) as older_half
                FROM crimes
                WHERE SQRT(POW(111.32 * (CAST(latitude AS DECIMAL(10,6)) - %s), 2) +
                          POW(111.32 * (%s - CAST(longitude AS DECIMAL(10,6))) * COS(CAST(latitude AS DECIMAL(10,6)) / 57.3), 2)) <= %s
                  AND crime_date >= %s
            """, (
                cutoff_90,
                cutoff_90,
                cutoff_30,
                cutoff_90,
                cutoff_recent_half,
                cutoff_recent_half,
                lat_float,
                lon_float,
                radius_float,
                cutoff_history,
            ))

            crime_stats = cursor.fetchone()
            crime_stats_dict = cast(Dict[str, Any], crime_stats) if crime_stats else {}

            def safe_convert(value):
                if value is None:
                    return 0
                if isinstance(value, (Decimal, float)):
                    return float(value)
                if isinstance(value, int):
                    return int(value)
                return value

            total_crimes = safe_convert(crime_stats_dict.get('total_crimes', 0))
            high_risk_count = safe_convert(crime_stats_dict.get('high_risk_count', 0))
            medium_risk_count = safe_convert(crime_stats_dict.get('medium_risk_count', 0))
            high_risk_count_90d = safe_convert(crime_stats_dict.get('high_risk_count_90d', 0))
            medium_risk_count_90d = safe_convert(crime_stats_dict.get('medium_risk_count_90d', 0))
            unique_crime_types = safe_convert(crime_stats_dict.get('unique_crime_types', 0))
            last_30_days = safe_convert(crime_stats_dict.get('last_30_days', 0))
            last_90_days = safe_convert(crime_stats_dict.get('last_90_days', 0))
            recent_half = safe_convert(crime_stats_dict.get('recent_half', 0))
            older_half = safe_convert(crime_stats_dict.get('older_half', 0))

            now = datetime.now()
            current_hour = int(now.hour)
            current_weekday = int(now.weekday())
            if current_hour >= 21 or current_hour <= 4:
                base_time_risk = 85.0
            elif 17 <= current_hour <= 20:
                base_time_risk = 70.0
            elif 5 <= current_hour <= 11:
                base_time_risk = 45.0
            else:
                base_time_risk = 35.0

            # Weekend effect (Fri/Sat) slightly elevates operational risk.
            if current_weekday in (4, 5):
                base_time_risk += 5.0

            time_risk_score = float(max(0.0, min(100.0, base_time_risk)))

            risk_summary = calculate_unified_risk_summary({
                'total_crimes': total_crimes,
                'high_risk_count': high_risk_count,
                'medium_risk_count': medium_risk_count,
                'last_30_days': last_30_days,
                'last_90_days': last_90_days,
                'recent_count': recent_half,
                'older_count': older_half,
                'time_risk_score': time_risk_score,
            }, alert_history_window_days)

            risk_pct = float(risk_summary.get('risk_score', 50.0))
            safety_score = float(risk_summary.get('safety_score', 50.0))
            risk_level = str(risk_summary.get('risk_level', 'Moderate'))

            # The calculate_unified_risk_summary function now handles zero-crime areas consistently,
            # returning 95% safety for areas with no crimes. No manual override needed.

            logger.info(
                f"📍 Unified safety data: risk_score={risk_pct}%, safety={safety_score}%, "
                f"risk={risk_level}, crimes={total_crimes}"
            )

            return {
                'safety_score': float(safety_score),
                'risk_pct': float(risk_pct),
                'risk_level': risk_level,
                'total_crimes': int(total_crimes),
                'high_risk_crimes': int(high_risk_count),
                'medium_risk_crimes': int(medium_risk_count),
                'high_risk_crimes_90d': int(high_risk_count_90d),
                'medium_risk_crimes_90d': int(medium_risk_count_90d),
                'low_risk_crimes': max(0, int(total_crimes) - int(high_risk_count) - int(medium_risk_count)),
                'unique_crime_types': int(unique_crime_types),
                'recent_high_risk_crimes': [],
                'data_confidence': risk_summary.get('data_confidence', 'low'),
                'score_components': risk_summary.get('score_components', {}),
                'no_recent_incidents': bool(int(last_90_days) == 0),
                'last_90_days': int(last_90_days),
            }

        except Error as e:
            logger.error(f"Database error getting safety data: {e}")
            return {
                'safety_score': 50.0,
                'risk_pct': 50.0,
                'risk_level': 'Unknown',
                'total_crimes': 0,
                'high_risk_crimes': 0,
                'medium_risk_crimes': 0,
                'low_risk_crimes': 0,
                'unique_crime_types': 0,
                'recent_high_risk_crimes': [],
                'error': str(e)
            }
        finally:
            if cursor:
                cursor.close()
            if conn and conn.is_connected():
                conn.close()
            
            
    async def send_browser_notification(self, alert: Any, user_data: Dict[str, Any]) -> bool:
        try:
            # Use Poisson risk_pct from alert if available, otherwise compute from safety data
            risk_pct_from_alert = getattr(alert, 'risk_pct', None)

            # Get real safety data (for fallback if risk_pct not on alert)
            safety_data = await self.get_real_safety_data(alert.latitude, alert.longitude)

            # Prefer the alert's precomputed Poisson risk_pct; fallback to safety_data
            if risk_pct_from_alert is not None:
                risk_pct = float(risk_pct_from_alert)
            else:
                risk_pct = float(safety_data.get('risk_pct', round(100 - float(safety_data['safety_score']), 1)))

            risk_lvl = safety_data['risk_level']

            # Resolve area display name
            area_translit = getattr(alert, 'area_translit', None)
            location_type = getattr(alert, 'location_type', 'monitored').upper()
            severity = getattr(alert, 'severity', None)
            total_crimes = safety_data.get('total_crimes', getattr(alert, 'total_crimes', 0))
            high_risk_count = safety_data.get('high_risk_crimes', alert.high_risk_crimes)

            raw_address = alert.address
            # Consistently normalize area name for display
            area_display_name = raw_address.split('(')[0].strip() if '(' in raw_address else raw_address.strip()
            area_display_name = normalize_area_name(area_display_name)
            
            logger.info(f"📍 Dispatching browser notification: {area_display_name} (Level: {risk_lvl}, Risk: {risk_pct}%)")

            # ── Find highest-risk sub-area ────────────────────────────────────
            subareas = getattr(alert, 'subareas', None) or []
            top_subarea_name = None
            top_subarea_risk_pct = None
            if subareas:
                try:
                    top = max(subareas, key=lambda s: float(s.get('risk_pct', 0) or s.get('safety_score', 0)))
                    top_subarea_name = top.get('name')
                    top_subarea_risk_pct = top.get('risk_pct') or round(100 - float(top.get('safety_score', 50)), 1)
                except Exception:
                    pass

            # ── Dominant crime type ───────────────────────────────────────────
            dominant_crime = getattr(alert, 'dominant_crime_type', None)

            # Determine severity
            if not severity:
                if risk_pct >= 81:
                    severity = "critical"
                elif risk_pct >= 51:
                    severity = "high"
                elif risk_pct >= 21:
                    severity = "medium"
                else:
                    severity = "low"

            # ── Safe Attribute Access for Time/Label ──
            def _get_val(obj, key, default=None):
                if isinstance(obj, dict): return obj.get(key, default)
                return getattr(obj, key, default)

            time_label = _get_val(alert, 'time_risk_label', 'Night') or 'Night'
            alert_type_str = str(_get_val(alert, 'alert_type', ''))
            severity = _get_val(alert, 'severity')
            incident_type  = _get_val(alert, 'incident_type', dominant_crime if 'incident' in alert_type_str else None)
            location_label = location_type.title()  # Home / Work / Monitored

            # 🎯 User Goal: "You just entered danger" structure
            _is_hist = "historical" in risk_lvl.lower() or (risk_pct <= 35 and "Proximity" in getattr(alert, 'alert_trigger_reason', ''))
            _time_str = (time_label or "night").lower()
            radius_km = float(getattr(alert, 'radius_km', 1.0) or 1.0)
            radius_label = f"{radius_km:g}"
            
            if location_type == "CURRENT" or 'movement' in alert_type_str.lower():
                if _is_hist:
                    title = "🚨 High-Risk Area Nearby"
                    body  = f"You are within {radius_label} km of a historically high-risk zone in {area_display_name}. Risk is higher at {_time_str}."
                else:
                    title = "🚨 Entered High-Risk Zone"
                    body  = f"Recent high-risk incidents detected near your location in {area_display_name}. Stay alert — especially at {_time_str}."
                
                action_map_url   = f"/dashboard?tab=map&area={area_display_name}&alert=live"
                action_route_url = f"/dashboard?tab=routes&from=current&to={area_display_name}"
            elif 'incident' in alert_type_str or 'new_incident' in alert_type_str:
                # 👉 INCIDENT-BASED ALERT
                incident_count = getattr(alert, '_recent_total', 1)
                crime_label = incident_type or dominant_crime or 'incident'
                title = f"🚨 {crime_label.title()} Near Your {location_label}"
                body  = f"A {severity}-severity {crime_label.lower()} was just reported in {area_display_name}. Risk is higher at {_time_str}."
                action_map_url   = f"/dashboard?tab=map&area={area_display_name}&alert=incident"
                action_route_url = f"/dashboard?tab=routes&avoid={area_display_name}"
            else:
                # 👉 DEFAULT / BACKGROUND MONITOR
                title = f"🚨 Safety Alert: {area_display_name}"
                body  = f"Risk level: {risk_pct:.0f}% ({risk_lvl}). Higher risk at {_time_str}."
                action_map_url   = f"/dashboard?tab=map&area={area_display_name}"
                action_route_url = f"/dashboard?tab=routes"

            icon = "/warning-icon.png" if risk_pct >= 51 else "/safe-icon.png"
            tag  = f"safevision-{alert_type_str or 'alert'}"

            # Notification options with deep-link action buttons
            notification_options = {
                'icon':     icon,
                'tag':      tag,
                'renotify': True,
                'data': {
                    'action':               'open_dashboard',
                    'url':                  action_map_url,
                    'area':                 area_display_name,
                    'overall_risk_pct':     risk_pct,
                    'overall_risk_level':   risk_lvl,
                    'top_subarea':          top_subarea_name,
                    'top_subarea_risk_pct': top_subarea_risk_pct,
                    'dominant_crime':       dominant_crime,
                    'timestamp':            datetime.now().isoformat(),
                    'map_url':              action_map_url,
                    'route_url':            action_route_url,
                }
            }

            # Store notification in database for frontend notification panel
            await self.store_browser_notification(
                alert.user_id,
                title,
                body,
                alert.alert_type,
                {
                    'safety_score': safety_data['safety_score'],
                    'risk_pct':     risk_pct,
                    'risk_level':   risk_lvl,
                    'address':      alert.address,
                    'latitude':     alert.latitude,
                    'longitude':    alert.longitude,
                    'total_crimes': total_crimes,
                    'high_risk_crimes': high_risk_count,
                    'alert_type':   alert.alert_type,
                    'severity':     severity,
                    'location_type': location_type,
                    'top_subarea':  top_subarea_name,
                    'top_subarea_risk_pct': top_subarea_risk_pct,
                    'dominant_crime': dominant_crime,
                    'area_name':    area_display_name,
                    'area_translit': area_translit,
                    'map_url':      action_map_url,
                    'route_url':    action_route_url,
                }
            )

            push_result = await self.send_web_push_notification(
                alert.user_id,
                title,
                body,
                notification_options
            )

            if push_result:
                logger.info(f"✅ Browser push notification sent for user {alert.user_id}")
            else:
                logger.warning(f"❌ Browser push notification failed for user {alert.user_id}")
            return push_result

        except Exception as e:
            logger.error(f"❌ Failed to send browser notification: {e}")
            return False
        
    async def send_web_push_notification(self, user_id: int, title: str, body: str, options: Optional[Dict[str, Any]] = None):
        try:  # Handle None options by providing empty dict
            if options is None:
               options = {}
        
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
        
            # Get user's browser push subscription
            cursor.execute("""
            SELECT endpoint, p256dh, auth 
            FROM browser_push_subscriptions 
            WHERE user_id = %s
        """, (user_id,))
        
            subscription_raw = cursor.fetchone()
        
            if not subscription_raw:
               logger.warning(f"No browser push subscription found for user {user_id}")
               return False
        
        # Type assertion to help Pylance understand this is a dictionary
            subscription = cast(Dict[str, Any], subscription_raw)

        # Prepare push payload
            payload = {
                "title":   title,
                "body":    body,
                "icon":    options.get('icon', '/icon-192x192.png'),
                "badge":   '/badge-72x72.png',
                "tag":     options.get('tag', 'safevision-alert'),
                "timestamp": datetime.now().isoformat(),
                "data":    options.get('data', {}),
                "actions": [
                    {
                        "action": "view_map",
                        "title":  "🗺️ View Map",
                        "icon":   "/map-icon.png"
                    },
                    {
                        "action": "safer_route",
                        "title":  "🦭 Safer Route",
                        "icon":   "/route-icon.png"
                    },
                    {
                        "action": "dismiss",
                        "title":  "Dismiss"
                    }
                ]
            }

        # Send using pywebpush (you'll need to install: pip install pywebpush)
            try:
                from pywebpush import webpush, WebPushException
            
                subscription_info = {
                "endpoint": subscription['endpoint'],
                "keys": {
                    "p256dh": subscription['p256dh'],
                    "auth": subscription['auth']
                }
            }
            
                webpush(
                  subscription_info=subscription_info,
                  data=json.dumps(payload),
                                    vapid_private_key=self.vapid_private_key_for_webpush,
                  vapid_claims={
                    "sub": "mailto:safevision.noreply@gmail.com",
                    "exp": int((datetime.now() + timedelta(hours=12)).timestamp())
                }
            )
            
                logger.info(f"✅ Web push sent successfully to user {user_id}")
                return True
            
            except ImportError:
                logger.warning("pywebpush not installed, skipping actual push delivery")
                logger.info(f"Would send push: {title} - {body}")
                return False
            except WebPushException as ex:
                logger.error(f"Web push failed: {ex}")
            # If subscription is invalid, remove it
                if ex.response and ex.response.status_code == 410:
                   cursor.execute("DELETE FROM browser_push_subscriptions WHERE user_id = %s", (user_id,))
                   conn.commit()
                   logger.info(f"Removed invalid subscription for user {user_id}")
                return False
            
        except Exception as e:
            logger.error(f"Error sending web push notification: {e}")
            return False
        finally:
            if cursor:
               cursor.close()
            if conn and conn.is_connected():
               conn.close()

    
    async def store_browser_notification(self, user_id: int, title: str, body: str, alert_type: str, data: Dict[str, Any]):
        """Store browser notification in database for frontend retrieval"""
        conn = None
        cursor = None
        try:
            if not user_id or not title or not body:
               logger.error("❌ Cannot store browser notification: missing required fields")
               return

            conn = get_db_connection()
            cursor = conn.cursor()

        # Use safe serialization
            safe_data = self.safe_json_serialize(data)

            cursor.execute("""
            INSERT INTO browser_notifications
            (user_id, title, message, alert_type, notification_data, is_read, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (
            user_id,
            title,
            body,
            alert_type,
            json.dumps(safe_data, default=str),  # Extra safety
            False,
            datetime.now()
        ))

            conn.commit()
            logger.info(f"✅ Browser notification stored for user {user_id}")

        except Error as e:
            logger.error(f"Database error storing browser notification: {e}")
            if conn:
               conn.rollback()
        except Exception as e:
            logger.error(f"Unexpected error storing browser notification: {e}")
            if conn:
               conn.rollback()
        finally:
            if cursor:
               cursor.close()
            if conn and conn.is_connected():
               conn.close()

    async def send_alert_email(self, alert: Any, user_email: str) -> bool:
        try:
            # Get real user data
            user_data = await self.get_real_user_data(alert.user_id)
            if not user_data:
                logger.error(f"User data not found for user_id: {alert.user_id}")
                return False

            # ── Generate 24-hour magic-link token for email button deep-links ──
            email_token = ""
            try:
                from app.routes.auth import generate_email_auth_token
                email_token = generate_email_auth_token(int(alert.user_id))
            except Exception as _tok_err:
                logger.warning(f"⚠️ Could not generate email link token: {_tok_err}")

            safety_data = await self.get_real_safety_data(alert.latitude, alert.longitude)

            # Resolve area metadata from alert object
            area_translit = None
            area_urdu = None
            subareas = getattr(alert, 'subareas', None)
            dominant_crime = getattr(alert, 'dominant_crime_type', None)
            top_crimes_list = getattr(alert, 'top_crimes_list', None)
            recent_7d_crimes = getattr(alert, 'recent_7d_crimes', 0)
            time_risk_label = getattr(alert, 'time_risk_label', None)
            alert_trigger_reason = getattr(alert, 'alert_trigger_reason', None)

            # Prefer precomputed alert risk_pct; otherwise use fresh safety summary
            risk_pct_from_alert = getattr(alert, 'risk_pct', None)
            if risk_pct_from_alert is not None:
                real_risk_pct = float(risk_pct_from_alert)
            else:
                real_risk_pct = float(safety_data.get('risk_pct', round(100 - float(safety_data['safety_score']), 1)))
            canonical_safety_score = float(getattr(alert, 'safety_score', safety_data.get('safety_score', 50.0)) or 50.0)
            canonical_risk_level = str(getattr(alert, 'risk_level', safety_data.get('risk_level', 'Unknown')) or 'Unknown')
            # Prefer counts computed at alert creation time (same area filter basis as dashboard/profile context).
            incidents_90d = int(getattr(alert, 'last_90_days', 0) or 0)
            total_365d = int(getattr(alert, 'total_crimes_365', 0) or 0)
            high_risk_90d = int(getattr(alert, 'high_risk_crimes_90d', 0) or 0)
            medium_risk_90d = int(getattr(alert, 'medium_risk_crimes_90d', 0) or 0)

            # Fallback to recomputed safety_data only when alert payload does not include values.
            if incidents_90d <= 0 and total_365d <= 0:
                incidents_90d = int(safety_data.get('last_90_days', safety_data.get('total_crimes', 0)) or 0)
                total_365d = int(safety_data.get('total_crimes', 0) or 0)
            if high_risk_90d <= 0 and incidents_90d > 0:
                high_risk_90d = int(safety_data.get('high_risk_crimes_90d', safety_data.get('high_risk_crimes', 0)) or 0)
            if medium_risk_90d <= 0 and incidents_90d > 0:
                medium_risk_90d = int(safety_data.get('medium_risk_crimes_90d', safety_data.get('medium_risk_crimes', 0)) or 0)

            # Keep hierarchy valid for all template outputs.
            if high_risk_90d > incidents_90d:
                high_risk_90d = incidents_90d
            if medium_risk_90d > incidents_90d:
                medium_risk_90d = incidents_90d

            # Determine if this is a registered home/work area for TEMPLATE choice
            is_home_area = user_data.get('home_area') and alert.address and user_data['home_area'].lower() in alert.address.lower()
            is_work_area = user_data.get('work_area') and alert.address and user_data['work_area'].lower() in alert.address.lower()

            # Composite risk bands: 0-20 Safe, 21-50 Caution, 51-80 Warning, 81-100 Avoid
            is_safe_area = real_risk_pct <= 20
            
            # If the original alert was tagged as "current" (LIVE sensor), KEEP it as current
            # to ensure the "Live Alert" template is used instead of the "Saved Area" status template.
            _raw_location_type = str(getattr(alert, 'location_type', 'monitored') or 'monitored').lower()
            if _raw_location_type == "current":
                area_type = "current"
                location_type = "current"
            else:
                area_type = "home" if is_home_area else "work" if is_work_area else "monitored"
                location_type = area_type

            # CRITICAL REFINEMENT: Use normalization for the email display
            raw_area = alert.address.split('(')[0].strip() if '(' in alert.address else alert.address
            display_area = normalize_area_name(raw_area)
            
            # Get template data
            area_type_val = getattr(alert, 'location_type', 'monitored').upper()
            
            logger.info(f"📧 Preparing email alert for {area_type_val} area: {display_area} (to {user_email})")

            # ── Check if this is a NEW INCIDENT alert for specialized formatting ──
            alert_type_val = str(getattr(alert, 'alert_type', 'high_risk_zone')).lower()
            if alert_type_val == "new_incident_alert":
                logger.info(f"🚨 Using NEW INCIDENT template for {alert.address}")
                template_data = self.email_templates.new_incident_alert({
                    'username': user_data.get('first_name', user_data.get('username', 'User')),
                    'area_name': display_area,
                    'address': alert.address,
                    'incident_type': getattr(alert, 'incident_type', dominant_crime or 'Incident'),
                    'incidents_list': getattr(alert, 'incidents_list', []),
                    'severity': getattr(alert, 'severity', 'High'),
                    'distance_km': getattr(alert, 'distance_km', 0.5),
                    'risk_pct': real_risk_pct,
                    'high_risk_crimes': high_risk_90d,
                    'total_crimes': incidents_90d,
                    'location_type': location_type,
                    'timestamp': getattr(alert, 'timestamp', datetime.now().strftime('%H:%M')),
                    'email_token': email_token,
                })
            # ── Check if this is a LIVE movement alert for short/urgent formatting ──
            elif not is_safe_area:
                if location_type == "current":
                    template_data = self.email_templates.live_location_alert({
                        'username': user_data.get('username'),
                        'risk_level': canonical_risk_level,
                        'area_name_raw': display_area, # USE NORMALIZED NAME HERE
                        'radius_km': getattr(alert, 'radius_km', None),
                        'safety_score': canonical_safety_score,
                        'risk_pct': real_risk_pct,
                        'total_crimes_365': total_365d,
                        'total_crimes': incidents_90d,
                        'high_risk_crimes': high_risk_90d,
                        'medium_risk_crimes': medium_risk_90d,
                        'dominant_crime_type': dominant_crime,
                        'dominant_crime': dominant_crime,
                        'alert_trigger_reason': alert_trigger_reason,
                        'time_risk_label': time_risk_label,
                        'timestamp': datetime.now().strftime('%H:%M:%S'),
                        'email_token': email_token,
                    })
                elif is_users_area or location_type in ("home", "work"):
                    template_data = self.email_templates.high_risk_alert_enhanced({
                        'username': user_data.get('first_name', user_data.get('username', 'User')),
                        'area_name': alert.address,
                        'area_translit': area_translit,
                        'area_urdu': area_urdu,
                        'area_type': area_type.upper(),
                        'safety_score': canonical_safety_score,
                        'risk_pct': real_risk_pct,
                        'risk_level': canonical_risk_level,
                        'high_risk_crimes': high_risk_90d,
                        'medium_risk_crimes': medium_risk_90d,
                        'total_crimes': incidents_90d,
                        'total_crimes_365': total_365d,
                        'no_recent_but_historical': bool(getattr(alert, 'no_recent_but_historical', False)),
                        'unique_crime_types': safety_data['unique_crime_types'],
                        'dominant_crime': dominant_crime,
                        'subareas': subareas,
                        'top_crimes_list': top_crimes_list,
                        'recent_7d_crimes': recent_7d_crimes,
                        'time_risk_label': time_risk_label,
                        'alert_trigger_reason': alert_trigger_reason,
                        'recent_high_risk_crimes': safety_data.get('recent_high_risk_crimes', []),
                        'recent_incidents': incidents_90d,
                        'latest_incident_type': dominant_crime or "High risk activity",
                        'precautions': "Take extreme caution in this area. Consider alternative routes if possible.",
                        'user_alert_radius': user_data.get('alert_radius', 5),
                        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        'email_token': email_token,
                    })
                else:
                    template_data = self.email_templates.high_risk_alert({
                        'username': user_data.get('first_name', user_data.get('username', 'User')),
                        'address': alert.address,
                        'area_name': alert.address,
                        'area_translit': area_translit,
                        'area_urdu': area_urdu,
                        'safety_score': canonical_safety_score,
                        'risk_pct': real_risk_pct,
                        'risk_level': canonical_risk_level,
                        'high_risk_crimes': high_risk_90d,
                        'medium_risk_crimes': medium_risk_90d,
                        'total_crimes': incidents_90d,
                        'total_crimes_365': total_365d,
                        'no_recent_but_historical': bool(getattr(alert, 'no_recent_but_historical', False)),
                        'unique_crime_types': safety_data['unique_crime_types'],
                        'dominant_crime': dominant_crime,
                        'subareas': subareas,
                        'top_crimes_list': top_crimes_list,
                        'recent_7d_crimes': recent_7d_crimes,
                        'time_risk_label': time_risk_label,
                        'alert_trigger_reason': alert_trigger_reason,
                        'recent_high_risk_crimes': safety_data.get('recent_high_risk_crimes', []),
                        'area': alert.address,
                        'user_alert_radius': user_data.get('alert_radius', 5),
                        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        'email_token': email_token,
                    })
            else:
                template_data = self.email_templates.safe_area_alert({
                    'username': user_data.get('first_name', user_data.get('username', 'User')),
                    'address': alert.address,
                    'area_name': alert.address,
                    'area_translit': area_translit,
                    'area_urdu': area_urdu,
                    'area_type': area_type.upper(),
                    'safety_score': canonical_safety_score,
                    'risk_pct': real_risk_pct,
                    'risk_level': canonical_risk_level,
                    'total_crimes': incidents_90d,
                    'total_crimes_365': total_365d,
                    'no_recent_but_historical': bool(getattr(alert, 'no_recent_but_historical', False)),
                    'recent_7d_crimes': recent_7d_crimes,
                    'time_risk_label': time_risk_label,
                    'alert_trigger_reason': alert_trigger_reason,
                    'top_crimes_list': top_crimes_list,
                    'area': alert.address,
                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'email_token': email_token,
                })

            logger.info(
                f"📧 Using {'risk' if not is_safe_area else 'safe-area'} email template "
                f"for alert type '{alert.alert_type}' at {alert.address} (Risk: {real_risk_pct}%)"
            )

            # Create email message
            msg = MIMEMultipart('alternative')
            msg['From'] = f"SafeVision Alerts <{self.email_config['smtp_username']}>"
            msg['To'] = user_email
            msg['Subject'] = template_data['subject']
            msg['X-Priority'] = '1'
            msg['X-MSMail-Priority'] = 'High'
            msg['Importance'] = 'High'
            msg['List-Unsubscribe'] = f'<mailto:{self.email_config["smtp_username"]}?subject=unsubscribe>'
            msg['List-Unsubscribe-Post'] = 'List-Unsubscribe=One-Click'
            msg['Auto-Submitted'] = 'auto-generated'
            msg['Precedence'] = 'bulk'
            msg['Message-ID'] = f"<{datetime.now().strftime('%Y%m%d%H%M%S')}.{user_email.split('@')[0]}@crimevision.com>"
            msg['X-Auto-Response-Suppress'] = 'OOF, AutoReply'
            msg['X-Report-Abuse'] = f'Please report abuse to {self.email_config["smtp_username"]}'

            # Attach HTML and plain text
            part1 = MIMEText(template_data['text'], 'plain', 'utf-8')
            part2 = MIMEText(template_data['html'], 'html', 'utf-8')
            msg.attach(part1)
            msg.attach(part2)

            # Send email
            logger.info(f"📧 Sending email alert to {user_email} for {alert.alert_type} at {alert.address}")
            with smtplib.SMTP(self.email_config['smtp_server'], self.email_config['smtp_port']) as server:
                server.starttls()
                server.login(self.email_config['smtp_username'], self.email_config['smtp_password'])
                server.send_message(msg)

            await self.log_notification_sent(alert.user_id, 'email', alert.alert_type, True)

            risk_status = "safe" if is_safe_area else "risk"
            logger.info(f"✅ {risk_status} email alert sent to {user_email} for {alert.alert_type} (Risk: {real_risk_pct}%)")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to send email alert to {user_email} for {alert.alert_type}: {e}")
            await self.log_notification_sent(alert.user_id, 'email', alert.alert_type, False, str(e))
            return False
    
    async def send_comprehensive_alert(self, alert: Any) -> Dict[str, bool]:
        """Send comprehensive alert through all available channels with real data"""
        user_data = await self.get_real_user_data(alert.user_id)
        if not user_data:
            return {'email': False, 'browser': False}

        results = {}

        # Send email alert
        if user_data.get('email'):
            results['email'] = await self.send_alert_email(alert, user_data['email'])

        # Send browser notification
        results['browser'] = await self.send_browser_notification(alert, user_data)

        # Log comprehensive alert sent
        await self.log_comprehensive_alert(alert.user_id, alert.alert_type, results)

        return results

    async def notify_nearby_users_of_incident(self, incident_data: Dict[str, Any]):
        """
        Notify all users whose registered areas or last known locations are near a new incident.
        This is a proactive 'immediate' alert.
        """
        lat = incident_data.get('latitude')
        lng = incident_data.get('longitude')
        if lat is None or lng is None:
            logger.warning("Proactive Alert: Missing latitude/longitude for incident notification")
            return

        incident_type = incident_data.get('incident_type') or incident_data.get('crime_type') or 'Incident'
        severity = str(incident_data.get('severity') or incident_data.get('risk_level') or 'Medium').capitalize()
        area_name = incident_data.get('area') or 'Nearby Area'

        # SQL to find users within their alert_radius (default 2km if radius is NULL)
        # Check proximity to home, work, and last known location.
        query = """
            SELECT id, email, username, first_name, 
                   home_latitude, home_longitude, 
                   work_latitude, work_longitude, 
                   last_latitude, last_longitude,
                   COALESCE(alert_radius, 2.0) as alert_radius, 
                   browser_notifications_enabled
            FROM users_info
            WHERE 
              (home_latitude IS NOT NULL AND SQRT(POW(111.32 * (home_latitude - %s), 2) + POW(111.32 * (%s - home_longitude) * COS(home_latitude / 57.3), 2)) <= COALESCE(alert_radius, 2.0))
              OR
              (work_latitude IS NOT NULL AND SQRT(POW(111.32 * (work_latitude - %s), 2) + POW(111.32 * (%s - work_longitude) * COS(work_latitude / 57.3), 2)) <= COALESCE(alert_radius, 2.0))
              OR
              (last_latitude IS NOT NULL AND SQRT(POW(111.32 * (last_latitude - %s), 2) + POW(111.32 * (%s - last_longitude) * COS(last_latitude / 57.3), 2)) <= COALESCE(alert_radius, 2.0))
        """
        
        conn = None
        cursor = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute(query, (lat, lng, lat, lng, lat, lng))
            users = cursor.fetchall()
            
            if not users:
                logger.info(f"Proactive Alert: No users found within radius of new {incident_type} at {area_name}")
                return

            logger.info(f"🚨 Proactive Alert: Notifying {len(users)} users about new {incident_type} at {area_name}")

            for user in users:
                user_id = user['id']
                user_email = user['email']
                
                # Determine which location triggered the alert (Home/Work/Current)
                def get_dist(u_lat, u_lng):
                    if u_lat is None or u_lng is None: return 999.0
                    try:
                        return math.sqrt(pow(111.32 * (float(u_lat) - float(lat)), 2) + pow(111.32 * (float(lng) - float(u_lng)) * math.cos(float(u_lat) / 57.3), 2))
                    except (ValueError, TypeError):
                        return 999.0

                dists = {
                    'home': get_dist(user['home_latitude'], user['home_longitude']),
                    'work': get_dist(user['work_latitude'], user['work_longitude']),
                    'current': get_dist(user['last_latitude'], user['last_longitude'])
                }
                
                closest_type = min(dists, key=lambda k: dists[k])
                min_dist = dists[closest_type]
                
                if min_dist > user['alert_radius'] + 0.1: # Small buffer
                    continue

                # Setup Alert data for template
                alert_payload = {
                    'area_name': area_name,
                    'incident_type': incident_type,
                    'severity': severity,
                    'distance_km': min_dist,
                    'location_type': closest_type,
                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }

                # 1. Store and Send Browser Notification (if enabled)
                if user.get('browser_notifications_enabled'):
                    title = f"🚨 URGENT: {incident_type} nearby"
                    body = f"{severity} severity incident reported {min_dist:.2f}km from your {closest_type} area in {area_name}."
                    
                    # Create a mock alert object for reuse of existing storage/push logic
                    class ProactiveAlert:
                        def __init__(self, u_id, lt, ln, addr, it):
                            self.user_id = u_id
                            self.latitude = lt
                            self.longitude = ln
                            self.address = addr
                            self.alert_type = "proximity_incident"
                            self.severity = it
                    
                    mock_alert = ProactiveAlert(user_id, lat, lng, area_name, severity)
                    
                    await self.store_browser_notification(
                        user_id, title, body, "proximity_incident", 
                        {**alert_payload, 'address': area_name, 'latitude': lat, 'longitude': lng}
                    )
                    
                    await self.send_web_push_notification(user_id, title, body, {
                        'tag': 'incident-proximity',
                        'data': {'action': 'open_dashboard', 'url': '/dashboard/alerts'}
                    })

                # 2. Send Email Notification
                try:
                    template_data = self.email_templates.nearby_incident_alert(alert_payload)
                    
                    msg = MIMEMultipart('alternative')
                    msg['From'] = f"SafeVision Proximity Alerts <{self.email_config['smtp_username']}>"
                    msg['To'] = user_email
                    msg['Subject'] = template_data['subject']
                    msg['X-Priority'] = '1' # High priority
                    
                    part1 = MIMEText(template_data['text'], 'plain', 'utf-8')
                    part2 = MIMEText(template_data['html'], 'html', 'utf-8')
                    msg.attach(part1)
                    msg.attach(part2)

                    with smtplib.SMTP(self.email_config['smtp_server'], self.email_config['smtp_port']) as server:
                        server.starttls()
                        server.login(self.email_config['smtp_username'], self.email_config['smtp_password'])
                        server.send_message(msg)
                    
                    await self.log_notification_sent(user_id, 'email', 'proximity_incident', True)
                    logger.info(f"✅ Proximity email sent to {user_email}")
                except Exception as e:
                    logger.error(f"Failed to send proximity email to {user_email}: {e}")
                    await self.log_notification_sent(user_id, 'email', 'proximity_incident', False, str(e))

        except Exception as e:
            logger.error(f"Error in notify_nearby_users_of_incident: {e}")
            import traceback
            logger.error(traceback.format_exc())
        finally:
            if cursor:
                cursor.close()
            if conn and conn.is_connected():
                conn.close()

    async def send_weekly_safety_report(self, user_email: str, report_data: Dict[str, Any]) -> bool:
        """Send a weekly safety summary report email"""
        try:
            # report_data expected keys: area_name, stats (total_7d, high_7d, safety_score), trend, obs_trend, obs_frequency
            template_data = self.email_templates.weekly_safety_report(report_data)
            
            msg = MIMEMultipart('alternative')
            msg['From'] = f"SafeVision Reports <{self.email_config['smtp_username']}>"
            msg['To'] = user_email
            msg['Subject'] = template_data['subject']
            
            part1 = MIMEText(template_data['text'], 'plain', 'utf-8')
            part2 = MIMEText(template_data['html'], 'html', 'utf-8')
            msg.attach(part1)
            msg.attach(part2)

            with smtplib.SMTP(self.email_config['smtp_server'], self.email_config['smtp_port']) as server:
                server.starttls()
                server.login(self.email_config['smtp_username'], self.email_config['smtp_password'])
                server.send_message(msg)
            
            area_label = str(report_data.get('area_label', '')).strip().lower()
            log_alert_type = f"weekly_report_{area_label}" if area_label else "weekly_report"
            await self.log_notification_sent(report_data['user_id'], 'email', log_alert_type, True)
            return True
        except Exception as e:
            logger.error(f"Failed to send weekly report to {user_email}: {e}")
            if 'user_id' in report_data:
                area_label = str(report_data.get('area_label', '')).strip().lower()
                log_alert_type = f"weekly_report_{area_label}" if area_label else "weekly_report"
                await self.log_notification_sent(report_data['user_id'], 'email', log_alert_type, False, str(e))
            return False

    async def log_notification_sent(self, user_id: int, notification_type: str, alert_type: str, success: bool, error_message: Optional[str] = None):
        """Log notification delivery status"""
        conn = None
        cursor = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO notification_logs
                (user_id, notification_type, alert_type, success, error_message, created_at)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (user_id, notification_type, alert_type, success, error_message, datetime.now()))

            conn.commit()

        except Error as e:
            logger.error(f"Failed to log notification: {e}")
        finally:
            if cursor:
                cursor.close()
            if conn and conn.is_connected():
                conn.close()

    async def log_comprehensive_alert(self, user_id: int, alert_type: str, results: Dict[str, bool]):
        """Log comprehensive alert delivery"""
        conn = None
        cursor = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO comprehensive_alerts
                (user_id, alert_type, email_sent, browser_sent, overall_success, created_at)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (
                user_id,
                alert_type,
                results.get('email', False),
                results.get('browser', False),
                any(results.values()),
                datetime.now()
            ))

            conn.commit()

        except Error as e:
            logger.error(f"Failed to log comprehensive alert: {e}")
        finally:
            if cursor:
                cursor.close()
            if conn and conn.is_connected():
                conn.close()
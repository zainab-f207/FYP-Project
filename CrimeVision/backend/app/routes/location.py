import asyncio
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Request
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import logging
import json
import aiohttp
import traceback
from ..core.database import get_db_connection
from ..models.schemas import LocationUpdateRequest, LocationHistoryResponse, LocationTrackingPreferences, RiskZoneAlert
from ..dependencies import get_current_user
from ..alert_notifications import AlertNotificationSystem
from .alerts import check_location_risk, alert_notification_system, send_alert_notification, create_and_send_alert

# Configure logging
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/location")

def is_valid_pakistan_coordinates(lat: float, lng: float) -> bool:
    """Enhanced Pakistan coordinates validation"""
    try:
        # Pakistan approximate bounds with buffer
        min_lat = 20.0  # Southern border with buffer
        max_lat = 40.0  # Northern border with buffer
        min_lng = 58.0  # Western border with buffer
        max_lng = 80.0  # Eastern border with buffer

        return min_lat <= float(lat) <= max_lat and min_lng <= float(lng) <= max_lng
    except (ValueError, TypeError):
        return False

def calculate_accuracy_score(accuracy: Optional[float], location_source: str, device_type: str) -> float:
    """Calculate accuracy score based on various factors"""
    try:
        if accuracy is None:
            accuracy = 1000  # Default accuracy if not provided

        base_score = 100.0

        if location_source == 'gps_high_accuracy':
            if accuracy <= 50:
                return base_score * 0.95  # Excellent
            elif accuracy <= 100:
                return base_score * 0.85  # Good
            elif accuracy <= 500:
                return base_score * 0.70  # Fair
            elif accuracy <= 1000:
                return base_score * 0.50  # Poor
            else:
                return base_score * 0.30  # Very poor
        elif location_source == 'gps':
            if accuracy <= 100:
                return base_score * 0.80
            elif accuracy <= 500:
                return base_score * 0.65
            else:
                return base_score * 0.45
        elif location_source == 'ip_fallback':
            return base_score * 0.40  # IP-based is less accurate
        else:
            return base_score * 0.60  # Default
    except Exception as e:
        logger.error(f"Error calculating accuracy score: {str(e)}")
        return 50.0  # Default score on error

def get_db_cursor(db):
    """Safe database cursor acquisition"""
    try:
        return db.cursor()
    except Exception as e:
        logger.error(f"Failed to get database cursor: {str(e)}")
        raise HTTPException(status_code=500, detail="Database connection error")

@router.post("/update")
async def update_location(
    request: Request,
    location_data: LocationUpdateRequest,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db_connection)
):
    """Enhanced location update with better error handling and validation"""
    cursor = None
    try:
        user_id = current_user.get("id")
        if not user_id:
            raise HTTPException(status_code=401, detail="User not authenticated")

        # Extract additional info from request
        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("user-agent", "")

        logger.info(f"Location update request from user {user_id}: {location_data.dict()}")

        # Enhanced coordinates validation
        if not is_valid_pakistan_coordinates(location_data.latitude, location_data.longitude):
            logger.warning(f"Invalid coordinates from user {user_id}: {location_data.latitude}, {location_data.longitude}")
            raise HTTPException(
                status_code=400,
                detail="Location coordinates are outside Pakistan boundaries. Please verify your location."
            )

        # Validate required fields
        if location_data.latitude is None or location_data.longitude is None:
            raise HTTPException(status_code=400, detail="Latitude and longitude are required")

        # Adaptive accuracy validation based on source and device
        device_type = getattr(location_data, 'device_type', 'desktop')
        location_source = getattr(location_data, 'location_source', 'gps')
        
        # More lenient accuracy thresholds
        accuracy_threshold = 50000  # 50km threshold for all devices

        if location_data.accuracy and location_data.accuracy > accuracy_threshold:
            logger.warning(f"Low accuracy location from user {user_id}: {location_data.accuracy}m")
            # Don't reject, just warn and proceed
            logger.info(f"Accepting low accuracy location for user {user_id}")

        # Calculate accuracy score
        accuracy_score = calculate_accuracy_score(
            location_data.accuracy,
            location_source,
            device_type
        )

        cursor = get_db_cursor(db)

        # Check if users_info table has the required columns
        try:
            # First, let's check the table structure
            cursor.execute("""
                SELECT COLUMN_NAME 
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_NAME = 'users_info' 
                AND TABLE_SCHEMA = DATABASE()
            """)
            columns = [row[0] for row in cursor.fetchall()]
            
            # Insert location with enhanced data
            cursor.execute("""
                INSERT INTO user_location_history
                (user_id, latitude, longitude, accuracy, accuracy_score, address,
                 risk_level, safety_score, location_source, device_type, client_ip)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                user_id,
                float(location_data.latitude),
                float(location_data.longitude),
                float(location_data.accuracy) if location_data.accuracy else None,
                float(accuracy_score),
                location_data.address,
                None,  # Will be calculated by risk system
                None,  # Will be calculated by risk system
                location_source,
                device_type,
                client_ip
            ))

            # Update user's last location - use compatible SQL that works with different schema versions
            update_sql = """
                UPDATE users_info 
                SET last_location_update = CURRENT_TIMESTAMP
            """
            update_params = []
            
            # Only include columns that exist
            if 'last_latitude' in columns:
                update_sql += ", last_latitude = %s"
                update_params.append(float(location_data.latitude))
            if 'last_longitude' in columns:
                update_sql += ", last_longitude = %s"
                update_params.append(float(location_data.longitude))
            if 'location_accuracy_score' in columns:
                update_sql += ", location_accuracy_score = %s"
                update_params.append(float(accuracy_score))
            if 'location_source' in columns:
                update_sql += ", location_source = %s"
                update_params.append(location_source)
                
            update_sql += " WHERE id = %s"
            update_params.append(user_id)
            
            cursor.execute(update_sql, update_params)

        except Exception as table_error:
            logger.error(f"Table structure issue: {str(table_error)}")
            # Fallback to basic insert
            cursor.execute("""
                INSERT INTO user_location_history
                (user_id, latitude, longitude, accuracy, address, location_source)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (
                user_id,
                float(location_data.latitude),
                float(location_data.longitude),
                float(location_data.accuracy) if location_data.accuracy else None,
                location_data.address,
                location_source
            ))
            
            # Basic user info update
            cursor.execute("""
                UPDATE users_info 
                SET last_location_update = CURRENT_TIMESTAMP 
                WHERE id = %s
            """, (user_id,))

        # Check for high-risk areas with enhanced data
        risk_data = None
        try:
            risk_data = await check_location_risk(
                user_id,
                location_data.latitude,
                location_data.longitude,
                area_name=location_data.address  # pass name for area-name fallback
            )
        except Exception as risk_error:
            logger.warning(f"Risk check failed for user {user_id}: {str(risk_error)}")
            # Continue without risk data

        # Get user's alert monitoring preference
        cursor.execute("SELECT monitor_live_location, live_alerts_enabled FROM users_info WHERE id = %s", (user_id,))
        user_pref = cursor.fetchone()
        monitor_enabled = False
        if user_pref:
            if isinstance(user_pref, dict):
                # Ensure BOTH live location monitoring (background) and live alerts are enabled
                monitor_enabled = bool(user_pref.get('monitor_live_location', False)) and bool(user_pref.get('live_alerts_enabled', True))
            else:
                monitor_enabled = bool(user_pref[0]) and bool(user_pref[1])
        
        # Determine if we should trigger an alert - safety checks for risk_data
        # CRITICAL: Only trigger alerts for REAL location updates (GPS), NOT dashboard entries
        risk_lvl = str(risk_data.get("risk_level", "Low")).lower() if risk_data else "low"
        is_high_risk = bool(risk_data.get("is_high_risk", False)) if risk_data else False
        
        # Trigger alerts for Moderate, High, and Critical risk zones.
        # Avoid triggering for 'Low' risk areas to prevent user fatigue in safe zones.
        # 'medium' and 'moderate' are considered elevated risk for live alerts.
        is_risky = (
            risk_lvl in ["high", "critical", "moderate", "medium", "warning"] or is_high_risk
        )
        
        # ✅ FIX: Only trigger alerts for REAL device GPS locations, NOT dashboard entries
        # Real location sources: 'gps', 'gps_high_accuracy' (actual device tracking)
        # Dashboard entries (no alert): 'dashboard_manual', 'dashboard_gps', 'ip_fallback'
        is_real_location_update = location_source not in ["dashboard_manual", "dashboard_gps", "ip_fallback"]
        
        should_trigger = is_risky and is_real_location_update
        
        logger.info(f"🔍 Live Alert Check: User={user_id}, Area={location_data.address}, Risk={risk_lvl}, LocationSource={location_source}, IsRealUpdate={is_real_location_update}, Enabled={monitor_enabled}, ShouldTrigger={should_trigger}")
        
        if should_trigger and monitor_enabled:
            try:
                await trigger_enhanced_alerts(
                    current_user,
                    location_data,
                    risk_data,
                    background_tasks,
                    accuracy_score
                )

                # Update location record with risk data
                cursor.execute("""
                    UPDATE user_location_history
                    SET risk_level = %s, safety_score = %s, alert_triggered = TRUE
                    WHERE user_id = %s 
                    ORDER BY created_at DESC LIMIT 1
                """, (
                    risk_data.get("risk_level") if risk_data else None,
                    risk_data.get("safety_score") if risk_data else None,
                    user_id
                ))
            except Exception as alert_error:
                logger.error(f"Alert triggering failed for user {user_id}: {str(alert_error)}")

        db.commit()

        logger.info(f"Location updated successfully for user {user_id}")

        return {
            "message": "Location updated successfully",
            "risk_alert": risk_data is not None,
            "accuracy_score": accuracy_score,
            "location_source": location_source
        }

    except HTTPException:
        raise
    except Exception as e:
        if db:
            db.rollback()
        logger.error(f"Failed to update location for user {current_user.get('id')}: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Failed to update location: {str(e)}")
    finally:
        if cursor:
            cursor.close()

async def trigger_enhanced_alerts(user_data: dict, location_data: LocationUpdateRequest,
                                risk_data: dict, background_tasks: BackgroundTasks,
                                accuracy_score: float):
    """Enhanced alert triggering with centralized notification system"""
    try:
        # Prepare enriched user data for the alert system
        # We pass the address as 'current_area' so the alert system can use it for 
        # database lookups (by name) if reverse geocoding is blocked.
        alert_user_data = user_data.copy()
        if location_data.address and location_data.address != "Unknown":
            alert_user_data["current_area"] = location_data.address
        
        # Use the unified create_and_send_alert which handles data enrichment
        # (translit/urdu area names, sub-areas) and triggers both email/push.
        background_tasks.add_task(
            create_and_send_alert,
            alert_user_data,
            "current",
            risk_data,
            location_data.latitude,
            location_data.longitude
        )

        logger.info(f"Live Location Alert queued for user {user_data.get('username')} at {location_data.latitude}, {location_data.longitude} (Area: {location_data.address})")

    except Exception as e:
        logger.error(f"Failed to trigger alerts for user {user_data.get('id', 'unknown')}: {str(e)}")
        logger.error(traceback.format_exc())

@router.get("/preferences")
async def get_location_preferences(
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db_connection)
):
    """Get user's location tracking preferences with enhanced error handling"""
    cursor = None
    try:
        user_id = current_user.get("id")
        if not user_id:
            raise HTTPException(status_code=401, detail="User not authenticated")

        cursor = db.cursor(dictionary=True)
        
        # Check if the required columns exist
        cursor.execute("""
            SELECT COLUMN_NAME 
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_NAME = 'users_info' 
            AND TABLE_SCHEMA = DATABASE()
            AND COLUMN_NAME IN ('location_tracking_enabled', 'location_update_interval', 
                              'background_location_tracking', 'high_risk_alerts_only')
        """)
        existing_columns = {row['COLUMN_NAME'] for row in cursor.fetchall()}
        
        # Build query based on available columns
        select_fields = []
        if 'location_tracking_enabled' in existing_columns:
            select_fields.append('location_tracking_enabled')
        else:
            select_fields.append('NULL as location_tracking_enabled')
            
        if 'location_update_interval' in existing_columns:
            select_fields.append('location_update_interval')
        else:
            select_fields.append('30 as location_update_interval')
            
        if 'background_location_tracking' in existing_columns:
            select_fields.append('background_location_tracking')
        else:
            select_fields.append('NULL as background_location_tracking')
            
        if 'high_risk_alerts_only' in existing_columns:
            select_fields.append('high_risk_alerts_only')
        else:
            select_fields.append('NULL as high_risk_alerts_only')
        
        query = f"SELECT {', '.join(select_fields)} FROM users_info WHERE id = %s"
        cursor.execute(query, (user_id,))

        prefs = cursor.fetchone()
        if not prefs:
            # Return default preferences if user not found
            return {
                "enabled": True,
                "update_interval": 30,
                "background_tracking": False,
                "high_risk_alerts_only": False
            }

        return {
            "enabled": bool(prefs.get("location_tracking_enabled", True)),
            "update_interval": prefs.get("location_update_interval", 30) or 30,
            "background_tracking": bool(prefs.get("background_location_tracking", False)),
            "high_risk_alerts_only": bool(prefs.get("high_risk_alerts_only", False))
        }

    except Exception as e:
        logger.error(f"Failed to fetch preferences for user {current_user.get('id')}: {str(e)}")
        logger.error(traceback.format_exc())
        # Return default preferences on error
        return {
            "enabled": True,
            "update_interval": 30,
            "background_tracking": False,
            "high_risk_alerts_only": False
        }
    finally:
        if cursor:
            cursor.close()

@router.put("/preferences")
async def update_location_preferences(
    preferences: LocationTrackingPreferences,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db_connection)
):
    """Update user's location tracking preferences with schema flexibility"""
    cursor = None
    try:
        user_id = current_user.get("id")
        if not user_id:
            raise HTTPException(status_code=401, detail="User not authenticated")

        cursor = db.cursor()
        
        # Check which columns exist in the table
        cursor.execute("""
            SELECT COLUMN_NAME 
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_NAME = 'users_info' 
            AND TABLE_SCHEMA = DATABASE()
            AND COLUMN_NAME IN ('location_tracking_enabled', 'location_update_interval', 
                              'background_location_tracking', 'high_risk_alerts_only')
        """)
        existing_columns = {row[0] for row in cursor.fetchall()}
        
        # Build update query based on available columns
        update_parts = []
        update_params = []
        
        if 'location_tracking_enabled' in existing_columns:
            update_parts.append("location_tracking_enabled = %s")
            update_params.append(preferences.enabled)
            
        if 'location_update_interval' in existing_columns:
            update_parts.append("location_update_interval = %s")
            update_params.append(preferences.update_interval)
            
        if 'background_location_tracking' in existing_columns:
            update_parts.append("background_location_tracking = %s")
            update_params.append(preferences.background_tracking)
            
        if 'high_risk_alerts_only' in existing_columns:
            update_parts.append("high_risk_alerts_only = %s")
            update_params.append(preferences.high_risk_alerts_only)
        
        if not update_parts:
            # If no preference columns exist, just update a basic field to ensure user exists
            update_parts.append("last_location_update = %s")
            update_params.append(datetime.now())
        
        update_params.append(user_id)
        
        query = f"UPDATE users_info SET {', '.join(update_parts)} WHERE id = %s"
        cursor.execute(query, update_params)

        db.commit()
        return {"message": "Location preferences updated successfully"}

    except Exception as e:
        if db:
            db.rollback()
        logger.error(f"Failed to update preferences for user {current_user.get('id')}: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Failed to update preferences: {str(e)}")
    finally:
        if cursor:
            cursor.close()

@router.get("/history", response_model=List[LocationHistoryResponse])
async def get_location_history(
    days: int = 7,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db_connection)
):
    """Get user's location history for the specified number of days."""
    cursor = None
    try:
        user_id = current_user.get("id")
        if not user_id:
            raise HTTPException(status_code=401, detail="User not authenticated")

        cutoff_date = datetime.now() - timedelta(days=days)

        cursor = db.cursor(dictionary=True)
        cursor.execute("""
            SELECT id, user_id, latitude, longitude, accuracy, address,
                   risk_level, safety_score, created_at, location_source
            FROM user_location_history
            WHERE user_id = %s AND created_at >= %s
            ORDER BY created_at DESC
        """, (user_id, cutoff_date))

        locations = cursor.fetchall()

        return [{
            "id": loc["id"],
            "user_id": loc["user_id"],
            "latitude": float(loc["latitude"]) if loc["latitude"] else 0.0,
            "longitude": float(loc["longitude"]) if loc["longitude"] else 0.0,
            "accuracy": float(loc["accuracy"]) if loc["accuracy"] else None,
            "address": loc["address"],
            "risk_level": loc["risk_level"],
            "safety_score": float(loc["safety_score"]) if loc["safety_score"] else None,
            "created_at": loc["created_at"].isoformat() if loc["created_at"] else None,
            "location_source": loc["location_source"] or "gps"
        } for loc in locations]

    except Exception as e:
        logger.error(f"Failed to fetch location history for user {current_user.get('id')}: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Failed to fetch location history: {str(e)}")
    finally:
        if cursor:
            cursor.close()

@router.get("/status")
async def get_location_status(
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db_connection)
):
    """Get enhanced location status and statistics"""
    cursor = None
    try:
        user_id = current_user.get("id")
        if not user_id:
            raise HTTPException(status_code=401, detail="User not authenticated")

        cursor = db.cursor(dictionary=True)

        # Get current location status with safe column access
        cursor.execute("""
            SELECT 
                last_location_update,
                COALESCE(last_latitude, 0) as last_latitude,
                COALESCE(last_longitude, 0) as last_longitude,
                location_accuracy_score,
                location_source
            FROM users_info
            WHERE id = %s
        """, (user_id,))

        status = cursor.fetchone()

        # Get location statistics
        cursor.execute("""
            SELECT
                COUNT(*) as total_updates,
                AVG(accuracy) as avg_accuracy,
                MIN(accuracy) as best_accuracy,
                MAX(accuracy) as worst_accuracy,
                location_source,
                COUNT(*) as source_count
            FROM user_location_history
            WHERE user_id = %s AND created_at >= %s
            GROUP BY location_source
        """, (user_id, datetime.now() - timedelta(days=7)))

        stats = cursor.fetchall()

        return {
            "current_status": {
                "has_location": status and status["last_latitude"] and status["last_longitude"],
                "last_update": status["last_location_update"].isoformat() if status and status["last_location_update"] else None,
                "accuracy_score": float(status["location_accuracy_score"]) if status and status["location_accuracy_score"] else None,
                "location_source": status["location_source"] if status else None
            },
            "statistics": {
                "total_updates": stats[0]["total_updates"] if stats else 0,
                "accuracy_breakdown": {
                    "average": float(stats[0]["avg_accuracy"]) if stats and stats[0]["avg_accuracy"] else None,
                    "best": float(stats[0]["best_accuracy"]) if stats and stats[0]["best_accuracy"] else None,
                    "worst": float(stats[0]["worst_accuracy"]) if stats and stats[0]["worst_accuracy"] else None
                },
                "sources": {stat["location_source"]: stat["source_count"] for stat in stats} if stats else {}
            }
        }

    except Exception as e:
        logger.error(f"Failed to get location status for user {user_id}: {str(e)}")
        # Return basic status instead of failing
        return {
            "current_status": {
                "has_location": False,
                "last_update": None,
                "accuracy_score": None,
                "location_source": None
            },
            "statistics": {
                "total_updates": 0,
                "accuracy_breakdown": {
                    "average": None,
                    "best": None,
                    "worst": None
                },
                "sources": {}
            }
        }
    finally:
        if cursor:
            cursor.close()

@router.get("/debug-schema")
async def debug_schema(
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db_connection)
):
    """Debug endpoint to check database schema"""
    cursor = None
    try:
        cursor = db.cursor(dictionary=True)
        
        # Check users_info table structure
        cursor.execute("""
            SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE, COLUMN_DEFAULT
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_NAME = 'users_info' 
            AND TABLE_SCHEMA = DATABASE()
            ORDER BY ORDINAL_POSITION
        """)
        users_info_columns = cursor.fetchall()
        
        # Check user_location_history table structure
        cursor.execute("""
            SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE, COLUMN_DEFAULT
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_NAME = 'user_location_history' 
            AND TABLE_SCHEMA = DATABASE()
            ORDER BY ORDINAL_POSITION
        """)
        location_history_columns = cursor.fetchall()
        
        return {
            "users_info_columns": users_info_columns,
            "user_location_history_columns": location_history_columns
        }
        
    except Exception as e:
        logger.error(f"Schema debug failed: {str(e)}")
        return {"error": str(e)}
    finally:
        if cursor:
            cursor.close()


@router.get("/debug")
async def debug_location(
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db_connection)
):
    """Debug endpoint for location issues"""
    try:
        user_id = current_user["id"]
        cursor = db.cursor(dictionary=True)

        # Get recent location attempts
        cursor.execute("""
            SELECT latitude, longitude, accuracy, location_source,
                   device_type, created_at, accuracy_score
            FROM user_location_history
            WHERE user_id = %s
            ORDER BY created_at DESC
            LIMIT 10
        """, (user_id,))

        recent_locations = cursor.fetchall()

        # Get accuracy statistics
        cursor.execute("""
            SELECT
                location_source,
                AVG(accuracy) as avg_accuracy,
                COUNT(*) as count,
                AVG(accuracy_score) as avg_score
            FROM user_location_history
            WHERE user_id = %s AND created_at >= %s
            GROUP BY location_source
        """, (user_id, datetime.now() - timedelta(days=1)))

        accuracy_stats = cursor.fetchall()

        return {
            "recent_locations": [
                {
                    "latitude": float(loc["latitude"]),
                    "longitude": float(loc["longitude"]),
                    "accuracy": float(loc["accuracy"]) if loc["accuracy"] else None,
                    "source": loc["location_source"],
                    "device_type": loc["device_type"],
                    "accuracy_score": float(loc["accuracy_score"]) if loc["accuracy_score"] else None,
                    "timestamp": loc["created_at"].isoformat() if loc["created_at"] else None
                } for loc in recent_locations
            ],
            "accuracy_analysis": {
                stat["location_source"]: {
                    "average_accuracy": float(stat["avg_accuracy"]) if stat["avg_accuracy"] else None,
                    "update_count": stat["count"],
                    "average_score": float(stat["avg_score"]) if stat["avg_score"] else None
                } for stat in accuracy_stats
            }
        }

    except Exception as e:
        logger.error(f"Debug endpoint failed for user {user_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Debug failed: {str(e)}")
    finally:
        cursor.close()

@router.delete("/history")
async def clear_location_history(
    days_to_keep: Optional[int] = None,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db_connection)
):
    """Clear old location history. If days_to_keep is None, clears all history."""
    cursor = None
    try:
        user_id = current_user.get("id")
        if not user_id:
            raise HTTPException(status_code=401, detail="User not authenticated")

        cursor = db.cursor()

        if days_to_keep is None:
            # Clear all history
            cursor.execute("DELETE FROM user_location_history WHERE user_id = %s", (user_id,))
        else:
            # Clear history older than specified days
            cutoff_date = datetime.now() - timedelta(days=days_to_keep)
            cursor.execute("""
                DELETE FROM user_location_history
                WHERE user_id = %s AND created_at < %s
            """, (user_id, cutoff_date))

        deleted_count = cursor.rowcount
        db.commit()

        return {"message": f"Cleared {deleted_count} location records"}

    except Exception as e:
        if db:
            db.rollback()
        logger.error(f"Failed to clear history for user {user_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to clear history: {str(e)}")
    finally:
        if cursor:
            cursor.close()

@router.get("/ip-geolocation")
async def get_ip_geolocation():
    """Get location from IP address using multiple services with fallback"""
    try:
        services = [
            {
                "name": "ipapi",
                "url": "http://ip-api.com/json/",
                "fields": {"lat": "lat", "lon": "lon", "city": "city", "country": "country"}
            },
            {
                "name": "ipinfo",
                "url": "https://ipinfo.io/json",
                "fields": {"lat": "loc", "lon": "loc", "city": "city", "country": "country"}
            }
        ]

        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
            for service in services:
                try:
                    logger.info(f"Trying IP geolocation service: {service['name']}")
                    async with session.get(service["url"]) as response:
                        if response.status == 200:
                            data = await response.json()
                            logger.info(f"Response from {service['name']}: {data}")

                            # Extract location data based on service fields
                            lat, lon = None, None
                            
                            if service["name"] == "ipinfo":
                                if "loc" in data:
                                    try:
                                        lat_str, lon_str = data["loc"].split(",")
                                        lat = float(lat_str)
                                        lon = float(lon_str)
                                    except (ValueError, AttributeError) as e:
                                        logger.warning(f"Failed to parse location from ipinfo: {e}")
                                        continue
                                else:
                                    logger.warning("No 'loc' field in ipinfo response")
                                    continue
                            else:  # ipapi
                                lat = data.get(service["fields"]["lat"])
                                lon = data.get(service["fields"]["lon"])
                                
                                # Convert to float if they exist
                                if lat is not None:
                                    try:
                                        lat = float(lat)
                                    except (ValueError, TypeError):
                                        lat = None
                                if lon is not None:
                                    try:
                                        lon = float(lon)
                                    except (ValueError, TypeError):
                                        lon = None

                            if lat is not None and lon is not None and not (lat == 0 and lon == 0):
                                # Validate coordinates are within Pakistan bounds
                                if is_valid_pakistan_coordinates(lat, lon):
                                    logger.info(f"✅ Valid coordinates found from {service['name']}: {lat}, {lon}")
                                    return {
                                        "latitude": lat,
                                        "longitude": lon,
                                        "city": data.get(service["fields"]["city"], ""),
                                        "country": data.get(service["fields"]["country"], ""),
                                        "source": service["name"],
                                        "accuracy": 5000  # IP-based accuracy estimate
                                    }
                                else:
                                    logger.warning(f"IP location outside Pakistan bounds from {service['name']}: {lat}, {lon}")
                            else:
                                logger.warning(f"Missing or invalid coordinates from {service['name']}: lat={lat}, lon={lon}")

                except asyncio.TimeoutError:
                    logger.warning(f"Timeout from {service['name']}")
                    continue
                except aiohttp.ClientError as e:
                    logger.warning(f"Network error from {service['name']}: {str(e)}")
                    continue
                except Exception as e:
                    logger.warning(f"Unexpected error from {service['name']}: {str(e)}")
                    continue

        # If all services fail, return a default location (Islamabad)
        logger.warning("All IP geolocation services failed, using default location")
        return {
            "latitude": 33.6844,
            "longitude": 73.0479,
            "city": "Islamabad",
            "country": "Pakistan",
            "source": "default",
            "accuracy": 10000
        }

    except Exception as e:
        logger.error(f"IP geolocation failed: {str(e)}")
        # Return default location instead of raising exception
        return {
            "latitude": 33.6844,
            "longitude": 73.0479,
            "city": "Islamabad",
            "country": "Pakistan",
            "source": "error_fallback",
            "accuracy": 15000
        }

        
@router.get("/reverse-geocode")
async def reverse_geocode(lat: float, lng: float):
    """Reverse geocode coordinates to address using backend API calls"""
    try:
        logger.info(f"Reverse geocoding request for coordinates: {lat}, {lng}")

        # Validate coordinates
        if not is_valid_pakistan_coordinates(lat, lng):
            raise HTTPException(
                status_code=400,
                detail="Coordinates are outside Pakistan boundaries"
            )

        # Use Nominatim (OpenStreetMap) for reverse geocoding
        nominatim_url = f"https://nominatim.openstreetmap.org/reverse?format=json&lat={lat}&lon={lng}&zoom=18&addressdetails=1"

        async with aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=10),
            headers={
                'User-Agent': 'SafeVision-App-FYP-Project-Pakistan (zainab.fayyaz921@example.com)',
                'Accept': 'application/json'
            }
        ) as session:
            async with session.get(nominatim_url) as response:
                if response.status == 200:
                    data = await response.json()

                    if data and data.get("address"):
                        addr = data["address"]
                        address_parts = []

                        # Enhanced address building logic
                        if addr.get("road"):
                            address_parts.append(addr["road"])
                        if addr.get("neighbourhood"):
                            address_parts.append(addr["neighbourhood"])
                        if addr.get("suburb"):
                            address_parts.append(addr["suburb"])
                        if addr.get("city_district"):
                            address_parts.append(addr["city_district"])
                        if addr.get("city"):
                            address_parts.append(addr["city"])
                        if addr.get("state"):
                            address_parts.append(addr["state"])

                        full_address = ", ".join(address_parts) if address_parts else f"{lat:.4f}, {lng:.4f}"

                        return {
                            "address": full_address,
                            "latitude": lat,
                            "longitude": lng,
                            "details": {
                                "road": addr.get("road"),
                                "neighbourhood": addr.get("neighbourhood"),
                                "suburb": addr.get("suburb"),
                                "city_district": addr.get("city_district"),
                                "city": addr.get("city"),
                                "state": addr.get("state"),
                                "country": addr.get("country"),
                                "postcode": addr.get("postcode")
                            },
                            "source": "nominatim"
                        }
                    else:
                        # Fallback to basic coordinate string
                        return {
                            "address": f"{lat:.4f}, {lng:.4f}",
                            "latitude": lat,
                            "longitude": lng,
                            "details": {},
                            "source": "coordinates"
                        }
                else:
                    logger.warning(f"Nominatim API error: {response.status}")
                    # Fallback to basic coordinate string
                    return {
                        "address": f"{lat:.4f}, {lng:.4f}",
                        "latitude": lat,
                        "longitude": lng,
                        "details": {},
                        "source": "coordinates"
                    }

    except aiohttp.ClientError as e:
        logger.error(f"Network error during reverse geocoding: {str(e)}")
        # Fallback to basic coordinate string
        return {
            "address": f"{lat:.4f}, {lng:.4f}",
            "latitude": lat,
            "longitude": lng,
            "details": {},
            "source": "coordinates"
        }
    except Exception as e:
        logger.error(f"Reverse geocoding failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to reverse geocode coordinates")

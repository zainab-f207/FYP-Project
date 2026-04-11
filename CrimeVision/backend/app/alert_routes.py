from configparser import Error
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Dict, Any, Optional, cast
from datetime import datetime
import json
from .core.database import get_db_connection
from app.dependencies import get_username_from_token
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/api/auth/me/alerts")
def get_user_alerts(
    current_user: str = Depends(get_username_from_token),
    limit: int = Query(50, description="Maximum number of alerts to return", ge=1, le=100),
    offset: int = Query(0, description="Number of alerts to skip", ge=0),
    unread_only: bool = Query(False, description="Return only unread alerts"),
    alert_type: Optional[str] = Query(None, description="Filter by alert type"),
    severity: Optional[str] = Query(None, description="Filter by severity")
):
    """Get personalized alerts for the current user"""
    user_areas = []  # Ensure this is always defined
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        nearby_risk_contexts = []
        # ...existing code...
        # (the code for area_coords and nearby_risk_contexts is only after user_areas is populated, not here)
        # Get user info including location preferences
        cursor.execute("""
            SELECT id, home_area, work_area, alert_radius 
            FROM users_info 
            WHERE username = %s
        """, (current_user,))
        user = cursor.fetchone()
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        user_id = cast(Dict[str, Any], user).get("id")
        user_areas = []
        if cast(Dict[str, Any], user).get("home_area"):
            user_areas.append(cast(Dict[str, Any], user).get("home_area"))
        if cast(Dict[str, Any], user).get("work_area"):
            user_areas.append(cast(Dict[str, Any], user).get("work_area"))
        
        # Build query for user-specific alerts
        query = """
            SELECT 
                id, title, message, alert_type, area, severity, 
                is_read, created_at, expires_at
            FROM user_alerts 
            WHERE user_id = %s
        """
        params = [user_id]
        
        if unread_only:
            query += " AND is_read = FALSE"
        
        if alert_type:
            query += " AND alert_type = %s"
            params.append(alert_type)
            
        if severity:
            query += " AND severity = %s"
            params.append(severity)
        
        # Add expiry check
        query += " AND (expires_at IS NULL OR expires_at > %s)"
        params.append(datetime.now())
        
        query += " ORDER BY created_at DESC LIMIT %s OFFSET %s"
        params.extend([limit, offset])
        
        cursor.execute(query, params)
        user_alerts = cursor.fetchall()
        
        # Get system alerts relevant to this user
        system_query = """
            SELECT 
                id, title, message, alert_type, area, severity,
                created_at, expires_at, 'system' as source
            FROM system_alerts 
            WHERE is_active = TRUE 
            AND (expires_at IS NULL OR expires_at > %s)
        """
        system_params: List[Any] = [datetime.now()]
        
        # If user has specific areas, include area-specific alerts
        if user_areas:
            placeholders = ','.join(['%s'] * len(user_areas))
            system_query += f" AND (area IS NULL OR area IN ({placeholders}))"
            system_params.extend(user_areas)
        else:
            system_query += " AND area IS NULL"
            
        system_query += " ORDER BY created_at DESC LIMIT %s"
        system_params.append(limit)
        
        cursor.execute(system_query, system_params)
        system_alerts = cursor.fetchall()
        
        # Combine and format alerts
        all_alerts = []
        
        # Process user alerts
        for alert in user_alerts:
            # Calculate priority based on severity and recency
            severity_weights = {"critical": 100, "high": 80, "medium": 60, "low": 40}
            priority = severity_weights.get(cast(Dict[str, Any], alert).get("severity", "medium"), 50)
            
            # Increase priority for unread alerts
            if not cast(Dict[str, Any], alert).get("is_read"):
                priority += 20
                
            all_alerts.append({
                "id": cast(Dict[str, Any], alert)["id"],
                "title": cast(Dict[str, Any], alert)["title"],
                "message": cast(Dict[str, Any], alert)["message"],
                "type": cast(Dict[str, Any], alert)["alert_type"],
                "area": cast(Dict[str, Any], alert).get("area"),
                "severity": cast(Dict[str, Any], alert)["severity"],
                "is_read": bool(cast(Dict[str, Any], alert).get("is_read")),
                "created_at": cast(Dict[str, Any], alert)["created_at"].isoformat() if cast(Dict[str, Any], alert)["created_at"] else None,
                "expires_at": cast(Dict[str, Any], alert)["expires_at"].isoformat() if cast(Dict[str, Any], alert)["expires_at"] else None,
                "priority": priority,
                "source": "personal"
            })
        
        # Process system alerts
        for alert in system_alerts:
            severity_weights = {"critical": 100, "high": 80, "medium": 60, "low": 40}
            priority = severity_weights.get(cast(Dict[str, Any], alert).get("severity", "medium"), 50)
            
            all_alerts.append({
                "id": f"system_{cast(Dict[str, Any], alert)['id']}",
                "title": cast(Dict[str, Any], alert)["title"],
                "message": cast(Dict[str, Any], alert)["message"],
                "type": cast(Dict[str, Any], alert)["alert_type"],
                "area": cast(Dict[str, Any], alert).get("area"),
                "severity": cast(Dict[str, Any], alert)["severity"],
                "is_read": False,  # System alerts are always considered unread for display
                "created_at": cast(Dict[str, Any], alert)["created_at"].isoformat() if cast(Dict[str, Any], alert)["created_at"] else None,
                "expires_at": cast(Dict[str, Any], alert)["expires_at"].isoformat() if cast(Dict[str, Any], alert)["expires_at"] else None,
                "priority": priority,
                "source": "system"
            })
        
        # Sort by priority (highest first) then by creation date (newest first)
        all_alerts.sort(key=lambda x: (-x["priority"], x["created_at"]), reverse=True)
        
        # Get unread count
        cursor.execute("""
            SELECT COUNT(*) as unread_count 
            FROM user_alerts 
            WHERE user_id = %s AND is_read = FALSE
            AND (expires_at IS NULL OR expires_at > %s)
        """, (user_id, datetime.now()))
        unread_result = cursor.fetchone()
        unread_count = cast(Dict[str, Any], unread_result)["unread_count"] if unread_result else 0
        
        result = {
            "alerts": all_alerts[:limit],  # Ensure we don't exceed limit
            "total_count": len(all_alerts),
            "unread_count": unread_count,
            "pagination": {
                "limit": limit,
                "offset": offset,
                "has_more": len(all_alerts) > limit
            }
        }
        if nearby_risk_contexts:
            result["nearby_risk_context"] = nearby_risk_contexts
        return result
        
    except Error as e:
        logger.error(f"Database error getting user alerts: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve user alerts")
    finally:
        cursor.close()
        conn.close()

@router.post("/api/community/alerts/subscribe")
async def subscribe_to_alerts(
    alert_subscription: dict,
    current_user: str = Depends(get_username_from_token)
):
    """Subscribe to community alerts"""
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
        
        user_id = cast(Dict[str, Any], user)["id"]
        
        # Prepare subscription data
        subscription_data = {
            "user_id": user_id,
            "alert_types": alert_subscription.get("alert_types", ["all"]),
            "areas": alert_subscription.get("areas", []),
            "radius": alert_subscription.get("radius", 5.0),
            "notification_types": alert_subscription.get("notification_types", ["browser"]),
            "is_active": True,
            "created_at": datetime.now()
        }
        
        # Insert or update subscription
        cursor.execute("""
            INSERT INTO alert_subscriptions 
            (user_id, alert_types, areas, radius, notification_types, is_active, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
            alert_types = VALUES(alert_types),
            areas = VALUES(areas),
            radius = VALUES(radius),
            notification_types = VALUES(notification_types),
            is_active = VALUES(is_active),
            updated_at = VALUES(created_at)
        """, (
            user_id,
            json.dumps(subscription_data["alert_types"]),
            json.dumps(subscription_data["areas"]),
            subscription_data["radius"],
            json.dumps(subscription_data["notification_types"]),
            subscription_data["is_active"],
            subscription_data["created_at"]
        ))
        
        # Update user's browser_notifications_enabled flag
        if "browser" in subscription_data["notification_types"]:
            cursor.execute("""
                UPDATE users_info 
                SET browser_notifications_enabled = TRUE
                WHERE id = %s
            """, (user_id,))
        
        conn.commit()
        
        return {"message": "Successfully subscribed to alerts", "subscription": subscription_data}
        
    except Exception as e:
        logger.error(f"Error subscribing to alerts: {e}")
        if conn:
            conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()
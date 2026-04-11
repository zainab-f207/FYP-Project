from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Dict, Any, List, Optional, cast
from datetime import datetime
import logging
import json
from mysql.connector import Error

from app.core.database import get_db_connection, log_user_activity
from app.dependencies import get_username_from_token

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth/me", tags=["user profile"])

# NOTE: /stats endpoint is handled in main.py (main.py:/api/auth/me/stats)
# This router is intentionally NOT defining /stats to avoid duplicate/conflicting endpoints.
# The correct safety score stats are served from main.py's api_me_stats_alias() function.

@router.get("/activity")
def get_user_recent_activity(current_user: str = Depends(get_username_from_token)):
    """Get user's recent activity for dashboard"""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        # Get user ID
        cursor.execute("SELECT id FROM users_info WHERE username = %s", (current_user,))
        user = cursor.fetchone()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        user = cast(Dict[str, Any], user)
        user_id = user["id"]
        
        # Get recent activity
        cursor.execute("""
            SELECT 
                id,
                activity_type as type,
                activity_details->>'$.message' as description,
                created_at as timestamp,
                activity_details->>'$.area' as area
            FROM user_activity_logs 
            WHERE user_id = %s 
            ORDER BY created_at DESC 
            LIMIT 10
        """, (user_id,))
        
        activities = cursor.fetchall()
        activities = [cast(Dict[str, Any], row) for row in activities]
        
        # Format activities
        formatted_activities = []
        for activity in activities:
            formatted_activities.append({
                "id": activity["id"],
                "type": activity["type"],
                "description": activity.get("description", "User activity"),
                "timestamp": activity["timestamp"].isoformat() if activity["timestamp"] else None,
                "area": activity.get("area")
            })
        
        return formatted_activities
        
    except Exception as e:
        logger.error(f"Database error getting user activity: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve user activity")
    finally:
        cursor.close()
        conn.close()

@router.get("/alerts")
def get_user_alerts(
    current_user: str = Depends(get_username_from_token),
    limit: Optional[int] = None,
    offset: Optional[int] = None,
    unread_only: Optional[bool] = None,
    alert_type: Optional[str] = None,
    severity: Optional[str] = None
):
    # Set default values if not provided
    limit = 50 if limit is None else int(limit)
    offset = 0 if offset is None else int(offset)
    unread_only = False if unread_only is None else bool(unread_only)
    """Get personalized alerts for the current user"""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
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

        # Build query for user-specific alerts - FIXED QUERY
        query = """
            SELECT
                id, title, message, alert_type, area, severity,
                is_read, created_at, expires_at, source
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
        # Convert FastAPI Query objects to integers for MySQL
        limit_val = limit if isinstance(limit, int) else int(limit)
        offset_val = offset if isinstance(offset, int) else int(offset)
        params.extend([limit_val, offset_val])

        cursor.execute(query, tuple(params))
        user_alerts = cursor.fetchall()
        
        # Get system alerts relevant to this user
        user_areas = []
        if cast(Dict[str, Any], user).get("home_area"):
            user_areas.append(cast(Dict[str, Any], user).get("home_area"))
        if cast(Dict[str, Any], user).get("work_area"):
            user_areas.append(cast(Dict[str, Any], user).get("work_area"))
            
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
            alert_dict = cast(Dict[str, Any], alert)
            # Calculate priority based on severity and recency
            severity_weights = {"critical": 100, "high": 80, "medium": 60, "low": 40}
            priority = severity_weights.get(alert_dict.get("severity", "medium"), 50)
            
            # Increase priority for unread alerts
            if not alert_dict.get("is_read"):
                priority += 20
                
            all_alerts.append({
                "id": alert_dict["id"],
                "title": alert_dict["title"],
                "message": alert_dict["message"],
                "type": alert_dict["alert_type"],
                "area": alert_dict.get("area"),
                "severity": alert_dict["severity"],
                "is_read": bool(alert_dict.get("is_read")),
                "created_at": alert_dict["created_at"].isoformat() if alert_dict["created_at"] else None,
                "expires_at": alert_dict["expires_at"].isoformat() if alert_dict["expires_at"] else None,
                "priority": priority,
                "source": "personal"
            })
        
        # Process system alerts
        for alert in system_alerts:
            alert_dict = cast(Dict[str, Any], alert)
            severity_weights = {"critical": 100, "high": 80, "medium": 60, "low": 40}
            priority = severity_weights.get(alert_dict.get("severity", "medium"), 50)
            
            all_alerts.append({
                "id": f"system_{alert_dict['id']}",
                "title": alert_dict["title"],
                "message": alert_dict["message"],
                "type": alert_dict["alert_type"],
                "area": alert_dict.get("area"),
                "severity": alert_dict["severity"],
                "is_read": False,  # System alerts are always considered unread for display
                "created_at": alert_dict["created_at"].isoformat() if alert_dict["created_at"] else None,
                "expires_at": alert_dict["expires_at"].isoformat() if alert_dict["expires_at"] else None,
                "priority": priority,
                "source": "system"
            })
        
        # Sort by priority (highest first) then by creation date (newest first)
        all_alerts.sort(key=lambda x: (-x["priority"], x["created_at"] or ""), reverse=True)
        
        # Get unread count
        cursor.execute("""
            SELECT COUNT(*) as unread_count 
            FROM user_alerts 
            WHERE user_id = %s AND is_read = FALSE
            AND (expires_at IS NULL OR expires_at > %s)
        """, (user_id, datetime.now()))
        unread_result = cursor.fetchone()
        unread_count = cast(Dict[str, Any], unread_result)["unread_count"] if unread_result else 0
        
        # Convert limit to integer for slicing
        limit_val = limit if isinstance(limit, int) else int(limit)
        
        return {
            "alerts": all_alerts[:limit_val],  # Ensure we don't exceed limit
            "total_count": len(all_alerts),
            "unread_count": unread_count,
            "pagination": {
                "limit": limit_val,
                "offset": offset if isinstance(offset, int) else int(offset),
                "has_more": len(all_alerts) > limit_val
            }
        }
        
    except Error as e:
        logger.error(f"Database error getting user alerts: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve user alerts")
    finally:
        cursor.close()
        conn.close()

            
@router.post("/alerts/{alert_id}/read")
def mark_alert_as_read(
    alert_id: int,
    current_user: str = Depends(get_username_from_token)
):
    """Mark a specific alert as read"""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        # Get user ID
        cursor.execute("SELECT id FROM users_info WHERE username = %s", (current_user,))
        user = cursor.fetchone()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        user = cast(Dict[str, Any], user)
        user_id = user["id"]
        
        # Update the alert
        cursor.execute("""
            UPDATE user_alerts 
            SET is_read = TRUE 
            WHERE id = %s AND user_id = %s
        """, (alert_id, user_id))
        
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Alert not found or access denied")
        
        conn.commit()
        
        return {"message": "Alert marked as read", "alert_id": alert_id}
        
    except Exception as e:
        logger.error(f"Database error marking alert as read: {e}")
        raise HTTPException(status_code=500, detail="Failed to update alert")
    finally:
        cursor.close()
        conn.close()

@router.post("/alerts/read-all")
def mark_all_alerts_as_read(
    current_user: str = Depends(get_username_from_token)
):
    """Mark all user alerts as read"""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        # Get user ID
        cursor.execute("SELECT id FROM users_info WHERE username = %s", (current_user,))
        user = cursor.fetchone()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        user = cast(Dict[str, Any], user)
        user_id = user["id"]
        
        # Update all user alerts
        cursor.execute("""
            UPDATE user_alerts 
            SET is_read = TRUE 
            WHERE user_id = %s AND is_read = FALSE
        """, (user_id,))
        
        updated_count = cursor.rowcount
        conn.commit()
        
        return {"message": f"Marked {updated_count} alerts as read"}
        
    except Exception as e:
        logger.error(f"Database error marking all alerts as read: {e}")
        raise HTTPException(status_code=500, detail="Failed to update alerts")
    finally:
        cursor.close()
        conn.close()
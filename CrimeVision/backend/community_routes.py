from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel
from typing import List, Optional, Dict, Any, cast
import logging
from datetime import datetime, timedelta
from mysql.connector import Error

# Import from main app modules for consistency
from app.core.database import get_db_connection
from app.auth_updated import verify_token
from app.core.config import get_logger

logger = get_logger(__name__)

# Pydantic models
class NeighborhoodWatchGroup(BaseModel):
    id: Optional[int] = None
    name: str
    description: str
    area: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    radius_km: Optional[float] = 2.0
    max_members: Optional[int] = 50
    created_by: Optional[int] = None
    created_at: Optional[datetime] = None
    is_active: Optional[bool] = True

class GroupMember(BaseModel):
    id: Optional[int] = None
    group_id: int
    user_id: int
    role: Optional[str] = 'member'
    joined_at: Optional[datetime] = None
    is_active: Optional[bool] = True

class CommunityAlert(BaseModel):
    id: Optional[int] = None
    title: str
    message: str
    alert_type: Optional[str] = 'info'
    severity: Optional[str] = 'medium'
    area: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    radius_km: Optional[float] = 5.0
    created_by: Optional[int] = None
    created_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    is_active: Optional[bool] = True

class AlertSubscription(BaseModel):
    id: Optional[int] = None
    user_id: int
    alert_type: Optional[str] = 'all'
    area: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    radius_km: Optional[float] = 10.0
    is_active: Optional[bool] = True

class SafetyResource(BaseModel):
    id: Optional[int] = None
    title: str
    description: str
    resource_type: Optional[str] = 'guide'
    category: Optional[str] = None
    content: Optional[str] = None
    file_path: Optional[str] = None
    download_count: Optional[int] = 0
    created_by: Optional[int] = None
    is_public: Optional[bool] = True
    is_active: Optional[bool] = True

class SafetyConnection(BaseModel):
    id: Optional[int] = None
    requester_id: int
    target_id: int
    connection_type: Optional[str] = 'neighbor'
    status: Optional[str] = 'pending'
    requested_at: Optional[datetime] = None
    responded_at: Optional[datetime] = None
    notes: Optional[str] = None

class IncidentReport(BaseModel):
    id: Optional[int] = None
    title: str
    description: str
    incident_type: str
    severity: Optional[str] = 'medium'
    area: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    reported_by: Optional[int] = None
    assigned_group_id: Optional[int] = None
    status: Optional[str] = 'reported'
    created_at: Optional[datetime] = None
    is_anonymous: Optional[bool] = False

class PatrolRequest(BaseModel):
    id: Optional[int] = None
    requested_by: Optional[int] = None
    latitude: float
    longitude: float
    urgency: Optional[str] = 'medium'
    description: str
    status: Optional[str] = 'pending'
    assigned_to: Optional[int] = None
    created_at: Optional[datetime] = None

# Helper function to extract user_id from token
def get_current_user(token: str):
    """Extract user ID from JWT token using verify_token"""
    if not token:
        raise HTTPException(status_code=401, detail="Token required")
    
    user_id = verify_token(token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    return int(user_id)

# Router
router = APIRouter(prefix="/api/community", tags=["community"])

# Neighborhood Watch Routes
@router.get("/neighborhood-watch/groups")
def get_neighborhood_watch_groups(
    area: Optional[str] = None,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
    radius_km: Optional[float] = 5.0
):
    """Get neighborhood watch groups, optionally filtered by location"""
    conn, cursor = None, None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        query = """
            SELECT g.*, u.first_name, u.last_name,
                   COUNT(m.id) as member_count
            FROM neighborhood_watch_groups g
            LEFT JOIN users u ON g.created_by = u.id
            LEFT JOIN group_members m ON g.id = m.group_id AND m.is_active = TRUE
            WHERE g.is_active = TRUE
        """
        params = []

        if area:
            query += " AND g.area LIKE %s"
            params.append(f'%{area}%')

        if latitude and longitude and radius_km:
            query += """
                AND ST_Distance_Sphere(
                    POINT(g.longitude, g.latitude),
                    POINT(%s, %s)
                ) <= %s * 1000
            """
            params.extend([longitude, latitude, radius_km])

        query += " GROUP BY g.id ORDER BY g.created_at DESC"

        cursor.execute(query, params)
        groups = cursor.fetchall()

        return {"groups": groups}

    except Error as e:
        logger.error(f"MySQL error: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch groups")
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()

@router.post("/neighborhood-watch/groups")
def create_neighborhood_watch_group(group: NeighborhoodWatchGroup, token: Optional[str] = None):
    """Create a new neighborhood watch group"""
    user_id = get_current_user(token) if token else None

    conn, cursor = None, None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        query = """
            INSERT INTO neighborhood_watch_groups
            (name, description, area, latitude, longitude, radius_km, max_members, created_by)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """

        cursor.execute(query, (
            group.name, group.description, group.area,
            group.latitude, group.longitude, group.radius_km,
            group.max_members, user_id
        ))

        group_id = cursor.lastrowid

        # Add creator as admin member
        if user_id:
            cursor.execute("""
                INSERT INTO group_members (group_id, user_id, role)
                VALUES (%s, %s, 'admin')
            """, (group_id, user_id))

        conn.commit()

        # Log activity
        if user_id:
            cursor.execute("""
                INSERT INTO community_activity_log
                (user_id, activity_type, description, related_id)
                VALUES (%s, 'joined_group', %s, %s)
            """, (user_id, f"Created neighborhood watch group: {group.name}", group_id))

        conn.commit()

        return {"message": "Group created successfully", "group_id": group_id}

    except Error as e:
        logger.error(f"MySQL error: {e}")
        raise HTTPException(status_code=500, detail="Failed to create group")
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()

@router.post("/neighborhood-watch/groups/{group_id}/join")
def join_neighborhood_watch_group(group_id: int, token: Optional[str] = None):
    """Join a neighborhood watch group"""
    user_id = get_current_user(token) if token else None
    
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")

    conn, cursor = None, None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Check if group exists and is active
        cursor.execute("""
            SELECT id, max_members FROM neighborhood_watch_groups
            WHERE id = %s AND is_active = TRUE
        """, (group_id,))
        group = cursor.fetchone()

        if not group:
            raise HTTPException(status_code=404, detail="Group not found")

        # Check current member count
        cursor.execute("""
            SELECT COUNT(*) as member_count FROM group_members
            WHERE group_id = %s AND is_active = TRUE
        """, (group_id,))
        member_count_result = cursor.fetchone()
        # Safely convert member count to int
        try:
            member_count = int(str(member_count_result[0])) if member_count_result and member_count_result[0] is not None else 0
        except (ValueError, TypeError):
            member_count = 0

        # Safely convert max_members to int (group[1] is max_members from database)
        try:
            # Convert to string first to handle various database types, then to int
            max_members = int(str(group[1])) if group[1] is not None else 0
        except (ValueError, TypeError):
            max_members = 0
        if member_count >= max_members:
            raise HTTPException(status_code=400, detail="Group is full")

        # Check if already a member
        cursor.execute("""
            SELECT id FROM group_members
            WHERE group_id = %s AND user_id = %s
        """, (group_id, user_id))
        existing = cursor.fetchone()

        if existing:
            # Reactivate if previously left
            cursor.execute("""
                UPDATE group_members SET is_active = TRUE
                WHERE group_id = %s AND user_id = %s
            """, (group_id, user_id))
        else:
            # Add new member
            cursor.execute("""
                INSERT INTO group_members (group_id, user_id, role)
                VALUES (%s, %s, 'member')
            """, (group_id, user_id))

        # Log activity
        cursor.execute("""
            INSERT INTO community_activity_log
            (user_id, activity_type, description, related_id)
            VALUES (%s, 'joined_group', %s, %s)
        """, (user_id, f"Joined neighborhood watch group", group_id))

        conn.commit()

        return {"message": "Successfully joined group"}

    except Error as e:
        logger.error(f"MySQL error: {e}")
        raise HTTPException(status_code=500, detail="Failed to join group")
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()

# Community Alerts Routes
@router.get("/alerts")
def get_community_alerts(
    area: Optional[str] = None,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
    radius_km: Optional[float] = 10.0,
    alert_type: Optional[str] = None
):
    """Get community alerts, optionally filtered by location and type"""
    conn, cursor = None, None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        query = """
            SELECT a.*, u.first_name, u.last_name
            FROM community_alerts a
            LEFT JOIN users u ON a.created_by = u.id
            WHERE a.is_active = TRUE AND (a.expires_at IS NULL OR a.expires_at > NOW())
        """
        params = []

        if area:
            query += " AND a.area LIKE %s"
            params.append(f'%{area}%')

        if latitude and longitude and radius_km:
            query += """
                AND ST_Distance_Sphere(
                    POINT(a.longitude, a.latitude),
                    POINT(%s, %s)
                ) <= %s * 1000
            """
            params.extend([longitude, latitude, radius_km])

        if alert_type and alert_type != 'all':
            query += " AND a.alert_type = %s"
            params.append(alert_type)

        query += " ORDER BY a.created_at DESC LIMIT 50"

        cursor.execute(query, params)
        alerts = cursor.fetchall()

        return {"alerts": alerts}

    except Error as e:
        logger.error(f"MySQL error: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch alerts")
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()

@router.post("/alerts")
def create_community_alert(alert: CommunityAlert, token: Optional[str] = None):
    """Create a new community alert"""
    user_id = get_current_user(token) if token else None

    conn, cursor = None, None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        query = """
            INSERT INTO community_alerts
            (title, message, alert_type, severity, area, latitude, longitude, radius_km, created_by, expires_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """

        cursor.execute(query, (
            alert.title, alert.message, alert.alert_type, alert.severity,
            alert.area, alert.latitude, alert.longitude, alert.radius_km,
            user_id, alert.expires_at
        ))

        alert_id = cursor.lastrowid
        conn.commit()

        return {"message": "Alert created successfully", "alert_id": alert_id}

    except Error as e:
        logger.error(f"MySQL error: {e}")
        raise HTTPException(status_code=500, detail="Failed to create alert")
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()

@router.post("/alerts/subscribe")
def subscribe_to_alerts(subscription: AlertSubscription, token: Optional[str] = None):
    """Subscribe to community alerts"""
    user_id = get_current_user(token) if token else None
    
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")

    conn, cursor = None, None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Check if subscription already exists
        cursor.execute("""
            SELECT id FROM alert_subscriptions
            WHERE user_id = %s AND alert_type = %s AND area = %s
        """, (user_id, subscription.alert_type, subscription.area))

        existing = cursor.fetchone()

        if existing:
            # Update existing subscription
            subscription_id = cast(int, existing[0])
            cursor.execute("""
                UPDATE alert_subscriptions
                SET latitude = %s, longitude = %s, radius_km = %s, is_active = TRUE
                WHERE id = %s
            """, (subscription.latitude, subscription.longitude, subscription.radius_km, subscription_id))
        else:
            # Create new subscription
            cursor.execute("""
                INSERT INTO alert_subscriptions
                (user_id, alert_type, area, latitude, longitude, radius_km)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (user_id, subscription.alert_type, subscription.area,
                  subscription.latitude, subscription.longitude, subscription.radius_km))

        conn.commit()

        return {"message": "Successfully subscribed to alerts"}

    except Error as e:
        logger.error(f"MySQL error: {e}")
        raise HTTPException(status_code=500, detail="Failed to subscribe to alerts")
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()

# Safety Resources Routes
@router.get("/resources")
def get_safety_resources(
    resource_type: Optional[str] = None,
    category: Optional[str] = None,
    search: Optional[str] = None
):
    """Get safety resources, optionally filtered"""
    conn, cursor = None, None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        query = """
            SELECT r.*, u.first_name, u.last_name
            FROM safety_resources r
            LEFT JOIN users u ON r.created_by = u.id
            WHERE r.is_active = TRUE AND r.is_public = TRUE
        """
        params = []

        if resource_type:
            query += " AND r.resource_type = %s"
            params.append(resource_type)

        if category:
            query += " AND r.category LIKE %s"
            params.append(f'%{category}%')

        if search:
            query += " AND (r.title LIKE %s OR r.description LIKE %s)"
            params.extend([f'%{search}%', f'%{search}%'])

        query += " ORDER BY r.created_at DESC"

        cursor.execute(query, params)
        resources = cursor.fetchall()

        return {"resources": resources}

    except Error as e:
        logger.error(f"MySQL error: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch resources")
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()

@router.post("/resources/{resource_id}/download")
def download_safety_resource(resource_id: int):
    """Increment download count for a resource"""
    conn, cursor = None, None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE safety_resources
            SET download_count = download_count + 1
            WHERE id = %s AND is_active = TRUE
        """, (resource_id,))

        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Resource not found")

        conn.commit()

        return {"message": "Download recorded"}

    except Error as e:
        logger.error(f"MySQL error: {e}")
        raise HTTPException(status_code=500, detail="Failed to record download")
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()

# Safety Network Routes
@router.get("/network/connections")
def get_safety_connections(token: Optional[str] = None):
    """Get user's safety network connections"""
    user_id = get_current_user(token) if token else None
    
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")

    conn, cursor = None, None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Get connections where user is requester or target
        cursor.execute("""
            SELECT c.*,
                   u1.first_name as requester_first_name, u1.last_name as requester_last_name,
                   u2.first_name as target_first_name, u2.last_name as target_last_name
            FROM safety_network_connections c
            LEFT JOIN users u1 ON c.requester_id = u1.id
            LEFT JOIN users u2 ON c.target_id = u2.id
            WHERE (c.requester_id = %s OR c.target_id = %s) AND c.status != 'blocked'
            ORDER BY c.requested_at DESC
        """, (user_id, user_id))

        connections = cursor.fetchall()

        return {"connections": connections}

    except Error as e:
        logger.error(f"MySQL error: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch connections")
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()

@router.post("/network/connect")
def request_safety_connection(connection: SafetyConnection, token: Optional[str] = None):
    """Request a safety network connection"""
    user_id = get_current_user(token) if token else None
    
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")

    if connection.target_id == user_id:
        raise HTTPException(status_code=400, detail="Cannot connect to yourself")

    conn, cursor = None, None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Check if connection already exists
        cursor.execute("""
            SELECT id, status FROM safety_network_connections
            WHERE (requester_id = %s AND target_id = %s) OR (requester_id = %s AND target_id = %s)
        """, (user_id, connection.target_id, connection.target_id, user_id))

        existing = cursor.fetchone()

        if existing:
            if existing[1] == 'accepted':
                raise HTTPException(status_code=400, detail="Connection already exists")
            elif existing[1] == 'pending':
                raise HTTPException(status_code=400, detail="Connection request already pending")

        # Create new connection request
        cursor.execute("""
            INSERT INTO safety_network_connections
            (requester_id, target_id, connection_type, notes)
            VALUES (%s, %s, %s, %s)
        """, (user_id, connection.target_id, connection.connection_type, connection.notes))

        conn.commit()

        return {"message": "Connection request sent"}

    except Error as e:
        logger.error(f"MySQL error: {e}")
        raise HTTPException(status_code=500, detail="Failed to send connection request")
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()

# Incident Reports Routes
@router.post("/incidents")
def report_incident(incident: IncidentReport, token: Optional[str] = None):
    """Report a community incident"""
    user_id = get_current_user(token) if token and not incident.is_anonymous else None

    conn, cursor = None, None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        query = """
            INSERT INTO community_incident_reports
            (title, description, incident_type, severity, area, latitude, longitude, reported_by, is_anonymous)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """

        cursor.execute(query, (
            incident.title, incident.description, incident.incident_type,
            incident.severity, incident.area, incident.latitude, incident.longitude,
            user_id, incident.is_anonymous
        ))

        incident_id = cursor.lastrowid
        conn.commit()

        # Log activity if not anonymous
        if user_id:
            cursor.execute("""
                INSERT INTO community_activity_log
                (user_id, activity_type, description, related_id)
                VALUES (%s, 'reported_incident', %s, %s)
            """, (user_id, f"Reported incident: {incident.title}", incident_id))

        conn.commit()

        return {"message": "Incident reported successfully", "incident_id": incident_id}

    except Error as e:
        logger.error(f"MySQL error: {e}")
        raise HTTPException(status_code=500, detail="Failed to report incident")
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()

# Patrol Request Routes
@router.get("/patrol-requests")
def get_patrol_requests(token: Optional[str] = None):
    """Get user's patrol requests"""
    user_id = get_current_user(token) if token else None

    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")

    conn, cursor = None, None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT id, latitude, longitude, urgency, description, status, assigned_to, created_at
            FROM patrol_requests
            WHERE requested_by = %s
            ORDER BY created_at DESC
        """, (user_id,))

        requests = cursor.fetchall()

        return {"patrol_requests": requests}

    except Error as e:
        logger.error(f"MySQL error: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch patrol requests")
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()

@router.post("/patrol-request")
def request_patrol(patrol: PatrolRequest, token: Optional[str] = None):
    """Request patrol assistance"""
    user_id = get_current_user(token) if token else None

    conn, cursor = None, None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        query = """
            INSERT INTO patrol_requests
            (requested_by, latitude, longitude, urgency, description)
            VALUES (%s, %s, %s, %s, %s)
        """

        cursor.execute(query, (
            user_id, patrol.latitude, patrol.longitude,
            patrol.urgency, patrol.description
        ))

        request_id = cursor.lastrowid
        conn.commit()

        # Log activity
        if user_id:
            cursor.execute("""
                INSERT INTO community_activity_log
                (user_id, activity_type, description, related_id)
                VALUES (%s, 'requested_patrol', %s, %s)
            """, (user_id, f"Requested patrol assistance", request_id))

        conn.commit()

        return {"message": "Patrol request submitted successfully", "request_id": request_id}

    except Error as e:
        logger.error(f"MySQL error: {e}")
        raise HTTPException(status_code=500, detail="Failed to submit patrol request")
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()

# User Status Routes
@router.get("/user/status")
def get_user_community_status(token: Optional[str] = None):
    """Get user's community participation status"""
    user_id = get_current_user(token) if token else None
    
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")

    conn, cursor = None, None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        status = {}

        # Check if user is in any groups
        cursor.execute("""
            SELECT COUNT(*) as group_count FROM group_members
            WHERE user_id = %s AND is_active = TRUE
        """, (user_id,))
        result = cast(Optional[Dict[str, Any]], cursor.fetchone())
        status['groups_joined'] = result['group_count'] if result else 0

        # Check alert subscriptions
        cursor.execute("""
            SELECT COUNT(*) as subscription_count FROM alert_subscriptions
            WHERE user_id = %s AND is_active = TRUE
        """, (user_id,))
        result = cast(Optional[Dict[str, Any]], cursor.fetchone())
        status['alert_subscriptions'] = result['subscription_count'] if result else 0

        # Check network connections
        cursor.execute("""
            SELECT COUNT(*) as connection_count FROM safety_network_connections
            WHERE (requester_id = %s OR target_id = %s) AND status = 'accepted'
        """, (user_id, user_id))
        result = cast(Optional[Dict[str, Any]], cursor.fetchone())
        status['network_connections'] = result['connection_count'] if result else 0

        # Check resources downloaded
        cursor.execute("""
            SELECT COUNT(*) as downloads FROM resource_downloads
            WHERE user_id = %s
        """, (user_id,))
        result = cast(Optional[Dict[str, Any]], cursor.fetchone())
        status['resources_downloaded'] = result['downloads'] if result else 0

        return {"status": status}

    except Error as e:
        logger.error(f"MySQL error: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch user status")
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()

@router.get("/user/alert-status")
def get_user_alert_status(token: Optional[str] = None):
    """Get user's alert subscription status"""
    user_id = get_current_user(token) if token else None
    
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")

    conn, cursor = None, None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT id, alert_type, area, latitude, longitude, radius_km, created_at
            FROM alert_subscriptions
            WHERE user_id = %s AND is_active = TRUE
            ORDER BY created_at DESC
        """, (user_id,))

        subscriptions = cursor.fetchall()
        return {"status": {"subscriptions": subscriptions}}

    except Error as e:
        logger.error(f"MySQL error: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch alert status")
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()

@router.get("/user/resource-status")
def get_user_resource_status(token: Optional[str] = None):
    """Get user's resource interaction status"""
    user_id = get_current_user(token) if token else None
    
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")

    conn, cursor = None, None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Get downloaded resources
        cursor.execute("""
            SELECT r.title, rd.downloaded_at
            FROM resource_downloads rd
            JOIN safety_resources r ON rd.resource_id = r.id
            WHERE rd.user_id = %s
            ORDER BY rd.downloaded_at DESC
            LIMIT 10
        """, (user_id,))

        downloads = cursor.fetchall()
        return {"status": {"downloads": downloads}}

    except Error as e:
        logger.error(f"MySQL error: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch resource status")
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()

@router.get("/user/network-status")
def get_user_network_status(token: Optional[str] = None):
    """Get user's network connection status"""
    user_id = get_current_user(token) if token else None
    
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")

    conn, cursor = None, None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT c.id, c.connection_type, c.status, c.requested_at,
                   CASE
                       WHEN c.requester_id = %s THEN CONCAT(u2.first_name, ' ', u2.last_name)
                       ELSE CONCAT(u1.first_name, ' ', u1.last_name)
                   END as connected_user
            FROM safety_network_connections c
            LEFT JOIN users u1 ON c.requester_id = u1.id
            LEFT JOIN users u2 ON c.target_id = u2.id
            WHERE (c.requester_id = %s OR c.target_id = %s) AND c.status = 'accepted'
            ORDER BY c.requested_at DESC
        """, (user_id, user_id, user_id))

        connections = cursor.fetchall()
        return {"status": {"connections": connections}}

    except Error as e:
        logger.error(f"MySQL error: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch network status")
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()

# Action Routes
@router.delete("/alerts/unsubscribe/{subscription_id}")
def unsubscribe_from_alerts(subscription_id: int, token: Optional[str] = None):
    """Unsubscribe from alerts"""
    user_id = get_current_user(token) if token else None
    
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")

    conn, cursor = None, None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Verify subscription belongs to user
        cursor.execute("""
            SELECT id FROM alert_subscriptions
            WHERE id = %s AND user_id = %s AND is_active = TRUE
        """, (subscription_id, user_id))

        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Subscription not found")

        # Deactivate subscription
        cursor.execute("""
            UPDATE alert_subscriptions
            SET is_active = FALSE
            WHERE id = %s
        """, (subscription_id,))

        conn.commit()
        return {"message": "Successfully unsubscribed from alerts"}

    except Error as e:
        logger.error(f"MySQL error: {e}")
        raise HTTPException(status_code=500, detail="Failed to unsubscribe from alerts")
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()

@router.delete("/network/disconnect/{connection_id}")
def disconnect_from_network(connection_id: int, token: Optional[str] = None):
    """Disconnect from safety network"""
    user_id = get_current_user(token) if token else None
    
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")

    conn, cursor = None, None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Verify connection belongs to user
        cursor.execute("""
            SELECT id FROM safety_network_connections
            WHERE id = %s AND (requester_id = %s OR target_id = %s) AND status = 'accepted'
        """, (connection_id, user_id, user_id))

        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Connection not found")

        # Remove connection
        cursor.execute("""
            DELETE FROM safety_network_connections
            WHERE id = %s
        """, (connection_id,))

        conn.commit()
        return {"message": "Successfully disconnected from network"}

    except Error as e:
        logger.error(f"MySQL error: {e}")
        raise HTTPException(status_code=500, detail="Failed to disconnect from network")
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()

@router.delete("/neighborhood-watch/groups/{group_id}/leave")
def leave_community_group(group_id: int, token: Optional[str] = None):
    """Leave a neighborhood watch group"""
    user_id = get_current_user(token) if token else None
    
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")

    conn, cursor = None, None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Check if user is a member of the group
        cursor.execute("""
            SELECT id, role FROM group_members
            WHERE group_id = %s AND user_id = %s AND is_active = TRUE
        """, (group_id, user_id))

        membership = cursor.fetchone()
        if not membership:
            raise HTTPException(status_code=404, detail="Not a member of this group")

        # If user is admin, check if there are other admins
        if membership[1] == 'admin':
            cursor.execute("""
                SELECT COUNT(*) as admin_count FROM group_members
                WHERE group_id = %s AND role = 'admin' AND is_active = TRUE
            """, (group_id,))
            result = cast(Optional[tuple], cursor.fetchone())
            admin_count: int = result[0] if result else 0

            if admin_count <= 1:
                raise HTTPException(status_code=400, detail="Cannot leave group as the last admin")

        # Remove membership
        cursor.execute("""
            UPDATE group_members
            SET is_active = FALSE
            WHERE group_id = %s AND user_id = %s
        """, (group_id, user_id))

        # Log activity
        cursor.execute("""
            INSERT INTO community_activity_log
            (user_id, activity_type, description, related_id)
            VALUES (%s, 'left_group', %s, %s)
        """, (user_id, f"Left neighborhood watch group", group_id))

        conn.commit()
        return {"message": "Successfully left the group"}

    except Error as e:
        logger.error(f"MySQL error: {e}")
        raise HTTPException(status_code=500, detail="Failed to leave group")
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()

# Community Activity Log Routes
@router.get("/activity-log")
def get_community_activity_log(
    activity_type: Optional[str] = None,
    area: Optional[str] = None,
    limit: int = 50
):
    """Get community activity log with optional filters"""
    conn, cursor = None, None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        query = """
            SELECT a.*, u.first_name, u.last_name
            FROM community_activity_log a
            LEFT JOIN users u ON a.user_id = u.id
        """
        params = []

        if activity_type:
            query += " WHERE a.activity_type = %s"
            params.append(activity_type)

        if area:
            if activity_type:
                query += " AND a.area LIKE %s"
            else:
                query += " WHERE a.area LIKE %s"
            params.append(f'%{area}%')

        query += " ORDER BY a.created_at DESC LIMIT %s"
        params.append(limit)

        cursor.execute(query, params)
        activities = cursor.fetchall()

        return {"activities": activities}

    except Error as e:
        logger.error(f"MySQL error: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch activity log")
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()

# Community Stats Route
@router.get("/stats")
def get_community_stats():
    """Get community statistics"""
    conn, cursor = None, None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        stats = {}

        # Total members across all groups
        cursor.execute("""
            SELECT COUNT(DISTINCT user_id) as total_members
            FROM group_members WHERE is_active = TRUE
        """)
        result = cast(Optional[Dict[str, Any]], cursor.fetchone())
        stats['total_members'] = result['total_members'] if result else 0

        # Active today - users who have performed activities in the last 24 hours
        cursor.execute("""
            SELECT COUNT(DISTINCT user_id) as active_today
            FROM community_activity_log
            WHERE created_at >= DATE_SUB(NOW(), INTERVAL 1 DAY)
        """)
        result = cast(Optional[Dict[str, Any]], cursor.fetchone())
        stats['active_today'] = result['active_today'] if result else 0

        # Weekly alerts
        cursor.execute("""
            SELECT COUNT(*) as alerts_this_week
            FROM community_alerts
            WHERE created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY) AND is_active = TRUE
        """)
        result = cast(Optional[Dict[str, Any]], cursor.fetchone())
        stats['alerts_this_week'] = result['alerts_this_week'] if result else 0

        # Available resources
        cursor.execute("""
            SELECT COUNT(*) as resources_available
            FROM safety_resources WHERE is_active = TRUE AND is_public = TRUE
        """)
        result = cast(Optional[Dict[str, Any]], cursor.fetchone())
        stats['resources_available'] = result['resources_available'] if result else 0

        # Total connections
        cursor.execute("""
            SELECT COUNT(*) as connections_made
            FROM safety_network_connections WHERE status = 'accepted'
        """)
        result = cast(Optional[Dict[str, Any]], cursor.fetchone())
        stats['connections_made'] = result['connections_made'] if result else 0

        # Recent incidents (last 30 days)
        cursor.execute("""
            SELECT COUNT(*) as incidents_reported
            FROM community_incident_reports
            WHERE created_at >= DATE_SUB(NOW(), INTERVAL 30 DAY)
        """)
        result = cast(Optional[Dict[str, Any]], cursor.fetchone())
        stats['incidents_reported'] = result['incidents_reported'] if result else 0

        return {"stats": stats}

    except Error as e:
        logger.error(f"MySQL error: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch community stats")
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()

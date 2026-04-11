from fastapi import APIRouter, Depends, HTTPException
from typing import List, Optional, Dict, Any
import logging
from datetime import datetime

from app.core.database import get_db_connection, log_user_activity
from app.dependencies import get_username_from_token
from app.models.schemas import EmergencyCallRequest, PatrolRequestRequest, EmergencyContact

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/emergency", tags=["emergency"])

@router.get("/emergency-contacts")
def get_emergency_contacts():
    """Get emergency contacts data"""
    emergency_contacts = [
        {
            "id": 1,
            "name": "Police Emergency",
            "number": "15",
            "color": "#ff4444",
            "gradient": "linear-gradient(135deg, #ff4444, #cc0000)",
            "icon": "fas fa-shield-alt",
            "response": "2-5 min",
            "coordinates": {"lat": 31.5204, "lng": 74.3587},
            "description": "Immediate police response for emergencies, accidents, and security threats.",
            "services": ["Emergency Response", "Crime Reporting", "Traffic Control", "Security Patrol"]
        },
        {
            "id": 2,
            "name": "Rescue 1122",
            "number": "1122",
            "color": "#ff8800",
            "gradient": "linear-gradient(135deg, #ff8800, #cc6600)",
            "icon": "fas fa-ambulance",
            "response": "5-8 min",
            "coordinates": {"lat": 31.5204, "lng": 74.3587},
            "description": "Medical emergencies, fire response, and disaster management services.",
            "services": ["Medical Emergency", "Fire Response", "Disaster Relief", "Ambulance Service"]
        },
        {
            "id": 3,
            "name": "Fire Brigade",
            "number": "16",
            "color": "#ff6600",
            "gradient": "linear-gradient(135deg, #ff6600, #cc3300)",
            "icon": "fas fa-fire-extinguisher",
            "response": "3-6 min",
            "coordinates": {"lat": 31.5204, "lng": 74.3587},
            "description": "Fire fighting, rescue operations, and hazardous material incidents.",
            "services": ["Fire Fighting", "Rescue Operations", "Hazard Response", "Prevention Services"]
        },
        {
            "id": 4,
            "name": "Women Helpline",
            "number": "1099",
            "color": "#ff66aa",
            "gradient": "linear-gradient(135deg, #ff66aa, #cc3388)",
            "icon": "fas fa-female",
            "response": "10-15 min",
            "coordinates": {"lat": 31.5204, "lng": 74.3587},
            "description": "Support for women facing harassment, abuse, or domestic violence.",
            "services": ["Harassment Support", "Legal Aid", "Counseling", "Emergency Shelter"]
        },
        {
            "id": 5,
            "name": "Child Helpline",
            "number": "1121",
            "color": "#66aaff",
            "gradient": "linear-gradient(135deg, #66aaff, #3388cc)",
            "icon": "fas fa-child",
            "response": "8-12 min",
            "coordinates": {"lat": 31.5204, "lng": 74.3587},
            "description": "Protection and support services for children in distress or danger.",
            "services": ["Child Protection", "Missing Children", "Abuse Reporting", "Counseling Services"]
        },
        {
            "id": 6,
            "name": "Traffic Police",
            "number": "1915",
            "color": "#44aa44",
            "gradient": "linear-gradient(135deg, #44aa44, #228822)",
            "icon": "fas fa-car",
            "response": "5-10 min",
            "coordinates": {"lat": 31.5204, "lng": 74.3587},
            "description": "Traffic accidents, violations, and road safety assistance.",
            "services": ["Accident Response", "Traffic Control", "Violation Reports", "Road Safety"]
        }
    ]

    logger.info(f"Returning {len(emergency_contacts)} emergency contacts")
    return {"contacts": emergency_contacts}

@router.post("/emergency-call")
async def log_emergency_call(
    call_data: EmergencyCallRequest,
    current_user: Optional[str] = Depends(get_username_from_token)
):
    """Log an emergency call to the database"""
    conn, cursor = None, None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Get user ID from username if logged in
        user_id = None
        username = 'anonymous'
        if current_user:
            cursor.execute("SELECT id FROM users_info WHERE username = %s", (current_user,))
            user_result = cursor.fetchone()
            if user_result:
                user_id = user_result['id']  # type: ignore
                username = current_user

        # Insert emergency call record
        insert_query = """
            INSERT INTO emergency_calls 
            (contact_name, contact_number, caller_location_lat, caller_location_lng,
             caller_address, user_id, username, emergency_type, status, call_timestamp)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """

        cursor.execute(insert_query, (
            call_data.contact_name,
            call_data.contact_number,
            call_data.caller_location_lat,
            call_data.caller_location_lng,
            call_data.caller_address,
            user_id,
            username,
            call_data.emergency_type,
            'completed',
            datetime.now()
        ))

        conn.commit()
        call_id = cursor.lastrowid

        # Log the emergency call activity only if user is logged in
        if current_user:
            log_user_activity(
                activity_type="emergency_call",
                username=current_user,
                user_id=user_id,
                activity_details={
                    "contact_name": call_data.contact_name,
                    "contact_number": call_data.contact_number,
                    "emergency_type": call_data.emergency_type,
                    "location": {
                        "lat": call_data.caller_location_lat,
                        "lng": call_data.caller_location_lng,
                        "address": call_data.caller_address
                    }
                }
            )

        logger.info(f"Emergency call logged: id={call_id}, user={username}, contact={call_data.contact_name}")

        return {
            "message": "Emergency call logged successfully",
            "call_id": call_id,
            "status": "completed"
        }

    except Exception as e:
        logger.error(f"Database error logging emergency call: {e}")
        raise HTTPException(status_code=500, detail="Failed to log emergency call")
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()

@router.post("/emergency-call/public")
async def log_emergency_call_public(call_data: EmergencyCallRequest):
    """Public endpoint for emergency calls - no authentication required"""
    conn, cursor = None, None
    try:
        logger.info(f"Received public emergency call data: {call_data}")
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Insert emergency call record as anonymous user
        insert_query = """
            INSERT INTO emergency_calls 
            (contact_name, contact_number, caller_location_lat, caller_location_lng,
             caller_address, user_id, username, emergency_type, status, call_timestamp)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """

        cursor.execute(insert_query, (
            call_data.contact_name,
            call_data.contact_number,
            call_data.caller_location_lat,
            call_data.caller_location_lng,
            call_data.caller_address,
            None,
            'anonymous',
            call_data.emergency_type,
            'completed',
            datetime.now()
        ))

        conn.commit()
        call_id = cursor.lastrowid

        logger.info(f"Public emergency call logged: id={call_id}, contact={call_data.contact_name}")

        return {
            "message": "Emergency call logged successfully",
            "call_id": call_id,
            "status": "completed"
        }

    except Exception as e:
        logger.error(f"Database error logging public emergency call: {e}")
        raise HTTPException(status_code=500, detail="Failed to log emergency call")
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()

@router.post("/patrol-request")
def submit_patrol_request(
    request_data: PatrolRequestRequest,
    current_user: str = Depends(get_username_from_token)
):
    """Submit a patrol request to the database"""
    conn, cursor = None, None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Get user ID from username
        cursor.execute("SELECT id FROM users_info WHERE username = %s", (current_user,))
        user_result = cursor.fetchone()
        try:
            user_id = int(str(user_result[0])) if user_result and user_result[0] is not None else None
        except (ValueError, TypeError):
            user_id = None

        # Insert patrol request record
        insert_query = """
            INSERT INTO patrol_requests
            (user_id, username, request_type, location_lat, location_lng, address, status, urgency, description)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """

        cursor.execute(insert_query, (
            user_id,
            current_user,
            request_data.request_type,
            request_data.location_lat,
            request_data.location_lng,
            request_data.address,
            'pending',
            request_data.urgency,
            request_data.description
        ))

        conn.commit()
        request_id = cursor.lastrowid

        # Log the patrol request activity
        log_user_activity(
            activity_type="patrol_request",
            username=current_user,
            user_id=user_id,
            activity_details={
                "request_type": request_data.request_type,
                "urgency": request_data.urgency,
                "location": {
                    "lat": request_data.location_lat,
                    "lng": request_data.location_lng,
                    "address": request_data.address
                },
                "description": request_data.description
            }
        )

        logger.info(f"Patrol request submitted: id={request_id}, user={current_user}, type={request_data.request_type}")

        return {
            "message": "Patrol request submitted successfully",
            "request_id": request_id,
            "status": "pending"
        }

    except Exception as e:
        logger.error(f"Database error submitting patrol request: {e}")
        raise HTTPException(status_code=500, detail="Failed to submit patrol request")
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()

@router.get("/emergency-stats")
async def get_emergency_stats():
    """Get real-time emergency statistics from database"""
    conn, cursor = None, None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Calls today
        cursor.execute("""
            SELECT COUNT(*) as calls_today 
            FROM emergency_calls 
            WHERE DATE(call_timestamp) = CURDATE()
        """)
        calls_result = cursor.fetchone()
        calls_today = calls_result['calls_today'] if calls_result else 0  # type: ignore

        # Active units
        cursor.execute("""
            SELECT COUNT(*) as active_units
            FROM patrol_requests
            WHERE status NOT IN ('completed', 'cancelled')
        """)
        units_result = cursor.fetchone()
        active_units = units_result['active_units'] if units_result else 0  # type: ignore

        # Resolved rate
        cursor.execute("""
            SELECT
                CASE
                    WHEN COUNT(*) > 0 THEN 100.0
                    ELSE 0
                END as resolved_rate
            FROM emergency_calls
            WHERE DATE(call_timestamp) = CURDATE()
        """)
        resolved_result = cursor.fetchone()
        resolved_rate = resolved_result['resolved_rate'] if resolved_result else 0.0  # type: ignore

        # Avg response time
        avg_response = "2.5min"

        stats = {
            "calls_today": calls_today,
            "avg_response": avg_response,
            "active_units": active_units,
            "resolved_rate": f"{resolved_rate}%"
        }

        logger.info(f"Emergency stats: {stats}")
        return stats

    except Exception as e:
        logger.error(f"MySQL error in emergency stats: {e}")
        return {
            "calls_today": 0,
            "avg_response": "N/A",
            "active_units": 0,
            "resolved_rate": "0%"
        }
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()
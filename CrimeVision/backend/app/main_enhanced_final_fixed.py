from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union, cast
from fastapi import FastAPI, Query, HTTPException, Depends, Request, BackgroundTasks
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
import os
import sys
from app.alert_notifications import AlertNotificationSystem
from app.routes import test_alerts
from app.alert_tester import AlertTester
# Ensure parent (backend) directory is on sys.path so absolute imports like
# `from app.core...` work even when running uvicorn from inside the `app` folder.
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from pydantic import BaseModel, Field
import secrets
import string
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from app.core.database import ensure_alerts_tables_schema, ensure_alert_subscriptions_table, ensure_browser_notifications_tables

if TYPE_CHECKING:
    from fastapi import BackgroundTasks



# Add these imports at the top
import asyncio
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
import threading
import requests
import difflib
import json
import joblib
import numpy as np
import os
import pandas as pd
import sys
import uvicorn
from datetime import datetime, timedelta

from fastapi.middleware.cors import CORSMiddleware

from mysql.connector import Error

# Add the backend directory to Python path for absolute imports
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from app.auth_updated import create_access_token, get_password_hash, verify_password, verify_token, create_refresh_token, verify_refresh_token
from app.core.database import get_db_connection, initialize_schema, log_user_activity
from app.auth_routes import router as auth_router

from app.core.config import ALLOWED_ORIGINS, MODEL_DIR, get_api_title, get_logger
from app.models.types import CrimeRow, CrimeTypeRow
from app.utils.geo import get_coordinates
from app.utils.validation import (
    generate_username,
    validate_crime_type,
    validate_date_format,
    validate_name,
)

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

# Add this global variable for cooldown tracking (put it with your other configs)
alert_cooldown_cache: Dict[str, datetime] = {}

# # Import community routes
# from app.community_routes import router as community_router
security = HTTPBearer()
app = FastAPI(title="SafeVision API")
app.add_middleware(
    CORSMiddleware,
    # Read from ALLOWED_ORIGINS env var (comma-separated). Defaults to local
    # dev origins. Production: set ALLOWED_ORIGINS to your Vercel URL.
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=3600,
)
app.include_router(test_alerts.test_router)

class AlertSubscription(BaseModel):
    user_id: int
    alert_types: List[str] = ["crime", "safety", "emergency"]
    areas: List[str] = []
    radius: float = 5.0  # in km
    notification_types: List[str] = ["email", "browser"]
    is_active: bool = True
    monitor_live_location: bool = False
    monitor_saved_locations: bool = True

# In your main.py, update the UserProfileUpdate model
class UserProfileUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    profile_picture: Optional[str] = None
    home_area: Optional[str] = None
    work_area: Optional[str] = None
    alert_radius: Optional[int] = Field(None, ge=1, le=50)
    phone_number: Optional[str] = None 
    browser_notifications_enabled: Optional[bool] = None

class LocationAlertRequest(BaseModel):
    latitude: float
    longitude: float
    address: Optional[str] = None
    check_immediate: bool = True

class RiskZoneAlert(BaseModel):
    user_id: int
    username: str
    email: str
    phone: Optional[str] = None
    latitude: float
    longitude: float
    address: str
    risk_level: str
    safety_score: float
    high_risk_crimes: int
    alert_type: str = "high_risk_zone"
    precautions: Optional[str] = None
    message: str

# Add background task scheduler
scheduler = BackgroundScheduler()
scheduler.start()



# Email configuration for alerts
ALERT_EMAIL_CONFIG = {
    'smtp_server': os.getenv('SMTP_SERVER', 'smtp.gmail.com'),
    'smtp_port': int(os.getenv('SMTP_PORT', 587)),
    'smtp_username': os.getenv('SMTP_USERNAME', 'safevision.alerts@gmail.com'),
    'smtp_password': os.getenv('SMTP_PASSWORD', '')
}

# In your main.py or config.py

SAFE_AREA_ALERT_CONFIG = {
    'min_safety_score': int(os.getenv('SAFE_AREA_MIN_SCORE', '70')),
    'send_safe_alerts': os.getenv('SEND_SAFE_ALERTS', 'True').lower() == 'true',
    'cooldown_minutes': int(os.getenv('SAFE_ALERT_COOLDOWN', '60')),  # 60 minutes for safe areas
}
alert_notification_system = AlertNotificationSystem(ALERT_EMAIL_CONFIG)
# Alert System Core Functions


# New API Endpoints

# Import or define missing models for FastAPI endpoints

# Fallback: define minimal stubs if not available
class Token(BaseModel):
    access_token: str
    token_type: str
    username: Optional[str] = None
    message: Optional[str] = None

class UserRegister(BaseModel):
    first_name: str
    last_name: str
    email: str
    password: str
    home_area: Optional[str] = None

class AlertCreate(BaseModel):
    title: str
    message: str
    alert_type: str = "info"  # info, warning, danger
    area: Optional[str] = None
    severity: str = "medium"  # low, medium, high, critical
    expires_at: Optional[str] = None

class UserAlertResponse(BaseModel):
    id: int
    title: str
    message: str
    alert_type: str
    area: Optional[str]
    severity: str
    is_read: bool
    created_at: str
    expires_at: Optional[str]
    priority: int  # Calculated field for sorting
class UserLogin(BaseModel):
    email: str
    password: str
    two_factor_code: Optional[str] = None

class RegistrationResponse(BaseModel):
    message: str

class LocationResponse(BaseModel):
    area: str
    latitude: float
    longitude: float
    source: str

class LocationRequest(BaseModel):
    area: str

class UserLocationUpdate(BaseModel):
    home_area: Optional[str] = None
    work_area: Optional[str] = None
    alert_radius: Optional[int] = None

class EmergencyCallRequest(BaseModel):
    contact_name: str
    contact_number: str
    caller_location_lat: Optional[float] = None
    caller_location_lng: Optional[float] = None
    caller_address: Optional[str] = None
    emergency_type: str = "general"

class PatrolRequestRequest(BaseModel):
    request_type: str = "general_patrol"
    location_lat: float
    location_lng: float
    address: str
    urgency: str = "medium"
    description: Optional[str] = None

class EmergencyContact(BaseModel):
    id: int
    name: str
    number: str
    color: str
    gradient: str
    icon: str
    response: str
    coordinates: Dict[str, float]
    description: str
    services: List[str]


class ResendVerificationRequest(BaseModel):
    email: str

class Crime(BaseModel):
    id: int
    area: str
    type: str
    date: str
    coordinates: List[float]
    risk_level: str

class PredictRiskRequest(BaseModel):
    area: str
    crime_type: str
    date: Optional[str] = None

class CrimeCreate(BaseModel):
    area: str
    crime_type: str
    date: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None



# Import 2FA functions
from app.two_factor import (
    is_2fa_enabled,
    get_user_2fa_secret,
    verify_2fa_code,
    generate_2fa_secret as generate_2fa_secret_util,
    get_2fa_uri,
    enable_2fa,
    disable_2fa,
)

# Import email functions
from app.email_verification import send_verification_email

sys.path.append(os.path.join(os.path.dirname(__file__), 'crime_risk_model'))
# Import crime risk model utilities - these will be available when running from backend directory
try:
    from crime_risk_model.utils.helpers import engineer_features, load_model
except ImportError:
    # Fallback for when running directly
    sys.path.append(os.path.dirname(__file__))
    from crime_risk_model.utils.helpers import engineer_features, load_model

logger = get_logger(__name__)

# Email configuration is loaded from env vars (SMTP_SERVER, SMTP_PORT,
# SMTP_USERNAME, SMTP_PASSWORD). See .env.example for the full list.


# Load ML model and encoders
try:
    model = joblib.load(os.path.join(MODEL_DIR, 'random_forest_model.joblib'))
    le_area = joblib.load(os.path.join(MODEL_DIR, 'label_encoder_area.joblib'))
    le_crime = joblib.load(os.path.join(MODEL_DIR, 'label_encoder_crime.joblib'))
    le_risk = joblib.load(os.path.join(MODEL_DIR, 'label_encoder_risk.joblib'))
except Exception as e:
    logger.error(f"Error loading ML model or encoders: {e}")
    model = None
    le_area = None
    le_crime = None
    le_risk = None

# -------------------------------
# FastAPI app + endpoint
# -------------------------------

app.include_router(auth_router)
# app.include_router(community_router)

# Import password reset functions and models
from app.password_reset_fixed import forgot_password, reset_password, ForgotPasswordRequest, ResetPasswordRequest

# In your main.py, add better error handling for database connections


# Mount static files for profile photos
app.mount("/profile_photos", StaticFiles(directory=os.path.join(os.path.dirname(__file__), "profile_photos")), name="profile_photos")


@app.get("/")
def root(request: Request):
    logger.info(f"Request received: {request.method} {request.url.path}")
    return {"message": "Welcome to CrimeVision API. Go to /api/crimes"}

@app.get("/welcome")
def welcome(request: Request):
    logger.info(f"Request received: {request.method} {request.url.path}")
    return {"message": "Welcome to the CrimeVision API Service!"}

# Add password reset endpoints
@app.post("/auth/forgot-password")
async def api_forgot_password(request: ForgotPasswordRequest, background_tasks: BackgroundTasks):
    return await forgot_password(request, background_tasks)

@app.post("/auth/reset-password")
async def api_reset_password(request: ResetPasswordRequest, background_tasks: BackgroundTasks):
    return await reset_password(request, background_tasks)

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
        return {"database": "error", "message": str(e)}

# Authentication endpoints
@app.post("/auth/register", response_model=RegistrationResponse)
def register(user: UserRegister, background_tasks: BackgroundTasks):
    """Register a new user with email verification"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Validate names
        first_name = validate_name(user.first_name)
        last_name = validate_name(user.last_name)

        # Generate username from first and last name
        username = generate_username(first_name, last_name)

        # Check if email already exists
        cursor.execute("SELECT id FROM users_info WHERE email = %s", (user.email,))
        if cursor.fetchone():
            raise HTTPException(status_code=400, detail="Email already exists")

        # Hash password
        password_hash = get_password_hash(user.password)

        # Get coordinates for home area if provided - WITH BETTER ERROR HANDLING
        home_lat, home_lon = None, None
        if user.home_area:
            try:
                logger.info(f"🔍 Fetching coordinates for home area: {user.home_area}")
                coords = get_coordinates(user.home_area)
                if coords:
                    home_lat, home_lon = coords
                    logger.info(f"✅ Coordinates found: {home_lat}, {home_lon}")
                else:
                    logger.warning(f"❌ No coordinates found for area: {user.home_area}")
            except Exception as e:
                logger.error(f"❌ Error fetching coordinates for {user.home_area}: {e}")
                # Don't fail registration if coordinates fail, just log it

        # Generate email verification token
        verification_token = secrets.token_urlsafe(32)
        token_expires_at = datetime.utcnow() + timedelta(hours=24)

        # Create user with is_verified = false
        cursor.execute(
            "INSERT INTO users_info (username, first_name, last_name, email, password_hash, home_area, home_latitude, home_longitude, activity_logs, is_verified, email_verification_token, token_expires_at) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
            (username, first_name, last_name, user.email, password_hash, user.home_area, home_lat, home_lon, json.dumps([]), False, verification_token, token_expires_at)
        )
        conn.commit()

        # Send verification email in background
        background_tasks.add_task(send_verification_email, user.email, first_name, verification_token)

        return {
            "message": f"User registered successfully. Please check your email to verify your account. Your username is: {username}"
        }

    except Error as e:
        logger.error(f"Database error during registration: {e}")
        raise HTTPException(status_code=500, detail="Database error")
    finally:
        cursor.close()
        conn.close()

@app.post("/auth/resend-verification")
def resend_verification(request: ResendVerificationRequest, background_tasks: BackgroundTasks):
    """Resend email verification link for a user who hasn't verified yet."""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT id, first_name, is_verified FROM users_info WHERE email = %s", (request.email,))
        user = cursor.fetchone()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        if cast(Dict[str, Any], user).get("is_verified"):
            raise HTTPException(status_code=400, detail="User is already verified")

        # Generate new verification token and expiry
        new_token = secrets.token_urlsafe(32)
        new_expires = datetime.utcnow() + timedelta(hours=24)

        cursor.execute(
            "UPDATE users_info SET email_verification_token = %s, token_expires_at = %s WHERE id = %s",
            (new_token, new_expires, cast(Dict[str, Any], user).get("id"))
        )
        conn.commit()

        # Send email in background
        first_name = cast(Dict[str, Any], user).get("first_name") or "User"
        background_tasks.add_task(send_verification_email, request.email, first_name, new_token)

        return {"message": "Verification email re-sent. Please check your inbox."}

    except HTTPException:
        raise
    except Error as e:
        logger.error(f"Database error during resend verification: {e}")
        raise HTTPException(status_code=500, detail="Database error")
    finally:
        cursor.close()
        conn.close()

@app.post("/auth/verify-email")
def verify_email(token: str = Query(..., description="Email verification token")):
    """Verify user's email address using verification token"""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        # Find user with matching verification token
        cursor.execute(
            "SELECT id, username, email, token_expires_at FROM users_info WHERE email_verification_token = %s",
            (token,)
        )
        user = cursor.fetchone()

        if not user:
            raise HTTPException(status_code=400, detail="Invalid verification token")

        user_dict = cast(Dict[str, Any], user)
        logger.info(f"Attempting email verification for token={token} matched_user={user_dict.get('email')} (id={user_dict.get('id')})")

        # Check if token has expired
        token_expires_at = cast(Dict[str, Any], user).get("token_expires_at")
        user_dict = cast(Dict[str, Any], user)
        logger.info(f"Token expiry from DB for user {user_dict.get('username')}: {token_expires_at}")
        if token_expires_at and datetime.utcnow() > token_expires_at:
            raise HTTPException(status_code=400, detail="Verification token has expired")

        # Update user as verified and clear verification token
        cursor.execute(
            "UPDATE users_info SET is_verified = %s, email_verification_token = NULL, token_expires_at = NULL WHERE id = %s",
            (True, cast(Dict[str, Any], user).get("id"))
        )
        conn.commit()

        logger.info(f"Update executed, cursor.rowcount={cursor.rowcount}")

        # Re-query to confirm change persisted
        cursor.execute("SELECT is_verified, email_verification_token FROM users_info WHERE id = %s", (cast(Dict[str, Any], user).get("id"),))
        confirmation = cursor.fetchone()
        logger.info(f"Post-update confirmation for id={cast(Dict[str, Any], user).get('id')}: {confirmation}")

        # Log the verification
        log_user_activity(
            activity_type="email_verified",
            username=cast(Dict[str, Any], user).get("username"),
            user_id=cast(Dict[str, Any], user).get("id"),
            activity_details={"message": "User email verified successfully."},
        )

        return {"message": "Email verified successfully. You can now log in to your account."}

    except HTTPException:
        raise
    except Error as e:
        logger.error(f"Database error during email verification: {e}")
        raise HTTPException(status_code=500, detail="Database error")
    finally:
        cursor.close()
        conn.close()

@app.get("/auth/verify-email")
def verify_email_redirect(token: str = Query(..., description="Email verification token")):
    """Redirect legacy GET verification links to the frontend verification page."""
    try:
        # Determine frontend URL - prefer localhost for development to enable SPA routing
        frontend_url = os.getenv('FRONTEND_URL')

        if not frontend_url:
            # Check if we're in development mode (no FRONTEND_URL set)
            # Use localhost for development so Vite's historyApiFallback works
            dev_mode = os.getenv('ENV') != 'production' and not os.getenv('FRONTEND_URL')
            if dev_mode:
                frontend_url = "http://localhost:5173"
            else:
                # Production mode - use the configured origin
                try:
                    frontend_url = ALLOWED_ORIGINS[0] if ALLOWED_ORIGINS and len(ALLOWED_ORIGINS) > 0 else None
                except Exception:
                    frontend_url = None

        if not frontend_url:
            frontend_url = "http://localhost:5173"

        redirect_to = f"{frontend_url.rstrip('/')}/verify-email?token={token}"
        logger.info(f"Redirecting GET /auth/verify-email to frontend: {redirect_to}")
        return RedirectResponse(url=redirect_to)
    except Exception as e:
        logger.error(f"Error redirecting verification link: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.post("/auth/login")
def login(user: UserLogin):
    """Login user and return JWT token"""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        # Get user from database
        cursor.execute("SELECT id, username, password_hash, is_verified FROM users_info WHERE email = %s", (user.email,))
        db_user = cursor.fetchone()

        if not db_user:
            raise HTTPException(status_code=401, detail="Invalid credentials")

        # Check if user is verified
        is_verified = cast(Dict[str, Any], db_user).get("is_verified", False)
        if not is_verified:
            raise HTTPException(status_code=403, detail="Please verify your email address before logging in.")

        # Verify password
        password_hash = cast(Dict[str, Any], db_user).get("password_hash", "")
        if not verify_password(user.password, password_hash):
            raise HTTPException(status_code=401, detail="Invalid credentials")

        # Check 2FA
        user_id = cast(Dict[str, Any], db_user).get("id")
        if is_2fa_enabled(user_id):
            if not user.two_factor_code:
                # Return response indicating 2FA required
                return {
                    "requires_2fa": True, 
                    "message": "Two-factor authentication code required"
                }
            secret = get_user_2fa_secret(user_id)
            if not secret or not verify_2fa_code(secret, user.two_factor_code):
                raise HTTPException(status_code=401, detail="Invalid two-factor authentication code")

        # Create access and refresh tokens
        username = cast(Dict[str, Any], db_user).get("username")
        access_token = create_access_token(data={"sub": username})
        refresh_token = create_refresh_token(data={"sub": username})
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "username": username
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error during login: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        cursor.close()
        conn.close()

def get_username_from_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    """Get current user from JWT token"""
    token = credentials.credentials
    username = verify_token(token)
    if username is None:
        raise HTTPException(status_code=401, detail="Invalid token")
    return username

@app.get("/auth/me", response_model=Dict[str, Any])
def get_user_info(current_user: str = Depends(get_username_from_token)) -> Dict[str, Any]:
    """Get current user information"""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        logger.info(f"Querying /auth/me for username: '{current_user}'")
        cursor.execute("""
            SELECT id, username, first_name, last_name, email, profile_picture, 
                   home_area, work_area, alert_radius, role, created_at, phone_number,
                   browser_notifications_enabled, two_factor_enabled  -- MAKE SURE THIS IS INCLUDED
            FROM users_info WHERE LOWER(username) = LOWER(%s)
        """, (current_user.lower(),))
        user = cursor.fetchone()

        if not user:
            raise HTTPException(status_code=401, detail="Invalid session - user not found")

        user_dict = cast(Dict[str, Any], user)  # Type cast for proper dictionary access
        
        # Get user ID for 2FA check
        user_id = user_dict.get("id")

        # Check if 2FA is enabled for this user
        two_factor_enabled = False
        if user_id:
            try:
                two_factor_enabled = is_2fa_enabled(user_id)
            except Exception as e:
                logger.warning(f"Error checking 2FA status for user {current_user}: {e}")
                two_factor_enabled = False

        # ADD DEBUG LOG TO SEE WHAT'S BEING RETURNED
        logger.info(f"User data for {current_user}: browser_notifications_enabled = {user_dict.get('browser_notifications_enabled')}")

        return {
            "username": user_dict.get("username", ""),
            "first_name": user_dict.get("first_name", ""),
            "last_name": user_dict.get("last_name", ""),
            "email": user_dict.get("email", ""),
            "profile_picture": user_dict.get("profile_picture"),
            "phone_number": user_dict.get("phone_number"),
            "home_area": user_dict.get("home_area"),
            "work_area": user_dict.get("work_area"),
            "alert_radius": user_dict.get("alert_radius", 5),
            "role": user_dict.get("role", "user"),
            "two_factor_enabled": two_factor_enabled,
            "browser_notifications_enabled": user_dict.get("browser_notifications_enabled", False),  # MAKE SURE THIS IS INCLUDED
            "created_at": user_dict.get("created_at", "")
        }

    except Exception as e:
        logger.error(f"Exception in /auth/me: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Database error")
    finally:
        cursor.close()
        conn.close()
        
@app.get("/test-user/{username}")
def test_user(username: str):
    """Test fetching user info by username"""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT * FROM users_info WHERE username = %s", (username,))
        user = cursor.fetchone()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        return user
    except Exception as e:
        logger.error(f"Exception in /test-user/{username}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Database error")
    finally:
        cursor.close()
        conn.close()

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    """Get current user from JWT token - FIXED VERSION"""
    token = credentials.credentials
    username = verify_token(token)
    if username is None:
        raise HTTPException(status_code=401, detail="Invalid token")
    return username

def get_user_id_from_username(username: str) -> Optional[int]:
    """Get user ID from username - FIXED VERSION"""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT id FROM users_info WHERE username = %s", (username,))
        user = cursor.fetchone()
        return cast(Dict[str, Any], user).get('id') if user else None
    except Error as e:
        logger.error(f"Database error getting user ID: {e}")
        return None
    finally:
        cursor.close()
        conn.close()


# Location endpoints
@app.post("/api/get-coordinates", response_model=LocationResponse)
def get_coordinates_endpoint(request: LocationRequest):
    """Get coordinates for an area name"""
    coords = get_coordinates(request.area)

    if not coords:
        raise HTTPException(status_code=404, detail="Could not find coordinates for this area")

    lat, lon = coords
    return LocationResponse(
        area=request.area,
        latitude=lat,
        longitude=lon,
        source="api"
    )

@app.put("/auth/update-location")
def update_user_location(
    location_data: UserLocationUpdate,
    current_user: str = Depends(get_username_from_token)
):
    """Update user's location information"""
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Get coordinates for areas if provided
        home_lat, home_lon = None, None
        work_lat, work_lon = None, None

        if location_data.home_area:
            coords = get_coordinates(location_data.home_area)
            if coords:
                home_lat, home_lon = coords

        if location_data.work_area:
            coords = get_coordinates(location_data.work_area)
            if coords:
                work_lat, work_lon = coords

        # Update user location data
        update_fields = []
        params = []

        if location_data.home_area is not None:
            update_fields.append("home_area = %s")
            params.append(location_data.home_area)
            if home_lat is not None:
                update_fields.append("home_latitude = %s")
                params.append(home_lat)
                update_fields.append("home_longitude = %s")
                params.append(home_lon)

        if location_data.work_area is not None:
            update_fields.append("work_area = %s")
            params.append(location_data.work_area)
            if work_lat is not None:
                update_fields.append("work_latitude = %s")
                params.append(work_lat)
                update_fields.append("work_longitude = %s")
                params.append(work_lon)

        if location_data.alert_radius is not None:
            update_fields.append("alert_radius = %s")
            params.append(location_data.alert_radius)

        if not update_fields:
            raise HTTPException(status_code=400, detail="No fields to update")

        params.append(current_user)
        query = f"UPDATE users_info SET {', '.join(update_fields)} WHERE username = %s"

        cursor.execute(query, params)
        conn.commit()

        log_user_activity(
            activity_type="location_update",
            username=current_user,
            activity_details={
                "updated_fields": [field.split(" = ")[0] for field in update_fields],
                "home_area": location_data.home_area,
                "work_area": location_data.work_area,
                "alert_radius": location_data.alert_radius,
            },
        )

        return {"message": "Location updated successfully"}

    except Error as e:
        logger.error(f"Database error updating location: {e}")
        raise HTTPException(status_code=500, detail="Database error")
    finally:
        cursor.close()
        conn.close()

# New Pydantic model for profile update

# Admin models
class AdminRegister(BaseModel):
    name: str = Field(..., min_length=1, max_length=50, description="Full name")
    email: str = Field(..., description="Email address")
    password: str = Field(..., min_length=6, description="Password")
    department: str = Field(..., description="Department")
    permissions: List[str] = Field(..., description="List of permissions")
    phone: Optional[str] = None
    address: Optional[str] = None

class AdminResponse(BaseModel):
    id: int
    username: str
    name: str
    email: str
    department: str
    permissions: List[str]
    phone: Optional[str]
    address: Optional[str]
    created_at: str
    status: str = "active"


async def check_location_risk(user_id: int, lat: float, lng: float, radius_km: float = 2.0) -> Dict:
    """Check if a location is in a high-risk zone"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Calculate bounding box for the radius
        earth_radius = 6371  # Earth's radius in km
        lat_range = (radius_km / earth_radius) * (180 / 3.14159)
        lng_range = (radius_km / (earth_radius * 3.14159 / 180 * abs(3.14159/180 * lat))) if lat != 0 else (radius_km / earth_radius) * (180 / 3.14159)
        
        # Get crimes in the area
        cursor.execute("""
            SELECT 
                COUNT(*) as total_crimes,
                SUM(CASE WHEN risk_level = 'High' THEN 1 ELSE 0 END) as high_risk_count,
                SUM(CASE WHEN risk_level = 'Medium' THEN 1 ELSE 0 END) as medium_risk_count,
                AVG(CASE WHEN risk_level = 'High' THEN 1 ELSE 0 END) * 100 as high_risk_percentage
            FROM crimes 
            WHERE latitude BETWEEN %s AND %s 
                AND longitude BETWEEN %s AND %s
                AND SQRT(POW(69.1 * (latitude - %s), 2) + POW(69.1 * (%s - longitude) * COS(latitude / 57.3), 2)) <= %s
        """, (lat - lat_range, lat + lat_range, lng - lng_range, lng + lng_range, lat, lng, radius_km))
        
        result = cursor.fetchone()
        
        if not result:
            return {"is_high_risk": False, "safety_score": 100, "high_risk_crimes": 0}
        
        total_crimes = cast(Dict[str, Any], result)["total_crimes"] or 0
        high_risk_count = cast(Dict[str, Any], result)["high_risk_count"] or 0
        
        # Calculate safety score
        if total_crimes == 0:
            safety_score = 100
        else:
            base_score = 100
            crime_density_penalty = min(60, (total_crimes * 2))
            severity_penalty = (high_risk_count * 3)
            safety_score = max(0, base_score - crime_density_penalty - severity_penalty)
        
        is_high_risk = safety_score < 40 or high_risk_count >= 3
        
        return {
            "is_high_risk": is_high_risk,
            "safety_score": safety_score,
            "high_risk_crimes": high_risk_count,
            "total_crimes": total_crimes,
            "risk_level": "High" if safety_score < 40 else "Medium" if safety_score < 60 else "Low"
        }
        
    except Error as e:
        logger.error(f"Error checking location risk: {e}")
        return {"is_high_risk": False, "safety_score": 50, "high_risk_crimes": 0}
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()


@app.post("/api/location/check-risk")
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
            SELECT id, username, email, phone_number, browser_notifications_enabled, alert_radius, live_alerts_enabled 
            FROM users_info WHERE username = %s
        """, (current_user,))
        user = cursor.fetchone()
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Cast to Dict to satisfy type checker since cursor(dictionary=True) returns dict
        user = cast(Dict[str, Any], user)
        
        user_id = user["id"]
        alert_radius = float(user.get("alert_radius", 5.0))
        live_alerts_enabled = bool(user.get("live_alerts_enabled", True))
        
        # Check location risk with REAL data
        risk_assessment = await get_real_safety_data_from_endpoints(
            request.latitude, 
            request.longitude,
            request.address
        )
        
        print(f"📊 Real risk assessment: {risk_assessment}")
        
        # Send alert if high risk (safety score < 40)
        if risk_assessment["safety_score"] < 40 and request.check_immediate and live_alerts_enabled:
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

async def send_alert_notification(alert: RiskZoneAlert):
    """Send alert notifications via email and browser push - FIXED VERSION"""
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Get complete user data including id
        cursor.execute("""
            SELECT id, username, email, browser_notifications_enabled 
            FROM users_info 
            WHERE id = %s
        """, (alert.user_id,))
        
        user_row = cursor.fetchone()
        
        if not user_row:
            print("❌ User not found for alert notification")
            return
        
        user_data = cast(Dict[str, Any], user_row)  # Cast to Dict for type checking since cursor is set to dictionary=True
        
        # Send email notification
        email_success = False
        user_email = user_data.get('email')
        if user_email:
            if hasattr(alert_notification_system, 'send_alert_email'):
                email_success = await alert_notification_system.send_alert_email(alert, user_email)
                print(f"✅ Email notification sent: {email_success}")
        
        # Now call send_browser_notification with complete user_data
        browser_success = False
        if user_data.get('browser_notifications_enabled'):
            browser_success = await alert_notification_system.send_browser_notification(alert, user_data)
            print(f"✅ Browser notification sent: {browser_success}")
        
        # Log the alert
        cursor.execute("""
            INSERT INTO alert_notifications 
            (user_id, alert_type, message, sent_via, created_at, success_status, safety_score, risk_level, high_risk_count)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            alert.user_id,
            alert.alert_type,
            alert.message,
            'both' if (email_success and browser_success) else 'email' if email_success else 'browser' if browser_success else 'none',
            datetime.now(),
            'success' if (email_success or browser_success) else 'failed',
            alert.safety_score,
            alert.risk_level,
            alert.high_risk_crimes
        ))
        
        conn.commit()
        print("✅ Enhanced alert notification completed successfully")
        
        return {
            "email_sent": email_success,
            "browser_sent": browser_success,
            "alert_message": alert.message
        }
        
    except Exception as e:
        print(f"❌ Error sending enhanced alert notification: {e}")
        logger.error(f"Error sending enhanced alert notification: {e}")
        return {
            "email_sent": False,
            "browser_sent": False,
            "error": str(e)
        }
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()

# Add browser notification endpoints
@app.post("/api/browser-notifications/subscribe")
async def subscribe_browser_notifications(
    subscription_data: dict,
    current_user: str = Depends(get_username_from_token)
):
    """Subscribe to browser push notifications - FIXED VERSION"""
    conn = None
    cursor = None
    try:
        print(f"🌐 Browser push subscription request from user: {current_user}")
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Get user ID
        cursor.execute("SELECT id FROM users_info WHERE username = %s", (current_user,))
        user = cursor.fetchone()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        user_id = cast(Dict[str, Any], user)["id"]
        
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
        
        conn.commit()
        
        print(f"✅ Browser push subscription saved for user {current_user}")
        
        return {"message": "Browser push notifications subscribed successfully"}
        
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

@app.get("/api/browser-notifications")
async def get_browser_notifications(
    current_user: str = Depends(get_username_from_token),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0)
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
        
        # Cast to Dict after None check to satisfy type checker
        user = cast(Dict[str, Any], user)
        user_id = user["id"]
        
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

@app.post("/api/browser-notifications/{notification_id}/read")
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
        
        user_id = cast(Dict[str, Any], user)["id"]
        
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

# Call this function during startup
@app.on_event("startup")
def on_startup():
    """Prepare database schema when the application starts."""
    try:
        initialize_schema()
        ensure_browser_notifications_tables()
        ensure_alert_subscriptions_table()
        ensure_alerts_tables_schema()
        print("✅ Database schema initialized successfully")
    except Exception as exc:
        logger.error("Startup schema initialization failed", exc_info=exc)
        print(f"❌ Database initialization error: {exc}")

async def run_monitor_saved_locations():
    """Wrapper to run the async monitor function"""
    try:
        await monitor_saved_locations()
    except Exception as e:
        logger.error(f"Error in monitor_saved_locations: {e}")

def monitor_saved_locations_job():
    """Synchronous wrapper for the async function"""
    asyncio.run(run_monitor_saved_locations())

async def send_alert_email(alert: RiskZoneAlert):
    """Send email alert"""
    try:
        # Create email message
        subject = f"🚨 Safety Alert: High Risk Zone Detected"
        
        message = f"""
        <html>
        <body>
            <h2>Safety Alert from SafeVision</h2>
            <p>Dear {alert.username},</p>
            
            <div style="background-color: #fff3cd; border: 1px solid #ffeaa7; padding: 15px; border-radius: 5px; margin: 15px 0;">
                <h3 style="color: #856404; margin-top: 0;">⚠️ High Risk Zone Alert</h3>
                <p style="margin: 5px 0;"><strong>Location:</strong> {alert.address}</p>
                <p style="margin: 5px 0;"><strong>Safety Score:</strong> {alert.safety_score}%</p>
                <p style="margin: 5px 0;"><strong>Risk Level:</strong> {alert.risk_level}</p>
                <p style="margin: 5px 0;"><strong>High Risk Incidents:</strong> {alert.high_risk_crimes} in area</p>
            </div>
            
            <h3>Recommended Actions:</h3>
            <ul>
                <li>Stay alert and aware of your surroundings</li>
                <li>Avoid walking alone if possible</li>
                <li>Keep emergency contacts readily available</li>
                <li>Consider alternative routes</li>
                <li>Report any suspicious activity to authorities</li>
            </ul>
            
            <p><strong>Alert Time:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            
            <hr>
            <p style="color: #666; font-size: 12px;">
                This is an automated safety alert from CrimeVision. 
                To manage your alert preferences, visit your dashboard settings.
            </p>
        </body>
        </html>
        """
        
        # Send email (implement your email sending logic here)
        # This is a placeholder - implement with your preferred email service
        logger.info(f"Would send email alert to {alert.email}: {subject}")
        
    except Exception as e:
        logger.error(f"Error sending alert email: {e}")



@app.post("/api/location/monitor-live")
async def monitor_live_location(
    request: LocationAlertRequest,
    current_user: str = Depends(get_username_from_token)
):
    """Monitor live location for immediate risk alerts"""
    try:
        print(f"📍 Live location monitoring for user: {current_user}")
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Get user info
        cursor.execute("""
            SELECT id, username, email, browser_notifications_enabled, alert_radius, live_alerts_enabled 
            FROM users_info WHERE username = %s
        """, (current_user,))
        user = cursor.fetchone()
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        user_id = cast(Dict[str, Any], user)["id"]
        alert_radius = float(cast(Dict[str, Any], user).get("alert_radius", 5.0))
        live_alerts_enabled = bool(cast(Dict[str, Any], user).get("live_alerts_enabled", True))
        
        # Get real safety data
        safety_data = await get_real_safety_data_from_endpoints(
            request.latitude, 
            request.longitude,
            request.address
        )
        
        print(f"📊 Safety data for live location: {safety_data}")
        
        # Send immediate alert if high risk (safety score < 40)
        if safety_data["safety_score"] < 40 and live_alerts_enabled:
            alert = RiskZoneAlert(
                user_id=user_id,
                username=cast(Dict[str, Any], user).get("username", ""),
                email=cast(Dict[str, Any], user).get("email", ""),
                latitude=request.latitude,
                longitude=request.longitude,
                address=request.address or f"Current location ({request.latitude}, {request.longitude})",
                risk_level=safety_data["risk_level"],
                safety_score=safety_data["safety_score"],
                high_risk_crimes=safety_data["high_risk_crimes"],
                alert_type="live_high_risk_zone",
                message=f"🚨 {safety_data['risk_level']} risk detected at your current location! Safety score: {safety_data['safety_score']}%"
            )
            
            print("🚨 High risk detected at live location - sending immediate alert")
            result = await send_alert_notification(alert)
            
            return {
                "alert_sent": True,
                "safety_data": safety_data,
                "notification_result": result,
                "message": "High risk detected - alert sent"
            }
        
        return {
            "alert_sent": False,
            "safety_data": safety_data,
            "message": "Location is safe - no alert needed"
        }
        
    except Exception as e:
        print(f"❌ Error in live location monitoring: {e}")
        logger.error(f"Error monitoring live location: {e}")
        raise HTTPException(status_code=500, detail="Failed to monitor live location")
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()


async def get_real_safety_data_from_endpoints(latitude: float, longitude: float, address: Optional[str] = None) -> Dict[str, Any]:
    try:
        print(f"🔍 Fetching REAL safety data for: {latitude}, {longitude}")
        
        area_name = await get_area_name_from_coordinates(latitude, longitude)
        print(f"📍 Area identified: {area_name}")
        
        # Get safety score data (this should be the primary source)
        safety_score_data = await get_area_safety_score_from_endpoint(area_name)
        crime_data = await get_crime_data_from_endpoint(latitude, longitude, area_name)
        
        print(f"📊 Safety score data: {safety_score_data}")
        print(f"📊 Crime data: {crime_data}")
        
        # Use safety score as primary, fallback to crime data if needed
        safety_score = safety_score_data.get('safety_score', 50.0)
        risk_level = safety_score_data.get('risk_level', 'Unknown')
        
        # Get crime counts from safety score data (more reliable)
        total_crimes = safety_score_data.get('total_crimes', 0)
        high_risk_crimes = safety_score_data.get('high_risk_count', 0)
        
        # FIXED: Consistent risk assessment using safety score
        is_high_risk = safety_score < 60  # Anything below 60% is considered risky
        
        print(f"🎯 FINAL ASSESSMENT - Area: {area_name}, Score: {safety_score}%, "
              f"Risk: {risk_level}, Total Crimes: {total_crimes}, "
              f"High-risk: {high_risk_crimes}, IsHighRisk: {is_high_risk}")
        
        return {
            'safety_score': safety_score,
            'risk_level': risk_level,
            'is_high_risk': is_high_risk,
            'total_crimes': total_crimes,
            'high_risk_crimes': high_risk_crimes,
            'area_name': area_name,
            'source': 'real_endpoints'
        }
        
    except Exception as e:
        print(f"❌ Error in safety data: {e}")
        return {
            'safety_score': 50.0,
            'risk_level': 'Unknown',
            'is_high_risk': False,
            'total_crimes': 0,
            'high_risk_crimes': 0,
            'area_name': 'Unknown',
            'source': 'error_fallback'
        }

async def get_area_name_from_coordinates(lat: float, lng: float) -> str:
    """Get area name from coordinates using reverse geocoding"""
    try:
        # Perform reverse geocoding using Nominatim API in a thread
        def reverse_geocode():
            response = requests.get(
                "https://nominatim.openstreetmap.org/reverse",
                params={
                    "lat": lat,
                    "lon": lng,
                    "format": "json",
                    "addressdetails": 1,
                    "zoom": 18
                },
                headers={"User-Agent": "CrimeVision/1.0 (contact@example.com)"},
                timeout=10,
            )
            response.raise_for_status()
            return response.json()
        
        # Run the synchronous request in a thread pool
        data = await asyncio.to_thread(reverse_geocode)
        
        if not data:
            print(f"No reverse geocoding results for ({lat}, {lng})")
            return "Unknown"
        
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
        return "Unknown"

async def get_area_safety_score_from_endpoint(area_name: str) -> Dict[str, Any]:
    """Get accurate safety score for an area"""
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Get accurate crime statistics
        cursor.execute("""
            SELECT
                COUNT(*) as total_crimes,
                SUM(CASE WHEN risk_level = 'High' THEN 1 ELSE 0 END) as high_risk_count,
                SUM(CASE WHEN risk_level = 'Medium' THEN 1 ELSE 0 END) as medium_risk_count
            FROM crimes
            WHERE area = %s
        """, (area_name,))
        
        stats = cursor.fetchone()
        
        if stats:
            stats_dict = cast(Dict[str, Any], stats)
            total_crimes = stats_dict.get('total_crimes', 0) or 0
            high_risk_count = stats_dict.get('high_risk_count', 0) or 0
            medium_risk_count = stats_dict.get('medium_risk_count', 0) or 0
            
            print(f"🔍 AREA STATS for {area_name}: total={total_crimes}, high_risk={high_risk_count}, medium_risk={medium_risk_count}")
            
            # REAL safety score calculation
            if total_crimes == 0:
                safety_score = 100.0
            else:
                base_score = 100.0
                # Penalize based on crime density and severity
                crime_density_penalty = min(50.0, (total_crimes * 0.5))  # Reduced multiplier
                high_risk_penalty = high_risk_count * 2.0
                medium_risk_penalty = medium_risk_count * 0.5
                
                safety_score = max(0.0, base_score - crime_density_penalty - high_risk_penalty - medium_risk_penalty)
            
            # Determine risk level based on score
            if safety_score < 40:
                risk_level = "High"
            elif safety_score < 70:
                risk_level = "Medium"
            else:
                risk_level = "Low"
            
            print(f"🎯 CALCULATED SCORE for {area_name}: {safety_score}% -> {risk_level}")
            
            return {
                'safety_score': round(safety_score, 1),
                'risk_level': risk_level,
                'total_crimes': total_crimes,
                'high_risk_count': high_risk_count,
                'medium_risk_count': medium_risk_count
            }
        
        return {'safety_score': 100.0, 'risk_level': 'Low', 'total_crimes': 0}
        
    except Exception as e:
        print(f"❌ Error getting safety score for {area_name}: {e}")
        return {'safety_score': 50.0, 'risk_level': 'Unknown'}
    finally:
        # FIX: Proper resource cleanup
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()
async def get_crime_data_from_endpoint(lat: float, lng: float, area_name: str) -> Dict[str, Any]:
    """Get crime data using your existing crimes endpoint logic"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Get crimes in the area (similar to your /api/crimes endpoint)
        cursor.execute("""
            SELECT 
                COUNT(*) as total_crimes,
                SUM(CASE WHEN risk_level = 'High' THEN 1 ELSE 0 END) as high_risk_count,
                SUM(CASE WHEN risk_level = 'Medium' THEN 1 ELSE 0 END) as medium_risk_count,
                COUNT(DISTINCT crime_type) as unique_crime_types
            FROM crimes 
            WHERE area = %s OR (
                latitude BETWEEN %s AND %s 
                AND longitude BETWEEN %s AND %s
            )
        """, (area_name, lat-0.02, lat+0.02, lng-0.02, lng+0.02))
        
        result = cursor.fetchone()
        
        if result:
            result_dict = cast(Dict[str, Any], result)
            return {
                'total_crimes': result_dict.get('total_crimes', 0) or 0,
                'high_risk_count': result_dict.get('high_risk_count', 0) or 0,
                'medium_risk_count': result_dict.get('medium_risk_count', 0) or 0,
                'unique_crime_types': result_dict.get('unique_crime_types', 0) or 0
            }
        
        return {'total_crimes': 0, 'high_risk_count': 0, 'medium_risk_count': 0}
        
    except Exception as e:
        print(f"Error getting crime data: {e}")
        return {'total_crimes': 0, 'high_risk_count': 0, 'medium_risk_count': 0}

async def get_safety_data_from_database(lat: float, lng: float) -> Dict[str, Any]:
    """Fallback: get safety data directly from database"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("""
            SELECT 
                COUNT(*) as total_crimes,
                SUM(CASE WHEN risk_level = 'High' THEN 1 ELSE 0 END) as high_risk_count,
                SUM(CASE WHEN risk_level = 'Medium' THEN 1 ELSE 0 END) as medium_risk_count
            FROM crimes 
            WHERE latitude BETWEEN %s AND %s 
                AND longitude BETWEEN %s AND %s
                AND SQRT(POW(69.1 * (latitude - %s), 2) + POW(69.1 * (%s - longitude) * COS(latitude / 57.3), 2)) <= %s
        """, (lat-0.02, lat+0.02, lng-0.02, lng+0.02, lat, lng, 2.0))
        
        stats = cursor.fetchone()
        
        if stats:
            stats_dict = cast(Dict[str, Any], stats)
            total_crimes = stats_dict.get('total_crimes', 0) or 0
            high_risk_count = stats_dict.get('high_risk_count', 0) or 0
            
            if total_crimes == 0:
                safety_score = 100.0
            else:
                base_score = 100.0
                crime_density_penalty = min(60.0, (total_crimes * 2.0))
                severity_penalty = (high_risk_count * 3.0)
                safety_score = max(0.0, base_score - crime_density_penalty - severity_penalty)
            
            risk_level = "High" if safety_score < 40 else "Medium" if safety_score < 60 else "Low"
            
            return {
                'safety_score': round(safety_score, 1),
                'risk_level': risk_level,
                'total_crimes': total_crimes,
                'high_risk_crimes': high_risk_count,
                'medium_risk_crimes': stats_dict.get('medium_risk_count', 0) or 0,
                'source': 'database_direct'
            }
        
        return {
            'safety_score': 100.0,
            'risk_level': 'Low',
            'total_crimes': 0,
            'high_risk_crimes': 0,
            'medium_risk_crimes': 0,
            'source': 'no_data'
        }
        
    except Exception as e:
        print(f"Database fallback error: {e}")
        return {
            'safety_score': 50.0,
            'risk_level': 'Unknown',
            'total_crimes': 0,
            'high_risk_crimes': 0,
            'source': 'error'
        }
    
async def monitor_saved_locations():
    """Background task to check saved locations and send alerts - FIXED VERSION"""
    conn = None
    cursor = None
    try:
        logger.info("🔄 Starting enhanced saved locations monitoring...")
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Get users with active alert subscriptions - IMPROVED QUERY
        cursor.execute("""
            SELECT DISTINCT u.id, u.username, u.email, 
                   u.home_area, u.work_area, 
                   u.home_latitude, u.home_longitude,
                   u.work_latitude, u.work_longitude, 
                   u.alert_radius, u.browser_notifications_enabled,
                   s.id as subscription_id, s.is_active as subscription_active
            FROM users_info u
            LEFT JOIN alert_subscriptions s ON u.id = s.user_id AND s.is_active = TRUE
            WHERE u.is_active = TRUE 
            AND s.is_active = TRUE
            AND (u.home_latitude IS NOT NULL OR u.work_latitude IS NOT NULL
                 OR u.home_area IS NOT NULL OR u.work_area IS NOT NULL)
        """)
        
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
                                (home_lat, home_lng, user_id)
                            )
                            logger.info(f"✅ Updated home coordinates for user {user_id}")
                    except Exception as e:
                        logger.error(f"❌ Error fetching home coordinates: {e}")
                        continue  # Skip this location if coordinates can't be fetched
                
                # Only process home location if we have valid coordinates
                if home_lat is not None and home_lng is not None:
                    try:
                        # Get REAL safety data for home location
                        safety_data = await get_real_safety_data_from_endpoints(
                            float(home_lat),
                            float(home_lng),
                            home_area or "Home Location"
                        )
                        
                        # Create risk assessment
                        risk_assessment = {
                            "safety_score": safety_data['safety_score'],
                            "risk_level": safety_data['risk_level'],
                            "high_risk_crimes": safety_data['high_risk_crimes'],
                            "is_high_risk": safety_data['safety_score'] < 40,
                            "precautions": safety_data.get('precautions', 'General safety precautions advised.')
                        }
                        
                        # Send alert for home location
                        await create_and_send_alert(
                            user,
                            "home",
                            risk_assessment,
                            float(home_lat),
                            float(home_lng)
                        )
                        logger.info(f"✅ Processed home location for user {user_id}")
                    except Exception as e:
                        logger.error(f"❌ Error processing home location for user {user_id}: {e}")
                
                # Check work location - FIXED: Better coordinate handling
                work_lat = cast(Dict[str, Any], user).get("work_latitude")
                work_lng = cast(Dict[str, Any], user).get("work_longitude")
                work_area = cast(Dict[str, Any], user).get("work_area")
                
                # FIX: Better coordinate handling for work area
                if work_area and (work_lat is None or work_lng is None):
                    try:
                        logger.info(f"🔍 Fetching missing coordinates for work area: {work_area}")
                        coords = get_coordinates(work_area)
                        if coords:
                            work_lat, work_lng = coords
                            # Update user coordinates in database
                            cursor.execute(
                                "UPDATE users_info SET work_latitude = %s, work_longitude = %s WHERE id = %s",
                                (work_lat, work_lng, user_id)
                            )
                            logger.info(f"✅ Updated work coordinates for user {user_id}")
                    except Exception as e:
                        logger.error(f"❌ Error fetching work coordinates: {e}")
                        continue  # Skip this location if coordinates can't be fetched
                
                # Only process work location if we have valid coordinates
                if work_lat is not None and work_lng is not None:
                    try:
                        # Get REAL safety data for work location
                        safety_data = await get_real_safety_data_from_endpoints(
                            float(work_lat),
                            float(work_lng),
                            work_area or "Work Location"
                        )
                        
                        # Create risk assessment
                        risk_assessment = {
                            "safety_score": safety_data['safety_score'],
                            "risk_level": safety_data['risk_level'],
                            "high_risk_crimes": safety_data['high_risk_crimes'],
                            "is_high_risk": safety_data['safety_score'] < 40,
                            "precautions": safety_data.get('precautions', 'General safety precautions advised.')
                        }
                        
                        # Send alert for work location
                        await create_and_send_alert(
                            user,
                            "work", 
                            risk_assessment,
                            float(work_lat),
                            float(work_lng)
                        )
                        logger.info(f"✅ Processed work location for user {user_id}")
                    except Exception as e:
                        logger.error(f"❌ Error processing work location for user {user_id}: {e}")
                        
            except Exception as e:
                logger.error(f"❌ Error monitoring locations for user {cast(Dict[str, Any], user).get('username', 'unknown')}: {e}")
                continue
                
        conn.commit()
                
    except Exception as e:
        logger.error(f"❌ Error in enhanced monitor_saved_locations: {e}")
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()

@app.post("/api/test/fix-alerts")
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
        
        # Create a test alert with all required fields
        user_dict = cast(Dict[str, Any], user_data)
        alert = RiskZoneAlert(
            user_id=user_dict['id'],
            username=user_dict['username'],
            email=user_dict['email'],
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
async def get_recent_incidents(lat: float, lng: float, radius_km: float = 2.0) -> Dict[str, Any]:
    """Get recent incidents in the area for alert details"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Get incidents from last 24 hours
        yesterday = datetime.now() - timedelta(hours=24)
        
        cursor.execute("""
            SELECT 
                crime_type,
                risk_level,
                COUNT(*) as incident_count,
                MAX(crime_date) as latest_incident
            FROM crimes 
            WHERE latitude BETWEEN %s AND %s 
                AND longitude BETWEEN %s AND %s
                AND crime_date >= %s
            GROUP BY crime_type, risk_level
            ORDER BY latest_incident DESC
            LIMIT 5
        """, (lat - 0.02, lat + 0.02, lng - 0.02, lng + 0.02, yesterday))
        
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
            "incidents_detail": incidents
        }
        
    except Exception as e:
        logger.error(f"Error getting recent incidents: {e}")
        return {"recent_incidents": 0, "latest_incident_type": None}
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
            "Be cautious when using ATMs or carrying cash"
        ])
    
    if 'Vehicle Theft' in incident_types:
        precautions.extend([
            "Park in well-lit, secure areas",
            "Never leave valuables in your vehicle",
            "Use steering wheel locks or anti-theft devices"
        ])
    
    if any(crime in incident_types for crime in ['Violent Crime', 'murder']):
        precautions.extend([
            "Travel in groups when possible",
            "Avoid confrontations and stay in public areas",
            "Have emergency numbers readily accessible"
        ])
    
    # Default precautions
    if not precautions:
        precautions = [
            "Stay alert to your surroundings",
            "Avoid isolated or poorly lit areas",
            "Keep emergency contacts handy"
        ]
    
    return ". ".join(precautions) + "."



@app.post("/api/test/alerts/trigger-immediate")
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
        
        user_dict = cast(Dict[str, Any], user_data)
        
        # Use home location or default test location
        test_lat = user_dict.get('home_latitude') or 31.5204
        test_lng = user_dict.get('home_longitude') or 74.3587
        test_address = user_dict.get('home_area') or "Test Location"
        
        # GET REAL SAFETY DATA FIRST
        safety_data = await get_real_safety_data_from_endpoints(test_lat, test_lng, test_address)
        print(f"📊 REAL safety data for test: {safety_data}")
        
        # Create a test alert with REAL data from endpoints
        alert = RiskZoneAlert(
            user_id=user_dict['id'],
            username=user_dict['username'],
            email=user_dict['email'],
            phone=user_dict.get('phone_number'),
            latitude=test_lat,
            longitude=test_lng,
            address=test_address,
            risk_level=safety_data['risk_level'],  # REAL DATA
            safety_score=safety_data['safety_score'],  # REAL DATA
            high_risk_crimes=safety_data['high_risk_crimes'],  # REAL DATA
            alert_type="test_immediate_alert",
            message=f"TEST: {safety_data['risk_level']} risk area. Safety score: {safety_data['safety_score']}%. {safety_data['high_risk_crimes']} high-risk incidents."
        )
        
        print(f"🔔 Testing immediate alert for user: {user_dict['username']}")
        print(f"📊 Using REAL data - Score: {safety_data['safety_score']}%, Risk: {safety_data['risk_level']}, High-risk crimes: {safety_data['high_risk_crimes']}")
        
        # Send the alert with REAL data
        result = await send_alert_notification(alert)
        
        return {
            "message": "✅ Test alert triggered successfully with REAL data",
            "user": user_dict['username'],
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
            

async def create_and_send_alert(user_data, location_type, risk_assessment, lat, lng):
    try:
        safety_score = risk_assessment["safety_score"]
        risk_level = risk_assessment["risk_level"]
        is_high_risk = risk_assessment.get("is_high_risk", safety_score < 40)
        
        # Get area name
        area_name = await get_area_name_from_coordinates(lat, lng)
        if not area_name or area_name == "Unknown":
            area_name = user_data.get(f"{location_type}_area", f"{location_type.title()} Location")
        
        if is_high_risk or safety_score < 60:  # Only send alerts for actual high/medium risk
            alert_type = "high_risk_zone"
            should_send_alert = True
            logger.info(f"🚨 RISK ALERT at {area_name}: {safety_score}% ({risk_level})")
        else:
            alert_type = "safe_area" 
            should_send_alert = SAFE_AREA_ALERT_CONFIG['send_safe_alerts']
            logger.info(f"✅ SAFE AREA at {area_name}: {safety_score}% ({risk_level})")
        
    # In create_and_send_alert function
        cooldown_key = f"{user_data['id']}_{location_type}"

# Only use cooldown for safe areas, never for high risk
        if alert_type == "safe_area":
            if cooldown_key in alert_cooldown_cache:
                last_alert_time = alert_cooldown_cache[cooldown_key]
                cooldown_minutes = SAFE_AREA_ALERT_CONFIG['cooldown_minutes']
                if (datetime.now() - last_alert_time).total_seconds() < cooldown_minutes * 60:
                    logger.info(f"⏳ Skipping safe area alert due to cooldown")
                    return
            alert_cooldown_cache[cooldown_key] = datetime.now()
        else:
    # For risk alerts, clear any cooldown to ensure immediate delivery
            if cooldown_key in alert_cooldown_cache:
                del alert_cooldown_cache[cooldown_key]
        
        # Only proceed if we should send alert
        if not should_send_alert:
            return
        
        # Create the alert
        location_name = user_data.get(f"{location_type}_area", f"{location_type.title()} Location")
        address = f"{location_name} ({lat:.4f}, {lng:.4f})"
        
        # Create appropriate message based on alert type
        if alert_type == "safe_area":
            title = f"✅ Safe Area - {location_name}"
            message = f"Your {location_type} location is safe. Safety score: {safety_score}%. Risk level: {risk_level}."
            severity = "low"
        else:
            title = f"🚨 High Risk Alert - {location_name}"
            message = f"High risk detected at your {location_type} location. Safety score: {safety_score}%. Risk level: {risk_level}."
            severity = "high"
        
        # Create alert record in database
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("""
            INSERT INTO user_alerts 
            (user_id, title, message, alert_type, area, severity, is_read, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            user_data["id"],
            title,
            message,
            alert_type,
            location_name,
            severity,
            False,
            datetime.now()
        ))
        
        alert_id = cursor.lastrowid
        
        # Create RiskZoneAlert for notification
        alert = RiskZoneAlert(
            user_id=user_data["id"],
            username=user_data["username"],
            email=user_data["email"],
            phone=user_data.get("phone_number"),
            latitude=lat,
            longitude=lng,
            address=address,
            risk_level=risk_level,
            safety_score=safety_score,
            high_risk_crimes=risk_assessment["high_risk_crimes"],
            alert_type=alert_type,
            message=message,
            precautions=risk_assessment.get("precautions", "Stay alert and aware of your surroundings.")
        )
        
        # Send the appropriate alert notification
        if alert_type == "safe_area":
            await send_safe_area_notification(alert)
        else:
            await send_alert_notification(alert)
        
        conn.commit()
        logger.info(f"✅ {alert_type} alert created and sent for user {user_data['username']} - {location_name}")
        
    except Exception as e:
        logger.error(f"❌ Error creating alert for user {user_data.get('username', 'unknown')}: {e}")
        if conn:
            conn.rollback()
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()


async def is_in_cooldown(user_id: int, location_type: str) -> bool:
    """Check if safe area alert is in cooldown for this user and location"""
    cooldown_key = f"{user_id}_{location_type}_safe"
    if cooldown_key in alert_cooldown_cache:
        last_alert_time = alert_cooldown_cache[cooldown_key]
        cooldown_minutes = SAFE_AREA_ALERT_CONFIG['cooldown_minutes']
        if (datetime.now() - last_alert_time).total_seconds() < cooldown_minutes * 60:
            return True
    return False

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
        browser_notifications_enabled = bool(cast(Dict[str, Any], user).get("browser_notifications_enabled", True))
        
        # Send formatted safe area email alert
        email_success = False
        if user_email:
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
# In your main.py, update the scheduler setup
def start_background_monitoring():
    """Start background monitoring tasks - FIXED VERSION"""
    try:
        # Remove any existing jobs to avoid duplicates
        try:
            scheduler.remove_job('monitor_saved_locations')
        except Exception:
            pass
        
        # Use the synchronous wrapper for APScheduler
        scheduler.add_job(
            monitor_saved_locations_job,
            trigger=IntervalTrigger(minutes=1),  # Run every minute for testing
            id='monitor_saved_locations',
            name='Monitor saved locations for risk alerts',
            replace_existing=True,
            max_instances=1
        )
        
        
        logger.info("✅ Background monitoring tasks started successfully")
        print("🕒 Scheduler started - monitoring jobs are active")
        
    except Exception as e:
        logger.error(f"❌ Error starting background monitoring: {e}")
        print(f"❌ Scheduler error: {e}")


@app.post("/api/test/alert-system")
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
        
        # Cast to Dict for type safety
        user_dict = cast(Dict[str, Any], user_data)
        
        # Use home location or default
        test_lat = user_dict.get('home_latitude') or 31.5204
        test_lng = user_dict.get('home_longitude') or 74.3587
        test_address = user_dict.get('home_area') or "Test Location"
        
        # Create test alert
        alert = RiskZoneAlert(
            user_id=user_dict['id'],
            username=user_dict['username'],
            email=user_dict['email'],
            phone=user_dict.get('phone_number'),
            latitude=test_lat,
            longitude=test_lng,
            address=test_address,
            risk_level="High",
            safety_score=35.0,
            high_risk_crimes=3,
            alert_type="test_alert",
            precautions = None,
            message="TEST: This is a test alert from the CrimeVision system.",
            
        )
        
        print(f"🔔 Testing alert system for user: {user_dict['username']}")
        
        # Send the alert
        result = await send_alert_notification(alert)
        
        return {
            "message": "✅ Test alert completed successfully",
            "user": user_dict['username'],
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
            
def test_scheduler_job():
    """Test job to verify scheduler is working"""
    try:
        print(f"✅ Scheduler test job running at {datetime.now()}")
        logger.info("Scheduler test job executed successfully")
    except Exception as e:
        logger.error(f"Scheduler test job error: {e}")

# Update the startup event
@app.on_event("startup")
async def startup_event():
    """Start background tasks on application startup"""
    print("🚀 Starting application...")
    try:
        start_background_monitoring()
        print("✅ Background monitoring started")
        
        # Test the scheduler immediately
        scheduler.print_jobs()
        
    except Exception as e:
        print(f"❌ Startup error: {e}")
        logger.error(f"Startup error: {e}")

@app.put("/auth/update-profile")
def update_user_profile(
    profile_data: UserProfileUpdate,
    current_user: str = Depends(get_username_from_token)
):
    """Update user's profile information - FIXED BROWSER NOTIFICATIONS"""
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        update_fields = []
        params = []

        # Existing fields...
        if profile_data.first_name is not None:
            update_fields.append("first_name = %s")
            params.append(validate_name(profile_data.first_name))

        if profile_data.last_name is not None:
            update_fields.append("last_name = %s")
            params.append(validate_name(profile_data.last_name))

        # Phone number handling
        if profile_data.phone_number is not None:
            phone_number = profile_data.phone_number.strip()
            if phone_number:
                if not phone_number.replace('+', '').replace('-', '').replace(' ', '').isdigit():
                    raise HTTPException(status_code=400, detail="Invalid phone number format")
                
                update_fields.append("phone_number = %s")
                params.append(phone_number)
            else:
                update_fields.append("phone_number = NULL")

        if profile_data.browser_notifications_enabled is not None:
            update_fields.append("browser_notifications_enabled = %s")
            # Ensure proper boolean conversion
            browser_enabled = bool(profile_data.browser_notifications_enabled)
            params.append(browser_enabled)
            logger.info(f"🔄 Setting browser_notifications_enabled to: {browser_enabled}")
            
        if profile_data.monitor_live_location is not None:
            update_fields.append("monitor_live_location = %s")
            # Coerce boolean to integer to avoid DB adapter type issues
            live_enabled = 1 if bool(profile_data.monitor_live_location) else 0
            params.append(live_enabled)
            logger.info(f"🔄 Setting monitor_live_location to: {live_enabled}")


        # Handle home area with coordinates
        if profile_data.home_area is not None:
            update_fields.append("home_area = %s")
            params.append(profile_data.home_area)
            
            try:
                logger.info(f"🔍 Fetching coordinates for updated home area: {profile_data.home_area}")
                coords = get_coordinates(profile_data.home_area)
                if coords:
                    home_lat, home_lon = coords
                    update_fields.append("home_latitude = %s")
                    params.append(home_lat)
                    update_fields.append("home_longitude = %s")
                    params.append(home_lon)
                    logger.info(f"✅ Home coordinates updated: {home_lat}, {home_lon}")
                else:
                    logger.warning(f"❌ No coordinates found for home area: {profile_data.home_area}")
                    # Set to NULL instead of empty strings
                    update_fields.append("home_latitude = NULL")
                    update_fields.append("home_longitude = NULL")
            except Exception as e:
                logger.error(f"❌ Error fetching home coordinates: {e}")
                update_fields.append("home_latitude = NULL")
                update_fields.append("home_longitude = NULL")

        # Handle work area with coordinates
        if profile_data.work_area is not None:
            update_fields.append("work_area = %s")
            params.append(profile_data.work_area)
            
            try:
                logger.info(f"🔍 Fetching coordinates for updated work area: {profile_data.work_area}")
                coords = get_coordinates(profile_data.work_area)
                if coords:
                    work_lat, work_lon = coords
                    update_fields.append("work_latitude = %s")
                    params.append(work_lat)
                    update_fields.append("work_longitude = %s")
                    params.append(work_lon)
                    logger.info(f"✅ Work coordinates updated: {work_lat}, {work_lon}")
                else:
                    logger.warning(f"❌ No coordinates found for work area: {profile_data.work_area}")
                    update_fields.append("work_latitude = NULL")
                    update_fields.append("work_longitude = NULL")
            except Exception as e:
                logger.error(f"❌ Error fetching work coordinates: {e}")
                update_fields.append("work_latitude = NULL")
                update_fields.append("work_longitude = NULL")

        if profile_data.alert_radius is not None:
            update_fields.append("alert_radius = %s")
            params.append(profile_data.alert_radius)

        if not update_fields:
            raise HTTPException(status_code=400, detail="No fields to update")

        params.append(current_user)
        query = f"UPDATE users_info SET {', '.join(update_fields)} WHERE username = %s"

        logger.info(f"🔄 Executing profile update query: {query}")
        logger.info(f"📊 Update parameters: {params}")

        cursor.execute(query, params)
        conn.commit()

       
        # VERIFY the update worked
        cursor.execute("SELECT browser_notifications_enabled FROM users_info WHERE username = %s", (current_user,))
        updated_value = cursor.fetchone()
        if updated_value:
            browser_status = "ENABLED" if updated_value[0] else "DISABLED"
            logger.info(f"✅ Profile updated successfully. browser_notifications_enabled is now: {browser_status}")

        return {"message": "Profile updated successfully"}

    except Error as e:
        logger.error(f"Database error updating profile: {e}")
        raise HTTPException(status_code=500, detail="Database error")
    finally:
        cursor.close()
        conn.close()
@app.post("/auth/refresh-token")
async def refresh_token_endpoint(request: dict):
    """Issue a new access token using a valid refresh token"""
    refresh_token = request.get("refresh_token")
    if not refresh_token:
        raise HTTPException(status_code=400, detail="Refresh token required")
    
    username = verify_refresh_token(refresh_token)
    if username is None:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    
    # Create new access token
    access_token = create_access_token({"sub": username})
    return {"access_token": access_token}
@app.post("/api/community/alerts/subscribe")
async def subscribe_to_alerts(
    subscription_data: dict,
    current_user: str = Depends(get_current_user)
):
    """Subscribe to safety alerts - UPDATED FOR BROWSER NOTIFICATIONS"""
    conn = None
    cursor = None
    try:
        print(f"🔔 Subscription request from user: {current_user}")
        print(f"📦 Subscription data: {subscription_data}")
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Get user info
        cursor.execute("SELECT id, email FROM users_info WHERE username = %s", (current_user,))
        user = cursor.fetchone()
        
        if not user:
            print("❌ User not found")
            raise HTTPException(status_code=404, detail="User not found")
        
        user_id = cast(Dict[str, Any], user).get("id")
        print(f"👤 User ID: {user_id}")
        
        # Extract and validate fields for new schema
        alert_types = subscription_data.get('alert_types', ['crime', 'safety', 'emergency'])
        areas = subscription_data.get('areas', ['General'])
        radius = float(subscription_data.get('radius', 5.0))
        # UPDATE NOTIFICATION TYPES TO USE BROWSER INSTEAD OF SMS
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

        existing_subscription = cursor.fetchone()

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
                cast(Dict[str, Any], existing_subscription).get("id")
            ))
            subscription_id = cast(Dict[str, Any], existing_subscription).get("id")
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
                "notification_types": notification_types,  # ADD THIS
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
     

@app.post("/api/alerts/check-location")
async def check_location_for_alerts(
    request: LocationAlertRequest,
    current_user: str = Depends(get_username_from_token)
):
    """Check location for immediate alerts - UPDATED VERSION"""
    try:
        print(f"📍 Checking location alerts for user: {current_user}")
        print(f"📌 Location: {request.latitude}, {request.longitude}")
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Get user info - REMOVE SMS FIELDS
        cursor.execute("""
            SELECT id, username, email, browser_notifications_enabled, 
                   alert_radius, home_area, work_area
            FROM users_info WHERE username = %s
        """, (current_user,))
        user = cursor.fetchone()
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        user_dict = cast(Dict[str, Any], user)
        user_id = user_dict["id"]
        alert_radius = float(user_dict.get("alert_radius", 5.0))
        
        # Check location risk using your existing function
        risk_assessment = await check_location_risk(
            user_id, 
            request.latitude, 
            request.longitude,
            alert_radius
        )
        
        print(f"📊 Risk assessment: {risk_assessment}")
        
        # Send immediate alert if high risk
        if risk_assessment["is_high_risk"] and request.check_immediate:
            alert = RiskZoneAlert(
                user_id=user_id,
                username=user_dict.get("username", ""),
                email=user_dict.get("email", ""),
                # REMOVE PHONE FIELD
                latitude=request.latitude,
                longitude=request.longitude,
                address=request.address or f"Current location ({request.latitude}, {request.longitude})",
                risk_level=risk_assessment["risk_level"],
                safety_score=risk_assessment["safety_score"],
                high_risk_crimes=risk_assessment["high_risk_crimes"],
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
            
@app.get("/api/community/stats")
async def get_community_stats():
    """Get community statistics - REAL IMPLEMENTATION"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Get real stats from database
        stats = {
            "total_users": 0,
            "active_alerts": 0,
            "community_patrols": 0,
            "safety_rating": 4.5
        }
        
        # Total users
        cursor.execute("SELECT COUNT(*) as count FROM users_info WHERE role = 'user'")
        users_result = cursor.fetchone()
        stats["total_users"] = users_result.get("count", 0) if users_result else 0
        
        # Active alerts (last 24 hours)
        cursor.execute("""
            SELECT COUNT(*) as count FROM alert_notifications
            WHERE created_at >= DATE_SUB(NOW(), INTERVAL 24 HOUR)
        """)
        alerts_result = cursor.fetchone()
        stats["active_alerts"] = alerts_result.get("count", 0) if alerts_result else 0
        
        # Community patrols (last 7 days)
        cursor.execute("""
            SELECT COUNT(*) as count FROM patrol_requests
            WHERE created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)
        """)
        patrols_result = cursor.fetchone()
        stats["community_patrols"] = patrols_result.get("count", 0) if patrols_result else 0
        
        return {"stats": stats}
        
    except Exception as e:
        logger.error(f"Error getting community stats: {e}")
        return {
            "stats": {
                "total_users": 1500,
                "active_alerts": 23,
                "community_patrols": 45,
                "safety_rating": 4.5
            }
        }
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()
@app.get("/api/alerts/status")
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
        
        result = cursor.fetchone()
        
        if not result:
            raise HTTPException(status_code=404, detail="User not found")
        
        preferences = json.loads(cast(Dict[str, Any], result).get("alert_preferences", "{}"))
        
        return {
            "is_subscribed": cast(Dict[str, Any], result)["active_subscriptions"] > 0,
            "preferences": preferences,
            "alert_radius": cast(Dict[str, Any], result)["alert_radius"],
            "monitor_live_location": bool(cast(Dict[str, Any], result)["monitor_live_location"]),
            "monitor_saved_locations": preferences.get('monitor_saved_locations', True)
        }
        
    except Error as e:
        logger.error(f"Database error getting alert status: {e}")
        raise HTTPException(status_code=500, detail="Failed to get alert status")
    finally:
        cursor.close()
        conn.close()

@app.post("/api/alerts/unsubscribe")
async def unsubscribe_from_alerts(current_user: str = Depends(get_username_from_token)):
    """Unsubscribe from all alerts"""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        # Get user ID
        cursor.execute("SELECT id FROM users_info WHERE username = %s", (current_user,))
        user = cursor.fetchone()
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        user_id = cast(Dict[str, Any], user).get("id")
        
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
        
    except Error as e:
        logger.error(f"Database error unsubscribing from alerts: {e}")
        raise HTTPException(status_code=500, detail="Failed to unsubscribe")
    finally:
        cursor.close()
        conn.close()

@app.get("/auth/2fa-status")
def get_2fa_status(current_user: str = Depends(get_username_from_token)):
    """Get the current 2FA status for the authenticated user"""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT id FROM users_info WHERE username = %s", (current_user,))
        user = cursor.fetchone()
        if not user:
            raise HTTPException(status_code=401, detail="User not found")

        user_id = cast(Dict[str, Any], user).get("id")
        is_enabled = is_2fa_enabled(user_id)

        return {"enabled": is_enabled}

    except Error as e:
        logger.error(f"Database error getting 2FA status: {e}")
        raise HTTPException(status_code=500, detail="Database error")
    finally:
        cursor.close()
        conn.close()

@app.post("/auth/generate-2fa")
def generate_2fa_secret(current_user: str = Depends(get_username_from_token)):
    """Generate a new 2FA secret and return the QR code URI"""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT id, email FROM users_info WHERE username = %s", (current_user,))
        user = cursor.fetchone()
        if not user:
            raise HTTPException(status_code=401, detail="User not found")

        user_id = cast(Dict[str, Any], user).get("id")
        email = cast(Dict[str, Any], user).get("email")

        # Check if 2FA is already enabled
        if is_2fa_enabled(user_id):
            raise HTTPException(status_code=400, detail="2FA is already enabled for this account")

        # Generate new secret
        secret = generate_2fa_secret_util()
        uri = get_2fa_uri(secret, email, "CrimeVision")

        return {
            "secret": secret,
            "uri": uri,
            "message": "Scan the QR code with your authenticator app and use the code to enable 2FA"
        }

    except Error as e:
        logger.error(f"Database error generating 2FA secret: {e}")
        raise HTTPException(status_code=500, detail="Database error")
    finally:
        cursor.close()
        conn.close()

@app.post("/auth/enable-2fa")
def enable_2fa_endpoint(
    request: dict,
    current_user: str = Depends(get_username_from_token)
):
    """Enable 2FA for the authenticated user"""
    code = request.get("code")
    secret = request.get("secret")

    if not code or not secret:
        raise HTTPException(status_code=400, detail="Code and secret are required")

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT id FROM users_info WHERE username = %s", (current_user,))
        user = cursor.fetchone()
        if not user:
            raise HTTPException(status_code=401, detail="User not found")

        user_id = cast(Dict[str, Any], user).get("id")

        # Check if 2FA is already enabled
        if is_2fa_enabled(user_id):
            raise HTTPException(status_code=400, detail="2FA is already enabled for this account")

        # Verify the code
        if not verify_2fa_code(secret, code):
            raise HTTPException(status_code=400, detail="Invalid verification code")

        # Enable 2FA
        enable_2fa(user_id, secret)

        log_user_activity(
            activity_type="2fa_enabled",
            username=current_user,
            user_id=user_id,
            activity_details={"message": "Two-factor authentication enabled successfully."},
        )

        return {"message": "2FA enabled successfully"}

    except Error as e:
        logger.error(f"Database error enabling 2FA: {e}")
        raise HTTPException(status_code=500, detail="Database error")
    finally:
        cursor.close()
        conn.close()

@app.post("/auth/disable-2fa")
def disable_2fa_endpoint(
    request: dict,
    current_user: str = Depends(get_username_from_token)
):
    """Disable 2FA for the authenticated user"""
    code = request.get("code")

    if not code:
        raise HTTPException(status_code=400, detail="Verification code is required")

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT id FROM users_info WHERE username = %s", (current_user,))
        user = cursor.fetchone()
        if not user:
            raise HTTPException(status_code=401, detail="User not found")

        user_id = cast(Dict[str, Any], user).get("id")

        # Check if 2FA is enabled
        if not is_2fa_enabled(user_id):
            raise HTTPException(status_code=400, detail="2FA is not enabled for this account")

        # Get the secret to verify the code
        secret = get_user_2fa_secret(user_id)
        if not secret:
            raise HTTPException(status_code=400, detail="2FA secret not found")

        # Verify the code
        if not verify_2fa_code(secret, code):
            raise HTTPException(status_code=400, detail="Invalid verification code")

        # Disable 2FA
        disable_2fa(user_id)

        log_user_activity(
            activity_type="2fa_disabled",
            username=current_user,
            user_id=user_id,
            activity_details={"message": "Two-factor authentication disabled successfully."},
        )

        return {"message": "2FA disabled successfully"}

    except Error as e:
        logger.error(f"Database error disabling 2FA: {e}")
        raise HTTPException(status_code=500, detail="Database error")
    finally:
        cursor.close()
        conn.close()

from fastapi import UploadFile, File

@app.post("/auth/upload-profile-photo")
async def upload_profile_photo(
    file: UploadFile = File(...),
    current_user: str = Depends(get_username_from_token)
):
    """Upload profile photo and update user's profile_picture field"""
    # Save file to local directory 'profile_photos' with unique filename
    upload_dir = os.path.join(os.path.dirname(__file__), "profile_photos")
    os.makedirs(upload_dir, exist_ok=True)

    filename = f"{current_user}_{int(datetime.now().timestamp())}_{file.filename}"
    file_path = os.path.join(upload_dir, filename)

    try:
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)

        # Save relative path or URL to DB
        relative_path = f"profile_photos/{filename}"

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE users_info SET profile_picture = %s WHERE username = %s",
            (relative_path, current_user)
        )
        conn.commit()

        return {"message": "Profile photo uploaded successfully", "profile_picture": relative_path}

    except Exception as e:
        logger.error(f"Error uploading profile photo: {e}")
        raise HTTPException(status_code=500, detail="Failed to upload profile photo")

# Crime endpoints
@app.get("/api/areas")
def get_areas():
    """Get all unique areas from the crimes table (areas with crime data for prediction)"""
    conn, cursor = None, None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Get areas from crimes table only (since model is trained on crime data)
        cursor.execute("SELECT DISTINCT area FROM crimes WHERE area IS NOT NULL AND area != '' ORDER BY area")
        crime_areas = cursor.fetchall()

        areas_list = [cast(Dict[str, Any], row)['area'] for row in crime_areas if cast(Dict[str, Any], row)['area']]
        logger.info(f"Retrieved {len(areas_list)} unique areas from crimes data")
        return {"areas": areas_list}

    except Error as e:
        logger.error(f"MySQL error: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve areas")
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()

@app.get("/api/crime-types")
def get_crime_types():
    """Get all unique crime types from the database"""
    conn, cursor = None, None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT DISTINCT crime_type FROM crimes ORDER BY crime_type")
        rows = cursor.fetchall()

        # Cast rows to proper dictionary type for Pylance
        crime_types = [cast(Dict[str, Any], row)['crime_type'] for row in rows if cast(Dict[str, Any], row)['crime_type']]
        logger.info(f"Retrieved {len(crime_types)} unique crime types")
        return {"crime_types": crime_types}

    except Error as e:
        logger.error(f"MySQL error: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve crime types")
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()

@app.get("/api/crimes", response_model=List[Crime])
def get_crimes(
    area: Optional[str] = Query(None, description="Filter by area", max_length=100),
    crime_type: Optional[str] = Query(None, description="Filter by crime type", max_length=50),
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)", regex=r'^\d{4}-\d{2}-\d{2}$'),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)", regex=r'^\d{4}-\d{2}-\d{2}$'),
    limit: int = Query(1000, description="Maximum number of records to return", ge=1, le=10000)
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
            SELECT id, area, crime_type, crime_date, latitude, longitude, risk_level
            FROM crimes
            WHERE 1=1
        """
        params: list[Any] = []

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

        query += " ORDER BY crime_date DESC, id DESC LIMIT %s"
        params.append(limit)

        cursor.execute(query, params)
        rows = cursor.fetchall()

        crimes_list: List[Crime] = []
        for row in rows:
            try:
                # Check if coordinates are valid (not None)
                latitude = cast(Dict[str, Any], row).get("latitude")
                longitude = cast(Dict[str, Any], row).get("longitude")

                # Skip crimes without valid coordinates
                if latitude is None or longitude is None:
                    logger.warning(f"Skipping crime {cast(Dict[str, Any], row)['id']} - missing coordinates")
                    continue

                crime_record = Crime(
                    id=int(cast(Dict[str, Any], row)["id"]),
                    area=cast(Dict[str, Any], row).get("area", "Unknown"),
                    type=cast(Dict[str, Any], row).get("crime_type", "Unknown"),
                    date=str(cast(Dict[str, Any], row).get("crime_date", "Unknown")),
                    coordinates=[
                        float(latitude),
                        float(longitude)
                    ],
                    risk_level=cast(Dict[str, Any], row).get("risk_level", "Unknown")
                )
                crimes_list.append(crime_record)
            except Exception as e:
                logger.warning(f"Skipping bad row: {e}")
                continue

        logger.info(f"Retrieved {len(crimes_list)} records")
        return crimes_list

    except Error as e:
        logger.error(f"MySQL error: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve crime data")
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()

# Helper to find best matching encoder class (case-insensitive + substring + fuzzy)
def find_best_match(value: str, le) -> Optional[str]:
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
    # For areas, check if the input contains or is contained by known areas
    for cls in le.classes_:
        cls_lower = cls.lower()
        value_lower = value_stripped.lower()

        # Check if one is a substring of the other (with some length threshold)
        if (len(value_lower) > 3 and value_lower in cls_lower) or \
           (len(cls_lower) > 3 and cls_lower in value_lower):
            return cls

    # 3. Fuzzy matching with higher threshold
    matches = difflib.get_close_matches(value_stripped, le.classes_, n=1, cutoff=0.7)
    if matches:
        return matches[0]

    # 4. Return None instead of defaulting to wrong area
    return None

def calculate_risk_percentage(risk_level: str, probabilities: List[float], label_encoder) -> int:
    """Calculate meaningful risk percentage based on predicted class"""
    risk_ranges = {
        "High": (70, 100),    # High risk: 70-100%
        "Medium": (30, 70),   # Medium risk: 30-70%
        "Low": (0, 30)        # Low risk: 0-30%
    }

    # Get the probability of the predicted class
    try:
        class_index = list(label_encoder.classes_).index(risk_level)
        class_probability = probabilities[class_index]
    except (ValueError, IndexError):
        # Fallback if class not found
        class_probability = max(probabilities)

    # Map to the appropriate range
    min_range, max_range = risk_ranges.get(risk_level, (30, 70))
    risk_percentage = int(min_range + (class_probability * (max_range - min_range)))

    return min(100, max(0, risk_percentage))  # Ensure within 0-100%

@app.post("/api/predict-risk")
def predict_risk(request: PredictRiskRequest):
    """Predict risk level for given area, crime type, and date"""
    if not model or not le_area or not le_crime or not le_risk:
        logger.error("ML model or encoders not loaded properly")
        raise HTTPException(status_code=500, detail="ML model not loaded")

    try:
        area = request.area
        crime_type = request.crime_type
        date = request.date

        # Use current date if not provided
        if not date:
            date = datetime.now().strftime('%Y-%m-%d')

        if not validate_date_format(date):
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")

        parsed_date = datetime.strptime(date, '%Y-%m-%d')
        year = int(parsed_date.year)
        month = int(parsed_date.month)
        day = int(parsed_date.day)
        weekday = int(parsed_date.weekday())  # 0=Monday
        day_of_year = int(parsed_date.timetuple().tm_yday)
        is_weekend = 1 if weekday in [5, 6] else 0

        logger.info(f"Raw input area: '{area}', crime_type: '{crime_type}', date: {date}")

        # Best-effort mapping to encoder classes
        matched_area = find_best_match(area, le_area)
        matched_crime = find_best_match(crime_type, le_crime)

        area_known = matched_area is not None
        crime_known = matched_crime is not None

        logger.info(f"Matched area: {matched_area}, matched_crime: {matched_crime}")
        logger.info(f"le_area.classes_[:5]: {le_area.classes_[:5]}")
        logger.info(f"le_crime.classes_[:5]: {le_crime.classes_[:5]}")
        logger.info(f"area_known: {area_known}, crime_known: {crime_known}")

        if not area_known or not crime_known:
            # Provide more specific messaging
            message_parts = []
            if not area_known:
                message_parts.append(f"Area '{area}'")
            if not crime_known:
                message_parts.append(f"crime type '{crime_type}'")

            message = f"{' and '.join(message_parts)} not found in training data. Showing default risk level."
            return {
                "risk_level": "Medium",
                "risk_percentage": 50,
                "confidence": 0.5,
                "message": message,
                "is_estimated": True
            }

        # Encode categorical variables
        try:
            area_enc = int(le_area.transform([matched_area])[0])
            crime_type_enc = int(le_crime.transform([matched_crime])[0])
        except Exception as e:
            logger.error(f"Encoding error: {e}")
            raise HTTPException(status_code=500, detail="Encoding error for categorical variables")

        # Create feature DataFrame with ALL 8 features
        features_df = pd.DataFrame(
            [[area_enc, crime_type_enc, year, month, day, weekday, day_of_year, is_weekend]],
            columns=['area_enc', 'crime_type_enc', 'year', 'month', 'day', 'weekday', 'day_of_year', 'is_weekend']
        ).astype(int)

        # Debug log the actual features passed to model
        logger.info(f"Features to model: {features_df.iloc[0].to_list()} (dtypes: {features_df.dtypes.to_dict()})")

        # Make prediction & probability
        pred = model.predict(features_df)[0]
        pred_proba = model.predict_proba(features_df)[0]

        # Map model output back to label
        try:
            risk_level = le_risk.inverse_transform([pred])[0]
        except Exception as e:
            logger.error(f"Error decoding risk label: {e}")
            raise HTTPException(status_code=500, detail="Failed to decode predicted risk label")

        # CORRECT RISK PERCENTAGE CALCULATION
        risk_level_cap = str(risk_level).capitalize()
        risk_percentage = calculate_risk_percentage(risk_level_cap, pred_proba.tolist(), le_risk)
        confidence = float(max(pred_proba))

        logger.info(f"Prediction result: risk_level={risk_level_cap}, risk_percentage={risk_percentage}%, probabilities={pred_proba.tolist()}, confidence={confidence}")

        return {
            "risk_level": risk_level_cap,
            "risk_percentage": risk_percentage,
            "confidence": confidence
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Prediction error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Prediction failed")


@app.post("/api/crimes")
def create_crime(crime: CrimeCreate):
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

        # Default risk values (in case ML not available or encoding fails)
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

                    logger.info(f"create_crime prediction: risk_level={risk_level}, "
                                f"probabilities={pred_proba.tolist()}, confidence={confidence}")

                except Exception as e:
                    logger.error(f"Encoding or prediction error in create_crime: {e}", exc_info=True)
        else:
            logger.warning("ML model not loaded - storing default Medium risk")

        # Save to database using MySQL connection pattern
        conn = get_db_connection()
        cursor = conn.cursor()
        
        insert_query = """
            INSERT INTO crimes (area, crime_type, crime_date, latitude, longitude, risk_level, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        
        # Use provided coordinates or default to None
        latitude = crime.latitude
        longitude = crime.longitude
        created_at = datetime.now()
        
        cursor.execute(insert_query, (
            area,
            crime_type,
            date,
            latitude,
            longitude,
            risk_level.capitalize() if risk_level else "Medium",
            created_at
        ))
        
        conn.commit()
        crime_id = cursor.lastrowid
        
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

# Helper function to ensure admins table schema exists
def ensure_admins_table_schema(cursor):
    """Ensure the admins table exists with required columns."""
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS admins (
            id INT AUTO_INCREMENT PRIMARY KEY,
            username VARCHAR(100) NOT NULL UNIQUE,
            first_name VARCHAR(50),
            last_name VARCHAR(50),
            email VARCHAR(100) NOT NULL UNIQUE,
            password_hash VARCHAR(255) NOT NULL,
            role VARCHAR(20) NOT NULL DEFAULT 'admin',
            department VARCHAR(20),
            permissions TEXT,
            phone VARCHAR(20),
            address VARCHAR(255),
            created_at DATETIME NOT NULL,
            status VARCHAR(20) DEFAULT 'active'
        )
    """)

# Admin endpoints
@app.post("/admin/register", response_model=AdminResponse)
def register_admin(admin: AdminRegister, current_user: str = Depends(get_username_from_token)):
    """Register a new admin with permissions"""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        # Check if current user is super admin
        cursor.execute("SELECT role FROM users_info WHERE username = %s", (current_user,))
        user = cursor.fetchone()
        if not user or cast(Dict[str, Any], user).get("role") != "superadmin":
            raise HTTPException(status_code=403, detail="Only super admins can register new admins")

        ensure_admins_table_schema(cursor)

        # Check if email already exists in users_info or admins table
        cursor.execute("SELECT id FROM users_info WHERE email = %s", (admin.email,))
        if cursor.fetchone():
            raise HTTPException(status_code=400, detail="Email already exists")
        cursor.execute("SELECT id FROM admins WHERE email = %s", (admin.email,))
        if cursor.fetchone():
            raise HTTPException(status_code=400, detail="Email already exists")

        # Generate username from name
        first_name, last_name = admin.name.split(" ", 1) if " " in admin.name else (admin.name, "")
        username = generate_username(first_name, last_name)

        # Hash password
        password_hash = get_password_hash(admin.password)

        # Insert admin user into users_info table
        cursor.execute(
            """INSERT INTO users_info
               (username, first_name, last_name, email, password_hash, role, permissions, home_area, work_area, alert_radius, activity_logs, created_at)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
            (username, first_name, last_name, admin.email, password_hash, "admin",
             json.dumps(admin.permissions), None, None, 5, json.dumps([]), datetime.now())
        )

        # Insert admin user into admins table
        cursor.execute(
            """INSERT INTO admins
               (username, first_name, last_name, email, password_hash, role, permissions, phone, address, created_at)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
            (username, first_name, last_name, admin.email, password_hash, "admin",
             json.dumps(admin.permissions), admin.phone, admin.address, datetime.now())
        )
        admin_id = cast(int, cursor.lastrowid)
        conn.commit()

        return AdminResponse(
            id=admin_id,
            username=username,
            name=admin.name,
            email=admin.email,
            department=admin.department,
            permissions=admin.permissions,
            phone=admin.phone,
            address=admin.address,
            created_at=datetime.now().isoformat(),
            status="active"
        )

    except Error as e:
        logger.error(f"Database error during admin registration: {e}")
        raise HTTPException(status_code=500, detail="Database error")
    finally:
        cursor.close()
        conn.close()

@app.get("/admin/list")
def get_admins(current_user: str = Depends(get_username_from_token)):
    """Get list of all admins"""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        # Check if current user is super admin
        cursor.execute("SELECT role FROM users_info WHERE username = %s", (current_user,))
        user = cursor.fetchone()
        role_value = cast(Dict[str, Any], user).get("role") if user else None
        if role_value != "superadmin":
            raise HTTPException(status_code=403, detail="Only super admins can view admin list")

        ensure_admins_table_schema(cursor)

        cursor.execute(
            """SELECT id, username, CONCAT(first_name, ' ', last_name) as name, email,
                      role, permissions, phone, address, created_at
               FROM admins
               ORDER BY created_at DESC"""
        )
        admins = cursor.fetchall()

        admin_list = []
        for admin in admins:
            raw_permissions = cast(Dict[str, Any], admin).get("permissions")
            if isinstance(raw_permissions, list):
                permissions = raw_permissions
            elif isinstance(raw_permissions, str) and raw_permissions.strip():
                try:
                    permissions = json.loads(raw_permissions)
                except (json.JSONDecodeError, TypeError):
                    permissions = []
            else:
                permissions = []

            created_at_value = cast(Dict[str, Any], admin).get("created_at")
            if created_at_value is not None and hasattr(created_at_value, "isoformat"):
                created_at_str = created_at_value.isoformat()
            elif isinstance(created_at_value, str):
                created_at_str = created_at_value
            else:
                created_at_str = None

            admin_list.append({
                "id": cast(Dict[str, Any], admin)["id"],
                "username": cast(Dict[str, Any], admin)["username"],
                "name": cast(Dict[str, Any], admin)["name"],
                "email": cast(Dict[str, Any], admin)["email"],
                "department": "Admin",  # Default department
                "permissions": permissions,
                "phone": cast(Dict[str, Any], admin).get("phone"),
                "address": cast(Dict[str, Any], admin).get("address"),
                "created_at": created_at_str,
                "status": "active"
            })

        return {"admins": admin_list}

    except Error as e:
        logger.error(f"Database error getting admins: {e}")
        raise HTTPException(status_code=500, detail="Database error")
    finally:
        cursor.close()
        conn.close()

@app.get("/admin/stats")
def get_admin_stats(current_user: str = Depends(get_username_from_token)):
    """Get admin dashboard statistics"""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        # Check if current user is super admin
        cursor.execute("SELECT role FROM users_info WHERE username = %s", (current_user,))
        user = cursor.fetchone()
        if not user or cast(Dict[str, Any], user).get("role") != "superadmin":
            raise HTTPException(status_code=403, detail="Access denied")

        ensure_admins_table_schema(cursor)

        stats = {}

        # Total crimes
        cursor.execute("SELECT COUNT(*) as total_crimes FROM crimes")
        total_crimes_result = cursor.fetchone()
        stats["total_crimes"] = cast(Dict[str, Any], total_crimes_result)["total_crimes"]

        # Crimes by risk level
        cursor.execute("SELECT risk_level, COUNT(*) as count FROM crimes GROUP BY risk_level")
        risk_stats = cursor.fetchall()
        stats["crimes_by_risk"] = {cast(Dict[str, Any], row)["risk_level"]: cast(Dict[str, Any], row)["count"] for row in risk_stats}

        # Total users
        cursor.execute("SELECT COUNT(*) as total_users FROM users_info WHERE role = 'user'")
        total_users_result = cursor.fetchone()
        stats["total_users"] = cast(Dict[str, Any], total_users_result)["total_users"]

        # Total admins
        cursor.execute("SELECT COUNT(*) as total_admins FROM admins WHERE role = 'admin'")
        total_admins_result = cursor.fetchone()
        stats["total_admins"] = cast(Dict[str, Any], total_admins_result)["total_admins"]

        # Recent crimes (last 30 days)
        thirty_days_ago = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        cursor.execute("SELECT COUNT(*) as recent_crimes FROM crimes WHERE crime_date >= %s", (thirty_days_ago,))
        recent_crimes_result = cursor.fetchone()
        stats["recent_crimes"] = cast(Dict[str, Any], recent_crimes_result)["recent_crimes"]

        # Crimes by area (top 10)
        cursor.execute("""
            SELECT area, COUNT(*) as count
            FROM crimes
            GROUP BY area
            ORDER BY count DESC
            LIMIT 10
        """)
        area_stats = cursor.fetchall()
        stats["crimes_by_area"] = {cast(Dict[str, Any], row)["area"]: cast(Dict[str, Any], row)["count"] for row in area_stats}

        return stats

    except Error as e:
        logger.error(f"Database error getting stats: {e}")
        raise HTTPException(status_code=500, detail="Database error")
    finally:
        cursor.close()
        conn.close()

@app.get("/admin/notifications")
def get_admin_notifications(current_user: str = Depends(get_username_from_token)):
    """Get admin notifications"""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        # Check if current user is super admin or admin
        cursor.execute("SELECT role FROM users_info WHERE username = %s", (current_user,))
        user = cursor.fetchone()
        if not user or cast(Dict[str, Any], user).get("role") not in ["superadmin", "admin"]:
            raise HTTPException(status_code=403, detail="Access denied")

        ensure_admins_table_schema(cursor)

        notifications = []

        # High risk crimes in last 24 hours
        yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        cursor.execute(
            "SELECT COUNT(*) as high_risk_count FROM crimes WHERE risk_level = 'High' AND crime_date >= %s",
            (yesterday,)
        )
        high_risk_result = cursor.fetchone()
        high_risk = cast(Dict[str, Any], high_risk_result)["high_risk_count"]
        if high_risk > 0:
            notifications.append({
                "id": 1,
                "type": "warning",
                "title": "High Risk Crimes",
                "message": f"{high_risk} high-risk crimes reported in the last 24 hours",
                "timestamp": datetime.now().isoformat()
            })

        # New user registrations today
        today = datetime.now().strftime('%Y-%m-%d')
        cursor.execute(
            "SELECT COUNT(*) as new_users FROM users_info WHERE DATE(created_at) = %s AND role = 'user'",
            (today,)
        )
        new_users_result = cursor.fetchone()
        new_users = cast(Dict[str, Any], new_users_result)["new_users"]
        if new_users > 0:
            notifications.append({
                "id": 2,
                "type": "info",
                "title": "New User Registrations",
                "message": f"{new_users} new users registered today",
                "timestamp": datetime.now().isoformat()
            })

        # System status
        notifications.append({
            "id": 3,
            "type": "success",
            "title": "System Status",
            "message": "All systems operational",
            "timestamp": datetime.now().isoformat()
        })

        return {"notifications": notifications}

    except Error as e:
        logger.error(f"Database error getting notifications: {e}")
        raise HTTPException(status_code=500, detail="Database error")
    finally:
        cursor.close()
        conn.close()

@app.get("/admin/users")
def get_users(
    current_user: str = Depends(get_username_from_token),
    search: Optional[str] = Query(None, description="Search by username, first name, or email"),
    role: Optional[str] = Query(None, description="Filter by role"),
    limit: int = Query(50, description="Maximum number of records to return", ge=1, le=1000),
    offset: int = Query(0, description="Number of records to skip", ge=0)
):
    """Get list of users with filtering and pagination"""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        # Check if current user is super admin
        cursor.execute("SELECT role FROM users_info WHERE username = %s", (current_user,))
        user = cursor.fetchone()
        if not user or cast(Dict[str, Any], user).get("role") not in ["superadmin", "admin"]:
            raise HTTPException(status_code=403, detail="Access denied")

        query = """
            SELECT id, username, first_name, last_name, email, role, permissions,
                   home_area, work_area, alert_radius, created_at, activity_logs
            FROM users_info
            WHERE 1=1
        """
        params = []

        if search:
            query += " AND (username LIKE %s OR first_name LIKE %s OR last_name LIKE %s OR email LIKE %s)"
            search_param = f"%{search}%"
            params.extend([search_param] * 4)

        if role:
            query += " AND role = %s"
            params.append(role)

        query += " ORDER BY created_at DESC LIMIT %s OFFSET %s"
        params.extend([limit, offset])

        cursor.execute(query, params)
        users = cursor.fetchall()

        # Get total count for pagination
        count_query = "SELECT COUNT(*) as total FROM users_info WHERE 1=1"
        count_params = []
        if search:
            count_query += " AND (username LIKE %s OR first_name LIKE %s OR last_name LIKE %s OR email LIKE %s)"
            count_params.extend([search_param] * 4)
        if role:
            count_query += " AND role = %s"
            count_params.append(role)

        cursor.execute(count_query, count_params)
        total_result = cursor.fetchone()
        total = cast(Dict[str, Any], total_result)["total"]

        # Format users data
        users_list = []
        for user in users:
            raw_permissions = cast(Dict[str, Any], user).get("permissions")
            raw_activity_logs = cast(Dict[str, Any], user).get("activity_logs")

            if isinstance(raw_permissions, list):
                permissions = raw_permissions
            elif isinstance(raw_permissions, str) and raw_permissions.strip():
                try:
                    permissions = json.loads(raw_permissions)
                except (json.JSONDecodeError, TypeError):
                    permissions = []
            else:
                permissions = []

            if isinstance(raw_activity_logs, list):
                activity_logs = raw_activity_logs
            elif isinstance(raw_activity_logs, str) and raw_activity_logs.strip():
                try:
                    activity_logs = json.loads(raw_activity_logs)
                except (json.JSONDecodeError, TypeError):
                    activity_logs = []
            else:
                activity_logs = []

            users_list.append({
                "id": cast(Dict[str, Any], user)["id"],
                "username": cast(Dict[str, Any], user)["username"],
                "first_name": cast(Dict[str, Any], user)["first_name"],
                "last_name": cast(Dict[str, Any], user)["last_name"],
                "email": cast(Dict[str, Any], user)["email"],
                "role": cast(Dict[str, Any], user)["role"],
                "permissions": permissions,
                "home_area": cast(Dict[str, Any], user)["home_area"],
                "work_area": cast(Dict[str, Any], user)["work_area"],
                "alert_radius": cast(Dict[str, Any], user)["alert_radius"],
                "created_at": cast(Dict[str, Any], user)["created_at"].isoformat() if cast(Dict[str, Any], user)["created_at"] is not None and hasattr(cast(Dict[str, Any], user)["created_at"], "isoformat") else None,
                "activity_logs": activity_logs
            })

        return {
            "users": users_list,
            "total": total,
            "limit": limit,
            "offset": offset
        }

    except Error as e:
        logger.error(f"Database error getting users: {e}")
        raise HTTPException(status_code=500, detail="Database error")
    finally:
        cursor.close()
        conn.close()

@app.post("/admin/user-bulk")
def bulk_user_actions(
    action: str = Query(..., description="Action to perform: suspend, activate, delete"),
    user_ids: List[int] = Query(..., description="List of user IDs to perform action on"),
    current_user: str = Depends(get_username_from_token)
):
    """Perform bulk actions on users (suspend, activate, delete)"""
    if action not in ["suspend", "activate", "delete"]:
        raise HTTPException(status_code=400, detail="Invalid action")

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        # Check if current user is super admin
        cursor.execute("SELECT role FROM users_info WHERE username = %s", (current_user,))
        user = cursor.fetchone()
        if not user or cast(Dict[str, Any], user).get("role") != "superadmin":
            raise HTTPException(status_code=403, detail="Only super admins can perform bulk actions")

        if not user_ids:
            raise HTTPException(status_code=400, detail="No user IDs provided")

        # Log the bulk action
        cursor.execute(
            "INSERT INTO audit_logs (admin_username, action, target_type, details) VALUES (%s, %s, %s, %s)",
            (current_user, f"bulk_{action}", "user", json.dumps({"user_ids": user_ids, "count": len(user_ids)}))
        )

        if action == "delete":
            # Delete users
            format_strings = ','.join(['%s'] * len(user_ids))
            cursor.execute(f"DELETE FROM users_info WHERE id IN ({format_strings})", user_ids)
        else:
            # Suspend or activate (set role to inactive/active)
            new_role = "inactive" if action == "suspend" else "user"
            format_strings = ','.join(['%s'] * len(user_ids))
            cursor.execute(f"UPDATE users_info SET role = %s WHERE id IN ({format_strings})", [new_role] + user_ids)

        conn.commit()

        return {"message": f"Successfully {action}d {len(user_ids)} users"}

    except Error as e:
        logger.error(f"Database error in bulk action: {e}")
        raise HTTPException(status_code=500, detail="Database error")
    finally:
        cursor.close()
        conn.close()

@app.put("/admin/user-roles")
def update_user_roles(
    user_id: int = Query(..., description="User ID to update"),
    permissions: List[str] = Query(..., description="New permissions list"),
    current_user: str = Depends(get_username_from_token)
):
    """Update user permissions"""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        # Check if current user is super admin
        cursor.execute("SELECT role FROM users_info WHERE username = %s", (current_user,))
        user = cursor.fetchone()
        if not user or cast(Dict[str, Any], user).get("role") != "superadmin":
            raise HTTPException(status_code=403, detail="Only super admins can update user roles")

        # Update permissions
        cursor.execute(
            "UPDATE users_info SET permissions = %s WHERE id = %s",
            (json.dumps(permissions), user_id)
        )

        # Log the action
        cursor.execute(
            "INSERT INTO audit_logs (admin_username, action, target_type, target_id, details) VALUES (%s, %s, %s, %s, %s)",
            (current_user, "update_permissions", "user", user_id, json.dumps({"permissions": permissions}))
        )

        conn.commit()

        return {"message": "User permissions updated successfully"}

    except Error as e:
        logger.error(f"Database error updating user roles: {e}")
        raise HTTPException(status_code=500, detail="Database error")
    finally:
        cursor.close()
        conn.close()

@app.get("/admin/audit-logs")
def get_audit_logs(
    current_user: str = Depends(get_username_from_token),
    action: Optional[str] = Query(None, description="Filter by action"),
    target_type: Optional[str] = Query(None, description="Filter by target type"),
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    limit: int = Query(100, description="Maximum number of records to return", ge=1, le=1000)
):
    """Get admin activity audit logs"""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        # Check if current user is super admin
        cursor.execute("SELECT role FROM users_info WHERE username = %s", (current_user,))
        user = cursor.fetchone()
        if not user or cast(Dict[str, Any], user).get("role") != "superadmin":
            raise HTTPException(status_code=403, detail="Only super admins can view audit logs")

        query = "SELECT * FROM audit_logs WHERE 1=1"
        params = []

        if action:
            query += " AND action = %s"
            params.append(action)

        if target_type:
            query += " AND target_type = %s"
            params.append(target_type)

        if start_date:
            query += " AND DATE(created_at) >= %s"
            params.append(start_date)

        if end_date:
            query += " AND DATE(created_at) <= %s"
            params.append(end_date)

        query += " ORDER BY created_at DESC LIMIT %s"
        params.append(limit)

        cursor.execute(query, params)
        logs = cursor.fetchall()

        logs_list = []
        for log in logs:
            details = json.loads(cast(Dict[str, Any], log).get("details", "{}"))
            logs_list.append({
                "id": cast(Dict[str, Any], log)["id"],
                "admin_username": cast(Dict[str, Any], log)["admin_username"],
                "action": cast(Dict[str, Any], log)["action"],
                "target_type": cast(Dict[str, Any], log)["target_type"],
                "target_id": cast(Dict[str, Any], log)["target_id"],
                "details": details,
                "ip_address": cast(Dict[str, Any], log)["ip_address"],
                "user_agent": cast(Dict[str, Any], log)["user_agent"],
                "created_at": cast(Dict[str, Any], log)["created_at"].isoformat() if cast(Dict[str, Any], log)["created_at"] is not None and hasattr(cast(Dict[str, Any], log)["created_at"], "isoformat") else None
            })

        return {"audit_logs": logs_list}

    except Error as e:
        logger.error(f"Database error getting audit logs: {e}")
        raise HTTPException(status_code=500, detail="Database error")
    finally:
        cursor.close()
        conn.close()

# Reporting endpoints
@app.get("/api/reports/crime-summary")
def get_crime_summary_report(
    current_user: str = Depends(get_username_from_token),
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    area: Optional[str] = Query(None, description="Filter by area"),
    crime_type: Optional[str] = Query(None, description="Filter by crime type")
):
    """Generate crime summary report with statistics"""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        # Check if user has admin privileges
        cursor.execute("SELECT role FROM users_info WHERE username = %s", (current_user,))
        user = cursor.fetchone()
        if not user or cast(Dict[str, Any], user).get("role") not in ["superadmin", "admin"]:
            raise HTTPException(status_code=403, detail="Access denied")

        # Build query with filters
        query = """
            SELECT
                COUNT(*) as total_crimes,
                COUNT(DISTINCT area) as unique_areas,
                COUNT(DISTINCT crime_type) as unique_crime_types,
                AVG(CASE WHEN risk_level = 'High' THEN 1 ELSE 0 END) * 100 as high_risk_percentage,
                AVG(CASE WHEN risk_level = 'Medium' THEN 1 ELSE 0 END) * 100 as medium_risk_percentage,
                AVG(CASE WHEN risk_level = 'Low' THEN 1 ELSE 0 END) * 100 as low_risk_percentage
            FROM crimes
            WHERE 1=1
        """
        params = []

        if start_date:
            query += " AND crime_date >= %s"
            params.append(start_date)
        if end_date:
            query += " AND crime_date <= %s"
            params.append(end_date)
        if area:
            query += " AND area = %s"
            params.append(area)
        if crime_type:
            query += " AND crime_type = %s"
            params.append(crime_type)

        cursor.execute(query, params)
        summary = cursor.fetchone()

        # Get crime distribution by area
        area_query = """
            SELECT area, COUNT(*) as crime_count
            FROM crimes
            WHERE 1=1
        """
        area_params = []
        if start_date:
            area_query += " AND crime_date >= %s"
            area_params.append(start_date)
        if end_date:
            area_query += " AND crime_date <= %s"
            area_params.append(end_date)
        if crime_type:
            area_query += " AND crime_type = %s"
            area_params.append(crime_type)

        area_query += " GROUP BY area ORDER BY crime_count DESC LIMIT 10"
        cursor.execute(area_query, area_params)
        area_distribution = cursor.fetchall()

        # Get crime distribution by type
        type_query = """
            SELECT crime_type, COUNT(*) as crime_count
            FROM crimes
            WHERE 1=1
        """
        type_params = []
        if start_date:
            type_query += " AND crime_date >= %s"
            type_params.append(start_date)
        if end_date:
            type_query += " AND crime_date <= %s"
            type_params.append(end_date)
        if area:
            type_query += " AND area = %s"
            type_params.append(area)

        type_query += " GROUP BY crime_type ORDER BY crime_count DESC LIMIT 10"
        cursor.execute(type_query, type_params)
        type_distribution = cursor.fetchall()

        # Get monthly trend (last 12 months)
        trend_query = """
            SELECT
                DATE_FORMAT(crime_date, '%Y-%m') as month,
                COUNT(*) as crime_count
            FROM crimes
            WHERE crime_date >= DATE_SUB(CURDATE(), INTERVAL 12 MONTH)
        """
        trend_params = []
        if area:
            trend_query += " AND area = %s"
            trend_params.append(area)
        if crime_type:
            trend_query += " AND crime_type = %s"
            trend_params.append(crime_type)

        trend_query += " GROUP BY DATE_FORMAT(crime_date, '%Y-%m') ORDER BY month"
        cursor.execute(trend_query, trend_params)
        monthly_trend = cursor.fetchall()

        return {
            "summary": {
                "total_crimes": cast(Dict[str, Any], summary)["total_crimes"],
                "unique_areas": cast(Dict[str, Any], summary)["unique_areas"],
                "unique_crime_types": cast(Dict[str, Any], summary)["unique_crime_types"],
                "high_risk_percentage": round(cast(Dict[str, Any], summary)["high_risk_percentage"] or 0, 2),
                "medium_risk_percentage": round(cast(Dict[str, Any], summary)["medium_risk_percentage"] or 0, 2),
                "low_risk_percentage": round(cast(Dict[str, Any], summary)["low_risk_percentage"] or 0, 2)
            },
            "area_distribution": [
                {"area": cast(Dict[str, Any], row)["area"], "count": cast(Dict[str, Any], row)["crime_count"]}
                for row in area_distribution
            ],
            "crime_type_distribution": [
                {"crime_type": cast(Dict[str, Any], row)["crime_type"], "count": cast(Dict[str, Any], row)["crime_count"]}
                for row in type_distribution
            ],
            "monthly_trend": [
                {"month": cast(Dict[str, Any], row)["month"], "count": cast(Dict[str, Any], row)["crime_count"]}
                for row in monthly_trend
            ],
            "filters_applied": {
                "start_date": start_date,
                "end_date": end_date,
                "area": area,
                "crime_type": crime_type
            }
        }

    except Error as e:
        logger.error(f"Database error generating crime summary report: {e}")
        raise HTTPException(status_code=500, detail="Database error")
    finally:
        cursor.close()
        conn.close()

@app.get("/api/reports/user-activity")
def get_user_activity_report(
    current_user: str = Depends(get_username_from_token),
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    user_role: Optional[str] = Query(None, description="Filter by user role")
):
    """Generate user activity report"""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        # Check if user has admin privileges
        cursor.execute("SELECT role FROM users_info WHERE username = %s", (current_user,))
        user = cursor.fetchone()
        if not user or cast(Dict[str, Any], user).get("role") not in ["superadmin", "admin"]:
            raise HTTPException(status_code=403, detail="Access denied")

        # User registration statistics
        reg_query = """
            SELECT
                COUNT(*) as total_users,
                COUNT(CASE WHEN role = 'user' THEN 1 END) as regular_users,
                COUNT(CASE WHEN role = 'admin' THEN 1 END) as admin_users,
                COUNT(CASE WHEN role = 'superadmin' THEN 1 END) as superadmin_users,
                COUNT(CASE WHEN DATE(created_at) = CURDATE() THEN 1 END) as new_today,
                COUNT(CASE WHEN created_at >= DATE_SUB(CURDATE(), INTERVAL 7 DAY) THEN 1 END) as new_this_week,
                COUNT(CASE WHEN created_at >= DATE_SUB(CURDATE(), INTERVAL 30 DAY) THEN 1 END) as new_this_month
            FROM users_info
            WHERE 1=1
        """
        reg_params = []

        if user_role:
            reg_query += " AND role = %s"
            reg_params.append(user_role)

        cursor.execute(reg_query, reg_params)
        user_stats = cursor.fetchone()

        # User activity logs summary
        activity_query = """
            SELECT
                activity_type,
                COUNT(*) as count
            FROM user_activity_logs
            WHERE 1=1
        """
        activity_params = []

        if start_date:
            activity_query += " AND DATE(created_at) >= %s"
            activity_params.append(start_date)
        if end_date:
            activity_query += " AND DATE(created_at) <= %s"
            activity_params.append(end_date)

        activity_query += " GROUP BY activity_type ORDER BY count DESC"
        cursor.execute(activity_query, activity_params)
        activity_summary = cursor.fetchall()

        # Recent user registrations
        recent_query = """
            SELECT username, first_name, last_name, email, role, created_at
            FROM users_info
            WHERE 1=1
        """
        recent_params = []

        if user_role:
            recent_query += " AND role = %s"
            recent_params.append(user_role)

        recent_query += " ORDER BY created_at DESC LIMIT 20"
        cursor.execute(recent_query, recent_params)
        recent_users = cursor.fetchall()

        return {
            "user_statistics": {
                "total_users": cast(Dict[str, Any], user_stats)["total_users"],
                "regular_users": cast(Dict[str, Any], user_stats)["regular_users"],
                "admin_users": cast(Dict[str, Any], user_stats)["admin_users"],
                "superadmin_users": cast(Dict[str, Any], user_stats)["superadmin_users"],
                "new_today": cast(Dict[str, Any], user_stats)["new_today"],
                "new_this_week": cast(Dict[str, Any], user_stats)["new_this_week"],
                "new_this_month": cast(Dict[str, Any], user_stats)["new_this_month"]
            },
            "activity_summary": [
                {"activity_type": cast(Dict[str, Any], row)["activity_type"], "count": cast(Dict[str, Any], row)["count"]}
                for row in activity_summary
            ],
            "recent_registrations": [
                {
                    "username": cast(Dict[str, Any], row)["username"],
                    "name": f"{cast(Dict[str, Any], row)['first_name']} {cast(Dict[str, Any], row)['last_name']}",
                    "email": cast(Dict[str, Any], row)["email"],
                    "role": cast(Dict[str, Any], row)["role"],
                    "created_at": cast(Dict[str, Any], row)["created_at"].isoformat() if cast(Dict[str, Any], row)["created_at"] else None
                }
                for row in recent_users
            ],
            "filters_applied": {
                "start_date": start_date,
                "end_date": end_date,
                "user_role": user_role
            }
        }

    except Error as e:
        logger.error(f"Database error generating user activity report: {e}")
        raise HTTPException(status_code=500, detail="Database error")
    finally:
        cursor.close()
        conn.close()

@app.get("/api/reports/system-health")
def get_system_health_report(current_user: str = Depends(get_username_from_token)):
    """Generate system health report"""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        # Check if user has admin privileges
        cursor.execute("SELECT role FROM users_info WHERE username = %s", (current_user,))
        user = cursor.fetchone()
        if not user or cast(Dict[str, Any], user).get("role") not in ["superadmin", "admin"]:
            raise HTTPException(status_code=403, detail="Access denied")

        # Database connection health
        db_health = "healthy"
        try:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        except Exception as e:
            db_health = f"unhealthy: {str(e)}"

        # Table statistics
        tables_stats = {}
        tables = ["users_info", "crimes", "admins", "user_activity_logs", "audit_logs"]

        for table in tables:
            try:
                cursor.execute(f"SELECT COUNT(*) as count FROM {table}")
                result = cursor.fetchone()
                tables_stats[table] = cast(Dict[str, Any], result)["count"]
            except Exception as e:
                tables_stats[table] = f"error: {str(e)}"

        # System metrics
        cursor.execute("SELECT COUNT(*) as active_users FROM users_info WHERE role = 'user'")
        active_users_result = cursor.fetchone()
        active_users = cast(Dict[str, Any], active_users_result)["active_users"]

        cursor.execute("SELECT COUNT(*) as total_crimes FROM crimes")
        total_crimes_result = cursor.fetchone()
        total_crimes = cast(Dict[str, Any], total_crimes_result)["total_crimes"]

        cursor.execute("SELECT COUNT(*) as recent_activities FROM user_activity_logs WHERE created_at >= DATE_SUB(NOW(), INTERVAL 24 HOUR)")
        recent_activities_result = cursor.fetchone()
        recent_activities = cast(Dict[str, Any], recent_activities_result)["recent_activities"]

        # ML model status
        ml_status = "loaded" if model and le_area and le_crime and le_risk else "not_loaded"

        return {
            "database_health": db_health,
            "table_statistics": tables_stats,
            "system_metrics": {
                "active_users": active_users,
                "total_crimes": total_crimes,
                "recent_activities_24h": recent_activities,
                "ml_model_status": ml_status
            },
            "timestamp": datetime.now().isoformat()
        }

    except Error as e:
        logger.error(f"Database error generating system health report: {e}")
        raise HTTPException(status_code=500, detail="Database error")
    finally:
        cursor.close()
        conn.close()

@app.get("/api/reports/export-crime-data")
def export_crime_data(
    current_user: str = Depends(get_username_from_token),
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    area: Optional[str] = Query(None, description="Filter by area"),
    crime_type: Optional[str] = Query(None, description="Filter by crime type"),
    format: str = Query("json", description="Export format: json or csv")
):
    """Export crime data for reporting purposes"""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        # Check if user has admin privileges
        cursor.execute("SELECT role FROM users_info WHERE username = %s", (current_user,))
        user = cursor.fetchone()
        if not user or cast(Dict[str, Any], user).get("role") not in ["superadmin", "admin"]:
            raise HTTPException(status_code=403, detail="Access denied")

        # Build query
        query = """
            SELECT
                id, area, crime_type, crime_date, latitude, longitude, risk_level, created_at
            FROM crimes
            WHERE 1=1
        """
        params = []

        if start_date:
            query += " AND crime_date >= %s"
            params.append(start_date)
        if end_date:
            query += " AND crime_date <= %s"
            params.append(end_date)
        if area:
            query += " AND area = %s"
            params.append(area)
        if crime_type:
            query += " AND crime_type = %s"
            params.append(crime_type)

        query += " ORDER BY crime_date DESC"

        cursor.execute(query, params)
        crimes = cursor.fetchall()

        # Format data
        export_data = []
        for crime in crimes:
            export_data.append({
                "id": cast(Dict[str, Any], crime)["id"],
                "area": cast(Dict[str, Any], crime)["area"],
                "crime_type": cast(Dict[str, Any], crime)["crime_type"],
                "crime_date": str(cast(Dict[str, Any], crime)["crime_date"]),
                "latitude": cast(Dict[str, Any], crime)["latitude"],
                "longitude": cast(Dict[str, Any], crime)["longitude"],
                "risk_level": cast(Dict[str, Any], crime)["risk_level"],
                "created_at": cast(Dict[str, Any], crime)["created_at"].isoformat() if cast(Dict[str, Any], crime)["created_at"] else None
            })

        if format.lower() == "csv":
            # Convert to CSV format (simple implementation)
            if not export_data:
                csv_content = "No data available"
            else:
                headers = list(export_data[0].keys())
                csv_content = ",".join(headers) + "\n"
                for row in export_data:
                    csv_row = ",".join(str(row.get(header, "")) for header in headers)
                    csv_content += csv_row + "\n"

            return {
                "format": "csv",
                "data": csv_content,
                "record_count": len(export_data),
                "filters_applied": {
                    "start_date": start_date,
                    "end_date": end_date,
                    "area": area,
                    "crime_type": crime_type
                }
            }
        else:
            # Default JSON format
            return {
                "format": "json",
                "data": export_data,
                "record_count": len(export_data),
                "filters_applied": {
                    "start_date": start_date,
                    "end_date": end_date,
                    "area": area,
                    "crime_type": crime_type
                }
            }

    except Error as e:
        logger.error(f"Database error exporting crime data: {e}")
        raise HTTPException(status_code=500, detail="Database error")
    finally:
        cursor.close()
        conn.close()

# Admin reporting endpoints for ReportingDashboard
@app.get("/admin/reports/history")
def get_report_history(
    current_user: str = Depends(get_username_from_token),
    limit: int = Query(50, description="Maximum number of reports to return", ge=1, le=100)
):
    """Get report generation history"""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        # Check if user has admin privileges
        cursor.execute("SELECT role FROM users_info WHERE username = %s", (current_user,))
        user = cursor.fetchone()
        if not user or cast(Dict[str, Any], user).get("role") not in ["superadmin", "admin"]:
            raise HTTPException(status_code=403, detail="Access denied")

        # Return real reports from DB
        from app.reports import get_reports_from_db
        reports = get_reports_from_db(limit)
        return {"reports": reports}

    except Error as e:
        logger.error(f"Database error getting report history: {e}")
        raise HTTPException(status_code=500, detail="Database error")
    finally:
        cursor.close()
        conn.close()

@app.get("/admin/reports/scheduled")
def get_scheduled_reports(
    current_user: str = Depends(get_username_from_token),
    limit: int = Query(50, description="Maximum number of scheduled reports to return", ge=1, le=100)
):
    """Get scheduled reports"""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        # Check if user has admin privileges
        cursor.execute("SELECT role FROM users_info WHERE username = %s", (current_user,))
        user = cursor.fetchone()
        if not user or cast(Dict[str, Any], user).get("role") not in ["superadmin", "admin"]:
            raise HTTPException(status_code=403, detail="Access denied")

        # Return real scheduled reports from DB
        from app.reports import get_scheduled_reports_from_db
        scheduled = get_scheduled_reports_from_db(limit)
        return {"scheduled_reports": scheduled}

    except Error as e:
        logger.error(f"Database error getting scheduled reports: {e}")
        raise HTTPException(status_code=500, detail="Database error")
    finally:
        cursor.close()
        conn.close()

@app.post("/admin/reports/generate")
def generate_custom_report(
    report_data: Dict[str, Any],
    current_user: str = Depends(get_username_from_token)
):
    """Generate a custom report"""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        # Check if user has admin privileges
        cursor.execute("SELECT role FROM users_info WHERE username = %s", (current_user,))
        user = cursor.fetchone()
        if not user or cast(Dict[str, Any], user).get("role") not in ["superadmin", "admin"]:
            raise HTTPException(status_code=403, detail="Access denied")

        # Select report type and format
        from app.reports import (
            save_report_to_db,
            generate_crime_summary_pdf,
            generate_crime_summary_excel,
            generate_crime_summary_csv,
            generate_user_activity_pdf,
            generate_user_activity_excel,
            generate_user_activity_csv,
            generate_system_health_pdf,
            generate_system_health_excel,
            generate_system_health_csv
        )
        report_type = report_data.get("type", "crime_summary")
        format_type = report_data.get("format", "pdf").lower()
        filters = report_data.get("filters", {})
        report_style = report_data.get("report_style", "table")  # default to table if not provided

        # Get report data from corresponding internal functions
        if report_type == "crime_summary":
            data = get_crime_summary_data(**filters, report_style=report_style)
        elif report_type == "user_activity":
            data = get_user_activity_data(**filters, report_style=report_style)
        elif report_type == "system_health":
            data = get_system_health_data(report_style=report_style)
        else:
            data = {}

        if report_type == "crime_summary":
            if format_type == "pdf":
                file_path = generate_crime_summary_pdf(data, filters, report_style=report_style)
            elif format_type == "excel":
                file_path = generate_crime_summary_excel(data, filters, report_style=report_style)
            elif format_type == "csv":
                file_path = generate_crime_summary_csv(data, filters, report_style=report_style)
            else:
                raise HTTPException(status_code=400, detail=f"Unsupported format: {format_type}")
        elif report_type == "user_activity":
            if format_type == "pdf":
                file_path = generate_user_activity_pdf(data, filters, report_style=report_style)
            elif format_type == "excel":
                file_path = generate_user_activity_excel(data, filters, report_style=report_style)
            elif format_type == "csv":
                file_path = generate_user_activity_csv(data, filters, report_style=report_style)
            else:
                raise HTTPException(status_code=400, detail=f"Unsupported format for user activity: {format_type}")
        elif report_type == "system_health":
            if format_type == "pdf":
                file_path = generate_system_health_pdf(data, report_style=report_style)
            elif format_type == "excel":
                file_path = generate_system_health_excel(data, filters, report_style=report_style)
            elif format_type == "csv":
                file_path = generate_system_health_csv(data, filters, report_style=report_style)
            else:
                raise HTTPException(status_code=400, detail=f"Unsupported format for system health: {format_type}")
        else:
            raise HTTPException(status_code=400, detail=f"Unknown report type: {report_type}")

        # Save report metadata to DB
        title = f"{report_type.replace('_', ' ').title()} Report ({format_type.upper()})"
        report_id = save_report_to_db(
            title=title,
            report_type=report_type,
            format_type=format_type,
            filepath=file_path,
            created_by=current_user,
            parameters=report_data
        )
        logger.info(f"save_report_to_db returned report_id: {report_id}")
        if not report_id:
            logger.error(f"Report DB save failed: Could not save report metadata for file {file_path}")
            raise HTTPException(status_code=500, detail="Failed to save report metadata to database")
        logger.info(f"Report generated and saved: id={report_id}, path={file_path}")
        return {"message": "Report generated successfully", "report_id": report_id}

    except Error as e:
        logger.error(f"Database error generating custom report: {e}")
        raise HTTPException(status_code=500, detail="Database error")
    finally:
        cursor.close()
        conn.close()

@app.post("/admin/reports/schedule")
def schedule_report(
    schedule_data: Dict[str, Any],
    current_user: str = Depends(get_username_from_token)
):
    """Schedule a report for automatic generation"""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        # Check if user has admin privileges
        cursor.execute("SELECT role FROM users_info WHERE username = %s", (current_user,))
        user = cursor.fetchone()
        if not user or cast(Dict[str, Any], user).get("role") not in ["superadmin", "admin"]:
            raise HTTPException(status_code=403, detail="Access denied")

        # Mock report scheduling - in real implementation, this would create a scheduled task
        schedule_id = int(datetime.now().timestamp())

        return {
            "schedule_id": schedule_id,
            "status": "scheduled",
            "message": "Report scheduled successfully",
            "next_run": "2024-02-01T10:00:00Z"
        }

    except Error as e:
        logger.error(f"Database error scheduling report: {e}")
        raise HTTPException(status_code=500, detail="Database error")
    finally:
        cursor.close()
        conn.close()

@app.get("/admin/reports/download/{report_id}")
def download_report(
    report_id: int,
    current_user: str = Depends(get_username_from_token)
):
    """Download a generated report"""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        # Check if user has admin privileges
        cursor.execute("SELECT role FROM users_info WHERE username = %s", (current_user,))
        user = cursor.fetchone()
        if not user or cast(Dict[str, Any], user).get("role") not in ["superadmin", "admin"]:
            raise HTTPException(status_code=403, detail="Access denied")

        # Serve real report file
        from fastapi.responses import FileResponse
        from app.reports import get_reports_from_db
        reports = get_reports_from_db(100)
        report = next((r for r in reports if r["id"] == report_id), None)
        if not report:
            logger.error(f"Download failed: Report with id {report_id} not found in DB.")
            raise HTTPException(status_code=404, detail=f"Report not found (id={report_id})")
        file_path = report.get("file_path")
        logger.info(f"Attempting to download report id={report_id}, raw file_path from DB: {file_path}")
        if not file_path:
            logger.error(f"Download failed: Report id {report_id} has no file_path in DB.")
            raise HTTPException(status_code=404, detail=f"Report file path missing for report id {report_id}")

        # Normalize path for Windows
        normalized_path = os.path.normpath(file_path)
        logger.info(f"Normalized file path: {normalized_path}")

        if not os.path.exists(normalized_path):
            logger.error(f"Download failed: File does not exist at normalized path {normalized_path} for report id {report_id}.")
            raise HTTPException(status_code=404, detail=f"Report file not found at {normalized_path}")

        logger.info(f"Download success: Serving file {normalized_path} for report id {report_id}.")

        # Map report format to MIME type
        format_to_mime = {
            "pdf": "application/pdf",
            "excel": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "csv": "text/csv"
        }
        report_format = report.get("format", "pdf").lower()
        media_type = format_to_mime.get(report_format, "application/pdf")

        return FileResponse(
            path=normalized_path,
            media_type=media_type,
            filename=os.path.basename(normalized_path),
            headers={"Content-Disposition": f"attachment; filename={os.path.basename(normalized_path)}"}
        )

    except Error as e:
        logger.error(f"Database error downloading report: {e}")
        raise HTTPException(status_code=500, detail="Database error")
    finally:
        cursor.close()
        conn.close()


@app.post("/api/patrol-request")
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
            'pending',  # Default status
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

    except Error as e:
        logger.error(f"Database error submitting patrol request: {e}")
        raise HTTPException(status_code=500, detail="Failed to submit patrol request")
    except Exception as e:
        logger.error(f"Unexpected error submitting patrol request: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()

@app.get("/api/emergency-contacts")
def get_emergency_contacts():
    """Get emergency contacts data"""
    # Return the same data structure as used in the frontend
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

# Make sure these endpoints are in your main FastAPI app
@app.post("/api/emergency-call")
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
                user_id = cast(Dict[str, Any], user_result)['id']
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
            'completed',  # Default status
            datetime.now()  # Explicit timestamp
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

    except Error as e:
        logger.error(f"Database error logging emergency call: {e}")
        raise HTTPException(status_code=500, detail="Failed to log emergency call")
    except Exception as e:
        logger.error(f"Unexpected error logging emergency call: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()


@app.post("/api/emergency-call/public")
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
            None,  # user_id
            'anonymous',  # username
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

    except Error as e:
        logger.error(f"Database error logging public emergency call: {e}")
        raise HTTPException(status_code=500, detail="Failed to log emergency call")
    except Exception as e:
        logger.error(f"Unexpected error logging public emergency call: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()

            

@app.get("/api/areas/{area}/safety-score")
def get_area_safety_score(area: str):
    """Calculate safety score for a specific area based on crime data"""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        # Get crime statistics for the area
        cursor.execute("""
            SELECT 
                COUNT(*) as total_crimes,
                SUM(CASE WHEN risk_level = 'High' THEN 1 ELSE 0 END) as high_risk_count,
                SUM(CASE WHEN risk_level = 'Medium' THEN 1 ELSE 0 END) as medium_risk_count,
                SUM(CASE WHEN risk_level = 'Low' THEN 1 ELSE 0 END) as low_risk_count,
                COUNT(DISTINCT crime_type) as unique_crime_types,
                MIN(crime_date) as first_incident,
                MAX(crime_date) as last_incident
            FROM crimes 
            WHERE area = %s
        """, (area,))
        
        stats = cursor.fetchone()
        
        if not stats or cast(Dict[str, Any], stats)["total_crimes"] == 0:
            return {
                "area": area,
                "safety_score": 100,  # Default high score for areas with no crime data
                "risk_level": "Very Safe",
                "message": "No crime data available for this area",
                "confidence": "low"
            }

        total_crimes = cast(Dict[str, Any], stats)["total_crimes"]
        high_risk_count = cast(Dict[str, Any], stats)["high_risk_count"]
        medium_risk_count = cast(Dict[str, Any], stats)["medium_risk_count"]
        low_risk_count = cast(Dict[str, Any], stats)["low_risk_count"]
        
        # Calculate base safety score (0-100 scale)
        # Higher score = safer area
        base_score = 100
        
        # Penalize based on crime density and severity
        crime_density_penalty = min(60, (total_crimes * 2))  # Max 60 point penalty for high crime density
        severity_penalty = (high_risk_count * 3) + (medium_risk_count * 1.5) + (low_risk_count * 0.5)
        
        # Apply penalties
        safety_score = max(0, base_score - crime_density_penalty - severity_penalty)
        
        # Adjust for crime variety (more types = more concerning)
        unique_crime_penalty = min(15, cast(Dict[str, Any], stats)["unique_crime_types"] * 2)
        safety_score = max(0, safety_score - unique_crime_penalty)
        
        # Ensure score is between 0-100
        safety_score = min(100, max(0, round(safety_score, 1)))
        
        # Determine risk level
        if safety_score >= 80:
            risk_level = "Very Safe"
            color = "green"
        elif safety_score >= 60:
            risk_level = "Generally Safe"
            color = "blue"
        elif safety_score >= 40:
            risk_level = "Moderate Risk"
            color = "orange"
        elif safety_score >= 20:
            risk_level = "High Risk"
            color = "red"
        else:
            risk_level = "Very High Risk"
            color = "darkred"
        
        # Calculate confidence based on data volume
        confidence = "high" if total_crimes > 10 else "medium" if total_crimes > 3 else "low"
        
        return {
            "area": area,
            "safety_score": safety_score,
            "risk_level": risk_level,
            "color": color,
            "crime_statistics": {
                "total_crimes": total_crimes,
                "high_risk_crimes": high_risk_count,
                "medium_risk_crimes": medium_risk_count,
                "low_risk_crimes": low_risk_count,
                "unique_crime_types": cast(Dict[str, Any], stats)["unique_crime_types"],
                "data_period": {
                    "first_incident": str(cast(Dict[str, Any], stats)["first_incident"]),
                    "last_incident": str(cast(Dict[str, Any], stats)["last_incident"])
                }
            },
            "confidence": confidence,
            "factors_considered": [
                "Total crime count",
                "Crime severity distribution", 
                "Variety of crime types",
                "Historical data coverage"
            ]
        }

    except Error as e:
        logger.error(f"Database error calculating safety score: {e}")
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

@app.get("/api/areas/{area}/safety-score/detailed")
def get_detailed_safety_score(area: str, days: int = Query(90, description="Analysis period in days")):
    """Get detailed safety score with trend analysis"""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        # Get recent crime data for trend analysis
        cutoff_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        
        cursor.execute("""
            SELECT 
                -- Overall stats
                COUNT(*) as total_crimes,
                SUM(CASE WHEN risk_level = 'High' THEN 1 ELSE 0 END) as high_risk_count,
                
                -- Recent trend (last 30 days vs previous period)
                SUM(CASE WHEN crime_date >= DATE_SUB(CURDATE(), INTERVAL 30 DAY) THEN 1 ELSE 0 END) as recent_crimes,
                SUM(CASE WHEN crime_date >= DATE_SUB(CURDATE(), INTERVAL 60 DAY) 
                         AND crime_date < DATE_SUB(CURDATE(), INTERVAL 30 DAY) THEN 1 ELSE 0 END) as previous_crimes,
                
                -- Time-based patterns
                SUM(CASE WHEN HOUR(created_at) BETWEEN 18 AND 23 OR HOUR(created_at) BETWEEN 0 AND 6 THEN 1 ELSE 0 END) as night_crimes,
                SUM(CASE WHEN DAYOFWEEK(crime_date) IN (1,7) THEN 1 ELSE 0 END) as weekend_crimes
                
            FROM crimes 
            WHERE area = %s AND crime_date >= %s
        """, (area, cutoff_date))
        
        stats = cursor.fetchone()
        
        if not stats or cast(Dict[str, Any], stats)["total_crimes"] == 0:
            return get_area_safety_score(area)  # Fall back to basic calculation
        
        total_crimes = cast(Dict[str, Any], stats)["total_crimes"]
        high_risk_count = cast(Dict[str, Any], stats)["high_risk_count"]
        recent_crimes = cast(Dict[str, Any], stats)["recent_crimes"]
        previous_crimes = cast(Dict[str, Any], stats)["previous_crimes"]
        night_crimes = cast(Dict[str, Any], stats)["night_crimes"]
        
        # Calculate base safety score
        base_score = 100
        
        # Crime density penalty
        crime_density_penalty = min(50, (total_crimes / days) * 100)
        
        # Severity penalty
        severity_penalty = min(30, (high_risk_count / total_crimes) * 100) if total_crimes > 0 else 0
        
        # Trend analysis
        trend_penalty = 0
        if previous_crimes > 0:
            crime_trend = (recent_crimes - previous_crimes) / previous_crimes
            if crime_trend > 0.2:  # 20% increase
                trend_penalty = 15
            elif crime_trend > 0.5:  # 50% increase
                trend_penalty = 25
        
        # Time pattern penalties
        night_crime_ratio = night_crimes / total_crimes if total_crimes > 0 else 0
        time_penalty = min(10, night_crime_ratio * 20)
        
        # Calculate final score
        safety_score = max(0, base_score - crime_density_penalty - severity_penalty - trend_penalty - time_penalty)
        safety_score = round(safety_score, 1)
        
        # Determine risk level (same as before)
        if safety_score >= 80:
            risk_level = "Very Safe"
        elif safety_score >= 60:
            risk_level = "Generally Safe" 
        elif safety_score >= 40:
            risk_level = "Moderate Risk"
        elif safety_score >= 20:
            risk_level = "High Risk"
        else:
            risk_level = "Very High Risk"
        
        return {
            "area": area,
            "safety_score": safety_score,
            "risk_level": risk_level,
            "analysis_period_days": days,
            "trend_analysis": {
                "recent_crimes_30d": recent_crimes,
                "previous_crimes_30d": previous_crimes,
                "trend": "increasing" if trend_penalty > 0 else "stable" if recent_crimes == previous_crimes else "decreasing",
                "night_crime_ratio": round(night_crime_ratio * 100, 1)
            },
            "factors": {
                "crime_density": round(crime_density_penalty, 1),
                "crime_severity": round(severity_penalty, 1),
                "recent_trend": trend_penalty,
                "time_patterns": time_penalty
            }
        }
        
    except Error as e:
        logger.error(f"Database error calculating detailed safety score: {e}")
        raise HTTPException(status_code=500, detail="Failed to calculate detailed safety score")
    finally:
        cursor.close()
        conn.close()
@app.get("/api/emergency-stats")
async def get_emergency_stats():
    """Get real-time emergency statistics from database"""
    conn, cursor = None, None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Calls today: Count of emergency calls made today
        cursor.execute("""
            SELECT COUNT(*) as calls_today 
            FROM emergency_calls 
            WHERE DATE(call_timestamp) = CURDATE()
        """)
        calls_result = cursor.fetchone()
        calls_today = cast(Dict[str, Any], calls_result)['calls_today'] if calls_result else 0

        # Active units: Count of active patrol requests (not completed)
        cursor.execute("""
            SELECT COUNT(*) as active_units
            FROM patrol_requests
            WHERE status NOT IN ('completed', 'cancelled')
        """)
        units_result = cursor.fetchone()
        active_units = cast(Dict[str, Any], units_result)['active_units'] if units_result else 0

        # Resolved rate: Percentage of emergency calls (all are considered resolved for now)
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
        resolved_rate = cast(Dict[str, Any], resolved_result)['resolved_rate'] if resolved_result else 0.0

        # Avg response time: Mock data for now since we don't have response time tracking
        avg_response = "2.5min"

        stats = {
            "calls_today": calls_today,
            "avg_response": avg_response,
            "active_units": active_units,
            "resolved_rate": f"{resolved_rate}%"
        }

        logger.info(f"Emergency stats: {stats}")
        return stats

    except Error as e:
        logger.error(f"MySQL error in emergency stats: {e}")
        # Return default values if database error
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


# Area analytics and details endpoints

# Add these endpoints to your main.py or appropriate router file

@app.get("/api/auth/me/stats")
def get_user_stats(
    current_user: str = Depends(get_username_from_token),
    latitude: Optional[float] = Query(None),
    longitude: Optional[float] = Query(None),
    area: Optional[str] = Query(None),
    time_filter: Optional[str] = Query('12m')
):
    """Get user statistics for dashboard"""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        # Get user ID
        cursor.execute("SELECT id FROM users_info WHERE username = %s", (current_user,))
        user = cursor.fetchone()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        user_id = cast(Dict[str, Any], user).get("id")
        
        # Calculate user stats
        # Predictions made (count predictions from activity logs)
        cursor.execute("""
            SELECT COUNT(*) as predictions_made 
            FROM user_activity_logs 
            WHERE user_id = %s AND activity_type LIKE '%prediction%'
        """, (user_id,))
        predictions_result = cursor.fetchone()
        
        # Areas monitored (count distinct areas from user's activity)
        cursor.execute("""
            SELECT COUNT(DISTINCT home_area) as areas_monitored 
            FROM users_info 
            WHERE id = %s AND home_area IS NOT NULL
        """, (user_id,))
        areas_result = cursor.fetchone()
        
        # Alerts received (count alerts from activity logs)
        cursor.execute("""
            SELECT COUNT(*) as alerts_received 
            FROM user_activity_logs 
            WHERE user_id = %s AND activity_type LIKE '%alert%'
        """, (user_id,))
        alerts_result = cursor.fetchone()
        
        # Account age
        cursor.execute("""
            SELECT DATEDIFF(NOW(), created_at) as account_age 
            FROM users_info 
            WHERE id = %s
        """, (user_id,))
        age_result = cursor.fetchone()
        
        return {
            "predictions_made": cast(Dict[str, Any], predictions_result)["predictions_made"] or 0,
            "areas_monitored": cast(Dict[str, Any], areas_result)["areas_monitored"] or 0,
            "alerts_received": cast(Dict[str, Any], alerts_result)["alerts_received"] or 0,
            "account_age": cast(Dict[str, Any], age_result)["account_age"] or 0
        }
        
    except Error as e:
        logger.error(f"Database error getting user stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve user statistics")
    finally:
        cursor.close()
        conn.close()

@app.get("/api/auth/me/activity")
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
        
        user_id = cast(Dict[str, Any], user).get("id")
        
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
        
        # Format activities
        formatted_activities = []
        for activity in activities:
            formatted_activities.append({
                "id": cast(Dict[str, Any], activity)["id"],
                "type": cast(Dict[str, Any], activity)["type"],
                "description": cast(Dict[str, Any], activity).get("description", "User activity"),
                "timestamp": cast(Dict[str, Any], activity)["timestamp"].isoformat() if cast(Dict[str, Any], activity)["timestamp"] else None,
                "area": cast(Dict[str, Any], activity).get("area")
            })
        
        return formatted_activities
        
    except Error as e:
        logger.error(f"Database error getting user activity: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve user activity")
    finally:
        cursor.close()
        conn.close()
@app.get("/api/areas/{area}/analytics")
def get_area_analytics(area: str):
    """Get comprehensive analytics for a specific area"""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        # Get basic crime statistics for the area
        cursor.execute("""
            SELECT 
                COUNT(*) as total_crimes,
                COUNT(DISTINCT crime_type) as unique_crime_types,
                AVG(CASE WHEN risk_level = 'High' THEN 1 ELSE 0 END) * 100 as high_risk_percentage,
                AVG(CASE WHEN risk_level = 'Medium' THEN 1 ELSE 0 END) * 100 as medium_risk_percentage,
                AVG(CASE WHEN risk_level = 'Low' THEN 1 ELSE 0 END) * 100 as low_risk_percentage,
                MIN(crime_date) as first_recorded,
                MAX(crime_date) as last_recorded
            FROM crimes 
            WHERE area = %s
        """, (area,))
        stats = cursor.fetchone()

        # Get crime distribution by type for this area
        cursor.execute("""
            SELECT crime_type, COUNT(*) as count, 
                   AVG(CASE WHEN risk_level = 'High' THEN 1 ELSE 0 END) * 100 as high_risk_rate
            FROM crimes 
            WHERE area = %s 
            GROUP BY crime_type 
            ORDER BY count DESC
            LIMIT 10
        """, (area,))
        crime_types = cursor.fetchall()

        # Get monthly trend for this area (last 12 months)
        cursor.execute("""
            SELECT 
                DATE_FORMAT(crime_date, '%Y-%m') as month,
                COUNT(*) as crime_count,
                AVG(CASE WHEN risk_level = 'High' THEN 1 ELSE 0 END) * 100 as high_risk_rate
            FROM crimes 
            WHERE area = %s AND crime_date >= DATE_SUB(CURDATE(), INTERVAL 12 MONTH)
            GROUP BY DATE_FORMAT(crime_date, '%Y-%m') 
            ORDER BY month
        """, (area,))
        monthly_trend = cursor.fetchall()

        # Get risk level distribution
        cursor.execute("""
            SELECT risk_level, COUNT(*) as count
            FROM crimes 
            WHERE area = %s
            GROUP BY risk_level
            ORDER BY FIELD(risk_level, 'High', 'Medium', 'Low')
        """, (area,))
        risk_distribution = cursor.fetchall()

        # Get coordinates for the area (average of all crimes in this area)
        cursor.execute("""
            SELECT 
                AVG(latitude) as avg_lat,
                AVG(longitude) as avg_lng,
                COUNT(*) as data_points
            FROM crimes 
            WHERE area = %s AND latitude IS NOT NULL AND longitude IS NOT NULL
        """, (area,))
        coords = cursor.fetchone()

        return {
            "area": area,
            "statistics": {
                "total_crimes": cast(Dict[str, Any], stats)["total_crimes"] or 0,
                "unique_crime_types": cast(Dict[str, Any], stats)["unique_crime_types"] or 0,
                "high_risk_percentage": round(cast(Dict[str, Any], stats)["high_risk_percentage"] or 0, 2),
                "medium_risk_percentage": round(cast(Dict[str, Any], stats)["medium_risk_percentage"] or 0, 2),
                "low_risk_percentage": round(cast(Dict[str, Any], stats)["low_risk_percentage"] or 0, 2),
                "data_coverage": {
                    "first_recorded": str(cast(Dict[str, Any], stats)["first_recorded"]) if cast(Dict[str, Any], stats)["first_recorded"] else None,
                    "last_recorded": str(cast(Dict[str, Any], stats)["last_recorded"]) if cast(Dict[str, Any], stats)["last_recorded"] else None
                }
            },
            "crime_type_breakdown": [
                {
                    "crime_type": cast(Dict[str, Any], row)["crime_type"],
                    "count": cast(Dict[str, Any], row)["count"],
                    "high_risk_rate": round(cast(Dict[str, Any], row)["high_risk_rate"] or 0, 2)
                }
                for row in crime_types
            ],
            "monthly_trend": [
                {
                    "month": cast(Dict[str, Any], row)["month"],
                    "crime_count": cast(Dict[str, Any], row)["crime_count"],
                    "high_risk_rate": round(cast(Dict[str, Any], row)["high_risk_rate"] or 0, 2)
                }
                for row in monthly_trend
            ],
            "risk_distribution": [
                {
                    "risk_level": cast(Dict[str, Any], row)["risk_level"],
                    "count": cast(Dict[str, Any], row)["count"]
                }
                for row in risk_distribution
            ],
            "coordinates": {
                "latitude": float(cast(Dict[str, Any], coords)["avg_lat"]) if cast(Dict[str, Any], coords)["avg_lat"] else None,
                "longitude": float(cast(Dict[str, Any], coords)["avg_lng"]) if cast(Dict[str, Any], coords)["avg_lng"] else None,
                "data_points": cast(Dict[str, Any], coords)["data_points"] or 0
            }
        }

    except Error as e:
        logger.error(f"Database error getting area analytics: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve area analytics")
    finally:
        cursor.close()
        conn.close()

@app.get("/api/areas/{area}/details")
def get_area_details(area: str):
    """Get detailed information about a specific area"""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        # Get basic area information from crimes data
        cursor.execute("""
            SELECT 
                area,
                COUNT(*) as total_crimes,
                MIN(crime_date) as first_incident,
                MAX(crime_date) as last_incident,
                AVG(latitude) as center_lat,
                AVG(longitude) as center_lng
            FROM crimes 
            WHERE area = %s
            GROUP BY area
        """, (area,))
        area_info = cursor.fetchone()

        if not area_info:
            raise HTTPException(status_code=404, detail="Area not found in crime data")

        # Get most common crime types
        cursor.execute("""
            SELECT crime_type, COUNT(*) as frequency
            FROM crimes 
            WHERE area = %s
            GROUP BY crime_type
            ORDER BY frequency DESC
            LIMIT 5
        """, (area,))
        common_crimes = cursor.fetchall()

        # Get risk level summary
        cursor.execute("""
            SELECT 
                risk_level,
                COUNT(*) as count,
                COUNT(*) * 100.0 / (SELECT COUNT(*) FROM crimes WHERE area = %s) as percentage
            FROM crimes 
            WHERE area = %s
            GROUP BY risk_level
            ORDER BY FIELD(risk_level, 'High', 'Medium', 'Low')
        """, (area, area))
        risk_summary = cursor.fetchall()

        # Get recent crimes (last 30 days)
        cursor.execute("""
            SELECT crime_type, crime_date, risk_level
            FROM crimes 
            WHERE area = %s AND crime_date >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
            ORDER BY crime_date DESC
            LIMIT 10
        """, (area,))
        recent_crimes = cursor.fetchall()

        # Calculate safety score based on risk distribution
        total_crimes = cast(Dict[str, Any], area_info)["total_crimes"] or 1
        high_risk_count = next((cast(Dict[str, Any], row)["count"] for row in risk_summary if cast(Dict[str, Any], row)["risk_level"] == "High"), 0)
        medium_risk_count = next((cast(Dict[str, Any], row)["count"] for row in risk_summary if cast(Dict[str, Any], row)["risk_level"] == "Medium"), 0)
        
        # Safety score: 100 - (high_risk_percentage * 0.7 + medium_risk_percentage * 0.3)
        high_risk_percentage = (high_risk_count / total_crimes) * 100
        medium_risk_percentage = (medium_risk_count / total_crimes) * 100
        safety_score = max(0, 100 - (high_risk_percentage * 0.7 + medium_risk_percentage * 0.3))

        return {
            "area": area,
            "total_crimes": cast(Dict[str, Any], area_info)["total_crimes"],
            "first_incident": str(cast(Dict[str, Any], area_info)["first_incident"]) if cast(Dict[str, Any], area_info)["first_incident"] else None,
            "last_incident": str(cast(Dict[str, Any], area_info)["last_incident"]) if cast(Dict[str, Any], area_info)["last_incident"] else None,
            "coordinates": {
                "latitude": float(cast(Dict[str, Any], area_info)["center_lat"]) if cast(Dict[str, Any], area_info)["center_lat"] else None,
                "longitude": float(cast(Dict[str, Any], area_info)["center_lng"]) if cast(Dict[str, Any], area_info)["center_lng"] else None
            },
            "common_crime_types": [
                {
                    "crime_type": cast(Dict[str, Any], row)["crime_type"],
                    "frequency": cast(Dict[str, Any], row)["frequency"]
                }
                for row in common_crimes
            ],
            "risk_summary": [
                {
                    "risk_level": cast(Dict[str, Any], row)["risk_level"],
                    "count": cast(Dict[str, Any], row)["count"],
                    "percentage": round(cast(Dict[str, Any], row)["percentage"] or 0, 2)
                }
                for row in risk_summary
            ],
            "recent_activity": [
                {
                    "crime_type": cast(Dict[str, Any], row)["crime_type"],
                    "date": str(cast(Dict[str, Any], row)["crime_date"]),
                    "risk_level": cast(Dict[str, Any], row)["risk_level"]
                }
                for row in recent_crimes
            ],
            "safety_metrics": {
                "safety_score": round(safety_score, 1),
                "risk_level": "High" if safety_score < 40 else "Medium" if safety_score < 70 else "Low",
                "trend": "stable"  # Could be calculated based on historical data
            }
        }

    except Error as e:
        logger.error(f"Database error getting area details: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve area details")
    finally:
        cursor.close()
        conn.close()

@app.get("/api/areas/{area}/heatmap")
def get_heatmap_data(area: str):  
    """Get heatmap data for crime density in a specific area"""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        # Get all crimes with coordinates for the area
        cursor.execute("""
            SELECT 
                latitude,
                longitude,
                crime_type,
                risk_level,
                crime_date
            FROM crimes 
            WHERE area = %s 
                AND latitude IS NOT NULL 
                AND longitude IS NOT NULL
            ORDER BY crime_date DESC
            LIMIT 1000
        """, (area,))
        crimes = cursor.fetchall()

        # Transform into heatmap format
        heatmap_data = []
        for crime in crimes:
            # Type hint: crime is a dictionary when cursor is created with dictionary=True
            crime_dict = cast(Dict[str, Any], crime)
            if crime_dict["latitude"] and crime_dict["longitude"]:
                heatmap_data.append({
                    "lat": float(crime_dict["latitude"]),
                    "lng": float(crime_dict["longitude"]),
                    "weight": 1.0,  # Base weight
                    "risk_level": crime_dict["risk_level"],
                    "crime_type": crime_dict["crime_type"],
                    "date": str(crime_dict["crime_date"])
                })

        # Calculate density clusters (simplified)
        clusters = []
        if heatmap_data:
            # Simple clustering by rounding coordinates
            cluster_map = {}
            for point in heatmap_data:
                cluster_key = f"{round(point['lat'], 3)},{round(point['lng'], 3)}"
                if cluster_key not in cluster_map:
                    cluster_map[cluster_key] = {
                        "lat": round(point['lat'], 3),
                        "lng": round(point['lng'], 3),
                        "count": 0,
                        "high_risk_count": 0
                    }
                cluster_map[cluster_key]["count"] += 1
                if point["risk_level"] == "High":
                    cluster_map[cluster_key]["high_risk_count"] += 1

            clusters = [
                {
                    "lat": cluster["lat"],
                    "lng": cluster["lng"],
                    "intensity": min(1.0, cluster["count"] / 10),  # Normalize intensity
                    "crime_count": cluster["count"],
                    "high_risk_ratio": cluster["high_risk_count"] / cluster["count"] if cluster["count"] > 0 else 0
                }
                for cluster in cluster_map.values()
            ]

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

    except Error as e:
        logger.error(f"Database error getting heatmap data: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve heatmap data")
    finally:
        cursor.close()
        conn.close()

@app.get("/api/areas/{area}/timeseries")
def get_time_series_data(
    area: str, 
    range: str = Query("7d", description="Time range: 7d, 30d, 90d, 1y")
):
    """Get time series data for crime trends in a specific area"""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        # Calculate date range
        end_date = datetime.now()
        if range == "7d":
            start_date = end_date - timedelta(days=7)
            group_format = "%Y-%m-%d"
        elif range == "30d":
            start_date = end_date - timedelta(days=30)
            group_format = "%Y-%m-%d"
        elif range == "90d":
            start_date = end_date - timedelta(days=90)
            group_format = "%Y-%m-%d"
        elif range == "1y":
            start_date = end_date - timedelta(days=365)
            group_format = "%Y-%m"
        else:
            start_date = end_date - timedelta(days=7)
            group_format = "%Y-%m-%d"

        # Get time series data
        cursor.execute(f"""
            SELECT 
                DATE_FORMAT(crime_date, '{group_format}') as period,
                COUNT(*) as total_crimes,
                SUM(CASE WHEN risk_level = 'High' THEN 1 ELSE 0 END) as high_risk_crimes,
                SUM(CASE WHEN risk_level = 'Medium' THEN 1 ELSE 0 END) as medium_risk_crimes,
                SUM(CASE WHEN risk_level = 'Low' THEN 1 ELSE 0 END) as low_risk_crimes
            FROM crimes 
            WHERE area = %s AND crime_date >= %s AND crime_date <= %s
            GROUP BY DATE_FORMAT(crime_date, '{group_format}')
            ORDER BY period
        """, (area, start_date.date(), end_date.date()))
        
        time_series = cursor.fetchall()

        # Get crime type trends
        cursor.execute(f"""
            SELECT 
                DATE_FORMAT(crime_date, '{group_format}') as period,
                crime_type,
                COUNT(*) as count
            FROM crimes 
            WHERE area = %s AND crime_date >= %s AND crime_date <= %s
            GROUP BY DATE_FORMAT(crime_date, '{group_format}'), crime_type
            ORDER BY period, count DESC
        """, (area, start_date.date(), end_date.date()))
        
        crime_type_trends = cursor.fetchall()

        # Format the response
        formatted_series = []
        crime_type_data = {}

        for row in time_series:
            period_data = {
                "period": cast(Dict[str, Any], row)["period"],
                "total_crimes": cast(Dict[str, Any], row)["total_crimes"],
                "high_risk_crimes": cast(Dict[str, Any], row)["high_risk_crimes"],
                "medium_risk_crimes": cast(Dict[str, Any], row)["medium_risk_crimes"],
                "low_risk_crimes": cast(Dict[str, Any], row)["low_risk_crimes"],
                "high_risk_percentage": round((cast(Dict[str, Any], row)["high_risk_crimes"] / cast(Dict[str, Any], row)["total_crimes"] * 100) if cast(Dict[str, Any], row)["total_crimes"] > 0 else 0, 2)
            }
            formatted_series.append(period_data)

        # Organize crime type trends
        for row in crime_type_trends:
            period = cast(Dict[str, Any], row)["period"]
            crime_type = cast(Dict[str, Any], row)["crime_type"]
            count = cast(Dict[str, Any], row)["count"]
            
            if crime_type not in crime_type_data:
                crime_type_data[crime_type] = []
            
            crime_type_data[crime_type].append({
                "period": period,
                "count": count
            })

        return {
            "area": area,
            "time_range": range,
            "time_series": formatted_series,
            "crime_type_trends": crime_type_data,
            "summary": {
                "total_periods": len(formatted_series),
                "total_crimes": sum(row["total_crimes"] for row in formatted_series),
                "avg_crimes_per_period": round(sum(row["total_crimes"] for row in formatted_series) / len(formatted_series), 2) if formatted_series else 0,
                "trend": calculate_trend(formatted_series)
            }
        }

    except Error as e:
        logger.error(f"Database error getting time series data: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve time series data")
    finally:
        cursor.close()
        conn.close()

def calculate_trend(time_series):
    """Calculate trend based on time series data"""
    if len(time_series) < 2:
        return "insufficient_data"
    
    first_half = time_series[:len(time_series)//2]
    second_half = time_series[len(time_series)//2:]
    
    first_avg = sum(row["total_crimes"] for row in first_half) / len(first_half)
    second_avg = sum(row["total_crimes"] for row in second_half) / len(second_half)
    
    if second_avg > first_avg * 1.1:
        return "increasing"
    elif second_avg < first_avg * 0.9:
        return "decreasing"
    else:
        return "stable"

@app.get("/api/areas/{area}/comparison")
def get_area_comparison(area: str):  
    """Compare the specified area with other areas"""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        # Get statistics for the target area
        cursor.execute("""
            SELECT 
                area,
                COUNT(*) as total_crimes,
                AVG(CASE WHEN risk_level = 'High' THEN 1 ELSE 0 END) * 100 as high_risk_percentage,
                COUNT(DISTINCT crime_type) as unique_crime_types,
                COUNT(*) / (SELECT COUNT(*) FROM crimes) * 100 as percentage_of_total_crimes
            FROM crimes 
            WHERE area = %s
            GROUP BY area
        """, (area,))
        target_area = cursor.fetchone()

        if not target_area:
            raise HTTPException(status_code=404, detail="Area not found")

        # Get statistics for all areas for comparison
        cursor.execute("""
            SELECT 
                area,
                COUNT(*) as total_crimes,
                AVG(CASE WHEN risk_level = 'High' THEN 1 ELSE 0 END) * 100 as high_risk_percentage,
                COUNT(DISTINCT crime_type) as unique_crime_types,
                COUNT(*) / (SELECT COUNT(*) FROM crimes) * 100 as percentage_of_total_crimes
            FROM crimes 
            GROUP BY area
            HAVING total_crimes > 0
            ORDER BY total_crimes DESC
            LIMIT 20
        """)
        all_areas = cursor.fetchall()

        # Calculate rankings
        sorted_by_crime_count = sorted(all_areas, key=lambda x: cast(Dict[str, Any], x)["total_crimes"], reverse=True)
        sorted_by_risk = sorted(all_areas, key=lambda x: cast(Dict[str, Any], x)["high_risk_percentage"], reverse=True)

        target_crime_count = cast(Dict[str, Any], target_area)["total_crimes"]
        target_risk_percentage = cast(Dict[str, Any], target_area)["high_risk_percentage"]

        crime_rank = next((i + 1 for i, a in enumerate(sorted_by_crime_count) if cast(Dict[str, Any], a)["area"] == area), None)
        risk_rank = next((i + 1 for i, a in enumerate(sorted_by_risk) if cast(Dict[str, Any], a)["area"] == area), None)

        # Get similar areas (by crime count and risk profile)
        similar_areas = []
        for other_area in all_areas:
            if cast(Dict[str, Any], other_area)["area"] != area:
                crime_count_diff = abs(cast(Dict[str, Any], other_area)["total_crimes"] - target_crime_count) / target_crime_count
                risk_diff = abs(cast(Dict[str, Any], other_area)["high_risk_percentage"] - target_risk_percentage)
                
                if crime_count_diff < 0.3 and risk_diff < 15:  # Within 30% crime count and 15% risk difference
                    similar_areas.append(other_area)

        # Get top 5 highest and lowest risk areas
        top_risk_areas = sorted_by_risk[:5]
        lowest_risk_areas = sorted_by_risk[-5:]

        return {
            "target_area": {
                "name": area,
                "total_crimes": cast(Dict[str, Any], target_area)["total_crimes"],
                "high_risk_percentage": round(cast(Dict[str, Any], target_area)["high_risk_percentage"] or 0, 2),
                "unique_crime_types": cast(Dict[str, Any], target_area)["unique_crime_types"],
                "percentage_of_total_crimes": round(cast(Dict[str, Any], target_area)["percentage_of_total_crimes"] or 0, 2)
            },
            "rankings": {
                "crime_count_rank": crime_rank,
                "risk_rank": risk_rank,
                "total_areas_compared": len(all_areas)
            },
            "comparison_metrics": {
                "average_crimes_per_area": round(sum(cast(Dict[str, Any], a)["total_crimes"] for a in all_areas) / len(all_areas), 2),
                "average_high_risk_percentage": round(sum(cast(Dict[str, Any], a)["high_risk_percentage"] or 0 for a in all_areas) / len(all_areas), 2),
                "target_vs_average": {
                    "crime_count_ratio": round(target_crime_count / (sum(cast(Dict[str, Any], a)["total_crimes"] for a in all_areas) / len(all_areas)), 2),
                    "risk_ratio": round((target_risk_percentage or 0) / (sum(cast(Dict[str, Any], a)["high_risk_percentage"] or 0 for a in all_areas) / len(all_areas)), 2)
                }
            },
            "similar_areas": [
                {
                    "name": cast(Dict[str, Any], area)["area"],
                    "total_crimes": cast(Dict[str, Any], area)["total_crimes"],
                    "high_risk_percentage": round(cast(Dict[str, Any], area)["high_risk_percentage"] or 0, 2),
                    "crime_count_similarity": round(1 - abs(cast(Dict[str, Any], area)["total_crimes"] - target_crime_count) / target_crime_count, 2),
                    "risk_similarity": round(1 - abs((cast(Dict[str, Any], area)["high_risk_percentage"] or 0) - target_risk_percentage) / 100, 2)
                }
                for area in similar_areas[:5]  # Limit to top 5 most similar
            ],
            "benchmarks": {
                "highest_risk_areas": [
                    {
                        "name": cast(Dict[str, Any], area)["area"],
                        "high_risk_percentage": round(cast(Dict[str, Any], area)["high_risk_percentage"] or 0, 2),
                        "total_crimes": cast(Dict[str, Any], area)["total_crimes"]
                    }
                    for area in top_risk_areas
                ],
                "lowest_risk_areas": [
                    {
                        "name": cast(Dict[str, Any], area)["area"],
                        "high_risk_percentage": round(cast(Dict[str, Any], area)["high_risk_percentage"] or 0, 2),
                        "total_crimes": cast(Dict[str, Any], area)["total_crimes"]
                    }
                    for area in lowest_risk_areas
                ]
            }
        }

    except Error as e:
        logger.error(f"Database error getting area comparison: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve area comparison")
    finally:
        cursor.close()
        conn.close()

@app.get("/api/auth/me/alerts")
def get_user_alerts(
    current_user: str = Depends(get_username_from_token),
    limit: int = Query(50, description="Maximum number of alerts to return", ge=1, le=100),
    offset: int = Query(0, description="Number of alerts to skip", ge=0),
    unread_only: bool = Query(False, description="Return only unread alerts"),
    alert_type: Optional[str] = Query(None, description="Filter by alert type"),
    severity: Optional[str] = Query(None, description="Filter by severity")
):
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
        
        return {
            "alerts": all_alerts[:limit],  # Ensure we don't exceed limit
            "total_count": len(all_alerts),
            "unread_count": unread_count,
            "pagination": {
                "limit": limit,
                "offset": offset,
                "has_more": len(all_alerts) > limit
            }
        }
        
    except Error as e:
        logger.error(f"Database error getting user alerts: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve user alerts")
    finally:
        cursor.close()
        conn.close()

@app.post("/admin/alerts/system")
def create_system_alert(
    alert_data: AlertCreate,
    current_user: str = Depends(get_username_from_token)
):
    """Create a system-wide alert (admin only)"""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        # Check admin permissions
        cursor.execute("SELECT role FROM users_info WHERE username = %s", (current_user,))
        user = cursor.fetchone()
        if not user or cast(Dict[str, Any], user).get("role") not in ["superadmin", "admin"]:
            raise HTTPException(status_code=403, detail="Admin access required")
        
        # Parse expiry date if provided
        expires_at = None
        if alert_data.expires_at:
            try:
                expires_at = datetime.fromisoformat(alert_data.expires_at.replace('Z', '+00:00'))
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid expiry date format")
        
        # Insert system alert
        cursor.execute("""
            INSERT INTO system_alerts 
            (title, message, alert_type, area, severity, created_by, created_at, expires_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            alert_data.title,
            alert_data.message,
            alert_data.alert_type,
            alert_data.area,
            alert_data.severity,
            current_user,
            datetime.now(),
            expires_at
        ))
        
        alert_id = cursor.lastrowid
        conn.commit()
        
        # Log the action
        log_user_activity(
            activity_type="system_alert_created",
            username=current_user,
            activity_details={
                "alert_id": alert_id,
                "title": alert_data.title,
                "severity": alert_data.severity,
                "area": alert_data.area
            }
        )
        
        return {"message": "System alert created", "alert_id": alert_id}
        
    except Error as e:
        logger.error(f"Database error creating system alert: {e}")
        raise HTTPException(status_code=500, detail="Failed to create system alert")
    finally:
        cursor.close()
        conn.close()

        
@app.post("/api/auth/me/alerts/{alert_id}/read")
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
        
        user_id = cast(Dict[str, Any], user).get("id")
        
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
        
    except Error as e:
        logger.error(f"Database error marking alert as read: {e}")
        raise HTTPException(status_code=500, detail="Failed to update alert")
    finally:
        cursor.close()
        conn.close()

@app.post("/api/auth/me/alerts/read-all")
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
        
        user_id = cast(Dict[str, Any], user).get("id")
        
        # Update all user alerts
        cursor.execute("""
            UPDATE user_alerts 
            SET is_read = TRUE 
            WHERE user_id = %s AND is_read = FALSE
        """, (user_id,))
        
        updated_count = cursor.rowcount
        conn.commit()
        
        return {"message": f"Marked {updated_count} alerts as read"}
        
    except Error as e:
        logger.error(f"Database error marking all alerts as read: {e}")
        raise HTTPException(status_code=500, detail="Failed to update alerts")
    finally:
        cursor.close()
        conn.close()


@app.post("/api/browser-notifications/read-all")
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
        
        user_id = cast(Dict[str, Any], user).get("id")
        
        # Mark all notifications as read
        cursor.execute("""
            UPDATE browser_notifications 
            SET is_read = TRUE 
            WHERE user_id = %s AND is_read = FALSE
        """, (user_id,))
        
        updated_count = cursor.rowcount
        conn.commit()
        
        return {
            "message": f"Marked {updated_count} notifications as read",
            "updated_count": updated_count
        }
        
    except Error as e:
        logger.error(f"Database error marking all browser notifications as read: {e}")
        raise HTTPException(status_code=500, detail="Failed to update notifications")
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()

@app.get("/api/community/alerts")
def get_community_alerts():
    """Get community alerts (basic implementation)"""
    try:
        # Return empty array for now, or implement real logic
        return {"alerts": []}
    except Exception as e:
        logger.error(f"Error getting community alerts: {e}")
        return {"alerts": []}

@app.get("/api/areas/{area}/coordinates")
def get_area_coordinates(area: str):
    """Get coordinates for a specific area from the database"""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        # Get coordinates from crimes data for this area
        cursor.execute("""
            SELECT 
                AVG(latitude) as avg_lat,
                AVG(longitude) as avg_lng,
                COUNT(*) as data_points
            FROM crimes 
            WHERE area = %s AND latitude IS NOT NULL AND longitude IS NOT NULL
        """, (area,))
        coords = cursor.fetchone()
        
        # Ensure the fetched row is treated as a mapping for type-checkers
        coords_dict = cast(Dict[str, Any], coords) if coords is not None else None

        if not coords_dict or not coords_dict.get("avg_lat") or not coords_dict.get("avg_lng"):
            # Fallback to geocoding if no coordinates in database
            geocoded_coords = get_coordinates(area)
            if geocoded_coords:
                lat, lng = geocoded_coords
                return {
                    "area": area,
                    "coordinates": {
                        "lat": lat,
                        "lng": lng
                    },
                    "source": "geocoding",
                    "data_points": 0
                }
            else:
                raise HTTPException(status_code=404, detail="No coordinates found for this area")
        
        # Safely convert averaged coordinates to floats, handling None values
        avg_lat_val = coords_dict.get("avg_lat")
        avg_lng_val = coords_dict.get("avg_lng")
        lat = float(avg_lat_val) if avg_lat_val is not None else None
        lng = float(avg_lng_val) if avg_lng_val is not None else None

        return {
            "area": area,
            "coordinates": {
                "lat": lat,
                "lng": lng
            },
            "source": "database",
            "data_points": coords_dict.get("data_points")
        }

    except Error as e:
        logger.error(f"Database error getting area coordinates: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve area coordinates")
    finally:
        cursor.close()
        conn.close()


@app.post("/api/test/trigger-monitoring")
async def trigger_monitoring_test():
    """Test endpoint to manually trigger saved location monitoring"""
    try:
        await monitor_saved_locations()
        return {"message": "✅ Saved location monitoring triggered successfully"}
    except Exception as e:
        logger.error(f"Test monitoring error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
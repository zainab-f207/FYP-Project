from fastapi import FastAPI, Query, HTTPException, Depends, BackgroundTasks
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
import os
from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional, cast
import secrets
import string
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta

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
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from mysql.connector import Error

# Add the backend directory to Python path for absolute imports
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from app.auth_updated import create_access_token, get_password_hash, verify_password, verify_token
from app.auth_routes import router as auth_router

from app.core.config import ALLOWED_ORIGINS, MODEL_DIR, get_api_title, get_logger
from app.core.database import get_db_connection, initialize_schema, log_user_activity
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
    from crime_risk_model.utils.helpers import engineer_features, interpret_clusters, assign_individual_risk_levels, load_model, load_risk_mapping
except ImportError:
    # Fallback for when running directly
    sys.path.append(os.path.dirname(__file__))
    from crime_risk_model.utils.helpers import engineer_features, interpret_clusters, assign_individual_risk_levels, load_model, load_risk_mapping

logger = get_logger(__name__)

# Email configuration
# SMTP_SERVER = "smtp.gmail.com"  # Change to your SMTP server
# SMTP_PORT = 587
# SMTP_USERNAME = "safevision.noreply@gmail.com"  # Replace with your email
# SMTP_PASSWORD = "dzik alfk tgxy banc"  # Replace with your app password


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
app = FastAPI(title="CrimeVision API")
app.include_router(auth_router)

# Import password reset functions and models
from app.password_reset_fixed import forgot_password, reset_password, ForgotPasswordRequest, ResetPasswordRequest

@app.on_event("startup")
def on_startup() -> None:
    """Prepare database schema when the application starts."""
    try:
        initialize_schema()
    except Error as exc:
        logger.error("Startup schema initialization failed", exc_info=exc)
        raise

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files for profile photos
app.mount("/profile_photos", StaticFiles(directory="profile_photos"), name="profile_photos")


@app.get("/")
def root():
    return {"message": "Welcome to CrimeVision API. Go to /api/crimes"}

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

        # Get coordinates for home area if provided
        home_lat, home_lon = None, None
        if user.home_area:
            coords = get_coordinates(user.home_area)
            if coords:
                home_lat, home_lon = coords

        # Generate email verification token
        verification_token = secrets.token_urlsafe(32)
        token_expires_at = datetime.utcnow() + timedelta(hours=24)  # Token expires in 24 hours

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
                return {"requires_2fa": True, "message": "Two-factor authentication code required"}
            secret = get_user_2fa_secret(user_id)
            if not secret or not verify_2fa_code(secret, user.two_factor_code):
                raise HTTPException(status_code=401, detail="Invalid two-factor authentication code")
            log_user_activity(
                activity_type="2fa_verified",
                username=cast(Dict[str, Any], db_user).get("username"),
                user_id=user_id,
                activity_details={"message": "Two-factor authentication code verified successfully."},
            )

        # Create access token
        access_token = create_access_token(data={"sub": cast(Dict[str, Any], db_user).get("username")})
        log_user_activity(
            activity_type="login_success",
            username=cast(Dict[str, Any], db_user).get("username"),
            user_id=cast(Dict[str, Any], db_user).get("id"),
            activity_details={"message": "User logged in successfully."},
        )
        return {"access_token": access_token, "token_type": "bearer"}

    except HTTPException as ex:
        if ex.status_code == 401:
            log_user_activity(
                activity_type="login_failed",
                username=user.email,  # Use email for failed login logging
                activity_details={"message": "Failed login attempt."},
            )
        raise
    except Error as e:
        logger.error(f"Database error during login: {e}")
        raise HTTPException(status_code=500, detail="Database error")
    finally:
        cursor.close()
        conn.close()

security = HTTPBearer()
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
        cursor.execute("SELECT id, username, first_name, last_name, email, profile_picture, home_area, work_area, alert_radius, role, created_at FROM users_info WHERE LOWER(username) = LOWER(%s)", (current_user.lower(),))
        user = cursor.fetchone()

        if not user:
            raise HTTPException(status_code=401, detail="Invalid session - user not found")

        # Get user ID for 2FA check
        user_id = cast(Dict[str, Any], user).get("id")

        # Check if 2FA is enabled for this user
        two_factor_enabled = False
        if user_id:
            try:
                two_factor_enabled = is_2fa_enabled(user_id)
            except Exception as e:
                logger.warning(f"Error checking 2FA status for user {current_user}: {e}")
                two_factor_enabled = False

        # Log user data for debugging
        logger.info(f"User data retrieved for {current_user}: {user}")

        return {
            "username": cast(Dict[str, Any], user).get("username", ""),
            "first_name": cast(Dict[str, Any], user).get("first_name", ""),
            "last_name": cast(Dict[str, Any], user).get("last_name", ""),
            "email": cast(Dict[str, Any], user).get("email", ""),
            "profile_picture": cast(Dict[str, Any], user).get("profile_picture"),
            "home_area": cast(Dict[str, Any], user).get("home_area"),
            "work_area": cast(Dict[str, Any], user).get("work_area"),
            "alert_radius": cast(Dict[str, Any], user).get("alert_radius", 5),
            "role": cast(Dict[str, Any], user).get("role", "user"),
            "two_factor_enabled": two_factor_enabled,
            "created_at": cast(Dict[str, Any], user).get("created_at", "")
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
class UserProfileUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    profile_picture: Optional[str] = None
    home_area: Optional[str] = None
    work_area: Optional[str] = None
    alert_radius: Optional[int] = Field(None, ge=1, le=50)

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

@app.put("/auth/update-profile")
def update_user_profile(
    profile_data: UserProfileUpdate,
    current_user: str = Depends(get_username_from_token)
):
    """Update user's profile information including profile picture"""
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        update_fields = []
        params = []

        if profile_data.first_name is not None:
            update_fields.append("first_name = %s")
            params.append(validate_name(profile_data.first_name))

        if profile_data.last_name is not None:
            update_fields.append("last_name = %s")
            params.append(validate_name(profile_data.last_name))

        if profile_data.email is not None:
            update_fields.append("email = %s")
            params.append(profile_data.email)

        if profile_data.profile_picture is not None:
            update_fields.append("profile_picture = %s")
            params.append(profile_data.profile_picture)

        if profile_data.home_area is not None:
            update_fields.append("home_area = %s")
            params.append(profile_data.home_area)

        if profile_data.work_area is not None:
            update_fields.append("work_area = %s")
            params.append(profile_data.work_area)

        if profile_data.alert_radius is not None:
            update_fields.append("alert_radius = %s")
            params.append(profile_data.alert_radius)

        if not update_fields:
            raise HTTPException(status_code=400, detail="No fields to update")

        params.append(current_user)
        query = f"UPDATE users_info SET {', '.join(update_fields)} WHERE username = %s"

        cursor.execute(query, params)
        conn.commit()

        log_user_activity(
            activity_type="profile_update",
            username=current_user,
            activity_details={
                "updated_fields": [field.split(" = ")[0] for field in update_fields],
            },
        )

        return {"message": "Profile updated successfully"}

    except Error as e:
        logger.error(f"Database error updating profile: {e}")
        raise HTTPException(status_code=500, detail="Database error")
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

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)

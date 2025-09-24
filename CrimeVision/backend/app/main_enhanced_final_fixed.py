from fastapi import FastAPI, Query, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import List, Optional, Any, TypedDict, Dict, cast
import mysql.connector
from mysql.connector import Error
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from datetime import timedelta
from auth_updated import verify_password, get_password_hash, create_access_token, verify_token
from dotenv import load_dotenv
import os
import logging
from datetime import datetime
import re
import joblib
import pandas as pd
import numpy as np
import sys
import difflib
import requests
import json
import time
sys.path.append(os.path.join(os.path.dirname(__file__), 'crime_risk_model'))
# Import crime risk model utilities - these will be available when running from backend directory
try:
    from crime_risk_model.utils.helpers import engineer_features, interpret_clusters, assign_individual_risk_levels, load_model, load_risk_mapping
except ImportError:
    # Fallback for when running directly
    import sys
    import os
    sys.path.append(os.path.dirname(__file__))
    from crime_risk_model.utils.helpers import engineer_features, interpret_clusters, assign_individual_risk_levels, load_model, load_risk_mapping

# -------------------------------
# TypedDict for DB rows
# -------------------------------
class CrimeRow(TypedDict):
    id: int
    area: str
    crime_type: str  # Changed from 'type' to 'crime_type' to match database schema
    date: str
    latitude: float
    longitude: float
    risk_level: str

class CrimeTypeRow(TypedDict):
    crime_type: str

load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load ML model and encoders
MODEL_DIR = os.path.join(os.path.dirname(__file__),'predict_risk_level', 'model')
try:
    model = joblib.load(os.path.join(MODEL_DIR, 'random_forest_model.joblib'))
    le_area = joblib.load(os.path.join(MODEL_DIR, 'label_encoder_area.joblib'))
    le_crime = joblib.load(os.path.join(MODEL_DIR, 'label_encoder_crime.joblib'))
    le_risk = joblib.load(os.path.join(MODEL_DIR, 'label_encoder_risk.joblib'))
    logger.info(f"Looking for model files in: {MODEL_DIR}")
    logger.info(f"Random Forest model loaded successfully: {type(model)}")
    logger.info(f"le_area.classes_[:5]: {le_area.classes_[:5]}")
    logger.info(f"le_crime.classes_[:5]: {le_crime.classes_[:5]}")
    logger.info(f"le_risk.classes_: {le_risk.classes_}")
    # Check if any of the encoders have empty classes, which would cause model to be None
    if len(le_area.classes_) == 0 or len(le_crime.classes_) == 0 or len(le_risk.classes_) == 0:
        logger.warning("One or more label encoders have empty classes, setting model to None")
        model = None
        le_area = None
        le_crime = None
        le_risk = None
except Exception as e:
    logger.warning(f"Could not load Gradient Boosting model: {e}")
    model = None
    le_area = None
    le_crime = None
    le_risk = None

# CORS configuration - FIXED
ALLOWED_ORIGINS_STR = os.getenv("ALLOWED_ORIGINS", "http://localhost:5173, http://localhost:5174, http://127.0.0.1:5173, http://127.0.0.1:5174")
ALLOWED_ORIGINS = [origin.strip() for origin in ALLOWED_ORIGINS_STR.split(",")]

# Database config
DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", "hafsa555"),
    "database": os.getenv("DB_NAME", "crimevision_db"),
    "port": int(os.getenv("DB_PORT", 3306)),
}

# Response model
class Crime(BaseModel):
    id: int = Field(..., ge=1, description="Crime ID")
    area: str = Field(..., min_length=1, max_length=100, description="Crime area/location")
    type: str = Field(..., min_length=1, max_length=50, description="Crime type")
    date: str = Field(..., description="Crime date in YYYY-MM-DD format")
    coordinates: List[float] = Field(..., min_length=2, max_length=2, description="[latitude, longitude]")
    risk_level: str = Field(..., min_length=1, max_length=20, description="Risk level")

# Request model for predict risk
class PredictRiskRequest(BaseModel):
    area: str
    crime_type: str
    date: Optional[str] = None

# Request model for new crime
class NewCrimeRequest(BaseModel):
    crime_type: str = Field(..., min_length=1, max_length=100, description="Crime type")
    area: str = Field(..., min_length=1, max_length=100, description="Area")
    date: str = Field(..., description="Crime date in YYYY-MM-DD format")
    latitude: float = Field(..., description="Latitude")
    longitude: float = Field(..., description="Longitude")

# Request model for creating a crime record
class CrimeCreate(BaseModel):
    crime_type: str = Field(..., min_length=1, max_length=100, description="Crime type")
    area: str = Field(..., min_length=1, max_length=100, description="Area")
    date: Optional[str] = Field(None, description="Crime date in YYYY-MM-DD format (defaults to current date)")
    latitude: Optional[float] = Field(None, description="Latitude")
    longitude: Optional[float] = Field(None, description="Longitude")

# Authentication models
class UserRegister(BaseModel):
    first_name: str = Field(..., min_length=1, max_length=50, description="First name")
    last_name: str = Field(..., min_length=1, max_length=50, description="Last name")
    email: str = Field(..., description="Email address")
    password: str = Field(..., min_length=6, description="Password")
    home_area: Optional[str] = Field(None, description="User's home area")

class UserLogin(BaseModel):
    username: str = Field(..., description="Username")
    password: str = Field(..., description="Password")

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

# Location models
class LocationRequest(BaseModel):
    area: str = Field(..., description="Area name to get coordinates for")

class LocationResponse(BaseModel):
    area: str
    latitude: float
    longitude: float
    source: str = Field(..., description="Source of coordinates (api, database, cache)")

class UserLocationUpdate(BaseModel):
    home_area: Optional[str] = None
    work_area: Optional[str] = None
    alert_radius: Optional[int] = Field(None, ge=1, le=50, description="Alert radius in km")

# JWT Security
security = HTTPBearer()

# -------------------------------
# Helper Functions
# -------------------------------
def generate_username(first_name: str, last_name: str) -> str:
    """Generate username from first name and last name"""
    base_username = f"{first_name.lower()}.{last_name.lower()}"
    username = base_username

    # Check if username already exists and add number if needed
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        counter = 1
        while True:
            cursor.execute("SELECT id FROM users_info WHERE username = %s", (username,))
            if not cursor.fetchone():
                break
            username = f"{base_username}{counter}"
            counter += 1
    except Error as e:
        logger.error(f"Database error checking username: {e}")
    finally:
        cursor.close()
        conn.close()

    return username

def validate_name(name: str) -> str:
    """Validate and sanitize name input"""
    sanitized = re.sub(r'[^\w\s\-_]', '', name.strip())
    if not sanitized:
        raise HTTPException(status_code=400, detail="Invalid name format")
    return sanitized[:50]

# -------------------------------
# Geocoding Functions
# -------------------------------
def get_coordinates_from_api(area_name: str) -> Optional[tuple[float, float]]:
    """Get coordinates using Nominatim API"""
    try:
        url = "https://nominatim.openstreetmap.org/search"
        params = {
            'q': f"{area_name}, Pakistan",
            'format': 'json',
            'limit': 1,
            'countrycodes': 'pk'
        }

        headers = {
            'User-Agent': 'CrimeVision/1.0'
        }

        response = requests.get(url, params=params, headers=headers, timeout=10)
        response.raise_for_status()

        data = response.json()
        if data:
            lat = float(data[0]['lat'])
            lon = float(data[0]['lon'])
            return lat, lon

    except Exception as e:
        logger.warning(f"Geocoding API error for {area_name}: {e}")

    return None

def get_coordinates_from_database(area_name: str) -> Optional[tuple[float, float]]:
    """Get coordinates from local database"""
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            "SELECT latitude, longitude FROM area_coordinates WHERE area_name = %s",
            (area_name,)
        )
        result = cursor.fetchone()

        if result:
            # Fix: Handle None values and different data types properly
            lat_val = result[0]
            lon_val = result[1]
            if lat_val is not None and lon_val is not None:
                try:
                    # Convert to string first to handle different data types
                    lat_str = str(lat_val).strip()
                    lon_str = str(lon_val).strip()
                    return float(lat_str), float(lon_str)
                except (ValueError, TypeError, AttributeError):
                    return None
            return None

    except Error as e:
        logger.error(f"Database error getting coordinates: {e}")
    finally:
        cursor.close()
        conn.close()

    return None

def save_coordinates_to_database(area_name: str, lat: float, lon: float):
    """Save coordinates to database for future use"""
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            "INSERT INTO area_coordinates (area_name, latitude, longitude) VALUES (%s, %s, %s)",
            (area_name, lat, lon)
        )
        conn.commit()
        logger.info(f"Saved coordinates for {area_name} to database")

    except Error as e:
        logger.error(f"Error saving coordinates: {e}")
    finally:
        cursor.close()
        conn.close()

def get_coordinates(area_name: str) -> Optional[tuple[float, float]]:
    """Get coordinates using hybrid approach: API first, then database"""
    if not area_name or not area_name.strip():
        return None

    area_name = area_name.strip()

    # Try database first (faster)
    coords = get_coordinates_from_database(area_name)
    if coords:
        logger.info(f"Found coordinates for {area_name} in database")
        return coords

    # Try API if not in database
    coords = get_coordinates_from_api(area_name)
    if coords:
        logger.info(f"Got coordinates for {area_name} from API")
        # Save to database for future use
        save_coordinates_to_database(area_name, coords[0], coords[1])
        return coords

    return None

# -------------------------------
# Helpers
# -------------------------------
def validate_date_format(date_str: str) -> bool:
    """Validate date format YYYY-MM-DD with reasonable date range"""
    if not date_str or len(date_str) != 10:
        return False
    if not re.match(r'^\d{4}-\d{2}-\d{2}$', date_str):
        return False
    try:
        parsed_date = datetime.strptime(date_str, '%Y-%m-%d')
        current_year = datetime.now().year
        if not (1900 <= parsed_date.year <= current_year + 1):
            return False
        return True
    except ValueError:
        return False

def validate_crime_type(crime_type: str) -> str:
    """Validate and sanitize crime type input"""
    sanitized = re.sub(r'[^\w\s\-_]', '', crime_type.strip())
    if not sanitized:
        raise HTTPException(status_code=400, detail="Invalid crime type format")
    return sanitized[:50]

def get_db_connection():
    """Create a new DB connection each time"""
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        if conn.is_connected():
            return conn
        else:
            raise HTTPException(status_code=500, detail="Failed to connect to database")
    except Error as e:
        logger.error(f"Database connection failed: {e}")
        raise HTTPException(status_code=500, detail="Database connection failed")

# Create users table if it doesn't exist
def create_users_table():
    """Create users_info table for authentication with first_name and last_name"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS users_info (
            id INT AUTO_INCREMENT PRIMARY KEY,
            username VARCHAR(50) UNIQUE NOT NULL,
            first_name VARCHAR(50) NOT NULL,
            last_name VARCHAR(50) NOT NULL,
            email VARCHAR(100) UNIQUE NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            profile_picture VARCHAR(255) DEFAULT NULL,
            home_area VARCHAR(100),
            home_latitude DECIMAL(10, 8),
            home_longitude DECIMAL(11, 8),
            work_area VARCHAR(100),
            work_latitude DECIMAL(10, 8),
            work_longitude DECIMAL(11, 8),
            alert_radius INT DEFAULT 5,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        conn.commit()
        logger.info("Users_info table created successfully")
    except Error as e:
        logger.error(f"Error creating users_info table: {e}")
        raise HTTPException(status_code=500, detail="Database error")
    finally:
        cursor.close()
        conn.close()

# Create area coordinates table
def create_area_coordinates_table():
    """Create area coordinates table for caching geocoding results"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS area_coordinates (
                id INT AUTO_INCREMENT PRIMARY KEY,
                area_name VARCHAR(100) UNIQUE NOT NULL,
                latitude DECIMAL(10, 8) NOT NULL,
                longitude DECIMAL(11, 8) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_area_name (area_name)
            )
        """)
        conn.commit()
        logger.info("Area coordinates table created successfully")
    except Error as e:
        logger.error(f"Error creating area coordinates table: {e}")
    finally:
        cursor.close()
        conn.close()

# Initialize tables on startup
create_users_table()
create_area_coordinates_table()

# -------------------------------
# FastAPI app + endpoint
# -------------------------------
app = FastAPI(title="CrimeVision API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {"message": "Welcome to CrimeVision API. Go to /api/crimes"}

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
@app.post("/auth/register", response_model=Token)
def register(user: UserRegister):
    """Register a new user with auto-generated username"""
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

        # Create user
        cursor.execute(
            "INSERT INTO users_info (username, first_name, last_name, email, password_hash, home_area, home_latitude, home_longitude) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
            (username, first_name, last_name, user.email, password_hash, user.home_area, home_lat, home_lon)
        )
        conn.commit()

        # Create access token
        access_token = create_access_token(data={"sub": username})
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "username": username,
            "message": f"User registered successfully. Your username is: {username}"
        }

    except Error as e:
        logger.error(f"Database error during registration: {e}")
        raise HTTPException(status_code=500, detail="Database error")
    finally:
        cursor.close()
        conn.close()

@app.post("/auth/login", response_model=Token)
def login(user: UserLogin):
    """Login user and return JWT token"""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        # Get user from database
        cursor.execute("SELECT username, password_hash FROM users_info WHERE username = %s", (user.username,))
        db_user = cursor.fetchone()

        if not db_user:
            raise HTTPException(status_code=401, detail="Invalid credentials")

        # Verify password
        password_hash = cast(Dict[str, Any], db_user).get("password_hash", "")
        if not verify_password(user.password, password_hash):
            raise HTTPException(status_code=401, detail="Invalid credentials")

        # Create access token
        access_token = create_access_token(data={"sub": user.username})
        return {"access_token": access_token, "token_type": "bearer"}

    except Error as e:
        logger.error(f"Database error during login: {e}")
        raise HTTPException(status_code=500, detail="Database error")
    finally:
        cursor.close()
        conn.close()

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Get current user from JWT token"""
    token = credentials.credentials
    username = verify_token(token)
    if username is None:
        raise HTTPException(status_code=401, detail="Invalid token")
    return username

@app.get("/auth/me")
def get_current_user_info(current_user: str = Depends(get_current_user)):
    """Get current user information"""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT username, first_name, last_name, email, profile_picture, home_area, work_area, alert_radius, created_at FROM users_info WHERE username = %s", (current_user,))
        user = cursor.fetchone()

        if not user:
            raise HTTPException(status_code=404, detail="User not found")

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
    current_user: str = Depends(get_current_user)
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

@app.put("/auth/update-profile")
def update_user_profile(
    profile_data: UserProfileUpdate,
    current_user: str = Depends(get_current_user)
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

        return {"message": "Profile updated successfully"}

    except Error as e:
        logger.error(f"Database error updating profile: {e}")
        raise HTTPException(status_code=500, detail="Database error")
    finally:
        cursor.close()
        conn.close()

from fastapi import UploadFile, File

@app.post("/auth/upload-profile-photo")
async def upload_profile_photo(
    file: UploadFile = File(...),
    current_user: str = Depends(get_current_user)
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

                    features_df = pd.DataFrame(
                        [[area_enc, crime_type_enc, year, month, day, weekday]],
                        columns=['area_enc', 'crime_type_enc', 'year', 'month', 'day', 'weekday']
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

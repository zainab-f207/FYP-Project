
from fastapi import FastAPI, Query, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional, Any, TypedDict, Dict, cast
import mysql.connector
from mysql.connector import Error
from fastapi.middleware.cors import CORSMiddleware
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
sys.path.append(os.path.join(os.path.dirname(__file__), 'crime_risk_model'))
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
                crime_record = Crime(
                    id=int(cast(Dict[str, Any], row)["id"]),
                    area=cast(Dict[str, Any], row).get("area", "Unknown"),
                    type=cast(Dict[str, Any], row).get("crime_type", "Unknown"),
                    date=str(cast(Dict[str, Any], row).get("crime_date", "Unknown")),
                    coordinates=[
                        float(cast(Dict[str, Any], row).get("latitude", 0.0)),
                        float(cast(Dict[str, Any], row).get("longitude", 0.0))
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
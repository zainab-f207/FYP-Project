import os
import re
from fastapi import APIRouter
from fastapi.security import HTTPBearer
from pydantic import BaseModel, Field, field_validator 
from typing import Optional, List, Dict, Any, Union
from datetime import datetime

# Auth Models
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
    username: str
    home_area: Optional[str] = None
    phone_number: Optional[str] = None

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "1062377219587-u12ic1km1lus47l8vl813mmib0p7cjsp.apps.googleusercontent.com")

router = APIRouter()
security = HTTPBearer()

class GoogleAuthRequest(BaseModel):
    credential: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    home_area: Optional[str] = None
    phone_number: Optional[str] = None

class GoogleAuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: Dict[str, Any]
    is_new_user: bool
class GoogleRegister(BaseModel):
    first_name: str
    last_name: str
    email: str  
    home_area: Optional[str] = None
    work_area: Optional[str] = None
    phone_number: Optional[str] = None
    alert_radius: Optional[int] = 5
    credential: str
    two_factor_code: Optional[str] = None
    profile_picture: Optional[str] = None
    @field_validator('email')
    @classmethod
    def validate_email(cls, v):
        if not v:
            raise ValueError('Email is required')
        email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_regex, v):
            raise ValueError('Invalid email format')
        return v

class UserLogin(BaseModel):
    email: str
    password: str
    two_factor_code: Optional[str] = None

class RegistrationResponse(BaseModel):
    message: str

class ResendVerificationRequest(BaseModel):
    email: str

# User Profile Models
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
    email_alerts_enabled: Optional[bool] = None
    monitor_live_location: Optional[bool] = None
    weekly_reports_enabled: Optional[bool] = None
    incident_alerts_enabled: Optional[bool] = None
    live_alerts_enabled: Optional[bool] = None
    alert_channel_preferences: Optional[Dict[str, Dict[str, bool]]] = None


class UserLocationUpdate(BaseModel):
    home_area: Optional[str] = None
    work_area: Optional[str] = None
    alert_radius: Optional[int] = None

# Location Models
class LocationRequest(BaseModel):
    area: str

class LocationResponse(BaseModel):
    area: str
    latitude: float
    longitude: float
    source: str

class LocationAlertRequest(BaseModel):
    latitude: float
    longitude: float
    address: Optional[str] = None
    check_immediate: bool = True

# Alert Models
class AlertSubscription(BaseModel):
    user_id: int
    alert_types: List[str] = ["crime", "safety", "emergency"]
    areas: List[str] = []
    radius: float = 5.0  # in km
    notification_types: List[str] = ["email", "browser"]
    is_active: bool = True
    monitor_live_location: bool = False
    monitor_saved_locations: bool = True

class RiskZoneAlert(BaseModel):
    user_id: int
    username: str
    email: str
    phone: Optional[str] = None
    latitude: float
    longitude: float
    address: str
    area_translit: Optional[str] = None   # Roman transliteration of the Urdu area name
    area_urdu: Optional[str] = None       # Original Urdu script area name
    risk_level: str
    safety_score: float
    risk_pct: Optional[float] = None      # Poisson probability % (continuous risk score)
    high_risk_crimes: int
    medium_risk_crimes: int = 0
    high_risk_crimes_90d: int = 0
    medium_risk_crimes_90d: int = 0
    last_90_days: int = 0
    total_crimes: int = 0
    total_crimes_365: int = 0
    no_recent_but_historical: bool = False
    subareas: Optional[List[Dict[str, Any]]] = None  # [{name, urdu, risk_level, risk_pct, total, dominant_crime}]
    top_crimes_list: Optional[List[Dict[str, Any]]] = None  # [{crime_type, count, risk_level}] top actual crimes
    dominant_crime_type: Optional[str] = None  # Most frequent crime type in the area
    recent_7d_crimes: int = 0             # Crime count in last 7 days (for alert trigger transparency)
    time_risk_label: Optional[str] = None # "Morning", "Afternoon", "Evening", "Night" + relative risk
    alert_trigger_reason: Optional[str] = None  # Human-readable explanation of why alert was triggered
    alert_type: str = "high_risk_zone"
    severity: str = "high"
    location_type: str = "monitored"      # "home", "work", "current", "monitored"
    incident_type: Optional[str] = None   # For new incident alerts (e.g. "Murder")
    distance_km: Optional[float] = None   # For proximity alerts
    radius_km: Optional[float] = None     # Effective policy radius used for this alert
    timestamp: Optional[str] = None       # Generation time
    precautions: Optional[str] = None
    incidents_list: Optional[List[Dict[str, Any]]] = None  # [{type, time, severity}]
    message: str

class AlertCreate(BaseModel):
    title: str
    message: str
    alert_type: str = "info"
    area: Optional[str] = None
    severity: str = "medium"
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
    priority: int

# Crime Models
class Crime(BaseModel):
    id: int
    area: str
    area_urdu: Optional[str] = None        # Original Urdu area name from OCR
    area_translit: Optional[str] = None   # Transliterated Roman form (Microsoft Translator)
    type: str
    date: str        # Combined "YYYY-MM-DD HH:MM:SS" when time is available, else "YYYY-MM-DD"
    crime_time: Optional[str] = None       # Raw time string stored in DB (e.g. "03:22 AM")
    coordinates: List[float]
    risk_level: str

class PredictRiskRequest(BaseModel):
    area: str
    crime_type: str
    date: Optional[str] = None
    time: Optional[str] = None         # e.g. "22:00", "10:30 PM", "14:00:00"

class CrimeCreate(BaseModel):
    area: str
    crime_type: str
    date: Optional[str] = None
    crime_time: Optional[str] = None       # e.g. "08:53 PM"
    area_urdu: Optional[str] = None        # original Urdu text if entered
    area_translit: Optional[str] = None   # Roman transliteration
    latitude: Optional[float] = None
    longitude: Optional[float] = None

# Emergency Models
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

# Admin Models
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

# Password Reset Models
class ForgotPasswordRequest(BaseModel):
    email: str

class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str

# Location Tracking Models
class LocationUpdateRequest(BaseModel):
    latitude: float
    longitude: float
    accuracy: Optional[float] = None
    timestamp: Optional[datetime] = None
    address: Optional[str] = None
    location_source: Optional[str] = "gps"  # Source of location data: 'gps', 'ip_fallback', etc.
    device_type: Optional[str] = "desktop"  # Device type: 'mobile', 'desktop', 'tablet'

class LocationHistoryResponse(BaseModel):
    id: int
    user_id: int
    latitude: float
    longitude: float
    accuracy: Optional[float]
    address: Optional[str]
    risk_level: Optional[str]
    safety_score: Optional[float]
    created_at: str
    location_source: Optional[str] = "gps"

class LocationTrackingPreferences(BaseModel):
    enabled: bool = False
    update_interval: int = 30  # seconds
    background_tracking: bool = True
    high_risk_alerts_only: bool = False
class Waypoint(BaseModel):
    lat: float
    lng: float

class Step(BaseModel):
    instruction: Optional[str]
    distance: Optional[float]
    duration: Optional[float]

class RouteData(BaseModel):
    start_lat: Optional[float] = None
    start_lng: Optional[float] = None
    end_lat: Optional[float] = None
    end_lng: Optional[float] = None
    distance: Optional[float] = None
    duration: Optional[float] = None
    geometry: Optional[Dict] = None
    steps: Optional[List[Step]] = None
    waypoints: Optional[List[Waypoint]] = None

class SafetyResponse(BaseModel):
    overall_score: float  # 0-100 safety score
    alerts: List[Dict[str, Any]]  # [{"type": str, "description": str, "severity": str, "location": str}, ...]
    safety_level: Optional[str] = "medium"  # high, medium, low
    factors: Optional[Dict[str, Any]] = None  # {crime_rate, lighting, traffic, emergency_services_proximity, road_type}

# AI Route Safety Analysis Models
class RoutePointData(BaseModel):
    latitude: float
    longitude: float
    area: str
    crime_type: str

class AIRouteSafetyRequest(BaseModel):
    route_points: List[RoutePointData]
    date: Optional[str] = None

class PointPrediction(BaseModel):
    point_index: int
    latitude: float
    longitude: float
    area: str
    crime_type: str
    prediction: Dict[str, Any]

class AIRouteSafetyResponse(BaseModel):
    overall_score: float
    safety_level: str
    point_predictions: List[PointPrediction]
    alerts: List[Dict[str, Any]]
    summary: Dict[str, Any]

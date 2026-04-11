"""Pydantic schemas and database row type definitions."""

# Export all schemas
from app.models.schemas import (
    RouteData,
    SafetyResponse,
    RegistrationResponse,
    ResendVerificationRequest,
    UserProfileUpdate,
    UserLocationUpdate,
    LocationRequest,
    LocationResponse,
    LocationAlertRequest,
    AlertSubscription,
    RiskZoneAlert,
    AlertCreate,
    UserAlertResponse,
    Crime,
    PredictRiskRequest,
    CrimeCreate,
    EmergencyCallRequest,
    PatrolRequestRequest,
    EmergencyContact,
    AdminRegister,
    AdminResponse,
    ForgotPasswordRequest,
    ResetPasswordRequest,
    LocationUpdateRequest,
    LocationHistoryResponse,
    LocationTrackingPreferences,
)

# Export all types
from app.models.types import (
    CrimeRow,
    CrimeTypeRow,
)

__all__ = [
    # Schemas
    "RouteData",
    "SafetyResponse",
    "RegistrationResponse",
    "ResendVerificationRequest",
    "UserProfileUpdate",
    "UserLocationUpdate",
    "LocationRequest",
    "LocationResponse",
    "LocationAlertRequest",
    "AlertSubscription",
    "RiskZoneAlert",
    "AlertCreate",
    "UserAlertResponse",
    "Crime",
    "PredictRiskRequest",
    "CrimeCreate",
    "EmergencyCallRequest",
    "PatrolRequestRequest",
    "EmergencyContact",
    "AdminRegister",
    "AdminResponse",
    "ForgotPasswordRequest",
    "ResetPasswordRequest",
    "LocationUpdateRequest",
    "LocationHistoryResponse",
    "LocationTrackingPreferences",
    # Types
    "CrimeRow",
    "CrimeTypeRow",
]
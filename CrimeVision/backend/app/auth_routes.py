from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel
from app.password_reset import forgot_password, reset_password, ForgotPasswordRequest, ResetPasswordRequest
from app.two_factor import generate_2fa_secret, verify_2fa_code, setup_2fa, enable_2fa, disable_2fa, get_2fa_uri, get_user_2fa_secret
from app.auth import verify_token, verify_refresh_token, create_access_token
from fastapi import Request
from app.core.database import get_db_connection
from typing import cast, Dict, Any

router = APIRouter()

class RefreshTokenRequest(BaseModel):
    refresh_token: str

@router.post("/auth/refresh-token")
async def refresh_token_endpoint(request: RefreshTokenRequest):
    """Issue a new access token using a valid refresh token"""
    username = verify_refresh_token(request.refresh_token)
    if username is None:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    # Optionally, check if user still exists or is active
    access_token = create_access_token({"sub": username})
    return {"access_token": access_token}

# 2FA Models
class Enable2FARequest(BaseModel):
    code: str

class Verify2FAResponse(BaseModel):
    success: bool
    message: str

security = HTTPBearer()

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Get current user from JWT token"""
    token = credentials.credentials
    username = verify_token(token)
    if username is None:
        raise HTTPException(status_code=401, detail="Invalid token")
    return username

def get_user_id_from_username(username: str):
    """Get user ID from username"""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT id FROM users_info WHERE username = %s", (username,))
        user = cursor.fetchone()
        return cast(Dict[str, Any], user).get('id') if user else None
    finally:
        cursor.close()
        conn.close()

@router.post("/auth/forgot-password")
async def forgot_password_endpoint(request: ForgotPasswordRequest, background_tasks: BackgroundTasks):
    """Send password reset email to user"""
    return await forgot_password(request, background_tasks)

@router.post("/auth/reset-password")
async def reset_password_endpoint(request: ResetPasswordRequest, background_tasks: BackgroundTasks):
    """Reset user password using reset token"""
    return await reset_password(request, background_tasks)

# 2FA Endpoints
@router.get("/auth/2fa/setup")
async def setup_2fa_endpoint(current_user: str = Depends(get_current_user)):
    """Generate 2FA secret and URI for QR code"""
    user_id = get_user_id_from_username(current_user)
    if not user_id:
        raise HTTPException(status_code=404, detail="User not found")

    secret = generate_2fa_secret()
    setup_2fa(user_id, secret)
    uri = get_2fa_uri(secret, current_user)
    return {"secret": secret, "uri": uri}

@router.post("/auth/2fa/enable")
async def enable_2fa_endpoint(request: Enable2FARequest, current_user: str = Depends(get_current_user)):
    """Enable 2FA after verifying code"""
    user_id = get_user_id_from_username(current_user)
    if not user_id:
        raise HTTPException(status_code=404, detail="User not found")

    secret = get_user_2fa_secret(user_id)
    if not secret:
        raise HTTPException(status_code=400, detail="2FA not set up")
    if not verify_2fa_code(secret, request.code):
        raise HTTPException(status_code=400, detail="Invalid 2FA code")
    enable_2fa(user_id, secret)
    return {"message": "2FA enabled successfully"}

@router.post("/auth/2fa/disable")
async def disable_2fa_endpoint(current_user: str = Depends(get_current_user)):
    """Disable 2FA"""
    user_id = get_user_id_from_username(current_user)
    if not user_id:
        raise HTTPException(status_code=404, detail="User not found")

    disable_2fa(user_id)
    return {"message": "2FA disabled successfully"}

@router.post("/auth/2fa/verify")
async def verify_2fa_endpoint(request: Enable2FARequest, current_user: str = Depends(get_current_user)):
    """Verify 2FA code"""
    user_id = get_user_id_from_username(current_user)
    if not user_id:
        raise HTTPException(status_code=404, detail="User not found")

    secret = get_user_2fa_secret(user_id)
    if not secret:
        raise HTTPException(status_code=400, detail="2FA not set up")
    success = verify_2fa_code(secret, request.code)
    return Verify2FAResponse(success=success, message="Code verified" if success else "Invalid code")

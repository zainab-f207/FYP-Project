from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, UploadFile, File, Request
from fastapi.responses import RedirectResponse
from typing import Dict, Any, Optional, cast
import secrets
from datetime import datetime, timedelta
import logging
import os
import re
import json

from app.auth_updated import create_access_token, get_password_hash, verify_password, create_refresh_token, verify_refresh_token, verify_google_token, create_or_get_google_user
from app.core.database import get_db_connection, log_user_activity
from app.utils.validation import validate_name
from app.utils.geo import get_coordinates
from app.email_verification import send_verification_email
from app.two_factor import is_2fa_enabled, get_user_2fa_secret, verify_2fa_code, generate_2fa_secret as generate_2fa_secret_util, get_2fa_uri, enable_2fa, disable_2fa
from app.rate_limiting import check_rate_limit, record_login_attempt, reset_login_attempts
from app.password_reset_fixed import forgot_password, reset_password, ForgotPasswordRequest, ResetPasswordRequest
from app.email_otp import generate_otp, store_otp, verify_otp, send_otp_email, send_login_alert_email

from app.dependencies import get_username_from_token, get_current_user
from app.models.schemas import (
    UserRegister, UserLogin, RegistrationResponse, ResendVerificationRequest,
    Token, UserProfileUpdate, UserLocationUpdate, GoogleRegister
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["authentication"])

@router.post("/register", response_model=RegistrationResponse)
def register(user: UserRegister, background_tasks: BackgroundTasks):
    """Register a new user with email verification"""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        # Validate names
        first_name = validate_name(user.first_name)
        last_name = validate_name(user.last_name)

        # Use username provided from frontend
        username = user.username

        # Check if email already exists
        cursor.execute("SELECT id FROM users_info WHERE email = %s", (user.email,))
        if cursor.fetchone():
            raise HTTPException(status_code=400, detail="Email already exists")

        # Validate password against current system settings for regular users
        pw_error = validate_password_strength(user.password, "user")
        if pw_error:
            raise HTTPException(status_code=400, detail=pw_error)

        # Hash password
        password_hash = get_password_hash(user.password)

        # Get coordinates for home area if provided (Strictly Lahore)
        home_lat, home_lon = None, None
        if user.home_area:
            try:
                logger.info(f"🔍 Fetching coordinates for home area: {user.home_area}")
                coords = get_coordinates(user.home_area)
                if coords:
                    home_lat, home_lon = coords
                    logger.info(f"✅ Coordinates found: {home_lat}, {home_lon}")
                else:
                    logger.warning(f"❌ Area not in Lahore: {user.home_area}")
                    raise HTTPException(
                        status_code=400, 
                        detail=f"The area '{user.home_area}' was not found in Lahore. Please provide a valid Lahore location (e.g. 'Model Town, Lahore')."
                    )
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"❌ Error fetching coordinates for {user.home_area}: {e}")
                raise HTTPException(status_code=500, detail="Location service error")

        # Generate email verification token
        verification_token = secrets.token_urlsafe(32)
        token_expires_at = datetime.utcnow() + timedelta(hours=24)

        # Create user with is_verified = false and verification_status = pending
        cursor.execute(
            """INSERT INTO users_info (username, first_name, last_name, email, password_hash, home_area, home_latitude, home_longitude, phone_number, activity_logs, is_verified, verification_status, email_verification_token, token_expires_at) 
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
            (username, first_name, last_name, user.email, password_hash, user.home_area, home_lat, home_lon, user.phone_number, "[]", False, 'pending', verification_token, token_expires_at)
        )
        conn.commit()

        # Send verification email in background
        background_tasks.add_task(send_verification_email, user.email, first_name, verification_token)

        return {
            "message": f"User registered successfully. Please check your email to verify your account. Your username is: {username}"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Database error during registration: {e}")
        raise HTTPException(status_code=500, detail="Database error")
    finally:
        cursor.close()
        conn.close()

@router.post("/resend-verification")
def resend_verification(request: ResendVerificationRequest, background_tasks: BackgroundTasks):
    """Resend email verification link"""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT id, first_name, is_verified FROM users_info WHERE email = %s", (request.email,))
        user = cast(Optional[Dict[str, Any]], cursor.fetchone())
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        if user.get("is_verified"):
            raise HTTPException(status_code=400, detail="User is already verified")

        # Generate new verification token and expiry
        new_token = secrets.token_urlsafe(32)
        new_expires = datetime.utcnow() + timedelta(hours=24)

        cursor.execute(
            "UPDATE users_info SET email_verification_token = %s, token_expires_at = %s WHERE id = %s",
            (new_token, new_expires, user.get("id"))
        )
        conn.commit()

        # Send email in background
        first_name = user.get("first_name") or "User"
        background_tasks.add_task(send_verification_email, request.email, first_name, new_token)

        return {"message": "Verification email re-sent. Please check your inbox."}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Database error during resend verification: {e}")
        raise HTTPException(status_code=500, detail="Database error")
    finally:
        cursor.close()
        conn.close()

@router.post("/verify-email")
def verify_email(token: str):
    """Verify user's email address using verification token"""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            "SELECT id, username, email, token_expires_at FROM users_info WHERE email_verification_token = %s",
            (token,)
        )
        user = cast(Optional[Dict[str, Any]], cursor.fetchone())

        if not user:
            raise HTTPException(status_code=400, detail="Invalid verification token")

        # Check if token has expired
        token_expires_at = user.get("token_expires_at")
        if token_expires_at and datetime.utcnow() > token_expires_at:
            raise HTTPException(status_code=400, detail="Verification token has expired")

        # Update user as verified, set verification_status, and clear verification token
        cursor.execute(
            """UPDATE users_info 
               SET is_verified = %s, 
                   verification_status = 'verified',
                   verified_at = NOW(),
                   email_verification_token = NULL, 
                   token_expires_at = NULL 
               WHERE id = %s""",
            (True, user.get("id"))
        )
        conn.commit()

        # Log the verification
        log_user_activity(
            activity_type="email_verified",
            username=user.get("username"),
            user_id=user.get("id"),
            activity_details={"message": "User email verified successfully."},
        )

        return {"message": "Email verified successfully. You can now log in to your account."}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Database error during email verification: {e}")
        raise HTTPException(status_code=500, detail="Database error")
    finally:
        cursor.close()
        conn.close()

@router.get("/verify-email")
def verify_email_redirect(token: str):
    """Redirect legacy GET verification links to the frontend verification page."""
    try:
        # Determine frontend URL
        frontend_url = os.getenv('FRONTEND_URL')
        if not frontend_url:
            dev_mode = os.getenv('ENV') != 'production' and not os.getenv('FRONTEND_URL')
            if dev_mode:
                frontend_url = "http://localhost:5173"
            else:
                from app.core.config import ALLOWED_ORIGINS
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

@router.post("/login")
def login(user: UserLogin, request: Request):
    """Login user and return JWT token"""
    logger.info(f"Request received: {request.method} {request.url.path}")

    # --- Rate limiting check ---
    client_ip = None
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        client_ip = forwarded.split(",")[0].strip()
    elif request.client:
        client_ip = request.client.host

    is_allowed, remaining_attempts, lockout_seconds = check_rate_limit(user.email, client_ip)
    if not is_allowed:
        lockout_minutes = max(1, lockout_seconds // 60)
        raise HTTPException(
            status_code=429,
            detail=f"Account temporarily locked due to too many failed attempts. Try again in {lockout_minutes} minute(s).",
            headers={"Retry-After": str(lockout_seconds)},
        )

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        # Get user from database
        cursor.execute("SELECT id, username, password_hash, is_verified, role FROM users_info WHERE email = %s", (user.email,))
        db_user = cast(Optional[Dict[str, Any]], cursor.fetchone())

        if not db_user:
            record_login_attempt(user.email, client_ip, False)
            raise HTTPException(status_code=401, detail="Invalid credentials")

        # Check if user is verified
        is_verified = db_user.get("is_verified", False)
        if not is_verified:
            raise HTTPException(status_code=403, detail="Please verify your email address before logging in.")

        # Verify password
        password_hash = db_user.get("password_hash", "")
        if not verify_password(user.password, password_hash):
            record_login_attempt(user.email, client_ip, False)
            # Return remaining attempts info
            _, new_remaining, _ = check_rate_limit(user.email, client_ip)
            detail_msg = "Invalid credentials"
            if new_remaining <= 2:
                detail_msg += f". {new_remaining} attempt(s) remaining before account lockout."
            raise HTTPException(status_code=401, detail=detail_msg)

        # Check 2FA
        user_id = db_user.get("id")
        user_role = db_user.get("role", "user")
        username = db_user.get("username")

        # --- Mandatory Email OTP for admin/superadmin ---
        if user_role in ("admin", "superadmin"):
            # For admin/superadmin, ALWAYS require email OTP (mandatory 2FA)
            # Get user's email and name for OTP
            cursor.execute("SELECT first_name, last_name, username, email FROM users_info WHERE id = %s", (user_id,))
            user_info = cast(Optional[Dict[str, Any]], cursor.fetchone())
            if user_info:
                fn = (user_info.get("first_name") or "").strip()
                ln = (user_info.get("last_name") or "").strip()
                full_name = f"{fn} {ln}".strip() if fn or ln else user_info.get("username", "Admin")
                user_email = user_info.get("email", user.email)
            else:
                full_name = "Admin"
                user_email = user.email

            # Generate and send OTP
            otp_code = generate_otp()
            if not store_otp(user_id, otp_code):
                raise HTTPException(status_code=500, detail="Failed to generate verification code")

            send_otp_email(user_email, full_name, otp_code)
            logger.info(f"OTP sent to {user_role} user {username} at {user_email}")

            return {
                "requires_email_otp": True,
                "user_id": user_id,
                "username": username,
                "role": user_role,
                "message": f"A verification code has been sent to your email ({user_email[:3]}***{user_email[user_email.index('@'):]})."
            }

        # For regular users, check optional TOTP 2FA
        if is_2fa_enabled(user_id):
            if not user.two_factor_code:
                return {
                    "requires_2fa": True,
                    "message": "Two-factor authentication code required"
                }
            secret = get_user_2fa_secret(user_id)
            if not secret or not verify_2fa_code(secret, user.two_factor_code):
                record_login_attempt(user.email, client_ip, False)
                raise HTTPException(status_code=401, detail="Invalid two-factor authentication code")

        # Create access and refresh tokens (include role for session timeout)
        access_token = create_access_token(data={"sub": username, "role": user_role})
        refresh_token = create_refresh_token(data={"sub": username})

        # Record successful login & reset failed attempts
        record_login_attempt(user.email, client_ip, True)
        reset_login_attempts(user.email)

        # Update user activity tracking on successful login
        cursor.execute(
            "UPDATE users_info SET is_logged_in = TRUE, last_activity_at = NOW() WHERE id = %s",
            (user_id,)
        )
        conn.commit()

        # Log the login activity
        log_user_activity(
            activity_type="login",
            username=username,
            user_id=user_id,
            activity_details={"message": "User logged in successfully."},
        )

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



@router.post("/verify-login-otp")
def verify_login_otp(request: dict, req: Request):
    """Verify email OTP for admin/superadmin login. Completes the login flow."""
    user_id = request.get("user_id")
    otp_code = request.get("otp_code")

    if not user_id or not otp_code:
        raise HTTPException(status_code=400, detail="User ID and OTP code are required")

    # Get client IP
    client_ip = None
    forwarded = req.headers.get("X-Forwarded-For")
    if forwarded:
        client_ip = forwarded.split(",")[0].strip()
    elif req.client:
        client_ip = req.client.host

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        # Verify OTP
        if not verify_otp(int(user_id), otp_code):
            raise HTTPException(status_code=401, detail="Invalid or expired verification code. Please request a new one.")

        # Get user details
        cursor.execute(
            "SELECT id, username, email, first_name, last_name, role, password_must_change FROM users_info WHERE id = %s",
            (user_id,)
        )
        db_user = cast(Optional[Dict[str, Any]], cursor.fetchone())
        if not db_user:
            raise HTTPException(status_code=401, detail="User not found")

        username = db_user.get("username")
        user_role = db_user.get("role", "user")
        user_email = db_user.get("email", "")
        fn = (db_user.get("first_name") or "").strip()
        ln = (db_user.get("last_name") or "").strip()
        full_name = f"{fn} {ln}".strip() if fn or ln else username or "User"
        must_change_pw = db_user.get("password_must_change", False)

        # Create tokens
        access_token = create_access_token(data={"sub": username, "role": user_role})
        refresh_token = create_refresh_token(data={"sub": username})

        # Record successful login
        record_login_attempt(user_email, client_ip, True)
        reset_login_attempts(user_email)

        # Update activity tracking
        cursor.execute(
            "UPDATE users_info SET is_logged_in = TRUE, last_activity_at = NOW() WHERE id = %s",
            (user_id,)
        )
        conn.commit()

        log_user_activity(
            activity_type="login",
            username=username,
            user_id=int(user_id),
            activity_details={"message": f"{user_role.title()} logged in via email OTP."},
        )

        # Send login alert email (background - don't block response)
        login_time = datetime.now().strftime("%I:%M %p, %B %d, %Y")
        try:
            send_login_alert_email(user_email, full_name, user_role, client_ip or "Unknown", login_time)
        except Exception as e:
            logger.warning(f"Failed to send login alert email: {e}")

        response = {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "username": username,
            "role": user_role,
        }

        # Check if password change is required (first login)
        if must_change_pw:
            response["requires_password_change"] = True
            response["message"] = "You must change your password before continuing."

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error verifying login OTP: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        cursor.close()
        conn.close()


@router.post("/resend-login-otp")
def resend_login_otp(request: dict):
    """Resend OTP for admin/superadmin login."""
    user_id = request.get("user_id")
    if not user_id:
        raise HTTPException(status_code=400, detail="User ID is required")

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT first_name, email, role FROM users_info WHERE id = %s", (user_id,))
        user_info = cast(Optional[Dict[str, Any]], cursor.fetchone())
        if not user_info:
            raise HTTPException(status_code=404, detail="User not found")

        if user_info.get("role") not in ("admin", "superadmin"):
            raise HTTPException(status_code=400, detail="OTP is only for admin/superadmin accounts")

        otp_code = generate_otp()
        if not store_otp(int(user_id), otp_code):
            raise HTTPException(status_code=500, detail="Failed to generate verification code")

        send_otp_email(user_info["email"], user_info.get("first_name", "Admin"), otp_code)

        email = user_info["email"]
        return {
            "message": f"A new verification code has been sent to {email[:3]}***{email[email.index('@'):]}"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error resending OTP: {e}")
        raise HTTPException(status_code=500, detail="Failed to resend verification code")
    finally:
        cursor.close()
        conn.close()


@router.post("/force-change-password")
def force_change_password(request: dict, current_user: str = Depends(get_username_from_token)):
    """Force password change for first-login admin users."""
    new_password = request.get("new_password")
    confirm_password = request.get("confirm_password")

    if not new_password or not confirm_password:
        raise HTTPException(status_code=400, detail="New password and confirmation are required")

    if new_password != confirm_password:
        raise HTTPException(status_code=400, detail="Passwords do not match")

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT id, role, password_must_change FROM users_info WHERE username = %s", (current_user,))
        db_user = cast(Optional[Dict[str, Any]], cursor.fetchone())
        if not db_user:
            raise HTTPException(status_code=404, detail="User not found")

        user_role = db_user.get("role", "user")

        # Validate password strength based on role
        error = validate_password_strength(new_password, user_role)
        if error:
            raise HTTPException(status_code=400, detail=error)

        # Hash and update password
        password_hash = get_password_hash(new_password)
        cursor.execute(
            "UPDATE users_info SET password_hash = %s, password_must_change = FALSE WHERE id = %s",
            (password_hash, db_user["id"])
        )
        # Also update admins table if exists
        try:
            cursor.execute(
                "UPDATE admins SET password_hash = %s WHERE username = %s",
                (password_hash, current_user)
            )
        except Exception:
            pass

        conn.commit()

        log_user_activity(
            activity_type="password_change",
            username=current_user,
            user_id=db_user["id"],
            activity_details={"message": "Password changed on first login."},
        )

        return {"message": "Password changed successfully. You can now use the system."}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error force changing password: {e}")
        raise HTTPException(status_code=500, detail="Failed to change password")
    finally:
        cursor.close()
        conn.close()


def _get_pw_setting(key: str, default: int) -> int:
    """Read a numeric password setting from system_settings; falls back to default.
    This helper avoids circular imports by querying the DB directly."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT setting_value FROM system_settings WHERE setting_key = %s", (key,))
        row = cursor.fetchone()
        cursor.close()
        conn.close()
        if row:
            return int(cast(Dict[str, Any], row)["setting_value"])
    except Exception:
        pass
    return default


def validate_password_strength(password: str, role: str = "user") -> Optional[str]:
    """Validate password strength based on user role.
    Minimum lengths are read from system_settings (configurable by SuperAdmin).
    Defaults: user=8, admin=10, superadmin=12.
    """
    if role == "superadmin":
        min_len = _get_pw_setting("superadmin_password_min_length", 12)
        if len(password) < min_len:
            return f"SuperAdmin password must be at least {min_len} characters"
        if not re.search(r'[A-Z]', password):
            return "Password must contain at least one uppercase letter"
        if not re.search(r'[a-z]', password):
            return "Password must contain at least one lowercase letter"
        if not re.search(r'[0-9]', password):
            return "Password must contain at least one number"
        if not re.search(r'[!@#$%^&*()_+\-=\[\]{};:\'",.<>?/\\|`~]', password):
            return "SuperAdmin password must contain at least one special character (!@#$%^&*...)"
    elif role == "admin":
        min_len = _get_pw_setting("admin_password_min_length", 10)
        if len(password) < min_len:
            return f"Admin password must be at least {min_len} characters"
        if not re.search(r'[A-Z]', password):
            return "Password must contain at least one uppercase letter"
        if not re.search(r'[a-z]', password):
            return "Password must contain at least one lowercase letter"
        if not re.search(r'[0-9]', password):
            return "Password must contain at least one number"
    else:
        min_len = _get_pw_setting("password_min_length", 8)
        if len(password) < min_len:
            return f"Password must be at least {min_len} characters"
        if not re.search(r'[A-Z]', password):
            return "Password must contain at least one uppercase letter"
        if not re.search(r'[a-z]', password):
            return "Password must contain at least one lowercase letter"
        if not re.search(r'[0-9]', password):
            return "Password must contain at least one number"
    return None


@router.post("/google-login")
async def google_login(request: dict):
    """Login or register user with Google OAuth token"""
    credential = request.get("credential")
    two_factor_code = request.get("two_factor_code")

    # Fix: Check if credential exists before slicing
    if not credential:
        print("❌ No credential provided in Google login request")
        raise HTTPException(status_code=400, detail="Google credential is required")

    # Safe logging - check if credential is long enough to slice
    credential_preview = credential[:20] + "..." if credential and len(credential) > 20 else credential
    print(f"✅ Received Google login request with credential: {credential_preview}")

    try:
        # Verify Google credential and get user info
        print(f"🔐 Google login: Verifying Google token...")
        google_user_info = verify_google_token(credential)
        print(f"🔐 Google login: Token verified for email: {google_user_info.get('email')}")
        
        if not google_user_info.get('email_verified', False):
            print(f"❌ Google email not verified: {google_user_info.get('email')}")
            raise HTTPException(status_code=403, detail="Google email not verified")

        # Get database connection
        print(f"🔐 Google login: Getting database connection...")
        conn = get_db_connection()
        print(f"🔐 Google login: Database connection established")

        # Enforce: user must already exist and be linked with Google
        email = google_user_info.get('email')
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id, username, email, is_verified, google_id FROM users_info WHERE email = %s", (email,))
        user = cast(Optional[Dict[str, Any]], cursor.fetchone())
        if not user:
            print(f"❌ Google login blocked - user not found for email: {email}")
            cursor.close()
            raise HTTPException(status_code=404, detail="User not found. Please sign up with Google first.")
        if not user.get('google_id'):
            print(f"❌ Google login blocked - account not registered with Google: {email}")
            cursor.close()
            raise HTTPException(status_code=400, detail="Account not registered with Google")
        cursor.close()
        print(f"🔐 Google login: Existing Google-linked user found: {user.get('username')}")

        # Check if user is verified (for Google signups)
        is_verified = user.get("is_verified", False)
        if not is_verified:
            print(f"❌ User {user['username']} is not verified, returning requires_verification")
            return {
                "requires_verification": True,
                "message": "Please check your email to verify your account before logging in.",
                "user_info": {
                    "username": user.get("username"),
                    "email": user.get("email")
                }
            }

        # Check if user has 2FA enabled
        if is_2fa_enabled(user['id']):
            if not two_factor_code:
                return {
                    "requires_2fa": True,
                    "message": "Two-factor authentication code required",
                    "user_info": {
                        "username": user.get("username"),
                        "email": user.get("email")
                    }
                }
            # Verify 2FA code
            secret = get_user_2fa_secret(user['id'])
            if not secret or not verify_2fa_code(secret, two_factor_code):
                raise HTTPException(status_code=401, detail="Invalid two-factor authentication code")

        # Create access and refresh tokens
        access_token = create_access_token(data={"sub": user["username"]})
        refresh_token = create_refresh_token(data={"sub": user["username"]})

        # Update user activity tracking
        try:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE users_info SET is_logged_in = TRUE, last_activity_at = NOW() WHERE id = %s",
                (user['id'],)
            )
            conn.commit()
            cursor.close()
        except Exception as e:
            print(f"⚠️ Warning: Failed to update last_activity_at: {e}")
            # Don't fail the login, just warn

        # Log the login activity
        log_user_activity(
            activity_type="google_login",
            username=user["username"],
            user_id=user['id'],
            activity_details={"message": "User logged in with Google successfully."},
        )

        print(f"✅ Google login successful for user: {user['username']}")

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "username": user["username"],
            "is_new_user": user.get("is_new_user", False)
        }

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        logger.error(f"❌ Error during Google login: {e}", exc_info=True)
        print(f"❌ Detailed error: {str(e)}")
        print(f"❌ Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

# @router.get("/check-2fa-status")
# def check_2fa_status(email: str):
#     """Check if 2FA is enabled for a given email"""
#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor(dictionary=True)
        
#         cursor.execute("SELECT id FROM users_info WHERE email = %s", (email,))
#         user = cursor.fetchone()
#         cursor.close()
#         conn.close()
        
#         if not user:
#             return {"enabled": False}
        
#         user_id = user.get("id")
#         enabled = is_2fa_enabled(user_id)
        
#         return {"enabled": enabled}
        
#     except Exception as e:
#         logger.error(f"Error checking 2FA status for email {email}: {e}")
#         return {"enabled": False}

@router.post("/logout")
def logout(current_user: str = Depends(get_username_from_token)):
    """Logout user and mark as logged out"""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        # Get user ID
        cursor.execute("SELECT id FROM users_info WHERE username = %s", (current_user,))
        user = cast(Optional[Dict[str, Any]], cursor.fetchone())

        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        user_id = user.get("id")

        # Update user activity tracking on logout
        cursor.execute(
            "UPDATE users_info SET is_logged_in = FALSE WHERE id = %s",
            (user_id,)
        )
        conn.commit()

        # Log the logout activity
        log_user_activity(
            activity_type="logout",
            username=current_user,
            user_id=user_id,
            activity_details={"message": "User logged out successfully."},
        )

        return {"message": "Logged out successfully"}

    except Exception as e:
        logger.error(f"Error during logout: {e}")
        raise HTTPException(status_code=500, detail="Database error")
    finally:
        cursor.close()
        conn.close()

@router.get("/me", response_model=Dict[str, Any])
def get_user_info(current_user: str = Depends(get_username_from_token)) -> Dict[str, Any]:
    """Get current user information"""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        logger.info(f"Querying /auth/me for username: '{current_user}'")
        cursor.execute("""
            SELECT id, username, first_name, last_name, email, profile_picture, 
                   home_area, work_area, alert_radius, role, created_at, phone_number,
                   browser_notifications_enabled, email_alerts_enabled, alert_preferences,
                   two_factor_enabled, monitor_live_location,
                   weekly_reports_enabled, incident_alerts_enabled, live_alerts_enabled
            FROM users_info WHERE LOWER(username) = LOWER(%s)
        """, (current_user.lower(),))
        user = cast(Optional[Dict[str, Any]], cursor.fetchone())

        if not user:
            raise HTTPException(status_code=401, detail="Invalid session - user not found")
        
        # Check if 2FA is enabled for this user
        user_id = user.get("id")
        two_factor_enabled = False
        if user_id:
            try:
                two_factor_enabled = is_2fa_enabled(user_id)
            except Exception as e:
                logger.warning(f"Error checking 2FA status for user {current_user}: {e}")
                two_factor_enabled = False

        logger.info(f"User data for {current_user}: browser_notifications_enabled = {user.get('browser_notifications_enabled')}")

        default_email_enabled = bool(user.get("email_alerts_enabled", True))
        default_browser_enabled = bool(user.get("browser_notifications_enabled", False))

        alert_channel_preferences = {
            "incident": {"email": default_email_enabled, "browser": default_browser_enabled},
            "live": {"email": default_email_enabled, "browser": default_browser_enabled},
            "weekly": {"email": default_email_enabled, "browser": default_browser_enabled},
        }

        raw_alert_preferences = user.get("alert_preferences")
        if raw_alert_preferences:
            try:
                parsed_preferences = raw_alert_preferences if isinstance(raw_alert_preferences, dict) else json.loads(raw_alert_preferences)
                stored_channels = parsed_preferences.get("alert_channel_preferences", {}) if isinstance(parsed_preferences, dict) else {}
                for alert_type in ("incident", "live", "weekly"):
                    type_prefs = stored_channels.get(alert_type, {}) if isinstance(stored_channels, dict) else {}
                    if isinstance(type_prefs, dict):
                        alert_channel_preferences[alert_type]["email"] = bool(type_prefs.get("email", alert_channel_preferences[alert_type]["email"]))
                        alert_channel_preferences[alert_type]["browser"] = bool(type_prefs.get("browser", alert_channel_preferences[alert_type]["browser"]))
            except Exception as pref_error:
                logger.warning(f"Could not parse alert_preferences for {current_user}: {pref_error}")

        response_data = {
            "username": user.get("username", ""),
            "first_name": user.get("first_name", ""),
            "last_name": user.get("last_name", ""),
            "email": user.get("email", ""),
            "profile_picture": user.get("profile_picture"),
            "phone_number": user.get("phone_number"),
            "home_area": user.get("home_area"),
            "work_area": user.get("work_area"),
            "alert_radius": user.get("alert_radius", 5),
            "role": user.get("role", "user"),
            "two_factor_enabled": two_factor_enabled,
            "browser_notifications_enabled": user.get("browser_notifications_enabled", False),
            "email_alerts_enabled": user.get("email_alerts_enabled", True),
            "monitor_live_location": bool(user.get("monitor_live_location", False)),
            "weekly_reports_enabled": bool(user.get("weekly_reports_enabled", True)),
            "incident_alerts_enabled": bool(user.get("incident_alerts_enabled", True)),
            "live_alerts_enabled": bool(user.get("live_alerts_enabled", True)),
            "alert_channel_preferences": alert_channel_preferences,
            "created_at": user.get("created_at", "")

        }

        # For admin/superadmin users, also fetch permissions and department from admins table
        user_role = user.get("role", "user")
        if user_role in ("admin", "superadmin"):
            try:
                cursor.execute(
                    "SELECT department, permissions FROM admins WHERE LOWER(username) = LOWER(%s)",
                    (current_user.lower(),)
                )
                admin_data = cursor.fetchone()
                if admin_data:
                    admin_data = cast(Dict[str, Any], admin_data)
                    response_data["department"] = admin_data.get("department", "")
                    perms = admin_data.get("permissions", "[]")
                    if isinstance(perms, str):
                        import json as _json
                        try:
                            response_data["permissions"] = _json.loads(perms)
                        except Exception:
                            response_data["permissions"] = []
                    elif isinstance(perms, list):
                        response_data["permissions"] = perms
                    else:
                        response_data["permissions"] = []
                else:
                    response_data["department"] = ""
                    response_data["permissions"] = []
            except Exception as e:
                logger.warning(f"Error fetching admin permissions for {current_user}: {e}")
                response_data["department"] = ""
                response_data["permissions"] = []

        return response_data

    except Exception as e:
        logger.error(f"Exception in /auth/me: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Database error")
    finally:
        cursor.close()
        conn.close()

@router.post("/refresh-token")
async def refresh_token_endpoint(request: dict):
    """Issue a new access token using a valid refresh token"""
    refresh_token = request.get("refresh_token")
    if not refresh_token:
        raise HTTPException(status_code=400, detail="Refresh token required")

    username = verify_refresh_token(refresh_token)
    if username is None:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    # Look up user role to set correct token expiry
    role = "user"
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT role FROM users_info WHERE username = %s", (username,))
        db_user = cast(Optional[Dict[str, Any]], cursor.fetchone())
        if db_user:
            role = db_user.get("role", "user")
        cursor.close()
    except Exception:
        pass
    finally:
        if conn and conn.is_connected():
            conn.close()

    # Create new access token with role
    access_token = create_access_token({"sub": username, "role": role})
    return {"access_token": access_token}

@router.put("/update-location")
def update_user_location(
    location_data: UserLocationUpdate,
    current_user: str = Depends(get_username_from_token)
):
    """Update user's location information"""
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Get coordinates for areas if provided (Locked to Lahore)
        home_lat, home_lon = None, None
        work_lat, work_lon = None, None

        if location_data.home_area:
            coords = get_coordinates(location_data.home_area)
            if not coords:
                raise HTTPException(status_code=400, detail=f"The area '{location_data.home_area}' is not a recognized area in Lahore.")
            home_lat, home_lon = coords
        elif location_data.home_area == "":
             # Case: clearing area
             home_lat, home_lon = None, None

        if location_data.work_area:
            coords = get_coordinates(location_data.work_area)
            if not coords:
                raise HTTPException(status_code=400, detail=f"The area '{location_data.work_area}' is not a recognized area in Lahore.")
            work_lat, work_lon = coords
        elif location_data.work_area == "":
             # Case: clearing area
             work_lat, work_lon = None, None

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

    except Exception as e:
        logger.error(f"Database error updating location: {e}")
        raise HTTPException(status_code=500, detail="Database error")
    finally:
        cursor.close()
        conn.close()

@router.put("/update-profile")
def update_user_profile(
    profile_data: UserProfileUpdate,
    current_user: str = Depends(get_username_from_token)
):
    """Update user's profile information"""
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Log incoming profile update payload (safe fields only)
        try:
            logger.info(f"Incoming profile update for {current_user}: { {k: getattr(profile_data, k) for k in ['first_name','last_name','phone_number','home_area','work_area','alert_radius','browser_notifications_enabled'] } }")
        except Exception:
            logger.debug("Could not stringify profile_data for logging")

        update_fields = []
        params = []

        # Existing fields...
        if profile_data.first_name is not None:
            update_fields.append("first_name = %s")
            params.append(validate_name(profile_data.first_name))

        if profile_data.last_name is not None:
            update_fields.append("last_name = %s")
            params.append(validate_name(profile_data.last_name))

        # Skip email field (not updateable via this endpoint for security)
        # Email updates should go through a separate verification flow

        # Profile picture handling (from separate upload endpoint)
        if profile_data.profile_picture is not None:
            update_fields.append("profile_picture = %s")
            params.append(profile_data.profile_picture)

        # Phone number handling
        if profile_data.phone_number is not None:
            # Normalize phone number (allow empty -> clear on DB)
            phone_number = profile_data.phone_number.strip()
            if phone_number:
                if not phone_number.replace('+', '').replace('-', '').replace(' ', '').isdigit():
                    # Let validation errors bubble up as a 400
                    raise HTTPException(status_code=400, detail="Invalid phone number format")

                update_fields.append("phone_number = %s")
                params.append(phone_number)
            else:
                # Explicitly clear phone number in DB
                update_fields.append("phone_number = NULL")

        if profile_data.browser_notifications_enabled is not None:
            update_fields.append("browser_notifications_enabled = %s")
            # Coerce boolean to integer to avoid DB adapter type issues
            browser_enabled = 1 if bool(profile_data.browser_notifications_enabled) else 0
            params.append(browser_enabled)
            logger.info(f"🔄 Setting browser_notifications_enabled to: {browser_enabled}")
        
        if profile_data.email_alerts_enabled is not None:
            update_fields.append("email_alerts_enabled = %s")
            # Coerce boolean to integer to avoid DB adapter type issues
            email_enabled = 1 if bool(profile_data.email_alerts_enabled) else 0
            params.append(email_enabled)
            logger.info(f"🔄 Setting email_alerts_enabled to: {email_enabled}")
        
        if profile_data.monitor_live_location is not None:
            update_fields.append("monitor_live_location = %s")
            # Coerce boolean to integer to avoid DB adapter type issues
            live_enabled = 1 if bool(profile_data.monitor_live_location) else 0
            params.append(live_enabled)
            logger.info(f"🔄 Setting monitor_live_location to: {live_enabled}")

        if profile_data.weekly_reports_enabled is not None:
            update_fields.append("weekly_reports_enabled = %s")
            weekly_enabled = 1 if bool(profile_data.weekly_reports_enabled) else 0
            params.append(weekly_enabled)
            
        if profile_data.incident_alerts_enabled is not None:
            update_fields.append("incident_alerts_enabled = %s")
            incident_enabled = 1 if bool(profile_data.incident_alerts_enabled) else 0
            params.append(incident_enabled)
            
        if profile_data.live_alerts_enabled is not None:
            update_fields.append("live_alerts_enabled = %s")
            live_alerts_enabled = 1 if bool(profile_data.live_alerts_enabled) else 0
            params.append(live_alerts_enabled)

        if profile_data.alert_channel_preferences is not None:
            incoming = profile_data.alert_channel_preferences if isinstance(profile_data.alert_channel_preferences, dict) else {}

            normalized_channels = {
                "incident": {
                    "email": bool((incoming.get("incident") or {}).get("email", False)),
                    "browser": bool((incoming.get("incident") or {}).get("browser", False)),
                },
                "live": {
                    "email": bool((incoming.get("live") or {}).get("email", False)),
                    "browser": bool((incoming.get("live") or {}).get("browser", False)),
                },
                "weekly": {
                    "email": bool((incoming.get("weekly") or {}).get("email", False)),
                    "browser": bool((incoming.get("weekly") or {}).get("browser", False)),
                },
            }

            cursor.execute("SELECT alert_preferences FROM users_info WHERE username = %s", (current_user,))
            existing_pref_row = cursor.fetchone()
            merged_preferences: Dict[str, Any] = {}

            try:
                if existing_pref_row and existing_pref_row[0]:
                    existing_raw = existing_pref_row[0]
                    if isinstance(existing_raw, dict):
                        merged_preferences = dict(existing_raw)
                    elif isinstance(existing_raw, str):
                        merged_preferences = json.loads(existing_raw)
            except Exception:
                merged_preferences = {}

            merged_preferences["alert_channel_preferences"] = normalized_channels

            if "alert_preferences = %s" not in update_fields:
                update_fields.append("alert_preferences = %s")
                params.append(json.dumps(merged_preferences))

            # Keep legacy/global flags aligned so existing logic still works.
            any_email = any(v.get("email", False) for v in normalized_channels.values())
            any_browser = any(v.get("browser", False) for v in normalized_channels.values())

            if "email_alerts_enabled = %s" not in update_fields:
                update_fields.append("email_alerts_enabled = %s")
                params.append(1 if any_email else 0)

            if "browser_notifications_enabled = %s" not in update_fields:
                update_fields.append("browser_notifications_enabled = %s")
                params.append(1 if any_browser else 0)



        # Handle home area with coordinates (Strictly Lahore)
        if profile_data.home_area is not None:
            update_fields.append("home_area = %s")
            params.append(profile_data.home_area)
            
            trimmed_home = profile_data.home_area.strip() if profile_data.home_area else ""
            if trimmed_home:
                logger.info(f"🔍 Fetching coordinates for updated home area: '{trimmed_home}'")
                coords = get_coordinates(trimmed_home)
                if coords:
                    home_lat, home_lon = coords
                    update_fields.append("home_latitude = %s")
                    params.append(home_lat)
                    update_fields.append("home_longitude = %s")
                    params.append(home_lon)
                    logger.info(f"✅ Home coordinates updated: {home_lat}, {home_lon}")
                else:
                    logger.warning(f"❌ Geocoding failed for home_area: '{trimmed_home}'")
                    raise HTTPException(status_code=400, detail=f"'{trimmed_home}' is not in Lahore. Please provide a Lahore location.")
            else:
                # User cleared their home area
                logger.info("🗑️ Clearing home area coordinates (empty string provided)")
                update_fields.append("home_latitude = NULL")
                update_fields.append("home_longitude = NULL")

        # Handle work area with coordinates (Strictly Lahore)
        if profile_data.work_area is not None:
            update_fields.append("work_area = %s")
            params.append(profile_data.work_area)
            
            trimmed_work = profile_data.work_area.strip() if profile_data.work_area else ""
            if trimmed_work:
                logger.info(f"🔍 Fetching coordinates for updated work area: '{trimmed_work}'")
                coords = get_coordinates(trimmed_work)
                if coords:
                    work_lat, work_lon = coords
                    update_fields.append("work_latitude = %s")
                    params.append(work_lat)
                    update_fields.append("work_longitude = %s")
                    params.append(work_lon)
                    logger.info(f"✅ Work coordinates updated: {work_lat}, {work_lon}")
                else:
                    logger.warning(f"❌ Geocoding failed for work_area: '{trimmed_work}'")
                    raise HTTPException(status_code=400, detail=f"The location '{trimmed_work}' could not be identified as a valid Lahore area. Please provide an area name from Lahore.")
            else:
                # User cleared their work area
                logger.info("🗑️ Clearing work area coordinates (empty string provided)")
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

        # Execute the update
        cursor.execute(query, params)
        conn.commit()

        # VERIFY the update worked
        cursor.execute("SELECT browser_notifications_enabled FROM users_info WHERE username = %s", (current_user,))
        updated_value = cursor.fetchone()
        if updated_value:
            browser_status = "ENABLED" if updated_value[0] else "DISABLED"
            logger.info(f"✅ Profile updated successfully. browser_notifications_enabled is now: {browser_status}")

        return {"message": "Profile updated successfully"}

    except HTTPException:
        # Re-raise HTTPExceptions (validation/user errors) so client gets proper status codes
        raise
    except Exception as e:
        # Log full exception with traceback for easier debugging
        logger.error(f"Database error updating profile: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Database error")
    finally:
        cursor.close()
        conn.close()

@router.post("/upload-profile-photo")
async def upload_profile_photo(
    file: UploadFile = File(...),
    current_user: str = Depends(get_username_from_token)
):
    """Upload profile photo and update user's profile_picture field"""
    upload_dir = os.path.join(os.path.dirname(__file__), "..", "profile_photos")
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

# 2FA Endpoints
@router.get("/check-2fa-status")
def check_2fa_status(email: str):
    """Check if 2FA is enabled for a user by email (used during login form)"""
    if not email:
        raise HTTPException(status_code=400, detail="Email is required")

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT id FROM users_info WHERE email = %s", (email,))
        user = cast(Optional[Dict[str, Any]], cursor.fetchone())

        if not user:
            # Don't reveal if user exists or not for security
            return {"enabled": False}

        user_id = user.get("id")
        enabled = is_2fa_enabled(user_id)

        return {"enabled": enabled}

    except Exception as e:
        logger.error(f"Database error checking 2FA status: {e}")
        raise HTTPException(status_code=500, detail="Database error")
    finally:
        cursor.close()
        conn.close()

@router.post("/generate-2fa")
def generate_2fa_secret(current_user: str = Depends(get_username_from_token)):
    """Generate a new 2FA secret and return the QR code URI"""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT id, email FROM users_info WHERE username = %s", (current_user,))
        user = cast(Optional[Dict[str, Any]], cursor.fetchone())
        if not user:
            raise HTTPException(status_code=401, detail="User not found")

        user_id = user.get("id")
        email = user.get("email")

        # Check if 2FA is already enabled
        if is_2fa_enabled(user_id):
            raise HTTPException(status_code=400, detail="2FA is already enabled for this account")

        # Generate new secret
        secret = generate_2fa_secret_util()
        uri = get_2fa_uri(secret, email, "SafeVision")

        return {
            "secret": secret,
            "uri": uri,
            "message": "Scan the QR code with your authenticator app and use the code to enable 2FA"
        }

    except Exception as e:
        logger.error(f"Database error generating 2FA secret: {e}")
        raise HTTPException(status_code=500, detail="Database error")
    finally:
        cursor.close()
        conn.close()

@router.post("/enable-2fa")
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
        user = cast(Optional[Dict[str, Any]], cursor.fetchone())
        if not user:
            raise HTTPException(status_code=401, detail="User not found")

        user_id = user.get("id")

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

    except Exception as e:
        logger.error(f"Database error enabling 2FA: {e}")
        raise HTTPException(status_code=500, detail="Database error")
    finally:
        cursor.close()
        conn.close()

@router.post("/disable-2fa")
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
        user = cast(Optional[Dict[str, Any]], cursor.fetchone())
        if not user:
            raise HTTPException(status_code=401, detail="User not found")

        user_id = user.get("id")

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

    except Exception as e:
        logger.error(f"Database error disabling 2FA: {e}")
        raise HTTPException(status_code=500, detail="Database error")
    finally:
        cursor.close()
        conn.close()

@router.post("/google-register")
async def google_register(user: GoogleRegister):
    """Register new user with Google OAuth and additional user data"""
    logger.info(f"🔍 [BACKEND] Google register request received for email: {user.email}")
    
    conn = None
    try:
        # Step 1: Verify Google token
        logger.info("🔍 [BACKEND] Step 1: Verifying Google token...")
        google_user_info = verify_google_token(user.credential)
        logger.info(f"🔍 [BACKEND] Google user info: {google_user_info.get('email')}")

        if not google_user_info.get('email_verified', False):
            raise HTTPException(status_code=403, detail="Google email not verified")

        if google_user_info.get('email') != user.email:
            raise HTTPException(status_code=400, detail="Email mismatch")

        # Step 2: Get database connection
        logger.info("🔍 [BACKEND] Step 2: Getting database connection...")
        conn = get_db_connection()
        
        # Step 2.5: Reject if email already exists (do not auto-link in register)
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT id FROM users_info WHERE email = %s", (user.email,))
        if cur.fetchone():
            cur.close()
            logger.info(f"❌ [BACKEND] Google register blocked - email already exists: {user.email}")
            raise HTTPException(status_code=409, detail="Email already exists")
        cur.close()
        
        # Step 3: Create/get user
        logger.info("🔍 [BACKEND] Step 3: Creating/getting user...")
        user_record = create_or_get_google_user(google_user_info, conn)
        
        if not user_record:
            raise HTTPException(status_code=500, detail="Failed to create user")

        logger.info(f"🔍 [BACKEND] User created: {user_record.get('username')}")

        # Step 4: Create tokens
        logger.info("🔍 [BACKEND] Step 4: Creating tokens...")
        access_token = create_access_token(data={"sub": user_record["username"]})
        refresh_token = create_refresh_token(data={"sub": user_record["username"]})

        # Step 5: Return response
        response_data = {
            "success": True,
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "username": user_record["username"],
            "message": f"User registered successfully. Username: {user_record['username']}"
        }
        
        logger.info(f"✅ [BACKEND] Registration successful, returning response")
        return response_data

    except HTTPException as he:
        logger.error(f"❌ [BACKEND] HTTPException: {he.detail}")
        if conn:
            conn.close()
        # Re-raise to let FastAPI handle it
        raise he
        
    except Exception as e:
        logger.error(f"❌ [BACKEND] Unexpected error: {e}", exc_info=True)
        if conn:
            conn.close()
        # Always return a proper JSON response, never null
        raise HTTPException(status_code=500, detail=f"Registration failed: {str(e)}")

@router.post("/forgot-password")
async def api_forgot_password(request: ForgotPasswordRequest, background_tasks: BackgroundTasks):
    return await forgot_password(request, background_tasks)

@router.post("/reset-password")
async def api_reset_password(request: ResetPasswordRequest, background_tasks: BackgroundTasks):
    return await reset_password(request, background_tasks)

@router.get("/google-client-id")
def get_google_client_id():
    """Get Google OAuth client ID for frontend"""
    from app.models.schemas import GOOGLE_CLIENT_ID
    return {"client_id": GOOGLE_CLIENT_ID}


# ─── Email Magic-Link Auto-Login ──────────────────────────────────────────────

from jose import jwt as _jose_jwt, JWTError as _JWTError

EMAIL_LINK_SECRET = os.getenv("SECRET_KEY", "safevision-email-link-secret")
EMAIL_LINK_ALGO   = "HS256"
EMAIL_LINK_TTL_H  = 24  # hours


def generate_email_auth_token(user_id: int, next_path: str = "/dashboard") -> str:
    """Generate a short-lived JWT for email deep-link auto-login."""
    payload = {
        "sub":  str(user_id),
        "type": "email_link",
        "next": next_path,
        "exp":  datetime.utcnow() + timedelta(hours=EMAIL_LINK_TTL_H),
    }
    return _jose_jwt.encode(payload, EMAIL_LINK_SECRET, algorithm=EMAIL_LINK_ALGO)


@router.post("/generate-email-token")
def create_email_link_token(body: dict):
    """
    Internal endpoint: alert system calls this to get a magic-link token
    for a specific user_id and target path.
    Body: { "user_id": int, "next": "/dashboard?tab=map&area=..." }
    """
    user_id   = body.get("user_id")
    next_path = body.get("next", "/dashboard")
    if not user_id:
        raise HTTPException(status_code=400, detail="user_id is required")
    token = generate_email_auth_token(int(user_id), next_path)
    return {"token": token}


@router.get("/email-link")
def email_link_autologin(token: str):
    """
    Email deep-link handler.
    Validates the magic-link token, issues a full access token,
    then redirects the browser to:
      {FRONTEND_URL}/autologin?access_token=<JWT>&next=<target_path>
    The frontend AutoLoginPage stores the token and navigates to <next>.
    """
    frontend_url = os.getenv("APP_BASE_URL", "http://localhost:5173").rstrip("/")
    try:
        payload = _jose_jwt.decode(token, EMAIL_LINK_SECRET, algorithms=[EMAIL_LINK_ALGO])
        if payload.get("type") != "email_link":
            raise HTTPException(status_code=400, detail="Invalid token type")

        user_id    = int(payload["sub"])
        next_path  = payload.get("next", "/dashboard")

        conn   = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT id, username, role, is_active FROM users_info WHERE id = %s",
            (user_id,)
        )
        user = cast(Optional[Dict[str, Any]], cursor.fetchone())
        cursor.close()
        conn.close()

        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        if not user.get("is_active", True):
            raise HTTPException(status_code=403, detail="Account is inactive")

        username  = user["username"]
        user_role = user.get("role", "user")

        # Issue a full 30-day access token (same as normal login)
        access_token = create_access_token(data={"sub": username, "role": user_role})

        import urllib.parse
        redirect_url = (
            f"{frontend_url}/autologin"
            f"?access_token={urllib.parse.quote(access_token)}"
            f"&next={urllib.parse.quote(next_path)}"
        )
        logger.info(f"✅ Email link auto-login for user {username} → {next_path}")
        return RedirectResponse(url=redirect_url, status_code=302)

    except _JWTError as je:
        logger.warning(f"Invalid email link token: {je}")
        return RedirectResponse(url=f"{frontend_url}/login?error=expired_link", status_code=302)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Email link auth error: {e}")
        return RedirectResponse(url=f"{frontend_url}/login?error=link_error", status_code=302)

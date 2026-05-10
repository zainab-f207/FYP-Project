import os
import re
from fastapi import HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Dict, Any, Optional, cast
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from mysql.connector import Error
import secrets

from app.auth_updated import get_password_hash
from app.core.database import get_db_connection, log_user_activity
from app.core.config import get_logger

logger = get_logger(__name__)

# Email configuration (same as main file)
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_USERNAME = "safevision.noreply@gmail.com"  
SMTP_PASSWORD = os.getenv('AUTH_EMAIL_PASSWORD', '')

def generate_password_reset_token() -> str:
    """Generate a secure random token for password reset"""
    return secrets.token_urlsafe(32)

# Password reset models
class ForgotPasswordRequest(BaseModel):
    email: str

class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str

def _get_pw_setting(key: str, default: int) -> int:
    """Read numeric password settings from system_settings with fallback."""
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT setting_value FROM system_settings WHERE setting_key = %s", (key,))
        row = cursor.fetchone()
        if row:
            return int(cast(Dict[str, Any], row)["setting_value"])
    except Exception:
        pass
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
    return default

def _validate_password_strength_by_role(password: str, role: str = "user") -> Optional[str]:
    """Validate password policy by role (aligned with auth routes)."""
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
        if not re.search(r'[!@#$%^&*()_+\-=\[\]{};:\'\",.<>?/\\|`~]', password):
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

def send_password_reset_email(email: str, first_name: str, reset_token: str):
    """Send password reset email to user"""
    try:
        # Construct reset link (adjust URL based on your frontend)
        reset_link = f"http://localhost:5173/reset-password?token={reset_token}"

        # Email template with 30 minutes expiration and updated text
        html_template = """<!DOCTYPE html>
<html>
  <body style="font-family: Arial, sans-serif; background-color: #f8f9fa; padding: 20px;">
    <div style="max-width: 600px; margin: auto; background: #ffffff; padding: 30px; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
      <h2 style="color: #dc3545;">Reset Your SafeVision Password</h2>
      <p>Dear {UserName},</p>
      <p>You have requested to reset your password for your <strong>SafeVision</strong> account. Click the button below to reset your password:</p>
      <p style="text-align: center; margin: 30px 0;">
        <a href="{ResetLink}" style="background-color: #dc3545; color: #ffffff; padding: 12px 24px; text-decoration: none; border-radius: 5px; font-weight: bold;">Reset Password</a>
      </p>
      <p>This link will expire in 30 minutes.</p>
      <p>If you did not request this password reset, please ignore this message.</p>
      <p>Best regards,<br><strong>SafeVision Team</strong><br>support@safevision.com</p>
    </div>
  </body>
</html>"""

        # Replace placeholders
        html_content = html_template.replace("{UserName}", first_name)
        html_content = html_content.replace("{ResetLink}", reset_link)

        plain_text = (
            f"Dear {first_name},\n\n"
            f"You have requested to reset your password for your SafeVision account. "
            f"Visit the link below to reset your password:\n\n"
            f"{reset_link}\n\n"
            f"This link will expire in 30 minutes.\n"
            f"If you did not request this password reset, please ignore this message.\n\n"
            f"Best regards,\nSafeVision Team\nsupport@safevision.com\n"
        )

        # Create message with plain-text + HTML alternatives (better deliverability)
        msg = MIMEMultipart('alternative')
        msg['From'] = f"SafeVision <{SMTP_USERNAME}>"
        msg['To'] = email
        msg['Reply-To'] = SMTP_USERNAME
        msg['Subject'] = "Reset your SafeVision password"

        msg.attach(MIMEText(plain_text, 'plain'))
        msg.attach(MIMEText(html_content, 'html'))

        # Send email
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SMTP_USERNAME, SMTP_PASSWORD)
        text = msg.as_string()
        server.sendmail(SMTP_USERNAME, email, text)
        server.quit()

        logger.info(f"Password reset email sent successfully to {email}")

    except Exception as e:
        logger.error(f"Failed to send password reset email to {email}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to send password reset email")

def send_password_reset_confirmation_email(email: str, first_name: str):
    """Send confirmation email after successful password reset"""
    try:
        html_template = """<!DOCTYPE html>
<html>
  <body style="font-family: Arial, sans-serif; background-color: #f8f9fa; padding: 20px;">
    <div style="max-width: 600px; margin: auto; background: #ffffff; padding: 30px; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
      <h2 style="color: #28a745;">Your SafeVision Password Has Been Reset</h2>
      <p>Dear {UserName},</p>
      <p>This is a confirmation that your password for your <strong>SafeVision</strong> account has been successfully reset.</p>
      <p>If you did not perform this action, please contact our support team immediately.</p>
      <p>Best regards,<br><strong>SafeVision Team</strong><br>support@safevision.com</p>
    </div>
  </body>
</html>"""

        html_content = html_template.replace("{UserName}", first_name)

        plain_text = (
            f"Dear {first_name},\n\n"
            f"This is a confirmation that your password for your SafeVision account "
            f"has been successfully reset.\n"
            f"If you did not perform this action, please contact our support team immediately.\n\n"
            f"Best regards,\nSafeVision Team\nsupport@safevision.com\n"
        )

        msg = MIMEMultipart('alternative')
        msg['From'] = f"SafeVision <{SMTP_USERNAME}>"
        msg['To'] = email
        msg['Reply-To'] = SMTP_USERNAME
        msg['Subject'] = "Your SafeVision password was reset"

        msg.attach(MIMEText(plain_text, 'plain'))
        msg.attach(MIMEText(html_content, 'html'))

        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SMTP_USERNAME, SMTP_PASSWORD)
        text = msg.as_string()
        server.sendmail(SMTP_USERNAME, email, text)
        server.quit()

        logger.info(f"Password reset confirmation email sent successfully to {email}")

    except Exception as e:
        logger.error(f"Failed to send password reset confirmation email to {email}: {str(e)}")
        # Do not raise HTTPException here to avoid blocking reset success

async def forgot_password(request: ForgotPasswordRequest, background_tasks: BackgroundTasks):
    """Send password reset email to user"""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        # Check if user exists
        cursor.execute("SELECT id, first_name, email FROM users_info WHERE email = %s", (request.email,))
        user = cursor.fetchone()

        if not user:
            # Don't reveal if email exists or not for security
            return {"message": "If the email exists, a password reset link has been sent."}

        # Generate password reset token
        reset_token = generate_password_reset_token()
        token_expires_at = datetime.utcnow() + timedelta(minutes=30)  # Token expires in 30 minutes

        # Update user with reset token
        cursor.execute(
            "UPDATE users_info SET password_reset_token = %s, reset_token_expires_at = %s WHERE email = %s",
            (reset_token, token_expires_at, request.email)
        )
        conn.commit()

        # Send password reset email in background
        first_name = cast(Dict[str, Any], user).get("first_name") or "User"
        background_tasks.add_task(send_password_reset_email, request.email, str(first_name), reset_token)

        return {"message": "If the email exists, a password reset link has been sent."}

    except Error as e:
        logger.error(f"Database error during forgot password: {e}")
        raise HTTPException(status_code=500, detail="Database error")
    finally:
        cursor.close()
        conn.close()

async def reset_password(request: ResetPasswordRequest, background_tasks: BackgroundTasks):
    """Reset user password using reset token"""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        # Find user by reset token
        cursor.execute(
            "SELECT id, username, first_name, email, role, reset_token_expires_at FROM users_info WHERE password_reset_token = %s",
            (request.token,)
        )
        user = cursor.fetchone()

        if not user:
            raise HTTPException(status_code=400, detail="Invalid or expired reset token")

        # Check if token is expired
        expires_at = cast(Dict[str, Any], user).get("reset_token_expires_at")
        if expires_at is None or expires_at < datetime.utcnow():
            raise HTTPException(status_code=400, detail="Reset token has expired")

        # Validate against role-specific password policy.
        user_role = cast(Dict[str, Any], user).get("role") or "user"
        pw_error = _validate_password_strength_by_role(request.new_password, str(user_role))
        if pw_error:
            raise HTTPException(status_code=400, detail=pw_error)

        # Hash new password
        new_password_hash = get_password_hash(request.new_password)

        # Update password and clear reset token
        cursor.execute(
            "UPDATE users_info SET password_hash = %s, password_reset_token = NULL, reset_token_expires_at = NULL WHERE id = %s",
            (new_password_hash, cast(Dict[str, Any], user).get("id"))
        )
        conn.commit()

        # Log password reset activity
        log_user_activity(
            activity_type="password_reset",
            username=cast(Dict[str, Any], user).get("username"),
            user_id=cast(Dict[str, Any], user).get("id"),
            activity_details={"message": "Password reset successfully."},
        )

        # Send confirmation email in background
        first_name = cast(Dict[str, Any], user).get("first_name") or "User"
        email = cast(Dict[str, Any], user).get("email")
        if email:
            background_tasks.add_task(send_password_reset_confirmation_email, str(email), str(first_name))

        return {"message": "Password reset successfully"}

    except Error as e:
        logger.error(f"Database error during password reset: {e}")
        raise HTTPException(status_code=500, detail="Database error")
    finally:
        cursor.close()
        conn.close()

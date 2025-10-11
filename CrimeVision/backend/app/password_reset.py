from fastapi import HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Dict, Any, cast
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from mysql.connector import Error

from app.auth_updated import get_password_hash, generate_password_reset_token
from app.core.database import get_db_connection, log_user_activity
from app.core.config import get_logger

logger = get_logger(__name__)

# Email configuration (same as main file)
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_USERNAME = "safevision.noreply@gmail.com"  
SMTP_PASSWORD = "dzik alfk tgxy banc"

# Password reset models
class ForgotPasswordRequest(BaseModel):
    email: str

class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str

def send_password_reset_email(email: str, first_name: str, reset_token: str):
    """Send password reset email to user"""
    try:
        # Construct reset link (adjust URL based on your frontend)
        reset_link = f"http://localhost:5173/reset-password?token={reset_token}"

        # Email template
        html_template = """<!DOCTYPE html>
<html>
  <body style="font-family: Arial, sans-serif; background-color: #f8f9fa; padding: 20px;">
    <div style="max-width: 600px; margin: auto; background: #ffffff; padding: 30px; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
      <h2 style="color: #333333;">Reset Your Password</h2>
      <p>Dear {UserName},</p>
      <p>You have requested to reset your password for your <strong>{YourAppName}</strong> account. Click the button below to reset your password:</p>
      <p style="text-align: center; margin: 30px 0;">
        <a href="{ResetLink}" style="background-color: #dc3545; color: #ffffff; padding: 12px 24px; text-decoration: none; border-radius: 5px; font-weight: bold;">Reset Password</a>
      </p>
      <p>This link will expire in 1 hour.</p>
      <p>If you did not request this password reset, please ignore this message.</p>
      <p>Best regards,<br><strong>{YourAppName} Team</strong><br>support@{yourappdomain}.com</p>
    </div>
  </body>
</html>"""

        # Replace placeholders
        html_content = html_template.replace("{UserName}", first_name)
        html_content = html_content.replace("{YourAppName}", "CrimeVision")
        html_content = html_content.replace("{ResetLink}", reset_link)
        html_content = html_content.replace("{yourappdomain}", "crimevision.com")

        # Create message
        msg = MIMEMultipart()
        msg['From'] = SMTP_USERNAME
        msg['To'] = email
        msg['Subject'] = "Reset Your CrimeVision Password"

        # Attach HTML content
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
        token_expires_at = datetime.utcnow() + timedelta(hours=1)  # Token expires in 1 hour

        # Update user with reset token
        cursor.execute(
            "UPDATE users_info SET password_reset_token = %s, reset_token_expires_at = %s WHERE email = %s",
            (reset_token, token_expires_at, request.email)
        )
        conn.commit()

        # Send password reset email in background
        first_name = cast(Dict[str, Any], user).get("first_name") or ""
        background_tasks.add_task(send_password_reset_email, request.email, first_name, reset_token)

        return {"message": "If the email exists, a password reset link has been sent."}

    except Error as e:
        logger.error(f"Database error during forgot password: {e}")
        raise HTTPException(status_code=500, detail="Database error")
    finally:
        cursor.close()
        conn.close()

async def reset_password(request: ResetPasswordRequest):
    """Reset user password using reset token"""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        # Find user by reset token
        cursor.execute(
            "SELECT id, username, reset_token_expires_at FROM users_info WHERE password_reset_token = %s",
            (request.token,)
        )
        user = cursor.fetchone()

        if not user:
            raise HTTPException(status_code=400, detail="Invalid or expired reset token")

        # Check if token is expired
        reset_token_expires_at = cast(Dict[str, Any], user).get("reset_token_expires_at")
        if reset_token_expires_at is None or reset_token_expires_at < datetime.utcnow():
            raise HTTPException(status_code=400, detail="Reset token has expired")

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

        return {"message": "Password reset successfully"}

    except Error as e:
        logger.error(f"Database error during password reset: {e}")
        raise HTTPException(status_code=500, detail="Database error")
    finally:
        cursor.close()
        conn.close()

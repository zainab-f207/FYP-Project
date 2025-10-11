from fastapi import HTTPException
import os
from app.core.config import ALLOWED_ORIGINS
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import logging

logger = logging.getLogger(__name__)

# Email configuration
SMTP_SERVER = "smtp.gmail.com"  
SMTP_PORT = 587
SMTP_USERNAME = "safevision.noreply@gmail.com"  
SMTP_PASSWORD = "dzik alfk tgxy banc"

def send_verification_email(email: str, first_name: str, verification_token: str):
    """Send email verification email to user"""
    try:
        # Determine frontend URL for verification link. Prefer explicit env var, then ALLOWED_ORIGINS, then fallback.
        frontend_url = os.getenv('FRONTEND_URL')
        if not frontend_url:
            try:
                # For local development, prefer localhost even if ngrok is in ALLOWED_ORIGINS
                if ALLOWED_ORIGINS and len(ALLOWED_ORIGINS) > 0 and 'ngrok' in ALLOWED_ORIGINS[0]:
                    frontend_url = "http://localhost:5173"
                else:
                    # Check if we have localhost origins
                    localhost_origins = [origin for origin in ALLOWED_ORIGINS if 'localhost' in origin or '127.0.0.1' in origin]
                    if localhost_origins:
                        frontend_url = localhost_origins[0]
                    else:
                        frontend_url = ALLOWED_ORIGINS[0] if ALLOWED_ORIGINS and len(ALLOWED_ORIGINS) > 0 else None
            except Exception:
                frontend_url = None

        if not frontend_url:
            frontend_url = "http://localhost:5173"

        # Build link to frontend route which will call backend POST /auth/verify-email with the token.
        verification_link = f"{frontend_url.rstrip('/')}/verify-email?token={verification_token}"
        logger.info(f"Using frontend verification link: {verification_link}")

        # Email template
        html_template = """<!DOCTYPE html>
<html>
  <body style="font-family: Arial, sans-serif; background-color: #f8f9fa; padding: 20px;">
    <div style="max-width: 600px; margin: auto; background: #ffffff; padding: 30px; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
      <h2 style="color: #333333;">Verify Your Account</h2>
      <p>Dear {UserName},</p>
      <p>Thank you for registering with <strong>{YourAppName}</strong>. To activate your account, please verify your email address by clicking the button below:</p>
      <p style="text-align: center; margin: 30px 0;">
        <a href="{VerificationLink}" style="background-color: #007bff; color: #ffffff; padding: 12px 24px; text-decoration: none; border-radius: 5px; font-weight: bold;">Verify Email</a>
      </p>
      <p>This link will expire in 24 hours.</p>
      <p>If you did not create this account, please ignore this message.</p>
      <p>Best regards,<br><strong>{YourAppName} Team</strong><br>support@{yourappdomain}.com</p>
    </div>
  </body>
</html>"""

        # Replace placeholders
        html_content = html_template.replace("{UserName}", first_name)
        html_content = html_content.replace("{YourAppName}", "CrimeVision")
        html_content = html_content.replace("{VerificationLink}", verification_link)
        html_content = html_content.replace("{yourappdomain}", "crimevision.com")

        # Create message
        msg = MIMEMultipart()
        msg['From'] = SMTP_USERNAME
        msg['To'] = email
        msg['Subject'] = "Verify Your CrimeVision Account"

        # Attach HTML content
        msg.attach(MIMEText(html_content, 'html'))

        # Send email
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SMTP_USERNAME, SMTP_PASSWORD)
        text = msg.as_string()
        server.sendmail(SMTP_USERNAME, email, text)
        server.quit()

        logger.info(f"Verification email sent successfully to {email}")

    except Exception as e:
        logger.error(f"Failed to send verification email to {email}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to send verification email")

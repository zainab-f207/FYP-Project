"""Email-based OTP system for mandatory admin/superadmin 2FA."""
import os
import random
import string
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formatdate, make_msgid
from datetime import datetime, timedelta


from app.core.database import get_db_connection

logger = logging.getLogger(__name__)

# Email configuration - reuse existing SMTP settings
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_USERNAME = os.getenv('AUTH_EMAIL_USERNAME', 'safevision.noreply@gmail.com')
SMTP_PASSWORD = os.getenv('AUTH_EMAIL_PASSWORD', '')

OTP_EXPIRY_MINUTES = 5  # OTP valid for 5 minutes


def generate_otp(length: int = 6) -> str:
    """Generate a random numeric OTP code."""
    return ''.join(random.choices(string.digits, k=length))


def store_otp(user_id: int, otp_code: str) -> bool:
    """Store OTP code and expiry in database."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        expires_at = datetime.now() + timedelta(minutes=OTP_EXPIRY_MINUTES)
        cursor.execute(
            "UPDATE users_info SET otp_code = %s, otp_expires_at = %s WHERE id = %s",
            (otp_code, expires_at, user_id)
        )
        conn.commit()
        cursor.close()
        return True
    except Exception as e:
        logger.error(f"Failed to store OTP for user {user_id}: {e}")
        return False
    finally:
        if conn and conn.is_connected():
            conn.close()


def verify_otp(user_id: int, otp_code: str) -> bool:
    """Verify the OTP code for a user."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT otp_code, otp_expires_at FROM users_info WHERE id = %s",
            (user_id,)
        )
        row = cursor.fetchone()  # type: ignore[union-attr]
        if not row:
            return False

        stored_otp = row['otp_code']  # type: ignore[index]
        expires_at = row['otp_expires_at']  # type: ignore[index]

        if not stored_otp or not expires_at:
            return False

        # Check expiry
        if datetime.now() > expires_at:
            logger.warning(f"OTP expired for user {user_id}")
            return False

        # Check code match
        if stored_otp != otp_code:
            return False

        # Clear OTP after successful verification
        cursor.execute(
            "UPDATE users_info SET otp_code = NULL, otp_expires_at = NULL WHERE id = %s",
            (user_id,)
        )
        conn.commit()
        cursor.close()
        return True
    except Exception as e:
        logger.error(f"Failed to verify OTP for user {user_id}: {e}")
        return False
    finally:
        if conn and conn.is_connected():
            conn.close()


def send_otp_email(email: str, name: str, otp_code: str) -> bool:
    """Send OTP code via email."""
    try:
        # Minimal text-style HTML — mimics Google/GitHub verification emails.
        # Heavy gradients, neon colors, emojis, and "security alert" framing trigger spam filters.
        html_content = f"""<!DOCTYPE html>
<html>
  <body style="font-family: Arial, sans-serif; color: #202124; line-height: 1.6; padding: 20px;">
    <p>Hi {name},</p>
    <p>Your SafeVision sign-in code is:</p>
    <p style="font-size: 28px; font-weight: bold; letter-spacing: 6px; margin: 24px 0;">{otp_code}</p>
    <p>This code expires in {OTP_EXPIRY_MINUTES} minutes.</p>
    <p>If you did not try to sign in, you can ignore this message.</p>
    <p>Thanks,<br>The SafeVision team</p>
  </body>
</html>"""

        plain_text = (
            f"Hi {name},\n\n"
            f"Your SafeVision sign-in code is: {otp_code}\n\n"
            f"This code expires in {OTP_EXPIRY_MINUTES} minutes.\n"
            f"If you did not try to sign in, you can ignore this message.\n\n"
            f"Thanks,\nThe SafeVision team\n"
        )

        msg = MIMEMultipart('alternative')
        msg['From'] = f'SafeVision <{SMTP_USERNAME}>'
        msg['To'] = email
        msg['Reply-To'] = SMTP_USERNAME
        msg['Subject'] = "Your SafeVision sign-in code"
        msg['Date'] = formatdate(localtime=True)
        msg['Message-ID'] = make_msgid(domain='safevision.app')
        msg.attach(MIMEText(plain_text, 'plain'))
        msg.attach(MIMEText(html_content, 'html'))

        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SMTP_USERNAME, SMTP_PASSWORD)
        server.sendmail(SMTP_USERNAME, email, msg.as_string())
        server.quit()

        logger.info(f"OTP email sent successfully to {email}")
        return True
    except Exception as e:
        logger.error(f"Failed to send OTP email to {email}: {e}")
        return False


def send_login_alert_email(email: str, name: str, role: str, ip_address: str, login_time: str) -> bool:
    """Send login alert notification email with professional SafeVision branding."""
    try:
        role_badge_bg = "linear-gradient(135deg,#8b5cf6,#6d28d9)" if role == "superadmin" else "linear-gradient(135deg,#00d4ff,#0891b2)"
        role_label = role.upper()
        html_content = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"></head>
<body style="margin:0;padding:0;background:#f1f5f9;font-family:'Segoe UI',Roboto,Arial,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#f1f5f9;padding:40px 0;">
<tr><td align="center">
<table width="560" cellpadding="0" cellspacing="0" style="max-width:560px;width:100%;background:#ffffff;border-radius:16px;overflow:hidden;box-shadow:0 8px 30px rgba(15,23,42,0.12);">
  <!-- Header -->
  <tr><td style="background:linear-gradient(135deg,#0f172a 0%,#1e293b 100%);padding:36px 40px;text-align:center;">
    <div style="display:inline-block;margin-bottom:8px;">
      <span style="font-size:28px;font-weight:800;background:linear-gradient(135deg,#00d4ff,#8b5cf6);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;letter-spacing:1px;">🛡️ SafeVision</span>
    </div>
    <p style="color:rgba(255,255,255,0.5);font-size:11px;margin:6px 0 0;letter-spacing:3px;text-transform:uppercase;">Security Alert</p>
  </td></tr>
  <!-- Body -->
  <tr><td style="padding:36px 40px 24px;">
    <h2 style="color:#0f172a;font-size:20px;margin:0 0 6px;font-weight:700;">🔔 New Login Detected</h2>
    <div style="width:50px;height:3px;background:linear-gradient(135deg,#00d4ff,#8b5cf6);border-radius:2px;margin-bottom:20px;"></div>
    <p style="color:#334155;font-size:15px;line-height:1.7;margin:0 0 6px;">Hi <strong style="color:#0f172a;">{name}</strong>,</p>
    <p style="color:#475569;font-size:15px;line-height:1.7;margin:0 0 24px;">A successful sign-in to your SafeVision admin account was just recorded. Please review the details below.</p>
    <!-- Login Details -->
    <table width="100%" cellpadding="0" cellspacing="0" style="border:1px solid #e2e8f0;border-radius:10px;overflow:hidden;margin:0 0 24px;">
      <tr>
        <td style="padding:12px 18px;background:#f8fafc;font-weight:700;color:#0f172a;font-size:13px;border-bottom:1px solid #e2e8f0;width:120px;">Role</td>
        <td style="padding:12px 18px;background:#f8fafc;border-bottom:1px solid #e2e8f0;">
          <span style="display:inline-block;background:{role_badge_bg};color:#ffffff;font-size:11px;font-weight:700;padding:4px 14px;border-radius:20px;letter-spacing:0.5px;">{role_label}</span>
        </td>
      </tr>
      <tr>
        <td style="padding:12px 18px;font-weight:700;color:#0f172a;font-size:13px;border-bottom:1px solid #e2e8f0;">Time</td>
        <td style="padding:12px 18px;color:#475569;font-size:14px;border-bottom:1px solid #e2e8f0;">{login_time}</td>
      </tr>
      <tr>
        <td style="padding:12px 18px;font-weight:700;color:#0f172a;font-size:13px;">IP Address</td>
        <td style="padding:12px 18px;color:#475569;font-size:14px;font-family:'Courier New',monospace;">{ip_address}</td>
      </tr>
    </table>
  </td></tr>
  <!-- Security Warning -->
  <tr><td style="padding:0 40px 32px;">
    <table width="100%" cellpadding="0" cellspacing="0" style="background:#fef2f2;border-left:4px solid #ef4444;border-radius:0 8px 8px 0;">
      <tr><td style="padding:14px 18px;">
        <p style="color:#991b1b;font-size:13px;margin:0 0 6px;font-weight:700;">⚠️ Wasn't you?</p>
        <p style="color:#7f1d1d;font-size:13px;margin:0;line-height:1.6;">
          If you did not perform this login, your account may be compromised. <strong>Change your password immediately</strong> and contact your system administrator.
        </p>
      </td></tr>
    </table>
  </td></tr>
  <!-- Footer -->
  <tr><td style="background:#f8fafc;padding:20px 40px;border-top:1px solid #e2e8f0;text-align:center;">
    <p style="color:#94a3b8;font-size:11px;margin:0 0 4px;line-height:1.5;">This is an automated security alert from SafeVision. Do not reply.</p>
    <p style="color:#94a3b8;font-size:11px;margin:0;">© {datetime.now().year} SafeVision — Government Crime Prediction &amp; Mapping</p>
  </td></tr>
</table>
</td></tr></table>
</body></html>"""

        plain_text = (
            f"Hi {name},\n\n"
            f"A successful sign-in to your SafeVision {role} account was just recorded.\n\n"
            f"Time: {login_time}\n"
            f"IP address: {ip_address}\n"
            f"Role: {role_label}\n\n"
            f"If this was not you, please change your password and contact your administrator.\n\n"
            f"SafeVision\n"
        )

        msg = MIMEMultipart('alternative')
        msg['From'] = f'SafeVision <{SMTP_USERNAME}>'
        msg['To'] = email
        msg['Reply-To'] = SMTP_USERNAME
        msg['Subject'] = f"New sign-in to your SafeVision {role} account"
        msg['Date'] = formatdate(localtime=True)
        msg['Message-ID'] = make_msgid(domain='safevision.app')
        msg.attach(MIMEText(plain_text, 'plain'))
        msg.attach(MIMEText(html_content, 'html'))

        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SMTP_USERNAME, SMTP_PASSWORD)
        server.sendmail(SMTP_USERNAME, email, msg.as_string())
        server.quit()
        logger.info(f"Login alert email sent to {email}")
        return True
    except Exception as e:
        logger.error(f"Failed to send login alert to {email}: {e}")
        return False


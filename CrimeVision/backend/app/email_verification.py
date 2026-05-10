from fastapi import HTTPException
import os
from app.core.config import ALLOWED_ORIGINS
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formataddr, formatdate, make_msgid
import logging

logger = logging.getLogger(__name__)

# Email configuration
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_USERNAME = os.getenv('AUTH_EMAIL_USERNAME', 'safevision.noreply@gmail.com')
SMTP_PASSWORD = os.getenv('AUTH_EMAIL_PASSWORD', '')  # Set this in your environment variables


def _resolve_frontend_url() -> str:
    """Pick the frontend URL the verification / warning links should point to.

    Order of preference:
      1. FRONTEND_URL env var (always wins — set this in production)
      2. First non-localhost origin in ALLOWED_ORIGINS (so a deployed app
         that listed its render.com URL via the ALLOWED_ORIGINS env will work
         without setting FRONTEND_URL too)
      3. First localhost origin (development fallback)
      4. http://localhost:5173 (last-resort default)
    """
    explicit = os.getenv('FRONTEND_URL')
    if explicit:
        return explicit.rstrip('/')

    try:
        if ALLOWED_ORIGINS:
            non_local = [
                origin for origin in ALLOWED_ORIGINS
                if origin and 'localhost' not in origin and '127.0.0.1' not in origin
            ]
            if non_local:
                return non_local[0].rstrip('/')
            local = [
                origin for origin in ALLOWED_ORIGINS
                if origin and ('localhost' in origin or '127.0.0.1' in origin)
            ]
            if local:
                return local[0].rstrip('/')
    except Exception:
        pass

    return "http://localhost:5173"


def _stamp_message_headers(
    msg: MIMEMultipart,
    subject: str,
    to_email: str,
    *,
    transactional: bool = True,
    bulk: bool = False,
) -> None:
    """Apply headers that improve deliverability when sending via Gmail SMTP.

    Two relevant scenarios:
      * `transactional=True` (default): per-user mail like signup verification,
        warnings, deletion notices. We mark these auto-generated so Gmail
        classifies them as system mail rather than promotional.
      * `bulk=True`: optional flag for the SuperAdmin maintenance summary email
        (one message that goes to all admins). Adds `Precedence: bulk`.

    These headers don't fix sender-domain reputation, but they reliably reduce
    the chance of landing in spam from a free Gmail SMTP sender.
    """
    domain = SMTP_USERNAME.split('@')[-1] if '@' in SMTP_USERNAME else 'safevision.local'

    # Use the bare address (no display name) as the visible From. The mismatch
    # between a brand-style display name ("SafeVision") and a free @gmail.com
    # mailbox is a major Gmail spam trigger; better to let recipients see the
    # actual sending account so the headers line up with the domain.
    msg['From'] = formataddr((None, SMTP_USERNAME))
    msg['To'] = to_email
    msg['Reply-To'] = formataddr((None, SMTP_USERNAME))
    msg['Sender'] = SMTP_USERNAME
    msg['Subject'] = subject
    msg['Date'] = formatdate(localtime=True)
    msg['Message-ID'] = make_msgid(domain=domain)
    msg['MIME-Version'] = '1.0'

    # Mark as auto-generated system mail (RFC 3834). Gmail honors this when
    # classifying — system notifications are less likely to be filtered as
    # promotional/spam than mail with no auto-submitted hint.
    if transactional:
        msg['Auto-Submitted'] = 'auto-generated'
        msg['X-Auto-Response-Suppress'] = 'All'

    # Neutral priority — explicitly NOT low/promotional
    msg['X-Priority'] = '3'
    msg['Importance'] = 'Normal'
    msg['X-Mailer'] = 'SafeVision-Mailer/1.0'

    if bulk:
        msg['Precedence'] = 'bulk'

def send_verification_email(email: str, first_name: str, verification_token: str):
    """Send email verification email to user"""
    try:
        frontend_url = _resolve_frontend_url()
        verification_link = f"{frontend_url}/verify-email?token={verification_token}"
        logger.info(f"Using frontend verification link: {verification_link}")

        # Keep the body short, plain-looking, and identical between text + HTML.
        # Gmail's spam filter compares the two parts; mismatch is a flag. Stay
        # under ~50 lines, one URL, no images, no marketing-style buttons.
        display_name = first_name or "there"

        plain_text = (
            f"Hi {display_name},\n\n"
            "Please confirm your email so you can finish signing in to SafeVision:\n\n"
            f"{verification_link}\n\n"
            "This link is valid for 24 hours. If you did not create a SafeVision "
            "account, you can ignore this message.\n\n"
            "Thanks,\n"
            "The SafeVision team\n"
        )

        html_content = f"""<!DOCTYPE html>
<html>
  <body style="font-family: -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif; color: #1f2937; line-height: 1.55; margin: 0; padding: 24px;">
    <p>Hi {display_name},</p>
    <p>Please confirm your email so you can finish signing in to SafeVision:</p>
    <p><a href="{verification_link}" style="color:#1d4ed8;word-break:break-all;">{verification_link}</a></p>
    <p>This link is valid for 24 hours. If you did not create a SafeVision account, you can ignore this message.</p>
    <p>Thanks,<br>The SafeVision team</p>
  </body>
</html>"""

        msg = MIMEMultipart('alternative')
        _stamp_message_headers(
            msg,
            "Confirm your SafeVision email",
            email,
            transactional=True,
        )
        msg.attach(MIMEText(plain_text, 'plain', 'utf-8'))
        msg.attach(MIMEText(html_content, 'html', 'utf-8'))

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

def send_admin_notification_email(admin_email: str, deleted_accounts: list):
    """Send notification email to SuperAdmin about deleted unverified accounts"""
    try:
        if not deleted_accounts:
            return
        
        # Build HTML table of deleted accounts
        accounts_table = """
        <table style="width: 100%; border-collapse: collapse; margin: 20px 0;">
            <thead>
                <tr style="background-color: #f8f9fa;">
                    <th style="padding: 12px; border: 1px solid #dee2e6; text-align: left;">Username</th>
                    <th style="padding: 12px; border: 1px solid #dee2e6; text-align: left;">Email</th>
                    <th style="padding: 12px; border: 1px solid #dee2e6; text-align: left;">Name</th>
                    <th style="padding: 12px; border: 1px solid #dee2e6; text-align: left;">Created At</th>
                    <th style="padding: 12px; border: 1px solid #dee2e6; text-align: left;">Token Expired At</th>
                </tr>
            </thead>
            <tbody>
        """
        
        for account in deleted_accounts:
            accounts_table += f"""
                <tr>
                    <td style="padding: 12px; border: 1px solid #dee2e6;">{account.get('username', 'N/A')}</td>
                    <td style="padding: 12px; border: 1px solid #dee2e6;">{account.get('email', 'N/A')}</td>
                    <td style="padding: 12px; border: 1px solid #dee2e6;">{account.get('name', 'N/A')}</td>
                    <td style="padding: 12px; border: 1px solid #dee2e6;">{account.get('created_at', 'N/A')}</td>
                    <td style="padding: 12px; border: 1px solid #dee2e6;">{account.get('token_expired_at', 'N/A')}</td>
                </tr>
            """
        
        accounts_table += """
            </tbody>
        </table>
        """
        
        # Email template
        html_template = """<!DOCTYPE html>
<html>
  <body style="font-family: Arial, sans-serif; background-color: #f8f9fa; padding: 20px;">
    <div style="max-width: 800px; margin: auto; background: #ffffff; padding: 30px; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
      <h2 style="color: #333333;">Unverified Accounts Cleanup Report</h2>
      <p>Dear SuperAdmin,</p>
      <p>The automated cleanup process has removed <strong>{AccountCount}</strong> expired unverified user account(s) from the SafeVision system.</p>
      <p>These accounts did not complete email verification within the 24-hour window and have been removed from the database.</p>

      <h3 style="color: #333333; margin-top: 30px;">Affected Accounts:</h3>
      {AccountsTable}

      <hr style="margin: 30px 0; border: none; border-top: 1px solid #dee2e6;">

      <p style="color: #6c757d; font-size: 14px;">
        <strong>Note:</strong> This is an automated notification from the SafeVision account maintenance system.
        The cleanup process runs every 6 hours.
      </p>

      <p>Best regards,<br><strong>SafeVision Automated System</strong></p>
    </div>
  </body>
</html>"""

        # Replace placeholders
        html_content = html_template.replace("{AccountCount}", str(len(deleted_accounts)))
        html_content = html_content.replace("{AccountsTable}", accounts_table)

        plain_lines = [
            "Dear SuperAdmin,",
            "",
            f"The automated cleanup process has removed {len(deleted_accounts)} "
            "expired unverified user account(s) from the SafeVision system.",
            "",
            "Affected accounts:",
        ]
        for account in deleted_accounts:
            plain_lines.append(
                f"- {account.get('username', 'N/A')} | {account.get('email', 'N/A')} "
                f"| {account.get('name', 'N/A')} | created {account.get('created_at', 'N/A')}"
            )
        plain_lines.extend([
            "",
            "This is an automated notification from the SafeVision account maintenance system.",
            "The cleanup process runs every 6 hours.",
            "",
            "SafeVision Automated System",
        ])
        plain_text = "\n".join(plain_lines)

        msg = MIMEMultipart('alternative')
        _stamp_message_headers(
            msg,
            f"SafeVision account maintenance report ({len(deleted_accounts)})",
            admin_email,
            transactional=True,
            bulk=True,
        )
        msg.attach(MIMEText(plain_text, 'plain', 'utf-8'))
        msg.attach(MIMEText(html_content, 'html', 'utf-8'))
        
        # Send email
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SMTP_USERNAME, SMTP_PASSWORD)
        text = msg.as_string()
        server.sendmail(SMTP_USERNAME, admin_email, text)
        server.quit()
        
        logger.info(f"Admin notification email sent successfully to {admin_email}")

    except Exception as e:
        logger.error(f"Failed to send admin notification email to {admin_email}: {str(e)}")
        # Don't raise exception here as this is a notification, not critical


def send_unverified_warning_email(email: str, first_name: str, hours_remaining: int):
    """Warn an unverified user that their account will be deleted soon."""
    try:
        display_name = first_name or "there"
        login_link = f"{_resolve_frontend_url()}/"

        if hours_remaining >= 48:
            window_label = f"{hours_remaining // 24} days"
        elif hours_remaining >= 24:
            window_label = "24 hours" if hours_remaining == 24 else f"{hours_remaining} hours"
        else:
            window_label = f"{hours_remaining} hour(s)"

        # Neutral, transactional subject — avoids "Action required",
        # "Urgent", and similar phrases that Gmail scores as promotional.
        subject = f"Reminder to confirm your SafeVision email"

        plain_text = (
            f"Hi {display_name},\n\n"
            "Your SafeVision account is still unconfirmed. If you don't confirm your email, "
            f"the account will be removed in about {window_label}.\n\n"
            "To keep the account, request a new confirmation link here:\n"
            f"{login_link}\n\n"
            "If you didn't create a SafeVision account, you can ignore this message — "
            "no further action is needed.\n\n"
            "Thanks,\n"
            "The SafeVision team\n"
        )

        html_content = f"""<!DOCTYPE html>
<html>
  <body style="font-family: -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif; color: #1f2937; line-height: 1.55; margin: 0; padding: 24px;">
    <p>Hi {display_name},</p>
    <p>Your SafeVision account is still unconfirmed. If you don't confirm your email,
       the account will be removed in about <strong>{window_label}</strong>.</p>
    <p>To keep the account, request a new confirmation link here:</p>
    <p><a href="{login_link}" style="color:#1d4ed8;word-break:break-all;">{login_link}</a></p>
    <p>If you didn't create a SafeVision account, you can ignore this message — no further action is needed.</p>
    <p>Thanks,<br>The SafeVision team</p>
  </body>
</html>"""

        msg = MIMEMultipart('alternative')
        _stamp_message_headers(msg, subject, email, transactional=True)
        msg.attach(MIMEText(plain_text, 'plain', 'utf-8'))
        msg.attach(MIMEText(html_content, 'html', 'utf-8'))

        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SMTP_USERNAME, SMTP_PASSWORD)
        server.sendmail(SMTP_USERNAME, email, msg.as_string())
        server.quit()

        logger.info(f"Unverified-account warning email sent to {email}")
    except Exception as e:
        logger.error(f"Failed to send warning email to {email}: {e}")


def send_unverified_deleted_email(email: str, first_name: str):
    """Tell the user their unverified account has been deleted."""
    try:
        display_name = first_name or "there"
        subject = "Your SafeVision account was removed"
        signup_link = f"{_resolve_frontend_url()}/"

        plain_text = (
            f"Hi {display_name},\n\n"
            "Your SafeVision account was never confirmed, so it has been removed during "
            "routine cleanup.\n\n"
            "If you still want to use SafeVision, you can sign up again here:\n"
            f"{signup_link}\n\n"
            "This time, please open the confirmation link we send to your email.\n\n"
            "Thanks,\n"
            "The SafeVision team\n"
        )

        html_content = f"""<!DOCTYPE html>
<html>
  <body style="font-family: -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif; color: #1f2937; line-height: 1.55; margin: 0; padding: 24px;">
    <p>Hi {display_name},</p>
    <p>Your SafeVision account was never confirmed, so it has been removed during routine cleanup.</p>
    <p>If you still want to use SafeVision, you can sign up again here:</p>
    <p><a href="{signup_link}" style="color:#1d4ed8;word-break:break-all;">{signup_link}</a></p>
    <p>This time, please open the confirmation link we send to your email.</p>
    <p>Thanks,<br>The SafeVision team</p>
  </body>
</html>"""

        msg = MIMEMultipart('alternative')
        _stamp_message_headers(msg, subject, email, transactional=True)
        msg.attach(MIMEText(plain_text, 'plain', 'utf-8'))
        msg.attach(MIMEText(html_content, 'html', 'utf-8'))

        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SMTP_USERNAME, SMTP_PASSWORD)
        server.sendmail(SMTP_USERNAME, email, msg.as_string())
        server.quit()

        logger.info(f"Unverified-account deletion notice sent to {email}")
    except Exception as e:
        logger.error(f"Failed to send deletion-notice email to {email}: {e}")

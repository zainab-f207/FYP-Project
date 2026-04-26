#!/usr/bin/env python3
"""
Simple Email Test Script - No Emojis for Windows Compatibility
"""
import os
import sys
import smtplib
import socket
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def test_email_connection():
    """Test email sending with enhanced error handling"""
    print("=" * 50)
    print("EMAIL CONFIGURATION TEST")
    print("=" * 50)

    # Load environment variables
    try:
        smtp_server = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
        smtp_port = int(os.getenv('SMTP_PORT', 587))
        smtp_username = os.getenv('SMTP_USERNAME', 'safevision.alerts@gmail.com')
        smtp_password = os.getenv('SMTP_PASSWORD', '')

        print(f"Server: {smtp_server}:{smtp_port}")
        print(f"Username: {smtp_username}")
        print(f"Password: {'*' * len(smtp_password)} (length: {len(smtp_password)})")

        # Test network connectivity first
        print("\nTesting network connectivity...")
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10)
        result = sock.connect_ex(('smtp.gmail.com', 587))
        sock.close()

        if result != 0:
            print(f"FAILED: Cannot connect to {smtp_server}:{smtp_port}")
            print("Check internet connection and firewall settings")
            return False

        print("Network connection OK")

        # Create test email
        msg = MIMEMultipart()
        msg['From'] = f"SafeVision Test <{smtp_username}>"
        msg['To'] = "zainabfayyaz207@gmail.com"
        msg['Subject'] = "SafeVision Email Test - Success"

        body = f"""
        <html><body>
        <h2>Email Configuration Test Successful!</h2>
        <p>If you received this email, your SMTP configuration is working correctly.</p>
        <p><strong>Server:</strong> {smtp_server}:{smtp_port}</p>
        <p><strong>Test completed successfully</strong></p>
        </body></html>
        """

        msg.attach(MIMEText(body, 'html'))

        # Send email with timeout
        print("Connecting to SMTP server...")
        server = smtplib.SMTP(smtp_server, smtp_port, timeout=10)

        print("Starting TLS...")
        server.starttls()

        print("Logging in...")
        server.login(smtp_username, smtp_password)

        print("Sending email...")
        server.send_message(msg)
        server.quit()

        print("SUCCESS: Email sent successfully!")
        print("Check inbox: zainabfayyaz207@gmail.com")
        print("Also check spam/promotions folder")
        return True

    except smtplib.SMTPAuthenticationError as e:
        print(f"AUTHENTICATION FAILED: {e}")
        print("\nPossible solutions:")
        print("1. Check Gmail App Password is correct")
        print("2. Ensure 2FA is enabled on Gmail account")
        print("3. Generate new App Password")
        print("4. Update SMTP_PASSWORD in .env file")
        return False

    except smtplib.SMTPConnectError as e:
        print(f"CONNECTION FAILED: {e}")
        print("\nPossible solutions:")
        print("1. Check internet connection")
        print("2. Check firewall settings")
        print("3. Try different network")
        return False

    except socket.timeout as e:
        print(f"TIMEOUT ERROR: {e}")
        print("\nConnection timed out - check network/firewall")
        return False

    except Exception as e:
        print(f"GENERAL ERROR: {e}")
        print("\nCheck all settings and try again")
        return False

def test_vapid_keys():
    """Test VAPID key configuration"""
    print("\n" + "=" * 50)
    print("BROWSER NOTIFICATION CONFIGURATION TEST")
    print("=" * 50)

    vapid_public = os.getenv('VAPID_PUBLIC_KEY')
    vapid_private = os.getenv('VAPID_PRIVATE_KEY')

    print(f"Public Key: {vapid_public[:20] if vapid_public else 'MISSING'}...")
    print(f"Private Key: {'*' * 20 if vapid_private else 'MISSING'}...")

    if not vapid_public or not vapid_private:
        print("ERROR: VAPID keys missing!")
        print("Run: python generate_vapid_keys.py")
        return False

    if len(vapid_public) < 80 or len(vapid_private) < 40:
        print("ERROR: VAPID keys appear too short!")
        return False

    print("SUCCESS: VAPID keys configuration looks good!")
    return True

if __name__ == "__main__":
    print("SafeVision Notification Test")

    # Test email
    email_success = test_email_connection()

    # Test VAPID
    vapid_success = test_vapid_keys()

    print("\n" + "=" * 50)
    print("FINAL SUMMARY")
    print("=" * 50)
    print(f"Email: {'PASS' if email_success else 'FAIL'}")
    print(f"VAPID: {'PASS' if vapid_success else 'FAIL'}")

    if not email_success:
        print("\nTo fix email issues:")
        print("1. Check Gmail App Password")
        print("2. Update .env file")
        print("3. Restart backend server")

    if not vapid_success:
        print("\nTo fix VAPID issues:")
        print("1. Run: py generate_vapid_keys.py")
        print("2. Update .env file")
        print("3. Restart backend server")
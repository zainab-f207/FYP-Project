#!/usr/bin/env python3
"""
Enhanced Notification Debug Test Script
Tests both email and browser notifications with detailed logging and timeouts
"""
import os
import sys
import smtplib
import asyncio
import socket
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def test_network_connectivity():
    """Test basic network connectivity to Gmail SMTP"""
    print("🌐 Testing network connectivity...")

    try:
        # Test basic socket connection to Gmail SMTP
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10)  # 10 second timeout
        result = sock.connect_ex(('smtp.gmail.com', 587))
        sock.close()

        if result == 0:
            print("✅ Network connection to smtp.gmail.com:587 successful")
            return True
        else:
            print(f"❌ Cannot connect to smtp.gmail.com:587 (Error: {result})")
            print("🔍 Possible issues:")
            print("   - Firewall blocking outbound connections")
            print("   - Corporate network restrictions")
            print("   - Internet connectivity problems")
            return False

    except Exception as e:
        print(f"❌ Network test failed: {e}")
        return False

# Simple email test with timeout
def test_email_direct():
    """Test email sending directly with timeout and detailed error handling"""
    print("🔧 Testing Email Configuration...")

    # First test network connectivity
    if not test_network_connectivity():
        return False

    try:
        # Load environment variables
        smtp_server = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
        smtp_port = int(os.getenv('SMTP_PORT', 587))
        smtp_username = os.getenv('SMTP_USERNAME', 'safevision.alerts@gmail.com')
        smtp_password = os.getenv('SMTP_PASSWORD', 'pwvc mypu lihm upfr')

        print(f"📧 SMTP Config:")
        print(f"   Server: {smtp_server}:{smtp_port}")
        print(f"   Username: {smtp_username}")
        print(f"   Password: {'*' * len(smtp_password)} (length: {len(smtp_password)})")

        # Create test email
        msg = MIMEMultipart()
        msg['From'] = f"SafeVision Test <{smtp_username}>"
        msg['To'] = "zainabfayyaz207@gmail.com"  # Your test email
        msg['Subject'] = "🔧 SafeVision Email Test"

        body = f"""
        <html><body>
        <h2>✅ Email Configuration Test Successful!</h2>
        <p>If you received this email, your SMTP configuration is working correctly.</p>
        <p><strong>Timestamp:</strong> {os.popen('date /T && time /T').read().strip()}</p>
        <p><strong>From:</strong> SafeVision Alert System</p>
        <p><strong>Config:</strong> {smtp_server}:{smtp_port}</p>
        </body></html>
        """

        msg.attach(MIMEText(body, 'html'))

        # Send email with timeout
        print("📤 Connecting to SMTP server (10s timeout)...")
        server = smtplib.SMTP(smtp_server, smtp_port, timeout=10)

        print("🔐 Starting TLS...")
        server.starttls()

        print("🔑 Logging in...")
        server.login(smtp_username, smtp_password)

        print("📨 Sending email...")
        server.send_message(msg)
        server.quit()

        print("✅ Email sent successfully!")
        print("📬 Check your inbox: zainabfayyaz207@gmail.com")
        print("📱 Also check spam/promotions folder")
        return True

    except smtplib.SMTPAuthenticationError as e:
        print(f"❌ Authentication failed: {e}")
        print("🔍 Gmail authentication issues:")
        print("   1. ❌ Wrong Gmail App Password")
        print("   2. ❌ 2FA not enabled on Gmail account")
        print("   3. ❌ App Password generated for wrong account")
        print("   4. ❌ App Password expired or revoked")
        print("\n🔧 To fix:")
        print("   1. Go to Google Account settings")
        print("   2. Security → 2-Step Verification → App passwords")
        print("   3. Generate NEW app password for 'Mail'")
        print("   4. Update SMTP_PASSWORD in .env file")
        return False

    except smtplib.SMTPConnectError as e:
        print(f"❌ Connection failed: {e}")
        print("🔍 Connection issues:")
        print("   - Network/firewall blocking SMTP")
        print("   - Wrong server/port configuration")
        return False

    except socket.timeout as e:
        print(f"❌ Connection timeout: {e}")
        print("🔍 Timeout issues:")
        print("   - Slow network connection")
        print("   - Firewall interference")
        print("   - Corporate network restrictions")
        return False

    except Exception as e:
        print(f"❌ Email test failed: {e}")
        print("🔍 General troubleshooting:")
        print("   1. Check internet connection")
        print("   2. Verify Gmail account credentials")
        print("   3. Check firewall/antivirus settings")
        print("   4. Try from different network")
        return False

async def test_browser_notifications():
    """Test browser notification configuration"""
    print("\n🔧 Testing Browser Notification Configuration...")

    try:
        vapid_public = os.getenv('VAPID_PUBLIC_KEY')
        vapid_private = os.getenv('VAPID_PRIVATE_KEY')

        print(f"📱 VAPID Keys:")
        if vapid_public:
            print(f"   Public: {vapid_public[:20]}... (length: {len(vapid_public)})")
        else:
            print("   Public: ❌ MISSING!")

        if vapid_private:
            print(f"   Private: {'*' * 20}... (length: {len(vapid_private)})")
        else:
            print("   Private: ❌ MISSING!")

        if not vapid_public or not vapid_private:
            print("❌ VAPID keys missing!")
            return False

        if len(vapid_public) < 80 or len(vapid_private) < 40:
            print("❌ VAPID keys appear too short!")
            return False

        print("✅ VAPID keys configuration looks good!")
        print("🔍 Browser notification troubleshooting:")
        print("   1. 🔔 Check browser notification permission")
        print("   2. 🚫 Check if ad blocker is interfering")
        print("   3. 🌐 Test in different browser")
        print("   4. 🔄 Refresh page and try subscribing again")
        print("\n📋 Steps to enable browser notifications:")
        print("   1. Look for 🔔 icon in address bar")
        print("   2. Click 'Allow' for notifications")
        print("   3. Go to User Dashboard → Enable notifications")

        return True

    except Exception as e:
        print(f"❌ Browser notification test failed: {e}")
        return False

def main():
    """Main test function with enhanced error handling"""
    print("="*70)
    print("🧪 SafeVision Enhanced Notification Debug Test")
    print("="*70)

    # Test email with enhanced error handling
    email_success = test_email_direct()

    # Test browser notifications
    browser_success = asyncio.run(test_browser_notifications())

    print("\n" + "="*70)
    print("📊 COMPREHENSIVE SUMMARY:")
    print("="*70)

    if email_success:
        print("✅ Email: Configuration working - check inbox!")
    else:
        print("❌ Email: Configuration needs attention")

    if browser_success:
        print("✅ Browser: VAPID configuration looks good")
    else:
        print("❌ Browser: VAPID configuration needs attention")

    print("\n🎯 NEXT STEPS:")
    if not email_success:
        print("📧 Email Issues:")
        print("   1. Check Gmail App Password is correct")
        print("   2. Ensure 2FA is enabled on Gmail")
        print("   3. Try generating new App Password")
        print("   4. Update .env file and restart backend")

    print("📱 Browser Notifications:")
    print("   1. Grant permission when prompted")
    print("   2. Check browser notification settings")
    print("   3. Disable ad blockers temporarily")
    print("   4. Test in incognito mode")

    print("\n🔄 After fixing issues:")
    print("   1. Restart backend server")
    print("   2. Clear browser cache")
    print("   3. Test alerts again")
    print("="*70)

if __name__ == "__main__":
    main()
"""
Scheduled task to cleanup expired unverified user accounts
Runs periodically to delete accounts where verification token has expired
and sends notifications to SuperAdmin
"""

import schedule
import time
import logging
from datetime import datetime
from app.core.database import get_db_connection
from app.email_verification import send_admin_notification_email
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def cleanup_expired_unverified_accounts():
    """
    Delete user accounts that:
    1. Are not verified (is_verified = FALSE)
    2. Have an expired verification token (token_expires_at < NOW())
    3. Send notification to SuperAdmin about deleted accounts
    """
    conn = None
    cursor = None
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Find expired unverified accounts
        cursor.execute("""
            SELECT id, username, email, first_name, last_name, created_at, token_expires_at
            FROM users_info
            WHERE is_verified = FALSE
            AND token_expires_at IS NOT NULL
            AND token_expires_at < NOW()
        """)
        
        expired_accounts = cursor.fetchall()
        
        if not expired_accounts:
            logger.info("✅ No expired unverified accounts found")
            return
        
        logger.info(f"🗑️ Found {len(expired_accounts)} expired unverified accounts to delete")
        
        # Collect account info for notification
        deleted_accounts_info = []
        
        for account in expired_accounts:
            account_info = {
                'username': account.get('username'),
                'email': account.get('email'),
                'name': f"{account.get('first_name', '')} {account.get('last_name', '')}".strip(),
                'created_at': account.get('created_at'),
                'token_expired_at': account.get('token_expires_at')
            }
            deleted_accounts_info.append(account_info)
            
            # Delete the account
            cursor.execute("DELETE FROM users_info WHERE id = %s", (account.get('id'),))
            logger.info(f"🗑️ Deleted expired account: {account.get('username')} ({account.get('email')})")
        
        conn.commit()
        
        # Send notification to SuperAdmin
        try:
            # Get SuperAdmin email from environment or use default
            super_admin_email = os.getenv('SUPER_ADMIN_EMAIL', 'admin@crimevision.com')
            
            # Send notification email
            send_admin_notification_email(
                admin_email=super_admin_email,
                deleted_accounts=deleted_accounts_info
            )
            
            logger.info(f"📧 Sent notification to SuperAdmin: {super_admin_email}")
            
        except Exception as email_error:
            logger.error(f"❌ Failed to send notification email to SuperAdmin: {email_error}")
        
        logger.info(f"✅ Successfully deleted {len(expired_accounts)} expired unverified accounts")
        
    except Exception as e:
        logger.error(f"❌ Error during cleanup of expired accounts: {e}")
        if conn:
            conn.rollback()
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

def run_scheduler():
    """
    Run the scheduler to periodically cleanup expired accounts
    Runs every 6 hours
    """
    # Schedule the cleanup task to run every 6 hours
    schedule.every(6).hours.do(cleanup_expired_unverified_accounts)
    
    # Also run once immediately on startup
    logger.info("🚀 Starting account cleanup scheduler...")
    cleanup_expired_unverified_accounts()
    
    logger.info("⏰ Scheduler running. Will check for expired accounts every 6 hours.")
    
    while True:
        schedule.run_pending()
        time.sleep(60)  # Check every minute if there's a task to run

if __name__ == "__main__":
    run_scheduler()

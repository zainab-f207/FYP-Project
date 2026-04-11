"""Clean up browser push subscriptions table"""
from app.core.database import get_db_connection
import logging

logger = logging.getLogger(__name__)

def cleanup_subscriptions():
    """Clean up stale browser push subscriptions"""
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Delete all existing subscriptions to start fresh
        cursor.execute("TRUNCATE TABLE browser_push_subscriptions")
        conn.commit()

        logger.info("✅ Successfully cleaned up browser push subscriptions")
        print("✅ Successfully cleaned up browser push subscriptions")
        print("Users will need to re-subscribe to push notifications")

    except Exception as e:
        logger.error(f"Error cleaning up subscriptions: {e}")
        print(f"❌ Error cleaning up subscriptions: {e}")
        if conn:
            conn.rollback()
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()

if __name__ == "__main__":
    cleanup_subscriptions()
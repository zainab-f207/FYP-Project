import mysql.connector

def verify_user():
    try:
        conn = mysql.connector.connect(
            host='localhost',
            user='root',
            password='',
            database='crimevision'
        )
        cursor = conn.cursor()

        # Update user to verified
        cursor.execute("""
            UPDATE users_info
            SET is_verified = TRUE
            WHERE email = 'test@example.com'
        """)

        conn.commit()
        print("User verified successfully")

        cursor.close()
        conn.close()

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    verify_user()

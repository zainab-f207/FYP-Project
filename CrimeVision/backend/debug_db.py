import mysql.connector
import json

def debug_db():
    try:
        conn = mysql.connector.connect(
            host='localhost', 
            user='root', 
            password='hafsa555', 
            database='crimevision_db'
        )
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("SELECT id, username, home_area, alert_radius FROM users_info WHERE id = 47")
        user = cursor.fetchone()
        
        with open("db_debug_output_2.json", "w") as f:
            json.dump(user, f, default=str, indent=2)
            
    except Exception as e:
        with open("db_debug_output_2.json", "w") as f:
            f.write(str(e))
    finally:
        if 'conn' in locals() and conn:
            conn.close()

if __name__ == "__main__":
    debug_db()

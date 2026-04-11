
import mysql.connector
from mysql.connector import Error
import sys
import os
import logging

# Suppress mysql connector info
logging.getLogger('mysql.connector').setLevel(logging.WARNING)

# Add parent directory to path to import app modules if needed
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.database import get_db_config

def check_fatehgarh():
    output_file = 'radius_results.txt'
    with open(output_file, 'w', encoding='utf-8') as f:
        try:
            config = get_db_config()
            connection = mysql.connector.connect(**config)
            cursor = connection.cursor(dictionary=True)
            
            # Fatehgarh coordinates
            lat, lon = 31.5657, 74.3996
            
            f.write(f"Checking radius searches around Fatehgarh ({lat}, {lon}):\n")
            
            for radius in [1000, 2000, 3000, 5000, 10000]:
                cursor.execute("""
                    SELECT COUNT(*) as count 
                    FROM crimes 
                    WHERE ST_Distance_Sphere(point(longitude, latitude), point(%s, %s)) <= %s
                    AND crime_date >= DATE_SUB(NOW(), INTERVAL 365 DAY)
                """, (lon, lat, radius))
                count = cursor.fetchone()['count']
                f.write(f"- Within {radius}m (365d): {count} crimes\n")
                
            f.write("\nAbsolute latest crime date in DB:\n")
            cursor.execute("SELECT MAX(crime_date) as max_date FROM crimes")
            f.write(f"Max date: {cursor.fetchone()['max_date']}\n")

            f.write("\nChecking nearest area from area_coordinates:\n")
            cursor.execute("""
                SELECT area_name, ST_Distance_Sphere(point(longitude, latitude), point(%s, %s)) as dist
                FROM area_coordinates 
                ORDER BY dist ASC 
                LIMIT 5
            """, (lon, lat))
            areas = cursor.fetchall()
            for a in areas:
                cursor.execute("SELECT COUNT(*) as count FROM crimes WHERE area LIKE %s", (f"%{a['area_name']}%",))
                c_count = cursor.fetchone()['count']
                f.write(f"- {a['area_name']} ({a['dist']:.1f}m): {c_count} crimes in DB (via LIKE)\n")

            f.write("\nDistinct areas in crimes table (first 50):\n")
            cursor.execute("SELECT DISTINCT area FROM crimes LIMIT 50")
            for row in cursor.fetchall():
                f.write(f"- {row['area']}\n")

        except Error as e:
            f.write(f"Error: {e}\n")
        finally:
            if 'connection' in locals() and connection.is_connected():
                cursor.close()
                connection.close()
    
    print(f"Results written to {output_file}")

if __name__ == "__main__":
    check_fatehgarh()

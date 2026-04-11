
import mysql.connector
import os

try:
    conn = mysql.connector.connect(
        host='localhost',
        user='root',
        password='',
        database='crime_vision'
    )
    cursor = conn.cursor(dictionary=True)
    cursor.execute("DESCRIBE area_coordinates")
    for row in cursor.fetchall():
        print(row)
    conn.close()
except Exception as e:
    print(f"Error: {e}")

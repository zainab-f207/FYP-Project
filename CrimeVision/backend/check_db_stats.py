from app.core.database import get_db_connection

def check_crimes():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        # Check unique locations
        cursor.execute("SELECT COUNT(DISTINCT latitude, longitude) as count FROM crimes")
        print(f"Unique crime locations: {cursor.fetchone()['count']}")
        
        # Check top locations
        cursor.execute("SELECT latitude, longitude, area, COUNT(*) as count FROM crimes GROUP BY latitude, longitude, area ORDER BY count DESC LIMIT 5")
        print("\nTop Crime Locations:")
        for row in cursor.fetchall():
            print(f"Location: {row['latitude']}, {row['longitude']} ({row['area']}) - Count: {row['count']}")
            
        # Check total crimes
        cursor.execute("SELECT COUNT(*) as count FROM crimes")
        print(f"\nTotal Crimes: {cursor.fetchone()['count']}")
        
        # Check area_coordinates table
        try:
            cursor.execute("SELECT COUNT(*) as count FROM area_coordinates")
            print(f"Area Coordinates records: {cursor.fetchone()['count']}")
            if True:
                 cursor.execute("SELECT area_name, latitude, longitude FROM area_coordinates LIMIT 5")
                 print("\nSample Area Mappings:")
                 for row in cursor.fetchall():
                     print(f"{row['area_name']}: {row['latitude']}, {row['longitude']}")
        except Exception as e:
            print(f"\nError or missing area_coordinates table: {e}")
            
        # Specific check for Fatehgarh
        print("\nChecking for 'Fatehgarh' in crimes:")
        cursor.execute("SELECT COUNT(*) as count FROM crimes WHERE area LIKE '%Fatehgarh%'")
        print(f"Crimes in 'Fatehgarh': {cursor.fetchone()['count']}")
        
        # Check crimes in Gulberg
        print("\nChecking crimes in 'Gulberg':")
        cursor.execute("SELECT COUNT(*) as count FROM crimes WHERE area LIKE '%Gulberg%'")
        print(f"Crimes in 'Gulberg': {cursor.fetchone()['count']}")

        # Overall crime distribution
        print("\nCrime Bounding Box:")
        cursor.execute("SELECT MIN(latitude) as min_lat, MAX(latitude) as max_lat, MIN(longitude) as min_lon, MAX(longitude) as max_lon FROM crimes")
        bbox = cursor.fetchone()
        print(f"Lat: {bbox['min_lat']} to {bbox['max_lat']}")
        print(f"Lon: {bbox['min_lon']} to {bbox['max_lon']}")

        # Simulate the fallback logic for Fatehgarh (31.5657, 74.3996)
        print("\nSimulating Area Fallback for Fatehgarh:")
        cursor.execute("""
            SELECT area_name, ST_Distance_Sphere(point(longitude, latitude), point(%s, %s)) as dist
            FROM area_coordinates 
            ORDER BY dist ASC 
            LIMIT 5
        """, (74.3996, 31.5657))
        matches = cursor.fetchall()
        for idx, m in enumerate(matches):
            print(f"{idx+1}. {m['area_name']} - Distance: {m['dist']:.2f}m")

        # Check date range of crimes
        print("\nCrime Date Range:")
        cursor.execute("SELECT MIN(crime_date) as min_date, MAX(crime_date) as max_date, COUNT(*) as recent_count FROM crimes WHERE crime_date >= DATE_SUB(NOW(), INTERVAL 90 DAY)")
        dates = cursor.fetchone()
        print(f"Oldest: {dates['min_date']}")
        print(f"Newest: {dates['max_date']}")
        print(f"Crimes in last 90 days: {dates['recent_count']}")

        # Check spelling variations for Fatehgarh
        print("\nChecking spelling variations:")
        cursor.execute("SELECT COUNT(*) as count FROM crimes WHERE area LIKE '%Fateh Garh%'")
        print(f"Crimes in 'Fateh Garh': {cursor.fetchone()['count']}")
        cursor.execute("SELECT COUNT(*) as count FROM crimes WHERE area LIKE '%Fatehgarh%'")
        print(f"Crimes in 'Fatehgarh': {cursor.fetchone()['count']}")
        
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    check_crimes()

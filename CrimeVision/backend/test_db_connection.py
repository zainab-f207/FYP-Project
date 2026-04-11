"""
Test database connection and verify data exists
"""

import sys
sys.path.insert(0, '.')

from app.core.database import get_db_connection

try:
    print("\n" + "="*60)
    print("DATABASE CONNECTION TEST")
    print("="*60)
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    print("✅ Database connection successful")
    
    # Check if crimes table exists and has data
    cursor.execute('SELECT COUNT(*) as count FROM crimes')
    result = cursor.fetchone()
    crime_count = result['count'] if result else 0
    print(f"✅ Crime records in database: {crime_count}")
    
    # Check recent crimes (last 90 days)
    cursor.execute("""
        SELECT COUNT(*) as count FROM crimes 
        WHERE crime_date >= DATE_SUB(NOW(), INTERVAL 90 DAY)
    """)
    result = cursor.fetchone()
    recent_crime_count = result['count'] if result else 0
    print(f"✅ Recent crimes (last 90 days): {recent_crime_count}")
    
    # Check if locations table exists
    cursor.execute('SELECT COUNT(*) as count FROM locations')
    result = cursor.fetchone()
    location_count = result['count'] if result else 0
    print(f"✅ Total locations in database: {location_count}")
    
    # Check police stations
    cursor.execute("SELECT COUNT(*) as count FROM locations WHERE location_type = 'police_station'")
    result = cursor.fetchone()
    police_count = result['count'] if result else 0
    print(f"✅ Police stations: {police_count}")
    
    # Check hospitals
    cursor.execute("SELECT COUNT(*) as count FROM locations WHERE location_type = 'hospital'")
    result = cursor.fetchone()
    hospital_count = result['count'] if result else 0
    print(f"✅ Hospitals: {hospital_count}")
    
    # Test ST_Distance_Sphere function
    print("\n" + "-"*60)
    print("Testing ST_Distance_Sphere function...")
    print("-"*60)
    
    try:
        cursor.execute("""
            SELECT ST_Distance_Sphere(
                point(-74.0060, 40.7128),
                point(-73.9855, 40.7580)
            ) as distance_meters
        """)
        result = cursor.fetchone()
        if result:
            distance = result['distance_meters']
            print(f"✅ ST_Distance_Sphere works! Distance: {distance:.2f} meters")
        else:
            print("❌ ST_Distance_Sphere returned no result")
    except Exception as e:
        print(f"❌ ST_Distance_Sphere error: {e}")
    
    # Test crime query with spatial function
    print("\n" + "-"*60)
    print("Testing crime query with spatial function...")
    print("-"*60)
    
    try:
        cursor.execute("""
            SELECT
                COUNT(*) as crime_count,
                SUM(CASE WHEN risk_level = 'High' THEN 3
                         WHEN risk_level = 'Medium' THEN 2
                         WHEN risk_level = 'Low' THEN 1
                         ELSE 1 END) as risk_score
            FROM crimes
            WHERE ST_Distance_Sphere(
                point(longitude, latitude),
                point(-74.0060, 40.7128)
            ) <= 1000
            AND crime_date >= DATE_SUB(NOW(), INTERVAL 90 DAY)
        """)
        result = cursor.fetchone()
        if result:
            print(f"✅ Crime query works!")
            print(f"   Crimes within 1km: {result['crime_count']}")
            print(f"   Risk score: {result['risk_score']}")
        else:
            print("❌ Crime query returned no result")
    except Exception as e:
        print(f"❌ Crime query error: {e}")
        import traceback
        traceback.print_exc()
    
    # Check areas table
    print("\n" + "-"*60)
    print("Checking areas table...")
    print("-"*60)

    cursor.execute('SELECT COUNT(*) as count FROM areas')
    result = cursor.fetchone()
    areas_count = result['count'] if result else 0
    print(f"✅ Total areas: {areas_count}")

    # Check area_coordinates table
    cursor.execute('SELECT COUNT(*) as count FROM area_coordinates')
    result = cursor.fetchone()
    area_coords_count = result['count'] if result else 0
    print(f"✅ Area coordinates: {area_coords_count}")

    cursor.close()
    conn.close()

    print("\n" + "="*60)
    print("✅ DATABASE TESTS COMPLETED")
    print("="*60 + "\n")

except Exception as e:
    print(f"\n❌ Database error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)


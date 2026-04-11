import os
import sys
sys.path.append(os.getcwd())
try:
    from app.core.database import get_db_connection
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    print("--- VERIFYING ALERT LOGS ---")
    cursor.execute("SELECT user_id, message, high_risk_count, created_at FROM alert_notifications ORDER BY created_at DESC LIMIT 3")
    for row in cursor.fetchall():
        print(f"Time: {row['created_at']}, Msg: {row['message'][:100]}..., Count: {row['high_risk_count']}")

    print("\n--- VERIFYING REHMAN VILLAS (Bahria Orchard coords) ---")
    # Coordinates from previous turn sensor log for user 47
    lng, lat = 74.39, 31.47 
    # Try with name too
    area_name = "Rehman Villas"
    cursor.execute("SELECT COUNT(*) as cnt FROM crimes WHERE ST_Distance_Sphere(point(longitude, latitude), point(%s, %s)) <= 1200", (lng, lat))
    r1 = cursor.fetchone()
    print(f"Radius check (1.2km) counts: {r1['cnt']}")

    cursor.execute("SELECT area, COUNT(*) as cnt FROM crimes WHERE ST_Distance_Sphere(point(longitude, latitude), point(%s, %s)) <= 1200 GROUP BY area ORDER BY cnt DESC", (lng, lat))
    print(f"Subareas in radius: {cursor.fetchall()}")

    print("\n--- VERIFYING DHA PHASE 4 ---")
    # Coordinates for Phase 4 (roughly)
    lng4, lat4 = 74.4371, 31.4398
    cursor.execute("SELECT COUNT(*) as cnt FROM crimes WHERE ST_Distance_Sphere(point(longitude, latitude), point(%s, %s)) <= 1200", (lng4, lat4))
    r2 = cursor.fetchone()
    print(f"Radius check (DHA Ph 4, 1.2km) counts: {r2['cnt']}")
    
    cursor.execute("SELECT COUNT(*) as cnt FROM crimes WHERE area LIKE '%Phase 4%' AND risk_level='High' AND crime_date >= (NOW() - INTERVAL 365 DAY)")
    r3 = cursor.fetchone()
    print(f"Overall DHA Phase 4 High Risk (365d): {r3}")

    # Check riskiest subareas for Phase 4 spatial
    cursor.execute("SELECT area, COUNT(*) as cnt FROM crimes WHERE ST_Distance_Sphere(point(longitude, latitude), point(%s, %s)) <= 1200 GROUP BY area ORDER BY cnt DESC LIMIT 5", (lng4, lat4))
    print(f"Subareas near Ph 4: {cursor.fetchall()}")

    cursor.close()
    conn.close()
except Exception as e:
    print(f"Verification Error: {e}")
    import traceback
    traceback.print_exc()

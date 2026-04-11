import sys
with open('../backend/main.py', 'r', encoding='utf-8') as f:
    text = f.read()

old_radar = '''            # Breakdown for Radar Chart (Radius based - using 5km)
            cursor.execute("""
                SELECT crime_type, COUNT(*) as count
                FROM crimes
                WHERE ST_Distance_Sphere(point(longitude, latitude), point(%s, %s)) <= 5000
                AND crime_date >= DATE_SUB(NOW(), INTERVAL 365 DAY)
                GROUP BY crime_type
            """, (lon, lat))
            crime_counts = cursor.fetchall()
            
            # Time of Day Breakdown
            cursor.execute("""
                SELECT 
                    SUM(CASE WHEN HOUR(crime_date) BETWEEN 6 AND 18 THEN 1 ELSE 0 END) as day_crimes,
                    SUM(CASE WHEN HOUR(crime_date) NOT BETWEEN 6 AND 18 THEN 1 ELSE 0 END) as night_crimes
                FROM crimes
                WHERE ST_Distance_Sphere(point(longitude, latitude), point(%s, %s)) <= 5000
                AND crime_date >= DATE_SUB(NOW(), INTERVAL 365 DAY)
            """, (lon, lat))
            time_stats = cursor.fetchone()'''

new_radar = '''            # Breakdown for Radar Chart
            if confidence == "medium" and 'search_pattern' in locals():
                cursor.execute("""
                    SELECT crime_type, COUNT(*) as count
                    FROM crimes
                    WHERE area LIKE %s
                    AND crime_date >= DATE_SUB(NOW(), INTERVAL 365 DAY)
                    GROUP BY crime_type
                """, (search_pattern,))
                crime_counts = cursor.fetchall()
                
                cursor.execute("""
                    SELECT 
                        SUM(CASE WHEN HOUR(crime_date) BETWEEN 6 AND 18 THEN 1 ELSE 0 END) as day_crimes,
                        SUM(CASE WHEN HOUR(crime_date) NOT BETWEEN 6 AND 18 THEN 1 ELSE 0 END) as night_crimes
                    FROM crimes
                    WHERE area LIKE %s
                    AND crime_date >= DATE_SUB(NOW(), INTERVAL 365 DAY)
                """, (search_pattern,))
                time_stats = cursor.fetchone()
            else:
                cursor.execute("""
                    SELECT crime_type, COUNT(*) as count
                    FROM crimes
                    WHERE ST_Distance_Sphere(point(longitude, latitude), point(%s, %s)) <= 5000
                    AND crime_date >= DATE_SUB(NOW(), INTERVAL 365 DAY)
                    GROUP BY crime_type
                """, (lon, lat))
                crime_counts = cursor.fetchall()
                
                cursor.execute("""
                    SELECT 
                        SUM(CASE WHEN HOUR(crime_date) BETWEEN 6 AND 18 THEN 1 ELSE 0 END) as day_crimes,
                        SUM(CASE WHEN HOUR(crime_date) NOT BETWEEN 6 AND 18 THEN 1 ELSE 0 END) as night_crimes
                    FROM crimes
                    WHERE ST_Distance_Sphere(point(longitude, latitude), point(%s, %s)) <= 5000
                    AND crime_date >= DATE_SUB(NOW(), INTERVAL 365 DAY)
                """, (lon, lat))
                time_stats = cursor.fetchone()'''

text = text.replace(old_radar, new_radar)

with open('../backend/main.py', 'w', encoding='utf-8') as f:
    f.write(text)
print('Radar chart fixed')

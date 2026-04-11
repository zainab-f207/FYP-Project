import sys
with open('../backend/main.py', 'r', encoding='utf-8') as f:
    text = f.read()

old_prev = '''            # Previous Period (Comparison)
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_crimes,
                    SUM(CASE WHEN risk_level = 'High' THEN 1 ELSE 0 END) as high_risk_count,
                    SUM(CASE WHEN risk_level = 'Medium' THEN 1 ELSE 0 END) as medium_risk_count,
                    SUM(CASE WHEN risk_level = 'Low' THEN 1 ELSE 0 END) as low_risk_count,
                    SUM(CASE WHEN risk_level IS NULL OR risk_level = 'Unknown' THEN 1 ELSE 0 END) as unknown_risk_count,
                    COUNT(DISTINCT crime_type) as unique_crime_types
                FROM crimes 
                WHERE ST_Distance_Sphere(point(longitude, latitude), point(%s, %s)) <= 5000
                AND crime_date >= DATE_SUB(NOW(), INTERVAL 730 DAY)
                AND crime_date < DATE_SUB(NOW(), INTERVAL 365 DAY)
            """, (lon, lat))
            prev_stats = cursor.fetchone()'''

new_prev = '''            # Previous Period (Comparison)
            if confidence == "medium" and 'search_pattern' in locals():
                cursor.execute("""
                    SELECT 
                        COUNT(*) as total_crimes,
                        SUM(CASE WHEN risk_level = 'High' THEN 1 ELSE 0 END) as high_risk_count,
                        SUM(CASE WHEN risk_level = 'Medium' THEN 1 ELSE 0 END) as medium_risk_count,
                        SUM(CASE WHEN risk_level = 'Low' THEN 1 ELSE 0 END) as low_risk_count,
                        SUM(CASE WHEN risk_level IS NULL OR risk_level = 'Unknown' THEN 1 ELSE 0 END) as unknown_risk_count,
                        COUNT(DISTINCT crime_type) as unique_crime_types
                    FROM crimes 
                    WHERE area LIKE %s
                    AND crime_date >= DATE_SUB(NOW(), INTERVAL 730 DAY)
                    AND crime_date < DATE_SUB(NOW(), INTERVAL 365 DAY)
                """, (search_pattern,))
            else:
                cursor.execute("""
                    SELECT 
                        COUNT(*) as total_crimes,
                        SUM(CASE WHEN risk_level = 'High' THEN 1 ELSE 0 END) as high_risk_count,
                        SUM(CASE WHEN risk_level = 'Medium' THEN 1 ELSE 0 END) as medium_risk_count,
                        SUM(CASE WHEN risk_level = 'Low' THEN 1 ELSE 0 END) as low_risk_count,
                        SUM(CASE WHEN risk_level IS NULL OR risk_level = 'Unknown' THEN 1 ELSE 0 END) as unknown_risk_count,
                        COUNT(DISTINCT crime_type) as unique_crime_types
                    FROM crimes 
                    WHERE ST_Distance_Sphere(point(longitude, latitude), point(%s, %s)) <= 5000
                    AND crime_date >= DATE_SUB(NOW(), INTERVAL 730 DAY)
                    AND crime_date < DATE_SUB(NOW(), INTERVAL 365 DAY)
                """, (lon, lat))
            prev_stats = cursor.fetchone()'''

text = text.replace(old_prev, new_prev)

with open('../backend/main.py', 'w', encoding='utf-8') as f:
    f.write(text)
print('Prev fixed')

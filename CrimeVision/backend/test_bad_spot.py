import sys
import asyncio
sys.path.append('d:/FYP/Project/CrimeVision/backend')
from app.routes.alerts import get_real_safety_data_from_endpoints
from app.core.database import get_db_connection

async def get_bad_spot():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT latitude, longitude, area FROM crimes WHERE risk_level='High' GROUP BY area, latitude, longitude ORDER BY COUNT(*) DESC LIMIT 5")
    for row in cursor.fetchall():
        lat, lng = float(row['latitude']), float(row['longitude'])
        res = await get_real_safety_data_from_endpoints(lat, lng, row['area'])
        if res['is_high_risk']:
            with open('test_bad_spot_output.txt', 'w', encoding='utf-8') as f:
                f.write(f"BINGO: Lat {lat}, Lng {lng} is HIGH RISK! (Score: {res['safety_score']}%)")
            return
    with open('test_bad_spot_output.txt', 'w', encoding='utf-8') as f:
        f.write("Could not find a high risk spot easily.")

asyncio.run(get_bad_spot())

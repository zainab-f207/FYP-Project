import warnings
warnings.filterwarnings("ignore")
from app.core.database import get_db_connection
conn = get_db_connection()
cur = conn.cursor(dictionary=True)
cur.execute("SELECT COUNT(DISTINCT area_urdu) as n FROM crimes WHERE area_urdu IS NOT NULL AND area_urdu <> ''")
row = cur.fetchone()
print("Unique area_urdu values:", row["n"])
# Estimate: 1 API call per area at 1sec/call + text-match cache hits
# Likely ~30-50% text-match hits (no API needed)
conn.close()

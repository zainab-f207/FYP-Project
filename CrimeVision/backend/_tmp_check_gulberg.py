from app.core.database import get_db_connection
c = get_db_connection()
cur = c.cursor(dictionary=True)
cur.execute("SHOW COLUMNS FROM crimes")
cols = [r["Field"] for r in cur.fetchall()]
print("COLS", cols)
cur.execute("SELECT COUNT(*) c FROM crimes WHERE area LIKE %s", ('%gulberg%',))
print("TOTAL_GULBERG", cur.fetchone()['c'])
cur.execute("SELECT COALESCE(NULLIF(TRIM(crime_type),''),'__NULL__') ct, COUNT(*) c FROM crimes WHERE area LIKE %s GROUP BY ct ORDER BY c DESC LIMIT 20", ('%gulberg%',))
print("TOP_CT", cur.fetchall())
cur.close()
c.close()

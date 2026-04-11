from app.core.database import get_db_connection
c=get_db_connection(); cur=c.cursor(dictionary=True)
cur.execute("SELECT area, COUNT(*) c FROM crimes WHERE area LIKE %s GROUP BY area ORDER BY c DESC LIMIT 20", ('%fateh%',))
print('AREAS_MATCH_FATEH', cur.fetchall())
cur.close(); c.close()

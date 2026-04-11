from app.core.database import get_db_connection
c=get_db_connection(); cur=c.cursor(dictionary=True)
areas=['Gulberg','Fatehgarh','Fathegarh']
for a in areas:
    cur.execute("SELECT COUNT(*) c FROM crimes WHERE area=%s", (a,))
    exact=cur.fetchone()['c']
    cur.execute("SELECT COUNT(*) c FROM crimes WHERE area LIKE %s", (f'%{a}%',))
    like=cur.fetchone()['c']
    print(a, 'EXACT', exact, 'LIKE', like)

cur.execute("SELECT area, COUNT(*) c FROM crimes WHERE area LIKE %s GROUP BY area ORDER BY c DESC", ('%fatehgarh%',))
print('AREAS_MATCH_FATEHGARH', cur.fetchall())

cur.execute("SELECT area, COUNT(*) c FROM crimes WHERE area LIKE %s GROUP BY area ORDER BY c DESC", ('%fathegarh%',))
print('AREAS_MATCH_FATHEGARH', cur.fetchall())

cur.close(); c.close()

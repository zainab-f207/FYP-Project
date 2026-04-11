from app.core.database import get_db_connection

conn=get_db_connection(); cur=conn.cursor()

print('=== AREAS TABLE CHECK ===')
cur.execute("SELECT area_name FROM areas WHERE area_name LIKE 'DHA Phase %' ORDER BY area_name")
for r in cur.fetchall():
    print(r[0] if isinstance(r,(list,tuple)) else r['area_name'])
cur.execute("SELECT area_name FROM areas WHERE LOWER(area_name) LIKE '%badami bagh%' ORDER BY area_name")
rows=cur.fetchall()
print('Badami areas:', [row[0] if isinstance(row,(list,tuple)) else row['area_name'] for row in rows])

print('\n=== DHA PHASES IN CRIMES ===')
for p in ['DHA Phase 1','DHA Phase 2','DHA Phase 3','DHA Phase 4','DHA Phase 5','DHA Phase 6']:
    cur.execute('SELECT COUNT(*) FROM crimes WHERE area=%s',(p,))
    print(p, cur.fetchone()[0])

print('\n=== DHA URDU ROWS DISTRIBUTION ===')
cur.execute('''
    SELECT area, area_translit, COUNT(*) c
    FROM crimes
    WHERE area_urdu LIKE '%ڈی ایچ اے%'
    GROUP BY area, area_translit
    ORDER BY c DESC
    LIMIT 80
''')
for a,t,c in cur.fetchall():
    print(f'{c:4d} | area={a} | translit={t}')

print('\n=== BADAMI BAGH IN CRIMES (URDU/translit) ===')
cur.execute('''
    SELECT area_urdu, area_translit, area, COUNT(*) c
    FROM crimes
    WHERE area_urdu LIKE '%بادامی باغ%' OR LOWER(area_translit) LIKE '%badami bagh%'
    GROUP BY area_urdu, area_translit, area
    ORDER BY c DESC
    LIMIT 80
''')
rows=cur.fetchall()
if not rows:
    print('NO_ROWS')
else:
    for u,t,a,c in rows:
        print(f'{c:4d} | area={a} | urdu={u} | translit={t}')

print('\n=== Potential DHA translit casing issues ===')
cur.execute('''
    SELECT area_translit, COUNT(*) c
    FROM crimes
    WHERE area_urdu LIKE '%ڈی ایچ اے%' AND (area_translit LIKE 'Dha %' OR area_translit LIKE 'Dha%')
    GROUP BY area_translit
    ORDER BY c DESC
    LIMIT 30
''')
rows=cur.fetchall()
if not rows:
    print('NO_DHA_CASING_ISSUES')
else:
    for t,c in rows:
        print(f'{c:4d} | {t}')

cur.close(); conn.close()

import re
from app.core.database import get_db_connection

conn=get_db_connection(); cur=conn.cursor()

cur.execute("SELECT id, area_urdu, area_translit, area FROM crimes WHERE area_urdu LIKE '%ڈی ایچ اے%' OR LOWER(area_translit) LIKE '%dha phase %'")
rows=cur.fetchall()

phase_re_ur = re.compile(r'فیز\s*(\d+)')
phase_re_en = re.compile(r'dha\s*phase\s*(\d+)', re.I)

tot=0
mismatch=0
phase16=0
phase16_mismatch=0
for row in rows:
    rid,u,t,a = row
    u=u or ''
    t=t or ''
    found=None
    m=phase_re_ur.search(u)
    if m:
        found=int(m.group(1))
    else:
        m2=phase_re_en.search(t)
        if m2:
            found=int(m2.group(1))
    if found is None:
        continue
    tot += 1
    expected=f'DHA Phase {found}'
    if 1 <= found <= 6:
        phase16 += 1
        if a != expected:
            phase16_mismatch += 1
    if a != expected:
        mismatch += 1

print('dha_rows_with_detected_phase=', tot)
print('all_phase_mismatches=', mismatch)
print('phase1to6_rows=', phase16)
print('phase1to6_mismatches=', phase16_mismatch)

print('\nSample phase1to6 mismatches (top 20):')
cur.execute("""
    SELECT id, area_urdu, area_translit, area
    FROM crimes
    WHERE (area_urdu LIKE '%ڈی ایچ اے فیز 1%' OR area_urdu LIKE '%ڈی ایچ اے فیز 2%' OR area_urdu LIKE '%ڈی ایچ اے فیز 3%' OR area_urdu LIKE '%ڈی ایچ اے فیز 4%' OR area_urdu LIKE '%ڈی ایچ اے فیز 5%' OR area_urdu LIKE '%ڈی ایچ اے فیز 6%')
      AND area NOT IN ('DHA Phase 1','DHA Phase 2','DHA Phase 3','DHA Phase 4','DHA Phase 5','DHA Phase 6')
    LIMIT 20
""")
for rid,u,t,a in cur.fetchall():
    print(rid, '|', a, '|', u, '|', t)

cur.close(); conn.close()

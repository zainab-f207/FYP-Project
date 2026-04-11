import re
from app.core.database import get_db_connection
from import_fir_data import _urdu_to_english_area

conn=get_db_connection(); cur=conn.cursor()

# 1) Normalize DHA transliteration casing globally where applicable
cur.execute('''
    UPDATE crimes
    SET area_translit = REPLACE(area_translit, 'Dha Phase', 'DHA Phase')
    WHERE area_urdu LIKE '%ڈی ایچ اے%' OR area LIKE 'DHA Phase %'
''')
case_fix_rows = cur.rowcount

# 2) Recompute transliteration + enforce area for DHA phases 1-6 from Urdu/translit phase extraction
cur.execute("SELECT id, area_urdu, area_translit, area FROM crimes WHERE area_urdu LIKE '%ڈی ایچ اے%'")
rows=cur.fetchall()
phase_re_ur = re.compile(r'فیز\s*(\d+)')
phase_re_en = re.compile(r'dha\s*phase\s*(\d+)', re.I)

fix_rows=0
for rid,u,t,a in rows:
    u = u or ''
    t = t or ''

    m = phase_re_ur.search(u)
    phase = int(m.group(1)) if m else None
    if phase is None:
        m2 = phase_re_en.search(t)
        if m2:
            phase = int(m2.group(1))

    # translation normalization
    new_t = _urdu_to_english_area(u) if u else t
    new_t = (new_t or t).replace('Pcsir', 'PCSIR').replace('Dha Phase', 'DHA Phase')

    new_area = a
    if phase is not None and 1 <= phase <= 6:
        new_area = f'DHA Phase {phase}'

    if new_t != t or new_area != a:
        cur.execute('UPDATE crimes SET area_translit=%s, area=%s WHERE id=%s', (new_t, new_area, rid))
        fix_rows += cur.rowcount

# 3) Badami Bagh rows (if any)
cur.execute("SELECT id, area_urdu, area_translit, area FROM crimes WHERE area_urdu LIKE '%بادامی باغ%' OR LOWER(area_translit) LIKE '%badami bagh%'")
b_rows=cur.fetchall()
b_fix=0
for rid,u,t,a in b_rows:
    u = u or ''
    new_t = _urdu_to_english_area(u) if u else (t or '')
    if 'Badami Bagh' not in new_t:
        if new_t:
            new_t = f'Badami Bagh, {new_t}'
        else:
            new_t = 'Badami Bagh'
    new_area = 'Badami Bagh, Lahore'
    if new_t != (t or '') or new_area != (a or ''):
        cur.execute('UPDATE crimes SET area_translit=%s, area=%s WHERE id=%s', (new_t, new_area, rid))
        b_fix += cur.rowcount

conn.commit()
print(f'dha_case_fix_rows={case_fix_rows}')
print(f'dha_phase_1to6_rows_updated={fix_rows}')
print(f'badami_bagh_rows_updated={b_fix}')

# quick verify
print('\n=== DHA PHASE 1-6 COUNTS (POST) ===')
for p in range(1,7):
    cur.execute('SELECT COUNT(*) FROM crimes WHERE area=%s', (f'DHA Phase {p}',))
    print(f'DHA Phase {p}:', cur.fetchone()[0])

cur.execute('''
    SELECT COUNT(*)
    FROM crimes
    WHERE area_urdu LIKE '%ڈی ایچ اے فیز 1%' AND area <> 'DHA Phase 1'
       OR area_urdu LIKE '%ڈی ایچ اے فیز 2%' AND area <> 'DHA Phase 2'
       OR area_urdu LIKE '%ڈی ایچ اے فیز 3%' AND area <> 'DHA Phase 3'
       OR area_urdu LIKE '%ڈی ایچ اے فیز 4%' AND area <> 'DHA Phase 4'
       OR area_urdu LIKE '%ڈی ایچ اے فیز 5%' AND area <> 'DHA Phase 5'
       OR area_urdu LIKE '%ڈی ایچ اے فیز 6%' AND area <> 'DHA Phase 6'
''')
print('remaining_phase1to6_mismatch_rows=', cur.fetchone()[0])

cur.close(); conn.close()

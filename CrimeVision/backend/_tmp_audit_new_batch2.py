from app.core.database import get_db_connection

conn=get_db_connection(); cur=conn.cursor(dictionary=True)

checks=[
'راوی روڈ، راوی روڈ',
'کینٹ صدر بازار، صدر بازار روڈ',
'آسکاری 12 بلاک A، کینٹ روڈ',
'بحریہ آرچرڈ فیز 4 بلاک H، کینٹ روڈ',
'الخضریا ہاؤسنگ بلاک H، کینٹ روڈ',
'لال کرتی کینٹ، ٹھوکر نیاز بیگ انٹرچینج',
'سرفرار روڈ کینٹ، گجومتہ انٹرچینج',
'فوجی کالونی کینٹ، نجات روڈ',
'پی آئی اے سوسائٹی بلاک H سب بلاک P',
'فورٹریس اسٹیڈیم ایریا سب بلاک K',
'چوبرجی انڈر پاس',
'نہر کنار روڈ',
'جیل روڈ، جیل روڈ'
]
for u in checks:
    cur.execute('SELECT area, area_translit, COUNT(*) cnt FROM crimes WHERE area_urdu=%s GROUP BY area, area_translit ORDER BY cnt DESC',(u,))
    rows=cur.fetchall(); print(f"\n[EXACT] {u}")
    if not rows: print('  (no exact rows)')
    for r in rows: print(f"{int(r['cnt']):>4} | area={r['area']} | translit={r['area_translit']}")

likes=['راوی روڈ','کینٹ صدر بازار','آسکاری','بحریہ آرچرڈ','الخضریا','لال کرتی','سرفرار روڈ','فوجی کالونی','پی آئی اے سوسائٹی','فورٹریس اسٹیڈیم ایریا','چوبرجی','نہر کنار روڈ','جیل روڈ']
for k in likes:
    cur.execute("SELECT area, area_urdu, area_translit, COUNT(*) cnt FROM crimes WHERE area_urdu LIKE %s GROUP BY area, area_urdu, area_translit ORDER BY cnt DESC LIMIT 30",(f"%{k}%",))
    rows=cur.fetchall(); print(f"\n[LIKE] {k}")
    for r in rows: print(f"{int(r['cnt']):>4} | area={r['area']} | {r['area_urdu']} -> {r['area_translit']}")

cur.close(); conn.close()

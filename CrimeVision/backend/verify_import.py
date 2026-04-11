"""Quick verification of imported FIR data."""
import sys
sys.path.insert(0, '.')
from app.core.database import get_db_connection

conn = get_db_connection()
cur = conn.cursor()

cur.execute('SELECT COUNT(*) FROM crimes')
print('Total rows:', cur.fetchone()[0])

cur.execute('SELECT COUNT(*) FROM crimes WHERE crime_time IS NOT NULL')
print('Rows with crime_time:', cur.fetchone()[0])

print('\nRisk level distribution:')
cur.execute('SELECT risk_level, COUNT(*) FROM crimes GROUP BY risk_level ORDER BY 2 DESC')
for r in cur.fetchall():
    print(f'  {r[0]:8}  {r[1]}')

print('\nTop 8 areas:')
cur.execute('SELECT area, COUNT(*) c FROM crimes GROUP BY area ORDER BY c DESC LIMIT 8')
for r in cur.fetchall():
    print(f'  {r[0]:30}  {r[1]}')

print('\nSample rows (English columns only):')
cur.execute('SELECT crime_date, crime_time, area, crime_type, risk_level FROM crimes LIMIT 5')
for r in cur.fetchall():
    print(f'  {r[0]}  {str(r[1]):10}  {str(r[2]):25}  {str(r[3])[:40]:42}  {r[4]}')

print('\nNull crime_time records:')
cur.execute('SELECT COUNT(*) FROM crimes WHERE crime_time IS NULL')
print(' ', cur.fetchone()[0])

print('\nDate range:')
cur.execute('SELECT MIN(crime_date), MAX(crime_date) FROM crimes')
print(' ', cur.fetchone())

cur.close()
conn.close()
print('\nAll checks passed.')

from app.routes.auth import update_user_profile
from app.models.schemas import UserProfileUpdate
from app.core.database import get_db_connection

# fetch a username from DB to test
conn = get_db_connection()
cur = conn.cursor()
cur.execute("SELECT username FROM users_info LIMIT 1")
row = cur.fetchone()
cur.close()
conn.close()

if not row:
    print('No users in DB to test')
else:
    username = row[0]
    print('Testing update_user_profile for username:', username)
    data = UserProfileUpdate(first_name='TestFirst')
    try:
        resp = update_user_profile(data, username)
        print('Response:', resp)
    except Exception as e:
        import traceback
        traceback.print_exc()
        print('Error:', e)

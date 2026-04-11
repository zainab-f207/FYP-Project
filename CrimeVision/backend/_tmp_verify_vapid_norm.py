import os
from app.alert_notifications import AlertNotificationSystem
from app.routes.alerts import ALERT_EMAIL_CONFIG
raw = os.getenv('VAPID_PRIVATE_KEY')
s = AlertNotificationSystem(ALERT_EMAIL_CONFIG, os.getenv('VAPID_PUBLIC_KEY'), raw)
print('RAW_LEN', len(raw) if raw else None)
print('NORM_IS_PEM', bool(s.vapid_private_key and 'BEGIN PRIVATE KEY' in s.vapid_private_key))
print('NORM_HEAD', (s.vapid_private_key or '')[:30])

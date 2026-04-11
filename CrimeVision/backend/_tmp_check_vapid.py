import os, base64
from app.core.config import load_dotenv
pub = os.getenv('VAPID_PUBLIC_KEY')
priv = os.getenv('VAPID_PRIVATE_KEY')
print('PUB_LEN', len(pub) if pub else None, 'PUB_HEAD', (pub or '')[:20])
print('PRIV_LEN', len(priv) if priv else None, 'PRIV_HEAD', (priv or '')[:30])
if priv:
    try:
        pad = '=' * ((4 - len(priv) % 4) % 4)
        dec = base64.urlsafe_b64decode((priv+pad).encode())
        print('B64_DECODE_OK', True, 'DECODE_HEAD', dec[:30])
    except Exception as e:
        print('B64_DECODE_OK', False, e)

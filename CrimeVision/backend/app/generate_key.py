from pywebpush import Vapid

vapid = Vapid()
vapid.generate_keys()
print("VAPID_PUBLIC_KEY =", vapid.public_pem().decode())
print("VAPID_PRIVATE_KEY =", vapid.private_pem().decode())

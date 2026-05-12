#!/usr/bin/env python3
"""
Grant `manage_fir_ocr` permission to existing admin accounts.

This script is idempotent — it will add the permission where missing
in both `users_info.permissions` and `admins.permissions` JSON columns.

Usage:
  python grant_manage_fir_ocr.py

Run from the repository root (where your virtualenv / PYTHONPATH can import
`app.core.database.get_db_connection`).
"""
import json
import sys
from app.core.database import get_db_connection

PERM = "manage_fir_ocr"


def add_perm_to_row(cursor, table, row_id, raw_perms):
    if isinstance(raw_perms, list):
        perms = raw_perms
    elif isinstance(raw_perms, str):
        try:
            perms = json.loads(raw_perms) if raw_perms.strip() else []
        except Exception:
            perms = []
    else:
        perms = []

    if PERM in perms:
        return False
    perms.append(PERM)
    cursor.execute(f"UPDATE {table} SET permissions = %s WHERE id = %s", (json.dumps(perms), row_id))
    return True


def main():
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Update users_info admin rows
        cursor.execute("SELECT id, permissions FROM users_info WHERE role = 'admin'")
        rows = cursor.fetchall() or []
        updated_users = 0
        for r in rows:
            if add_perm_to_row(cursor, "users_info", r["id"], r.get("permissions")):
                updated_users += 1

        # Update admins table
        cursor.execute("SELECT id, permissions FROM admins")
        rows = cursor.fetchall() or []
        updated_admins = 0
        for r in rows:
            if add_perm_to_row(cursor, "admins", r["id"], r.get("permissions")):
                updated_admins += 1

        conn.commit()
        print(f"Updated users_info: {updated_users}; admins: {updated_admins}")
    except Exception as e:
        if conn:
            conn.rollback()
        print("Error:", e)
        sys.exit(2)
    finally:
        if conn:
            cursor.close()
            conn.close()


if __name__ == "__main__":
    main()

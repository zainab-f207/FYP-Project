"""
Copy data from local MySQL to TiDB Cloud (or wherever .env points).

What it does:
    1. Connects to BOTH local MySQL (interactive password) and TiDB (.env).
    2. For each table in COPY_TABLES, reads all rows from local and inserts
       into TiDB using INSERT ... ON DUPLICATE KEY UPDATE so you can re-run
       safely.
    3. Disables FK checks on TiDB during the load so table order doesn't
       matter.

Usage:
    cd CrimeVision/backend
    python copy_data_to_tidb.py            # copies the default table list
    python copy_data_to_tidb.py --all      # copies every table local has
    python copy_data_to_tidb.py users_info crimes  # copy specific tables only

Notes:
    - Source columns that don't exist in the target table are skipped
      (with a warning) so schema drift between local and TiDB doesn't crash
      the copy.
    - Rows are inserted in batches of 500.
    - Read-only on the source (local MySQL). Idempotent on the target.
"""
from __future__ import annotations

import getpass
import os
import sys
from typing import Any

import mysql.connector
from dotenv import load_dotenv

load_dotenv()

# Default set: enough to get login + map working. Add more by running
# with --all or naming tables on the command line.
COPY_TABLES = [
    "users_info",
    "admins",
    "areas",
    "area_coordinates",
    "law_sections",
    "crimes",
    "alert_subscriptions",
    "user_alert_preferences",
    "browser_push_subscriptions",
]

LOCAL_HOST = "localhost"
LOCAL_PORT = 3306
LOCAL_USER = "root"
LOCAL_DATABASE = "crimevision_db"

BATCH_SIZE = 500


def get_tidb_connection() -> Any:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from app.core.config import get_db_config

    return mysql.connector.connect(**get_db_config())


def get_local_connection(password: str) -> Any:
    return mysql.connector.connect(
        host=LOCAL_HOST,
        port=LOCAL_PORT,
        user=LOCAL_USER,
        password=password,
        database=LOCAL_DATABASE,
    )


def get_table_columns(cursor, table: str) -> list[str]:
    cursor.execute(f"DESCRIBE `{table}`")
    rows = cursor.fetchall()
    # Cursor may be dict-mode (from local) or tuple-mode (from TiDB) — handle both.
    return [row["Field"] if isinstance(row, dict) else row[0] for row in rows]


def copy_table(local_conn, tidb_conn, table: str) -> tuple[int, int]:
    src_cur = local_conn.cursor(dictionary=True)
    dst_cur = tidb_conn.cursor()

    try:
        src_cols = get_table_columns(src_cur, table)
    except mysql.connector.Error as e:
        print(f"  SKIP — local has no table `{table}`: {e.msg}")
        src_cur.close()
        dst_cur.close()
        return (0, 0)

    try:
        dst_cols = set(get_table_columns(dst_cur, table))
    except mysql.connector.Error as e:
        print(f"  SKIP — TiDB has no table `{table}`: {e.msg}")
        src_cur.close()
        dst_cur.close()
        return (0, 0)

    common_cols = [c for c in src_cols if c in dst_cols]
    skipped_cols = [c for c in src_cols if c not in dst_cols]
    if skipped_cols:
        print(f"  WARN — columns not in TiDB target, will skip: {skipped_cols}")

    if not common_cols:
        print(f"  SKIP — no common columns between local and TiDB for `{table}`")
        src_cur.close()
        dst_cur.close()
        return (0, 0)

    src_cur.execute(f"SELECT COUNT(*) AS cnt FROM `{table}`")
    total = src_cur.fetchone()["cnt"]
    print(f"  rows in local: {total:,}")

    if total == 0:
        src_cur.close()
        dst_cur.close()
        return (0, 0)

    src_cur.execute(f"SELECT {', '.join(f'`{c}`' for c in common_cols)} FROM `{table}`")

    cols_sql = ", ".join(f"`{c}`" for c in common_cols)
    placeholders = ", ".join(["%s"] * len(common_cols))
    update_sql = ", ".join(f"`{c}`=VALUES(`{c}`)" for c in common_cols)
    insert_sql = (
        f"INSERT INTO `{table}` ({cols_sql}) VALUES ({placeholders}) "
        f"ON DUPLICATE KEY UPDATE {update_sql}"
    )

    inserted = 0
    failed = 0
    batch: list[tuple[Any, ...]] = []

    for row in src_cur:
        batch.append(tuple(row[c] for c in common_cols))
        if len(batch) >= BATCH_SIZE:
            try:
                dst_cur.executemany(insert_sql, batch)
                tidb_conn.commit()
                inserted += len(batch)
            except mysql.connector.Error as e:
                tidb_conn.rollback()
                failed += len(batch)
                print(f"  ERR batch failed: {e.errno}: {e.msg}")
            batch = []

    if batch:
        try:
            dst_cur.executemany(insert_sql, batch)
            tidb_conn.commit()
            inserted += len(batch)
        except mysql.connector.Error as e:
            tidb_conn.rollback()
            failed += len(batch)
            print(f"  ERR final batch failed: {e.errno}: {e.msg}")

    src_cur.close()
    dst_cur.close()
    return (inserted, failed)


def main() -> None:
    args = sys.argv[1:]
    if "--all" in args:
        tables_to_copy = None  # special: discover at runtime
    elif args:
        tables_to_copy = args
    else:
        tables_to_copy = COPY_TABLES

    # Password sources, in priority order:
    # 1. LOCAL_DB_PASSWORD env var  (recommended on Windows)
    # 2. getpass prompt              (hidden input, unreliable on PowerShell)
    # 3. plain input fallback        (visible — fine on your own machine)
    password = os.getenv("LOCAL_DB_PASSWORD", "")
    if not password:
        try:
            password = getpass.getpass("Local MySQL password: ")
        except Exception:
            password = ""
    if not password:
        print("(getpass returned empty — falling back to visible input)")
        password = input("Local MySQL password (visible): ").strip()
    if not password:
        print("ERROR: no password provided.")
        sys.exit(1)

    print(f"\nConnecting to local MySQL ({LOCAL_HOST}:{LOCAL_PORT})...")
    try:
        local = get_local_connection(password)
    except mysql.connector.Error as e:
        print(f"ERROR: {e}")
        sys.exit(1)

    print(f"Connecting to TiDB...")
    try:
        tidb = get_tidb_connection()
    except mysql.connector.Error as e:
        print(f"ERROR: {e}")
        local.close()
        sys.exit(1)

    if tables_to_copy is None:
        cur = local.cursor()
        cur.execute("SHOW TABLES")
        tables_to_copy = [row[0] for row in cur.fetchall()]
        cur.close()
        print(f"\n--all flag: copying all {len(tables_to_copy)} tables")

    # Disable FK checks on TiDB so order doesn't matter
    tidb_cur = tidb.cursor()
    tidb_cur.execute("SET FOREIGN_KEY_CHECKS = 0")
    tidb_cur.close()

    total_inserted = 0
    total_failed = 0

    for table in tables_to_copy:
        print(f"\n=== {table} ===")
        inserted, failed = copy_table(local, tidb, table)
        total_inserted += inserted
        total_failed += failed
        print(f"  inserted: {inserted:,}, failed: {failed:,}")

    tidb_cur = tidb.cursor()
    tidb_cur.execute("SET FOREIGN_KEY_CHECKS = 1")
    tidb_cur.close()

    local.close()
    tidb.close()

    print(f"\n{'=' * 70}")
    print(f"Done: {total_inserted:,} rows inserted, {total_failed:,} failed.")
    print(f"{'=' * 70}")
    print("\nNext: try logging in again — your old accounts should now work.")


if __name__ == "__main__":
    main()

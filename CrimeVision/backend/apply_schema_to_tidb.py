"""
Apply schema.sql to whichever DB the current .env points at (TiDB by default).

Why this exists:
    Pasting a large schema.sql into the TiDB Cloud SQL editor often fails
    silently — the editor truncates or partial-imports. This script
    connects directly via mysql.connector, runs each statement, and
    reports every success/failure so nothing is hidden.

Usage:
    cd CrimeVision/backend
    python apply_schema_to_tidb.py            # uses schema.sql in cwd
    python apply_schema_to_tidb.py mysql.sql  # custom file

Safety:
    schema.sql contains `DROP TABLE IF EXISTS` before each CREATE, so
    running this on a non-empty TiDB will WIPE existing tables and data.
    For a first import to a fresh TiDB cluster this is exactly what you
    want. Don't run on a DB with real production data.
"""
from __future__ import annotations

import os
import re
import sys

import mysql.connector
from dotenv import load_dotenv

load_dotenv()

SCHEMA_FILE = sys.argv[1] if len(sys.argv) > 1 else "schema.sql"


def split_statements(sql: str) -> list[str]:
    """Strip SQL comments and split into individual statements."""
    # Strip line-comments
    sql = re.sub(r"--[^\n]*\n", "\n", sql)
    # Strip /* */ block comments
    sql = re.sub(r"/\*.*?\*/", "", sql, flags=re.DOTALL)

    statements: list[str] = []
    current: list[str] = []
    in_delimiter_block = False

    for line in sql.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        # Skip DELIMITER directives — TiDB handles ; just fine for triggers,
        # and our trigger blocks are rare enough to ignore for now.
        if stripped.upper().startswith("DELIMITER"):
            in_delimiter_block = not in_delimiter_block
            continue
        if in_delimiter_block:
            continue
        current.append(line)
        if stripped.endswith(";"):
            joined = "\n".join(current).strip().rstrip(";").strip()
            if joined:
                statements.append(joined)
            current = []
    # Trailing statement without semicolon
    if current:
        joined = "\n".join(current).strip().rstrip(";").strip()
        if joined:
            statements.append(joined)
    return statements


def main() -> None:
    if not os.path.exists(SCHEMA_FILE):
        print(f"ERROR: {SCHEMA_FILE} not found. Run export_local_schema.py first.")
        sys.exit(1)

    print(f"Reading {SCHEMA_FILE}...")
    with open(SCHEMA_FILE, "r", encoding="utf-8") as f:
        sql = f.read()
    print(f"  {len(sql):,} bytes")

    statements = split_statements(sql)
    print(f"  parsed {len(statements)} statements")

    # Add app/ to path so we can import from app.core.config
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from app.core.config import get_db_config

    config = dict(get_db_config())
    # Ensure we connect to the default DB before USE statements
    db_name = config.get("database", "crimevision_db")
    print(f"\nConnecting to {config['host']}:{config['port']} as {config['user']} (DB={db_name})...")

    # Connect WITHOUT specifying database first, in case it doesn't exist yet
    config_no_db = {k: v for k, v in config.items() if k != "database"}
    conn = mysql.connector.connect(**config_no_db)
    cursor = conn.cursor()

    # Make sure the database exists, then USE it
    cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{db_name}`")
    cursor.execute(f"USE `{db_name}`")
    print(f"  using database: {db_name}\n")

    success = 0
    failed = 0
    failures: list[tuple[int, str, str]] = []

    for i, statement in enumerate(statements, 1):
        preview = " ".join(statement.split())[:90]
        try:
            cursor.execute(statement)
            conn.commit()
            print(f"  [{i:>3}/{len(statements)}] OK  {preview}")
            success += 1
        except mysql.connector.Error as e:
            print(f"  [{i:>3}/{len(statements)}] ERR {preview}")
            print(f"          -> {e.errno}: {e.msg}")
            failures.append((i, preview, f"{e.errno}: {e.msg}"))
            failed += 1
            try:
                conn.rollback()
            except Exception:
                pass

    cursor.close()
    conn.close()

    print(f"\n{'=' * 70}")
    print(f"Done: {success} succeeded, {failed} failed.")
    if failures:
        print(f"\nFailed statements (first 10):")
        for i, preview, err in failures[:10]:
            print(f"  [{i}] {preview}")
            print(f"       {err}")
    print(f"{'=' * 70}\n")

    print("Next: restart your backend.")
    print("  uvicorn app.main_enhanced_final_fixed:app --reload")


if __name__ == "__main__":
    main()

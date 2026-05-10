"""
validation.py — small, defensive input-cleaning helpers used by the API.

The goal of this module is to keep "garbage in" from turning into
"garbage out" anywhere in the system. Every function here is short,
synchronous, and either:
    a) returns a clean / safe version of the input, or
    b) raises an HTTPException(400) so FastAPI immediately returns a
       proper 400 Bad Request to the client.

These helpers are deliberately simple. They are meant to run on
practically every request, so they avoid heavy regex, network calls,
or anything that could become a performance bottleneck.
"""
from __future__ import annotations

import re
from datetime import datetime

from fastapi import HTTPException

from ..core.config import get_logger
from ..core.database import get_db_connection

logger = get_logger("utils.validation")


def validate_date_format(date_str: str) -> bool:
    """Return True only if `date_str` is a strictly-formatted YYYY-MM-DD
    date AND the year is plausible for our domain.

    Why we are this strict:
        - The frontend sends ISO-style dates ("2025-04-12") and our SQL
          queries assume that exact shape — anything else would either
          confuse MySQL or open us up to subtle injection-shaped bugs.
        - We additionally reject pre-1900 dates (clearly garbage for a
          crime database) and dates more than one year in the future
          (which usually indicate a typo on the user's side, e.g. 2125).

    The function returns a boolean rather than raising, because callers
    sometimes want to silently fall back to a default range instead of
    exploding with a 400 error.
    """
    if not date_str or len(date_str) != 10:
        return False
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", date_str):
        return False
    try:
        parsed_date = datetime.strptime(date_str, "%Y-%m-%d")
        current_year = datetime.now().year
        return 1900 <= parsed_date.year <= current_year + 1
    except ValueError:
        # `strptime` catches invalid days/months (e.g. 2025-02-30).
        return False


def validate_crime_type(crime_type: str) -> str:
    """Sanitise a free-form crime type string and cap its length.

    The regex `[^\w\s\-_]` strips out everything that isn't a word
    character, whitespace, hyphen, or underscore — basically removing
    punctuation, quotes, slashes, semicolons, etc. that could be used
    in injection-style attacks or that would otherwise look weird in
    the UI as a chip / filter label.

    If the user typed only forbidden characters (so the result is an
    empty string), we 400 out so they don't end up filtering by an
    invisible blank string. We also truncate to 50 characters because
    nothing in our taxonomy needs to be longer than that.
    """
    sanitized = re.sub(r"[^\w\s\-_]", "", crime_type.strip())
    if not sanitized:
        raise HTTPException(status_code=400, detail="Invalid crime type format")
    return sanitized[:50]


def validate_name(name: str) -> str:
    """Same idea as `validate_crime_type`, but for a person/area name.

    Kept as a separate function (instead of one generic helper) so that
    if the rules ever diverge — e.g. crime types should accept '&' but
    names should not — only one of them needs to change.
    """
    sanitized = re.sub(r"[^\w\s\-_]", "", name.strip())
    if not sanitized:
        raise HTTPException(status_code=400, detail="Invalid name format")
    return sanitized[:50]


def generate_username(first_name: str, last_name: str) -> str:
    """Build a unique-in-the-database username from a person's name.

    Strategy in plain words:
        1) Start with `firstname.lastname` lowercased (e.g. "john.doe").
        2) If either part is missing we fall back to whichever exists;
           if both are empty the result is an empty string and the loop
           below will immediately try "1", "2", ... which is harmless.
        3) Repeatedly query the `users_info` table for a row with that
           username. If we find one, we append a counter and try again
           ("john.doe1", "john.doe2", ...). Keep going until we find a
           free slot.

    This is O(N) in the worst case (N = number of duplicate names),
    but in practice the loop terminates after one or two iterations
    because real users rarely share both names.

    NOTE: This function performs its own DB connection lifecycle
    (open → cursor → close) so callers don't have to manage it; that
    keeps the call sites clean at the cost of one extra round-trip.
    """
    base_username = f"{first_name.lower()}.{last_name.lower()}".strip(".")
    username = base_username or (first_name.lower() or last_name.lower())

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        counter = 1
        while True:
            cursor.execute("SELECT id FROM users_info WHERE username = %s", (username,))
            if not cursor.fetchone():
                break
            username = f"{base_username}{counter}"
            counter += 1
    except Exception as exc:  # pragma: no cover - depends on DB
        # Even if the uniqueness check fails (e.g. DB outage) we still
        # return SOMETHING sensible rather than crashing the signup
        # flow — the caller will catch any subsequent insert errors.
        logger.error("Database error checking username", exc_info=exc)
    finally:
        cursor.close()
        conn.close()
    return username


"""Repair low-quality area_translit values in crimes using improved transliteration logic.

Usage examples:
  python fix_translit_quality.py --area "Gulberg, Lahore" --apply
  python fix_translit_quality.py --apply
"""

import argparse
import re
import time
from typing import Dict, List, Tuple

from app.core.database import get_db_connection
from import_fir_data import _mymemory_single, azure_transliterate_batch

URDU_RE = re.compile(r"[\u0600-\u06FF\u0750-\u077F\uFB50-\uFDFF\uFE70-\uFEFF]+")
TOKEN_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9\-]*")
GENERIC_TOKENS = {
    "road", "block", "sub", "sub-block", "subblock", "interchange", "market", "gate",
    "chowk", "bazaar", "street", "avenue", "boulevard", "town", "city", "housing",
    "society", "point", "underpass",
}

STRONG_ANCHORS = {
    "abdul haq", "liaquat ali khan", "defence", "revenue", "chunian", "badian",
    "gajumatta", "sagian", "sheikh zayed", "shahpur kanjran", "niazi", "mall road",
    "main boulevard", "walton", "thokar niaz baig", "jinnah avenue", "mm alam",
    "gt road", "raiwind", "burki", "kutchery", "iqbal avenue", "tanki wala",
    "roti tandoor", "khayaban-e-jinnah", "kamahan interchange", "al hamd", "canal bank",
}

NORMALIZE_REPLACEMENTS = {
    "New Z": "Niazi",
    "Sagyan": "Sagian",
    "Pia Society": "PIA Society",
    "Ninth Kot": "Nawan Kot",
    "Edinbad": "Eden Abad",
    "Gt Road": "GT Road",
    "Raywind": "Raiwind",
    "Tinki": "Tanki",
    "Kuchhari": "Kutchery",
    "Khaya Bin Jinnah": "Khayaban-e-Jinnah",
    "Khayab In Jinnah": "Khayaban-e-Jinnah",
}


def _norm(value: str) -> str:
    return re.sub(r"\s+", " ", (value or "").strip())


def _normalize_translit_text(value: str) -> str:
    text = _norm(value)
    for old, new in NORMALIZE_REPLACEMENTS.items():
        text = text.replace(old, new)
    return _norm(text)


def _named_token_count(value: str) -> int:
    tokens = [
        t.lower() for t in TOKEN_RE.findall(_norm(value))
        if len(t) > 1 and not t.isdigit()
    ]
    return sum(1 for t in tokens if t not in GENERIC_TOKENS)


def _is_low_quality(value: str) -> bool:
    v = _norm(value)
    if not v:
        return True
    if URDU_RE.search(v):
        return True
    tokens = [t.lower() for t in TOKEN_RE.findall(v)]
    if not tokens:
        return True
    if all(t in GENERIC_TOKENS for t in tokens):
        return True
    if _named_token_count(v) == 0:
        return True
    return False


def _should_replace(old_val: str, new_val: str) -> bool:
    old_v = _norm(old_val)
    new_v = _norm(new_val)
    if not new_v:
        return False
    if old_v.lower() == new_v.lower():
        return False

    # Conservative by design: only repair rows that are clearly low quality.
    if not _is_low_quality(old_v):
        return False

    if _named_token_count(new_v) == 0:
        return False

    lowered_new = new_v.lower()
    return any(anchor in lowered_new for anchor in STRONG_ANCHORS)


def _pick_better_translit(urdu: str, keyword_translit: str) -> str:
    """Try API translation for better accuracy on repaired rows."""
    candidate = _normalize_translit_text(keyword_translit)
    try:
        api_translit = _normalize_translit_text(_mymemory_single(urdu) or "")
    except Exception:
        api_translit = ""

    if not api_translit:
        return candidate

    if _named_token_count(api_translit) >= _named_token_count(candidate):
        return api_translit
    return candidate


def _fetch_distinct_areas(area_filter: str | None) -> List[Tuple[str, str, int]]:
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    try:
        if area_filter:
            cur.execute(
                """
                SELECT area_urdu, area_translit, COUNT(*) AS cnt
                FROM crimes
                WHERE area = %s
                  AND area_urdu IS NOT NULL
                  AND TRIM(area_urdu) != ''
                GROUP BY area_urdu, area_translit
                ORDER BY cnt DESC
                """,
                (area_filter,),
            )
        else:
            cur.execute(
                """
                SELECT area_urdu, area_translit, COUNT(*) AS cnt
                FROM crimes
                WHERE area_urdu IS NOT NULL
                  AND TRIM(area_urdu) != ''
                GROUP BY area_urdu, area_translit
                ORDER BY cnt DESC
                """
            )
        rows = cur.fetchall()
        return [(r["area_urdu"], r["area_translit"] or "", int(r["cnt"])) for r in rows]
    finally:
        cur.close()
        conn.close()


def _update_rows(updates: Dict[str, str], area_filter: str | None, apply: bool) -> int:
    if not updates:
        return 0

    conn = get_db_connection()
    cur = conn.cursor()
    changed_rows = 0
    try:
        for area_urdu, new_translit in updates.items():
            if area_filter:
                cur.execute(
                    """
                    UPDATE crimes
                    SET area_translit = %s
                    WHERE area_urdu = %s AND area = %s
                    """,
                    (new_translit, area_urdu, area_filter),
                )
            else:
                cur.execute(
                    """
                    UPDATE crimes
                    SET area_translit = %s
                    WHERE area_urdu = %s
                    """,
                    (new_translit, area_urdu),
                )
            changed_rows += int(cur.rowcount)

        if apply:
            conn.commit()
        else:
            conn.rollback()
        return changed_rows
    finally:
        cur.close()
        conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Fix low-quality transliteration in crimes.area_translit")
    parser.add_argument("--area", default=None, help="Optional area filter, e.g. 'Gulberg, Lahore'")
    parser.add_argument("--apply", action="store_true", help="Apply updates (default is dry-run)")
    parser.add_argument("--preview", type=int, default=20, help="Preview first N proposed replacements")
    args = parser.parse_args()

    rows = _fetch_distinct_areas(args.area)
    if not rows:
        print("No matching rows found.")
        return

    unique_urdu = sorted({u for u, _, _ in rows})
    generated = azure_transliterate_batch(unique_urdu)

    current_best: Dict[str, str] = {}
    for urdu, translit, _ in rows:
        best = current_best.get(urdu, "")
        if len(_norm(translit)) > len(_norm(best)):
            current_best[urdu] = translit

    updates: Dict[str, str] = {}
    preview: List[Tuple[str, str, str]] = []

    for urdu in unique_urdu:
        old_val = current_best.get(urdu, "")
        new_val = _norm(generated.get(urdu, ""))
        if _should_replace(old_val, new_val):
            new_val = _pick_better_translit(urdu, new_val)
            updates[urdu] = new_val
            if len(preview) < args.preview:
                preview.append((urdu, old_val, new_val))
            time.sleep(0.35)

    scope = f"area='{args.area}'" if args.area else "all areas"
    print(f"Scanned {len(unique_urdu)} unique Urdu subareas in {scope}")
    print(f"Proposed updates: {len(updates)}")
    print("\nPreview:")
    for urdu, old_val, new_val in preview:
        print(f"- {urdu}")
        print(f"  old: {old_val}")
        print(f"  new: {new_val}")

    changed_rows = _update_rows(updates, args.area, args.apply)
    mode = "APPLIED" if args.apply else "DRY-RUN"
    print(f"\n{mode}: rows affected = {changed_rows}")


if __name__ == "__main__":
    main()

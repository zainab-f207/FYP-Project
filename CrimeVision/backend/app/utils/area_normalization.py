"""
area_normalization.py — make "the same neighbourhood" actually look the same.

Why this file is necessary:
    Crime data in CrimeVision comes from many sources — manually-typed
    user reports, OCR'd FIR PDFs, bulk imports of historical CSVs.
    Each source spells areas differently:
        "Gulberg"           "Gulberg, Lahore"           "GULBERG (Lahore)"
        "Chuburji"          "Chauburji"                 "Chuburji, Lahore, Pakistan"
        "DHA Phase 5"       "DHA Ph 5"                  "DHA Sec FF Ph 5"
    If we treated every one of those as a different neighbourhood, the
    Area Profile, Heatmap and Risk Prediction tools would split a
    single area's data across many rows and report wildly low numbers.

This module solves that problem with three layers of normalisation:

    1) STRIP GENERIC SUFFIXES — "Lahore", "Punjab", "Pakistan" and their
       common short forms. Almost every record in our DB has them and
       they add no information.

    2) PHONETIC MATCHING (SOUNDEX) — applied at SQL time by
       `area_match_clause`. This catches arbitrary typos like
       "Chuburji" vs "Chauburji" without anyone having to maintain a
       hand-curated list.

    3) MANUAL ALIAS OVERRIDES — for the small number of cases SOUNDEX
       cannot handle (same place known by very different names, e.g.
       "Liberty" vs "Liberty Market"). The dict is intentionally empty
       today; add entries only when you confirm the automatic layers
       miss a real-world variant.

Public surface used by the rest of the codebase:
    canonicalize_area_query  → for QUERY input  (matching keys)
    canonical_area_name      → for STORAGE/UI   (display names)
    area_aliases             → all known spellings of one area
    area_like_pattern        → quick "%area%" pattern (legacy callers)
    area_match_clause        → full SQL fragment + parameters tuple
    normalize_area_name      → DHA-phase aware bucketing for analytics
"""

import re
from typing import Iterable, List, Optional, Tuple


# ── Optional manual overrides (rarely needed) ───────────────────────────────
# The system handles spelling variants AUTOMATICALLY for any area via SOUNDEX
# at query time and aggressive suffix stripping at canonicalization time.
# This dict is only for the rare cases SOUNDEX cannot catch:
#   * Same place with very different names (e.g. "Liberty" vs "Liberty Market")
#   * Phonetic codes that diverge despite being the same place
#
# 99% of typos and ", Lahore"-style suffixes are handled WITHOUT touching this.
_MANUAL_AREA_ALIASES: dict[str, List[str]] = {
    # Format: "canonical_key": ["variant1", "variant2", ...]
    # (canonical_key itself doesn't need to appear in the list)
}


# Optional curated display form per canonical key. Lets us force a nicer
# title-case in the UI (e.g. "DHA Phase 5" instead of "Dha Phase 5") for
# specific areas. Empty by default — fall back to .title() when absent.
_CANONICAL_DISPLAY: dict[str, str] = {}


# Suffixes (case-insensitive) that should be stripped when normalizing an
# area name. The list is deliberately small and city/country-scoped so we
# never accidentally chop off a real neighbourhood name that ends with
# one of these words.
_GENERIC_SUFFIXES = (
    "lahore", "lhr", "punjab", "pakistan", "pak", "pk",
)


def _strip_parens(text: str) -> str:
    """Drop a trailing parenthesised qualifier: "Chuburji (Lahore)" -> "Chuburji"."""
    return re.sub(r"\s*\([^)]*\)\s*$", "", text).strip()


def _strip_generic_suffixes(text: str) -> str:
    """Drop trailing ", Lahore" / ", Pakistan" / ", Punjab" style suffixes
    (case-insensitive). Repeats so "X, Lahore, Pakistan" → "X"."""
    if not text:
        return text
    cur = text.strip()
    while True:
        nxt = cur
        for suf in _GENERIC_SUFFIXES:
            # Match a comma-suffix or whitespace-suffix at end of string
            nxt = re.sub(rf",\s*{re.escape(suf)}\s*$", "", nxt, flags=re.IGNORECASE).strip()
            nxt = re.sub(rf"\s+{re.escape(suf)}\s*$", "", nxt, flags=re.IGNORECASE).strip()
        if nxt == cur:
            return cur
        cur = nxt


def _norm_segment(text: str) -> str:
    """Lowercase, strip, collapse whitespace, drop common suffixes.

    Handles: Urdu commas, parens, ", Lahore" / ", Pakistan" / etc., extra
    whitespace. Intended to give a stable join key for matching.

    Examples:
        "Chuburji, Lahore"      -> "chuburji"
        "Chuburji (Lahore)"     -> "chuburji"
        "  GULBERG ,  Lahore "  -> "gulberg"
        "Liberty Market, Gulberg, Lahore" -> "liberty market"  (first segment kept)
    """
    if not text:
        return ""
    cleaned = str(text).strip().replace("،", ",")
    cleaned = re.sub(r"\s+", " ", cleaned)
    cleaned = _strip_parens(cleaned)
    cleaned = _strip_generic_suffixes(cleaned)
    # Take first comma-segment AFTER suffix stripping — so "Liberty Market, Lahore"
    # becomes "liberty market" rather than "liberty market" being split further.
    first_segment = cleaned.split(",", 1)[0].strip()
    # Strip a second time in case the first segment itself had a suffix
    first_segment = _strip_generic_suffixes(first_segment)
    return first_segment.casefold()


# Reverse index for the optional manual overrides
_VARIANT_TO_CANONICAL: dict[str, str] = {}
for _canonical, _variants in _MANUAL_AREA_ALIASES.items():
    _VARIANT_TO_CANONICAL[_canonical] = _canonical
    for _v in _variants:
        _VARIANT_TO_CANONICAL[_norm_segment(_v)] = _canonical


def canonicalize_area_query(area: Optional[str]) -> str:
    """Return a normalized area token for matching.

    Strips ", Lahore"/", Pakistan"/parens/whitespace and lowercases. Optionally
    resolves a manual alias if one is configured. Spelling variants like
    "Chuburji" vs "Chauburji" are NOT collapsed here — that's handled at SQL
    query time via :func:`area_match_clause` using SOUNDEX (works for any
    area without needing a hardcoded list).

    Examples:
        "Gulberg, Lahore"       -> "gulberg"
        "Chuburji (Lahore)"     -> "chuburji"
        "Chauburji, Lahore"     -> "chauburji"
        "DHA Phase 5"           -> "dha phase 5"
    """
    key = _norm_segment(area or "")
    if not key:
        return ""
    if key in _VARIANT_TO_CANONICAL:
        return _VARIANT_TO_CANONICAL[key]
    # Substring override — only fires for manually-configured aliases
    for variant_key, canonical in _VARIANT_TO_CANONICAL.items():
        if len(variant_key) >= 4 and variant_key in key:
            return canonical
    return key


def canonical_area_name(area: Optional[str]) -> str:
    """Return the canonical display-form area name for STORAGE/UI.

    Used on the crimes-INSERT path so future rows are stored without
    ", Lahore"-style suffixes. Preserves user-entered casing where possible.

    Examples:
        "Chuburji, Lahore"   -> "Chuburji"
        "Chuburji (Lahore)"  -> "Chuburji"
        "Gulberg, Lahore"    -> "Gulberg"
        "DHA Phase 5"        -> "DHA Phase 5"
    """
    if not area:
        return ""
    canonical_key = canonicalize_area_query(area)
    if not canonical_key:
        return str(area).strip()

    if canonical_key in _CANONICAL_DISPLAY:
        return _CANONICAL_DISPLAY[canonical_key]

    # Try to preserve the user's original casing for the relevant segment
    raw = str(area).strip().replace("،", ",")
    raw = _strip_parens(raw)
    raw = _strip_generic_suffixes(raw)
    raw_first = raw.split(",", 1)[0].strip()
    raw_first = _strip_generic_suffixes(raw_first)

    if raw_first.casefold() == canonical_key:
        return raw_first

    return canonical_key.title()


def area_aliases(area: Optional[str]) -> List[str]:
    """All manually-configured spellings for an area (canonical first).

    Returns just ``[canonical]`` if no override exists — auto-typo tolerance
    is handled separately via SOUNDEX in :func:`area_match_clause`.
    """
    canonical = canonicalize_area_query(area)
    if not canonical:
        return []
    if canonical in _MANUAL_AREA_ALIASES:
        return [canonical, *_MANUAL_AREA_ALIASES[canonical]]
    return [canonical]


def area_like_pattern(area: Optional[str]) -> str:
    """LIKE pattern for the canonical form of an area (single value).

    Kept for backwards compatibility with existing callers. New code should
    prefer :func:`area_match_clause` which also handles spelling variants
    automatically via SOUNDEX.
    """
    key = canonicalize_area_query(area)
    return f"%{key}%" if key else "%"


def area_match_clause(
    area: Optional[str],
    columns: Iterable[str] = ("area", "area_translit"),
    *,
    fuzzy: bool = True,
) -> Tuple[str, List[str]]:
    """Build a SQL fragment that matches an area across all spelling variants.

    Strategy (all OR'd together):
      1. **Literal LIKE** on each given column for each manually-configured
         alias (handles cases like "Liberty" ↔ "Liberty Market").
      2. **SOUNDEX match** on the comma-stripped first segment of each column
         (handles arbitrary typos: "Chuburji" ↔ "Chauburji",
          "Mughalpura" ↔ "Mughalpora", etc. — no manual config needed).

    The SOUNDEX comparison strips the ", Lahore" suffix from the stored value
    on-the-fly, so rows like ``area = 'Chuburji, Lahore'`` match queries for
    ``Chauburji`` without requiring the legacy data to be migrated first.

    Returns ``(clause, params)`` to drop into ``cursor.execute``::

        clause, params = area_match_clause("Chauburji")
        cursor.execute(
            f"SELECT * FROM crimes WHERE {clause} AND crime_date >= %s",
            (*params, last_week),
        )

    Pass ``fuzzy=False`` to disable SOUNDEX (rare — useful only when you
    need to match exactly the typed name, not phonetic neighbors).
    """
    aliases = area_aliases(area)
    cols = list(columns)
    if not aliases or not cols:
        return ("1=0", [])

    parts: List[str] = []
    params: List[str] = []

    # Literal substring match per column per alias
    for col in cols:
        for alias in aliases:
            parts.append(f"LOWER({col}) LIKE %s")
            params.append(f"%{alias}%")

    # Phonetic match per column — strip ", Lahore"-style suffix before SOUNDEX
    if fuzzy:
        canonical = aliases[0]
        for col in cols:
            parts.append(
                f"SOUNDEX(TRIM(SUBSTRING_INDEX({col}, ',', 1))) = SOUNDEX(%s)"
            )
            params.append(canonical)

    return ("(" + " OR ".join(parts) + ")", params)


def normalize_area_name(area_name: str) -> str:
    """Roll up tiny DHA sub-sectors into their parent "DHA Phase N" bucket.

    DHA is a huge planned colony that is split into Phases (1..9) and
    each Phase is further split into Blocks and Sectors. Crime data we
    receive uses inconsistent granularity:

        "DHA Phase 5"               <- already what we want
        "DHA Phase 5 Block H"       <- too granular
        "DHA Sec FF Ph 4"           <- abbreviation hell
        "Phase 4 Block F..."        <- missing the "DHA" prefix entirely
        "DHA Ph: 6"                 <- punctuation noise

    For dashboard analytics we want all of those to roll up to a single
    bucket (e.g. "DHA Phase 5") so the sample size is large enough to
    compute meaningful safety scores. This function does that rollup.

    Special cases handled:
        - "Bahria Town" is NOT inside DHA, even though it looks similar
          superficially — it gets short-circuited and returned as-is.
        - Roman-numeral phases ("Phase IV") are preserved upper-cased.
        - "Unknown" / empty inputs pass through untouched.

    Anything that doesn't match one of the DHA patterns is returned
    unchanged, so non-DHA areas keep their original spelling.
    """
    if not area_name or area_name == "Unknown":
        return area_name

    _an_lower = area_name.lower().strip()

    # Bahria is a separate developer/colony — never absorb it into DHA.
    if "bahria" in _an_lower:
        return area_name

    # Detect any of the common ways people write "Phase": the full word,
    # " ph " as a token, trailing " ph", or punctuated forms " ph:" / " ph.".
    if "phase" in _an_lower or " ph " in _an_lower or _an_lower.endswith(" ph") or " ph:" in _an_lower or " ph." in _an_lower:
        _phase_trigger = "phase" if "phase" in _an_lower else "ph"
        _parts = _an_lower.split(_phase_trigger)
        if len(_parts) > 1:
            # Take everything after "phase"/"ph" and pull just the
            # phase identifier out of it. Anything else (Block, Road,
            # House #) is intentionally discarded for the rollup.
            _suffix = _parts[1].strip()
            _suffix = _suffix.replace(":", "").replace(".", "").strip()
            _num_match = re.match(r'^(\d+)', _suffix)
            if _num_match:
                # Standard arabic-numeral phase like "Phase 5"
                return f"DHA Phase {_num_match.group(1)}"
            elif _suffix:
                # Fallback for non-numeric phases (Roman numerals "IV"/"V"
                # or letter-coded phases). Take the first whitespace-
                # delimited token and upper-case it for consistency.
                _num = _suffix.split()[0].strip()
                if _num: return f"DHA Phase {_num.upper()}"

    # If the string starts with "DHA " but had no Phase information we
    # can't safely guess which phase it belongs to — better to leave it
    # untouched than to invent a wrong phase number.
    if _an_lower.startswith("dha "):
        return area_name

    return area_name

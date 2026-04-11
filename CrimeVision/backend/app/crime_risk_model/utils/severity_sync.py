"""
severity_sync.py
================
Derives **real, data-driven** severity scores for every law section in the
``law_sections`` database table and keeps ``severity_map.json`` in sync.

Scoring algorithm (1-10 scale, higher = more severe):
  Priority 1  Keyword matching against ``english_title`` using the same
              rules as ``infer_severity_from_keywords()`` in helpers.py.
  Priority 2  PPC-chapter keyword → base severity band.
  Priority 3  Law-type default   (ATA=9, CNSA=8, PECA=6, PPC=5).

Called from:
  • Backend startup   — ``sync_severity_from_db()``
  • New/updated section — ``on_law_section_saved(title, chapter, law_type)``
"""

import os
import json
import logging
import sys

logger = logging.getLogger(__name__)

# ── Paths ─────────────────────────────────────────────────────────────────────
_UTILS_DIR  = os.path.dirname(__file__)
_CONFIG_PATH = os.path.normpath(os.path.join(_UTILS_DIR, '..', 'config', 'severity_map.json'))

# Make sure helpers is importable even when called from outside crime_risk_model
if _UTILS_DIR not in sys.path:
    sys.path.insert(0, _UTILS_DIR)

# ── PPC chapter → base severity ───────────────────────────────────────────────
# Keyword fragments for chapter titles (lowercase match).
# Ordered from highest to lowest so the first match wins.
_CHAPTER_SEVERITY = [
    (10, ['murder', 'qatl', 'terrorism', 'anti-terrorism', 'assassination',
          'culpable homicide amounting']),
    (9,  ['culpable homicide', 'rape', 'gang rape', 'kidnapping', 'abduction',
          'trafficking in persons', 'forced labour', 'thagi or dacoity',
          'waging war', 'sedition']),
    (8,  ['sexual offences', 'hurt', 'causing miscarriage',
          'endangering life', 'offences affecting the human body',
          'army', 'navy', 'air force', 'dacoity', 'robberies',
          'offences against the state']),
    (7,  ['robbery', 'extortion', 'arson', 'drug', 'narcotic',
          'public tranquility', 'kidnap', 'slavery']),
    (6,  ['religion', 'religious', 'criminal force', 'outraging modesty',
          'marriage', 'defiling', 'cyber', 'electronic', 'peca',
          'wrongful confinement', 'criminal breach of trust']),
    (5,  ['theft', 'burglary', 'cheating', 'false document',
          'breach of trust', 'misappropriation', 'property']),
    (4,  ['mischief', 'defamation', 'criminal intimidation', 'currency',
          'counterfeit', 'weights', 'measures', 'obstructing justice']),
    (3,  ['contempt', 'false evidence', 'perjury', 'elections',
          'public nuisance', 'negligence', 'public health']),
]

# Law-type safe defaults when no chapter/keyword match found
_LAW_TYPE_DEFAULT = {
    'ATA':  9,   # Anti-Terrorism Act — all offences are serious by definition
    'CNSA': 8,   # Control of Narcotics Substances Act
    'PECA': 6,   # Prevention of Electronic Crimes Act
    'PPC':  5,   # Pakistan Penal Code — broad default
}


# ── Internal helpers ─────────────────────────────────────────────────────────

def _load_severity_map():
    """Load current severity_map.json; return empty dict on any error."""
    try:
        with open(_CONFIG_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.warning("Could not read severity_map.json: %s", e)
        return {}


def _save_severity_map(data: dict):
    """Write severity_map.json atomically."""
    tmp = _CONFIG_PATH + '.tmp'
    try:
        with open(tmp, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        os.replace(tmp, _CONFIG_PATH)
    except Exception as e:
        logger.error("Failed to write severity_map.json: %s", e)


def _chapter_score(chapter: str) -> int | None:
    """Return severity score for a chapter string, or None if no match."""
    if not chapter:
        return None
    lower = chapter.lower()
    for score, keywords in _CHAPTER_SEVERITY:
        if any(kw in lower for kw in keywords):
            return score
    return None


def score_law_section(section_number: str, title: str,
                      chapter: str = '', law_type: str = 'PPC') -> int:
    """
    Derive an integer severity score (1-10) for a single law section.

    Steps:
      1. Keyword-match the ``english_title`` using helpers.py rules.
      2. Keyword-match the ``chapter`` title.
      3. Fall back to law-type default.
    """
    # ── Step 1: title keyword matching ───────────────────────────────────────
    try:
        from helpers import infer_severity_from_keywords   # relative import
    except ImportError:
        try:
            from utils.helpers import infer_severity_from_keywords
        except ImportError:
            infer_severity_from_keywords = None  # type: ignore

    if infer_severity_from_keywords is not None:
        title_score = infer_severity_from_keywords(title or '')
        if title_score is not None:
            return int(title_score)

    # ── Step 2: chapter keyword matching ─────────────────────────────────────
    chap_score = _chapter_score(chapter or '')
    if chap_score is not None:
        return chap_score

    # ── Step 3: law-type default ──────────────────────────────────────────────
    return _LAW_TYPE_DEFAULT.get((law_type or 'PPC').upper(), 5)


# ── Public API ────────────────────────────────────────────────────────────────

def on_law_section_saved(title: str, chapter: str = '',
                         law_type: str = 'PPC',
                         section_number: str = '') -> int:
    """
    Score one newly added / updated law section and persist it to
    severity_map.json immediately.

    Returns the computed severity score.
    """
    key   = title.lower().strip()
    score = score_law_section(section_number, title, chapter, law_type)

    data = _load_severity_map()
    if data.get(key) != score:
        data[key] = score
        _save_severity_map(data)
        logger.info("severity_sync: '%s' → %d (section %s %s)",
                    key, score, law_type, section_number)
    return score


def sync_severity_from_db() -> dict:
    """
    Read every row in ``law_sections``, score it, and update
    ``severity_map.json`` with any missing or updated entries.

    Returns a summary dict:
      {'added': N, 'updated': N, 'unchanged': N, 'errors': N}
    """
    summary = {'added': 0, 'updated': 0, 'unchanged': 0, 'errors': 0}

    # Lazy DB import to avoid circular imports at module import time
    try:
        import mysql.connector
        from dotenv import load_dotenv
        load_dotenv()

        db_cfg = {
            'host':     os.getenv('DB_HOST', 'localhost'),
            'user':     os.getenv('DB_USER', 'root'),
            'password': os.getenv('DB_PASSWORD', 'hafsa555'),
            'database': os.getenv('DB_NAME', 'crimevision_db'),
            'port':     int(os.getenv('DB_PORT', 3306)),
        }
        conn   = mysql.connector.connect(**db_cfg)
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT section_number, english_title, chapter, law_type FROM law_sections"
        )
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
    except Exception as e:
        logger.error("severity_sync: DB read failed — %s", e)
        return summary

    if not rows:
        logger.info("severity_sync: law_sections table is empty, skipping.")
        return summary

    data = _load_severity_map()
    changed = False

    for row in rows:
        try:
            title   = (row.get('english_title') or '').strip()
            chapter = (row.get('chapter') or '')
            lt      = (row.get('law_type') or 'PPC')
            sec_num = str(row.get('section_number') or '')
            key     = title.lower()

            if not key:
                continue

            new_score = score_law_section(sec_num, title, chapter, lt)
            existing  = data.get(key)

            if existing is None:
                data[key] = new_score
                summary['added'] += 1
                changed = True
            elif existing != new_score:
                data[key] = new_score
                summary['updated'] += 1
                changed = True
            else:
                summary['unchanged'] += 1
        except Exception as e:
            logger.warning("severity_sync: error scoring row %s — %s", row, e)
            summary['errors'] += 1

    if changed:
        _save_severity_map(data)

    logger.info(
        "severity_sync complete: +%d added, %d updated, %d unchanged, %d errors",
        summary['added'], summary['updated'], summary['unchanged'], summary['errors'],
    )
    return summary

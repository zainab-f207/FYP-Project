"""
Law Sections Management API Routes.

Provides CRUD + AI verification for Pakistani law sections (PPC, ATA, CNSA, etc.)
Only superadmin can modify; admin can flag; all authenticated users can read.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Body
from typing import Optional, Dict, Any, List, cast
from datetime import datetime
import logging
import json
import sys
import os
import threading

from app.core.database import get_db_connection
from app.dependencies import get_username_from_token

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/law-sections", tags=["law-sections"])

# ── severity_sync helper (non-fatal if model not yet trained) ─────────────────
_SEVERITY_SYNC = None
_SEVERITY_SYNC_BULK = None
try:
    _CRM_UTILS = os.path.normpath(
        os.path.join(os.path.dirname(__file__), '..', 'crime_risk_model', 'utils')
    )
    if _CRM_UTILS not in sys.path:
        sys.path.insert(0, _CRM_UTILS)
    from severity_sync import on_law_section_saved as _on_ls_saved, sync_severity_from_db as _sync_bulk
    _SEVERITY_SYNC = _on_ls_saved
    _SEVERITY_SYNC_BULK = _sync_bulk
    logger.info("law_sections: severity_sync loaded OK")
except Exception as _sse:
    logger.warning("law_sections: severity_sync not available (%s)", _sse)


def _sync_section(title: str, chapter: str = '', law_type: str = 'PPC', section_number: str = ''):
    """Fire-and-forget severity sync (never raises)."""
    if _SEVERITY_SYNC is None:
        return
    try:
        score = _SEVERITY_SYNC(
            title=title, chapter=chapter,
            law_type=law_type, section_number=section_number,
        )
        logger.debug("severity_sync: '%s' scored %d", title, score)
    except Exception as e:
        logger.warning("severity_sync failed for '%s': %s", title, e)


def ensure_law_sections_tables(cursor):
    """Create law_sections tables if they don't exist."""
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS law_sections (
            id INT AUTO_INCREMENT PRIMARY KEY,
            law_type VARCHAR(20) NOT NULL DEFAULT 'PPC',
            section_number VARCHAR(30) NOT NULL,
            english_title VARCHAR(500) NOT NULL,
            chapter VARCHAR(200) DEFAULT NULL,
            source VARCHAR(50) NOT NULL DEFAULT 'hardcoded_initial',
            verified_by VARCHAR(100) DEFAULT NULL,
            verified_at DATETIME DEFAULT NULL,
            is_verified BOOLEAN DEFAULT FALSE,
            ai_response TEXT DEFAULT NULL,
            ai_model VARCHAR(50) DEFAULT NULL,
            last_ai_check DATETIME DEFAULT NULL,
            notes TEXT DEFAULT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            UNIQUE KEY uk_law_section (law_type, section_number),
            INDEX idx_law_type (law_type),
            INDEX idx_verified (is_verified),
            INDEX idx_section_number (section_number)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS law_sections_audit (
            id INT AUTO_INCREMENT PRIMARY KEY,
            law_section_id INT NOT NULL,
            action VARCHAR(20) NOT NULL,
            old_title VARCHAR(500) DEFAULT NULL,
            new_title VARCHAR(500) DEFAULT NULL,
            changed_by VARCHAR(100) NOT NULL,
            change_reason TEXT DEFAULT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_section_id (law_section_id),
            INDEX idx_changed_by (changed_by),
            FOREIGN KEY (law_section_id) REFERENCES law_sections(id) ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """)
    # One-time migration: rename legacy 'gemini_verified' source to 'ai_verified'
    cursor.execute("""
        UPDATE law_sections SET source = 'ai_verified'
        WHERE source = 'gemini_verified'
    """)


def _check_superadmin(cursor, username: str):
    """Verify user is superadmin."""
    cursor.execute("SELECT role FROM users_info WHERE username = %s", (username,))
    user = cursor.fetchone()
    if not user or cast(Dict[str, Any], user).get("role") != "superadmin":
        raise HTTPException(status_code=403, detail="Only superadmins can perform this action")


# ---- READ ENDPOINTS (any authenticated user) ----

@router.get("")
def get_law_sections(
    law_type: Optional[str] = Query(None),
    is_verified: Optional[bool] = Query(None),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    current_user: str = Depends(get_username_from_token),
):
    """Get law sections with optional filters and pagination."""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        ensure_law_sections_tables(cursor)

        where_clauses = []
        params = []

        if law_type:
            where_clauses.append("law_type = %s")
            params.append(law_type.upper())
        if is_verified is not None:
            where_clauses.append("is_verified = %s")
            params.append(is_verified)
        if search:
            where_clauses.append("(section_number LIKE %s OR english_title LIKE %s)")
            params.extend([f"%{search}%", f"%{search}%"])

        where_sql = " WHERE " + " AND ".join(where_clauses) if where_clauses else ""

        # Count total
        cursor.execute(f"SELECT COUNT(*) as total FROM law_sections{where_sql}", params)
        total = cast(Dict[str, Any], cursor.fetchone())["total"]

        # Fetch page
        offset = (page - 1) * per_page
        cursor.execute(
            f"""SELECT id, law_type, section_number, english_title, chapter,
                       source, verified_by, verified_at, is_verified,
                       ai_model, last_ai_check, notes, created_at, updated_at
                FROM law_sections{where_sql}
                ORDER BY law_type, CAST(REGEXP_SUBSTR(section_number, '[0-9]+') AS UNSIGNED), section_number
                LIMIT %s OFFSET %s""",
            params + [per_page, offset],
        )
        rows = cursor.fetchall()

        # Get stats
        cursor.execute("""
            SELECT
                COUNT(*) as total_sections,
                SUM(is_verified) as verified_count,
                COUNT(DISTINCT law_type) as law_types_count
            FROM law_sections
        """)
        stats = cast(Dict[str, Any], cursor.fetchone())

        return {
            "sections": rows,
            "pagination": {"page": page, "per_page": per_page, "total": total, "pages": (total + per_page - 1) // per_page},
            "stats": {
                "total": stats["total_sections"],
                "verified": int(stats["verified_count"] or 0),
                "unverified": stats["total_sections"] - int(stats["verified_count"] or 0),
                "law_types": stats["law_types_count"],
            },
        }
    finally:
        cursor.close()
        conn.close()


@router.get("/stats")
def get_law_sections_stats(current_user: str = Depends(get_username_from_token)):
    """Get summary statistics for law sections."""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        ensure_law_sections_tables(cursor)
        cursor.execute("""
            SELECT law_type, COUNT(*) as count,
                   SUM(is_verified) as verified
            FROM law_sections GROUP BY law_type ORDER BY count DESC
        """)
        by_type = cursor.fetchall()
        total = sum(r["count"] for r in by_type)
        verified = sum(int(r["verified"] or 0) for r in by_type)
        return {"total": total, "verified": verified, "unverified": total - verified, "by_type": by_type}
    finally:
        cursor.close()
        conn.close()


@router.get("/lookup/{section_number}")
def lookup_section(section_number: str, law_type: str = Query("PPC")):
    """Public lookup - get English meaning of a law section (no auth needed for read)."""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        ensure_law_sections_tables(cursor)
        cursor.execute(
            "SELECT * FROM law_sections WHERE law_type = %s AND section_number = %s",
            (law_type.upper(), section_number.strip()),
        )
        row = cursor.fetchone()
        if row:
            return {"found": True, "section": row}
        # Fallback to hardcoded
        from app.ocr.ppc_sections import get_crime_name
        crime_name, detected_law = get_crime_name(
            f"{law_type}-{section_number}" if law_type != "PPC" else section_number
        )
        return {"found": False, "fallback": True, "crime_name": crime_name, "law_type": detected_law}
    finally:
        cursor.close()
        conn.close()


# ---- SUPERADMIN ENDPOINTS ----

@router.post("/verify-ai")
async def verify_with_ai(
    law_type: str = Query("PPC"),
    section_number: str = Query(...),
    current_user: str = Depends(get_username_from_token),
):
    """Use Gemini AI to verify a law section. Superadmin only."""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        _check_superadmin(cursor, current_user)

        # Get current section from DB
        cursor.execute(
            "SELECT id, english_title, ai_response, ai_model, last_ai_check FROM law_sections WHERE law_type = %s AND section_number = %s",
            (law_type.upper(), section_number.strip()),
        )
        row = cursor.fetchone()
        current_title = cast(Dict[str, Any], row)["english_title"] if row else None

        # Return cached result if Gemini was already called within the last 60 minutes
        if row:
            row = cast(Dict[str, Any], row)
            last_check = row.get("last_ai_check")
            cached_response = row.get("ai_response")
            if last_check and cached_response:
                age_minutes = (datetime.now() - last_check).total_seconds() / 60
                if age_minutes < 60:
                    try:
                        cached = json.loads(cached_response)
                        cached["_from_cache"] = True
                        cached["_cache_age_minutes"] = round(age_minutes, 1)
                        logger.info(f"[law-sections] Returning cached AI result for {law_type} {section_number} (age: {age_minutes:.1f}m)")
                        return cached
                    except Exception:
                        pass  # Cache corrupted — fall through to live call

        from app.services.gemini_law_verifier import verify_law_section
        result = await verify_law_section(law_type.upper(), section_number.strip(), current_title)

        # Save full AI response JSON to DB for caching
        if row:
            cursor.execute(
                """UPDATE law_sections SET ai_response = %s, ai_model = %s, last_ai_check = %s
                   WHERE law_type = %s AND section_number = %s""",
                (json.dumps(result), result.get("model", ""), datetime.now(),
                 law_type.upper(), section_number.strip()),
            )
            conn.commit()

        return result
    finally:
        cursor.close()
        conn.close()


@router.put("/{section_id}")
def update_section(
    section_id: int,
    body: Dict[str, Any] = Body(...),
    current_user: str = Depends(get_username_from_token),
):
    """Update a law section. Superadmin only."""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        _check_superadmin(cursor, current_user)

        cursor.execute("SELECT * FROM law_sections WHERE id = %s", (section_id,))
        existing = cursor.fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail="Section not found")
        existing = cast(Dict[str, Any], existing)

        new_title = body.get("english_title", existing["english_title"])
        new_verified = body.get("is_verified", existing["is_verified"])
        notes = body.get("notes", existing.get("notes"))
        reason = body.get("change_reason", "")

        cursor.execute(
            """UPDATE law_sections SET english_title = %s, is_verified = %s,
                      verified_by = %s, verified_at = %s, notes = %s, source = %s
               WHERE id = %s""",
            (new_title, new_verified,
             current_user if new_verified else existing.get("verified_by"),
             datetime.now() if new_verified else existing.get("verified_at"),
             notes, "superadmin_manual", section_id),
        )

        # Audit trail
        if new_title != existing["english_title"]:
            cursor.execute(
                """INSERT INTO law_sections_audit
                   (law_section_id, action, old_title, new_title, changed_by, change_reason)
                   VALUES (%s, %s, %s, %s, %s, %s)""",
                (section_id, "update", existing["english_title"], new_title, current_user, reason),
            )

        conn.commit()
        # Sync severity_map.json with the updated title
        _sync_section(
            title=new_title,
            chapter=existing.get('chapter', ''),
            law_type=existing.get('law_type', 'PPC'),
            section_number=str(existing.get('section_number', '')),
        )
        return {"success": True, "message": "Section updated successfully"}
    finally:
        cursor.close()
        conn.close()


@router.post("/approve-ai/{section_id}")
def approve_ai_suggestion(
    section_id: int,
    body: Dict[str, Any] = Body(...),
    current_user: str = Depends(get_username_from_token),
):
    """Approve AI suggestion and update section title. Superadmin only."""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        _check_superadmin(cursor, current_user)

        cursor.execute("SELECT * FROM law_sections WHERE id = %s", (section_id,))
        existing = cursor.fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail="Section not found")
        existing = cast(Dict[str, Any], existing)

        ai_title = body.get("ai_title", "")
        if not ai_title:
            raise HTTPException(status_code=400, detail="ai_title is required")

        cursor.execute(
            """UPDATE law_sections SET english_title = %s, is_verified = TRUE,
                      verified_by = %s, verified_at = %s, source = 'ai_verified'
               WHERE id = %s""",
            (ai_title, current_user, datetime.now(), section_id),
        )

        cursor.execute(
            """INSERT INTO law_sections_audit
               (law_section_id, action, old_title, new_title, changed_by, change_reason)
               VALUES (%s, %s, %s, %s, %s, %s)""",
            (section_id, "ai_approve", existing["english_title"], ai_title, current_user,
             "Approved AI (Gemini) suggestion"),
        )

        conn.commit()
        # Sync severity_map.json with the approved AI title
        _sync_section(
            title=ai_title,
            chapter=existing.get('chapter', ''),
            law_type=existing.get('law_type', 'PPC'),
            section_number=str(existing.get('section_number', '')),
        )
        return {"success": True, "message": "AI suggestion approved"}
    finally:
        cursor.close()
        conn.close()


@router.post("/seed")
def seed_from_hardcoded(current_user: str = Depends(get_username_from_token)):
    """Seed database from hardcoded ppc_sections.py. Superadmin only. Skips existing."""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        _check_superadmin(cursor, current_user)
        ensure_law_sections_tables(cursor)

        from app.ocr.ppc_sections import PPC_SECTIONS, LAW_MAPPINGS

        inserted = 0
        skipped = 0

        # Seed PPC sections
        for sec_num, title in PPC_SECTIONS.items():
            try:
                cursor.execute(
                    """INSERT IGNORE INTO law_sections (law_type, section_number, english_title, source)
                       VALUES (%s, %s, %s, %s)""",
                    ("PPC", sec_num, title, "hardcoded_initial"),
                )
                if cursor.rowcount > 0:
                    inserted += 1
                else:
                    skipped += 1
            except Exception:
                skipped += 1

        # Seed other law types
        for prefix, info in LAW_MAPPINGS.items():
            law_dict = info["dict"]
            law_name = info.get("name", prefix)
            for sec_num, title in law_dict.items():
                try:
                    cursor.execute(
                        """INSERT IGNORE INTO law_sections (law_type, section_number, english_title, source)
                           VALUES (%s, %s, %s, %s)""",
                        (law_name.upper() if law_name.upper() in ("ATA", "CNSA", "PECA") else prefix,
                         sec_num, title, "hardcoded_initial"),
                    )
                    if cursor.rowcount > 0:
                        inserted += 1
                    else:
                        skipped += 1
                except Exception:
                    skipped += 1

        conn.commit()
        # Bulk-sync ALL sections to severity_map.json after seeding
        if _SEVERITY_SYNC_BULK is not None:
            try:
                threading.Thread(target=_SEVERITY_SYNC_BULK, daemon=True,
                                 name='SeveritySeedSync').start()
            except Exception as _bse:
                logger.warning("severity_sync bulk post-seed failed: %s", _bse)
        return {"success": True, "inserted": inserted, "skipped": skipped,
                "message": f"Seeded {inserted} sections ({skipped} already existed)"}
    finally:
        cursor.close()
        conn.close()


@router.get("/audit/{section_id}")
def get_audit_trail(section_id: int, current_user: str = Depends(get_username_from_token)):
    """Get audit trail for a specific section."""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            "SELECT * FROM law_sections_audit WHERE law_section_id = %s ORDER BY created_at DESC",
            (section_id,),
        )
        return {"audit": cursor.fetchall()}
    finally:
        cursor.close()
        conn.close()


@router.post("/ppc/scan-missing")
async def scan_missing_ppc(current_user: str = Depends(get_username_from_token)):
    """Use AI to find important PPC sections missing from the DB. Superadmin only."""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        _check_superadmin(cursor, current_user)
        ensure_law_sections_tables(cursor)

        # Get all existing PPC section numbers
        cursor.execute("SELECT section_number FROM law_sections WHERE law_type = 'PPC'")
        existing = [r["section_number"] for r in cursor.fetchall()]

        from app.services.gemini_law_verifier import scan_missing_ppc_sections
        result = await scan_missing_ppc_sections(existing)
        return result
    finally:
        cursor.close()
        conn.close()


@router.post("/insert")
def insert_law_section(
    body: Dict[str, Any] = Body(...),
    current_user: str = Depends(get_username_from_token),
):
    """Insert a new law section (e.g. AI-suggested missing PPC). Superadmin only."""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        _check_superadmin(cursor, current_user)
        ensure_law_sections_tables(cursor)

        law_type = body.get("law_type", "PPC").upper()
        section_number = str(body.get("section_number", "")).strip()
        english_title = str(body.get("english_title", "")).strip()
        chapter = str(body.get("chapter", "")).strip() or None
        notes = str(body.get("notes", "")).strip() or None

        if not section_number or not english_title:
            raise HTTPException(status_code=400, detail="section_number and english_title are required")

        # Check for duplicates
        cursor.execute(
            "SELECT id FROM law_sections WHERE law_type = %s AND section_number = %s",
            (law_type, section_number),
        )
        if cursor.fetchone():
            raise HTTPException(status_code=409, detail=f"{law_type} section {section_number} already exists")

        cursor.execute(
            """INSERT INTO law_sections
               (law_type, section_number, english_title, chapter, notes, source, is_verified, verified_by, verified_at)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""",
            (law_type, section_number, english_title, chapter, notes,
             "ai_suggested", True, current_user, datetime.now()),
        )
        new_id = cursor.lastrowid

        # Audit entry
        cursor.execute(
            """INSERT INTO law_sections_audit
               (law_section_id, action, old_title, new_title, changed_by, change_reason)
               VALUES (%s, %s, %s, %s, %s, %s)""",
            (new_id, "insert", None, english_title, current_user, "AI-suggested missing section inserted"),
        )

        conn.commit()
        # Sync severity for the new section immediately
        _sync_section(
            title=english_title,
            chapter=chapter or '',
            law_type=law_type,
            section_number=section_number,
        )
        return {"success": True, "id": new_id, "message": f"{law_type} {section_number} inserted successfully"}
    finally:
        cursor.close()
        conn.close()


@router.get("/law-types")
def get_law_types(current_user: str = Depends(get_username_from_token)):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        ensure_law_sections_tables(cursor)
        cursor.execute("SELECT DISTINCT law_type FROM law_sections ORDER BY law_type")
        return {"law_types": [r["law_type"] for r in cursor.fetchall()]}
    finally:
        cursor.close()
        conn.close()


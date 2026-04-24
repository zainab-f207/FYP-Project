# """
# Approval Workflow Module
# Admin sensitive actions require superadmin approval before execution.
# """

# import json
# import logging
# import os
# import re
# import unicodedata
# from datetime import datetime
# from typing import Optional, List, Dict, Any, Tuple, cast

# import requests

# import joblib
# import pandas as pd

# # Severity map for PPC-based risk derivation (no hardcoded category mapping)
# _SEVERITY_MAP: Dict[str, float] = {}
# try:
#     _sev_path = os.path.join(
#         os.path.dirname(__file__),
#         "crime_risk_model", "config", "severity_map.json"
#     )
#     with open(_sev_path, "r", encoding="utf-8") as _sf:
#         _SEVERITY_MAP = json.load(_sf)
# except Exception as _se:
#     pass  # risk will default to Medium

# from app.core.database import get_db_connection
# from app.core.config import MODEL_DIR
# from app.ocr.ppc_sections import get_crime_name
# from app.ocr.fir_specialized_ocr import URDU_TO_ENGLISH_THANA

# logger = logging.getLogger(__name__)


# def _get_system_setting_int(key: str, default: int, min_value: int, max_value: int) -> int:
#     """Fetch integer system setting with bounds and fallback."""
#     conn = None
#     cursor = None
#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor(dictionary=True)
#         cursor.execute("SELECT setting_value FROM system_settings WHERE setting_key = %s", (key,))
#         row = cast(Optional[Dict[str, Any]], cursor.fetchone())
#         raw = row.get("setting_value") if row else default
#         val = int(raw)
#         return max(min_value, min(max_value, val))
#     except Exception:
#         return default
#     finally:
#         if cursor:
#             cursor.close()
#         if conn and conn.is_connected():
#             conn.close()

# # --------------- ML model & encoders (for risk prediction) ---------------
# try:
#     _rf_model = joblib.load(os.path.join(MODEL_DIR, "random_forest_model.joblib"))
#     _le_area = joblib.load(os.path.join(MODEL_DIR, "label_encoder_area.joblib"))
#     _le_crime = joblib.load(os.path.join(MODEL_DIR, "label_encoder_crime.joblib"))
#     _le_risk = joblib.load(os.path.join(MODEL_DIR, "label_encoder_risk.joblib"))
# except Exception as _e:
#     logger.error(f"Approval-workflow: could not load ML model/encoders: {_e}")
#     _rf_model = _le_area = _le_crime = _le_risk = None

# # Urdu → English area mapping (combines thana dict + common geocode locations)
# _URDU_EN_MAP: Dict[str, str] = {**URDU_TO_ENGLISH_THANA}
# # Add extra mappings that live inside the geocode function but are commonly needed:
# _EXTRA_EN = {
#     "بھاٹی گیٹ": "Bhati Gate", "لوہاری گیٹ": "Lohari Gate",
#     "دہلی گیٹ": "Delhi Gate", "سمن آباد": "Samanabad",
#     "سبزہ زار": "Sabzazar", "چوبرجی": "Chauburji",
#     "لکشمی چوک": "Lakshmi Chowk", "نشتر ٹاؤن": "Nishtar Town",
#     "باغبانپورہ": "Baghbanpura", "ہربنس پورہ": "Harbanspura",
#     "غڑی شاہو": "Garhi Shahu", "شاد باغ مارکیٹ": "Shadbagh Market",
#     "شادمان": "Shadman", "ڈی ایچ اے": "DHA Lahore",
#     "بحریہ ٹاؤن": "Bahria Town Lahore",
# }
# _URDU_EN_MAP.update(_EXTRA_EN)

# # ── Transliteration: MyMemory API (free, no account, no card, forever) ───────
# # https://mymemory.translated.net — 5,000 chars/day free, no key needed.
# # Falls back to keyword substitution if the API call fails.
# _MYMEMORY_URL = "https://api.mymemory.translated.net/get"
# _URDU_CHARS_RE = re.compile(r"[\u0600-\u06FF\u0750-\u077F\uFB50-\uFDFF\uFE70-\uFEFF]")

# # Keyword map used as fast pre-pass and fallback
# _KW_MAP = [
#     ("گلشنِ راوی، جی بلاک روڈ", "Gulshan-e-Ravi G Block Road"),
#     ("الخضریا ہاؤسنگ بلاک F، مین والٹن روڈ", "Al-Khadriya Housing Block F, Main Walton Road"),
#     ("ایڈن آباد بلاک G، شاہ پور کانجراں روڈ", "Eden Abad Block G, Shahpur Kanjran Road"),
#     ("ایڈن آباد بلاک E، کچھہری روڈ", "Eden Abad Block E, Kutchery Road"),
#     ("ایڈن آباد بلاک F، چونیاں روڈ", "Eden Abad Block F, Chunian Road"),
#     ("پی آئی اے سوسائٹی بلاک G، جی ٹی روڈ", "PIA Society Block G, GT Road"),
#     ("پی آئی اے سوسائٹی بلاک E، مین والٹن روڈ", "PIA Society Block E, Main Walton Road"),
#     ("پی آئی اے سوسائٹی بلاک F، چونیاں روڈ", "PIA Society Block F, Chunian Road"),
#     ("الخضریا ہاؤسنگ بلاک G، ٹھوکر نیاز بیگ انٹرچینج", "Al-Khadriya Housing Block G, Thokar Niaz Baig Interchange"),
#     ("الخضریا ہاؤسنگ بلاک E، روٹی تندور روڈ", "Al-Khadriya Housing Block E, Roti Tandoor Road"),
#     ("بحریہ آرچرڈ فیز 1 بلاک F، شیخ زید روڈ", "Bahria Orchard Phase 1 Block F, Sheikh Zayed Road"),
#     ("بحریہ آرچرڈ فیز 2 بلاک F، رائیونڈ روڈ", "Bahria Orchard Phase 2 Block F, Raiwind Road"),
#     ("بحریہ آرچرڈ فیز 2 بلاک G، خیا ب انِ جناح", "Bahria Orchard Phase 2 Block G, Khayaban-e-Jinnah"),
#     ("بحریہ آرچرڈ فیز 1 بلاک G، آسوکی روڈ", "Bahria Orchard Phase 1 Block G, Asooki Road"),
#     ("بحریہ آرچرڈ فیز 3 بلاک G، گجو متہ روڈ", "Bahria Orchard Phase 3 Block G, Gajumatta Road"),
#     ("بحریہ آرچرڈ فیز 3 بلاک F، آسوکی روڈ", "Bahria Orchard Phase 3 Block F, Asooki Road"),
#     ("راوی روڈ، راوی روڈ", "Ravi Road"),
#     ("کینٹ صدر بازار، صدر بازار روڈ", "Cantt Saddar Bazaar, Saddar Bazaar Road"),
#     ("بحریہ آرچرڈ فیز 4 بلاک H، کینٹ روڈ", "Bahria Orchard Phase 4 Block H, Cantt Road"),
#     ("الخضریا ہاؤسنگ بلاک H، کینٹ روڈ", "Al-Khadriya Housing Block H, Cantt Road"),
#     ("لال کرتی کینٹ، ٹھوکر نیاز بیگ انٹرچینج", "Lal Kurti (Cantt), Thokar Niaz Baig Interchange"),
#     ("سرفرار روڈ کینٹ، گجومتہ انٹرچینج", "Sarfaraz Road Cantt, Gajumatta Interchange"),
#     ("فوجی کالونی کینٹ، نجات روڈ", "Fauji Colony Cantt, Nijat Road"),
#     ("پی آئی اے سوسائٹی بلاک H سب بلاک P، کینٹ روڈ", "PIA Society Block H Sub-Block P, Cantt Road"),
#     ("فورٹریس اسٹیڈیم ایریا سب بلاک K، کینٹ روڈ", "Fortress Stadium Area Sub-Block K, Cantt"),
#     ("چوبرجی انڈر پاس سب بلاک K، کینٹ روڈ", "Chuburji Underpass Sub-Block K, Cantt Road"),
#     ("لال کرتی کینٹ سب بلاک J، نہر کنار روڈ", "Lal Kurti Cantt Sub-Block J, Canal Road (Nehar Kinara Road)"),
#     ("سرفرار روڈ کینٹ سب بلاک D، شاہراہِ پاکستان", "Sarfaraz Road Cantt Sub-Block D, Shahrah-e-Pakistan"),
#     ("جیل روڈ، جیل روڈ", "Jail Road"),
#     ("ٹاؤن شپ، مدینہ چوک / جامعہ اشرفیہ روڈ", "Township Madina Chowk / Jamia Ashrafia Road"),
#     ("شالامار باغ، جی ٹی روڈ", "Shalimar Bagh GT Road"),
#     ("شاہدرہ ٹاؤن، راوی روڈ / جی ٹی روڈ", "Shahdara Town Ravi Road / GT Road"),
#     ("علامہ اقبال ٹاؤن (کری بلاک مارکیٹ)، وریسٹر روڈ/مولانا شوکت علی؟", "Allama Iqbal Town Karim Block Market / Wahdat Road / Maulana Shaukat Ali Road"),
#     ("سمن آباد، سمن آباد مین بلیوارڈ", "Samanabad Main Boulevard"),
#     ("فیروزپور روڈ (قینچی)، قینچی امرسدھو", "Ferozepur Road (Qainchi), Qainchi Amer Sidhu"),
#     ("کاماہاں انٹرچینج سب بلاک A، فیروزپور روڈ", "Kamahan Interchange Sub-Block A, Ferozepur Road"),
#     ("لی ڈی اے سٹی سیکٹر 2 بلاک H سب بلاک P، فیروزپور روڈ", "LDA City Sector 2 Block H Sub-Block P, Ferozepur Road"),
#     ("گدا فی اسٹیڈیم، فروزپور روڈ / قذافی", "Gaddafi Stadium / Ferozepur Road"),
#     ("قذافی اسٹیڈیم، فروزپور روڈ / قذافی", "Gaddafi Stadium / Ferozepur Road"),
#     ("ریلوے اسٹیشن لاہور، نزد امیگریشن/مکلوڈ روڈ", "Lahore Railway Station / Near Immigration / Macleod Road"),
#     ("برکی روڈ / بیدیان، برکی روڈ", "Barkee Road / Beedian"),
#     ("فورٹریس اسٹیڈیم ایریا، لیاقت علی خان روڈ", "Fortress Stadium Area / Liaqat Ali Khan Road"),
#     ("فورٹریس اسٹیڈیم ایریا سب بلاک P، چونیاں روڈ", "Fortress Stadium Area Sub-Block P / Choonian Road"),
#     ("فورٹریس اسٹیڈیم ایریا سب بلاک I، رائیونڈ روڈ", "Fortress Stadium Area Sub-Block I / Raiwind Road"),
#     ("نواں کوٹ بائیک پوائنٹ، بیدیاں روڈ", "Nawan Kot Bike Point / Badian Road"),
#     ("شادمـان مارکیٹ، شادمـان روڈ", "Shadman Market / Shadman Road"),
#     ("شامدان مارکیٹ، شادمان روڈ", "Shadman Market / Shadman Road"),
#     ("شاد باغ مارکیٹ", "Shad Bagh Market"),
#     ("بادامی باغ", "Badami Bagh"),
#     ("ماڈل ٹاؤن پارک، ایف بلاک روڈ", "Model Town Park / F Block Road"),
#     ("فیصل ٹاؤن، آربی بلاک روڈ", "Faisal Town / R Block Road"),
#     ("بحریہ آرچرڈ فیز 3 بلاک E، کینال روڈ", "Bahria Orchard Phase 3, Block E / Canal Road"),
#     ("بحریہ آرچرڈ فیز 1 بلاک E، ریونیو روڈ", "Bahria Orchard Phase 1, Block E / Revenue Road"),
#     ("عامر روڈ (اسٹریٹ 9، تاج گزی پارک کے سامنے)، شاد باغ", "Amir Road (Street 9, Opposite Taj Ghazi Park), Shad Bagh"),
#     ("سنت نگر چوک، مزنگ روڈ، گورنمنٹ گرلز ہائی اسکول کے سامنے", "Santanagar Chowk Mazang Road (Opposite Government Girls High School)"),
#     ("دہلی گیٹ، دہلی گیٹ روڈ", "Delhi Gate Road"),
#     ("سبزہ زار، سبزہ زار مین بلیوارڈ", "Sabzazar Main Boulevard"),
#     # Valencia Town — only valid if Defence/Asooki/Awan/Raiwind/Gajumatta
#     ("والینشیا ٹاؤن بلاک D، آسوکی روڈ", "Valencia Town Block D, Asooki Road"),
#     ("والینشیا ٹاؤن بلاک K، اعوان روڈ", "Valencia Town Block K, Awan Road"),
#     ("والینشیا ٹاؤن بلاک B، ڈیفنس روڈ", "Valencia Town Block B, Defence Road"),
#     ("والینشیا ٹاؤن بلاک J، ڈیفنس روڈ", "Valencia Town Block J, Defence Road"),
#     ("والینشیا ٹاؤن بلاک M، ملتان روڈ", "Valencia Town Block M, Multan Road"),
#     ("والینشیا ٹاؤن بلاک A، گجومتہ انٹرچینج", "Valencia Town Block A, Gajumatta Interchange"),
#     # Lake City — only valid if Sectors M1-M8 with Defence/Raiwind/Asooki
#     ("لیک سٹی سیکٹر M1 سب بلاک T، آسوکی روڈ", "Lake City Sector M1 Sub-Block T, Asooski Road"),
#     ("لیک سٹی سیکٹر M3 سب بلاک R، ڈیفنس روڈ", "Lake City Sector M3 Sub-Block R, Defence Road"),
#     ("لیک سٹی سیکٹر M5 سب بلاک R، ڈیفنس روڈ", "Lake City Sector M5 Sub-Block R, Defence Road"),
#     ("لیک سٹی سیکٹر M5 سب بلاک V، ریونیو روڈ", "Lake City Sector M5 Sub-Block V, Revenue Road"),
#     ("لیک سٹی سیکٹر M3، ریونیو روڈ", "Lake City Sector M3, Revenue Road"),
#     # Disambiguate misassigned societies
#     ("پی آئی اے سوسائٹی بلاک B، شیخ زید روڈ", "PIA Society Block B, Sheikh Zayed Road"),
#     ("بحریہ آرچرڈ فیز 1 بلاک B، ڈیفنس روڈ", "Bahria Orchard Phase 1 Block B, Defence Road"),
#     ("بحریہ آرچرڈ فیز 2 بلاک B، ڈیفنس روڈ", "Bahria Orchard Phase 2 Block B, Defence Road"),
#     ("بحریہ آرچرڈ فیز 3 بلاک B، اعوان روڈ", "Bahria Orchard Phase 3 Block B, Awan Road"),
#     ("الخضریا ہاؤسنگ بلاک B، رائیونڈ روڈ", "Al-Khadriya Housing Block B, Raiwind Road"),
#     ("ایڈن آباد بلاک B، وارث روڈ", "Eden Abad Block B, Waris Road"),
#     ("پی سی ایس آئی آر", "PCSIR Housing Scheme"),
#     ("ڈی ایچ اے", "DHA"), ("بحریہ ٹاؤن", "Bahria Town"),
#     ("جوہر ٹاؤن", "Johar Town"), ("ماڈل ٹاؤن", "Model Town"),
#     ("گارڈن ٹاؤن", "Garden Town"), ("علامہ اقبال ٹاؤن", "Allama Iqbal Town"),
#     ("واپڈا ٹاؤن", "WAPDA Town"), ("لی ڈی اے", "LDA"),
#     ("گلبرگ", "Gulberg"), ("شادمان", "Shadman"),
#     ("گلشنِ راوی", "Gulshan-e-Ravi"), ("گجومتہ", "Gajumatta"),
#     ("ٹھوکر نیاز بیگ", "Thokar Niaz Baig"), ("مولانا شوکت علی", "Maulana Shaukat Ali"),
#     ("شاہ عالمی", "Shah Alam"), ("داتا دربار", "Data Darbar"),
#     ("لبرٹی مارکیٹ", "Liberty Market"), ("حفیظ سنٹر", "Hafeez Centre"),
#     ("جی ٹی روڈ", "GT Road"), ("ٹنکی والا روڈ", "Tanki Wala Road"),
#     ("کچھہری روڈ", "Kutchery Road"), ("الحمد روڈ", "Al Hamd Road"),
#     ("نجات روڈ", "Nijat Road"),
#     ("برکی روڈ", "Burki Road"), ("رائیونڈ روڈ", "Raiwind Road"),
#     ("نہر کنار روڈ", "Canal Bank Road"),
#     ("روٹی تندور روڈ", "Roti Tandoor Road"), ("اقبال ایونیو", "Iqbal Avenue"),
#     ("خیا ب انِ جناح", "Khayaban-e-Jinnah"), ("خیابانِ جناح", "Khayaban-e-Jinnah"),
#     ("کاماہاں انٹرچینج", "Kamahan Interchange"),
#     ("عبدالحق روڈ", "Abdul Haq Road"), ("لیاقت علی خان روڈ", "Liaquat Ali Khan Road"),
#     ("بیرونی سمن آباد روڈ", "Outer Samnabad Road"), ("چونیاں روڈ", "Chunian Road"),
#     ("نشتر روڈ", "Nishtar Road"), ("ریونیو روڈ", "Revenue Road"),
#     ("ڈیفنس روڈ", "Defence Road"), ("شاہ پور کانجراں روڈ", "Shahpur Kanjran Road"),
#     ("نیا زی", "Niazi"), ("بیرونی", "Outer"), ("مین", "Main"),
#     ("ساگیان", "Sagian"), ("شیخ زید", "Sheikh Zayed"),
#     ("گجو متہ روڈ", "Gajumatta Road"), ("ایڈن آباد", "Eden Abad"),
#     ("الخضریا ہاؤسنگ", "Al Khazriya Housing"), ("پی آئی اے سوسائٹی", "PIA Society"),
#     ("پی آئی اے سوسائٹی", "PIA Society"),
#     ("نواں کوٹ", "Nawan Kot"), ("بائیک پوائنٹ", "Bike Point"),
#     ("چوبرجی انڈر پاس", "Chauburji Underpass"),
#     ("مین بلیوارڈ", "Main Boulevard"), ("فیروزپور روڈ", "Ferozepur Road"),
#     ("ملتان روڈ", "Multan Road"), ("کینال روڈ", "Canal Road"),
#     ("روڈ", "Road"), ("چوک", "Chowk"), ("بازار", "Bazaar"),
#     ("سٹریٹ", "Street"), ("بلاک", "Block"), ("سیکٹر", "Sector"),
#     ("فیز", "Phase"), ("ٹاؤن", "Town"), ("مارکیٹ", "Market"),
#     ("کالونی", "Colony"), ("پارک", "Park"),
# ]

# _URDU_CHAR_ROMAN: Dict[str, str] = {
#     "ا": "a", "آ": "aa", "أ": "a", "إ": "i", "ء": "", "ئ": "e", "ؤ": "o",
#     "ب": "b", "پ": "p", "ت": "t", "ٹ": "t", "ث": "s", "ج": "j", "چ": "ch",
#     "ح": "h", "خ": "kh", "د": "d", "ڈ": "d", "ذ": "z", "ر": "r", "ڑ": "r",
#     "ز": "z", "ژ": "zh", "س": "s", "ش": "sh", "ص": "s", "ض": "z", "ط": "t",
#     "ظ": "z", "ع": "a", "غ": "gh", "ف": "f", "ق": "q", "ک": "k", "گ": "g",
#     "ل": "l", "م": "m", "ن": "n", "ں": "n", "و": "o", "ہ": "h", "ھ": "h",
#     "ی": "y", "ے": "e",
# }


# def _romanize_urdu_token(token: str) -> str:
#     out: List[str] = []
#     for ch in token:
#         out.append(_URDU_CHAR_ROMAN.get(ch, ""))
#     roman = "".join(out)
#     roman = re.sub(r"(.)\\1{2,}", r"\\1\\1", roman)
#     return re.sub(r"\s+", " ", roman).strip(" -_/,.،")


# def _romanize_remaining_urdu(text: str) -> str:
#     def _repl(match: re.Match[str]) -> str:
#         roman = _romanize_urdu_token(match.group(0))
#         return f" {roman} " if roman else " "

#     return _URDU_CHARS_RE.sub(_repl, text)


# def _keyword_sub(urdu_text: str) -> str:
#     """Apply keyword substitution, strip remaining Urdu chars, title-case."""
#     result = urdu_text
#     for urdu_kw, eng_kw in _KW_MAP:
#         result = result.replace(urdu_kw, eng_kw)
#     result = _romanize_remaining_urdu(result)
#     result = _URDU_CHARS_RE.sub(" ", result)
#     result = re.sub(r"\s+", " ", result).strip()
#     if len(result) < 4:
#         return urdu_text
#     titled = result.title()
#     # Preserve known acronym casing after title-casing.
#     titled = re.sub(r"\bPcsir\b", "PCSIR", titled)
#     titled = re.sub(r"\bDha\b", "DHA", titled)
#     titled = re.sub(r"\bLda\b", "LDA", titled)
#     titled = re.sub(r"\bWapda\b", "WAPDA", titled)
#     titled = re.sub(r"\bGt\b", "GT", titled)
#     titled = re.sub(r"\bMm Alam\b", "MM Alam", titled)
#     return titled


# def _azure_transliterate_single(urdu_text: str) -> str:
#     """
#     Translate a single Urdu area string to English via MyMemory free API.
#     No account, no credit card, no API key — free forever (5,000 chars/day).

#     Strategy:
#       1. Apply keyword substitution (instant, handles most common Lahore areas).
#       2. If result still has Urdu chars, call MyMemory for the full translation.
#       3. Fall back to keyword result if API call fails or quota exceeded.
#     """
#     if not urdu_text or not urdu_text.strip():
#         return ""

#     # Deterministic handling for structured FIR locations.
#     # This avoids external transliteration drift (e.g. Phase 9 -> Phase 1).
#     normalized = re.sub(r"\s+", " ", urdu_text.strip())
#     ocr_letter_map = {
#         "6": "G",
#         "0": "O",
#         "1": "I",
#         "5": "S",
#         "8": "B",
#     }

#     dha = re.search(
#         r"ڈی\s*ایچ\s*اے\s*فیز\s*(\d+)(?:\s*بلاک\s*([A-Za-z0-9]))?(?:\s*(?:سب\s*بلاک|سے\s*بلاک)\s*([A-Za-z0-9]))?",
#         normalized,
#         flags=re.IGNORECASE,
#     )
#     if dha:
#         phase = dha.group(1)
#         block = dha.group(2)
#         sub_block = dha.group(3)
#         out = f"DHA Phase {phase}"
#         if block:
#             out += f" Block {ocr_letter_map.get(block.upper(), block.upper())}"
#         if sub_block:
#             out += f" Sub-Block {ocr_letter_map.get(sub_block.upper(), sub_block.upper())}"
#         return out

#     bahria = re.search(
#         r"بحریہ\s*ٹاؤن\s*(?:سیکٹر|سیٹ|سکٹر)\s*([A-Za-z0-9])(?:\s*بلاک\s*([A-Za-z0-9]))?(?:\s*(?:سب\s*بلاک|سے\s*بلاک)\s*([A-Za-z0-9]))?",
#         normalized,
#         flags=re.IGNORECASE,
#     )
#     if bahria:
#         sector = ocr_letter_map.get(bahria.group(1).upper(), bahria.group(1).upper())
#         block = bahria.group(2)
#         sub_block = bahria.group(3)
#         out = f"Bahria Town Sector {sector}"
#         if block:
#             out += f" Block {ocr_letter_map.get(block.upper(), block.upper())}"
#         if sub_block:
#             out += f" Sub-Block {ocr_letter_map.get(sub_block.upper(), sub_block.upper())}"
#         return out

#     # Pass 1: keyword substitution
#     kw_result = _keyword_sub(urdu_text)

#     # If keyword pass left no Urdu chars, it's good enough — no API call needed
#     if not _URDU_CHARS_RE.search(kw_result):
#         return kw_result

#     # Pass 2: MyMemory API for remaining Urdu text
#     try:
#         timeout_seconds = _get_system_setting_int(
#             "ocr_transliteration_timeout_seconds",
#             default=8,
#             min_value=1,
#             max_value=60,
#         )
#         resp = requests.get(
#             _MYMEMORY_URL,
#             params={"q": urdu_text[:500], "langpair": "ur|en"},
#             timeout=timeout_seconds,
#         )
#         if resp.status_code == 200:
#             data = resp.json()
#             translated = data.get("responseData", {}).get("translatedText", "")
#             # MyMemory echoes original on failure or quota exceeded
#             if translated and translated != urdu_text and not _URDU_CHARS_RE.search(translated):
#                 return re.sub(r"\s+", " ", translated).strip().title()
#     except Exception as _exc:
#         logger.debug(f"MyMemory call failed: {_exc} — using keyword result")

#     return kw_result  # keyword result as final fallback


# # Actions that require superadmin approval
# SENSITIVE_ACTIONS = [
#     "delete_user",
#     "bulk_delete",
#     "change_role_to_admin",
#     "change_role_to_superadmin",
#     "bulk_suspend",
#     "fir_ocr_submission",
# ]

# # Permission required for each action type (None = any admin may submit)
# ACTION_PERMISSIONS = {
#     "delete_user": "manage_users",
#     "bulk_delete": "manage_users",
#     "bulk_suspend": "manage_users",
#     "change_role_to_admin": "manage_users",
#     "change_role_to_superadmin": "manage_users",
#     "fir_ocr_submission": None,  # any admin can submit FIR for approval
# }


# def create_approval_request(
#     admin_username: str,
#     action_type: str,
#     target_type: str,
#     target_id: Optional[int] = None,
#     request_data: Optional[dict] = None,
# ) -> Optional[int]:
#     """
#     Create an approval request for a sensitive admin action.
#     Returns the request ID or None on failure.
#     """
#     conn = None
#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor()
#         cursor.execute(
#             """INSERT INTO approval_requests
#                (admin_username, action_type, target_type, target_id, request_data, status, requested_at)
#                VALUES (%s, %s, %s, %s, %s, 'pending', %s)""",
#             (
#                 admin_username,
#                 action_type,
#                 target_type,
#                 target_id,
#                 json.dumps(request_data) if request_data else None,
#                 datetime.now(),
#             ),
#         )
#         request_id = cursor.lastrowid
#         conn.commit()
#         cursor.close()
#         logger.info(f"Approval request #{request_id} created by {admin_username}: {action_type}")
#         return request_id
#     except Exception as e:
#         logger.error(f"Failed to create approval request: {e}")
#         return None
#     finally:
#         if conn and conn.is_connected():
#             conn.close()


# def get_pending_approvals(limit: int = 100) -> List[Dict[str, Any]]:
#     """Get all pending approval requests (for superadmin review)."""
#     conn = None
#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor(dictionary=True)
#         # Increase sort buffer for this session to handle large request_data blobs
#         cursor.execute("SET SESSION sort_buffer_size = 8388608")
#         # Step 1: get sorted IDs without sorting large blob data
#         cursor.execute(
#             """SELECT id FROM approval_requests
#                WHERE status = 'pending'
#                ORDER BY requested_at DESC
#                LIMIT %s""",
#             (limit,),
#         )
#         id_rows = cursor.fetchall()
#         if not id_rows:
#             cursor.close()
#             return []
#         ids = [r["id"] for r in id_rows]
#         # Step 2: fetch full rows by primary key (no sort needed)
#         placeholders = ",".join(["%s"] * len(ids))
#         cursor.execute(
#             f"SELECT * FROM approval_requests WHERE id IN ({placeholders})",
#             ids,
#         )
#         rows = cursor.fetchall()
#         # Preserve the ORDER BY order from step 1
#         id_order = {rid: idx for idx, rid in enumerate(ids)}
#         rows.sort(key=lambda r: id_order.get(r["id"], 0))
#         results = []
#         for row in rows:
#             r = cast(Dict[str, Any], row)
#             data = json.loads(r["request_data"]) if r.get("request_data") else {}
#             # Strip the heavy image blob from list responses; it is only needed per-review
#             data.pop("fir_image_base64", None)

#             # Proactive duplicate warning for FIR submissions in pending queue.
#             if r.get("action_type") == "fir_ocr_submission":
#                 try:
#                     is_dup, dup_reason = _detect_duplicate_fir_submission(data, cursor)
#                     r["duplicate_candidate"] = bool(is_dup)
#                     r["duplicate_reason"] = dup_reason if is_dup else None
#                 except Exception as _dup_exc:
#                     logger.debug("duplicate check failed for request %s: %s", r.get("id"), _dup_exc)
#                     r["duplicate_candidate"] = False
#                     r["duplicate_reason"] = None

#             r["request_data"] = data
#             if r.get("requested_at") and hasattr(r["requested_at"], "isoformat"):
#                 r["requested_at"] = r["requested_at"].isoformat()
#             if r.get("reviewed_at") and hasattr(r["reviewed_at"], "isoformat"):
#                 r["reviewed_at"] = r["reviewed_at"].isoformat()
#             results.append(r)
#         cursor.close()
#         return results
#     except Exception as e:
#         logger.error(f"Failed to get pending approvals: {e}")
#         return []
#     finally:
#         if conn and conn.is_connected():
#             conn.close()


# def get_approval_requests_for_admin(admin_username: str, limit: int = 50) -> List[Dict[str, Any]]:
#     """Get approval requests submitted by a specific admin."""
#     conn = None
#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor(dictionary=True)
#         # Increase sort buffer for this session to handle large request_data blobs
#         cursor.execute("SET SESSION sort_buffer_size = 8388608")
#         # Step 1: get sorted IDs without sorting large blob data
#         cursor.execute(
#             """SELECT id FROM approval_requests
#                WHERE admin_username = %s
#                ORDER BY requested_at DESC
#                LIMIT %s""",
#             (admin_username, limit),
#         )
#         id_rows = cursor.fetchall()
#         if not id_rows:
#             cursor.close()
#             return []
#         ids = [r["id"] for r in id_rows]
#         # Step 2: fetch full rows by primary key (no sort needed)
#         placeholders = ",".join(["%s"] * len(ids))
#         cursor.execute(
#             f"SELECT * FROM approval_requests WHERE id IN ({placeholders})",
#             ids,
#         )
#         rows = cursor.fetchall()
#         cursor.close()
#         # Preserve the ORDER BY order from step 1
#         id_order = {rid: idx for idx, rid in enumerate(ids)}
#         rows.sort(key=lambda r: id_order.get(r["id"], 0))
#         results = []
#         for row in rows:
#             r = cast(Dict[str, Any], row)
#             data = json.loads(r["request_data"]) if r.get("request_data") else {}
#             # Strip the heavy image blob from list responses; it is only needed per-review
#             data.pop("fir_image_base64", None)
#             r["request_data"] = data
#             if r.get("requested_at") and hasattr(r["requested_at"], "isoformat"):
#                 r["requested_at"] = r["requested_at"].isoformat()
#             if r.get("reviewed_at") and hasattr(r["reviewed_at"], "isoformat"):
#                 r["reviewed_at"] = r["reviewed_at"].isoformat()
#             results.append(r)
#         return results
#     except Exception as e:
#         logger.error(f"Failed to get admin approval requests: {e}")
#         return []
#     finally:
#         if conn and conn.is_connected():
#             conn.close()


# def get_approval_request_by_id(request_id: int) -> Optional[Dict[str, Any]]:
#     """Get a single approval request by ID, including the full FIR image."""
#     conn = None
#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor(dictionary=True)
#         cursor.execute("SELECT * FROM approval_requests WHERE id = %s", (request_id,))
#         row = cast(Optional[Dict[str, Any]], cursor.fetchone())
#         cursor.close()
#         if not row:
#             return None
#         row["request_data"] = json.loads(row["request_data"]) if row.get("request_data") else {}
#         if row.get("requested_at") and hasattr(row["requested_at"], "isoformat"):
#             row["requested_at"] = row["requested_at"].isoformat()
#         if row.get("reviewed_at") and hasattr(row["reviewed_at"], "isoformat"):
#             row["reviewed_at"] = row["reviewed_at"].isoformat()
#         return row
#     except Exception as e:
#         logger.error(f"Failed to get approval request #{request_id}: {e}")
#         return None
#     finally:
#         if conn and conn.is_connected():
#             conn.close()


# def review_approval_request(
#     request_id: int,
#     reviewer_username: str,
#     approved: bool,
#     notes: Optional[str] = None,
#     edited_data: Optional[Dict[str, Any]] = None,
# ) -> Dict[str, Any]:
#     """
#     Approve or reject an approval request. If approved, execute the action.
#     edited_data: optional overrides from SuperAdmin (e.g. corrected FIR fields).
#     Returns a dict with status and message.
#     """
#     conn = None
#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor(dictionary=True)

#         # Get the request
#         cursor.execute("SELECT * FROM approval_requests WHERE id = %s", (request_id,))
#         req = cast(Optional[Dict[str, Any]], cursor.fetchone())
#         if not req:
#             return {"success": False, "message": "Approval request not found"}

#         if req["status"] != "pending":
#             return {"success": False, "message": f"Request already {req['status']}"}

#         # If SuperAdmin edited the data, merge edits into request_data before execution
#         if edited_data and approved:
#             original_data = json.loads(req["request_data"]) if req.get("request_data") else {}
#             # Merge edited fields into original data
#             if "extracted_fields" in edited_data:
#                 original_data["extracted_fields"] = {
#                     **original_data.get("extracted_fields", {}),
#                     **edited_data["extracted_fields"],
#                 }
#             if "extracted_sections" in edited_data:
#                 original_data["extracted_sections"] = edited_data["extracted_sections"]
#             req["request_data"] = json.dumps(original_data)
#             # Also update in DB so the audit trail has the edited version
#             cursor.execute(
#                 "UPDATE approval_requests SET request_data = %s WHERE id = %s",
#                 (req["request_data"], request_id),
#             )

#         # Auto-reject duplicate FIR submissions even if SuperAdmin clicks approve.
#         if approved and req.get("action_type") == "fir_ocr_submission":
#             req_data_obj = json.loads(req["request_data"]) if req.get("request_data") else {}
#             is_dup, dup_reason = _detect_duplicate_fir_submission(req_data_obj, cursor)
#             if is_dup:
#                 auto_note = f"Auto-rejected: {dup_reason}"
#                 merged_notes = f"{notes}\n{auto_note}" if notes else auto_note
#                 cursor.execute(
#                     """UPDATE approval_requests
#                        SET status = 'rejected', reviewed_by = %s, reviewed_at = %s, review_notes = %s
#                        WHERE id = %s""",
#                     (reviewer_username, datetime.now(), merged_notes, request_id),
#                 )
#                 conn.commit()
#                 cursor.close()
#                 return {
#                     "success": True,
#                     "message": "Request rejected: duplicate FIR incident already exists in database",
#                     "status": "rejected",
#                     "auto_rejected": True,
#                     "reason": dup_reason,
#                 }

#         new_status = "approved" if approved else "rejected"

#         cursor.execute(
#             """UPDATE approval_requests
#                SET status = %s, reviewed_by = %s, reviewed_at = %s, review_notes = %s
#                WHERE id = %s""",
#             (new_status, reviewer_username, datetime.now(), notes, request_id),
#         )
#         conn.commit()

#         result = {"success": True, "message": f"Request {new_status}", "status": new_status}

#         # If approved, execute the action
#         if approved:
#             exec_result = _execute_approved_action(req, cursor, conn)
#             result["execution"] = exec_result

#         cursor.close()
#         return result
#     except Exception as e:
#         logger.error(f"Failed to review approval request: {e}")
#         return {"success": False, "message": str(e)}
#     finally:
#         if conn and conn.is_connected():
#             conn.close()


# def _execute_approved_action(req: Dict[str, Any], cursor, conn) -> Dict[str, Any]:
#     """Execute an approved action."""
#     action = req["action_type"]
#     request_data = json.loads(req["request_data"]) if req.get("request_data") else {}

#     try:
#         if action == "delete_user":
#             user_id = req.get("target_id")
#             if user_id:
#                 cursor.execute("DELETE FROM users_info WHERE id = %s", (user_id,))
#                 conn.commit()
#                 return {"success": True, "message": f"User {user_id} deleted"}

#         elif action == "bulk_delete":
#             user_ids = request_data.get("user_ids", [])
#             if user_ids:
#                 fmt = ",".join(["%s"] * len(user_ids))
#                 cursor.execute(f"DELETE FROM users_info WHERE id IN ({fmt})", user_ids)
#                 conn.commit()
#                 return {"success": True, "message": f"{len(user_ids)} users deleted"}

#         elif action == "bulk_suspend":
#             user_ids = request_data.get("user_ids", [])
#             if user_ids:
#                 fmt = ",".join(["%s"] * len(user_ids))
#                 cursor.execute(
#                     f"UPDATE users_info SET role = 'inactive' WHERE id IN ({fmt})", user_ids
#                 )
#                 conn.commit()
#                 return {"success": True, "message": f"{len(user_ids)} users suspended"}

#         elif action in ("change_role_to_admin", "change_role_to_superadmin"):
#             user_id = req.get("target_id")
#             new_role = "admin" if action == "change_role_to_admin" else "superadmin"
#             if user_id:
#                 cursor.execute(
#                     "UPDATE users_info SET role = %s WHERE id = %s", (new_role, user_id)
#                 )
#                 conn.commit()
#                 return {"success": True, "message": f"User {user_id} role changed to {new_role}"}

#         elif action == "fir_ocr_submission":
#             return _execute_fir_submission(request_data, cursor, conn)

#         return {"success": False, "message": f"Unknown action: {action}"}

#     except Exception as e:
#         logger.error(f"Failed to execute approved action: {e}")
#         conn.rollback()
#         return {"success": False, "message": str(e)}


# def _predict_risk(area_english: str, crime_name: str, parsed_date: datetime) -> str:
#     """Predict risk level using the Random Forest model. Returns 'Low'/'Medium'/'High'."""
#     if not _rf_model or not _le_area or not _le_crime or not _le_risk:
#         return "Medium"  # fallback when model unavailable
#     try:
#         # Best-effort match against encoder classes
#         matched_area = _best_label_match(area_english, _le_area)
#         matched_crime = _best_label_match(crime_name, _le_crime)
#         if not matched_area or not matched_crime:
#             logger.warning(f"Risk prediction: no encoder match for area='{area_english}' or crime='{crime_name}' — defaulting to Medium")
#             return "Medium"
#         area_enc = int(_le_area.transform([matched_area])[0])
#         crime_enc = int(_le_crime.transform([matched_crime])[0])
#         year = int(parsed_date.year)
#         month = int(parsed_date.month)
#         day = int(parsed_date.day)
#         weekday = int(parsed_date.weekday())
#         day_of_year = int(parsed_date.timetuple().tm_yday)
#         is_weekend = 1 if weekday in (5, 6) else 0
#         features = pd.DataFrame(
#             [[area_enc, crime_enc, year, month, day, weekday, day_of_year, is_weekend]],
#             columns=["area_enc", "crime_type_enc", "year", "month", "day", "weekday", "day_of_year", "is_weekend"],
#         ).astype(int)
#         pred = _rf_model.predict(features)[0]
#         risk = _le_risk.inverse_transform([pred])[0]
#         return str(risk).capitalize()
#     except Exception as exc:
#         logger.error(f"Risk prediction failed: {exc}")
#         return "Medium"


# def _best_label_match(value: str, le) -> Optional[str]:
#     """Case-insensitive / substring match against a LabelEncoder's classes."""
#     if not value:
#         return None
#     v = value.strip().lower()
#     for cls in le.classes_:
#         if cls.lower() == v:
#             return cls
#     for cls in le.classes_:
#         if v in cls.lower() or cls.lower() in v:
#             return cls
#     return None


# def _risk_from_severity(crime_name: str) -> str:
#     """
#     Derive High/Medium/Low risk from the PPC crime name by fuzzy-matching
#     against severity_map.json (which covers all PPC offences).
#     No hardcoded category mapping — works with every real PPC section name.

#     severity weighted-score >= 7.5 → High
#     severity weighted-score >= 4.5 → Medium
#     otherwise                      → Low
#     """
#     if not _SEVERITY_MAP:
#         return "Medium"
#     n = crime_name.lower()
#     best_score: float = 0.0
#     for key, score in _SEVERITY_MAP.items():
#         # Strip punctuation from key, then check each meaningful word
#         key_words = [w for w in key.replace("(", "").replace(")", "")
#                      .replace("-", " ").split() if len(w) > 3]
#         if not key_words:
#             continue
#         matches = sum(1 for w in key_words if w in n)
#         if matches:
#             weighted = (matches / len(key_words)) * float(score)
#             if weighted > best_score:
#                 best_score = weighted
#     if best_score >= 7.5:
#         return "High"
#     if best_score >= 4.5:
#         return "Medium"
#     if best_score > 0:
#         return "Low"
#     return "Medium"  # default when no match found


# def _nearest_area_name(lat: float, lon: float, cursor) -> Optional[str]:
#     """
#     Return the English area name from the `areas` table closest (by
#     Haversine distance) to the given coordinates.  Returns None on failure.
#     """
#     try:
#         cursor.execute(
#             """
#             SELECT area_name,
#                    (6371 * acos(LEAST(1.0,
#                      cos(radians(%s)) * cos(radians(latitude))
#                      * cos(radians(longitude) - radians(%s))
#                      + sin(radians(%s)) * sin(radians(latitude))
#                    ))) AS dist_km
#             FROM areas
#             ORDER BY dist_km ASC
#             LIMIT 1
#             """,
#             (lat, lon, lat),
#         )
#         row = cursor.fetchone()
#         if row:
#             return row["area_name"] if isinstance(row, dict) else row[0]
#     except Exception as exc:
#         logger.warning(f"Nearest-area lookup failed: {exc}")
#     return None


# def _resolve_plot_area(area_urdu_raw: str, area_translit: str, nearest_area: Optional[str]) -> str:
#     """
#     Resolve canonical `crimes.area` used for map plotting.
#     Prefer explicit locality signals from FIR text for known edge-cases.
#     """
#     hint = f"{area_urdu_raw or ''} {area_translit or ''}".lower()

#     _dha_ur = re.search(r"ڈی\s*ایچ\s*اے\s*فیز\s*(\d+)", area_urdu_raw or "")
#     if _dha_ur:
#         phase_num = int(_dha_ur.group(1))
#         if 1 <= phase_num <= 9:
#             return f"DHA Phase {phase_num}"

#     _dha_en = re.search(r"dha\s*phase\s*(\d+)", hint)
#     if _dha_en:
#         phase_num = int(_dha_en.group(1))
#         if 1 <= phase_num <= 9:
#             return f"DHA Phase {phase_num}"

#     if "بادامی باغ" in (area_urdu_raw or "") or "badami bagh" in hint:
#         return "Badami Bagh, Lahore"

#     if "داتا دربار" in (area_urdu_raw or "") or "data darbar" in hint:
#         return "Data Darbar, Lahore"

#     if "انارکلی" in (area_urdu_raw or "") or "anarkali" in hint:
#         return "Anarkali, Lahore"

#     if "لوہاری گیٹ" in (area_urdu_raw or "") or "lohari gate" in hint:
#         return "Lohari Gate, Lahore"

#     if "دہلی گیٹ" in (area_urdu_raw or "") or "delhi gate" in hint:
#         return "Delhi Gate, Lahore"

#     if "بھاٹی گیٹ" in (area_urdu_raw or "") or "bhati gate" in hint:
#         return "Bhati Gate, Lahore"

#     if "مزنگ روڈ" in (area_urdu_raw or "") or "mazang road" in hint or "santanagar chowk" in hint:
#         return "Mazang, Lahore"

#     if "پی سی ایس" in (area_urdu_raw or "") or "pcsir" in hint:
#         return "PCSIR Housing Scheme"

#     if "راوی روڈ، راوی روڈ" in (area_urdu_raw or "") or "ravi road ravi road" in hint or hint.strip() == "ravi road":
#         return "Ravi Town, Lahore"

#     if "کینٹ صدر بازار" in (area_urdu_raw or "") or ("cantt saddar bazaar" in hint and "saddar bazaar road" in hint):
#         return "Cantt"

#     if "فوجی کالونی" in (area_urdu_raw or "") and "کینٹ" in (area_urdu_raw or ""):
#         return "Cantt"

#     if "سرفرار روڈ" in (area_urdu_raw or "") and "کینٹ" in (area_urdu_raw or "") and ("گجومتہ" in (area_urdu_raw or "") or "gajumatta" in hint):
#         return "Cantt"

#     if "لال کرتی" in (area_urdu_raw or "") and "ٹھوکر نیاز بیگ" in (area_urdu_raw or ""):
#         return "Lal Kurti, Cantt"

#     if ("پی آئی اے سوسائٹی" in (area_urdu_raw or "") or "پی آئی اے سوسائٹی" in (area_urdu_raw or "")) and ("کینٹ روڈ" in (area_urdu_raw or "") or "cantt road" in hint):
#         return "PIA Housing Society"

#     if "فورٹریس اسٹیڈیم ایریا" in (area_urdu_raw or "") and "سب بلاک" in (area_urdu_raw or ""):
#         return "Cantt"

#     if "چوبرجی" in (area_urdu_raw or "") or "chuburji" in hint:
#         return "Chuburji, Lahore"

#     if "نہر کنار روڈ" in (area_urdu_raw or "") or "canal road" in hint or "nehar kinara" in hint:
#         if "لال کرتی" in (area_urdu_raw or "") and "کینٹ" in (area_urdu_raw or ""):
#             return "Cantt"
#         return "Canal Road, Lahore"

#     if "جیل روڈ، جیل روڈ" in (area_urdu_raw or "") or hint.strip() == "jail road" or "jail road jail road" in hint:
#         return "Ichhra, Lahore"

#     if "ٹاؤن شپ" in (area_urdu_raw or "") or "township madina chowk" in hint or "jamia ashrafia" in hint:
#         return "Township"

#     if "شالامار باغ" in (area_urdu_raw or "") or ("shalimar bagh" in hint and "gt road" in hint):
#         return "Shalimar Bagh / GT Road"

#     if "شاہدرہ ٹاؤن" in (area_urdu_raw or "") or ("shahdara town" in hint and "ravi road" in hint):
#         return "Shahdara"

#     if "علامہ اقبال ٹاؤن" in (area_urdu_raw or "") and "karim block" in hint:
#         return "Allama Iqbal Town"

#     if "سمن آباد" in (area_urdu_raw or "") and "مین بلیوارڈ" in (area_urdu_raw or ""):
#         return "Samanabad"

#     if "قینچی" in (area_urdu_raw or "") or "qainchi" in hint or "amer sidhu" in hint:
#         return "Qainchi Amer Sidhu"

#     if "کاماہاں انٹرچینج" in (area_urdu_raw or "") or "kamahan interchange" in hint:
#         return "Kamahan Interchange"

#     if "بحریہ آرچرڈ" in (area_urdu_raw or "") or "bahria orchard" in hint:
#         return "Bahria Orchard, Lahore"

#     if "ایڈن آباد" in (area_urdu_raw or "") or "eden abad" in hint or "شاہ پور کانجراں" in (area_urdu_raw or "") or "shahpur kanjran" in hint:
#         return "Raiwind Road, Lahore"

#     if "پی آئی اے سوسائٹی" in (area_urdu_raw or "") or "پی آئی اے سوسائٹی" in (area_urdu_raw or "") or "pia society" in hint:
#         return "PIA Housing Society"

#     if "الخضریا ہاؤسنگ" in (area_urdu_raw or "") and ("والٹن روڈ" in (area_urdu_raw or "") or "ٹھوکر نیاز بیگ" in (area_urdu_raw or "") or "روٹی تندور" in (area_urdu_raw or "") or "walton road" in hint or "thokar niaz baig" in hint or "roti tandoor" in hint):
#         return "Cantt"

#     if "کچھہری روڈ" in (area_urdu_raw or "") or "kutchery road" in hint:
#         return "Kutchery Road, Lahore"

#     if "ٹھوکر نیاز بیگ" in (area_urdu_raw or "") or "thokar niaz baig" in hint:
#         return "Thokar Niaz Baig"

#     # Guardrail: when geocoding drifts to Gulshan-e-Ravi, remap known out-of-zone markers.
#     if (nearest_area or "").lower() == "gulshan-e-ravi":
#         if "شیخ زید" in (area_urdu_raw or "") or "خیابانِ جناح" in (area_urdu_raw or "") or "sheikh zayed" in hint or "khayaban-e-jinnah" in hint:
#             return "Canal Road, Lahore"
#         if "والٹن روڈ" in (area_urdu_raw or "") or "walton road" in hint:
#             return "Cantt"
#         if "چونیاں روڈ" in (area_urdu_raw or "") or "chunian road" in hint:
#             return "Raiwind Road, Lahore"
#         if "روٹی تندور" in (area_urdu_raw or "") or "roti tandoor" in hint:
#             return "Cantt"

#     if "بحریہ ٹاؤن" in (area_urdu_raw or "") or ("bahria town" in hint and "sector" in hint):
#         return "Bahria Town, Lahore"

#     if "لی ڈی اے سٹی" in (area_urdu_raw or "") or "ایل ڈی اے سٹی" in (area_urdu_raw or "") or "lda city" in hint:
#         return "LDA City"

#     if "واپڈا ٹاؤن" in (area_urdu_raw or "") or "wapda town" in hint:
#         return "Wapda Town"

#     _dha = re.search(r"dha\s*phase\s*(\d+)", hint)
#     if _dha:
#         return f"DHA Phase {_dha.group(1)}"

#     _askari = re.search(r"askari\s*(\d+)", hint)
#     if _askari:
#         return f"Askari {_askari.group(1)}"

#     if "آسکاری" in (area_urdu_raw or "") or "askari" in hint:
#         return "Askari"

#     if "شاد باغ" in (area_urdu_raw or "") or "shad bagh" in hint or "shadbagh" in hint:
#         return "Shad Bagh, Lahore"

#     # Valencia Town — must be Defence/Raiwind/Asooki/Awan/Gajumatta context, NOT MM Alam/Walton/Samnabad/Cantt/GT/Sheikh Zayed
#     if "والینشیا ٹاؤن" in (area_urdu_raw or "") or "valencia town" in hint:
#         if "defence road" in hint or "ڈیفنس روڈ" in (area_urdu_raw or "") or "asooki" in hint or "آسوکی" in (area_urdu_raw or "") or "awan road" in hint or "اعوان روڈ" in (area_urdu_raw or "") or "gajumatta" in hint or "multan road" in hint or "ملتان روڈ" in (area_urdu_raw or ""):
#             return "Valencia Housing Society"
#         if "mm alam" in hint or "ایم ایم عالم" in (area_urdu_raw or "") or "walton" in hint or "والٹن" in (area_urdu_raw or "") or "samnabad" in hint or "سمن آباد" in (area_urdu_raw or "") or "cantt road" in hint or "gt road" in hint or "sheikh zayed" in hint or "شیخ زید" in (area_urdu_raw or "") or "mall road" in hint:
#             return nearest_area or "Lahore"

#     # Lake City — only Sectors M1-M8 with Defence/Raiwind/Asooki, NOT mixed societies and NOT wrong roads
#     if "لیک سٹی" in (area_urdu_raw or "") or "lake city sector m" in hint:
#         if "defence road" in hint or "ڈیفنس روڈ" in (area_urdu_raw or "") or "raiwind road" in hint or "رائیونڈ روڈ" in (area_urdu_raw or "") or "asooki" in hint or "آسوکی" in (area_urdu_raw or "") or "revenue road" in hint or "ریونیو روڈ" in (area_urdu_raw or "") or "waris road" in hint:
#             return "Lake City"
#         if "بحریہ" in (area_urdu_raw or "") or "bahria" in hint or "پی آئی اے سوسائٹی" in (area_urdu_raw or "") or "pia" in hint or "ایڈن آباد" in (area_urdu_raw or "") or "eden abad" in hint or "الخضریا" in (area_urdu_raw or "") or "khadriya" in hint:
#             return nearest_area or "Lahore"
#         if "mm alam" in hint or "ایم ایم عالم" in (area_urdu_raw or "") or "walton" in hint or "والٹن" in (area_urdu_raw or "") or "samnabad" in hint or "سمن آباد" in (area_urdu_raw or "") or "cantt road" in hint or "barki" in hint or "برکی" in (area_urdu_raw or "") or "sagian" in hint or "niazi" in hint:
#             return nearest_area or "Lahore"

#     return nearest_area or "Lahore"


# def _parse_fir_date_to_iso(raw_date: str) -> str:
#     """Parse common FIR date formats and return YYYY-MM-DD (today if unknown)."""
#     _DATE_FORMATS = [
#         "%Y-%m-%d",
#         "%d-%m-%Y",
#         "%d/%m/%Y",
#         "%m/%d/%Y",
#         "%d-%m-%y",
#         "%d/%m/%y",
#         "%Y/%m/%d",
#     ]
#     for _fmt in _DATE_FORMATS:
#         try:
#             return datetime.strptime(str(raw_date).strip(), _fmt).strftime("%Y-%m-%d")
#         except ValueError:
#             continue
#     return datetime.now().strftime("%Y-%m-%d")


# def _detect_duplicate_fir_submission(request_data: Dict[str, Any], cursor) -> Tuple[bool, str]:
#     """
#     Detect whether an incoming FIR submission is already present in `crimes`.

#     Matching strategy (two-pass):
#       Pass 1 — strict: same date + same time + coordinates within 0.002° (~220 m)
#       Pass 2 — loose : same date + coordinates within 0.005° (~550 m), ignoring time
#                        (handles OCR time-extraction variance and CSV-imported records
#                         that have no area_urdu / slightly different geocoded coords)

#     Area-text columns (area_urdu / area_translit) are intentionally excluded from
#     the WHERE clause because:
#       - CSV-imported records often have area_urdu = NULL
#       - OCR may return the area in English on one upload and Urdu on the next
#     """
#     fields = request_data.get("extracted_fields", {}) or {}
#     location = fields.get("location", {}) or {}
#     sections = request_data.get("extracted_sections", []) or []

#     raw_date = fields.get("crime_date") or datetime.now().strftime("%Y-%m-%d")
#     crime_date = _parse_fir_date_to_iso(str(raw_date))
#     crime_time = (fields.get("crime_time") or None)
#     if crime_time:
#         crime_time = str(crime_time).strip() or None

#     latitude = location.get("latitude")
#     longitude = location.get("longitude")
#     if latitude is None or longitude is None:
#         return False, "Coordinates missing — duplicate check skipped"

#     expected_crime_types = set()
#     for sec in sections:
#         cname, _lt = get_crime_name(str(sec))
#         expected_crime_types.add(cname)
#     if not expected_crime_types:
#         return False, "No sections available for duplicate comparison"

#     lat_f = float(latitude)
#     lon_f = float(longitude)

#     # ── Pass 1: strict — date + time + tight coordinate window ─────────────
#     strict_query = """
#         SELECT crime_type
#         FROM crimes
#         WHERE crime_date = %s
#           AND ( (crime_time = %s) OR (%s IS NULL AND crime_time IS NULL) )
#           AND ABS(latitude  - %s) <= 0.002
#           AND ABS(longitude - %s) <= 0.002
#     """
#     cursor.execute(strict_query, (crime_date, crime_time, crime_time, lat_f, lon_f))
#     rows = cursor.fetchall() or []

#     # ── Pass 2: loose — date only + broader coordinate window (skip time) ──
#     if not rows:
#         loose_query = """
#             SELECT crime_type
#             FROM crimes
#             WHERE crime_date = %s
#               AND ABS(latitude  - %s) <= 0.005
#               AND ABS(longitude - %s) <= 0.005
#         """
#         cursor.execute(loose_query, (crime_date, lat_f, lon_f))
#         rows = cursor.fetchall() or []

#     if not rows:
#         return False, "No existing rows matched date/location key"

#     existing_types = {str(r["crime_type"]) for r in rows if r.get("crime_type")}
#     if expected_crime_types.issubset(existing_types):
#         return (
#             True,
#             f"Duplicate FIR detected for {crime_date} {crime_time or ''} at ({lat_f:.6f}, {lon_f:.6f}); all section crime types already exist in the database",
#         )

#     return False, "Partial overlap only — not treated as duplicate"


# def _execute_fir_submission(request_data: Dict[str, Any], cursor, conn) -> Dict[str, Any]:
#     """
#     Insert FIR OCR extracted data into the crimes table.
#     Creates one row per PPC section with:
#       - area stored as "اردو (English)"
#       - crime_type = English crime name from PPC mapping
#       - risk_level auto-predicted by ML model
#     """
#     try:
#         fields = request_data.get("extracted_fields", {})
#         raw_date = fields.get("crime_date") or datetime.now().strftime("%Y-%m-%d")

#         location = fields.get("location") or {}
#         sections = request_data.get("extracted_sections", [])

#         # ── Coordinates ─────────────────────────────────────────────────
#         latitude  = location.get("latitude")
#         longitude = location.get("longitude")

#         # Final fallback: Lahore city-centre
#         if not latitude or not longitude:
#             latitude, longitude = 31.5204, 74.3587

#         # ── Preserve raw Urdu area name from OCR for bilingual display ────
#         area_urdu_raw = (location.get("thana_name") or fields.get("crime_area") or "").strip()

#         # ── Extract crime_time from FIR OCR fields ────────────────────────
#         crime_time = fields.get("crime_time") or None
#         # Normalise: strip any surrounding whitespace
#         if crime_time:
#             crime_time = str(crime_time).strip() or None

#         # ── Transliterate Urdu area → Roman for display ───────────────────
#         area_translit = _azure_transliterate_single(area_urdu_raw) if area_urdu_raw else None

#         nearest_mapped_area = _nearest_area_name(float(latitude), float(longitude), cursor)
#         area_display = _resolve_plot_area(area_urdu_raw, area_translit or "", nearest_mapped_area)

#         logger.info(
#             f"FIR Processing: Lat={latitude}, Lon={longitude}, FIR Area='{area_translit}', "
#             f"Nearest Mapped Area='{nearest_mapped_area}', Saved Plot Area='{area_display}'"
#         )

#         # ── Parse date — try multiple common FIR date formats ───────────
#         _DATE_FORMATS = [
#             "%Y-%m-%d",   # ISO:        2025-05-24
#             "%d-%m-%Y",   # Pakistani:  24-05-2025
#             "%d/%m/%Y",   # slash:      24/05/2025
#             "%m/%d/%Y",   # US:         05/24/2025
#             "%d-%m-%y",   # 2-digit yr: 24-05-25
#             "%d/%m/%y",
#             "%Y/%m/%d",
#         ]
#         parsed_date = None
#         for _fmt in _DATE_FORMATS:
#             try:
#                 parsed_date = datetime.strptime(str(raw_date).strip(), _fmt)
#                 raw_date = parsed_date.strftime("%Y-%m-%d")
#                 break
#             except ValueError:
#                 continue
#         if parsed_date is None:
#             logger.warning(f"FIR date '{raw_date}' could not be parsed — defaulting to today")
#             parsed_date = datetime.now()
#             raw_date = parsed_date.strftime("%Y-%m-%d")

#         # ── Ensure we have at least one section to insert ───────────────
#         if not sections:
#             sections = ["Unknown"]

#         created_ids: List[int] = []

#         for section in sections:
#             crime_name, law_type = get_crime_name(str(section))

#             # Derive risk directly from the PPC crime name via severity_map
#             # (no category mapping needed — works with every real PPC section)
#             risk_level = _risk_from_severity(crime_name)

#             # Store the full readable PPC crime name in the crimes table
#             crime_type_label = crime_name

#             description = f"FIR OCR extraction — §{section} {law_type}: {crime_name}"

#             cursor.execute(
#                 """INSERT INTO crimes
#                    (crime_date, crime_time, area, area_urdu, area_translit,
#                     crime_type, latitude, longitude,
#                     risk_level, source, status, description, created_at)
#                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
#                 (
#                     raw_date,
#                     crime_time,
#                     area_display,
#                     area_urdu_raw or None,
#                     area_translit or None,
#                     crime_type_label,
#                     latitude,
#                     longitude,
#                     risk_level,
#                     "admin",
#                     "verified",
#                     description,
#                     datetime.now(),
#                 ),
#             )
#             created_ids.append(cursor.lastrowid)
#             logger.info(
#                 f"Crime record #{cursor.lastrowid} created: §{section} {law_type} "
#                 f"→ {crime_type_label}, area={area_display}, risk={risk_level}"
#             )

#         conn.commit()
#         msg = f"{len(created_ids)} crime record(s) created from FIR (IDs: {created_ids})"
#         logger.info(msg)

#         # ── IMMEDIATE ALERT TRIGGER: Notify users of these new verified incidents ──
#         try:
#             from app.routes.alerts import dispatch_new_incident_alerts
#             import asyncio
#             import threading

#             def _dispatch_task(crime_pkg):
#                 """Run the async dispatch in a separate thread so we don't block the review process"""
#                 try:
#                     asyncio.run(dispatch_new_incident_alerts(crime_pkg))
#                 except Exception as _de:
#                     logger.error(f"Background FIR alert dispatch failed: {_de}")

#             # Prepare data package for each crime
#             for i, cid in enumerate(created_ids):
#                 # Using current local mapping for area/crime_type
#                 # If there are multiple sections, they all share basic loc info
#                 crime_pkg = {
#                     "id": cid,
#                     "area": area_display,
#                     "area_translit": area_translit or area_display,
#                     "crime_type": sections[i] if i < len(sections) else "Incident",
#                     "latitude": float(latitude),
#                     "longitude": float(longitude),
#                     "risk_level": _risk_from_severity(sections[i]) if i < len(sections) else "Medium",
#                     "crime_date": raw_date
#                 }
#                 # Spawn a thread — this is a safe way to run async in a sync context without 
#                 # a persistent background_tasks object available from FastAPI router.
#                 threading.Thread(target=_dispatch_task, args=(crime_pkg,), daemon=True).start()
            
#             logger.info(f"🚀 Immediate alert dispatch threads launched for {len(created_ids)} FIR incidents")
#         except Exception as alert_err:
#             logger.error(f"Failed to launch immediate alerts for FIR approval: {alert_err}")

#         # Notify auto-retrain guard for each new record — runs in background,
#         # schedules model retrain when new areas/crime types accumulate
#         try:
#             from app.crime_risk_model.utils.auto_retrain import notify_new_record as _ar_notify
#             for section in sections:
#                 crime_name_for_notify, _ = get_crime_name(str(section))
#                 _ar_notify(area_display, crime_name_for_notify)
#         except Exception as _arex:
#             logger.debug("auto_retrain notify failed (non-fatal): %s", _arex)

#         return {"success": True, "message": msg, "crime_ids": created_ids}

#     except Exception as e:
#         logger.error(f"Failed to execute FIR submission: {e}")
#         conn.rollback()
#         return {"success": False, "message": str(e)}


# def is_sensitive_action(action_type: str) -> bool:
#     """Check if an action requires superadmin approval."""
#     return action_type in SENSITIVE_ACTIONS


# def get_required_permission(action_type: str) -> Optional[str]:
#     """Get the permission required for a given action type."""
#     return ACTION_PERMISSIONS.get(action_type)



"""
Approval Workflow Module
Admin sensitive actions require superadmin approval before execution.
"""

import json
import logging
import os
import re
import unicodedata
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple, cast

import requests

import joblib
import pandas as pd

# Severity map for PPC-based risk derivation (no hardcoded category mapping)
_SEVERITY_MAP: Dict[str, float] = {}
try:
    _sev_path = os.path.join(
        os.path.dirname(__file__),
        "crime_risk_model", "config", "severity_map.json"
    )
    with open(_sev_path, "r", encoding="utf-8") as _sf:
        _SEVERITY_MAP = json.load(_sf)
except Exception as _se:
    pass  # risk will default to Medium

from app.core.database import get_db_connection
from app.core.config import MODEL_DIR
from app.ocr.ppc_sections import get_crime_name
from app.ocr.fir_specialized_ocr import URDU_TO_ENGLISH_THANA

logger = logging.getLogger(__name__)

# --------------- ML model & encoders (for risk prediction) ---------------
try:
    _rf_model = joblib.load(os.path.join(MODEL_DIR, "random_forest_model.joblib"))
    _le_area = joblib.load(os.path.join(MODEL_DIR, "label_encoder_area.joblib"))
    _le_crime = joblib.load(os.path.join(MODEL_DIR, "label_encoder_crime.joblib"))
    _le_risk = joblib.load(os.path.join(MODEL_DIR, "label_encoder_risk.joblib"))
except Exception as _e:
    logger.error(f"Approval-workflow: could not load ML model/encoders: {_e}")
    _rf_model = _le_area = _le_crime = _le_risk = None

# Urdu → English area mapping (combines thana dict + common geocode locations)
_URDU_EN_MAP: Dict[str, str] = {**URDU_TO_ENGLISH_THANA}
# Add extra mappings that live inside the geocode function but are commonly needed:
_EXTRA_EN = {
    "بھاٹی گیٹ": "Bhati Gate", "لوہاری گیٹ": "Lohari Gate",
    "دہلی گیٹ": "Delhi Gate", "سمن آباد": "Samanabad",
    "سبزہ زار": "Sabzazar", "چوبرجی": "Chauburji",
    "لکشمی چوک": "Lakshmi Chowk", "نشتر ٹاؤن": "Nishtar Town",
    "باغبانپورہ": "Baghbanpura", "ہربنس پورہ": "Harbanspura",
    "غڑی شاہو": "Garhi Shahu", "شاد باغ مارکیٹ": "Shadbagh Market",
    "شادمان": "Shadman", "ڈی ایچ اے": "DHA Lahore",
    "بحریہ ٹاؤن": "Bahria Town Lahore",
}
_URDU_EN_MAP.update(_EXTRA_EN)

# ── Transliteration: MyMemory API (free, no account, no card, forever) ───────
# https://mymemory.translated.net — 5,000 chars/day free, no key needed.
# Falls back to keyword substitution if the API call fails.
_MYMEMORY_URL = "https://api.mymemory.translated.net/get"
_URDU_CHARS_RE = re.compile(r"[\u0600-\u06FF\u0750-\u077F\uFB50-\uFDFF\uFE70-\uFEFF]")

# Keyword map used as fast pre-pass and fallback
_KW_MAP = [
    ("گلشنِ راوی، جی بلاک روڈ", "Gulshan-e-Ravi G Block Road"),
    ("الخضریا ہاؤسنگ بلاک F، مین والٹن روڈ", "Al-Khadriya Housing Block F, Main Walton Road"),
    ("ایڈن آباد بلاک G، شاہ پور کانجراں روڈ", "Eden Abad Block G, Shahpur Kanjran Road"),
    ("ایڈن آباد بلاک E، کچھہری روڈ", "Eden Abad Block E, Kutchery Road"),
    ("ایڈن آباد بلاک F، چونیاں روڈ", "Eden Abad Block F, Chunian Road"),
    ("پی آئی اے سوسائٹی بلاک G، جی ٹی روڈ", "PIA Society Block G, GT Road"),
    ("پی آئی اے سوسائٹی بلاک E، مین والٹن روڈ", "PIA Society Block E, Main Walton Road"),
    ("پی آئی اے سوسائٹی بلاک F، چونیاں روڈ", "PIA Society Block F, Chunian Road"),
    ("الخضریا ہاؤسنگ بلاک G، ٹھوکر نیاز بیگ انٹرچینج", "Al-Khadriya Housing Block G, Thokar Niaz Baig Interchange"),
    ("الخضریا ہاؤسنگ بلاک E، روٹی تندور روڈ", "Al-Khadriya Housing Block E, Roti Tandoor Road"),
    ("بحریہ آرچرڈ فیز 1 بلاک F، شیخ زید روڈ", "Bahria Orchard Phase 1 Block F, Sheikh Zayed Road"),
    ("بحریہ آرچرڈ فیز 2 بلاک F، رائیونڈ روڈ", "Bahria Orchard Phase 2 Block F, Raiwind Road"),
    ("بحریہ آرچرڈ فیز 2 بلاک G، خیا ب انِ جناح", "Bahria Orchard Phase 2 Block G, Khayaban-e-Jinnah"),
    ("بحریہ آرچرڈ فیز 1 بلاک G، آسوکی روڈ", "Bahria Orchard Phase 1 Block G, Asooki Road"),
    ("بحریہ آرچرڈ فیز 3 بلاک G، گجو متہ روڈ", "Bahria Orchard Phase 3 Block G, Gajumatta Road"),
    ("بحریہ آرچرڈ فیز 3 بلاک F، آسوکی روڈ", "Bahria Orchard Phase 3 Block F, Asooki Road"),
    ("راوی روڈ، راوی روڈ", "Ravi Road"),
    ("کینٹ صدر بازار، صدر بازار روڈ", "Cantt Saddar Bazaar, Saddar Bazaar Road"),
    ("بحریہ آرچرڈ فیز 4 بلاک H، کینٹ روڈ", "Bahria Orchard Phase 4 Block H, Cantt Road"),
    ("الخضریا ہاؤسنگ بلاک H، کینٹ روڈ", "Al-Khadriya Housing Block H, Cantt Road"),
    ("لال کرتی کینٹ، ٹھوکر نیاز بیگ انٹرچینج", "Lal Kurti (Cantt), Thokar Niaz Baig Interchange"),
    ("سرفرار روڈ کینٹ، گجومتہ انٹرچینج", "Sarfaraz Road Cantt, Gajumatta Interchange"),
    ("فوجی کالونی کینٹ، نجات روڈ", "Fauji Colony Cantt, Nijat Road"),
    ("پی آئی اے سوسائٹی بلاک H سب بلاک P، کینٹ روڈ", "PIA Society Block H Sub-Block P, Cantt Road"),
    ("فورٹریس اسٹیڈیم ایریا سب بلاک K، کینٹ روڈ", "Fortress Stadium Area Sub-Block K, Cantt"),
    ("چوبرجی انڈر پاس سب بلاک K، کینٹ روڈ", "Chuburji Underpass Sub-Block K, Cantt Road"),
    ("لال کرتی کینٹ سب بلاک J، نہر کنار روڈ", "Lal Kurti Cantt Sub-Block J, Canal Road (Nehar Kinara Road)"),
    ("سرفرار روڈ کینٹ سب بلاک D، شاہراہِ پاکستان", "Sarfaraz Road Cantt Sub-Block D, Shahrah-e-Pakistan"),
    ("جیل روڈ، جیل روڈ", "Jail Road"),
    ("ٹاؤن شپ، مدینہ چوک / جامعہ اشرفیہ روڈ", "Township Madina Chowk / Jamia Ashrafia Road"),
    ("شالامار باغ، جی ٹی روڈ", "Shalimar Bagh GT Road"),
    ("شاہدرہ ٹاؤن، راوی روڈ / جی ٹی روڈ", "Shahdara Town Ravi Road / GT Road"),
    ("علامہ اقبال ٹاؤن (کری بلاک مارکیٹ)، وریسٹر روڈ/مولانا شوکت علی؟", "Allama Iqbal Town Karim Block Market / Wahdat Road / Maulana Shaukat Ali Road"),
    ("سمن آباد، سمن آباد مین بلیوارڈ", "Samanabad Main Boulevard"),
    ("فیروزپور روڈ (قینچی)، قینچی امرسدھو", "Ferozepur Road (Qainchi), Qainchi Amer Sidhu"),
    ("کاماہاں انٹرچینج سب بلاک A، فیروزپور روڈ", "Kamahan Interchange Sub-Block A, Ferozepur Road"),
    ("لی ڈی اے سٹی سیکٹر 2 بلاک H سب بلاک P، فیروزپور روڈ", "LDA City Sector 2 Block H Sub-Block P, Ferozepur Road"),
    ("گدا فی اسٹیڈیم، فروزپور روڈ / قذافی", "Gaddafi Stadium / Ferozepur Road"),
    ("قذافی اسٹیڈیم، فروزپور روڈ / قذافی", "Gaddafi Stadium / Ferozepur Road"),
    ("ریلوے اسٹیشن لاہور، نزد امیگریشن/مکلوڈ روڈ", "Lahore Railway Station / Near Immigration / Macleod Road"),
    ("برکی روڈ / بیدیان، برکی روڈ", "Barkee Road / Beedian"),
    ("فورٹریس اسٹیڈیم ایریا، لیاقت علی خان روڈ", "Fortress Stadium Area / Liaqat Ali Khan Road"),
    ("فورٹریس اسٹیڈیم ایریا سب بلاک P، چونیاں روڈ", "Fortress Stadium Area Sub-Block P / Choonian Road"),
    ("فورٹریس اسٹیڈیم ایریا سب بلاک I، رائیونڈ روڈ", "Fortress Stadium Area Sub-Block I / Raiwind Road"),
    ("نواں کوٹ بائیک پوائنٹ، بیدیاں روڈ", "Nawan Kot Bike Point / Badian Road"),
    ("شادمـان مارکیٹ، شادمـان روڈ", "Shadman Market / Shadman Road"),
    ("شامدان مارکیٹ، شادمان روڈ", "Shadman Market / Shadman Road"),
    ("شاد باغ مارکیٹ", "Shad Bagh Market"),
    ("بادامی باغ", "Badami Bagh"),
    ("ماڈل ٹاؤن پارک، ایف بلاک روڈ", "Model Town Park / F Block Road"),
    ("فیصل ٹاؤن، آربی بلاک روڈ", "Faisal Town / R Block Road"),
    ("بحریہ آرچرڈ فیز 3 بلاک E، کینال روڈ", "Bahria Orchard Phase 3, Block E / Canal Road"),
    ("بحریہ آرچرڈ فیز 1 بلاک E، ریونیو روڈ", "Bahria Orchard Phase 1, Block E / Revenue Road"),
    ("عامر روڈ (اسٹریٹ 9، تاج گزی پارک کے سامنے)، شاد باغ", "Amir Road (Street 9, Opposite Taj Ghazi Park), Shad Bagh"),
    ("سنت نگر چوک، مزنگ روڈ، گورنمنٹ گرلز ہائی اسکول کے سامنے", "Santanagar Chowk Mazang Road (Opposite Government Girls High School)"),
    ("دہلی گیٹ، دہلی گیٹ روڈ", "Delhi Gate Road"),
    ("سبزہ زار، سبزہ زار مین بلیوارڈ", "Sabzazar Main Boulevard"),
    # Valencia Town — only valid if Defence/Asooki/Awan/Raiwind/Gajumatta
    ("والینشیا ٹاؤن بلاک D، آسوکی روڈ", "Valencia Town Block D, Asooki Road"),
    ("والینشیا ٹاؤن بلاک K، اعوان روڈ", "Valencia Town Block K, Awan Road"),
    ("والینشیا ٹاؤن بلاک B، ڈیفنس روڈ", "Valencia Town Block B, Defence Road"),
    ("والینشیا ٹاؤن بلاک J، ڈیفنس روڈ", "Valencia Town Block J, Defence Road"),
    ("والینشیا ٹاؤن بلاک M، ملتان روڈ", "Valencia Town Block M, Multan Road"),
    ("والینشیا ٹاؤن بلاک A، گجومتہ انٹرچینج", "Valencia Town Block A, Gajumatta Interchange"),
    # Lake City — only valid if Sectors M1-M8 with Defence/Raiwind/Asooki
    ("لیک سٹی سیکٹر M1 سب بلاک T، آسوکی روڈ", "Lake City Sector M1 Sub-Block T, Asooski Road"),
    ("لیک سٹی سیکٹر M3 سب بلاک R، ڈیفنس روڈ", "Lake City Sector M3 Sub-Block R, Defence Road"),
    ("لیک سٹی سیکٹر M5 سب بلاک R، ڈیفنس روڈ", "Lake City Sector M5 Sub-Block R, Defence Road"),
    ("لیک سٹی سیکٹر M5 سب بلاک V، ریونیو روڈ", "Lake City Sector M5 Sub-Block V, Revenue Road"),
    ("لیک سٹی سیکٹر M3، ریونیو روڈ", "Lake City Sector M3, Revenue Road"),
    # Disambiguate misassigned societies
    ("پی آئی اے سوسائٹی بلاک B، شیخ زید روڈ", "PIA Society Block B, Sheikh Zayed Road"),
    ("بحریہ آرچرڈ فیز 1 بلاک B، ڈیفنس روڈ", "Bahria Orchard Phase 1 Block B, Defence Road"),
    ("بحریہ آرچرڈ فیز 2 بلاک B، ڈیفنس روڈ", "Bahria Orchard Phase 2 Block B, Defence Road"),
    ("بحریہ آرچرڈ فیز 3 بلاک B، اعوان روڈ", "Bahria Orchard Phase 3 Block B, Awan Road"),
    ("الخضریا ہاؤسنگ بلاک B، رائیونڈ روڈ", "Al-Khadriya Housing Block B, Raiwind Road"),
    ("ایڈن آباد بلاک B، وارث روڈ", "Eden Abad Block B, Waris Road"),
    ("پی سی ایس آئی آر", "PCSIR Housing Scheme"),
    ("ڈی ایچ اے", "DHA"), ("بحریہ ٹاؤن", "Bahria Town"),
    ("جوہر ٹاؤن", "Johar Town"), ("ماڈل ٹاؤن", "Model Town"),
    ("گارڈن ٹاؤن", "Garden Town"), ("علامہ اقبال ٹاؤن", "Allama Iqbal Town"),
    ("واپڈا ٹاؤن", "WAPDA Town"), ("لی ڈی اے", "LDA"),
    ("گلبرگ", "Gulberg"), ("شادمان", "Shadman"),
    ("گلشنِ راوی", "Gulshan-e-Ravi"), ("گجومتہ", "Gajumatta"),
    ("ٹھوکر نیاز بیگ", "Thokar Niaz Baig"), ("مولانا شوکت علی", "Maulana Shaukat Ali"),
    ("شاہ عالمی", "Shah Alam"), ("داتا دربار", "Data Darbar"),
    ("لبرٹی مارکیٹ", "Liberty Market"), ("حفیظ سنٹر", "Hafeez Centre"),
    ("جی ٹی روڈ", "GT Road"), ("ٹنکی والا روڈ", "Tanki Wala Road"),
    ("کچھہری روڈ", "Kutchery Road"), ("الحمد روڈ", "Al Hamd Road"),
    ("نجات روڈ", "Nijat Road"),
    ("برکی روڈ", "Burki Road"), ("رائیونڈ روڈ", "Raiwind Road"),
    ("نہر کنار روڈ", "Canal Bank Road"),
    ("روٹی تندور روڈ", "Roti Tandoor Road"), ("اقبال ایونیو", "Iqbal Avenue"),
    ("خیا ب انِ جناح", "Khayaban-e-Jinnah"), ("خیابانِ جناح", "Khayaban-e-Jinnah"),
    ("کاماہاں انٹرچینج", "Kamahan Interchange"),
    ("عبدالحق روڈ", "Abdul Haq Road"), ("لیاقت علی خان روڈ", "Liaquat Ali Khan Road"),
    ("بیرونی سمن آباد روڈ", "Outer Samnabad Road"), ("چونیاں روڈ", "Chunian Road"),
    ("نشتر روڈ", "Nishtar Road"), ("ریونیو روڈ", "Revenue Road"),
    ("ڈیفنس روڈ", "Defence Road"), ("شاہ پور کانجراں روڈ", "Shahpur Kanjran Road"),
    ("نیا زی", "Niazi"), ("بیرونی", "Outer"), ("مین", "Main"),
    ("ساگیان", "Sagian"), ("شیخ زید", "Sheikh Zayed"),
    ("گجو متہ روڈ", "Gajumatta Road"), ("ایڈن آباد", "Eden Abad"),
    ("الخضریا ہاؤسنگ", "Al Khazriya Housing"), ("پی آئی اے سوسائٹی", "PIA Society"),
    ("پی آئی اے سوسائٹی", "PIA Society"),
    ("نواں کوٹ", "Nawan Kot"), ("بائیک پوائنٹ", "Bike Point"),
    ("چوبرجی انڈر پاس", "Chauburji Underpass"),
    ("مین بلیوارڈ", "Main Boulevard"), ("فیروزپور روڈ", "Ferozepur Road"),
    ("ملتان روڈ", "Multan Road"), ("کینال روڈ", "Canal Road"),
    ("روڈ", "Road"), ("چوک", "Chowk"), ("بازار", "Bazaar"),
    ("سٹریٹ", "Street"), ("بلاک", "Block"), ("سیکٹر", "Sector"),
    ("فیز", "Phase"), ("ٹاؤن", "Town"), ("مارکیٹ", "Market"),
    ("کالونی", "Colony"), ("پارک", "Park"),
]

_URDU_CHAR_ROMAN: Dict[str, str] = {
    "ا": "a", "آ": "aa", "أ": "a", "إ": "i", "ء": "", "ئ": "e", "ؤ": "o",
    "ب": "b", "پ": "p", "ت": "t", "ٹ": "t", "ث": "s", "ج": "j", "چ": "ch",
    "ح": "h", "خ": "kh", "د": "d", "ڈ": "d", "ذ": "z", "ر": "r", "ڑ": "r",
    "ز": "z", "ژ": "zh", "س": "s", "ش": "sh", "ص": "s", "ض": "z", "ط": "t",
    "ظ": "z", "ع": "a", "غ": "gh", "ف": "f", "ق": "q", "ک": "k", "گ": "g",
    "ل": "l", "م": "m", "ن": "n", "ں": "n", "و": "o", "ہ": "h", "ھ": "h",
    "ی": "y", "ے": "e",
}


def _romanize_urdu_token(token: str) -> str:
    out: List[str] = []
    for ch in token:
        out.append(_URDU_CHAR_ROMAN.get(ch, ""))
    roman = "".join(out)
    roman = re.sub(r"(.)\\1{2,}", r"\\1\\1", roman)
    return re.sub(r"\s+", " ", roman).strip(" -_/,.،")


def _romanize_remaining_urdu(text: str) -> str:
    def _repl(match: re.Match[str]) -> str:
        roman = _romanize_urdu_token(match.group(0))
        return f" {roman} " if roman else " "

    return _URDU_CHARS_RE.sub(_repl, text)


def _keyword_sub(urdu_text: str) -> str:
    """Apply keyword substitution, strip remaining Urdu chars, title-case."""
    result = urdu_text
    for urdu_kw, eng_kw in _KW_MAP:
        result = result.replace(urdu_kw, eng_kw)
    result = _romanize_remaining_urdu(result)
    result = _URDU_CHARS_RE.sub(" ", result)
    result = re.sub(r"\s+", " ", result).strip()
    if len(result) < 4:
        return urdu_text
    titled = result.title()
    # Preserve known acronym casing after title-casing.
    titled = re.sub(r"\bPcsir\b", "PCSIR", titled)
    titled = re.sub(r"\bDha\b", "DHA", titled)
    titled = re.sub(r"\bLda\b", "LDA", titled)
    titled = re.sub(r"\bWapda\b", "WAPDA", titled)
    titled = re.sub(r"\bGt\b", "GT", titled)
    titled = re.sub(r"\bMm Alam\b", "MM Alam", titled)
    return titled


def _azure_transliterate_single(urdu_text: str) -> str:
    """
    Translate a single Urdu area string to English via MyMemory free API.
    No account, no credit card, no API key — free forever (5,000 chars/day).

    Strategy:
      1. Apply keyword substitution (instant, handles most common Lahore areas).
      2. If result still has Urdu chars, call MyMemory for the full translation.
      3. Fall back to keyword result if API call fails or quota exceeded.
    """
    if not urdu_text or not urdu_text.strip():
        return ""

    # Pass 1: keyword substitution
    kw_result = _keyword_sub(urdu_text)

    # If keyword pass left no Urdu chars, it's good enough — no API call needed
    if not _URDU_CHARS_RE.search(kw_result):
        return kw_result

    # Pass 2: MyMemory API for remaining Urdu text
    try:
        resp = requests.get(
            _MYMEMORY_URL,
            params={"q": urdu_text[:500], "langpair": "ur|en"},
            timeout=8,
        )
        if resp.status_code == 200:
            data = resp.json()
            translated = data.get("responseData", {}).get("translatedText", "")
            # MyMemory echoes original on failure or quota exceeded
            if translated and translated != urdu_text and not _URDU_CHARS_RE.search(translated):
                return re.sub(r"\s+", " ", translated).strip().title()
    except Exception as _exc:
        logger.debug(f"MyMemory call failed: {_exc} — using keyword result")

    return kw_result  # keyword result as final fallback


# Actions that require superadmin approval
SENSITIVE_ACTIONS = [
    "delete_user",
    "bulk_delete",
    "change_role_to_admin",
    "change_role_to_superadmin",
    "bulk_suspend",
    "fir_ocr_submission",
]

# Permission required for each action type (None = any admin may submit)
ACTION_PERMISSIONS = {
    "delete_user": "manage_users",
    "bulk_delete": "manage_users",
    "bulk_suspend": "manage_users",
    "change_role_to_admin": "manage_users",
    "change_role_to_superadmin": "manage_users",
    "fir_ocr_submission": None,  # any admin can submit FIR for approval
}


def create_approval_request(
    admin_username: str,
    action_type: str,
    target_type: str,
    target_id: Optional[int] = None,
    request_data: Optional[dict] = None,
) -> Optional[int]:
    """
    Create an approval request for a sensitive admin action.
    Returns the request ID or None on failure.
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO approval_requests
               (admin_username, action_type, target_type, target_id, request_data, status, requested_at)
               VALUES (%s, %s, %s, %s, %s, 'pending', %s)""",
            (
                admin_username,
                action_type,
                target_type,
                target_id,
                json.dumps(request_data) if request_data else None,
                datetime.now(),
            ),
        )
        request_id = cursor.lastrowid
        conn.commit()
        cursor.close()
        logger.info(f"Approval request #{request_id} created by {admin_username}: {action_type}")
        return request_id
    except Exception as e:
        logger.error(f"Failed to create approval request: {e}")
        return None
    finally:
        if conn and conn.is_connected():
            conn.close()


def get_pending_approvals(limit: int = 100) -> List[Dict[str, Any]]:
    """Get all pending approval requests (for superadmin review)."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        # Increase sort buffer for this session to handle large request_data blobs
        cursor.execute("SET SESSION sort_buffer_size = 8388608")
        # Step 1: get sorted IDs without sorting large blob data
        cursor.execute(
            """SELECT id FROM approval_requests
               WHERE status = 'pending'
               ORDER BY requested_at DESC
               LIMIT %s""",
            (limit,),
        )
        id_rows = cursor.fetchall()
        if not id_rows:
            cursor.close()
            return []
        ids = [r["id"] for r in id_rows]
        # Step 2: fetch full rows by primary key (no sort needed)
        placeholders = ",".join(["%s"] * len(ids))
        cursor.execute(
            f"SELECT * FROM approval_requests WHERE id IN ({placeholders})",
            ids,
        )
        rows = cursor.fetchall()
        # Preserve the ORDER BY order from step 1
        id_order = {rid: idx for idx, rid in enumerate(ids)}
        rows.sort(key=lambda r: id_order.get(r["id"], 0))
        results = []
        for row in rows:
            r = cast(Dict[str, Any], row)
            data = json.loads(r["request_data"]) if r.get("request_data") else {}
            # Strip the heavy image blob from list responses; it is only needed per-review
            data.pop("fir_image_base64", None)

            # Proactive duplicate warning for FIR submissions in pending queue.
            if r.get("action_type") == "fir_ocr_submission":
                try:
                    is_dup, dup_reason = _detect_duplicate_fir_submission(data, cursor)
                    r["duplicate_candidate"] = bool(is_dup)
                    r["duplicate_reason"] = dup_reason if is_dup else None
                except Exception as _dup_exc:
                    logger.debug("duplicate check failed for request %s: %s", r.get("id"), _dup_exc)
                    r["duplicate_candidate"] = False
                    r["duplicate_reason"] = None

            r["request_data"] = data
            if r.get("requested_at") and hasattr(r["requested_at"], "isoformat"):
                r["requested_at"] = r["requested_at"].isoformat()
            if r.get("reviewed_at") and hasattr(r["reviewed_at"], "isoformat"):
                r["reviewed_at"] = r["reviewed_at"].isoformat()
            results.append(r)
        cursor.close()
        return results
    except Exception as e:
        logger.error(f"Failed to get pending approvals: {e}")
        return []
    finally:
        if conn and conn.is_connected():
            conn.close()


def get_approval_requests_for_admin(admin_username: str, limit: int = 50) -> List[Dict[str, Any]]:
    """Get approval requests submitted by a specific admin."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        # Increase sort buffer for this session to handle large request_data blobs
        cursor.execute("SET SESSION sort_buffer_size = 8388608")
        # Step 1: get sorted IDs without sorting large blob data
        cursor.execute(
            """SELECT id FROM approval_requests
               WHERE admin_username = %s
               ORDER BY requested_at DESC
               LIMIT %s""",
            (admin_username, limit),
        )
        id_rows = cursor.fetchall()
        if not id_rows:
            cursor.close()
            return []
        ids = [r["id"] for r in id_rows]
        # Step 2: fetch full rows by primary key (no sort needed)
        placeholders = ",".join(["%s"] * len(ids))
        cursor.execute(
            f"SELECT * FROM approval_requests WHERE id IN ({placeholders})",
            ids,
        )
        rows = cursor.fetchall()
        cursor.close()
        # Preserve the ORDER BY order from step 1
        id_order = {rid: idx for idx, rid in enumerate(ids)}
        rows.sort(key=lambda r: id_order.get(r["id"], 0))
        results = []
        for row in rows:
            r = cast(Dict[str, Any], row)
            data = json.loads(r["request_data"]) if r.get("request_data") else {}
            # Strip the heavy image blob from list responses; it is only needed per-review
            data.pop("fir_image_base64", None)
            r["request_data"] = data
            if r.get("requested_at") and hasattr(r["requested_at"], "isoformat"):
                r["requested_at"] = r["requested_at"].isoformat()
            if r.get("reviewed_at") and hasattr(r["reviewed_at"], "isoformat"):
                r["reviewed_at"] = r["reviewed_at"].isoformat()
            results.append(r)
        return results
    except Exception as e:
        logger.error(f"Failed to get admin approval requests: {e}")
        return []
    finally:
        if conn and conn.is_connected():
            conn.close()


def get_approval_request_by_id(request_id: int) -> Optional[Dict[str, Any]]:
    """Get a single approval request by ID, including the full FIR image."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM approval_requests WHERE id = %s", (request_id,))
        row = cast(Optional[Dict[str, Any]], cursor.fetchone())
        cursor.close()
        if not row:
            return None
        row["request_data"] = json.loads(row["request_data"]) if row.get("request_data") else {}
        if row.get("requested_at") and hasattr(row["requested_at"], "isoformat"):
            row["requested_at"] = row["requested_at"].isoformat()
        if row.get("reviewed_at") and hasattr(row["reviewed_at"], "isoformat"):
            row["reviewed_at"] = row["reviewed_at"].isoformat()
        return row
    except Exception as e:
        logger.error(f"Failed to get approval request #{request_id}: {e}")
        return None
    finally:
        if conn and conn.is_connected():
            conn.close()


def review_approval_request(
    request_id: int,
    reviewer_username: str,
    approved: bool,
    notes: Optional[str] = None,
    edited_data: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Approve or reject an approval request. If approved, execute the action.
    edited_data: optional overrides from SuperAdmin (e.g. corrected FIR fields).
    Returns a dict with status and message.
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Get the request
        cursor.execute("SELECT * FROM approval_requests WHERE id = %s", (request_id,))
        req = cast(Optional[Dict[str, Any]], cursor.fetchone())
        if not req:
            return {"success": False, "message": "Approval request not found"}

        if req["status"] != "pending":
            return {"success": False, "message": f"Request already {req['status']}"}

        # If SuperAdmin edited the data, merge edits into request_data before execution
        if edited_data and approved:
            original_data = json.loads(req["request_data"]) if req.get("request_data") else {}
            # Merge edited fields into original data
            if "extracted_fields" in edited_data:
                original_data["extracted_fields"] = {
                    **original_data.get("extracted_fields", {}),
                    **edited_data["extracted_fields"],
                }
            if "extracted_sections" in edited_data:
                original_data["extracted_sections"] = edited_data["extracted_sections"]
            req["request_data"] = json.dumps(original_data)
            # Also update in DB so the audit trail has the edited version
            cursor.execute(
                "UPDATE approval_requests SET request_data = %s WHERE id = %s",
                (req["request_data"], request_id),
            )

        # Auto-reject duplicate FIR submissions even if SuperAdmin clicks approve.
        if approved and req.get("action_type") == "fir_ocr_submission":
            req_data_obj = json.loads(req["request_data"]) if req.get("request_data") else {}
            is_dup, dup_reason = _detect_duplicate_fir_submission(req_data_obj, cursor)
            if is_dup:
                auto_note = f"Auto-rejected: {dup_reason}"
                merged_notes = f"{notes}\n{auto_note}" if notes else auto_note
                cursor.execute(
                    """UPDATE approval_requests
                       SET status = 'rejected', reviewed_by = %s, reviewed_at = %s, review_notes = %s
                       WHERE id = %s""",
                    (reviewer_username, datetime.now(), merged_notes, request_id),
                )
                conn.commit()
                cursor.close()
                return {
                    "success": True,
                    "message": "Request rejected: duplicate FIR incident already exists in database",
                    "status": "rejected",
                    "auto_rejected": True,
                    "reason": dup_reason,
                }

        new_status = "approved" if approved else "rejected"

        cursor.execute(
            """UPDATE approval_requests
               SET status = %s, reviewed_by = %s, reviewed_at = %s, review_notes = %s
               WHERE id = %s""",
            (new_status, reviewer_username, datetime.now(), notes, request_id),
        )
        conn.commit()

        result = {"success": True, "message": f"Request {new_status}", "status": new_status}

        # If approved, execute the action
        if approved:
            exec_result = _execute_approved_action(req, cursor, conn)
            result["execution"] = exec_result

        cursor.close()
        return result
    except Exception as e:
        logger.error(f"Failed to review approval request: {e}")
        return {"success": False, "message": str(e)}
    finally:
        if conn and conn.is_connected():
            conn.close()


def _execute_approved_action(req: Dict[str, Any], cursor, conn) -> Dict[str, Any]:
    """Execute an approved action."""
    action = req["action_type"]
    request_data = json.loads(req["request_data"]) if req.get("request_data") else {}

    try:
        if action == "delete_user":
            user_id = req.get("target_id")
            if user_id:
                cursor.execute("DELETE FROM users_info WHERE id = %s", (user_id,))
                conn.commit()
                return {"success": True, "message": f"User {user_id} deleted"}

        elif action == "bulk_delete":
            user_ids = request_data.get("user_ids", [])
            if user_ids:
                fmt = ",".join(["%s"] * len(user_ids))
                cursor.execute(f"DELETE FROM users_info WHERE id IN ({fmt})", user_ids)
                conn.commit()
                return {"success": True, "message": f"{len(user_ids)} users deleted"}

        elif action == "bulk_suspend":
            user_ids = request_data.get("user_ids", [])
            if user_ids:
                fmt = ",".join(["%s"] * len(user_ids))
                cursor.execute(
                    f"UPDATE users_info SET role = 'inactive' WHERE id IN ({fmt})", user_ids
                )
                conn.commit()
                return {"success": True, "message": f"{len(user_ids)} users suspended"}

        elif action in ("change_role_to_admin", "change_role_to_superadmin"):
            user_id = req.get("target_id")
            new_role = "admin" if action == "change_role_to_admin" else "superadmin"
            if user_id:
                cursor.execute(
                    "UPDATE users_info SET role = %s WHERE id = %s", (new_role, user_id)
                )
                conn.commit()
                return {"success": True, "message": f"User {user_id} role changed to {new_role}"}

        elif action == "fir_ocr_submission":
            return _execute_fir_submission(request_data, cursor, conn)

        return {"success": False, "message": f"Unknown action: {action}"}

    except Exception as e:
        logger.error(f"Failed to execute approved action: {e}")
        conn.rollback()
        return {"success": False, "message": str(e)}


def _predict_risk(area_english: str, crime_name: str, parsed_date: datetime) -> str:
    """Predict risk level using the Random Forest model. Returns 'Low'/'Medium'/'High'."""
    if not _rf_model or not _le_area or not _le_crime or not _le_risk:
        return "Medium"  # fallback when model unavailable
    try:
        # Best-effort match against encoder classes
        matched_area = _best_label_match(area_english, _le_area)
        matched_crime = _best_label_match(crime_name, _le_crime)
        if not matched_area or not matched_crime:
            logger.warning(f"Risk prediction: no encoder match for area='{area_english}' or crime='{crime_name}' — defaulting to Medium")
            return "Medium"
        area_enc = int(_le_area.transform([matched_area])[0])
        crime_enc = int(_le_crime.transform([matched_crime])[0])
        year = int(parsed_date.year)
        month = int(parsed_date.month)
        day = int(parsed_date.day)
        weekday = int(parsed_date.weekday())
        day_of_year = int(parsed_date.timetuple().tm_yday)
        is_weekend = 1 if weekday in (5, 6) else 0
        features = pd.DataFrame(
            [[area_enc, crime_enc, year, month, day, weekday, day_of_year, is_weekend]],
            columns=["area_enc", "crime_type_enc", "year", "month", "day", "weekday", "day_of_year", "is_weekend"],
        ).astype(int)
        pred = _rf_model.predict(features)[0]
        risk = _le_risk.inverse_transform([pred])[0]
        return str(risk).capitalize()
    except Exception as exc:
        logger.error(f"Risk prediction failed: {exc}")
        return "Medium"


def _best_label_match(value: str, le) -> Optional[str]:
    """Case-insensitive / substring match against a LabelEncoder's classes."""
    if not value:
        return None
    v = value.strip().lower()
    for cls in le.classes_:
        if cls.lower() == v:
            return cls
    for cls in le.classes_:
        if v in cls.lower() or cls.lower() in v:
            return cls
    return None


def _risk_from_severity(crime_name: str) -> str:
    """
    Derive High/Medium/Low risk from the PPC crime name by fuzzy-matching
    against severity_map.json (which covers all PPC offences).
    No hardcoded category mapping — works with every real PPC section name.

    severity weighted-score >= 7.5 → High
    severity weighted-score >= 4.5 → Medium
    otherwise                      → Low
    """
    if not _SEVERITY_MAP:
        return "Medium"
    n = crime_name.lower()
    best_score: float = 0.0
    for key, score in _SEVERITY_MAP.items():
        # Strip punctuation from key, then check each meaningful word
        key_words = [w for w in key.replace("(", "").replace(")", "")
                     .replace("-", " ").split() if len(w) > 3]
        if not key_words:
            continue
        matches = sum(1 for w in key_words if w in n)
        if matches:
            weighted = (matches / len(key_words)) * float(score)
            if weighted > best_score:
                best_score = weighted
    if best_score >= 7.5:
        return "High"
    if best_score >= 4.5:
        return "Medium"
    if best_score > 0:
        return "Low"
    return "Medium"  # default when no match found


def _first_address_component(display_name: Optional[str]) -> Optional[str]:
    """Return the first comma-separated component of a Nominatim display_name.

    E.g. "Eden Lane Villas 1, Labor Colony, Punjab, ..." → "Eden Lane Villas 1".
    Used as a last-resort label when the `areas` table has no nearby row.
    """
    if not display_name:
        return None
    first = display_name.split(",", 1)[0].strip()
    return first or None


# Sub-division keywords (English + Urdu). Everything from the first occurrence
# of any of these onward is considered granular detail (block / house / plot)
# that should NOT be part of the canonical area name. "Phase" is intentionally
# excluded because it's part of proper names like "DHA Phase 5".
_AREA_SUBDIVISION_MARKERS_EN = re.compile(
    r"\b(sub\s*block|sub-?block|block|sector|house\s*no|house|plot\s*no|plot|gali|street|lane|chak\s*no|near|opposite)\b",
    flags=re.IGNORECASE,
)
_AREA_SUBDIVISION_MARKERS_UR = re.compile(
    r"(سب\s*بلاک|بلاک|سیکٹر|مکان\s*نمبر|مکان|پلاٹ|گلی|سٹریٹ|کے\s*قریب|کے\s*سامنے)"
)


def _simplify_area_name(text: Optional[str]) -> Optional[str]:
    """Strip granular sub-division suffixes to leave the locality name.

    Examples:
      "Bahria Town Sector F Block J S B Block Z"   → "Bahria Town"
      "Eden Abad Block F Sub Block G"              → "Eden Abad"
      "DHA Phase 5 Block L"                        → "DHA Phase 5"
      "Askari 11"                                  → "Askari 11"
      "بحریہ ٹاؤن سیکٹر F بلاک J سب بلاک Z"        → "بحریہ ٹاؤن"

    The rule is data-agnostic — no hardcoded locality list. Any FIR runs
    through the same marker-based split.
    """
    if not text:
        return text
    has_urdu = bool(re.search(r"[؀-ۿ]", text))
    pattern = _AREA_SUBDIVISION_MARKERS_UR if has_urdu else _AREA_SUBDIVISION_MARKERS_EN
    m = pattern.search(text)
    if m:
        text = text[: m.start()]
    # Trim punctuation/whitespace left dangling by the cut
    text = text.strip(" ,،-–—")
    # Drop trailing city suffixes that add no disambiguation value
    text = re.sub(r"[,،]?\s+(Lahore|لاہور)\s*$", "", text, flags=re.IGNORECASE)
    return text.strip(" ,،-–—") or None


def _nearest_area_name(lat: float, lon: float, cursor) -> Optional[str]:
    """
    Return the English area name from the `areas` table closest (by
    Haversine distance) to the given coordinates.  Returns None on failure.
    """
    try:
        cursor.execute(
            """
            SELECT area_name,
                   (6371 * acos(LEAST(1.0,
                     cos(radians(%s)) * cos(radians(latitude))
                     * cos(radians(longitude) - radians(%s))
                     + sin(radians(%s)) * sin(radians(latitude))
                   ))) AS dist_km
            FROM areas
            ORDER BY dist_km ASC
            LIMIT 1
            """,
            (lat, lon, lat),
        )
        row = cursor.fetchone()
        if row:
            return row["area_name"] if isinstance(row, dict) else row[0]
    except Exception as exc:
        logger.warning(f"Nearest-area lookup failed: {exc}")
    return None


def _parse_fir_date_to_iso(raw_date: str) -> str:
    """Parse common FIR date formats and return YYYY-MM-DD (today if unknown)."""
    _DATE_FORMATS = [
        "%Y-%m-%d",
        "%d-%m-%Y",
        "%d/%m/%Y",
        "%m/%d/%Y",
        "%d-%m-%y",
        "%d/%m/%y",
        "%Y/%m/%d",
    ]
    for _fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(str(raw_date).strip(), _fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return datetime.now().strftime("%Y-%m-%d")


def _detect_duplicate_fir_submission(request_data: Dict[str, Any], cursor) -> Tuple[bool, str]:
    """
    Detect whether an incoming FIR submission is already present in `crimes`.

    Matching strategy (two-pass):
      Pass 1 — strict: same date + same time + coordinates within 0.002° (~220 m)
      Pass 2 — loose : same date + coordinates within 0.005° (~550 m), ignoring time
                       (handles OCR time-extraction variance and CSV-imported records
                        that have no area_urdu / slightly different geocoded coords)

    Area-text columns (area_urdu / area_translit) are intentionally excluded from
    the WHERE clause because:
      - CSV-imported records often have area_urdu = NULL
      - OCR may return the area in English on one upload and Urdu on the next
    """
    fields = request_data.get("extracted_fields", {}) or {}
    location = fields.get("location", {}) or {}
    sections = request_data.get("extracted_sections", []) or []

    raw_date = fields.get("crime_date") or datetime.now().strftime("%Y-%m-%d")
    crime_date = _parse_fir_date_to_iso(str(raw_date))
    crime_time = (fields.get("crime_time") or None)
    if crime_time:
        crime_time = str(crime_time).strip() or None

    latitude = location.get("latitude")
    longitude = location.get("longitude")
    if latitude is None or longitude is None:
        return False, "Coordinates missing — duplicate check skipped"

    expected_crime_types = set()
    for sec in sections:
        cname, _lt = get_crime_name(str(sec))
        expected_crime_types.add(cname)
    if not expected_crime_types:
        return False, "No sections available for duplicate comparison"

    lat_f = float(latitude)
    lon_f = float(longitude)

    # ── Pass 1: strict — date + time + tight coordinate window ─────────────
    strict_query = """
        SELECT crime_type
        FROM crimes
        WHERE crime_date = %s
          AND ( (crime_time = %s) OR (%s IS NULL AND crime_time IS NULL) )
          AND ABS(latitude  - %s) <= 0.002
          AND ABS(longitude - %s) <= 0.002
    """
    cursor.execute(strict_query, (crime_date, crime_time, crime_time, lat_f, lon_f))
    rows = cursor.fetchall() or []

    # ── Pass 2: loose — date only + broader coordinate window (skip time) ──
    if not rows:
        loose_query = """
            SELECT crime_type
            FROM crimes
            WHERE crime_date = %s
              AND ABS(latitude  - %s) <= 0.005
              AND ABS(longitude - %s) <= 0.005
        """
        cursor.execute(loose_query, (crime_date, lat_f, lon_f))
        rows = cursor.fetchall() or []

    if not rows:
        return False, "No existing rows matched date/location key"

    existing_types = {str(r["crime_type"]) for r in rows if r.get("crime_type")}
    if expected_crime_types.issubset(existing_types):
        return (
            True,
            f"Duplicate FIR detected for {crime_date} {crime_time or ''} at ({lat_f:.6f}, {lon_f:.6f}); all section crime types already exist in the database",
        )

    return False, "Partial overlap only — not treated as duplicate"


def _execute_fir_submission(request_data: Dict[str, Any], cursor, conn) -> Dict[str, Any]:
    """
    Insert FIR OCR extracted data into the crimes table.
    Creates one row per PPC section with:
      - area stored as "اردو (English)"
      - crime_type = English crime name from PPC mapping
      - risk_level auto-predicted by ML model
    """
    try:
        fields = request_data.get("extracted_fields", {})
        raw_date = fields.get("crime_date") or datetime.now().strftime("%Y-%m-%d")

        location = fields.get("location") or {}
        sections = request_data.get("extracted_sections", [])

        # ── Coordinates ─────────────────────────────────────────────────
        latitude  = location.get("latitude")
        longitude = location.get("longitude")

        # Final fallback: Lahore city-centre
        if not latitude or not longitude:
            latitude, longitude = 31.5204, 74.3587

        # ── Preserve raw Urdu area name from OCR for bilingual display ────
        area_urdu_raw = (location.get("thana_name") or fields.get("crime_area") or "").strip()

        # ── Extract crime_time from FIR OCR fields ────────────────────────
        crime_time = fields.get("crime_time") or None
        # Normalise: strip any surrounding whitespace
        if crime_time:
            crime_time = str(crime_time).strip() or None

        # ── Transliterate Urdu area → Roman for display ───────────────────
        area_translit = _azure_transliterate_single(area_urdu_raw) if area_urdu_raw else None

        # ── Resolve the canonical `area` column (used for map aggregation) ──
        # Data-driven — no hardcoded locality list. Priority:
        #   1. simplified area_translit — the FIR's neighborhood, with
        #      block/sector/sub-block suffixes stripped (e.g.
        #      "Bahria Town Sector F Block J" → "Bahria Town").
        #   2. nearest_area   — Haversine lookup against the `areas` DB table.
        #   3. Nominatim display_name first component.
        #   4. raw Urdu       — last-resort text the admin saw on screen.
        #   5. "Lahore"       — absolute fallback.
        nearest_mapped_area = _nearest_area_name(float(latitude), float(longitude), cursor)
        area_display = (
            _simplify_area_name((area_translit or "").strip())
            or nearest_mapped_area
            or _first_address_component(location.get("display_name"))
            or _simplify_area_name(area_urdu_raw)
            or "Lahore"
        )

        logger.info(
            f"FIR Processing: Lat={latitude}, Lon={longitude}, FIR Area='{area_translit}', "
            f"Nearest Mapped Area='{nearest_mapped_area}', Saved Plot Area='{area_display}'"
        )

        # ── Parse date — try multiple common FIR date formats ───────────
        _DATE_FORMATS = [
            "%Y-%m-%d",   # ISO:        2025-05-24
            "%d-%m-%Y",   # Pakistani:  24-05-2025
            "%d/%m/%Y",   # slash:      24/05/2025
            "%m/%d/%Y",   # US:         05/24/2025
            "%d-%m-%y",   # 2-digit yr: 24-05-25
            "%d/%m/%y",
            "%Y/%m/%d",
        ]
        parsed_date = None
        for _fmt in _DATE_FORMATS:
            try:
                parsed_date = datetime.strptime(str(raw_date).strip(), _fmt)
                raw_date = parsed_date.strftime("%Y-%m-%d")
                break
            except ValueError:
                continue
        if parsed_date is None:
            logger.warning(f"FIR date '{raw_date}' could not be parsed — defaulting to today")
            parsed_date = datetime.now()
            raw_date = parsed_date.strftime("%Y-%m-%d")

        # ── Ensure we have at least one section to insert ───────────────
        if not sections:
            sections = ["Unknown"]

        created_ids: List[int] = []

        for section in sections:
            crime_name, law_type = get_crime_name(str(section))

            # Derive risk directly from the PPC crime name via severity_map
            # (no category mapping needed — works with every real PPC section)
            risk_level = _risk_from_severity(crime_name)

            # Store the full readable PPC crime name in the crimes table
            crime_type_label = crime_name

            description = f"FIR OCR extraction — §{section} {law_type}: {crime_name}"

            cursor.execute(
                """INSERT INTO crimes
                   (crime_date, crime_time, area, area_urdu, area_translit,
                    crime_type, latitude, longitude,
                    risk_level, source, status, description, created_at)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                (
                    raw_date,
                    crime_time,
                    area_display,
                    area_urdu_raw or None,
                    area_translit or None,
                    crime_type_label,
                    latitude,
                    longitude,
                    risk_level,
                    "admin",
                    "verified",
                    description,
                    datetime.now(),
                ),
            )
            created_ids.append(cursor.lastrowid)
            logger.info(
                f"Crime record #{cursor.lastrowid} created: §{section} {law_type} "
                f"→ {crime_type_label}, area={area_display}, risk={risk_level}"
            )

        conn.commit()
        msg = f"{len(created_ids)} crime record(s) created from FIR (IDs: {created_ids})"
        logger.info(msg)

        # ── IMMEDIATE ALERT TRIGGER: Notify users of these new verified incidents ──
        try:
            from app.routes.alerts import dispatch_new_incident_alerts
            import asyncio
            import threading

            def _dispatch_task(crime_pkg):
                """Run the async dispatch in a separate thread so we don't block the review process"""
                try:
                    asyncio.run(dispatch_new_incident_alerts(crime_pkg))
                except Exception as _de:
                    logger.error(f"Background FIR alert dispatch failed: {_de}")

            # Prepare data package for each crime
            for i, cid in enumerate(created_ids):
                # Using current local mapping for area/crime_type
                # If there are multiple sections, they all share basic loc info
                crime_pkg = {
                    "id": cid,
                    "area": area_display,
                    "area_translit": area_translit or area_display,
                    "crime_type": sections[i] if i < len(sections) else "Incident",
                    "latitude": float(latitude),
                    "longitude": float(longitude),
                    "risk_level": _risk_from_severity(sections[i]) if i < len(sections) else "Medium",
                    "crime_date": raw_date
                }
                # Spawn a thread — this is a safe way to run async in a sync context without 
                # a persistent background_tasks object available from FastAPI router.
                threading.Thread(target=_dispatch_task, args=(crime_pkg,), daemon=True).start()
            
            logger.info(f"🚀 Immediate alert dispatch threads launched for {len(created_ids)} FIR incidents")
        except Exception as alert_err:
            logger.error(f"Failed to launch immediate alerts for FIR approval: {alert_err}")

        # Notify auto-retrain guard for each new record — runs in background,
        # schedules model retrain when new areas/crime types accumulate
        try:
            from app.crime_risk_model.utils.auto_retrain import notify_new_record as _ar_notify
            for section in sections:
                crime_name_for_notify, _ = get_crime_name(str(section))
                _ar_notify(area_display, crime_name_for_notify)
        except Exception as _arex:
            logger.debug("auto_retrain notify failed (non-fatal): %s", _arex)

        return {"success": True, "message": msg, "crime_ids": created_ids}

    except Exception as e:
        logger.error(f"Failed to execute FIR submission: {e}")
        conn.rollback()
        return {"success": False, "message": str(e)}


def is_sensitive_action(action_type: str) -> bool:
    """Check if an action requires superadmin approval."""
    return action_type in SENSITIVE_ACTIONS


def get_required_permission(action_type: str) -> Optional[str]:
    """Get the permission required for a given action type."""
    return ACTION_PERMISSIONS.get(action_type)


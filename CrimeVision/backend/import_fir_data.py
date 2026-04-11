"""
FIR Data Import Script
======================
Imports data from fir_data_2500.txt into the crimes table.

Actions performed:
  1. Adds crime_time column to crimes table (if not already present)
  2. Deletes all existing data from crimes table
  3. Parses each line of fir_data_2500.txt
  4. Geocodes Urdu area names → lat/lng via Nominatim (OpenStreetMap, free)
  5. Resolves nearest English area name from the `areas` DB table
  6. Derives risk_level from severity_map.json (the correct model for crimes table)
  7. Resolves English crime name per section via ppc_sections.get_crime_name()
  8. Inserts one DB row per section (each section gets its own row)

Usage:
    cd CrimeVision/backend
    .\venv\Scripts\python.exe import_fir_data.py
"""

import sys, os, re, json, time, logging, unicodedata
from datetime import datetime
from typing import Optional, Tuple, List, Dict

import requests

sys.path.insert(0, os.path.dirname(__file__))

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)s  %(message)s",
    handlers=[logging.StreamHandler(
        open(sys.stdout.fileno(), mode="w", encoding="utf-8", buffering=1, closefd=False)
    )],
)
log = logging.getLogger("fir_import")

# ── Paths ─────────────────────────────────────────────────────────────────────
BASE_DIR    = os.path.dirname(__file__)
DATA_FILE   = os.path.join(
    BASE_DIR, "..", "Image-to-text", "backend", "fir_data_2500.txt"
)
SEVERITY_MAP_PATH = os.path.join(
    BASE_DIR, "app", "crime_risk_model", "config", "severity_map.json"
)

# ── Load Severity Map ─────────────────────────────────────────────────────────
_SEVERITY_MAP: Dict[str, float] = {}
try:
    with open(SEVERITY_MAP_PATH, "r", encoding="utf-8") as _f:
        _SEVERITY_MAP = json.load(_f)
    log.info(f"✓ Loaded severity_map.json ({len(_SEVERITY_MAP)} entries)")
except Exception as _e:
    log.warning(f"Could not load severity_map.json: {_e}  →  risk defaults to Medium")

# ── Urdu character range ───────────────────────────────────────────────────────
URDU_RE = re.compile(r"[\u0600-\u06FF\u0750-\u077F\uFB50-\uFDFF\uFE70-\uFEFF]+")

# ── Urdu → English keyword map for geocoding assistance ───────────────────────
_URDU_KW: List[Tuple[str, str]] = [
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
    ("لیک سٹی سیکٹر M1 سب بلاک T، آسوکی روڈ", "Lake City Sector M1 Sub-Block T, Asooki Road"),
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
    ("سب بلاک",             "Sub-Block"),   # must precede بلاک
    ("ڈی ایچ اے",           "DHA"),

    ("بحریہ ٹاؤن",          "Bahria Town"),
    ("آسکاری",              "Askari"),
    ("واپڈا ٹاؤن",          "WAPDA Town"),
    ("پی سی ایس آئی آر",   "PCSIR"),
    ("لی ڈی اے",            "LDA"),
    ("ایل ڈی اے",           "LDA"),   # alternate FIR spelling (Ell-Dee-Ay)
    # Compound سٹی names — MUST precede bare سٹی→City
    ("لیک سٹی",             "Lake City"),
    ("پارگون سٹی",          "Paragon City"),
    ("سٹی",                 "City"),
    # Road / junction landmarks
    ("ٹھوکر نیاز بیگ",     "Thokar Niaz Baig"),
    ("انٹرچینج",            "Interchange"),
    ("والینشیا",            "Valencia"),
    ("علامہ اقبال ٹاؤن",   "Allama Iqbal Town"),
    ("جوہر ٹاؤن",           "Johar Town"),
    ("گارڈن ٹاؤن",          "Garden Town"),
    ("ماڈل ٹاؤن",           "Model Town"),
    ("شادمان",              "Shadman"),
    ("گلبرگ",               "Gulberg"),
    ("فیصل ٹاؤن",           "Faisal Town"),
    ("ٹاؤن شپ",             "Township"),
    ("سمن آباد",            "Samnabad"),
    ("سبزہ زار",            "Sabzazar"),
    ("گلشنِ راوی",          "Gulshan-e-Ravi"),
    ("شاہدرہ ٹاؤن",        "Shahdara Town"),
    ("باغبانپورہ",          "Baghbanpura"),
    ("مغلپورہ",             "Mughalpura"),
    ("مولانا شوکت علی",    "Maulana Shaukat Ali"),
    ("شاہ عالمی",           "Shah Alam"),
    ("انارکلی",             "Anarkali"),
    ("لوہاری گیٹ",          "Lohari Gate"),
    ("دہلی گیٹ",            "Delhi Gate"),
    ("بھاٹی گیٹ",           "Bhati Gate"),
    ("داتا دربار",          "Data Darbar"),
    ("نیلا گنبد",           "Neela Gumbad"),
    ("ہال روڈ",             "Hall Road"),
    ("ریگل چوک",            "Regal Chowk"),
    ("لبرٹی مارکیٹ",       "Liberty Market"),
    ("شاہراہ قائداعظم",     "Shahrah Quaid-e-Azam"),
    ("شاہراہِ پاکستان",     "Shahrah-e-Pakistan"),
    ("جی ٹی روڈ",           "GT Road"),
    ("ٹنکی والا روڈ",       "Tanki Wala Road"),
    ("کچھہری روڈ",          "Kutchery Road"),
    ("الحمد روڈ",           "Al Hamd Road"),
    ("نجات روڈ",            "Nijat Road"),
    ("برکی روڈ",            "Burki Road"),
    ("رائیونڈ روڈ",         "Raiwind Road"),
    ("نہر کنار روڈ",        "Canal Bank Road"),
    ("روٹی تندور روڈ",      "Roti Tandoor Road"),
    ("اقبال ایونیو",        "Iqbal Avenue"),
    ("خیا ب انِ جناح",       "Khayaban-e-Jinnah"),
    ("خیابانِ جناح",         "Khayaban-e-Jinnah"),
    ("کاماہاں انٹرچینج",     "Kamahan Interchange"),
    ("عبدالحق روڈ",         "Abdul Haq Road"),
    ("لیاقت علی خان روڈ",   "Liaquat Ali Khan Road"),
    ("بیرونی سمن آباد روڈ", "Outer Samnabad Road"),
    ("چونیاں روڈ",          "Chunian Road"),
    ("نشتر روڈ",            "Nishtar Road"),
    ("ریونیو روڈ",          "Revenue Road"),
    ("ڈیفنس روڈ",           "Defence Road"),
    ("شاہ پور کانجراں روڈ", "Shahpur Kanjran Road"),
    ("گجو متہ روڈ",         "Gajumatta Road"),
    ("ایڈن آباد",           "Eden Abad"),
    ("الخضریا ہاؤسنگ",      "Al Khazriya Housing"),
    ("پی آئی اے سوسائٹی",  "PIA Society"),
    ("پی آئی اے سوسائٹی",  "PIA Society"),
    ("نواں کوٹ",            "Nawan Kot"),
    ("بائیک پوائنٹ",        "Bike Point"),
    ("چوبرجی انڈر پاس",     "Chauburji Underpass"),
    ("جناح ایونیو",          "Jinnah Avenue"),
    ("ایم ایم عالم روڈ",    "MM Alam Road"),
    ("مال روڈ",             "Mall Road"),
    ("جیل روڈ",             "Jail Road"),
    ("کینال روڈ",           "Canal Road"),
    ("راوی روڈ",            "Ravi Road"),
    ("والٹن روڈ",           "Walton Road"),
    ("وحدت روڈ",            "Wahdat Road"),
    ("فیروزپور روڈ",        "Ferozepur Road"),
    ("ملتان روڈ",           "Multan Road"),
    ("ریلوے اسٹیشن",        "Railway Station"),
    ("کینٹ",                "Cantt"),
    ("ہربنس پورہ",          "Harbanspura"),
    ("شالامار باغ",        "Shalimar Garden"),
    ("غری شاہو",            "Garhi Shahu"),
    ("مین بلیوارڈ",         "Main Boulevard"),
    ("حفیظ سنٹر",           "Hafeez Centre"),
    ("ایمپوریئم مال",       "Emporium Mall"),
    ("قذافی اسٹیڈیم",       "Gaddafi Stadium"),
    ("اچھرہ",               "Ichhra"),
    ("برکت مارکیٹ",         "Barkat Market"),
    ("گجومتہ",              "Gajumatta"),
    ("گجو متہ",             "Gajumatta"),
    ("نیا زی",              "Niazi"),
    ("بیرونی",              "Outer"),
    ("مین",                 "Main"),
    ("ساگیان",              "Sagian"),
    ("شیخ زید",             "Sheikh Zayed"),
    ("ٹھوکر",               "Thokar"),
    ("نیاز بیگ",            "Niaz Baig"),
    ("بابو صابو",           "Babu Sabu"),
    ("ساگیاں",              "Sagian"),
    ("شاہ پور کانجراں",     "Shahpur Kanjran"),
    ("ریلوے روڈ",           "Railway Road"),
    ("ٹھوکر نیاز بیگ",     "Thokar Niaz Baig"),
    ("بیدیاں روڈ",          "Badian Road"),
    ("آسوکی",               "Asooki"),
    ("سیکٹر",               "Sector"),
    ("فیز",                 "Phase"),
    ("بلاک",                "Block"),
    ("مارکیٹ",              "Market"),
    ("ٹاؤن",                "Town"),
    ("روڈ",                 "Road"),
    ("باغ",                 "Bagh"),
    ("چوک",                 "Chowk"),
    ("بازار",               "Bazaar"),
    ("گیٹ",                 "Gate"),
    ("نزد",                 ""),
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
    """Best-effort Roman Urdu fallback so unknown words are not dropped."""
    out: List[str] = []
    for ch in token:
        out.append(_URDU_CHAR_ROMAN.get(ch, ""))
    roman = "".join(out)
    roman = re.sub(r"(.)\\1{2,}", r"\\1\\1", roman)
    roman = re.sub(r"\b([aeiou]{1,2})([aeiou]+)", r"\\1\\2", roman)
    roman = re.sub(r"\s+", " ", roman).strip(" -_/,.،")
    return roman


def _romanize_remaining_urdu(text: str) -> str:
    def _repl(match: re.Match[str]) -> str:
        token = match.group(0)
        roman = _romanize_urdu_token(token)
        return f" {roman} " if roman else " "

    return URDU_RE.sub(_repl, text)

def _urdu_to_english_area(urdu_str: str) -> str:
    """Translate Urdu area name to English by replacing known keywords."""
    result = urdu_str
    for urdu, english in _URDU_KW:
        result = result.replace(urdu, english)
    # Romanize remaining Urdu fragments instead of dropping them as blanks.
    result = _romanize_remaining_urdu(result).strip()
    result = URDU_RE.sub(" ", result).strip()
    result = re.sub(r"\s+", " ", result).strip()
    # Strip trailing punctuation/separators
    result = result.strip("،,/- ").strip()
    return result


# ── Transliteration: MyMemory API (free, no account, no card) ────────────────
# MyMemory: https://mymemory.translated.net  — 5,000 chars/day free, no key needed.
# For new FIRs (real-time, 1 per submission): always uses MyMemory.
# For bulk backfill (1,780 unique areas): uses keyword-substitution to avoid
# hitting the daily limit; re-run after getting a key if better quality needed.
_MYMEMORY_URL = "https://api.mymemory.translated.net/get"
_URDU_RE_CHECK = re.compile(r"[\u0600-\u06FF\u0750-\u077F\uFB50-\uFDFF\uFE70-\uFEFF]")


def _ascii_fold(text: str) -> str:
    """Strip IAST diacritics so 'maulānā' → 'maulana' for clean display."""
    return unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii").strip()


def _title_case_translit(raw: str) -> str:
    """Capitalise each word, strip extra whitespace."""
    return re.sub(r"\s+", " ", _ascii_fold(raw)).title().strip()


def _keyword_translit(urdu_text: str) -> str:
    """Apply keyword substitution and return title-cased result."""
    sub = _title_case_translit(_urdu_to_english_area(urdu_text))
    return sub if len(sub) >= 4 else urdu_text


def _mymemory_single(urdu_text: str) -> Optional[str]:
    """
    Translate a single Urdu string via MyMemory free API.
    Returns Roman result or None on failure.
    Free tier: 5,000 chars/day, no API key, no account needed.
    """
    try:
        resp = requests.get(
            _MYMEMORY_URL,
            params={"q": urdu_text[:500], "langpair": "ur|en"},
            timeout=8,
        )
        if resp.status_code == 200:
            data = resp.json()
            translated = data.get("responseData", {}).get("translatedText", "")
            # MyMemory returns the original on failure or quota exceeded
            if translated and translated != urdu_text and not _URDU_RE_CHECK.search(translated):
                return re.sub(r"\s+", " ", translated).strip().title()
    except Exception as exc:
        log.debug(f"MyMemory call failed: {exc}")
    return None


def azure_transliterate_batch(texts: List[str]) -> Dict[str, str]:
    """
    Transliterate a batch of Urdu area strings to Roman/English.

    Strategy (hybrid, no paid API needed):
      1. Apply keyword substitution for all texts (instant, handles ~70% of cases).
      2. For texts that still contain significant Urdu, call MyMemory API
         (free, 5,000 chars/day) — but only up to 4,500 chars per run to
         stay safely under the daily limit.
      3. Fall back to keyword result if MyMemory fails or limit exceeded.

    For bulk import (1,780 unique areas) the keyword pass handles most cases.
    For new FIRs (1-2/day) MyMemory gives full quality on every submission.
    """
    result: Dict[str, str] = {}
    unique = list(set(texts))

    # Pass 1: keyword substitution for everything
    for t in unique:
        result[t] = _keyword_translit(t)

    # Pass 2: MyMemory for texts that still have Urdu characters
    chars_used = 0
    DAILY_BUDGET = 4500  # stay under 5K/day limit
    api_count = 0

    for t in unique:
        if not _URDU_RE_CHECK.search(result[t]):  # already clean
            continue
        if chars_used + len(t) > DAILY_BUDGET:
            log.info(f"  MyMemory daily budget reached after {api_count} calls — using keyword for rest")
            break
        translated = _mymemory_single(t)
        if translated:
            result[t] = translated
            chars_used += len(t)
            api_count += 1
            time.sleep(0.35)  # stay well under rate limit

    log.info(f"  Transliteration done: {len(result)} entries ({api_count} via MyMemory, rest keyword)")

    # Fill any gaps for texts not in unique (duplicate originals)
    for t in texts:
        if t not in result:
            result[t] = _keyword_translit(t)

    return result


# ── Geocoding via Nominatim (OpenStreetMap, free) ─────────────────────────────
# Geocode cache: urdu_area → (lat, lon)
_GEOCODE_CACHE: Dict[str, Tuple[float, float]] = {}
_LAST_NOMINATIM = 0.0

# DB areas table loaded into memory for text-match fallback
# area_name → (lat, lon)  — populated in setup_database()
_AREAS_DICT: Dict[str, Tuple[float, float]] = {}


def _load_areas_dict(cursor) -> None:
    """Pre-load the areas table for text-match geocoding fallback."""
    global _AREAS_DICT
    try:
        cursor.execute("SELECT area_name, latitude, longitude FROM areas")
        for row in cursor.fetchall():
            if isinstance(row, dict):
                _AREAS_DICT[row["area_name"]] = (float(row["latitude"]), float(row["longitude"]))
            else:
                _AREAS_DICT[row[0]] = (float(row[1]), float(row[2]))
        log.info(f"✓ Loaded {len(_AREAS_DICT)} area records for geocoding fallback")
    except Exception as exc:
        log.warning(f"Could not load areas table: {exc}")


_NOISE_WORDS = {"the", "and", "for", "lahore", "town", "area", "housing", "colony", "of"}

def _text_match_area(urdu_area: str) -> Tuple[Optional[float], Optional[float]]:
    """
    Text-match fallback: find the best-matching DB area name for a (possibly
    Urdu) address using two tiers:
      1. Full substring match (e.g. "DHA Phase 2" inside "DHA Phase 2 Block W …")
      2. Word-level match: majority of significant words overlap, first word must match
    Longer / more-specific matches win.
    """
    if not _AREAS_DICT:
        return None, None

    en = _urdu_to_english_area(urdu_area).lower()
    en_words = set(re.findall(r"\b[a-z0-9]\w*\b", en))

    best_name: Optional[str] = None
    best_score = 0

    for area_name in _AREAS_DICT:
        an = area_name.lower()

        # Tier 1: full substring
        if an in en:
            score = len(an) * 3
            if score > best_score:
                best_name, best_score = area_name, score
            continue

        # Tier 2: word-level — strip noise words before comparing
        area_words = [w for w in re.findall(r"\b[a-z0-9]\w*\b", an)
                      if w not in _NOISE_WORDS]
        if not area_words:
            continue

        matches = sum(1 for w in area_words if w in en_words)
        frac = matches / len(area_words)
        # First significant word must match; majority must match
        if area_words[0] in en_words and frac >= 0.5:
            score = int(matches * len(an))
            if score > best_score:
                best_name, best_score = area_name, score

    if best_name:
        lat, lon = _AREAS_DICT[best_name]
        log.debug(f"Text-match '{urdu_area[:40]}' → '{best_name}' ({lat:.4f},{lon:.4f})")
        return lat, lon
    return None, None


# ── Canonical area key for geocoding deduplication ───────────────────────────
# Strips from Block / Road onwards  ("DHA Phase 2 Block W …" → "DHA Phase 2")
_BLOCK_STOP_RE = re.compile(
    r"\b(Sub[\s-]?Block|Block|Street|Road|Chowk|Market|Bagh|Gate|Near|Stop)\b.*",
    flags=re.IGNORECASE,
)
# Strips from Sector / Phase onwards  ("LDA City Sector 5 …" → "LDA City")
_SOCIETY_STOP_RE = re.compile(
    r"\b(Sector|Phase|Block|Sub[\s-]?Block|Street|Road|Chowk|Market|Bagh|Gate|Near|Stop|Avenue|Colony)\b.*",
    flags=re.IGNORECASE,
)


def _extract_society(en: str) -> str:
    """
    Return just the top-level housing-society /neighbourhood name.

    Examples:
      "LDA City Sector 5 Block F Sub-Block N Cantt Road" → "LDA City"
      "DHA Phase 2 Block W Sub Block L"                 → "DHA"
      "Bahria Town Sector G Block B Sub Block N"        → "Bahria Town"
      "Gulshan-e-Ravi Block C"                          → "Gulshan-e-Ravi"
    """
    stripped = _SOCIETY_STOP_RE.sub("", en).strip().strip("-,. ")
    stripped = re.sub(r"\s+", " ", stripped).strip()
    return stripped


def _canonical_area_key(urdu_area: str) -> str:
    """
    Reduce a full Urdu/English address to its meaningful base area for
    geocoding deduplication.

    Examples:
      "ڈی ایچ اے فیز 2 بلاک W سب بلاک L، Babu Sabu" → "DHA Phase 2"
      "Bahria Town Sector G Block B Sub Block N"      → "Bahria Town Sector G"
      "گلبرگ لاہور"                                    → "Gulberg Lahore"
    """
    first_urdu = urdu_area.split("،")[0].split(",")[0].strip()
    en = _urdu_to_english_area(first_urdu)
    stripped = _BLOCK_STOP_RE.sub("", en).strip().strip("-,. ")
    stripped = re.sub(r"\s+", " ", stripped).strip()
    # Keep at most 4 words so "Bahria Town Sector G" doesn't become too specific
    words = stripped.split()
    key = " ".join(words[:4]) if words else en
    return key or urdu_area.strip()


NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
NOMINATIM_HEADERS = {
    "User-Agent": "CrimeVision-FIR-Importer/1.0 (Educational Research Project)"
}
DEFAULT_LAT, DEFAULT_LON = 31.5204, 74.3587  # Lahore city centre fallback

# Lahore approximate bounding box: (min_lon, min_lat, max_lon, max_lat)
_LAHORE_VIEWBOX = "74.10,31.25,74.70,31.75"

# Lahore geographic bounds for sanity-checking returned coordinates
_LAT_MIN, _LAT_MAX = 31.25, 31.75
_LON_MIN, _LON_MAX = 74.10, 74.70


def _in_lahore(lat: Optional[float], lon: Optional[float]) -> bool:
    """Return True if the coordinates fall within the Lahore bounding box."""
    if lat is None or lon is None:
        return False
    return _LAT_MIN <= lat <= _LAT_MAX and _LON_MIN <= lon <= _LON_MAX

# Specificity score for OSM result types — higher is better (more precise)
_OSM_SPECIFICITY: Dict[str, int] = {
    "road": 100, "footway": 90, "path": 90, "pedestrian": 90,
    "residential": 85, "unclassified": 80, "service": 75,
    "neighbourhood": 70, "quarter": 65,
    "suburb": 60, "village": 55, "hamlet": 55,
    "city_district": 30, "county": 20,
    "administrative": 10, "city": 5, "town": 8, "state": 2,
}


def _result_specificity(result: dict) -> int:
    """Return a specificity score for a single Nominatim result dict."""
    r_type  = (result.get("type")  or "").lower()
    r_class = (result.get("class") or "").lower()
    # Roads by class
    if r_class == "highway":
        return 100
    # Named places by type
    score = _OSM_SPECIFICITY.get(r_type, 0)
    if score == 0:
        score = _OSM_SPECIFICITY.get(r_class, 0)
    return score


def _nominatim_lookup(query: str) -> Tuple[Optional[float], Optional[float]]:
    """
    Call Nominatim API (1 req/sec rate limit).
    Requests up to 5 candidates and returns the **most specific** one
    (road > neighbourhood > suburb > admin boundary), ignoring overly
    broad administrative/city results unless no better option exists.
    """
    global _LAST_NOMINATIM
    elapsed = time.time() - _LAST_NOMINATIM
    if elapsed < 1.05:
        time.sleep(1.05 - elapsed)
    try:
        params = {
            "q": query,
            "format": "json",
            "limit": 5,
            "addressdetails": 1,
            "countrycodes": "pk",
            # Strictly bound to Lahore — prevents false matches in Karachi/Islamabad
            "viewbox": _LAHORE_VIEWBOX,
            "bounded": 1,
        }
        resp = requests.get(NOMINATIM_URL, params=params, headers=NOMINATIM_HEADERS, timeout=10)
        _LAST_NOMINATIM = time.time()
        if resp.status_code != 200:
            return None, None
        data = resp.json()
        if not data:
            return None, None

        # Sort candidates by specificity descending; keep the best one
        data_sorted = sorted(data, key=_result_specificity, reverse=True)
        best = data_sorted[0]
        best_score = _result_specificity(best)

        # If the best result is still a city/admin-level hit (score ≤ 10),
        # skip it so the caller can try a more-specific query instead.
        if best_score <= 10:
            log.debug(f"Nominatim '{query[:50]}' → only admin-level result "
                      f"({best.get('type')}/{best.get('class')}) — skipping")
            return None, None

        log.debug(f"Nominatim '{query[:50]}' → {best.get('type')}/{best.get('class')} "
                  f"score={best_score} [{best.get('display_name','')[:60]}]")
        return float(best["lat"]), float(best["lon"])
    except Exception as exc:
        log.debug(f"Nominatim error for '{query}': {exc}")
    return None, None

def _nominatim_lookup_relaxed(query: str) -> Tuple[Optional[float], Optional[float]]:
    """
    Like _nominatim_lookup but accepts ANY result including admin-level areas.
    Used as last resort before the Lahore-centre default.
    """
    global _LAST_NOMINATIM
    elapsed = time.time() - _LAST_NOMINATIM
    if elapsed < 1.05:
        time.sleep(1.05 - elapsed)
    try:
        params = {
            "q": query,
            "format": "json",
            "limit": 1,
            "countrycodes": "pk",
            # Strictly bound to Lahore — prevents false city fallbacks
            "viewbox": _LAHORE_VIEWBOX,
            "bounded": 1,
        }
        resp = requests.get(NOMINATIM_URL, params=params, headers=NOMINATIM_HEADERS, timeout=10)
        _LAST_NOMINATIM = time.time()
        if resp.status_code == 200:
            data = resp.json()
            if data:
                return float(data[0]["lat"]), float(data[0]["lon"])
    except Exception as exc:
        log.debug(f"Nominatim relaxed error for '{query}': {exc}")
    return None, None

def _make_queries(urdu_area: str) -> List[str]:
    """
    Build an ordered list of Nominatim query strings for an Urdu area name,
    coarsest-first so that the top-level housing society / neighbourhood is
    tried before street-level noise can pull Nominatim to the wrong area.

    Query order:
      1. Society-only  ("LDA City, Lahore, Pakistan")          ← best signal
      2. Block-stripped ("LDA City Sector 5, Lahore, Pakistan")
      3. Full comma    ("LDA City Sector 5 Block F …, Lahore, Pakistan")
      4. Full space    (same without commas)
      5. Urdu native   ("ایل ڈی اے سٹی، لاہور")
    """
    first_urdu = urdu_area.split("،")[0].split(",")[0].split("/")[0].strip()
    first_en   = _urdu_to_english_area(first_urdu)
    full_en    = _urdu_to_english_area(urdu_area)

    queries: List[str] = []

    if first_en and not URDU_RE.search(first_en):
        # 1. Society-only: strip from Sector/Phase onwards
        society = _extract_society(first_en)
        if society and society != first_en:
            queries.append(f"{society}, Lahore, Pakistan")

        # 2. Block-stripped: strip from Block/Road onwards (keeps Sector N)
        block_stripped = _BLOCK_STOP_RE.sub("", first_en).strip().strip("-,. ")
        block_stripped = re.sub(r"\s+", " ", block_stripped).strip()
        if block_stripped and block_stripped not in (first_en, society):
            queries.append(f"{block_stripped}, Lahore, Pakistan")

        # 3. Full English translation — comma-separated
        queries.append(f"{first_en}, Lahore, Pakistan")

        # 4. Full multi-segment translation
        if full_en and full_en != first_en and not URDU_RE.search(full_en):
            queries.append(f"{full_en}, Lahore, Pakistan")

        # 5. Space-separated fallback
        queries.append(f"{first_en} Lahore Pakistan")

    # 6. Original Urdu + city (Nominatim handles Urdu text natively)
    queries.append(f"{first_urdu}، لاہور")
    queries.append(f"{first_urdu} Lahore Pakistan")

    # De-duplicate while preserving order
    seen: set = set()
    unique: List[str] = []
    for q in queries:
        if q not in seen:
            seen.add(q)
            unique.append(q)
    return unique


def geocode_area(urdu_area: str) -> Tuple[float, float]:
    """
    Geocode a (potentially Urdu) area name → (lat, lon).

    Priority order:
      1. DB text-match (our curated areas table — always most reliable)
      2. Nominatim (specific results only: roads, suburbs, neighbourhoods)
      3. Nominatim relaxed (accepts admin-level results as last resort)
      4. Default Lahore city-centre coords
    """
    cache_key = urdu_area.strip()
    if cache_key in _GEOCODE_CACHE:
        return _GEOCODE_CACHE[cache_key]

    # Pass 1: Try our curated areas table first (fast, zero API calls)
    lat, lon = _text_match_area(urdu_area)
    if lat is not None:
        if _in_lahore(lat, lon):
            log.debug(f"  Text-match for '{cache_key[:50]}'")
            _GEOCODE_CACHE[cache_key] = (lat, lon)
            return lat, lon
        else:
            log.warning(f"  Areas table returned out-of-Lahore coords for '{cache_key[:40]}' "
                        f"({lat:.4f},{lon:.4f}) — skipping, falling to Nominatim")

    # Pass 2: Nominatim — specific results only (admin-level skipped)
    queries = _make_queries(urdu_area)
    lat, lon = None, None
    for q in queries:
        lat, lon = _nominatim_lookup(q)
        if lat is not None:
            log.debug(f"Geocoded '{cache_key[:40]}' via '{q[:55]}' → {lat:.4f},{lon:.4f}")
            break

    # Pass 3: Nominatim relaxed — accept admin-level results if nothing better found
    if lat is None:
        for q in queries:
            rlat, rlon = _nominatim_lookup_relaxed(q)
            if rlat is not None and _in_lahore(rlat, rlon):
                lat, lon = rlat, rlon
                log.debug(f"Geocoded (relaxed) '{cache_key[:40]}' via '{q[:55]}' → {lat:.4f},{lon:.4f}")
                break

    if lat is None:
        log.warning(f"  ⚠ No geocode for '{cache_key[:50]}' — using Lahore centre")
        lat, lon = DEFAULT_LAT, DEFAULT_LON

    _GEOCODE_CACHE[cache_key] = (lat, lon)
    return lat, lon


# ── Nearest English area from DB ─────────────────────────────────────────────
_NOISE_AREA = {"the", "and", "for", "lahore", "town", "area", "housing",
               "colony", "of", "road", "block", "sub", "phase",
               "sector", "interchange", "main", "boulevard"}

def nearest_area_name(lat: float, lon: float, cursor,
                      translit_hint: str = "") -> str:
    """
    Return the best-matching English area name from the `areas` table.

    Strategy (in priority order):
      1. Text-match: if `translit_hint` contains words that uniquely identify
         a known area name, return that area directly (avoids geocoding drift).
      2. Haversine: fall back to the geographically nearest area entry.
    """
    # ── Step 1: text-match against known area names ───────────────────────────
    if translit_hint:
        try:
            cursor.execute("SELECT area_name FROM areas")
            all_areas = cursor.fetchall()
            hint_lower = translit_hint.lower()
            hint_words = [
                w for w in re.findall(r"\b[a-z0-9]\w*\b", hint_lower)
                if w not in _NOISE_AREA and len(w) > 2
            ]
            best_name, best_score = "", 0
            for row in all_areas:
                an = (row[0] if isinstance(row, (list, tuple)) else row["area_name"]).lower()
                an_words = [
                    w for w in re.findall(r"\b[a-z0-9]\w*\b", an)
                    if w not in _NOISE_AREA and len(w) > 2
                ]
                if not an_words:
                    continue
                matches = sum(1 for w in an_words if w in hint_words)
                frac = matches / len(an_words)
                # Require first meaningful word of area name to appear in hint
                # and at least 60% word coverage
                if an_words[0] in hint_words and frac >= 0.60:
                    score = frac + matches * 0.1
                    if score > best_score:
                        best_score = score
                        best_name = (row[0] if isinstance(row, (list, tuple))
                                     else row["area_name"])
            if best_name:
                log.debug(f"text-match '{translit_hint[:50]}' → '{best_name}'")
                return best_name
        except Exception as exc:
            log.debug(f"nearest_area_name text-match failed (non-fatal): {exc}")

    # ── Step 2: Haversine nearest-area fallback ───────────────────────────────
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
            return row[0] if isinstance(row, (list, tuple)) else row["area_name"]
    except Exception as exc:
        log.warning(f"nearest_area_name failed: {exc}")
    return "Lahore"


def _resolve_plot_area(translit_hint: str, nearest_area: str) -> str:
    """
    Resolve canonical `crimes.area` for map plotting.
    Uses FIR text first for known boundary-sensitive schemes, then falls back to nearest-area.
    Prevents cross-contamination between Valencia, Lake City, and other housing societies.
    """
    hint = (translit_hint or "").lower()

    _dha = re.search(r"dha\s*phase\s*(\d+)", hint)
    if _dha:
        phase_num = int(_dha.group(1))
        if 1 <= phase_num <= 9:
            return f"DHA Phase {phase_num}"

    if "badami bagh" in hint:
        return "Badami Bagh, Lahore"

    if "data darbar" in hint:
        return "Data Darbar, Lahore"

    if "anarkali" in hint:
        return "Anarkali, Lahore"

    if "lohari gate" in hint:
        return "Lohari Gate, Lahore"

    if "delhi gate" in hint:
        return "Delhi Gate, Lahore"

    if "bhati gate" in hint:
        return "Bhati Gate, Lahore"

    if "mazang road" in hint or "santanagar chowk" in hint:
        return "Mazang, Lahore"

    if "pcsir" in hint:
        return "PCSIR Housing Scheme"

    # Valencia Town — must be Defence/Raiwind/Asooki/Awan/Gajumatta context, NOT MM Alam/Walton/Samnabad/Cantt/GT/Sheikh Zayed
    if "valencia town block" in hint or "valencia housing society" in hint:
        # Accept only these roads for Valencia
        if "defence road" in hint or "asooki road" in hint or "awan road" in hint or "gajumatta" in hint or "multan road" in hint:
            return "Valencia Housing Society"
        # Reject these wrong zones
        if "mm alam" in hint or "walton" in hint or "samnabad" in hint or "cantt road" in hint or "gt road" in hint or "sheikh zayed" in hint or "mall road" in hint or "iqbal avenue" in hint:
            return nearest_area or "Lahore"  # fallback to geocoded area

    # Lake City — only valid for Sectors M1-M8 with Defence/Raiwind/Asooki, NOT Bahria/PIA/Eden/Al-Khadriya and NOT MM Alam/Walton/Samnabad/Cantt/Barki/Sagian/Niazi
    if "lake city sector m" in hint:
        if "defence road" in hint or "raiwind road" in hint or "asooki road" in hint or "revenue road" in hint or "waris road" in hint:
            return "Lake City"
        # Reject if mixed with other societies or wrong roads
        if "bahria" in hint or "pia" in hint or "eden abad" in hint or "khadriya" in hint:
            return nearest_area or "Lahore"  # remap to actual society
        if "mm alam" in hint or "walton" in hint or "samnabad" in hint or "cantt road" in hint or "barki road" in hint or "sagian" in hint or "niazi" in hint:
            return nearest_area or "Lahore"

    # Bahria Orchard — separate society, never Lake City
    if "bahria orchard" in hint or "bahria phase" in hint:
        return "Bahria Orchard, Lahore"

    # PIA Society — separate society, never Valencia or Lake City
    if "pia society" in hint or "pia housing" in hint:
        return "PIA Housing Society"

    # Eden Abad — separate society, never Valencia or Lake City
    if "eden abad" in hint:
        return "Raiwind Road, Lahore"

    # Al-Khadriya — separate society, never Valencia or Lake City
    if "khadriya housing" in hint or "al-khadriya" in hint:
        return "Cantt"

    if "ravi road ravi road" in hint or hint.strip() == "ravi road":
        return "Ravi Town, Lahore"

    if "cantt saddar bazaar" in hint and "saddar bazaar road" in hint:
        return "Cantt"

    if "fauji colony cantt" in hint:
        return "Cantt"

    if "sarfaraz road cantt" in hint and "gajumatta" in hint:
        return "Cantt"

    if "lal kurti" in hint and "thokar niaz baig" in hint:
        return "Lal Kurti, Cantt"

    if "pia society" in hint and "cantt road" in hint:
        return "PIA Housing Society"

    if "fortress stadium area" in hint and "sub-block k" in hint:
        return "Cantt"

    if "chuburji" in hint:
        return "Chuburji, Lahore"

    if "canal road" in hint or "nehar kinara" in hint:
        if "lal kurti" in hint and "cantt" in hint:
            return "Cantt"
        return "Canal Road, Lahore"

    if hint.strip() == "jail road" or "jail road jail road" in hint:
        return "Ichhra, Lahore"

    if "township madina chowk" in hint or "jamia ashrafia" in hint:
        return "Township"

    if "shalimar bagh" in hint and "gt road" in hint:
        return "Shalimar Bagh / GT Road"

    if "shahdara town" in hint and "ravi road" in hint:
        return "Shahdara"

    if "allama iqbal town" in hint and "karim block" in hint:
        return "Allama Iqbal Town"

    if "samanabad main boulevard" in hint:
        return "Samanabad"

    if "qainchi" in hint or "amer sidhu" in hint:
        return "Qainchi Amer Sidhu"

    if "kamahan interchange" in hint:
        return "Kamahan Interchange"

    if "bahria orchard" in hint:
        return "Bahria Orchard, Lahore"

    if "eden abad" in hint or "shahpur kanjran" in hint:
        return "Raiwind Road, Lahore"

    if "pia society" in hint:
        return "PIA Housing Society"

    if "al-khadriya" in hint and ("walton road" in hint or "thokar niaz baig" in hint or "roti tandoor" in hint):
        return "Cantt"

    if "kutchery road" in hint:
        return "Kutchery Road, Lahore"

    if "thokar niaz baig" in hint:
        return "Thokar Niaz Baig"

    # Guardrail: if nearest-area geocoding drifts to Gulshan-e-Ravi, override for known out-of-zone markers.
    if (nearest_area or "").lower() == "gulshan-e-ravi":
        if "sheikh zayed" in hint or "khayaban-e-jinnah" in hint:
            return "Canal Road, Lahore"
        if "walton road" in hint:
            return "Cantt"
        if "chunian road" in hint:
            return "Raiwind Road, Lahore"
        if "roti tandoor" in hint:
            return "Cantt"

    if "bahria town" in hint:
        return "Bahria Town, Lahore"

    if "lda city" in hint:
        return "LDA City"

    if "wapda town" in hint:
        return "Wapda Town"

    _dha = re.search(r"dha\s*phase\s*(\d+)", hint)
    if _dha:
        return f"DHA Phase {_dha.group(1)}"

    _askari = re.search(r"askari\s*(\d+)", hint)
    if _askari:
        return f"Askari {_askari.group(1)}"

    if "askari" in hint:
        return "Askari"

    if "shad bagh" in hint or "shadbagh" in hint:
        return "Shad Bagh, Lahore"

    # Valencia Town — must be Defence/Raiwind/Asooki/Awan/Gajumatta context, NOT MM Alam/Walton/Samnabad/Cantt/GT/Sheikh Zayed
    if "valencia town block" in hint or "valencia housing society" in hint:
        # Accept only these roads for Valencia
        if "defence road" in hint or "asooki road" in hint or "awan road" in hint or "gajumatta" in hint or "multan road" in hint:
            return "Valencia Housing Society"
        # Reject these wrong zones
        if "mm alam" in hint or "walton" in hint or "samnabad" in hint or "cantt road" in hint or "gt road" in hint or "sheikh zayed" in hint or "mall road" in hint or "iqbal avenue" in hint:
            return nearest_area or "Lahore"  # fallback to geocoded area

    # Lake City — only valid for Sectors M1-M8 with Defence/Raiwind/Asooki, NOT Bahria/PIA/Eden/Al-Khadriya and NOT MM Alam/Walton/Samnabad/Cantt/Barki/Sagian/Niazi
    if "lake city sector m" in hint:
        if "defence road" in hint or "raiwind road" in hint or "asooki road" in hint or "revenue road" in hint or "waris road" in hint:
            return "Lake City"
        # Reject if mixed with other societies or wrong roads
        if "bahria" in hint or "pia" in hint or "eden abad" in hint or "khadriya" in hint:
            return nearest_area or "Lahore"  # remap to actual society
        if "mm alam" in hint or "walton" in hint or "samnabad" in hint or "cantt road" in hint or "barki road" in hint or "sagian" in hint or "niazi" in hint:
            return nearest_area or "Lahore"

    # Bahria Orchard — separate society, never Lake City
    if "bahria orchard" in hint or "bahria phase" in hint:
        return "Bahria Orchard, Lahore"

    # PIA Society — separate society, never Valencia or Lake City
    if "pia society" in hint or "pia housing" in hint:
        return "PIA Housing Society"

    # Eden Abad — separate society, never Valencia or Lake City
    if "eden abad" in hint:
        return "Raiwind Road, Lahore"

    # Al-Khadriya — separate society, never Valencia or Lake City
    if "khadriya housing" in hint or "al-khadriya" in hint:
        return "Cantt"

    return nearest_area or "Lahore"


# ── Risk level from severity_map.json ─────────────────────────────────────────
def risk_from_severity(crime_name: str) -> str:
    """
    Derive High/Medium/Low from crime name against severity_map.json.
    This is the correct model for the crimes.risk_level column.
    (The predict_risk_level model is for future crime predictions,
     crime_risk_model is for real-time risk overlays — neither is for DB insertion.)
    """
    if not _SEVERITY_MAP:
        return "Medium"
    n = crime_name.lower()
    best: float = 0.0
    for key, score in _SEVERITY_MAP.items():
        key_words = [w for w in
                     key.replace("(", "").replace(")", "").replace("-", " ").split()
                     if len(w) > 3]
        if not key_words:
            continue
        hits = sum(1 for w in key_words if w in n)
        if hits:
            weighted = (hits / len(key_words)) * float(score)
            if weighted > best:
                best = weighted
    if best >= 7.5: return "High"
    if best >= 4.5: return "Medium"
    if best > 0:    return "Low"
    return "Medium"


# ── Section parsing ───────────────────────────────────────────────────────────
_KNOWN_LAWS = {"ATA", "CNSA", "ARMS", "PECA", "MPO", "PA", "EPFO"}


def _normalize_one(raw: str) -> str:
    """
    Normalise a single raw section token to the format expected by get_crime_name.

    Handles:
      148 ت پ      → 148
      7-ATA        → ATA-7
      ATA-7        → ATA-7
      120-B ت پ    → 120-B
      506/B        → 506-B
      124A         → 124-A
      153A         → 153-A
      CNSA-6       → CNSA-6
    """
    s = raw.strip()
    # Remove Urdu chars
    s = URDU_RE.sub(" ", s).strip()
    s = re.sub(r"\s+", " ", s).strip()
    if not s:
        return ""

    # Normalise slash separator in sub-sections: 506/B → 506-B
    # Only if right side is a single letter (not a whole second section like 379/381)
    slash_m = re.match(r"^(\d[\d-]*)/([A-Za-z])$", s)
    if slash_m:
        s = slash_m.group(1) + "-" + slash_m.group(2).upper()

    # Fix missing hyphen before letter suffix: 124A → 124-A
    s = re.sub(r"(\d{2,})([A-Za-z])$", lambda m: m.group(1) + "-" + m.group(2).upper(), s)

    # Normalise space between number and letter: 120 B → 120-B
    s = re.sub(r"(\d+)\s+([A-Za-z])$", r"\1-\2", s)

    # Normalise NUMBER-LAWNAME → LAWNAME-NUMBER  (e.g. 7-ATA → ATA-7)
    m = re.match(r"^(\d+(?:-[A-Z])?)-([A-Za-z]{2,})$", s)
    if m:
        num_part, law_part = m.group(1), m.group(2).upper()
        if law_part in _KNOWN_LAWS:
            s = f"{law_part}-{num_part}"
            return s

    # If it starts with letter prefix (e.g. ATA-7, CNSA-6) – keep as is
    m = re.match(r"^([A-Za-z]{2,})-(.+)$", s)
    if m and m.group(1).upper() in _KNOWN_LAWS:
        return f"{m.group(1).upper()}-{m.group(2).strip()}"

    # Strip any leading non-numeric word that isn't a known law prefix
    # e.g. "chori - 379" → "379"
    m = re.match(r"^[A-Za-z\s]+-\s*(\d.*)$", s)
    if m:
        candidate = m.group(1).strip()
        if re.search(r"\d", candidate):
            s = candidate

    s = s.strip()
    if not re.search(r"\d", s):
        return ""
    return s


def parse_sections(raw: str) -> List[str]:
    """
    Parse the sections field from fir_data_2500.txt.
    Returns list of clean section tokens ready for get_crime_name().
    """
    sections: List[str] = []
    for part in raw.split(";"):
        part = part.strip()
        if not part:
            continue

        # Remove Urdu characters to isolate section portion
        cleaned = URDU_RE.sub(" ", part).strip()
        cleaned = re.sub(r"\s+", " ", cleaned).strip()

        # Check for slash-separated pair of sections like 379/381
        # (but NOT letter suffixes like 506/B — handled in _normalize_one)
        if "/" in cleaned:
            slash_parts = cleaned.split("/")
            # If all parts are purely numeric-ish, treat as separate sections
            if all(re.match(r"^\d[\d-]*[A-Za-z]?$", p.strip()) for p in slash_parts):
                for sp in slash_parts:
                    n = _normalize_one(sp.strip())
                    if n:
                        sections.append(n)
                continue

        n = _normalize_one(cleaned)
        if n:
            sections.append(n)

    return sections


# ── Date / time parsing ───────────────────────────────────────────────────────
_DATE_TIME_PATTERNS = [
    # "08:53PM 12-02-2025"  or  "08:53 PM 12-02-2025"
    re.compile(r"(\d{1,2}:\d{2})\s*([AaPp][Mm])\s+(\d{1,2}-\d{1,2}-\d{4})"),
    # "24-01-2023 05:46 PM"  or  "24-01-2023 05:46PM"
    re.compile(r"(\d{1,2}-\d{1,2}-\d{4})\s+(\d{1,2}:\d{2})\s*([AaPp][Mm])"),
]


def parse_datetime_field(raw: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Parse the datetime field from fir_data_2500.txt.
    Returns (date_ISO, time_str) where:
      date_ISO = "YYYY-MM-DD"
      time_str = "HH:MM AM"  (or None if not found)
    """
    raw = raw.strip()

    # Pattern 1: time first  → "08:53PM 12-02-2025"
    m = _DATE_TIME_PATTERNS[0].search(raw)
    if m:
        t, ampm, d = m.group(1), m.group(2).upper(), m.group(3)
        parts = d.split("-")
        date_iso = f"{parts[2]}-{parts[1].zfill(2)}-{parts[0].zfill(2)}"
        return date_iso, f"{t} {ampm}"

    # Pattern 2: date first  → "24-01-2023 05:46 PM"
    m = _DATE_TIME_PATTERNS[1].search(raw)
    if m:
        d, t, ampm = m.group(1), m.group(2), m.group(3).upper()
        parts = d.split("-")
        date_iso = f"{parts[2]}-{parts[1].zfill(2)}-{parts[0].zfill(2)}"
        return date_iso, f"{t} {ampm}"

    # Date only fallback
    m = re.search(r"(\d{1,2}-\d{1,2}-\d{4})", raw)
    if m:
        parts = m.group(1).split("-")
        date_iso = f"{parts[2]}-{parts[1].zfill(2)}-{parts[0].zfill(2)}"
        return date_iso, None

    return None, None


# ── Database setup / teardown ─────────────────────────────────────────────────
def setup_database():
    """Add crime_time column (if missing) and truncate crimes table."""
    from app.core.database import get_db_connection
    conn = get_db_connection()
    cursor = conn.cursor()

    # Add crime_time column if not present
    cursor.execute("SHOW COLUMNS FROM crimes LIKE 'crime_time'")
    if not cursor.fetchone():
        log.info("Adding  crimes.crime_time  VARCHAR(20) column…")
        cursor.execute("ALTER TABLE crimes ADD COLUMN crime_time VARCHAR(20) DEFAULT NULL AFTER crime_date")
        conn.commit()
        log.info("✓ crime_time column added")
    else:
        log.info("crime_time column already exists — skipping ALTER")

    # Add area_translit column if not present
    cursor.execute("SHOW COLUMNS FROM crimes LIKE 'area_translit'")
    if not cursor.fetchone():
        log.info("Adding  crimes.area_translit  VARCHAR(255) column…")
        cursor.execute(
            "ALTER TABLE crimes ADD COLUMN area_translit VARCHAR(255) DEFAULT NULL AFTER area_urdu"
        )
        conn.commit()
        log.info("✓ area_translit column added")
    else:
        log.info("area_translit column already exists — skipping ALTER")

    # Clear existing data
    log.info("Truncating crimes table…")
    cursor.execute("SET FOREIGN_KEY_CHECKS = 0")
    cursor.execute("TRUNCATE TABLE crimes")
    cursor.execute("SET FOREIGN_KEY_CHECKS = 1")
    conn.commit()
    log.info("✓ crimes table cleared")

    # Pre-load areas for geocoding fallback
    _load_areas_dict(cursor)

    cursor.close()
    conn.close()


# ── Main import logic ─────────────────────────────────────────────────────────
def import_fir_data():
    from app.core.database import get_db_connection
    from app.ocr.ppc_sections import get_crime_name

    conn = get_db_connection()
    cursor = conn.cursor()

    # Read data file
    if not os.path.exists(DATA_FILE):
        log.error(f"Data file not found: {DATA_FILE}")
        sys.exit(1)

    with open(DATA_FILE, "r", encoding="utf-8") as fh:
        lines = [l.rstrip("\n") for l in fh if l.strip()]

    log.info(f"Loaded {len(lines)} FIR records from {os.path.basename(DATA_FILE)}")

    total_rows = 0
    total_firs = 0
    skipped   = 0
    geocode_errors = 0

    # Pre-collect unique areas so we log geocoding progress sensibly
    unique_areas = set()
    parsed_records = []

    log.info("Phase 1 / 2 — Parsing all records…")
    for line_no, line in enumerate(lines, 1):
        parts = [p.strip() for p in line.split("|")]
        if len(parts) < 4:
            log.warning(f"  Line {line_no}: malformed (only {len(parts)} fields) — skipped")
            skipped += 1
            continue

        fir_id     = parts[0].strip()
        area_urdu  = parts[1].strip()
        sections   = parse_sections(parts[2])
        date_iso, time_str = parse_datetime_field(parts[3])

        if not sections:
            log.warning(f"  {fir_id}: no valid sections parsed — skipped")
            skipped += 1
            continue

        if not date_iso:
            log.warning(f"  {fir_id}: could not parse date from '{parts[3]}' — skipped")
            skipped += 1
            continue

        unique_areas.add(area_urdu)
        parsed_records.append((fir_id, area_urdu, sections, date_iso, time_str))

    log.info(f"  Parsed {len(parsed_records)} valid records, {len(unique_areas)} unique areas")

    # ── Phase 2: canonical-key deduplication + geocoding ──────────────────
    # Many detailed Urdu addresses (e.g. "DHA Phase 2 Block W Sub Block L, …"
    # and "DHA Phase 2 Block X Sub Block Y, …") reduce to the same base area
    # ("DHA Phase 2").  We geocode the canonical key ONCE and share the result
    # with all sibling addresses, cutting API calls from ~1700 to ~100-200.
    canonical_to_areas: Dict[str, List[str]] = {}
    for area in unique_areas:
        ckey = _canonical_area_key(area)
        canonical_to_areas.setdefault(ckey, []).append(area)

    canonical_count = len(canonical_to_areas)
    log.info(
        f"Phase 2 / 2 — Geocoding {canonical_count} canonical areas "
        f"(deduplicated from {len(unique_areas)}, Nominatim 1 req/sec)..."
    )

    geocoded = 0
    for ckey, siblings in canonical_to_areas.items():
        # Try to geocode the canonical key (already English-translated)
        lat, lon = None, None
        if ckey and not URDU_RE.search(ckey):
            # Query 1: exact canonical key
            lat, lon = _nominatim_lookup(f"{ckey} Lahore Pakistan")
            # Query 2: first 3 words (e.g. "DHA Phase 2" from "DHA Phase 2 Sector A")
            if lat is None:
                words = ckey.split()
                if len(words) > 3:
                    lat, lon = _nominatim_lookup(f'{" ".join(words[:3])} Lahore Pakistan')
        # Text-match fallback using first sibling's Urdu string
        if lat is None:
            lat, lon = _text_match_area(siblings[0])
        if lat is None:
            log.warning(f"  ⚠ No geocode for '{ckey[:50]}' — using Lahore centre")
            lat, lon = DEFAULT_LAT, DEFAULT_LON
            geocode_errors += 1

        # Write result to cache for ALL sibling areas
        for sibling in siblings:
            _GEOCODE_CACHE[sibling.strip()] = (lat, lon)

        geocoded += 1
        if geocoded % 25 == 0 or geocoded == canonical_count:
            log.info(f"  Geocoded {geocoded} / {canonical_count} canonical areas...")

    # ── Phase 3: Transliterate all unique Urdu addresses ─────────────────────
    all_urdu_areas = list({rec[1] for rec in parsed_records})
    translit_map = azure_transliterate_batch(all_urdu_areas)

    log.info("Inserting rows into crimes table...")
    for fir_id, area_urdu, sections, date_iso, time_str in parsed_records:
        # Compute transliteration first so it can be used as a text-match hint
        # for area assignment (more reliable than geocoding for known localities)
        area_translit = translit_map.get(area_urdu, _title_case_translit(_urdu_to_english_area(area_urdu)))
        lat, lon      = geocode_area(area_urdu)   # from cache, no API call
        nearest_area  = nearest_area_name(lat, lon, cursor, translit_hint=area_translit)
        area_en       = _resolve_plot_area(area_translit, nearest_area)

        for section in sections:
            crime_name, law_type = get_crime_name(section)
            risk = risk_from_severity(crime_name)
            description = (
                f"FIR {fir_id} — §{section} {law_type}: {crime_name} "
                f"| Area: {area_urdu}"
            )
            cursor.execute(
                """
                INSERT INTO crimes
                    (crime_date, crime_time, area, area_urdu, area_translit,
                     crime_type, latitude, longitude, risk_level,
                     source, status, description, created_at)
                VALUES
                    (%s, %s, %s, %s, %s,
                     %s, %s, %s, %s,
                     %s, %s, %s, %s)
                """,
                (
                    date_iso,
                    time_str,
                    area_en,
                    area_urdu,
                    area_translit,
                    crime_name,              # English crime name (not section number)
                    lat,
                    lon,
                    risk,
                    "admin",
                    "verified",
                    description,
                    datetime.now(),
                ),
            )
            total_rows += 1

        total_firs += 1
        if total_firs % 250 == 0:
            conn.commit()
            log.info(f"  [{total_firs} FIRs / {total_rows} rows inserted…]")

    conn.commit()
    cursor.close()
    conn.close()

    log.info("=" * 60)
    log.info(f"✓ Import complete")
    log.info(f"  FIRs processed : {total_firs}")
    log.info(f"  Rows inserted  : {total_rows}")
    log.info(f"  FIRs skipped   : {skipped}")
    log.info(f"  Geocode fallbacks (Lahore centre used): {geocode_errors}")
    log.info("=" * 60)


if __name__ == "__main__":
    log.info("=" * 60)
    log.info("CrimeVision — FIR Data Import")
    log.info("=" * 60)
    setup_database()
    import_fir_data()

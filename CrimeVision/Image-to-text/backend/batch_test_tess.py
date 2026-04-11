"""
Batch test crime area extraction using Tesseract only (no EasyOCR/PyTorch).
This saves ~500MB RAM, allowing processing of large FIR images.
"""
import cv2
import sys
import os
import gc
import re
import time
import numpy as np

os.environ['DISABLE_MODEL_SOURCE_CHECK'] = 'True'

if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

import pytesseract
from urdu_location_dictionary import correct_location_text, _urdu_similarity, _normalize_text

IMAGE_DIR = r"D:\FYP\Project\CrimeVision\OCRModel\app\data\raw"
SUMMARY_FILE = os.path.join(os.path.dirname(__file__), "fir_summary.txt")

# Region coordinates for crime area (Row 4) - multiple strips for robustness
# The crime area text is at different Y positions depending on image format
CRIME_STRIPS = [
    # (top, bottom, left, right) - overlapping vertical strips
    (0.38, 0.451, 0.29, 0.62),  # Original narrow region (proven for large format)
    (0.39, 0.49, 0.20, 0.70),  # Wide: captures text for both large + small format
    (0.41, 0.49, 0.20, 0.70),  # Lower strip: small format images often have text here
    (0.43, 0.50, 0.20, 0.70),  # Lowest strip: catches text at very bottom of row
]


def parse_summary(path):
    """Parse fir_summary.txt into {filename: expected_area} dict."""
    entries = {}
    with open(path, 'r', encoding='utf-8') as f:
        lines = f.read().strip().split('\n')
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if line.startswith('FIR_') and line.endswith('.png'):
            fname = line
            i += 1
            while i < len(lines) and not lines[i].strip():
                i += 1
            if i < len(lines) and not lines[i].strip().startswith('FIR_'):
                area = lines[i].strip()
                entries[fname] = area
            continue
        i += 1
    return entries


def extract_first_location(full_area: str) -> str:
    parts = full_area.split('،')
    if not parts:
        parts = full_area.split(',')
    return parts[0].strip()


def is_match(extracted: str, expected_full: str, threshold=0.45) -> bool:
    if not extracted:
        return False
    expected_first = extract_first_location(expected_full)
    ext_norm = _normalize_text(extracted)
    exp_norm = _normalize_text(expected_first)
    exp_full_norm = _normalize_text(expected_full)
    
    sim1 = _urdu_similarity(ext_norm, exp_norm)
    if sim1 >= threshold:
        return True
    sim2 = _urdu_similarity(ext_norm, exp_full_norm)
    if sim2 >= threshold:
        return True
    # Substring match only if the substring is meaningful (>=4 chars)
    if exp_norm and len(exp_norm) >= 4 and exp_norm in ext_norm:
        return True
    if ext_norm and len(ext_norm) >= 4 and ext_norm in exp_full_norm:
        return True
    return False


def clean_crime_area_text(raw_text: str) -> str:
    """Clean OCR text for crime area extraction."""
    text = raw_text.strip()
    if not text:
        return ""
    
    # Remove RTL/LTR control characters
    text = re.sub(r'[\u200e\u200f\u200b\u200c\u200d\u202a-\u202e\u2066-\u2069\ufeff]', '', text)
    
    # For multi-line text, find the line with the most Urdu location content
    lines = text.split('\n')
    if len(lines) > 1:
        # Score each line for location relevance
        location_keywords = [
            'روڈ', 'مارکیٹ', 'چوک', 'گیٹ', 'ٹاؤن', 'بازار', 'بلاک',
            'پارک', 'کالونی', 'نگر', 'پورہ', 'فیز', 'سیکٹر',
            'آباد', 'سوسائٹی', 'ہاؤسنگ', 'دربار', 'ایونیو', 'انٹرچینج',
            'آسکاری', 'بحریہ', 'ڈی ایچ اے', 'والینشیا', 'واپڈا',
        ]
        # Negative keywords: lines from adjacent rows (not crime area)
        negative_keywords = ['اطلاع', 'فون', 'بزریعہ', 'ذریعہ', 'موصول',
                            'عوائی', 'ٹریفک', 'صورتحال', 'ٹرییک', 'ہوئی', 'ہوئگی']
        best_line = ""
        best_score = -1
        for line in lines:
            line = line.strip()
            if not line:
                continue
            urdu = sum(1 for c in line if '\u0600' <= c <= '\u06FF')
            keywords_found = sum(1 for kw in location_keywords if kw in line)
            score = urdu + keywords_found * 5
            # Penalize lines from adjacent rows
            for nk in negative_keywords:
                if nk in line:
                    score -= 20
            if score > best_score:
                best_score = score
                best_line = line
        if best_line:
            text = best_line
    
    # Remove leading non-Urdu characters
    text = re.sub(r'^[^\u0600-\u06FF]+', '', text)
    
    # Remove row labels
    labels = [
        r'جائے\s*وقوعہ',
        r'جائے\s*اور\s*علاقہ.*',
        r'تحصیل\s*و\s*ضلع',
        r'علاقہ\s*تحصیل',
    ]
    for label in labels:
        text = re.sub(label, '', text, flags=re.UNICODE)
    
    # Split at "سے" (distance marker)
    text = re.split(r'\s+سے\s+', text)[0]
    
    # Distance pattern (handles garbled OCR of "سے تقریباً")
    distance_pattern = r'(?:سے|ے)\s*(?:تقر|نقر|تھر|تمر|تپ|تر|نر|۲ر|تت)'
    text = re.split(distance_pattern, text)[0]
    
    # Extract before dash (----)
    dash_patterns = [r'^(.*?)[\-]{2,}', r'^(.*?)[ـ]{3,}', r'^(.*?)[\.۔]{4,}']
    for pattern in dash_patterns:
        match = re.search(pattern, text, re.UNICODE)
        if match:
            text = match.group(1).strip()
            break
    
    # Remove distance/direction phrases
    text = re.sub(r'[\d٠-٩\.]+\s*کلو\s*میٹر', '', text)
    text = re.sub(r'[\d٠-٩\.]+\s*کاو\s*می', '', text)
    text = re.sub(r'شمال\s*(?:مشرق|مغرب)?\.?\s*$', '', text)
    text = re.sub(r'جنوب\s*(?:مشرق|مغرب)?\.?\s*$', '', text)
    text = re.sub(r'مشرق[ی]?\s*$', '', text)
    text = re.sub(r'(?:مغرب|مطرب|وخرب|مخرب|مطضرب)\s*$', '', text)
    
    # Clean up whitespace and punctuation
    text = re.sub(r'\s+', ' ', text).strip()
    text = re.sub(r'^[\s\-_=.:،۔/\d٠-٩۰-۹]+', '', text)
    text = re.sub(r'[\s\-_=.:،۔]+$', '', text)
    text = re.sub(r'[\[\]{}()!@#$%^&*;:<>|/\\]', '', text)
    
    # Smart truncation at last location keyword
    location_keywords = [
        'روڈ', 'رڈ', 'مارکیٹ', 'مارکٹ', 'چوک', 'گیٹ', 'کیٹ',
        'ٹاؤن', 'بازار', 'کالونی', 'نگر', 'کوٹ', 'پورہ', 'پوری',
        'پارک', 'بلاک', 'سوسائٹی', 'ہاؤسنگ', 'سیکٹر', 'فیز',
        'انٹرچینج', 'ایونیو',
    ]
    
    last_keyword_pos = -1
    last_keyword_end = -1
    last_keyword_text = ''
    for keyword in location_keywords:
        pos = text.rfind(keyword)
        if pos > last_keyword_pos:
            last_keyword_pos = pos
            last_keyword_end = pos + len(keyword)
            last_keyword_text = keyword
    
    if last_keyword_end > 0:
        if last_keyword_text in ('بلاک', 'فیز', 'سیکٹر'):
            # Preserve letter/number after block/phase/sector
            remaining = text[last_keyword_end:].strip()
            if remaining:
                next_token = remaining.split()[0] if remaining.split() else ''
                if len(next_token) <= 3:
                    text = text[:last_keyword_end] + ' ' + next_token
                else:
                    text = text[:last_keyword_end]
            else:
                text = text[:last_keyword_end]
        else:
            text = text[:last_keyword_end]
    
    # Remove trailing garbage
    text = re.sub(r'[\d٠-٩۰-۹]+\s*$', '', text)
    text = re.sub(r'[a-zA-Z]{1,2}\s*$', '', text)
    
    return text.strip()


def detect_structured_location(raw_text: str) -> str:
    """Detect structured housing scheme locations from raw/garbled OCR text.
    
    Uses keyword anchoring to identify DHA, Bahria, Askari, LDA, WAPDA patterns
    even in heavily garbled Tesseract output.
    Returns constructed location string or empty string.
    """
    text = re.sub(r'\s+', ' ', raw_text.strip())
    if len(text) < 5:
        return ""
    
    # ===== DHA (ڈی ایچ اے) =====
    dha_markers = ['ایچ اے', 'اچ اے', 'اگ اے', 'ائچ اے', 'ایچ ای',
                   'اچ ای', 'ای اے', 'اگ ے', 'ایچاے', 'اچاے',
                   'ایج اے', 'اگ ای', 'ایچ ے', 'ایگ اے',
                   'کی اے', 'کے اے', 'کی ای', 'کے ای',
                   'اچ کے', 'اچ کی']  # extra garbles: ایچ اے→اچ کے
    for marker in dha_markers:
        pos = text.find(marker)
        if pos >= 0:
            # Strict validation: require ڈی pattern close to marker
            # ڈ/ڑ followed by 0-1 chars then ی (handles ڈی, ڑی, ڑکی garbles)
            # Rejects "ارڈ تی" (2+ chars between ڈ and ی, from garbled بلیوارڈ)
            prefix = text[max(0, pos-5):pos]
            has_d_context = bool(re.search(r'[ڈڑ].?ی', prefix))
            # Also allow ڈ at very start of text (pos <= 3)
            if not has_d_context and pos <= 3:
                has_d_context = 'ڈ' in text[:pos]
            if not has_d_context:
                continue
            # Additional validation: text around marker shouldn't be mostly noise
            context = text[max(0, pos-15):min(len(text), pos+len(marker)+20)]
            urdu_in_ctx = sum(1 for c in context if '\u0600' <= c <= '\u06FF')
            if urdu_in_ctx < len(context) * 0.3:  # Too much noise
                continue
            after = text[pos + len(marker):]
            phase_match = re.search(r'(\d)', after[:30])
            if phase_match:
                phase = phase_match.group(1)
                if 1 <= int(phase) <= 9:
                    after_phase = after[phase_match.end():]
                    block_match = re.search(r'(?:بلاک|لاک|ملاک|بلک)\s*([A-Za-z])', after_phase[:25])
                    if block_match:
                        return f"ڈی ایچ اے فیز {phase} بلاک {block_match.group(1).upper()}"
                    return f"ڈی ایچ اے فیز {phase}"
    
    # ===== آسکاری (Askari) =====
    askari_markers = ['آسکاری', 'آسکار', 'اسکاری', 'اسکار', 'آسکری',
                      'آساری', 'آسکادری', 'اسکادری']  # garbled: آساری, آسکادری
    for marker in askari_markers:
        pos = text.find(marker)
        if pos >= 0:
            after = text[pos + len(marker):]
            num_match = re.search(r'(\d+)', after[:15])
            if num_match:
                num = num_match.group(1)
                remaining = after[num_match.end():]
                block_match = re.search(r'(?:بلاک|لاک)\s*([A-Za-z])', remaining[:20])
                if block_match:
                    return f"آسکاری {num} بلاک {block_match.group(1).upper()}"
                return f"آسکاری {num}"
    
    # ===== بحریہ ٹاؤن (Bahria Town) =====
    bahria_markers = ['بحریہ', 'بحرہ', 'بحربہ', 'نحریہ', 'بحری ہ']
    for marker in bahria_markers:
        pos = text.find(marker)
        if pos >= 0:
            after = text[pos + len(marker):]
            sector_match = re.search(r'(?:سیکٹر|سکٹر|سیکنر|صیکٹر|شیکٹر|سی کٹر)\s*([A-Za-z])', after[:40])
            if sector_match:
                sector = sector_match.group(1).upper()
                remaining = after[sector_match.end():]
                block_match = re.search(r'(?:بلاک|لاک)\s*([A-Za-z])', remaining[:25])
                if block_match:
                    return f"بحریہ ٹاؤن سیکٹر {sector} بلاک {block_match.group(1).upper()}"
                return f"بحریہ ٹاؤن سیکٹر {sector}"
            return "بحریہ ٹاؤن"
    
    # ===== لی ڈی اے (LDA City) =====
    lda_markers = ['لی ڈی اے', 'لے ڈی اے', 'لی ڈے اے', 'لی ڈ اے',
                    'لی دے', 'لاڈ ی ے', 'ڈی نے بی', 'لی ڈی', 'ڈی لے',
                    'لاڈی ے', 'ڈڑی دے']  # garbled variants
    for marker in lda_markers:
        pos = text.find(marker)
        if pos >= 0:
            after = text[pos + len(marker):]
            sector_match = re.search(r'(?:سیکٹر|سکٹر|صیکٹر|[مخنٹکھ]ر)\s*(\d+)', after[:30])
            if sector_match:
                sector = sector_match.group(1)
                # Handle doubled digits from OCR garbling (44→4, 33→3)
                if len(sector) == 2 and sector[0] == sector[1]:
                    sector = sector[0]
                remaining = after[sector_match.end():]
                block_match = re.search(r'(?:بلاک|لاک|ملاک)\s*([A-Za-z])', remaining[:20])
                if block_match:
                    return f"لی ڈی اے سٹی سیکٹر {sector} بلاک {block_match.group(1).upper()}"
                return f"لی ڈی اے سٹی سیکٹر {sector}"
            return "لی ڈی اے سٹی"  # fallback when marker found but no sector
    
    # ===== واپڈا ٹاؤن (WAPDA Town) =====
    wapda_markers = ['واپڈا', 'واپدا', 'وپڈا', 'وابڈا', 'داپڑا', 'دایڑا']
    for marker in wapda_markers:
        pos = text.find(marker)
        if pos >= 0:
            after = text[pos + len(marker):]
            phase_match = re.search(r'(?:فیز|فیر|فین|ٹر|نر)\s*(\d+)', after[:30])
            if phase_match:
                phase = phase_match.group(1)
                remaining = after[phase_match.end():]
                block_match = re.search(r'(?:بلاک|لاک|ملاک)\s*([A-Za-z])', remaining[:20])
                if block_match:
                    return f"واپڈا ٹاؤن فیز {phase} بلاک {block_match.group(1).upper()}"
                return f"واپڈا ٹاؤن فیز {phase}"
            return "واپڈا ٹاؤن"  # fallback
    
    # ===== پی سی ایس آئی آر (PCSIR) =====
    pcsir_markers = ['سی ایس آئی آر', 'سی ایی آئی آر', 'سی ایس آئی', 'سی ایی آئی']
    for marker in pcsir_markers:
        pos = text.find(marker)
        if pos >= 0:
            after = text[pos + len(marker):]
            phase_match = re.search(r'(?:فیز|فیر|ٹر|نر)\s*(\d+)', after[:30])
            if phase_match:
                phase = phase_match.group(1)
                remaining = after[phase_match.end():]
                block_match = re.search(r'(?:بلاک|لاک|ملاک)\s*([A-Za-z])', remaining[:20])
                if block_match:
                    return f"پی سی ایس آئی آر فیز {phase} بلاک {block_match.group(1).upper()}"
                return f"پی سی ایس آئی آر فیز {phase}"
    
    # ===== پی آئی اے سوسائٹی (PIA Society) =====
    pia_markers = ['پی آئی اے', 'پی کی اے']
    for marker in pia_markers:
        pos = text.find(marker)
        if pos >= 0:
            after = text[pos + len(marker):]
            # Look for سوسائٹی or garbled variant
            if re.search(r'(?:صوس|سوس|سوسائ)', after[:20]):
                block_match = re.search(r'(?:بلاک|لاک|بلاگ|ملاک)\s*(\d+|[A-Za-z])', after[:40])
                if block_match:
                    bl = block_match.group(1)
                    return f"پی آئی اے سوسائٹی بلاک {bl.upper()}"
                return "پی آئی اے سوسائٹی"
    
    return ""


def detect_location_fragments(raw_text: str) -> str:
    """Detect specific location names from garbled OCR using distinctive fragments.
    
    Many locations have distinctive character sequences that survive OCR garbling.
    This function looks for these fragments across ALL strips' raw text and returns
    the best matching known location.
    
    Returns location name or empty string.
    """
    if not raw_text or len(raw_text.strip()) < 3:
        return ""
    
    # Pre-filter: remove distance reference text (after سے) and noise lines
    lines = raw_text.strip().split('\n')
    filtered_lines = []
    noise_keywords = ['اطلاع', 'بذریعہ', 'ہذریعہ', 'ہزریعہ', 'فون', 'موصول',
                       'بزریعہ', 'ذریعہ', 'ٹریفک', 'صورتحال', 'عوائی']
    for line in lines:
        line = line.strip()
        if not line:
            continue
        # Skip lines that are info-source (not crime-area)
        if any(nk in line for nk in noise_keywords):
            continue
        # Cut at distance marker - handles both proper "سے" and garbled forms
        # Patterns: "سے تقریباً", "ے7", "ےت", "ےآ" (garbled سے)
        # First try proper سے
        parts = re.split(r'\s+سے\s+', line)
        line = parts[0] if parts else line
        # Also cut at garbled distance patterns: والشن ے7, والشن ےت, etc.
        # Pattern: location_ref + ے + digit/letter (garbled "سے تقریباً distance")
        line = re.split(r'ے[تط7]\s*آ?\s*[\d٠-٩\[\]]', line)[0]
        # Cut at dash separator (crime-area --- reference-point)
        line = re.split(r'[-ـ۔\.]{2,}', line)[0]
        # Cut at کاو/کلو (garbled کلومیٹر) 
        line = re.split(r'[\d٠-٩\[\]]+\s*,?\s*کاو', line)[0]
        line = re.split(r'[\d٠-٩\[\]]+\s*,?\s*کلو', line)[0]
        if line.strip():
            filtered_lines.append(line.strip())
    
    orig = re.sub(r'\s+', ' ', ' '.join(filtered_lines)).strip()
    if len(orig) < 3:
        return ""
    
    # Each entry: (list_of_fragment_patterns, result_location, min_fragments_needed)
    # Fragment patterns are substrings that commonly survive OCR garbling
    FRAGMENT_RULES = [
        # انارکلی بازار - use longer fragment to avoid false positives
        (['انارکل'], 'انارکلی بازار', 1),
        (['انار', 'بازار'], 'انارکلی بازار', 2),
        (['انار', 'کلی'], 'انارکلی بازار', 2),
        # دہلی گیٹ - "دی گیٹ" or "دہلی" or "دھلی"
        (['دی گیٹ'], 'دہلی گیٹ', 1),
        (['دہلی'], 'دہلی گیٹ', 1),
        # شاہ عالمی مارکیٹ
        (['عالمی', 'مارکیٹ'], 'شاہ عالمی مارکیٹ', 2),
        # لوہاری گیٹ
        (['لوہاری'], 'لوہاری گیٹ', 1),
        # بھاٹی گیٹ
        (['بھاٹی'], 'بھاٹی گیٹ', 1),
        # ریگل چوک
        (['ریگل'], 'ریگل چوک', 1),
        # نیلا گنبد
        (['نیلا', 'گنبد'], 'نیلا گنبد', 1),
        (['گنبد'], 'نیلا گنبد', 1),
        # ایڈورڈ روڈ (sometimes OCR gives this for نیلا گنبد area)
        (['ایڈورڈ'], 'نیلا گنبد', 1),
        # مین بلیوارڈ گلبرگ - "بلیوار" is distinctive
        (['بلیوار'], 'مین بلیوارڈ گلبرگ', 1),
        (['جلیوار'], 'مین بلیوارڈ گلبرگ', 1),  # garble
        # قذافی اسٹیڈیم - "قذا" fragment
        (['قذا'], 'قذافی اسٹیڈیم', 1),
        # فیصل ٹاؤن - "فیصل" or garbled variants
        (['فیصل'], 'فیصل ٹاؤن', 1),
        # گارڈن ٹاؤن - "گارڈ" or "گار ڈ"
        (['گارڈ'], 'گارڈن ٹاؤن', 1),
        (['گار ڈ'], 'گارڈن ٹاؤن', 1),
        # ٹاؤن شپ - "شپ" near "ٹاؤن"
        (['ٹاؤن شپ'], 'ٹاؤن شپ', 1),
        (['نع شب'], 'ٹاؤن شپ', 1),  # OCR garble
        # والٹن روڈ - only match proper والٹن, not والشن (too many false positives
        # as والشن frequently appears as a distance reference point)
        (['والٹن'], 'والٹن روڈ', 1),
        # شادمان
        (['شادمان'], 'شادمان مارکیٹ', 1),
        (['شادم'], 'شادمان مارکیٹ', 1),
        # جیل روڈ - "جیل" or "ٹیل رد" (garbled)
        (['جیل'], 'جیل روڈ', 1),
        (['ٹیل ر'], 'جیل روڈ', 1),  # garbled OCR
        # مغلپورہ
        (['مغلپور'], 'مغلپورہ', 1),
        (['مغلپ'], 'مغلپورہ', 1),
        # ہربنس پورہ
        (['ہربنس'], 'ہربنس پورہ', 1),
        (['ہر یئ'], 'ہربنس پورہ', 1),  # garbled (seen in FIR_024)
        (['ہر یشس'], 'ہربنس پورہ', 1),  # garbled
        # غڑی شاہو / غری شاہو (removed 'شاہو' alone rule - too many reference-point false positives)
        (['غڑی'], 'غڑی شاہو', 1),
        (['غری'], 'غڑی شاہو', 1),
        # شالامار باغ
        (['شالامار'], 'شالامار باغ', 1),
        (['شالا'], 'شالامار باغ', 1),
        # باغبانپورہ - "غازی آباد" linked to it
        (['باغبان'], 'باغبانپورہ', 1),
        (['ذائیآ'], 'باغبانپورہ', 1),  # garbled غازی آباد
        # سمن آباد
        (['سمن'], 'سمن آباد', 1),
        (['نآ اد'], 'سمن آباد', 1),  # garbled
        (['نآ بادہ'], 'سمن آباد', 1),  # garbled
        (['تنآ اد'], 'سمن آباد', 1),  # garbled
        # ریلوے اسٹیشن
        (['ریلوے'], 'ریلوے اسٹیشن لاہور', 1),
        (['اسٹیشن'], 'ریلوے اسٹیشن لاہور', 1),
        (['مگیشن'], 'ریلوے اسٹیشن لاہور', 1),  # garbled
        # کینٹ صدر بازار
        (['کینٹ', 'صدر'], 'کینٹ صدر بازار', 2),
        (['کین', 'صدر'], 'کینٹ صدر بازار', 2),
        (['کین', 'مدر'], 'کینٹ صدر بازار', 2),  # garbled صدر→مدر
        (['گیٹ', 'مدر'], 'کینٹ صدر بازار', 2),  # garbled: گیٹ مدر = کینٹ صدر
        # برکی روڈ / بیدیان
        (['بیدیان'], 'برکی روڈ', 1),
        (['بیدان'], 'برکی روڈ', 1),  # garbled
        (['یدان'], 'برکی روڈ', 1),
        (['برکی'], 'برکی روڈ', 1),
        # فیروزپور روڈ
        (['فیروزپور'], 'فیروزپور روڈ', 1),
        (['فیروز'], 'فیروزپور روڈ', 1),
        # وحدت روڈ
        (['وحدت'], 'وحدت روڈ', 1),
        (['دحرت'], 'وحدت روڈ', 1),         # garbled وحدت (FIR_035 PSM6)
        (['دحد تر'], 'وحدت روڈ', 1),       # garbled وحدت (FIR_035 Otsu)
        # لبرٹی مارکیٹ
        (['لبرٹی'], 'لبرٹی مارکیٹ', 1),
        # حفیظ سنٹر
        (['حفیظ'], 'حفیظ سنٹر', 1),
        # جوہر ٹاؤن
        (['جوہر'], 'جوہر ٹاؤن', 1),
        # ایمپوریئم
        (['ایمپوریئم'], 'جوہر ٹاؤن ایمپوریئم مال', 1),
        # ماڈل ٹاؤن  
        (['ماڈل'], 'ماڈل ٹاؤن', 1),
        # سبزہ زار
        (['سبزہ'], 'سبزہ زار', 1),
        # گلشن راوی
        (['گلشن'], 'گلشنِ راوی', 1),
        # اقبال ٹاؤن
        (['اقبال'], 'علامہ اقبال ٹاؤن', 1),
        # کینال روڈ
        (['کینال'], 'کینال روڈ', 1),
        # راوی روڈ
        (['راوی ر'], 'راوی روڈ', 1),
        # شاہدرہ
        (['شاہدرہ'], 'شاہدرہ ٹاؤن', 1),
        (['شاہدر'], 'شاہدرہ ٹاؤن', 1),
        # داتا دربار
        (['داتا'], 'داتا دربار', 1),
        # کریم بلاک
        (['کریم', 'بلاک'], 'کریم بلاک مارکیٹ', 2),
        # ای ایم ای سوسائٹی - require both patterns to avoid false positives
        # (ایم ایم عالم روڈ is a common reference road, not ای ایم ای سوسائٹی)
        (['ایم ای', 'سوسائ'], 'ای ایم ای سوسائٹی', 2),
        # مولانا شوکت
        (['شوکت'], 'مولانا شوکت علی روڈ', 1),
        # بحریہ ٹاؤن - garbled OCR patterns from small-format images
        (['بر مائن'], 'بحریہ ٹاؤن', 1),    # garbled بحریہ مین
        (['بر مان'], 'بحریہ ٹاؤن', 1),     # garbled without ئ
        (['بھریے مان'], 'بحریہ ٹاؤن', 1),   # garbled at scale 3.0
        (['بھریہ مان'], 'بحریہ ٹاؤن', 1),   # garbled variant
        (['بھری مان'], 'بحریہ ٹاؤن', 1),    # garbled variant
        (['بھرس مان'], 'بحریہ ٹاؤن', 1),    # garbled FIR_198
        (['بھرسہ'], 'بحریہ ٹاؤن', 1),       # garbled FIR_198
        (['بجھرسہ مان'], 'بحریہ ٹاؤن', 1),  # garbled FIR_113
        (['بجھرس مان'], 'بحریہ ٹاؤن', 1),   # garbled FIR_155
        (['جھری مان'], 'بحریہ ٹاؤن', 1),   # garbled بحریہ مین
        (['جھری', 'لاک'], 'بحریہ ٹاؤن', 2), # garbled بحریہ بلاک
        # بحریہ آرچرڈ - garbled
        (['پھر آرڈ'], 'بحریہ آرچرڈ', 1),    # garbled FIR_151
        (['بھرں آرجھڈ'], 'بحریہ آرچرڈ', 1), # garbled FIR_188
        (['آرجھڈ'], 'بحریہ آرچرڈ', 1),      # garbled آرچرڈ
        # الخضریا ہاؤسنگ - garbled
        (['النریا'], 'الخضریا ہاؤسنگ', 1),  # garbled FIR_156
        # مغلپورہ - additional garbled patterns
        (['للپور'], 'مغلپورہ', 1),          # garbled from FIR_023
        # فیصل ٹاؤن - highly garbled patterns
        (['یصل'], 'فیصل ٹاؤن', 1),         # partial فیصل
        (['یل انان'], 'فیصل ٹاؤن', 1),     # garbled فیصل ٹاؤن (FIR_015 PSM6)
        (['ٹیل نون'], 'فیصل ٹاؤن', 1),     # garbled فیصل ٹاؤن (FIR_015 PSM7)
        (['نیھل'], 'فیصل ٹاؤن', 1),        # garbled فیصل (FIR_015 Otsu)
        # اقبال ٹاؤن - additional garbled patterns  
        (['اتال', 'ڈاؤ'], 'علامہ اقبال ٹاؤن', 2),  # garbled اقبال ٹاؤن
        (['اتال', 'مان'], 'علامہ اقبال ٹاؤن', 2),  # garbled
        # چوبرجی
        (['چوبرجی'], 'چوبرجی', 1),
        # لکشمی چوک
        (['لکشم'], 'لکشمی چوک', 1),
        # نسبت روڈ
        (['نسبت'], 'نسبت روڈ', 1),
        # نشتر ٹاؤن - removed as standalone, too many reference-point false positives
        # (نشتر is always a reference point in our dataset, never the crime area)
        # پران انارکلی
        (['پرانی', 'نارکل'], 'پرانی انارکلی', 2),
        # عامر روڈ - garbled
        (['ام ز روڈ'], 'عامر روڈ', 1),     # garbled FIR_16: ام ز روڈ→عامر روڈ
        (['امر روڈ'], 'عامر روڈ', 1),
        (['پامرروڑ'], 'عامر روڈ', 1),      # garbled FIR_16 S1: پامرروڑ
        # سنت نگر - garbled
        (['سنت نگر'], 'سنت نگر چوک', 1),
    ]
    
    best_result = ""
    best_fragments = 0
    
    for fragments, location, min_needed in FRAGMENT_RULES:
        found = sum(1 for f in fragments if f in orig)
        if found >= min_needed and found > best_fragments:
            best_fragments = found
            best_result = location
        elif found >= min_needed and found == best_fragments:
            # Prefer longer location names for more specific matches
            if len(location) > len(best_result):
                best_result = location
    
    return best_result


def extract_crime_area_tesseract(img: np.ndarray) -> str:
    """Extract crime area using Tesseract only with multi-strip scanning."""
    h, w = img.shape[:2]
    from urdu_location_dictionary import KNOWN_LOCATIONS
    
    all_candidates = []  # (corrected_text, adjusted_score, engine_name)
    
    for strip_idx, (top, bottom, left, right) in enumerate(CRIME_STRIPS):
        y1 = int(h * top)
        y2 = int(h * bottom)
        x1 = int(w * left)
        x2 = int(w * right)
        
        region = img[y1:y2, x1:x2]
        rh, rw = region.shape[:2]
        if rh < 20 or rw < 50:
            continue
        
        gray = cv2.cvtColor(region, cv2.COLOR_BGR2GRAY) if len(region.shape) == 3 else region
        
        # Determine scale based on crop width
        if rw > 1500:
            scale = 2.0
        elif rw > 800:
            scale = 3.0
        else:
            scale = 4.0
        
        # Create enhanced version
        scaled = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(scaled)
        del scaled
        
        # Run multiple Tesseract strategies on this strip
        strip_texts = []
        
        # Strategy 1: PSM6 on CLAHE enhanced
        try:
            text = pytesseract.image_to_string(enhanced, lang='urd', config='--oem 1 --psm 6')
            if text and text.strip():
                urdu_count = sum(1 for c in text.strip() if '\u0600' <= c <= '\u06FF')
                if urdu_count >= 3:
                    strip_texts.append((text.strip(), f'S{strip_idx}-PSM6'))
        except Exception:
            pass
        
        # Strategy 2: PSM7 (single text line)
        try:
            text = pytesseract.image_to_string(enhanced, lang='urd', config='--oem 1 --psm 7')
            if text and text.strip():
                urdu_count = sum(1 for c in text.strip() if '\u0600' <= c <= '\u06FF')
                if urdu_count >= 3:
                    strip_texts.append((text.strip(), f'S{strip_idx}-PSM7'))
        except Exception:
            pass
        
        # Strategy 3: Adaptive threshold + PSM6
        try:
            adaptive = cv2.adaptiveThreshold(enhanced, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                              cv2.THRESH_BINARY, 31, 10)
            text = pytesseract.image_to_string(adaptive, lang='urd', config='--oem 1 --psm 6')
            if text and text.strip():
                urdu_count = sum(1 for c in text.strip() if '\u0600' <= c <= '\u06FF')
                if urdu_count >= 3:
                    strip_texts.append((text.strip(), f'S{strip_idx}-Adapt'))
            del adaptive
        except Exception:
            pass
        
        # Strategy 4: Otsu binary + PSM6
        try:
            _, otsu = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            text = pytesseract.image_to_string(otsu, lang='urd', config='--oem 1 --psm 6')
            if text and text.strip():
                urdu_count = sum(1 for c in text.strip() if '\u0600' <= c <= '\u06FF')
                if urdu_count >= 3:
                    strip_texts.append((text.strip(), f'S{strip_idx}-Otsu'))
            del otsu
        except Exception:
            pass
        
        del enhanced
        gc.collect()
        
        # Score each text against dictionary
        for raw_text, engine in strip_texts:
            # Try structured pattern detection first (DHA, Bahria, Askari, etc.)
            structured = detect_structured_location(raw_text)
            if structured:
                struct_score = 0.96 + (0.03 if strip_idx == 0 else 0.0)
                all_candidates.append((structured, struct_score, engine + '-Struct'))
            
            # Try fragment detection on raw OCR text (catches garbled location names)
            # Fragment detection is highly specific (pre-filtered) so gets priority
            fragment_loc = detect_location_fragments(raw_text)
            if fragment_loc:
                frag_score = 0.92 + (0.03 if strip_idx == 0 else 0.0)
                all_candidates.append((fragment_loc, frag_score, engine + '-Frag'))
            
            cleaned = clean_crime_area_text(raw_text)
            if not cleaned or len(cleaned) < 2:
                continue
            
            # Also try fragment detection on cleaned text
            if not fragment_loc:
                fragment_loc2 = detect_location_fragments(cleaned)
                if fragment_loc2:
                    frag_score = 0.90 + (0.03 if strip_idx == 0 else 0.0)
                    all_candidates.append((fragment_loc2, frag_score, engine + '-FragC'))
            
            corrected = correct_location_text(cleaned)
            if corrected and len(corrected) >= 2:
                norm_corrected = _normalize_text(corrected)
                match_score = 0.0
                for loc in KNOWN_LOCATIONS:
                    sim = _urdu_similarity(norm_corrected, _normalize_text(loc))
                    if sim > match_score:
                        match_score = sim
                
                orig_to_corrected = _urdu_similarity(_normalize_text(cleaned), _normalize_text(corrected))
                adjusted_score = max(
                    match_score * 0.7 + orig_to_corrected * 0.3,
                    match_score * orig_to_corrected
                )
                
                # Bonus for strip0 (original proven region)
                if strip_idx == 0:
                    adjusted_score += 0.05
                
                # Penalize very short single-word results (often noise)
                if len(corrected.split()) == 1 and len(corrected) <= 5:
                    adjusted_score *= 0.6
                
                # Cap fuzzy score to prevent false positives from overriding 
                # fragment detection (fragments are more specific/reliable)
                adjusted_score = min(adjusted_score, 0.89)
                
                all_candidates.append((corrected, adjusted_score, engine))
        
        del gray
        gc.collect()
    
    if not all_candidates:
        return ""
    
    # Pick candidate with highest adjusted score
    all_candidates.sort(key=lambda x: x[1], reverse=True)
    best = all_candidates[0]
    
    if best[1] >= 0.15:
        return best[0]
    
    # Quality fallback - return best cleaned text with location indicators
    location_indicators = [
        'روڈ', 'مارکیٹ', 'چوک', 'گیٹ', 'ٹاؤن', 'بازار', 'بلاک',
        'پارک', 'کالونی', 'نگر', 'پورہ', 'فیز', 'سیکٹر',
        'آباد', 'سوسائٹی', 'ہاؤسنگ', 'دربار', 'مسجد',
        'ایونیو', 'انٹرچینج', 'کوٹ', 'باغ',
    ]
    
    # Re-scan primary strip for quality fallback
    top, bottom, left, right = CRIME_STRIPS[0]
    y1 = int(h * top)
    y2 = int(h * bottom)
    x1 = int(w * left)
    x2 = int(w * right)
    region = img[y1:y2, x1:x2]
    gray = cv2.cvtColor(region, cv2.COLOR_BGR2GRAY) if len(region.shape) == 3 else region
    rh, rw = gray.shape[:2]
    scale = 3.0 if rw < 800 else 2.0
    scaled = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    enh = clahe.apply(scaled)
    text = pytesseract.image_to_string(enh, lang='urd', config='--oem 1 --psm 6').strip()
    del scaled, enh, gray
    gc.collect()
    
    cleaned = clean_crime_area_text(text)
    if cleaned and len(cleaned) >= 3:
        urdu_chars = sum(1 for c in cleaned if '\u0600' <= c <= '\u06FF')
        if urdu_chars >= 4:
            has_indicator = any(ind in cleaned for ind in location_indicators)
            if has_indicator:
                corrected = correct_location_text(cleaned)
                if corrected and len(corrected) >= 3:
                    return corrected
                return cleaned
    
    return ""


def main():
    entries = parse_summary(SUMMARY_FILE)
    print(f"Loaded {len(entries)} entries from fir_summary.txt")
    
    start_idx = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    end_idx = int(sys.argv[2]) if len(sys.argv) > 2 else len(entries)
    
    sorted_entries = sorted(entries.items(), key=lambda x: x[0])
    sorted_entries = sorted_entries[start_idx:end_idx]
    
    print(f"Testing {len(sorted_entries)} images (index {start_idx} to {end_idx})")
    print("=" * 100)
    
    results = []
    passed = 0
    failed = 0
    errors = 0
    
    for fname, expected in sorted_entries:
        img_path = os.path.join(IMAGE_DIR, fname)
        if not os.path.exists(img_path):
            print(f"  SKIP {fname} - file not found")
            continue
        
        t0 = time.time()
        img = None
        try:
            file_size = os.path.getsize(img_path)
            
            # Use half resolution for large files to prevent OOM
            # (Tesseract-only mode uses much less RAM than EasyOCR)
            if file_size > 15_000_000:
                img = cv2.imread(img_path, cv2.IMREAD_REDUCED_COLOR_2)
            else:
                img = cv2.imread(img_path)
            
            if img is None:
                print(f"  SKIP {fname} - failed to load")
                continue
            
            ih, iw = img.shape[:2]
            if max(ih, iw) > 5000:
                s = 3000.0 / max(ih, iw)
                img = cv2.resize(img, None, fx=s, fy=s, interpolation=cv2.INTER_AREA)
            
            extracted = extract_crime_area_tesseract(img)
            del img
            img = None
            gc.collect()
            elapsed = time.time() - t0
            
            expected_first = extract_first_location(expected)
            match = is_match(extracted, expected)
            
            if match:
                status = "PASS"
                passed += 1
            else:
                status = "FAIL"
                failed += 1
            
            if extracted:
                sim = _urdu_similarity(_normalize_text(extracted), _normalize_text(expected_first))
            else:
                sim = 0.0
            
            results.append((fname, status, expected_first, extracted or "(empty)", sim, elapsed))
            mark = "OK" if match else "XX"
            print(f"  [{mark}] {fname:<16} sim={sim:.2f} t={elapsed:.1f}s | expected: {expected_first} | got: {extracted or '(empty)'}")
            
        except Exception as e:
            elapsed = time.time() - t0
            errors += 1
            results.append((fname, "ERR", extract_first_location(expected), str(e)[:50], 0.0, elapsed))
            print(f"  [ER] {fname:<16} ERROR: {str(e)[:80]}")
        finally:
            if img is not None:
                try:
                    del img
                except:
                    pass
            gc.collect()
    
    total = passed + failed + errors
    print("\n" + "=" * 100)
    print(f"RESULTS: {passed}/{total} passed ({100*passed/max(total,1):.1f}%), {failed} failed, {errors} errors")
    print("=" * 100)
    
    if failed > 0:
        print("\nFAILED images:")
        for fname, status, expected, extracted, sim, elapsed in results:
            if status == "FAIL":
                print(f"  {fname:<16} expected: {expected}")
                print(f"  {'':16} got:      {extracted} (sim={sim:.2f})")
    
    if errors > 0:
        print("\nERROR images:")
        for fname, status, expected, extracted, sim, elapsed in results:
            if status == "ERR":
                print(f"  {fname}: {extracted}")


if __name__ == "__main__":
    main()

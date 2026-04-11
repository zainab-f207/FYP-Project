"""
Fuzzy correction for Urdu crime area location OCR text.

Uses:
1. Dictionary of known location names (Lahore areas, markets, roads, etc.)
2. Common Urdu location words (مارکیٹ, روڈ, چوک, etc.)
3. Character-level substitution for common Tesseract misreads
4. Word-level fuzzy matching with scoring

This module corrects garbled Tesseract output into readable location names.
"""

import re
from difflib import SequenceMatcher

# ============================================================
#  KNOWN LOCATIONS - Lahore areas, markets, and landmarks
# ============================================================
KNOWN_LOCATIONS = [
    # Major areas
    "ماڈل ٹاؤن", "گلبرگ", "جوہر ٹاؤن", "ٹاؤن شپ", "کینٹ",
    "والٹن", "ایچی سن", "فیصل ٹاؤن", "سمن آباد", "اچھرہ",
    "مغلپورہ", "شالامار", "باغبانپورہ", "بادامی باغ", "مستی گیٹ",
    "لاہور", "شاہدرہ", "راوی", "اقبال ٹاؤن", "ساندہ",
    "شاہ عالم", "لوہاری", "گڑھی شاہو", "مزنگ", "چوبرجی",
    "قلعہ گجر سنگھ", "لکشمی چوک", "ریلوے اسٹیشن", "مقدس پورہ",
    "شادمان", "گلشن راوی", "نیو گارڈن ٹاؤن", "فردوس مارکیٹ",
    "حسین چوک", "کلمہ چوک", "لبرٹی", "دھرم پورہ",
    "نیو مسلم ٹاؤن", "واہگہ", "ڈیفنس", "ای ایم ای سوسائٹی",
    "پنجاب سوسائٹی", "ویلنسیا", "بحریہ ٹاؤن", "ڈی ایچ اے",
    "سبزہ زار", "میاں میر", "کوٹ لکھپت", "یتیم خانہ",
    "قذافی اسٹیڈیم", "مال روڈ", "دی مال", "انارکلی",
    "اردو بازار", "شاہ عالم مارکیٹ", "لنڈا بازار",
    "حیدر آباد", "حیدری", "داتا دربار", "بھاٹی گیٹ",
    "دلی گیٹ", "لاہوری گیٹ", "اکبری گیٹ", "موچی گیٹ",
    "سرکلر روڈ", "ڈیٹا دربار", "داتا دربار سرکلر روڈ",
    "لوہاری گیٹ", "لوہاری بازار", "لوہاری بازار روڈ", "لوہاری گیٹ لوہاری بازار روڈ",
    "ٹکسالی گیٹ", "یاکی گیٹ", "شیرانوالہ گیٹ", "روشنائی گیٹ",
    "لنگر خانہ", "حضوری باغ", "عالمگنج", "خلیق نگر",
    "نیا موہلہ", "کریم پارک", "باغ گل بیگم", "ملتان روڈ",
    "فیروزپور روڈ", "کینال روڈ", "گرینڈ ٹرنک روڈ", "جی ٹی روڈ",
    "مین بلیوارڈ", "عبدالحق روڈ", "ایبٹ روڈ", "ٹیمپل روڈ",
    "ہال روڈ", "میکلوڈ روڈ", "لارنس روڈ", "نسبت روڈ",
    "برانڈریتھ روڈ", "بیڈن روڈ", "شیرشاہ روڈ", "چنیوٹ بازار",
    "گوالمنڈی", "بیکرز", "ماڈل ٹاؤن پارک", "جلو مور",
    "مناور چوک", "پاک بلاک", "لاہور کینال", "ریس کورس",
    "نشتر میڈیکل", "گنگا رام", "مایو ہسپتال", "سروسز ہسپتال",
    "جنرل ہسپتال", "ایم ایم عالم روڈ", "حفیظ سینٹر",
    "گلشن اقبال", "عوامی مارکیٹ", "مارکیٹ", "چوک",
    "رحمان پورہ", "وحدت کالونی", "نیشنل ٹاؤن", "علامہ اقبال ٹاؤن",
    "سرفراز رفیقی روڈ", "ایچ بلاک", "ڈی بلاک", "سی بلاک",
    "اے بلاک", "بی بلاک", "ای بلاک", "ایف بلاک", "جی بلاک",
    "ایل بلاک", "ایم بلاک", "این بلاک", "پی بلاک", "آر بلاک",
    # Model Town specifics
    "ماڈل ٹاؤن مارکیٹ", "ماڈل ٹاؤن لنک روڈ", "ماڈل ٹاؤن پارک ای بلاک روڈ",
    "ماڈل ٹاؤن ایکسٹینشن",
    "ماڈل ٹاؤن پارک ایف بلاک روڈ", "ماڈل ٹاؤن پارک ایف بلاک",
    # Shalimar / Bhati area
    "شالامار باغ", "شالامار لنک روڈ", "بھاٹی چوک",
    "بھاٹی گیٹ بھاٹی چوک", "بھاٹی چوک بھاٹی گیٹ",
    # Liberty / Gulberg area
    "لبرٹی مارکیٹ", "لبرٹی مارکیٹ ایم ایم عالم روڈ",
    "ایم ایم عالم روڈ لبرٹی مارکیٹ",
    # Anarkali area
    "انارکلی بازار", "انارکلی فوڈ اسٹریٹ",
    "انارکلی روڈ", "پرانی انارکلی روڈ",
    "پرانی انارکلی روڈ انارکلی", "انارکلی روڈ انارکلی لاہور",
    "پرانی انارکلی روڈ انارکلی لاہور",
    # Major roads
    "ایئرپورٹ روڈ", "بادشاہی مسجد", "مینار پاکستان",
    "شاہراہ قائداعظم", "شاہراہ فیصل", "شاہراہ پاکستان",
    "ماڈل ٹاؤن روڈ", "لنک روڈ",
    # More areas
    "جیل روڈ", "ناصر باغ", "تاج پورہ", "قینچی",
    "کوہاٹ", "جمال پورہ", "کمہار پورہ", "سیالکوٹ",
    "نیو انارکلی", "ریگل چوک", "پریس کلب", "الحمرا",
    "شیخوپورہ", "قصور", "ننکانہ صاحب",
    # Common patterns
    "پارک", "کالونی", "سوسائٹی", "نگر", "آباد", "پورہ",
    "ٹاؤن", "بازار", "چوک", "مارکیٹ", "روڈ", "بلاک",
    "گیٹ", "دربار", "مسجد", "عیدگاہ", "اسٹیشن",
    "ہسپتال", "سکول", "کالج", "یونیورسٹی",
    # Islamabad areas (in case)
    "اسلام آباد", "راولپنڈی", "بلیو ایریا", "ایف سیکٹر",

    # ============================================================
    #  EXPANDED: All locations from fir_summary.txt + housing patterns
    # ============================================================

    # --- Specific locations from FIR summary ---
    "انارکلی بازار", "شاہ عالمی مارکیٹ",
    "دہلی گیٹ", "دلی گیٹ", "دہلی گیٹ روڈ",
    "ریگل چوک", "ریگل چوک مال روڈ",
    "نیلا گنبد", "نیلا گنبد ایڈورڈ روڈ",
    "ہال روڈ", "مین بلیوارڈ گلبرگ",
    "گلبرگ لاہور", "گلبرگ مین بلیوارڈ",
    "گدا فی اسٹیڈیم", "قذافی اسٹیڈیم فیروزپور روڈ",
    "حفیظ سنٹر", "حفیظ سنٹر ایم ایم عالم روڈ",
    "پریس کلب کوئٹہ", "پریس کلب",
    "فیصل ٹاؤن آربی بلاک", "فیصل ٹاؤن آربی بلاک روڈ",
    "گارڈن ٹاؤن", "گارڈن ٹاؤن باغ جناح روڈ",
    "جوہر ٹاؤن ایمپوریئم مال", "ایمپوریئم مال",
    "ٹاؤن شپ مدینہ چوک", "مدینہ چوک",
    "والٹن روڈ", "ریلوے اسٹیشن لاہور",
    "شادمان مارکیٹ", "شادمـان مارکیٹ", "شادمان روڈ",
    "جیل روڈ", "کینال روڈ", "کینال بینک روڈ",
    "مغلپورہ روڈ", "مغلپورہ مغلپورہ روڈ",
    "ہربنس پورہ", "ہربنس پورہ جی ٹی روڈ",
    "غری شاہو", "غری شاہو روڈ", "گڑھی شاہو",
    "شاہدرہ ٹاؤن", "شاہدرہ ٹاؤن راوی روڈ",
    "راوی روڈ", "شالامار باغ جی ٹی روڈ",
    "باغبانپورہ غازی آباد روڈ",
    "سبزہ زار مین بلیوارڈ",
    "علامہ اقبال ٹاؤن کری بلاک", "کری بلاک مارکیٹ",
    "کریم بلاک مارکیٹ", "کریم بلاک روڈ",
    "سمن آباد مین بلیوارڈ",
    "گلشن راوی", "گلشنِ راوی", "گلشنِ راوی جی بلاک روڈ",
    "وحدت روڈ", "کینٹ صدر بازار", "صدر بازار", "صدر بازار روڈ",
    "برکی روڈ", "بیدیان", "برکی روڈ بیدیان",
    "فیروزپور روڈ قینچی", "قینچی امرسدھو",
    "شاد باغ مارکیٹ", "شاد باغ",
    "اچھرہ مارکیٹ", "اچھرہ فیروزپور روڈ",
    "سنت نگر چوک", "سنت نگر", "مزنگ روڈ",
    "اولڈ انارکلی روڈ", "اولڈ انارکلی",
    "د تا در بار", "داتا دربار اندرون لاہور",
    "مین بلیوارڈ برکت مارکیٹ", "برکت مارکیٹ",
    "عامر روڈ شاد باغ", "عامر روڈ اسٹریٹ 9",

    # --- DHA (ڈی ایچ اے) phases ---
    "ڈی ایچ اے فیز 1", "ڈی ایچ اے فیز 2", "ڈی ایچ اے فیز 3",
    "ڈی ایچ اے فیز 4", "ڈی ایچ اے فیز 5", "ڈی ایچ اے فیز 6",
    "ڈی ایچ اے فیز 7", "ڈی ایچ اے فیز 8", "ڈی ایچ اے فیز 9",
    # DHA with blocks (common from summary)
    "ڈی ایچ اے فیز 1 بلاک G", "ڈی ایچ اے فیز 1 بلاک H",
    "ڈی ایچ اے فیز 1 بلاک T", "ڈی ایچ اے فیز 1 بلاک X",
    "ڈی ایچ اے فیز 2 بلاک E", "ڈی ایچ اے فیز 2 بلاک H",
    "ڈی ایچ اے فیز 2 بلاک L", "ڈی ایچ اے فیز 2 بلاک O",
    "ڈی ایچ اے فیز 2 بلاک T", "ڈی ایچ اے فیز 2 بلاک V",
    "ڈی ایچ اے فیز 2 بلاک W",
    "ڈی ایچ اے فیز 3 بلاک C", "ڈی ایچ اے فیز 3 بلاک T",
    "ڈی ایچ اے فیز 3 بلاک Y", "ڈی ایچ اے فیز 3 بلاک Z",
    "ڈی ایچ اے فیز 3 وای بلاک",
    "ڈی ایچ اے فیز 4 بلاک B", "ڈی ایچ اے فیز 4 بلاک H",
    "ڈی ایچ اے فیز 4 بلاک J", "ڈی ایچ اے فیز 4 بلاک Q",
    "ڈی ایچ اے فیز 4 بلاک U",
    "ڈی ایچ اے فیز 5 بلاک C", "ڈی ایچ اے فیز 5 بلاک D",
    "ڈی ایچ اے فیز 5 بلاک J", "ڈی ایچ اے فیز 5 بلاک O",
    "ڈی ایچ اے فیز 5 بلاک T", "ڈی ایچ اے فیز 5 بلاک X",
    "ڈی ایچ اے فیز 6 بلاک B", "ڈی ایچ اے فیز 6 بلاک I",
    "ڈی ایچ اے فیز 6 بلاک N", "ڈی ایچ اے فیز 6 بلاک P",
    "ڈی ایچ اے فیز 7 بلاک M", "ڈی ایچ اے فیز 7 بلاک R",
    "ڈی ایچ اے فیز 8 بلاک G", "ڈی ایچ اے فیز 8 بلاک Q",
    "ڈی ایچ اے فیز 8 بلاک S", "ڈی ایچ اے فیز 8 بلاک V",
    "ڈی ایچ اے فیز 9 بلاک B", "ڈی ایچ اے فیز 9 بلاک Z",

    # --- Bahria Town (بحریہ ٹاؤن) sectors ---
    "بحریہ ٹاؤن سیکٹر A", "بحریہ ٹاؤن سیکٹر B",
    "بحریہ ٹاؤن سیکٹر C", "بحریہ ٹاؤن سیکٹر D",
    "بحریہ ٹاؤن سیکٹر E", "بحریہ ٹاؤن سیکٹر F",
    "بحریہ ٹاؤن سیکٹر G", "بحریہ ٹاؤن سیکٹر H",
    # Bahria with specific blocks
    "بحریہ ٹاؤن سیکٹر A بلاک E",
    "بحریہ ٹاؤن سیکٹر B بلاک B", "بحریہ ٹاؤن سیکٹر B بلاک H",
    "بحریہ ٹاؤن سیکٹر B بلاک I", "بحریہ ٹاؤن سیکٹر B بلاک J",
    "بحریہ ٹاؤن سیکٹر C بلاک C", "بحریہ ٹاؤن سیکٹر C بلاک D",
    "بحریہ ٹاؤن سیکٹر C بلاک I",
    "بحریہ ٹاؤن سیکٹر D بلاک D", "بحریہ ٹاؤن سیکٹر D بلاک J",
    "بحریہ ٹاؤن سیکٹر E بلاک A", "بحریہ ٹاؤن سیکٹر E بلاک C",
    "بحریہ ٹاؤن سیکٹر E بلاک H", "بحریہ ٹاؤن سیکٹر E بلاک I",
    "بحریہ ٹاؤن سیکٹر F بلاک A", "بحریہ ٹاؤن سیکٹر F بلاک G",
    "بحریہ ٹاؤن سیکٹر G بلاک B", "بحریہ ٹاؤن سیکٹر G بلاک F",
    "بحریہ ٹاؤن سیکٹر H بلاک G", "بحریہ ٹاؤن سیکٹر H بلاک H",
    # Bahria Orchard
    "بحریہ آرچرڈ", "بحریہ آرچرڈ فیز 1", "بحریہ آرچرڈ فیز 2",
    "بحریہ آرچرڈ فیز 1 بلاک B", "بحریہ آرچرڈ فیز 2 بلاک B",

    # --- Askari (آسکاری) ---
    "آسکاری 1", "آسکاری 2", "آسکاری 3", "آسکاری 4",
    "آسکاری 5", "آسکاری 6", "آسکاری 7", "آسکاری 8",
    "آسکاری 9", "آسکاری 10", "آسکاری 11", "آسکاری 12", "آسکاری 13",
    "آسکاری 5 بلاک E", "آسکاری 5 بلاک F",
    "آسکاری 6 بلاک E",
    "آسکاری 8 بلاک C", "آسکاری 8 بلاک H",
    "آسکاری 10 بلاک C", "آسکاری 10 بلاک E",
    "آسکاری 11 بلاک D", "آسکاری 11 بلاک H",
    "آسکاری 12 بلاک A", "آسکاری 12 بلاک F",
    "آسکاری 13 بلاک G", "آسکاری 13 بلاک H",

    # --- WAPDA Town (واپڈا ٹاؤن) ---
    "واپڈا ٹاؤن", "واپڈا ٹاؤن فیز 1", "واپڈا ٹاؤن فیز 2",
    "واپڈا ٹاؤن فیز 1 بلاک A", "واپڈا ٹاؤن فیز 1 بلاک B",
    "واپڈا ٹاؤن فیز 1 بلاک C", "واپڈا ٹاؤن فیز 1 بلاک J",
    "واپڈا ٹاؤن فیز 2 بلاک A", "واپڈا ٹاؤن فیز 2 بلاک B",
    "واپڈا ٹاؤن فیز 2 بلاک E",

    # --- LDA City (لی ڈی اے سٹی) ---
    "لی ڈی اے سٹی",
    "لی ڈی اے سٹی سیکٹر 1", "لی ڈی اے سٹی سیکٹر 2",
    "لی ڈی اے سٹی سیکٹر 3", "لی ڈی اے سٹی سیکٹر 4",
    "لی ڈی اے سٹی سیکٹر 5",
    "لی ڈی اے سٹی سیکٹر 1 بلاک B",
    "لی ڈی اے سٹی سیکٹر 2 بلاک H",
    "لی ڈی اے سٹی سیکٹر 3 بلاک B", "لی ڈی اے سٹی سیکٹر 3 بلاک H",
    "لی ڈی اے سٹی سیکٹر 4 بلاک B", "لی ڈی اے سٹی سیکٹر 4 بلاک C",
    "لی ڈی اے سٹی سیکٹر 4 بلاک M",
    "لی ڈی اے سٹی سیکٹر 5 بلاک C", "لی ڈی اے سٹی سیکٹر 5 بلاک I",

    # --- Valencia Town (والینشیا ٹاؤن) ---
    "والینشیا ٹاؤن", "والینشیا",
    "والینشیا ٹاؤن بلاک H", "والینشیا ٹاؤن بلاک N",

    # --- PIA Society (پی آئی اے سوسائٹی) ---
    "پی آئی اے سوسائٹی",
    "پی آئی اے سوسائٹی بلاک H", "پی آئی اے سوسائٹی بلاک I",

    # --- PCSIR (پی سی ایس آئی آر) ---
    "پی سی ایس آئی آر",
    "پی سی ایس آئی آر فیز 1", "پی سی ایس آئی آر فیز 2",
    "پی سی ایس آئی آر فیز 1 بلاک H",
    "پی سی ایس آئی آر فیز 2 بلاک F", "پی سی ایس آئی آر فیز 2 بلاک G",

    # --- Other housing societies ---
    "الخضریا ہاؤسنگ", "الخضریا ہاؤسنگ بلاک F",
    "ایڈن آباد", "ایڈن آباد بلاک C",
    "جوہر ٹاؤن بلاک H", "جوہر ٹاؤن بلاک Q",

    # --- Additional roads ---
    "بیدیاں روڈ", "رائیونڈ روڈ", "شیخ زید روڈ",
    "آسوکی روڈ", "اعوان روڈ", "اقبال ایونیو", "الحمد روڈ",
    "چونیاں روڈ", "ڈیفنس روڈ", "روٹی تندور روڈ",
    "ریونیو روڈ", "ٹنکی والا روڈ", "وارث روڈ",
    "کاچھا جیل روڈ", "کچھہری روڈ", "کینٹ روڈ",
    "نجات روڈ", "نشتر روڈ", "نہر کنار روڈ",
    "مین والٹن روڈ", "بیرونی سمن آباد روڈ",
    "لیاقت علی خان روڈ", "مولانا شوکت علی روڈ",
    "شاہ پور کانجراں روڈ", "غازی آباد روڈ",
    "جناح ایونیو", "خیابان جناح",
    "ساگیان انٹرچینج", "بابو صابو انٹرچینج",
    "نیاز بیگ انٹرچینج", "ٹھوکر نیاز بیگ",
    "گجومتہ انٹرچینج", "نیا زی انٹرچینج",
    "آربی بلاک روڈ", "شاہراہ قائداعظم مال روڈ",
    "دہلی گیٹ روڈ", "شادمان روڈ", "شادمـان روڈ",
    "شاہ عالمی روڈ", "ادورڈ روڈ", "ایڈورڈ روڈ",
    "صدر بازار روڈ", "گجو متہ روڈ",

    # --- Additional Lahore areas/thanas ---
    "اسلام پورہ", "اندرون لاہور", "فیکٹری ایریا",
    "ملت پارک", "نارتھ کینٹ", "ساوتھ کینٹ",
    "نشتر ٹاؤن", "نشتر کالونی", "نصیر آباد",
    "نواز ٹاؤن", "نواں کوٹ", "نولکھا",
    "سول لائنز", "لوئر مال", "لور اسٹیشن",
    "قائداعظم انڈسٹریل ایریا", "خان بابا",
    "کہنا", "برکی", "ڈیفنس بی",
    "کٹلری", "بادامی باغ",
]

# ============================================================
#  COMMON URDU LOCATION WORDS - for partial matching
# ============================================================
LOCATION_WORDS = {
    "مارکیٹ": ["ارکیٹ", "ماککیٹ", "مارکیط", "مارک", "مار کیٹ", "ما رکیٹ", "مارکٹ", "مارکیط", "ارکیط"],
    "روڈ": ["رروڈ", "ر وڈ", "رود", "روز", "رین", "ررڈ", "ردڈ", "روف", "ردز"],
    "ٹاؤن": ["ماؤن", "جائان", "لاؤن", "جاؤن", "تاؤں", "ٹائن", "لوان", "ٹاون", "آؤن"],
    "چوک": ["جوک", "پک", "چک", "جک", "چ ک"],
    "گیٹ": ["کیٹ", "گیط", "یلیٹ", "لیٹ", "کٹ", "یط", "گی ٹ"],
    "پارک": ["ارک", "پار", "بارک", "بارگ"],
    "بلاک": ["لاک", "ملاک", "یلاک", "بلاگ", "بلک"],
    "بازار": ["بزار", "بازر", "بار", "زار", "با زار", "یازار"],
    "فیز": ["فین", "فیر", "فپر", "قیز", "فر", "فیص"],
    "سیکٹر": ["سیکنر", "سکٹر", "سی کٹر", "صیکٹر", "شیکٹر"],
    "ڈی ایچ اے": ["ڈے ایچ اے", "ری ایچ اے", "ڈی ایچ ای", "ڈی ائچ اے", "ڈے ائچ"],
    "بحریہ": ["بحرہ", "بحربہ", "نحریہ", "بحر یہ", "بحری ہ"],
    "آسکاری": ["آسکار", "اسکاری", "آسکارے", "اسکار", "آسکری"],
    "واپڈا": ["واپدا", "وپڈا", "واپ ڈا", "وابڈا", "واپلا"],
    "والینشیا": ["والنشیا", "والینسبا", "وایلنشیا", "والینش"],
    "لی ڈی اے": ["لے ڈی اے", "لی ڈے اے", "لی ڈ اے"],
    "ہاؤسنگ": ["ہاونگ", "ہاؤسبگ", "ہاؤنگ"],
    "سوسائٹی": ["سوسائٹے", "سوسائ", "صوصائٹی"],
    "انٹرچینج": ["انٹرچنج", "انترچینج", "انٹر چینج"],
    "ایمپوریئم": ["ایمپوربم", "امپوریم"],
    "ایونیو": ["ایونے", "ایوینو", "ایوبیو"],
    "مسجد": ["مسخد", "مسجر"],
    "نگر": ["تگر", "بگر"],
    "کالونی": ["کالونے", "کالوبی"],
    "سوسائٹی": ["سوسائٹے", "سوسائ"],
    "شالامار": ["سالامار", "شالا مار", "شالمار", "شال مار", "شالا ار", "شال ار", "شالشار"],
    "بھاٹی": ["بعائی", "بھانی", "بعاتی", "بھائی", "بای", "بھاٹ", "بمائی"],
    "ماڈل": ["مال", "ماأال", "مادل", "ملال", "مبال"],
    "انارکلی": ["اتارکلی", "انارکل"],
    "فیروزپور": ["فیروز پور", "فیروز بور"],
    "ملتان": ["ملتاب", "ملتاں"],
    "فیصل": ["فیظل", "فظل", "فیسل"],
    "گلبرگ": ["کلبرگ", "گلبرک", "کلپرگ"],
    "حیدر": ["ہیدر", "ہیور", "حیور", "جیدر"],
    "اقبال": ["اتبال", "وقپال", "دقپال", "قپال", "اقبل", "وقال", "وقبال", "ماؤن"],
    "دالم": ["دا لم", "الم", "اسلام"],
    "داتا": ["ڈیٹا", "ڈاٹا", "تا", "اڑھ", "ڈی ٹا", "اڑہ", "دا تا", "جاور", "جہ ور", "جدہ", "داٹا"],
    "دربار": ["ہار", "دربر", "درپار", "ہر بار", "اربار", "دار بار", "ہار گر", "ار", "بار", "ا ر"],
    "سرکلر": ["سر کار", "صرکار", "سرکر", "ثر کار", "صر کار", "سر گار", "سرگار", "زگ ر", "زگر", "کگ ر", "گر", "سرکار"],
    "داتا دربار": ["ڈیٹا دربار", "داتا ہار", "اڑھ ہار", "ڈاٹا دربار", "دا تا دربار", "تا ہار", "جاور ار", "جاور ہار", "جور ار"],
    "داتا دربار سرکلر روڈ": ["اڑھ ہار گر رون", "جاور ار زگ ر وڈ", "اڑھ ہار گر روڈ", "جاور ار سرکلر روڈ", "جاور ار سرکار روڈ", "داتا دربار سرکار روڈ"],
    "اسلام": ["ایام", "ازیم", "اسلاب", "اصلام", "اظلام"],
    "مغلپورہ": ["مفلپورہ", "مغلبورہ"],
    "سمن آباد": ["سمن اباد", "سمن ابال", "سامنآباد", "صمن آباد"],
    "اچھرہ": ["اچرہ", "اچھرا"],
    "کینٹ": ["کنٹ", "کنت"],
    "شاہدرہ": ["شادرہ", "شاہ درا"],
    "مزنگ": ["مزتگ", "مزبگ"],
    "چوبرجی": ["چوبرخی", "جوبرجی"],
    "لکشمی": ["لکشمے", "لکثمی"],
    "لبرٹی": ["لبرتی", "لبرٹے"],
    "لوہاری": ["ادرک", "لذ ری", "لذری", "لہاری", "لواری", "نوہاری", "لوہ اری", "لو ہاری", "لرہاری"],
    "لوہاری گیٹ": ["ادرک یلیٹ", "ادرک گیٹ", "لذ ری یلیٹ", "لذری یلیٹ", "لہاری گیٹ"],
    "لوہاری بازار": ["لذ ری زار", "لذری زار", "ادرک زار", "لہاری بازار", "لوہاری بزار"],
}

# ============================================================
#  CHARACTER-LEVEL OCR MISREADS  (Tesseract Urdu common errors)
# ============================================================
CHAR_SUBSTITUTIONS = {
    # Very common confusions in Nastaliq
    "ۻ": "ٹ", "ۀ": "ہ", 
    "؛": "",  # semicolon artifact
    "٭": "",  # star artifact
    ",": "،",  # comma to Urdu comma
    # Number-letter confusion
    "۸": "ا", "۱": "ا", "۰": "۔", "٦": "،",
    "۲": "ر", "۵": "و", "۷": "ق",
    "0": "۔", "7": "ق", "8": "ا", "6": "و",
    # Common letter swaps
    "ؤ": "و",
}

# ============================================================
#  CORE FUNCTIONS
# ============================================================

def _normalize_text(text: str) -> str:
    """Normalize Urdu text for comparison: remove diacritics, normalize spaces."""
    if not text:
        return ""
    # Remove Arabic diacritics (harakat)
    text = re.sub(r'[\u064B-\u065F\u0670]', '', text)
    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    # Remove stray punctuation
    text = re.sub(r'[\.۔,،:;؛\-_=\[\]{}()|/\\@#$%^&*!?؟\+]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def _urdu_similarity(s1: str, s2: str) -> float:
    """
    Compute similarity between two Urdu strings.
    Uses SequenceMatcher but also accounts for common OCR substitutions.
    """
    if not s1 or not s2:
        return 0.0
    s1 = _normalize_text(s1)
    s2 = _normalize_text(s2)
    if not s1 or not s2:
        return 0.0
    return SequenceMatcher(None, s1, s2).ratio()


def _apply_char_fixes(text: str) -> str:
    """Apply character-level substitutions for known Tesseract misreads."""
    for old, new in CHAR_SUBSTITUTIONS.items():
        text = text.replace(old, new)
    return text


def correct_word(word: str, min_similarity: float = 0.55) -> str:
    """
    Correct a single word using the location words dictionary.
    Returns the best match if similarity > threshold, else returns original.
    """
    word_clean = _normalize_text(word)
    if not word_clean or len(word_clean) < 2:
        return word
    
    best_match = word
    best_score = 0.0
    
    for correct_word_str, misreads in LOCATION_WORDS.items():
        # Check against correct word
        sim = _urdu_similarity(word_clean, correct_word_str)
        if sim > best_score and sim >= min_similarity:
            best_score = sim
            best_match = correct_word_str
        
        # Check against known misreads
        for misread in misreads:
            sim = _urdu_similarity(word_clean, misread)
            if sim > best_score and sim >= min_similarity:
                best_score = sim
                best_match = correct_word_str
    
    return best_match


def correct_location_text(text: str) -> str:
    """
    Correct a full location text using fuzzy matching.
    
    IMPROVED: Prefers known multi-word locations and limits output length
    to avoid over-correction of noisy OCR text.
    
    Steps:
    1. Apply character-level fixes
    2. Try matching against full known locations 
    3. Try multi-word location patterns (2-4 words)
    4. Fall back to word-level correction (limited to first 4-5 words)
    5. Return best result
    """
    if not text or len(text.strip()) < 2:
        return text
    
    # Step 1: Character-level cleanup
    text = _apply_char_fixes(text)
    text_clean = _normalize_text(text)
    
    if not text_clean:
        return text
    
    # Step 2: Try matching against full known locations
    best_location = None
    best_location_score = 0.0
    
    for loc in KNOWN_LOCATIONS:
        sim = _urdu_similarity(text_clean, loc)
        if sim > best_location_score:
            best_location_score = sim
            best_location = loc
    
    # Log the best match score for debugging
    import logging
    logger = logging.getLogger(__name__)
    if best_location:
        logger.debug(f"[Fuzzy] Best location match: '{best_location}' (score: {best_location_score:.3f})")
    
    # If very high match against a known location, return it directly
    # Raised threshold to 0.75 to avoid false positives on poor OCR
    if best_location_score >= 0.75:
        logger.info(f"[Fuzzy] High confidence match: '{best_location}' (score: {best_location_score:.3f})")
        return best_location
    
    # If moderate match (0.65-0.75), log warning about uncertain match
    if 0.65 <= best_location_score < 0.75:
        logger.warning(f"[Fuzzy] Moderate confidence match: '{best_location}' (score: {best_location_score:.3f}) - continuing to multi-word patterns")
        # Still try multi-word patterns before accepting this moderate match
        pass
    
    # Step 3: Try multi-word patterns (2-4 words) against known locations
    # This catches "داتا دربار" better than word-by-word correction
    words = text_clean.split()
    
    # Try first 2 words
    if len(words) >= 2:
        two_word = ' '.join(words[:2])
        for loc in KNOWN_LOCATIONS:
            if _urdu_similarity(two_word, loc) >= 0.55:
                # Found good 2-word match, correct just these two words
                w1 = correct_word(words[0])
                w2 = correct_word(words[1])
                result = f"{w1} {w2}"
                # Try 3rd word if it looks like "روڈ" or location word
                if len(words) >= 3 and (len(words[2]) >= 2):
                    w3 = correct_word(words[2])
                    # Check if 3-word combo is better
                    three_word_candidate = f"{w1} {w2} {w3}"
                    best_three = None
                    best_three_score = 0.0
                    for loc in KNOWN_LOCATIONS:
                        sim = _urdu_similarity(three_word_candidate, loc)
                        if sim > best_three_score:
                            best_three_score = sim
                            best_three = loc
                    if best_three_score >= 0.55:
                        return best_three
                    # If 3rd word is a location word (روڈ, مارکیٹ, etc), include it
                    if w3 in ['روڈ', 'مارکیٹ', 'چوک', 'گیٹ', 'بازار', 'بلاک', 'ٹاؤن', 'پارک']:
                        result = three_word_candidate
                return result
    
    # Try first 3 words
    if len(words) >= 3:
        three_word = ' '.join(words[:3])
        for loc in KNOWN_LOCATIONS:
            if _urdu_similarity(three_word, loc) >= 0.55:
                w1 = correct_word(words[0])
                w2 = correct_word(words[1])
                w3 = correct_word(words[2])
                return f"{w1} {w2} {w3}"
    
    # Try first 4 words
    if len(words) >= 4:
        four_word = ' '.join(words[:4])
        for loc in KNOWN_LOCATIONS:
            if _urdu_similarity(four_word, loc) >= 0.55:
                w1 = correct_word(words[0])
                w2 = correct_word(words[1])
                w3 = correct_word(words[2])
                w4 = correct_word(words[3])
                return f"{w1} {w2} {w3} {w4}"
    
    # Step 4: Fall back to word-level correction (LIMIT to first 5 words to avoid mess)
    max_words = min(5, len(words))
    corrected_words = []
    for i in range(max_words):
        w = words[i]
        if len(w) >= 2:
            corrected = correct_word(w)
            corrected_words.append(corrected)
        else:
            corrected_words.append(w)
    
    corrected_text = ' '.join(corrected_words)
    
    # Step 5: Try matching corrected text against known locations
    best_after = None
    best_after_score = 0.0
    for loc in KNOWN_LOCATIONS:
        sim = _urdu_similarity(corrected_text, loc)
        if sim > best_after_score:
            best_after_score = sim
            best_after = loc
    
    # If word correction brought us close to a known location, use it
    # BUT also check that the original text had SOME similarity to avoid false assemblies
    if best_after_score >= 0.55:
        original_to_result = _urdu_similarity(text_clean, best_after)
        # Trust high corrected scores, OR reasonable original similarity
        # Threshold lowered: OCR of Urdu handwriting is very garbled, heavy correction is normal
        if best_after_score >= 0.80 or original_to_result >= 0.12:
            logger.info(f"[Fuzzy] Word-corrected match: '{best_after}' (score: {best_after_score:.3f}, orig: {original_to_result:.3f})")
            return best_after
        else:
            logger.warning(f"[Fuzzy] Word-corrected '{best_after}' rejected: scores too low (corrected: {best_after_score:.3f}, orig: {original_to_result:.3f})")
    
    # If even the best location match from Step 2 was moderate, return it
    if 0.45 <= best_location_score < 0.75:
        logger.info(f"[Fuzzy] Returning moderate initial match: '{best_location}' (score: {best_location_score:.3f})")
        return best_location
    
    # Otherwise return the best corrected text even if score is marginal
    if best_after and best_after_score >= 0.45:
        logger.info(f"[Fuzzy] Returning marginal corrected match: '{best_after}' (score: {best_after_score:.3f})")
        return best_after
    
    logger.warning(f"[Fuzzy] No reliable match found (best scores: initial={best_location_score:.3f}, corrected={best_after_score:.3f})")
    return ""


def multi_vote_correct(ocr_results: list, min_results: int = 2) -> str:
    """
    Multi-config voting + fuzzy correction.
    
    Takes a list of OCR results from different configs, applies fuzzy correction
    to each, then picks the best one based on:
    1. How many corrected results agree (voting)
    2. Similarity to known locations
    3. Quality score (Urdu char count)
    
    Args:
        ocr_results: List of dicts with 'text', 'score', 'method' keys
        min_results: Minimum results needed for voting
    
    Returns:
        Best corrected location text
    """
    if not ocr_results:
        return ""
    
    # Apply fuzzy correction to each result
    corrected_results = []
    for r in ocr_results:
        raw_text = r.get('text', '')
        if not raw_text or len(raw_text.strip()) < 2:
            continue
        corrected = correct_location_text(raw_text)
        corrected_results.append({
            'raw': raw_text,
            'corrected': corrected,
            'score': r.get('score', 0),
            'method': r.get('method', ''),
        })
    
    if not corrected_results:
        return ""
    
    # Voting: group similar corrected texts
    groups = []
    for cr in corrected_results:
        placed = False
        for group in groups:
            rep = group[0]['corrected']
            if _urdu_similarity(cr['corrected'], rep) >= 0.6:
                group.append(cr)
                placed = True
                break
        if not placed:
            groups.append([cr])
    
    # Pick the group with most votes and highest total score
    groups.sort(key=lambda g: (len(g), sum(x['score'] for x in g)), reverse=True)
    
    best_group = groups[0]
    
    # From the winning group, pick the result closest to a known location
    best_final = None
    best_final_score = -999
    
    for item in best_group:
        # Score: known location similarity + OCR quality
        loc_sim = 0.0
        for loc in KNOWN_LOCATIONS:
            sim = _urdu_similarity(item['corrected'], loc)
            if sim > loc_sim:
                loc_sim = sim
        
        combined_score = loc_sim * 100 + item['score']
        if combined_score > best_final_score:
            best_final_score = combined_score
            best_final = item['corrected']
    
    return best_final or corrected_results[0]['corrected']


# ============================================================
#  CONVENIENCE: Test on a single string
# ============================================================
def test_correction(text: str) -> dict:
    """Test fuzzy correction on a single OCR text. Returns details."""
    corrected = correct_location_text(text)
    
    # Find best matching location
    best_loc = None
    best_sim = 0.0
    for loc in KNOWN_LOCATIONS:
        sim = _urdu_similarity(corrected, loc)
        if sim > best_sim:
            best_sim = sim
            best_loc = loc
    
    return {
        'input': text,
        'corrected': corrected,
        'best_match': best_loc,
        'similarity': best_sim,
    }

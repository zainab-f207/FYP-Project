"""
Best possible Tesseract approach for Urdu crime area OCR.
Uses multi-config word-level confidence voting with tessdata_best.
"""
import cv2
import numpy as np
import pytesseract
import os
import re
from collections import Counter, defaultdict

print("="*60)
print("BEST TESSERACT APPROACH - Word-Level Confidence Voting")
print("="*60)

# Config
TESSDATA_DIR = r"E:\programming softwares\Tesseract-OCR\tessdata"
IMG_PATH = "crime_area_best.png"

# Check if tessdata_best available
best_urd = os.path.join(TESSDATA_DIR, "urd_best.traineddata")
best_ara = os.path.join(TESSDATA_DIR, "ara_best.traineddata")
has_best = os.path.exists(best_urd) and os.path.exists(best_ara)
print(f"tessdata_best available: {has_best}")

img = cv2.imread(IMG_PATH)
if img is None:
    print(f"ERROR: Cannot load {IMG_PATH}")
    exit(1)
print(f"Image: {img.shape[1]}x{img.shape[0]}")

gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

# ============================================================
# PREPROCESSING VARIANTS  
# ============================================================
def get_preprocessed_variants(gray_img):
    """Generate best preprocessing variants from exhaustive testing"""
    variants = {}
    
    # 2x upscale base
    s2x = cv2.resize(gray_img, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
    # 3x upscale base
    s3x = cv2.resize(gray_img, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC)
    
    # 1. BEST: 2x + denoise + Otsu
    dn2x = cv2.fastNlMeansDenoising(s2x, None, 10, 7, 21)
    blur1 = cv2.GaussianBlur(dn2x, (3, 3), 0)
    _, v = cv2.threshold(blur1, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    variants['2x_dn_otsu'] = v

    # 2. 2x + bilateral + Otsu  
    bil = cv2.bilateralFilter(s2x, 9, 75, 75)
    blur2 = cv2.GaussianBlur(bil, (3, 3), 0)
    _, v = cv2.threshold(blur2, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    variants['2x_bil_otsu'] = v

    # 3. 3x + raw Otsu
    blur3 = cv2.GaussianBlur(s3x, (3, 3), 0)
    _, v = cv2.threshold(blur3, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    variants['3x_otsu'] = v

    # 4. 2x + CLAHE + Otsu
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    cl = clahe.apply(s2x)
    blur4 = cv2.GaussianBlur(cl, (3, 3), 0)
    _, v = cv2.threshold(blur4, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    variants['2x_clahe_otsu'] = v

    # 5. 2x + denoise + adaptive threshold
    adap = cv2.adaptiveThreshold(dn2x, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 15, 8)
    variants['2x_dn_adaptive'] = adap

    # 6. 3x + morph close + Otsu
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    morph = cv2.morphologyEx(s3x, cv2.MORPH_CLOSE, kernel)
    blur5 = cv2.GaussianBlur(morph, (3, 3), 0)
    _, v = cv2.threshold(blur5, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    variants['3x_morph_otsu'] = v

    # 7. 2x + sharpen + Otsu
    sharp_k = np.array([[-1,-1,-1],[-1,9,-1],[-1,-1,-1]])
    sharp = cv2.filter2D(s2x, -1, sharp_k)
    blur6 = cv2.GaussianBlur(sharp, (3, 3), 0)
    _, v = cv2.threshold(blur6, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    variants['2x_sharp_otsu'] = v

    return variants

variants = get_preprocessed_variants(gray)
print(f"Preprocessing variants: {len(variants)}")

# ============================================================
# OCR CONFIGS
# ============================================================
configs = [
    ('urd', '--psm 6 --oem 1'),
    ('urd', '--psm 4 --oem 1'),
    ('urd', '--psm 3 --oem 1'),
    ('urd+ara', '--psm 6 --oem 1'),
]

# If tessdata_best available, also test with those
if has_best:
    # We need to temporarily swap the tessdata files to use best
    # For now, create a separate tessdata dir with best files
    best_dir = os.path.join(os.getcwd(), "_tessdata_best")
    os.makedirs(best_dir, exist_ok=True)
    
    # Copy/link best files 
    import shutil
    for src_name, dst_name in [("urd_best.traineddata", "urd.traineddata"), 
                                ("ara_best.traineddata", "ara.traineddata")]:
        src = os.path.join(TESSDATA_DIR, src_name)
        dst = os.path.join(best_dir, dst_name)
        if not os.path.exists(dst):
            shutil.copy2(src, dst)
    
    # Also copy osd.traineddata
    osd_src = os.path.join(TESSDATA_DIR, "osd.traineddata")
    osd_dst = os.path.join(best_dir, "osd.traineddata")
    if os.path.exists(osd_src) and not os.path.exists(osd_dst):
        shutil.copy2(osd_src, osd_dst)

# ============================================================
# WORD-LEVEL OCR EXTRACTION
# ============================================================
def extract_words(img, lang, config, tessdata_dir=None):
    """Extract words with confidence from image using image_to_data"""
    full_config = config
    if tessdata_dir:
        full_config = f'--tessdata-dir "{tessdata_dir}" {config}'
    
    try:
        data = pytesseract.image_to_data(img, lang=lang, config=full_config, output_type=pytesseract.Output.DICT)
        words = []
        for i in range(len(data['text'])):
            text = data['text'][i].strip()
            conf = int(data['conf'][i])
            if text and conf > 0:
                words.append({
                    'text': text,
                    'conf': conf,
                    'left': data['left'][i],
                    'top': data['top'][i],
                    'width': data['width'][i],
                    'height': data['height'][i],
                    'line_num': data['line_num'][i],
                    'word_num': data['word_num'][i],
                })
        return words
    except Exception as e:
        return []

def extract_full_text(img, lang, config, tessdata_dir=None):
    """Extract full text from image"""
    full_config = config
    if tessdata_dir:
        full_config = f'--tessdata-dir "{tessdata_dir}" {config}'
    try:
        return pytesseract.image_to_string(img, lang=lang, config=full_config).strip()
    except:
        return ""

# ============================================================
# RUN ALL COMBINATIONS
# ============================================================
print(f"\n{'='*60}")
print("Running OCR combinations...")
print(f"{'='*60}")

all_word_results = []  # List of (words_list, method_name)
all_text_results = []  # List of (text, method_name, score)

for var_name, var_img in variants.items():
    for lang, cfg in configs:
        method = f"{var_name}|{lang}|{cfg.split('--psm ')[1][:1] if '--psm' in cfg else '?'}"
        
        # Word-level extraction
        words = extract_words(var_img, lang, cfg)
        if words:
            all_word_results.append((words, method))
        
        # Full text extraction 
        text = extract_full_text(var_img, lang, cfg)
        if text:
            # Score
            urdu = sum(1 for c in text if '\u0600' <= c <= '\u06FF')
            garbage = sum(1 for c in text if c in '[]{}()!@#$%^&*;:<>|')
            w = text.split()
            unique = len(set(w))
            rep = unique / max(len(w), 1)
            score = urdu * rep - garbage * 5
            if len(text) > 300:
                score -= (len(text) - 300) * 0.5
            all_text_results.append((text, method, score))

    # Also test with tessdata_best if available
    if has_best:
        for lang, cfg in [('urd', '--psm 6 --oem 1'), ('urd', '--psm 4 --oem 1')]:
            method = f"{var_name}|{lang}_best|psm{cfg.split('--psm ')[1][:1]}"
            
            words = extract_words(var_img, lang, cfg, tessdata_dir=best_dir)
            if words:
                all_word_results.append((words, method))
            
            text = extract_full_text(var_img, lang, cfg, tessdata_dir=best_dir)
            if text:
                urdu = sum(1 for c in text if '\u0600' <= c <= '\u06FF')
                garbage = sum(1 for c in text if c in '[]{}()!@#$%^&*;:<>|')
                w = text.split()
                unique = len(set(w))
                rep = unique / max(len(w), 1)
                score = urdu * rep - garbage * 5
                if len(text) > 300:
                    score -= (len(text) - 300) * 0.5
                all_text_results.append((text, method, score))

print(f"\nTotal word-level results: {len(all_word_results)}")
print(f"Total text results: {len(all_text_results)}")

# ============================================================
# ANALYSIS 1: High-confidence words across all configs
# ============================================================
print(f"\n{'='*60}")
print("HIGH-CONFIDENCE WORDS (conf >= 30)")
print(f"{'='*60}")

word_conf_map = defaultdict(list)  # word -> list of confidences
for words, method in all_word_results:
    for w in words:
        if w['conf'] >= 30 and len(w['text']) >= 2:
            # Normalize the word
            word_text = w['text'].strip()
            # Remove isolated punctuation
            if re.match(r'^[\.\,\-\_\:\;\!\?\s]+$', word_text):
                continue
            word_conf_map[word_text].append(w['conf'])

# Sort by frequency × avg confidence
word_scores = []
for word, confs in word_conf_map.items():
    freq = len(confs)
    avg_conf = sum(confs) / len(confs)
    score = freq * avg_conf
    word_scores.append((word, freq, avg_conf, score))

word_scores.sort(key=lambda x: x[3], reverse=True)

print(f"Unique high-conf words: {len(word_scores)}")
print("\nTop 30 words (by frequency × confidence):")
for word, freq, avg_conf, score in word_scores[:30]:
    print(f"  {word:>20s}  freq={freq:2d}  avg_conf={avg_conf:5.1f}  score={score:7.1f}")

# ============================================================
# ANALYSIS 2: Best full-text results
# ============================================================
print(f"\n{'='*60}")
print("TOP 5 FULL-TEXT RESULTS")
print(f"{'='*60}")

all_text_results.sort(key=lambda x: x[2], reverse=True)
for text, method, score in all_text_results[:5]:
    print(f"\n  Method: {method} | Score: {score:.1f}")
    print(f"  Text: {text[:200]}")

# ============================================================
# ANALYSIS 3: Consensus text from high-confidence words
# ============================================================
print(f"\n{'='*60}")
print("CONSENSUS TEXT (words appearing >= 3 times with avg conf >= 35)")
print(f"{'='*60}")

# Filter words
consensus_words = [(w, f, c) for w, f, c, s in word_scores if f >= 3 and c >= 35]
print(f"Consensus words: {len(consensus_words)}")
for word, freq, avg_conf in consensus_words:
    print(f"  {word:>20s}  freq={freq:2d}  avg_conf={avg_conf:5.1f}")

if consensus_words:
    consensus_text = ' '.join([w for w, f, c in consensus_words])
    print(f"\nCombined: {consensus_text}")

# ============================================================
# ANALYSIS 4: Best single run with highest total word confidence
# ============================================================
print(f"\n{'='*60}")
print("BEST SINGLE RUN (highest total word confidence)")
print(f"{'='*60}")

best_run = None
best_total_conf = 0
for words, method in all_word_results:
    # Only words with conf >= 25
    good_words = [w for w in words if w['conf'] >= 25 and len(w['text']) >= 2]
    total_conf = sum(w['conf'] for w in good_words)
    if total_conf > best_total_conf:
        best_total_conf = total_conf
        best_run = (good_words, method, total_conf)

if best_run:
    words, method, total = best_run
    print(f"Method: {method}")
    print(f"Total confidence: {total}")
    print(f"Words ({len(words)}):")
    for w in words:
        print(f"  [{w['conf']:3d}] line={w['line_num']} word={w['word_num']} | {w['text']}")
    
    # Reconstruct text - sort by line then by position (right to left for Urdu)
    lines = defaultdict(list)
    for w in words:
        lines[w['line_num']].append(w)
    
    # Sort each line by x position (left to right, Tesseract already handles RTL)
    reconstructed = []
    for line_num in sorted(lines.keys()):
        line_words = sorted(lines[line_num], key=lambda w: w['left'])
        line_text = ' '.join([w['text'] for w in line_words])
        reconstructed.append(line_text)
    
    full_text = ' '.join(reconstructed)
    print(f"\nReconstructed: {full_text}")

# ============================================================
# ANALYSIS 5: Filter + clean approach
# ============================================================
print(f"\n{'='*60}")  
print("FILTERED BEST: High-conf words from top 3 runs, cleaned")
print(f"{'='*60}")

# Get top 3 runs by total confidence
run_scores = []
for words, method in all_word_results:
    good = [w for w in words if w['conf'] >= 20]
    total = sum(w['conf'] for w in good)
    run_scores.append((total, words, method))
run_scores.sort(reverse=True)

for rank, (total, words, method) in enumerate(run_scores[:3]):
    print(f"\n  Run {rank+1}: {method} (total_conf={total})")
    good = [w for w in words if w['conf'] >= 25 and len(w['text']) >= 2]
    
    # Reconstruct
    lines = defaultdict(list)
    for w in good:
        lines[w['line_num']].append(w)
    
    parts = []
    for ln in sorted(lines.keys()):
        lw = sorted(lines[ln], key=lambda w: w['left'])
        parts.append(' '.join([w['text'] for w in lw]))
    
    text = ' '.join(parts)
    # Clean
    text = re.sub(r'جائے\s*وقوعہ', '', text)
    text = re.sub(r'جائے\s*اور\s*علاقہ', '', text)
    text = re.sub(r'[\[\]{}()!@#$%^&*;:<>|]', '', text)
    text = ' '.join(text.split()).strip()
    print(f"  Result: {text}")

# Cleanup
if has_best and os.path.exists(best_dir):
    import shutil
    shutil.rmtree(best_dir)

print(f"\n{'='*60}")
print("DONE!")
print(f"{'='*60}")

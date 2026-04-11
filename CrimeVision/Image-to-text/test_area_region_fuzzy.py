"""
Test fuzzy correction on actual FIR image crime area region
Uses the same region extraction as fir_specialized_ocr.py
"""
import sys
import os
import cv2
import numpy as np
import pytesseract
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from urdu_location_dictionary import correct_location_text, _urdu_similarity
import re

# FIR Region coordinates (from fir_specialized_ocr.py)
CRIME_AREA_TOP = 0.38
CRIME_AREA_BOTTOM = 0.451
CRIME_AREA_LEFT = 0.29
CRIME_AREA_RIGHT = 0.62

def extract_crime_area_region(image_path: str):
    """Extract the crime area region from FIR image"""
    print(f"\n{'='*70}")
    print(f"LOADING FIR IMAGE: {image_path}")
    print('='*70)
    
    # Load image
    img = cv2.imread(image_path)
    if img is None:
        print(f"❌ Error: Could not load image from {image_path}")
        return None
    
    h, w = img.shape[:2]
    print(f"✓ Image loaded: {w}x{h}px")
    
    # Extract crime area region using coordinates
    y1 = int(h * CRIME_AREA_TOP)
    y2 = int(h * CRIME_AREA_BOTTOM)
    x1 = int(w * CRIME_AREA_LEFT)
    x2 = int(w * CRIME_AREA_RIGHT)
    
    crime_area_region = img[y1:y2, x1:x2]
    rh, rw = crime_area_region.shape[:2]
    
    print(f"✓ Extracted crime area region:")
    print(f"  - Coordinates: Y[{y1}:{y2}] X[{x1}:{x2}]")
    print(f"  - Size: {rw}x{rh}px")
    print(f"  - Position: {CRIME_AREA_TOP*100:.1f}%-{CRIME_AREA_BOTTOM*100:.1f}% vertical")
    
    # Save debug image
    debug_path = "debug_crime_area_region.png"
    cv2.imwrite(debug_path, crime_area_region)
    print(f"✓ Saved region to: {debug_path}")
    
    # Draw rectangle on original for visualization
    viz_img = img.copy()
    cv2.rectangle(viz_img, (x1, y1), (x2, y2), (0, 255, 0), 3)
    cv2.imwrite("debug_crime_area_location.png", viz_img)
    print(f"✓ Saved visualization to: debug_crime_area_location.png")
    
    return crime_area_region

def preprocess_for_ocr(region: np.ndarray):
    """Apply preprocessing to enhance Urdu text"""
    gray = cv2.cvtColor(region, cv2.COLOR_BGR2GRAY)
    
    # Upscale for better OCR
    h, w = gray.shape
    scale = 4.0
    scaled = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
    
    # Denoise
    denoised = cv2.fastNlMeansDenoising(scaled, None, h=10, templateWindowSize=7, searchWindowSize=21)
    
    # Enhance contrast
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(denoised)
    
    # Save preprocessed
    cv2.imwrite("debug_crime_area_preprocessed.png", enhanced)
    
    print(f"\n{'='*70}")
    print("PREPROCESSING")
    print('='*70)
    print(f"✓ Upscaled {scale}x: {w}x{h} → {enhanced.shape[1]}x{enhanced.shape[0]}px")
    print(f"✓ Applied: denoising + CLAHE contrast enhancement")
    print(f"✓ Saved to: debug_crime_area_preprocessed.png")
    
    return enhanced

def run_ocr(preprocessed: np.ndarray):
    """Run Tesseract OCR on preprocessed region"""
    print(f"\n{'='*70}")
    print("RUNNING OCR")
    print('='*70)
    
    # Try multiple Tesseract configs
    configs = [
        ('--oem 1 --psm 6', 'Standard'),
        ('--oem 1 --psm 4', 'Multi-column'),
        ('--oem 1 --psm 3', 'Auto'),
    ]
    
    results = []
    for config, name in configs:
        try:
            text = pytesseract.image_to_string(preprocessed, lang='urd', config=config)
            if text and text.strip():
                results.append({'text': text.strip(), 'config': name})
                print(f"✓ {name} OCR: {len(text.strip())} chars")
        except Exception as e:
            print(f"✗ {name} OCR failed: {e}")
    
    if not results:
        print("❌ No OCR results")
        return None
    
    # Use the result with most Urdu characters
    best = max(results, key=lambda r: sum(1 for c in r['text'] if '\u0600' <= c <= '\u06FF'))
    print(f"\n✓ Best result: {best['config']} ({len(best['text'])} chars)")
    return best['text']

def clean_ocr_text(raw_text: str):
    """Clean OCR text before fuzzy correction"""
    if not raw_text:
        return ""
    
    text = raw_text.strip()
    
    # Remove row labels
    labels = [
        r'جائے\s*وقوعہ',
        r'جائے\s*اور\s*علاقہ.*',
        r'تحصیل\s*و\s*ضلع',
        r'علاقہ\s*تحصیل',
    ]
    for label in labels:
        text = re.sub(label, '', text, flags=re.UNICODE)
    
    # Remove distance patterns
    distance_pattern = r'(?:سے|ے)\s*(?:تقر|نقر|تھر|تمر|تپ|تر|نر|۲ر|تت)'
    text = re.split(distance_pattern, text)[0]
    
    # Extract text before dash
    dash_patterns = [
        r'^(.*?)[\-]{3,}',
        r'^(.*?)[ـ]{3,}',
        r'^(.*?)[\.۔]{4,}',
    ]
    
    for pattern in dash_patterns:
        match = re.search(pattern, text, re.UNICODE)
        if match:
            text = match.group(1).strip()
            break
    
    # Clean up
    text = re.sub(r'\s+', ' ', text).strip()
    text = re.sub(r'^[\s\-_=.:،۔\d]+', '', text)
    text = re.sub(r'[\s\-_=.:،۔]+$', '', text)
    text = re.sub(r'[\[\]{}()!@#$%^&*;:<>|]', '', text)
    
    return text.strip()

def apply_fuzzy_correction(cleaned_text: str):
    """Apply fuzzy correction to fix broken Urdu OCR"""
    if not cleaned_text or len(cleaned_text) < 2:
        return ""
    
    print(f"\n{'='*70}")
    print("APPLYING FUZZY CORRECTION")
    print('='*70)
    print(f"Input text: {cleaned_text}")
    print(f"Length: {len(cleaned_text)} chars")
    
    # Count Urdu characters
    urdu_chars = sum(1 for c in cleaned_text if '\u0600' <= c <= '\u06FF')
    print(f"Urdu chars: {urdu_chars}")
    
    # Apply fuzzy correction
    corrected = correct_location_text(cleaned_text)
    
    print(f"\n{'─'*70}")
    if corrected != cleaned_text:
        similarity = _urdu_similarity(cleaned_text, corrected)
        print(f"✨ CORRECTED!")
        print(f"   From: {cleaned_text}")
        print(f"   To:   {corrected}")
        print(f"   Similarity: {similarity:.1%}")
    else:
        print(f"✓ No correction needed (text already clean)")
        print(f"   Result: {corrected}")
    
    return corrected

def test_fir_image(image_path: str):
    """Complete test pipeline"""
    print(f"\n{'#'*70}")
    print(f"# TESTING AREA FUZZY CORRECTION ON FIR IMAGE")
    print(f"{'#'*70}")
    
    # Step 1: Extract region
    region = extract_crime_area_region(image_path)
    if region is None:
        return
    
    # Step 2: Preprocess
    preprocessed = preprocess_for_ocr(region)
    
    # Step 3: Run OCR
    raw_ocr_text = run_ocr(preprocessed)
    if not raw_ocr_text:
        print("\n❌ OCR failed - no text extracted")
        return
    
    print(f"\n{'='*70}")
    print("RAW OCR OUTPUT")
    print('='*70)
    print(raw_ocr_text)
    print('─'*70)
    
    # Step 4: Clean text
    cleaned_text = clean_ocr_text(raw_ocr_text)
    print(f"\n{'='*70}")
    print("CLEANED TEXT (after removing labels, distance, etc.)")
    print('='*70)
    print(f"Before: {raw_ocr_text[:150]}")
    print(f"After:  {cleaned_text}")
    print('─'*70)
    
    # Step 5: Apply fuzzy correction
    corrected_text = apply_fuzzy_correction(cleaned_text)
    
    # Final summary
    print(f"\n{'='*70}")
    print("FINAL RESULT")
    print('='*70)
    print(f"Raw OCR:    {raw_ocr_text[:80]}")
    print(f"Cleaned:    {cleaned_text}")
    print(f"Corrected:  {corrected_text}")
    print('='*70)
    
    return {
        'raw': raw_ocr_text,
        'cleaned': cleaned_text,
        'corrected': corrected_text
    }

if __name__ == "__main__":
    import glob
    
    # Find FIR images
    if len(sys.argv) > 1:
        # User provided image path
        image_path = sys.argv[1]
        if os.path.exists(image_path):
            test_fir_image(image_path)
        else:
            print(f"❌ Error: Image not found: {image_path}")
    else:
        # Look for FIR images in common locations
        search_paths = [
            "*.png",
            "*.jpg",
            "FIR_*.png",
            "backend/FIR_*.png",
            "D:/FYP/Project/CrimeVision/OCRModel/app/data/raw/FIR_*.png"
        ]
        
        found_images = []
        for pattern in search_paths:
            found_images.extend(glob.glob(pattern))
        
        if found_images:
            print(f"\n{'='*70}")
            print(f"FOUND {len(found_images)} FIR IMAGE(S)")
            print('='*70)
            for i, img in enumerate(found_images[:5], 1):
                print(f"{i}. {img}")
            
            # Test first image
            print(f"\n{'='*70}")
            print(f"Testing with: {found_images[0]}")
            print('='*70)
            test_fir_image(found_images[0])
        else:
            print("\n❌ No FIR images found!")
            print("\nUsage:")
            print("  python test_area_region_fuzzy.py <path_to_fir_image>")
            print("\nExample:")
            print("  python test_area_region_fuzzy.py FIR_001.png")
            print("  python test_area_region_fuzzy.py D:/FYP/Project/CrimeVision/OCRModel/app/data/raw/FIR_001.png")

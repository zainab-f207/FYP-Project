"""Test thana extraction on multiple FIR images to understand patterns"""
import cv2
import numpy as np
import easyocr
import gc

# Initialize EasyOCR once
print("Initializing EasyOCR...")
reader = easyocr.Reader(['ur', 'en'], gpu=False)

# Test multiple FIR images
fir_images = [
    r'D:\FYP\Project\CrimeVision\OCRModel\app\data\raw\FIR_001.png',
    r'D:\FYP\Project\CrimeVision\OCRModel\app\data\raw\FIR_002.png',
    r'D:\FYP\Project\CrimeVision\OCRModel\app\data\raw\FIR_003.png',
]

for img_path in fir_images:
    print("\n" + "=" * 70)
    print(f"ANALYZING: {img_path}")
    print("=" * 70)
    
    img = cv2.imread(img_path)
    if img is None:
        print(f"ERROR: Could not load {img_path}")
        continue
    
    h, w = img.shape[:2]
    print(f"Image size: {w}x{h}")
    
    # Extract row 3 (thana row) - y=10%-16%
    y1, y2 = int(h * 0.10), int(h * 0.16)
    row3 = img[y1:y2, 0:w]
    
    # Save for inspection
    img_name = img_path.split('\\')[-1].replace('.png', '')
    cv2.imwrite(f"{img_name}_row3.png", row3)
    
    # Focus on right portion (70-95%) where thana usually is
    x1, x2 = int(w * 0.70), int(w * 0.95)
    thana_region = row3[:, x1-int(w*0.70):]  # Relative to row3
    thana_region = img[y1:y2, int(w*0.70):int(w*0.95)]
    
    print(f"Thana region: {thana_region.shape[1]}x{thana_region.shape[0]}px")
    cv2.imwrite(f"{img_name}_thana_region.png", thana_region)
    
    # Try different preprocessing approaches
    print("\n--- RAW IMAGE ---")
    results = reader.readtext(thana_region, paragraph=False)
    for bbox, text, conf in results:
        print(f"  '{text}' (conf={conf:.2f})")
    
    # Upscale 2x
    print("\n--- UPSCALED 2x ---")
    upscaled = cv2.resize(thana_region, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
    results = reader.readtext(upscaled, paragraph=False)
    for bbox, text, conf in results:
        print(f"  '{text}' (conf={conf:.2f})")
    
    # Grayscale + Adaptive threshold
    print("\n--- ADAPTIVE THRESHOLD ---")
    gray = cv2.cvtColor(thana_region, cv2.COLOR_BGR2GRAY)
    upscaled_gray = cv2.resize(gray, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
    thresh = cv2.adaptiveThreshold(upscaled_gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                    cv2.THRESH_BINARY, 11, 2)
    results = reader.readtext(thresh, paragraph=False)
    for bbox, text, conf in results:
        print(f"  '{text}' (conf={conf:.2f})")
    
    # Invert (in case text is white on dark)
    print("\n--- INVERTED ---")
    inverted = cv2.bitwise_not(thresh)
    results = reader.readtext(inverted, paragraph=False)
    for bbox, text, conf in results:
        print(f"  '{text}' (conf={conf:.2f})")
    
    # Clean up memory
    gc.collect()

print("\n" + "=" * 70)
print("DONE - Check *_thana_region.png files")
print("=" * 70)

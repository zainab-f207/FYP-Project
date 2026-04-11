"""
Try advanced image preprocessing to improve OCR accuracy for poor quality FIR scans.
"""
import cv2
import numpy as np
import easyocr
import sys

def enhance_image(img):
    """Apply multiple preprocessing techniques to improve OCR accuracy."""
    results = {}
    
    # Convert to grayscale
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    results['gray'] = gray
    
    # 1. Adaptive thresholding
    adaptive = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                      cv2.THRESH_BINARY, 31, 10)
    results['adaptive'] = adaptive
    
    # 2. CLAHE (Contrast Limited Adaptive Histogram Equalization)
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(gray)
    results['clahe'] = enhanced
    
    # 3. Bilateral filter (edge-preserving smoothing) + threshold
    bilateral = cv2.bilateralFilter(gray, 11, 75, 75)
    _, bilateral_thresh = cv2.threshold(bilateral, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    results['bilateral'] = bilateral_thresh
    
    # 4. Morphological operations
    kernel = np.ones((2, 2), np.uint8)
    morph = cv2.morphologyEx(adaptive, cv2.MORPH_CLOSE, kernel)
    results['morph'] = morph
    
    # 5. Sharpen
    sharpen_kernel = np.array([[-1, -1, -1], [-1, 9, -1], [-1, -1, -1]])
    sharpened = cv2.filter2D(gray, -1, sharpen_kernel)
    results['sharpen'] = sharpened
    
    # 6. Denoise + CLAHE
    denoised = cv2.fastNlMeansDenoising(gray, None, h=10)
    denoised_clahe = clahe.apply(denoised)
    results['denoise_clahe'] = denoised_clahe
    
    return results

# Load the FIR image
img_path = sys.argv[1] if len(sys.argv) > 1 else r'D:\FYP\Project\CrimeVision\OCRModel\app\data\raw\FIR_001.png'
img = cv2.imread(img_path)
h, w = img.shape[:2]
print(f'Image size: {w}x{h}')

# Extract the header area where thana name appears
# Looking at Row 1-2 area with "تھانہ لاہور" text
header_top = int(h * 0.01)
header_bottom = int(h * 0.08)
header = img[header_top:header_bottom, :]

print(f'Header region: y={header_top}-{header_bottom}')

# Also get Row 4 (location row)
row4_top = int(h * 0.36)
row4_bottom = int(h * 0.42)
row4 = img[row4_top:row4_bottom, :]
print(f'Row 4 region: y={row4_top}-{row4_bottom}')

# Initialize EasyOCR
print('\nInitializing EasyOCR...')
reader = easyocr.Reader(['ur', 'en'], gpu=False)

# Test different preprocessing methods
print('\n' + '='*70)
print('TESTING DIFFERENT PREPROCESSING METHODS ON HEADER')
print('='*70)

preprocessed = enhance_image(header)
for name, processed in preprocessed.items():
    cv2.imwrite(f'debug_header_{name}.png', processed)
    
    # Upscale for better OCR
    scale = 3
    upscaled = cv2.resize(processed, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
    
    results = reader.readtext(upscaled, paragraph=True, detail=0)
    combined = ' '.join(results)
    
    # Check for any known thana names
    known_thanas = ["اقبال ٹاؤن", "ماڈل ٹاؤن", "گلبرگ", "جوہر ٹاؤن", "شفیق آباد", "شالیمار",
                   "Iqbal Town", "Model Town", "Gulberg", "Johar Town", "Shafiqabad", "Shalimar"]
    
    found_thanas = [t for t in known_thanas if t.lower() in combined.lower()]
    
    print(f'\n[{name}]')
    print(f'  Text: {combined[:100]}...' if len(combined) > 100 else f'  Text: {combined}')
    if found_thanas:
        print(f'  ✅ FOUND: {found_thanas}')

# Also check Row 4
print('\n' + '='*70)
print('TESTING ROW 4 (LOCATION ROW)')
print('='*70)

preprocessed_row4 = enhance_image(row4)
for name, processed in preprocessed_row4.items():
    cv2.imwrite(f'debug_row4_{name}.png', processed)
    
    # Upscale
    scale = 2
    upscaled = cv2.resize(processed, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
    
    results = reader.readtext(upscaled, paragraph=True, detail=0)
    combined = ' '.join(results)
    
    known_thanas = ["اقبال ٹاؤن", "ماڈل ٹاؤن", "گلبرگ", "جوہر ٹاؤن", "شفیق آباد", "شالیمار",
                   "Iqbal Town", "Model Town", "Gulberg", "Johar Town", "Shafiqabad", "Shalimar"]
    
    found_thanas = [t for t in known_thanas if t.lower() in combined.lower()]
    
    print(f'\n[{name}]')
    print(f'  Text: {combined[:150]}...' if len(combined) > 150 else f'  Text: {combined}')
    if found_thanas:
        print(f'  ✅ FOUND: {found_thanas}')

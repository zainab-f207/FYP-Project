"""
Advanced preprocessing for degraded thana text extraction
"""
import cv2
import numpy as np
import easyocr

# Load FIR image
img_path = r'D:\FYP\Project\CrimeVision\OCRModel\app\data\raw\FIR_001.png'
img = cv2.imread(img_path)

h, w = img.shape[:2]
print(f"Image size: {w}x{h}")

# Extract the thana region (Row 3, x=75%-92%)
y1, y2 = int(h * 0.10), int(h * 0.16)
x1, x2 = int(w * 0.75), int(w * 0.92)
thana_region = img[y1:y2, x1:x2]

print(f"Thana region: {thana_region.shape[1]}x{thana_region.shape[0]}px")
cv2.imwrite("adv_01_original.png", thana_region)

# Initialize EasyOCR
print("\nInitializing EasyOCR...")
reader = easyocr.Reader(['ur', 'en'], gpu=False)

def try_ocr(img_version, name):
    """Run OCR and return best text"""
    try:
        results = reader.readtext(img_version, paragraph=False)
        if results:
            # Filter and sort by confidence
            filtered = [(t, c) for _, t, c in results if len(t.strip()) >= 2]
            if filtered:
                filtered.sort(key=lambda x: x[1], reverse=True)
                return filtered[0]
    except:
        pass
    return (None, 0)

print("\n" + "=" * 70)
print("TRYING ADVANCED PREPROCESSING TECHNIQUES")
print("=" * 70)

# Convert to grayscale
gray = cv2.cvtColor(thana_region, cv2.COLOR_BGR2GRAY)

# =====================================================
# 1. Super Resolution via Upscaling
# =====================================================
print("\n1. HIGH UPSCALING (4x)")
upscaled_4x = cv2.resize(thana_region, None, fx=4, fy=4, interpolation=cv2.INTER_LANCZOS4)
cv2.imwrite("adv_02_upscaled4x.png", upscaled_4x)
text, conf = try_ocr(upscaled_4x, "upscaled4x")
print(f"   Result: '{text}' (conf={conf:.2f})")

# =====================================================
# 2. Contrast Enhancement (CLAHE with different params)
# =====================================================
print("\n2. CLAHE ENHANCEMENT (various params)")
for clip_limit in [2.0, 3.0, 4.0]:
    clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=(8, 8))
    gray_up = cv2.cvtColor(upscaled_4x, cv2.COLOR_BGR2GRAY)
    enhanced = clahe.apply(gray_up)
    cv2.imwrite(f"adv_03_clahe_{clip_limit}.png", enhanced)
    text, conf = try_ocr(enhanced, f"clahe_{clip_limit}")
    print(f"   clip={clip_limit}: '{text}' (conf={conf:.2f})")

# =====================================================
# 3. Morphological operations to clean text
# =====================================================
print("\n3. MORPHOLOGICAL CLEANING")

# Binary threshold first
gray_up = cv2.cvtColor(upscaled_4x, cv2.COLOR_BGR2GRAY)
_, binary = cv2.threshold(gray_up, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
cv2.imwrite("adv_04_binary.png", binary)

# Opening (removes noise)
kernel_small = np.ones((2, 2), np.uint8)
opened = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel_small)
cv2.imwrite("adv_05_opened.png", opened)
text, conf = try_ocr(opened, "opened")
print(f"   Opening: '{text}' (conf={conf:.2f})")

# Closing (fills gaps)
closed = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel_small)
cv2.imwrite("adv_06_closed.png", closed)
text, conf = try_ocr(closed, "closed")
print(f"   Closing: '{text}' (conf={conf:.2f})")

# =====================================================
# 4. Denoising
# =====================================================
print("\n4. DENOISING")
denoised = cv2.fastNlMeansDenoising(gray_up, None, h=10, templateWindowSize=7, searchWindowSize=21)
cv2.imwrite("adv_07_denoised.png", denoised)
text, conf = try_ocr(denoised, "denoised")
print(f"   Denoised: '{text}' (conf={conf:.2f})")

# =====================================================
# 5. Sharpening
# =====================================================
print("\n5. SHARPENING")
kernel_sharp = np.array([[-1,-1,-1], [-1,9,-1], [-1,-1,-1]])
sharpened = cv2.filter2D(gray_up, -1, kernel_sharp)
cv2.imwrite("adv_08_sharpened.png", sharpened)
text, conf = try_ocr(sharpened, "sharpened")
print(f"   Sharpened: '{text}' (conf={conf:.2f})")

# =====================================================
# 6. Unsharp Masking (better sharpening)
# =====================================================
print("\n6. UNSHARP MASKING")
blurred = cv2.GaussianBlur(gray_up, (0, 0), 3)
unsharp = cv2.addWeighted(gray_up, 1.5, blurred, -0.5, 0)
cv2.imwrite("adv_09_unsharp.png", unsharp)
text, conf = try_ocr(unsharp, "unsharp")
print(f"   Unsharp: '{text}' (conf={conf:.2f})")

# =====================================================
# 7. Combined: Denoise + CLAHE + Binary
# =====================================================
print("\n7. COMBINED PIPELINE")
step1 = cv2.fastNlMeansDenoising(gray_up, None, h=8)
clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))
step2 = clahe.apply(step1)
_, step3 = cv2.threshold(step2, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
cv2.imwrite("adv_10_combined.png", step3)
text, conf = try_ocr(step3, "combined")
print(f"   Combined: '{text}' (conf={conf:.2f})")

# =====================================================
# 8. Bilateral Filter (edge-preserving smoothing)
# =====================================================
print("\n8. BILATERAL FILTER")
bilateral = cv2.bilateralFilter(upscaled_4x, 9, 75, 75)
cv2.imwrite("adv_11_bilateral.png", bilateral)
text, conf = try_ocr(bilateral, "bilateral")
print(f"   Bilateral: '{text}' (conf={conf:.2f})")

# Also try on grayscale bilateral
gray_bilateral = cv2.cvtColor(bilateral, cv2.COLOR_BGR2GRAY)
clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
bilateral_enhanced = clahe.apply(gray_bilateral)
cv2.imwrite("adv_12_bilateral_clahe.png", bilateral_enhanced)
text, conf = try_ocr(bilateral_enhanced, "bilateral_clahe")
print(f"   Bilateral+CLAHE: '{text}' (conf={conf:.2f})")

# =====================================================
# 9. Invert (in case text is light on dark)
# =====================================================
print("\n9. INVERTED VERSIONS")
_, binary = cv2.threshold(gray_up, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
inverted = cv2.bitwise_not(binary)
cv2.imwrite("adv_13_inverted.png", inverted)
text, conf = try_ocr(inverted, "inverted")
print(f"   Inverted: '{text}' (conf={conf:.2f})")

# =====================================================
# 10. Adaptive threshold (better for varying lighting)
# =====================================================
print("\n10. ADAPTIVE THRESHOLD")
adaptive = cv2.adaptiveThreshold(gray_up, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 15, 5)
cv2.imwrite("adv_14_adaptive.png", adaptive)
text, conf = try_ocr(adaptive, "adaptive")
print(f"   Adaptive: '{text}' (conf={conf:.2f})")

print("\n" + "=" * 70)
print("Check adv_*.png files for visual inspection")
print("=" * 70)

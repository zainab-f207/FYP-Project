"""Extract thana - THIN the thick/congested text"""
import cv2
import numpy as np
import pytesseract
import easyocr

# Use FIR_001 as reference
img_path = r'D:\FYP\Project\CrimeVision\OCRModel\app\data\raw\FIR_001.png'
img = cv2.imread(img_path)

h, w = img.shape[:2]
print(f"Image size: {w}x{h}")

# Row 3 is at y=12-15%
y1, y2 = int(h * 0.12), int(h * 0.15)
row3 = img[y1:y2, 0:w]

# Extract thana region (70%-92% width)
x1, x2 = int(w * 0.70), int(w * 0.92)
thana_region = row3[:, x1:x2]
print(f"Thana region size: {thana_region.shape[1]}x{thana_region.shape[0]}")

# Convert to grayscale
gray = cv2.cvtColor(thana_region, cv2.COLOR_BGR2GRAY)

print("="*70)
print("THINNING THICK/CONGESTED TEXT")
print("="*70)

# Step 1: Upscale 6x for better detail
upscaled = cv2.resize(gray, None, fx=6, fy=6, interpolation=cv2.INTER_LANCZOS4)
cv2.imwrite("debug_1_upscaled.png", upscaled)

# Step 2: Light denoise (preserve edges)
denoised = cv2.fastNlMeansDenoising(upscaled, None, h=5, templateWindowSize=5, searchWindowSize=15)
cv2.imwrite("debug_2_denoised.png", denoised)

# Step 3: Binary threshold (Otsu)
_, binary = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
cv2.imwrite("debug_3_binary.png", binary)

# Step 4: ERODE to thin the text (text is black, so erosion makes it thinner)
# Try different kernel sizes
print("\nTrying different erosion levels to thin text:")

for erode_size in [1, 2, 3, 4, 5]:
    kernel = np.ones((erode_size, erode_size), np.uint8)
    eroded = cv2.erode(binary, kernel, iterations=1)
    cv2.imwrite(f"debug_4_eroded_{erode_size}px.png", eroded)

    # OCR on eroded
    text = pytesseract.image_to_string(eroded, lang='urd', config='--psm 6')
    text = text.strip().replace('\n', ' ')[:80]
    print(f"  Erode {erode_size}px: '{text}'")

# Step 5: Better thinning approach - use morphological gradient + thinning
print("\nCreating SOLID BLACK thinned text:")

# Method A: Morphological thinning using cv2.ximgproc if available
# First, let's try a simpler approach - find edges and make them bold

# Use Canny edge detection on the denoised image
edges = cv2.Canny(denoised, 50, 150)
cv2.imwrite("debug_5a_edges.png", edges)

# Dilate edges to make them visible
kernel_3 = np.ones((3, 3), np.uint8)
edges_dilated = cv2.dilate(edges, kernel_3, iterations=2)
# Invert so text is black on white
edges_black = cv2.bitwise_not(edges_dilated)
cv2.imwrite("debug_5a_edges_bold.png", edges_black)

text = pytesseract.image_to_string(edges_black, lang='urd', config='--psm 6')
print(f"  Canny edges+dilate: '{text.strip().replace(chr(10), ' ')[:80]}'")

# Method B: Use Laplacian for edge detection
laplacian = cv2.Laplacian(denoised, cv2.CV_64F)
laplacian = np.uint8(np.absolute(laplacian))
_, lap_binary = cv2.threshold(laplacian, 20, 255, cv2.THRESH_BINARY)
lap_dilated = cv2.dilate(lap_binary, kernel_3, iterations=2)
lap_black = cv2.bitwise_not(lap_dilated)
cv2.imwrite("debug_5b_laplacian.png", lap_black)

text = pytesseract.image_to_string(lap_black, lang='urd', config='--psm 6')
print(f"  Laplacian edges: '{text.strip().replace(chr(10), ' ')[:80]}'")

# Method C: Medium erosion on binary (best balance)
print("\nMedium erosion (thinned but readable):")
kernel_2 = np.ones((2, 2), np.uint8)
eroded_2 = cv2.erode(binary, kernel_2, iterations=1)
cv2.imwrite("debug_5c_eroded_medium.png", eroded_2)

text = pytesseract.image_to_string(eroded_2, lang='urd', config='--psm 6')
print(f"  Eroded 2x2: '{text.strip().replace(chr(10), ' ')[:80]}'")

# Method D: Try distance transform for better separation
print("\nDistance transform (separates touching characters):")
# Invert binary so text is white (foreground)
binary_inv = cv2.bitwise_not(binary)
dist = cv2.distanceTransform(binary_inv, cv2.DIST_L2, 5)
# Normalize and threshold
dist_norm = cv2.normalize(dist, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
_, dist_thresh = cv2.threshold(dist_norm, 0.3 * dist_norm.max(), 255, cv2.THRESH_BINARY)
# Dilate slightly to connect broken parts
dist_dilated = cv2.dilate(dist_thresh, kernel_3, iterations=1)
# Invert back (black text on white)
dist_black = cv2.bitwise_not(dist_dilated)
cv2.imwrite("debug_5d_distance.png", dist_black)

text = pytesseract.image_to_string(dist_black, lang='urd', config='--psm 6')
print(f"  Distance transform: '{text.strip().replace(chr(10), ' ')[:80]}'")

# Step 6: Try opening (erosion + dilation) - removes small noise while thinning
print("\nOpening (erosion + dilation) to clean up:")
for size in [2, 3]:
    kernel = np.ones((size, size), np.uint8)
    opened = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel)
    cv2.imwrite(f"debug_6_opened_{size}px.png", opened)

    text = pytesseract.image_to_string(opened, lang='urd', config='--psm 6')
    print(f"  Open {size}px: '{text.strip().replace(chr(10), ' ')[:80]}'")

# Try EasyOCR on best candidates
print("\n" + "="*70)
print("UPSCALING + OCR (helps with small/degraded text)")
print("="*70)

# Upscale 2x and 3x
for scale in [2, 3]:
    upscaled = cv2.resize(binary, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
    cv2.imwrite(f"debug_6_upscaled_{scale}x.png", upscaled)

    text = pytesseract.image_to_string(upscaled, lang='urd', config='--psm 6')
    print(f"  Upscaled {scale}x: '{text.strip().replace(chr(10), ' ')[:80]}'")

    # Also try upscaled + eroded
    kernel = np.ones((2, 2), np.uint8)
    upscaled_eroded = cv2.erode(upscaled, kernel, iterations=1)
    cv2.imwrite(f"debug_6_upscaled_{scale}x_eroded.png", upscaled_eroded)

    text = pytesseract.image_to_string(upscaled_eroded, lang='urd', config='--psm 6')
    print(f"  Upscaled {scale}x + eroded: '{text.strip().replace(chr(10), ' ')[:80]}'")

# Try on distance transform (properly inverted - black text on white)
print("\nDistance transform versions:")
dist_upscaled = cv2.resize(dist_black, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
cv2.imwrite("debug_6_distance_2x.png", dist_upscaled)
text = pytesseract.image_to_string(dist_upscaled, lang='urd', config='--psm 6')
print(f"  Distance 2x: '{text.strip().replace(chr(10), ' ')[:80]}'")

print("="*70)
print("EASYOCR ON UPSCALED IMAGES")
print("="*70)

reader = easyocr.Reader(['ur', 'en'], gpu=False)

# Best: upscaled 2x binary
upscaled_2x = cv2.resize(binary, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)

for name, img_data in [("Binary", binary), ("Upscaled 2x", upscaled_2x)]:
    results = reader.readtext(img_data)
    print(f"\n  {name}:")
    for bbox, text, conf in results:
        print(f"    [{conf:.2f}] '{text}'")


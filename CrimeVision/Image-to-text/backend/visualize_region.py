"""Visualize the sections region to help narrow it down"""
import cv2
import sys

fir_name = sys.argv[1] if len(sys.argv) > 1 else 'FIR_001'
img_path = f'D:/FYP/Project/CrimeVision/OCRModel/app/data/raw/{fir_name}.png'

img = cv2.imread(img_path)
if img is None:
    print(f"ERROR: Cannot load {img_path}")
    sys.exit(1)

h, w = img.shape[:2]
print(f'{fir_name} size: {w}x{h}')

# Current region
TOP, BOTTOM = 0.23, 0.50
LEFT, RIGHT = 0.42, 0.74

y1, y2 = int(h * TOP), int(h * BOTTOM)
x1, x2 = int(w * LEFT), int(w * RIGHT)

# Draw rectangle on image
img_marked = img.copy()
cv2.rectangle(img_marked, (x1, y1), (x2, y2), (0, 0, 255), 10)

# Add text
cv2.putText(img_marked, f"Region: {LEFT:.2f}-{RIGHT:.2f} x {TOP:.2f}-{BOTTOM:.2f}", 
            (x1, y1-20), cv2.FONT_HERSHEY_SIMPLEX, 2, (0, 0, 255), 3)

# Save marked full image (scaled down)
scale = 0.3
small = cv2.resize(img_marked, None, fx=scale, fy=scale)
cv2.imwrite(f'region_marked_{fir_name}.png', small)
print(f'Saved: region_marked_{fir_name}.png (full image with region marked)')

# Save just the region
region = img[y1:y2, x1:x2]
cv2.imwrite(f'region_crop_{fir_name}.png', region)
print(f'Saved: region_crop_{fir_name}.png (just the cropped region)')
print(f'\nRegion coordinates: Y[{y1}:{y2}] X[{x1}:{x2}]')
print(f'Region size: {x2-x1}x{y2-y1}')
print(f'\nPlease open region_crop_{fir_name}.png and tell me:')
print('1. Where are the REAL section numbers located? (left/center/right)')
print('2. What other numbers/text do you see that are NOT sections?')


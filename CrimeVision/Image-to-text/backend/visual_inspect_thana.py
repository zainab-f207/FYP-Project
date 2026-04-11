"""Visual inspection of what's in the thana cell"""
import cv2
import numpy as np

# Load FIR image
img_path = r'D:\FYP\Project\CrimeVision\OCRModel\app\data\raw\FIR_001.png'
img = cv2.imread(img_path)

h, w = img.shape[:2]
print(f"Image size: {w}x{h}")

# Let's create a visual map of the header area
# Draw grid lines to understand the structure

header = img[0:int(h * 0.25), 0:w].copy()

# Draw vertical grid lines at 10% intervals
for i in range(11):
    x = int(w * i / 10)
    cv2.line(header, (x, 0), (x, header.shape[0]), (0, 255, 0), 2)
    cv2.putText(header, f"{i*10}%", (x+5, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)

# Draw horizontal grid lines at 5% intervals (relative to header which is 25% of image)
for i in range(11):
    y = int(header.shape[0] * i / 10)
    actual_pct = int(25 * i / 10)  # Convert to image percentage
    cv2.line(header, (0, y), (w, y), (255, 0, 0), 2)
    cv2.putText(header, f"y={actual_pct}%", (10, y-5), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 0), 2)

cv2.imwrite("fir_header_grid.png", header)
print("Saved: fir_header_grid.png")

# Extract the focused thana cell region
# Currently: y=10%-16%, x=75%-92%
y1, y2 = int(h * 0.10), int(h * 0.16)
x1, x2 = int(w * 0.75), int(w * 0.92)

# Draw rectangle on header showing thana cell
header_marked = img[0:int(h * 0.25), 0:w].copy()
cv2.rectangle(header_marked, (x1, y1), (x2, y2), (0, 0, 255), 4)
cv2.putText(header_marked, "THANA CELL", (x1, y1-10), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
cv2.imwrite("fir_header_thana_marked.png", header_marked)
print("Saved: fir_header_thana_marked.png")

# Extract thana cell
thana_cell = img[y1:y2, x1:x2]
cv2.imwrite("thana_cell_current.png", thana_cell)
print(f"Thana cell: {thana_cell.shape[1]}x{thana_cell.shape[0]}px")

# Let's also try different region boundaries
print("\nTrying different region boundaries:")

# Try multiple x ranges at y=10%-16%
for x_start, x_end, name in [
    (0.65, 0.85, "center-right"),
    (0.70, 0.90, "right"),
    (0.75, 0.95, "far-right"),
    (0.80, 0.92, "thana-value-narrow"),
]:
    x1 = int(w * x_start)
    x2 = int(w * x_end)
    cell = img[y1:y2, x1:x2]
    cv2.imwrite(f"thana_cell_{name}.png", cell)
    print(f"  {name}: x={x_start*100:.0f}%-{x_end*100:.0f}% -> {cell.shape[1]}x{cell.shape[0]}px")

# Try different y ranges at x=75%-92%
print("\nTrying different y ranges:")
x1, x2 = int(w * 0.75), int(w * 0.92)
for y_start, y_end, name in [
    (0.08, 0.14, "row2-3"),
    (0.10, 0.16, "row3"),
    (0.12, 0.18, "row3-4"),
    (0.14, 0.20, "row4"),
]:
    y1 = int(h * y_start)
    y2 = int(h * y_end)
    cell = img[y1:y2, x1:x2]
    cv2.imwrite(f"thana_cell_y{name}.png", cell)
    print(f"  {name}: y={y_start*100:.0f}%-{y_end*100:.0f}% -> {cell.shape[1]}x{cell.shape[0]}px")

print("\nDone! Check the generated PNG files to see where thana text actually is.")

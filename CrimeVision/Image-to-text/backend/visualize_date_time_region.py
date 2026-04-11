"""
Visualize the CURRENT date region vs. PROPOSED date+time region.
Run this script to check if the expanded region correctly captures
the crime time (with AM/PM) on FIR documents.

Usage:
    python visualize_date_time_region.py
    python visualize_date_time_region.py FIR_001 FIR_005 FIR_010

Output PNGs:
    date_time_region_<FIR>.png  - Full-image view with both regions drawn
    date_time_crop_<FIR>.png    - Cropped view of the PROPOSED region only
"""

import cv2
import numpy as np
import sys
import os

# ─────────────────────────────────────────────────────────────────────────────
# CURRENT date region (left side of date row)
# ─────────────────────────────────────────────────────────────────────────────
CURRENT_DATE_TOP    = 0.10
CURRENT_DATE_BOTTOM = 0.16
CURRENT_DATE_LEFT   = 0.05
CURRENT_DATE_RIGHT  = 0.45

# ─────────────────────────────────────────────────────────────────────────────
# PROPOSED date+time region
#   → Extend RIGHT boundary from 0.45 → 0.72 to capture the time field
#     (time is written to the right of the date in Punjab Police FIRs)
#   → Extend BOTTOM slightly (0.16 → 0.19) in case time wraps to second line
# ─────────────────────────────────────────────────────────────────────────────
PROPOSED_DATE_TIME_TOP    = 0.10
PROPOSED_DATE_TIME_BOTTOM = 0.15   # adjusted bottom
PROPOSED_DATE_TIME_LEFT   = 0.02   # expanded 3% left
PROPOSED_DATE_TIME_RIGHT  = 0.57   # shrunk 15% from original right

# Image directory
FIR_DIR = r"D:\FYP\FIR_Images\output"

# Default FIRs to visualise (cover early, mid and late images)
DEFAULT_FIRS = ["FIR_001", "FIR_002", "FIR_005", "FIR_010", "FIR_015"]


def draw_region(img: np.ndarray, top: float, bottom: float,
                left: float, right: float,
                color: tuple, label: str, thickness: int = 4) -> np.ndarray:
    """Draw a labelled rectangle on the image (percentage coordinates)."""
    h, w = img.shape[:2]
    y1, y2 = int(h * top), int(h * bottom)
    x1, x2 = int(w * left), int(w * right)
    cv2.rectangle(img, (x1, y1), (x2, y2), color, thickness)
    # Label background
    (tw, th), baseline = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 1.0, 2)
    cv2.rectangle(img, (x1, y1 - th - baseline - 6), (x1 + tw + 4, y1), color, -1)
    cv2.putText(img, label, (x1 + 2, y1 - baseline - 4),
                cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2)
    return img


def process_fir(fir_name: str) -> None:
    img_path = os.path.join(FIR_DIR, f"{fir_name}.png")
    if not os.path.exists(img_path):
        print(f"[SKIP] {img_path} not found.")
        return

    img = cv2.imread(img_path)
    if img is None:
        print(f"[ERROR] Could not read {img_path}")
        return

    h, w = img.shape[:2]
    print(f"\n{'='*60}")
    print(f"  {fir_name}  —  {w}×{h} px")
    print(f"{'='*60}")

    # ── Full-image view with BOTH regions ────────────────────────────────
    vis = img.copy()

    # Draw PROPOSED region first (blue, thicker) so current overlaps on top
    draw_region(vis,
                PROPOSED_DATE_TIME_TOP, PROPOSED_DATE_TIME_BOTTOM,
                PROPOSED_DATE_TIME_LEFT, PROPOSED_DATE_TIME_RIGHT,
                color=(255, 140, 0),   # Orange-blue in BGR → vivid orange
                label="PROPOSED: Date+Time",
                thickness=5)

    # Draw CURRENT region (red)
    draw_region(vis,
                CURRENT_DATE_TOP, CURRENT_DATE_BOTTOM,
                CURRENT_DATE_LEFT, CURRENT_DATE_RIGHT,
                color=(0, 0, 220),     # Red
                label="CURRENT: Date only",
                thickness=3)

    # Legend at bottom
    legend_y = h - 20
    cv2.rectangle(vis, (20, legend_y - 50), (560, legend_y + 10), (50, 50, 50), -1)
    cv2.putText(vis, "RED = current date region",
                (30, legend_y - 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 220), 2)
    cv2.putText(vis, "ORANGE = proposed date+time region",
                (30, legend_y - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 140, 255), 2)

    # Scale down for readability (3 tall → show at 40%)
    scale = 0.40
    small = cv2.resize(vis, None, fx=scale, fy=scale)
    full_out = f"date_time_region_{fir_name}.png"
    cv2.imwrite(full_out, small)
    print(f"  [SAVED] Full view  → {full_out}")

    # ── Cropped view of PROPOSED region only ─────────────────────────────
    y1 = int(h * PROPOSED_DATE_TIME_TOP)
    y2 = int(h * PROPOSED_DATE_TIME_BOTTOM)
    x1 = int(w * PROPOSED_DATE_TIME_LEFT)
    x2 = int(w * PROPOSED_DATE_TIME_RIGHT)

    crop = img[y1:y2, x1:x2]
    # Upscale crop 3× for easier reading
    crop_big = cv2.resize(crop, None, fx=3.0, fy=3.0, interpolation=cv2.INTER_CUBIC)
    crop_out = f"date_time_crop_{fir_name}.png"
    cv2.imwrite(crop_out, crop_big)
    print(f"  [SAVED] Crop view  → {crop_out}")

    # Pixel positions for reference
    print(f"\n  Pixel coordinates of PROPOSED region:")
    print(f"    Y: {y1} → {y2}  ({y2-y1} px tall)")
    print(f"    X: {x1} → {x2}  ({x2-x1} px wide)")
    print(f"\n  Pixel coordinates of CURRENT date region:")
    print(f"    Y: {int(h*CURRENT_DATE_TOP)} → {int(h*CURRENT_DATE_BOTTOM)}  "
          f"({int(h*(CURRENT_DATE_BOTTOM-CURRENT_DATE_TOP))} px tall)")
    print(f"    X: {int(w*CURRENT_DATE_LEFT)} → {int(w*CURRENT_DATE_RIGHT)}  "
          f"({int(w*(CURRENT_DATE_RIGHT-CURRENT_DATE_LEFT))} px wide)")


def main():
    firs = sys.argv[1:] if len(sys.argv) > 1 else DEFAULT_FIRS

    out_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(out_dir)   # Save output images in backend/ folder
    print(f"Output directory: {out_dir}")

    for fir in firs:
        # Accept with or without extension
        name = fir.replace(".png", "")
        process_fir(name)

    print(f"\n{'='*60}")
    print("DONE.")
    print("\nFiles written to:")
    print(f"  {out_dir}")
    print("\nOpen the 'date_time_crop_*.png' files to check whether")
    print("the PROPOSED region captures the time with AM/PM correctly.")
    print("\nIf the crop looks good, reply 'region looks good' and the")
    print("extraction code will be updated to include time in the output.")


if __name__ == "__main__":
    main()

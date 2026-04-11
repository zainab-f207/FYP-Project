import os
import io
import cv2
import numpy as np
import pytesseract
from paddleocr import PaddleOCR
from PIL import Image
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import Optional, List, Any, cast
import logging
import re
import asyncio
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
import tempfile
import shutil
import glob
import time

# Import specialized FIR OCR
from fir_specialized_ocr import FIRExtractor

# Import fuzzy correction for area field
from urdu_location_dictionary import correct_location_text, _normalize_text

# Configure logging first
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Try to import EasyOCR (optional, better for Urdu)
try:
    import easyocr
    EASYOCR_AVAILABLE = True
    logger.info("✅ EasyOCR available - will use for better Urdu recognition")
except ImportError:
    EASYOCR_AVAILABLE = False
    logger.warning("⚠️ EasyOCR not available - install with: pip install easyocr")

# Cleanup function for storage management
def cleanup_temp_files():
    """Clean up temporary files to prevent storage issues"""
    try:
        # Clean up debug images older than 1 hour
        debug_files = glob.glob('debug_*.png')
        for f in debug_files:
            try:
                if os.path.exists(f) and os.path.getmtime(f) < (time.time() - 3600):
                    os.remove(f)
            except:
                pass

        # Clean up temp directory
        temp_dir = tempfile.gettempdir()
        tesseract_temp = os.path.join(temp_dir, 'tesseract*')
        for f in glob.glob(tesseract_temp):
            try:
                if os.path.isfile(f):
                    os.remove(f)
                elif os.path.isdir(f):
                    shutil.rmtree(f, ignore_errors=True)
            except:
                pass
    except Exception as e:
        logger.warning(f"Cleanup failed: {e}")

# Initialize FastAPI app
app = FastAPI(title="Urdu OCR API", version="1.0.0")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Log all incoming requests and responses for easier debugging
@app.middleware("http")
async def log_requests(request, call_next):
    try:
        origin = request.headers.get("origin")
        content_type = request.headers.get("content-type")
        content_length = request.headers.get("content-length")
        logger.info(
            f"➡️ Incoming {request.method} {request.url.path} | Origin: {origin} | "
            f"Content-Type: {content_type} | Content-Length: {content_length}"
        )
        response = await call_next(request)
        logger.info(
            f"⬅️ Response {request.method} {request.url.path} | Status: {response.status_code}"
        )
        return response
    except Exception as e:
        logger.error(f"Request logging failed: {e}")
        return await call_next(request)

class ImageProcessor:
    """Handle image preprocessing for better OCR accuracy"""

    @staticmethod
    def resize_if_large(image: np.ndarray, max_dimension: int = 3000) -> np.ndarray:
        """Resize image if it exceeds max dimension to save memory
        Increased to 3000 for maximum OCR accuracy on small text"""
        height, width = image.shape[:2]
        if max(height, width) > max_dimension:
            scale = max_dimension / max(height, width)
            new_width = int(width * scale)
            new_height = int(height * scale)
            # Use INTER_LANCZOS4 for better quality when downscaling
            return cv2.resize(image, (new_width, new_height), interpolation=cv2.INTER_LANCZOS4)
        return image

    @staticmethod
    def enhance_image_quality(image: np.ndarray) -> np.ndarray:
        """
        Enhance image quality for better OCR accuracy - OPTIMIZED for small text
        This is applied AFTER upscaling for maximum clarity
        """
        # Keep original color for better OCR
        # EasyOCR works better with color images

        # Apply gentle denoising to reduce noise while preserving details
        if len(image.shape) == 3:
            # For color images, denoise each channel
            # Reduced h from 5 to 3 for less aggressive denoising (preserve text edges)
            denoised = cv2.fastNlMeansDenoisingColored(image, None, h=3, hColor=3,
                                                        templateWindowSize=7, searchWindowSize=21)
        else:
            # For grayscale
            denoised = cv2.fastNlMeansDenoising(image, None, h=3, templateWindowSize=7, searchWindowSize=21)

        # Increase sharpness MORE to make small text clearer
        kernel = np.array([[-1,-1,-1],
                          [-1, 9,-1],
                          [-1,-1,-1]])
        sharpened = cv2.filter2D(denoised, -1, kernel * 0.5)  # Increased from 0.3 to 0.5

        # Increase contrast MORE using CLAHE for small text
        if len(sharpened.shape) == 3:
            # Convert to LAB color space for better contrast enhancement
            lab = cv2.cvtColor(sharpened, cv2.COLOR_BGR2LAB)
            l, a, b = cv2.split(lab)

            # Apply CLAHE to L channel with higher clip limit for more contrast
            clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8,8))  # Increased from 2.0 to 3.0
            l = clahe.apply(l)

            # Merge back
            enhanced = cv2.merge([l, a, b])
            enhanced = cv2.cvtColor(enhanced, cv2.COLOR_LAB2BGR)
        else:
            # For grayscale, apply CLAHE directly
            clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8,8))
            enhanced = clahe.apply(sharpened)

        return enhanced

    @staticmethod
    def remove_table_lines(image: np.ndarray) -> np.ndarray:
        """Remove horizontal and vertical lines from the image to improve OCR - gentle approach"""
        # Convert to gray if needed
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image

        # Thresholding
        thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]

        # Remove horizontal lines - use longer kernel to only remove table borders, not text
        horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (60, 1))
        remove_horizontal = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, horizontal_kernel, iterations=1)
        cnts = cv2.findContours(remove_horizontal, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        cnts = cnts[0] if len(cnts) == 2 else cnts[1]
        for c in cnts:
            cv2.drawContours(image, [c], -1, (255, 255, 255), 3)  # Thinner removal

        # Remove vertical lines - use longer kernel to only remove table borders
        vertical_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 60))
        remove_vertical = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, vertical_kernel, iterations=1)
        cnts = cv2.findContours(remove_vertical, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        cnts = cnts[0] if len(cnts) == 2 else cnts[1]
        for c in cnts:
            cv2.drawContours(image, [c], -1, (255, 255, 255), 3)  # Thinner removal

        return image

    @staticmethod
    def mask_qr_codes(image: np.ndarray) -> np.ndarray:
        """Enhanced QR code detection and masking"""
        try:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image

            # Use QRCodeDetector for better detection
            qr_detector = cv2.QRCodeDetector()
            retval, decoded_info, points, straight_qrcode = qr_detector.detectAndDecodeMulti(gray)

            if retval and points is not None:
                for point_set in points:
                    if point_set is not None:
                        # Create mask for QR code area
                        pts = np.array(point_set, dtype=np.int32)
                        cv2.fillPoly(image, [pts], (255, 255, 255))  # Fill with white

            # Fallback: Detect square-like contours (QR codes are square)
            contours, _ = cv2.findContours(gray, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            for contour in contours:
                area = cv2.contourArea(contour)
                if 1000 < area < 50000:  # QR code size range
                    # Check if contour is roughly square
                    peri = cv2.arcLength(contour, True)
                    approx = cv2.approxPolyDP(contour, 0.02 * peri, True)
                    if len(approx) == 4:
                        x, y, w, h = cv2.boundingRect(contour)
                        aspect_ratio = w / float(h)
                        if 0.8 <= aspect_ratio <= 1.2:  # Square-like
                            cv2.rectangle(image, (x, y), (x + w, y + h), (255, 255, 255), -1)

            return image
        except Exception as e:
            logger.warning(f"QR masking failed: {e}")
            return image

    @staticmethod
    def get_header_crop(image: np.ndarray) -> np.ndarray:
        """Extract ONLY the table portion (upper part) - stops before narrative text"""
        height, width = image.shape[:2]
        # INCREASED: Crop top 65% to capture full table including all sections
        # The table can extend further down in some FIR documents
        header_height = int(height * 0.65)
        return image[0:header_height, 0:width]

    @staticmethod
    def get_header_region(image: np.ndarray) -> np.ndarray:
        """
        Extract header region above the table for Thana name
        TOP = 8%, BOTTOM = 22% (the area below QR codes, above table)
        """
        height, width = image.shape[:2]
        start_y = int(height * 0.08)  # Skip QR codes
        end_y = int(height * 0.22)    # Stop at table start
        start_x = int(width * 0.04)   # Left margin
        end_x = int(width * 0.96)     # Right margin

        logger.info(f"FIR header region: Y[{start_y}:{end_y}] X[{start_x}:{end_x}]")
        return image[start_y:end_y, start_x:end_x]

    @staticmethod
    def get_table_region(image: np.ndarray) -> np.ndarray:
        """
        FIXED CROP REGION for Punjab Police FIR (resolution independent)
        TOP = 22%, BOTTOM = 68%, LEFT = 4%, RIGHT = 96%
        This extracts: Date, Sections table only
        """
        height, width = image.shape[:2]

        # Fixed percentage-based crop (identical for all FIR images)
        start_y = int(height * 0.22)  # Skip QR codes and heading
        end_y = int(height * 0.68)    # Stop before narrative paragraph
        start_x = int(width * 0.04)   # Small left margin
        end_x = int(width * 0.96)     # Small right margin

        logger.info(f"FIR table region: Y[{start_y}:{end_y}] X[{start_x}:{end_x}] (W:{end_x-start_x} H:{end_y-start_y})")
        return image[start_y:end_y, start_x:end_x]

    @staticmethod
    def extract_date_cell(image: np.ndarray) -> np.ndarray:
        """Extract the first row cell containing date/time info with enhanced preprocessing"""
        height, width = image.shape[:2]
        # Date is in first row of table (approximately top 15-20% of table region)
        # Left side of the image (first 50%)
        cell_start_y = int(height * 0.0)
        cell_end_y = int(height * 0.20)
        cell_start_x = 0
        cell_end_x = int(width * 0.50)

        date_cell = image[cell_start_y:cell_end_y, cell_start_x:cell_end_x]
        logger.info(f"Extracted date cell: {date_cell.shape}")
        return date_cell

    @staticmethod
    def enhance_for_date_extraction(image: np.ndarray) -> np.ndarray:
        """
        Specialized preprocessing for date/number extraction
        Optimized for digits and English characters
        """
        # Convert to grayscale
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image

        # EXTREME upscaling for small date text
        height, width = gray.shape[:2]
        target_width = 5000  # Even higher for dates
        if width < target_width:
            scale = target_width / width
            gray = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_LANCZOS4)
            logger.info(f"📅 Date cell upscaled {scale:.1f}x to {gray.shape[1]}x{gray.shape[0]}")

        # Remove noise
        gray = cv2.fastNlMeansDenoising(gray, None, h=15, templateWindowSize=7, searchWindowSize=21)

        # Extreme contrast for digits
        clahe = cv2.createCLAHE(clipLimit=6.0, tileGridSize=(4, 4))
        enhanced = clahe.apply(gray)

        # Binarization with Otsu's method (best for digits)
        _, binary = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

        # Morphological operations to clean up digits
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
        cleaned = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)

        logger.info("📅 Date preprocessing: 5000px + denoise + CLAHE + Otsu + morph")
        return cleaned

    @staticmethod
    def enhance_for_header(image: np.ndarray) -> np.ndarray:
        """
        SPECIALIZED preprocessing for header region (thana extraction)
        Focus: Clean Urdu text extraction, remove noise, maximize readability
        """
        # Convert to grayscale
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image

        # EXTREME upscaling to 5500px for header text clarity
        height, width = gray.shape[:2]
        target_width = 5500
        if width < target_width:
            scale = target_width / width
            gray = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_LANCZOS4)
            logger.info(f"🏛️ Header upscaled {scale:.1f}x to {gray.shape[1]}x{gray.shape[0]}")

        # VERY STRONG denoising to remove header artifacts
        gray = cv2.fastNlMeansDenoising(gray, None, h=15, templateWindowSize=7, searchWindowSize=21)

        # Normalize brightness
        # FIX: cv2.normalize() - pass src as dst for in-place operation
        cv2.normalize(gray, gray, 0, 255, cv2.NORM_MINMAX)

        # EXTREME CLAHE for maximum contrast
        clahe = cv2.createCLAHE(clipLimit=6.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)

        # Unsharp masking for ultra-crisp text
        gaussian = cv2.GaussianBlur(enhanced, (0, 0), 2.5)
        sharpened = cv2.addWeighted(enhanced, 2.5, gaussian, -1.5, 0)

        # Morphological opening to remove small noise
        kernel_small = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
        cleaned = cv2.morphologyEx(sharpened, cv2.MORPH_OPEN, kernel_small)

        # Final sharpening
        kernel = np.array([[-1,-1,-1], [-1, 11,-1], [-1,-1,-1]])
        final = cv2.filter2D(cleaned, -1, kernel * 0.4)

        # Ensure proper range
        final = np.clip(final, 0, 255).astype(np.uint8)

        logger.info("🏛️ Header preprocessing: EXTREME (5500px + denoise h=15 + CLAHE 6.0 + unsharp + morph + sharpen)")
        return final

    # REMOVED: validate_section_group() - No validation in pure OCR system

    @staticmethod
    def extract_sections_cell(image: np.ndarray) -> List[np.ndarray]:
        """
        ADAPTIVE section cell extraction - tries multiple regions
        Returns list of candidate regions to try
        Different FIR formats have different table layouts
        """
        height, width = image.shape[:2]

        candidates = []

        # Strategy 1: Left-center region (common in many FIRs)
        candidates.append({
            'name': 'Left-center',
            'region': image[int(height*0.25):int(height*0.65), int(width*0.15):int(width*0.50)]
        })

        # Strategy 2: Center region (some FIRs have centered sections)
        candidates.append({
            'name': 'Center',
            'region': image[int(height*0.30):int(height*0.60), int(width*0.35):int(width*0.65)]
        })

        # Strategy 3: Right-center region (some FIRs have sections on right)
        candidates.append({
            'name': 'Right-center',
            'region': image[int(height*0.25):int(height*0.65), int(width*0.50):int(width*0.85)]
        })

        # Strategy 4: Full middle band (widest coverage)
        candidates.append({
            'name': 'Full-middle',
            'region': image[int(height*0.20):int(height*0.70), int(width*0.10):int(width*0.90)]
        })

        # Strategy 5: Row-3 left (FIR layout-specific: sections list is usually here)
        candidates.append({
            'name': 'Row3-left',
            'region': image[int(height*0.32):int(height*0.56), int(width*0.52):int(width*0.72)]
        })

        # Strategy 6: Row-3 wide (captures section list + suffix letters like A)
        candidates.append({
            'name': 'Row3-wide',
            'region': image[int(height*0.30):int(height*0.60), int(width*0.45):int(width*0.80)]
        })

        logger.info(f"� Prepared {len(candidates)} candidate regions for section extraction")
        return candidates

    @staticmethod
    def _normalize_digit_chars(text: str) -> str:
        """
        Replace common OCR letter-for-digit confusions inside tokens that already
        contain at least one real digit.  Only modifies mixed tokens so Urdu words
        are left untouched.
        e.g. '1O9' → '109', 'l09' → '109', '3O2' → '302'
        """
        _MAP = {
            'O': '0', 'o': '0', 'D': '0', 'Q': '0',
            'l': '1', 'I': '1', 'i': '1',
            'Z': '2', 'z': '2',
            'S': '5',
            'B': '8',
            'G': '6',
            'g': '9', 'q': '9',
        }
        parts = text.split()
        out = []
        for part in parts:
            if any(c.isdigit() for c in part):
                part = ''.join(_MAP.get(c, c) for c in part)
            out.append(part)
        return ' '.join(out)

    @staticmethod
    def _bbox_has_strikethrough(image: np.ndarray, bbox, margin: int = 2) -> bool:
        """
        Return True if a horizontal strikethrough / crossing line is present inside
        the EasyOCR bounding box region.

        Approach: threshold the cropped region (inverted binary) and check whether
        any row in the MIDDLE VERTICAL THIRD of the box has dark pixels covering
        ≥ 70 % of the box width — that is the signature of a horizontal pen stroke.
        """
        try:
            pts = np.array(bbox, dtype=int)
            x1 = int(pts[:, 0].min()) - margin
            y1 = int(pts[:, 1].min()) - margin
            x2 = int(pts[:, 0].max()) + margin
            y2 = int(pts[:, 1].max()) + margin
            ih, iw = image.shape[:2]
            x1, y1 = max(0, x1), max(0, y1)
            x2, y2 = min(iw, x2), min(ih, y2)
            if x2 <= x1 or y2 <= y1:
                return False
            crop = image[y1:y2, x1:x2]
            gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY) if len(crop.shape) == 3 else crop.copy()
            _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
            rh, rw = binary.shape
            mid_start = rh // 3
            mid_end = 2 * rh // 3
            for row in range(mid_start, mid_end):
                dark = int(np.sum(binary[row] > 127))
                if dark / max(rw, 1) >= 0.60:
                    return True

            # Catch diagonal crossing strokes as well.
            lines = cv2.HoughLinesP(
                binary,
                rho=1,
                theta=np.pi / 180,
                threshold=max(12, rw // 4),
                minLineLength=max(10, int(0.60 * rw)),
                maxLineGap=3,
            )
            if lines is not None:
                for line in lines:
                    x1, y1, x2, y2 = line[0]
                    length = float(np.hypot(x2 - x1, y2 - y1))
                    if length < 0.60 * rw:
                        continue
                    y_mid = (y1 + y2) / 2.0
                    if rh * 0.20 <= y_mid <= rh * 0.80:
                        return True
            return False
        except Exception:
            return False

    @staticmethod
    def extract_sections_visual(sections_cell_img: np.ndarray) -> List[str]:
        """
        PURE OCR section extraction - matches successful date extraction approach

        KEY INSIGHT: Date extraction WORKS because it uses RAW images.
        This function was failing because of heavy preprocessing that destroys digits.

        New approach:
        1. Try EasyOCR on RAW image first (like date extraction)
        2. Try gentle upscale if needed
        3. Tesseract as fallback with minimal preprocessing
        """
        try:
            logger.info("🔍 PURE section extraction (minimal preprocessing like date)...")

            h, w = sections_cell_img.shape[:2]
            logger.info(f"📋 Input image: {w}x{h}")

            all_sections = set()

            def _collect_sections_from_easyocr(results, source_img: np.ndarray) -> List[str]:
                tokens = []
                for bbox, text, conf in results:
                    if ImageProcessor._bbox_has_strikethrough(source_img, bbox):
                        logger.info(f"  ✗ Skipping crossed-out text: '{text}'")
                        continue
                    text_norm = ImageProcessor._normalize_digit_chars(text)
                    xc = float(sum(p[0] for p in bbox) / 4.0)
                    yc = float(sum(p[1] for p in bbox) / 4.0)
                    tokens.append((yc, xc, text_norm, conf))

                if not tokens:
                    return []

                # Group OCR tokens into text lines by y-center proximity.
                tokens.sort(key=lambda t: t[0])
                line_gap = max(10.0, h * 0.035)
                lines_grouped = []
                for tok in tokens:
                    if not lines_grouped or abs(tok[0] - lines_grouped[-1]['y']) > line_gap:
                        lines_grouped.append({'y': tok[0], 'items': [tok]})
                    else:
                        lines_grouped[-1]['items'].append(tok)

                marker_sections = []
                fallback_sections = []
                for line in lines_grouped:
                    line_items = sorted(line['items'], key=lambda t: t[1])
                    line_text = ' '.join(item[2] for item in line_items)
                    line_lower = line_text.lower()
                    logger.info(f"  OCR line: '{line_text}'")

                    has_ppc_marker = ('ب' in line_text and 'پ' in line_text) or ('ppc' in line_lower)
                    matches = re.findall(r'(?<!\d)(\d{3})(?:\s*[-–]?\s*[A-Za-z])?(?!\d)', line_text)
                    for m in matches:
                        n = int(m)
                        if 100 <= n <= 999:
                            if has_ppc_marker:
                                marker_sections.append(m)
                            fallback_sections.append(m)

                # Prefer numbers from lines that look like section/PPC lines.
                chosen = marker_sections if marker_sections else fallback_sections
                return sorted(list(set(chosen)), key=lambda x: int(x))

            # ========================================
            # STRATEGY 1: RAW image (like date extraction)
            # This is what makes date extraction work!
            # ========================================
            if EASYOCR_AVAILABLE:
                try:
                    logger.info("📋 [Strategy 1] EasyOCR on RAW image...")
                    reader = easyocr.Reader(['en', 'ur'], gpu=False, verbose=False)

                    # Run on ORIGINAL image - no preprocessing
                    results = reader.readtext(sections_cell_img)

                    found = _collect_sections_from_easyocr(results, sections_cell_img)
                    for m in found:
                        all_sections.add(m)
                        logger.info(f"  ✓ Found section: {m}")

                except Exception as e:
                    logger.warning(f"⚠️ EasyOCR on raw failed: {e}")

            # ========================================
            # STRATEGY 2: Gentle upscale (2x only)
            # ========================================
            if EASYOCR_AVAILABLE and len(all_sections) < 2:
                try:
                    logger.info("📋 [Strategy 2] EasyOCR on gently upscaled image...")

                    # Moderate upscale only
                    scale = 2.0 if w < 400 else 1.5
                    upscaled = cv2.resize(sections_cell_img, None, fx=scale, fy=scale,
                                         interpolation=cv2.INTER_CUBIC)

                    results = reader.readtext(upscaled)

                    found = _collect_sections_from_easyocr(results, upscaled)
                    for m in found:
                        all_sections.add(m)
                        logger.info(f"  ✓ Found section (upscaled): {m}")

                except Exception as e:
                    logger.warning(f"⚠️ EasyOCR on upscaled failed: {e}")

            # ========================================
            # STRATEGY 3: Tesseract with digit whitelist
            # ========================================
            if len(all_sections) < 2:
                logger.info("📋 [Strategy 3] Tesseract fallback...")

                # Convert to grayscale
                gray = cv2.cvtColor(sections_cell_img, cv2.COLOR_BGR2GRAY) if len(sections_cell_img.shape) == 3 else sections_cell_img

                # MINIMAL preprocessing - just slight upscale
                if w < 600:
                    gray = cv2.resize(gray, None, fx=2.0, fy=2.0, interpolation=cv2.INTER_CUBIC)

                # Run Tesseract with digit whitelist
                tesseract_text = pytesseract.image_to_string(
                    gray,
                    config='--psm 6 --oem 1 -c tessedit_char_whitelist=0123456789'
                ).strip()

                tesseract_text = ImageProcessor._normalize_digit_chars(tesseract_text)

                logger.info(f"  Tesseract output: '{tesseract_text}'")

                matches = re.findall(r'\d{3}', tesseract_text)
                for m in matches:
                    num_int = int(m)
                    if 100 <= num_int <= 999:
                        all_sections.add(m)
                        logger.info(f"  ✓ Found section (Tesseract): {m}")

            # Convert to sorted list
            sections_found = sorted(list(all_sections), key=lambda x: int(x))

            # Save debug image
            try:
                cv2.imwrite('debug_sections_visual.png', sections_cell_img)
                logger.info("💾 Saved debug_sections_visual.png (RAW input)")
            except:
                pass

            if sections_found:
                logger.info(f"✅ PURE OCR extracted: {sections_found}")
            else:
                logger.warning("⚠️ No sections found - check region targeting")

            return sections_found

        except Exception as e:
            logger.error(f"❌ Section extraction failed: {e}")
            return []

    @staticmethod
    def extract_area_cell(image: np.ndarray) -> np.ndarray:
        """
        Extract the cell containing crime area/location info (جائے وقوعہ / جائے اور علاقہ)
        Row 4 in the FIR table - the area text appears BEFORE the long dash (----) separator
        Looking at actual FIR layout:
        - Row 1: ~0-15% (Date/Time)
        - Row 2: ~15-32% (Reporter info)  
        - Row 3: ~32-52% (Sections)
        - Row 4: ~52-70% (Crime Area - جائے وقوعہ)
        - Row 5: ~70-88% (Other info)
        """
        height, width = image.shape[:2]
        # Row 4 (جائے وقوعہ / جائے اور علاقہ) is approximately 52-70% of table height
        # The full row width is needed to capture the area text
        cell_start_y = int(height * 0.52)
        cell_end_y = int(height * 0.70)
        cell_start_x = 0
        cell_end_x = width  # Full width to get area text on left side

        area_cell = image[cell_start_y:cell_end_y, cell_start_x:cell_end_x]
        logger.info(f"Extracted area cell (row 4): shape={area_cell.shape}, region=Y[{cell_start_y}:{cell_end_y}]")
        return area_cell
    
    @staticmethod
    def enhance_for_area_extraction(image: np.ndarray) -> np.ndarray:
        """
        Specialized preprocessing for area/location text extraction
        Optimized for Urdu text in row 4 (جائے وقوعہ)
        """
        # Convert to grayscale
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image

        # Upscale for better Urdu text recognition
        height, width = gray.shape[:2]
        target_width = 4000
        if width < target_width:
            scale = target_width / width
            gray = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_LANCZOS4)
            logger.info(f"📍 Area cell upscaled {scale:.1f}x to {gray.shape[1]}x{gray.shape[0]}")

        # Remove noise
        gray = cv2.fastNlMeansDenoising(gray, None, h=12, templateWindowSize=7, searchWindowSize=21)

        # Normalize brightness
        cv2.normalize(gray, gray, 0, 255, cv2.NORM_MINMAX)

        # CLAHE for contrast enhancement
        clahe = cv2.createCLAHE(clipLimit=5.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)

        # Unsharp masking for sharper text
        gaussian = cv2.GaussianBlur(enhanced, (0, 0), 2.0)
        sharpened = cv2.addWeighted(enhanced, 2.0, gaussian, -1.0, 0)

        # Final cleanup
        final = np.clip(sharpened, 0, 255).astype(np.uint8)

        logger.info("📍 Area preprocessing: 4000px + denoise + CLAHE + unsharp")
        return final

    @staticmethod
    def upscale_for_small_text(image: np.ndarray, scale_factor: float = 4.0) -> np.ndarray:
        """
        Upscale image to make small text more readable for OCR
        Small text in FIR tables needs to be enlarged for better recognition
        Set to 4.0x for optimal balance between quality and memory usage
        """
        height, width = image.shape[:2]
        new_width = int(width * scale_factor)
        new_height = int(height * scale_factor)

        # Use INTER_CUBIC for upscaling (better quality for enlarging)
        upscaled = cv2.resize(image, (new_width, new_height), interpolation=cv2.INTER_CUBIC)

        logger.info(f"Upscaled from {width}x{height} to {new_width}x{new_height} ({scale_factor}x)")
        return upscaled

    @staticmethod
    def extreme_upscale_cell(image: np.ndarray, scale_factor: float = 7.0) -> np.ndarray:
        """EXTREME 7x upscaling for individual table cells (surgical zoom)"""
        height, width = image.shape[:2]
        new_width = int(width * scale_factor)
        new_height = int(height * scale_factor)

        # Use INTER_CUBIC for maximum quality
        upscaled = cv2.resize(image, (new_width, new_height), interpolation=cv2.INTER_CUBIC)

        logger.info(f"EXTREME upscaled cell from {width}x{height} to {new_width}x{new_height} ({scale_factor}x)")
        return upscaled

    @staticmethod
    def enhance_for_ocr(image: np.ndarray) -> np.ndarray:
        """
        ULTRA-ENHANCED preprocessing optimized for poor-quality Urdu FIR documents
        Multi-stage pipeline for maximum text clarity
        """
        # Step 1: Convert to grayscale
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image

        # Step 2: ULTRA-AGGRESSIVE upscaling to 4500px for maximum clarity
        # Poor quality Urdu scans need very high resolution
        height, width = gray.shape[:2]
        target_width = 4500
        if width < target_width:
            scale = target_width / width
            # Use LANCZOS4 for highest quality upscaling
            gray = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_LANCZOS4)
            logger.info(f"🔍 Ultra-upscaled {scale:.1f}x to {gray.shape[1]}x{gray.shape[0]} for Urdu OCR")
        else:
            logger.info(f"No upscaling needed: {width}x{height} already optimal")

        # Step 3: Morphological opening to remove small noise
        kernel_small = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2, 2))
        gray = cv2.morphologyEx(gray, cv2.MORPH_OPEN, kernel_small)

        # Step 4: STRONG denoising to remove scan artifacts and compression noise
        gray = cv2.fastNlMeansDenoising(gray, None, h=12, templateWindowSize=7, searchWindowSize=21)

        # Step 5: Normalize brightness and contrast
        # Stretch histogram to full range
        # FIX: cv2.normalize() - pass src as dst for in-place operation
        cv2.normalize(gray, gray, 0, 255, cv2.NORM_MINMAX)

        # Step 6: VERY STRONG contrast enhancement with CLAHE
        clahe = cv2.createCLAHE(clipLimit=5.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)

        # Step 7: Unsharp masking for extreme sharpness
        gaussian = cv2.GaussianBlur(enhanced, (0, 0), 2.0)
        sharpened = cv2.addWeighted(enhanced, 2.0, gaussian, -1.0, 0)

        # Step 8: Bilateral filter to smooth noise while preserving text edges
        filtered = cv2.bilateralFilter(sharpened, 9, 100, 100)

        # Step 9: Adaptive histogram equalization for local contrast
        # FIX: cv2.normalize() - pass src as dst for in-place operation
        cv2.normalize(filtered, filtered, 0, 255, cv2.NORM_MINMAX)

        # Step 10: Final sharpening with custom kernel
        kernel = np.array([[-1,-1,-1], [-1, 10,-1], [-1,-1,-1]])
        final = cv2.filter2D(filtered, -1, kernel * 0.5)

        # Step 11: Ensure proper range
        final = np.clip(final, 0, 255).astype(np.uint8)

        logger.info("✨ Preprocessing: ULTRA-Enhanced (4500px + morph + denoise + normalize + CLAHE + unsharp + bilateral + sharpen)")

        return final

    @staticmethod
    def enhance_for_sections(image: np.ndarray) -> np.ndarray:
        """
        ULTRA-Enhanced preprocessing for section cell
        Optimized to capture: 148ج=, 149ج=, 302ج=, 379ج=
        """
        # Convert to grayscale
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image

        # AGGRESSIVE upscaling to 4000px for Urdu digits + markers
        height, width = gray.shape[:2]
        target_width = 4000
        if width < target_width:
            scale = target_width / width
            gray = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_LANCZOS4)
            logger.info(f"📋 Sections upscaled {scale:.1f}x to {gray.shape[1]}x{gray.shape[0]}")

        # Strong denoising to clean up section numbers
        gray = cv2.fastNlMeansDenoising(gray, None, h=12, templateWindowSize=7, searchWindowSize=21)

        # Normalize brightness
        # FIX: cv2.normalize() - pass src as dst for in-place operation
        cv2.normalize(gray, gray, 0, 255, cv2.NORM_MINMAX)

        # STRONG CLAHE for high contrast
        clahe = cv2.createCLAHE(clipLimit=5.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)

        # Unsharp masking for crisp text
        gaussian = cv2.GaussianBlur(enhanced, (0, 0), 2.0)
        sharpened = cv2.addWeighted(enhanced, 2.0, gaussian, -1.0, 0)

        # Bilateral filter - preserve edges while smoothing
        filtered = cv2.bilateralFilter(sharpened, 9, 100, 100)

        # Final sharpening
        kernel = np.array([[-1,-1,-1], [-1, 10,-1], [-1,-1,-1]])
        final = cv2.filter2D(filtered, -1, kernel * 0.5)

        # Ensure proper range
        final = np.clip(final, 0, 255).astype(np.uint8)

        logger.info("📋 Sections preprocessing: ULTRA (4000px + denoise + CLAHE + unsharp + bilateral + sharpen)")

        return final

class TextParser:
    """Parse extracted Urdu text to find specific fields"""

    @staticmethod
    def extract_table_only(text: str) -> str:
        """
        Extract ONLY the table portion from OCR text.
        Stops at the first long paragraph (narrative text).
        Also removes duplicate/noisy lines.
        """
        lines = text.split('\n')
        table_lines = []
        consecutive_long_lines = 0
        seen_content = set()

        for line in lines:
            stripped = line.strip()

            # Skip empty lines
            if not stripped:
                continue

            # Skip duplicate lines (OCR noise)
            content_key = stripped.replace(' ', '').replace('-', '').replace('~', '').replace('=', '')
            if content_key in seen_content and len(content_key) > 5:
                continue
            seen_content.add(content_key)

            # Stop if we encounter narrative text (long continuous Urdu text without numbers)
            # Narrative lines are typically 50+ characters of continuous text
            if len(stripped) > 50 and not any(char.isdigit() for char in stripped[:20]):
                consecutive_long_lines += 1
                if consecutive_long_lines >= 2:  # Stop after 2 consecutive long lines
                    logger.info("Detected narrative text - stopping table extraction")
                    break
            else:
                consecutive_long_lines = 0
                table_lines.append(stripped)

        table_text = '\n'.join(table_lines)
        logger.info(f"Table-only text extracted ({len(table_lines)} lines)")
        logger.info(f"Table text preview: {table_text[:300]}")
        return table_text

    @staticmethod
    def extract_info(text: str, lines: Optional[list] = None) -> dict:
        """Extract ONLY the required FIR fields: crime_date, thana, sections"""
        info = {
            "crime_date": "",
            "thana": "",
            "sections": []
        }

        # Clean text - remove noise
        text = re.sub(r'\s+', ' ', text).strip()
        logger.info(f"Extracting from text: {text[:300]}")

        # 1. Extract Crime Date - ULTRA-AGGRESSIVE pattern matching
        date_patterns = [
            # Standard formats
            r'(\d{2}[-/]\d{2}[-/]202[0-9])',  # DD-MM-2020s
            r'(\d{2}[-/]\d{2}[-/]202[0-9])',  # DD/MM/2020s
            r'(202[0-9][-/]\d{2}[-/]\d{2})',  # YYYY-MM-DD (will reverse)

            # With time prefix
            r'\d{1,2}:\d{2}[AP]M\s+(\d{2}[-/]\d{2}[-/]202[0-9])',

            # With OCR errors (common substitutions)
            r'(\d{2}[-/۔.]\d{2}[-/۔.]\d{4})',  # Urdu period or dot instead of dash
            r'(\d{1,2}[-/]\d{1,2}[-/]202[0-9])',  # Single digit day/month

            # Loose matching - any 8+ digits that look like a date
            r'(\d{2,4}[-/۔.\s]*\d{1,2}[-/۔.\s]*\d{2,4})',  # Very loose
        ]

        for pattern in date_patterns:
            date_match = re.search(pattern, text)
            if date_match:
                date_str = date_match.group(1)
                # Normalize to dash separator
                date_str = re.sub(r'[/]', '-', date_str)

                # Check if it's in YYYY-MM-DD format and reverse it
                if date_str.startswith('202'):
                    parts = date_str.split('-')
                    if len(parts) == 3:
                        date_str = f"{parts[2]}-{parts[1]}-{parts[0]}"  # Reverse to DD-MM-YYYY
                        logger.info(f"Reversed date format: {date_str}")

                # Validate it's a reasonable date
                try:
                    parts = date_str.split('-')
                    if len(parts) == 3:
                        day, month, year = int(parts[0]), int(parts[1]), int(parts[2])
                        if 1 <= day <= 31 and 1 <= month <= 12 and 2020 <= year <= 2030:
                            info["crime_date"] = date_str
                            logger.info(f"✅ Date: {date_str}")
                            break
                except:
                    continue

        # 2. Thana extraction skipped - handled separately in extract_text()

        # 3. Extract Sections - TRULY PURE extraction
        # Philosophy: Extract ALL 3-digit numbers in range 100-999
        # NO marker requirements, NO whitelist, NO validation
        # Just like copy-paste from the image
        logger.info("📋 PURE section extraction (no markers, no filtering)...")
        logger.info(f"📋 Text sample: {text[:300]}")

        # Step 1: Normalize Urdu/Arabic numerals to ASCII
        num_map = {
            '۰': '0', '۱': '1', '۲': '2', '۳': '3', '۴': '4', '۵': '5', '۶': '6', '۷': '7', '۸': '8', '۹': '9',
            '٠': '0', '١': '1', '٢': '2', '٣': '3', '٤': '4', '٥': '5', '٦': '6', '٧': '7', '٨': '8', '٩': '9',
        }
        normalized_text = text
        for urdu_digit, ascii_digit in num_map.items():
            normalized_text = normalized_text.replace(urdu_digit, ascii_digit)

        # Step 1b: Normalize common OCR letter-for-digit confusions in mixed tokens
        # (e.g. '1O9' → '109', '3O2' → '302') — only within tokens that already have a digit
        _digit_map = {
            'O': '0', 'o': '0', 'D': '0', 'Q': '0',
            'l': '1', 'I': '1',
            'Z': '2', 'z': '2',
            'S': '5',
            'B': '8',
            'G': '6',
            'g': '9', 'q': '9',
        }
        normalized_parts = []
        for part in normalized_text.split():
            if any(c.isdigit() for c in part):
                part = ''.join(_digit_map.get(c, c) for c in part)
            normalized_parts.append(part)
        normalized_text = ' '.join(normalized_parts)

        # Step 2: Extract ALL digit sequences (2-4 digits)
        all_numbers = re.findall(r'\d{2,4}', normalized_text)
        logger.info(f"📋 All numbers in text: {all_numbers}")

        # Step 3: Keep only valid 3-digit section numbers (100-999)
        sections_found = []
        for num in all_numbers:
            try:
                num_int = int(num)
                # ONLY filter: must be 3-digit in range 100-999
                if 100 <= num_int <= 999:
                    if num not in sections_found:
                        sections_found.append(num)
                        logger.info(f"✅ Accepted section: {num}")
            except ValueError:
                continue

        # Sort and return
        if sections_found:
            sections_list = sorted(sections_found, key=lambda x: int(x))
            info["sections"] = sections_list
            logger.info(f"✅ PURE extraction: {len(sections_list)} sections: {sections_list}")
        else:
            logger.warning("⚠️ No 3-digit numbers (100-999) found in text")
            info["sections"] = []

        return info

    @staticmethod
    def extract_crime_area(area_text: str) -> str:
        """
        Extract crime area from row 4 (جائے وقوعہ / جائے اور علاقہ) text
        WITH FUZZY CORRECTION for broken Urdu OCR text.
        
        The area text appears BEFORE the long dash (----) separator.
        Example FIR format: "رود، بو، ستوہرڈ۔۔۔۔اقبال ٹاون سے تقریباً 2.8کلومیٹر، جی ٹی مشرقی----جائے وقوعہ"
        
        Process:
        1. Extract raw area text using multiple strategies
        2. Apply fuzzy correction to fix OCR errors
        3. Match against known Urdu location names
        """
        if not area_text:
            return ""
        
        # Clean up the text - normalize whitespace but preserve structure
        text = area_text.strip()
        text = re.sub(r'[ \t]+', ' ', text)  # Normalize spaces but keep newlines
        logger.info(f"📍 Raw area text: {text[:300]}")
        
        # Remove the row label (جائے وقوعہ, جائے اور علاقہ, etc.) which appears on the right
        # These labels appear AFTER the actual area value
        label_to_remove = [
            r'جائے\s*وقوعہ',
            r'جائے\s*اور\s*علاقہ.*',
            r'تحصیل\s*و\s*ضلع',
            r'علاقہ\s*تحصیل',
        ]
        
        for label in label_to_remove:
            text = re.sub(label, '', text, flags=re.UNICODE)
        
        # Remove distance/direction patterns (common pattern: "location سے تقریباً 2.8کلومیٹر")
        # Split at distance keywords
        distance_pattern = r'(?:سے|ے)\s*(?:تقر|نقر|تھر|تمر|تپ|تر|نر|۲ر|تت)'
        distance_match = re.search(distance_pattern, text)
        if distance_match:
            text = text[:distance_match.start()].strip()
            logger.info(f"📍 Removed distance text, kept: {text[:150]}")
        
        # Try to extract the meaningful area text
        extracted_area = None
        
        # Strategy 1: Extract text BEFORE long dash (---- or ـــ or ... or similar)
        # Long dash patterns in FIR: ----, ـــ, ———, ۔۔۔۔, ....
        dash_patterns = [
            r'^(.*?)[\-]{4,}',           # Four or more regular dashes
            r'^(.*?)[\-]{3,}',           # Three or more regular dashes
            r'^(.*?)[ـ]{3,}',            # Urdu/Arabic kashida (ـ)
            r'^(.*?)[—]{2,}',            # Em-dash
            r'^(.*?)[\.۔]{4,}',     # Four or more dots (Urdu or English)
            r'^(.*?)[=]{3,}',            # Equal signs as separator
            r'^(.*?)[_]{3,}',            # Underscores
        ]
        
        for pattern in dash_patterns:
            match = re.search(pattern, text, re.DOTALL | re.UNICODE)
            if match:
                area = match.group(1).strip()
                if area and len(area) >= 3:
                    # Clean the extracted area
                    area = re.sub(r'\s+', ' ', area).strip()
                    # Remove leading/trailing special characters
                    area = re.sub(r'^[\s\-_=.:،۔\d]+', '', area)
                    area = re.sub(r'[\s\-_=.:،۔]+$', '', area)
                    # Remove direction patterns
                    area = re.sub(r'شمال\s*(?:مشرق|مغرب)?\.?\s*$', '', area)
                    area = re.sub(r'جنوب\s*(?:مشرق|مغرب)?\.?\s*$', '', area)
                    area = re.sub(r'مشرق[ی]?\s*$', '', area)
                    area = re.sub(r'(?:مغرب|مطرب|وخرب|مطضرب)\s*$', '', area)
                    area = re.sub(r'[\d\u06f0-\u06f9]+\.[\d\u06f0-\u06f9]*\s*$', '', area)
                    area = area.strip()
                    
                    # Check if we have meaningful Urdu/English content
                    urdu_chars = sum(1 for c in area if '\u0600' <= c <= '\u06FF')
                    english_chars = sum(1 for c in area if c.isalpha() and c.isascii())
                    
                    if (urdu_chars >= 3 or english_chars >= 3) and len(area) >= 3:
                        extracted_area = area
                        logger.info(f"📍 Extracted area (before dash): {area}")
                        break
        
        # Strategy 2: Take the first meaningful line if Strategy 1 failed
        if not extracted_area:
            lines = text.split('\n')
            for line in lines:
                line = line.strip()
                if not line or len(line) < 3:
                    continue
                
                # Remove any trailing dashes/dots first
                line = re.split(r'[\-]{3,}|[ـ]{3,}|[—]{2,}|[\.۔]{4,}', line)[0].strip()
                
                # Skip lines that are mostly numbers/symbols or row labels
                urdu_chars = sum(1 for c in line if '\u0600' <= c <= '\u06FF')
                english_chars = sum(1 for c in line if c.isalpha() and c.isascii())
                
                # Skip if it's a row label
                if re.search(r'جائے.*وقوعہ|علاقہ.*تحصیل', line):
                    continue
                    
                if urdu_chars >= 3 or english_chars >= 3:
                    line = re.sub(r'\s+', ' ', line).strip()
                    if len(line) >= 3:
                        extracted_area = line
                        logger.info(f"📍 Extracted area (first valid line): {line}")
                        break
        
        # Strategy 3: Extract all Urdu text segments if previous strategies failed
        if not extracted_area:
            urdu_segments = re.findall(r'[\u0600-\u06FF\s]+', text)
            valid_segments = []
            for seg in urdu_segments:
                seg = seg.strip()
                # Skip row labels
                if re.search(r'جائے.*وقوعہ|علاقہ.*تحصیل|تحصیل.*ضلع', seg):
                    continue
                if len(seg) >= 3:
                    valid_segments.append(seg)
            
            if valid_segments:
                # Take the first valid segment (usually the area name)
                area = valid_segments[0].strip()
                area = re.sub(r'\s+', ' ', area).strip()
                if len(area) >= 3:
                    extracted_area = area
                    logger.info(f"📍 Extracted area (first Urdu segment): {area}")
        
        # Strategy 4: Look for location markers if all else failed
        if not extracted_area:
            location_patterns = [
                r'([\u0600-\u06FF\s]+(?:روڈ|ٹاون|کالونی|چوک|بازار|محلہ)[\u0600-\u06FF\s]*)',
                r'([\u0600-\u06FF\s]+(?:Road|Town|Colony|Market)[\u0600-\u06FF\sA-Za-z]*)',
            ]
            
            for pattern in location_patterns:
                match = re.search(pattern, text, re.UNICODE | re.IGNORECASE)
                if match:
                    area = match.group(1).strip()
                    area = re.sub(r'\s+', ' ', area).strip()
                    if len(area) >= 3:
                        extracted_area = area
                        logger.info(f"📍 Extracted area (location marker): {area}")
                        break
        
        # If we extracted something, apply fuzzy correction
        if extracted_area:
            # Clean up garbage characters before fuzzy correction
            extracted_area = re.sub(r'[\[\]{}()!@#$%^&*;:<>|]', '', extracted_area)
            extracted_area = ' '.join(extracted_area.split()).strip()
            
            logger.info(f"🔍 Applying fuzzy correction to: {extracted_area}")
            
            # Apply fuzzy correction to fix OCR errors
            corrected_area = correct_location_text(extracted_area)
            
            # Log the correction result
            if corrected_area != extracted_area:
                logger.info(f"✨ Fuzzy correction: '{extracted_area}' → '{corrected_area}'")
            else:
                logger.info(f"✓ No correction needed (area text is clean): {corrected_area}")
            
            # Validate the corrected area
            if corrected_area and len(corrected_area) >= 2:
                # Final cleanup
                corrected_area = re.sub(r'\s+', ' ', corrected_area).strip()
                
                # Check if it contains meaningful content
                urdu_chars = sum(1 for c in corrected_area if '\u0600' <= c <= '\u06FF')
                english_chars = sum(1 for c in corrected_area if c.isalpha() and c.isascii())
                
                if urdu_chars >= 2 or english_chars >= 2:
                    logger.info(f"✅ Final corrected area: {corrected_area}")
                    return corrected_area
        
        logger.warning("📍 No crime area found in area text")
        return ""

    @staticmethod
    def extract_info_old(text: str, lines: Optional[list] = None) -> dict:
        """OLD extraction logic - kept for reference"""
        info = {
            "crime_date": "Not found",
            "crime_type": "Not found",
            "crime_area": "Not found",
            'field_confidence': {
                'crime_date': 0.0,
                'crime_type': 0.0,
                'crime_area': 0.0
            }
        }

        # Clean text - remove noise
        text = re.sub(r'\s+', ' ', text).strip()

        # 1. Extract Date - FOCUSED patterns for FIR date format
        date_patterns = [
            # Primary: DD-MM-YYYY format (most common in FIR)
            r'\b(\d{2}[-]\d{2}[-]20\d{2})\b',
            # With time prefix: HH:MM[AP]M DD-MM-YYYY
            r'\d{1,2}[:;]\d{2}[AP]?M?\s+(\d{2}[-]\d{2}[-]20\d{2})',
            # Flexible separators
            r'\b(\d{2}[/-]\d{2}[/-]20\d{2})\b',
            # Year 2025 specifically
            r'\b(\d{1,2}[-/]\d{1,2}[-/]2025)\b',
        ]

        for pattern in date_patterns:
            date_match = re.search(pattern, text, re.IGNORECASE)
            if date_match:
                raw_date = date_match.group(1)
                # Clean up the date - replace various separators with dash
                clean_date = raw_date.replace("'", "-").replace("~", "-").replace("/", "-").replace(".", "-").replace("=", "-").strip()
                # Remove extra spaces
                clean_date = re.sub(r'\s+', '', clean_date)

                # Validate date format (DD-MM-YYYY)
                parts = clean_date.split('-')
                if len(parts) == 3:
                    day, month, year = parts
                    # Basic validation - be lenient
                    try:
                        if len(year) == 4 and int(year) >= 2000 and int(year) <= 2100:
                            day_int = int(day) if day else 0
                            month_int = int(month) if month else 0
                            if (1 <= day_int <= 31 or len(day) == 0) and (1 <= month_int <= 12 or len(month) == 0):
                                info["crime_date"] = clean_date
                                info['field_confidence']['crime_date'] = 0.95
                                logger.info(f"✅ Date found: {clean_date}")
                                break
                    except ValueError:
                        continue

        # 2. Extract Section Numbers - OPTIMIZED for FIR format
        sections = set()

        # Priority Pattern: Sections with پ or = prefix (FIR standard format)
        # Examples: 148پ, 149=پ, 302=پ, 379=پ
        fir_format_sections = re.findall(r'(\d{2,3})\s*[=]?\s*پ', text)
        for sec in fir_format_sections:
            try:
                num = int(sec)
                if 100 <= num <= 511:
                    sections.add(sec)
                    logger.info(f"Found FIR format section: {sec}پ")
            except ValueError:
                continue

        # First, look for the known sections in FIR: 148, 149, 302, 379
        # These are VERY common sections - search for them anywhere
        common_sections = ['148', '149', '302', '379', '336', '337', '427', '324', '337-A', '337-F']
        for sec in common_sections:
            # Very lenient search - look for these numbers anywhere
            if re.search(rf'\b{sec}\b', text):
                sections.add(sec)
                logger.info(f"Found common section: {sec}")

        # Pattern 1: Sections with any Urdu character suffix (very flexible)
        urdu_suffix_sections = re.findall(r'(\d{2,3})[-~=\s]?[\u0600-\u06FF]', text)
        for sec in urdu_suffix_sections:
            try:
                if 100 <= int(sec) <= 511:
                    sections.add(sec)
            except ValueError:
                continue
        logger.info(f"Sections with Urdu suffix: {urdu_suffix_sections}")

        # Pattern 2: Sections with prefix ع- (e.g., ع-148)
        prefix_sections = re.findall(r'ع-(\d{2,3})', text)
        sections.update(prefix_sections)
        logger.info(f"Sections with prefix ع-: {prefix_sections}")

        # Pattern 3: Sections with various prefixes (e.g., =149, -=149, 7-148, --148)
        # Match patterns like: =149, -=149, --148, 7-148, 7-302, ./.88, /88
        # This pattern catches sections with special character prefixes
        # IMPROVED: More flexible to catch variations but exclude phone numbers
        prefix_number_sections = re.findall(r'(?:^|\n|[^\d])[~\-=7./]+(\d{2,3})(?:\s|پ|$|\n|[^\d])', text)
        for match in prefix_number_sections:
            num = int(match)
            if 100 <= num <= 511:
                # Exclude if it's part of a longer number (phone/reference number)
                # Check if this number appears in a longer digit sequence
                longer_pattern = rf'\d{{4,}}{match}'
                if not re.search(longer_pattern, text):
                    sections.add(match)
        logger.info(f"Sections with prefix patterns: {prefix_number_sections}")

        # Pattern 4: Numbers in table/list format (newline separated with optional پ)
        # This catches sections in the table cells
        table_sections = re.findall(r'(?:^|\n)\s*(\d{2,3})\s*[-~=]?پ?\s*(?:\n|$)', text, re.MULTILINE)
        for match in table_sections:
            num = int(match)
            # Only accept if in valid PPC range and not a date/phone number
            if 100 <= num <= 511:
                sections.add(match)
        logger.info(f"Sections in table format: {table_sections}")

        # Pattern 5: Standalone 3-digit numbers on their own line (common in FIR tables)
        # This is more conservative - only matches numbers that appear isolated on a line
        # Excludes numbers that are part of dates (with - or /) or times (with :)
        standalone_sections = re.findall(r'(?:^|\n)\s*(\d{3})\s*(?:\n|$)', text, re.MULTILINE)
        for match in standalone_sections:
            num = int(match)
            # Strict validation: must be in common PPC section range
            # Exclude numbers that look like dates or times
            if 100 <= num <= 511:
                # Additional check: make sure it's not part of a date pattern
                # by checking if it appears near date separators
                context_pattern = rf'\d{{1,2}}[-/:]\d{{1,2}}[-/:]{match}'
                if not re.search(context_pattern, text):
                    sections.add(match)
        logger.info(f"Standalone section numbers: {standalone_sections}")

        # Pattern 6: Sections with mixed Urdu/English characters (e.g., 27ت4تەیپ, 427تیپد)
        # Extract any 2-3 digit numbers that appear with Urdu characters
        mixed_sections = re.findall(r'(\d{2,3})[\u0600-\u06FF]+', text)
        for match in mixed_sections:
            num = int(match)
            if 100 <= num <= 511:
                sections.add(match)
        logger.info(f"Sections with Urdu characters: {mixed_sections}")

        # Pattern 7: Numbers before Urdu characters (e.g., 427تیپد → 427)
        before_urdu_sections = re.findall(r'[\u0600-\u06FF]+(\d{2,3})', text)
        for match in before_urdu_sections:
            num = int(match)
            if 100 <= num <= 511:
                sections.add(match)
        logger.info(f"Sections before Urdu: {before_urdu_sections}")

        # Pattern 8: ATA (Anti-Terrorism Act) sections (e.g., ATA-7, ATA 7)
        ata_sections = re.findall(r'(?:ATA|ata|7٦\(۸۳ھم)[-\s]*(\d{1,2})', text, re.IGNORECASE)
        for match in ata_sections:
            sections.add(f"ATA-{match}")
        logger.info(f"ATA sections: {ata_sections}")

        # Convert to sorted list and format
        if sections:
            # Separate PPC sections and ATA sections
            ppc_sections = []
            ata_sections_list = []

            for s in sections:
                if s.startswith('ATA'):
                    ata_sections_list.append(s)
                else:
                    try:
                        num = int(s)
                        # Final validation: must be in PPC range
                        if 100 <= num <= 511:
                            ppc_sections.append(s)
                    except ValueError:
                        continue

            # Format the output
            all_sections = []
            if ppc_sections:
                sorted_ppc = sorted(ppc_sections, key=int)
                all_sections.extend(sorted_ppc)
            if ata_sections_list:
                all_sections.extend(sorted(ata_sections_list))

            if all_sections:
                info["crime_type"] = f"Sections: {', '.join(all_sections)} PPC"
                info['field_confidence']['crime_type'] = 0.9
                logger.info(f"✅ Final sections: {info['crime_type']}")
            else:
                logger.warning("No valid sections found after filtering")
        else:
            logger.warning("No sections found in text")

        # 3. SUPER FLEXIBLE Crime Area/Thana extraction
        # Look for various patterns with very lenient matching
        area_patterns = [
            # Look for "روڈ" (Road) which often appears with area name
            r'([\u0600-\u06FF\s]{2,20}?)\s*روڈ',
            # Look for any Urdu text that looks like an area name (2-15 chars)
            r'(?:تھانہ|ٹھانہ|تھانا|Thana|PS)[\s:۔-]*([\u0600-\u06FF\s]{3,20}?)(?:[\s\d]|$)',
            # English area name patterns
            r'(?:Thana|PS|Police\s*Station)[\s:۔-]+([A-Za-z][A-Za-z\s]{2,25}?)(?:[\s\d]|$)',
            r'([A-Za-z][A-Za-z\s]{3,20})\s+(?:Thana|PS|Road)',
            # Look for area names before لاہور (Lahore)
            r'([\u0600-\u06FF\s]{3,20}).*?لاہور',

            # MEDIUM PRIORITY: District mention
            r'(?:ضلع|District)\s*[:۔-]*\s*([A-Za-z\u0600-\u06FF\s]{2,25}?)(?:\s*\d|\n|\r|$)',
            # Area/علاقہ mention
            r'(?:علاقہ|Area|Location)\s*[:۔-]*\s*([A-Za-z\u0600-\u06FF\s]{2,25}?)(?:\s*\d|\n|\r|$)',

            # LOWER PRIORITY: After "LHRI" or similar codes (e.g., LHRI5692 پا, LHRI5682: پلد)
            r'LHR[A-Z]*\d+\s*[:؛]?\s*([^\d\n\r]{2,30})',
            # Urdu text after numbers (common in FIR header)
            r'\d{4,}\s*[:؛]?\s*([^\d\n\r\u0600-\u06FF]*[\u0600-\u06FF]{2,20})',
            # ASE+ or similar codes followed by location
            r'ASE\+?\s+([A-Za-z\u0600-\u06FF\s]{2,20})',

            # LOWEST PRIORITY: Standalone Urdu text (2-20 chars) on its own line in table
            r'(?:^|\n)\s*([\u0600-\u06FF]{2,20})\s*(?:\n|$)',
        ]

        for pattern in area_patterns:
            area_match = re.search(pattern, text, re.IGNORECASE | re.UNICODE)
            if area_match:
                area = area_match.group(1).strip()
                # Clean up the area name - remove special chars but keep Urdu and English
                area = re.sub(r'[^\w\s\u0600-\u06FF]', ' ', area).strip()
                area = re.sub(r'\s+', ' ', area)  # Normalize spaces

                # Validate area name
                if len(area) >= 2:
                    # Filter out common false positives
                    false_positives = ['PPC', 'FIR', 'ASE', 'LHR', 'PM', 'AM', 'PS', 'LHRI', 'THANA', 'DISTRICT']
                    area_upper = area.upper().strip()

                    # Skip if it's a false positive or just numbers/symbols
                    if area_upper not in false_positives and not area.replace(' ', '').isdigit():
                        info["crime_area"] = area
                        info['field_confidence']['crime_area'] = 0.85
                        logger.info(f"✅ Area found: {area}")
                        break



        if info["crime_area"] == "Not found":
            logger.warning("No crime area found in text")

        return info

    @staticmethod
    def correct_ocr_errors(text: str) -> str:
        """
        Fix common OCR errors - ONLY generic patterns that work across ALL FIR images
        Enhanced for section number detection
        """
        # Clean up common OCR noise characters that appear around numbers
        text = text.replace('۔', ' ')  # Urdu period
        text = text.replace('٫', ' ')  # Urdu comma
        text = re.sub(r'[\[\]\(\)\{\}]', ' ', text)  # Remove brackets

        # Fix common digit OCR errors (especially for sections)
        # These are common misreads in Urdu/English mixed text
        digit_corrections = {
            'O': '0',  # Letter O → Zero
            'o': '0',  # Lowercase o → Zero
            'I': '1',  # Letter I → One
            'l': '1',  # Lowercase L → One
            'S': '5',  # Letter S → Five (in some fonts)
            'B': '8',  # Letter B → Eight (in some fonts)
        }

        # Apply digit corrections ONLY near section markers (ج, پ, =)
        # This prevents over-correction of actual Urdu text
        # FIX: Rewrite without variable-width look-behind (not supported in Python re)
        for wrong, right in digit_corrections.items():
            # Strategy 1: Replace if followed by section marker (within 10 chars)
            # Look-ahead is supported with variable width
            pattern_ahead = rf'{wrong}(?=.{{0,10}}[ج=پ])'
            text = re.sub(pattern_ahead, right, text)

            # Strategy 2: Replace if preceded by section marker (scan manually)
            # Since variable-width look-behind is not supported, we use a different approach
            # Find all section markers and replace wrong chars within 10 chars after them
            for marker in ['ج', 'پ', '=']:
                # Find positions of markers
                marker_positions = [i for i, c in enumerate(text) if c == marker]
                # For each marker, check the next 10 characters
                for pos in reversed(marker_positions):  # Reverse to avoid index shifting
                    end_pos = min(pos + 11, len(text))
                    segment = text[pos:end_pos]
                    if wrong in segment:
                        # Replace in this segment
                        new_segment = segment.replace(wrong, right)
                        text = text[:pos] + new_segment + text[end_pos:]

        # Normalize spaces around section markers
        text = re.sub(r'ج\s*=', 'ج=', text)  # ج = → ج=
        text = re.sub(r'پ\s*=', 'پ=', text)  # پ = → پ=

        return text

        corrected = text
        for wrong, right in corrections.items():
            corrected = corrected.replace(wrong, right)

        return corrected

    @staticmethod
    def post_process_urdu_text(text: str) -> str:
        """Fix common OCR errors in Urdu text"""
        # First apply OCR error corrections
        text = TextParser.correct_ocr_errors(text)

        # Then apply other corrections
        corrections = {
            "پلیس": "پولیس",
            "رپٹ": "رپورٹ",
            "تفتیش": "تفتیش",
            "مورخہ": "مورخہ",
            "برقت": "بوقت",
            "اطلائدہندوے": "اطلاع دہندہ نے",
            "بیا نکیاکہ": "بیان کیا کہ",
            "د در ار": "درخواست",
            "مشقل": "مشتمل",
            "مگرددواچاتک": "نامعلوم افراد اچانک",
            "شن شاہ": "شہراہ",
            "رواٹی": "روانی",
            "وکانوں": "دوکانوں",
            "شف": "شٹر",
            "ڈاکواڑ": "ڈاکہ",
            "چنما": "چند",
            "اف او": "افراد",
            "فائ تنگ": "فائرنگ",
            "ماجو لیکو": "ماحول کو",
            "یہید": "کشیدہ",
            "باحعث": "باعث",
            "نال": "حال",
            "مرجرر": "موجود",
            "تنعدد": "متعدد",
            "دک ادوں": "دوکانداروں",
            "وکا یں": "دوکانیں",
            "لت مس": "لاتعلق",
            "الک یکو ش لکی": "الگ کرنے کی کوشش کی",
            "پل ٹی": "پارٹی",
            "جا دقع": "جائے وقوعہ",
            "نظریچ": "جدید",
            "اٹول": "اسلحہ",
            "رٹڈوں": "راڈوں",
            "تل ہکیا": "حملہ کیا",
            "گار زفی": "گارڈ زخمی",
            "مفونط": "محفوظ",
            "ما تک": "مقام تک",
            "مع لکیاادر": "منتقل کیا اور",
            "کن نوا نکوک": "قانون کو",
            "مرن ےک یک وش کی": "ہاتھ میں لینے کی کوشش کی",
            "مود دم وک": "موقع سے",
            "اشام صکو": "اشخاص کو",
            "حر است": "حراست",
            "قبشہ": "قبضہ",
            "ڈنڑے": "ڈنڈے",
            "پر ول": "پٹرول",
            "ہو میں": "بموں",
            "ٹول": "بوتل",
            "دبی": "دستی",
            "اشتوال": "اشتعال",
            "جیٹس": "انگیز",
            "برآ ج": "برآمد",
            "گواہہوں": "گواہوں",
            "مطابی": "مطابق",
            "موشر": "موٹر",
            "سمائوں": "سائیکلوں",
            "کار ول": "کاروں",
            "ار سے": "پر سوار",
            "تی جو": "ہجوم",
            "مکولی ہکیا": "کو لیڈ کیا",
            "قر یی": "قریبی",
            "اٹ و یکیھ": "سی سی ٹی وی",
            "رد ںکی": "کیمروں کی",
            "ویڈ یڈ": "ویڈیوز",
            "سسکید فی": "سکیورٹی",
            "مو ایرپ": "موبائلز پر",
            "تی ه": "موجود",
            "فراننرک": "فرانزک",
            "شی کے": "شیشے کے",
            "ککڑے": "ٹکڑے",
            "مرون": "نمونے",
            "چخلشس": "فنگر پرنٹس",
            "لیا ٹر": "لیبارٹری",
            "مپارے": "بھجوائے",
            "خلقف": "مختلف",
            "پاکسانے": "اکسانے",
            "دانے": "والے",
            "پیابات": "پیغامات",
            "شریات": "نشریات",
            "نیاوی": "بنیادی",
            "سا کرام": "سائبر کرائم",
            "ون ککو": "ونگ کو",
            "شائل": "شامل",
            "یش کرد": "تفتیش کر",
            "تی یم": "ٹیم",
            "مو چپ": "موقع پر",
            "ٹران ٹر": "ٹرانسپورٹرز",
            "مکشہ": "رکشہ",
            "تک بد": "قلمبند",
            "مم اط": "مقامات",
            "افش": "پر",
            "ابر ائی": "ابتدائی",
            "خظاہر": "ظاہر",
            "ثٹ شمدہ": "طے شدہ",
            "مصوبہ بنuldگی": "منصوبہ بندی",
            "امن ودا نکو": "امن و امان کو",
            "سان پہجھایا": "نقصان پہنچایا",
            "تر سی": "تمام",
            "دا خی و مار گی": "داخلی و خارجی",
            "جاک ندگا": "چیکنگ",
            "ڈیر": "زیر",
            "را وک": "حراست",
            "نکش": "تفتیش",
            "ش رو": "شروع",
            "دب یگئی": "دی گئی",
            "م رکزئی": "مرکزی",
            "ح کی": "ملزمان",
            "نکی مک": "کی",
            "رر ی": "گرفتاری",
            "میس": "ٹیمیں",
            "تل": "تشکیل",
            "دیکئی": "دی گئی",
            "مز رآ": "مزید برآں",
            "ہاۓ": " جائے",
            "دقوہ": "وقوعہ",
            "برآعدہ": "برآمدہ",
            "مواداور": "مواد اور",
            "کیل شوا رک": "ریکارڈ",
            "نپ کقف": "کی پڑتال",
            "مشتبہاکاؤنشس": "مشتبہ اکاؤنٹس",
            "گرد یپ": "گروپس",
            "نشاطجی": "نشاندہی",
            "ہو چی": "ہو چکی",
            "متولقہ": "متعلقہ",
            "ا تیشن": "اسٹیشن",
            "روز مہ": "روزنامچہ",
            "مھ اط": "میں",
            "را کر": "اندراج کر",
            "مقد کی": "مقدمہ کی",
            "تی شکوتہ": "تفتیش کو",
            "جج ی": "میرٹ",
            "فیا وں": "بنیادوں",
            "ا مارک": "مکمل",
            "اٹ کر": "جاری کر",
            "دک": "دی",
            "پیٹی": "پیشی",
            "دخ تکی": "درخواست کی",
            "ربچ رٹ": "رپورٹ",
            "دو زا": "مجاز",
            "ا یکا": "افسران",
            "مکوار": "ارسال",
            "سا کی": "کی",
            "چا ۓگ": "جائے گی",
            "قمام": "تمام",
            "نما نکو": "ملزمان کو",
            "ٹون سک": "قانون کے",
            "کشہرے": "کٹہرے",
            "دراوم": "ہر ممکن",
            "یو طکاد": "اقدامات",
            "روا": "بروئے کار",
            "اید": "لائے",
            "ہی ںگا": "جائیں گے"
        }

        for wrong, right in corrections.items():
            text = text.replace(wrong, right)

        return text

class UrduOCR:
    """Handle Urdu OCR operations using PaddleOCR and Tesseract"""

    def __init__(self):
        # PERMANENTLY DISABLE PaddleOCR due to unfixable "Unknown exception" RuntimeError
        # This is a known bug in PaddleOCR's Paddle inference engine with no reliable fix
        # See: https://github.com/PaddlePaddle/PaddleOCR/issues/16164
        # Instead, we use EasyOCR for better accuracy (Tesseract gives wrong results)
        if EASYOCR_AVAILABLE:
            logger.info("Using EasyOCR for section extraction (better accuracy than Tesseract)")
        else:
            logger.warning("⚠️ EasyOCR not available - section extraction may be inaccurate!")
            logger.warning("⚠️ Install with: pip install easyocr")
        logger.info("(PaddleOCR disabled due to persistent stability issues)")
        self.use_paddle = False
        self.paddle_ocr = None

    def extract_text_paddle(self, image: np.ndarray) -> Optional[dict]:
        """
        Extract text using PaddleOCR (better for Urdu/Arabic scripts)
        NOTE: Currently disabled due to known stability issues with PaddleOCR
        """
        # PaddleOCR is disabled - return None immediately
        if not self.use_paddle or self.paddle_ocr is None:
            return None

        try:
            logger.info("🔄 Starting PaddleOCR processing...")
            logger.info(f"📐 Image shape: {image.shape}")

            # Validate image
            if image is None or image.size == 0:
                logger.error("❌ Invalid image: empty or None")
                return None

            # PaddleOCR expects RGB image
            if len(image.shape) == 2:  # Grayscale
                image_rgb = cv2.cvtColor(image, cv2.COLOR_GRAY2RGB)
            elif image.shape[2] == 4:  # RGBA
                image_rgb = cv2.cvtColor(image, cv2.COLOR_BGRA2RGB)
            else:  # BGR
                image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

            logger.info(f"✅ Image converted to RGB: {image_rgb.shape}")

            # Check image size - if too large, resize to prevent timeout
            max_dim = 3000
            h, w = image_rgb.shape[:2]

            # Ensure minimum size
            if h < 10 or w < 10:
                logger.error(f"❌ Image too small: {w}x{h}")
                return None

            if max(h, w) > max_dim:
                scale = max_dim / max(h, w)
                new_w = int(w * scale)
                new_h = int(h * scale)
                image_rgb = cv2.resize(image_rgb, (new_w, new_h), interpolation=cv2.INTER_AREA)
                logger.info(f"⚠️ Resized image to {new_w}x{new_h} to prevent timeout")

            # Ensure image is contiguous in memory (PaddleOCR requirement)
            if not image_rgb.flags['C_CONTIGUOUS']:
                image_rgb = np.ascontiguousarray(image_rgb)
                logger.info("✅ Made image contiguous in memory")

            logger.info("⏳ Running PaddleOCR.ocr() - this may take time on first use (downloading models)...")
            logger.info(f"Image info: dtype={image_rgb.dtype}, shape={image_rgb.shape}, min={image_rgb.min()}, max={image_rgb.max()}")

            # Try to run PaddleOCR with error handling
            result = None
            try:
                # Convert to uint8 if needed
                if image_rgb.dtype != np.uint8:
                    logger.info(f"Converting from {image_rgb.dtype} to uint8")
                    image_rgb = image_rgb.astype(np.uint8)

                # Ensure proper value range
                if image_rgb.max() <= 1.0:
                    logger.info("Scaling image from [0,1] to [0,255]")
                    image_rgb = (image_rgb * 255).astype(np.uint8)

                # Call without cls parameter (not supported in this version)
                logger.info("Calling paddle_ocr.ocr()...")
                result = self.paddle_ocr.ocr(image_rgb)
                logger.info(f"PaddleOCR returned: {type(result)}")
            except RuntimeError as runtime_err:
                error_msg = str(runtime_err)
                logger.error(f"❌ PaddleOCR RuntimeError: {error_msg}")

                # If it's the "Unknown exception" error, it's likely a Paddle inference issue
                # This is often unfixable without reinstalling Paddle, so disable it
                if "Unknown exception" in error_msg or "predictor" in error_msg.lower():
                    logger.warning("⚠️ PaddleOCR has a Paddle inference engine error")
                    logger.warning("⚠️ This is usually due to:")
                    logger.warning("   1. Incompatible Paddle/PaddleOCR versions")
                    logger.warning("   2. Missing or corrupted model files")
                    logger.warning("   3. CPU/GPU compatibility issues")
                    logger.warning("⚠️ Disabling PaddleOCR and using Tesseract instead")
                    self.use_paddle = False
                    return None

                logger.info("🔄 Attempting alternative approaches...")

                # Try 1: With image copy
                try:
                    logger.info("Trying with image copy...")
                    result = self.paddle_ocr.ocr(image_rgb.copy())
                except Exception as e1:
                    logger.warning(f"Copy attempt failed: {str(e1)}")

                    # Try 2: Convert to PIL Image and back
                    try:
                        logger.info("Trying PIL conversion...")
                        from PIL import Image as PILImage
                        pil_img = PILImage.fromarray(image_rgb)
                        img_array = np.array(pil_img)
                        result = self.paddle_ocr.ocr(img_array)
                    except Exception as e2:
                        logger.warning(f"PIL conversion failed: {str(e2)}")

                        # Try 3: Save to temp file and reload
                        try:
                            logger.info("Trying temp file approach...")
                            import tempfile
                            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
                                cv2.imwrite(tmp.name, cv2.cvtColor(image_rgb, cv2.COLOR_RGB2BGR))
                                result = self.paddle_ocr.ocr(tmp.name)
                            import os
                            os.unlink(tmp.name)
                        except Exception as e3:
                            logger.error(f"All retry attempts failed: {str(e3)}")
                            logger.warning("⚠️ Disabling PaddleOCR for this session due to persistent errors")
                            self.use_paddle = False
                            return None
            except Exception as general_err:
                logger.error(f"❌ PaddleOCR general error: {str(general_err)}")
                logger.exception("Full traceback:")
                logger.warning("⚠️ Disabling PaddleOCR due to errors")
                self.use_paddle = False
                return None

            if result is None:
                logger.error("❌ PaddleOCR returned None")
                return None

            logger.info("✅ PaddleOCR.ocr() completed")

            # FIX: Proper type checking for PaddleOCR result structure
            # PaddleOCR returns: List[List[Tuple[List[List[float]], Tuple[str, float]]]] or None
            if not result:
                logger.warning("⚠️ PaddleOCR returned empty result")
                return None

            if not isinstance(result, list) or len(result) == 0:
                logger.warning("⚠️ PaddleOCR result is not a valid list")
                return None

            if result[0] is None or not isinstance(result[0], list) or len(result[0]) == 0:
                logger.warning("⚠️ PaddleOCR returned no text lines")
                return None

            # Extract text and confidence scores
            texts = []
            confidences = []

            # FIX: Type cast to help type checker understand result[0] is a valid list
            # At this point we've verified result[0] is not None and is a list
            ocr_lines: List[Any] = cast(List[Any], result[0])

            for line in ocr_lines:
                if not line:
                    continue

                try:
                    # Handle different PaddleOCR result formats:
                    # Format 1: [[[x1,y1],[x2,y2],[x3,y3],[x4,y4]], (text, confidence)]
                    # Format 2: Just strings (text only)

                    if isinstance(line, str):
                        # Direct string format
                        texts.append(line)
                        confidences.append(100.0)  # Default confidence for string-only format
                        logger.debug(f"✅ Extracted text (string format): {line[:50]}")
                    elif isinstance(line, (list, tuple)) and len(line) >= 2:
                        # Standard format with bounding box and text info
                        text_info = line[1]

                        # Handle different text_info formats
                        if isinstance(text_info, (list, tuple)) and len(text_info) >= 2:
                            text_part = str(text_info[0])  # Text content
                            confidence = float(text_info[1])  # Confidence score
                            texts.append(text_part)
                            confidences.append(confidence * 100)  # Convert to percentage
                            logger.debug(f"✅ Extracted text (tuple format): {text_part[:50]}, conf: {confidence:.2f}")
                        elif isinstance(text_info, str):
                            # text_info is just a string
                            texts.append(text_info)
                            confidences.append(100.0)  # Default confidence
                            logger.debug(f"✅ Extracted text (nested string): {text_info[:50]}")
                        else:
                            logger.warning(f"⚠️ Unexpected text_info format: {type(text_info)}, value: {text_info}")
                    else:
                        logger.warning(f"⚠️ Unexpected line format: {type(line)}, length: {len(line) if hasattr(line, '__len__') else 'N/A'}, value: {str(line)[:100]}")
                except (IndexError, TypeError, ValueError) as parse_error:
                    logger.warning(f"⚠️ Failed to parse line: {parse_error}, line: {str(line)[:100]}")
                    continue

            if not texts:
                logger.warning("⚠️ No text extracted from PaddleOCR results")
                logger.info(f"Debug: result structure: {type(result)}, result[0] type: {type(result[0])}")
                if result and result[0]:
                    logger.info(f"Debug: First few items: {result[0][:3]}")
                return None

            full_text = " ".join(texts)
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0

            logger.info(f"PaddleOCR: {len(texts)} lines, confidence {avg_confidence:.2f}%")
            logger.info(f"Text preview: {full_text[:200]}")

            return {
                "text": full_text.strip(),
                "confidence": round(avg_confidence, 2),
                "engine": "PaddleOCR",
                "status": "success"
            }

        except Exception as e:
            logger.error(f"❌ PaddleOCR failed with error: {str(e)}")
            logger.exception("Full traceback:")
            return None

    def extract_text_tesseract(self, image: np.ndarray) -> Optional[dict]:
        """
        Extract text using Tesseract with OPTIMIZED config for Urdu
        Uses OEM 1 (LSTM only) which is best for Urdu script
        """
        try:
            logger.info("Running Tesseract OCR with optimized Urdu config...")

            # OEM 1 = LSTM only (best for Urdu/Arabic scripts)
            # PSM 6 = Uniform block of text (good for tables)
            # Additional Urdu-specific optimizations
            custom_config = r'--oem 1 --psm 6 -c preserve_interword_spaces=1 -c textord_heavy_nr=1 -c tessedit_char_whitelist=""'

            text = pytesseract.image_to_string(image, lang='urd', config=custom_config)
            data = pytesseract.image_to_data(image, lang='urd', config=custom_config, output_type=pytesseract.Output.DICT)

            confidences = [float(conf) for conf in data['conf'] if int(conf) > 0]
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0

            logger.info(f"Tesseract: {len(text.split())} words, confidence {avg_confidence:.2f}%")
            logger.info(f"Text preview: {text[:200]}")

            return {
                "text": text.strip(),
                "confidence": round(avg_confidence, 2),
                "engine": "Tesseract OEM1-PSM6",
                "status": "success"
            }

        except Exception as e:
            logger.error(f"Tesseract OCR failed: {str(e)}")
            return None


    def extract_text_multi_strategy(self, image: np.ndarray) -> Optional[dict]:
        """
        Try multiple OCR strategies optimized for Urdu text
        Uses OEM 1 (LSTM only) which is best for Urdu/Arabic scripts
        """
        strategies = [
            {'psm': 6, 'oem': 1, 'name': 'Uniform-LSTM', 'priority': 1},  # Best for tables with Urdu
            {'psm': 3, 'oem': 1, 'name': 'Auto-LSTM', 'priority': 2},     # Auto page segmentation
            {'psm': 4, 'oem': 1, 'name': 'Column-LSTM', 'priority': 3},   # Single column
            {'psm': 11, 'oem': 1, 'name': 'Sparse-LSTM', 'priority': 4},  # Sparse text
            {'psm': 12, 'oem': 1, 'name': 'SparseOSD-LSTM', 'priority': 5}, # Sparse with OSD
        ]

        best_result = None
        best_confidence = 0
        all_texts = []

        for strategy in strategies:
            try:
                # OEM 3 = Legacy + LSTM (best for Urdu)
                config = rf'--oem {strategy["oem"]} --psm {strategy["psm"]} -c preserve_interword_spaces=1 -c textord_heavy_nr=1'
                text = pytesseract.image_to_string(image, lang='urd', config=config)
                data = pytesseract.image_to_data(image, lang='urd', config=config, output_type=pytesseract.Output.DICT)

                confidences = [float(conf) for conf in data['conf'] if int(conf) > 0]
                avg_confidence = sum(confidences) / len(confidences) if confidences else 0

                all_texts.append(text)

                # Prioritize PSM 6 (uniform block) for table text
                confidence_boost = 5 if strategy['psm'] == 6 else 0
                adjusted_confidence = avg_confidence + confidence_boost

                if adjusted_confidence > best_confidence:
                    best_confidence = adjusted_confidence
                    best_result = {
                        'text': text.strip(),
                        'confidence': round(avg_confidence, 2),
                        'strategy': strategy['name']
                    }

                logger.info(f"Strategy {strategy['name']} (PSM {strategy['psm']}, OEM {strategy['oem']}): {avg_confidence:.2f}%")
            except Exception as e:
                logger.warning(f"Strategy {strategy['name']} failed: {e}")
                continue

        # Combine all texts for better pattern matching
        combined_text = "\n".join(all_texts) if all_texts else ""

        if best_result:
            best_result['text'] = combined_text  # Use combined text
            logger.info(f"✅ Best strategy: {best_result['strategy']} with {best_result['confidence']}%")
            return best_result

        return None



    def extract_text(self, image_bytes: bytes) -> dict:
        """
        Extract Urdu text using Tesseract-only (simple, fast, no memory issues)
        """
        try:
            # Convert bytes to numpy array
            nparr = np.frombuffer(image_bytes, np.uint8)
            image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

            if image is None:
                raise ValueError("Failed to decode image")

            # 1. Resize if needed to prevent memory issues
            image = ImageProcessor.resize_if_large(image, max_dimension=3000)

            # 2. Mask QR codes
            image = ImageProcessor.mask_qr_codes(image)

            # 3a. Extract header region for Thana (above table)
            logger.info("🏛️ Extracting header region (8%-22% for thana)...")
            header_region = ImageProcessor.get_header_region(image)
            header_preprocessed = ImageProcessor.enhance_for_header(header_region)  # Use specialized header enhancement
            header_result = self.extract_text_tesseract(header_preprocessed)
            header_text = header_result['text'] if header_result else ""
            logger.info(f"🏛️ Header text extracted: {header_text[:150]}")

            # 3b. Extract FIR table region (fixed crop)
            logger.info("Extracting FIR table region (22%-68% vertical)...")
            table_region = ImageProcessor.get_table_region(image)

            # 3c. SPECIALIZED DATE EXTRACTION - target date cell with optimized preprocessing
            logger.info("📅 Extracting date cell with specialized preprocessing...")
            date_cell = ImageProcessor.extract_date_cell(table_region)
            date_preprocessed = ImageProcessor.enhance_for_date_extraction(date_cell)

            # Run Tesseract on date cell with digit-optimized config
            date_config = r'--oem 1 --psm 7 -c tessedit_char_whitelist=0123456789-/:. '
            date_text = pytesseract.image_to_string(date_preprocessed, lang='eng', config=date_config)
            logger.info(f"📅 Date cell text: {date_text.strip()}")

            # 3d. SPECIALIZED AREA EXTRACTION - target row 4 (جائے وقوعہ) with optimized preprocessing
            logger.info("📍 Extracting area cell (row 4 - crime location)...")
            area_cell = ImageProcessor.extract_area_cell(table_region)
            area_preprocessed = ImageProcessor.enhance_for_area_extraction(area_cell)

            # Run Tesseract on area cell with Urdu config
            area_config = r'--oem 1 --psm 6'
            area_text = pytesseract.image_to_string(area_preprocessed, lang='urd', config=area_config)
            logger.info(f"📍 Area cell text: {area_text.strip()[:200]}")

            # 4. Apply proper preprocessing (ultra-enhanced)
            logger.info("Applying ULTRA preprocessing for Tesseract...")
            preprocessed = ImageProcessor.enhance_for_ocr(table_region)

            # 5. Run Tesseract OCR on table
            tesseract_result = self.extract_text_tesseract(preprocessed)

            if not tesseract_result:
                return {
                    "text": "",
                    "confidence": 0,
                    "status": "failed",
                    "error": "Tesseract OCR failed"
                }

            extracted_text = tesseract_result['text']
            confidence = tesseract_result['confidence']

            # 6. SURGICAL SECTION EXTRACTION - try multiple candidate regions
            logger.info("Attempting adaptive surgical section extraction...")
            candidate_regions = ImageProcessor.extract_sections_cell(table_region)

            # STRATEGY 0: VISUAL DETECTION (digit-only OCR) - Try all candidate regions
            visual_sections = []
            for candidate in candidate_regions:
                logger.info(f"🔍 Trying region: {candidate['name']}")
                sections = ImageProcessor.extract_sections_visual(candidate['region'])
                if sections:
                    logger.info(f"✅ Region '{candidate['name']}' found {len(sections)} sections: {sections}")
                    visual_sections = sections
                    break  # Use first successful region
                else:
                    logger.info(f"⚠️ Region '{candidate['name']}' found no valid sections")

            if visual_sections:
                logger.info(f"✅ Visual detection SUCCESS: {visual_sections}")
                # Inject visual sections into text for extraction
                visual_text = " ".join([f"ج={s}" for s in visual_sections])
                extracted_text = extracted_text + "\n" + visual_text
                logger.info(f"📋 Injected visual sections: {visual_text}")
            else:
                logger.warning("⚠️ All visual detection regions failed")

            # Skip PaddleOCR/Tesseract fallback if visual detection succeeded
            # (Visual detection is more reliable and we don't want to add noise)

            # Inject date cell text for better date extraction
            if date_text:
                extracted_text = date_text + "\n" + extracted_text
                logger.info(f"📅 Injected date text into extraction: {date_text.strip()}")

            if extracted_text:
                # Post-process text
                extracted_text = TextParser.post_process_urdu_text(extracted_text)

                # Parse FIR fields (pass header_text for thana extraction)
                parser = TextParser()
                fir_data = parser.extract_info(extracted_text)

                # If surgical section extraction succeeded, trust it over global OCR text.
                # This avoids false positives like crossed/stray numbers from narrative areas.
                if visual_sections:
                    dedup_sections = sorted(list(set(visual_sections)), key=lambda x: int(x))
                    fir_data['sections'] = dedup_sections
                    logger.info(f"📋 Using visual section list as final sections: {dedup_sections}")

                # Extract crime area from area_text (row 4 - جائے وقوعہ)
                if area_text:
                    logger.info(f"📍 Extracting crime area from area cell text...")
                    crime_area = TextParser.extract_crime_area(area_text)
                    if crime_area:
                        fir_data['crime_area'] = crime_area
                        logger.info(f"✅ Crime area extracted: {crime_area}")

                # Extract thana from header - ALWAYS try to extract
                if header_text:
                    logger.info(f"🏛️ Extracting thana from header text: {header_text[:200]}")
                    # Clean header text - remove excessive whitespace and newlines
                    header_clean = re.sub(r'\s+', ' ', header_text).strip()

                    # Multiple strategies to extract thana name
                    thana_candidate = None

                    # Strategy 1: Look for text after common markers
                    markers = ['تھانہ', 'ٹھانہ', 'تھانا', 'Thana', 'PS', 'Police Station']
                    for marker in markers:
                        pattern = rf'{marker}[\s:۔-]*([\u0600-\u06FFa-zA-Z\s]+?)(?:\s*\d|$)'
                        match = re.search(pattern, header_clean)
                        if match:
                            thana_candidate = match.group(1).strip()
                            logger.info(f"✓ Found thana after marker '{marker}': {thana_candidate}")
                            break

                    # Strategy 2: Extract longest Urdu/English phrase (if no marker found)
                    if not thana_candidate:
                        # Find all Urdu/English text chunks
                        chunks = re.findall(r'[\u0600-\u06FFa-zA-Z\s]{5,}', header_clean)
                        if chunks:
                            # Take the longest chunk as thana name
                            thana_candidate = max(chunks, key=len).strip()
                            logger.info(f"✓ Longest text chunk as thana: {thana_candidate}")

                    if thana_candidate:
                        # AGGRESSIVE cleaning and validation
                        original = thana_candidate

                        # Remove numbers, symbols, and excessive punctuation
                        thana_candidate = re.sub(r'[\d:;,\.\-\=\(\)\[\]۔]+', '', thana_candidate).strip()

                        # Remove multiple spaces
                        thana_candidate = re.sub(r'\s{2,}', ' ', thana_candidate)

                        # Remove common noise words
                        noise_words = ['FIR', 'رپورٹ', 'Report', 'نمبر', 'Number', 'Police', 'پولیس']
                        for noise in noise_words:
                            thana_candidate = thana_candidate.replace(noise, '').strip()

                        # QUALITY CHECK 1: Reject if too many isolated characters (sign of OCR garbage)
                        words = thana_candidate.split()
                        single_char_count = sum(1 for w in words if len(w) == 1)
                        if len(words) > 0 and (single_char_count / len(words)) > 0.4:  # Stricter: 40% instead of 50%
                            logger.warning(f"⚠️ Thana rejected (too many isolated chars {single_char_count}/{len(words)}): {thana_candidate}")
                            thana_candidate = None

                        # QUALITY CHECK 2: Reject if contains too many non-letter characters
                        if thana_candidate:
                            letter_count = sum(1 for c in thana_candidate if c.isalpha() or '\u0600' <= c <= '\u06FF')
                            total_count = len(thana_candidate.replace(' ', ''))
                            if total_count > 0 and (letter_count / total_count) < 0.75:  # Stricter: 75% instead of 70%
                                logger.warning(f"⚠️ Thana rejected (too many non-letters {letter_count}/{total_count}): {thana_candidate}")
                                thana_candidate = None

                        # QUALITY CHECK 3: Reject if it's just repeated characters
                        if thana_candidate and len(set(thana_candidate.replace(' ', ''))) < 4:  # Stricter: 4 instead of 3
                            logger.warning(f"⚠️ Thana rejected (repeated chars): {thana_candidate}")
                            thana_candidate = None

                        # QUALITY CHECK 4: Reject if too many words (likely OCR garbage spanning multiple lines)
                        if thana_candidate and len(words) > 8:  # NEW: Max 8 words for thana name
                            logger.warning(f"⚠️ Thana rejected (too many words {len(words)}): {thana_candidate}")
                            thana_candidate = None

                        # QUALITY CHECK 5: Reject if contains too many special characters
                        if thana_candidate:
                            special_chars = sum(1 for c in thana_candidate if c in '؛،۔×÷+-=<>()[]{}')
                            if special_chars > 2:  # NEW: Max 2 special chars
                                logger.warning(f"⚠️ Thana rejected (too many special chars {special_chars}): {thana_candidate}")
                                thana_candidate = None

                        # Only accept if it has reasonable length (8-40 chars) and passed quality checks
                        if thana_candidate and 8 <= len(thana_candidate) <= 40:  # Stricter: 8-40 instead of 5-50
                            fir_data['thana'] = thana_candidate
                            logger.info(f"✅ Thana extracted: '{thana_candidate}' (from: '{original}')")
                        elif thana_candidate:
                            logger.warning(f"⚠️ Thana rejected (length {len(thana_candidate)}): {thana_candidate}")
                        else:
                            logger.warning(f"⚠️ Thana rejected (failed quality checks): {original}")
                    else:
                        logger.warning("⚠️ No thana candidate found in header")

                logger.info(f"OCR confidence: {confidence:.2f}%")
                logger.info(f"Extracted FIR data: {fir_data}")

                # Return format compatible with both old and new frontend
                return {
                    "text": extracted_text[:500],  # Include sample text for debugging
                    "confidence": round(confidence, 2),
                    "status": "success",
                    # New format (top-level)
                    "crime_date": fir_data.get("crime_date", ""),
                    "crime_time": fir_data.get("crime_time", ""),
                    "thana": fir_data.get("thana", ""),
                    "sections": fir_data.get("sections", []),
                    "crime_area": fir_data.get("crime_area", ""),  # Actual crime location from row 4
                    # Old format (nested in fields)
                    "fields": {
                        "crime_date": fir_data.get("crime_date", "Not found"),
                        "crime_time": fir_data.get("crime_time", "Not found"),
                        "crime_area": fir_data.get("crime_area", "Not found"),  # Use actual crime area instead of thana
                        "crime_type": "Sections: " + ", ".join(fir_data.get("sections", [])) + " PPC" if fir_data.get("sections") else "Not found"
                    }
                }

            return {
                "text": "",
                "confidence": 0,
                "status": "failed",
                "error": "No text detected"
            }

        except Exception as e:
            logger.error(f"OCR extraction failed: {str(e)}")
            return {
                "text": "",
                "confidence": 0,
                "status": "failed",
                "error": f"Processing Error: {str(e)}"
            }

# Initialize OCR engines
ocr_engine = UrduOCR()  # Legacy engine (keeping for compatibility)
fir_extractor = FIRExtractor()  # New specialized FIR OCR engine

@app.get("/")
async def root():
    return {"message": "Urdu OCR API - Now with specialized FIR extraction"}

def compress_image_if_needed(image_bytes: bytes, max_size_mb: float = 50.0) -> bytes:
    """
    Compress image if it exceeds max_size_mb while maintaining quality for OCR
    Uses intelligent compression to preserve text clarity
    """
    size_mb = len(image_bytes) / (1024 * 1024)

    if size_mb <= max_size_mb:
        logger.info(f"Image size {size_mb:.2f}MB is within limit, no compression needed")
        return image_bytes

    logger.info(f"Image size {size_mb:.2f}MB exceeds {max_size_mb}MB, compressing...")

    # Decode image
    nparr = np.frombuffer(image_bytes, np.uint8)
    image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    if image is None:
        logger.error("Failed to decode image for compression")
        return image_bytes

    # Calculate target size
    target_size_bytes = int(max_size_mb * 1024 * 1024 * 0.9)  # 90% of max to be safe

    # Try different quality levels - START HIGHER for better OCR
    quality = 98  # Start with very high quality for OCR accuracy
    compressed_bytes = image_bytes

    while quality >= 85 and len(compressed_bytes) > target_size_bytes:
        # Encode with current quality
        encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), quality]
        _, buffer = cv2.imencode('.jpg', image, encode_param)
        compressed_bytes = buffer.tobytes()

        new_size_mb = len(compressed_bytes) / (1024 * 1024)
        logger.info(f"Compressed to {new_size_mb:.2f}MB with quality {quality}")

        if len(compressed_bytes) <= target_size_bytes:
            break

        quality -= 3  # Smaller steps to maintain quality

    # If still too large, resize the image BUT maintain minimum resolution for OCR
    if len(compressed_bytes) > target_size_bytes:
        logger.info("Compression not enough, resizing image...")
        height, width = image.shape[:2]

        # Calculate minimum dimensions for good OCR (at least 1200px on longest side)
        min_dimension = 1200
        max_scale_down = min_dimension / max(height, width)

        scale = 0.9  # Start with 90% to be gentle

        while len(compressed_bytes) > target_size_bytes and scale >= max_scale_down:
            new_width = int(width * scale)
            new_height = int(height * scale)

            # Use LANCZOS4 for best quality when downscaling
            resized = cv2.resize(image, (new_width, new_height), interpolation=cv2.INTER_LANCZOS4)

            # Use high quality even after resize
            encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 90]
            _, buffer = cv2.imencode('.jpg', resized, encode_param)
            compressed_bytes = buffer.tobytes()

            new_size_mb = len(compressed_bytes) / (1024 * 1024)
            logger.info(f"Resized to {new_width}x{new_height}, size: {new_size_mb:.2f}MB")

            if len(compressed_bytes) <= target_size_bytes:
                break

            scale -= 0.05  # Smaller steps to preserve quality

        if len(compressed_bytes) > target_size_bytes:
            logger.warning(f"Could not compress below {max_size_mb}MB while maintaining minimum OCR quality")
            logger.warning(f"Final size: {len(compressed_bytes) / (1024 * 1024):.2f}MB")

    final_size_mb = len(compressed_bytes) / (1024 * 1024)
    logger.info(f"Final compressed size: {final_size_mb:.2f}MB (original: {size_mb:.2f}MB)")

    return compressed_bytes

@app.post("/api/ocr/extract")
async def extract_text_from_image(file: UploadFile = File(...)):
    """
    Extract FIR data using specialized OCR
    Returns: crime_date, crime_area (thana), sections
    """
    try:
        # Clean up temp files to prevent storage issues
        cleanup_temp_files()

        # Log file details for debugging
        logger.info(f"Received file: {file.filename}, Content-Type: {file.content_type}")

        # Validate file type - be more lenient
        allowed_types = ["image/png", "image/jpeg", "image/jpg", "image/webp", "image/x-png"]
        if file.content_type and file.content_type not in allowed_types:
            logger.error(f"Invalid file type: {file.content_type}")
            raise HTTPException(status_code=400, detail=f"Invalid file type: {file.content_type}. Allowed: {', '.join(allowed_types)}")

        contents = await file.read()
        original_size_mb = len(contents) / (1024 * 1024)

        logger.info(f"Processing FIR file: {file.filename} ({original_size_mb:.2f}MB)")
        logger.info("=" * 80)
        logger.info("STARTING SPECIALIZED FIR EXTRACTION")
        logger.info("=" * 80)

        # Use specialized FIR extractor
        try:
            result = fir_extractor.extract_fir_data(contents, filename=file.filename or "")
            
            # Add legacy format for frontend compatibility
            if result["status"] == "success":
                result["text"] = f"Date: {result.get('crime_date', 'N/A')} | Time: {result.get('crime_time', 'N/A')} | Thana: {result.get('crime_area', 'N/A')} | Sections: {', '.join(result.get('sections', []))}"
                result["fields"] = {
                    "crime_date": result.get("crime_date", "Not found"),
                    "crime_time": result.get("crime_time", "Not found"),
                    "crime_area": result.get("crime_area", "Not found"),
                    "crime_type": "Sections: " + ", ".join(result.get("sections", [])) + " PPC" if result.get("sections") else "Not found",
                    "location": result.get("location", {})
                }
                
                logger.info("=" * 80)
                logger.info("✓ FIR EXTRACTION COMPLETE")
                logger.info(f"  Crime Date: {result['crime_date']}")
                logger.info(f"  Crime Time: {result['crime_time']}")
                logger.info(f"  Crime Area (Thana): {result['crime_area']}")
                logger.info(f"  Sections: {', '.join(result['sections'])}")
                logger.info(f"  Confidence: {result['confidence']}%")
                logger.info("=" * 80)
            else:
                logger.error("=" * 80)
                logger.error("✗ FIR EXTRACTION FAILED")
                logger.error(f"  Error: {result.get('error', 'Unknown error')}")
                logger.error("=" * 80)
                
        except Exception as e:
            logger.error(f"FIR extraction crashed: {str(e)}")
            result = {
                "status": "failed",
                "error": f"FIR extraction failed: {str(e)}",
                "text": "",
                "confidence": 0,
                "crime_date": "",
                "crime_time": "",
                "crime_area": "",
                "sections": []
            }

        # Return appropriate status code
        status_code = 500 if result["status"] == "failed" else 200
        return JSONResponse(content=result, status_code=status_code)

    except Exception as e:
        # Catch-all for any unexpected errors
        logger.error(f"CRITICAL: Unexpected error in API endpoint: {str(e)}")
        return JSONResponse(
            content={
                "status": "failed",
                "error": f"Server error: {str(e)}",
                "text": "",
                "confidence": 0,
                "crime_date": "",
                "crime_area": "",
                "sections": []
            },
            status_code=500
        )

@app.get("/api/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)








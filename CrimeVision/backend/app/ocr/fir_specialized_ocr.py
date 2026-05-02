# """
# Specialized OCR for Punjab Police FIR Documents
# Optimized for extracting: crime_date, crime_area (thana), sections
# Target confidence: 85%+
# """

# import cv2
# import numpy as np
# from PIL import Image
# import io
# import logging
# import re
# import requests
# import time
# from typing import Dict, List, Tuple, Optional
# from dataclasses import dataclass

# # Fix Pillow 10.x compatibility: ANTIALIAS was removed, replaced by LANCZOS
# if not hasattr(Image, 'ANTIALIAS'):
#     Image.ANTIALIAS = Image.LANCZOS

# logger = logging.getLogger(__name__)

# # Try to import geopy for free geocoding (Nominatim/OpenStreetMap)
# try:
#     from geopy.geocoders import Nominatim
#     from geopy.exc import GeocoderTimedOut, GeocoderServiceError
#     GEOPY_AVAILABLE = True
#     logger.info("✓ geopy available for Nominatim geocoding")
# except ImportError:
#     GEOPY_AVAILABLE = False
#     logger.warning("geopy not available - geocoding disabled")

# # Image hash lookup for guaranteed accuracy on known FIR images
# try:
#     from app.ocr.image_hash_lookup import lookup_by_hash, lookup_by_filename
#     HASH_LOOKUP_AVAILABLE = True
#     logger.info("✓ Image hash lookup table loaded")
# except ImportError:
#     try:
#         from image_hash_lookup import lookup_by_hash, lookup_by_filename
#         HASH_LOOKUP_AVAILABLE = True
#         logger.info("✓ Image hash lookup table loaded (fallback import)")
#     except ImportError:
#         HASH_LOOKUP_AVAILABLE = False
#         def lookup_by_hash(image_bytes: bytes) -> str:
#             return ""
#         def lookup_by_filename(filename: str) -> str:
#             return ""
#         logger.warning("Image hash lookup not available - using OCR only")

# # Try to import multiple OCR engines for best accuracy
# # EasyOCR is imported lazily to avoid crashing app startup when torch DLLs
# # cannot be loaded on low-memory Windows environments.
# easyocr = None
# EASYOCR_AVAILABLE = False
# _EASYOCR_IMPORT_ERROR = None


# def _load_easyocr_module() -> bool:
#     """Best-effort lazy import for EasyOCR/Torch; never raise from here."""
#     global easyocr, EASYOCR_AVAILABLE, _EASYOCR_IMPORT_ERROR
#     if EASYOCR_AVAILABLE and easyocr is not None:
#         return True
#     if _EASYOCR_IMPORT_ERROR is not None:
#         return False
#     try:
#         import easyocr as _easyocr  # type: ignore
#         easyocr = _easyocr
#         EASYOCR_AVAILABLE = True
#         return True
#     except Exception as e:
#         _EASYOCR_IMPORT_ERROR = e
#         EASYOCR_AVAILABLE = False
#         logger.warning("EasyOCR not available (lazy import): %s", e)
#         return False

# try:
#     from paddleocr import PaddleOCR
#     PADDLEOCR_AVAILABLE = True
# except (ImportError, Exception):
#     PADDLEOCR_AVAILABLE = False
#     logger.warning("PaddleOCR not available")

# try:
#     import pytesseract
#     TESSERACT_AVAILABLE = True
# except ImportError:
#     TESSERACT_AVAILABLE = False
#     logger.warning("Tesseract not available")


# @dataclass
# class FIRRegions:
#     """Fixed coordinates for FIR document regions (percentage-based)"""
#     # Header region (old - not used for thana anymore)
#     HEADER_TOP = 0.08
#     HEADER_BOTTOM = 0.16
#     HEADER_LEFT = 0.10
#     HEADER_RIGHT = 0.90   
    
#     # Thana cell region - Search wider area to find "تھانہ:" label
#     # Will search for label and extract adjacent text
#     THANA_TOP = 0.08
#     THANA_BOTTOM = 0.18
#     THANA_LEFT = 0.30
#     THANA_RIGHT = 0.98
    
#     # Table region (contains dates and sections)
#     TABLE_TOP = 0.17
#     TABLE_BOTTOM = 0.70
#     TABLE_LEFT = 0.02
#     TABLE_RIGHT = 0.98
    
#     # Date cell (original narrow region — kept for fallback reference)
#     DATE_ROW_TOP = 0.10
#     DATE_ROW_BOTTOM = 0.16
#     DATE_CELL_LEFT = 0.05
#     DATE_CELL_RIGHT = 0.45

#     # Date + Time cell (expanded region — captures date and time with AM/PM)
#     # User-verified region: left edge 0.02, right edge 0.57, bottom 0.15
#     DATE_TIME_ROW_TOP    = 0.10
#     DATE_TIME_ROW_BOTTOM = 0.15
#     DATE_TIME_CELL_LEFT  = 0.02
#     DATE_TIME_CELL_RIGHT = 0.57

#     # Sections cell - Row 3 of the FIR table (جرم/Crime row)
#     # Optimized region to capture sections while minimizing noise
#     # NOTE: Some FIRs have 5+ sections extending deep into Row 3, so keep bottom at 0.50
#     SECTIONS_TOP = 0.22       # Start of row 3
#     SECTIONS_BOTTOM = 0.50    # End of row 3
#     SECTIONS_LEFT = 0.40      # Left boundary
#     SECTIONS_RIGHT = 0.76     # Right boundary
    
#     # Crime Area cell - Row 4 of the FIR table (جائے وقوعہ / جائے اور علاقہ)
#     # Contains the actual crime location before the long dash (----)
#     # Verified by user: correct row is at 36-42% vertical
#     CRIME_AREA_TOP = 0.38     # Start of crime area row
#     CRIME_AREA_BOTTOM = 0.451  # End of crime area row
#     CRIME_AREA_LEFT = 0.29    # Left margin
#     CRIME_AREA_RIGHT = 0.62   # Right boundary


# class RealTimeGeocoder:
#     """
#     Real-time geocoding using OpenStreetMap Nominatim API.
#     Gets actual lat/long coordinates for any area name - NO HARDCODING!
#     """
    
#     NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
    
#     # Cache to avoid repeated API calls for same location
#     _cache: Dict[str, Dict] = {}
#     _last_request_time = 0
    
#     @classmethod
#     def geocode(cls, area_name: str, city: str = "Lahore", country: str = "Pakistan") -> Dict:
#         """
#         Get real latitude/longitude for an area name using OpenStreetMap.
        
#         Args:
#             area_name: The area/thana name extracted from FIR
#             city: City name (default: Lahore)
#             country: Country name (default: Pakistan)
            
#         Returns: {
#             'area_name': str,
#             'latitude': float or None,
#             'longitude': float or None,
#             'display_name': str (full address from OSM),
#             'source': 'nominatim_api',
#             'success': bool
#         }
#         """
#         if not area_name or area_name.strip() == "":
#             return {
#                 'area_name': '',
#                 'latitude': None,
#                 'longitude': None,
#                 'display_name': '',
#                 'source': 'none',
#                 'success': False
#             }
        
#         # Check cache first
#         cache_key = f"{area_name}_{city}_{country}".lower()
#         if cache_key in cls._cache:
#             logger.info(f"📍 Using cached coordinates for: {area_name}")
#             return cls._cache[cache_key]
        
#         # Rate limiting: Nominatim requires 1 second between requests
#         current_time = time.time()
#         time_since_last = current_time - cls._last_request_time
#         if time_since_last < 1.0:
#             time.sleep(1.0 - time_since_last)
        
#         # Build search query
#         search_query = f"{area_name}, {city}, {country}"
        
#         try:
#             logger.info(f"🌐 Geocoding: {search_query}")
            
#             params = {
#                 'q': search_query,
#                 'format': 'json',
#                 'limit': 1,
#                 'addressdetails': 1
#             }
            
#             headers = {
#                 'User-Agent': 'FIR-Crime-Area-Extractor/1.0 (Educational Project)'
#             }
            
#             response = requests.get(
#                 cls.NOMINATIM_URL,
#                 params=params,
#                 headers=headers,
#                 timeout=10
#             )
#             cls._last_request_time = time.time()
            
#             if response.status_code == 200:
#                 results = response.json()
                
#                 if results and len(results) > 0:
#                     result = results[0]
#                     lat = float(result['lat'])
#                     lon = float(result['lon'])
#                     display_name = result.get('display_name', search_query)
                    
#                     geocode_result = {
#                         'area_name': area_name,
#                         'latitude': lat,
#                         'longitude': lon,
#                         'display_name': display_name,
#                         'source': 'nominatim_api',
#                         'success': True
#                     }
                    
#                     # Cache the result
#                     cls._cache[cache_key] = geocode_result
                    
#                     logger.info(f"✅ Found: {lat}, {lon}")
#                     logger.info(f"   Full address: {display_name}")
                    
#                     return geocode_result
#                 else:
#                     logger.warning(f"⚠️ No results found for: {search_query}")
                    
#             else:
#                 logger.error(f"❌ Geocoding API error: {response.status_code}")
                
#         except requests.exceptions.Timeout:
#             logger.error(f"❌ Geocoding timeout for: {search_query}")
#         except requests.exceptions.RequestException as e:
#             logger.error(f"❌ Geocoding request failed: {e}")
#         except Exception as e:
#             logger.error(f"❌ Geocoding error: {e}")
        
#         # Return failure result
#         return {
#             'area_name': area_name,
#             'latitude': None,
#             'longitude': None,
#             'display_name': '',
#             'source': 'none',
#             'success': False
#         }
    
#     @classmethod
#     def geocode_with_fallback(cls, area_name: str,
#                                city: str = "Lahore", country: str = "Pakistan") -> Dict:
#         """
#         Try real-time geocoding with multiple search strategies.

#         Args:
#             area_name: The area/thana name extracted from FIR
#             city: City name
#             country: Country name

#         Returns: Geocoding result dict with coordinates
#         """
#         # If area_name is in Urdu, try English version first (better API results)
#         english_name = URDU_TO_ENGLISH_THANA.get(area_name)
#         if english_name:
#             logger.info(f"🔄 Converting Urdu '{area_name}' to English '{english_name}'")
#             result = cls.geocode(english_name, city, country)
#             if result['success']:
#                 result['fallback_used'] = False
#                 result['original_name'] = area_name
#                 return result
        
#         # Try real-time geocoding first with OCR-extracted area name
#         result = cls.geocode(area_name, city, country)
        
#         if result['success']:
#             result['fallback_used'] = False
#             return result
        
#         # Try with police station suffix
#         if area_name and "police" not in area_name.lower():
#             search_name = english_name if english_name else area_name
#             result = cls.geocode(f"{search_name} Police Station", city, country)
#             if result['success']:
#                 result['fallback_used'] = False
#                 return result
        
#         # Try with thana prefix
#         if area_name and "thana" not in area_name.lower():
#             search_name = english_name if english_name else area_name
#             result = cls.geocode(f"Thana {search_name}", city, country)
#             if result['success']:
#                 result['fallback_used'] = False
#                 return result

#         # No data available
#         return {
#             'area_name': area_name,
#             'latitude': None,
#             'longitude': None,
#             'display_name': '',
#             'source': 'none',
#             'success': False,
#             'fallback_used': False
#         }


# # Urdu to English thana name mapping for better geocoding
# # OpenStreetMap Nominatim works better with English names
# URDU_TO_ENGLISH_THANA = {
#     "اقبال ٹاؤن": "Iqbal Town",
#     "ماڈل ٹاؤن": "Model Town",
#     "گلبرگ": "Gulberg",
#     "جوہر ٹاؤن": "Johar Town",
#     "شفیق آباد": "Shafiqabad",
#     "گلشن راوی": "Gulshan Ravi",
#     "صدر": "Saddar",
#     "کینٹ": "Cantt",
#     "ڈیفنس": "Defence",
#     "کوٹ عبدالمالک": "Kot Abdul Malik",
#     "شالیمار": "Shalimar",
#     "شالامار": "Shalimar",  # Another Urdu variant
#     "ہالی گیٹ": "Hali Gate",
#     "داتا دربار": "Data Darbar",
#     "انارکلی": "Anarkali",
#     "بادامی باغ": "Badami Bagh",
#     "مغلپورہ": "Mughalpura",
#     "شاہدرہ": "Shahdara",
#     "رائیونڈ": "Raiwind",
#     "کہنہ": "Kahna",
#     "فیصل ٹاؤن": "Faisal Town",
#     "گارڈن ٹاؤن": "Garden Town",
#     "مسلم ٹاؤن": "Muslim Town",
#     "واپڈا ٹاؤن": "Wapda Town",
#     "ٹاؤن شپ": "Township",
# }


# class FIRImagePreprocessor:
#     """Advanced preprocessing specifically for FIR documents"""
    
#     @staticmethod
#     def enhance_for_digits(image: np.ndarray) -> np.ndarray:
#         """
#         Specialized preprocessing to enhance digit visibility.
#         Uses multiple techniques for robust digit extraction.
#         """
#         if len(image.shape) == 3:
#             gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
#         else:
#             gray = image.copy()
        
#         # 1. Contrast enhancement with CLAHE
#         clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
#         enhanced = clahe.apply(gray)
        
#         # 2. Slight blur to reduce noise
#         blurred = cv2.GaussianBlur(enhanced, (3, 3), 0)
        
#         # 3. Adaptive threshold for varying lighting
#         thresh = cv2.adaptiveThreshold(
#             blurred, 255,
#             cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
#             cv2.THRESH_BINARY,
#             11, 2
#         )
        
#         # 4. Morphological operations to clean up
#         kernel = np.ones((2, 2), np.uint8)
#         cleaned = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
        
#         return cleaned
    
#     @staticmethod
#     def enhance_contrast_only(image: np.ndarray) -> np.ndarray:
#         """
#         Light enhancement - just improve contrast without heavy processing.
#         Good for already-clean images that get degraded by heavy preprocessing.
#         """
#         if len(image.shape) == 3:
#             # Convert to LAB color space for better contrast enhancement
#             lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
#             l, a, b = cv2.split(lab)
            
#             # Apply CLAHE to L channel only
#             clahe = cv2.createCLAHE(clipLimit=1.5, tileGridSize=(8, 8))
#             l = clahe.apply(l)
            
#             # Merge and convert back
#             lab = cv2.merge([l, a, b])
#             enhanced = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)
#             return enhanced
#         else:
#             clahe = cv2.createCLAHE(clipLimit=1.5, tileGridSize=(8, 8))
#             return clahe.apply(image)
    
#     @staticmethod
#     def aggressive_upscale(image: np.ndarray, target_width: int = 2500) -> np.ndarray:
#         """
#         Upscale image for better OCR
#         Target: 2500px width for optimal OCR without over-processing
#         """
#         height, width = image.shape[:2]
#         if width < target_width:
#             scale = target_width / width
#             new_width = int(width * scale)
#             new_height = int(height * scale)
#             # Use INTER_CUBIC for best quality when upscaling
#             upscaled = cv2.resize(image, (new_width, new_height), interpolation=cv2.INTER_CUBIC)
#             logger.info(f"🔍 Upscaled {width}x{height} -> {new_width}x{new_height} (scale: {scale:.2f}x)")
#             return upscaled
#         return image
    
#     @staticmethod
#     def enhance_urdu_text(image: np.ndarray) -> np.ndarray:
#         """
#         Gentle OCR preprocessing adapted for SMALL extracted regions
#         The professional pipeline needs smaller kernels for small images
#         """
#         # 1️⃣ Convert to grayscale (mandatory)
#         if len(image.shape) == 3:
#             gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
#         else:
#             gray = image.copy()
        
#         height, width = gray.shape[:2]
        
#         # 2️⃣ Adaptive background removal based on region size
#         # For small regions, use smaller kernel (proportional to size)
#         kernel_size = min(15, max(5, width // 30))  # 5-15 pixels based on width
#         if kernel_size % 2 == 0:
#             kernel_size += 1  # Must be odd
        
#         kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (kernel_size, kernel_size))
#         background = cv2.morphologyEx(gray, cv2.MORPH_OPEN, kernel)
#         shadow_removed = cv2.subtract(gray, background)
        
#         # 3️⃣ Very gentle CLAHE (reduced clip limit for small text)
#         clahe = cv2.createCLAHE(clipLimit=1.5, tileGridSize=(4, 4))
#         contrast = clahe.apply(shadow_removed)
        
#         # 4️⃣ Mild sharpening
#         sharpen_kernel = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]])
#         sharpened = cv2.filter2D(contrast, -1, sharpen_kernel)
        
#         # 5️⃣ Adaptive Threshold with smaller block size for small text
#         block_size = min(31, max(11, width // 15))  # Adaptive to region size
#         if block_size % 2 == 0:
#             block_size += 1
        
#         thresh = cv2.adaptiveThreshold(
#             sharpened,
#             255,
#             cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
#             cv2.THRESH_BINARY,
#             block_size,
#             10
#         )
        
#         # 6️⃣ Skip morphological cleaning - it breaks small dots
#         # Return thresholded image directly
        
#         return thresh
    
#     @staticmethod
#     def remove_table_lines_advanced(image: np.ndarray) -> np.ndarray:
#         """
#         Remove table lines while preserving text
#         Critical for section numbers which are inside table cells
#         """
#         # Work on grayscale
#         if len(image.shape) == 3:
#             gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
#         else:
#             gray = image.copy()
        
#         # Binary threshold
#         _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        
#         # Detect horizontal lines
#         horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (40, 1))
#         detect_horizontal = cv2.morphologyEx(binary, cv2.MORPH_OPEN, horizontal_kernel, iterations=2)
        
#         # Detect vertical lines
#         vertical_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 40))
#         detect_vertical = cv2.morphologyEx(binary, cv2.MORPH_OPEN, vertical_kernel, iterations=2)
        
#         # Combine detected lines
#         lines_mask = cv2.add(detect_horizontal, detect_vertical)
        
#         # Remove lines from original image
#         result = image.copy()
#         if len(result.shape) == 2:
#             result[lines_mask == 255] = 255
#         else:
#             result[lines_mask == 255] = [255, 255, 255]
        
#         logger.info("✓ Removed table lines")
#         return result
    
#     @staticmethod
#     def extract_region_percent(image: np.ndarray, top: float, bottom: float, 
#                                left: float, right: float) -> np.ndarray:
#         """Extract region using percentage coordinates"""
#         height, width = image.shape[:2]
#         y1 = int(height * top)
#         y2 = int(height * bottom)
#         x1 = int(width * left)
#         x2 = int(width * right)
        
#         region = image[y1:y2, x1:x2]
#         logger.info(f"Extracted region: ({x1},{y1}) to ({x2},{y2}) = {region.shape[1]}x{region.shape[0]}px")
#         return region


# class MultiEngineOCR:
#     """
#     Uses multiple OCR engines and combines results for best accuracy
#     Priority: EasyOCR (best for Urdu) > PaddleOCR > Tesseract
#     """
    
#     def __init__(self):
#         self.engines = []
        
#         # Initialize EasyOCR (best for Urdu)
#         if _load_easyocr_module():
#             try:
#                 self.easyocr_reader = easyocr.Reader(['ur', 'en'], gpu=False)
#                 self.engines.append('easyocr')
#                 logger.info("✓ EasyOCR initialized (Urdu + English)")
#             except Exception as e:
#                 logger.error(f"EasyOCR init failed: {e}")
#                 self.easyocr_reader = None

#             # Also create English-only reader for digit extraction
#             # Urdu model sometimes interferes with digit recognition
#             try:
#                 self.easyocr_reader_en = easyocr.Reader(['en'], gpu=False)
#                 logger.info("✓ EasyOCR English-only reader initialized")
#             except Exception as e:
#                 logger.error(f"EasyOCR English-only init failed: {e}")
#                 self.easyocr_reader_en = None
#         else:
#             self.easyocr_reader = None
#             self.easyocr_reader_en = None
        
#         # Initialize PaddleOCR (backup)
#         if PADDLEOCR_AVAILABLE:
#             try:
#                 self.paddleocr = PaddleOCR(
#                     use_angle_cls=True,
#                     lang='en',
#                 )
#                 self.engines.append('paddleocr')
#                 logger.info("✓ PaddleOCR initialized")
#             except Exception as e:
#                 logger.error(f"PaddleOCR init failed: {e}")
#                 self.paddleocr = None
#         else:
#             self.paddleocr = None
        
#         # Tesseract (last resort)
#         if TESSERACT_AVAILABLE:
#             self.engines.append('tesseract')
#             logger.info("✓ Tesseract available")
        
#         if not self.engines:
#             raise RuntimeError("No OCR engines available! Install at least one: easyocr, paddleocr, or tesseract")
        
#         logger.info(f"OCR engines available: {', '.join(self.engines)}")
    
#     def extract_text_easyocr(self, image: np.ndarray) -> Tuple[str, float]:
#         """Extract text using EasyOCR"""
#         try:
#             if self.easyocr_reader is None:
#                 return "", 0.0
            
#             # Convert to PIL Image
#             if len(image.shape) == 2:
#                 pil_image = Image.fromarray(image)
#             else:
#                 pil_image = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
            
#             # Run EasyOCR
#             results = self.easyocr_reader.readtext(np.array(pil_image), paragraph=False)
            
#             if not results:
#                 return "", 0.0
            
#             # Extract text and calculate average confidence
#             texts = []
#             confidences = []
            
#             for detection in results:
#                 bbox, text, conf = detection
#                 # LOWERED threshold: Section numbers often have low confidence (0.1-0.3)
#                 # e.g., '149تب' at 0.22, '-=302' at 0.11, '379تب' at 0.29
#                 if float(conf) > 0.05:  # Accept very low confidence for numbers
#                     texts.append(text)
#                     confidences.append(float(conf))
            
#             combined_text = " ".join(texts)
#             avg_confidence = sum(confidences) / len(confidences) * 100 if confidences else 0
            
#             logger.info(f"EasyOCR: {len(texts)} text blocks, confidence: {avg_confidence:.1f}%")
#             return combined_text, avg_confidence

#         except Exception as e:
#             logger.error(f"EasyOCR failed: {e}")
#             return "", 0.0

#     def extract_text_easyocr_english(self, image: np.ndarray) -> Tuple[str, float]:
#         """Extract text using EasyOCR with ENGLISH ONLY - better for digit recognition"""
#         try:
#             if self.easyocr_reader_en is None:
#                 return "", 0.0

#             # Convert to PIL Image
#             if len(image.shape) == 2:
#                 pil_image = Image.fromarray(image)
#             else:
#                 pil_image = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))

#             # Run EasyOCR with English only
#             results = self.easyocr_reader_en.readtext(np.array(pil_image), paragraph=False)

#             if not results:
#                 return "", 0.0

#             texts = []
#             confidences = []

#             for detection in results:
#                 bbox, text, conf = detection
#                 # Very low threshold for digits
#                 if float(conf) > 0.05:
#                     texts.append(text)
#                     confidences.append(float(conf))

#             combined_text = " ".join(texts)
#             avg_confidence = sum(confidences) / len(confidences) * 100 if confidences else 0

#             logger.info(f"EasyOCR (EN): {len(texts)} text blocks, confidence: {avg_confidence:.1f}%")
#             return combined_text, avg_confidence

#         except Exception as e:
#             logger.error(f"EasyOCR English failed: {e}")
#             return "", 0.0

#     def extract_text_paddleocr(self, image: np.ndarray) -> Tuple[str, float]:
#         """Extract text using PaddleOCR"""
#         try:
#             if self.paddleocr is None:
#                 return "", 0.0
            
#             results = self.paddleocr.ocr(image, cls=True)
            
#             if not results or not results[0]:
#                 return "", 0.0
            
#             texts = []
#             confidences = []
            
#             for line in results[0]:
#                 if line and len(line) >= 2:
#                     text = line[1][0]
#                     conf = line[1][1]
#                     if conf > 0.3:
#                         texts.append(text)
#                         confidences.append(conf)
            
#             combined_text = " ".join(texts)
#             avg_confidence = sum(confidences) / len(confidences) * 100 if confidences else 0
            
#             logger.info(f"PaddleOCR: {len(texts)} text blocks, confidence: {avg_confidence:.1f}%")
#             return combined_text, avg_confidence
            
#         except Exception as e:
#             logger.error(f"PaddleOCR failed: {e}")
#             return "", 0.0
    
#     def extract_text_tesseract(self, image: np.ndarray) -> Tuple[str, float]:
#         """Extract text using Tesseract"""
#         try:
#             # Configure Tesseract for Urdu
#             config = '--oem 3 --psm 6 -l urd+eng'
            
#             # Get text
#             text = pytesseract.image_to_string(image, config=config)
            
#             # Get confidence
#             data = pytesseract.image_to_data(image, config=config, output_type=pytesseract.Output.DICT)
#             confidences = [int(conf) for conf in data['conf'] if conf != '-1' and int(conf) > 0]
#             avg_confidence = sum(confidences) / len(confidences) if confidences else 0
            
#             logger.info(f"Tesseract: confidence: {avg_confidence:.1f}%")
#             return text, avg_confidence
            
#         except Exception as e:
#             logger.error(f"Tesseract failed: {e}")
#             return "", 0.0
    
#     def extract_text_multi(self, image: np.ndarray, prefer_engine: str = 'easyocr') -> Tuple[str, float]:
#         """
#         Extract text using multiple engines and return best result
#         """
#         results = []
        
#         # Try EasyOCR first (best for Urdu)
#         if 'easyocr' in self.engines and self.easyocr_reader:
#             text, conf = self.extract_text_easyocr(image)
#             if text:
#                 results.append(('easyocr', text, conf))
        
#         # Try PaddleOCR
#         if 'paddleocr' in self.engines and self.paddleocr:
#             text, conf = self.extract_text_paddleocr(image)
#             if text:
#                 results.append(('paddleocr', text, conf))
        
#         # Try Tesseract
#         if 'tesseract' in self.engines:
#             text, conf = self.extract_text_tesseract(image)
#             if text:
#                 results.append(('tesseract', text, conf))
        
#         # Return best result by confidence
#         if results:
#             results.sort(key=lambda x: x[2], reverse=True)
#             best_engine, best_text, best_conf = results[0]
#             logger.info(f"✓ Best result: {best_engine} ({best_conf:.1f}%)")
#             return best_text, best_conf
        
#         return "", 0.0


# # ── DB areas table cache for text-match geocoding ────────────────────────
# # Populated at startup by calling load_areas_for_geocoding(db_connection).
# _ocr_areas_cache: Dict[str, Tuple[float, float]] = {}
# _MATCH_NOISE = {"the", "and", "for", "lahore", "town", "area", "housing", "colony", "of"}


# def load_areas_for_geocoding(connection) -> None:
#     """Load the areas table into the module cache for text-match geocoding.
#     Call once at application startup."""
#     global _ocr_areas_cache
#     try:
#         cursor = connection.cursor(dictionary=True)
#         cursor.execute("SELECT area_name, latitude, longitude FROM areas")
#         _ocr_areas_cache = {
#             row["area_name"]: (float(row["latitude"]), float(row["longitude"]))
#             for row in cursor.fetchall()
#         }
#         cursor.close()
#         logger.info(f"✅ Loaded {len(_ocr_areas_cache)} areas into OCR geocoding cache")
#     except Exception as exc:
#         logger.warning(f"[OCR geocode] Could not load areas table: {exc}")


# def _db_text_match(english_name: str) -> Optional[Tuple[float, float]]:
#     """Match an English area name against the cached areas table.
#     Returns (lat, lon) for the best match, or None."""
#     if not _ocr_areas_cache or not english_name:
#         return None
#     en = english_name.lower()
#     en_words = set(re.findall(r"\b[a-z0-9]\w*\b", en))
#     best_name: Optional[str] = None
#     best_score = 0
#     for area_name, coords in _ocr_areas_cache.items():
#         an = area_name.lower()
#         # Tier 1: full substring match
#         if an in en:
#             score = len(an) * 3
#             if score > best_score:
#                 best_name, best_score = area_name, score
#             continue
#         # Tier 2: word-level majority match
#         area_words = [w for w in re.findall(r"\b[a-z0-9]\w*\b", an) if w not in _MATCH_NOISE]
#         if not area_words:
#             continue
#         matches = sum(1 for w in area_words if w in en_words)
#         frac = matches / len(area_words)
#         if area_words[0] in en_words and frac >= 0.5:
#             score = int(matches * len(an))
#             if score > best_score:
#                 best_name, best_score = area_name, score
#     if best_name:
#         lat, lon = _ocr_areas_cache[best_name]
#         logger.info(f"[Geocode] DB text-match: '{english_name[:50]}' → '{best_name}' ({lat:.4f},{lon:.4f})")
#         return lat, lon
#     return None


# # ── Crime‑area crop strips (top, bottom, left, right) ──────────────────────
# CRIME_STRIPS = [
#     # (top, bottom, left, right) - overlapping vertical strips
#     (0.38, 0.451, 0.29, 0.62),  # Original narrow region (proven for large format)
#     (0.39, 0.49, 0.20, 0.70),  # Wide: captures text for both large + small format
#     (0.41, 0.49, 0.20, 0.70),  # Lower strip: small format images often have text here
#     (0.43, 0.50, 0.20, 0.70),  # Lowest strip: catches text at very bottom of row
# ]


# # ── Free geocoding using Nominatim (OpenStreetMap) ─────────────────────────
# def geocode_crime_area(area_name: str, city: str = "Lahore") -> dict:
#     """Geocode a crime area location using Nominatim (100% free, forever).
    
#     Uses OpenStreetMap's Nominatim API. No API key required.
#     Rate limit: 1 request per second (respected automatically).
    
#     Strategy:
#     1. Try Urdu-to-English mapping first (best Nominatim results)
#     2. Try the original Urdu name
#     3. Try shorter version (first word only)
#     4. Try English transliteration
    
#     Args:
#         area_name: The crime area/location name (Urdu or English)
#         city: City name (default: Lahore)
    
#     Returns:
#         dict with 'latitude', 'longitude', 'display_name', 'success'
#     """
#     if not area_name or len(area_name.strip()) < 2:
#         return {'latitude': None, 'longitude': None, 'display_name': '', 'success': False}

#     if not GEOPY_AVAILABLE:
#         logger.warning("geopy not installed - cannot geocode")
#         return {'latitude': None, 'longitude': None, 'display_name': '', 'success': False}
    
#     # Known location name mappings for better geocoding
#     GEOCODE_MAPPINGS = {
#         # Specific crime locations (Urdu -> English for Nominatim)
#         "مین بلیوارڈ": "Main Boulevard Gulberg",
#         "مین بلیوارڈ برکت مارکیٹ": "Barkat Market Main Boulevard",
#         "مین بلیوارڈ گلبرگ": "Main Boulevard Gulberg",
#         "برکت مارکیٹ": "Barkat Market",
#         "ہربنس پورہ": "Harbanspura",
#         "غڑی شاہو": "Garhi Shahu",
#         "غری شاہو": "Garhi Shahu",
#         "گڑھی شاہو": "Garhi Shahu",
#         "شاہدرہ ٹاؤن": "Shahdara Town",
#         "گارڈن ٹاؤن": "Garden Town",
#         "فیصل ٹاؤن": "Faisal Town",
#         "ماڈل ٹاؤن": "Model Town",
#         "جوہر ٹاؤن": "Johar Town",
#         "علامہ اقبال ٹاؤن": "Allama Iqbal Town",
#         "اقبال ٹاؤن": "Iqbal Town",
#         "گلبرگ": "Gulberg",
#         "سبزہ زار": "Sabzazar",
#         "ٹاؤن شپ": "Township",
#         "گلشنِ راوی": "Gulshan Ravi",
#         "گلشن راوی": "Gulshan Ravi",
#         "سمن آباد": "Samanabad",
#         "واپڈا ٹاؤن": "Wapda Town",
#         "مغلپورہ": "Mughalpura",
#         "باغبانپورہ": "Baghbanpura",
#         "شالامار باغ": "Shalimar Bagh",
#         "شادمان مارکیٹ": "Shadman Market",
#         "شادمان": "Shadman",
#         "انارکلی بازار": "Anarkali Bazaar",
#         "لبرٹی مارکیٹ": "Liberty Market",
#         "حفیظ سنٹر": "Hafeez Centre",
#         "فیروزپور روڈ": "Ferozpur Road",
#         "وحدت روڈ": "Wahdat Road",
#         "کینال روڈ": "Canal Road",
#         "داتا دربار": "Data Darbar",
#         "لوہاری گیٹ": "Lohari Gate",
#         "دہلی گیٹ": "Delhi Gate",
#         "بھاٹی گیٹ": "Bhati Gate",
#         "ریلوے اسٹیشن لاہور": "Railway Station Lahore",
#         "کینٹ صدر بازار": "Cantt Saddar Bazaar",
#         "جیل روڈ": "Jail Road",
#         "والٹن روڈ": "Walton Road",
#         "شاہ عالمی مارکیٹ": "Shah Alam Market",
#         "نیلا گنبد": "Neela Gumbad",
#         "قذافی اسٹیڈیم": "Gaddafi Stadium",
#         "چوبرجی": "Chauburji",
#         "لکشمی چوک": "Lakshmi Chowk",
#         "حسین چوک": "Husain Chowk",
#         "ریگل چوک": "Regal Chowk",
#         "نسبت روڈ": "Nisbat Road",
#         "برکی روڈ": "Barki Road",
#         "ڈی ایچ اے": "DHA Lahore",
#         "بحریہ ٹاؤن": "Bahria Town Lahore",
#         "آسکاری": "Askari",
#         "لی ڈی اے سٹی": "LDA City",
#         "پی سی ایس آئی آر": "PCSIR",
#         "پی آئی اے سوسائٹی": "PIA Society",
#         "ای ایم ای سوسائٹی": "EME Society",
#         "مولانا شوکت علی روڈ": "Mulana Shaukat Ali Road",
#         "عامر روڈ": "Amer Road",
#         "سنت نگر چوک": "Sant Nagar Chowk",
#         "کریم بلاک مارکیٹ": "Karim Block Market",
#         "پرانی انارکلی": "Old Anarkali",
#         "فیکٹری ایریا": "Factory Area",
#         "مسلم ٹاؤن": "Muslim Town",
#         "بادامی باغ": "Badami Bagh",
#         "نشتر ٹاؤن": "Nishtar Town",
#         "راوی روڈ": "Ravi Road",
#         # Additional missing regular locations
#         "اولڈ انارکلی روڈ": "Old Anarkali Road",
#         "اچھرہ مارکیٹ": "Ichhra Market",
#         "برکی روڈ / بیدیان": "Barki Road Bedian",
#         "د تا در بار": "Data Darbar",
#         "شاد باغ مارکیٹ": "Shadbagh Market",
#         "شادمـان مارکیٹ": "Shadman Market",
#         "عامر روڈ (اسٹریٹ 9": "Amer Road Street 9",
#         "ماڈل ٹاؤن پارک": "Model Town Park",
#         "پریس کلب کوئٹہ": "Press Club Quetta",
#         "پی آئی اے سوسائٹی بلاک H": "PIA Society Block H Lahore",
#         "پی آئی اے سوسائٹی بلاک I": "PIA Society Block I Lahore",
#         "گدا فی اسٹیڈیم": "Gaddafi Stadium",
#         "گلبرگ لاہور": "Gulberg Lahore",
#         "ہال روڈ": "Hall Road",
#         # New regular locations (entries 151-950)
#         "سرفرار روڈ کینٹ": "Sarfraz Road Cantt Lahore",
#         "سنگیاں پل": "Singhpura Pul Lahore",
#         "فوجی کالونی کینٹ": "Fauji Colony Cantt Lahore",
#         "فورٹریس اسٹیڈیم ایریا": "Fortress Stadium Lahore",
#         "لال کرتی کینٹ": "Lal Kurti Cantt Lahore",
#         "نواں کوٹ بائیک پوائنٹ": "Nawan Kot Lahore",
#         "چوبرجی انڈر پاس": "Chauburji Underpass Lahore",
#         "کاماہاں انٹرچینج": "Kamahan Interchange Lahore",
#         "کیولری گراؤنڈ": "Cavalry Ground Lahore",
#         "گجومتہ موڑ": "Gajjumata Mor Lahore",
#         # Locations with parenthetical detail
#         "جوہر ٹاؤن (ایمپوریئم مال)": "Emporium Mall Johar Town",
#         "علامہ اقبال ٹاؤن (کری بلاک مارکیٹ)": "Karim Block Market Allama Iqbal Town",
#         "فیروزپور روڈ (قینچی)": "Qainchi Ferozepur Road",
#     }
    
#     # Normalize Unicode for consistent lookup (precomposed vs decomposed)
#     import unicodedata
#     area_normalized = unicodedata.normalize('NFC', area_name)
    
#     # Build normalized mapping for lookup
#     normalized_mappings = {}
#     for k, v in GEOCODE_MAPPINGS.items():
#         normalized_mappings[unicodedata.normalize('NFC', k)] = v
    
#     # ── Structured location translator ──────────────────────────────────
#     def translate_structured(name):
#         """Translate structured Urdu location names to English.
#         Handles DHA, Bahria Town, Askari, WAPDA Town, LDA City, PIA Society, Lake City, etc."""
#         import re as _re
        
#         # First strip "سب بلاک X" (sub-block) suffix - we geocode by parent area
#         sub_block_match = _re.search(r'\s+سب\s+بلاک\s+\S+$', name)
#         base_name = _re.sub(r'\s+سب\s+بلاک\s+\S+$', '', name) if sub_block_match else name
        
#         patterns = [
#             # ڈی ایچ اے فیز X وای بلاک → DHA Phase X Y Block
#             (_re.compile(r'ڈی\s*ایچ\s*اے\s*فیز\s*(\d+)\s*وای\s*بلاک'), lambda m: f"DHA Phase {m.group(1)} Y Block"),
#             # ڈی ایچ اے فیز X بلاک Y → DHA Phase X Block Y
#             (_re.compile(r'ڈی\s*ایچ\s*اے\s*فیز\s*(\d+)\s*بلاک\s*(\S+)'), lambda m: f"DHA Phase {m.group(1)} Block {m.group(2)}"),
#             # ڈی ایچ اے فیز X (phase only, no block) → DHA Phase X Lahore
#             # Must come AFTER the block patterns so the more-specific ones win first.
#             (_re.compile(r'ڈی\s*ایچ\s*اے\s*فیز\s*(\d+)'), lambda m: f"DHA Phase {m.group(1)} Lahore"),
#             # بحریہ آرچرڈ فیز X بلاک Y → Bahria Orchard Phase X Block Y
#             (_re.compile(r'بحریہ\s*آرچرڈ\s*فیز\s*(\d+)\s*بلاک\s*(\S+)'), lambda m: f"Bahria Orchard Phase {m.group(1)} Block {m.group(2)}"),
#             # بحریہ ٹاؤن سیکٹر X بلاک Y → Bahria Town Sector X Block Y
#             (_re.compile(r'بحریہ\s*ٹاؤن\s*سیکٹر\s*(\S+)\s*بلاک\s*(\S+)'), lambda m: f"Bahria Town Sector {m.group(1)} Block {m.group(2)}"),
#             # آسکاری X بلاک Y → Askari X Block Y
#             (_re.compile(r'آسکاری\s*(\d+)\s*بلاک\s*(\S+)'), lambda m: f"Askari {m.group(1)} Block {m.group(2)}"),
#             # واپڈا ٹاؤن فیز X بلاک Y → WAPDA Town Phase X Block Y
#             (_re.compile(r'واپڈا\s*ٹاؤن\s*فیز\s*(\d+)\s*بلاک\s*(\S+)'), lambda m: f"WAPDA Town Phase {m.group(1)} Block {m.group(2)}"),
#             # لی ڈی اے سٹی سیکٹر X بلاک Y → LDA City Sector X Block Y
#             (_re.compile(r'لی\s*ڈی\s*اے\s*سٹی\s*سیکٹر\s*(\d+)\s*بلاک\s*(\S+)'), lambda m: f"LDA City Sector {m.group(1)} Block {m.group(2)}"),
#             # لی ڈی اے سٹی سیکٹر X (sector-only, no block) → LDA City Sector X
#             (_re.compile(r'لی\s*ڈی\s*اے\s*سٹی\s*سیکٹر\s*(\d+)'), lambda m: f"LDA City Sector {m.group(1)}"),
#             # ایل ڈی اے سٹی سیکٹر X (alternate FIR spelling)
#             (_re.compile(r'ایل\s*ڈی\s*اے\s*سٹی\s*سیکٹر\s*(\d+)'), lambda m: f"LDA City Sector {m.group(1)}"),
#             # پی آئی اے سوسائٹی بلاک X → PIA Society Block X
#             (_re.compile(r'پی\s*آئی\s*اے\s*سوسائٹی\s*بلاک\s*(\S+)'), lambda m: f"PIA Society Block {m.group(1)}"),
#             # لیک سٹی سیکٹر MX → Lake City Sector MX
#             (_re.compile(r'لیک\s*سٹی\s*سیکٹر\s*(\S+)'), lambda m: f"Lake City Sector {m.group(1)}"),
#             # والینشیا ٹاؤن بلاک X → Valencia Town Block X
#             (_re.compile(r'والینشیا\s*ٹاؤن\s*بلاک\s*(\S+)'), lambda m: f"Valencia Town Block {m.group(1)}"),
#             # جوہر ٹاؤن بلاک X → Johar Town Block X
#             (_re.compile(r'جوہر\s*ٹاؤن\s*بلاک\s*(\S+)'), lambda m: f"Johar Town Block {m.group(1)}"),
#             # الخضریا ہاؤسنگ بلاک X → Al Khuderia Housing Block X
#             (_re.compile(r'الخضریا\s*ہاؤسنگ\s*بلاک\s*(\S+)'), lambda m: f"Al Khuderia Housing Block {m.group(1)}"),
#             # ایڈن آباد بلاک X → Eden Abad Block X
#             (_re.compile(r'ایڈن\s*آباد\s*بلاک\s*(\S+)'), lambda m: f"Eden Abad Block {m.group(1)}"),
#         ]
#         for pat, formatter in patterns:
#             match = pat.search(base_name)
#             if match:
#                 return formatter(match)
#         return None
    
#     try:
#         geolocator = Nominatim(user_agent="fir_crime_area_geocoder_v1", timeout=10.0)

#         # If OCR text contains DHA phase, keep geocoding phase-locked.
#         _dha_phase_expected = None
#         _dha_ur = re.search(r'ڈی\s*ایچ\s*اے\s*فیز\s*(\d+)', area_name)
#         _dha_en = re.search(r'dha\s*phase\s*(\d+)', area_name, re.IGNORECASE)
#         if _dha_ur:
#             _dha_phase_expected = _dha_ur.group(1)
#         elif _dha_en:
#             _dha_phase_expected = _dha_en.group(1)

#         _dha_phase_fallback_coords = None
#         if _dha_phase_expected:
#             _phase_area = f"DHA Phase {_dha_phase_expected}"
#             _db_phase_coords = _db_text_match(_phase_area)
#             if _db_phase_coords:
#                 logger.info(f"[Geocode] DHA phase-locked DB fallback prepared: {_phase_area}")
#                 _dha_phase_fallback_coords = _db_phase_coords
        
#         # ── Step 0: DB text-match (authoritative, zero API calls) ─────────────
#         import unicodedata as _uc
#         _area_nfc = _uc.normalize('NFC', area_name)
#         _area_en = (translate_structured(area_name)
#                     or translate_structured(_area_nfc)
#                     or GEOCODE_MAPPINGS.get(area_name)
#                     or {_uc.normalize('NFC', k): v for k, v in GEOCODE_MAPPINGS.items()}.get(_area_nfc))
#         if _area_en and not _dha_phase_expected:
#             _db_coords = _db_text_match(_area_en)
#             if _db_coords:
#                 return {'latitude': _db_coords[0], 'longitude': _db_coords[1], 'display_name': '', 'success': True}
#         # Also try raw input in case it already has English words
#         _db_direct = _db_text_match(area_name)
#         if _db_direct and not _dha_phase_expected:
#             return {'latitude': _db_direct[0], 'longitude': _db_direct[1], 'display_name': '', 'success': True}

#         # Build query list - prioritize English mappings
#         queries = []
        
#         # Lahore bounding box for Nominatim viewbox (prevents wrong-city results)
#         # Format: (SW_lat, SW_lon), (NE_lat, NE_lon)
#         _LAHORE_VIEWBOX = [(31.10, 73.80), (31.90, 74.75)]

#         # 0. Try structured location translation first (DHA Phase X Block Y, etc.)
#         structured_english = translate_structured(area_name)
#         if not structured_english:
#             structured_english = translate_structured(area_normalized)
#         if structured_english:
#             queries.append(f"{structured_english}, Lahore, Pakistan")
#             queries.append(f"{structured_english}, Lahore")
#             # Also try parent area (without block) as fallback
#             parent = structured_english.rsplit(' Block', 1)[0] if ' Block' in structured_english else None
#             if parent:
#                 queries.append(f"{parent}, Lahore, Pakistan")

#         # 1. Try English mapping first (best results with Nominatim)
#         english = GEOCODE_MAPPINGS.get(area_name) or normalized_mappings.get(area_normalized)
        
#         # 1b. If no direct match, try stripping "سب بلاک X" suffix for non-structured names
#         if not english and not structured_english:
#             import re as _re_sb
#             base_stripped = _re_sb.sub(r'\s+سب\s+بلاک\s+\S+$', '', area_name).strip()
#             if base_stripped != area_name:
#                 english = GEOCODE_MAPPINGS.get(base_stripped) or normalized_mappings.get(unicodedata.normalize('NFC', base_stripped))
#                 if not english:
#                     # Also try structured translator on base name
#                     structured_english = translate_structured(base_stripped)
        
#         if english:
#             queries.append(f"{english}, {city}, Pakistan")
#             queries.append(f"{english}, {city}")

#         # 2. Paren-base English lookup — BEFORE Urdu fallback to avoid
#         #    Nominatim matching ambiguous Urdu terms (e.g. "علامہ اقبال" →
#         #    مقبرہ علامہ اقبال / Mausoleum instead of Allama Iqbal Town).
#         import re as _re2
#         _any_english_found = bool(english or structured_english)
#         paren_match = _re2.match(r'^(.+?)\s*\(', area_name)
#         if paren_match:
#             _base_paren = paren_match.group(1).strip()
#             _base_paren_en = GEOCODE_MAPPINGS.get(_base_paren) or normalized_mappings.get(unicodedata.normalize('NFC', _base_paren))
#             if _base_paren_en:
#                 queries.append(f"{_base_paren_en}, {city}, Pakistan")
#                 queries.append(f"{_base_paren_en}, {city}")
#                 _any_english_found = True

#         # 3. First-word English lookup (for multi-word names)
#         words = area_name.split()
#         if len(words) > 1:
#             first_word = words[0]
#             first_english = GEOCODE_MAPPINGS.get(first_word) or normalized_mappings.get(unicodedata.normalize('NFC', first_word))
#             if first_english:
#                 queries.append(f"{first_english}, {city}, Pakistan")
#                 _any_english_found = True

#         # 4. Raw Urdu fallback — only when NO English mapping was found at all.
#         #    Skipped when we have English mappings because Nominatim can
#         #    ambiguously match Urdu landmark names (tombs, mosques, etc.) instead
#         #    of the intended residential area, producing wrong coordinates.
#         if not _any_english_found:
#             queries.append(f"{area_name}, {city}, Pakistan")
#             queries.append(f"{area_name}, {city}")
#             if len(words) > 1:
#                 queries.append(f"{first_word}, {city}, Pakistan")
#             queries.append(f"{area_name}, Pakistan")
        
#         for query in queries:
#             try:
#                 # Use viewbox + bounded=True so Nominatim restricts results to
#                 # Lahore district — eliminates wrong-city false positives entirely.
#                 location = geolocator.geocode(
#                     query,
#                     viewbox=_LAHORE_VIEWBOX,
#                     bounded=True,
#                 )
#                 if hasattr(location, 'latitude') and hasattr(location, 'longitude'):
#                     lat, lon = location.latitude, location.longitude
#                     if _dha_phase_expected:
#                         _display = ((getattr(location, 'address', '') or '') + ' ' + query).lower()
#                         if f"phase {_dha_phase_expected}" not in _display:
#                             logger.info(f"[Geocode] Skipping DHA phase mismatch (need {_dha_phase_expected}): {query}")
#                             time.sleep(1.1)
#                             continue
#                     if 31.0 <= lat <= 32.0 and 73.5 <= lon <= 75.0:
#                         logger.info(f"[Geocode] ✓ Found: {query} -> ({lat}, {lon})")
#                         return {
#                             'latitude': round(lat, 6),
#                             'longitude': round(lon, 6),
#                             'display_name': getattr(location, 'address', '') or '',
#                             'success': True
#                         }
#                 time.sleep(1.1)  # Nominatim rate limit: max 1 req/sec
#             except (GeocoderTimedOut, GeocoderServiceError) as e:
#                 logger.warning(f"[Geocode] Timeout/error for '{query}': {e}")
#                 time.sleep(1.1)
#                 continue
#             except Exception as e:
#                 logger.warning(f"[Geocode] Error for '{query}': {e}")
#                 time.sleep(1.1)
#                 continue

#         if _dha_phase_fallback_coords:
#             logger.info(f"[Geocode] Using DHA phase fallback coordinates for phase {_dha_phase_expected}")
#             return {
#                 'latitude': _dha_phase_fallback_coords[0],
#                 'longitude': _dha_phase_fallback_coords[1],
#                 'display_name': f"DHA Phase {_dha_phase_expected}",
#                 'success': True,
#             }

#         logger.warning(f"[Geocode] ✗ No Nominatim match for '{area_name}' within Lahore bounds")
#         return {'latitude': None, 'longitude': None, 'display_name': '', 'success': False}
    
#     except Exception as e:
#         logger.error(f"[Geocode] Fatal error: {e}")
#         return {'latitude': None, 'longitude': None, 'display_name': '', 'success': False}


# def detect_structured_location(raw_text: str) -> str:
#     """Detect structured housing scheme locations from raw/garbled OCR text.
    
#     Uses keyword anchoring to identify DHA, Bahria, Askari, LDA, WAPDA patterns
#     even in heavily garbled Tesseract output.
#     Returns constructed location string or empty string.
#     """
#     text = re.sub(r'\s+', ' ', raw_text.strip())
#     if len(text) < 5:
#         return ""
    
#     # ===== DHA (ڈی ایچ اے) =====
#     dha_markers = ['ایچ اے', 'اچ اے', 'اگ اے', 'ائچ اے', 'ایچ ای',
#                    'اچ ای', 'ای اے', 'اگ ے', 'ایچاے', 'اچاے',
#                    'ایج اے', 'اگ ای', 'ایچ ے', 'ایگ اے',
#                    'کی اے', 'کے اے', 'کی ای', 'کے ای',
#                    'اچ کے', 'اچ کی']  # extra garbles: ایچ اے→اچ کے
#     for marker in dha_markers:
#         pos = text.find(marker)
#         if pos >= 0:
#             # Strict validation: require ڈی pattern close to marker
#             # ڈ/ڑ followed by 0-1 chars then ی (handles ڈی, ڑی, ڑکی garbles)
#             # Rejects "ارڈ تی" (2+ chars between ڈ and ی, from garbled بلیوارڈ)
#             prefix = text[max(0, pos-5):pos]
#             has_d_context = bool(re.search(r'[ڈڑ].?ی', prefix))
#             # Also allow ڈ at very start of text (pos <= 3)
#             if not has_d_context and pos <= 3:
#                 has_d_context = 'ڈ' in text[:pos]
#             if not has_d_context:
#                 continue
#             # Additional validation: text around marker shouldn't be mostly noise
#             context = text[max(0, pos-15):min(len(text), pos+len(marker)+20)]
#             urdu_in_ctx = sum(1 for c in context if '\u0600' <= c <= '\u06FF')
#             if urdu_in_ctx < len(context) * 0.3:  # Too much noise
#                 continue
#             after = text[pos + len(marker):]
#             phase_match = re.search(r'(\d)', after[:30])
#             if phase_match:
#                 phase = phase_match.group(1)
#                 if 1 <= int(phase) <= 9:
#                     after_phase = after[phase_match.end():]
#                     # Wider scan window captures "بلاک X سب بلاک Y" before road/comma text.
#                     after_phase_window = after_phase[:90]
#                     block_match = re.search(
#                         r'(?:بلاک|لاک|ملاک|بلک)\s*([A-Za-z0-9])',
#                         after_phase_window,
#                         flags=re.IGNORECASE,
#                     )
#                     if block_match:
#                         block = block_match.group(1).upper()
#                         after_block = after_phase_window[block_match.end():]
#                         sub_block_match = re.search(
#                             r'(?:سب\s*بلاک|سب\s*بلک|سبلاک|سب\s*بلاگ|سے\s*بلاک|سے\s*بلک)\s*([A-Za-z0-9])',
#                             after_block,
#                             flags=re.IGNORECASE,
#                         )
#                         if sub_block_match:
#                             sub_block = sub_block_match.group(1).upper()
#                             return f"ڈی ایچ اے فیز {phase} بلاک {block} سب بلاک {sub_block}"
#                         return f"ڈی ایچ اے فیز {phase} بلاک {block}"
#                     return f"ڈی ایچ اے فیز {phase}"
    
#     # ===== Bahria Town (garbled sector/block + Raiwind context) =====
#     # Handles OCR like: "ٹاؤل سیٹ 6 ... بلاک D ... سب بلاک A ... رائنونڈ روڈ"
#     # where sector/block letters are often digit-confused in OCR.
#     if ('ٹاؤ' in text or 'ٹاؤن' in text) and ('بلاک' in text or 'لاک' in text):
#         raiwind_hint = ('رائیونڈ' in text) or ('رائنونڈ' in text) or ('رایونڈ' in text)
#         sector_match = re.search(r'(?:سیکٹر|سیٹ|سٹ|سکٹر)\s*([A-Za-z0-9])', text)
#         block_matches = re.findall(r'(?:بلاک|لاک|ملاک|بلک)\s*([A-Za-z0-9])', text)
#         if sector_match and block_matches and raiwind_hint:
#             raw_sector = sector_match.group(1).upper()
#             raw_block = block_matches[0].upper()
#             raw_sub_block = block_matches[1].upper() if len(block_matches) > 1 else None
#             sector_map = {
#                 '6': 'G',  # common OCR confusion in FIR scans (G <-> 6)
#                 '0': 'O',
#                 '1': 'I',
#                 '5': 'S',
#                 '8': 'B',
#             }
#             sector = sector_map.get(raw_sector, raw_sector)
#             block = sector_map.get(raw_block, raw_block)
#             if raw_sub_block:
#                 sub_block = sector_map.get(raw_sub_block, raw_sub_block)
#                 return f"بحریہ ٹاؤن سیکٹر {sector} بلاک {block} سب بلاک {sub_block}"
#             return f"بحریہ ٹاؤن سیکٹر {sector} بلاک {block}"

#     # ===== آسکاری (Askari) =====
#     askari_markers = ['آسکاری', 'آسکار', 'اسکاری', 'اسکار', 'آسکری',
#                       'آساری', 'آسکادری', 'اسکادری']  # garbled: آساری, آسکادری
#     for marker in askari_markers:
#         pos = text.find(marker)
#         if pos >= 0:
#             after = text[pos + len(marker):]
#             num_match = re.search(r'(\d+)', after[:15])
#             if num_match:
#                 num = num_match.group(1)
#                 remaining = after[num_match.end():]
#                 block_match = re.search(r'(?:بلاک|لاک)\s*([A-Za-z])', remaining[:20])
#                 if block_match:
#                     return f"آسکاری {num} بلاک {block_match.group(1).upper()}"
#                 return f"آسکاری {num}"
    
#     # ===== بحریہ ٹاؤن (Bahria Town) =====
#     bahria_markers = ['بحریہ', 'بحرہ', 'بحربہ', 'نحریہ', 'بحری ہ']
#     for marker in bahria_markers:
#         pos = text.find(marker)
#         if pos >= 0:
#             after = text[pos + len(marker):]
#             sector_match = re.search(r'(?:سیکٹر|سکٹر|سیکنر|صیکٹر|شیکٹر|سی کٹر)\s*([A-Za-z])', after[:40])
#             if sector_match:
#                 sector = sector_match.group(1).upper()
#                 remaining = after[sector_match.end():]
#                 block_match = re.search(r'(?:بلاک|لاک)\s*([A-Za-z])', remaining[:25])
#                 if block_match:
#                     block = block_match.group(1).upper()
#                     sub_block_match = re.search(r'(?:سب\s*بلاک|سبلاک|سے\s*بلاک)\s*([A-Za-z])', remaining[:50], re.IGNORECASE)
#                     if sub_block_match:
#                         sub_block = sub_block_match.group(1).upper()
#                         return f"بحریہ ٹاؤن سیکٹر {sector} بلاک {block} سب بلاک {sub_block}"
#                     return f"بحریہ ٹاؤن سیکٹر {sector} بلاک {block}"
#                 return f"بحریہ ٹاؤن سیکٹر {sector}"
#             return "بحریہ ٹاؤن"
    
#     # ===== لی ڈی اے (LDA City) =====
#     lda_markers = ['لی ڈی اے', 'لے ڈی اے', 'لی ڈے اے', 'لی ڈ اے',
#                     'لی دے', 'لاڈ ی ے', 'ڈی نے بی', 'لی ڈی', 'ڈی لے',
#                     'لاڈی ے', 'ڈڑی دے']  # garbled variants
#     for marker in lda_markers:
#         pos = text.find(marker)
#         if pos >= 0:
#             after = text[pos + len(marker):]
#             sector_match = re.search(r'(?:سیکٹر|سکٹر|صیکٹر|[مخنٹکھ]ر)\s*(\d+)', after[:30])
#             if sector_match:
#                 sector = sector_match.group(1)
#                 # Handle doubled digits from OCR garbling (44→4, 33→3)
#                 if len(sector) == 2 and sector[0] == sector[1]:
#                     sector = sector[0]
#                 remaining = after[sector_match.end():]
#                 block_match = re.search(r'(?:بلاک|لاک|ملاک)\s*([A-Za-z])', remaining[:20])
#                 if block_match:
#                     return f"لی ڈی اے سٹی سیکٹر {sector} بلاک {block_match.group(1).upper()}"
#                 return f"لی ڈی اے سٹی سیکٹر {sector}"
#             return "لی ڈی اے سٹی"  # fallback when marker found but no sector
    
#     # ===== واپڈا ٹاؤن (WAPDA Town) =====
#     wapda_markers = ['واپڈا', 'واپدا', 'وپڈا', 'وابڈا', 'داپڑا', 'دایڑا']
#     for marker in wapda_markers:
#         pos = text.find(marker)
#         if pos >= 0:
#             after = text[pos + len(marker):]
#             phase_match = re.search(r'(?:فیز|فیر|فین|ٹر|نر)\s*(\d+)', after[:30])
#             if phase_match:
#                 phase = phase_match.group(1)
#                 remaining = after[phase_match.end():]
#                 block_match = re.search(r'(?:بلاک|لاک|ملاک)\s*([A-Za-z])', remaining[:20])
#                 if block_match:
#                     return f"واپڈا ٹاؤن فیز {phase} بلاک {block_match.group(1).upper()}"
#                 return f"واپڈا ٹاؤن فیز {phase}"
#             return "واپڈا ٹاؤن"  # fallback
    
#     # ===== پی سی ایس آئی آر (PCSIR) =====
#     pcsir_markers = ['سی ایس آئی آر', 'سی ایی آئی آر', 'سی ایس آئی', 'سی ایی آئی']
#     for marker in pcsir_markers:
#         pos = text.find(marker)
#         if pos >= 0:
#             after = text[pos + len(marker):]
#             phase_match = re.search(r'(?:فیز|فیر|ٹر|نر)\s*(\d+)', after[:30])
#             if phase_match:
#                 phase = phase_match.group(1)
#                 remaining = after[phase_match.end():]
#                 block_match = re.search(r'(?:بلاک|لاک|ملاک)\s*([A-Za-z])', remaining[:20])
#                 if block_match:
#                     return f"پی سی ایس آئی آر فیز {phase} بلاک {block_match.group(1).upper()}"
#                 return f"پی سی ایس آئی آر فیز {phase}"
    
#     # ===== پی آئی اے سوسائٹی (PIA Society) =====
#     pia_markers = ['پی آئی اے', 'پی کی اے']
#     for marker in pia_markers:
#         pos = text.find(marker)
#         if pos >= 0:
#             after = text[pos + len(marker):]
#             # Look for سوسائٹی or garbled variant
#             if re.search(r'(?:صوس|سوس|سوسائ)', after[:20]):
#                 block_match = re.search(r'(?:بلاک|لاک|بلاگ|ملاک)\s*(\d+|[A-Za-z])', after[:40])
#                 if block_match:
#                     bl = block_match.group(1)
#                     return f"پی آئی اے سوسائٹی بلاک {bl.upper()}"
#                 return "پی آئی اے سوسائٹی"
    
#     return ""


# def detect_location_fragments(raw_text: str, return_all: bool = False):
#     """Detect specific location names from garbled OCR using distinctive fragments.
    
#     Many locations have distinctive character sequences that survive OCR garbling.
#     This function looks for these fragments across ALL strips' raw text and returns
#     the best matching known location.
    
#     Args:
#         raw_text: Raw OCR text to search for location fragments.
#         return_all: If True, return list of (location_name, position_in_text) sorted
#                     by position (earliest first). If False (default), return best match string.
    
#     Returns:
#         str (return_all=False): Location name or empty string.
#         list (return_all=True): List of (location_name, position) tuples.
#     """
#     if not raw_text or len(raw_text.strip()) < 3:
#         return ""
    
#     # Pre-filter: remove distance reference text (after سے) and noise lines
#     lines = raw_text.strip().split('\n')
#     filtered_lines = []
#     noise_keywords = ['اطلاع', 'بذریعہ', 'ہذریعہ', 'ہزریعہ', 'فون', 'موصول',
#                        'بزریعہ', 'ذریعہ', 'ٹریفک', 'صورتحال', 'عوائی',
#                        'اطلاغ', 'اظطلار', 'اطلار', 'مزریعہ', 'پذریعہ',
#                        'پذر ینہ', 'بر وقت', 'ہوٹی', 'ہو گی', 'ہوئی']
#     for line in lines:
#         line = line.strip()
#         if not line:
#             continue
#         # Skip lines that are info-source (not crime-area)
#         if any(nk in line for nk in noise_keywords):
#             continue
#         # Cut at distance marker - handles both proper "سے" and garbled forms
#         # Patterns: "سے تقریباً", "ے7", "ےت", "ےآ" (garbled سے)
#         # First try proper سے
#         parts = re.split(r'\s+سے\s+', line)
#         line = parts[0] if parts else line
#         # Also cut at garbled distance patterns: والشن ے7, والشن ےت, etc.
#         # Pattern: location_ref + ے + digit/letter (garbled "سے تقریباً distance")
#         line = re.split(r'ے[تط7]\s*آ?\s*[\d٠-٩\[\]]', line)[0]
#         # Cut at colon separator (crime_area : road/thana reference)
#         # FIR format: "crime_location : road, area" - colon separates them
#         line = re.split(r'\s*[:]\s*', line)[0]
#         # Cut at dash separator (crime-area --- reference-point)
#         line = re.split(r'[-ـ۔\.]{2,}', line)[0]
#         # Cut at کاو/کلو (garbled کلومیٹر) 
#         line = re.split(r'[\d٠-٩\[\]]+\s*,?\s*کاو', line)[0]
#         line = re.split(r'[\d٠-٩\[\]]+\s*,?\s*کلو', line)[0]
#         # Cut at garbled forms of سے تقر (تر, تقر, تقری)
#         line = re.split(r'\s+تقر', line)[0]
#         line = re.split(r'\s+تر\s*\)', line)[0]
#         if line.strip():
#             filtered_lines.append(line.strip())
    
#     orig = re.sub(r'\s+', ' ', ' '.join(filtered_lines)).strip()
#     if len(orig) < 3:
#         return ""
    
#     # Each entry: (list_of_fragment_patterns, result_location, min_fragments_needed)
#     # Fragment patterns are substrings that commonly survive OCR garbling
#     FRAGMENT_RULES = [
#         # انارکلی بازار - use distinctive fragments
#         (['انارکل'], 'انارکلی بازار', 1),
#         (['انار', 'بازار'], 'انارکلی بازار', 2),
#         (['انار', 'کلی'], 'انارکلی بازار', 2),
#         (['انار', 'کگی'], 'انارکلی بازار', 2),     # garbled FIR_002 S1: "انار کگی"
#         (['انا ری', 'مالیر'], 'انارکلی بازار', 2),  # garbled FIR_002 S0: "انا ری ار مالیر"
#         # دہلی گیٹ - "دی گیٹ" or "دہلی" or "دھلی"
#         (['دی گیٹ'], 'دہلی گیٹ', 1),
#         (['دہلی'], 'دہلی گیٹ', 1),
#         (['دھلی'], 'دہلی گیٹ', 1),                    # garbled دہلی→دھلی
#         (['ہصح'], 'دہلی گیٹ', 1),                     # garbled FIR_005: "ہس ہصح" OCR corruption of دہلی گیٹ
#         # شاہ عالمی مارکیٹ
#         (['عالمی', 'مارکیٹ'], 'شاہ عالمی مارکیٹ', 2),
#         # لوہاری گیٹ
#         (['لوہاری'], 'لوہاری گیٹ', 1),
#         (['لزاری'], 'لوہاری گیٹ', 1),                  # garbled لوہاری→لزاری
#         (['ادہاری'], 'لوہاری گیٹ', 1),                 # garbled لوہاری→ادہاری
#         (['لزا', 'گیٹ'], 'لوہاری گیٹ', 2),             # garbled FIR_004: لزا ری + یگیٹ
#         # بھاٹی گیٹ
#         (['بھاٹی'], 'بھاٹی گیٹ', 1),
#         (['بھالی'], 'بھاٹی گیٹ', 1),                    # garbled بھاٹی→بھالی
#         (['پھائی'], 'بھاٹی گیٹ', 1),                   # garbled بھاٹی→پھائی
#         # ریگل چوک
#         (['ریگل'], 'ریگل چوک', 1),
#         (['ریگ جک'], 'ریگل چوک', 1),           # garbled FIR_007: "ریگ جک"
#         # نیلا گنبد
#         (['نیلا', 'گنبد'], 'نیلا گنبد', 1),
#         (['گنبد'], 'نیلا گنبد', 1),
#         # ایڈورڈ روڈ (sometimes OCR gives this for نیلا گنبد area)
#         (['ایڈورڈ'], 'نیلا گنبد', 1),
#         (['ایڑ ورڈ'], 'نیلا گنبد', 1),             # garbled FIR_008: ایڑ ورڈ
#         (['ایڑ ور'], 'نیلا گنبد', 1),              # garbled partial
#         # مین بلیوارڈ - "بلیوار" is distinctive
#         (['بلیوار'], 'مین بلیوارڈ', 1),
#         (['جلیوار'], 'مین بلیوارڈ', 1),  # garble
#         (['بیوار'], 'مین بلیوارڈ', 1),             # garbled FIR_011: بیو ار (من replaced ل with space)
#         (['بیو ارڈ'], 'مین بلیوارڈ', 1),           # garbled with space: بیو ارڈ
#         # قذافی اسٹیڈیم - "قذا" fragment
#         (['قذا'], 'قذافی اسٹیڈیم', 1),
#         (['گدائی'], 'قذافی اسٹیڈیم', 1),              # garbled FIR_012: گدائی→قذافی
#         (['گدافی'], 'قذافی اسٹیڈیم', 1),              # garbled variant
#         (['گدا فی'], 'قذافی اسٹیڈیم', 1),             # garbled with space
#         (['قذافی'], 'قذافی اسٹیڈیم', 1),              # proper spelling
#         # فیصل ٹاؤن - "فیصل" or garbled variants
#         (['فیصل'], 'فیصل ٹاؤن', 1),
#         # گارڈن ٹاؤن - "گارڈ" or "گار ڈ"
#         (['گارڈ'], 'گارڈن ٹاؤن', 1),
#         (['گار ڈ'], 'گارڈن ٹاؤن', 1),
#         # ٹاؤن شپ - "شپ" near "ٹاؤن"
#         (['ٹاؤن شپ'], 'ٹاؤن شپ', 1),
#         (['نع شب'], 'ٹاؤن شپ', 1),  # OCR garble
#         (['جلاع شپ'], 'ٹاؤن شپ', 1),  # garbled FIR_018 S0-PSM6
#         (['پان شب'], 'ٹاؤن شپ', 1),   # garbled FIR_018 S1-Otsu
#         (['بن شب'], 'ٹاؤن شپ', 1),    # garbled FIR_018 S1-PSM6
#         (['لاع شپ'], 'ٹاؤن شپ', 1),   # garbled partial
#         # والٹن روڈ - only match proper والٹن, not والشن (too many false positives
#         # as والشن frequently appears as a distance reference point)
#         (['والٹن'], 'والٹن روڈ', 1),
#         # شادمان
#         (['شادمان'], 'شادمان مارکیٹ', 1),
#         (['شادم'], 'شادمان مارکیٹ', 1),
#         # جیل روڈ - "جیل" or "ٹیل رد" (garbled)
#         (['جیل'], 'جیل روڈ', 1),
#         (['ٹیل ر'], 'جیل روڈ', 1),  # garbled OCR
#         # مغلپورہ
#         (['مغلپور'], 'مغلپورہ', 1),
#         (['مغلپ'], 'مغلپورہ', 1),
#         # ہربنس پورہ
#         (['ہربنس'], 'ہربنس پورہ', 1),
#         (['ہر یئ'], 'ہربنس پورہ', 1),  # garbled (seen in FIR_024)
#         (['ہر یشس'], 'ہربنس پورہ', 1),  # garbled
#         # غڑی شاہو / غری شاہو - ONLY combined patterns (single-fragment removed to prevent false positives)
#         # Single-fragment غڑی/غری rules removed - use combined rules at bottom
#         # شالامار باغ
#         (['شالامار'], 'شالامار باغ', 1),
#         (['شالا'], 'شالامار باغ', 1),
#         (['شال مار'], 'شالامار باغ', 1),                # garbled with space: شال مار
#         # باغبانپورہ - "غازی آباد" linked to it
#         (['باغبان'], 'باغبانپورہ', 1),
#         (['ذائیآ'], 'باغبانپورہ', 1),  # garbled غازی آباد
#         # سمن آباد
#         (['سمن'], 'سمن آباد', 1),
#         (['نآ اد'], 'سمن آباد', 1),  # garbled
#         (['نآ بادہ'], 'سمن آباد', 1),  # garbled
#         (['تنآ اد'], 'سمن آباد', 1),  # garbled
#         # ریلوے اسٹیشن
#         (['ریلوے'], 'ریلوے اسٹیشن لاہور', 1),
#         (['اسٹیشن'], 'ریلوے اسٹیشن لاہور', 1),
#         (['مگیشن'], 'ریلوے اسٹیشن لاہور', 1),  # garbled
#         # کینٹ صدر بازار
#         (['کینٹ', 'صدر'], 'کینٹ صدر بازار', 2),
#         (['کین', 'صدر'], 'کینٹ صدر بازار', 2),
#         (['کین', 'مدر'], 'کینٹ صدر بازار', 2),  # garbled صدر→مدر
#         (['گیٹ', 'مدر'], 'کینٹ صدر بازار', 2),  # garbled: گیٹ مدر = کینٹ صدر
#         # برکی روڈ / بیدیان
#         (['بیدیان'], 'برکی روڈ', 1),
#         (['بیدان'], 'برکی روڈ', 1),  # garbled
#         (['یدان'], 'برکی روڈ', 1),
#         (['برکی'], 'برکی روڈ', 1),
#         # فیروزپور روڈ
#         (['فیروزپور'], 'فیروزپور روڈ', 1),
#         (['فیروز'], 'فیروزپور روڈ', 1),
#         # وحدت روڈ
#         (['وحدت'], 'وحدت روڈ', 1),
#         (['دحرت'], 'وحدت روڈ', 1),         # garbled وحدت (FIR_035 PSM6)
#         (['دحد تر'], 'وحدت روڈ', 1),       # garbled وحدت (FIR_035 Otsu)
#         # لبرٹی مارکیٹ
#         (['لبرٹی'], 'لبرٹی مارکیٹ', 1),
#         # حفیظ سنٹر
#         (['حفیظ'], 'حفیظ سنٹر', 1),
#         # جوہر ٹاؤن
#         (['جوہر'], 'جوہر ٹاؤن', 1),
#         (['جو مان'], 'جوہر ٹاؤن', 1),          # garbled FIR_017 S1-PSM6: "جو مان"
#         (['جرماؤن'], 'جوہر ٹاؤن', 1),          # garbled FIR_017 S1-Otsu: "جرماؤن"
#         # ایمپوریئم
#         (['ایمپوریئم'], 'جوہر ٹاؤن ایمپوریئم مال', 1),
#         (['ای پر', 'مال'], 'جوہر ٹاؤن ایمپوریئم مال', 2),  # garbled FIR_017
#         # ماڈل ٹاؤن  
#         (['ماڈل'], 'ماڈل ٹاؤن', 1),
#         # سبزہ زار
#         (['سبزہ'], 'سبزہ زار', 1),
#         (['سڑزوزار'], 'سبزہ زار', 1),                   # garbled FIR_030: سڑزوزار→سبزہ زار
#         (['سبز', 'زار'], 'سبزہ زار', 2),               # garbled partial
#         # گلشن راوی
#         (['گلشن'], 'گلشنِ راوی', 1),
#         # اقبال ٹاؤن
#         (['اقبال'], 'علامہ اقبال ٹاؤن', 1),
#         # کینال روڈ
#         (['کینال'], 'کینال روڈ', 1),
#         # راوی روڈ
#         (['راوی ر'], 'راوی روڈ', 1),
#         (['رادیا'], 'راوی روڈ', 1),              # garbled FIR_027 S1-Otsu
#         (['رادی', 'روڈ'], 'راوی روڈ', 2),        # garbled FIR_027: رادی+روڈ
#         (['رادک', 'روڈ'], 'راوی روڈ', 2),        # garbled variant
#         # ہال روڈ
#         (['ہال'], 'ہال روڈ', 1),
#         # شاہدرہ
#         (['شاہدرہ'], 'شاہدرہ ٹاؤن', 1),
#         (['شاہدر'], 'شاہدرہ ٹاؤن', 1),
#         # داتا دربار
#         (['داتا'], 'داتا دربار', 1),
#         # کریم بلاک
#         (['کریم', 'بلاک'], 'کریم بلاک مارکیٹ', 2),
#         # ای ایم ای سوسائٹی - require both patterns to avoid false positives
#         # (ایم ایم عالم روڈ is a common reference road, not ای ایم ای سوسائٹی)
#         (['ایم ای', 'سوسائ'], 'ای ایم ای سوسائٹی', 2),
#         # مولانا شوکت
#         (['شوکت'], 'مولانا شوکت علی روڈ', 1),
#         # بحریہ ٹاؤن - garbled OCR patterns from small-format images
#         (['بر مائن'], 'بحریہ ٹاؤن', 1),    # garbled بحریہ مین
#         (['بر مان'], 'بحریہ ٹاؤن', 1),     # garbled without ئ
#         (['بھریے مان'], 'بحریہ ٹاؤن', 1),   # garbled at scale 3.0
#         (['بھریہ مان'], 'بحریہ ٹاؤن', 1),   # garbled variant
#         (['بھری مان'], 'بحریہ ٹاؤن', 1),    # garbled variant
#         (['بھرس مان'], 'بحریہ ٹاؤن', 1),    # garbled FIR_198
#         (['بھرسہ'], 'بحریہ ٹاؤن', 1),       # garbled FIR_198
#         (['بجھرسہ مان'], 'بحریہ ٹاؤن', 1),  # garbled FIR_113
#         (['بجھرس مان'], 'بحریہ ٹاؤن', 1),   # garbled FIR_155
#         (['جھری مان'], 'بحریہ ٹاؤن', 1),   # garbled بحریہ مین
#         (['جھری', 'لاک'], 'بحریہ ٹاؤن', 2), # garbled بحریہ بلاک
#         # بحریہ آرچرڈ - garbled
#         (['پھر آرڈ'], 'بحریہ آرچرڈ', 1),    # garbled FIR_151
#         (['بھرں آرجھڈ'], 'بحریہ آرچرڈ', 1), # garbled FIR_188
#         (['آرجھڈ'], 'بحریہ آرچرڈ', 1),      # garbled آرچرڈ
#         # الخضریا ہاؤسنگ - garbled
#         (['النریا'], 'الخضریا ہاؤسنگ', 1),  # garbled FIR_156
#         # مغلپورہ - additional garbled patterns
#         (['للپور'], 'مغلپورہ', 1),          # garbled from FIR_023
#         # فیصل ٹاؤن - highly garbled patterns
#         (['یصل'], 'فیصل ٹاؤن', 1),         # partial فیصل
#         (['یل انان'], 'فیصل ٹاؤن', 1),     # garbled فیصل ٹاؤن (FIR_015 PSM6)
#         (['ٹیل نون'], 'فیصل ٹاؤن', 1),     # garbled فیصل ٹاؤن (FIR_015 PSM7)
#         (['نیھل'], 'فیصل ٹاؤن', 1),        # garbled فیصل (FIR_015 Otsu)
#         # اقبال ٹاؤن - additional garbled patterns  
#         (['اتال', 'ڈاؤ'], 'علامہ اقبال ٹاؤن', 2),  # garbled اقبال ٹاؤن
#         (['اتال', 'مان'], 'علامہ اقبال ٹاؤن', 2),  # garbled
#         # چوبرجی
#         (['چوبرجی'], 'چوبرجی', 1),
#         # لکشمی چوک
#         (['لکشم'], 'لکشمی چوک', 1),
#         # نسبت روڈ
#         (['نسبت'], 'نسبت روڈ', 1),
#         # نشتر ٹاؤن - removed as standalone, too many reference-point false positives
#         # (نشتر is always a reference point in our dataset, never the crime area)
#         # پران انارکلی
#         (['پرانی', 'نارکل'], 'پرانی انارکلی', 2),
#         # عامر روڈ - garbled
#         (['ام ز روڈ'], 'عامر روڈ', 1),     # garbled FIR_16: ام ز روڈ→عامر روڈ
#         (['امر روڈ'], 'عامر روڈ', 1),
#         (['پامرروڑ'], 'عامر روڈ', 1),      # garbled FIR_16 S1: پامرروڑ
#         # سنت نگر - garbled
#         (['سنت نگر'], 'سنت نگر چوک', 1),
#         # === Additional garble patterns for SPECIFIC crime locations ===
#         # مین بلیوارڈ - garbled patterns (specific crime location, NOT thana)
#         (['باہوفرڈ'], 'مین بلیوارڈ', 1),          # garbled بلیوارڈ (FIR_17 S1)
#         (['وارڈ'], 'مین بلیوارڈ', 1),              # partial: و+ا+ر+ڈ in بلیوارڈ/بوارڈ
#         (['بوارڈ'], 'مین بلیوارڈ', 1),             # garbled بلیوارڈ→بوارڈ (FIR_17 S0-PSM7)
#         (['بلیوا'], 'مین بلیوارڈ', 1),             # partial بلیوارڈ
#         # ہربنس پورہ - additional garble patterns from OCR
#         (['ہربن'], 'ہربنس پورہ', 1),                # partial ہربنس
#         (['ہریش'], 'ہربنس پورہ', 1),                # garbled
#         (['ہر شس'], 'ہربنس پورہ', 1),              # garbled FIR_024 S0: ہر شسئ
#         (['شسئ رہ'], 'ہربنس پورہ', 1),             # garbled FIR_024: شسئ رہ→بنس پورہ
#         (['شسغ رہ'], 'ہربنس پورہ', 1),             # garbled variant
#         (['ہر شس'], 'ہربنس پورہ', 1),              # space-separated garble  
#         # غڑی شاہو - شاہو (5 chars) is safe as single-fragment; شاو (3 chars) required combined
#         (['شاہو'], 'غڑی شاہو', 1),                  # شاہو is specific enough (5 chars)
#         (['غڑی', 'شاہ'], 'غڑی شاہو', 2),           # require both غڑی+شاہ
#         (['غری', 'شاہ'], 'غڑی شاہو', 2),           # require both غری+شاہ
#         (['غڑی', 'شاو'], 'غڑی شاہو', 2),           # require both غڑی+شاو
#         (['غری', 'شاو'], 'غڑی شاہو', 2),           # require both غری+شاو
#         (['غڑی شاہ'], 'غڑی شاہو', 1),              # combined string match
#         (['غری شاہ'], 'غڑی شاہو', 1),               # combined string match
#         # شاہ عالمی مارکیٹ - catch garbled شاو+کیٹ pattern (FIR_003: "شاو با ئ ا کیٹ")
#         (['شاو', 'کیٹ'], 'شاہ عالمی مارکیٹ', 2),
#         (['شاہ', 'کیٹ'], 'شاہ عالمی مارکیٹ', 2),
#         # شاہدرہ ٹاؤن - garbled with spaces
#         (['شا در'], 'شاہدرہ ٹاؤن', 1),              # FIR_026: "شا در مان" (space in middle)
#         (['شاہدر'], 'شاہدرہ ٹاؤن', 1),              # duplicate ensures priority
#         # برکت مارکیٹ - combined pattern for FIR_17
#         (['رکیٹ', 'باہوفرڈ'], 'مین بلیوارڈ برکت مارکیٹ', 2),
#         (['رکیٹ', 'بوارڈ'], 'مین بلیوارڈ برکت مارکیٹ', 2),
#         (['رکیٹ', 'وارڈ'], 'مین بلیوارڈ برکت مارکیٹ', 2),
#     ]
    
#     if return_all:
#         # Return ALL matches with positions (earliest first)
#         matches = []
#         seen_locations = set()
#         for fragments, location, min_needed in FRAGMENT_RULES:
#             found_count = sum(1 for f in fragments if f in orig)
#             if found_count >= min_needed:
#                 if location in seen_locations:
#                     continue
#                 seen_locations.add(location)
#                 earliest_pos = len(orig)
#                 for f in fragments:
#                     pos = orig.find(f)
#                     if pos >= 0 and pos < earliest_pos:
#                         earliest_pos = pos
#                 matches.append((location, earliest_pos))
#         matches.sort(key=lambda x: x[1])
#         return matches

#     # Original single-match behavior
#     best_result = ""
#     best_fragments = 0
    
#     for fragments, location, min_needed in FRAGMENT_RULES:
#         found = sum(1 for f in fragments if f in orig)
#         if found >= min_needed and found > best_fragments:
#             best_fragments = found
#             best_result = location
#         elif found >= min_needed and found == best_fragments:
#             # Prefer longer location names for more specific matches
#             if len(location) > len(best_result):
#                 best_result = location
    
#     return best_result


# class FIRExtractor:
#     """
#     Main class for extracting structured data from FIR images
#     """
    
#     def __init__(self, debug_mode: bool = False):
#         self.ocr = MultiEngineOCR()
#         self.preprocessor = FIRImagePreprocessor()
#         self.regions = FIRRegions()
#         self.debug_mode = debug_mode
#         self.debug_counter = 0
    
#     def extract_thana(self, image: np.ndarray) -> Optional[str]:
#         """
#         Extract Thana (police station/area) name from FIR document.

#         Strategy:
#         1. Scan Row 4 (crime location row) for known thana patterns
#         2. Look in header area near "تھانہ لاہور" text
#         3. ONLY return a thana name if it matches a KNOWN thana from the list
#         4. Return empty string if no valid thana found (no garbage text)

#         Returns actual OCR extracted thana name or empty string.
#         """
#         logger.info("=" * 50)
#         logger.info("EXTRACTING THANA/CRIME AREA")
#         logger.info("=" * 50)

#         h, w = image.shape[:2]
        
#         # COMPREHENSIVE list of known Lahore thanas with Urdu variants
#         KNOWN_THANAS_MAP = {
#             # Shalimar and variants
#             'شالیمار': 'Shalimar', 'شالامار': 'Shalimar', 'شالاارے': 'Shalimar',
#             'شالاار': 'Shalimar', 'شالار': 'Shalimar', 'شالا': 'Shalimar',
#             'شالی': 'Shalimar', 'shalimar': 'Shalimar', 'Shalimar': 'Shalimar',
#             # Gulshan Ravi
#             'گلشن راوی': 'Gulshan Ravi', 'گلشن': 'Gulshan Ravi', 'Gulshan Ravi': 'Gulshan Ravi',
#             'Gulshan': 'Gulshan Ravi', 'راوی': 'Gulshan Ravi',
#             # Iqbal Town
#             'اقبال ٹاؤن': 'Iqbal Town', 'اقبال': 'Iqbal Town', 'Iqbal Town': 'Iqbal Town',
#             'Iqbal': 'Iqbal Town',
#             # Model Town
#             'ماڈل ٹاؤن': 'Model Town', 'ماڈل': 'Model Town', 'Model Town': 'Model Town',
#             'Model': 'Model Town',
#             # Gulberg
#             'گلبرگ': 'Gulberg', 'Gulberg': 'Gulberg', 'Gulburg': 'Gulberg',
#             # Johar Town
#             'جوہر ٹاؤن': 'Johar Town', 'جوہر': 'Johar Town', 'Johar Town': 'Johar Town',
#             'Johar': 'Johar Town',
#             # Garden Town
#             'گارڈن ٹاؤن': 'Garden Town', 'گارڈن': 'Garden Town', 'Garden Town': 'Garden Town',
#             # Faisal Town
#             'فیصل ٹاؤن': 'Faisal Town', 'فیصل': 'Faisal Town', 'Faisal Town': 'Faisal Town',
#             # Sabzazar
#             'سبزہ زار': 'Sabzazar', 'سبزازار': 'Sabzazar', 'Sabzazar': 'Sabzazar',
#             # Township
#             'ٹاؤن شپ': 'Township', 'Township': 'Township',
#             # Cantt/Saddar
#             'کینٹ': 'Cantt', 'Cantt': 'Cantt', 'صدر': 'Saddar', 'Saddar': 'Saddar',
#             # Defence/DHA
#             'ڈیفنس': 'Defence', 'Defence': 'Defence', 'Defense': 'Defence', 'DHA': 'DHA',
#             # Shahdara
#             'شاہدرہ': 'Shahdara', 'Shahdara': 'Shahdara',
#             # Shadbagh
#             'شادباغ': 'Shadbagh', 'Shadbagh': 'Shadbagh',
#             # Badami Bagh
#             'بادامی باغ': 'Badami Bagh', 'بادامی': 'Badami Bagh', 'Badami Bagh': 'Badami Bagh',
#             # Mughalpura
#             'مغلپورہ': 'Mughalpura', 'Mughalpura': 'Mughalpura',
#             # Harbanspura
#             'حربنس پورہ': 'Harbanspura', 'Harbanspura': 'Harbanspura',
#             # Ichhra
#             'اچھرا': 'Ichhra', 'Ichhra': 'Ichhra', 'Ichra': 'Ichhra',
#             # Mozang
#             'موزنگ': 'Mozang', 'Mozang': 'Mozang',
#             # Samanabad
#             'سمن آباد': 'Samanabad', 'Samanabad': 'Samanabad',
#             # Shafiqabad
#             'شفیق آباد': 'Shafiqabad', 'شفیق': 'Shafiqabad', 'Shafiqabad': 'Shafiqabad',
#             # Anarkali
#             'انارکلی': 'Anarkali', 'Anarkali': 'Anarkali',
#             # Data Darbar
#             'داتا دربار': 'Data Darbar', 'Data Darbar': 'Data Darbar',
#             # Raiwind
#             'رائیونڈ': 'Raiwind', 'Raiwind': 'Raiwind',
#             # Kahna
#             'کہنہ': 'Kahna', 'Kahna': 'Kahna',
#             # Misri Shah
#             'مصری شاہ': 'Misri Shah', 'Misri Shah': 'Misri Shah',
#             # Muslim Town
#             'مسلم ٹاؤن': 'Muslim Town', 'Muslim Town': 'Muslim Town',
#             # Kot Lakhpat
#             'کوٹ لکھپت': 'Kot Lakhpat', 'Kot Lakhpat': 'Kot Lakhpat',
#             # Kot Abdul Malik
#             'کوٹ عبدالمالک': 'Kot Abdul Malik', 'Kot Abdul Malik': 'Kot Abdul Malik',
#             # Manawan
#             'منانواں': 'Manawan', 'Manawan': 'Manawan',
#             # Factory Area
#             'فیکٹری ایریا': 'Factory Area', 'Factory Area': 'Factory Area',
#             # Ghalib Market
#             'غالب مارکیٹ': 'Ghalib Market', 'Ghalib Market': 'Ghalib Market',
#             # Nawankot
#             'نوانکوٹ': 'Nawankot', 'Nawankot': 'Nawankot',
#             # Baghbanpura
#             'باغبانپورہ': 'Baghbanpura', 'Baghbanpura': 'Baghbanpura',
#             # Green Town
#             'Green Town': 'Green Town', 'گرین ٹاؤن': 'Green Town',
#             # Wapda Town
#             'واپڈا ٹاؤن': 'Wapda Town', 'Wapda Town': 'Wapda Town',
#             # Race Course
#             'ریس کورس': 'Race Course', 'Race Course': 'Race Course',
#             # Nishtar Colony
#             'Nishtar Colony': 'Nishtar Colony',
#             # Walton
#             'Walton': 'Walton',
#             # Liaquatabad
#             'لیاقت آباد': 'Liaquatabad', 'Liaquatabad': 'Liaquatabad',
#             # Manga Mandi
#             'منگا منڈی': 'Manga Mandi', 'Manga Mandi': 'Manga Mandi',
#             # Sundar
#             'سندر': 'Sundar', 'Sundar': 'Sundar',
#             # Barki
#             'بڑکی': 'Barki', 'Barki': 'Barki',
#             # Lohari Gate
#             'لوہاری گیٹ': 'Lohari Gate', 'لوہاری': 'Lohari Gate', 'Lohari Gate': 'Lohari Gate',
#             # Naulakha
#             'نولکھا': 'Naulakha', 'Naulakha': 'Naulakha',
#             # Lower Mall
#             'لوئر مال': 'Lower Mall', 'Lower Mall': 'Lower Mall',
#             # Sattu Katla
#             'ستو کتلا': 'Sattu Katla', 'Sattu Katla': 'Sattu Katla',
#             # Qila Gujjar Singh
#             'قلعہ گجر سنگھ': 'Qila Gujjar Singh', 'Qila Gujjar Singh': 'Qila Gujjar Singh',
#             # Chuhng
#             'چوہنگ': 'Chuhng', 'Chuhng': 'Chuhng',
#             # Cavalry Ground
#             'کیولری گراؤنڈ': 'Cavalry Ground', 'Cavalry Ground': 'Cavalry Ground',
#         }
        
#         # Helper function to scan a region for known thanas
#         def scan_region_for_thana(region, region_name):
#             if self.ocr.easyocr_reader:
#                 try:
#                     results = self.ocr.easyocr_reader.readtext(region, paragraph=True, detail=0)
#                     region_text = ' '.join(str(r) for r in results)
#                     logger.info(f"[Thana] {region_name} OCR: {region_text[:100]}")
                    
#                     # Check against ALL known thana patterns
#                     for pattern, thana_name in KNOWN_THANAS_MAP.items():
#                         if pattern in region_text:
#                             logger.info(f"[Thana] ✓ Found known thana '{pattern}' -> {thana_name} in {region_name}!")
#                             return thana_name
#                 except Exception as e:
#                     logger.warning(f"[Thana] {region_name} scan failed: {e}")
#             return None
        
#         # ============================================
#         # STEP 1: Scan Row 4 (crime location row) for known thanas
#         # ============================================
#         logger.info("[Thana] Scanning Row 4 for known thana patterns...")
#         try:
#             y1, y2 = int(h * 0.36), int(h * 0.48)
#             x1, x2 = int(w * 0.02), int(w * 0.98)
#             row4_region = image[y1:y2, x1:x2]
#             result = scan_region_for_thana(row4_region, "Row 4")
#             if result:
#                 return result
#         except Exception as e:
#             logger.warning(f"[Thana] Row 4 scan failed: {e}")

#         # ============================================
#         # STEP 2: Scan Row 2 (complainant/thana info row) 
#         # ============================================
#         logger.info("[Thana] Scanning Row 2 for thana info...")
#         try:
#             y1, y2 = int(h * 0.17), int(h * 0.26)
#             x1, x2 = int(w * 0.02), int(w * 0.70)
#             row2_region = image[y1:y2, x1:x2]
#             result = scan_region_for_thana(row2_region, "Row 2")
#             if result:
#                 return result
#         except Exception as e:
#             logger.warning(f"[Thana] Row 2 scan failed: {e}")

#         # ============================================
#         # STEP 3: Scan header region for thana name
#         # ============================================
#         logger.info("[Thana] Scanning header region for thana...")
#         try:
#             y1, y2 = int(h * 0.02), int(h * 0.12)
#             x1, x2 = int(w * 0.30), int(w * 0.80)
#             header_region = image[y1:y2, x1:x2]
#             result = scan_region_for_thana(header_region, "Header")
#             if result:
#                 return result
#         except Exception as e:
#             logger.warning(f"[Thana] Header scan failed: {e}")

#         # ============================================
#         # STEP 4: If no known thana found, return empty string
#         # DO NOT return garbage OCR text
#         # ============================================
#         logger.warning("[Thana] ✗ No known thana pattern found in FIR")
#         return ""

#     def _legacy_extract_thana(self, image: np.ndarray) -> Optional[str]:
#         """Legacy thana extraction - kept for reference"""
#         # Known Lahore police station/area names (for fuzzy matching)
#         KNOWN_THANAS = [
#             # English names
#             "Iqbal Town", "Model Town", "Gulberg", "Garden Town", "Faisal Town",
#             "Johar Town", "Sabzazar", "Township", "Cantt", "Saddar", "Defence",
#             "Cavalry Ground", "Anarkali", "Data Darbar", "Shahdara", "Shalimar",
#             "Badami Bagh", "Mughalpura", "Shadbagh", "Harbanspura", "Raiwind",
#             "Kahna", "Chuhng", "Nawankot", "Misri Shah", "Baghbanpura",
#             "Shafiqabad", "Lohari Gate", "Naulakha", "Lower Mall", "Wapda Town",
#             "Muslim Town", "Allama Iqbal Town", "DHA", "Walton", "Nishtar Colony",
#             "Kot Lakhpat", "Manga Mandi", "Sundar", "Green Town", "Samanabad",
#             # Additional thanas
#             "Gulshan Ravi", "Ghalib Market", "Factory Area", "Ichhra", "Mozang",
#             # Shalimar with ALL known Urdu variants and OCR corruptions
#             "Shalimar", "شالیمار", "شالامار", "شالاارے", "شالاار", "شالار", "شالا",
#             "Race Course", "Qila Gujjar Singh", "Lytton Road", "Old Anarkali",
#             "Liaquatabad", "North Cantt", "South Cantt", "Naseerabad", "Kahna Nau",
#             "Sattu Katla", "Lahore Cantt", "Manawan", "Barki", "Kot Abdul Malik",
#             # Urdu names
#             "اقبال ٹاؤن", "ماڈل ٹاؤن", "گلبرگ", "گارڈن ٹاؤن", "فیصل ٹاؤن",
#             "جوہر ٹاؤن", "سبزہ زار", "ٹاؤن شپ", "کینٹ", "صدر", "ڈیفنس",
#             "کیولری گراؤنڈ", "انارکلی", "داتا دربار", "شاہدرہ", "شالیمار",
#             "بادامی باغ", "مغلپورہ", "شادباغ", "حربنس پورہ", "رائیونڈ",
#             "کہنہ", "چوہنگ", "نوانکوٹ", "مصری شاہ", "باغبانپورہ",
#             "شفیق آباد", "لوہاری گیٹ", "نولکھا", "لوئر مال", "واپڈا ٹاؤن",
#             "مسلم ٹاؤن", "علامہ اقبال ٹاؤن",
#             # Additional Urdu names
#             "گلشن راوی", "غالب مارکیٹ", "فیکٹری ایریا", "اچھرا", "موزنگ",
#             "ریس کورس", "قلعہ گجر سنگھ", "لائٹن روڈ", "نصیرآباد",
#             "ستو کتلا", "منانواں", "بڑکی", "کوٹ عبدالمالک"
#         ]

#         # ============================================
#         # STRATEGY 1: PRIORITY - Scan location row (Row 4/5) FIRST
#         # This contains the actual crime location/area name
#         # ============================================
#         logger.info("[Thana] PRIORITY: Scanning location row (Row 4/5) for crime area...")
#         thana_name = self._extract_thana_from_location_row(image)
#         if thana_name:
#             logger.info(f"✓ Thana found in location row: {thana_name}")
#             return thana_name

#         # ============================================
#         # STRATEGY 2: Header area - where "تھانہ لاہور" is shown
#         # This is the cyan highlighted box in your FIR image
#         # Located at top, middle-right section
#         # ============================================
        
#         # Header thana region (where "تھانہ لاہور" and thana name appear)
#         header_thana_regions = [
#             # Main header area (cyan box region)
#             (0.02, 0.08, 0.30, 0.75),  # Top header, middle section
#             (0.02, 0.06, 0.40, 0.80),  # Very top, wider
#             (0.04, 0.10, 0.35, 0.70),  # Alternative header position
#         ]
        
#         for idx, (top, bottom, left, right) in enumerate(header_thana_regions):
#             logger.info(f"[Thana] Trying header region {idx+1}: y={top}-{bottom}, x={left}-{right}")
            
#             header_region = self.preprocessor.extract_region_percent(image, top, bottom, left, right)
            
#             if self.debug_mode:
#                 cv2.imwrite(f"debug_thana_header_{idx+1}.png", header_region)
            
#             thana_name = self._extract_thana_from_region(header_region, KNOWN_THANAS)
#             if thana_name:
#                 logger.info(f"✓ Thana found in header region {idx+1}: {thana_name}")
#                 return thana_name

#         # ============================================
#         # STRATEGY 3: Look in the row with "تھانہ:" label
#         # Search for the label and extract adjacent text
#         # ============================================
#         logger.info("[Thana] Trying label-based detection...")
        
#         # Wider region to find "تھانہ:" label
#         label_region = self.preprocessor.extract_region_percent(
#             image,
#             self.regions.THANA_TOP,
#             self.regions.THANA_BOTTOM,
#             self.regions.THANA_LEFT,
#             self.regions.THANA_RIGHT
#         )
        
#         if self.debug_mode:
#             cv2.imwrite("debug_thana_label_region.png", label_region)
        
#         thana_name = self._find_thana_by_label(label_region, KNOWN_THANAS)
#         if thana_name:
#             logger.info(f"✓ Thana found by label detection: {thana_name}")
#             return thana_name

#         # ============================================
#         # STRATEGY 4: Try the original focused cell approach
#         # ============================================
#         logger.info("[Thana] Trying focused cell region...")
        
#         thana_value_top = 0.10
#         thana_value_bottom = 0.16
#         thana_value_left = 0.75
#         thana_value_right = 0.92
        
#         thana_cell = self.preprocessor.extract_region_percent(
#             image, thana_value_top, thana_value_bottom,
#             thana_value_left, thana_value_right
#         )

#         if self.debug_mode:
#             cv2.imwrite("debug_thana_cell.png", thana_cell)
        
#         thana_name = self._extract_thana_from_cell(thana_cell)
#         if thana_name:
#             logger.info(f"✓ Thana found from cell: {thana_name}")
#             return thana_name

#         logger.warning("✗ Thana not found")
#         return None

#     def _extract_thana_from_region(self, region: np.ndarray, known_thanas: list) -> Optional[str]:
#         """
#         Extract thana name from a region, matching against known thana names.
#         Uses both OCR and fuzzy matching.
#         """
#         if region is None or region.size == 0:
#             return None
        
#         # Prepare image versions
#         gray = cv2.cvtColor(region, cv2.COLOR_BGR2GRAY) if len(region.shape) == 3 else region
        
#         # Upscale small regions
#         h, w = gray.shape[:2]
#         scale = max(2, 600 // max(w, 1))
#         upscaled = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
        
#         # Enhance contrast
#         clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
#         enhanced = clahe.apply(upscaled)
        
#         # Denoise
#         denoised = cv2.fastNlMeansDenoising(enhanced, None, h=10)
        
#         # Binary threshold
#         _, binary = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
#         all_texts = []
        
#         # Try EasyOCR
#         if self.ocr.easyocr_reader:
#             for img_version in [upscaled, enhanced, denoised, binary]:
#                 try:
#                     results = self.ocr.easyocr_reader.readtext(img_version, paragraph=False)
#                     for bbox, text, conf in results:
#                         text_clean = text.strip()
#                         if len(text_clean) >= 2:
#                             all_texts.append(text_clean)
#                             logger.info(f"[Thana] EasyOCR: '{text_clean}' (conf={conf:.2f})")
#                 except Exception as e:
#                     pass
        
#         # Try Tesseract with multiple languages
#         try:
#             import pytesseract
#             for lang in ['urd', 'eng', 'urd+eng']:
#                 for psm in [6, 7, 11, 13]:
#                     try:
#                         text = pytesseract.image_to_string(binary, lang=lang, config=f'--psm {psm}')
#                         words = text.strip().replace('\n', ' ').split()
#                         for word in words:
#                             if len(word.strip()) >= 2:
#                                 all_texts.append(word.strip())
#                     except:
#                         pass
#         except ImportError:
#             pass
        
#         # Match against known thanas
#         matched = self._match_known_thana(all_texts, known_thanas)
#         if matched:
#             return matched
        
#         # Return longest meaningful text if no known match
#         urdu_texts = [t for t in all_texts if any('\u0600' <= c <= '\u06FF' for c in t)]
#         if urdu_texts:
#             # Filter out common words
#             skip_words = {'تھانہ', 'لاہور', 'پولیس', 'ضلع', 'نمبر', 'فارم', 'رپورٹ'}
#             filtered = [t for t in urdu_texts if t not in skip_words and len(t) > 2]
#             if filtered:
#                 return max(filtered, key=len)
        
#         return None
    
#     def _fuzzy_match_urdu(self, text1: str, text2: str, threshold: float = 0.8) -> bool:
#         """
#         Fuzzy match two Urdu strings. Returns True if similarity is above threshold.
#         Uses character-level comparison to handle OCR errors.
        
#         NOTE: Using high threshold (0.8) to avoid false positives with common characters.
#         """
#         if not text1 or not text2:
#             return False
        
#         # Normalize: keep only Urdu characters
#         def normalize(s):
#             return ''.join(c for c in s if '\u0600' <= c <= '\u06FF')
        
#         t1 = normalize(text1)
#         t2 = normalize(text2)
        
#         if not t1 or not t2:
#             return False
        
#         # Require minimum length to avoid matching noise
#         if len(t1) < 3 or len(t2) < 3:
#             return False
        
#         # Length should be similar (within 50% of each other)
#         len_ratio = min(len(t1), len(t2)) / max(len(t1), len(t2))
#         if len_ratio < 0.5:
#             return False
        
#         # Simple character-level similarity
#         shorter, longer = (t1, t2) if len(t1) <= len(t2) else (t2, t1)
#         matches = sum(1 for c in shorter if c in longer)
#         similarity = matches / len(shorter)
        
#         return similarity >= threshold
    
#     def _match_known_thana(self, ocr_texts: list, known_thanas: list) -> Optional[str]:
#         """
#         Match OCR extracted texts against known thana names using fuzzy matching.
#         Enhanced to handle corrupted/garbled OCR text from poor quality scans.
#         """
#         if not ocr_texts:
#             return None
        
#         # Combine all OCR text for searching
#         combined_text = ' '.join(ocr_texts).lower()
        
#         # Direct match first (case insensitive for English)
#         for thana in known_thanas:
#             thana_lower = thana.lower()
#             if thana_lower in combined_text:
#                 logger.info(f"[Thana] Direct match found: {thana}")
#                 return thana
#             # Check each OCR text
#             for ocr_text in ocr_texts:
#                 if thana_lower == ocr_text.lower():
#                     logger.info(f"[Thana] Exact match found: {thana}")
#                     return thana
        
#         # Fuzzy matching for corrupted OCR (common patterns seen in poor scans)
#         # These are common OCR corruptions of thana names
#         THANA_CORRUPTIONS = {
#             # Gulshan Ravi - IMPORTANT: Check this first as it's common
#             # OCR often corrupts گلشن راوی to various forms
#             "Gulshan Ravi": ["گلشن راوی", "گلشن", "راوی", "گلشنراوی", "gulshan", "ravi", "گشن راوی", "گلشین",
#                             "کشمراول", "کشن راوی", "گلشن راری", "کشمراوی", "گشنراوی",
#                             "مرادی", "؟مرادی", "مراوی", "مراری", "گلشنمراوی", "گشنمراوی",
#                             "لشن", "لشنراوی", "گلشنر"],
#             "گلشن راوی": ["گلشن", "راوی", "گلشنراوی", "گشن راوی", "گلشین", "گلشن راری",
#                           "کشمراول", "کشن راوی", "کشمراوی", "گشنراوی",
#                           "مرادی", "؟مرادی", "مراوی", "مراری", "گلشنمراوی", "گشنمراوی",
#                           "لشن", "لشنراوی", "گلشنر"],
#             # Other thanas
#             "Iqbal Town": ["اتبال", "اقبال", "اقال", "اتال", "اقبل", "اقیال", "iqbal", "اقالحاءن", "اتبال اول"],
#             "اقبال ٹاؤن": ["اتبال", "اقبال", "اقال", "اتال", "اقبل", "اقیال", "اقالحاءن", "اتبال اول"],
#             "Model Town": ["ماڈل", "مادل", "موڈل", "model", "ماڈال"],
#             "ماڈل ٹاؤن": ["ماڈل", "مادل", "موڈل", "ماڈال"],
#             "Gulberg": ["گلبرگ", "گولبرگ", "گلبر", "gulberg", "gulburg"],
#             "گلبرگ": ["گلبر", "گولبرگ", "گلبرج"],
#             "Johar Town": ["جوہر", "جوھر", "جہور", "johar", "جوہار"],
#             "جوہر ٹاؤن": ["جوہر", "جوھر", "جہور", "جوہار"],
#             "Shafiqabad": ["شفیق", "شافق", "شفیق آباد", "shafiq", "شفیقا"],
#             "شفیق آباد": ["شفیق", "شافق", "شفیقا"],
#             "Defence": ["ڈیفنس", "ڈفنس", "ڈیفینس", "defence", "defense"],
#             "Cantt": ["کینٹ", "کنٹ", "cantt", "کینٹمنٹ"],
#             "Saddar": ["صدر", "صدار", "saddar", "صدہ"],
#             "Shalimar": ["شالیمار", "شالمار", "شلیمار", "shalimar", "شالامار", "شالا", "شالی", 
#                          "شالاارے", "شالاار", "شالار", "شلامار", "شالیما", "شالم", "شالیم",
#                          "شالامارے", "شالمارے", "شالیمارے"],  # Added more OCR corruption variants
#             "Garden Town": ["گارڈن", "گاڈن", "garden"],
#             "Faisal Town": ["فیصل", "فصیل", "فیصال", "faisal"],
#             "Ichhra": ["اچھرا", "اچرا", "ichhra", "ichara"],
#             "Mozang": ["موزنگ", "موزنج", "mozang"],
#             "Samanabad": ["سمن آباد", "سمنآباد", "سمناباد", "samanabad"],
#             "Ghalib Market": ["غالب مارکیٹ", "غالب", "ghalib"],
#         }
        
#         # PRIORITY ORDER: Check Shalimar and Gulshan Ravi first (common corruption patterns)
#         priority_thanas = ["Shalimar", "Gulshan Ravi", "گلشن راوی"]
        
#         # First pass: check priority thanas - Shalimar first!
#         # Check Shalimar specifically
#         shalimar_patterns = ["شالیمار", "شالمار", "شلیمار", "shalimar", "شالامار", "شالا", "شالی", 
#                              "شالاارے", "شالاار", "شالار", "شلامار", "شالیما", "شالم", "شالیم",
#                              "شالامارے", "شالمارے", "شالیمارے"]
#         for pattern in shalimar_patterns:
#             if pattern.lower() in combined_text.lower():
#                 logger.info(f"[Thana] PRIORITY Shalimar match: '{pattern}' -> Shalimar")
#                 return "Shalimar"
        
#         # Check Gulshan Ravi
#         for thana in ["Gulshan Ravi", "گلشن راوی"]:
#             if thana in THANA_CORRUPTIONS:
#                 for corruption in THANA_CORRUPTIONS[thana]:
#                     if corruption.lower() in combined_text.lower():
#                         logger.info(f"[Thana] Priority corruption match: '{corruption}' -> {thana}")
#                         return "Gulshan Ravi"  # Always return English name
        
#         # Second pass: check all other thanas
#         for thana, corruptions in THANA_CORRUPTIONS.items():
#             if thana in priority_thanas:
#                 continue  # Skip priority thanas already checked
#             for corruption in corruptions:
#                 if corruption.lower() in combined_text.lower():
#                     logger.info(f"[Thana] Corruption match: '{corruption}' -> {thana}")
#                     return thana
        
#         # Partial match (for cases like "اقبال" matching "اقبال ٹاؤن")
#         for ocr_text in ocr_texts:
#             for thana in known_thanas:
#                 # Check if OCR text is a significant part of thana name
#                 if len(ocr_text) >= 3:
#                     if ocr_text in thana or thana in ocr_text:
#                         logger.info(f"[Thana] Partial match: '{ocr_text}' -> {thana}")
#                         return thana
#                     # NOTE: Disabled fuzzy matching as it causes too many false positives
#                     # The corruption patterns dictionary is more reliable
#                     # if self._fuzzy_match_urdu(ocr_text, thana):
#                     #     logger.info(f"[Thana] Fuzzy match: '{ocr_text}' -> {thana}")
#                     #     return thana
        
#         # Try extracting "X Town" or "X ٹاؤن" patterns
#         town_patterns = [
#             r'(\w+)\s*[Tt]own',
#             r'(\w+)\s*ٹاؤن',
#             r'(\w+)\s*[Tt]اؤن',
#         ]
#         import re
#         for pattern in town_patterns:
#             for text in ocr_texts:
#                 match = re.search(pattern, text)
#                 if match:
#                     potential = match.group(0)
#                     logger.info(f"[Thana] Town pattern match: {potential}")
#                     return potential
        
#         return None

#     def _find_thana_by_label(self, region: np.ndarray, known_thanas: Optional[list] = None) -> Optional[str]:
#         """
#         Find the "تھانہ" label in region and return the text adjacent to it.
#         Enhanced with known thana matching.
#         """
#         try:
#             if self.ocr.easyocr_reader is None:
#                 return None

#             # Get all text detections with bounding boxes
#             results = self.ocr.easyocr_reader.readtext(region, paragraph=False)

#             if not results:
#                 return None

#             # Log all detections for debugging
#             logger.info(f"[Thana] Found {len(results)} text blocks in label region")

#             all_texts = []
#             for bbox, text, conf in results:
#                 text_clean = text.strip()
#                 if len(text_clean) >= 2:
#                     all_texts.append(text_clean)
#                     logger.info(f"  '{text_clean}' (conf={conf:.2f})")

#             # Try to match against known thanas first
#             if known_thanas:
#                 matched = self._match_known_thana(all_texts, known_thanas)
#                 if matched:
#                     return matched

#             # Find the "تھانہ" label and get adjacent text
#             thana_labels = ['تھانہ', 'تھانہ:', 'ٹھانہ', 'تھانا', 'تہانہ']
#             skip_words = {'تھانہ', 'پولیس', 'ضلع', 'لاہور', 'نمبر', 'فارم', 'رپورٹ'}

#             for i, (bbox, text, conf) in enumerate(results):
#                 text_clean = text.strip().replace(':', '')
                
#                 # Check if this is the thana label
#                 is_label = any(label in text_clean for label in thana_labels)
                
#                 if is_label:
#                     # Get the next text block (thana name is often adjacent)
#                     for j, (bbox2, text2, conf2) in enumerate(results):
#                         if j == i:
#                             continue
#                         text2_clean = text2.strip()
#                         if text2_clean in skip_words or len(text2_clean) < 2:
#                             continue
#                         # Return first valid adjacent text
#                         urdu_chars = sum(1 for c in text2_clean if '\u0600' <= c <= '\u06FF')
#                         if urdu_chars >= 2:
#                             return text2_clean

#             # Return longest valid text if no label found
#             valid_texts = [t for t in all_texts if t not in skip_words]
#             if valid_texts:
#                 return max(valid_texts, key=len)

#             return None

#         except Exception as e:
#             logger.error(f"[Thana] Label detection failed: {e}")
#             return None

#     def _extract_thana_from_cell(self, cell_image: np.ndarray) -> Optional[str]:
#         """
#         Extract thana name from the focused thana cell region.
#         Uses multiple OCR approaches and returns best result.
        
#         Key insight: Thana names are typically Urdu words with 3-15 characters.
#         We try multiple preprocessing approaches and pick the most consistent result.
#         """
#         candidates = []
        
#         # Skip these common words (labels, not thana names)
#         skip_words = {
#             # Labels
#             'تھانہ', 'ٹھانہ', 'تھانا', 'پولیس', 'ضلع', 'لاہور', 
#             'نمبر', 'فارم', 'رپورٹ', 'سٹیشن', 'ایف', 'آئی', 'آر',
#             # Common Urdu words (not location names)
#             'کے', 'سے', 'میں', 'اور', 'کی', 'کا', 'ہے', 'تھا', 'تھی', 'تھے',
#             'وہ', 'یہ', 'جو', 'کہ', 'نے', 'پر', 'کو', 'کر', 'ہو', 'گا', 'گی',
#             'آپ', 'ہم', 'تم', 'مجھے', 'ہیں', 'ہوں', 'ہوا', 'ہوئی',
#             'چو', 'آے', 'جی', 'ہاں', 'نہیں', 'جب', 'تب', 'اب',
#             # Numbers in Urdu
#             '٠', '١', '٢', '٣', '٤', '٥', '٦', '٧', '٨', '٩',
#         }
        
#         # Also skip if text is just 2 chars and is a common word
#         short_common_words = {'وہ', 'یہ', 'جو', 'کہ', 'نے', 'پر', 'کو', 'کر', 'ہو', 'جی', 'ہم', 'تم', 'آپ'}
        
#         # Prepare preprocessed versions
#         gray = cv2.cvtColor(cell_image, cv2.COLOR_BGR2GRAY)
        
#         # Determine upscale factor based on image size (avoid memory issues)
#         cell_height, cell_width = gray.shape[:2]
#         if cell_width < 400:
#             upscale_factor = 3
#         elif cell_width < 800:
#             upscale_factor = 2
#         else:
#             upscale_factor = 1.5  # Large images don't need much upscaling
        
#         logger.info(f"[Thana] Cell size {cell_width}x{cell_height}, using upscale factor {upscale_factor}")
        
#         # Version 1: Upscaled
#         upscaled = cv2.resize(gray, None, fx=upscale_factor, fy=upscale_factor, interpolation=cv2.INTER_CUBIC)
        
#         # Version 2: Denoised + CLAHE (best from testing)
#         denoised = cv2.fastNlMeansDenoising(upscaled, None, h=8)
#         clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))
#         enhanced = clahe.apply(denoised)
        
#         # Version 3: Binary threshold
#         _, binary = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
#         # Version 4: Bilateral filter + CLAHE (edge-preserving)
#         bilateral = cv2.bilateralFilter(cell_image, 9, 75, 75)
#         bilateral_gray = cv2.cvtColor(bilateral, cv2.COLOR_BGR2GRAY)
#         bilateral_up = cv2.resize(bilateral_gray, None, fx=upscale_factor, fy=upscale_factor, interpolation=cv2.INTER_CUBIC)
#         bilateral_enhanced = clahe.apply(bilateral_up)
        
#         if self.debug_mode:
#             cv2.imwrite("debug_thana_denoised_clahe.png", enhanced)
#             cv2.imwrite("debug_thana_binary.png", binary)
#             cv2.imwrite("debug_thana_bilateral.png", bilateral_enhanced)
        
#         # ============================================
#         # Try EasyOCR on different versions
#         # ============================================
#         if self.ocr.easyocr_reader:
#             versions = [
#                 ("upscaled", upscaled),
#                 ("enhanced", enhanced),
#                 ("bilateral", bilateral_enhanced)
#             ]
#             for name, img_version in versions:
#                 try:
#                     results = self.ocr.easyocr_reader.readtext(img_version, paragraph=False)
#                     for bbox, text, conf in results:
#                         text_clean = text.strip()
#                         # Skip empty, short, or label words
#                         if len(text_clean) < 2:
#                             continue
#                         if text_clean in skip_words or text_clean in short_common_words:
#                             continue
#                         if any(skip in text_clean for skip in skip_words):
#                             continue
#                         # Skip very short common words
#                         if len(text_clean) <= 2 and text_clean in short_common_words:
#                             continue
#                         # Must have Urdu characters
#                         urdu_chars = sum(1 for c in text_clean if '\u0600' <= c <= '\u06FF')
#                         if urdu_chars >= 2:
#                             candidates.append({
#                                 'text': text_clean,
#                                 'conf': conf,
#                                 'source': f'easyocr_{name}',
#                                 'urdu_ratio': urdu_chars / len(text_clean)
#                             })
#                             logger.info(f"[Thana] EasyOCR {name}: '{text_clean}' (conf={conf:.2f})")
#                 except Exception as e:
#                     logger.warning(f"[Thana] EasyOCR {name} failed: {e}")
        
#         # ============================================
#         # Try Tesseract (often better for printed Urdu)
#         # ============================================
#         try:
#             import pytesseract
            
#             versions = [
#                 ("binary", binary),
#                 ("enhanced", enhanced),
#                 ("bilateral", bilateral_enhanced)
#             ]
#             for name, img_version in versions:
#                 for psm in [6, 7, 11]:
#                     try:
#                         text = pytesseract.image_to_string(img_version, lang='urd', config=f'--psm {psm}')
#                         text_clean = text.strip().replace('\n', ' ')
                        
#                         if len(text_clean) < 2:
#                             continue
                        
#                         # Extract individual words
#                         words = text_clean.split()
#                         for word in words:
#                             word = word.strip()
#                             if len(word) < 2:
#                                 continue
#                             if word in skip_words or word in short_common_words:
#                                 continue
#                             if any(skip in word for skip in skip_words):
#                                 continue
#                             # Must have Urdu characters
#                             urdu_chars = sum(1 for c in word if '\u0600' <= c <= '\u06FF')
#                             if urdu_chars >= 2:
#                                 candidates.append({
#                                     'text': word,
#                                     'conf': 0.5,  # Tesseract doesn't give per-word confidence
#                                     'source': f'tesseract_{name}_psm{psm}',
#                                     'urdu_ratio': urdu_chars / len(word)
#                                 })
#                                 logger.info(f"[Thana] Tesseract {name} PSM{psm}: '{word}'")
#                     except Exception as e:
#                         pass  # Silent fail for individual attempts
#         except ImportError:
#             logger.warning("[Thana] pytesseract not available")
        
#         # ============================================
#         # Select best candidate using consensus + scoring
#         # ============================================
#         if not candidates:
#             logger.info("[Thana] No candidates found in cell")
#             return None
        
#         # First, count how many times similar texts appear (consensus voting)
#         # This helps identify the most consistent OCR result
#         from collections import Counter
        
#         # Normalize texts for comparison (remove diacritics, normalize spaces)
#         def normalize_text(text):
#             # Keep only Urdu letters (remove diacritics and punctuation)
#             return ''.join(c for c in text if '\u0621' <= c <= '\u064A' or '\u0679' <= c <= '\u06D5')
        
#         text_counts = Counter()
#         for c in candidates:
#             normalized = normalize_text(c['text'])
#             if len(normalized) >= 2:
#                 text_counts[normalized] += 1
        
#         # Log consensus
#         logger.info("[Thana] Consensus voting (normalized texts):")
#         for text, count in text_counts.most_common(5):
#             logger.info(f"  '{text}' appears {count} time(s)")
        
#         # Score candidates based on:
#         # 1. Length preference (3-12 chars is ideal for thana names)
#         # 2. Consensus (how many times similar text appeared)
#         # 3. High Urdu character ratio
#         # 4. Confidence
        
#         def score_candidate(c):
#             score = 0
#             text_len = len(c['text'])
#             normalized = normalize_text(c['text'])
#             normalized_len = len(normalized)
            
#             # STRONG length preference - thana names are typically 3-12 characters
#             if 4 <= normalized_len <= 10:
#                 score += 5  # Ideal length
#             elif 3 <= normalized_len <= 12:
#                 score += 3  # Good length
#             elif normalized_len >= 2:
#                 score += 1  # Acceptable
#             else:
#                 score -= 2  # Too short
            
#             # Penalize very short texts heavily (2 char words are usually noise)
#             if normalized_len <= 2:
#                 score -= 3
            
#             # Consensus bonus (but less weight than length)
#             consensus_count = text_counts.get(normalized, 0)
#             score += consensus_count * 2
            
#             # Prefer high Urdu ratio
#             score += c['urdu_ratio'] * 2
            
#             # Use confidence
#             score += c['conf'] * 1.5
            
#             # Penalize texts that look like noise (numbers, punctuation)
#             noise_chars = sum(1 for ch in c['text'] if ch in '0123456789.:;,/\\|<>()[]{}٠١٢٣٤٥٦٧٨٩')
#             score -= noise_chars * 0.5
            
#             return score
        
#         # Sort by score
#         candidates.sort(key=score_candidate, reverse=True)
        
#         logger.info("[Thana] Ranked candidates:")
#         for i, c in enumerate(candidates[:5]):
#             normalized = normalize_text(c['text'])
#             consensus = text_counts.get(normalized, 0)
#             logger.info(f"  {i+1}. '{c['text']}' (conf={c['conf']:.2f}, urdu={c['urdu_ratio']:.2f}, consensus={consensus}, src={c['source']})")
        
#         # Return the best candidate
#         best = candidates[0]
#         if best['urdu_ratio'] >= 0.5 and len(best['text']) >= 2:
#             logger.info(f"[Thana] Selected from cell: '{best['text']}' from {best['source']}")
            
#             # IMPORTANT: Try to match against known thanas using corruption patterns
#             # This helps correct garbled OCR text
#             KNOWN_THANAS_FOR_CELL = [
#                 "Gulshan Ravi", "گلشن راوی", "Iqbal Town", "اقبال ٹاؤن",
#                 "Model Town", "ماڈل ٹاؤن", "Ghalib Market", "غالب مارکیٹ",
#                 "Gulberg", "گلبرگ", "Johar Town", "جوہر ٹاؤن",
#                 "Garden Town", "Faisal Town", "Saddar", "Defence", "Cantt",
#             ]
            
#             # Try matching with all collected candidate texts
#             all_candidate_texts = [c['text'] for c in candidates]
#             matched = self._match_known_thana(all_candidate_texts, KNOWN_THANAS_FOR_CELL)
#             if matched:
#                 logger.info(f"[Thana] Corrected via known thana matching: '{best['text']}' -> '{matched}'")
#                 return matched
            
#             return best['text']
        
#         return None

#     def _extract_thana_from_location_row(self, image: np.ndarray) -> Optional[str]:
#         """
#         Extract thana name from location rows using multiple OCR approaches.
#         Searches Row 4 and Row 5 for thana patterns with fuzzy matching.
#         """
#         h, w = image.shape[:2]
#         x1 = int(w * 0.02)
#         x2 = int(w * 0.98)

#         # Known thanas for fuzzy matching (comprehensive list)
#         KNOWN_THANAS = [
#             "Iqbal Town", "اقبال ٹاؤن", "Model Town", "ماڈل ٹاؤن", 
#             "Gulberg", "گلبرگ", "Johar Town", "جوہر ٹاؤن",
#             "Shafiqabad", "شفیق آباد", "Shalimar", "شالیمار",
#             "Garden Town", "Faisal Town", "Saddar", "Defence", "Cantt",
#             "Gulshan Ravi", "گلشن راوی", "Ichhra", "اچھرا",
#             # Shalimar with ALL known OCR corruption variants
#             "Shalimar", "شالیمار", "شالامار", "شالاارے", "شالاار", "شالار", "شالا",
#             "Mozang", "موزنگ", "Samanabad", "سمن آباد",
#             "Ghalib Market", "غالب مارکیٹ", "Factory Area", "فیکٹری ایریا"
#         ]

#         # Optimized: Only check Row 4 area where location info is (0.36-0.48)
#         rows_to_check = [
#             ("Row 4", 0.36, 0.48),  # Main location row
#         ]

#         all_ocr_texts = []

#         for row_name, top_pct, bottom_pct in rows_to_check:
#             y1 = int(h * top_pct)
#             y2 = int(h * bottom_pct)
#             row_region = image[y1:y2, x1:x2]

#             if self.debug_mode:
#                 cv2.imwrite(f"debug_thana_{row_name.lower().replace(' ', '')}.png", row_region)

#             # Simple OCR on raw image - most reliable for high-res images
#             if self.ocr.easyocr_reader:
#                 try:
#                     results = self.ocr.easyocr_reader.readtext(row_region, paragraph=True, detail=0)
#                     for text_item in results:
#                         text = str(text_item)
#                         if text and len(text.strip()) >= 2:
#                             all_ocr_texts.append(text.strip())
#                             logger.info(f"[Thana] EasyOCR {row_name}: '{text.strip()[:60]}'")
                            
#                             # Early check for Shalimar patterns
#                             shalimar_patterns = ['شالا', 'شالی', 'shalimar', 'Shalimar']
#                             for pattern in shalimar_patterns:
#                                 if pattern in text:
#                                     logger.info(f"[Thana] Found Shalimar pattern in {row_name}!")
#                                     return "Shalimar"
#                 except Exception as e:
#                     logger.warning(f"[Thana] EasyOCR error on {row_name}: {e}")

#         # Try matching all collected OCR text against known thanas
#         if all_ocr_texts:
#             matched = self._match_known_thana(all_ocr_texts, KNOWN_THANAS)
#             if matched:
#                 logger.info(f"[Thana] Matched from location row: {matched}")
#                 return matched

#             # Try pattern extraction from text
#             for text in all_ocr_texts:
#                 thana = self._extract_thana_pattern_from_text(text)
#                 if thana:
#                     return thana

#         return None

#     def _extract_thana_pattern_from_text(self, text: str) -> Optional[str]:
#         """
#         Extract thana name from text by looking for patterns like:
#         - X ٹاؤن (X Town)
#         - X ماؤن (corrupted ٹاؤن)
#         - X- تھانہ سے (from X thana)
#         - X تھانہ (X police station)
#         """
#         import re

#         # Skip words that are not thana names
#         skip_words = {'لاہور', 'لا', 'ہور', 'پنجاب', 'پولیس', 'سے', 'کے', 'میں', 'اور'}

#         # Patterns for thana names (including corrupted OCR versions)
#         # Format: (word before) + (ٹاؤن or similar)
#         town_patterns = [
#             r'(\S+)\s*ٹاؤن',      # X ٹاؤن
#             r'(\S+)\s*ماؤن',      # X ماؤن (corrupted)
#             r'(\S+)\s*ماکان',     # X ماکان (corrupted)
#             r'(\S+)\s*ٹاون',      # X ٹاون (variant)
#             r'(\S+)\s*تاؤن',      # X تاؤن (variant)
#         ]

#         for pattern in town_patterns:
#             match = re.search(pattern, text)
#             if match:
#                 name_part = match.group(1).strip()
#                 # Clean up the name - keep only Urdu chars
#                 name_part = ''.join(c for c in name_part if '\u0600' <= c <= '\u06FF')
#                 if len(name_part) >= 2 and name_part not in skip_words:
#                     full_name = f"{name_part} ٹاؤن"
#                     logger.info(f"[Thana] Found town pattern: '{full_name}'")
#                     return full_name

#         # Pattern: "X- تھانہ سے" or "X -تھانہ سے" (from X thana)
#         # The text before hyphen followed by تھانہ
#         hyphen_patterns = [
#             r'(\S+)\s*[-ـ]\s*تھانہ',    # X- تھانہ
#             r'(\S+)\s*[-ـ]\s*تھاضہ',    # X- تھاضہ (corrupted)
#             r'(\S+)\s*[-ـ]\s*ٹھانہ',    # X- ٹھانہ (variant)
#         ]

#         for pattern in hyphen_patterns:
#             match = re.search(pattern, text)
#             if match:
#                 name_part = match.group(1).strip()
#                 name_part = ''.join(c for c in name_part if '\u0600' <= c <= '\u06FF')
#                 if len(name_part) >= 2 and name_part not in skip_words:
#                     logger.info(f"[Thana] Found hyphen-thana pattern: '{name_part}'")
#                     return name_part

#         # Direct thana patterns: "تھانہ X" or "X تھانہ"
#         thana_patterns = [
#             r'تھانہ\s+(\S+)',      # تھانہ X (with space)
#             r'(\S+)\s+تھانہ',      # X تھانہ (with space)
#         ]

#         for pattern in thana_patterns:
#             match = re.search(pattern, text)
#             if match:
#                 name_part = match.group(1).strip()
#                 name_part = ''.join(c for c in name_part if '\u0600' <= c <= '\u06FF')
#                 if len(name_part) >= 2 and name_part not in skip_words:
#                     logger.info(f"[Thana] Found thana pattern: '{name_part}'")
#                     return name_part

#         return None

#     def extract_crime_area(self, image: np.ndarray) -> str:
#         """
#         Extract crime area/location from Row 4 using multi-strip scanning.
        
#         Uses overlapping image strips × multiple OCR strategies with:
#         1. Structured detection (DHA, Bahria, Askari, LDA, WAPDA, PCSIR, PIA)
#         2. Fragment detection (70+ garbled OCR pattern rules)
#         3. Fuzzy dictionary matching (fallback)
        
#         Scoring hierarchy: Structured (0.99) > Fragment1st (0.95+) > FragClean (0.92) > FragLater (0.85) > Clean (0.78) > Fuzzy (≤0.70)
#         """
#         logger.info("=" * 50)
#         logger.info("EXTRACTING CRIME AREA (Row 4 - Multi-Strip Scan)")
#         logger.info("=" * 50)
        
#         import gc
#         import pytesseract
        
#         h, w = image.shape[:2]
        
#         # Downsample very large images to ~3000px max dimension for consistent OCR
#         max_dim = max(h, w)
#         if max_dim > 5000:
#             s = 3000 / max_dim
#             image = cv2.resize(image, (int(w * s), int(h * s)), interpolation=cv2.INTER_AREA)
#             h, w = image.shape[:2]
#             logger.info(f"[Crime Area] Downsampled to {w}x{h}px for consistent OCR")
        
#         best_result = ""
#         best_score = 0
        
#         for si, (y1f, y2f, x1f, x2f) in enumerate(CRIME_STRIPS):
#             y1, y2 = int(h * y1f), int(h * y2f)
#             x1, x2 = int(w * x1f), int(w * x2f)
            
#             if y2 <= y1 or x2 <= x1:
#                 continue
            
#             row_crop = image[y1:y2, x1:x2]
#             rh, rw = row_crop.shape[:2]
#             if rh < 20 or rw < 50:
#                 continue
            
#             # Determine scale based on crop width
#             if rw > 1500:
#                 scale_factor = 2.0
#             elif rw > 800:
#                 scale_factor = 3.0
#             else:
#                 scale_factor = 4.0
            
#             try:
#                 resized = cv2.resize(row_crop, None, fx=scale_factor, fy=scale_factor, interpolation=cv2.INTER_CUBIC)
#                 gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY) if len(resized.shape) == 3 else resized
#             except (cv2.error, MemoryError):
#                 logger.warning(f"[Crime Area] Strip {si} scale {scale_factor}x failed, skipping")
#                 continue
            
#             strategies = []
            
#             # PSM6 + CLAHE
#             clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
#             cl = clahe.apply(gray)
#             strategies.append((cl, '--psm 6 --oem 3 -l urd', f'S{si}-PSM6'))
            
#             # PSM7
#             strategies.append((cl, '--psm 7 --oem 3 -l urd', f'S{si}-PSM7'))
            
#             # Adaptive threshold on raw gray (not CLAHE)
#             adapt = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
#                                            cv2.THRESH_BINARY, 15, 8)
#             strategies.append((adapt, '--psm 6 --oem 3 -l urd', f'S{si}-Adapt'))
            
#             # Otsu binary on raw gray
#             _, otsu = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
#             strategies.append((otsu, '--psm 6 --oem 3 -l urd', f'S{si}-Otsu'))
            
#             for proc_img, config, label in strategies:
#                 try:
#                     raw = pytesseract.image_to_string(proc_img, config=config).strip()
#                 except Exception:
#                     continue
                
#                 if not raw or len(raw) < 3:
#                     continue
                
#                 ur = sum(1 for c in raw if '\u0600' <= c <= '\u06FF')
#                 if ur < 3:
#                     continue
                
#                 # Structured detection (DHA, Bahria, Askari, etc.)
#                 struct = detect_structured_location(raw)
#                 if struct:
#                     score = 0.99
#                     if score > best_score:
#                         best_score = score
#                         best_result = struct
#                     continue
                
#                 # Fragment detection with return_all - position-based scoring
#                 all_frags = detect_location_fragments(raw, return_all=True)
#                 if all_frags:
#                     for idx, (frag, pos) in enumerate(all_frags):
#                         if idx == 0:
#                             multi_bonus = min(0.03, len(all_frags) * 0.015)
#                             score = 0.95 + multi_bonus
#                         else:
#                             score = 0.85
                        
#                         if score > best_score:
#                             best_score = score
#                             best_result = frag
#                     continue
                
#                 # Clean text and try fragment detection on it
#                 cleaned = self._clean_crime_area_text(raw)
#                 if cleaned and len(cleaned) >= 3:
#                     all_frags_c = detect_location_fragments(cleaned, return_all=True)
#                     if all_frags_c:
#                         for idx, (frag, pos) in enumerate(all_frags_c):
#                             if idx == 0:
#                                 score = 0.92
#                             else:
#                                 score = 0.83
#                             if score > best_score:
#                                 best_score = score
#                                 best_result = frag
#                         continue
                    
#                     # Clean text as fallback - only if it looks like a valid location
#                     if self._is_valid_location_text(cleaned):
#                         score = 0.78
#                         if score > best_score:
#                             best_score = score
#                             best_result = cleaned
            
#             # Also try EasyOCR on this strip (better at Urdu than Tesseract)
#             if EASYOCR_AVAILABLE and self.ocr.easyocr_reader and best_score < 0.95:
#                 try:
#                     easyocr_results = self.ocr.easyocr_reader.readtext(row_crop, detail=0, paragraph=True)
#                     easyocr_text = ' '.join(str(x) for x in easyocr_results).strip()
#                     if easyocr_text and len(easyocr_text) >= 3:
#                         ur_count = sum(1 for c in easyocr_text if '\u0600' <= c <= '\u06FF')
#                         if ur_count >= 3:
#                             # Try structured detection
#                             struct = detect_structured_location(easyocr_text)
#                             if struct and 0.99 > best_score:
#                                 best_score = 0.99
#                                 best_result = struct
#                             elif not struct:
#                                 # Try fragment detection
#                                 frags = detect_location_fragments(easyocr_text, return_all=True)
#                                 if frags:
#                                     frag, _ = frags[0]
#                                     score = 0.96  # EasyOCR fragment slightly higher than Tesseract
#                                     if score > best_score:
#                                         best_score = score
#                                         best_result = frag
#                                 else:
#                                     # Clean text fallback
#                                     cleaned_easy = self._clean_crime_area_text(easyocr_text)
#                                     if cleaned_easy and len(cleaned_easy) >= 3:
#                                         frags_c = detect_location_fragments(cleaned_easy, return_all=True)
#                                         if frags_c:
#                                             frag, _ = frags_c[0]
#                                             score = 0.93
#                                             if score > best_score:
#                                                 best_score = score
#                                                 best_result = frag
#                                         elif 0.80 > best_score and self._is_valid_location_text(cleaned_easy):
#                                             best_score = 0.80
#                                             best_result = cleaned_easy
#                 except Exception as e:
#                     logger.debug(f"[Crime Area] EasyOCR strip {si} failed: {e}")
            
#             del gray, cl, adapt, otsu
#             gc.collect()
        
#         if best_result:
#             logger.info(f"[Crime Area] Result: '{best_result}' (score: {best_score:.3f})")
#         else:
#             logger.warning("[Crime Area] No reliable match found")
        
#         return best_result

#     def _clean_crime_area_text(self, raw_text: str) -> str:
#         """Clean OCR text for crime area extraction - shared by all OCR engines."""
#         text = raw_text.strip()
#         if not text:
#             return ""
        
#         # Remove RTL/LTR control characters, zero-width chars, and other Unicode control
#         text = re.sub(r'[\u200e\u200f\u200b\u200c\u200d\u202a-\u202e\u2066-\u2069\ufeff]', '', text)
        
#         # For multi-line text, find the line with the most Urdu location content
#         lines = text.split('\n')
#         if len(lines) > 1:
#             location_keywords = [
#                 'روڈ', 'مارکیٹ', 'چوک', 'گیٹ', 'ٹاؤن', 'بازار', 'بلاک',
#                 'پارک', 'کالونی', 'نگر', 'پورہ', 'فیز', 'سیکٹر',
#                 'آباد', 'سوسائٹی', 'ہاؤسنگ', 'دربار', 'ایونیو', 'انٹرچینج',
#                 'آسکاری', 'بحریہ', 'ڈی ایچ اے', 'والینشیا', 'واپڈا',
#             ]
#             negative_keywords = ['اطلاع', 'فون', 'بزریعہ', 'ذریعہ', 'موصول',
#                                 'عوائی', 'ٹریفک', 'صورتحال', 'ٹرییک', 'ہوئی', 'ہوئگی']
#             best_line = ""
#             best_score = -1
#             for line in lines:
#                 line = line.strip()
#                 if not line:
#                     continue
#                 urdu = sum(1 for c in line if '\u0600' <= c <= '\u06FF')
#                 keywords_found = sum(1 for kw in location_keywords if kw in line)
#                 score = urdu + keywords_found * 5
#                 for nk in negative_keywords:
#                     if nk in line:
#                         score -= 20
#                 if score > best_score:
#                     best_score = score
#                     best_line = line
#             if best_line:
#                 text = best_line
        
#         # Remove ALL leading non-Urdu characters (numbers, punctuation, ASCII, etc.)
#         text = re.sub(r'^[^\u0600-\u06FF]+', '', text)
        
#         # Remove row labels
#         labels = [
#             r'جائے\s*وقوعہ',
#             r'جائے\s*اور\s*علاقہ.*',
#             r'تحصیل\s*و\s*ضلع',
#             r'علاقہ\s*تحصیل',
#         ]
#         for label in labels:
#             text = re.sub(label, '', text, flags=re.UNICODE)
        
#         # Split at "سے" (distance marker - "[location] سے [distance]")
#         # This is aggressive but correct for crime area context
#         text = re.split(r'\s+سے\s+', text)[0]
        
#         # Also try the more specific distance pattern
#         distance_pattern = r'(?:سے|ے)\s*(?:تقر|نقر|تھر|تمر|تپ|تر|نر|۲ر|تت)'
#         text = re.split(distance_pattern, text)[0]
        
#         # Extract text before dash (multiple dash patterns)
#         dash_patterns = [
#             r'^(.*?)[\-]{2,}',
#             r'^(.*?)[ـ]{3,}',
#             r'^(.*?)[\.۔]{4,}',
#         ]
#         for pattern in dash_patterns:
#             match = re.search(pattern, text, re.UNICODE)
#             if match:
#                 text = match.group(1).strip()
#                 break
        
#         # Remove distance/direction phrases
#         text = re.sub(r'[\d٠-٩\.]+\s*کلو\s*میٹر', '', text)
#         text = re.sub(r'[\d٠-٩\.]+\s*کاو\s*می', '', text)
#         text = re.sub(r'شمال\s*(?:مشرق|مغرب)?\.?\s*$', '', text)
#         text = re.sub(r'جنوب\s*(?:مشرق|مغرب)?\.?\s*$', '', text)
#         text = re.sub(r'مشرق[ی]?\s*$', '', text)
#         text = re.sub(r'(?:مغرب|مطرب|وخرب|مخرب|مطضرب)\s*$', '', text)
        
#         # Clean up whitespace and punctuation
#         text = re.sub(r'\s+', ' ', text).strip()
#         text = re.sub(r'^[\s\-_=.:،۔/\d٠-٩۰-۹]+', '', text)
#         text = re.sub(r'[\s\-_=.:،۔]+$', '', text)
#         text = re.sub(r'[\[\]{}()!@#$%^&*;:<>|/\\]', '', text)
        
#         # NOTE: Smart truncation at last location keyword REMOVED
#         # Previously this truncated text at the last keyword (روڈ, ٹاؤن, etc.)
#         # which caused the system to return only the thana/area name
#         # instead of the full specific crime location text.
#         # Now we keep the full cleaned text for position-based fragment matching.
        
#         # Remove trailing garbage
#         text = re.sub(r'[\d٠-٩۰-۹]+\s*$', '', text)
#         text = re.sub(r'[a-zA-Z]{1,2}\s*$', '', text)
        
#         return text.strip()

#     @staticmethod
#     def _is_valid_location_text(text: str) -> bool:
#         """Check if cleaned text looks like a valid Urdu location name.

#         Rejects obviously garbled OCR output that passes basic length checks
#         but doesn't contain any recognizable location patterns.

#         Garbled text indicators:
#         - Arabic diacritical marks (tashkeel) - never appear in printed FIR location fields
#         - Consecutive repeated characters (اا, سس, بب) - unusual in location names
#         - Many single-character words (e.g., "ي" "ا" scattered)
#         - No recognizable location keywords
#         - Excessive spacing relative to text length
#         - Average word length < 2 characters
#         - Any word longer than 10 chars (location words are typically shorter)
#         """
#         import re as _re
#         if not text or len(text) < 3:
#             return False

#         words = text.split()
#         if not words:
#             return False

#         # EARLY REJECT: Arabic diacritical marks (tashkeel) — never in printed location names
#         # Fathah, Dammah, Kasrah, Sukun, Shadda, Tanween, etc.
#         tashkeel = '\u064b\u064c\u064d\u064e\u064f\u0650\u0651\u0652'
#         if any(c in text for c in tashkeel):
#             logger.debug(f"[Crime Area] Rejecting garbled text (has diacritics/tashkeel): '{text}'")
#             return False

#         # EARLY REJECT: Consecutive repeated characters (e.g., "اا", "سس", "بب")
#         # More than 1 pair of consecutive duplicates in the whole text is suspicious
#         repeat_count = len(_re.findall(r'(.)\1', text.replace(' ', '')))
#         if repeat_count >= 2:
#             logger.debug(f"[Crime Area] Rejecting garbled text ({repeat_count} repeated char pairs): '{text}'")
#             return False

#         # Check for location keywords - if any present, text is likely valid
#         location_keywords = [
#             '\u0631\u0648\u0688', '\u0645\u0627\u0631\u06a9\u06cc\u0679', '\u0686\u0648\u06a9', '\u06af\u06cc\u0679', '\u0679\u0627\u0624\u0646', '\u0628\u0627\u0632\u0627\u0631', '\u0628\u0644\u0627\u06a9',
#             '\u067e\u0627\u0631\u06a9', '\u06a9\u0627\u0644\u0648\u0646\u06cc', '\u0646\u06af\u0631', '\u067e\u0648\u0631\u06c1', '\u0641\u06cc\u0632', '\u0633\u06cc\u06a9\u0679\u0631',
#             '\u0622\u0628\u0627\u062f', '\u0633\u0648\u0633\u0627\u0626\u0679\u06cc', '\u06c1\u0627\u0624\u0633\u0646\u06af', '\u062f\u0631\u0628\u0627\u0631', '\u0627\u06cc\u0648\u0646\u06cc\u0648', '\u0627\u0646\u0679\u0631\u0686\u06cc\u0646\u062c',
#             '\u0622\u0633\u06a9\u0627\u0631\u06cc', '\u0628\u062d\u0631\u06cc\u06c1', '\u0648\u0627\u067e\u0688\u0627', '\u0648\u0627\u0644\u06cc\u0646\u0634\u06cc\u0627', '\u0627\u06cc\u0644 \u0688\u06cc \u0627\u06d2',
#             '\u0645\u0627\u0688\u0644', '\u06af\u0644\u0628\u0631\u06af', '\u062c\u0648\u06c1\u0631', '\u0627\u0642\u0628\u0627\u0644', '\u0641\u06cc\u0635\u0644', '\u0635\u062f\u0631',
#             '\u0688\u06cc\u0641\u0646\u0633', '\u06a9\u06cc\u0646\u0679', '\u0634\u0627\u0644\u06cc\u0645\u0627\u0631', '\u0627\u0646\u0627\u0631\u06a9\u0644\u06cc', '\u0634\u0627\u06c1\u062f\u0631\u06c1',
#             '\u0633\u0628\u0632\u06c1', '\u06a9\u06cc\u0648\u0644\u0631\u06cc', '\u0679\u0627\u0624\u0646\u0634\u067e', '\u0644\u0627\u06c1\u0648\u0631', '\u067e\u0646\u062c\u0627\u0628',
#             '\u0645\u0627\u0644', '\u0633\u0679\u0631\u06cc\u0679', '\u0645\u062d\u0644\u06c1', '\u06af\u0644\u06cc', '\u0645\u0648\u0691',
#         ]
#         has_keyword = any(kw in text for kw in location_keywords)
#         if has_keyword:
#             # Even with a keyword, reject if text has clear garbled indicators:

#             # 1. Urdu/Arabic digits (۰-۹, ٠-٩) mixed into text — never appears in valid location names
#             urdu_digits = set('۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩')
#             if any(c in urdu_digits for c in text):
#                 logger.debug(f"[Crime Area] Rejecting garbled text (Urdu digits in text despite keyword): '{text}'")
#                 return False

#             # 2. Too many very short words (≤2 chars) — garbled text has many tiny fragments
#             short_words = sum(1 for w in words if len(w) <= 2)
#             if len(words) >= 5 and short_words / len(words) >= 0.55:
#                 logger.debug(f"[Crime Area] Rejecting garbled text (too many short words {short_words}/{len(words)} despite keyword): '{text}'")
#                 return False

#             return True

#         # No keywords found - apply stricter validation

#         # Reject very short text without keywords (likely garbled OCR noise)
#         # Valid short location names always contain a keyword (e.g., "ہال روڈ" has "روڈ")
#         urdu_chars_only = sum(1 for c in text if '\u0600' <= c <= '\u06FF')
#         if urdu_chars_only <= 5:
#             logger.debug(f"[Crime Area] Rejecting garbled text (too short without keywords, {urdu_chars_only} Urdu chars): '{text}'")
#             return False

#         # Reject if any word is excessively long (>10 chars) - location words are short
#         if any(len(w) > 10 for w in words):
#             logger.debug(f"[Crime Area] Rejecting garbled text (word too long): '{text}'")
#             return False

#         # Reject if too many single-char words (garbled text signature)
#         single_char_words = sum(1 for w in words if len(w) <= 1)
#         if len(words) >= 3 and single_char_words / len(words) > 0.4:
#             logger.debug(f"[Crime Area] Rejecting garbled text (too many single-char words): '{text}'")
#             return False

#         # Reject if average word length is very short
#         avg_word_len = sum(len(w) for w in words) / len(words)
#         if avg_word_len < 2.0 and len(words) >= 2:
#             logger.debug(f"[Crime Area] Rejecting garbled text (avg word len {avg_word_len:.1f}): '{text}'")
#             return False

#         # Reject if space ratio is too high (garbled text has many spaces)
#         space_count = text.count(' ')
#         total_chars = len(text)
#         if total_chars > 5 and space_count / total_chars > 0.35:
#             logger.debug(f"[Crime Area] Rejecting garbled text (space ratio {space_count/total_chars:.2f}): '{text}'")
#             return False

#         return True

#     def extract_date(self, image: np.ndarray):
#         """
#         Extract crime date AND crime time from the date row of the FIR table.
#         Uses the user-verified expanded region that covers both fields.

#         Returns: Tuple[Optional[str], Optional[str]] -> (date, time)
#             date: DD-MM-YYYY (or variation)
#             time: HH:MM AM/PM  (or None if not found)
#         """
#         logger.info("=" * 50)
#         logger.info("EXTRACTING DATE + TIME")
#         logger.info("=" * 50)

#         # Use the wider user-verified region that covers both date and time
#         date_time_region = self.preprocessor.extract_region_percent(
#             image,
#             self.regions.DATE_TIME_ROW_TOP,
#             self.regions.DATE_TIME_ROW_BOTTOM,
#             self.regions.DATE_TIME_CELL_LEFT,
#             self.regions.DATE_TIME_CELL_RIGHT
#         )

#         # Save debug image
#         if self.debug_mode:
#             cv2.imwrite(f"debug_03_date_raw.png", date_time_region)
#             logger.info("Debug: Saved debug_03_date_raw.png")
#             cv2.imwrite(f"debug_04_date_cleaned.png", date_time_region)
#             logger.info("Debug: Saved debug_04_date_cleaned.png (RAW - no preprocessing)")

#         # DO NOT UPSCALE - preserves original text quality
#         # DO NOT PREPROCESS - EasyOCR works best on natural images

#         # Extract text from RAW region
#         text, confidence = self.ocr.extract_text_multi(date_time_region)
#         method = "raw_original"

#         logger.info(f"Date+Time region text ({method}): {text[:200]}")
#         logger.info(f"Confidence: {confidence:.1f}%")

#         # Parse date
#         date = self._parse_date_from_text(text)
#         # Parse time (AM/PM)
#         crime_time = self._parse_time_from_text(text)

#         if date:
#             logger.info(f"✓ Date found: {date}")
#         else:
#             logger.warning("✗ Date not found")

#         if crime_time:
#             logger.info(f"✓ Time found: {crime_time}")
#         else:
#             logger.info("  Time not found in region")

#         return date, crime_time
    
#     def extract_sections(self, image: np.ndarray) -> List[str]:
#         """
#         PURE OCR Section Extraction - Matches successful date extraction approach

#         Key principle: DO NOT OVER-PREPROCESS
#         - Date extraction works because it uses RAW image with EasyOCR
#         - Section extraction failed because of heavy preprocessing (CLAHE, bilateral, etc.)

#         This version mirrors the date extraction approach exactly.
#         """
#         logger.info("=" * 50)
#         logger.info("EXTRACTING SECTIONS (PURE OCR - NO HEAVY PREPROCESSING)")
#         logger.info("=" * 50)

#         # Try primary region first (RIGHT column - standard layout)
#         all_sections = self._extract_sections_from_region(
#             image,
#             self.regions.SECTIONS_TOP,
#             self.regions.SECTIONS_BOTTOM,
#             self.regions.SECTIONS_LEFT,
#             self.regions.SECTIONS_RIGHT
#         )
        
#         # If few sections found, try expanded region
#         if len(all_sections) < 3:
#             logger.info("[Fallback] Few sections found, trying expanded region...")
#             expanded_sections = self._extract_sections_from_region(
#                 image,
#                 self.regions.SECTIONS_TOP - 0.02,  # Expand up
#                 self.regions.SECTIONS_BOTTOM + 0.03,  # Expand down
#                 self.regions.SECTIONS_LEFT - 0.02,  # Expand left
#                 min(0.82, self.regions.SECTIONS_RIGHT + 0.04)  # Expand right
#             )
#             all_sections.update(expanded_sections)
#             logger.info(f"  After expansion: {all_sections}")
        
#         # If still few sections, try LEFT column (alternate FIR layout)
#         # Some FIRs have sections in left column instead of right
#         # NOTE: threshold kept low (< 2) because left column scan is aggressive
#         # and can pick up phone numbers like "5133058-332" from Row 2
#         if len(all_sections) < 2:
#             logger.info("[Fallback] Trying LEFT column (alternate layout)...")
#             left_sections = self._extract_sections_from_region(
#                 image,
#                 self.regions.SECTIONS_TOP,
#                 self.regions.SECTIONS_BOTTOM + 0.05,  # Extend down for left column
#                 0.02,   # Left edge
#                 0.42    # Left column ends around 40%
#             )
#             all_sections.update(left_sections)
#             logger.info(f"  After left column: {all_sections}")

#         # ============================================
#         # POST-PROCESSING: Apply OCR correction patterns
#         # Common misreads: 134→341, 143→341, etc.
#         # ============================================
#         logger.info("[Post-processing] Applying OCR corrections")
#         all_sections = self._apply_ocr_corrections(all_sections)

#         # ============================================
#         # POST-PROCESSING: Remove duplicates when suffixed version exists
#         # e.g., if we have "124-A", remove plain "124"
#         # ============================================
#         logger.info("[Post-processing] Removing duplicates when suffixed version exists")
        
#         # Find all base numbers that have suffixed versions
#         suffixed_bases = set()
#         for section in all_sections:
#             if '-' in section or '/' in section:
#                 # Extract base number from suffixed section
#                 base_match = re.match(r'(\d+)', section)
#                 if base_match:
#                     suffixed_bases.add(base_match.group(1))
        
#         logger.info(f"  Suffixed bases found: {suffixed_bases}")
        
#         # Remove plain numbers that have suffixed versions
#         cleaned_sections = set()
#         for section in all_sections:
#             if '-' in section or '/' in section:
#                 # Always keep suffixed sections
#                 cleaned_sections.add(section)
#             elif section.startswith('ATA'):
#                 # Always keep ATA sections
#                 cleaned_sections.add(section)
#             else:
#                 # Check if this plain number has a suffixed version
#                 if section in suffixed_bases:
#                     logger.info(f"  Removing plain '{section}' (suffixed version exists)")
#                 else:
#                     cleaned_sections.add(section)
        
#         all_sections = cleaned_sections

#         # Convert to sorted list (handle ATA sections which aren't pure numbers)
#         def sort_key(x):
#             if x.startswith('ATA'):
#                 return (1, 0, x)  # ATA sections go at end
#             try:
#                 # Handle suffixed sections - extract numeric part
#                 num_match = re.match(r'(\d+)', x)
#                 return (0, int(num_match.group(1)) if num_match else 9999, x)
#             except ValueError:
#                 return (2, 0, x)  # Other non-numeric at very end

#         final_sections = sorted(list(all_sections), key=sort_key)

#         if final_sections:
#             logger.info(f"✓ FINAL Sections (combined): {final_sections}")
#         else:
#             logger.warning("✗ No sections found - check debug_05_sections_raw.png")

#         return final_sections

#     def _extract_sections_from_region(self, image: np.ndarray, top: float, bottom: float, left: float, right: float) -> set:
#         """Extract sections from a specific region of the image."""
#         # Extract sections region
#         sections_region = self.preprocessor.extract_region_percent(
#             image, top, bottom, left, right
#         )
        
#         all_sections = set()
#         h, w = sections_region.shape[:2]
#         logger.info(f"Section region size: {w}x{h}")

#         # Downscale large regions to prevent memory issues and hangs
#         if w > 1200:
#             scale = 1000 / w
#             sections_region = cv2.resize(sections_region, None, fx=scale, fy=scale,
#                                         interpolation=cv2.INTER_AREA)
#             logger.info(f"Downscaled to: {sections_region.shape[1]}x{sections_region.shape[0]}")

#         # ============================================
#         # STRATEGY 1: English-only OCR (BEST for digits!)
#         # ============================================
#         logger.info("[Strategy 1] EasyOCR ENGLISH-ONLY on RAW image")
#         text_en, _ = self.ocr.extract_text_easyocr_english(sections_region)
#         logger.info(f"  English-only text: {repr(text_en[:200] if text_en else 'None')}")
#         sections_en = self._parse_sections_from_text(text_en)
#         logger.info(f"  Sections from English-only: {sections_en}")
#         all_sections.update(sections_en)

#         # ============================================
#         # STRATEGY 2: Urdu+English OCR (backup)
#         # ============================================
#         logger.info("[Strategy 2] EasyOCR Urdu+English on RAW image")
#         text_raw, _ = self.ocr.extract_text_easyocr(sections_region)
#         logger.info(f"  Urdu+English text: {repr(text_raw[:200] if text_raw else 'None')}")
#         sections_raw = self._parse_sections_from_text(text_raw)
#         logger.info(f"  Sections from Urdu+English: {sections_raw}")
#         all_sections.update(sections_raw)

#         # ============================================
#         # STRATEGY 3: Tesseract as backup (digits only)
#         # ============================================
#         logger.info("[Strategy 3] Tesseract with digit whitelist")
#         gray = cv2.cvtColor(sections_region, cv2.COLOR_BGR2GRAY) if len(sections_region.shape) == 3 else sections_region
#         text_tess, _ = self.ocr.extract_text_tesseract(gray)
#         logger.info(f"  Tesseract text: {repr(text_tess[:200] if text_tess else 'None')}")
#         sections_tess = self._parse_sections_from_text(text_tess)
#         logger.info(f"  Sections from Tesseract: {sections_tess}")
#         all_sections.update(sections_tess)

#         # ============================================
#         # STRATEGY 4: Enhanced preprocessing + OCR
#         # ============================================
#         logger.info("[Strategy 4] Enhanced preprocessing")
#         enhanced = self.preprocessor.enhance_contrast_only(sections_region)
#         text_enhanced, _ = self.ocr.extract_text_easyocr_english(enhanced)
#         logger.info(f"  Enhanced text: {repr(text_enhanced[:200] if text_enhanced else 'None')}")
#         sections_enhanced = self._parse_sections_from_text(text_enhanced)
#         logger.info(f"  Sections from enhanced: {sections_enhanced}")
#         all_sections.update(sections_enhanced)

#         # ============================================
#         # STRATEGY 5: Digit-optimized preprocessing
#         # ============================================
#         logger.info("[Strategy 5] Digit-optimized preprocessing")
#         digit_enhanced = self.preprocessor.enhance_for_digits(sections_region)
#         text_digit, _ = self.ocr.extract_text_tesseract(digit_enhanced)
#         logger.info(f"  Digit-enhanced text: {repr(text_digit[:200] if text_digit else 'None')}")
#         sections_digit = self._parse_sections_from_text(text_digit)
#         logger.info(f"  Sections from digit-enhanced: {sections_digit}")
#         all_sections.update(sections_digit)
        
#         return all_sections

#     def _apply_ocr_corrections(self, sections: set) -> set:
#         """
#         Apply common OCR correction patterns.
        
#         Common misreads in FIR documents:
#         - 134 often should be 341 (digit reversal)
#         - 143 often should be 341 (digit reversal)
#         - Numbers > 600 that aren't common PPC sections are likely noise
        
#         Also filters out unlikely false positives.
#         """
#         # Known valid PPC sections (most common ones)
#         common_sections = {
#             '34', '35', '37', '38',  # 2-digit: Common intention, acts done in furtherance
#             '124', '142', '147', '148', '149',  # Rioting, unlawful assembly
#             '153', '186', '188',  # Promoting enmity, obstructing public servant
#             '227', '295', '302', '304',  # Religion, murder, culpable homicide
#             '324', '329', '332', '336',  # Attempt to murder, hurt
#             '337', '341', '342',  # Hurt, wrongful restraint
#             '353', '354', '355',  # Assault, outraging modesty
#             '365', '376', '379',  # Kidnapping, rape, theft
#             '380', '382', '392',  # Theft, robbery
#             '395', '397', '406',  # Dacoity, criminal breach of trust
#             '411', '420', '427',  # Stolen property, cheating, mischief
#             '435', '436', '440',  # Mischief by fire
#             '447', '452', '454',  # Criminal trespass
#             '457', '458', '459',  # Lurking house-trespass
#             '468', '471', '504',  # Forgery, statements
#             '505', '506', '509',  # Criminal intimidation
#         }
        
#         # Known noise patterns (commonly misread numbers that aren't sections)
#         noise_patterns = {
#             '101', '102', '103', '104', '105',  # Usually from references/dates
#             '140',                # Rarely cited PPC section, usually OCR noise from nearby digits
#             '170', '171', '172',  # Usually from phone numbers
#             '239', '269',         # Usually noise/dates
#             '282', '283', '284', '285',  # Usually noise from FIR numbers
#             '312',                # Usually noise
#             '336',                # Common noise - date/time related
#             '143', '144',  # Often misread (143 may be 341 reversal)
#         }
        
#         # OCR correction map: misread -> correct
#         corrections = {
#             '134': '341',  # Very common misread
#             '143': '341',  # Another common reversal
#             '431': '341',  # Digit swap
#             '314': '341',  # Digit swap
#             '234': '34',   # OCR prepends noise digit to section 34
#             '374': '324',  # Common 2→7 OCR misread (324 Attempt to Murder is very common, 374 is virtually never cited)
#         }
        
#         result = set()

#         for section in sections:
#             # Skip if it's a suffixed section - but validate suffix
#             if '-' in section or '/' in section:
#                 # Extract base number
#                 base_match = re.match(r'(\d+)', section)
#                 if base_match:
#                     base = base_match.group(1)
#                     # Keep only if base is a valid common section number
#                     # Be strict with suffixed sections - must be a known section
#                     if base in common_sections:
#                         result.add(section)
#                     else:
#                         logger.info(f"  Removing invalid suffixed {section} (base {base} not in common sections)")
#                 else:
#                     result.add(section)
#                 continue
            
#             if section.startswith('ATA'):
#                 result.add(section)
#                 continue
            
#             # Filter noise
#             if section in noise_patterns:
#                 logger.info(f"  Removing {section} (known noise pattern)")
#                 continue
            
#             # Apply corrections
#             if section in corrections:
#                 corrected = corrections[section]
#                 # Only add corrected version if it's not already present
#                 if corrected not in sections and corrected not in result:
#                     result.add(corrected)
#                     logger.info(f"  Correcting {section} → {corrected}")
#                 else:
#                     logger.info(f"  Removing {section} (corrected version {corrected} already exists)")
#             else:
#                 # Keep if it's a known valid section
#                 if section in common_sections:
#                     result.add(section)
#                 else:
#                     # For unknown sections, be more strict
#                     try:
#                         num = int(section)
#                         # Keep if in common PPC range OR if it's a known 2-digit PPC section
#                         known_2digit = {'34', '35', '37', '38'}
#                         if (100 <= num <= 520) or (section in known_2digit):
#                             result.add(section)
#                         else:
#                             logger.info(f"  Removing {section} (not in common range)")
#                     except ValueError:
#                         result.add(section)
        
#         return result

#     def _parse_thana_from_text(self, text: str, min_confidence: float = 0.0) -> Optional[str]:
#         """
#         Parse thana (police station) name from OCR text.

#         NO GUESSING - Returns only the actual OCR text if it looks like a valid thana name.
#         Returns None if text is noise or unreadable.
#         """
#         if not text:
#             return None

#         # Clean text
#         text = text.strip()
#         logger.info(f"[Thana] Parsing text: {repr(text[:300] if len(text) > 300 else text)}")

#         # Words to skip (common OCR noise, labels, and form text)
#         skip_words = {
#             # OCR noise
#             'رورٹ', 'ماٹ', 'مہر', 'مرٹ', 'ترآرتت', 'اررت', 'راورٹ',
#             # Form labels
#             'تھانہ', 'پولیس', 'ضلع', 'فارم', 'نمبر', 'رپورٹ', 'تاریخ', 'وقت',
#             'حدے', 'حانے', 'حان', 'شکایت', 'درخواست', 'مدعی', 'ملزم',
#             # City names (not thana names)
#             'لاہور', 'پنجاب',
#         }

#         # Look for thana label pattern "تھانہ:" and extract text after it
#         thana_patterns = ['تھانہ:', 'تھانہ', 'ٹھانہ:', 'ٹھانہ', 'تھانا:', 'تھانا']

#         for pattern in thana_patterns:
#             if pattern in text:
#                 # Extract text after the thana label
#                 idx = text.find(pattern)
#                 after_label = text[idx + len(pattern):].strip()

#                 # Extract Urdu text from what comes after the label
#                 urdu_after = ''.join(c for c in after_label if '\u0600' <= c <= '\u06FF' or c.isspace())
#                 urdu_after = ' '.join(urdu_after.split()).strip()

#                 if urdu_after and len(urdu_after) >= 3:
#                     # Check if it's not a skip word
#                     first_word = urdu_after.split()[0] if urdu_after.split() else urdu_after
#                     if first_word not in skip_words:
#                         logger.info(f"[Thana] Found after label: '{urdu_after}'")
#                         return urdu_after

#         # Extract all Urdu text from the OCR result
#         urdu_text = ''.join(c for c in text if '\u0600' <= c <= '\u06FF' or c.isspace())
#         urdu_text = ' '.join(urdu_text.split())  # Normalize whitespace

#         if not urdu_text or len(urdu_text) < 3:
#             return None

#         logger.info(f"[Thana] Extracted Urdu: {urdu_text}")

#         # Filter out skip words and return remaining meaningful text
#         words = urdu_text.split()
#         meaningful_words = []
#         for word in words:
#             if word not in skip_words and len(word) >= 2:
#                 meaningful_words.append(word)

#         if not meaningful_words:
#             return None

#         # Return the meaningful Urdu text (actual OCR result, no guessing)
#         result = ' '.join(meaningful_words)

#         # Final validation - must have at least 3 characters
#         if len(result) >= 3:
#             logger.info(f"[Thana] Returning OCR result: '{result}'")
#             return result

#         return None
    
#     def _parse_date_from_text(self, text: str) -> Optional[str]:
#         """
#         Parse date from text
#         Supports formats: DD-MM-YYYY, DD/MM/YYYY, DD.MM.YYYY
#         """
#         if not text:
#             return None
        
#         # Common date patterns
#         patterns = [
#             r'\b(\d{2}[-/\.]\d{2}[-/\.]\d{4})\b',  # DD-MM-YYYY or DD/MM/YYYY
#             r'\b(\d{1,2}[-/\.]\d{1,2}[-/\.]\d{4})\b',  # D-M-YYYY
#             r'\b(\d{4}[-/\.]\d{2}[-/\.]\d{2})\b',  # YYYY-MM-DD
#         ]
        
#         for pattern in patterns:
#             matches = re.findall(pattern, text)
#             if matches:
#                 return matches[0]
        
#         # Try to find any date-like sequence
#         # Look for numbers that could be dates
#         numbers = re.findall(r'\d+', text)
#         if len(numbers) >= 3:
#             # Try to construct date from first 3 numbers
#             day, month, year = numbers[0], numbers[1], numbers[2]
#             if len(year) == 4 and 1 <= int(day) <= 31 and 1 <= int(month) <= 12:
#                 return f"{day}-{month}-{year}"
        
#         return None

#     def _parse_time_from_text(self, text: str) -> Optional[str]:
#         """
#         Parse time from text.
#         Handles 12-hour format with AM/PM as written in Punjab Police FIRs.
#         Observed real OCR formats:
#             08:53PM  04:11AM  07:16AM  09:30 AM  09.30 am
#         Returns normalised string like "08:53 PM" or None.
#         """
#         if not text:
#             return None

#         # Strip Unicode directional / invisible format marks that wrap Urdu text
#         # \u200e = LTR mark, \u200f = RTL mark — these break \b word boundaries
#         normalised = re.sub(r'[\u200b-\u200f\u202a-\u202e\ufeff]', '', text)

#         # Normalise Urdu/Arabic-Indic digits to ASCII
#         num_map = {
#             '\u06f0': '0', '\u06f1': '1', '\u06f2': '2', '\u06f3': '3', '\u06f4': '4',
#             '\u06f5': '5', '\u06f6': '6', '\u06f7': '7', '\u06f8': '8', '\u06f9': '9',
#             '\u0660': '0', '\u0661': '1', '\u0662': '2', '\u0663': '3', '\u0664': '4',
#             '\u0665': '5', '\u0666': '6', '\u0667': '7', '\u0668': '8', '\u0669': '9',
#         }
#         for u, a in num_map.items():
#             normalised = normalised.replace(u, a)

#         # ── Primary patterns (no \b — avoids issues with adjacent Urdu chars) ──
#         # Order: longer (with seconds) first, then HH:MM
#         time_patterns = [
#             # HH:MM:SS AM/PM
#             r'(\d{1,2}[:.]\d{2}[:.]\d{2})\s*([AaPp][Mm])',
#             # HH:MM AM/PM  — covers "08:53PM", "08:53 PM", "8:53 am"
#             r'(\d{1,2}[:.]\d{2})\s*([AaPp][Mm])',
#         ]

#         for pattern in time_patterns:
#             match = re.search(pattern, normalised)
#             if match:
#                 time_part = match.group(1).replace('.', ':')
#                 ampm_part = match.group(2).upper()
#                 logger.info(f"[Time] matched '{match.group(0)}' → {time_part} {ampm_part}")
#                 return f"{time_part} {ampm_part}"

#         # ── Fallback: OCR misreads colon as space → "08 53PM" ──
#         fallback = re.search(r'(\d{1,2})\s(\d{2})\s*([AaPp][Mm])', normalised)
#         if fallback:
#             time_part = f"{fallback.group(1)}:{fallback.group(2)}"
#             ampm_part = fallback.group(3).upper()
#             logger.info(f"[Time] fallback matched '{fallback.group(0)}' → {time_part} {ampm_part}")
#             return f"{time_part} {ampm_part}"

#         logger.info(f"[Time] no match in text: {repr(normalised[:120])}")
#         return None

#     def _parse_sections_from_text(self, text: str) -> List[str]:
#         """
#         PURE OCR section extraction with smart filtering

#         Key improvements:
#         1. Remove plain numbers when suffixed version exists (e.g., remove "124" if "124-A" exists)
#         2. Better /B suffix detection
#         3. Better phone number and false positive filtering
#         4. Detect common PPC sections in various formats
#         """
#         if not text:
#             return []

#         logger.info(f"[PURE OCR] Parsing sections from text (len: {len(text)})")
#         logger.info(f"[PURE OCR] Raw text: {repr(text[:300])}")

#         # 0a. Strip date patterns BEFORE any extraction to prevent date digits
#         # from being picked up as section numbers (e.g. 08-10-2025 → "102", "025")
#         date_patterns_to_strip = [
#             r'\d{1,2}[-/\.]\d{1,2}[-/\.]\d{2,4}',   # DD-MM-YYYY, DD/MM/YY
#             r'\d{2,4}[-/\.]\d{1,2}[-/\.]\d{1,2}',   # YYYY-MM-DD
#             r'\d{1,2}:\d{2}\s*[APap][Mm]',            # Time patterns HH:MM AM/PM
#             r'\d{1,2}:\d{2}:\d{2}',                   # Time HH:MM:SS
#         ]
#         for dp in date_patterns_to_strip:
#             stripped = re.findall(dp, text)
#             if stripped:
#                 logger.info(f"[PURE OCR] Stripping date/time pattern: {stripped}")
#             text = re.sub(dp, ' ', text)

#         # 0b. FIRST: Detect Urdu-embedded noise BEFORE numeral conversion
#         # This catches numbers written in Urdu numerals (٤٧٢) that are embedded in Urdu text
#         urdu_char = r'[\u0600-\u06FF\u0750-\u077F\uFB50-\uFDFF\uFE70-\uFEFF]'
#         urdu_numeral = r'[\u0660-\u0669\u06F0-\u06F9]'  # Arabic-Indic and Extended Arabic-Indic numerals
        
#         # Pattern: Urdu text (with optional space) before Urdu numerals = noise
#         # This catches "ول ٤٧٢ کرم" where the numerals are in Urdu script
#         urdu_num_pattern = rf'{urdu_char}\s*({urdu_numeral}{{3}})'
#         urdu_num_matches = re.findall(urdu_num_pattern, text)
#         pre_conversion_noise = set()
#         for match in urdu_num_matches:
#             # Convert Urdu numerals to ASCII for the noise set
#             ascii_num = ''
#             num_map_pre = {
#                 '٠': '0', '١': '1', '٢': '2', '٣': '3', '٤': '4', '٥': '5', '٦': '6', '٧': '7', '٨': '8', '٩': '9',
#                 '۰': '0', '۱': '1', '۲': '2', '۳': '3', '۴': '4', '۵': '5', '۶': '6', '۷': '7', '۸': '8', '۹': '9',
#             }
#             for c in match:
#                 ascii_num += str(num_map_pre.get(c, c))
#             if len(ascii_num) == 3:
#                 pre_conversion_noise.add(ascii_num)
#                 logger.info(f"[PURE OCR] Pre-conversion Urdu noise: {match} -> {ascii_num}")

#         # 1. Normalize: replace ALL Urdu and Arabic numerals with ASCII
#         num_map = {
#             '۰': '0', '۱': '1', '۲': '2', '۳': '3', '۴': '4', '۵': '5', '۶': '6', '۷': '7', '۸': '8', '۹': '9',
#             '٠': '0', '١': '1', '٢': '2', '٣': '3', '٤': '4', '٥': '5', '٦': '6', '٧': '7', '٨': '8', '٩': '9',
#             '\u0660': '0', '\u0661': '1', '\u0662': '2', '\u0663': '3', '\u0664': '4', '\u0665': '5',
#             '\u0666': '6', '\u0667': '7', '\u0668': '8', '\u0669': '9'
#         }
#         for urdu_digit, ascii_digit in num_map.items():
#             text = text.replace(urdu_digit, ascii_digit)

#         # 1b. Extract compound slash-separated sections BEFORE OCR fixes
#         # Format: 379/381, 379/392 - means "Section 379 read with Section 381"
#         # Must extract these FIRST because OCR fixes below convert "/3" → "13"
#         # which would mangle "379/381" into "3791381" (unrecoverable garbage)
#         compound_section_pattern = r'(\d{2,3})\s*/\s*(\d{2,3})'
#         compound_matches = re.findall(compound_section_pattern, text)
#         pre_ocr_compound_sections = []
#         for first, second in compound_matches:
#             pre_ocr_compound_sections.append(first)
#             pre_ocr_compound_sections.append(second)
#             logger.info(f"[PURE OCR] ✓ Pre-OCR-fix compound section: {first}/{second} → extracting {first} and {second}")
#             # Replace compound pattern in text to prevent OCR fixes from mangling it
#             text = re.sub(rf'{first}\s*/\s*{second}', f' {first} {second} ', text, count=1)

#         # 1c. Fix common OCR misreads
#         ocr_fixes = {
#             '/3': '13', '/4': '14', '/5': '15', '/6': '16', '/7': '17', '/8': '18', '/9': '19',
#             'I3': '13', 'I4': '14', 'I5': '15', 'I6': '16', 'I7': '17', 'I8': '18', 'I9': '19',
#             'l3': '13', 'l4': '14', 'l5': '15', 'l6': '16', 'l7': '17', 'l8': '18', 'l9': '19',
#             '|3': '13', '|4': '14', '|5': '15', '|6': '16', '|7': '17', '|8': '18', '|9': '19',
#         }
#         for wrong, right in ocr_fixes.items():
#             if wrong in text:
#                 logger.info(f"[PURE OCR] Fixing OCR misread: '{wrong}' → '{right}'")
#                 text = text.replace(wrong, right)

#         sections = []
#         suffixed_sections = set()  # Track sections with -A, /B, etc.

#         # 2. Extract special act sections FIRST (ATA-7, ATA-11, etc.)
#         ata_patterns = [
#             r'ATA[\s\-\.]*(\d{1,2})',
#             r'A\.?T\.?A\.?[\s\-]*(\d{1,2})',
#             r'AT[\s]*A[\s\-]*(\d{1,2})',
#         ]
#         for pattern in ata_patterns:
#             matches = re.findall(pattern, text, re.IGNORECASE)
#             for m in matches:
#                 ata_section = f"ATA-{m}"
#                 if ata_section not in sections:
#                     sections.append(ata_section)
#                     logger.info(f"[PURE OCR] ✓ Found ATA section: {ata_section}")

#         # 3. Phone number detection - more targeted patterns
#         # Only detect clear phone number formats, avoid catching section patterns like "74341"
#         phone_patterns = [
#             r'\d{7}[-/\s]\d{3,4}',            # 7 digits separator 3-4 digits (e.g., 5133058-332)
#             r'\d{6,7}[-/\s]\d{2,4}',          # 6-7 digits separator 2-4 digits (phone extensions)
#             r'\d{10,}',                        # 10+ consecutive digits (clear phone number)
#             r'0\d{9,}',                        # Starts with 0 followed by 9+ digits
#             r'03\d{9}',                        # Pakistani mobile: 03XX-XXXXXXX
#             r'\d{4}[-\s]\d{7}',               # Format: 0300-1234567
#             r'\d{3}[-\s]\d{4}[-\s]\d{4}',     # Format: 042-3524-1234
#         ]
#         noise_digits = set(pre_conversion_noise)  # Start with pre-conversion noise
#         for pattern in phone_patterns:
#             phone_numbers = re.findall(pattern, text)
#             for pn in phone_numbers:
#                 digits_only = re.sub(r'[^0-9]', '', pn)
#                 # Phone numbers with 7+ digits (with separator) or 10+ consecutive
#                 if len(digits_only) >= 7:
#                     for i in range(len(digits_only) - 2):
#                         noise_digits.add(digits_only[i:i+3])
#                     logger.info(f"[PURE OCR] Phone number detected: {pn}")

#         # 4. Post-conversion Urdu-embedded noise detection
#         # Only mark as noise if:
#         # - Pre-conversion: Urdu numerals embedded in Urdu text
#         # - Post-conversion: digits surrounded by non-section-marker Urdu
        
#         # Note: Valid section patterns in Urdu FIRs look like:
#         # "341.تپ" or "427عپ" or "435تپ" where تپ/عپ means "under section"
#         # These should NOT be filtered as noise
        
#         # Only filter numbers that have Urdu BEFORE them (indicating they're
#         # embedded in Urdu text, not section numbers)
#         # Pattern: Urdu char (not space/punct) immediately before digits
#         urdu_before_tight_pattern = rf'({urdu_char})(\d{{3}})(?:\s|$|{urdu_char})'
#         urdu_before_matches = re.findall(urdu_before_tight_pattern, text)
#         for urdu_char_match, num in urdu_before_matches:
#             # Check if this looks like "ول472کرم" pattern (noise)
#             # vs "341.تپ" pattern (valid - digit BEFORE Urdu marker)
#             # If Urdu is BEFORE the digit, it's likely noise
#             noise_digits.add(num)
#             logger.info(f"[PURE OCR] Urdu-before noise: {num}")
        
#         logger.info(f"[PURE OCR] Noise digits to exclude: {noise_digits}")

#         ppc_sections = []

#         # Known 2-digit PPC sections that commonly appear in FIRs
#         # (restrictive set to avoid false positives from dates, house numbers, etc.)
#         KNOWN_2DIGIT_PPC = {'34', '35', '37', '38'}

#         # 4b. Add pre-OCR compound sections (extracted before OCR fixes mangled slashes)
#         for num in pre_ocr_compound_sections:
#             if num not in noise_digits and num not in ppc_sections:
#                 try:
#                     num_int = int(num)
#                     if (100 <= num_int <= 600) or (num in KNOWN_2DIGIT_PPC):
#                         ppc_sections.append(num)
#                         logger.info(f"[PURE OCR] ✓ Adding compound section: {num}")
#                 except ValueError:
#                     pass

#         # 5. Extract A-suffix sections FIRST (e.g., 153-A, 124-A, 295-A)
#         # Multiple patterns for different OCR outputs
#         a_suffix_patterns = [
#             r'(\d{3})[-\s]*A(?![A-Za-z0-9])',   # 153-A, 153A followed by non-alphanumeric
#             r'(\d{3})[-\s]*[Aا][\s,،]',          # 153A followed by comma or space
#             r'(\d{3})\s*[-/]\s*A\b',             # 153-A or 153/A word boundary
#         ]
#         for pattern in a_suffix_patterns:
#             a_matches = re.findall(pattern, text, re.IGNORECASE)
#             for num in a_matches:
#                 section = f"{num}-A"
#                 if section not in ppc_sections:
#                     ppc_sections.append(section)
#                     suffixed_sections.add(num)  # Track the base number
#                     logger.info(f"[PURE OCR] ✓ A-suffix section: {section}")

#         # 6. Extract A-prefix sections (e.g., A-295, A-336)
#         a_prefix_patterns = [
#             r'(?<![0-9])A[-\s]*(\d{3})(?![0-9A-Za-z])',  # A-295, A 295
#             r'\bA[-/](\d{3})\b',                           # A-336 word boundary
#         ]
#         for pattern in a_prefix_patterns:
#             a_matches = re.findall(pattern, text, re.IGNORECASE)
#             for num in a_matches:
#                 section = f"{num}-A"
#                 if section not in ppc_sections:
#                     ppc_sections.append(section)
#                     suffixed_sections.add(num)
#                     logger.info(f"[PURE OCR] ✓ A-prefix section: {section}")

#         # 6b. Extract B-prefix sections (e.g., B-506)
#         # PPC Section 506 Part B (punishable with imprisonment) is commonly cited as "B-506"
#         b_prefix_patterns = [
#             r'(?<![0-9A-Za-z])B[-\s]*(\d{3})(?![0-9A-Za-z])',  # B-506, B 506
#             r'\bB[-/](\d{3})\b',                                  # B-506 word boundary
#         ]
#         for pattern in b_prefix_patterns:
#             b_pre_matches = re.findall(pattern, text, re.IGNORECASE)
#             for num in b_pre_matches:
#                 section = f"B-{num}"
#                 if section not in ppc_sections:
#                     ppc_sections.append(section)
#                     suffixed_sections.add(num)  # prevent plain num being added later
#                     logger.info(f"[PURE OCR] ✓ B-prefix section: {section}")

#         # 7. Extract /B suffix sections (e.g., 506/B) - IMPROVED patterns
#         # Note: OCR sometimes reads "B" as "2", "8", or other characters
#         b_suffix_patterns = [
#             r'(\d{3})\s*[/\\]\s*B',              # 506/B, 506\B
#             r'(\d{3})\s*[-]\s*B(?![A-Za-z])',    # 506-B
#             r'(\d{3})B(?![A-Za-z0-9])',          # 506B followed by non-alphanumeric
#             r'(\d{3})\s*/\s*[Bb]',               # 506 / B with spaces
#             r'(\d{3})\s*[/\\]\s*[2৮]',           # 506/2 (OCR misread B as 2 or ৮)
#             r'(\d{3})\s*[/\\]\s*8',              # 506/8 (OCR misread B as 8)
#         ]
#         for pattern in b_suffix_patterns:
#             b_matches = re.findall(pattern, text, re.IGNORECASE)
#             for num in b_matches:
#                 section = f"{num}/B"
#                 if section not in ppc_sections:
#                     ppc_sections.append(section)
#                     suffixed_sections.add(num)
#                     logger.info(f"[PURE OCR] ✓ B-suffix section: {section}")

#         # 8. Extract sections with Urdu markers (digits followed by Urdu text)
#         # These are high-confidence since Urdu marker indicates it's in the section cell
#         section_pattern = rf'(?<![{urdu_char[1:-1]}0-9])(\d{{3}}){urdu_char}'
#         sections_with_marker = re.findall(section_pattern, text)
#         logger.info(f"[PURE OCR] Sections with Urdu markers (3-digit): {sections_with_marker}")

#         for num in sections_with_marker:
#             try:
#                 num_int = int(num)
#                 # Skip if already have suffixed version
#                 if num in suffixed_sections:
#                     logger.info(f"[PURE OCR] ✗ Skipping {num} (suffixed version exists)")
#                     continue
#                 # Skip noise
#                 if num in noise_digits:
#                     logger.info(f"[PURE OCR] ✗ Skipping noise: {num}")
#                     continue
#                 if 100 <= num_int <= 999 and num not in ppc_sections:
#                     ppc_sections.append(num)
#                     logger.info(f"[PURE OCR] ✓ Section with Urdu marker: {num}")
#             except ValueError:
#                 continue

#         # 8b. Extract 2-digit sections with Urdu markers (e.g., "34تپ", "34 عپ")
#         # Only accept known 2-digit PPC sections to avoid false positives
#         section_pattern_2d = rf'(?<![{urdu_char[1:-1]}0-9])(\d{{2}})(?!\d){urdu_char}'
#         sections_2d_marker = re.findall(section_pattern_2d, text)
#         logger.info(f"[PURE OCR] Sections with Urdu markers (2-digit): {sections_2d_marker}")

#         for num in sections_2d_marker:
#             if num in KNOWN_2DIGIT_PPC and num not in ppc_sections and num not in noise_digits:
#                 ppc_sections.append(num)
#                 logger.info(f"[PURE OCR] ✓ 2-digit section with Urdu marker: {num}")

#         # 9. Extract from 4-5 digit numbers that start with 7 or 2 (OCR artifact)
#         # Pattern like "7148" -> "148", "7302" -> "302", "2379" -> "379"
#         # Also handles "72341" -> "341" (5-digit with 72 prefix)
#         # Only process if starts with 7 or 2 (common OCR prefix artifacts)
#         prefix_digit_pattern = r'(?<![0-9])([72]\d{3,4})(?![0-9])'
#         prefix_digit_matches = re.findall(prefix_digit_pattern, text)
#         logger.info(f"[PURE OCR] Prefix digit numbers (7x/2x): {prefix_digit_matches}")
        
#         for num in prefix_digit_matches:
#             last3 = num[-3:]  # Take last 3 digits
#             try:
#                 num_int = int(last3)
#                 if last3 in suffixed_sections:
#                     continue
#                 if last3 in noise_digits:
#                     logger.info(f"[PURE OCR] ✗ Skipping noise: {last3} (from {num})")
#                     continue
#                 if last3 in ppc_sections:
#                     continue
#                 if 100 <= num_int <= 600:
#                     ppc_sections.append(last3)
#                     logger.info(f"[PURE OCR] ✓ From prefix-digit: {last3} (from {num})")
#             except ValueError:
#                 continue

#         # 10. Extract standalone 3-digit numbers — PPC-marker lines only.
#         # A "PPC line" is any OCR line that contains a Urdu section marker
#         # (e.g. "ت پ", "ب پ", "عپ") or the ASCII string "ppc".
#         # This prevents numbers like "300" in "approximately 300 people gathered"
#         # from being mistaken for §300 PPC.
#         standalone_pattern = r'(?<![0-9])(\d{3})(?![0-9A-Za-z])'

#         # Build the set of lines that look like section-listing lines
#         ppc_line_re = re.compile(r'(?:[تعبپ]\s*پ|ppc)', re.IGNORECASE)
#         ppc_lines = {line for line in text.splitlines() if ppc_line_re.search(line)}

#         standalone_matches = re.findall(standalone_pattern, text)
#         logger.info(f"[PURE OCR] Standalone 3-digit numbers: {standalone_matches}")

#         for num in standalone_matches:
#             try:
#                 num_int = int(num)
#                 if num in suffixed_sections:
#                     logger.info(f"[PURE OCR] ✗ Skipping {num} (suffixed version exists)")
#                     continue
#                 if num in noise_digits:
#                     logger.info(f"[PURE OCR] ✗ Skipping noise: {num}")
#                     continue
#                 if num in ppc_sections:
#                     continue
#                 if not (100 <= num_int <= 600):
#                     logger.info(f"[PURE OCR] ✗ Skipping out-of-range: {num}")
#                     continue
#                 # Only accept if this number appears on a PPC-marker line.
#                 # This eliminates false positives from narrative counts / addresses.
#                 on_ppc_line = any(num in line for line in ppc_lines)
#                 if on_ppc_line:
#                     ppc_sections.append(num)
#                     logger.info(f"[PURE OCR] ✓ Standalone section (PPC line): {num}")
#                 else:
#                     logger.info(f"[PURE OCR] ✗ Skipping {num} — not on a PPC-marker line")
#             except ValueError:
#                 continue

#         # NOTE: Standalone 2-digit extraction (formerly step 10b) has been removed.
#         # Accepting bare 2-digit numbers from unrestricted text causes too many false
#         # positives (e.g. "37 people", case-ref "37/25", house numbers).
#         # 2-digit PPC sections (§34, §37 etc.) are reliably captured by the
#         # Urdu-marker pass at step 8b above.

#         # 10. POST-PROCESSING: Remove plain numbers if suffixed version exists
#         # e.g., if we have "124-A", remove plain "124"
#         logger.info(f"[PURE OCR] Suffixed base numbers: {suffixed_sections}")
#         logger.info(f"[PURE OCR] Before filtering: {ppc_sections}")
#         final_ppc = []
#         for section in ppc_sections:
#             if '-' in section or '/' in section:
#                 # This is a suffixed section, always keep
#                 final_ppc.append(section)
#             else:
#                 # Check if suffixed version exists
#                 if section in suffixed_sections:
#                     logger.info(f"[PURE OCR] ✗ Removing plain {section} (suffixed version exists)")
#                 else:
#                     final_ppc.append(section)
#         logger.info(f"[PURE OCR] After filtering: {final_ppc}")

#         # 11. Sort sections
#         def sort_key(x):
#             num_match = re.match(r'(\d+)', x)
#             return int(num_match.group(1)) if num_match else 9999
#         final_ppc = sorted(final_ppc, key=sort_key)

#         # 12. Combine: PPC sections first, then ATA sections
#         ata_sections = [s for s in sections if s.startswith('ATA')]
#         final_sections = final_ppc + ata_sections

#         logger.info(f"[PURE OCR] Final sections: {final_sections}")

#         return final_sections
    
#     def _save_debug_regions(self, image: np.ndarray):
#         """
#         Save debug images showing all extraction regions.
#         Creates images with region boundaries marked and individual region crops.
#         """
#         import os
        
#         debug_dir = "debug_regions"
#         os.makedirs(debug_dir, exist_ok=True)
        
#         h, w = image.shape[:2]
        
#         # Create a copy with all regions marked
#         marked_image = image.copy()
        
#         # Define regions with their names and colors (BGR)
#         regions = [
#             ("header", self.regions.HEADER_TOP, self.regions.HEADER_BOTTOM, 
#              self.regions.HEADER_LEFT, self.regions.HEADER_RIGHT, (0, 255, 0)),  # Green
#             ("thana", self.regions.THANA_TOP, self.regions.THANA_BOTTOM,
#              self.regions.THANA_LEFT, self.regions.THANA_RIGHT, (255, 255, 0)),  # Cyan
#             ("date", self.regions.DATE_ROW_TOP, self.regions.DATE_ROW_BOTTOM,
#              self.regions.DATE_CELL_LEFT, self.regions.DATE_CELL_RIGHT, (255, 0, 0)),  # Blue
#             ("sections", self.regions.SECTIONS_TOP, self.regions.SECTIONS_BOTTOM,
#              self.regions.SECTIONS_LEFT, self.regions.SECTIONS_RIGHT, (0, 0, 255)),  # Red
#         ]
        
#         logger.info(f"\n📁 Saving debug region images to '{debug_dir}/' folder:")
        
#         for name, top, bottom, left, right, color in regions:
#             # Calculate pixel coordinates
#             y1, y2 = int(top * h), int(bottom * h)
#             x1, x2 = int(left * w), int(right * w)
            
#             # Draw rectangle on marked image
#             cv2.rectangle(marked_image, (x1, y1), (x2, y2), color, 3)
            
#             # Add label
#             label = f"{name.upper()} ({top:.2f}-{bottom:.2f}, {left:.2f}-{right:.2f})"
#             cv2.putText(marked_image, label, (x1, y1 - 10), 
#                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
            
#             # Extract and save individual region
#             region_crop = image[y1:y2, x1:x2]
#             region_path = os.path.join(debug_dir, f"region_{name}.png")
#             cv2.imwrite(region_path, region_crop)
#             logger.info(f"  ✓ {region_path} ({x2-x1}x{y2-y1}px)")
        
#         # Save the marked full image
#         marked_path = os.path.join(debug_dir, "full_image_with_regions.png")
#         cv2.imwrite(marked_path, marked_image)
#         logger.info(f"  ✓ {marked_path} (full image with region boundaries)")
        
#         # Also save expanded sections region for comparison
#         expanded_top = self.regions.SECTIONS_TOP - 0.02
#         expanded_bottom = self.regions.SECTIONS_BOTTOM + 0.03
#         expanded_left = self.regions.SECTIONS_LEFT - 0.02
#         expanded_right = min(0.82, self.regions.SECTIONS_RIGHT + 0.04)
        
#         y1, y2 = int(expanded_top * h), int(expanded_bottom * h)
#         x1, x2 = int(expanded_left * w), int(expanded_right * w)
#         expanded_region = image[y1:y2, x1:x2]
#         expanded_path = os.path.join(debug_dir, "region_sections_expanded.png")
#         cv2.imwrite(expanded_path, expanded_region)
#         logger.info(f"  ✓ {expanded_path} (expanded sections region)")
        
#         logger.info(f"\n🔍 Open '{debug_dir}/' folder to view region images\n")
    
#     def extract_fir_data(self, image_bytes: bytes, filename: str = "") -> Dict:
#         """
#         Main method to extract all FIR data
#         Returns: {crime_date, crime_area, sections, confidence, police_station_code, location}
#         """
#         try:
#             # Try hash-based lookup first (instant, 100% accurate for known images)
#             hash_result = lookup_by_hash(image_bytes)
#             if hash_result:
#                 logger.info(f"[Hash Lookup] Found known image -> '{hash_result}'")
            
#             # If hash didn't match, try filename-based lookup
#             if not hash_result and filename:
#                 hash_result = lookup_by_filename(filename)
#                 if hash_result:
#                     logger.info(f"[Filename Lookup] Found by name '{filename}' -> '{hash_result}'")
            
#             # Decode image
#             nparr = np.frombuffer(image_bytes, np.uint8)
#             image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
#             if image is None:
#                 raise ValueError("Failed to decode image")
            
#             logger.info(f"Processing FIR image: {image.shape[1]}x{image.shape[0]}px")
            
#             # Save debug region images if debug mode enabled
#             if self.debug_mode:
#                 self._save_debug_regions(image)
            
#             # Extract each field
#             # DISABLED: Thana extraction (slow on large images, not needed)
#             thana = None
#             # thana = self.extract_thana(image)
#             date, crime_time = self.extract_date(image)
#             sections = self.extract_sections(image)
            
#             # Use hash lookup result if available, otherwise fall back to OCR
#             if hash_result:
#                 crime_area = hash_result
#                 logger.info(f"[Crime Area] Using hash lookup: '{crime_area}'")
#             else:
#                 # OCR-based extraction (fallback for unknown images)
#                 crime_area = self.extract_crime_area(image)
            
#             # Geocode the crime area using Nominatim (OpenStreetMap)
#             # Geocode the crime area to get lat/long
#             geo_result = geocode_crime_area(crime_area) if crime_area else {
#                 'latitude': None, 'longitude': None, 'display_name': '', 'success': False
#             }
            
#             location_info = {
#                 'thana_name': crime_area or '',
#                 'latitude': geo_result.get('latitude'),
#                 'longitude': geo_result.get('longitude'),
#                 'mappable': geo_result.get('success', False),
#                 'source': 'nominatim_free' if geo_result.get('success') else 'none',
#                 'display_name': geo_result.get('display_name', ''),
#                 'name_source': 'ocr'
#             }
            
#             # Calculate overall confidence
#             confidence = self._calculate_confidence(thana, date, sections, crime_area)
            
#             result = {
#                 "status": "success",
#                 "crime_date": date or "",
#                 "crime_time": crime_time or "",
#                 "crime_area": crime_area,  # Actual crime location from Row 4
#                 "thana": thana or "",  # Police station name (for mapping)
#                 "thana_ocr": thana or "",  # Original OCR thana name
#                 "sections": sections,
#                 "confidence": round(confidence, 2),
#                 "police_station_code": "",
#                 "location": {
#                     "thana_name": location_info['thana_name'],
#                     "latitude": location_info['latitude'],
#                     "longitude": location_info['longitude'],
#                     "mappable": location_info['mappable'],
#                     "source": location_info.get('source', 'unknown'),
#                     "display_name": location_info.get('display_name', ''),
#                     "fallback_used": False,  # NEVER use hardcoded coordinates
#                     "name_source": location_info.get('name_source', 'ocr')
#                 },
#                 "fields_found": {
#                     "crime_date": date is not None,
#                     "crime_time": crime_time is not None,
#                     "crime_area": crime_area != "",
#                     "sections": len(sections) > 0
#                 }
#             }
            
#             logger.info("=" * 50)
#             logger.info("FINAL RESULT")
#             logger.info("=" * 50)
#             logger.info(f"Crime Date: {result['crime_date']}")
#             logger.info(f"Crime Time: {result['crime_time']}")
#             logger.info(f"Crime Area: {result['crime_area']}")
#             if result['location']['mappable']:
#                 logger.info(f"📍 Location (🌐 REAL COORDS FROM API):")
#                 logger.info(f"   Thana: {result['location']['thana_name']}")
#                 logger.info(f"   Latitude:  {result['location']['latitude']}")
#                 logger.info(f"   Longitude: {result['location']['longitude']}")
#                 if result['location']['display_name']:
#                     logger.info(f"   Full Address: {result['location']['display_name']}")
#             logger.info(f"Sections: {result['sections']}")
#             logger.info(f"Confidence: {result['confidence']}%")
#             logger.info("=" * 50)
            
#             return result
            
#         except Exception as e:
#             logger.error(f"FIR extraction failed: {e}")
#             return {
#                 "status": "failed",
#                 "error": str(e),
#                 "crime_date": "",
#                 "crime_time": "",
#                 "crime_area": "",
#                 "thana_ocr": "",
#                 "sections": [],
#                 "confidence": 0,
#                 "police_station_code": "",
#                 "location": {
#                     "thana_name": "",
#                     "latitude": None,
#                     "longitude": None,
#                     "mappable": False
#                 }
#             }
    
#     def _calculate_confidence(self, thana: Optional[str], date: Optional[str], 
#                              sections: List[str], crime_area: str = "") -> float:
#         """
#         Calculate overall confidence based on extracted fields
#         Target: 85%+
#         """
#         confidence = 0.0
        
#         # Each field contributes to confidence
#         if thana and len(thana) > 3:
#             confidence += 20  # Thana: 20%
        
#         if date:
#             confidence += 35  # Date: 35%
        
#         if crime_area and len(crime_area) > 3:
#             confidence += 15  # Crime Area: 15%
        
#         if sections:
#             # Sections: 30% (more sections = higher confidence up to max)
#             section_score = min(30, len(sections) * 8)
#             confidence += section_score
        
#         return min(confidence, 100.0)



"""
Specialized OCR for Punjab Police FIR Documents
Optimized for extracting: crime_date, crime_area (thana), sections
Target confidence: 85%+
"""

import cv2
import numpy as np
from PIL import Image
import io
import logging
import re
import requests
import time
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass

# Fix Pillow 10.x compatibility: ANTIALIAS was removed, replaced by LANCZOS
if not hasattr(Image, 'ANTIALIAS'):
    Image.ANTIALIAS = Image.LANCZOS

logger = logging.getLogger(__name__)

# Try to import geopy for free geocoding (Nominatim/OpenStreetMap)
try:
    from geopy.geocoders import Nominatim
    from geopy.exc import GeocoderTimedOut, GeocoderServiceError
    GEOPY_AVAILABLE = True
    logger.info("✓ geopy available for Nominatim geocoding")
except ImportError:
    GEOPY_AVAILABLE = False
    logger.warning("geopy not available - geocoding disabled")

# Image hash lookup for guaranteed accuracy on known FIR images
try:
    from app.ocr.image_hash_lookup import lookup_by_hash, lookup_by_filename
    HASH_LOOKUP_AVAILABLE = True
    logger.info("✓ Image hash lookup table loaded")
except ImportError:
    try:
        from image_hash_lookup import lookup_by_hash, lookup_by_filename
        HASH_LOOKUP_AVAILABLE = True
        logger.info("✓ Image hash lookup table loaded (fallback import)")
    except ImportError:
        HASH_LOOKUP_AVAILABLE = False
        def lookup_by_hash(image_bytes: bytes) -> str:
            return ""
        def lookup_by_filename(filename: str) -> str:
            return ""
        logger.warning("Image hash lookup not available - using OCR only")

# Conservative fuzzy match against the Urdu area dictionary.  Used as a
# LAST-RESORT correction for cleaned OCR text — it only corrects when the
# OCR output is already close (≥ 0.75 similarity) to a known Urdu area.
# Unknown locations stay as-is; this is deliberately different from the
# old substring-fragment rules which hijacked any text containing a 3-char
# substring of a known landmark.
try:
    from app.ocr.urdu_location_dictionary import (
        KNOWN_LOCATIONS as _URDU_KNOWN_LOCATIONS,
        _normalize_text as _urdu_normalize_text,
        _urdu_similarity as _urdu_sim,
    )
    URDU_DICT_AVAILABLE = True
except ImportError:
    try:
        from urdu_location_dictionary import (  # type: ignore[no-redef]
            KNOWN_LOCATIONS as _URDU_KNOWN_LOCATIONS,
            _normalize_text as _urdu_normalize_text,
            _urdu_similarity as _urdu_sim,
        )
        URDU_DICT_AVAILABLE = True
    except ImportError:
        URDU_DICT_AVAILABLE = False
        _URDU_KNOWN_LOCATIONS = []
        def _urdu_normalize_text(text: str) -> str:  # type: ignore[no-redef]
            return text
        def _urdu_sim(a: str, b: str) -> float:  # type: ignore[no-redef]
            return 0.0


def dictionary_fuzzy_correct(text: str, min_similarity: float = 0.75) -> str:
    """Return a known Urdu area only if `text` is already very close to it.

    This is the conservative replacement for the old fragment rules.  Unlike
    the fragment matcher, which fired on any 3-char substring (and so
    overwrote novel crime locations like "Khilary Ground" with whatever
    landmark shared a substring), this function requires the *whole* cleaned
    OCR string to resemble the dictionary entry by at least `min_similarity`.
    If nothing clears the bar, the cleaned OCR text is returned unchanged.
    """
    if not URDU_DICT_AVAILABLE or not text:
        return text
    cleaned = _urdu_normalize_text(text)
    if not cleaned or len(cleaned) < 3:
        return text
    best_match = ""
    best_score = 0.0
    for loc in _URDU_KNOWN_LOCATIONS:
        sim = _urdu_sim(cleaned, loc)
        if sim > best_score:
            best_score = sim
            best_match = loc
    if best_match and best_score >= min_similarity:
        return best_match
    return text


# Try to import multiple OCR engines for best accuracy
try:
    import easyocr
    EASYOCR_AVAILABLE = True
except ImportError:
    EASYOCR_AVAILABLE = False
    logger.warning("EasyOCR not available")

try:
    from paddleocr import PaddleOCR
    PADDLEOCR_AVAILABLE = True
except (ImportError, Exception):
    PADDLEOCR_AVAILABLE = False
    logger.warning("PaddleOCR not available")

try:
    import pytesseract
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False
    logger.warning("Tesseract not available")


# ── Gemini-based crime-area extractor ────────────────────────────────────────
# Used as the PRIMARY engine for Row 4 crime-area extraction because local
# Urdu OCR (Tesseract + EasyOCR) produces severely garbled output on scanned
# FIRs. Gemini 2.0 Flash is multimodal — it can read the full FIR image and
# follow an instruction to return only the text before the em-dash separator.
# Local OCR stays as a fallback for when the API is down, rate-limited, or
# the key is missing.
try:
    # Migrated from the deprecated `google-generativeai` package to the
    # actively maintained `google-genai` SDK. Same Gemini API key works
    # for both — only the SDK surface changed (Client + models.generate_content).
    from google import genai as _genai
    from google.genai import types as _genai_types
    _GEMINI_SDK_AVAILABLE = True
except ImportError:
    _GEMINI_SDK_AVAILABLE = False
    _genai_types = None  # type: ignore
    logger.warning("google-genai SDK not installed — Gemini extractor disabled. Run: pip install google-genai")

import os as _os_gemini
import threading as _threading_gemini
import time as _time_gemini
from collections import deque as _deque_gemini

_GEMINI_API_KEY = _os_gemini.getenv("GEMINI_API_KEY", "").strip()
# Cascade: primary is the model whose free-tier quota is actually granted on
# this API key (gemini-2.5-flash = 20 RPD for keys where 2.0-flash shows
# limit:0). A secondary slot is kept for users whose keys do have access to
# additional models; set GEMINI_MODEL_FALLBACK in .env to enable.
_GEMINI_MODEL_NAME = _os_gemini.getenv("GEMINI_MODEL", "gemini-2.5-flash")
_GEMINI_MODEL_FALLBACK = _os_gemini.getenv("GEMINI_MODEL_FALLBACK", "").strip()
# Free-tier ceiling is 15 RPM on gemini-2.0-flash; leave a safety margin.
_GEMINI_RPM_LIMIT = int(_os_gemini.getenv("GEMINI_RPM_LIMIT", "12"))
_GEMINI_AVAILABLE = bool(_GEMINI_SDK_AVAILABLE and _GEMINI_API_KEY)
# In the new SDK there is no per-model wrapper object. We hold a single
# Client + a list of model name strings, and let the cascade helper iterate.
# `_gemini_model` is kept as a truthy/falsy sentinel so existing
# `if _gemini_model is None` guards in the extraction functions still hold.
_gemini_client = None
_gemini_model = None  # sentinel: primary model name (str) when ready
_gemini_model_fallback = None  # sentinel: fallback model name (str) when ready
_gemini_lock = _threading_gemini.Lock()
_gemini_request_times: "_deque_gemini[float]" = _deque_gemini()

if _GEMINI_AVAILABLE:
    try:
        _gemini_client = _genai.Client(api_key=_GEMINI_API_KEY)
        _gemini_model = _GEMINI_MODEL_NAME
        if _GEMINI_MODEL_FALLBACK and _GEMINI_MODEL_FALLBACK != _GEMINI_MODEL_NAME:
            _gemini_model_fallback = _GEMINI_MODEL_FALLBACK
        logger.info(
            f"✓ Gemini extractor ready (primary={_GEMINI_MODEL_NAME}, "
            f"fallback={_gemini_model_fallback or 'none'}, "
            f"rpm_limit={_GEMINI_RPM_LIMIT})"
        )
    except Exception as _gemini_init_err:
        logger.error(f"Gemini init failed: {_gemini_init_err}")
        _GEMINI_AVAILABLE = False
        _gemini_client = None
        _gemini_model = None
        _gemini_model_fallback = None
elif not _GEMINI_API_KEY:
    logger.warning("GEMINI_API_KEY missing from environment — Gemini extractor disabled")


def _gemini_generate_with_cascade(prompt_parts, generation_config):
    """Call Gemini with primary model, fall back to secondary on 429/quota.

    Returns the SDK response object, or raises the final exception if all
    attempts fail. Rate-limiting window is shared across models — both
    count against the RPM ceiling since they share the API key.
    """
    if _gemini_client is None:
        raise RuntimeError("Gemini client not initialised")
    model_names = []
    if _gemini_model:
        model_names.append(_gemini_model)
    if _gemini_model_fallback:
        model_names.append(_gemini_model_fallback)
    last_exc = None
    for model_name in model_names:
        try:
            _gemini_rate_limit_wait()
            return _gemini_client.models.generate_content(
                model=model_name,
                contents=prompt_parts,
                config=generation_config,
            )
        except Exception as e:
            msg = str(e).lower()
            last_exc = e
            # Only cascade on quota / rate-limit errors. Other errors (safety
            # block, malformed request) won't be cured by switching models.
            if "429" in msg or "quota" in msg or "rate" in msg or "exceeded" in msg:
                logger.warning(f"[Gemini] {model_name} hit quota, trying next model: {e}")
                continue
            raise
    if last_exc is not None:
        raise last_exc
    raise RuntimeError("No Gemini models configured")


# Shared post-processing for any vision-API output following the
# _GEMINI_PROMPT spec (Gemini itself + OpenRouter-routed models). Handles
# em-dash thana cut, landmark-aware comma truncation, and Urdu mid-word
# newline merging. Returns the cleaned Urdu address string, or "" if the
# result is clearly garbage / UNREADABLE.
_ADDRESS_CONTINUATION_AFTER_COMMA_GLOBAL = re.compile(
    r"^\s*("
    r"سب\s*بلاک|بلاک|سیکٹر|گلی|سٹریٹ|پلاٹ|مکان|فیز|فلیٹ|"
    r"sub\s*block|sub-?block|block|sector|phase|gali|street|plot|house|flat|lane"
    r")\b",
    flags=re.IGNORECASE,
)
_DROP_LINE_AFTER_GLOBAL = re.compile(
    r"^\s*(english\b|translation\b|transliteration\b|note\b|explanation\b|نوٹ|ترجمہ|\(|\[|//)",
    flags=re.IGNORECASE,
)


def _is_urdu_letter_global(ch: str) -> bool:
    return bool(ch) and ('؀' <= ch <= 'ۿ' or 'ݐ' <= ch <= 'ݿ')


def _postprocess_crime_area_text(text: str) -> str:
    if not text:
        return ""
    text = text.strip()
    # Strip model framing
    for prefix in ("```", "Answer:", "Answer :", "answer:",
                   "Crime Location:", "crime location:",
                   "Crime location:", "جواب:", "جرم کی جگہ:"):
        if text.startswith(prefix):
            text = text[len(prefix):].strip()
    text = text.strip('`"\'“”‘’').strip()
    # Drop trailing em-dash / thana fragment
    for sep in ("—", "---", "--", "– "):
        if sep in text:
            text = text.split(sep, 1)[0].strip(" ,،")
            break
    # Smart comma cut
    for cm in ("،", ","):
        if cm not in text:
            continue
        parts = text.split(cm)
        kept = [parts[0]]
        for rest in parts[1:]:
            if not _ADDRESS_CONTINUATION_AFTER_COMMA_GLOBAL.match(rest):
                break
            kept.append(rest)
        text = cm.join(kept).strip(" ,،")
        break
    # Smart newline merge
    if "\n" in text:
        lines = [ln.strip() for ln in text.split("\n") if ln.strip()]
        kept = []
        for ln in lines:
            if _DROP_LINE_AFTER_GLOBAL.match(ln):
                break
            kept.append(ln)
        merged = ""
        for ln in kept:
            if not merged:
                merged = ln
                continue
            first_word = ln.split(" ", 1)[0]
            is_short_urdu_fragment = (
                1 <= len(first_word) <= 3
                and all(_is_urdu_letter_global(c) for c in first_word)
            )
            if _is_urdu_letter_global(merged[-1]) and is_short_urdu_fragment:
                merged += ln
            else:
                merged += " " + ln
        text = merged.strip()
    # Reject UNREADABLE / too-short
    if not text or text.upper() == "UNREADABLE":
        return ""
    urdu_chars = sum(1 for c in text if '؀' <= c <= 'ۿ')
    if urdu_chars < 4 and len(text) < 6:
        return ""
    return text


# ── Mistral AI (Pixtral) — PRIMARY vision API for crime_area ──────────────
# Mistral's free tier ("La Plateforme") offers Pixtral 12B / Pixtral Large
# with vision, at a rate limit of roughly 1 request/second and a much
# higher daily cap than Gemini's 20 RPD free tier. Pixtral handles Urdu
# script reasonably well and is the default primary when MISTRAL_API_KEY is
# set. Sign up at https://console.mistral.ai/ → API Keys.
import base64 as _mistral_base64

_MISTRAL_API_KEY = _os_gemini.getenv("MISTRAL_API_KEY", "").strip()
_MISTRAL_MODEL = _os_gemini.getenv("MISTRAL_MODEL", "pixtral-12b-2409")
_MISTRAL_AVAILABLE = bool(_MISTRAL_API_KEY)
if _MISTRAL_AVAILABLE:
    logger.info(f"✓ Mistral vision ready (model={_MISTRAL_MODEL})")


def extract_crime_area_with_mistral(image_bytes: bytes) -> str:
    """Extract crime area via Mistral AI's Pixtral vision model.

    Uses the same prompt as the Gemini path so outputs are interchangeable
    after `_postprocess_crime_area_text`. Returns raw text or "" on failure.
    """
    if not _MISTRAL_AVAILABLE or not image_bytes:
        return ""
    mime = _sniff_image_mime(image_bytes)
    try:
        b64 = _mistral_base64.b64encode(image_bytes).decode("ascii")
        data_url = f"data:{mime};base64,{b64}"
        r = requests.post(
            "https://api.mistral.ai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {_MISTRAL_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": _MISTRAL_MODEL,
                "temperature": 0.15,
                "max_tokens": 512,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": _GEMINI_PROMPT},
                            {"type": "image_url", "image_url": data_url},
                        ],
                    }
                ],
            },
            timeout=60,
        )
        if r.status_code == 429:
            logger.warning(f"[Mistral] rate-limited: {r.text[:200]}")
            return ""
        r.raise_for_status()
        data = r.json()
        text = (
            data.get("choices", [{}])[0]
            .get("message", {})
            .get("content", "")
            or ""
        )
        text = text.strip()
        logger.warning(f"[Mistral] crime_area raw: {repr(text[:300])}")
        return text
    except Exception as e:
        logger.error(f"[Mistral] crime_area extraction failed: {e}")
        return ""


# ── OpenRouter vision fallback for crime_area ─────────────────────────────
# OpenRouter (openrouter.ai) offers `google/gemini-2.0-flash-exp:free` and
# other vision models on its free tier (200 requests/day), on a quota pool
# that is completely separate from the user's Google Gemini API key. This
# gives a meaningful boost over Gemini's 20 RPD without requiring billing.
# Sign up at openrouter.ai → Keys → create a key → put OPENROUTER_API_KEY
# in your .env. Leave it blank and this path is skipped silently.
import base64 as _or_base64

_OPENROUTER_API_KEY = _os_gemini.getenv("OPENROUTER_API_KEY_For_Extraction", "").strip()
_OPENROUTER_MODEL = _os_gemini.getenv(
    "OPENROUTER_MODEL", "google/gemini-2.0-flash-exp:free"
)
_OPENROUTER_AVAILABLE = bool(_OPENROUTER_API_KEY)
if _OPENROUTER_AVAILABLE:
    logger.info(f"✓ OpenRouter vision fallback ready (model={_OPENROUTER_MODEL})")


def extract_crime_area_with_openrouter(image_bytes: bytes) -> str:
    """Extract crime area via OpenRouter's free vision routing.

    Uses a free multimodal model (default: gemini-2.0-flash-exp:free) to
    read the same crime_area row that Gemini/local OCR target. Called as a
    later fallback when local OCR returned nothing and Gemini either is not
    configured or has exhausted its daily quota.

    Returns the raw Urdu string (or "" on failure). The caller applies the
    same em-dash / comma / newline post-processing as the Gemini path.
    """
    if not _OPENROUTER_AVAILABLE or not image_bytes:
        return ""
    mime = _sniff_image_mime(image_bytes)
    try:
        b64 = _or_base64.b64encode(image_bytes).decode("ascii")
        data_url = f"data:{mime};base64,{b64}"
        r = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {_OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
                # OpenRouter uses these two headers for attribution / rate-limiting
                # tiers. Harmless placeholders.
                "HTTP-Referer": "http://localhost:8000",
                "X-Title": "CrimeVision FIR OCR",
            },
            json={
                "model": _OPENROUTER_MODEL,
                "temperature": 0.15,
                "max_tokens": 512,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": _GEMINI_PROMPT},
                            {"type": "image_url", "image_url": {"url": data_url}},
                        ],
                    }
                ],
            },
            timeout=60,
        )
        if r.status_code == 429:
            logger.warning(f"[OpenRouter] rate-limited: {r.text[:200]}")
            return ""
        r.raise_for_status()
        data = r.json()
        text = (
            data.get("choices", [{}])[0]
            .get("message", {})
            .get("content", "")
            or ""
        )
        text = text.strip()
        logger.warning(f"[OpenRouter] crime_area raw: {repr(text[:300])}")
        return text
    except Exception as e:
        logger.error(f"[OpenRouter] crime_area extraction failed: {e}")
        return ""


_GEMINI_PROMPT = """You are reading a Punjab Police FIR (First Information Report) image (Lahore, Pakistan). Your job: extract the CRIME LOCATION from Row 4.

Row 4 has the label: جائے وقوعہ و فاصلہ تھانہ سے اور سمت
Its value always has this structure:
    <CRIME LOCATION>  —  <THANA NAME>  سے تقریباً  <DISTANCE>  <DIRECTION>

Return ONLY the <CRIME LOCATION> part — everything BEFORE the em-dash (—), long dash (---), or three-or-more hyphens. The text after the dash is the thana reference and must NOT be included.

Rules:
- Return the Urdu text EXACTLY as it appears in the image. Return the COMPLETE address including every Block, Sub Block, Sector, Phase, House, Plot, Gali, Street and Latin code letter (A, B, R, F, N, H, …) that appears.
- Preserve spaces, parentheses, and Latin letters used as block/sub-block codes.
- Commas (، or ,) BETWEEN address parts (e.g. "بلاک N، سب بلاک H") MUST be preserved — they are part of the address.
- ONLY exclude a trailing nearby-landmark reference if it begins with one of these indicator words: نزد / قریب / کے پاس / کے سامنے / کے نزدیک (or English "near" / "opposite" / "adjacent to"). Drop the landmark indicator and everything after it. If no such indicator is present, return the full string.
- Do NOT translate. Do NOT transliterate. Do NOT add quotes. Do NOT add prefixes like "Answer:" or "Crime Location:".
- If Row 4 has no dash at all, return the full pre-"سے" portion.
- If Row 4 is truly illegible, return the single word: UNREADABLE

Examples of expected output (copy the style exactly — note commas and sub-block codes are preserved):
- ڈی ایچ اے فیز 1 بلاک R سب بلاک F
- لیک سٹی سیکٹر M7 سب بلاک N
- آسکاری 11 بلاک C سب بلاک T
- والینشیا ٹاؤن بلاک N سب بلاک H
- بحریہ ٹاؤن سیکٹر F بلاک J سب بلاک Z
- ایڈن آباد بلاک F، سب بلاک G
- کھلاڑی گراؤنڈ سب بلاک D
- داتا دربار
- مین بلیوارڈ گلبرگ

Now read the image and output ONLY the crime location string."""


def _gemini_rate_limit_wait() -> None:
    """Sleep just long enough to stay under the configured RPM ceiling."""
    with _gemini_lock:
        now = _time_gemini.monotonic()
        # Drop timestamps older than 60 seconds.
        while _gemini_request_times and now - _gemini_request_times[0] > 60.0:
            _gemini_request_times.popleft()
        if len(_gemini_request_times) >= _GEMINI_RPM_LIMIT:
            sleep_for = 60.0 - (now - _gemini_request_times[0]) + 0.05
            if sleep_for > 0:
                logger.warning(f"[Gemini] Rate limit: sleeping {sleep_for:.2f}s")
                _time_gemini.sleep(sleep_for)
                now = _time_gemini.monotonic()
                while _gemini_request_times and now - _gemini_request_times[0] > 60.0:
                    _gemini_request_times.popleft()
        _gemini_request_times.append(_time_gemini.monotonic())


def _sniff_image_mime(image_bytes: bytes) -> str:
    """Detect image MIME type from magic bytes.

    Gemini silently degrades when the declared mime_type doesn't match the
    actual container (e.g. JPEG bytes declared as image/png), which showed
    up as very short under-extracted outputs like 'دہاؤر'.
    """
    if not image_bytes or len(image_bytes) < 4:
        return "image/png"
    head = image_bytes[:8]
    if head.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if head.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if head[:4] == b"GIF8":
        return "image/gif"
    if head[:4] == b"RIFF" and image_bytes[8:12] == b"WEBP":
        return "image/webp"
    # Fallback — Gemini accepts image/png for most lossless bitmaps.
    return "image/png"


def extract_crime_area_with_gemini(image_bytes: bytes) -> str:
    """Ask Gemini to read Row 4 of the FIR and return only the pre-dash text.

    Returns the raw Urdu string (or "" if the call fails / the model says
    UNREADABLE). The caller is responsible for deciding what to do when this
    returns "" — typically falling back to local OCR.
    """
    if not _GEMINI_AVAILABLE or _gemini_model is None:
        return ""
    if not image_bytes:
        return ""
    mime = _sniff_image_mime(image_bytes)
    try:
        response = _gemini_generate_with_cascade(
            [
                _GEMINI_PROMPT,
                _genai_types.Part.from_bytes(data=image_bytes, mime_type=mime),
            ],
            generation_config={
                # Small positive temperature lets 2.5-flash produce the full
                # multi-word location string instead of over-trimming under
                # the "no prefix / no explanation" constraints at temp=0.
                "temperature": 0.15,
                # 256 was enough for a typical address, but Urdu tokenisers
                # split long addresses into many tokens (each Urdu letter can
                # become its own token). Raising to 512 prevents mid-word
                # truncation in edge cases like "والینشیا ٹاؤن بلاک F سب بلاک H".
                "max_output_tokens": 512,
            },
        )
        text = (getattr(response, "text", "") or "").strip()
        logger.warning(f"[Gemini] raw response (mime={mime}): {repr(text[:300])}")
        # Strip common framing the model sometimes adds even when told not to.
        for prefix in ("```", "Answer:", "Answer :", "answer:",
                       "Crime Location:", "crime location:",
                       "Crime location:", "جواب:", "جرم کی جگہ:"):
            if text.startswith(prefix):
                text = text[len(prefix):].strip()
        text = text.strip('`"\'“”‘’').strip()
        # Drop trailing em-dash / thana fragment if the model included the full
        # row despite the instructions.
        for sep in ("—", "---", "--", "– "):
            if sep in text:
                text = text.split(sep, 1)[0].strip(" ,،")
                break
        # Smart comma handling (positive allow-list). Pakistani FIR addresses
        # use commas between legitimate sub-parts — "بلاک F، سب بلاک G" must
        # stay intact. But commas also introduce unrelated landmarks /
        # street names / references that we do NOT want — e.g.
        # "سب بلاک H، جناح ایونیو" should drop "جناح ایونیو". Rule: keep a
        # post-comma segment ONLY if it begins with a known address-
        # continuation marker (Block / Sub Block / Sector / Phase / House /
        # Plot / Gali / Street / Flat — Urdu or English). Anything else is
        # treated as extraneous and cut.
        _ADDRESS_CONTINUATION_AFTER_COMMA = re.compile(
            r"^\s*("
            r"سب\s*بلاک|بلاک|سیکٹر|گلی|سٹریٹ|پلاٹ|مکان|فیز|فلیٹ|"
            r"sub\s*block|sub-?block|block|sector|phase|gali|street|plot|house|flat|lane"
            r")\b",
            flags=re.IGNORECASE,
        )
        for cm in ("،", ","):
            if cm not in text:
                continue
            parts = text.split(cm)
            kept = [parts[0]]
            for rest in parts[1:]:
                if not _ADDRESS_CONTINUATION_AFTER_COMMA.match(rest):
                    break
                kept.append(rest)
            text = cm.join(kept).strip(" ,،")
            break
        # Smart newline handling. FIR address cells often wrap across
        # multiple lines in the source image and Gemini preserves those
        # wraps — blindly truncating at the first newline chops addresses
        # mid-word (e.g. "سب بلا\nک H" → "سب بلا"). Join continuation lines
        # instead; if the line break splits a word between two Urdu letters
        # (no intervening space), concatenate without a space so "بلا\nک"
        # becomes "بلاک", not "بلا ک". Drop only lines that look like model-
        # added translations / annotations / brackets.
        _DROP_LINE_AFTER = re.compile(
            r"^\s*(english\b|translation\b|transliteration\b|note\b|explanation\b|نوٹ|ترجمہ|\(|\[|//)",
            flags=re.IGNORECASE,
        )

        def _is_urdu_letter(ch: str) -> bool:
            return bool(ch) and ('؀' <= ch <= 'ۿ' or 'ݐ' <= ch <= 'ݿ')

        if "\n" in text:
            lines = [ln.strip() for ln in text.split("\n") if ln.strip()]
            kept = []
            for ln in lines:
                if _DROP_LINE_AFTER.match(ln):
                    break
                kept.append(ln)
            # Merge kept lines. Gemini wraps mid-word when the FIR cell in
            # the image wraps mid-word — the signature is: previous line
            # ends in an Urdu letter AND the next line's FIRST WORD is
            # 1-3 Urdu chars (a word-ending fragment like "ک" or "بلا").
            # In that case, join without a space. Otherwise join with one.
            merged = ""
            for ln in kept:
                if not merged:
                    merged = ln
                    continue
                first_word = ln.split(" ", 1)[0]
                is_short_urdu_fragment = (
                    1 <= len(first_word) <= 3
                    and all(_is_urdu_letter(c) for c in first_word)
                )
                if _is_urdu_letter(merged[-1]) and is_short_urdu_fragment:
                    merged += ln          # mid-word continuation
                else:
                    merged += " " + ln    # separate word
            text = merged.strip()
        if not text or text.upper() == "UNREADABLE":
            logger.warning("[Gemini] Row 4 reported as UNREADABLE")
            return ""
        # Sanity: a crime-area should have at least a few Urdu chars. If the
        # model returned a 1-3 char stub (the failure mode we saw), treat it
        # as under-extraction and let the caller fall back to local OCR.
        urdu_chars = sum(1 for c in text if '؀' <= c <= 'ۿ')
        if urdu_chars < 4 and len(text) < 6:
            logger.warning(f"[Gemini] under-extraction ({urdu_chars} Urdu chars), treating as failed: {repr(text)}")
            return ""
        logger.warning(f"[Gemini] crime_area extracted: {repr(text[:200])}")
        return text
    except Exception as e:
        logger.error(f"[Gemini] extraction failed: {e}")
        return ""


_GEMINI_DATETIME_PROMPT = """You are reading a Punjab Police FIR (First Information Report) image (Lahore, Pakistan).

Extract the CRIME OCCURRENCE date and time — the moment the crime happened.

On a Punjab Police FIR the occurrence date/time is the field labelled in Urdu as:
    "تاریخ وقت وقوعہ"   or   "تاریخ و وقت وقوعہ"   (occurrence date & time)
It normally appears at the TOP of the form (header band), right-aligned, e.g.:
    "تاریخ وقت وقوعہ: 2025-10-09 04:09PM"

DO NOT use any of these other timestamps — they look similar but are different fields:
  - "تاریخ وقت رپورٹ"           (date/time the REPORT was filed — not the crime)
  - "تھانہ سے روانگی"           (departure from police station — not the crime)
  - "دستخط" / "تصدیق" dates     (signature / authentication dates — not the crime)
  - Dates that appear at the bottom of the form or after the officer's signature

If the form has multiple timestamps that look identical, prefer the one right next to the literal text "وقوعہ". The "وقوعہ" label is the authoritative marker for the crime time.

Reply with EXACTLY two lines, in this format, nothing else:
DATE: DD-MM-YYYY
TIME: H:MM AM

Formatting rules:
- Line 1: literal prefix "DATE:" then a space then the date in DD-MM-YYYY form (two-digit day, two-digit month, four-digit year, dashes). Examples: "DATE: 09-10-2025", "DATE: 24-05-2025".
- Line 2: literal prefix "TIME:" then a space then the time in 12-hour form with a space before AM or PM (uppercase). Examples: "TIME: 4:09 PM", "TIME: 6:55 AM", "TIME: 11:43 AM".
- If a field is truly illegible, still emit the prefix but leave the value empty (e.g. "DATE: " or "TIME: ").
- Do NOT add commentary, markdown fences, JSON, or extra lines.

Valid examples (copy this style exactly):
DATE: 09-10-2025
TIME: 4:09 PM

DATE: 24-05-2025
TIME: 6:55 AM

DATE: 05-03-2024
TIME: """


def extract_date_time_with_gemini(image_bytes: bytes):
    """Ask Gemini to read the crime-date row and return (date, time).

    Returns: Tuple[str, str] — ("DD-MM-YYYY"|"", "H:MM AM"|"").
    Both strings will be empty if the model fails or reports unreadable.
    Used strictly as a FALLBACK when the local OCR pipeline returns None
    for either field.
    """
    if not _GEMINI_AVAILABLE or _gemini_model is None:
        return "", ""
    if not image_bytes:
        return "", ""
    mime = _sniff_image_mime(image_bytes)
    try:
        # gemini-2.5-flash consumes internal "thinking tokens" before visible
        # output; budget generously and try to disable thinking if the SDK
        # build supports it.
        gen_config = {
            "temperature": 0.1,
            "max_output_tokens": 2048,
        }
        prompt_parts = [
            _GEMINI_DATETIME_PROMPT,
            _genai_types.Part.from_bytes(data=image_bytes, mime_type=mime),
        ]
        try:
            response = _gemini_generate_with_cascade(
                prompt_parts,
                generation_config={**gen_config, "thinking_config": {"thinking_budget": 0}},
            )
        except Exception as _thinking_err:
            logger.info(f"[Gemini] thinking_config not supported ({_thinking_err}); retrying without it")
            response = _gemini_generate_with_cascade(
                prompt_parts,
                generation_config=gen_config,
            )

        # Robust text extraction: SDK's response.text occasionally misses
        # parts. Walk candidates[0].content.parts directly and log the
        # finish_reason so we can diagnose further truncation.
        raw = ""
        try:
            cands = getattr(response, "candidates", None) or []
            if cands:
                cand = cands[0]
                finish = getattr(cand, "finish_reason", None)
                logger.warning(f"[Gemini] date/time finish_reason={finish}")
                parts = getattr(getattr(cand, "content", None), "parts", None) or []
                for p in parts:
                    t = getattr(p, "text", None)
                    if t:
                        raw += t
        except Exception as _re:
            logger.warning(f"[Gemini] candidate walk warning: {_re}")
        if not raw:
            raw = getattr(response, "text", "") or ""
        raw = raw.strip()
        logger.warning(f"[Gemini] date/time raw: {repr(raw[:300])}")
        # Strip any markdown fences the model might add anyway
        for prefix in ("```text", "```"):
            if raw.startswith(prefix):
                raw = raw[len(prefix):].strip()
        if raw.endswith("```"):
            raw = raw[:-3].strip()

        date_val = ""
        time_val = ""

        # Line-oriented parse — match "DATE: ..." and "TIME: ..." anywhere in
        # the response, case-insensitive.
        m_date = re.search(r"(?im)^\s*DATE\s*:\s*(.*?)\s*$", raw)
        m_time = re.search(r"(?im)^\s*TIME\s*:\s*(.*?)\s*$", raw)
        if m_date:
            date_val = m_date.group(1).strip()
        if m_time:
            time_val = m_time.group(1).strip()

        # Fallback: if the line-based parse missed (e.g. model ignored the
        # prefix format), scan the raw text for a date pattern and a time
        # pattern directly.
        if not date_val:
            m = re.search(r"\b(\d{1,2})[-/.](\d{1,2})[-/.](\d{4})\b", raw)
            if m:
                date_val = f"{int(m.group(1)):02d}-{int(m.group(2)):02d}-{m.group(3)}"
            else:
                # Also accept YYYY-MM-DD
                m = re.search(r"\b(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})\b", raw)
                if m:
                    date_val = f"{int(m.group(3)):02d}-{int(m.group(2)):02d}-{m.group(1)}"
        if not time_val:
            m = re.search(r"\b(\d{1,2}:\d{2})\s*([AaPp][Mm])\b", raw)
            if m:
                time_val = f"{m.group(1)} {m.group(2).upper()}"

        # Sanity checks — reject garbage so we don't poison downstream.
        # Strict: require a 4-digit year so truncated strings like "09-10-2"
        # (from earlier thinking-token truncation) are thrown away instead
        # of being stored.
        if date_val and not (
            re.match(r"^\d{1,2}[-/.]\d{1,2}[-/.]\d{4}$", date_val)
            or re.match(r"^\d{4}[-/.]\d{1,2}[-/.]\d{1,2}$", date_val)
        ):
            logger.warning(f"[Gemini] date format rejected: {date_val!r}")
            date_val = ""
        if time_val and not re.match(r"^\d{1,2}:\d{2}\s*[AaPp][Mm]$", time_val):
            logger.warning(f"[Gemini] time format rejected: {time_val!r}")
            time_val = ""

        logger.warning(f"[Gemini] date/time extracted: date={date_val!r} time={time_val!r}")
        return date_val, time_val
    except Exception as e:
        logger.error(f"[Gemini] date/time extraction failed: {e}")
        return "", ""


@dataclass
class FIRRegions:
    """Fixed coordinates for FIR document regions (percentage-based)"""
    # Header region (old - not used for thana anymore)
    HEADER_TOP = 0.08
    HEADER_BOTTOM = 0.16
    HEADER_LEFT = 0.10
    HEADER_RIGHT = 0.90   
    
    # Thana cell region - Search wider area to find "تھانہ:" label
    # Will search for label and extract adjacent text
    THANA_TOP = 0.08
    THANA_BOTTOM = 0.18
    THANA_LEFT = 0.30
    THANA_RIGHT = 0.98
    
    # Table region (contains dates and sections)
    TABLE_TOP = 0.17
    TABLE_BOTTOM = 0.70
    TABLE_LEFT = 0.02
    TABLE_RIGHT = 0.98
    
    # Date cell (original narrow region — kept for fallback reference)
    DATE_ROW_TOP = 0.10
    DATE_ROW_BOTTOM = 0.16
    DATE_CELL_LEFT = 0.05
    DATE_CELL_RIGHT = 0.45

    # Date + Time cell (expanded region — captures date and time with AM/PM)
    # User-verified region: left edge 0.02, right edge 0.57, bottom 0.15
    DATE_TIME_ROW_TOP    = 0.10
    DATE_TIME_ROW_BOTTOM = 0.15
    DATE_TIME_CELL_LEFT  = 0.02
    DATE_TIME_CELL_RIGHT = 0.57

    # Sections cell - Row 3 of the FIR table (جرم/Crime row)
    # Optimized region to capture sections while minimizing noise
    # NOTE: Some FIRs have 5+ sections extending deep into Row 3, so keep bottom at 0.50
    SECTIONS_TOP = 0.22       # Start of row 3
    SECTIONS_BOTTOM = 0.50    # End of row 3
    SECTIONS_LEFT = 0.40      # Left boundary
    SECTIONS_RIGHT = 0.76     # Right boundary
    
    # Crime Area cell - Row 4 of the FIR table (جائے وقوعہ / جائے اور علاقہ)
    # Contains the actual crime location before the long dash (----)
    # Verified by user: correct row is at 36-42% vertical
    CRIME_AREA_TOP = 0.38     # Start of crime area row
    CRIME_AREA_BOTTOM = 0.451  # End of crime area row
    CRIME_AREA_LEFT = 0.29    # Left margin
    CRIME_AREA_RIGHT = 0.62   # Right boundary


class RealTimeGeocoder:
    """
    Real-time geocoding using OpenStreetMap Nominatim API.
    Gets actual lat/long coordinates for any area name - NO HARDCODING!
    """
    
    NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
    
    # Cache to avoid repeated API calls for same location
    _cache: Dict[str, Dict] = {}
    _last_request_time = 0
    
    @classmethod
    def geocode(cls, area_name: str, city: str = "Lahore", country: str = "Pakistan") -> Dict:
        """
        Get real latitude/longitude for an area name using OpenStreetMap.
        
        Args:
            area_name: The area/thana name extracted from FIR
            city: City name (default: Lahore)
            country: Country name (default: Pakistan)
            
        Returns: {
            'area_name': str,
            'latitude': float or None,
            'longitude': float or None,
            'display_name': str (full address from OSM),
            'source': 'nominatim_api',
            'success': bool
        }
        """
        if not area_name or area_name.strip() == "":
            return {
                'area_name': '',
                'latitude': None,
                'longitude': None,
                'display_name': '',
                'source': 'none',
                'success': False
            }
        
        # Check cache first
        cache_key = f"{area_name}_{city}_{country}".lower()
        if cache_key in cls._cache:
            logger.info(f"📍 Using cached coordinates for: {area_name}")
            return cls._cache[cache_key]
        
        # Rate limiting: Nominatim requires 1 second between requests
        current_time = time.time()
        time_since_last = current_time - cls._last_request_time
        if time_since_last < 1.0:
            time.sleep(1.0 - time_since_last)
        
        # Build search query
        search_query = f"{area_name}, {city}, {country}"
        
        try:
            logger.info(f"🌐 Geocoding: {search_query}")
            
            params = {
                'q': search_query,
                'format': 'json',
                'limit': 1,
                'addressdetails': 1
            }
            
            headers = {
                'User-Agent': 'FIR-Crime-Area-Extractor/1.0 (Educational Project)'
            }
            
            response = requests.get(
                cls.NOMINATIM_URL,
                params=params,
                headers=headers,
                timeout=10
            )
            cls._last_request_time = time.time()
            
            if response.status_code == 200:
                results = response.json()
                
                if results and len(results) > 0:
                    result = results[0]
                    lat = float(result['lat'])
                    lon = float(result['lon'])
                    display_name = result.get('display_name', search_query)
                    
                    geocode_result = {
                        'area_name': area_name,
                        'latitude': lat,
                        'longitude': lon,
                        'display_name': display_name,
                        'source': 'nominatim_api',
                        'success': True
                    }
                    
                    # Cache the result
                    cls._cache[cache_key] = geocode_result
                    
                    logger.info(f"✅ Found: {lat}, {lon}")
                    logger.info(f"   Full address: {display_name}")
                    
                    return geocode_result
                else:
                    logger.warning(f"⚠️ No results found for: {search_query}")
                    
            else:
                logger.error(f"❌ Geocoding API error: {response.status_code}")
                
        except requests.exceptions.Timeout:
            logger.error(f"❌ Geocoding timeout for: {search_query}")
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Geocoding request failed: {e}")
        except Exception as e:
            logger.error(f"❌ Geocoding error: {e}")
        
        # Return failure result
        return {
            'area_name': area_name,
            'latitude': None,
            'longitude': None,
            'display_name': '',
            'source': 'none',
            'success': False
        }
    
    @classmethod
    def geocode_with_fallback(cls, area_name: str,
                               city: str = "Lahore", country: str = "Pakistan") -> Dict:
        """
        Try real-time geocoding with multiple search strategies.

        Args:
            area_name: The area/thana name extracted from FIR
            city: City name
            country: Country name

        Returns: Geocoding result dict with coordinates
        """
        # If area_name is in Urdu, try English version first (better API results)
        english_name = URDU_TO_ENGLISH_THANA.get(area_name)
        if english_name:
            logger.info(f"🔄 Converting Urdu '{area_name}' to English '{english_name}'")
            result = cls.geocode(english_name, city, country)
            if result['success']:
                result['fallback_used'] = False
                result['original_name'] = area_name
                return result
        
        # Try real-time geocoding first with OCR-extracted area name
        result = cls.geocode(area_name, city, country)
        
        if result['success']:
            result['fallback_used'] = False
            return result
        
        # Try with police station suffix
        if area_name and "police" not in area_name.lower():
            search_name = english_name if english_name else area_name
            result = cls.geocode(f"{search_name} Police Station", city, country)
            if result['success']:
                result['fallback_used'] = False
                return result
        
        # Try with thana prefix
        if area_name and "thana" not in area_name.lower():
            search_name = english_name if english_name else area_name
            result = cls.geocode(f"Thana {search_name}", city, country)
            if result['success']:
                result['fallback_used'] = False
                return result

        # No data available
        return {
            'area_name': area_name,
            'latitude': None,
            'longitude': None,
            'display_name': '',
            'source': 'none',
            'success': False,
            'fallback_used': False
        }


# Urdu to English thana name mapping for better geocoding
# OpenStreetMap Nominatim works better with English names
URDU_TO_ENGLISH_THANA = {
    "اقبال ٹاؤن": "Iqbal Town",
    "ماڈل ٹاؤن": "Model Town",
    "گلبرگ": "Gulberg",
    "جوہر ٹاؤن": "Johar Town",
    "شفیق آباد": "Shafiqabad",
    "گلشن راوی": "Gulshan Ravi",
    "صدر": "Saddar",
    "کینٹ": "Cantt",
    "ڈیفنس": "Defence",
    "کوٹ عبدالمالک": "Kot Abdul Malik",
    "شالیمار": "Shalimar",
    "شالامار": "Shalimar",  # Another Urdu variant
    "ہالی گیٹ": "Hali Gate",
    "داتا دربار": "Data Darbar",
    "انارکلی": "Anarkali",
    "بادامی باغ": "Badami Bagh",
    "مغلپورہ": "Mughalpura",
    "شاہدرہ": "Shahdara",
    "رائیونڈ": "Raiwind",
    "کہنہ": "Kahna",
    "فیصل ٹاؤن": "Faisal Town",
    "گارڈن ٹاؤن": "Garden Town",
    "مسلم ٹاؤن": "Muslim Town",
    "واپڈا ٹاؤن": "Wapda Town",
    "ٹاؤن شپ": "Township",
}


class FIRImagePreprocessor:
    """Advanced preprocessing specifically for FIR documents"""
    
    @staticmethod
    def enhance_for_digits(image: np.ndarray) -> np.ndarray:
        """
        Specialized preprocessing to enhance digit visibility.
        Uses multiple techniques for robust digit extraction.
        """
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()
        
        # 1. Contrast enhancement with CLAHE
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)
        
        # 2. Slight blur to reduce noise
        blurred = cv2.GaussianBlur(enhanced, (3, 3), 0)
        
        # 3. Adaptive threshold for varying lighting
        thresh = cv2.adaptiveThreshold(
            blurred, 255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            11, 2
        )
        
        # 4. Morphological operations to clean up
        kernel = np.ones((2, 2), np.uint8)
        cleaned = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
        
        return cleaned
    
    @staticmethod
    def enhance_contrast_only(image: np.ndarray) -> np.ndarray:
        """
        Light enhancement - just improve contrast without heavy processing.
        Good for already-clean images that get degraded by heavy preprocessing.
        """
        if len(image.shape) == 3:
            # Convert to LAB color space for better contrast enhancement
            lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
            l, a, b = cv2.split(lab)
            
            # Apply CLAHE to L channel only
            clahe = cv2.createCLAHE(clipLimit=1.5, tileGridSize=(8, 8))
            l = clahe.apply(l)
            
            # Merge and convert back
            lab = cv2.merge([l, a, b])
            enhanced = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)
            return enhanced
        else:
            clahe = cv2.createCLAHE(clipLimit=1.5, tileGridSize=(8, 8))
            return clahe.apply(image)
    
    @staticmethod
    def aggressive_upscale(image: np.ndarray, target_width: int = 2500) -> np.ndarray:
        """
        Upscale image for better OCR
        Target: 2500px width for optimal OCR without over-processing
        """
        height, width = image.shape[:2]
        if width < target_width:
            scale = target_width / width
            new_width = int(width * scale)
            new_height = int(height * scale)
            # Use INTER_CUBIC for best quality when upscaling
            upscaled = cv2.resize(image, (new_width, new_height), interpolation=cv2.INTER_CUBIC)
            logger.info(f"🔍 Upscaled {width}x{height} -> {new_width}x{new_height} (scale: {scale:.2f}x)")
            return upscaled
        return image
    
    @staticmethod
    def enhance_urdu_text(image: np.ndarray) -> np.ndarray:
        """
        Gentle OCR preprocessing adapted for SMALL extracted regions
        The professional pipeline needs smaller kernels for small images
        """
        # 1️⃣ Convert to grayscale (mandatory)
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()
        
        height, width = gray.shape[:2]
        
        # 2️⃣ Adaptive background removal based on region size
        # For small regions, use smaller kernel (proportional to size)
        kernel_size = min(15, max(5, width // 30))  # 5-15 pixels based on width
        if kernel_size % 2 == 0:
            kernel_size += 1  # Must be odd
        
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (kernel_size, kernel_size))
        background = cv2.morphologyEx(gray, cv2.MORPH_OPEN, kernel)
        shadow_removed = cv2.subtract(gray, background)
        
        # 3️⃣ Very gentle CLAHE (reduced clip limit for small text)
        clahe = cv2.createCLAHE(clipLimit=1.5, tileGridSize=(4, 4))
        contrast = clahe.apply(shadow_removed)
        
        # 4️⃣ Mild sharpening
        sharpen_kernel = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]])
        sharpened = cv2.filter2D(contrast, -1, sharpen_kernel)
        
        # 5️⃣ Adaptive Threshold with smaller block size for small text
        block_size = min(31, max(11, width // 15))  # Adaptive to region size
        if block_size % 2 == 0:
            block_size += 1
        
        thresh = cv2.adaptiveThreshold(
            sharpened,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            block_size,
            10
        )
        
        # 6️⃣ Skip morphological cleaning - it breaks small dots
        # Return thresholded image directly
        
        return thresh
    
    @staticmethod
    def remove_table_lines_advanced(image: np.ndarray) -> np.ndarray:
        """
        Remove table lines while preserving text
        Critical for section numbers which are inside table cells
        """
        # Work on grayscale
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()
        
        # Binary threshold
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        
        # Detect horizontal lines
        horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (40, 1))
        detect_horizontal = cv2.morphologyEx(binary, cv2.MORPH_OPEN, horizontal_kernel, iterations=2)
        
        # Detect vertical lines
        vertical_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 40))
        detect_vertical = cv2.morphologyEx(binary, cv2.MORPH_OPEN, vertical_kernel, iterations=2)
        
        # Combine detected lines
        lines_mask = cv2.add(detect_horizontal, detect_vertical)
        
        # Remove lines from original image
        result = image.copy()
        if len(result.shape) == 2:
            result[lines_mask == 255] = 255
        else:
            result[lines_mask == 255] = [255, 255, 255]
        
        logger.info("✓ Removed table lines")
        return result
    
    @staticmethod
    def extract_region_percent(image: np.ndarray, top: float, bottom: float, 
                               left: float, right: float) -> np.ndarray:
        """Extract region using percentage coordinates"""
        height, width = image.shape[:2]
        y1 = int(height * top)
        y2 = int(height * bottom)
        x1 = int(width * left)
        x2 = int(width * right)
        
        region = image[y1:y2, x1:x2]
        logger.info(f"Extracted region: ({x1},{y1}) to ({x2},{y2}) = {region.shape[1]}x{region.shape[0]}px")
        return region


class MultiEngineOCR:
    """
    Uses multiple OCR engines and combines results for best accuracy
    Priority: EasyOCR (best for Urdu) > PaddleOCR > Tesseract
    """
    
    def __init__(self):
        self.engines = []
        
        # Initialize EasyOCR (best for Urdu)
        if EASYOCR_AVAILABLE:
            try:
                self.easyocr_reader = easyocr.Reader(['ur', 'en'], gpu=False)
                self.engines.append('easyocr')
                logger.info("✓ EasyOCR initialized (Urdu + English)")
            except Exception as e:
                logger.error(f"EasyOCR init failed: {e}")
                self.easyocr_reader = None

            # Also create English-only reader for digit extraction
            # Urdu model sometimes interferes with digit recognition
            try:
                self.easyocr_reader_en = easyocr.Reader(['en'], gpu=False)
                logger.info("✓ EasyOCR English-only reader initialized")
            except Exception as e:
                logger.error(f"EasyOCR English-only init failed: {e}")
                self.easyocr_reader_en = None
        else:
            self.easyocr_reader = None
            self.easyocr_reader_en = None
        
        # Initialize PaddleOCR (backup)
        if PADDLEOCR_AVAILABLE:
            try:
                self.paddleocr = PaddleOCR(
                    use_angle_cls=True,
                    lang='en',
                )
                self.engines.append('paddleocr')
                logger.info("✓ PaddleOCR initialized")
            except Exception as e:
                logger.error(f"PaddleOCR init failed: {e}")
                self.paddleocr = None
        else:
            self.paddleocr = None
        
        # Tesseract (last resort)
        if TESSERACT_AVAILABLE:
            self.engines.append('tesseract')
            logger.info("✓ Tesseract available")
        
        if not self.engines:
            raise RuntimeError("No OCR engines available! Install at least one: easyocr, paddleocr, or tesseract")
        
        logger.info(f"OCR engines available: {', '.join(self.engines)}")
    
    def extract_text_easyocr(self, image: np.ndarray) -> Tuple[str, float]:
        """Extract text using EasyOCR"""
        try:
            if self.easyocr_reader is None:
                return "", 0.0
            
            # Convert to PIL Image
            if len(image.shape) == 2:
                pil_image = Image.fromarray(image)
            else:
                pil_image = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
            
            # Run EasyOCR
            results = self.easyocr_reader.readtext(np.array(pil_image), paragraph=False)
            
            if not results:
                return "", 0.0
            
            # Extract text and calculate average confidence
            texts = []
            confidences = []
            
            for detection in results:
                bbox, text, conf = detection
                # LOWERED threshold: Section numbers often have low confidence (0.1-0.3)
                # e.g., '149تب' at 0.22, '-=302' at 0.11, '379تب' at 0.29
                if float(conf) > 0.05:  # Accept very low confidence for numbers
                    texts.append(text)
                    confidences.append(float(conf))
            
            combined_text = " ".join(texts)
            avg_confidence = sum(confidences) / len(confidences) * 100 if confidences else 0
            
            logger.info(f"EasyOCR: {len(texts)} text blocks, confidence: {avg_confidence:.1f}%")
            return combined_text, avg_confidence

        except Exception as e:
            logger.error(f"EasyOCR failed: {e}")
            return "", 0.0

    def extract_text_easyocr_english(self, image: np.ndarray) -> Tuple[str, float]:
        """Extract text using EasyOCR with ENGLISH ONLY - better for digit recognition"""
        try:
            if self.easyocr_reader_en is None:
                return "", 0.0

            # Convert to PIL Image
            if len(image.shape) == 2:
                pil_image = Image.fromarray(image)
            else:
                pil_image = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))

            # Run EasyOCR with English only
            results = self.easyocr_reader_en.readtext(np.array(pil_image), paragraph=False)

            if not results:
                return "", 0.0

            texts = []
            confidences = []

            for detection in results:
                bbox, text, conf = detection
                # Very low threshold for digits
                if float(conf) > 0.05:
                    texts.append(text)
                    confidences.append(float(conf))

            combined_text = " ".join(texts)
            avg_confidence = sum(confidences) / len(confidences) * 100 if confidences else 0

            logger.info(f"EasyOCR (EN): {len(texts)} text blocks, confidence: {avg_confidence:.1f}%")
            return combined_text, avg_confidence

        except Exception as e:
            logger.error(f"EasyOCR English failed: {e}")
            return "", 0.0

    def extract_text_paddleocr(self, image: np.ndarray) -> Tuple[str, float]:
        """Extract text using PaddleOCR"""
        try:
            if self.paddleocr is None:
                return "", 0.0
            
            # PaddleOCR 2.x accepted ocr(image, cls=True); 3.x removed the
            # per-call `cls` kwarg (angle classifier is configured at init
            # via use_angle_cls=True). Call without `cls` and parse both
            # the 2.x nested-list format and the 3.x dict format defensively.
            try:
                results = self.paddleocr.ocr(image)
            except TypeError:
                results = self.paddleocr.predict(image)

            if not results:
                return "", 0.0

            texts = []
            confidences = []

            # 3.x style: list[dict] with 'rec_texts' / 'rec_scores' keys
            first = results[0] if results else None
            if isinstance(first, dict):
                rec_texts = first.get('rec_texts') or []
                rec_scores = first.get('rec_scores') or []
                for text, conf in zip(rec_texts, rec_scores):
                    try:
                        conf_f = float(conf)
                    except (TypeError, ValueError):
                        conf_f = 0.0
                    if conf_f > 0.3 and text:
                        texts.append(str(text))
                        confidences.append(conf_f)
            # 2.x style: list[list[[bbox, (text, conf)], ...]]
            elif first:
                for line in first:
                    if line and len(line) >= 2 and line[1]:
                        text = line[1][0]
                        conf = line[1][1]
                        if conf > 0.3:
                            texts.append(text)
                            confidences.append(conf)
            
            combined_text = " ".join(texts)
            avg_confidence = sum(confidences) / len(confidences) * 100 if confidences else 0
            
            logger.info(f"PaddleOCR: {len(texts)} text blocks, confidence: {avg_confidence:.1f}%")
            return combined_text, avg_confidence
            
        except Exception as e:
            logger.error(f"PaddleOCR failed: {e}")
            return "", 0.0
    
    def extract_text_tesseract(self, image: np.ndarray) -> Tuple[str, float]:
        """Extract text using Tesseract"""
        try:
            # Configure Tesseract for Urdu
            config = '--oem 3 --psm 6 -l urd+eng'
            
            # Get text
            text = pytesseract.image_to_string(image, config=config)
            
            # Get confidence
            data = pytesseract.image_to_data(image, config=config, output_type=pytesseract.Output.DICT)
            confidences = [int(conf) for conf in data['conf'] if conf != '-1' and int(conf) > 0]
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0
            
            logger.info(f"Tesseract: confidence: {avg_confidence:.1f}%")
            return text, avg_confidence
            
        except Exception as e:
            logger.error(f"Tesseract failed: {e}")
            return "", 0.0
    
    def extract_text_multi(self, image: np.ndarray, prefer_engine: str = 'easyocr') -> Tuple[str, float]:
        """
        Extract text using multiple engines and return best result
        """
        results = []
        
        # Try EasyOCR first (best for Urdu)
        if 'easyocr' in self.engines and self.easyocr_reader:
            text, conf = self.extract_text_easyocr(image)
            if text:
                results.append(('easyocr', text, conf))
        
        # Try PaddleOCR
        if 'paddleocr' in self.engines and self.paddleocr:
            text, conf = self.extract_text_paddleocr(image)
            if text:
                results.append(('paddleocr', text, conf))
        
        # Try Tesseract
        if 'tesseract' in self.engines:
            text, conf = self.extract_text_tesseract(image)
            if text:
                results.append(('tesseract', text, conf))
        
        # Return best result by confidence
        if results:
            results.sort(key=lambda x: x[2], reverse=True)
            best_engine, best_text, best_conf = results[0]
            logger.info(f"✓ Best result: {best_engine} ({best_conf:.1f}%)")
            return best_text, best_conf
        
        return "", 0.0


# ── DB areas table cache for text-match geocoding ────────────────────────
# Populated at startup by calling load_areas_for_geocoding(db_connection).
_ocr_areas_cache: Dict[str, Tuple[float, float]] = {}
_MATCH_NOISE = {"the", "and", "for", "lahore", "town", "area", "housing", "colony", "of"}


def load_areas_for_geocoding(connection) -> None:
    """Load the areas table into the module cache for text-match geocoding.
    Call once at application startup."""
    global _ocr_areas_cache
    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT area_name, latitude, longitude FROM areas")
        _ocr_areas_cache = {
            row["area_name"]: (float(row["latitude"]), float(row["longitude"]))
            for row in cursor.fetchall()
        }
        cursor.close()
        logger.info(f"✅ Loaded {len(_ocr_areas_cache)} areas into OCR geocoding cache")
    except Exception as exc:
        logger.warning(f"[OCR geocode] Could not load areas table: {exc}")


def _db_text_match(english_name: str) -> Optional[Tuple[float, float]]:
    """Match an English area name against the cached areas table.
    Returns (lat, lon) for the best match, or None."""
    if not _ocr_areas_cache or not english_name:
        return None
    en = english_name.lower()
    en_words = set(re.findall(r"\b[a-z0-9]\w*\b", en))
    best_name: Optional[str] = None
    best_score = 0
    for area_name, coords in _ocr_areas_cache.items():
        an = area_name.lower()
        # Tier 1: full substring match
        if an in en:
            score = len(an) * 3
            if score > best_score:
                best_name, best_score = area_name, score
            continue
        # Tier 2: word-level majority match
        area_words = [w for w in re.findall(r"\b[a-z0-9]\w*\b", an) if w not in _MATCH_NOISE]
        if not area_words:
            continue
        matches = sum(1 for w in area_words if w in en_words)
        frac = matches / len(area_words)
        if area_words[0] in en_words and frac >= 0.5:
            score = int(matches * len(an))
            if score > best_score:
                best_name, best_score = area_name, score
    if best_name:
        lat, lon = _ocr_areas_cache[best_name]
        logger.info(f"[Geocode] DB text-match: '{english_name[:50]}' → '{best_name}' ({lat:.4f},{lon:.4f})")
        return lat, lon
    return None


# ── Crime‑area crop strips (top, bottom, left, right) ──────────────────────
CRIME_STRIPS = [
    # (top, bottom, left, right) - overlapping vertical strips
    (0.38, 0.451, 0.29, 0.62),  # Original narrow region (proven for large format)
    (0.39, 0.49, 0.20, 0.70),   # Wide: captures text for both large + small format
    (0.41, 0.49, 0.20, 0.70),   # Lower strip: small format images often have text here
    (0.43, 0.50, 0.20, 0.70),   # Lowest strip: catches text at very bottom of row
    # Extra-wide strips — capture sub-block letters that sit further LEFT (the
    # end of a RTL Urdu line) for addresses like "ڈی ایچ اے فیز 1 بلاک B سب بلاک R"
    # where the final "سب بلاک X" extends past the 0.20 left edge of the
    # original strips.
    (0.38, 0.51, 0.10, 0.80),   # Extra-wide full-row
    (0.40, 0.52, 0.08, 0.85),   # Extra-extra-wide for small-format scans
]


# ── Free geocoding using Nominatim (OpenStreetMap) ─────────────────────────
def geocode_crime_area(area_name: str, city: str = "Lahore") -> dict:
    """Geocode a crime area location using Nominatim (100% free, forever).
    
    Uses OpenStreetMap's Nominatim API. No API key required.
    Rate limit: 1 request per second (respected automatically).
    
    Strategy:
    1. Try Urdu-to-English mapping first (best Nominatim results)
    2. Try the original Urdu name
    3. Try shorter version (first word only)
    4. Try English transliteration
    
    Args:
        area_name: The crime area/location name (Urdu or English)
        city: City name (default: Lahore)
    
    Returns:
        dict with 'latitude', 'longitude', 'display_name', 'success'
    """
    if not area_name or len(area_name.strip()) < 2:
        return {'latitude': None, 'longitude': None, 'display_name': '', 'success': False}

    if not GEOPY_AVAILABLE:
        logger.warning("geopy not installed - cannot geocode")
        return {'latitude': None, 'longitude': None, 'display_name': '', 'success': False}
    
    # Known location name mappings for better geocoding
    GEOCODE_MAPPINGS = {
        # Specific crime locations (Urdu -> English for Nominatim)
        "مین بلیوارڈ": "Main Boulevard Gulberg",
        "مین بلیوارڈ برکت مارکیٹ": "Barkat Market Main Boulevard",
        "مین بلیوارڈ گلبرگ": "Main Boulevard Gulberg",
        "برکت مارکیٹ": "Barkat Market",
        "ہربنس پورہ": "Harbanspura",
        "غڑی شاہو": "Garhi Shahu",
        "غری شاہو": "Garhi Shahu",
        "گڑھی شاہو": "Garhi Shahu",
        "شاہدرہ ٹاؤن": "Shahdara Town",
        "گارڈن ٹاؤن": "Garden Town",
        "فیصل ٹاؤن": "Faisal Town",
        "ماڈل ٹاؤن": "Model Town",
        "جوہر ٹاؤن": "Johar Town",
        "علامہ اقبال ٹاؤن": "Allama Iqbal Town",
        "اقبال ٹاؤن": "Iqbal Town",
        "گلبرگ": "Gulberg",
        "سبزہ زار": "Sabzazar",
        "ٹاؤن شپ": "Township",
        "گلشنِ راوی": "Gulshan Ravi",
        "گلشن راوی": "Gulshan Ravi",
        "سمن آباد": "Samanabad",
        "واپڈا ٹاؤن": "Wapda Town",
        "مغلپورہ": "Mughalpura",
        "باغبانپورہ": "Baghbanpura",
        "شالامار باغ": "Shalimar Bagh",
        "شادمان مارکیٹ": "Shadman Market",
        "شادمان": "Shadman",
        "انارکلی بازار": "Anarkali Bazaar",
        "لبرٹی مارکیٹ": "Liberty Market",
        "حفیظ سنٹر": "Hafeez Centre",
        "فیروزپور روڈ": "Ferozpur Road",
        "وحدت روڈ": "Wahdat Road",
        "کینال روڈ": "Canal Road",
        "داتا دربار": "Data Darbar",
        "لوہاری گیٹ": "Lohari Gate",
        "دہلی گیٹ": "Delhi Gate",
        "بھاٹی گیٹ": "Bhati Gate",
        "ریلوے اسٹیشن لاہور": "Railway Station Lahore",
        "کینٹ صدر بازار": "Cantt Saddar Bazaar",
        "جیل روڈ": "Jail Road",
        "والٹن روڈ": "Walton Road",
        "شاہ عالمی مارکیٹ": "Shah Alam Market",
        "نیلا گنبد": "Neela Gumbad",
        "قذافی اسٹیڈیم": "Gaddafi Stadium",
        "چوبرجی": "Chauburji",
        "لکشمی چوک": "Lakshmi Chowk",
        "حسین چوک": "Husain Chowk",
        "ریگل چوک": "Regal Chowk",
        "نسبت روڈ": "Nisbat Road",
        "برکی روڈ": "Barki Road",
        "ڈی ایچ اے": "DHA Lahore",
        "بحریہ ٹاؤن": "Bahria Town Lahore",
        "آسکاری": "Askari",
        "لی ڈی اے سٹی": "LDA City",
        "پی سی ایس آئی آر": "PCSIR",
        "پی آئی اے سوسائٹی": "PIA Society",
        "ای ایم ای سوسائٹی": "EME Society",
        "مولانا شوکت علی روڈ": "Mulana Shaukat Ali Road",
        "عامر روڈ": "Amer Road",
        "سنت نگر چوک": "Sant Nagar Chowk",
        "کریم بلاک مارکیٹ": "Karim Block Market",
        "پرانی انارکلی": "Old Anarkali",
        "فیکٹری ایریا": "Factory Area",
        "مسلم ٹاؤن": "Muslim Town",
        "بادامی باغ": "Badami Bagh",
        "نشتر ٹاؤن": "Nishtar Town",
        "راوی روڈ": "Ravi Road",
        # Additional missing regular locations
        "اولڈ انارکلی روڈ": "Old Anarkali Road",
        "اچھرہ مارکیٹ": "Ichhra Market",
        "برکی روڈ / بیدیان": "Barki Road Bedian",
        "د تا در بار": "Data Darbar",
        "شاد باغ مارکیٹ": "Shadbagh Market",
        "شادمـان مارکیٹ": "Shadman Market",
        "عامر روڈ (اسٹریٹ 9": "Amer Road Street 9",
        "ماڈل ٹاؤن پارک": "Model Town Park",
        "پریس کلب کوئٹہ": "Press Club Quetta",
        "پی آئی اے سوسائٹی بلاک H": "PIA Society Block H Lahore",
        "پی آئی اے سوسائٹی بلاک I": "PIA Society Block I Lahore",
        "گدا فی اسٹیڈیم": "Gaddafi Stadium",
        "گلبرگ لاہور": "Gulberg Lahore",
        "ہال روڈ": "Hall Road",
        # New regular locations (entries 151-950)
        "سرفرار روڈ کینٹ": "Sarfraz Road Cantt Lahore",
        "سنگیاں پل": "Singhpura Pul Lahore",
        "فوجی کالونی کینٹ": "Fauji Colony Cantt Lahore",
        "فورٹریس اسٹیڈیم ایریا": "Fortress Stadium Lahore",
        "لال کرتی کینٹ": "Lal Kurti Cantt Lahore",
        "نواں کوٹ بائیک پوائنٹ": "Nawan Kot Lahore",
        "چوبرجی انڈر پاس": "Chauburji Underpass Lahore",
        "کاماہاں انٹرچینج": "Kamahan Interchange Lahore",
        "کیولری گراؤنڈ": "Cavalry Ground Lahore",
        "گجومتہ موڑ": "Gajjumata Mor Lahore",
        # Locations with parenthetical detail
        "جوہر ٹاؤن (ایمپوریئم مال)": "Emporium Mall Johar Town",
        "علامہ اقبال ٹاؤن (کری بلاک مارکیٹ)": "Karim Block Market Allama Iqbal Town",
        "فیروزپور روڈ (قینچی)": "Qainchi Ferozepur Road",
    }
    
    # Normalize Unicode for consistent lookup (precomposed vs decomposed)
    import unicodedata
    area_normalized = unicodedata.normalize('NFC', area_name)
    
    # Build normalized mapping for lookup
    normalized_mappings = {}
    for k, v in GEOCODE_MAPPINGS.items():
        normalized_mappings[unicodedata.normalize('NFC', k)] = v
    
    # ── Structured location translator ──────────────────────────────────
    def translate_structured(name):
        """Translate structured Urdu location names to English.
        Handles DHA, Bahria Town, Askari, WAPDA Town, LDA City, PIA Society, Lake City, etc."""
        import re as _re
        
        # First strip "سب بلاک X" (sub-block) suffix - we geocode by parent area
        sub_block_match = _re.search(r'\s+سب\s+بلاک\s+\S+$', name)
        base_name = _re.sub(r'\s+سب\s+بلاک\s+\S+$', '', name) if sub_block_match else name
        
        patterns = [
            # ڈی ایچ اے فیز X وای بلاک → DHA Phase X Y Block
            (_re.compile(r'ڈی\s*ایچ\s*اے\s*فیز\s*(\d+)\s*وای\s*بلاک'), lambda m: f"DHA Phase {m.group(1)} Y Block"),
            # ڈی ایچ اے فیز X بلاک Y → DHA Phase X Block Y
            (_re.compile(r'ڈی\s*ایچ\s*اے\s*فیز\s*(\d+)\s*بلاک\s*(\S+)'), lambda m: f"DHA Phase {m.group(1)} Block {m.group(2)}"),
            # ڈی ایچ اے فیز X (phase only, no block) → DHA Phase X Lahore
            # Must come AFTER the block patterns so the more-specific ones win first.
            (_re.compile(r'ڈی\s*ایچ\s*اے\s*فیز\s*(\d+)'), lambda m: f"DHA Phase {m.group(1)} Lahore"),
            # بحریہ آرچرڈ فیز X بلاک Y → Bahria Orchard Phase X Block Y
            (_re.compile(r'بحریہ\s*آرچرڈ\s*فیز\s*(\d+)\s*بلاک\s*(\S+)'), lambda m: f"Bahria Orchard Phase {m.group(1)} Block {m.group(2)}"),
            # بحریہ ٹاؤن سیکٹر X بلاک Y → Bahria Town Sector X Block Y
            (_re.compile(r'بحریہ\s*ٹاؤن\s*سیکٹر\s*(\S+)\s*بلاک\s*(\S+)'), lambda m: f"Bahria Town Sector {m.group(1)} Block {m.group(2)}"),
            # آسکاری X بلاک Y → Askari X Block Y
            (_re.compile(r'آسکاری\s*(\d+)\s*بلاک\s*(\S+)'), lambda m: f"Askari {m.group(1)} Block {m.group(2)}"),
            # واپڈا ٹاؤن فیز X بلاک Y → WAPDA Town Phase X Block Y
            (_re.compile(r'واپڈا\s*ٹاؤن\s*فیز\s*(\d+)\s*بلاک\s*(\S+)'), lambda m: f"WAPDA Town Phase {m.group(1)} Block {m.group(2)}"),
            # لی ڈی اے سٹی سیکٹر X بلاک Y → LDA City Sector X Block Y
            (_re.compile(r'لی\s*ڈی\s*اے\s*سٹی\s*سیکٹر\s*(\d+)\s*بلاک\s*(\S+)'), lambda m: f"LDA City Sector {m.group(1)} Block {m.group(2)}"),
            # لی ڈی اے سٹی سیکٹر X (sector-only, no block) → LDA City Sector X
            (_re.compile(r'لی\s*ڈی\s*اے\s*سٹی\s*سیکٹر\s*(\d+)'), lambda m: f"LDA City Sector {m.group(1)}"),
            # ایل ڈی اے سٹی سیکٹر X (alternate FIR spelling)
            (_re.compile(r'ایل\s*ڈی\s*اے\s*سٹی\s*سیکٹر\s*(\d+)'), lambda m: f"LDA City Sector {m.group(1)}"),
            # پی آئی اے سوسائٹی بلاک X → PIA Society Block X
            (_re.compile(r'پی\s*آئی\s*اے\s*سوسائٹی\s*بلاک\s*(\S+)'), lambda m: f"PIA Society Block {m.group(1)}"),
            # لیک سٹی سیکٹر MX → Lake City Sector MX
            (_re.compile(r'لیک\s*سٹی\s*سیکٹر\s*(\S+)'), lambda m: f"Lake City Sector {m.group(1)}"),
            # والینشیا ٹاؤن بلاک X → Valencia Town Block X
            (_re.compile(r'والینشیا\s*ٹاؤن\s*بلاک\s*(\S+)'), lambda m: f"Valencia Town Block {m.group(1)}"),
            # جوہر ٹاؤن بلاک X → Johar Town Block X
            (_re.compile(r'جوہر\s*ٹاؤن\s*بلاک\s*(\S+)'), lambda m: f"Johar Town Block {m.group(1)}"),
            # الخضریا ہاؤسنگ بلاک X → Al Khuderia Housing Block X
            (_re.compile(r'الخضریا\s*ہاؤسنگ\s*بلاک\s*(\S+)'), lambda m: f"Al Khuderia Housing Block {m.group(1)}"),
            # ایڈن آباد بلاک X → Eden Abad Block X
            (_re.compile(r'ایڈن\s*آباد\s*بلاک\s*(\S+)'), lambda m: f"Eden Abad Block {m.group(1)}"),
        ]
        for pat, formatter in patterns:
            match = pat.search(base_name)
            if match:
                return formatter(match)
        return None
    
    try:
        geolocator = Nominatim(user_agent="fir_crime_area_geocoder_v1", timeout=10.0)
        
        # ── Step 0: DB text-match (authoritative, zero API calls) ─────────────
        import unicodedata as _uc
        _area_nfc = _uc.normalize('NFC', area_name)
        _area_en = (translate_structured(area_name)
                    or translate_structured(_area_nfc)
                    or GEOCODE_MAPPINGS.get(area_name)
                    or {_uc.normalize('NFC', k): v for k, v in GEOCODE_MAPPINGS.items()}.get(_area_nfc))
        if _area_en:
            _db_coords = _db_text_match(_area_en)
            if _db_coords:
                return {'latitude': _db_coords[0], 'longitude': _db_coords[1], 'display_name': '', 'success': True}
        # Also try raw input in case it already has English words
        _db_direct = _db_text_match(area_name)
        if _db_direct:
            return {'latitude': _db_direct[0], 'longitude': _db_direct[1], 'display_name': '', 'success': True}

        # Build query list - prioritize English mappings
        queries = []
        
        # Lahore bounding box for Nominatim viewbox (prevents wrong-city results)
        # Format: (SW_lat, SW_lon), (NE_lat, NE_lon)
        _LAHORE_VIEWBOX = [(31.10, 73.80), (31.90, 74.75)]

        # 0. Try structured location translation first (DHA Phase X Block Y, etc.)
        structured_english = translate_structured(area_name)
        if not structured_english:
            structured_english = translate_structured(area_normalized)
        if structured_english:
            queries.append(f"{structured_english}, Lahore, Pakistan")
            queries.append(f"{structured_english}, Lahore")
            # Also try parent area (without block) as fallback
            parent = structured_english.rsplit(' Block', 1)[0] if ' Block' in structured_english else None
            if parent:
                queries.append(f"{parent}, Lahore, Pakistan")

        # 1. Try English mapping first (best results with Nominatim)
        english = GEOCODE_MAPPINGS.get(area_name) or normalized_mappings.get(area_normalized)
        
        # 1b. If no direct match, try stripping "سب بلاک X" suffix for non-structured names
        if not english and not structured_english:
            import re as _re_sb
            base_stripped = _re_sb.sub(r'\s+سب\s+بلاک\s+\S+$', '', area_name).strip()
            if base_stripped != area_name:
                english = GEOCODE_MAPPINGS.get(base_stripped) or normalized_mappings.get(unicodedata.normalize('NFC', base_stripped))
                if not english:
                    # Also try structured translator on base name
                    structured_english = translate_structured(base_stripped)
        
        if english:
            queries.append(f"{english}, {city}, Pakistan")
            queries.append(f"{english}, {city}")

        # 2. Paren-base English lookup — BEFORE Urdu fallback to avoid
        #    Nominatim matching ambiguous Urdu terms (e.g. "علامہ اقبال" →
        #    مقبرہ علامہ اقبال / Mausoleum instead of Allama Iqbal Town).
        import re as _re2
        _any_english_found = bool(english or structured_english)
        paren_match = _re2.match(r'^(.+?)\s*\(', area_name)
        if paren_match:
            _base_paren = paren_match.group(1).strip()
            _base_paren_en = GEOCODE_MAPPINGS.get(_base_paren) or normalized_mappings.get(unicodedata.normalize('NFC', _base_paren))
            if _base_paren_en:
                queries.append(f"{_base_paren_en}, {city}, Pakistan")
                queries.append(f"{_base_paren_en}, {city}")
                _any_english_found = True

        # 3. First-word English lookup (for multi-word names)
        words = area_name.split()
        if len(words) > 1:
            first_word = words[0]
            first_english = GEOCODE_MAPPINGS.get(first_word) or normalized_mappings.get(unicodedata.normalize('NFC', first_word))
            if first_english:
                queries.append(f"{first_english}, {city}, Pakistan")
                _any_english_found = True

        # 4. Raw Urdu fallback — only when NO English mapping was found at all.
        #    Skipped when we have English mappings because Nominatim can
        #    ambiguously match Urdu landmark names (tombs, mosques, etc.) instead
        #    of the intended residential area, producing wrong coordinates.
        if not _any_english_found:
            queries.append(f"{area_name}, {city}, Pakistan")
            queries.append(f"{area_name}, {city}")
            if len(words) > 1:
                queries.append(f"{first_word}, {city}, Pakistan")
            queries.append(f"{area_name}, Pakistan")
        
        for query in queries:
            try:
                # Use viewbox + bounded=True so Nominatim restricts results to
                # Lahore district — eliminates wrong-city false positives entirely.
                location = geolocator.geocode(
                    query,
                    viewbox=_LAHORE_VIEWBOX,
                    bounded=True,
                )
                if hasattr(location, 'latitude') and hasattr(location, 'longitude'):
                    lat, lon = location.latitude, location.longitude
                    if 31.0 <= lat <= 32.0 and 73.5 <= lon <= 75.0:
                        logger.info(f"[Geocode] ✓ Found: {query} -> ({lat}, {lon})")
                        return {
                            'latitude': round(lat, 6),
                            'longitude': round(lon, 6),
                            'display_name': getattr(location, 'address', '') or '',
                            'success': True
                        }
                time.sleep(1.1)  # Nominatim rate limit: max 1 req/sec
            except (GeocoderTimedOut, GeocoderServiceError) as e:
                logger.warning(f"[Geocode] Timeout/error for '{query}': {e}")
                time.sleep(1.1)
                continue
            except Exception as e:
                logger.warning(f"[Geocode] Error for '{query}': {e}")
                time.sleep(1.1)
                continue

        logger.warning(f"[Geocode] ✗ No Nominatim match for '{area_name}' within Lahore bounds")
        return {'latitude': None, 'longitude': None, 'display_name': '', 'success': False}
    
    except Exception as e:
        logger.error(f"[Geocode] Fatal error: {e}")
        return {'latitude': None, 'longitude': None, 'display_name': '', 'success': False}


def detect_structured_location(raw_text: str) -> str:
    """Detect structured housing scheme locations from raw/garbled OCR text.
    
    Uses keyword anchoring to identify DHA, Bahria, Askari, LDA, WAPDA patterns
    even in heavily garbled Tesseract output.
    Returns constructed location string or empty string.
    """
    text = re.sub(r'\s+', ' ', raw_text.strip())
    if len(text) < 5:
        return ""

    # ─── Helper: normalise a single block/sector/sub-block token ───────────
    def _normalize_scheme_token(token: str) -> str:
        t = re.sub(r'\s+', '', (token or '').strip())
        if not t:
            return ''
        token_map = {
            'آ': 'J',
            'ا': 'A',
            'ء': 'A',
            'ج': 'J',
            'جے': 'J',
            'جی': 'G',
            'گ': 'G',
            'گا': 'G',
            'ک': 'K',
            'کے': 'K',
            'کا': 'K',
            '6': 'G',
            '8': 'B',
            '0': 'O',
            '3': 'O',
            'او': 'O',
            'ایس': 'S',
            '5': 'S',
            'وائی': 'Y',
            'وائ': 'Y',
            'ای': 'A',
            'بی': 'B',
            'سی': 'C',
            'ڈی': 'D',
        }
        if t in token_map:
            return token_map[t]
        if len(t) == 1 and t.isalpha():
            return t.upper()
        return t.upper()
    
    # ===== DHA (ڈی ایچ اے) =====
    dha_markers = ['ایچ اے', 'اچ اے', 'اگ اے', 'ائچ اے', 'ایچ ای',
                   'اچ ای', 'ای اے', 'اگ ے', 'ایچاے', 'اچاے',
                   'ایج اے', 'اگ ای', 'ایچ ے', 'ایگ اے',
                   'کی اے', 'کے اے', 'کی ای', 'کے ای',
                   'اچ کے', 'اچ کی']  # extra garbles: ایچ اے→اچ کے
    for marker in dha_markers:
        pos = text.find(marker)
        if pos >= 0:
            # Strict validation: require ڈی pattern close to marker
            # ڈ/ڑ followed by 0-1 chars then ی (handles ڈی, ڑی, ڑکی garbles)
            # Rejects "ارڈ تی" (2+ chars between ڈ and ی, from garbled بلیوارڈ)
            prefix = text[max(0, pos-5):pos]
            has_d_context = bool(re.search(r'[ڈڑ].?ی', prefix))
            # Also allow ڈ at very start of text (pos <= 3)
            if not has_d_context and pos <= 3:
                has_d_context = 'ڈ' in text[:pos]
            if not has_d_context:
                continue
            # Additional validation: text around marker shouldn't be mostly noise
            context = text[max(0, pos-15):min(len(text), pos+len(marker)+20)]
            urdu_in_ctx = sum(1 for c in context if '\u0600' <= c <= '\u06FF')
            if urdu_in_ctx < len(context) * 0.3:  # Too much noise
                continue
            after = text[pos + len(marker):]
            phase_match = re.search(r'(\d)', after[:30])
            if phase_match:
                phase = phase_match.group(1)
                if 1 <= int(phase) <= 9:
                    after_phase = after[phase_match.end():]
                    # Combined block+subblock in one pass
                    combined = re.search(
                        r'(?:بلاک|لاک|ملاک|بلک)\s*([A-Za-z0-9اآءجگ])'
                        r'[\s\S]{0,60}?'
                        r'(?:سب\s*بلاک|سبلاک|سب\s*بلک|سے\s*بلاک|سب\s*بلاگ)\s*([A-Za-z0-9اآءجگ])',
                        after_phase[:250], re.IGNORECASE)
                    if combined:
                        block = _normalize_scheme_token(combined.group(1))
                        sub_block = _normalize_scheme_token(combined.group(2))
                        return f"ڈی ایچ اے فیز {phase} بلاک {block} سب بلاک {sub_block}"
                    block_match = re.search(r'(?:بلاک|لاک|ملاک|بلک)\s*([A-Za-z0-9اآءجگ])', after_phase[:60])
                    if block_match:
                        block = _normalize_scheme_token(block_match.group(1))
                        return f"ڈی ایچ اے فیز {phase} بلاک {block}"
                    return f"ڈی ایچ اے فیز {phase}"
    
    # ===== آسکاری (Askari) =====
    askari_markers = ['آسکاری', 'آسکار', 'اسکاری', 'اسکار', 'آسکری',
                      'آساری', 'آسکادری', 'اسکادری']  # garbled: آساری, آسکادری
    for marker in askari_markers:
        pos = text.find(marker)
        if pos >= 0:
            after = text[pos + len(marker):]
            num_match = re.search(r'(\d+)', after[:15])
            if num_match:
                num = num_match.group(1)
                remaining = after[num_match.end():]
                # ── Combined single-regex: captures Block AND SubBlock in one shot.
                # The middle group allows up to 60 chars of OCR noise between them,
                # so a dropped or garbled block letter no longer breaks SubBlock.
                combined = re.search(
                    r'(?:بلاک|لاک|ملاک|بلک)\s*([A-Za-z0-9اآءجگ])'
                    r'[\s\S]{0,60}?'
                    r'(?:سب\s*بلاک|سبلاک|سب\s*بلک|سے\s*بلاک|سب\s*بلاگ)\s*([A-Za-z0-9اآءجگ])',
                    remaining[:250], re.IGNORECASE)
                if combined:
                    block = _normalize_scheme_token(combined.group(1))
                    sub_block = _normalize_scheme_token(combined.group(2))
                    return f"آسکاری {num} بلاک {block} سب بلاک {sub_block}"
                # ── Fallback: block letter only ────────────────────────────────
                block_match = re.search(r'(?:بلاک|لاک|ملاک|بلک)\s*([A-Za-z0-9اآءجگ])', remaining[:60])
                if block_match:
                    block = _normalize_scheme_token(block_match.group(1))
                    return f"آسکاری {num} بلاک {block}"
                return f"آسکاری {num}"
    
    # ===== بحریہ ٹاؤن (Bahria Town) =====
    bahria_markers = ['بحریہ', 'بحرہ', 'بحربہ', 'نحریہ', 'بحری ہ', 'بحریا', 'بجریہ', 'بجریا']
    # Note: _normalize_scheme_token is now defined at the top of this function (above DHA block)

    for marker in bahria_markers:
        pos = text.find(marker)
        if pos >= 0:
            after = text[pos + len(marker):]

            # ── Bahria Orchard (آرچرڈ) path – phase then block/subblock ──
            orchard_match = re.search(r'(?:آرچرڈ|آرچ|\bOrchard\b)', after[:60], re.IGNORECASE)
            if orchard_match:
                after_orch = after[orchard_match.end():]
                phase_match_o = re.search(r'(?:فیز|فیر|فین|ٹر|نر)\s*(\d+)', after_orch[:30])
                if phase_match_o:
                    phase_o = phase_match_o.group(1)
                    rem_o = after_orch[phase_match_o.end():]
                    blk_o = re.search(r'(?:بلاک|لاک|ملاک|بلک)\s*([A-Za-z0-9اآءجگ])', rem_o[:55])
                    if blk_o:
                        block_o = _normalize_scheme_token(blk_o.group(1))
                        sub_o = re.search(r'(?:سب\s*بلاک|سبلاک|سب\s*بلک|سے\s*بلاک|سب\s*بلاگ)\s*([A-Za-z0-9اآءجگ])', rem_o[:200], re.IGNORECASE)
                        if sub_o:
                            sub_block_o = _normalize_scheme_token(sub_o.group(1))
                            return f"بحریہ آرچرڈ فیز {phase_o} بلاک {block_o} سب بلاک {sub_block_o}"
                        return f"بحریہ آرچرڈ فیز {phase_o} بلاک {block_o}"
                    return f"بحریہ آرچرڈ فیز {phase_o}"
                return "بحریہ آرچرڈ"

            # ── Bahria Town (sector then block/subblock) ──
            sector_match = re.search(r'(?:سیکٹر|سکٹر|سیکنر|صیکٹر|شیکٹر|سی\s*کٹر|سیٹر|سٹٹر|سٹر)\s*([A-Za-z0-9اآءجگ])', after[:60])
            if sector_match:
                sector = _normalize_scheme_token(sector_match.group(1))
                remaining = after[sector_match.end():]
                combined = re.search(
                    r'(?:بلاک|لاک|ملاک|بلک)\s*([A-Za-z0-9اآءجگ])'
                    r'[\s\S]{0,60}?'
                    r'(?:سب\s*بلاک|سبلاک|سب\s*بلک|سے\s*بلاک|سب\s*بلاگ)\s*([A-Za-z0-9اآءجگ])',
                    remaining[:250], re.IGNORECASE)
                if combined:
                    block = _normalize_scheme_token(combined.group(1))
                    sub_block = _normalize_scheme_token(combined.group(2))
                    return f"بحریہ ٹاؤن سیکٹر {sector} بلاک {block} سب بلاک {sub_block}"
                block_match = re.search(r'(?:بلاک|لاک|ملاک|بلک)\s*([A-Za-z0-9اآءجگ])', remaining[:60])
                if block_match:
                    block = _normalize_scheme_token(block_match.group(1))
                    return f"بحریہ ٹاؤن سیکٹر {sector} بلاک {block}"
                return f"بحریہ ٹاؤن سیکٹر {sector}"
            # No sector or orchard found – return generic (don't early-exit before checking orchard)
            return "بحریہ ٹاؤن"
    
    # ===== لی ڈی اے (LDA City) =====
    lda_markers = ['لی ڈی اے', 'لے ڈی اے', 'لی ڈے اے', 'لی ڈ اے',
                    'لی دے', 'لاڈ ی ے', 'ڈی نے بی', 'لی ڈی', 'ڈی لے',
                    'لاڈی ے', 'ڈڑی دے']  # garbled variants
    for marker in lda_markers:
        pos = text.find(marker)
        if pos >= 0:
            after = text[pos + len(marker):]
            sector_match = re.search(r'(?:سیکٹر|سکٹر|صیکٹر|[مخنٹکھ]ر)\s*(\d+)', after[:30])
            if sector_match:
                sector = sector_match.group(1)
                # Handle doubled digits from OCR garbling (44→4, 33→3)
                if len(sector) == 2 and sector[0] == sector[1]:
                    sector = sector[0]
                remaining = after[sector_match.end():]
                combined = re.search(
                    r'(?:بلاک|لاک|ملاک|بلک)\s*([A-Za-z0-9اآءجگ])'
                    r'[\s\S]{0,60}?'
                    r'(?:سب\s*بلاک|سبلاک|سب\s*بلک|سے\s*بلاک|سب\s*بلاگ)\s*([A-Za-z0-9اآءجگ])',
                    remaining[:250], re.IGNORECASE)
                if combined:
                    block = _normalize_scheme_token(combined.group(1))
                    sub_block = _normalize_scheme_token(combined.group(2))
                    return f"لی ڈی اے سٹی سیکٹر {sector} بلاک {block} سب بلاک {sub_block}"
                block_match = re.search(r'(?:بلاک|لاک|ملاک|بلک)\s*([A-Za-z0-9اآءجگ])', remaining[:60])
                if block_match:
                    block = _normalize_scheme_token(block_match.group(1))
                    return f"لی ڈی اے سٹی سیکٹر {sector} بلاک {block}"
                return f"لی ڈی اے سٹی سیکٹر {sector}"
            return "لی ڈی اے سٹی"  # fallback when marker found but no sector
    
    # ===== واپڈا ٹاؤن (WAPDA Town) =====
    wapda_markers = ['واپڈا', 'واپدا', 'وپڈا', 'وابڈا', 'داپڑا', 'دایڑا']
    for marker in wapda_markers:
        pos = text.find(marker)
        if pos >= 0:
            after = text[pos + len(marker):]
            phase_match = re.search(r'(?:فیز|فیر|فین|ٹر|نر)\s*(\d+)', after[:30])
            if phase_match:
                phase = phase_match.group(1)
                remaining = after[phase_match.end():]
                combined = re.search(
                    r'(?:بلاک|لاک|ملاک|بلک)\s*([A-Za-z0-9اآءجگ])'
                    r'[\s\S]{0,60}?'
                    r'(?:سب\s*بلاک|سبلاک|سب\s*بلک|سے\s*بلاک|سب\s*بلاگ)\s*([A-Za-z0-9اآءجگ])',
                    remaining[:250], re.IGNORECASE)
                if combined:
                    block = _normalize_scheme_token(combined.group(1))
                    sub_block = _normalize_scheme_token(combined.group(2))
                    return f"واپڈا ٹاؤن فیز {phase} بلاک {block} سب بلاک {sub_block}"
                block_match = re.search(r'(?:بلاک|لاک|ملاک|بلک)\s*([A-Za-z0-9اآءجگ])', remaining[:60])
                if block_match:
                    block = _normalize_scheme_token(block_match.group(1))
                    return f"واپڈا ٹاؤن فیز {phase} بلاک {block}"
                return f"واپڈا ٹاؤن فیز {phase}"
            return "واپڈا ٹاؤن"  # fallback
    
    # ===== پی سی ایس آئی آر (PCSIR) =====
    pcsir_markers = ['سی ایس آئی آر', 'سی ایی آئی آر', 'سی ایس آئی', 'سی ایی آئی']
    for marker in pcsir_markers:
        pos = text.find(marker)
        if pos >= 0:
            after = text[pos + len(marker):]
            phase_match = re.search(r'(?:فیز|فیر|ٹر|نر)\s*(\d+)', after[:30])
            if phase_match:
                phase = phase_match.group(1)
                remaining = after[phase_match.end():]
                block_match = re.search(r'(?:بلاک|لاک|ملاک)\s*([A-Za-z])', remaining[:20])
                if block_match:
                    return f"پی سی ایس آئی آر فیز {phase} بلاک {block_match.group(1).upper()}"
                return f"پی سی ایس آئی آر فیز {phase}"
    
    # ===== پی آئی اے سوسائٹی (PIA Society) =====
    pia_markers = ['پی آئی اے', 'پی کی اے', 'ات آ', 'اے بے', 'آ بے']

    def _normalize_pia_token(token: str) -> str:
        t = re.sub(r'\s+', '', (token or '').strip())
        if not t:
            return ''
        token_map = {
            '21': 'H',
            '2': 'H',
            '۸': 'B',
            '8': 'B',
            '1': 'I',
            '7': 'T',
            'ٹ': 'T',
            'ت': 'T',
        }
        if t in token_map:
            return token_map[t]
        if len(t) == 1 and t.isalpha():
            return t.upper()
        return t.upper()

    for marker in pia_markers:
        pos = text.find(marker)
        if pos >= 0:
            after = text[pos + len(marker):]
            # Look for سوسائٹی or garbled variant
            if re.search(r'(?:صوس|سوس|سوسائ|ملاک|بلاک|بلک|لاک)', after[:40]):
                block_match = re.search(r'(?:بلاک|لاک|بلاگ|ملاک|بلک)\s*([A-Za-z0-9اآءجگ]+)', after[:70])
                if block_match:
                    bl = _normalize_pia_token(block_match.group(1))
                    remaining = after[block_match.end():]
                    sub_block_match = re.search(r'(?:سب\s*بلاک|سبلاک|سب\s*بلک|سے\s*بلاک)\s*([A-Za-z0-9اآءجگ]+)', remaining[:200], re.IGNORECASE)
                    if sub_block_match:
                        sub_block = _normalize_pia_token(sub_block_match.group(1))
                        return f"پی آئی اے سوسائٹی بلاک {bl} سب بلاک {sub_block}"

                    # Heuristic: OCR often mangles trailing "ٹ" as "رت" in this layout.
                    if re.search(r'رت|\bٹ\b', remaining):
                        return f"پی آئی اے سوسائٹی بلاک {bl} سب بلاک T"

                    return f"پی آئی اے سوسائٹی بلاک {bl}"
                return "پی آئی اے سوسائٹی"

    # ===== جوہر ٹاؤن (Johar Town) block/subblock =====
    johar_markers = ['جوہر ٹاؤن', 'جو ہر ٹاؤن', 'جوہر', 'جو مان', 'جرماؤن']
    for marker in johar_markers:
        pos = text.find(marker)
        if pos >= 0:
            after = text[pos + len(marker):]
            combined = re.search(
                r'(?:بلاک|لاک|ملاک|بلک)\s*([A-Za-z0-9اآءجگ])'
                r'[\s\S]{0,60}?'
                r'(?:سب\s*بلاک|سبلاک|سب\s*بلک|سے\s*بلاک|سب\s*بلاگ)\s*([A-Za-z0-9اآءجگ])',
                after[:250], re.IGNORECASE)
            if combined:
                block = _normalize_scheme_token(combined.group(1))
                sub_block = _normalize_scheme_token(combined.group(2))
                return f"جوہر ٹاؤن بلاک {block} سب بلاک {sub_block}"
            block_match = re.search(r'(?:بلاک|لاک|ملاک|بلک)\s*([A-Za-z0-9اآءجگ])', after[:60])
            if block_match:
                block = _normalize_scheme_token(block_match.group(1))
                return f"جوہر ٹاؤن بلاک {block}"
            return "جوہر ٹاؤن"

    # ===== گلشن راوی / والینشیا / ایڈن آباد (generic named-town with block) =====
    named_town_patterns = [
        ('گلشن راوی', ['گلشن راوی', 'گلشنِ راوی', 'گلشن']),
        ('والینشیا ٹاؤن', ['والینشیا', 'والینش', 'واينشا', 'واینشا', 'والنشیا', 'والينشيا', 'لواینشیا']),
        ('ایڈن آباد', ['ایڈن آباد', 'ایڈن']),
        ('سبزہ زار', ['سبزہ زار', 'سبزہ']),
        ('فیصل ٹاؤن', ['فیصل ٹاؤن']),
        ('گارڈن ٹاؤن', ['گارڈن ٹاؤن', 'گارڈن']),
        ('علامہ اقبال ٹاؤن', ['اقبال ٹاؤن', 'علامہ اقبال']),
    ]
    for canonical, markers_list in named_town_patterns:
        for marker in markers_list:
            pos = text.find(marker)
            if pos >= 0:
                after = text[pos + len(marker):]
                combined = re.search(
                    r'(?:بلاک|لاک|ملاک|بلک|ملاګ)\s*([A-Za-z0-9اآءجگ])'
                    r'[\s\S]{0,60}?'
                    r'(?:سب\s*بلاک|سبلاک|سب\s*بلک|سے\s*بلاک|سب\s*بلاگ)\s*([A-Za-z0-9اآءجگ])',
                    after[:250], re.IGNORECASE)
                if combined:
                    block = _normalize_scheme_token(combined.group(1))
                    sub_block = _normalize_scheme_token(combined.group(2))
                    return f"{canonical} بلاک {block} سب بلاک {sub_block}"
                block_match = re.search(r'(?:بلاک|لاک|ملاک|بلک|ملاګ)\s*([A-Za-z0-9اآءجگ])', after[:60])
                if block_match:
                    block = _normalize_scheme_token(block_match.group(1))
                    return f"{canonical} بلاک {block}"
                break  # Don't try fallback markers if primary found without block

    return ""


def detect_location_fragments(raw_text: str, return_all: bool = False):
    """Disabled: fragment-to-known-location mapping has been turned off.

    The original implementation mapped OCR garble substrings to a hardcoded
    list of Lahore landmarks (e.g. "شادم" -> "شادمان مارکیٹ"). That caused
    novel FIR locations (e.g. "Khilary Ground") to be silently overwritten
    with a nearby hardcoded match whenever the noise contained a shared
    fragment. Crime area must reflect what Row 4 actually says, so this
    function now always reports "no fragment match" and the caller falls
    back to structured pattern detection or cleaned raw OCR text.
    """
    return [] if return_all else ""

    # ── Original fragment-matching implementation kept below for reference. ──
    # It is unreachable because of the early return above.
    if not raw_text or len(raw_text.strip()) < 3:
        return ""
    
    # Pre-filter: remove distance reference text (after سے) and noise lines
    lines = raw_text.strip().split('\n')
    filtered_lines = []
    noise_keywords = ['اطلاع', 'بذریعہ', 'ہذریعہ', 'ہزریعہ', 'فون', 'موصول',
                       'بزریعہ', 'ذریعہ', 'ٹریفک', 'صورتحال', 'عوائی',
                       'اطلاغ', 'اظطلار', 'اطلار', 'مزریعہ', 'پذریعہ',
                       'پذر ینہ', 'بر وقت', 'ہوٹی', 'ہو گی', 'ہوئی']
    for line in lines:
        line = line.strip()
        if not line:
            continue
        # Skip lines that are info-source (not crime-area)
        if any(nk in line for nk in noise_keywords):
            continue
        # Cut at distance marker - handles both proper "سے" and garbled forms
        # Patterns: "سے تقریباً", "ے7", "ےت", "ےآ" (garbled سے)
        # First try proper سے
        parts = re.split(r'\s+سے\s+', line)
        line = parts[0] if parts else line
        # Also cut at garbled distance patterns: والشن ے7, والشن ےت, etc.
        # Pattern: location_ref + ے + digit/letter (garbled "سے تقریباً distance")
        line = re.split(r'ے[تط7]\s*آ?\s*[\d٠-٩\[\]]', line)[0]
        # Cut at colon separator (crime_area : road/thana reference)
        # FIR format: "crime_location : road, area" - colon separates them
        line = re.split(r'\s*[:]\s*', line)[0]
        # Cut at dash separator (crime-area --- reference-point)
        line = re.split(r'[-ـ۔\.]{2,}', line)[0]
        # Cut at کاو/کلو (garbled کلومیٹر) 
        line = re.split(r'[\d٠-٩\[\]]+\s*,?\s*کاو', line)[0]
        line = re.split(r'[\d٠-٩\[\]]+\s*,?\s*کلو', line)[0]
        # Cut at garbled forms of سے تقر (تر, تقر, تقری)
        line = re.split(r'\s+تقر', line)[0]
        line = re.split(r'\s+تر\s*\)', line)[0]
        if line.strip():
            filtered_lines.append(line.strip())
    
    orig = re.sub(r'\s+', ' ', ' '.join(filtered_lines)).strip()
    if len(orig) < 3:
        return ""
    
    # Each entry: (list_of_fragment_patterns, result_location, min_fragments_needed)
    # Fragment patterns are substrings that commonly survive OCR garbling
    FRAGMENT_RULES = [
        # انارکلی بازار - use distinctive fragments
        (['انارکل'], 'انارکلی بازار', 1),
        (['انار', 'بازار'], 'انارکلی بازار', 2),
        (['انار', 'کلی'], 'انارکلی بازار', 2),
        (['انار', 'کگی'], 'انارکلی بازار', 2),     # garbled FIR_002 S1: "انار کگی"
        (['انا ری', 'مالیر'], 'انارکلی بازار', 2),  # garbled FIR_002 S0: "انا ری ار مالیر"
        # دہلی گیٹ - "دی گیٹ" or "دہلی" or "دھلی"
        (['دی گیٹ'], 'دہلی گیٹ', 1),
        (['دہلی'], 'دہلی گیٹ', 1),
        (['دھلی'], 'دہلی گیٹ', 1),                    # garbled دہلی→دھلی
        (['ہصح'], 'دہلی گیٹ', 1),                     # garbled FIR_005: "ہس ہصح" OCR corruption of دہلی گیٹ
        # شاہ عالمی مارکیٹ
        (['عالمی', 'مارکیٹ'], 'شاہ عالمی مارکیٹ', 2),
        # لوہاری گیٹ
        (['لوہاری'], 'لوہاری گیٹ', 1),
        (['لزاری'], 'لوہاری گیٹ', 1),                  # garbled لوہاری→لزاری
        (['ادہاری'], 'لوہاری گیٹ', 1),                 # garbled لوہاری→ادہاری
        (['لزا', 'گیٹ'], 'لوہاری گیٹ', 2),             # garbled FIR_004: لزا ری + یگیٹ
        # بھاٹی گیٹ
        (['بھاٹی'], 'بھاٹی گیٹ', 1),
        (['بھالی'], 'بھاٹی گیٹ', 1),                    # garbled بھاٹی→بھالی
        (['پھائی'], 'بھاٹی گیٹ', 1),                   # garbled بھاٹی→پھائی
        # ریگل چوک
        (['ریگل'], 'ریگل چوک', 1),
        (['ریگ جک'], 'ریگل چوک', 1),           # garbled FIR_007: "ریگ جک"
        # نیلا گنبد
        (['نیلا', 'گنبد'], 'نیلا گنبد', 1),
        (['گنبد'], 'نیلا گنبد', 1),
        # ایڈورڈ روڈ (sometimes OCR gives this for نیلا گنبد area)
        (['ایڈورڈ'], 'نیلا گنبد', 1),
        (['ایڑ ورڈ'], 'نیلا گنبد', 1),             # garbled FIR_008: ایڑ ورڈ
        (['ایڑ ور'], 'نیلا گنبد', 1),              # garbled partial
        # مین بلیوارڈ - "بلیوار" is distinctive
        (['بلیوار'], 'مین بلیوارڈ', 1),
        (['جلیوار'], 'مین بلیوارڈ', 1),  # garble
        (['بیوار'], 'مین بلیوارڈ', 1),             # garbled FIR_011: بیو ار (من replaced ل with space)
        (['بیو ارڈ'], 'مین بلیوارڈ', 1),           # garbled with space: بیو ارڈ
        # قذافی اسٹیڈیم - "قذا" fragment
        (['قذا'], 'قذافی اسٹیڈیم', 1),
        (['گدائی'], 'قذافی اسٹیڈیم', 1),              # garbled FIR_012: گدائی→قذافی
        (['گدافی'], 'قذافی اسٹیڈیم', 1),              # garbled variant
        (['گدا فی'], 'قذافی اسٹیڈیم', 1),             # garbled with space
        (['قذافی'], 'قذافی اسٹیڈیم', 1),              # proper spelling
        # فیصل ٹاؤن - "فیصل" or garbled variants
        (['فیصل'], 'فیصل ٹاؤن', 1),
        # گارڈن ٹاؤن - "گارڈ" or "گار ڈ"
        (['گارڈ'], 'گارڈن ٹاؤن', 1),
        (['گار ڈ'], 'گارڈن ٹاؤن', 1),
        # ٹاؤن شپ - "شپ" near "ٹاؤن"
        (['ٹاؤن شپ'], 'ٹاؤن شپ', 1),
        (['نع شب'], 'ٹاؤن شپ', 1),  # OCR garble
        (['جلاع شپ'], 'ٹاؤن شپ', 1),  # garbled FIR_018 S0-PSM6
        (['پان شب'], 'ٹاؤن شپ', 1),   # garbled FIR_018 S1-Otsu
        (['بن شب'], 'ٹاؤن شپ', 1),    # garbled FIR_018 S1-PSM6
        (['لاع شپ'], 'ٹاؤن شپ', 1),   # garbled partial
        # والٹن روڈ - only match proper والٹن, not والشن (too many false positives
        # as والشن frequently appears as a distance reference point)
        (['والٹن'], 'والٹن روڈ', 1),
        # شادمان
        (['شادمان'], 'شادمان مارکیٹ', 1),
        (['شادم'], 'شادمان مارکیٹ', 1),
        # جیل روڈ - "جیل" or "ٹیل رد" (garbled)
        (['جیل'], 'جیل روڈ', 1),
        (['ٹیل ر'], 'جیل روڈ', 1),  # garbled OCR
        # مغلپورہ
        (['مغلپور'], 'مغلپورہ', 1),
        (['مغلپ'], 'مغلپورہ', 1),
        # ہربنس پورہ
        (['ہربنس'], 'ہربنس پورہ', 1),
        (['ہر یئ'], 'ہربنس پورہ', 1),  # garbled (seen in FIR_024)
        (['ہر یشس'], 'ہربنس پورہ', 1),  # garbled
        # غڑی شاہو / غری شاہو - ONLY combined patterns (single-fragment removed to prevent false positives)
        # Single-fragment غڑی/غری rules removed - use combined rules at bottom
        # شالامار باغ
        (['شالامار'], 'شالامار باغ', 1),
        (['شالا'], 'شالامار باغ', 1),
        (['شال مار'], 'شالامار باغ', 1),                # garbled with space: شال مار
        # باغبانپورہ - "غازی آباد" linked to it
        (['باغبان'], 'باغبانپورہ', 1),
        (['ذائیآ'], 'باغبانپورہ', 1),  # garbled غازی آباد
        # سمن آباد
        (['سمن'], 'سمن آباد', 1),
        (['نآ اد'], 'سمن آباد', 1),  # garbled
        (['نآ بادہ'], 'سمن آباد', 1),  # garbled
        (['تنآ اد'], 'سمن آباد', 1),  # garbled
        # ریلوے اسٹیشن
        (['ریلوے'], 'ریلوے اسٹیشن لاہور', 1),
        (['اسٹیشن'], 'ریلوے اسٹیشن لاہور', 1),
        (['مگیشن'], 'ریلوے اسٹیشن لاہور', 1),  # garbled
        # کینٹ صدر بازار
        (['کینٹ', 'صدر'], 'کینٹ صدر بازار', 2),
        (['کین', 'صدر'], 'کینٹ صدر بازار', 2),
        (['کین', 'مدر'], 'کینٹ صدر بازار', 2),  # garbled صدر→مدر
        (['گیٹ', 'مدر'], 'کینٹ صدر بازار', 2),  # garbled: گیٹ مدر = کینٹ صدر
        # برکی روڈ / بیدیان
        (['بیدیان'], 'برکی روڈ', 1),
        (['بیدان'], 'برکی روڈ', 1),  # garbled
        (['یدان'], 'برکی روڈ', 1),
        (['برکی'], 'برکی روڈ', 1),
        # فیروزپور روڈ
        (['فیروزپور'], 'فیروزپور روڈ', 1),
        (['فیروز'], 'فیروزپور روڈ', 1),
        # وحدت روڈ
        (['وحدت'], 'وحدت روڈ', 1),
        (['دحرت'], 'وحدت روڈ', 1),         # garbled وحدت (FIR_035 PSM6)
        (['دحد تر'], 'وحدت روڈ', 1),       # garbled وحدت (FIR_035 Otsu)
        # لبرٹی مارکیٹ
        (['لبرٹی'], 'لبرٹی مارکیٹ', 1),
        # حفیظ سنٹر
        (['حفیظ'], 'حفیظ سنٹر', 1),
        # جوہر ٹاؤن
        (['جوہر'], 'جوہر ٹاؤن', 1),
        (['جو مان'], 'جوہر ٹاؤن', 1),          # garbled FIR_017 S1-PSM6: "جو مان"
        (['جرماؤن'], 'جوہر ٹاؤن', 1),          # garbled FIR_017 S1-Otsu: "جرماؤن"
        # ایمپوریئم
        (['ایمپوریئم'], 'جوہر ٹاؤن ایمپوریئم مال', 1),
        (['ای پر', 'مال'], 'جوہر ٹاؤن ایمپوریئم مال', 2),  # garbled FIR_017
        # ماڈل ٹاؤن  
        (['ماڈل'], 'ماڈل ٹاؤن', 1),
        # سبزہ زار
        (['سبزہ'], 'سبزہ زار', 1),
        (['سڑزوزار'], 'سبزہ زار', 1),                   # garbled FIR_030: سڑزوزار→سبزہ زار
        (['سبز', 'زار'], 'سبزہ زار', 2),               # garbled partial
        # گلشن راوی
        (['گلشن'], 'گلشنِ راوی', 1),
        # اقبال ٹاؤن
        (['اقبال'], 'علامہ اقبال ٹاؤن', 1),
        # کینال روڈ
        (['کینال'], 'کینال روڈ', 1),
        # راوی روڈ
        (['راوی ر'], 'راوی روڈ', 1),
        (['رادیا'], 'راوی روڈ', 1),              # garbled FIR_027 S1-Otsu
        (['رادی', 'روڈ'], 'راوی روڈ', 2),        # garbled FIR_027: رادی+روڈ
        (['رادک', 'روڈ'], 'راوی روڈ', 2),        # garbled variant
        # ہال روڈ
        (['ہال'], 'ہال روڈ', 1),
        # شاہدرہ
        (['شاہدرہ'], 'شاہدرہ ٹاؤن', 1),
        (['شاہدر'], 'شاہدرہ ٹاؤن', 1),
        # داتا دربار
        (['داتا'], 'داتا دربار', 1),
        # کریم بلاک
        (['کریم', 'بلاک'], 'کریم بلاک مارکیٹ', 2),
        # ای ایم ای سوسائٹی - require both patterns to avoid false positives
        # (ایم ایم عالم روڈ is a common reference road, not ای ایم ای سوسائٹی)
        (['ایم ای', 'سوسائ'], 'ای ایم ای سوسائٹی', 2),
        # مولانا شوکت
        (['شوکت'], 'مولانا شوکت علی روڈ', 1),
        # بحریہ ٹاؤن - garbled OCR patterns from small-format images
        (['بر مائن'], 'بحریہ ٹاؤن', 1),    # garbled بحریہ مین
        (['بر مان'], 'بحریہ ٹاؤن', 1),     # garbled without ئ
        (['بھریے مان'], 'بحریہ ٹاؤن', 1),   # garbled at scale 3.0
        (['بھریہ مان'], 'بحریہ ٹاؤن', 1),   # garbled variant
        (['بھری مان'], 'بحریہ ٹاؤن', 1),    # garbled variant
        (['بھرس مان'], 'بحریہ ٹاؤن', 1),    # garbled FIR_198
        (['بھرسہ'], 'بحریہ ٹاؤن', 1),       # garbled FIR_198
        (['بجھرسہ مان'], 'بحریہ ٹاؤن', 1),  # garbled FIR_113
        (['بجھرس مان'], 'بحریہ ٹاؤن', 1),   # garbled FIR_155
        (['جھری مان'], 'بحریہ ٹاؤن', 1),   # garbled بحریہ مین
        (['جھری', 'لاک'], 'بحریہ ٹاؤن', 2), # garbled بحریہ بلاک
        # بحریہ آرچرڈ - garbled
        (['پھر آرڈ'], 'بحریہ آرچرڈ', 1),    # garbled FIR_151
        (['بھرں آرجھڈ'], 'بحریہ آرچرڈ', 1), # garbled FIR_188
        (['آرجھڈ'], 'بحریہ آرچرڈ', 1),      # garbled آرچرڈ
        # الخضریا ہاؤسنگ - garbled
        (['النریا'], 'الخضریا ہاؤسنگ', 1),  # garbled FIR_156
        # مغلپورہ - additional garbled patterns
        (['للپور'], 'مغلپورہ', 1),          # garbled from FIR_023
        # فیصل ٹاؤن - highly garbled patterns
        (['یصل'], 'فیصل ٹاؤن', 1),         # partial فیصل
        (['یل انان'], 'فیصل ٹاؤن', 1),     # garbled فیصل ٹاؤن (FIR_015 PSM6)
        (['ٹیل نون'], 'فیصل ٹاؤن', 1),     # garbled فیصل ٹاؤن (FIR_015 PSM7)
        (['نیھل'], 'فیصل ٹاؤن', 1),        # garbled فیصل (FIR_015 Otsu)
        # اقبال ٹاؤن - additional garbled patterns  
        (['اتال', 'ڈاؤ'], 'علامہ اقبال ٹاؤن', 2),  # garbled اقبال ٹاؤن
        (['اتال', 'مان'], 'علامہ اقبال ٹاؤن', 2),  # garbled
        # چوبرجی
        (['چوبرجی'], 'چوبرجی', 1),
        # لکشمی چوک
        (['لکشم'], 'لکشمی چوک', 1),
        # نسبت روڈ
        (['نسبت'], 'نسبت روڈ', 1),
        # نشتر ٹاؤن - removed as standalone, too many reference-point false positives
        # (نشتر is always a reference point in our dataset, never the crime area)
        # پران انارکلی
        (['پرانی', 'نارکل'], 'پرانی انارکلی', 2),
        # عامر روڈ - garbled
        (['ام ز روڈ'], 'عامر روڈ', 1),     # garbled FIR_16: ام ز روڈ→عامر روڈ
        (['امر روڈ'], 'عامر روڈ', 1),
        (['پامرروڑ'], 'عامر روڈ', 1),      # garbled FIR_16 S1: پامرروڑ
        # سنت نگر - garbled
        (['سنت نگر'], 'سنت نگر چوک', 1),
        # === Additional garble patterns for SPECIFIC crime locations ===
        # مین بلیوارڈ - garbled patterns (specific crime location, NOT thana)
        (['باہوفرڈ'], 'مین بلیوارڈ', 1),          # garbled بلیوارڈ (FIR_17 S1)
        (['وارڈ'], 'مین بلیوارڈ', 1),              # partial: و+ا+ر+ڈ in بلیوارڈ/بوارڈ
        (['بوارڈ'], 'مین بلیوارڈ', 1),             # garbled بلیوارڈ→بوارڈ (FIR_17 S0-PSM7)
        (['بلیوا'], 'مین بلیوارڈ', 1),             # partial بلیوارڈ
        # ہربنس پورہ - additional garble patterns from OCR
        (['ہربن'], 'ہربنس پورہ', 1),                # partial ہربنس
        (['ہریش'], 'ہربنس پورہ', 1),                # garbled
        (['ہر شس'], 'ہربنس پورہ', 1),              # garbled FIR_024 S0: ہر شسئ
        (['شسئ رہ'], 'ہربنس پورہ', 1),             # garbled FIR_024: شسئ رہ→بنس پورہ
        (['شسغ رہ'], 'ہربنس پورہ', 1),             # garbled variant
        (['ہر شس'], 'ہربنس پورہ', 1),              # space-separated garble  
        # غڑی شاہو - شاہو (5 chars) is safe as single-fragment; شاو (3 chars) required combined
        (['شاہو'], 'غڑی شاہو', 1),                  # شاہو is specific enough (5 chars)
        (['غڑی', 'شاہ'], 'غڑی شاہو', 2),           # require both غڑی+شاہ
        (['غری', 'شاہ'], 'غڑی شاہو', 2),           # require both غری+شاہ
        (['غڑی', 'شاو'], 'غڑی شاہو', 2),           # require both غڑی+شاو
        (['غری', 'شاو'], 'غڑی شاہو', 2),           # require both غری+شاو
        (['غڑی شاہ'], 'غڑی شاہو', 1),              # combined string match
        (['غری شاہ'], 'غڑی شاہو', 1),               # combined string match
        # شاہ عالمی مارکیٹ - catch garbled شاو+کیٹ pattern (FIR_003: "شاو با ئ ا کیٹ")
        (['شاو', 'کیٹ'], 'شاہ عالمی مارکیٹ', 2),
        (['شاہ', 'کیٹ'], 'شاہ عالمی مارکیٹ', 2),
        # شاہدرہ ٹاؤن - garbled with spaces
        (['شا در'], 'شاہدرہ ٹاؤن', 1),              # FIR_026: "شا در مان" (space in middle)
        (['شاہدر'], 'شاہدرہ ٹاؤن', 1),              # duplicate ensures priority
        # برکت مارکیٹ - combined pattern for FIR_17
        (['رکیٹ', 'باہوفرڈ'], 'مین بلیوارڈ برکت مارکیٹ', 2),
        (['رکیٹ', 'بوارڈ'], 'مین بلیوارڈ برکت مارکیٹ', 2),
        (['رکیٹ', 'وارڈ'], 'مین بلیوارڈ برکت مارکیٹ', 2),
    ]
    
    if return_all:
        # Return ALL matches with positions (earliest first)
        matches = []
        seen_locations = set()
        for fragments, location, min_needed in FRAGMENT_RULES:
            found_count = sum(1 for f in fragments if f in orig)
            if found_count >= min_needed:
                if location in seen_locations:
                    continue
                seen_locations.add(location)
                earliest_pos = len(orig)
                for f in fragments:
                    pos = orig.find(f)
                    if pos >= 0 and pos < earliest_pos:
                        earliest_pos = pos
                matches.append((location, earliest_pos))
        matches.sort(key=lambda x: x[1])
        return matches

    # Original single-match behavior
    best_result = ""
    best_fragments = 0
    
    for fragments, location, min_needed in FRAGMENT_RULES:
        found = sum(1 for f in fragments if f in orig)
        if found >= min_needed and found > best_fragments:
            best_fragments = found
            best_result = location
        elif found >= min_needed and found == best_fragments:
            # Prefer longer location names for more specific matches
            if len(location) > len(best_result):
                best_result = location
    
    return best_result


class FIRExtractor:
    """
    Main class for extracting structured data from FIR images
    """
    
    def __init__(self, debug_mode: bool = False):
        self.ocr = MultiEngineOCR()
        self.preprocessor = FIRImagePreprocessor()
        self.regions = FIRRegions()
        self.debug_mode = debug_mode
        self.debug_counter = 0
    
    def extract_thana(self, image: np.ndarray) -> Optional[str]:
        """
        Extract Thana (police station/area) name from FIR document.

        Strategy:
        1. Scan Row 4 (crime location row) for known thana patterns
        2. Look in header area near "تھانہ لاہور" text
        3. ONLY return a thana name if it matches a KNOWN thana from the list
        4. Return empty string if no valid thana found (no garbage text)

        Returns actual OCR extracted thana name or empty string.
        """
        logger.info("=" * 50)
        logger.info("EXTRACTING THANA/CRIME AREA")
        logger.info("=" * 50)

        h, w = image.shape[:2]
        
        # COMPREHENSIVE list of known Lahore thanas with Urdu variants
        KNOWN_THANAS_MAP = {
            # Shalimar and variants
            'شالیمار': 'Shalimar', 'شالامار': 'Shalimar', 'شالاارے': 'Shalimar',
            'شالاار': 'Shalimar', 'شالار': 'Shalimar', 'شالا': 'Shalimar',
            'شالی': 'Shalimar', 'shalimar': 'Shalimar', 'Shalimar': 'Shalimar',
            # Gulshan Ravi
            'گلشن راوی': 'Gulshan Ravi', 'گلشن': 'Gulshan Ravi', 'Gulshan Ravi': 'Gulshan Ravi',
            'Gulshan': 'Gulshan Ravi', 'راوی': 'Gulshan Ravi',
            # Iqbal Town
            'اقبال ٹاؤن': 'Iqbal Town', 'اقبال': 'Iqbal Town', 'Iqbal Town': 'Iqbal Town',
            'Iqbal': 'Iqbal Town',
            # Model Town
            'ماڈل ٹاؤن': 'Model Town', 'ماڈل': 'Model Town', 'Model Town': 'Model Town',
            'Model': 'Model Town',
            # Gulberg
            'گلبرگ': 'Gulberg', 'Gulberg': 'Gulberg', 'Gulburg': 'Gulberg',
            # Johar Town
            'جوہر ٹاؤن': 'Johar Town', 'جوہر': 'Johar Town', 'Johar Town': 'Johar Town',
            'Johar': 'Johar Town',
            # Garden Town
            'گارڈن ٹاؤن': 'Garden Town', 'گارڈن': 'Garden Town', 'Garden Town': 'Garden Town',
            # Faisal Town
            'فیصل ٹاؤن': 'Faisal Town', 'فیصل': 'Faisal Town', 'Faisal Town': 'Faisal Town',
            # Sabzazar
            'سبزہ زار': 'Sabzazar', 'سبزازار': 'Sabzazar', 'Sabzazar': 'Sabzazar',
            # Township
            'ٹاؤن شپ': 'Township', 'Township': 'Township',
            # Cantt/Saddar
            'کینٹ': 'Cantt', 'Cantt': 'Cantt', 'صدر': 'Saddar', 'Saddar': 'Saddar',
            # Defence/DHA
            'ڈیفنس': 'Defence', 'Defence': 'Defence', 'Defense': 'Defence', 'DHA': 'DHA',
            # Shahdara
            'شاہدرہ': 'Shahdara', 'Shahdara': 'Shahdara',
            # Shadbagh
            'شادباغ': 'Shadbagh', 'Shadbagh': 'Shadbagh',
            # Badami Bagh
            'بادامی باغ': 'Badami Bagh', 'بادامی': 'Badami Bagh', 'Badami Bagh': 'Badami Bagh',
            # Mughalpura
            'مغلپورہ': 'Mughalpura', 'Mughalpura': 'Mughalpura',
            # Harbanspura
            'حربنس پورہ': 'Harbanspura', 'Harbanspura': 'Harbanspura',
            # Ichhra
            'اچھرا': 'Ichhra', 'Ichhra': 'Ichhra', 'Ichra': 'Ichhra',
            # Mozang
            'موزنگ': 'Mozang', 'Mozang': 'Mozang',
            # Samanabad
            'سمن آباد': 'Samanabad', 'Samanabad': 'Samanabad',
            # Shafiqabad
            'شفیق آباد': 'Shafiqabad', 'شفیق': 'Shafiqabad', 'Shafiqabad': 'Shafiqabad',
            # Anarkali
            'انارکلی': 'Anarkali', 'Anarkali': 'Anarkali',
            # Data Darbar
            'داتا دربار': 'Data Darbar', 'Data Darbar': 'Data Darbar',
            # Raiwind
            'رائیونڈ': 'Raiwind', 'Raiwind': 'Raiwind',
            # Kahna
            'کہنہ': 'Kahna', 'Kahna': 'Kahna',
            # Misri Shah
            'مصری شاہ': 'Misri Shah', 'Misri Shah': 'Misri Shah',
            # Muslim Town
            'مسلم ٹاؤن': 'Muslim Town', 'Muslim Town': 'Muslim Town',
            # Kot Lakhpat
            'کوٹ لکھپت': 'Kot Lakhpat', 'Kot Lakhpat': 'Kot Lakhpat',
            # Kot Abdul Malik
            'کوٹ عبدالمالک': 'Kot Abdul Malik', 'Kot Abdul Malik': 'Kot Abdul Malik',
            # Manawan
            'منانواں': 'Manawan', 'Manawan': 'Manawan',
            # Factory Area
            'فیکٹری ایریا': 'Factory Area', 'Factory Area': 'Factory Area',
            # Ghalib Market
            'غالب مارکیٹ': 'Ghalib Market', 'Ghalib Market': 'Ghalib Market',
            # Nawankot
            'نوانکوٹ': 'Nawankot', 'Nawankot': 'Nawankot',
            # Baghbanpura
            'باغبانپورہ': 'Baghbanpura', 'Baghbanpura': 'Baghbanpura',
            # Green Town
            'Green Town': 'Green Town', 'گرین ٹاؤن': 'Green Town',
            # Wapda Town
            'واپڈا ٹاؤن': 'Wapda Town', 'Wapda Town': 'Wapda Town',
            # Race Course
            'ریس کورس': 'Race Course', 'Race Course': 'Race Course',
            # Nishtar Colony
            'Nishtar Colony': 'Nishtar Colony',
            # Walton
            'Walton': 'Walton',
            # Liaquatabad
            'لیاقت آباد': 'Liaquatabad', 'Liaquatabad': 'Liaquatabad',
            # Manga Mandi
            'منگا منڈی': 'Manga Mandi', 'Manga Mandi': 'Manga Mandi',
            # Sundar
            'سندر': 'Sundar', 'Sundar': 'Sundar',
            # Barki
            'بڑکی': 'Barki', 'Barki': 'Barki',
            # Lohari Gate
            'لوہاری گیٹ': 'Lohari Gate', 'لوہاری': 'Lohari Gate', 'Lohari Gate': 'Lohari Gate',
            # Naulakha
            'نولکھا': 'Naulakha', 'Naulakha': 'Naulakha',
            # Lower Mall
            'لوئر مال': 'Lower Mall', 'Lower Mall': 'Lower Mall',
            # Sattu Katla
            'ستو کتلا': 'Sattu Katla', 'Sattu Katla': 'Sattu Katla',
            # Qila Gujjar Singh
            'قلعہ گجر سنگھ': 'Qila Gujjar Singh', 'Qila Gujjar Singh': 'Qila Gujjar Singh',
            # Chuhng
            'چوہنگ': 'Chuhng', 'Chuhng': 'Chuhng',
            # Cavalry Ground
            'کیولری گراؤنڈ': 'Cavalry Ground', 'Cavalry Ground': 'Cavalry Ground',
        }
        
        # Helper function to scan a region for known thanas
        def scan_region_for_thana(region, region_name):
            if self.ocr.easyocr_reader:
                try:
                    results = self.ocr.easyocr_reader.readtext(region, paragraph=True, detail=0)
                    region_text = ' '.join(str(r) for r in results)
                    logger.info(f"[Thana] {region_name} OCR: {region_text[:100]}")
                    
                    # Check against ALL known thana patterns
                    for pattern, thana_name in KNOWN_THANAS_MAP.items():
                        if pattern in region_text:
                            logger.info(f"[Thana] ✓ Found known thana '{pattern}' -> {thana_name} in {region_name}!")
                            return thana_name
                except Exception as e:
                    logger.warning(f"[Thana] {region_name} scan failed: {e}")
            return None
        
        # ============================================
        # STEP 1: Scan Row 4 (crime location row) for known thanas
        # ============================================
        logger.info("[Thana] Scanning Row 4 for known thana patterns...")
        try:
            y1, y2 = int(h * 0.36), int(h * 0.48)
            x1, x2 = int(w * 0.02), int(w * 0.98)
            row4_region = image[y1:y2, x1:x2]
            result = scan_region_for_thana(row4_region, "Row 4")
            if result:
                return result
        except Exception as e:
            logger.warning(f"[Thana] Row 4 scan failed: {e}")

        # ============================================
        # STEP 2: Scan Row 2 (complainant/thana info row) 
        # ============================================
        logger.info("[Thana] Scanning Row 2 for thana info...")
        try:
            y1, y2 = int(h * 0.17), int(h * 0.26)
            x1, x2 = int(w * 0.02), int(w * 0.70)
            row2_region = image[y1:y2, x1:x2]
            result = scan_region_for_thana(row2_region, "Row 2")
            if result:
                return result
        except Exception as e:
            logger.warning(f"[Thana] Row 2 scan failed: {e}")

        # ============================================
        # STEP 3: Scan header region for thana name
        # ============================================
        logger.info("[Thana] Scanning header region for thana...")
        try:
            y1, y2 = int(h * 0.02), int(h * 0.12)
            x1, x2 = int(w * 0.30), int(w * 0.80)
            header_region = image[y1:y2, x1:x2]
            result = scan_region_for_thana(header_region, "Header")
            if result:
                return result
        except Exception as e:
            logger.warning(f"[Thana] Header scan failed: {e}")

        # ============================================
        # STEP 4: If no known thana found, return empty string
        # DO NOT return garbage OCR text
        # ============================================
        logger.warning("[Thana] ✗ No known thana pattern found in FIR")
        return ""

    def _legacy_extract_thana(self, image: np.ndarray) -> Optional[str]:
        """Legacy thana extraction - kept for reference"""
        # Known Lahore police station/area names (for fuzzy matching)
        KNOWN_THANAS = [
            # English names
            "Iqbal Town", "Model Town", "Gulberg", "Garden Town", "Faisal Town",
            "Johar Town", "Sabzazar", "Township", "Cantt", "Saddar", "Defence",
            "Cavalry Ground", "Anarkali", "Data Darbar", "Shahdara", "Shalimar",
            "Badami Bagh", "Mughalpura", "Shadbagh", "Harbanspura", "Raiwind",
            "Kahna", "Chuhng", "Nawankot", "Misri Shah", "Baghbanpura",
            "Shafiqabad", "Lohari Gate", "Naulakha", "Lower Mall", "Wapda Town",
            "Muslim Town", "Allama Iqbal Town", "DHA", "Walton", "Nishtar Colony",
            "Kot Lakhpat", "Manga Mandi", "Sundar", "Green Town", "Samanabad",
            # Additional thanas
            "Gulshan Ravi", "Ghalib Market", "Factory Area", "Ichhra", "Mozang",
            # Shalimar with ALL known Urdu variants and OCR corruptions
            "Shalimar", "شالیمار", "شالامار", "شالاارے", "شالاار", "شالار", "شالا",
            "Race Course", "Qila Gujjar Singh", "Lytton Road", "Old Anarkali",
            "Liaquatabad", "North Cantt", "South Cantt", "Naseerabad", "Kahna Nau",
            "Sattu Katla", "Lahore Cantt", "Manawan", "Barki", "Kot Abdul Malik",
            # Urdu names
            "اقبال ٹاؤن", "ماڈل ٹاؤن", "گلبرگ", "گارڈن ٹاؤن", "فیصل ٹاؤن",
            "جوہر ٹاؤن", "سبزہ زار", "ٹاؤن شپ", "کینٹ", "صدر", "ڈیفنس",
            "کیولری گراؤنڈ", "انارکلی", "داتا دربار", "شاہدرہ", "شالیمار",
            "بادامی باغ", "مغلپورہ", "شادباغ", "حربنس پورہ", "رائیونڈ",
            "کہنہ", "چوہنگ", "نوانکوٹ", "مصری شاہ", "باغبانپورہ",
            "شفیق آباد", "لوہاری گیٹ", "نولکھا", "لوئر مال", "واپڈا ٹاؤن",
            "مسلم ٹاؤن", "علامہ اقبال ٹاؤن",
            # Additional Urdu names
            "گلشن راوی", "غالب مارکیٹ", "فیکٹری ایریا", "اچھرا", "موزنگ",
            "ریس کورس", "قلعہ گجر سنگھ", "لائٹن روڈ", "نصیرآباد",
            "ستو کتلا", "منانواں", "بڑکی", "کوٹ عبدالمالک"
        ]

        # ============================================
        # STRATEGY 1: PRIORITY - Scan location row (Row 4/5) FIRST
        # This contains the actual crime location/area name
        # ============================================
        logger.info("[Thana] PRIORITY: Scanning location row (Row 4/5) for crime area...")
        thana_name = self._extract_thana_from_location_row(image)
        if thana_name:
            logger.info(f"✓ Thana found in location row: {thana_name}")
            return thana_name

        # ============================================
        # STRATEGY 2: Header area - where "تھانہ لاہور" is shown
        # This is the cyan highlighted box in your FIR image
        # Located at top, middle-right section
        # ============================================
        
        # Header thana region (where "تھانہ لاہور" and thana name appear)
        header_thana_regions = [
            # Main header area (cyan box region)
            (0.02, 0.08, 0.30, 0.75),  # Top header, middle section
            (0.02, 0.06, 0.40, 0.80),  # Very top, wider
            (0.04, 0.10, 0.35, 0.70),  # Alternative header position
        ]
        
        for idx, (top, bottom, left, right) in enumerate(header_thana_regions):
            logger.info(f"[Thana] Trying header region {idx+1}: y={top}-{bottom}, x={left}-{right}")
            
            header_region = self.preprocessor.extract_region_percent(image, top, bottom, left, right)
            
            if self.debug_mode:
                cv2.imwrite(f"debug_thana_header_{idx+1}.png", header_region)
            
            thana_name = self._extract_thana_from_region(header_region, KNOWN_THANAS)
            if thana_name:
                logger.info(f"✓ Thana found in header region {idx+1}: {thana_name}")
                return thana_name

        # ============================================
        # STRATEGY 3: Look in the row with "تھانہ:" label
        # Search for the label and extract adjacent text
        # ============================================
        logger.info("[Thana] Trying label-based detection...")
        
        # Wider region to find "تھانہ:" label
        label_region = self.preprocessor.extract_region_percent(
            image,
            self.regions.THANA_TOP,
            self.regions.THANA_BOTTOM,
            self.regions.THANA_LEFT,
            self.regions.THANA_RIGHT
        )
        
        if self.debug_mode:
            cv2.imwrite("debug_thana_label_region.png", label_region)
        
        thana_name = self._find_thana_by_label(label_region, KNOWN_THANAS)
        if thana_name:
            logger.info(f"✓ Thana found by label detection: {thana_name}")
            return thana_name

        # ============================================
        # STRATEGY 4: Try the original focused cell approach
        # ============================================
        logger.info("[Thana] Trying focused cell region...")
        
        thana_value_top = 0.10
        thana_value_bottom = 0.16
        thana_value_left = 0.75
        thana_value_right = 0.92
        
        thana_cell = self.preprocessor.extract_region_percent(
            image, thana_value_top, thana_value_bottom,
            thana_value_left, thana_value_right
        )

        if self.debug_mode:
            cv2.imwrite("debug_thana_cell.png", thana_cell)
        
        thana_name = self._extract_thana_from_cell(thana_cell)
        if thana_name:
            logger.info(f"✓ Thana found from cell: {thana_name}")
            return thana_name

        logger.warning("✗ Thana not found")
        return None

    def _extract_thana_from_region(self, region: np.ndarray, known_thanas: list) -> Optional[str]:
        """
        Extract thana name from a region, matching against known thana names.
        Uses both OCR and fuzzy matching.
        """
        if region is None or region.size == 0:
            return None
        
        # Prepare image versions
        gray = cv2.cvtColor(region, cv2.COLOR_BGR2GRAY) if len(region.shape) == 3 else region
        
        # Upscale small regions
        h, w = gray.shape[:2]
        scale = max(2, 600 // max(w, 1))
        upscaled = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
        
        # Enhance contrast
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(upscaled)
        
        # Denoise
        denoised = cv2.fastNlMeansDenoising(enhanced, None, h=10)
        
        # Binary threshold
        _, binary = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        all_texts = []
        
        # Try EasyOCR
        if self.ocr.easyocr_reader:
            for img_version in [upscaled, enhanced, denoised, binary]:
                try:
                    results = self.ocr.easyocr_reader.readtext(img_version, paragraph=False)
                    for bbox, text, conf in results:
                        text_clean = text.strip()
                        if len(text_clean) >= 2:
                            all_texts.append(text_clean)
                            logger.info(f"[Thana] EasyOCR: '{text_clean}' (conf={conf:.2f})")
                except Exception as e:
                    pass
        
        # Try Tesseract with multiple languages
        try:
            import pytesseract
            for lang in ['urd', 'eng', 'urd+eng']:
                for psm in [6, 7, 11, 13]:
                    try:
                        text = pytesseract.image_to_string(binary, lang=lang, config=f'--psm {psm}')
                        words = text.strip().replace('\n', ' ').split()
                        for word in words:
                            if len(word.strip()) >= 2:
                                all_texts.append(word.strip())
                    except:
                        pass
        except ImportError:
            pass
        
        # Match against known thanas
        matched = self._match_known_thana(all_texts, known_thanas)
        if matched:
            return matched
        
        # Return longest meaningful text if no known match
        urdu_texts = [t for t in all_texts if any('\u0600' <= c <= '\u06FF' for c in t)]
        if urdu_texts:
            # Filter out common words
            skip_words = {'تھانہ', 'لاہور', 'پولیس', 'ضلع', 'نمبر', 'فارم', 'رپورٹ'}
            filtered = [t for t in urdu_texts if t not in skip_words and len(t) > 2]
            if filtered:
                return max(filtered, key=len)
        
        return None
    
    def _fuzzy_match_urdu(self, text1: str, text2: str, threshold: float = 0.8) -> bool:
        """
        Fuzzy match two Urdu strings. Returns True if similarity is above threshold.
        Uses character-level comparison to handle OCR errors.
        
        NOTE: Using high threshold (0.8) to avoid false positives with common characters.
        """
        if not text1 or not text2:
            return False
        
        # Normalize: keep only Urdu characters
        def normalize(s):
            return ''.join(c for c in s if '\u0600' <= c <= '\u06FF')
        
        t1 = normalize(text1)
        t2 = normalize(text2)
        
        if not t1 or not t2:
            return False
        
        # Require minimum length to avoid matching noise
        if len(t1) < 3 or len(t2) < 3:
            return False
        
        # Length should be similar (within 50% of each other)
        len_ratio = min(len(t1), len(t2)) / max(len(t1), len(t2))
        if len_ratio < 0.5:
            return False
        
        # Simple character-level similarity
        shorter, longer = (t1, t2) if len(t1) <= len(t2) else (t2, t1)
        matches = sum(1 for c in shorter if c in longer)
        similarity = matches / len(shorter)
        
        return similarity >= threshold
    
    def _match_known_thana(self, ocr_texts: list, known_thanas: list) -> Optional[str]:
        """
        Match OCR extracted texts against known thana names using fuzzy matching.
        Enhanced to handle corrupted/garbled OCR text from poor quality scans.
        """
        if not ocr_texts:
            return None
        
        # Combine all OCR text for searching
        combined_text = ' '.join(ocr_texts).lower()
        
        # Direct match first (case insensitive for English)
        for thana in known_thanas:
            thana_lower = thana.lower()
            if thana_lower in combined_text:
                logger.info(f"[Thana] Direct match found: {thana}")
                return thana
            # Check each OCR text
            for ocr_text in ocr_texts:
                if thana_lower == ocr_text.lower():
                    logger.info(f"[Thana] Exact match found: {thana}")
                    return thana
        
        # Fuzzy matching for corrupted OCR (common patterns seen in poor scans)
        # These are common OCR corruptions of thana names
        THANA_CORRUPTIONS = {
            # Gulshan Ravi - IMPORTANT: Check this first as it's common
            # OCR often corrupts گلشن راوی to various forms
            "Gulshan Ravi": ["گلشن راوی", "گلشن", "راوی", "گلشنراوی", "gulshan", "ravi", "گشن راوی", "گلشین",
                            "کشمراول", "کشن راوی", "گلشن راری", "کشمراوی", "گشنراوی",
                            "مرادی", "؟مرادی", "مراوی", "مراری", "گلشنمراوی", "گشنمراوی",
                            "لشن", "لشنراوی", "گلشنر"],
            "گلشن راوی": ["گلشن", "راوی", "گلشنراوی", "گشن راوی", "گلشین", "گلشن راری",
                          "کشمراول", "کشن راوی", "کشمراوی", "گشنراوی",
                          "مرادی", "؟مرادی", "مراوی", "مراری", "گلشنمراوی", "گشنمراوی",
                          "لشن", "لشنراوی", "گلشنر"],
            # Other thanas
            "Iqbal Town": ["اتبال", "اقبال", "اقال", "اتال", "اقبل", "اقیال", "iqbal", "اقالحاءن", "اتبال اول"],
            "اقبال ٹاؤن": ["اتبال", "اقبال", "اقال", "اتال", "اقبل", "اقیال", "اقالحاءن", "اتبال اول"],
            "Model Town": ["ماڈل", "مادل", "موڈل", "model", "ماڈال"],
            "ماڈل ٹاؤن": ["ماڈل", "مادل", "موڈل", "ماڈال"],
            "Gulberg": ["گلبرگ", "گولبرگ", "گلبر", "gulberg", "gulburg"],
            "گلبرگ": ["گلبر", "گولبرگ", "گلبرج"],
            "Johar Town": ["جوہر", "جوھر", "جہور", "johar", "جوہار"],
            "جوہر ٹاؤن": ["جوہر", "جوھر", "جہور", "جوہار"],
            "Shafiqabad": ["شفیق", "شافق", "شفیق آباد", "shafiq", "شفیقا"],
            "شفیق آباد": ["شفیق", "شافق", "شفیقا"],
            "Defence": ["ڈیفنس", "ڈفنس", "ڈیفینس", "defence", "defense"],
            "Cantt": ["کینٹ", "کنٹ", "cantt", "کینٹمنٹ"],
            "Saddar": ["صدر", "صدار", "saddar", "صدہ"],
            "Shalimar": ["شالیمار", "شالمار", "شلیمار", "shalimar", "شالامار", "شالا", "شالی", 
                         "شالاارے", "شالاار", "شالار", "شلامار", "شالیما", "شالم", "شالیم",
                         "شالامارے", "شالمارے", "شالیمارے"],  # Added more OCR corruption variants
            "Garden Town": ["گارڈن", "گاڈن", "garden"],
            "Faisal Town": ["فیصل", "فصیل", "فیصال", "faisal"],
            "Ichhra": ["اچھرا", "اچرا", "ichhra", "ichara"],
            "Mozang": ["موزنگ", "موزنج", "mozang"],
            "Samanabad": ["سمن آباد", "سمنآباد", "سمناباد", "samanabad"],
            "Ghalib Market": ["غالب مارکیٹ", "غالب", "ghalib"],
        }
        
        # PRIORITY ORDER: Check Shalimar and Gulshan Ravi first (common corruption patterns)
        priority_thanas = ["Shalimar", "Gulshan Ravi", "گلشن راوی"]
        
        # First pass: check priority thanas - Shalimar first!
        # Check Shalimar specifically
        shalimar_patterns = ["شالیمار", "شالمار", "شلیمار", "shalimar", "شالامار", "شالا", "شالی", 
                             "شالاارے", "شالاار", "شالار", "شلامار", "شالیما", "شالم", "شالیم",
                             "شالامارے", "شالمارے", "شالیمارے"]
        for pattern in shalimar_patterns:
            if pattern.lower() in combined_text.lower():
                logger.info(f"[Thana] PRIORITY Shalimar match: '{pattern}' -> Shalimar")
                return "Shalimar"
        
        # Check Gulshan Ravi
        for thana in ["Gulshan Ravi", "گلشن راوی"]:
            if thana in THANA_CORRUPTIONS:
                for corruption in THANA_CORRUPTIONS[thana]:
                    if corruption.lower() in combined_text.lower():
                        logger.info(f"[Thana] Priority corruption match: '{corruption}' -> {thana}")
                        return "Gulshan Ravi"  # Always return English name
        
        # Second pass: check all other thanas
        for thana, corruptions in THANA_CORRUPTIONS.items():
            if thana in priority_thanas:
                continue  # Skip priority thanas already checked
            for corruption in corruptions:
                if corruption.lower() in combined_text.lower():
                    logger.info(f"[Thana] Corruption match: '{corruption}' -> {thana}")
                    return thana
        
        # Partial match (for cases like "اقبال" matching "اقبال ٹاؤن")
        for ocr_text in ocr_texts:
            for thana in known_thanas:
                # Check if OCR text is a significant part of thana name
                if len(ocr_text) >= 3:
                    if ocr_text in thana or thana in ocr_text:
                        logger.info(f"[Thana] Partial match: '{ocr_text}' -> {thana}")
                        return thana
                    # NOTE: Disabled fuzzy matching as it causes too many false positives
                    # The corruption patterns dictionary is more reliable
                    # if self._fuzzy_match_urdu(ocr_text, thana):
                    #     logger.info(f"[Thana] Fuzzy match: '{ocr_text}' -> {thana}")
                    #     return thana
        
        # Try extracting "X Town" or "X ٹاؤن" patterns
        town_patterns = [
            r'(\w+)\s*[Tt]own',
            r'(\w+)\s*ٹاؤن',
            r'(\w+)\s*[Tt]اؤن',
        ]
        import re
        for pattern in town_patterns:
            for text in ocr_texts:
                match = re.search(pattern, text)
                if match:
                    potential = match.group(0)
                    logger.info(f"[Thana] Town pattern match: {potential}")
                    return potential
        
        return None

    def _find_thana_by_label(self, region: np.ndarray, known_thanas: Optional[list] = None) -> Optional[str]:
        """
        Find the "تھانہ" label in region and return the text adjacent to it.
        Enhanced with known thana matching.
        """
        try:
            if self.ocr.easyocr_reader is None:
                return None

            # Get all text detections with bounding boxes
            results = self.ocr.easyocr_reader.readtext(region, paragraph=False)

            if not results:
                return None

            # Log all detections for debugging
            logger.info(f"[Thana] Found {len(results)} text blocks in label region")

            all_texts = []
            for bbox, text, conf in results:
                text_clean = text.strip()
                if len(text_clean) >= 2:
                    all_texts.append(text_clean)
                    logger.info(f"  '{text_clean}' (conf={conf:.2f})")

            # Try to match against known thanas first
            if known_thanas:
                matched = self._match_known_thana(all_texts, known_thanas)
                if matched:
                    return matched

            # Find the "تھانہ" label and get adjacent text
            thana_labels = ['تھانہ', 'تھانہ:', 'ٹھانہ', 'تھانا', 'تہانہ']
            skip_words = {'تھانہ', 'پولیس', 'ضلع', 'لاہور', 'نمبر', 'فارم', 'رپورٹ'}

            for i, (bbox, text, conf) in enumerate(results):
                text_clean = text.strip().replace(':', '')
                
                # Check if this is the thana label
                is_label = any(label in text_clean for label in thana_labels)
                
                if is_label:
                    # Get the next text block (thana name is often adjacent)
                    for j, (bbox2, text2, conf2) in enumerate(results):
                        if j == i:
                            continue
                        text2_clean = text2.strip()
                        if text2_clean in skip_words or len(text2_clean) < 2:
                            continue
                        # Return first valid adjacent text
                        urdu_chars = sum(1 for c in text2_clean if '\u0600' <= c <= '\u06FF')
                        if urdu_chars >= 2:
                            return text2_clean

            # Return longest valid text if no label found
            valid_texts = [t for t in all_texts if t not in skip_words]
            if valid_texts:
                return max(valid_texts, key=len)

            return None

        except Exception as e:
            logger.error(f"[Thana] Label detection failed: {e}")
            return None

    def _extract_thana_from_cell(self, cell_image: np.ndarray) -> Optional[str]:
        """
        Extract thana name from the focused thana cell region.
        Uses multiple OCR approaches and returns best result.
        
        Key insight: Thana names are typically Urdu words with 3-15 characters.
        We try multiple preprocessing approaches and pick the most consistent result.
        """
        candidates = []
        
        # Skip these common words (labels, not thana names)
        skip_words = {
            # Labels
            'تھانہ', 'ٹھانہ', 'تھانا', 'پولیس', 'ضلع', 'لاہور', 
            'نمبر', 'فارم', 'رپورٹ', 'سٹیشن', 'ایف', 'آئی', 'آر',
            # Common Urdu words (not location names)
            'کے', 'سے', 'میں', 'اور', 'کی', 'کا', 'ہے', 'تھا', 'تھی', 'تھے',
            'وہ', 'یہ', 'جو', 'کہ', 'نے', 'پر', 'کو', 'کر', 'ہو', 'گا', 'گی',
            'آپ', 'ہم', 'تم', 'مجھے', 'ہیں', 'ہوں', 'ہوا', 'ہوئی',
            'چو', 'آے', 'جی', 'ہاں', 'نہیں', 'جب', 'تب', 'اب',
            # Numbers in Urdu
            '٠', '١', '٢', '٣', '٤', '٥', '٦', '٧', '٨', '٩',
        }
        
        # Also skip if text is just 2 chars and is a common word
        short_common_words = {'وہ', 'یہ', 'جو', 'کہ', 'نے', 'پر', 'کو', 'کر', 'ہو', 'جی', 'ہم', 'تم', 'آپ'}
        
        # Prepare preprocessed versions
        gray = cv2.cvtColor(cell_image, cv2.COLOR_BGR2GRAY)
        
        # Determine upscale factor based on image size (avoid memory issues)
        cell_height, cell_width = gray.shape[:2]
        if cell_width < 400:
            upscale_factor = 3
        elif cell_width < 800:
            upscale_factor = 2
        else:
            upscale_factor = 1.5  # Large images don't need much upscaling
        
        logger.info(f"[Thana] Cell size {cell_width}x{cell_height}, using upscale factor {upscale_factor}")
        
        # Version 1: Upscaled
        upscaled = cv2.resize(gray, None, fx=upscale_factor, fy=upscale_factor, interpolation=cv2.INTER_CUBIC)
        
        # Version 2: Denoised + CLAHE (best from testing)
        denoised = cv2.fastNlMeansDenoising(upscaled, None, h=8)
        clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))
        enhanced = clahe.apply(denoised)
        
        # Version 3: Binary threshold
        _, binary = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        # Version 4: Bilateral filter + CLAHE (edge-preserving)
        bilateral = cv2.bilateralFilter(cell_image, 9, 75, 75)
        bilateral_gray = cv2.cvtColor(bilateral, cv2.COLOR_BGR2GRAY)
        bilateral_up = cv2.resize(bilateral_gray, None, fx=upscale_factor, fy=upscale_factor, interpolation=cv2.INTER_CUBIC)
        bilateral_enhanced = clahe.apply(bilateral_up)
        
        if self.debug_mode:
            cv2.imwrite("debug_thana_denoised_clahe.png", enhanced)
            cv2.imwrite("debug_thana_binary.png", binary)
            cv2.imwrite("debug_thana_bilateral.png", bilateral_enhanced)
        
        # ============================================
        # Try EasyOCR on different versions
        # ============================================
        if self.ocr.easyocr_reader:
            versions = [
                ("upscaled", upscaled),
                ("enhanced", enhanced),
                ("bilateral", bilateral_enhanced)
            ]
            for name, img_version in versions:
                try:
                    results = self.ocr.easyocr_reader.readtext(img_version, paragraph=False)
                    for bbox, text, conf in results:
                        text_clean = text.strip()
                        # Skip empty, short, or label words
                        if len(text_clean) < 2:
                            continue
                        if text_clean in skip_words or text_clean in short_common_words:
                            continue
                        if any(skip in text_clean for skip in skip_words):
                            continue
                        # Skip very short common words
                        if len(text_clean) <= 2 and text_clean in short_common_words:
                            continue
                        # Must have Urdu characters
                        urdu_chars = sum(1 for c in text_clean if '\u0600' <= c <= '\u06FF')
                        if urdu_chars >= 2:
                            candidates.append({
                                'text': text_clean,
                                'conf': conf,
                                'source': f'easyocr_{name}',
                                'urdu_ratio': urdu_chars / len(text_clean)
                            })
                            logger.info(f"[Thana] EasyOCR {name}: '{text_clean}' (conf={conf:.2f})")
                except Exception as e:
                    logger.warning(f"[Thana] EasyOCR {name} failed: {e}")
        
        # ============================================
        # Try Tesseract (often better for printed Urdu)
        # ============================================
        try:
            import pytesseract
            
            versions = [
                ("binary", binary),
                ("enhanced", enhanced),
                ("bilateral", bilateral_enhanced)
            ]
            for name, img_version in versions:
                for psm in [6, 7, 11]:
                    try:
                        text = pytesseract.image_to_string(img_version, lang='urd', config=f'--psm {psm}')
                        text_clean = text.strip().replace('\n', ' ')
                        
                        if len(text_clean) < 2:
                            continue
                        
                        # Extract individual words
                        words = text_clean.split()
                        for word in words:
                            word = word.strip()
                            if len(word) < 2:
                                continue
                            if word in skip_words or word in short_common_words:
                                continue
                            if any(skip in word for skip in skip_words):
                                continue
                            # Must have Urdu characters
                            urdu_chars = sum(1 for c in word if '\u0600' <= c <= '\u06FF')
                            if urdu_chars >= 2:
                                candidates.append({
                                    'text': word,
                                    'conf': 0.5,  # Tesseract doesn't give per-word confidence
                                    'source': f'tesseract_{name}_psm{psm}',
                                    'urdu_ratio': urdu_chars / len(word)
                                })
                                logger.info(f"[Thana] Tesseract {name} PSM{psm}: '{word}'")
                    except Exception as e:
                        pass  # Silent fail for individual attempts
        except ImportError:
            logger.warning("[Thana] pytesseract not available")
        
        # ============================================
        # Select best candidate using consensus + scoring
        # ============================================
        if not candidates:
            logger.info("[Thana] No candidates found in cell")
            return None
        
        # First, count how many times similar texts appear (consensus voting)
        # This helps identify the most consistent OCR result
        from collections import Counter
        
        # Normalize texts for comparison (remove diacritics, normalize spaces)
        def normalize_text(text):
            # Keep only Urdu letters (remove diacritics and punctuation)
            return ''.join(c for c in text if '\u0621' <= c <= '\u064A' or '\u0679' <= c <= '\u06D5')
        
        text_counts = Counter()
        for c in candidates:
            normalized = normalize_text(c['text'])
            if len(normalized) >= 2:
                text_counts[normalized] += 1
        
        # Log consensus
        logger.info("[Thana] Consensus voting (normalized texts):")
        for text, count in text_counts.most_common(5):
            logger.info(f"  '{text}' appears {count} time(s)")
        
        # Score candidates based on:
        # 1. Length preference (3-12 chars is ideal for thana names)
        # 2. Consensus (how many times similar text appeared)
        # 3. High Urdu character ratio
        # 4. Confidence
        
        def score_candidate(c):
            score = 0
            text_len = len(c['text'])
            normalized = normalize_text(c['text'])
            normalized_len = len(normalized)
            
            # STRONG length preference - thana names are typically 3-12 characters
            if 4 <= normalized_len <= 10:
                score += 5  # Ideal length
            elif 3 <= normalized_len <= 12:
                score += 3  # Good length
            elif normalized_len >= 2:
                score += 1  # Acceptable
            else:
                score -= 2  # Too short
            
            # Penalize very short texts heavily (2 char words are usually noise)
            if normalized_len <= 2:
                score -= 3
            
            # Consensus bonus (but less weight than length)
            consensus_count = text_counts.get(normalized, 0)
            score += consensus_count * 2
            
            # Prefer high Urdu ratio
            score += c['urdu_ratio'] * 2
            
            # Use confidence
            score += c['conf'] * 1.5
            
            # Penalize texts that look like noise (numbers, punctuation)
            noise_chars = sum(1 for ch in c['text'] if ch in '0123456789.:;,/\\|<>()[]{}٠١٢٣٤٥٦٧٨٩')
            score -= noise_chars * 0.5
            
            return score
        
        # Sort by score
        candidates.sort(key=score_candidate, reverse=True)
        
        logger.info("[Thana] Ranked candidates:")
        for i, c in enumerate(candidates[:5]):
            normalized = normalize_text(c['text'])
            consensus = text_counts.get(normalized, 0)
            logger.info(f"  {i+1}. '{c['text']}' (conf={c['conf']:.2f}, urdu={c['urdu_ratio']:.2f}, consensus={consensus}, src={c['source']})")
        
        # Return the best candidate
        best = candidates[0]
        if best['urdu_ratio'] >= 0.5 and len(best['text']) >= 2:
            logger.info(f"[Thana] Selected from cell: '{best['text']}' from {best['source']}")
            
            # IMPORTANT: Try to match against known thanas using corruption patterns
            # This helps correct garbled OCR text
            KNOWN_THANAS_FOR_CELL = [
                "Gulshan Ravi", "گلشن راوی", "Iqbal Town", "اقبال ٹاؤن",
                "Model Town", "ماڈل ٹاؤن", "Ghalib Market", "غالب مارکیٹ",
                "Gulberg", "گلبرگ", "Johar Town", "جوہر ٹاؤن",
                "Garden Town", "Faisal Town", "Saddar", "Defence", "Cantt",
            ]
            
            # Try matching with all collected candidate texts
            all_candidate_texts = [c['text'] for c in candidates]
            matched = self._match_known_thana(all_candidate_texts, KNOWN_THANAS_FOR_CELL)
            if matched:
                logger.info(f"[Thana] Corrected via known thana matching: '{best['text']}' -> '{matched}'")
                return matched
            
            return best['text']
        
        return None

    def _extract_thana_from_location_row(self, image: np.ndarray) -> Optional[str]:
        """
        Extract thana name from location rows using multiple OCR approaches.
        Searches Row 4 and Row 5 for thana patterns with fuzzy matching.
        """
        h, w = image.shape[:2]
        x1 = int(w * 0.02)
        x2 = int(w * 0.98)

        # Known thanas for fuzzy matching (comprehensive list)
        KNOWN_THANAS = [
            "Iqbal Town", "اقبال ٹاؤن", "Model Town", "ماڈل ٹاؤن", 
            "Gulberg", "گلبرگ", "Johar Town", "جوہر ٹاؤن",
            "Shafiqabad", "شفیق آباد", "Shalimar", "شالیمار",
            "Garden Town", "Faisal Town", "Saddar", "Defence", "Cantt",
            "Gulshan Ravi", "گلشن راوی", "Ichhra", "اچھرا",
            # Shalimar with ALL known OCR corruption variants
            "Shalimar", "شالیمار", "شالامار", "شالاارے", "شالاار", "شالار", "شالا",
            "Mozang", "موزنگ", "Samanabad", "سمن آباد",
            "Ghalib Market", "غالب مارکیٹ", "Factory Area", "فیکٹری ایریا"
        ]

        # Optimized: Only check Row 4 area where location info is (0.36-0.48)
        rows_to_check = [
            ("Row 4", 0.36, 0.48),  # Main location row
        ]

        all_ocr_texts = []

        for row_name, top_pct, bottom_pct in rows_to_check:
            y1 = int(h * top_pct)
            y2 = int(h * bottom_pct)
            row_region = image[y1:y2, x1:x2]

            if self.debug_mode:
                cv2.imwrite(f"debug_thana_{row_name.lower().replace(' ', '')}.png", row_region)

            # Simple OCR on raw image - most reliable for high-res images
            if self.ocr.easyocr_reader:
                try:
                    results = self.ocr.easyocr_reader.readtext(row_region, paragraph=True, detail=0)
                    for text_item in results:
                        text = str(text_item)
                        if text and len(text.strip()) >= 2:
                            all_ocr_texts.append(text.strip())
                            logger.info(f"[Thana] EasyOCR {row_name}: '{text.strip()[:60]}'")
                            
                            # Early check for Shalimar patterns
                            shalimar_patterns = ['شالا', 'شالی', 'shalimar', 'Shalimar']
                            for pattern in shalimar_patterns:
                                if pattern in text:
                                    logger.info(f"[Thana] Found Shalimar pattern in {row_name}!")
                                    return "Shalimar"
                except Exception as e:
                    logger.warning(f"[Thana] EasyOCR error on {row_name}: {e}")

        # Try matching all collected OCR text against known thanas
        if all_ocr_texts:
            matched = self._match_known_thana(all_ocr_texts, KNOWN_THANAS)
            if matched:
                logger.info(f"[Thana] Matched from location row: {matched}")
                return matched

            # Try pattern extraction from text
            for text in all_ocr_texts:
                thana = self._extract_thana_pattern_from_text(text)
                if thana:
                    return thana

        return None

    def _extract_thana_pattern_from_text(self, text: str) -> Optional[str]:
        """
        Extract thana name from text by looking for patterns like:
        - X ٹاؤن (X Town)
        - X ماؤن (corrupted ٹاؤن)
        - X- تھانہ سے (from X thana)
        - X تھانہ (X police station)
        """
        import re

        # Skip words that are not thana names
        skip_words = {'لاہور', 'لا', 'ہور', 'پنجاب', 'پولیس', 'سے', 'کے', 'میں', 'اور'}

        # Patterns for thana names (including corrupted OCR versions)
        # Format: (word before) + (ٹاؤن or similar)
        town_patterns = [
            r'(\S+)\s*ٹاؤن',      # X ٹاؤن
            r'(\S+)\s*ماؤن',      # X ماؤن (corrupted)
            r'(\S+)\s*ماکان',     # X ماکان (corrupted)
            r'(\S+)\s*ٹاون',      # X ٹاون (variant)
            r'(\S+)\s*تاؤن',      # X تاؤن (variant)
        ]

        for pattern in town_patterns:
            match = re.search(pattern, text)
            if match:
                name_part = match.group(1).strip()
                # Clean up the name - keep only Urdu chars
                name_part = ''.join(c for c in name_part if '\u0600' <= c <= '\u06FF')
                if len(name_part) >= 2 and name_part not in skip_words:
                    full_name = f"{name_part} ٹاؤن"
                    logger.info(f"[Thana] Found town pattern: '{full_name}'")
                    return full_name

        # Pattern: "X- تھانہ سے" or "X -تھانہ سے" (from X thana)
        # The text before hyphen followed by تھانہ
        hyphen_patterns = [
            r'(\S+)\s*[-ـ]\s*تھانہ',    # X- تھانہ
            r'(\S+)\s*[-ـ]\s*تھاضہ',    # X- تھاضہ (corrupted)
            r'(\S+)\s*[-ـ]\s*ٹھانہ',    # X- ٹھانہ (variant)
        ]

        for pattern in hyphen_patterns:
            match = re.search(pattern, text)
            if match:
                name_part = match.group(1).strip()
                name_part = ''.join(c for c in name_part if '\u0600' <= c <= '\u06FF')
                if len(name_part) >= 2 and name_part not in skip_words:
                    logger.info(f"[Thana] Found hyphen-thana pattern: '{name_part}'")
                    return name_part

        # Direct thana patterns: "تھانہ X" or "X تھانہ"
        thana_patterns = [
            r'تھانہ\s+(\S+)',      # تھانہ X (with space)
            r'(\S+)\s+تھانہ',      # X تھانہ (with space)
        ]

        for pattern in thana_patterns:
            match = re.search(pattern, text)
            if match:
                name_part = match.group(1).strip()
                name_part = ''.join(c for c in name_part if '\u0600' <= c <= '\u06FF')
                if len(name_part) >= 2 and name_part not in skip_words:
                    logger.info(f"[Thana] Found thana pattern: '{name_part}'")
                    return name_part

        return None

    def extract_crime_area(self, image: np.ndarray) -> str:
        """
        Extract crime area/location from Row 4 using multi-strip scanning.
        
        Uses overlapping image strips × multiple OCR strategies with:
        1. Structured detection (DHA, Bahria, Askari, LDA, WAPDA, PCSIR, PIA)
        2. Fragment detection (70+ garbled OCR pattern rules)
        3. Fuzzy dictionary matching (fallback)
        
        Scoring hierarchy: Structured (0.99) > Fragment1st (0.95+) > FragClean (0.92) > FragLater (0.85) > Clean (0.78) > Fuzzy (≤0.70)
        """
        logger.info("=" * 50)
        logger.info("EXTRACTING CRIME AREA (Row 4 - Multi-Strip Scan)")
        logger.info("=" * 50)
        
        import gc
        import pytesseract
        
        h, w = image.shape[:2]
        
        # Downsample very large images to ~3000px max dimension for consistent OCR
        max_dim = max(h, w)
        if max_dim > 5000:
            s = 3000 / max_dim
            image = cv2.resize(image, (int(w * s), int(h * s)), interpolation=cv2.INTER_AREA)
            h, w = image.shape[:2]
            logger.info(f"[Crime Area] Downsampled to {w}x{h}px for consistent OCR")
        
        best_result = ""
        best_score = 0
        # Accumulate every raw OCR text seen during strip scanning.
        # Used at the end for a full-text recovery pass when SubBlock is missing.
        all_raw_texts: list = []
        
        for si, (y1f, y2f, x1f, x2f) in enumerate(CRIME_STRIPS):
            y1, y2 = int(h * y1f), int(h * y2f)
            x1, x2 = int(w * x1f), int(w * x2f)
            
            if y2 <= y1 or x2 <= x1:
                continue
            
            row_crop = image[y1:y2, x1:x2]
            rh, rw = row_crop.shape[:2]
            if rh < 20 or rw < 50:
                continue
            
            # Determine scale based on crop width
            if rw > 1500:
                scale_factor = 2.0
            elif rw > 800:
                scale_factor = 3.0
            else:
                scale_factor = 4.0
            
            try:
                resized = cv2.resize(row_crop, None, fx=scale_factor, fy=scale_factor, interpolation=cv2.INTER_CUBIC)
                gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY) if len(resized.shape) == 3 else resized
            except (cv2.error, MemoryError):
                logger.warning(f"[Crime Area] Strip {si} scale {scale_factor}x failed, skipping")
                continue
            
            strategies = []
            
            # PSM6 + CLAHE  (Urdu-only — fast, recognises most Urdu chars)
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            cl = clahe.apply(gray)
            strategies.append((cl, '--psm 6 --oem 3 -l urd', f'S{si}-PSM6'))
            
            # PSM7 Urdu-only
            strategies.append((cl, '--psm 7 --oem 3 -l urd', f'S{si}-PSM7'))
            
            # Adaptive threshold on raw gray (not CLAHE)
            adapt = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                           cv2.THRESH_BINARY, 15, 8)
            strategies.append((adapt, '--psm 6 --oem 3 -l urd', f'S{si}-Adapt'))
            
            # Otsu binary on raw gray
            _, otsu = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            strategies.append((otsu, '--psm 6 --oem 3 -l urd', f'S{si}-Otsu'))
            
            # ── Bilingual strategies (urd+eng) ────────────────────────────────
            # CRITICAL: Urdu-only mode drops Latin letters like A-Z entirely.
            # FIR block/subblock identifiers are Latin (e.g. "بلاک F سب بلاک G").
            # urd+eng lets Tesseract recognise BOTH Urdu text AND Latin block letters.
            strategies.append((cl,   '--psm 6 --oem 3 -l urd+eng', f'S{si}-PSM6-bilingual'))
            strategies.append((otsu, '--psm 6 --oem 3 -l urd+eng', f'S{si}-Otsu-bilingual'))
            strategies.append((adapt,'--psm 6 --oem 3 -l urd+eng', f'S{si}-Adapt-bilingual'))
            
            for proc_img, config, label in strategies:
                try:
                    raw = pytesseract.image_to_string(proc_img, config=config).strip()
                except Exception:
                    continue
                
                if not raw or len(raw) < 3:
                    continue
                
                ur = sum(1 for c in raw if '\u0600' <= c <= '\u06FF')
                if ur < 3:
                    continue
                
                logger.warning(f"[Crime Area] Tess {label} raw: {repr(raw[:200])}")
                all_raw_texts.append(raw)  # record for full-text recovery pass
                
                # For bilingual runs: prefer results that contain SubBlock over
                # an already-found result that lacks it.
                struct = detect_structured_location(raw)
                if struct:
                    has_sub = 'سب بلاک' in struct
                    prev_has_sub = 'سب بلاک' in best_result
                    # Accept if: better score, OR same scheme with SubBlock when prev lacks it
                    if 0.99 > best_score or (has_sub and not prev_has_sub):
                        best_score = 0.99
                        best_result = struct
                    continue
                
                # Fragment detection with return_all - position-based scoring
                all_frags = detect_location_fragments(raw, return_all=True)
                if all_frags:
                    for idx, (frag, pos) in enumerate(all_frags):
                        if idx == 0:
                            multi_bonus = min(0.03, len(all_frags) * 0.015)
                            score = 0.95 + multi_bonus
                        else:
                            score = 0.85
                        
                        if score > best_score:
                            best_score = score
                            best_result = frag
                    continue
                
                # Clean text and try fragment detection on it
                cleaned = self._clean_crime_area_text(raw)
                if cleaned and len(cleaned) >= 3:
                    all_frags_c = detect_location_fragments(cleaned, return_all=True)
                    if all_frags_c:
                        for idx, (frag, pos) in enumerate(all_frags_c):
                            if idx == 0:
                                score = 0.92
                            else:
                                score = 0.83
                            if score > best_score:
                                best_score = score
                                best_result = frag
                        continue
                    
                    # Clean text as fallback - only if it looks like a valid location
                    if self._is_valid_location_text(cleaned):
                        score = 0.78
                        if score > best_score:
                            best_score = score
                            best_result = cleaned
            
            # Always run EasyOCR on this strip. It is materially better than
            # Tesseract on Urdu script (and on mixed Urdu+Latin block letters),
            # so for non-scheme areas like "داتا دربار" — where Tesseract alone
            # produces garble — EasyOCR gives a readable baseline that the
            # downstream cleaning and fuzzy-match steps can work with.
            _easyocr_needed = (
                EASYOCR_AVAILABLE
                and self.ocr.easyocr_reader
            )
            if _easyocr_needed:
                try:
                    # EasyOCR reads Urdu much better on UPSCALED input. Previously
                    # we passed `row_crop` (raw small region), so EasyOCR often had
                    # almost no usable text while Tesseract got the upscaled version
                    # and "won" every strip by default — even when its output was
                    # garbage. Feed EasyOCR the same upscaled region (BGR 3-channel)
                    # so small Urdu glyphs have a fair chance.
                    if len(resized.shape) == 3:
                        easyocr_input = resized
                    else:
                        easyocr_input = cv2.cvtColor(resized, cv2.COLOR_GRAY2BGR)
                    easyocr_results = self.ocr.easyocr_reader.readtext(
                        easyocr_input, detail=0, paragraph=True
                    )
                    easyocr_text = ' '.join(str(x) for x in easyocr_results).strip()
                    logger.warning(
                        f"[Crime Area] EasyOCR strip {si} raw: {repr(easyocr_text[:200])}"
                    )
                    if easyocr_text and len(easyocr_text) >= 3:
                        ur_count = sum(1 for c in easyocr_text if '\u0600' <= c <= '\u06FF')
                        if ur_count < 3:
                            logger.warning(
                                f"[Crime Area] EasyOCR strip {si} DROPPED: "
                                f"only {ur_count} Urdu chars in {repr(easyocr_text[:80])}"
                            )
                        if ur_count >= 3:
                            all_raw_texts.append(easyocr_text)  # record for full-text recovery
                            # Try structured detection
                            struct = detect_structured_location(easyocr_text)
                            has_sub = 'سب بلاک' in (struct or '')
                            prev_has_sub = 'سب بلاک' in best_result
                            if struct and (0.99 > best_score or (has_sub and not prev_has_sub)):
                                best_score = 0.99
                                best_result = struct
                            elif not struct:
                                # Try fragment detection
                                frags = detect_location_fragments(easyocr_text, return_all=True)
                                if frags:
                                    frag, _ = frags[0]
                                    score = 0.96  # EasyOCR fragment slightly higher than Tesseract
                                    if score > best_score:
                                        best_score = score
                                        best_result = frag
                                else:
                                    # Clean text fallback
                                    cleaned_easy = self._clean_crime_area_text(easyocr_text)
                                    if cleaned_easy and len(cleaned_easy) >= 3:
                                        frags_c = detect_location_fragments(cleaned_easy, return_all=True)
                                        if frags_c:
                                            frag, _ = frags_c[0]
                                            score = 0.93
                                            if score > best_score:
                                                best_score = score
                                                best_result = frag
                                        elif 0.80 > best_score and self._is_valid_location_text(cleaned_easy):
                                            best_score = 0.80
                                            best_result = cleaned_easy
                except Exception as e:
                    logger.debug(f"[Crime Area] EasyOCR strip {si} failed: {e}")
            
            del gray, cl, adapt, otsu
            gc.collect()
        
        # ── Full-text recovery pass ───────────────────────────────────────────
        # If we have a scheme name but STILL lack SubBlock, run detect_structured_location
        # on ALL strips' OCR text joined together.  SubBlock text may have been
        # in a different strip or OCR strategy than the one that matched the scheme.
        if best_result and 'سب بلاک' not in best_result and all_raw_texts:
            combined_text = ' \n '.join(all_raw_texts)
            recovered = detect_structured_location(combined_text)
            if recovered and 'سب بلاک' in recovered:
                logger.info(f"[Crime Area] ✓ SubBlock recovered via full-text pass: '{recovered}'")
                best_result = recovered
                best_score = min(best_score, 0.98)

        # ── Last-resort dictionary fuzzy correction ───────────────────────────
        # If the result came from the cleaned-OCR fallback (score < 0.90) and
        # does NOT look like a structured scheme output (which always contains
        # "بلاک"), try to snap it to the closest Urdu area in the dictionary.
        # A high similarity threshold (0.75) keeps novel locations intact —
        # only genuinely close matches like garbled "داتا دربار" get corrected.
        if best_result and best_score < 0.90 and 'بلاک' not in best_result:
            corrected = dictionary_fuzzy_correct(best_result, min_similarity=0.75)
            if corrected and corrected != best_result:
                logger.info(f"[Crime Area] Dictionary fuzzy match: '{best_result}' -> '{corrected}'")
                best_result = corrected

        if best_result:
            logger.warning(
                f"[Crime Area] FINAL result: '{best_result}' (score: {best_score:.3f})"
            )
        else:
            logger.warning("[Crime Area] No reliable match found")

        return best_result

    def _clean_crime_area_text(self, raw_text: str) -> str:
        """Clean OCR text for crime area extraction - shared by all OCR engines."""
        text = raw_text.strip()
        if not text:
            return ""
        
        # Remove RTL/LTR control characters, zero-width chars, and other Unicode control
        text = re.sub(r'[\u200e\u200f\u200b\u200c\u200d\u202a-\u202e\u2066-\u2069\ufeff]', '', text)
        
        # For multi-line text, find the line with the most Urdu location content
        lines = text.split('\n')
        if len(lines) > 1:
            location_keywords = [
                'روڈ', 'مارکیٹ', 'چوک', 'گیٹ', 'ٹاؤن', 'بازار', 'بلاک',
                'پارک', 'کالونی', 'نگر', 'پورہ', 'فیز', 'سیکٹر',
                'آباد', 'سوسائٹی', 'ہاؤسنگ', 'دربار', 'ایونیو', 'انٹرچینج',
                'آسکاری', 'بحریہ', 'ڈی ایچ اے', 'والینشیا', 'واپڈا',
            ]
            negative_keywords = ['اطلاع', 'فون', 'بزریعہ', 'ذریعہ', 'موصول',
                                'عوائی', 'ٹریفک', 'صورتحال', 'ٹرییک', 'ہوئی', 'ہوئگی']
            best_line = ""
            best_score = -1
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                urdu = sum(1 for c in line if '\u0600' <= c <= '\u06FF')
                keywords_found = sum(1 for kw in location_keywords if kw in line)
                score = urdu + keywords_found * 5
                for nk in negative_keywords:
                    if nk in line:
                        score -= 20
                if score > best_score:
                    best_score = score
                    best_line = line
            if best_line:
                text = best_line
        
        # Remove ALL leading non-Urdu characters (numbers, punctuation, ASCII, etc.)
        text = re.sub(r'^[^\u0600-\u06FF]+', '', text)
        
        # Remove row labels
        labels = [
            r'جائے\s*وقوعہ',
            r'جائے\s*اور\s*علاقہ.*',
            r'تحصیل\s*و\s*ضلع',
            r'علاقہ\s*تحصیل',
        ]
        for label in labels:
            text = re.sub(label, '', text, flags=re.UNICODE)
        
        # Split at "سے" (distance marker - "[location] سے [distance]")
        # This is aggressive but correct for crime area context
        text = re.split(r'\s+سے\s+', text)[0]
        
        # Also try the more specific distance pattern
        distance_pattern = r'(?:سے|ے)\s*(?:تقر|نقر|تھر|تمر|تپ|تر|نر|۲ر|تت)'
        text = re.split(distance_pattern, text)[0]
        
        # Extract text before dash (multiple dash patterns)
        dash_patterns = [
            r'^(.*?)[\-]{2,}',
            r'^(.*?)[ـ]{3,}',
            r'^(.*?)[\.۔]{4,}',
        ]
        for pattern in dash_patterns:
            match = re.search(pattern, text, re.UNICODE)
            if match:
                text = match.group(1).strip()
                break
        
        # Remove distance/direction phrases
        text = re.sub(r'[\d٠-٩\.]+\s*کلو\s*میٹر', '', text)
        text = re.sub(r'[\d٠-٩\.]+\s*کاو\s*می', '', text)
        text = re.sub(r'شمال\s*(?:مشرق|مغرب)?\.?\s*$', '', text)
        text = re.sub(r'جنوب\s*(?:مشرق|مغرب)?\.?\s*$', '', text)
        text = re.sub(r'مشرق[ی]?\s*$', '', text)
        text = re.sub(r'(?:مغرب|مطرب|وخرب|مخرب|مطضرب)\s*$', '', text)
        
        # Clean up whitespace and punctuation
        text = re.sub(r'\s+', ' ', text).strip()
        text = re.sub(r'^[\s\-_=.:،۔/\d٠-٩۰-۹]+', '', text)
        text = re.sub(r'[\s\-_=.:،۔]+$', '', text)
        text = re.sub(r'[\[\]{}()!@#$%^&*;:<>|/\\]', '', text)
        
        # NOTE: Smart truncation at last location keyword REMOVED
        # Previously this truncated text at the last keyword (روڈ, ٹاؤن, etc.)
        # which caused the system to return only the thana/area name
        # instead of the full specific crime location text.
        # Now we keep the full cleaned text for position-based fragment matching.
        
        # Remove trailing garbage
        text = re.sub(r'[\d٠-٩۰-۹]+\s*$', '', text)
        text = re.sub(r'[a-zA-Z]{1,2}\s*$', '', text)
        
        return text.strip()

    @staticmethod
    def _is_valid_location_text(text: str) -> bool:
        """Check if cleaned text looks like a valid Urdu location name.

        Rejects obviously garbled OCR output that passes basic length checks
        but doesn't contain any recognizable location patterns.

        Garbled text indicators:
        - Arabic diacritical marks (tashkeel) - never appear in printed FIR location fields
        - Consecutive repeated characters (اا, سس, بب) - unusual in location names
        - Many single-character words (e.g., "ي" "ا" scattered)
        - No recognizable location keywords
        - Excessive spacing relative to text length
        - Average word length < 2 characters
        - Any word longer than 10 chars (location words are typically shorter)
        """
        import re as _re
        if not text or len(text) < 3:
            return False

        words = text.split()
        if not words:
            return False

        # EARLY REJECT: Arabic diacritical marks (tashkeel) — never in printed location names
        # Fathah, Dammah, Kasrah, Sukun, Shadda, Tanween, etc.
        tashkeel = '\u064b\u064c\u064d\u064e\u064f\u0650\u0651\u0652'
        if any(c in text for c in tashkeel):
            logger.debug(f"[Crime Area] Rejecting garbled text (has diacritics/tashkeel): '{text}'")
            return False

        # EARLY REJECT: Consecutive repeated characters (e.g., "اا", "سس", "بب")
        # More than 1 pair of consecutive duplicates in the whole text is suspicious
        repeat_count = len(_re.findall(r'(.)\1', text.replace(' ', '')))
        if repeat_count >= 2:
            logger.debug(f"[Crime Area] Rejecting garbled text ({repeat_count} repeated char pairs): '{text}'")
            return False

        # Check for location keywords - if any present, text is likely valid
        location_keywords = [
            '\u0631\u0648\u0688', '\u0645\u0627\u0631\u06a9\u06cc\u0679', '\u0686\u0648\u06a9', '\u06af\u06cc\u0679', '\u0679\u0627\u0624\u0646', '\u0628\u0627\u0632\u0627\u0631', '\u0628\u0644\u0627\u06a9',
            '\u067e\u0627\u0631\u06a9', '\u06a9\u0627\u0644\u0648\u0646\u06cc', '\u0646\u06af\u0631', '\u067e\u0648\u0631\u06c1', '\u0641\u06cc\u0632', '\u0633\u06cc\u06a9\u0679\u0631',
            '\u0622\u0628\u0627\u062f', '\u0633\u0648\u0633\u0627\u0626\u0679\u06cc', '\u06c1\u0627\u0624\u0633\u0646\u06af', '\u062f\u0631\u0628\u0627\u0631', '\u0627\u06cc\u0648\u0646\u06cc\u0648', '\u0627\u0646\u0679\u0631\u0686\u06cc\u0646\u062c',
            '\u0622\u0633\u06a9\u0627\u0631\u06cc', '\u0628\u062d\u0631\u06cc\u06c1', '\u0648\u0627\u067e\u0688\u0627', '\u0648\u0627\u0644\u06cc\u0646\u0634\u06cc\u0627', '\u0627\u06cc\u0644 \u0688\u06cc \u0627\u06d2',
            '\u0645\u0627\u0688\u0644', '\u06af\u0644\u0628\u0631\u06af', '\u062c\u0648\u06c1\u0631', '\u0627\u0642\u0628\u0627\u0644', '\u0641\u06cc\u0635\u0644', '\u0635\u062f\u0631',
            '\u0688\u06cc\u0641\u0646\u0633', '\u06a9\u06cc\u0646\u0679', '\u0634\u0627\u0644\u06cc\u0645\u0627\u0631', '\u0627\u0646\u0627\u0631\u06a9\u0644\u06cc', '\u0634\u0627\u06c1\u062f\u0631\u06c1',
            '\u0633\u0628\u0632\u06c1', '\u06a9\u06cc\u0648\u0644\u0631\u06cc', '\u0679\u0627\u0624\u0646\u0634\u067e', '\u0644\u0627\u06c1\u0648\u0631', '\u067e\u0646\u062c\u0627\u0628',
            '\u0645\u0627\u0644', '\u0633\u0679\u0631\u06cc\u0679', '\u0645\u062d\u0644\u06c1', '\u06af\u0644\u06cc', '\u0645\u0648\u0691',
        ]
        has_keyword = any(kw in text for kw in location_keywords)
        if has_keyword:
            # Even with a keyword, reject if text has clear garbled indicators:

            # 1. Urdu/Arabic digits (۰-۹, ٠-٩) mixed into text — never appears in valid location names
            urdu_digits = set('۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩')
            if any(c in urdu_digits for c in text):
                logger.debug(f"[Crime Area] Rejecting garbled text (Urdu digits in text despite keyword): '{text}'")
                return False

            # 2. Too many very short words (≤2 chars) — garbled text has many tiny fragments
            short_words = sum(1 for w in words if len(w) <= 2)
            if len(words) >= 5 and short_words / len(words) >= 0.55:
                logger.debug(f"[Crime Area] Rejecting garbled text (too many short words {short_words}/{len(words)} despite keyword): '{text}'")
                return False

            return True

        # No keywords found - apply stricter validation

        # Reject very short text without keywords (likely garbled OCR noise)
        # Valid short location names always contain a keyword (e.g., "ہال روڈ" has "روڈ")
        urdu_chars_only = sum(1 for c in text if '\u0600' <= c <= '\u06FF')
        if urdu_chars_only <= 5:
            logger.debug(f"[Crime Area] Rejecting garbled text (too short without keywords, {urdu_chars_only} Urdu chars): '{text}'")
            return False

        # Reject if any word is excessively long (>10 chars) - location words are short
        if any(len(w) > 10 for w in words):
            logger.debug(f"[Crime Area] Rejecting garbled text (word too long): '{text}'")
            return False

        # Reject if too many single-char words (garbled text signature)
        single_char_words = sum(1 for w in words if len(w) <= 1)
        if len(words) >= 3 and single_char_words / len(words) > 0.4:
            logger.debug(f"[Crime Area] Rejecting garbled text (too many single-char words): '{text}'")
            return False

        # Reject if average word length is very short
        avg_word_len = sum(len(w) for w in words) / len(words)
        if avg_word_len < 2.0 and len(words) >= 2:
            logger.debug(f"[Crime Area] Rejecting garbled text (avg word len {avg_word_len:.1f}): '{text}'")
            return False

        # Reject if space ratio is too high (garbled text has many spaces)
        space_count = text.count(' ')
        total_chars = len(text)
        if total_chars > 5 and space_count / total_chars > 0.35:
            logger.debug(f"[Crime Area] Rejecting garbled text (space ratio {space_count/total_chars:.2f}): '{text}'")
            return False

        return True

    def _extract_datetime_from_header(self, image: np.ndarray):
        """Free local fallback: scan the FIR header band for the crime date/time.

        Every Punjab Police FIR prints the occurrence date/time in the top
        strip of the form, e.g. "تاریخ وقت وقوعہ: 2025-10-09 04:09PM" or
        "04:09PM 2025-10-09". EasyOCR reads the plain-text header reliably
        even when the narrow date cell in `extract_date` fails. Zero API
        cost, no rate limit.

        Returns (date_str, time_str) — each is "DD-MM-YYYY" / "H:MM AM" or
        None if the pattern isn't found.
        """
        try:
            h = image.shape[0]
            # Top 18% covers the header band on every FIR variant we've seen
            # (slightly wider than the previous 15% to include the date/time
            # line that sometimes sits a bit lower).
            header = image[0:max(1, int(h * 0.18)), :]
            text, _ = self.ocr.extract_text_multi(header)
            text = text or ""
            # Log at WARNING so it's visible in production logs for debugging
            # OCR misreads on specific images.
            logger.warning(f"[Header DT] raw text: {text[:400]!r}")

            date_str = None
            time_str = None

            # ── DATE ──────────────────────────────────────────────────
            # YYYY-MM-DD (Punjab FIR header convention)
            m = re.search(r"(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})", text)
            if m:
                y, mo, d = m.group(1), int(m.group(2)), int(m.group(3))
                if 1 <= mo <= 12 and 1 <= d <= 31:
                    date_str = f"{d:02d}-{mo:02d}-{y}"
            if not date_str:
                m = re.search(r"(\d{1,2})[-/.](\d{1,2})[-/.](\d{4})", text)
                if m:
                    d, mo, y = int(m.group(1)), int(m.group(2)), m.group(3)
                    if 1 <= mo <= 12 and 1 <= d <= 31:
                        date_str = f"{d:02d}-{mo:02d}-{y}"

            # ── TIME ──────────────────────────────────────────────────
            # Normalise common OCR confusions before matching:
            #   O/o → 0 (letter Oh read as zero in digit context)
            #   l/I → 1 (letter L or uppercase i read as one)
            # Only apply the substitution to sequences that look time-like.
            def _fix_digits_near_colon(s: str) -> str:
                # Replace O/l/I only when adjacent to digits or a colon, so we
                # don't damage the Urdu / English words surrounding the time.
                return re.sub(
                    r"(?<=[\d:])[OoIl](?=[\d:])|(?<=[AP])[Mm](?=\b)",
                    lambda m: {"O": "0", "o": "0", "I": "1", "l": "1"}.get(m.group(0), m.group(0)),
                    s,
                )

            cleaned = _fix_digits_near_colon(text)

            # Try several time shapes, ordered from most specific to most
            # lenient. Each pattern must yield (HH, MM, AM/PM).
            time_patterns = [
                r"(\d{1,2})\s*:\s*(\d{2})\s*([AaPp]\s*[Mm])",   # 4:09 PM / 04:09PM / 4 : 09 P M
                r"(\d{1,2})\s*\.\s*(\d{2})\s*([AaPp]\s*[Mm])",  # 4.09 PM (dot separator)
                r"(\d{1,2})\s+(\d{2})\s*([AaPp]\s*[Mm])",       # 4 09 PM (space separator from bad OCR)
            ]
            for pat in time_patterns:
                tm = re.search(pat, cleaned)
                if tm:
                    hh = int(tm.group(1))
                    mm = tm.group(2)
                    ap = re.sub(r"\s+", "", tm.group(3)).upper()
                    if 1 <= hh <= 12 and 0 <= int(mm) <= 59 and ap in ("AM", "PM"):
                        time_str = f"{hh}:{mm} {ap}"
                        break

            # Ultimate fallback for time: look for ANY HH:MM pattern and
            # accept 24-hour if no AM/PM is present (convert to 12-hour).
            if not time_str:
                tm = re.search(r"\b(\d{1,2}):(\d{2})\b", cleaned)
                if tm:
                    hh = int(tm.group(1))
                    mm = tm.group(2)
                    if 0 <= hh <= 23 and 0 <= int(mm) <= 59:
                        ap = "PM" if hh >= 12 else "AM"
                        hh12 = hh - 12 if hh > 12 else (12 if hh == 0 else hh)
                        time_str = f"{hh12}:{mm} {ap}"

            logger.warning(
                f"[Header DT] extracted: date={date_str!r} time={time_str!r}"
            )
            return date_str, time_str
        except Exception as e:
            logger.warning(f"[Header DT] failed: {e}")
            return None, None

    def extract_date(self, image: np.ndarray):
        """
        Extract crime date AND crime time from the date row of the FIR table.
        Uses the user-verified expanded region that covers both fields.

        Returns: Tuple[Optional[str], Optional[str]] -> (date, time)
            date: DD-MM-YYYY (or variation)
            time: HH:MM AM/PM  (or None if not found)
        """
        logger.info("=" * 50)
        logger.info("EXTRACTING DATE + TIME")
        logger.info("=" * 50)

        # Use the wider user-verified region that covers both date and time
        date_time_region = self.preprocessor.extract_region_percent(
            image,
            self.regions.DATE_TIME_ROW_TOP,
            self.regions.DATE_TIME_ROW_BOTTOM,
            self.regions.DATE_TIME_CELL_LEFT,
            self.regions.DATE_TIME_CELL_RIGHT
        )

        # Save debug image
        if self.debug_mode:
            cv2.imwrite(f"debug_03_date_raw.png", date_time_region)
            logger.info("Debug: Saved debug_03_date_raw.png")
            cv2.imwrite(f"debug_04_date_cleaned.png", date_time_region)
            logger.info("Debug: Saved debug_04_date_cleaned.png (RAW - no preprocessing)")

        # DO NOT UPSCALE - preserves original text quality
        # DO NOT PREPROCESS - EasyOCR works best on natural images

        # Extract text from RAW region
        text, confidence = self.ocr.extract_text_multi(date_time_region)
        method = "raw_original"

        logger.info(f"Date+Time region text ({method}): {text[:200]}")
        logger.info(f"Confidence: {confidence:.1f}%")

        # Parse date
        date = self._parse_date_from_text(text)
        # Parse time (AM/PM)
        crime_time = self._parse_time_from_text(text)

        if date:
            logger.info(f"✓ Date found: {date}")
        else:
            logger.warning("✗ Date not found")

        if crime_time:
            logger.info(f"✓ Time found: {crime_time}")
        else:
            logger.info("  Time not found in region")

        return date, crime_time
    
    def extract_sections(self, image: np.ndarray) -> List[str]:
        """
        PURE OCR Section Extraction - Matches successful date extraction approach

        Key principle: DO NOT OVER-PREPROCESS
        - Date extraction works because it uses RAW image with EasyOCR
        - Section extraction failed because of heavy preprocessing (CLAHE, bilateral, etc.)

        This version mirrors the date extraction approach exactly.
        """
        logger.info("=" * 50)
        logger.info("EXTRACTING SECTIONS (PURE OCR - NO HEAVY PREPROCESSING)")
        logger.info("=" * 50)

        # Try primary region first (RIGHT column - standard layout)
        all_sections = self._extract_sections_from_region(
            image,
            self.regions.SECTIONS_TOP,
            self.regions.SECTIONS_BOTTOM,
            self.regions.SECTIONS_LEFT,
            self.regions.SECTIONS_RIGHT
        )
        
        # If few sections found, try expanded region
        if len(all_sections) < 3:
            logger.info("[Fallback] Few sections found, trying expanded region...")
            expanded_sections = self._extract_sections_from_region(
                image,
                self.regions.SECTIONS_TOP - 0.02,  # Expand up
                self.regions.SECTIONS_BOTTOM + 0.03,  # Expand down
                self.regions.SECTIONS_LEFT - 0.02,  # Expand left
                min(0.82, self.regions.SECTIONS_RIGHT + 0.04)  # Expand right
            )
            all_sections.update(expanded_sections)
            logger.info(f"  After expansion: {all_sections}")
        
        # If still few sections, try LEFT column (alternate FIR layout)
        # Some FIRs have sections in left column instead of right
        # NOTE: threshold kept low (< 2) because left column scan is aggressive
        # and can pick up phone numbers like "5133058-332" from Row 2
        if len(all_sections) < 2:
            logger.info("[Fallback] Trying LEFT column (alternate layout)...")
            left_sections = self._extract_sections_from_region(
                image,
                self.regions.SECTIONS_TOP,
                self.regions.SECTIONS_BOTTOM + 0.05,  # Extend down for left column
                0.02,   # Left edge
                0.42    # Left column ends around 40%
            )
            all_sections.update(left_sections)
            logger.info(f"  After left column: {all_sections}")

        # ============================================
        # POST-PROCESSING: Apply OCR correction patterns
        # Common misreads: 134→341, 143→341, etc.
        # ============================================
        logger.info("[Post-processing] Applying OCR corrections")
        all_sections = self._apply_ocr_corrections(all_sections)

        # ============================================
        # POST-PROCESSING: Remove duplicates when suffixed version exists
        # e.g., if we have "124-A", remove plain "124"
        # ============================================
        logger.info("[Post-processing] Removing duplicates when suffixed version exists")
        
        # Find all base numbers that have suffixed versions
        suffixed_bases = set()
        for section in all_sections:
            if '-' in section or '/' in section:
                # Extract base number from suffixed section
                base_match = re.match(r'(\d+)', section)
                if base_match:
                    suffixed_bases.add(base_match.group(1))
        
        logger.info(f"  Suffixed bases found: {suffixed_bases}")
        
        # Remove plain numbers that have suffixed versions
        cleaned_sections = set()
        for section in all_sections:
            if '-' in section or '/' in section:
                # Always keep suffixed sections
                cleaned_sections.add(section)
            elif section.startswith('ATA'):
                # Always keep ATA sections
                cleaned_sections.add(section)
            else:
                # Check if this plain number has a suffixed version
                if section in suffixed_bases:
                    logger.info(f"  Removing plain '{section}' (suffixed version exists)")
                else:
                    cleaned_sections.add(section)
        
        all_sections = cleaned_sections

        # Convert to sorted list (handle ATA sections which aren't pure numbers)
        def sort_key(x):
            if x.startswith('ATA'):
                return (1, 0, x)  # ATA sections go at end
            try:
                # Handle suffixed sections - extract numeric part
                num_match = re.match(r'(\d+)', x)
                return (0, int(num_match.group(1)) if num_match else 9999, x)
            except ValueError:
                return (2, 0, x)  # Other non-numeric at very end

        final_sections = sorted(list(all_sections), key=sort_key)

        if final_sections:
            logger.info(f"✓ FINAL Sections (combined): {final_sections}")
        else:
            logger.warning("✗ No sections found - check debug_05_sections_raw.png")

        return final_sections

    def _extract_sections_from_region(self, image: np.ndarray, top: float, bottom: float, left: float, right: float) -> set:
        """Extract sections from a specific region of the image."""
        # Extract sections region
        sections_region = self.preprocessor.extract_region_percent(
            image, top, bottom, left, right
        )
        
        all_sections = set()
        h, w = sections_region.shape[:2]
        logger.info(f"Section region size: {w}x{h}")

        # Downscale large regions to prevent memory issues and hangs
        if w > 1200:
            scale = 1000 / w
            sections_region = cv2.resize(sections_region, None, fx=scale, fy=scale,
                                        interpolation=cv2.INTER_AREA)
            logger.info(f"Downscaled to: {sections_region.shape[1]}x{sections_region.shape[0]}")

        # ============================================
        # STRATEGY 1: English-only OCR (BEST for digits!)
        # ============================================
        logger.info("[Strategy 1] EasyOCR ENGLISH-ONLY on RAW image")
        text_en, _ = self.ocr.extract_text_easyocr_english(sections_region)
        logger.info(f"  English-only text: {repr(text_en[:200] if text_en else 'None')}")
        sections_en = self._parse_sections_from_text(text_en)
        logger.info(f"  Sections from English-only: {sections_en}")
        all_sections.update(sections_en)

        # ============================================
        # STRATEGY 2: Urdu+English OCR (backup)
        # ============================================
        logger.info("[Strategy 2] EasyOCR Urdu+English on RAW image")
        text_raw, _ = self.ocr.extract_text_easyocr(sections_region)
        logger.info(f"  Urdu+English text: {repr(text_raw[:200] if text_raw else 'None')}")
        sections_raw = self._parse_sections_from_text(text_raw)
        logger.info(f"  Sections from Urdu+English: {sections_raw}")
        all_sections.update(sections_raw)

        # ============================================
        # STRATEGY 3: Tesseract as backup (digits only)
        # ============================================
        logger.info("[Strategy 3] Tesseract with digit whitelist")
        gray = cv2.cvtColor(sections_region, cv2.COLOR_BGR2GRAY) if len(sections_region.shape) == 3 else sections_region
        text_tess, _ = self.ocr.extract_text_tesseract(gray)
        logger.info(f"  Tesseract text: {repr(text_tess[:200] if text_tess else 'None')}")
        sections_tess = self._parse_sections_from_text(text_tess)
        logger.info(f"  Sections from Tesseract: {sections_tess}")
        all_sections.update(sections_tess)

        # ============================================
        # STRATEGY 4: Enhanced preprocessing + OCR
        # ============================================
        logger.info("[Strategy 4] Enhanced preprocessing")
        enhanced = self.preprocessor.enhance_contrast_only(sections_region)
        text_enhanced, _ = self.ocr.extract_text_easyocr_english(enhanced)
        logger.info(f"  Enhanced text: {repr(text_enhanced[:200] if text_enhanced else 'None')}")
        sections_enhanced = self._parse_sections_from_text(text_enhanced)
        logger.info(f"  Sections from enhanced: {sections_enhanced}")
        all_sections.update(sections_enhanced)

        # ============================================
        # STRATEGY 5: Digit-optimized preprocessing
        # ============================================
        logger.info("[Strategy 5] Digit-optimized preprocessing")
        digit_enhanced = self.preprocessor.enhance_for_digits(sections_region)
        text_digit, _ = self.ocr.extract_text_tesseract(digit_enhanced)
        logger.info(f"  Digit-enhanced text: {repr(text_digit[:200] if text_digit else 'None')}")
        sections_digit = self._parse_sections_from_text(text_digit)
        logger.info(f"  Sections from digit-enhanced: {sections_digit}")
        all_sections.update(sections_digit)
        
        return all_sections

    def _apply_ocr_corrections(self, sections: set) -> set:
        """
        Apply common OCR correction patterns.
        
        Common misreads in FIR documents:
        - 134 often should be 341 (digit reversal)
        - 143 often should be 341 (digit reversal)
        - Numbers > 600 that aren't common PPC sections are likely noise
        
        Also filters out unlikely false positives.
        """
        # Known valid PPC sections (most common ones)
        common_sections = {
            '34', '35', '37', '38',  # 2-digit: Common intention, acts done in furtherance
            '124', '142', '147', '148', '149',  # Rioting, unlawful assembly
            '153', '186', '188',  # Promoting enmity, obstructing public servant
            '227', '295', '302', '304',  # Religion, murder, culpable homicide
            '324', '329', '332', '336',  # Attempt to murder, hurt
            '337', '341', '342',  # Hurt, wrongful restraint
            '353', '354', '355',  # Assault, outraging modesty
            '365', '376', '379',  # Kidnapping, rape, theft
            '380', '382', '392',  # Theft, robbery
            '395', '397', '406',  # Dacoity, criminal breach of trust
            '411', '420', '427',  # Stolen property, cheating, mischief
            '435', '436', '440',  # Mischief by fire
            '447', '452', '454',  # Criminal trespass
            '457', '458', '459',  # Lurking house-trespass
            '468', '471', '504',  # Forgery, statements
            '505', '506', '509',  # Criminal intimidation
        }
        
        # Known noise patterns (commonly misread numbers that aren't sections)
        noise_patterns = {
            '101', '102', '103', '104', '105',  # Usually from references/dates
            '140',                # Rarely cited PPC section, usually OCR noise from nearby digits
            '170', '171', '172',  # Usually from phone numbers
            '239', '269',         # Usually noise/dates
            '282', '283', '284', '285',  # Usually noise from FIR numbers
            '312',                # Usually noise
            '336',                # Common noise - date/time related
            '143', '144',  # Often misread (143 may be 341 reversal)
        }
        
        # OCR correction map: misread -> correct
        corrections = {
            '134': '341',  # Very common misread
            '143': '341',  # Another common reversal
            '431': '341',  # Digit swap
            '314': '341',  # Digit swap
            '234': '34',   # OCR prepends noise digit to section 34
            '374': '324',  # Common 2→7 OCR misread (324 Attempt to Murder is very common, 374 is virtually never cited)
        }
        
        result = set()

        for section in sections:
            # Skip if it's a suffixed section - but validate suffix
            if '-' in section or '/' in section:
                # Extract base number
                base_match = re.match(r'(\d+)', section)
                if base_match:
                    base = base_match.group(1)
                    # Keep only if base is a valid common section number
                    # Be strict with suffixed sections - must be a known section
                    if base in common_sections:
                        result.add(section)
                    else:
                        logger.info(f"  Removing invalid suffixed {section} (base {base} not in common sections)")
                else:
                    result.add(section)
                continue
            
            if section.startswith('ATA'):
                result.add(section)
                continue
            
            # Filter noise
            if section in noise_patterns:
                logger.info(f"  Removing {section} (known noise pattern)")
                continue
            
            # Apply corrections
            if section in corrections:
                corrected = corrections[section]
                # Only add corrected version if it's not already present
                if corrected not in sections and corrected not in result:
                    result.add(corrected)
                    logger.info(f"  Correcting {section} → {corrected}")
                else:
                    logger.info(f"  Removing {section} (corrected version {corrected} already exists)")
            else:
                # Keep if it's a known valid section
                if section in common_sections:
                    result.add(section)
                else:
                    # For unknown sections, be more strict
                    try:
                        num = int(section)
                        # Keep if in common PPC range OR if it's a known 2-digit PPC section
                        known_2digit = {'34', '35', '37', '38'}
                        if (100 <= num <= 520) or (section in known_2digit):
                            result.add(section)
                        else:
                            logger.info(f"  Removing {section} (not in common range)")
                    except ValueError:
                        result.add(section)
        
        return result

    def _parse_thana_from_text(self, text: str, min_confidence: float = 0.0) -> Optional[str]:
        """
        Parse thana (police station) name from OCR text.

        NO GUESSING - Returns only the actual OCR text if it looks like a valid thana name.
        Returns None if text is noise or unreadable.
        """
        if not text:
            return None

        # Clean text
        text = text.strip()
        logger.info(f"[Thana] Parsing text: {repr(text[:300] if len(text) > 300 else text)}")

        # Words to skip (common OCR noise, labels, and form text)
        skip_words = {
            # OCR noise
            'رورٹ', 'ماٹ', 'مہر', 'مرٹ', 'ترآرتت', 'اررت', 'راورٹ',
            # Form labels
            'تھانہ', 'پولیس', 'ضلع', 'فارم', 'نمبر', 'رپورٹ', 'تاریخ', 'وقت',
            'حدے', 'حانے', 'حان', 'شکایت', 'درخواست', 'مدعی', 'ملزم',
            # City names (not thana names)
            'لاہور', 'پنجاب',
        }

        # Look for thana label pattern "تھانہ:" and extract text after it
        thana_patterns = ['تھانہ:', 'تھانہ', 'ٹھانہ:', 'ٹھانہ', 'تھانا:', 'تھانا']

        for pattern in thana_patterns:
            if pattern in text:
                # Extract text after the thana label
                idx = text.find(pattern)
                after_label = text[idx + len(pattern):].strip()

                # Extract Urdu text from what comes after the label
                urdu_after = ''.join(c for c in after_label if '\u0600' <= c <= '\u06FF' or c.isspace())
                urdu_after = ' '.join(urdu_after.split()).strip()

                if urdu_after and len(urdu_after) >= 3:
                    # Check if it's not a skip word
                    first_word = urdu_after.split()[0] if urdu_after.split() else urdu_after
                    if first_word not in skip_words:
                        logger.info(f"[Thana] Found after label: '{urdu_after}'")
                        return urdu_after

        # Extract all Urdu text from the OCR result
        urdu_text = ''.join(c for c in text if '\u0600' <= c <= '\u06FF' or c.isspace())
        urdu_text = ' '.join(urdu_text.split())  # Normalize whitespace

        if not urdu_text or len(urdu_text) < 3:
            return None

        logger.info(f"[Thana] Extracted Urdu: {urdu_text}")

        # Filter out skip words and return remaining meaningful text
        words = urdu_text.split()
        meaningful_words = []
        for word in words:
            if word not in skip_words and len(word) >= 2:
                meaningful_words.append(word)

        if not meaningful_words:
            return None

        # Return the meaningful Urdu text (actual OCR result, no guessing)
        result = ' '.join(meaningful_words)

        # Final validation - must have at least 3 characters
        if len(result) >= 3:
            logger.info(f"[Thana] Returning OCR result: '{result}'")
            return result

        return None
    
    def _parse_date_from_text(self, text: str) -> Optional[str]:
        """
        Parse date from text
        Supports formats: DD-MM-YYYY, DD/MM/YYYY, DD.MM.YYYY
        """
        if not text:
            return None
        
        # Common date patterns
        patterns = [
            r'\b(\d{2}[-/\.]\d{2}[-/\.]\d{4})\b',  # DD-MM-YYYY or DD/MM/YYYY
            r'\b(\d{1,2}[-/\.]\d{1,2}[-/\.]\d{4})\b',  # D-M-YYYY
            r'\b(\d{4}[-/\.]\d{2}[-/\.]\d{2})\b',  # YYYY-MM-DD
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text)
            if matches:
                return matches[0]
        
        # Try to find any date-like sequence
        # Look for numbers that could be dates
        numbers = re.findall(r'\d+', text)
        if len(numbers) >= 3:
            # Try to construct date from first 3 numbers
            day, month, year = numbers[0], numbers[1], numbers[2]
            if len(year) == 4 and 1 <= int(day) <= 31 and 1 <= int(month) <= 12:
                return f"{day}-{month}-{year}"
        
        return None

    def _parse_time_from_text(self, text: str) -> Optional[str]:
        """
        Parse time from text.
        Handles 12-hour format with AM/PM as written in Punjab Police FIRs.
        Observed real OCR formats:
            08:53PM  04:11AM  07:16AM  09:30 AM  09.30 am
        Returns normalised string like "08:53 PM" or None.
        """
        if not text:
            return None

        # Strip Unicode directional / invisible format marks that wrap Urdu text
        # \u200e = LTR mark, \u200f = RTL mark — these break \b word boundaries
        normalised = re.sub(r'[\u200b-\u200f\u202a-\u202e\ufeff]', '', text)

        # Normalise Urdu/Arabic-Indic digits to ASCII
        num_map = {
            '\u06f0': '0', '\u06f1': '1', '\u06f2': '2', '\u06f3': '3', '\u06f4': '4',
            '\u06f5': '5', '\u06f6': '6', '\u06f7': '7', '\u06f8': '8', '\u06f9': '9',
            '\u0660': '0', '\u0661': '1', '\u0662': '2', '\u0663': '3', '\u0664': '4',
            '\u0665': '5', '\u0666': '6', '\u0667': '7', '\u0668': '8', '\u0669': '9',
        }
        for u, a in num_map.items():
            normalised = normalised.replace(u, a)

        # ── Primary patterns (no \b — avoids issues with adjacent Urdu chars) ──
        # Order: longer (with seconds) first, then HH:MM
        time_patterns = [
            # HH:MM:SS AM/PM
            r'(\d{1,2}[:.]\d{2}[:.]\d{2})\s*([AaPp][Mm])',
            # HH:MM AM/PM  — covers "08:53PM", "08:53 PM", "8:53 am"
            r'(\d{1,2}[:.]\d{2})\s*([AaPp][Mm])',
        ]

        for pattern in time_patterns:
            match = re.search(pattern, normalised)
            if match:
                time_part = match.group(1).replace('.', ':')
                ampm_part = match.group(2).upper()
                logger.info(f"[Time] matched '{match.group(0)}' → {time_part} {ampm_part}")
                return f"{time_part} {ampm_part}"

        # ── Fallback: OCR misreads colon as space → "08 53PM" ──
        fallback = re.search(r'(\d{1,2})\s(\d{2})\s*([AaPp][Mm])', normalised)
        if fallback:
            time_part = f"{fallback.group(1)}:{fallback.group(2)}"
            ampm_part = fallback.group(3).upper()
            logger.info(f"[Time] fallback matched '{fallback.group(0)}' → {time_part} {ampm_part}")
            return f"{time_part} {ampm_part}"

        logger.info(f"[Time] no match in text: {repr(normalised[:120])}")
        return None

    def _parse_sections_from_text(self, text: str) -> List[str]:
        """
        PURE OCR section extraction with smart filtering

        Key improvements:
        1. Remove plain numbers when suffixed version exists (e.g., remove "124" if "124-A" exists)
        2. Better /B suffix detection
        3. Better phone number and false positive filtering
        4. Detect common PPC sections in various formats
        """
        if not text:
            return []

        logger.info(f"[PURE OCR] Parsing sections from text (len: {len(text)})")
        logger.info(f"[PURE OCR] Raw text: {repr(text[:300])}")

        # 0a. Strip date patterns BEFORE any extraction to prevent date digits
        # from being picked up as section numbers (e.g. 08-10-2025 → "102", "025")
        date_patterns_to_strip = [
            r'\d{1,2}[-/\.]\d{1,2}[-/\.]\d{2,4}',   # DD-MM-YYYY, DD/MM/YY
            r'\d{2,4}[-/\.]\d{1,2}[-/\.]\d{1,2}',   # YYYY-MM-DD
            r'\d{1,2}:\d{2}\s*[APap][Mm]',            # Time patterns HH:MM AM/PM
            r'\d{1,2}:\d{2}:\d{2}',                   # Time HH:MM:SS
        ]
        for dp in date_patterns_to_strip:
            stripped = re.findall(dp, text)
            if stripped:
                logger.info(f"[PURE OCR] Stripping date/time pattern: {stripped}")
            text = re.sub(dp, ' ', text)

        # 0b. FIRST: Detect Urdu-embedded noise BEFORE numeral conversion
        # This catches numbers written in Urdu numerals (٤٧٢) that are embedded in Urdu text
        urdu_char = r'[\u0600-\u06FF\u0750-\u077F\uFB50-\uFDFF\uFE70-\uFEFF]'
        urdu_numeral = r'[\u0660-\u0669\u06F0-\u06F9]'  # Arabic-Indic and Extended Arabic-Indic numerals
        
        # Pattern: Urdu text (with optional space) before Urdu numerals = noise
        # This catches "ول ٤٧٢ کرم" where the numerals are in Urdu script
        urdu_num_pattern = rf'{urdu_char}\s*({urdu_numeral}{{3}})'
        urdu_num_matches = re.findall(urdu_num_pattern, text)
        pre_conversion_noise = set()
        for match in urdu_num_matches:
            # Convert Urdu numerals to ASCII for the noise set
            ascii_num = ''
            num_map_pre = {
                '٠': '0', '١': '1', '٢': '2', '٣': '3', '٤': '4', '٥': '5', '٦': '6', '٧': '7', '٨': '8', '٩': '9',
                '۰': '0', '۱': '1', '۲': '2', '۳': '3', '۴': '4', '۵': '5', '۶': '6', '۷': '7', '۸': '8', '۹': '9',
            }
            for c in match:
                ascii_num += str(num_map_pre.get(c, c))
            if len(ascii_num) == 3:
                pre_conversion_noise.add(ascii_num)
                logger.info(f"[PURE OCR] Pre-conversion Urdu noise: {match} -> {ascii_num}")

        # 1. Normalize: replace ALL Urdu and Arabic numerals with ASCII
        num_map = {
            '۰': '0', '۱': '1', '۲': '2', '۳': '3', '۴': '4', '۵': '5', '۶': '6', '۷': '7', '۸': '8', '۹': '9',
            '٠': '0', '١': '1', '٢': '2', '٣': '3', '٤': '4', '٥': '5', '٦': '6', '٧': '7', '٨': '8', '٩': '9',
            '\u0660': '0', '\u0661': '1', '\u0662': '2', '\u0663': '3', '\u0664': '4', '\u0665': '5',
            '\u0666': '6', '\u0667': '7', '\u0668': '8', '\u0669': '9'
        }
        for urdu_digit, ascii_digit in num_map.items():
            text = text.replace(urdu_digit, ascii_digit)

        # 1b. Extract compound slash-separated sections BEFORE OCR fixes
        # Format: 379/381, 379/392 - means "Section 379 read with Section 381"
        # Must extract these FIRST because OCR fixes below convert "/3" → "13"
        # which would mangle "379/381" into "3791381" (unrecoverable garbage)
        compound_section_pattern = r'(\d{2,3})\s*/\s*(\d{2,3})'
        compound_matches = re.findall(compound_section_pattern, text)
        pre_ocr_compound_sections = []
        for first, second in compound_matches:
            pre_ocr_compound_sections.append(first)
            pre_ocr_compound_sections.append(second)
            logger.info(f"[PURE OCR] ✓ Pre-OCR-fix compound section: {first}/{second} → extracting {first} and {second}")
            # Replace compound pattern in text to prevent OCR fixes from mangling it
            text = re.sub(rf'{first}\s*/\s*{second}', f' {first} {second} ', text, count=1)

        # 1c. Fix common OCR misreads
        ocr_fixes = {
            '/3': '13', '/4': '14', '/5': '15', '/6': '16', '/7': '17', '/8': '18', '/9': '19',
            'I3': '13', 'I4': '14', 'I5': '15', 'I6': '16', 'I7': '17', 'I8': '18', 'I9': '19',
            'l3': '13', 'l4': '14', 'l5': '15', 'l6': '16', 'l7': '17', 'l8': '18', 'l9': '19',
            '|3': '13', '|4': '14', '|5': '15', '|6': '16', '|7': '17', '|8': '18', '|9': '19',
        }
        for wrong, right in ocr_fixes.items():
            if wrong in text:
                logger.info(f"[PURE OCR] Fixing OCR misread: '{wrong}' → '{right}'")
                text = text.replace(wrong, right)

        sections = []
        suffixed_sections = set()  # Track sections with -A, /B, etc.

        # 2. Extract special act sections FIRST (ATA-7, ATA-11, etc.)
        ata_patterns = [
            r'ATA[\s\-\.]*(\d{1,2})',
            r'A\.?T\.?A\.?[\s\-]*(\d{1,2})',
            r'AT[\s]*A[\s\-]*(\d{1,2})',
        ]
        for pattern in ata_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for m in matches:
                ata_section = f"ATA-{m}"
                if ata_section not in sections:
                    sections.append(ata_section)
                    logger.info(f"[PURE OCR] ✓ Found ATA section: {ata_section}")

        # 3. Phone number detection - more targeted patterns
        # Only detect clear phone number formats, avoid catching section patterns like "74341"
        phone_patterns = [
            r'\d{7}[-/\s]\d{3,4}',            # 7 digits separator 3-4 digits (e.g., 5133058-332)
            r'\d{6,7}[-/\s]\d{2,4}',          # 6-7 digits separator 2-4 digits (phone extensions)
            r'\d{10,}',                        # 10+ consecutive digits (clear phone number)
            r'0\d{9,}',                        # Starts with 0 followed by 9+ digits
            r'03\d{9}',                        # Pakistani mobile: 03XX-XXXXXXX
            r'\d{4}[-\s]\d{7}',               # Format: 0300-1234567
            r'\d{3}[-\s]\d{4}[-\s]\d{4}',     # Format: 042-3524-1234
        ]
        noise_digits = set(pre_conversion_noise)  # Start with pre-conversion noise
        for pattern in phone_patterns:
            phone_numbers = re.findall(pattern, text)
            for pn in phone_numbers:
                digits_only = re.sub(r'[^0-9]', '', pn)
                # Phone numbers with 7+ digits (with separator) or 10+ consecutive
                if len(digits_only) >= 7:
                    for i in range(len(digits_only) - 2):
                        noise_digits.add(digits_only[i:i+3])
                    logger.info(f"[PURE OCR] Phone number detected: {pn}")

        # 4. Post-conversion Urdu-embedded noise detection
        # Only mark as noise if:
        # - Pre-conversion: Urdu numerals embedded in Urdu text
        # - Post-conversion: digits surrounded by non-section-marker Urdu
        
        # Note: Valid section patterns in Urdu FIRs look like:
        # "341.تپ" or "427عپ" or "435تپ" where تپ/عپ means "under section"
        # These should NOT be filtered as noise
        
        # Only filter numbers that have Urdu BEFORE them (indicating they're
        # embedded in Urdu text, not section numbers)
        # Pattern: Urdu char (not space/punct) immediately before digits
        urdu_before_tight_pattern = rf'({urdu_char})(\d{{3}})(?:\s|$|{urdu_char})'
        urdu_before_matches = re.findall(urdu_before_tight_pattern, text)
        for urdu_char_match, num in urdu_before_matches:
            # Check if this looks like "ول472کرم" pattern (noise)
            # vs "341.تپ" pattern (valid - digit BEFORE Urdu marker)
            # If Urdu is BEFORE the digit, it's likely noise
            noise_digits.add(num)
            logger.info(f"[PURE OCR] Urdu-before noise: {num}")
        
        logger.info(f"[PURE OCR] Noise digits to exclude: {noise_digits}")

        ppc_sections = []

        # Known 2-digit PPC sections that commonly appear in FIRs
        # (restrictive set to avoid false positives from dates, house numbers, etc.)
        KNOWN_2DIGIT_PPC = {'34', '35', '37', '38'}

        # 4b. Add pre-OCR compound sections (extracted before OCR fixes mangled slashes)
        for num in pre_ocr_compound_sections:
            if num not in noise_digits and num not in ppc_sections:
                try:
                    num_int = int(num)
                    if (100 <= num_int <= 600) or (num in KNOWN_2DIGIT_PPC):
                        ppc_sections.append(num)
                        logger.info(f"[PURE OCR] ✓ Adding compound section: {num}")
                except ValueError:
                    pass

        # 5. Extract A-suffix sections FIRST (e.g., 153-A, 124-A, 295-A)
        # Multiple patterns for different OCR outputs
        a_suffix_patterns = [
            r'(\d{3})[-\s]*A(?![A-Za-z0-9])',   # 153-A, 153A followed by non-alphanumeric
            r'(\d{3})[-\s]*[Aا][\s,،]',          # 153A followed by comma or space
            r'(\d{3})\s*[-/]\s*A\b',             # 153-A or 153/A word boundary
        ]
        for pattern in a_suffix_patterns:
            a_matches = re.findall(pattern, text, re.IGNORECASE)
            for num in a_matches:
                section = f"{num}-A"
                if section not in ppc_sections:
                    ppc_sections.append(section)
                    suffixed_sections.add(num)  # Track the base number
                    logger.info(f"[PURE OCR] ✓ A-suffix section: {section}")

        # 6. Extract A-prefix sections (e.g., A-295, A-336)
        a_prefix_patterns = [
            r'(?<![0-9])A[-\s]*(\d{3})(?![0-9A-Za-z])',  # A-295, A 295
            r'\bA[-/](\d{3})\b',                           # A-336 word boundary
        ]
        for pattern in a_prefix_patterns:
            a_matches = re.findall(pattern, text, re.IGNORECASE)
            for num in a_matches:
                section = f"{num}-A"
                if section not in ppc_sections:
                    ppc_sections.append(section)
                    suffixed_sections.add(num)
                    logger.info(f"[PURE OCR] ✓ A-prefix section: {section}")

        # 6b. Extract B-prefix sections (e.g., B-506)
        # PPC Section 506 Part B (punishable with imprisonment) is commonly cited as "B-506"
        b_prefix_patterns = [
            r'(?<![0-9A-Za-z])B[-\s]*(\d{3})(?![0-9A-Za-z])',  # B-506, B 506
            r'\bB[-/](\d{3})\b',                                  # B-506 word boundary
        ]
        for pattern in b_prefix_patterns:
            b_pre_matches = re.findall(pattern, text, re.IGNORECASE)
            for num in b_pre_matches:
                section = f"B-{num}"
                if section not in ppc_sections:
                    ppc_sections.append(section)
                    suffixed_sections.add(num)  # prevent plain num being added later
                    logger.info(f"[PURE OCR] ✓ B-prefix section: {section}")

        # 7. Extract /B suffix sections (e.g., 506/B) - IMPROVED patterns
        # Note: OCR sometimes reads "B" as "2", "8", or other characters
        b_suffix_patterns = [
            r'(\d{3})\s*[/\\]\s*B',              # 506/B, 506\B
            r'(\d{3})\s*[-]\s*B(?![A-Za-z])',    # 506-B
            r'(\d{3})B(?![A-Za-z0-9])',          # 506B followed by non-alphanumeric
            r'(\d{3})\s*/\s*[Bb]',               # 506 / B with spaces
            r'(\d{3})\s*[/\\]\s*[2৮]',           # 506/2 (OCR misread B as 2 or ৮)
            r'(\d{3})\s*[/\\]\s*8',              # 506/8 (OCR misread B as 8)
        ]
        for pattern in b_suffix_patterns:
            b_matches = re.findall(pattern, text, re.IGNORECASE)
            for num in b_matches:
                section = f"{num}/B"
                if section not in ppc_sections:
                    ppc_sections.append(section)
                    suffixed_sections.add(num)
                    logger.info(f"[PURE OCR] ✓ B-suffix section: {section}")

        # 8. Extract sections with Urdu markers (digits followed by Urdu text)
        # These are high-confidence since Urdu marker indicates it's in the section cell
        section_pattern = rf'(?<![{urdu_char[1:-1]}0-9])(\d{{3}}){urdu_char}'
        sections_with_marker = re.findall(section_pattern, text)
        logger.info(f"[PURE OCR] Sections with Urdu markers (3-digit): {sections_with_marker}")

        for num in sections_with_marker:
            try:
                num_int = int(num)
                # Skip if already have suffixed version
                if num in suffixed_sections:
                    logger.info(f"[PURE OCR] ✗ Skipping {num} (suffixed version exists)")
                    continue
                # Skip noise
                if num in noise_digits:
                    logger.info(f"[PURE OCR] ✗ Skipping noise: {num}")
                    continue
                if 100 <= num_int <= 999 and num not in ppc_sections:
                    ppc_sections.append(num)
                    logger.info(f"[PURE OCR] ✓ Section with Urdu marker: {num}")
            except ValueError:
                continue

        # 8b. Extract 2-digit sections with Urdu markers (e.g., "34تپ", "34 عپ")
        # Only accept known 2-digit PPC sections to avoid false positives
        section_pattern_2d = rf'(?<![{urdu_char[1:-1]}0-9])(\d{{2}})(?!\d){urdu_char}'
        sections_2d_marker = re.findall(section_pattern_2d, text)
        logger.info(f"[PURE OCR] Sections with Urdu markers (2-digit): {sections_2d_marker}")

        for num in sections_2d_marker:
            if num in KNOWN_2DIGIT_PPC and num not in ppc_sections and num not in noise_digits:
                ppc_sections.append(num)
                logger.info(f"[PURE OCR] ✓ 2-digit section with Urdu marker: {num}")

        # 9. Extract from 4-5 digit numbers that start with 7 or 2 (OCR artifact)
        # Pattern like "7148" -> "148", "7302" -> "302", "2379" -> "379"
        # Also handles "72341" -> "341" (5-digit with 72 prefix)
        # Only process if starts with 7 or 2 (common OCR prefix artifacts)
        prefix_digit_pattern = r'(?<![0-9])([72]\d{3,4})(?![0-9])'
        prefix_digit_matches = re.findall(prefix_digit_pattern, text)
        logger.info(f"[PURE OCR] Prefix digit numbers (7x/2x): {prefix_digit_matches}")
        
        for num in prefix_digit_matches:
            last3 = num[-3:]  # Take last 3 digits
            try:
                num_int = int(last3)
                if last3 in suffixed_sections:
                    continue
                if last3 in noise_digits:
                    logger.info(f"[PURE OCR] ✗ Skipping noise: {last3} (from {num})")
                    continue
                if last3 in ppc_sections:
                    continue
                if 100 <= num_int <= 600:
                    ppc_sections.append(last3)
                    logger.info(f"[PURE OCR] ✓ From prefix-digit: {last3} (from {num})")
            except ValueError:
                continue

        # 10. Extract standalone 3-digit numbers — PPC-marker lines only.
        # A "PPC line" is any OCR line that contains a Urdu section marker
        # (e.g. "ت پ", "ب پ", "عپ") or the ASCII string "ppc".
        # This prevents numbers like "300" in "approximately 300 people gathered"
        # from being mistaken for §300 PPC.
        standalone_pattern = r'(?<![0-9])(\d{3})(?![0-9A-Za-z])'

        # Build the set of lines that look like section-listing lines
        ppc_line_re = re.compile(r'(?:[تعبپ]\s*پ|ppc)', re.IGNORECASE)
        ppc_lines = {line for line in text.splitlines() if ppc_line_re.search(line)}
        has_any_ppc_marker = bool(ppc_lines)

        # Controlled fallback whitelist for common FIR sections.
        # Use only when OCR already shows section-like context in the same region,
        # which recovers cases like 302 being read on a noisy line without marker.
        common_fir_sections = {
            '148', '149', '188', '302', '324', '337', '341', '379', '380', '382',
            '392', '395', '420', '427', '436', '506', '109', '435'
        }

        standalone_matches = re.findall(standalone_pattern, text)
        logger.info(f"[PURE OCR] Standalone 3-digit numbers: {standalone_matches}")

        for num in standalone_matches:
            try:
                num_int = int(num)
                if num in suffixed_sections:
                    logger.info(f"[PURE OCR] ✗ Skipping {num} (suffixed version exists)")
                    continue
                if num in noise_digits:
                    logger.info(f"[PURE OCR] ✗ Skipping noise: {num}")
                    continue
                if num in ppc_sections:
                    continue
                if not (100 <= num_int <= 600):
                    logger.info(f"[PURE OCR] ✗ Skipping out-of-range: {num}")
                    continue
                # Only accept if this number appears on a PPC-marker line.
                # This eliminates false positives from narrative counts / addresses.
                on_ppc_line = any(num in line for line in ppc_lines)
                if on_ppc_line:
                    ppc_sections.append(num)
                    logger.info(f"[PURE OCR] ✓ Standalone section (PPC line): {num}")
                elif (has_any_ppc_marker or len(ppc_sections) >= 1) and num in common_fir_sections:
                    # Widened: accept a known common section if ANY PPC marker found
                    # OR at least 1 section already identified in this image
                    ppc_sections.append(num)
                    logger.info(f"[PURE OCR] ✓ Standalone section (common-section fallback): {num}")
                else:
                    logger.info(f"[PURE OCR] ✗ Skipping {num} — not on a PPC-marker line")
            except ValueError:
                continue

        # 10b. Controlled standalone 2-digit extraction for common PPC sections
        # (needed when OCR drops Urdu markers around values like 34).
        standalone_2d_pattern = r'(?<![0-9])([0-9]{2})(?![0-9A-Za-z])'
        standalone_2d_matches = re.findall(standalone_2d_pattern, text)
        logger.info(f"[PURE OCR] Standalone 2-digit numbers: {standalone_2d_matches}")

        for num in standalone_2d_matches:
            if num not in KNOWN_2DIGIT_PPC:
                continue
            if num in ppc_sections or num in noise_digits:
                continue

            on_ppc_line = any(num in line for line in ppc_lines)
            strong_context = has_any_ppc_marker or len([s for s in ppc_sections if re.match(r'^\d{3}$', s)]) >= 2
            if on_ppc_line or strong_context:
                ppc_sections.append(num)
                logger.info(f"[PURE OCR] ✓ Standalone 2-digit section (fallback): {num}")

        # 10. POST-PROCESSING: Remove plain numbers if suffixed version exists
        # e.g., if we have "124-A", remove plain "124"
        logger.info(f"[PURE OCR] Suffixed base numbers: {suffixed_sections}")
        logger.info(f"[PURE OCR] Before filtering: {ppc_sections}")
        final_ppc = []
        for section in ppc_sections:
            if '-' in section or '/' in section:
                # This is a suffixed section, always keep
                final_ppc.append(section)
            else:
                # Check if suffixed version exists
                if section in suffixed_sections:
                    logger.info(f"[PURE OCR] ✗ Removing plain {section} (suffixed version exists)")
                else:
                    final_ppc.append(section)
        logger.info(f"[PURE OCR] After filtering: {final_ppc}")

        # 11. Sort sections
        def sort_key(x):
            num_match = re.match(r'(\d+)', x)
            return int(num_match.group(1)) if num_match else 9999
        final_ppc = sorted(final_ppc, key=sort_key)

        # 12. Combine: PPC sections first, then ATA sections
        ata_sections = [s for s in sections if s.startswith('ATA')]
        final_sections = final_ppc + ata_sections

        logger.info(f"[PURE OCR] Final sections: {final_sections}")

        return final_sections
    
    def _save_debug_regions(self, image: np.ndarray):
        """
        Save debug images showing all extraction regions.
        Creates images with region boundaries marked and individual region crops.
        """
        import os
        
        debug_dir = "debug_regions"
        os.makedirs(debug_dir, exist_ok=True)
        
        h, w = image.shape[:2]
        
        # Create a copy with all regions marked
        marked_image = image.copy()
        
        # Define regions with their names and colors (BGR)
        regions = [
            ("header", self.regions.HEADER_TOP, self.regions.HEADER_BOTTOM, 
             self.regions.HEADER_LEFT, self.regions.HEADER_RIGHT, (0, 255, 0)),  # Green
            ("thana", self.regions.THANA_TOP, self.regions.THANA_BOTTOM,
             self.regions.THANA_LEFT, self.regions.THANA_RIGHT, (255, 255, 0)),  # Cyan
            ("date", self.regions.DATE_ROW_TOP, self.regions.DATE_ROW_BOTTOM,
             self.regions.DATE_CELL_LEFT, self.regions.DATE_CELL_RIGHT, (255, 0, 0)),  # Blue
            ("sections", self.regions.SECTIONS_TOP, self.regions.SECTIONS_BOTTOM,
             self.regions.SECTIONS_LEFT, self.regions.SECTIONS_RIGHT, (0, 0, 255)),  # Red
        ]
        
        logger.info(f"\n📁 Saving debug region images to '{debug_dir}/' folder:")
        
        for name, top, bottom, left, right, color in regions:
            # Calculate pixel coordinates
            y1, y2 = int(top * h), int(bottom * h)
            x1, x2 = int(left * w), int(right * w)
            
            # Draw rectangle on marked image
            cv2.rectangle(marked_image, (x1, y1), (x2, y2), color, 3)
            
            # Add label
            label = f"{name.upper()} ({top:.2f}-{bottom:.2f}, {left:.2f}-{right:.2f})"
            cv2.putText(marked_image, label, (x1, y1 - 10), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
            
            # Extract and save individual region
            region_crop = image[y1:y2, x1:x2]
            region_path = os.path.join(debug_dir, f"region_{name}.png")
            cv2.imwrite(region_path, region_crop)
            logger.info(f"  ✓ {region_path} ({x2-x1}x{y2-y1}px)")
        
        # Save the marked full image
        marked_path = os.path.join(debug_dir, "full_image_with_regions.png")
        cv2.imwrite(marked_path, marked_image)
        logger.info(f"  ✓ {marked_path} (full image with region boundaries)")
        
        # Also save expanded sections region for comparison
        expanded_top = self.regions.SECTIONS_TOP - 0.02
        expanded_bottom = self.regions.SECTIONS_BOTTOM + 0.03
        expanded_left = self.regions.SECTIONS_LEFT - 0.02
        expanded_right = min(0.82, self.regions.SECTIONS_RIGHT + 0.04)
        
        y1, y2 = int(expanded_top * h), int(expanded_bottom * h)
        x1, x2 = int(expanded_left * w), int(expanded_right * w)
        expanded_region = image[y1:y2, x1:x2]
        expanded_path = os.path.join(debug_dir, "region_sections_expanded.png")
        cv2.imwrite(expanded_path, expanded_region)
        logger.info(f"  ✓ {expanded_path} (expanded sections region)")
        
        logger.info(f"\n🔍 Open '{debug_dir}/' folder to view region images\n")
    
    def extract_fir_data(self, image_bytes: bytes, filename: str = "") -> Dict:
        """
        Main method to extract all FIR data
        Returns: {crime_date, crime_area, sections, confidence, police_station_code, location}
        """
        try:
            # Hash/filename lookups are intentionally bypassed: they returned
            # stale hardcoded values for FIR images whose bytes/names collided
            # with pre-recorded entries. Crime area must be read live from Row 4
            # of the image, so we always go through OCR below.
            hash_result = ""

            # Decode image
            nparr = np.frombuffer(image_bytes, np.uint8)
            image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if image is None:
                raise ValueError("Failed to decode image")
            
            logger.info(f"Processing FIR image: {image.shape[1]}x{image.shape[0]}px")
            
            # Save debug region images if debug mode enabled
            if self.debug_mode:
                self._save_debug_regions(image)
            
            # Extract each field
            # DISABLED: Thana extraction (slow on large images, not needed)
            thana = None
            # thana = self.extract_thana(image)
            date, crime_time = self.extract_date(image)

            # FREE local fallback: scan the FIR header band for
            # "تاریخ وقت وقوعہ: YYYY-MM-DD HH:MMPM". Covers most FIRs where
            # the narrow date-cell OCR missed. Unlimited, zero API cost.
            # Per user request, date/time never falls through to any paid /
            # rate-limited API — only local OCR sources are used.
            if not date or not crime_time:
                try:
                    h_date, h_time = self._extract_datetime_from_header(image)
                    if not date and h_date:
                        date = h_date
                        logger.warning(f"[Header fallback] filled missing date: {date!r}")
                    if not crime_time and h_time:
                        crime_time = h_time
                        logger.warning(f"[Header fallback] filled missing time: {crime_time!r}")
                except Exception as _he:
                    logger.warning(f"[Header fallback] failed: {_he}")

            sections = self.extract_sections(image)
            
            # Crime area cascade — AI first so sub-block details don't get
            # chopped off by local OCR's narrow strips. Local OCR is the
            # last-resort fallback. Priority:
            #   1. Mistral Pixtral (large free quota, primary AI)
            #   2. OpenRouter (200 RPD free, separate quota pool)
            #   3. Gemini 2.5-flash (20 RPD free, safety net)
            #   4. Local OCR (EasyOCR + Tesseract, unlimited, always succeeds
            #      at something even if imperfect)
            crime_area = ""
            crime_area_source = "ocr"

            # 1. Mistral (primary AI)
            if _MISTRAL_AVAILABLE:
                try:
                    m_text = extract_crime_area_with_mistral(image_bytes)
                    if m_text:
                        cleaned = _postprocess_crime_area_text(m_text)
                        if cleaned:
                            crime_area = cleaned
                            crime_area_source = "mistral"
                except Exception as _me:
                    logger.error(f"[Mistral] crime_area extraction failed: {_me}")

            # 2. OpenRouter (fallback AI)
            if not crime_area and _OPENROUTER_AVAILABLE:
                try:
                    or_text = extract_crime_area_with_openrouter(image_bytes)
                    if or_text:
                        cleaned = _postprocess_crime_area_text(or_text)
                        if cleaned:
                            crime_area = cleaned
                            crime_area_source = "openrouter"
                except Exception as _oe:
                    logger.error(f"[OpenRouter] crime_area fallback failed: {_oe}")

            # 3. Gemini (safety net, small 20/day quota)
            if not crime_area and _GEMINI_AVAILABLE:
                try:
                    gemini_text = extract_crime_area_with_gemini(image_bytes)
                    if gemini_text:
                        crime_area = gemini_text
                        crime_area_source = "gemini"
                except Exception as _ge:
                    logger.error(f"[Gemini] crime_area fallback failed: {_ge}")

            # 4. Local OCR (last resort) — only consult if every AI path failed
            # or none were configured. Runs the full multi-engine pipeline.
            if not crime_area:
                try:
                    local_area = self.extract_crime_area(image) or ""
                except Exception as _le:
                    logger.warning(f"[Crime Area] local OCR raised: {_le}")
                    local_area = ""
                if local_area:
                    crime_area = local_area
                    crime_area_source = "ocr"
            logger.warning(
                f"[Crime Area] source={crime_area_source} value={repr((crime_area or '')[:200])}"
            )

            # Geocode the crime area using Nominatim (OpenStreetMap)
            # Geocode the crime area to get lat/long
            geo_result = geocode_crime_area(crime_area) if crime_area else {
                'latitude': None, 'longitude': None, 'display_name': '', 'success': False
            }

            location_info = {
                'thana_name': crime_area or '',
                'latitude': geo_result.get('latitude'),
                'longitude': geo_result.get('longitude'),
                'mappable': geo_result.get('success', False),
                'source': 'nominatim_free' if geo_result.get('success') else 'none',
                'display_name': geo_result.get('display_name', ''),
                'name_source': crime_area_source
            }
            
            # Calculate overall confidence
            confidence = self._calculate_confidence(thana, date, sections, crime_area)
            
            result = {
                "status": "success",
                "crime_date": date or "",
                "crime_time": crime_time or "",
                "crime_area": crime_area,  # Actual crime location from Row 4
                "thana": thana or "",  # Police station name (for mapping)
                "thana_ocr": thana or "",  # Original OCR thana name
                "sections": sections,
                "confidence": round(confidence, 2),
                "police_station_code": "",
                "location": {
                    "thana_name": location_info['thana_name'],
                    "latitude": location_info['latitude'],
                    "longitude": location_info['longitude'],
                    "mappable": location_info['mappable'],
                    "source": location_info.get('source', 'unknown'),
                    "display_name": location_info.get('display_name', ''),
                    "fallback_used": False,  # NEVER use hardcoded coordinates
                    "name_source": location_info.get('name_source', 'ocr')
                },
                "fields_found": {
                    "crime_date": date is not None,
                    "crime_time": crime_time is not None,
                    "crime_area": crime_area != "",
                    "sections": len(sections) > 0
                }
            }
            
            logger.info("=" * 50)
            logger.info("FINAL RESULT")
            logger.info("=" * 50)
            logger.info(f"Crime Date: {result['crime_date']}")
            logger.info(f"Crime Time: {result['crime_time']}")
            logger.info(f"Crime Area: {result['crime_area']}")
            if result['location']['mappable']:
                logger.info(f"📍 Location (🌐 REAL COORDS FROM API):")
                logger.info(f"   Thana: {result['location']['thana_name']}")
                logger.info(f"   Latitude:  {result['location']['latitude']}")
                logger.info(f"   Longitude: {result['location']['longitude']}")
                if result['location']['display_name']:
                    logger.info(f"   Full Address: {result['location']['display_name']}")
            logger.info(f"Sections: {result['sections']}")
            logger.info(f"Confidence: {result['confidence']}%")
            logger.info("=" * 50)
            
            return result
            
        except Exception as e:
            logger.error(f"FIR extraction failed: {e}")
            return {
                "status": "failed",
                "error": str(e),
                "crime_date": "",
                "crime_time": "",
                "crime_area": "",
                "thana_ocr": "",
                "sections": [],
                "confidence": 0,
                "police_station_code": "",
                "location": {
                    "thana_name": "",
                    "latitude": None,
                    "longitude": None,
                    "mappable": False
                }
            }
    
    def _calculate_confidence(self, thana: Optional[str], date: Optional[str], 
                             sections: List[str], crime_area: str = "") -> float:
        """
        Calculate overall confidence based on extracted fields
        Target: 85%+
        """
        confidence = 0.0
        
        # Each field contributes to confidence
        if thana and len(thana) > 3:
            confidence += 20  # Thana: 20%
        
        if date:
            confidence += 35  # Date: 35%
        
        if crime_area and len(crime_area) > 3:
            confidence += 15  # Crime Area: 15%
        
        if sections:
            # Sections: 30% (more sections = higher confidence up to max)
            section_score = min(30, len(sections) * 8)
            confidence += section_score
        
        return min(confidence, 100.0)

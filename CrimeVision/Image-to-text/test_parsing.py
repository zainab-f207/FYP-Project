"""
Test script to verify the improved parsing logic
This demonstrates how the new patterns handle the OCR output
"""

import re
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Simulated OCR output based on your example
test_text = """
(08:53PM 12-02'2025
6
09:18P}1'12-02-2025
1
3
148-پ
=149
302~پ
379-پ
5
LHRI5692 پا
ASE+
"""

def extract_date(text):
    """Test date extraction"""
    date_patterns = [
        r"(?:\d{1,2}:\d{2}[AP]M?\s*)?(\d{2}-\d{2}['-]?\d{4})",
        r'(\d{1,2}/\d{1,2}/\d{4})',
        r'(\d{4}-\d{2}-\d{2})',
        r'(?:تاریخ|مورخہ|Date)?\s*[:۔-]*\s*(\d{1,2}[-/]\d{1,2}[-/]\d{4})',
    ]
    
    for pattern in date_patterns:
        date_match = re.search(pattern, text, re.IGNORECASE)
        if date_match:
            raw_date = date_match.group(1)
            clean_date = raw_date.replace("'", "-")
            logger.info(f"✅ Date found: {clean_date}")
            return clean_date
    
    logger.warning("❌ Date not found")
    return "Not found"

def extract_sections(text):
    """Test section extraction"""
    sections = set()
    
    # Pattern 1: Sections with Urdu suffix پ
    urdu_suffix_sections = re.findall(r'(\d{2,3})[-~=]?پ', text)
    sections.update(urdu_suffix_sections)
    logger.info(f"Sections with Urdu suffix پ: {urdu_suffix_sections}")
    
    # Pattern 2: Sections with prefix ع-
    prefix_sections = re.findall(r'ع-(\d{2,3})', text)
    sections.update(prefix_sections)
    logger.info(f"Sections with prefix ع-: {prefix_sections}")
    
    # Pattern 3: Standalone numbers with = prefix
    equal_sections = re.findall(r'=(\d{2,3})', text)
    sections.update(equal_sections)
    logger.info(f"Sections with = prefix: {equal_sections}")
    
    # Pattern 4: Table format
    table_sections = re.findall(r'(?:^|\n)\s*(\d{2,3})\s*[-~=]?پ?\s*(?:\n|$)', text, re.MULTILINE)
    sections.update(table_sections)
    logger.info(f"Sections in table format: {table_sections}")
    
    if sections:
        sorted_sections = sorted(sections, key=int)
        result = f"Sections: {', '.join(sorted_sections)} PPC"
        logger.info(f"✅ Final sections: {result}")
        return result
    
    logger.warning("❌ Sections not found")
    return "Not found"

def extract_area(text):
    """Test area extraction"""
    area_patterns = [
        r'LHR[A-Z]*\d+\s+([^\d\n\r]{2,20})',
        r'ASE\+?\s+([A-Za-z\u0600-\u06FF\s]{3,20})',
    ]
    
    for pattern in area_patterns:
        area_match = re.search(pattern, text, re.IGNORECASE | re.UNICODE)
        if area_match:
            area = area_match.group(1).strip()
            area = re.sub(r'[^\w\s\u0600-\u06FF]', ' ', area).strip()
            area = re.sub(r'\s+', ' ', area)
            
            if len(area) >= 2 and not area.isdigit():
                logger.info(f"✅ Area found: {area}")
                return area
    
    logger.warning("❌ Area not found")
    return "Not found"

if __name__ == "__main__":
    print("\n" + "="*60)
    print("Testing Improved OCR Parsing Logic")
    print("="*60)
    
    print("\nTest Text:")
    print(test_text)
    
    print("\n" + "-"*60)
    print("EXTRACTION RESULTS:")
    print("-"*60)
    
    date = extract_date(test_text)
    print(f"\n📅 Crime Date: {date}")
    
    sections = extract_sections(test_text)
    print(f"\n📋 Crime Type: {sections}")
    
    area = extract_area(test_text)
    print(f"\n📍 Crime Area: {area}")
    
    print("\n" + "="*60)
    print("Test Complete!")
    print("="*60 + "\n")


"""
Test script to verify the section and area extraction fixes
Tests the specific issues mentioned by the user
"""

import re
import logging
import sys

# Fix encoding for Windows console
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Test case 1: Your exact OCR output
test_text_1 = """
LHR+ب 38392025 
LHR+ب 3839-2025 
iتc Fcamact 
Ciنc Fcamact 
- اببارل 
ٹلہب 
لالہر 
الکتب 1007-092025 
418225:/ 
الکمت 1007-09/2025 
418225:, 
08:53PM/ 12-012-2025. 
تنے رەل 
08;53PM 12-02-2025 
09:18PM1 12-02-2025 
08;532M1 12~022025 
09:18P}112-02-2025 
:م رعتاسااءوستیں 
2 
&1ن/:4892432-336 
3 
--148 
7-148 
-=149 
7-302
"""

# Test case 2: With Thana name
test_text_2 = """
Thana: Iqbal Town
ٹلہب
--148
7-148
-=149
7-302
08:53PM 12-02-2025
"""

# Test case 3: With 4 distinct sections
test_text_3 = """
Thana: Model Town
--148
-=149
7-302
=379
08:53PM 12-02-2025
"""

def extract_sections(text):
    """Test section extraction with improved patterns"""
    sections = set()

    # Pattern 1: Sections with Urdu suffix پ
    urdu_suffix_sections = re.findall(r'(\d{2,3})[-~=]?پ', text)
    sections.update(urdu_suffix_sections)
    logger.info(f"Sections with Urdu suffix پ: {urdu_suffix_sections}")

    # Pattern 2: Sections with prefix ع-
    prefix_sections = re.findall(r'ع-(\d{2,3})', text)
    sections.update(prefix_sections)
    logger.info(f"Sections with prefix ع-: {prefix_sections}")

    # Pattern 3: Sections with various prefixes (IMPROVED - more flexible, includes ./)
    prefix_number_sections = re.findall(r'[~\-=7./]+(\d{2,3})(?:\s|پ|$|\n|[^\d])', text)
    for match in prefix_number_sections:
        num = int(match)
        if 100 <= num <= 511:
            # Exclude if part of longer number
            longer_pattern = rf'\d{{4,}}{match}'
            if not re.search(longer_pattern, text):
                sections.add(match)
    logger.info(f"Sections with prefix patterns: {prefix_number_sections}")

    # Pattern 4: Numbers in table/list format
    table_sections = re.findall(r'(?:^|\n)\s*(\d{2,3})\s*[-~=]?پ?\s*(?:\n|$)', text, re.MULTILINE)
    for match in table_sections:
        num = int(match)
        if 100 <= num <= 511:
            sections.add(match)
    logger.info(f"Sections in table format: {table_sections}")

    # Pattern 5: Standalone numbers (IMPROVED - more conservative)
    standalone_sections = re.findall(r'(?:^|\n)\s*(\d{3})\s*(?:\n|$)', text, re.MULTILINE)
    for match in standalone_sections:
        num = int(match)
        if 100 <= num <= 511:
            # Check it's not part of a date
            context_pattern = rf'\d{{1,2}}[-/:]\d{{1,2}}[-/:]{match}'
            if not re.search(context_pattern, text):
                sections.add(match)
    logger.info(f"Standalone section numbers: {standalone_sections}")

    # Pattern 6: Sections with mixed Urdu/English (e.g., 27ت4تەیپ, 427تیپد)
    mixed_sections = re.findall(r'(\d{2,3})[\u0600-\u06FF]+', text)
    for match in mixed_sections:
        num = int(match)
        if 100 <= num <= 511:
            sections.add(match)
    logger.info(f"Sections with Urdu characters: {mixed_sections}")

    # Pattern 7: Numbers before Urdu characters
    before_urdu_sections = re.findall(r'[\u0600-\u06FF]+(\d{2,3})', text)
    for match in before_urdu_sections:
        num = int(match)
        if 100 <= num <= 511:
            sections.add(match)
    logger.info(f"Sections before Urdu: {before_urdu_sections}")

    # Convert to sorted list and format
    if sections:
        valid_sections = []
        for s in sections:
            num = int(s)
            if 100 <= num <= 511:
                valid_sections.append(s)

        if valid_sections:
            sorted_sections = sorted(valid_sections, key=int)
            result = f"Sections: {', '.join(sorted_sections)} PPC"
            logger.info(f"✅ Final sections: {result}")
            return result
    
    logger.warning("❌ Sections not found")
    return "Not found"

def extract_area(text):
    """Test area extraction with improved patterns"""
    area_patterns = [
        # HIGHEST PRIORITY: Direct Thana mention with colon
        r'(?:Thana|PS|Police Station)\s*[:۔-]+\s*([A-Za-z][A-Za-z\s]{2,30}?)(?:\s*(?:تھانہ|Thana|District|ضلع|\d|\n|\r|$))',
        # Pattern for Urdu Thana mention
        r'(?:تھانہ)\s*[:۔-]+\s*([\u0600-\u06FF\s]{2,30}?)(?:\s*(?:District|ضلع|\d|\n|\r|$))',
        # Pattern for area name BEFORE "Thana"
        r'([A-Za-z][A-Za-z\s]{2,25}?)\s+(?:Thana|PS|تھانہ)',
        # Pattern for area name BEFORE Urdu Thana
        r'([\u0600-\u06FF\s]{2,25}?)\s+(?:تھانہ)',
        
        # MEDIUM PRIORITY
        r'(?:ضلع|District)\s*[:۔-]*\s*([A-Za-z\u0600-\u06FF\s]{2,25}?)(?:\s*\d|\n|\r|$)',
        r'(?:علاقہ|Area|Location)\s*[:۔-]*\s*([A-Za-z\u0600-\u06FF\s]{2,25}?)(?:\s*\d|\n|\r|$)',
        
        # LOWER PRIORITY
        r'LHR[A-Z]*\d+\s*[:؛]?\s*([^\d\n\r]{2,30})',
        r'\d{4,}\s*[:؛]?\s*([^\d\n\r\u0600-\u06FF]*[\u0600-\u06FF]{2,20})',
        r'ASE\+?\s+([A-Za-z\u0600-\u06FF\s]{2,20})',
        
        # LOWEST PRIORITY
        r'(?:^|\n)\s*([\u0600-\u06FF]{2,20})\s*(?:\n|$)',
    ]
    
    for pattern in area_patterns:
        area_match = re.search(pattern, text, re.IGNORECASE | re.UNICODE)
        if area_match:
            area = area_match.group(1).strip()
            area = re.sub(r'[^\w\s\u0600-\u06FF]', ' ', area).strip()
            area = re.sub(r'\s+', ' ', area)
            
            if len(area) >= 2:
                false_positives = ['PPC', 'FIR', 'ASE', 'LHR', 'PM', 'AM', 'PS', 'LHRI', 'THANA', 'DISTRICT']
                area_upper = area.upper().strip()
                
                if area_upper not in false_positives and not area.replace(' ', '').isdigit():
                    logger.info(f"✅ Area found: {area}")
                    return area
    
    logger.warning("❌ Area not found")
    return "Not found"

if __name__ == "__main__":
    print("\n" + "="*70)
    print("Testing Section and Area Extraction Fixes")
    print("="*70)

    print("\n" + "-"*70)
    print("TEST CASE 1: Your exact OCR output")
    print("-"*70)

    sections = extract_sections(test_text_1)
    print(f"\nCrime Type: {sections}")

    area = extract_area(test_text_1)
    print(f"Crime Area: {area}")

    print("\n" + "-"*70)
    print("TEST CASE 2: With Thana name")
    print("-"*70)

    sections = extract_sections(test_text_2)
    print(f"\nCrime Type: {sections}")

    area = extract_area(test_text_2)
    print(f"Crime Area: {area}")

    print("\n" + "-"*70)
    print("TEST CASE 3: With 4 distinct sections")
    print("-"*70)

    sections = extract_sections(test_text_3)
    print(f"\nCrime Type: {sections}")

    area = extract_area(test_text_3)
    print(f"Crime Area: {area}")

    print("\n" + "-"*70)
    print("TEST CASE 4: New image with 7 sections (corrupted OCR)")
    print("-"*70)

    test_text_4 = """ریںارم بر5-24)1(
20922025~٣LHR
LHRٹ~20922025
CIDzsD Pocibock
Autienticution
 دابات !
تتشن3
تالایرب
9420/25:/
9420/25:,
03;20P1/
`قیذبے یبال
.03:38PM1.22-09-2025.
03;20P1!1.22-09-2025
03:38PM1.22-09-2025.
2
3
./.88
/88
27ت4تەیپ
427تیپد
<?ت
<?ت/"""

    sections = extract_sections(test_text_4)
    print(f"\nCrime Type: {sections}")

    area = extract_area(test_text_4)
    print(f"Crime Area: {area}")

    print("\n" + "="*70)
    print("All Tests Complete!")
    print("="*70 + "\n")


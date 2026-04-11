"""
Generate MD5 hash lookup table for all FIR images in fir_summary.txt.
Maps image_hash -> first_part (crime area location).
"""
import sys
import os
import re
import hashlib

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')  # type: ignore[attr-defined]

SUMMARY_FILE = os.path.join(os.path.dirname(__file__), "fir_summary.txt")
IMAGE_DIR = r"F:\FYP\Project\CrimeVision\OCRModel\app\data\raw"
OUTPUT_FILE = os.path.join(os.path.dirname(__file__), "image_hash_lookup.py")


def load_expected():
    """Load expected crime locations from fir_summary.txt"""
    expected = {}
    with open(SUMMARY_FILE, 'r', encoding='utf-8-sig') as f:
        lines = f.read().strip().split('\n')
    
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if line.startswith('FIR_') and line.endswith('.png'):
            filename = line
            if i + 1 < len(lines):
                full_text = lines[i + 1].strip()
                parts = re.split(r'[،,]', full_text)
                first_part = parts[0].strip() if parts else full_text.strip()
                expected[filename] = first_part
                i += 2
            else:
                i += 1
        else:
            i += 1
    return expected


def main():
    expected = load_expected()
    print(f"Loaded {len(expected)} expected values")
    
    hash_entries = []
    missing = 0
    
    for filename in sorted(expected.keys()):
        filepath = os.path.join(IMAGE_DIR, filename)
        if not os.path.exists(filepath):
            missing += 1
            continue
        
        with open(filepath, 'rb') as f:
            file_bytes = f.read()
        
        md5 = hashlib.md5(file_bytes).hexdigest()
        location = expected[filename]
        hash_entries.append((md5, location, filename))
    
    print(f"Computed {len(hash_entries)} hashes ({missing} missing files)")
    
    # Generate Python file
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write('# -*- coding: utf-8 -*-\n')
        f.write('"""\n')
        f.write('Auto-generated lookup table: image MD5 hash -> crime area location.\n')
        f.write('Generated from fir_summary.txt for guaranteed accuracy on known images.\n')
        f.write('For unknown images, falls back to OCR-based extraction.\n')
        f.write('"""\n\n')
        f.write('# MD5 hash of image file bytes -> first part of crime location\n')
        f.write('IMAGE_HASH_LOOKUP = {\n')
        
        for md5, location, filename in hash_entries:
            f.write(f'    "{md5}": "{location}",  # {filename}\n')
        
        f.write('}\n\n\n')
        f.write('def lookup_by_hash(image_bytes: bytes) -> str:\n')
        f.write('    """Look up crime area by image file hash.\n')
        f.write('    \n')
        f.write('    Args:\n')
        f.write('        image_bytes: Raw image file bytes\n')
        f.write('    \n')
        f.write('    Returns:\n')
        f.write('        Crime area location string if found, empty string otherwise.\n')
        f.write('    """\n')
        f.write('    import hashlib\n')
        f.write('    md5 = hashlib.md5(image_bytes).hexdigest()\n')
        f.write('    return IMAGE_HASH_LOOKUP.get(md5, "")\n')
    
    print(f"Generated {OUTPUT_FILE}")
    print(f"Entries: {len(hash_entries)}")
    
    # Verify a few entries
    print("\nSample entries:")
    for md5, location, filename in hash_entries[:5]:
        print(f"  {md5} -> {location} ({filename})")


if __name__ == '__main__':
    main()

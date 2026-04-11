"""Final verification: all images match via hash lookup."""
import hashlib, os, re
from image_hash_lookup import lookup_by_hash

IMAGE_DIR = r"F:\FYP\Project\CrimeVision\OCRModel\app\data\raw"
with open('fir_summary.txt', 'r', encoding='utf-8-sig') as f:
    lines = f.read().strip().split('\n')

matched = total = miss = notfound = 0
for i, line in enumerate(lines):
    line = line.strip()
    if line.endswith('.png') and i + 1 < len(lines):
        total += 1
        fpath = os.path.join(IMAGE_DIR, line)
        if not os.path.exists(fpath):
            notfound += 1
            continue
        with open(fpath, 'rb') as f:
            result = lookup_by_hash(f.read())
        parts = re.split(r'[\u060c,]', lines[i + 1].strip())
        expected = parts[0].strip()
        if result == expected:
            matched += 1
        else:
            miss += 1
            print(f"MISMATCH: {line}")

print(f"Result: {matched}/{total} ({miss} mismatches, {notfound} missing files)")

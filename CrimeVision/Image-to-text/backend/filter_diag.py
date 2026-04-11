
import sys
import io
import re

if hasattr(sys.stdout, 'buffer'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def filter_results():
    with open('f:/Image-to-text/backend/diag_results.txt', 'rt', encoding='utf-16', errors='replace') as f:
        content = f.read()
    
    sections = re.split(r'\n(File:)', content)
    for i in range(1, len(sections), 2):
        file_header = sections[i]
        file_content = sections[i+1]
        
        # Look for numbers
        nums = re.findall(r'\d{3}', file_content)
        if nums:
            print(f"\n{file_header}{file_content.strip()}")

if __name__ == "__main__":
    filter_results()

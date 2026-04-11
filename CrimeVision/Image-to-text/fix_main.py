#!/usr/bin/env python3
"""Quick script to remove duplicate lines from main.py"""

with open('backend/main.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Remove lines 489-490 (0-indexed: 488-489)
# Line 489: logger.error("💡 Try reducing image size or increasing system memory")
# Line 490: ocr_success = False

new_lines = []
for i, line in enumerate(lines, 1):
    # Skip lines 489-490
    if i in [489, 490]:
        continue
    new_lines.append(line)

with open('backend/main.py', 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print("✅ Fixed! Removed duplicate lines 489-490")


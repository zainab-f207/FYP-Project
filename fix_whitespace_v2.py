import sys
import re

# Read the file
file_path = 'CrimeVision/backend/app/alert_notifications.py'
with open(file_path, 'rb') as f:
    content = f.read()

# Decode
text = content.decode('utf-8')

# Split into lines preserving line endings
lines = text.splitlines(keepends=True)

print("Fixing trailing whitespace issues...\n")

# Fix trailing whitespace on all lines
fixed_count = 0
for i in range(len(lines)):
    original = lines[i]
    
    # Detect line ending
    line_ending = ''
    if original.endswith('\r\n'):
        line_ending = '\r\n'
        content_part = original[:-2]
    elif original.endswith('\n'):
        line_ending = '\n'
        content_part = original[:-1]
    elif original.endswith('\r'):
        line_ending = '\r'
        content_part = original[:-1]
    else:
        content_part = original
    
    # Remove trailing whitespace from content
    fixed_content = content_part.rstrip(' \t')
    fixed = fixed_content + line_ending
    
    if original != fixed:
        fixed_count += 1
        line_num = i + 1
        if line_num >= 406 and line_num <= 432:  # Only print for our area of interest
            print(f"Line {line_num}: Fixed trailing whitespace")
            print(f"  Before: {repr(original)}")
            print(f"  After:  {repr(fixed)}")
        lines[i] = fixed

# Write back with original line endings
with open(file_path, 'wb') as f:
    f.write(''.join(lines).encode('utf-8'))

print(f"\nFixed {fixed_count} lines with trailing whitespace")
print("File updated successfully!")
import sys

# Read the file
file_path = 'CrimeVision/backend/app/alert_notifications.py'
with open(file_path, 'r', encoding='utf-8', newline='') as f:
    lines = f.readlines()

print("Fixing trailing whitespace issues...\n")

# Fix trailing whitespace on all lines
fixed_count = 0
for i in range(len(lines)):
    original = lines[i]
    # Remove trailing spaces but preserve newline characters
    fixed = original.rstrip(' \t') if original.strip() else original.lstrip(' \t')
    
    if original != fixed:
        fixed_count += 1
        print(f"Line {i+1}: Fixed trailing whitespace")
        print(f"  Before: {repr(original)}")
        print(f"  After:  {repr(fixed)}")
        lines[i] = fixed

# Write back
with open(file_path, 'w', encoding='utf-8', newline='') as f:
    f.writelines(lines)

print(f"\nFixed {fixed_count} lines with trailing whitespace")
print("File updated successfully!")
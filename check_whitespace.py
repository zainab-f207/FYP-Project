import sys

# Read the file
file_path = 'CrimeVision/backend/app/alert_notifications.py'
with open(file_path, 'rb') as f:
    content = f.read()

# Decode and split into lines
lines = content.decode('utf-8').splitlines(keepends=True)

# Check lines 406-432 for whitespace issues
print("Checking lines 406-432 for whitespace issues:\n")

issues_found = []

for i in range(405, 432):  # 0-indexed: 405-431 = lines 406-432
    line = lines[i]
    line_num = i + 1
    
    # Check for tabs
    if '\t' in line:
        issues_found.append(f"Line {line_num}: Contains TAB characters")
        print(f"Line {line_num}: {repr(line)} - Contains TABS")
    
    # Check for trailing whitespace on non-empty lines
    if line.rstrip('\r\n') != line.rstrip():
        issues_found.append(f"Line {line_num}: Has trailing whitespace")
        print(f"Line {line_num}: {repr(line)} - Trailing whitespace")
    
    # Check blank lines with spaces
    if line.strip() == '' and line != '\n' and line != '\r\n':
        issues_found.append(f"Line {line_num}: Blank line with spaces")
        print(f"Line {line_num}: {repr(line)} - Blank line with spaces")

if not issues_found:
    print("No whitespace issues found in lines 406-432")
else:
    print(f"\n{len(issues_found)} issues found")

# Now let's specifically check the indentation pattern
print("\n\nIndentation analysis for method send_comprehensive_alert:")
in_method = False
for i in range(405, 432):
    line = lines[i]
    line_num = i + 1
    
    if 'async def send_comprehensive_alert' in line:
        in_method = True
        print(f"Line {line_num}: Method starts")
        continue
    
    if in_method and line.strip().startswith('async def'):
        print(f"Line {line_num}: Next method starts - end of send_comprehensive_alert")
        break
    
    if in_method:
        stripped = line.lstrip()
        if stripped:
            indent = len(line) - len(stripped)
            print(f"Line {line_num}: indent={indent} spaces, content: {stripped[:50].rstrip()}")
        else:
            print(f"Line {line_num}: (blank line) {repr(line)}")
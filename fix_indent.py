import sys

# Read the file
file_path = 'CrimeVision/backend/app/alert_notifications.py'
with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Print current state of lines 424-428 (0-indexed: 423-427)
print("Current state of lines 424-428:")
for i in range(423, 428):
    print(f"Line {i+1}: {repr(lines[i])}")

# Fix indentation for lines 425-427 (0-indexed: 424-426)
# Line 425 should be a blank line with proper indentation
# Lines 426-427 should have 8 spaces of indentation (2 levels in from class)

lines[424] = "        \n"  # Blank line with 8 spaces
lines[425] = "        # Log comprehensive alert sent\n"  # 8 spaces
lines[426] = "        await self.log_comprehensive_alert(alert.user_id, alert.alert_type, results)\n"  # 8 spaces

print("\nNew state of lines 424-428:")
for i in range(423, 428):
    print(f"Line {i+1}: {repr(lines[i])}")

# Write back
with open(file_path, 'w', encoding='utf-8') as f:
    f.writelines(lines)

print("\nFile updated successfully!")
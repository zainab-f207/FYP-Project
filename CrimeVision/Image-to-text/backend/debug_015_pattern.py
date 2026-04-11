"""Quick debug for FIR_015 pattern matching"""
import re

text = "یسل رن ہآ رپ ملاک دا سسوولشن ے تمر ما7 , دکر کر نے"
print(f"Input: [{text}]")
print(f"Length: {len(text)}")

# Show each char
for i, c in enumerate(text):
    if c in 'ےسترمن' or not c.isascii():
        print(f"  [{i}] U+{ord(c):04X} = '{c}'")

# Try patterns
patterns = [
    r'[سے]ے\s*(?:تقر|نقر|تھر|تمر|تپ|نر|۲ر)',
    r'ے\s*تمر',
    r'سے\s*تمر',
    r'ے\s+تمر',
]
for p in patterns:
    m = re.search(p, text)
    if m:
        print(f"\nPattern '{p}' matched at pos {m.start()}: '{m.group()}'")
        print(f"  Before: [{text[:m.start()]}]")
    else:
        print(f"\nPattern '{p}' - NO MATCH")

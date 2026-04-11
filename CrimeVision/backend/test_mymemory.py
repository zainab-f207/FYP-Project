import sys, time
sys.path.insert(0,'.')
from app.approval_workflow import _azure_transliterate_single

tests = [
    'مولانا شوکت علی روڈ',
    'داتا دربار سرکلر روڈ',
    'ڈی ایچ اے فیز 6 بلاک J',
    'بحریہ ٹاؤن سیکٹر G',
    'شاہ عالمی مارکیٹ شاہ عالمی روڈ',
    'گلبرگ لاہور',
    'لبرٹی مارکیٹ ایم ایم عالم روڈ',
    'مین بلیوارڈ گلبرگ',
]
for t in tests:
    r = _azure_transliterate_single(t)
    print(f'{t[:35]:38} -> {r}')
    time.sleep(0.4)
print('\nDone.')

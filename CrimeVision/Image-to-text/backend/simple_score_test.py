"""Simple test to verify the scoring logic without importing heavy OCR modules."""

from collections import Counter

# Simulated candidates from OCR (based on previous test outputs)
candidates = [
    {'text': 'سس', 'conf': 0.4, 'urdu_ratio': 1.0, 'source': 'upscaled'},
    {'text': 'لہ', 'conf': 0.5, 'urdu_ratio': 1.0, 'source': 'denoised'},
    {'text': 'وہ', 'conf': 0.6, 'urdu_ratio': 1.0, 'source': 'binary'},
    {'text': 'بیرق', 'conf': 0.3, 'urdu_ratio': 1.0, 'source': 'bilateral'},
    {'text': 'ارالاکن', 'conf': 0.23, 'urdu_ratio': 1.0, 'source': 'upscaled'},
    {'text': 'حد : ارال اکن', 'conf': 0.22, 'urdu_ratio': 0.8, 'source': 'denoised'},
    {'text': 'سس', 'conf': 0.35, 'urdu_ratio': 1.0, 'source': 'binary'},
    {'text': 'لہ', 'conf': 0.45, 'urdu_ratio': 1.0, 'source': 'bilateral'},
    {'text': 'لہ', 'conf': 0.5, 'urdu_ratio': 1.0, 'source': 'tesseract_upscaled'},
    {'text': 'لہ', 'conf': 0.4, 'urdu_ratio': 1.0, 'source': 'tesseract_binary'},
]

def normalize_text(text):
    """Keep only Urdu letters (remove diacritics and punctuation)"""
    return ''.join(c for c in text if '\u0621' <= c <= '\u064A' or '\u0679' <= c <= '\u06D5')

# Build consensus
text_counts = Counter()
for c in candidates:
    normalized = normalize_text(c['text'])
    if len(normalized) >= 2:
        text_counts[normalized] += 1

print("=== Consensus Counts ===")
for text, count in text_counts.most_common():
    print(f"  '{text}' appears {count} time(s)")

def score_candidate(c):
    """New scoring function with stronger length preferences"""
    score = 0
    text_len = len(c['text'])
    normalized = normalize_text(c['text'])
    normalized_len = len(normalized)
    
    # STRONG length preference - thana names are typically 3-12 characters
    if 4 <= normalized_len <= 10:
        score += 5  # Ideal length
    elif 3 <= normalized_len <= 12:
        score += 3  # Good length
    elif normalized_len >= 2:
        score += 1  # Acceptable
    else:
        score -= 2  # Too short
    
    # Penalize very short texts heavily (2 char words are usually noise)
    if normalized_len <= 2:
        score -= 3
    
    # Consensus bonus (but less weight than length)
    consensus_count = text_counts.get(normalized, 0)
    score += consensus_count * 2
    
    # Prefer high Urdu ratio
    score += c['urdu_ratio'] * 2
    
    # Use confidence
    score += c['conf'] * 1.5
    
    # Penalize texts that look like noise (numbers, punctuation)
    noise_chars = sum(1 for ch in c['text'] if ch in '0123456789.:;,/\\|<>()[]{}٠١٢٣٤٥٦٧٨٩')
    score -= noise_chars * 0.5
    
    return score

print("\n=== Scoring Results ===")
print(f"{'Text':<20} {'Len':<5} {'NormLen':<8} {'Conf':<6} {'Consensus':<10} {'Score':<8}")
print("-" * 65)

for c in sorted(candidates, key=score_candidate, reverse=True):
    normalized = normalize_text(c['text'])
    consensus = text_counts.get(normalized, 0)
    sc = score_candidate(c)
    print(f"{c['text']:<20} {len(c['text']):<5} {len(normalized):<8} {c['conf']:<6.2f} {consensus:<10} {sc:<8.2f}")

# Show best
best = max(candidates, key=score_candidate)
print(f"\n=== SELECTED: '{best['text']}' ===")

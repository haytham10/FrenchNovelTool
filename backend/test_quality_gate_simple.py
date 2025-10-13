#!/usr/bin/env python3
"""
Simple Quality Gate validation test - bypasses Flask application context.
Tests the core logic of quality gate validation to understand why sentences are rejected.
"""

import sys
import os

# Add the backend app to the path so we can import services
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))

try:
    from services.quality_gate import QualityGate
except ImportError as e:
    print(f"Import error: {e}")
    print("Note: spaCy model may not be available in this environment")
    # Create a minimal test version
    class TestQualityGate:
        def __init__(self, min_words=4, max_words=8):
            self.min_words = min_words
            self.max_words = max_words
        
        def token_count(self, sentence):
            return len([t for t in sentence.split() if t.strip()])
        
        def has_verb(self, sentence):
            # Simple fallback verb check
            naive_verbs = {"être", "avoir", "faire", "aller", "venir", "dire", "voir", "prendre", "est", "sont", "était", "étaient", "a", "ai", "as", "ont"}
            tokens = [t.strip(".,;:!?()\"'«»") for t in sentence.lower().split()]
            return any(tok in naive_verbs for tok in tokens)
        
        def is_fragment(self, sentence):
            if not sentence or not sentence.strip():
                return True
            
            sentence = sentence.strip()
            
            # Basic capitalization check
            if not sentence[0].isupper():
                return True
            
            # Basic punctuation check
            if not sentence[-1] in '.!?…»"\'':
                return True
            
            return False
        
        def validate_sentence(self, sentence):
            reasons = []
            
            if not isinstance(sentence, str) or not sentence.strip():
                return {'valid': False, 'sentence': sentence, 'reasons': ['Empty sentence']}
            
            sentence = sentence.strip()
            
            # Check verb presence
            if not self.has_verb(sentence):
                reasons.append('No verb found')
            
            # Check length
            tc = self.token_count(sentence)
            if tc < self.min_words:
                reasons.append(f'Too short ({tc} words, min {self.min_words})')
            elif tc > self.max_words:
                reasons.append(f'Too long ({tc} words, max {self.max_words})')
            
            # Check fragment
            if self.is_fragment(sentence):
                reasons.append('Likely fragment (incomplete structure)')
            
            return {
                'valid': len(reasons) == 0,
                'sentence': sentence,
                'reasons': reasons
            }
    
    QualityGate = TestQualityGate
    print("Using fallback Quality Gate implementation")

# Test sentences from the Google Sheets output
test_sentences = [
    "Savez-vous ce que vous allez faire ?",
    "Logiquement, vous devriez être heureux.",
    "On peut être sensible sans fragilité.",
    "Vous devez la prendre au sérieux.",
    "Avoir un enfant ?",
    "Vous voulez la prendre dans vos bras.",
    "Il voulait être responsable.",
    "Son pouvoir de séduction était grand.",
    "Il devait être impeccable.",
    "C'était un être hybride.",
    "Il voulait faire demi-tour.",
    "Voulait-il savoir vraiment ?"
]

# Additional test sentences that might get rejected
potential_rejects = [
    "Dans la rue sombre.",  # Fragment - no verb
    "Avec le succès et l'argent.",  # Fragment - no verb
    "Pour perdre dix kilos vite.",  # Fragment - no conjugated verb
    "Après cela, plus rien.",  # Fragment - no verb
    "Si tu restes avec elle,",  # Fragment - incomplete conditional
    "Mais pas certain.",  # Fragment - incomplete
    "Il marchait lentement dans la rue en regardant les vitrines des magasins.",  # Too long
    "Bonjour.",  # Too short
    "Il mange une pomme rouge délicieuse.",  # Just over limit (6 words)
    "Il mange une pomme rouge très délicieuse maintenant.",  # Way over limit (8+ words)
]

print("=== QUALITY GATE VALIDATION TEST ===\n")

# Test with default 4-8 word limit
qg = QualityGate(min_words=4, max_words=8)

print("ACCEPTED SENTENCES (from Google Sheets):")
accepted_count = 0
for sentence in test_sentences:
    result = qg.validate_sentence(sentence)
    if result['valid']:
        accepted_count += 1
        print(f"✅ {sentence}")
    else:
        print(f"❌ {sentence} -> {', '.join(result['reasons'])}")

print(f"\nACCEPTED: {accepted_count}/{len(test_sentences)} ({accepted_count/len(test_sentences)*100:.1f}%)")

print("\nTEST REJECTION CASES:")
rejected_count = 0
for sentence in potential_rejects:
    result = qg.validate_sentence(sentence)
    if not result['valid']:
        rejected_count += 1
        print(f"❌ {sentence} -> {', '.join(result['reasons'])}")
    else:
        print(f"✅ {sentence} (unexpectedly accepted)")

print(f"\nREJECTED: {rejected_count}/{len(potential_rejects)} ({rejected_count/len(potential_rejects)*100:.1f}%)")

# Test reason distribution
print("\nREASON DISTRIBUTION ANALYSIS:")
all_test_sentences = test_sentences + potential_rejects
reason_counts = {}

for sentence in all_test_sentences:
    result = qg.validate_sentence(sentence)
    if not result['valid']:
        for reason in result['reasons']:
            reason_counts[reason] = reason_counts.get(reason, 0) + 1

if reason_counts:
    print("Top rejection reasons:")
    for reason, count in sorted(reason_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"  {reason}: {count}")
else:
    print("No rejections found")

print("\n=== END TEST ===")
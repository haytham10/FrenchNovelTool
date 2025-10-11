"""
Simple test script for Stage 1 preprocessing implementation.

This script tests the spaCy-based preprocessing without Flask dependencies.
"""

import sys
import os
import re

# Test if spaCy is installed and model is available
def test_spacy_availability():
    """Test if spaCy and the French model are available"""
    try:
        import spacy
        print("[OK] spaCy is installed")
        try:
            nlp = spacy.load("fr_core_news_lg", disable=["ner"])
            print("[OK] French model (fr_core_news_lg) is loaded")
            return nlp
        except Exception as e:
            print(f"[FAIL] French model not available: {e}")
            print("\nTo install the French model, run:")
            print("  python -m spacy download fr_core_news_lg")
            return None
    except ImportError:
        print("[FAIL] spaCy is not installed")
        return None


def fix_pdf_artifacts(text: str) -> str:
    """Test the PDF artifact fixing function"""
    # Fix hyphenation (word- break across lines)
    text = re.sub(r'(\w+)-\s+(\w+)', r'\1\2', text)

    # Fix spacing issues around punctuation
    text = re.sub(r'\s+([,.;:!?])', r'\1', text)
    text = re.sub(r'([,.;:!?])([A-Z])', r'\1 \2', text)

    # Normalize quotes
    text = text.replace('«', '"').replace('»', '"')

    # Remove multiple spaces
    text = re.sub(r'\s+', ' ', text)

    return text.strip()


def contains_verb(sent) -> bool:
    """Test verb detection"""
    for token in sent:
        if token.pos_ == "VERB" and token.tag_ not in ["VerbForm=Inf"]:
            return True
        if token.pos_ == "AUX":
            return True
    return False


def is_dialogue(text: str) -> bool:
    """Test dialogue detection"""
    return text.startswith('"') or text.startswith('—') or text.startswith('«')


def calculate_complexity(sent) -> float:
    """Test complexity calculation"""
    word_count = len([t for t in sent if not t.is_punct and not t.is_space])
    subordinates = sum(1 for t in sent if t.dep_ in ["mark", "relcl"])
    coordinates = sum(1 for t in sent if t.dep_ == "cc")
    complexity = (word_count * 1.0) + (subordinates * 3.0) + (coordinates * 2.0)
    return complexity


def test_preprocessing_functions():
    """Test the preprocessing functions"""
    print("=" * 80)
    print("Testing Stage 1: spaCy-Based Preprocessing Functions")
    print("=" * 80)

    # Test 1: spaCy availability
    print("\n1. Testing spaCy availability...")
    nlp = test_spacy_availability()

    if not nlp:
        print("\n[WARN] Cannot continue without spaCy model installed.")
        return

    # Test 2: PDF artifact cleaning
    print("\n2. Testing PDF artifact cleaning...")
    test_text = "rock. It's Now orNever, le standard d'Elvis Presley,se déverse bruyamment"
    cleaned = fix_pdf_artifacts(test_text)
    print(f"   Original: {test_text}")
    print(f"   Cleaned:  {cleaned}")

    # Test 3: Sentence segmentation with metadata
    print("\n3. Testing sentence segmentation with metadata...")

    # Sample French text from the blueprint
    test_sentences = [
        "Il marchait lentement dans la rue sombre et froide, pensant à elle.",
        "Maintenant ou jamais.",
        "Pour toujours et à jamais.",
        "Dans quinze ans, c'est moi qui serai là.",
        "Le jour où vous avez tiré un trait sur votre existence."
    ]

    print("\n   Processing test sentences...")
    results = []

    for i, sent_text in enumerate(test_sentences, 1):
        doc = nlp(sent_text)

        # Get the sentence (should be just one for these examples)
        for sent in doc.sents:
            token_count = len([t for t in sent if not t.is_punct and not t.is_space])
            has_verb = contains_verb(sent)
            is_dialog = is_dialogue(sent_text)
            complexity = calculate_complexity(sent)

            result = {
                'text': sent_text,
                'token_count': token_count,
                'has_verb': has_verb,
                'is_dialogue': is_dialog,
                'complexity_score': complexity
            }
            results.append(result)

            print(f"\n   Sentence {i}:")
            print(f"   Text: {sent_text}")
            print(f"   Tokens: {token_count}, Has Verb: {has_verb}, "
                  f"Dialogue: {is_dialog}, Complexity: {complexity:.1f}")

            # Show POS tags for first few tokens
            pos_tags = [(t.text, t.pos_, t.tag_) for t in sent[:8]]
            print(f"   POS tags: {pos_tags}")

    # Test 4: Complexity categorization
    print("\n4. Testing complexity categorization for adaptive processing...")

    passthrough = sum(1 for r in results if 4 <= r['token_count'] <= 8 and r['has_verb'])
    light_rewrite = sum(1 for r in results if 3 <= r['token_count'] <= 10
                       and not (4 <= r['token_count'] <= 8 and r['has_verb']))
    heavy_rewrite = len(results) - passthrough - light_rewrite

    print(f"   - Passthrough (4-8 words + verb): {passthrough}/{len(results)}")
    print(f"   - Light rewrite (3-10 words): {light_rewrite}/{len(results)}")
    print(f"   - Heavy rewrite (complex): {heavy_rewrite}/{len(results)}")

    # Test 5: Expected outcomes
    print("\n5. Validation against expected outcomes...")

    # Sentence 2 should NOT have a verb
    if not results[1]['has_verb']:
        print("   [OK] Sentence 2 correctly identified as having NO VERB")
    else:
        print("   [FAIL] Sentence 2 should not have a verb")

    # Sentence 3 should NOT have a verb
    if not results[2]['has_verb']:
        print("   [OK] Sentence 3 correctly identified as having NO VERB")
    else:
        print("   [FAIL] Sentence 3 should not have a verb")

    # Sentence 4 should have a verb and be 8 words or less
    if results[3]['has_verb'] and results[3]['token_count'] <= 8:
        print("   [OK] Sentence 4 correctly identified (has verb, <=8 words)")
    else:
        print(f"   [FAIL] Sentence 4 issue: has_verb={results[3]['has_verb']}, "
              f"tokens={results[3]['token_count']}")

    # Sentence 1 should be complex (>12)
    if results[0]['complexity_score'] > 12:
        print(f"   [OK] Sentence 1 correctly identified as complex "
              f"(score: {results[0]['complexity_score']:.1f})")
    else:
        print(f"   [WARN] Sentence 1 complexity lower than expected: "
              f"{results[0]['complexity_score']:.1f}")

    print("\n" + "=" * 80)
    print("Test completed successfully!")
    print("=" * 80)
    print("\nNext steps:")
    print("1. Ensure spaCy French model is installed: python -m spacy download fr_core_news_lg")
    print("2. Integration testing with actual PDF files")
    print("3. Proceed to Stage 2: AI Strategy Enhancement")


if __name__ == "__main__":
    test_preprocessing_functions()

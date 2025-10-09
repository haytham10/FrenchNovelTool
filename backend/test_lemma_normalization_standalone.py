"""
Standalone test for French lemma normalization (no Flask dependencies required)
This tests the core normalize_french_lemma function directly.
"""

import sys
import os

# Add the app directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ''))


def normalize_french_lemma(lemma: str) -> str:
    """
    Enhanced French lemma normalization for better word matching.
    (Copy of the function from linguistics.py for standalone testing)
    """
    if not lemma:
        return ""

    # Trim and lowercase
    lemma = lemma.strip().lower()

    # Handle reflexive pronouns FIRST
    if lemma.startswith("se_"):
        lemma = lemma[3:]  # Remove "se_"
    elif lemma.startswith("s'"):
        lemma = lemma[2:]  # Remove "s'"

    # Handle elisions: expand common contractions
    # Note: We do this AFTER reflexive pronoun handling
    elision_expansions = {
        "l'": "le",
        "d'": "de",
        "j'": "je",
        "qu'": "que",
        "n'": "ne",
        "t'": "te",
        "c'": "ce",
        "m'": "me",
    }

    for contraction, expansion in elision_expansions.items():
        if lemma.startswith(contraction):
            # Replace the contraction with the full form
            lemma = expansion + lemma[len(contraction):]
            break

    # Remove any remaining apostrophes
    lemma = lemma.replace("'", "")

    # Normalize whitespace
    lemma = " ".join(lemma.split())

    return lemma


def test_elision_expansions():
    """Test that common French elisions are expanded correctly"""
    print("Testing elision expansions...")
    
    tests = {
        "l'homme": "lehomme",
        "l'ami": "leami",
        "d'abord": "deabord",
        "d'accord": "deaccord",
        "j'ai": "jeai",
        "j'aime": "jeaime",
        "qu'il": "queil",
        "qu'elle": "queelle",
        "n'est": "neest",  # n' → ne, then remove apostrophe
        "t'aime": "teaime",
        "c'est": "ceest",  # c' → ce, then remove apostrophe
        "m'aider": "meaider",
    }
    
    failed = 0
    for input_word, expected in tests.items():
        result = normalize_french_lemma(input_word)
        if result == expected:
            print(f"  ✓ {input_word} → {result}")
        else:
            print(f"  ✗ {input_word} → {result} (expected: {expected})")
            failed += 1
    
    return failed


def test_reflexive_pronouns():
    """Test that reflexive pronouns are handled"""
    print("\nTesting reflexive pronouns...")
    
    tests = {
        "se_laver": "laver",
        "se_lever": "lever",
        "se_appeler": "appeler",
        "s'appeler": "appeler",
        "s'habiller": "habiller",
    }
    
    failed = 0
    for input_word, expected in tests.items():
        result = normalize_french_lemma(input_word)
        if result == expected:
            print(f"  ✓ {input_word} → {result}")
        else:
            print(f"  ✗ {input_word} → {result} (expected: {expected})")
            failed += 1
    
    return failed


def test_case_normalization():
    """Test that case is normalized"""
    print("\nTesting case normalization...")
    
    tests = {
        "BONJOUR": "bonjour",
        "Maison": "maison",
        "L'HOMME": "lehomme",
        "Se_Laver": "laver",
    }
    
    failed = 0
    for input_word, expected in tests.items():
        result = normalize_french_lemma(input_word)
        if result == expected:
            print(f"  ✓ {input_word} → {result}")
        else:
            print(f"  ✗ {input_word} → {result} (expected: {expected})")
            failed += 1
    
    return failed


def test_whitespace_normalization():
    """Test that whitespace is normalized"""
    print("\nTesting whitespace normalization...")
    
    tests = {
        "  chat  ": "chat",
        "un  chat": "un chat",
        "chat   noir  ": "chat noir",
    }
    
    failed = 0
    for input_word, expected in tests.items():
        result = normalize_french_lemma(input_word)
        if result == expected:
            print(f"  ✓ '{input_word}' → '{result}'")
        else:
            print(f"  ✗ '{input_word}' → '{result}' (expected: '{expected}')")
            failed += 1
    
    return failed


def test_edge_cases():
    """Test edge cases"""
    print("\nTesting edge cases...")
    
    tests = {
        "": "",
        "   ": "",
        "aujourd'hui": "aujourdhui",
        "chat": "chat",
        "maison": "maison",
    }
    
    failed = 0
    for input_word, expected in tests.items():
        result = normalize_french_lemma(input_word)
        if result == expected:
            print(f"  ✓ '{input_word}' → '{result}'")
        else:
            print(f"  ✗ '{input_word}' → '{result}' (expected: '{expected}')")
            failed += 1
    
    return failed


if __name__ == "__main__":
    print("=" * 70)
    print("French Lemma Normalization Standalone Tests")
    print("=" * 70)
    
    total_failed = 0
    total_failed += test_elision_expansions()
    total_failed += test_reflexive_pronouns()
    total_failed += test_case_normalization()
    total_failed += test_whitespace_normalization()
    total_failed += test_edge_cases()
    
    print("\n" + "=" * 70)
    if total_failed == 0:
        print("✓ All tests passed!")
    else:
        print(f"✗ {total_failed} test(s) failed")
    print("=" * 70)
    
    sys.exit(0 if total_failed == 0 else 1)

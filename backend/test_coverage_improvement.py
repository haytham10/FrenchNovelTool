"""
Demonstration script showing coverage improvement with French lemma normalization.

This script simulates the matching process between a word list and sentences
to show how the French-specific normalization improves coverage.
"""

import sys
import os

# Add the app directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ''))


def normalize_french_lemma(lemma: str) -> str:
    """Enhanced French lemma normalization (copy from linguistics.py)"""
    if not lemma:
        return ""
    
    lemma = lemma.strip().lower()
    
    # Handle reflexive pronouns FIRST
    if lemma.startswith("se_"):
        lemma = lemma[3:]
    elif lemma.startswith("s'"):
        lemma = lemma[2:]
    
    # Handle elisions
    elision_expansions = {
        "l'": "le", "d'": "de", "j'": "je", "qu'": "que",
        "n'": "ne", "t'": "te", "c'": "ce", "m'": "me",
    }
    
    for contraction, expansion in elision_expansions.items():
        if lemma.startswith(contraction):
            lemma = expansion + lemma[len(contraction):]
            break
    
    lemma = lemma.replace("'", "")
    lemma = " ".join(lemma.split())
    
    return lemma


def normalize_text(text: str, fold_diacritics: bool = True) -> str:
    """General text normalization (simplified version)"""
    import unicodedata
    import re
    
    if not text:
        return ""
    
    text = text.strip().casefold()
    text = re.sub(r'[\u200b-\u200f\ufeff]', '', text)
    
    if fold_diacritics:
        text = ''.join(
            c for c in unicodedata.normalize('NFD', text)
            if unicodedata.category(c) != 'Mn'
        )
    
    text = text.replace("'", "")
    return text


def normalize_word_OLD(word: str) -> str:
    """Word list normalization - extracts lexical head from elisions"""
    import re
    import unicodedata
    
    if not word:
        return ""
    
    word = word.strip()
    
    # Extract the part after elision (e.g., "l'homme" → "homme")
    elision_pattern = r"^(?:l'|d'|j'|n'|s'|t'|c'|qu')\s*(.+)$"
    match = re.match(elision_pattern, word, re.IGNORECASE)
    if match:
        word = match.group(1)
    else:
        word = word.replace("'", "")
    
    word = word.casefold()
    
    # Fold diacritics
    word = ''.join(
        c for c in unicodedata.normalize('NFD', word)
        if unicodedata.category(c) != 'Mn'
    )
    
    return word.strip()


def test_coverage_improvement():
    """
    Test coverage improvement by comparing OLD vs NEW normalization.
    
    The KEY IMPROVEMENT is handling reflexive pronouns in lemma normalization.
    Word list normalization stays the same (extracts head words from elisions).
    """
    
    print("=" * 80)
    print("Coverage Improvement Demonstration")
    print("=" * 80)
    print()
    print("Key Improvement: French lemma normalization now handles reflexive pronouns!")
    print("This allows base verb forms in word lists to match reflexive lemmas from spaCy")
    print()
    
    # Sample word list (base vocabulary forms)
    word_list_raw = [
        "ami",         # friend
        "accord",      # agreement  
        "être",        # to be
        "laver",       # to wash (BASE FORM, not "se laver")
        "appeler",     # to call (BASE FORM, not "s'appeler")
        "aujourd'hui", # today
        "avoir",       # to have
    ]
    
    # Sample lemmas (as spaCy lemmatizes them, INCLUDING reflexive forms)
    sentence_lemmas = [
        "ami",         # from "l'ami"
        "accord",      # from "d'accord"
        "etre",        # from "être"
        "se_laver",    # REFLEXIVE: spaCy lemmatizes "il se lave" to "se_laver"
        "se_appeler",  # REFLEXIVE: spaCy lemmatizes "il s'appelle" to "se_appeler"
        "aujourdhui",  # from "aujourd'hui"
        "avoir",       # from "avoir"
    ]
    
    print("Word List (base vocabulary forms):")
    for word in word_list_raw:
        print(f"  • {word}")
    print()
    
    print("Sentence Lemmas (from spaCy, including reflexive forms):")
    for lemma in sentence_lemmas:
        print(f"  • {lemma}")
    print()
    
    # OLD approach: lemmas don't handle reflexive pronouns
    print("=" * 80)
    print("OLD APPROACH (Before Fix - no reflexive handling in lemmas)")
    print("=" * 80)
    wordlist_normalized_OLD = {normalize_word_OLD(w): w for w in word_list_raw}
    # OLD: No reflexive handling in lemmas
    lemmas_normalized_OLD = {normalize_text(l, True): l for l in sentence_lemmas}
    
    print("\nNormalized Word List:")
    for norm, orig in sorted(wordlist_normalized_OLD.items()):
        print(f"  '{orig}' → '{norm}'")
    
    print("\nNormalized Lemmas (OLD - no reflexive handling):")
    for norm, orig in sorted(lemmas_normalized_OLD.items()):
        print(f"  '{orig}' → '{norm}'")
    
    matches_OLD = set(wordlist_normalized_OLD.keys()) & set(lemmas_normalized_OLD.keys())
    coverage_OLD = len(matches_OLD) / len(wordlist_normalized_OLD) * 100
    
    print(f"\nMatches: {len(matches_OLD)}/{len(wordlist_normalized_OLD)}")
    print(f"Coverage: {coverage_OLD:.1f}%")
    for match in sorted(matches_OLD):
        print(f"  ✓ '{match}'")
    
    print("\nMissed words (reflexive verbs don't match):")
    missed_OLD = set(wordlist_normalized_OLD.keys()) - matches_OLD
    for norm in sorted(missed_OLD):
        print(f"  ✗ '{wordlist_normalized_OLD[norm]}' (normalized: '{norm}')")
    
    # NEW approach: lemmas now handle reflexive pronouns
    print()
    print("=" * 80)
    print("NEW APPROACH (After Fix - with reflexive pronoun handling in lemmas)")
    print("=" * 80)
    wordlist_normalized_NEW = {normalize_word_OLD(w): w for w in word_list_raw}  # Same as OLD
    # NEW: Reflexive handling in lemmas via normalize_french_lemma
    lemmas_normalized_NEW = {
        normalize_text(normalize_french_lemma(l), True): l 
        for l in sentence_lemmas
    }
    
    print("\nNormalized Word List (unchanged):")
    for norm, orig in sorted(wordlist_normalized_NEW.items()):
        print(f"  '{orig}' → '{norm}'")
    
    print("\nNormalized Lemmas (NEW - with reflexive handling):")
    for norm, orig in sorted(lemmas_normalized_NEW.items()):
        marker = "⭐" if orig.startswith("se_") or orig.startswith("s'") else "  "
        print(f"{marker} '{orig}' → '{norm}'")
    
    matches_NEW = set(wordlist_normalized_NEW.keys()) & set(lemmas_normalized_NEW.keys())
    coverage_NEW = len(matches_NEW) / len(wordlist_normalized_NEW) * 100
    
    print(f"\nMatches: {len(matches_NEW)}/{len(wordlist_normalized_NEW)}")
    print(f"Coverage: {coverage_NEW:.1f}%")
    for match in sorted(matches_NEW):
        print(f"  ✓ '{match}'")
    
    print("\nMissed words:")
    missed_NEW = set(wordlist_normalized_NEW.keys()) - matches_NEW
    if missed_NEW:
        for norm in sorted(missed_NEW):
            print(f"  ✗ '{wordlist_normalized_NEW[norm]}' (normalized: '{norm}')")
    else:
        print("  None! All words matched.")
    
    # Summary
    print()
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"OLD Coverage: {coverage_OLD:.1f}% ({len(matches_OLD)}/{len(wordlist_normalized_OLD)} words)")
    print(f"NEW Coverage: {coverage_NEW:.1f}% ({len(matches_NEW)}/{len(wordlist_normalized_NEW)} words)")
    improvement = coverage_NEW - coverage_OLD
    print(f"Improvement: +{improvement:.1f} percentage points")
    print()
    
    # Highlight the key improvement
    new_matches = matches_NEW - matches_OLD
    if new_matches:
        print("⭐ NEW MATCHES (thanks to reflexive pronoun handling):")
        for match in sorted(new_matches):
            orig_word = wordlist_normalized_NEW[match]
            orig_lemma = lemmas_normalized_NEW[match]
            print(f"  ✓ '{orig_word}' now matches '{orig_lemma}'")
        print()
    
    if improvement > 0:
        print("✅ SUCCESS! The French lemma normalization improves coverage!")
        print()
        print("What changed:")
        print("  • normalize_french_lemma() now strips reflexive pronouns (se_, s')")
        print("  • Applied in tokenize_and_lemmatize() before matching")
        print("  • Reflexive verbs (se_laver, se_appeler) now match base forms (laver, appeler)")
        print()
        print("Result:")
        print(f"  • {len(new_matches)} additional words matched")
        print(f"  • Coverage improved by {improvement:.1f} percentage points")
    
    print("=" * 80)


if __name__ == "__main__":
    test_coverage_improvement()

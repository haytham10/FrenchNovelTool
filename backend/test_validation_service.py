"""
Test script for validation_service.py

This script tests the SentenceValidator with various test cases
to verify the validation logic works correctly.
"""

import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.validation_service import SentenceValidator


def test_validation_service():
    """Test the validation service with various sentence types"""

    print("=" * 70)
    print("VALIDATION SERVICE TEST")
    print("=" * 70)
    print()

    # Initialize validator
    print("Initializing SentenceValidator...")
    validator = SentenceValidator()
    print("✓ Validator initialized successfully")
    print()

    # Define test cases
    test_cases = [
        # (sentence, expected_valid, description)

        # VALID SENTENCES (4-8 words, has verb, complete)
        ("Elle marche dans la rue.", True, "Valid: 5 words, has verb 'marche'"),
        ("Il est très content aujourd'hui.", True, "Valid: 5 words, has AUX 'est'"),
        ("Le chat dort sur le canapé.", True, "Valid: 6 words, has verb 'dort'"),
        ("Nous partons demain matin tôt.", True, "Valid: 5 words, has verb 'partons'"),
        ("Je pense à elle souvent.", True, "Valid: 5 words, has verb 'pense'"),
        ("Dans quinze ans, je serai là.", True, "Valid: 6 words, has verb 'serai'"),

        # INVALID: TOO SHORT (<4 words)
        ("Elle va.", False, "Invalid: 2 words (too short)"),
        ("Il marche vite.", False, "Invalid: 3 words (too short)"),
        ("Le chat.", False, "Invalid: 2 words (too short)"),

        # INVALID: TOO LONG (>8 words)
        ("Elle va au marché pour acheter des fruits frais.", False, "Invalid: 9 words (too long)"),
        ("Le chat noir dort paisiblement sur le canapé confortable du salon.", False, "Invalid: 11 words (too long)"),

        # INVALID: NO VERB
        ("Pour toujours et à jamais.", False, "Invalid: 5 words, NO VERB (prepositional phrase)"),
        ("Dans la rue sombre et froide.", False, "Invalid: 6 words, NO VERB (prepositional phrase)"),
        ("Avec le temps qui passe.", False, "Invalid: 5 words, NO VERB (prepositional phrase)"),
        ("Le grand chat noir.", False, "Invalid: 4 words, NO VERB (noun phrase)"),

        # INVALID: FRAGMENTS (has words + verb but incomplete)
        ("qui était très content", False, "Invalid: Fragment (relative pronoun start)"),
        ("que nous aimons beaucoup", False, "Invalid: Fragment (relative pronoun start)"),
        ("quand il arrive demain", False, "Invalid: Fragment (subordinate without main)"),
        ("dans la rue sombre", False, "Invalid: Fragment (prepositional phrase without verb in first half)"),

        # EDGE CASES
        ("", False, "Invalid: Empty string"),
        ("   ", False, "Invalid: Whitespace only"),
        ("Marcher lentement dans le parc.", False, "Invalid: Infinitive verb, not conjugated"),
    ]

    # Run validation on all test cases
    print("TESTING INDIVIDUAL SENTENCES:")
    print("-" * 70)

    passed_tests = 0
    failed_tests = 0

    for sentence, expected_valid, description in test_cases:
        is_valid, failure_reason = validator.validate_single(sentence)

        # Check if result matches expectation
        test_passed = (is_valid == expected_valid)

        if test_passed:
            status = "✓ PASS"
            passed_tests += 1
        else:
            status = "✗ FAIL"
            failed_tests += 1

        # Print result
        print(f"{status} | {description}")
        print(f"     Sentence: \"{sentence}\"")
        print(f"     Expected: {'VALID' if expected_valid else 'INVALID'}, Got: {'VALID' if is_valid else f'INVALID ({failure_reason})'}")
        print()

    print("-" * 70)
    print(f"Individual tests: {passed_tests} passed, {failed_tests} failed")
    print()

    # Test batch validation
    print("TESTING BATCH VALIDATION:")
    print("-" * 70)

    # Reset stats for clean batch test
    validator.reset_stats()

    batch_sentences = [
        "Elle marche dans la rue.",  # Valid
        "Pour toujours.",  # Invalid: no verb, too short
        "Le chat dort bien aujourd'hui.",  # Valid
        "qui était content",  # Invalid: fragment
        "Il est très heureux maintenant.",  # Valid
        "Dans la rue sombre",  # Invalid: no verb in first half
        "Nous partons demain matin tôt.",  # Valid
        "Elle va au marché pour acheter des fruits frais maintenant.",  # Invalid: too long
    ]

    valid_sentences, report = validator.validate_batch(batch_sentences, discard_failures=True)

    print(f"Batch size: {report['total']}")
    print(f"Valid sentences: {report['valid']}")
    print(f"Invalid sentences: {report['invalid']}")
    print(f"Pass rate: {report['pass_rate']:.1f}%")
    print()

    print("Valid sentences kept:")
    for i, sentence in enumerate(valid_sentences, 1):
        print(f"  {i}. {sentence}")
    print()

    print("Sample failures:")
    for failure in report['failures'][:5]:
        print(f"  - \"{failure['sentence']}\" (reason: {failure['reason']})")
    print()

    # Get statistics summary
    stats = validator.get_stats_summary()
    print("Validation Statistics:")
    for key, value in stats.items():
        print(f"  {key}: {value}")
    print()

    print("=" * 70)
    print("TEST COMPLETE")
    print("=" * 70)

    # Return overall success
    return failed_tests == 0


if __name__ == "__main__":
    try:
        success = test_validation_service()
        if success:
            print("\n✓ All tests passed!")
            sys.exit(0)
        else:
            print("\n✗ Some tests failed")
            sys.exit(1)
    except Exception as e:
        print(f"\n✗ Test script failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

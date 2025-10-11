"""
Standalone test for validation_service.py

This script tests the SentenceValidator directly without Flask dependencies.
"""

import spacy
from typing import List, Dict, Tuple


class SentenceValidator:
    """
    Validates normalized sentences using spaCy POS tagging.

    Stan's Requirements:
    1. Length: 4-8 words (content words only)
    2. Completeness: Must have a conjugated verb
    3. Grammar: Must be a complete, independent sentence
    """

    def __init__(self):
        """Initialize the validator with French spaCy model."""
        # Load French spaCy model (disable NER for speed)
        self.nlp = spacy.load("fr_core_news_lg", disable=["ner"])

        # Validation statistics
        self.stats = {
            'total_processed': 0,
            'passed': 0,
            'failed_length': 0,
            'failed_no_verb': 0,
            'failed_fragment': 0
        }

    def validate_batch(
        self,
        sentences: List[str],
        discard_failures: bool = True
    ) -> Tuple[List[str], Dict]:
        """Validate a batch of sentences."""
        valid_sentences = []
        failures = []

        for sentence in sentences:
            is_valid, failure_reason = self.validate_single(sentence)

            if is_valid:
                valid_sentences.append(sentence)
                self.stats['passed'] += 1
            else:
                failures.append({
                    'sentence': sentence,
                    'reason': failure_reason
                })
                self.stats[f'failed_{failure_reason}'] += 1

                if not discard_failures:
                    valid_sentences.append(sentence)

            self.stats['total_processed'] += 1

        report = {
            'total': len(sentences),
            'valid': len(valid_sentences),
            'invalid': len(failures),
            'pass_rate': len(valid_sentences) / len(sentences) * 100 if sentences else 0,
            'failures': failures[:20],
            'stats': self.stats.copy()
        }

        return valid_sentences, report

    def validate_single(self, sentence: str) -> Tuple[bool, str]:
        """Validate a single sentence against all criteria."""
        if not sentence or not sentence.strip():
            return False, "empty"

        doc = self.nlp(sentence.strip())
        content_tokens = [
            token for token in doc
            if not token.is_punct and not token.is_space
        ]
        word_count = len(content_tokens)

        # CHECK 1: Length validation (4-8 words)
        if word_count < 4 or word_count > 8:
            return False, "length"

        # CHECK 2: Verb requirement
        has_verb = self._has_conjugated_verb(doc)
        if not has_verb:
            return False, "no_verb"

        # CHECK 3: Fragment detection
        is_fragment = self._is_fragment(doc, sentence)
        if is_fragment:
            return False, "fragment"

        return True, None

    def _has_conjugated_verb(self, doc) -> bool:
        """Check if sentence contains a conjugated verb."""
        for token in doc:
            if token.pos_ == "VERB":
                morph_dict = token.morph.to_dict()
                if morph_dict.get("VerbForm") == "Inf":
                    continue
                if morph_dict.get("VerbForm") == "Part" and token.dep_ == "amod":
                    continue
                return True
            if token.pos_ == "AUX":
                return True
        return False

    def _is_fragment(self, doc, sentence: str) -> bool:
        """Detect common fragment patterns."""
        if len(doc) == 0:
            return True

        first_token = doc[0]
        first_word_lower = first_token.text.lower()

        # Relative pronouns starting sentence = fragment
        if first_word_lower in ["qui", "que", "qu'", "dont", "où", "lequel", "laquelle"]:
            return True

        # Subordinating conjunctions without main clause
        subordinating_conjunctions = [
            "quand", "lorsque", "si", "comme", "parce", "puisque",
            "bien que", "quoique", "afin que", "pour que"
        ]
        if first_word_lower in subordinating_conjunctions:
            comma_count = sum(1 for t in doc if t.text == ",")
            if comma_count == 0:
                return True

        # Prepositional phrases at start - check for verb position
        prepositions = ["dans", "sur", "sous", "avec", "sans", "pour", "de", "à", "vers", "chez", "par"]
        if first_word_lower in prepositions:
            midpoint = len(doc) // 2
            has_early_verb = any(
                t.pos_ in ["VERB", "AUX"] for t in doc[:midpoint]
            )
            if not has_early_verb:
                return True

        return False

    def get_stats_summary(self) -> Dict:
        """Get validation statistics summary."""
        return {
            **self.stats,
            'pass_rate': (self.stats['passed'] / self.stats['total_processed'] * 100)
                        if self.stats['total_processed'] > 0 else 0
        }

    def reset_stats(self):
        """Reset statistics counters for new batch."""
        self.stats = {
            'total_processed': 0,
            'passed': 0,
            'failed_length': 0,
            'failed_no_verb': 0,
            'failed_fragment': 0
        }


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

        # EDGE CASES
        ("", False, "Invalid: Empty string"),
        ("   ", False, "Invalid: Whitespace only"),
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
    import sys
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

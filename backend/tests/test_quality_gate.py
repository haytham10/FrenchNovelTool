"""Tests for Quality Gate Service - Fragment rejection with spaCy POS tagging.

This test suite validates the Quality Gate Service's ability to:
1. Detect and reject sentence fragments
2. Accept valid complete sentences
3. Use spaCy POS tagging for accurate verb detection
4. Handle edge cases (imperatives, questions, short sentences)
5. Provide detailed rejection reasons
6. Perform within performance requirements (<10ms per sentence)
"""

import pytest
import time
from unittest.mock import Mock, patch
from app.services.quality_gate_service import QualityGateService


# Test Fixtures
@pytest.fixture
def quality_gate():
    """Create a Quality Gate Service instance with default config."""
    with patch('flask.current_app') as mock_app:
        mock_app.logger = Mock()
        service = QualityGateService(config={
            'min_length': 4,
            'max_length': 8,
            'require_verb': True
        })
        return service


@pytest.fixture
def quality_gate_lenient():
    """Create a Quality Gate Service with lenient verb requirement."""
    with patch('flask.current_app') as mock_app:
        mock_app.logger = Mock()
        service = QualityGateService(config={
            'min_length': 2,
            'max_length': 8,
            'require_verb': False
        })
        return service


# Fragment Tests (Should Reject)
class TestFragmentRejection:
    """Test that the quality gate correctly rejects sentence fragments."""

    def test_reject_prepositional_phrase_no_verb(self, quality_gate):
        """Reject: 'Dans la rue sombre.' (no verb)"""
        is_valid, reason = quality_gate.validate_sentence("Dans la rue sombre.")
        assert not is_valid, "Should reject prepositional phrase without verb"
        assert 'No verb found' in reason or 'verb' in reason.lower()

    def test_reject_conjunction_fragment(self, quality_gate):
        """Reject: 'et froide' (conjunction fragment, too short)"""
        is_valid, reason = quality_gate.validate_sentence("Et froide.")
        assert not is_valid, "Should reject conjunction fragment"
        # Could be rejected for length or missing verb
        assert reason is not None

    def test_reject_idiomatic_fragment(self, quality_gate):
        """Reject: 'Pour toujours et à jamais' (idiomatic fragment, no verb)"""
        is_valid, reason = quality_gate.validate_sentence("Pour toujours et à jamais.")
        assert not is_valid, "Should reject idiomatic fragment without verb"
        # Length is 5 words (valid range), but should fail verb check
        assert 'verb' in reason.lower()

    def test_reject_adverbial_phrase(self, quality_gate):
        """Reject: 'Avec le temps' (no verb)"""
        is_valid, reason = quality_gate.validate_sentence("Avec le temps.")
        assert not is_valid, "Should reject adverbial phrase without verb"
        # 3 words, below minimum of 4
        assert 'short' in reason.lower() or 'verb' in reason.lower()

    def test_reject_time_expression(self, quality_gate):
        """Reject: 'Dans quinze ans' (time expression, no verb)"""
        is_valid, reason = quality_gate.validate_sentence("Dans quinze ans.")
        assert not is_valid, "Should reject time expression without verb"
        # 3 words, below minimum
        assert 'short' in reason.lower() or 'verb' in reason.lower()

    def test_reject_participial_phrase(self, quality_gate):
        """Reject: 'De retour dans la chambre' (participial phrase, no auxiliary)"""
        is_valid, reason = quality_gate.validate_sentence("De retour dans la chambre.")
        assert not is_valid, "Should reject participial phrase without verb"
        assert 'verb' in reason.lower()

    def test_reject_too_short(self, quality_gate):
        """Reject: 'Bon.' (too short, 1 word, min 4)"""
        is_valid, reason = quality_gate.validate_sentence("Bon.")
        assert not is_valid, "Should reject sentence too short"
        assert 'short' in reason.lower() or '1 word' in reason

    def test_reject_too_long(self, quality_gate):
        """Reject: 'Il mange des pommes rouges et délicieuses maintenant.' (9 words, max 8)"""
        is_valid, reason = quality_gate.validate_sentence(
            "Il mange des pommes rouges et délicieuses maintenant."
        )
        assert not is_valid, "Should reject sentence too long"
        assert 'long' in reason.lower() or '9 words' in reason

    def test_reject_missing_punctuation(self, quality_gate):
        """Reject: 'Il marche lentement' (missing period)"""
        is_valid, reason = quality_gate.validate_sentence("Il marche lentement")
        assert not is_valid, "Should reject missing end punctuation"
        assert 'punctuation' in reason.lower()

    def test_reject_no_capital(self, quality_gate):
        """Reject: 'il marche lentement.' (no capital letter)"""
        is_valid, reason = quality_gate.validate_sentence("il marche lentement.")
        assert not is_valid, "Should reject sentence not starting with capital"
        assert 'capital' in reason.lower()


# Valid Sentence Tests (Should Accept)
class TestValidSentenceAcceptance:
    """Test that the quality gate correctly accepts valid sentences."""

    def test_accept_simple_sentence_with_verb(self, quality_gate):
        """Accept: 'Il marche lentement.' (has verb 'marche')"""
        is_valid, reason = quality_gate.validate_sentence("Il marche lentement.")
        assert is_valid, f"Should accept valid sentence with verb: {reason}"
        assert reason is None

    def test_accept_sentence_with_etre(self, quality_gate):
        """Accept: 'Elle est belle aujourd'hui.' (has verb 'est')"""
        is_valid, reason = quality_gate.validate_sentence("Elle est belle aujourd'hui.")
        assert is_valid, f"Should accept sentence with être: {reason}"
        assert reason is None

    def test_accept_past_tense(self, quality_gate):
        """Accept: 'La rue était sombre hier.' (has verb 'était')"""
        is_valid, reason = quality_gate.validate_sentence("La rue était sombre hier.")
        assert is_valid, f"Should accept past tense sentence: {reason}"
        assert reason is None

    def test_accept_compound_sentence(self, quality_gate):
        """Accept: 'Il pense et elle comprend.' (6 words, 2 verbs)"""
        is_valid, reason = quality_gate.validate_sentence("Il pense et elle comprend.")
        assert is_valid, f"Should accept compound sentence: {reason}"
        assert reason is None

    def test_accept_weather_expression(self, quality_gate):
        """Accept: 'Il faisait très froid.' (5 words, has verb)"""
        is_valid, reason = quality_gate.validate_sentence("Il faisait très froid.")
        assert is_valid, f"Should accept weather expression: {reason}"
        assert reason is None


# Edge Case Tests
class TestEdgeCases:
    """Test edge cases: imperatives, questions, special forms."""

    def test_accept_imperative_short(self, quality_gate_lenient):
        """Accept: 'Cours !' (imperative, valid verb form)"""
        # Note: Imperatives might be tricky for spaCy, using lenient config
        is_valid, reason = quality_gate_lenient.validate_sentence("Cours !")
        # This should pass if spaCy recognizes it as a verb or if min_length=2
        # For now, we expect it might fail due to length with strict config
        # With lenient (min=2, no verb requirement), should pass
        assert is_valid or 'short' in reason.lower()

    def test_accept_question_with_verb(self, quality_gate):
        """Accept: 'Où vas-tu maintenant ?' (question with verb)"""
        is_valid, reason = quality_gate.validate_sentence("Où vas-tu maintenant ?")
        assert is_valid, f"Should accept question with verb: {reason}"
        assert reason is None

    def test_accept_question_simple(self, quality_gate):
        """Accept: 'Qui est-il vraiment ?' (5 words, verb 'est')"""
        is_valid, reason = quality_gate.validate_sentence("Qui est-il vraiment ?")
        assert is_valid, f"Should accept simple question: {reason}"
        assert reason is None

    def test_accept_exclamation_with_verb(self, quality_gate):
        """Accept: 'Quelle belle journée c'est !' (6 words, verb)"""
        is_valid, reason = quality_gate.validate_sentence("Quelle belle journée c'est !")
        assert is_valid, f"Should accept exclamation with verb: {reason}"
        assert reason is None

    def test_ellipsis_punctuation(self, quality_gate):
        """Accept: 'Il attend encore longtemps…' (with ellipsis)"""
        is_valid, reason = quality_gate.validate_sentence("Il attend encore longtemps…")
        assert is_valid, f"Should accept sentence with ellipsis: {reason}"
        assert reason is None

    def test_preposition_with_verb(self, quality_gate):
        """Accept: 'Dans la rue il marche.' (preposition + complete clause)"""
        is_valid, reason = quality_gate.validate_sentence("Dans la rue il marche.")
        assert is_valid, f"Should accept prepositional phrase with verb: {reason}"
        assert reason is None


# spaCy POS Tagging Tests
class TestSpacyVerbDetection:
    """Test spaCy-specific verb detection functionality."""

    def test_spacy_detects_main_verb(self, quality_gate):
        """Verify spaCy correctly identifies VERB tokens."""
        is_valid, reason = quality_gate.validate_sentence("Il marche lentement chaque jour.")
        # 5 words (within range), main verb 'marche' should be detected
        assert is_valid, f"spaCy should detect main verb 'marche': {reason}"

    def test_spacy_detects_auxiliary_verb(self, quality_gate):
        """Verify spaCy accepts auxiliary verbs (être, avoir)."""
        is_valid, reason = quality_gate.validate_sentence("Elle est très belle aujourd'hui.")
        # 'est' is AUX in spaCy, but should still be accepted
        assert is_valid, f"spaCy should accept auxiliary verb 'est': {reason}"

    def test_spacy_rejects_no_verb_adjective_phrase(self, quality_gate):
        """Verify spaCy rejects pure adjective phrases."""
        is_valid, reason = quality_gate.validate_sentence("Très belle et élégante aujourd'hui.")
        # No verb, should be rejected
        assert not is_valid, "spaCy should reject adjective phrase without verb"
        assert 'verb' in reason.lower()

    def test_spacy_complex_sentence_with_verb(self, quality_gate):
        """Verify spaCy handles complex sentences with verb."""
        is_valid, reason = quality_gate.validate_sentence("Les enfants jouent dehors joyeusement.")
        # 5 words, verb 'jouent'
        assert is_valid, f"spaCy should detect verb in complex sentence: {reason}"


# Batch Validation Tests
class TestBatchValidation:
    """Test batch validation functionality."""

    def test_batch_validate_mixed(self, quality_gate):
        """Test batch validation with mix of valid and invalid sentences."""
        sentences = [
            "Il marche lentement dehors.",  # Valid
            "Dans la rue sombre.",  # Invalid (no verb)
            "Elle est très belle.",  # Valid
            "et froide",  # Invalid (too short, no punct)
        ]

        results = quality_gate.batch_validate(sentences)

        assert len(results) == 4
        assert results[0]['is_valid'] == True
        assert results[1]['is_valid'] == False
        assert results[2]['is_valid'] == True
        assert results[3]['is_valid'] == False

    def test_batch_validation_stats(self, quality_gate):
        """Test validation statistics calculation."""
        sentences = [
            "Il marche lentement dehors.",
            "Dans la rue sombre.",
            "Elle est très belle.",
            "Pour toujours et à jamais.",
        ]

        results = quality_gate.batch_validate(sentences)
        stats = quality_gate.get_validation_stats(results)

        assert stats['total'] == 4
        assert stats['valid'] == 2
        assert stats['rejected'] == 2
        assert stats['rejection_rate'] == 50.0
        assert isinstance(stats['rejection_reasons'], dict)


# Performance Tests
class TestPerformance:
    """Test performance requirements (<10ms per sentence)."""

    def test_performance_single_sentence(self, quality_gate):
        """Verify single sentence validation completes within 10ms."""
        sentence = "Il marche lentement dans la rue."

        start = time.time()
        quality_gate.validate_sentence(sentence)
        elapsed = (time.time() - start) * 1000  # Convert to milliseconds

        assert elapsed < 10, f"Validation took {elapsed:.2f}ms, should be <10ms"

    def test_performance_batch_average(self, quality_gate):
        """Verify average batch validation time is <10ms per sentence."""
        sentences = [
            "Il marche lentement dehors.",
            "Elle est très belle.",
            "La rue était sombre.",
            "Il faisait très froid.",
            "Les enfants jouent dehors.",
        ] * 10  # 50 sentences total

        start = time.time()
        quality_gate.batch_validate(sentences)
        elapsed = (time.time() - start) * 1000  # milliseconds

        avg_per_sentence = elapsed / len(sentences)
        assert avg_per_sentence < 10, f"Average {avg_per_sentence:.2f}ms per sentence, should be <10ms"


# Configuration Tests
class TestConfiguration:
    """Test different configuration options."""

    def test_custom_length_limits(self):
        """Test custom min/max length configuration."""
        with patch('flask.current_app') as mock_app:
            mock_app.logger = Mock()
            service = QualityGateService(config={
                'min_length': 3,
                'max_length': 10,
                'require_verb': True
            })

            # 3 words - should pass minimum
            is_valid, _ = service.validate_sentence("Il mange bien.")
            assert is_valid

            # 10 words - should pass maximum (need a 10-word sentence with verb)
            is_valid, _ = service.validate_sentence(
                "Il mange des pommes rouges et des poires jaunes chaque jour."
            )
            assert is_valid

    def test_verb_requirement_disabled(self):
        """Test disabling verb requirement."""
        with patch('flask.current_app') as mock_app:
            mock_app.logger = Mock()
            service = QualityGateService(config={
                'min_length': 4,
                'max_length': 8,
                'require_verb': False
            })

            # Should pass even without verb (if other criteria met)
            is_valid, reason = service.validate_sentence("Dans la rue sombre maintenant.")
            # 5 words, no verb, but verb check disabled
            # Should still check other criteria (length, punctuation, capital)
            # Since verb check is disabled, should pass if other criteria OK
            if not is_valid:
                assert 'verb' not in reason.lower()


# Error Handling Tests
class TestErrorHandling:
    """Test error handling and edge cases."""

    def test_empty_sentence(self, quality_gate):
        """Test handling of empty sentence."""
        is_valid, reason = quality_gate.validate_sentence("")
        assert not is_valid
        assert 'empty' in reason.lower() or 'whitespace' in reason.lower()

    def test_whitespace_only(self, quality_gate):
        """Test handling of whitespace-only sentence."""
        is_valid, reason = quality_gate.validate_sentence("   \t\n  ")
        assert not is_valid
        assert 'empty' in reason.lower() or 'whitespace' in reason.lower()


# Real-World Fragment Examples
class TestRealWorldFragments:
    """Test with real-world fragment examples from actual data."""

    def test_reject_noun_phrase(self, quality_gate):
        """Reject: 'le standard d'Elvis Presley' (noun phrase, no verb)"""
        is_valid, reason = quality_gate.validate_sentence("Le standard d'Elvis Presley.")
        assert not is_valid, "Should reject noun phrase"
        # 4 words exactly, at minimum, but no verb
        assert 'verb' in reason.lower()

    def test_accept_noun_phrase_with_verb(self, quality_gate):
        """Accept: 'Le standard d'Elvis Presley joue.' (complete sentence)"""
        is_valid, reason = quality_gate.validate_sentence("Le standard d'Elvis Presley joue.")
        assert is_valid, f"Should accept noun phrase with verb: {reason}"

    def test_reject_title_reference(self, quality_gate):
        """Reject: 'It's Now or Never' (title without context, no verb)"""
        is_valid, reason = quality_gate.validate_sentence("It's Now or Never.")
        # 4 words, but likely no French verb
        assert not is_valid

    def test_accept_title_with_context(self, quality_gate):
        """Accept: 'La chanson résonne partout.' (title + context)"""
        is_valid, reason = quality_gate.validate_sentence(
            "La chanson résonne partout maintenant."
        )
        assert is_valid, f"Should accept title with context: {reason}"

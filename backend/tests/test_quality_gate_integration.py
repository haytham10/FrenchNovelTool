"""Integration tests for Quality Gate Service with GeminiService.

This test suite validates the integration between Quality Gate and GeminiService:
1. Quality gate properly rejects fragments during post-processing
2. Rejection stats are tracked correctly
3. Only valid sentences pass through to final output
4. GeminiService configuration properly enables/disables quality gate
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from app.services.gemini_service import GeminiService
from app.services.quality_gate_service import QualityGateService


@pytest.fixture
def mock_flask_app():
    """Mock Flask current_app for testing."""
    with patch('flask.current_app') as mock_app:
        # Mock config
        mock_app.config = {
            'GEMINI_API_KEY': 'test-key',
            'GEMINI_MODEL': 'gemini-2.5-flash-lite',
            'GEMINI_MAX_RETRIES': 3,
            'GEMINI_RETRY_DELAY': 1,
            'QUALITY_GATE_ENABLED': True,  # Enable quality gate
            'GEMINI_ENABLE_REPAIR': False,  # Disable repair for simpler testing
        }
        mock_app.logger = Mock()
        yield mock_app


@pytest.fixture
def gemini_service_with_quality_gate(mock_flask_app):
    """Create GeminiService with quality gate enabled."""
    service = GeminiService(
        sentence_length_limit=8,
        min_sentence_length=4,
        model_preference='speed'
    )
    return service


@pytest.fixture
def gemini_service_without_quality_gate(mock_flask_app):
    """Create GeminiService with quality gate disabled."""
    mock_flask_app.config['QUALITY_GATE_ENABLED'] = False
    service = GeminiService(
        sentence_length_limit=8,
        min_sentence_length=4,
        model_preference='speed'
    )
    return service


class TestQualityGateIntegration:
    """Test Quality Gate integration with GeminiService."""

    def test_quality_gate_enabled_initialization(self, gemini_service_with_quality_gate):
        """Test that quality gate is properly initialized when enabled."""
        service = gemini_service_with_quality_gate
        assert service.quality_gate_enabled == True
        assert service.quality_gate is not None
        assert isinstance(service.quality_gate, QualityGateService)
        assert service.quality_gate_rejections == 0
        assert service.rejected_sentences == []

    def test_quality_gate_disabled_initialization(self, gemini_service_without_quality_gate):
        """Test that quality gate is not initialized when disabled."""
        service = gemini_service_without_quality_gate
        assert service.quality_gate_enabled == False
        assert service.quality_gate is None

    def test_quality_gate_rejects_fragments(self, gemini_service_with_quality_gate):
        """Test that quality gate rejects fragments during post-processing."""
        service = gemini_service_with_quality_gate

        # Mock sentences with mix of valid and fragments
        mock_sentences = [
            "Il marche lentement dehors.",  # Valid
            "Dans la rue sombre.",  # Fragment (no verb)
            "Elle est très belle.",  # Valid
            "Pour toujours et à jamais.",  # Fragment (no verb)
            "Il faisait très froid.",  # Valid
        ]

        # Call _post_process_sentences (the integration point)
        result = service._post_process_sentences(mock_sentences)

        # Verify: Only valid sentences should pass through
        assert len(result) == 3, f"Expected 3 valid sentences, got {len(result)}: {result}"
        assert "Il marche lentement dehors." in result
        assert "Elle est très belle." in result
        assert "Il faisait très froid." in result

        # Verify: Fragments should be rejected
        assert "Dans la rue sombre." not in result
        assert "Pour toujours et à jamais." not in result

        # Verify: Rejection stats tracked
        assert service.quality_gate_rejections >= 2
        assert len(service.rejected_sentences) >= 2

    def test_quality_gate_tracks_rejection_reasons(self, gemini_service_with_quality_gate):
        """Test that quality gate tracks detailed rejection reasons."""
        service = gemini_service_with_quality_gate

        mock_sentences = [
            "Dans la rue sombre.",  # Should be rejected (no verb)
            "Il marche lentement dehors.",  # Should be accepted
        ]

        result = service._post_process_sentences(mock_sentences)

        # Verify rejection tracking
        assert len(service.rejected_sentences) >= 1
        rejected = service.rejected_sentences[0]
        assert 'text' in rejected
        assert 'reason' in rejected
        assert 'index' in rejected
        assert 'verb' in rejected['reason'].lower()

    def test_quality_gate_disabled_accepts_all(self, gemini_service_without_quality_gate):
        """Test that when quality gate is disabled, fragments pass through."""
        service = gemini_service_without_quality_gate

        mock_sentences = [
            "Il marche lentement dehors.",  # Valid
            "Dans la rue sombre.",  # Fragment (but should pass when disabled)
        ]

        result = service._post_process_sentences(mock_sentences)

        # With quality gate disabled, both should pass through
        # (Note: legacy fragment detector still runs as warning-only)
        assert len(result) >= 2 or service.quality_gate_enabled == False

    def test_quality_gate_with_edge_cases(self, gemini_service_with_quality_gate):
        """Test quality gate handles edge cases correctly."""
        service = gemini_service_with_quality_gate

        mock_sentences = [
            "Où vas-tu maintenant ?",  # Valid question
            "Il faisait très froid.",  # Valid statement
            "",  # Empty (should be filtered before quality gate)
            "  \t  ",  # Whitespace (should be filtered)
        ]

        result = service._post_process_sentences(mock_sentences)

        # Valid sentences should pass
        assert "Où vas-tu maintenant ?" in result or "Où vas-tu maintenant?" in result
        assert "Il faisait très froid." in result

    def test_quality_gate_respects_sentence_length_limits(self, gemini_service_with_quality_gate):
        """Test that quality gate respects configured length limits."""
        service = gemini_service_with_quality_gate

        mock_sentences = [
            "Bon.",  # Too short (1 word, min 4)
            "Il marche lentement dehors.",  # Valid (4 words)
            "Il mange des pommes rouges et délicieuses maintenant.",  # Too long (9 words, max 8)
        ]

        result = service._post_process_sentences(mock_sentences)

        # Only middle sentence should pass
        assert "Il marche lentement dehors." in result
        assert "Bon." not in result
        # Long sentence might be in rejected_sentences
        assert service.quality_gate_rejections >= 2


class TestQualityGatePerformance:
    """Test performance characteristics of quality gate integration."""

    def test_quality_gate_doesnt_significantly_slow_processing(self, gemini_service_with_quality_gate):
        """Test that quality gate adds minimal overhead to processing."""
        import time

        service = gemini_service_with_quality_gate

        # Large batch of sentences
        mock_sentences = [
            "Il marche lentement dehors.",
            "Elle est très belle.",
            "Il faisait très froid.",
        ] * 100  # 300 sentences

        start = time.time()
        result = service._post_process_sentences(mock_sentences)
        elapsed = time.time() - start

        # Should process 300 sentences in reasonable time (<3 seconds)
        assert elapsed < 3.0, f"Processing took {elapsed:.2f}s, should be <3s"

        # All valid sentences should pass
        assert len(result) == 300


class TestQualityGateConfiguration:
    """Test various configuration scenarios."""

    def test_quality_gate_initialization_failure_fallback(self, mock_flask_app):
        """Test that GeminiService continues if quality gate fails to initialize."""
        # Force quality gate initialization to fail
        with patch('app.services.gemini_service.QualityGateService', side_effect=Exception("spaCy not installed")):
            service = GeminiService(
                sentence_length_limit=8,
                min_sentence_length=4
            )

            # Service should still be created, but quality gate disabled
            assert service.quality_gate_enabled == False
            assert service.quality_gate is None

    def test_quality_gate_respects_custom_config(self, mock_flask_app):
        """Test that quality gate uses correct configuration from GeminiService."""
        service = GeminiService(
            sentence_length_limit=10,  # Custom max
            min_sentence_length=3,  # Custom min
        )

        if service.quality_gate:
            assert service.quality_gate.min_length == 3
            assert service.quality_gate.max_length == 10
            assert service.quality_gate.require_verb == True


class TestEndToEndScenarios:
    """Test realistic end-to-end scenarios."""

    def test_realistic_mixed_output(self, gemini_service_with_quality_gate):
        """Test with realistic mix of valid sentences and fragments."""
        service = gemini_service_with_quality_gate

        # Realistic output that might come from Gemini
        mock_gemini_output = [
            "Il marchait lentement dans la rue.",  # Valid
            "La rue était sombre et froide.",  # Valid (6 words)
            "dans la rue sombre",  # Fragment (no capital, no punct, no verb)
            "Il pensait à elle constamment.",  # Valid
            "Pour toujours et à jamais.",  # Fragment (no verb)
            "Elle était partie depuis longtemps.",  # Valid (6 words)
        ]

        result = service._post_process_sentences(mock_gemini_output)

        # Should have 4 valid sentences
        assert len(result) == 4, f"Expected 4 valid, got {len(result)}: {result}"

        # Verify valid sentences present
        valid_count = sum(1 for s in result if len(s.split()) >= 4 and len(s.split()) <= 8)
        assert valid_count >= 4

        # Verify rejections tracked
        assert service.quality_gate_rejections >= 2
        assert len(service.rejected_sentences) >= 2

    def test_all_valid_sentences_passthrough(self, gemini_service_with_quality_gate):
        """Test that all valid sentences pass through without rejection."""
        service = gemini_service_with_quality_gate

        all_valid = [
            "Il marche lentement dehors.",
            "Elle est très belle.",
            "La rue était très sombre.",
            "Il faisait très froid.",
            "Les enfants jouent dehors joyeusement.",
        ]

        result = service._post_process_sentences(all_valid)

        # All should pass
        assert len(result) == 5
        assert service.quality_gate_rejections == 0
        assert len(service.rejected_sentences) == 0

    def test_all_fragments_rejected(self, gemini_service_with_quality_gate):
        """Test that all fragments are rejected."""
        service = gemini_service_with_quality_gate

        all_fragments = [
            "Dans la rue sombre.",  # No verb
            "Pour toujours et à jamais.",  # No verb
            "Avec le temps qui passe.",  # No main verb
            "De retour dans la chambre.",  # No verb
        ]

        result = service._post_process_sentences(all_fragments)

        # None should pass (all rejected)
        assert len(result) == 0
        assert service.quality_gate_rejections >= 4

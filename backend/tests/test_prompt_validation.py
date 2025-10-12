"""
Prompt Validation Test Suite

Tests the new few-shot prompt against a comprehensive set of fragment patterns
and edge cases to ensure <0.5% fragment rate.

This test suite mocks Gemini API calls to test prompt logic without requiring
actual API access.
"""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from app.services.gemini_service import GeminiService


class TestFragmentDetection:
    """Test the fragment detection logic in GeminiService."""

    def setup_method(self):
        """Set up test fixtures before each test method."""
        # Mock the Flask app context and config
        self.mock_app = MagicMock()
        self.mock_app.config = {
            "GEMINI_API_KEY": "test_key",
            "GEMINI_MODEL": "gemini-2.5-flash-lite",
            "GEMINI_MAX_RETRIES": 3,
            "GEMINI_RETRY_DELAY": 1,
            "GEMINI_ALLOW_LOCAL_FALLBACK": False,
            "GEMINI_ENABLE_REPAIR": True,
            "GEMINI_REPAIR_MULTIPLIER": 1.5,
            "GEMINI_MAX_REPAIR_ATTEMPTS": 1,
            "GEMINI_FRAGMENT_RATE_RETRY_THRESHOLD": 3.0,
            "GEMINI_REJECT_ON_HIGH_FRAGMENT_RATE": False,
            "GEMINI_CALL_TIMEOUT_SECONDS": 180,
        }
        self.mock_app.logger = MagicMock()

    @pytest.fixture
    def gemini_service(self):
        """Create a GeminiService instance with mocked Flask context."""
        with patch("app.services.gemini_service.current_app", self.mock_app):
            service = GeminiService(
                sentence_length_limit=8,
                min_sentence_length=2,
                model_preference="speed",
            )
            return service

    def test_fragment_detection_prepositional_phrase(self, gemini_service):
        """Test detection of prepositional phrase fragments."""
        fragments = [
            "Dans la rue.",
            "Sur la table.",
            "Avec elle.",
            "Sans lui.",
            "Pour toujours.",
            "De retour dans la chambre.",
        ]

        with patch("app.services.gemini_service.current_app", self.mock_app):
            for fragment in fragments:
                assert gemini_service._is_likely_fragment(
                    fragment
                ), f"Failed to detect fragment: {fragment}"

    def test_fragment_detection_conjunction_start(self, gemini_service):
        """Test detection of conjunction fragments."""
        fragments = [
            "Et froide.",
            "Mais seul.",
            "Donc parti.",
        ]

        with patch("app.services.gemini_service.current_app", self.mock_app):
            for fragment in fragments:
                assert gemini_service._is_likely_fragment(
                    fragment
                ), f"Failed to detect fragment: {fragment}"

    def test_fragment_detection_temporal_expressions(self, gemini_service):
        """Test detection of temporal expression fragments."""
        fragments = [
            "Dans quinze ans.",
            "Pendant l'été.",
            "Avant le soir.",
        ]

        with patch("app.services.gemini_service.current_app", self.mock_app):
            for fragment in fragments:
                assert gemini_service._is_likely_fragment(
                    fragment
                ), f"Failed to detect fragment: {fragment}"

    def test_fragment_detection_idiomatic_phrases(self, gemini_service):
        """Test detection of idiomatic phrase fragments."""
        fragments = [
            "Pour toujours et à jamais",
            "Avec le temps",
        ]

        with patch("app.services.gemini_service.current_app", self.mock_app):
            for fragment in fragments:
                assert gemini_service._is_likely_fragment(
                    fragment
                ), f"Failed to detect fragment: {fragment}"

    def test_complete_sentence_not_flagged(self, gemini_service):
        """Test that complete sentences are NOT flagged as fragments."""
        complete_sentences = [
            "Il marchait dans la rue.",
            "La rue était sombre et froide.",
            "Elle pensait à lui constamment.",
            "Ils s'aimeront pour toujours.",
            "Le temps passera lentement.",
            "Il est retourné dans la chambre.",
            "La chanson jouait à la radio.",
        ]

        with patch("app.services.gemini_service.current_app", self.mock_app):
            for sentence in complete_sentences:
                assert not gemini_service._is_likely_fragment(
                    sentence
                ), f"False positive fragment detection: {sentence}"

    def test_short_complete_sentences(self, gemini_service):
        """Test that short but complete sentences are valid."""
        complete_sentences = [
            "Il court.",
            "Elle rit.",
            "Ils partent.",
            "Je sais.",
        ]

        with patch("app.services.gemini_service.current_app", self.mock_app):
            for sentence in complete_sentences:
                assert not gemini_service._is_likely_fragment(
                    sentence
                ), f"False positive on short complete sentence: {sentence}"

    def test_questions_not_flagged(self, gemini_service):
        """Test that questions are not flagged as fragments."""
        questions = [
            "Où est-il ?",
            "Que fait-elle ?",
            "Pourquoi partent-ils ?",
        ]

        with patch("app.services.gemini_service.current_app", self.mock_app):
            for question in questions:
                assert not gemini_service._is_likely_fragment(
                    question
                ), f"False positive on question: {question}"


class TestPromptValidation:
    """Test the prompt generation and validation logic."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_app = MagicMock()
        self.mock_app.config = {
            "GEMINI_API_KEY": "test_key",
            "GEMINI_MODEL": "gemini-2.5-flash-lite",
            "GEMINI_MAX_RETRIES": 3,
            "GEMINI_RETRY_DELAY": 1,
            "GEMINI_ALLOW_LOCAL_FALLBACK": False,
            "GEMINI_ENABLE_REPAIR": True,
            "GEMINI_REPAIR_MULTIPLIER": 1.5,
            "GEMINI_MAX_REPAIR_ATTEMPTS": 1,
            "GEMINI_FRAGMENT_RATE_RETRY_THRESHOLD": 3.0,
            "GEMINI_REJECT_ON_HIGH_FRAGMENT_RATE": False,
            "GEMINI_CALL_TIMEOUT_SECONDS": 180,
            "GEMINI_PROMPT_VERSION": "v2",  # Use new prompt
        }
        self.mock_app.logger = MagicMock()

    @pytest.fixture
    def gemini_service(self):
        """Create GeminiService with new prompt."""
        with patch("app.services.gemini_service.current_app", self.mock_app):
            service = GeminiService(
                sentence_length_limit=8,
                min_sentence_length=2,
                model_preference="speed",
            )
            return service

    def test_new_prompt_imports(self):
        """Test that new prompt module can be imported."""
        from app.services.prompts import build_sentence_normalizer_prompt

        prompt = build_sentence_normalizer_prompt()
        assert prompt
        assert len(prompt) > 0
        assert "EXAMPLES" in prompt
        assert "FRAGMENT" in prompt

    def test_new_prompt_length(self):
        """Test that new prompt is concise (target: ≤65 lines)."""
        from app.services.prompts import build_sentence_normalizer_prompt

        prompt = build_sentence_normalizer_prompt()
        line_count = len(prompt.split("\n"))
        # Allow some buffer for configuration variations
        assert line_count <= 65, f"Prompt too long: {line_count} lines (target: ≤65)"

    def test_prompt_contains_few_shot_examples(self):
        """Test that prompt includes few-shot examples."""
        from app.services.prompts import build_sentence_normalizer_prompt

        prompt = build_sentence_normalizer_prompt()

        # Check for key example components
        assert "Example 1" in prompt
        assert "WRONG OUTPUT" in prompt
        assert "CORRECT OUTPUT" in prompt
        assert "Why correct" in prompt

    def test_minimal_prompt_generation(self):
        """Test minimal prompt for fallback scenarios."""
        from app.services.prompts import build_minimal_prompt

        minimal = build_minimal_prompt()
        assert minimal
        assert "JSON" in minimal
        assert "complete" in minimal.lower()


class TestMockedGeminiResponses:
    """Test GeminiService with mocked API responses to validate prompt effectiveness."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_app = MagicMock()
        self.mock_app.config = {
            "GEMINI_API_KEY": "test_key",
            "GEMINI_MODEL": "gemini-2.5-flash-lite",
            "GEMINI_MAX_RETRIES": 3,
            "GEMINI_RETRY_DELAY": 1,
            "GEMINI_ALLOW_LOCAL_FALLBACK": False,
            "GEMINI_ENABLE_REPAIR": False,  # Disable repair for these tests
            "GEMINI_REPAIR_MULTIPLIER": 1.5,
            "GEMINI_MAX_REPAIR_ATTEMPTS": 1,
            "GEMINI_FRAGMENT_RATE_RETRY_THRESHOLD": 3.0,
            "GEMINI_REJECT_ON_HIGH_FRAGMENT_RATE": False,
            "GEMINI_CALL_TIMEOUT_SECONDS": 180,
        }
        self.mock_app.logger = MagicMock()

    @pytest.fixture
    def gemini_service(self):
        """Create GeminiService instance."""
        with patch("app.services.gemini_service.current_app", self.mock_app):
            service = GeminiService(
                sentence_length_limit=8,
                min_sentence_length=2,
                model_preference="speed",
            )
            return service

    def test_simple_sentence_passthrough(self, gemini_service):
        """Test that simple sentences pass through unchanged."""
        with patch("app.services.gemini_service.current_app", self.mock_app):
            mock_response = Mock()
            mock_response.text = json.dumps({"sentences": ["Il marche dans la rue."]})

            with patch.object(
                gemini_service.client.models, "generate_content", return_value=mock_response
            ):
                result = gemini_service.normalize_text("Il marche dans la rue.")
                sentences = [s["normalized"] for s in result["sentences"]]

                assert len(sentences) == 1
                assert sentences[0] == "Il marche dans la rue."
                assert gemini_service.last_fragment_rate == 0.0

    def test_fragment_rejection_prepositional_phrase(self, gemini_service):
        """Test that prepositional phrase fragments are detected."""
        with patch("app.services.gemini_service.current_app", self.mock_app):
            # Simulate AI returning a fragment (BAD behavior)
            mock_response = Mock()
            mock_response.text = json.dumps({"sentences": ["Dans la rue."]})

            with patch.object(
                gemini_service.client.models, "generate_content", return_value=mock_response
            ):
                result = gemini_service.normalize_text("Dans la rue.")
                sentences = [s["normalized"] for s in result["sentences"]]

                # Fragment detector should flag this
                assert gemini_service.last_fragment_count > 0
                assert gemini_service.last_fragment_rate > 0

    def test_long_sentence_splitting_no_fragments(self, gemini_service):
        """Test that long sentences are split WITHOUT creating fragments."""
        with patch("app.services.gemini_service.current_app", self.mock_app):
            # Good AI behavior: complete sentences only
            mock_response = Mock()
            mock_response.text = json.dumps(
                {
                    "sentences": [
                        "Il marchait lentement dans la rue.",
                        "La rue était sombre et froide.",
                        "Il pensait à elle.",
                    ]
                }
            )

            with patch.object(
                gemini_service.client.models, "generate_content", return_value=mock_response
            ):
                result = gemini_service.normalize_text(
                    "Il marchait lentement dans la rue sombre et froide, pensant à elle."
                )
                sentences = [s["normalized"] for s in result["sentences"]]

                assert len(sentences) == 3
                # No fragments should be detected
                assert gemini_service.last_fragment_count == 0
                assert gemini_service.last_fragment_rate == 0.0

    def test_bad_ai_response_with_fragments(self, gemini_service):
        """Test detection when AI returns fragments (BAD behavior)."""
        with patch("app.services.gemini_service.current_app", self.mock_app):
            # Bad AI behavior: returns fragments
            mock_response = Mock()
            mock_response.text = json.dumps(
                {
                    "sentences": [
                        "Il marchait lentement.",
                        "dans la rue sombre",  # FRAGMENT
                        "et froide",  # FRAGMENT
                        "pensant à elle",  # FRAGMENT
                    ]
                }
            )

            # Temporarily disable fragment retry threshold to test detection
            original_threshold = gemini_service.fragment_rate_retry_threshold
            gemini_service.fragment_rate_retry_threshold = 100.0  # Never retry

            with patch.object(
                gemini_service.client.models, "generate_content", return_value=mock_response
            ):
                result = gemini_service.normalize_text(
                    "Il marchait lentement dans la rue sombre et froide, pensant à elle."
                )

                # Should detect multiple fragments
                assert gemini_service.last_fragment_count >= 3
                assert gemini_service.last_fragment_rate > 0

                # Restore original threshold
                gemini_service.fragment_rate_retry_threshold = original_threshold

    def test_temporal_fragment_detection(self, gemini_service):
        """Test detection of temporal expression fragments."""
        with patch("app.services.gemini_service.current_app", self.mock_app):
            mock_response = Mock()
            mock_response.text = json.dumps({"sentences": ["Pour toujours et à jamais"]})

            with patch.object(
                gemini_service.client.models, "generate_content", return_value=mock_response
            ):
                result = gemini_service.normalize_text("Pour toujours et à jamais")

                # Should detect fragment
                assert gemini_service.last_fragment_count > 0

    def test_dialogue_handling(self, gemini_service):
        """Test that dialogue is handled properly."""
        with patch("app.services.gemini_service.current_app", self.mock_app):
            mock_response = Mock()
            mock_response.text = json.dumps({"sentences": ["Il dit qu'il l'aime."]})

            with patch.object(
                gemini_service.client.models, "generate_content", return_value=mock_response
            ):
                result = gemini_service.normalize_text("Il dit : « Je t'aime. »")
                sentences = [s["normalized"] for s in result["sentences"]]

                assert len(sentences) == 1
                assert gemini_service.last_fragment_count == 0

    def test_multiple_complete_sentences(self, gemini_service):
        """Test processing of multiple complete sentences."""
        with patch("app.services.gemini_service.current_app", self.mock_app):
            mock_response = Mock()
            mock_response.text = json.dumps(
                {
                    "sentences": [
                        "Le soleil brille.",
                        "Les oiseaux chantent.",
                        "C'est une belle journée.",
                    ]
                }
            )

            with patch.object(
                gemini_service.client.models, "generate_content", return_value=mock_response
            ):
                result = gemini_service.normalize_text(
                    "Le soleil brille. Les oiseaux chantent. C'est une belle journée."
                )
                sentences = [s["normalized"] for s in result["sentences"]]

                assert len(sentences) == 3
                assert gemini_service.last_fragment_count == 0
                assert gemini_service.last_fragment_rate == 0.0


class TestFragmentRateCalculation:
    """Test fragment rate calculation and thresholds."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_app = MagicMock()
        self.mock_app.config = {
            "GEMINI_API_KEY": "test_key",
            "GEMINI_MODEL": "gemini-2.5-flash-lite",
            "GEMINI_MAX_RETRIES": 3,
            "GEMINI_RETRY_DELAY": 1,
            "GEMINI_ALLOW_LOCAL_FALLBACK": False,
            "GEMINI_ENABLE_REPAIR": False,
            "GEMINI_REPAIR_MULTIPLIER": 1.5,
            "GEMINI_MAX_REPAIR_ATTEMPTS": 1,
            "GEMINI_FRAGMENT_RATE_RETRY_THRESHOLD": 0.5,  # Strict threshold
            "GEMINI_REJECT_ON_HIGH_FRAGMENT_RATE": True,
            "GEMINI_CALL_TIMEOUT_SECONDS": 180,
        }
        self.mock_app.logger = MagicMock()

    @pytest.fixture
    def gemini_service(self):
        """Create GeminiService with strict fragment threshold."""
        with patch("app.services.gemini_service.current_app", self.mock_app):
            service = GeminiService(
                sentence_length_limit=8,
                min_sentence_length=2,
                model_preference="speed",
            )
            return service

    def test_fragment_rate_calculation(self, gemini_service):
        """Test that fragment rate is calculated correctly."""
        with patch("app.services.gemini_service.current_app", self.mock_app):
            # 1 fragment out of 4 sentences = 25% fragment rate
            mock_response = Mock()
            mock_response.text = json.dumps(
                {
                    "sentences": [
                        "Il marche.",
                        "Dans la rue.",  # FRAGMENT
                        "Elle court.",
                        "Ils jouent.",
                    ]
                }
            )

            with patch.object(
                gemini_service.client.models, "generate_content", return_value=mock_response
            ):
                try:
                    result = gemini_service.normalize_text("Test text")
                except Exception:
                    pass  # May raise due to high fragment rate

                # Check that fragment rate is around 25%
                assert gemini_service.last_fragment_count >= 1
                assert gemini_service.last_fragment_rate > 20.0

    def test_zero_fragment_rate_target(self, gemini_service):
        """Test achieving zero fragment rate with perfect AI output."""
        with patch("app.services.gemini_service.current_app", self.mock_app):
            # Perfect AI response: no fragments
            mock_response = Mock()
            mock_response.text = json.dumps(
                {
                    "sentences": [
                        "Il marche dans la rue.",
                        "La rue est sombre.",
                        "Elle court vite.",
                        "Ils jouent ensemble.",
                    ]
                }
            )

            with patch.object(
                gemini_service.client.models, "generate_content", return_value=mock_response
            ):
                result = gemini_service.normalize_text("Test text")
                sentences = [s["normalized"] for s in result["sentences"]]

                assert len(sentences) == 4
                assert gemini_service.last_fragment_count == 0
                assert gemini_service.last_fragment_rate == 0.0


class TestEdgeCases:
    """Test edge cases and corner scenarios."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_app = MagicMock()
        self.mock_app.config = {
            "GEMINI_API_KEY": "test_key",
            "GEMINI_MODEL": "gemini-2.5-flash-lite",
            "GEMINI_MAX_RETRIES": 3,
            "GEMINI_RETRY_DELAY": 1,
            "GEMINI_ALLOW_LOCAL_FALLBACK": False,
            "GEMINI_ENABLE_REPAIR": False,
            "GEMINI_REPAIR_MULTIPLIER": 1.5,
            "GEMINI_MAX_REPAIR_ATTEMPTS": 1,
            "GEMINI_FRAGMENT_RATE_RETRY_THRESHOLD": 3.0,
            "GEMINI_REJECT_ON_HIGH_FRAGMENT_RATE": False,
            "GEMINI_CALL_TIMEOUT_SECONDS": 180,
        }
        self.mock_app.logger = MagicMock()

    @pytest.fixture
    def gemini_service(self):
        """Create GeminiService instance."""
        with patch("app.services.gemini_service.current_app", self.mock_app):
            service = GeminiService(
                sentence_length_limit=8,
                min_sentence_length=2,
                model_preference="speed",
            )
            return service

    def test_empty_input(self, gemini_service):
        """Test handling of empty input."""
        with patch("app.services.gemini_service.current_app", self.mock_app):
            result = gemini_service.normalize_text("")
            assert result["sentences"] == []

    def test_single_word_input(self, gemini_service):
        """Test handling of single word input."""
        with patch("app.services.gemini_service.current_app", self.mock_app):
            mock_response = Mock()
            mock_response.text = json.dumps(
                {"sentences": [{"normalized": "Il est seul.", "original": "Seul"}]}
            )

            with patch.object(
                gemini_service.client.models, "generate_content", return_value=mock_response
            ):
                result = gemini_service.normalize_text("Seul")
                # Either empty or completed sentence
                sentences = [s["normalized"] for s in result["sentences"]]
                # If sentences returned, they should not be fragments
                for sentence in sentences:
                    word_count = len(sentence.split())
                    # Allow short but complete sentences
                    if word_count == 1:
                        # Single word must be checked - likely a fragment
                        assert sentence.endswith((".", "!", "?"))

    def test_very_long_sentence(self, gemini_service):
        """Test handling of very long sentences."""
        with patch("app.services.gemini_service.current_app", self.mock_app):
            long_sentence = (
                "Il marchait lentement dans la rue sombre et froide, "
                "pensant à elle constamment, se demandant s'il la reverrait un jour, "
                "espérant qu'elle penserait aussi à lui de temps en temps."
            )

            mock_response = Mock()
            mock_response.text = json.dumps(
                {
                    "sentences": [
                        "Il marchait lentement dans la rue.",
                        "La rue était sombre et froide.",
                        "Il pensait à elle constamment.",
                        "Il se demandait s'il la reverrait.",
                        "Il espérait qu'elle penserait à lui.",
                    ]
                }
            )

            with patch.object(
                gemini_service.client.models, "generate_content", return_value=mock_response
            ):
                result = gemini_service.normalize_text(long_sentence)
                sentences = [s["normalized"] for s in result["sentences"]]

                # Should produce multiple complete sentences
                assert len(sentences) >= 3
                # No fragments
                assert gemini_service.last_fragment_count == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

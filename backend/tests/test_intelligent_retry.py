"""Tests for intelligent Gemini retry cascade functionality."""
import pytest
from unittest.mock import Mock, patch, MagicMock
from app.services.gemini_service import GeminiService, GeminiAPIError


class TestIntelligentRetry:
    """Test cases for intelligent retry cascade in GeminiService."""

    @pytest.fixture
    def app_context(self):
        """Create Flask app context for testing."""
        from app import create_app
        app = create_app()
        with app.app_context():
            yield app

    @pytest.fixture
    def mock_gemini_response(self):
        """Create a mock Gemini response."""
        mock_response = Mock()
        mock_response.text = '{"sentences": ["Test sentence one.", "Test sentence two."]}'
        return mock_response

    @pytest.fixture
    def mock_empty_response(self):
        """Create a mock empty Gemini response."""
        mock_response = Mock()
        mock_response.text = ''
        return mock_response

    def test_primary_model_success(self, app_context, mock_gemini_response):
        """Test that primary model succeeds on first try."""
        with patch('google.genai.Client') as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client
            mock_client.models.generate_content.return_value = mock_gemini_response

            service = GeminiService(sentence_length_limit=8, model_preference='speed')
            result = service.normalize_text("Test text")

            assert 'sentences' in result
            assert len(result['sentences']) == 2
            assert '_fallback_method' not in result  # Primary succeeded
            # Verify only called once with primary model
            assert mock_client.models.generate_content.call_count == 1

    def test_model_fallback_speed_to_balanced(self, app_context, mock_empty_response, mock_gemini_response):
        """Test fallback from speed to balanced model."""
        with patch('google.genai.Client') as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client

            # First call fails (empty response), second succeeds
            mock_client.models.generate_content.side_effect = [
                mock_empty_response,  # speed model fails
                mock_gemini_response  # balanced model succeeds
            ]

            service = GeminiService(sentence_length_limit=8, model_preference='speed')
            result = service.normalize_text("Test text")

            assert 'sentences' in result
            assert len(result['sentences']) == 2
            assert '_fallback_method' in result
            assert 'model_fallback:balanced' in result['_fallback_method']
            # Verify called twice (speed then balanced)
            assert mock_client.models.generate_content.call_count == 2

    def test_model_fallback_cascade(self, app_context, mock_empty_response, mock_gemini_response):
        """Test full model fallback cascade speed -> balanced -> quality."""
        with patch('google.genai.Client') as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client

            # First two calls fail, third succeeds
            mock_client.models.generate_content.side_effect = [
                mock_empty_response,  # speed model fails
                mock_empty_response,  # balanced model fails
                mock_gemini_response  # quality model succeeds
            ]

            service = GeminiService(sentence_length_limit=8, model_preference='speed')
            result = service.normalize_text("Test text")

            assert 'sentences' in result
            assert '_fallback_method' in result
            assert 'model_fallback:quality' in result['_fallback_method']
            # Verify called three times (speed, balanced, quality)
            assert mock_client.models.generate_content.call_count == 3

    def test_subchunk_fallback(self, app_context, mock_empty_response, mock_gemini_response):
        """Test subchunk splitting when all models fail on full text."""
        with patch('google.genai.Client') as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client

            # Define responses: fail on full text, succeed on subchunks
            call_count = [0]
            def side_effect(*args, **kwargs):
                call_count[0] += 1
                # First 3 calls fail (speed, balanced, quality on full text)
                if call_count[0] <= 3:
                    return mock_empty_response
                # Subsequent calls succeed (subchunks)
                return mock_gemini_response

            mock_client.models.generate_content.side_effect = side_effect

            # Use a longer text that will be split into subchunks
            long_text = "This is a test sentence. " * 50
            service = GeminiService(sentence_length_limit=8, model_preference='speed')
            result = service.normalize_text(long_text)

            assert 'sentences' in result
            assert '_fallback_method' in result
            assert 'subchunk' in result['_fallback_method']

    def test_minimal_prompt_fallback(self, app_context):
        """Test minimal prompt fallback when subchunking fails."""
        with patch('google.genai.Client') as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client

            mock_empty = Mock()
            mock_empty.text = ''
            mock_success = Mock()
            mock_success.text = '{"sentences": ["Short test."]}'

            call_count = [0]
            def side_effect(*args, **kwargs):
                call_count[0] += 1
                # Fail initial attempts and subchunk attempts
                # Succeed on minimal prompt (call 8+)
                if call_count[0] >= 8:
                    return mock_success
                return mock_empty

            mock_client.models.generate_content.side_effect = side_effect

            service = GeminiService(sentence_length_limit=8, model_preference='speed')
            # Use short text so subchunking doesn't help
            result = service.normalize_text("Test")

            assert 'sentences' in result
            assert '_fallback_method' in result
            assert 'minimal_prompt' in result['_fallback_method']

    def test_local_fallback_last_resort(self, app_context, mock_empty_response):
        """Test local fallback is used as absolute last resort."""
        with patch('google.genai.Client') as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client

            # All Gemini calls fail
            mock_client.models.generate_content.return_value = mock_empty_response

            service = GeminiService(sentence_length_limit=8, model_preference='speed')
            result = service.normalize_text("Test sentence.")

            assert 'sentences' in result
            assert '_fallback_method' in result
            assert 'local_segmentation' in result['_fallback_method']
            # Verify local fallback produced result
            assert len(result['sentences']) > 0

    def test_balanced_model_has_quality_fallback(self, app_context, mock_empty_response, mock_gemini_response):
        """Test that balanced model falls back to quality only."""
        with patch('google.genai.Client') as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client

            # First call fails (balanced), second succeeds (quality)
            mock_client.models.generate_content.side_effect = [
                mock_empty_response,  # balanced fails
                mock_gemini_response  # quality succeeds
            ]

            service = GeminiService(sentence_length_limit=8, model_preference='balanced')
            result = service.normalize_text("Test text")

            assert 'sentences' in result
            assert '_fallback_method' in result
            assert 'model_fallback:quality' in result['_fallback_method']
            # Only 2 calls: balanced then quality
            assert mock_client.models.generate_content.call_count == 2

    def test_quality_model_no_model_fallback(self, app_context, mock_empty_response):
        """Test that quality model has no model fallback (goes straight to subchunk)."""
        with patch('google.genai.Client') as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client

            # Mock response for subchunks
            mock_success = Mock()
            mock_success.text = '{"sentences": ["Test one.", "Test two."]}'

            call_count = [0]
            def side_effect(*args, **kwargs):
                call_count[0] += 1
                # First call fails (quality on full text)
                if call_count[0] == 1:
                    return mock_empty_response
                # Subsequent calls succeed (subchunks)
                return mock_success

            mock_client.models.generate_content.side_effect = side_effect

            service = GeminiService(sentence_length_limit=8, model_preference='quality')
            long_text = "This is test. " * 20
            result = service.normalize_text(long_text)

            assert 'sentences' in result
            # Should skip model fallback and go to subchunk
            assert '_fallback_method' in result
            assert 'subchunk' in result['_fallback_method']

    def test_minimal_prompt_format(self, app_context):
        """Test that minimal prompt is actually minimal and well-formed."""
        with patch('google.genai.Client'):
            service = GeminiService(sentence_length_limit=12, model_preference='speed')
            minimal = service.build_minimal_prompt()

            # Verify it's short
            assert len(minimal) < 300
            # Verify it mentions JSON
            assert 'JSON' in minimal or 'json' in minimal
            # Verify it mentions sentence limit
            assert '12' in minimal
            # Verify it doesn't contain verbose instructions
            assert 'Context-Awareness' not in minimal
            assert 'Style and Tone' not in minimal

    def test_full_prompt_still_available(self, app_context):
        """Test that full prompt is still available and detailed."""
        with patch('google.genai.Client'):
            service = GeminiService(sentence_length_limit=12, model_preference='speed')
            full = service.build_prompt()

            # Verify it's comprehensive
            assert len(full) > 500
            # Verify it contains detailed instructions
            assert 'Context-Awareness' in full
            assert 'Dialogue Handling' in full

    def test_subchunk_splitting_creates_multiple_chunks(self, app_context):
        """Test that text is properly split into subchunks."""
        with patch('google.genai.Client'):
            service = GeminiService(sentence_length_limit=8, model_preference='speed')

            # Create text with clear paragraph boundaries
            text = "Paragraph one.\n\nParagraph two.\n\nParagraph three.\n\nParagraph four."
            subchunks = service._split_text_into_subchunks(text, num_subchunks=2)

            assert len(subchunks) == 2
            assert all(len(s) > 0 for s in subchunks)

    def test_api_error_propagation_from_call_gemini_api(self, app_context):
        """Test that GeminiAPIError is properly raised from _call_gemini_api."""
        with patch('google.genai.Client') as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client

            mock_empty = Mock()
            mock_empty.text = ''
            mock_client.models.generate_content.return_value = mock_empty

            service = GeminiService(sentence_length_limit=8, model_preference='speed')

            with pytest.raises(GeminiAPIError):
                service._call_gemini_api("Test", "Prompt", "gemini-2.5-flash")

    def test_malformed_json_recovery_in_call_gemini_api(self, app_context):
        """Test that malformed JSON is recovered in _call_gemini_api."""
        with patch('google.genai.Client') as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client

            # Response with recoverable list but not proper JSON
            mock_response = Mock()
            mock_response.text = 'Here are the sentences: ["Sentence one.", "Sentence two."]'
            mock_client.models.generate_content.return_value = mock_response

            service = GeminiService(sentence_length_limit=8, model_preference='speed')
            result = service._call_gemini_api("Test", "Prompt", "gemini-2.5-flash")

            assert 'sentences' in result
            assert len(result['sentences']) == 2

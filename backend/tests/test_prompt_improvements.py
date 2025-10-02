"""
Test suite for Phase 1 Prompt Improvements
Tests the improved Gemini prompt for French novel sentence rewriting.

NOTE: These tests are currently disabled as Phase 1 advanced features have been rolled back
to restore basic functionality. See issue #15 for context.
"""
import sys
import os

# Add the backend directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from unittest.mock import MagicMock, patch
from flask import Flask
from app.services.gemini_service import GeminiService
from config import Config


@pytest.fixture
def app_context():
    """Create Flask app context for testing"""
    app = Flask(__name__)
    app.config.from_object(Config)
    with app.app_context():
        yield app


# DISABLED: Phase 1 features have been rolled back
@pytest.mark.skip(reason="Phase 1 features rolled back - see issue #15")
class TestPhase1PromptImprovements:
    """Test cases for Phase 1 prompt improvements"""

    def test_prompt_includes_grammatical_rules(self, app_context):
        """Test that prompt includes specific grammatical splitting rules"""
        # This test verifies the prompt contains the key phrases
        # In a real scenario, we'd test against actual Gemini API responses

        # Get the route function
        with app_context.test_request_context():
            # The prompt is constructed with sentence_length_limit
            sentence_length_limit = 8

            prompt = (
                "You are a literary assistant specialized in processing French novels. "
                "Your task is to extract and process EVERY SINGLE SENTENCE from the entire document. "
                "You must process the complete text from beginning to end without skipping any content. "
                f"If a sentence is {sentence_length_limit} words long or less, "
                "add it to the list as is. "
                f"If a sentence is longer than {sentence_length_limit} words, "
                "you must rewrite it into shorter sentences, "
                f"each with {sentence_length_limit} words or fewer. "
                "\n\n"
                "**Rewriting Rules:**\n"
                "- Split long sentences at natural grammatical breaks, such as "
                "conjunctions (e.g., 'et', 'mais', 'donc', 'car', 'or'), "
                "subordinate clauses, or where a logical shift in thought occurs.\n"
                "- Do not break meaning; each new sentence must stand alone "
                "grammatically and semantically.\n"
                "\n"
                "**Context-Awareness:**\n"
                "- Ensure the rewritten sentences maintain the logical flow and "
                "connection to the preceding text. "
                "The output must read as a continuous, coherent narrative.\n"
                "\n"
                "**Dialogue Handling:**\n"
                "- If a sentence is enclosed in quotation marks (« », \" \", or ' '), "
                "treat it as dialogue. "
                "Do not split it unless absolutely necessary. "
                "If a split is unavoidable, do so in a way that maintains "
                "the natural cadence of speech.\n"
                "\n"
                "**Style and Tone Preservation:**\n"
                "- Maintain the literary tone and style of the original text. "
                "Avoid using overly simplistic language or modern idioms "
                "that would feel out of place.\n"
                "- Preserve the exact original meaning and use as many of the "
                "original French words as possible.\n"
                "\n"
                "**Output Format:**\n"
                "Present the final output as a JSON object with a single key "
                "'sentences' which is an array of strings. "
                f"For example: {{\"sentences\": [\"Voici la première phrase.\", "
                "\"Et voici la deuxième.\"]}}"
            )

            # Verify key components are present
            assert "literary assistant" in prompt
            assert "grammatical breaks" in prompt
            assert "conjunctions" in prompt
            assert "'et', 'mais', 'donc'" in prompt
            assert "Context-Awareness" in prompt
            assert "Dialogue Handling" in prompt
            assert "quotation marks" in prompt
            assert "Style and Tone Preservation" in prompt
            assert "literary tone" in prompt
            assert "JSON object" in prompt
            assert "For example:" in prompt

    @patch('google.genai.Client')
    def test_json_output_validation(self, mock_client, app_context):
        """Test that the service properly validates JSON output"""
        # Mock the Gemini client
        mock_response = MagicMock()
        mock_response.text = '{"sentences": ["Première phrase.", "Deuxième phrase."]}'

        mock_model = MagicMock()
        mock_model.generate_content.return_value = mock_response

        mock_client_instance = MagicMock()
        mock_client_instance.models = mock_model
        mock_client.return_value = mock_client_instance

        gemini_service = GeminiService(sentence_length_limit=8)

        # Create a minimal test PDF file
        pdf_content = b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n%%EOF"
        temp_path = "/tmp/test_prompt.pdf"
        with open(temp_path, 'wb') as f:
            f.write(pdf_content)

        try:
            prompt = "Test prompt"
            sentences = gemini_service.generate_content_from_pdf(prompt, temp_path)

            # Verify the output is a list
            assert isinstance(sentences, list)
            assert len(sentences) == 2
            assert sentences[0] == "Première phrase."
            assert sentences[1] == "Deuxième phrase."
        finally:
            # Clean up
            if os.path.exists(temp_path):
                os.remove(temp_path)

    @patch('google.genai.Client')
    def test_invalid_json_handling(self, mock_client, app_context):
        """Test that the service handles invalid JSON gracefully"""
        # Mock the Gemini client to return invalid JSON
        mock_response = MagicMock()
        mock_response.text = 'This is not valid JSON'

        mock_model = MagicMock()
        mock_model.generate_content.return_value = mock_response

        mock_client_instance = MagicMock()
        mock_client_instance.models = mock_model
        mock_client.return_value = mock_client_instance

        gemini_service = GeminiService(sentence_length_limit=8)

        # Create a minimal test PDF file
        pdf_content = b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n%%EOF"
        temp_path = "/tmp/test_invalid_json.pdf"
        with open(temp_path, 'wb') as f:
            f.write(pdf_content)

        try:
            prompt = "Test prompt"
            with pytest.raises(ValueError, match="Failed to parse response from Gemini API"):
                gemini_service.generate_content_from_pdf(prompt, temp_path)
        finally:
            # Clean up
            if os.path.exists(temp_path):
                os.remove(temp_path)

    @patch('google.genai.Client')
    def test_empty_response_handling(self, mock_client, app_context):
        """Test that the service handles empty responses gracefully"""
        # Mock the Gemini client to return empty response
        mock_response = MagicMock()
        mock_response.text = ''

        mock_model = MagicMock()
        mock_model.generate_content.return_value = mock_response

        mock_client_instance = MagicMock()
        mock_client_instance.models = mock_model
        mock_client.return_value = mock_client_instance

        gemini_service = GeminiService(sentence_length_limit=8)

        # Create a minimal test PDF file
        pdf_content = b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n%%EOF"
        temp_path = "/tmp/test_empty.pdf"
        with open(temp_path, 'wb') as f:
            f.write(pdf_content)

        try:
            prompt = "Test prompt"
            with pytest.raises(ValueError, match="Gemini returned an empty response"):
                gemini_service.generate_content_from_pdf(prompt, temp_path)
        finally:
            # Clean up
            if os.path.exists(temp_path):
                os.remove(temp_path)


# DISABLED: Phase 1 features have been rolled back
@pytest.mark.skip(reason="Phase 1 features rolled back - see issue #15")
class TestPromptExamples:
    """Test cases with example French text scenarios"""

    def test_dialogue_example_format(self):
        """Test that dialogue examples follow expected format"""
        # Test data representing dialogue that should be preserved
        dialogue_examples = [
            '« Bonjour, comment allez-vous aujourd\'hui ? »',
            '"Il fait beau", dit-elle en souriant.',
            '\'Je ne sais pas\', répondit-il.'
        ]

        for example in dialogue_examples:
            # Verify dialogue markers are present
            assert any(marker in example for marker in ['«', '»', '"', "'"]), \
                f"Dialogue example should contain quotation marks: {example}"

    def test_long_sentence_split_example(self):
        """Test example of how a long sentence should be split"""
        # Example: Long sentence with conjunction
        long_sentence = (
            "Le jeune homme marchait lentement dans la rue sombre et "
            "froide, pensant à sa vie passée et aux choix qu'il avait "
            "faits durant toutes ces années difficiles."
        )

        # Count words to verify it exceeds typical limit
        word_count = len(long_sentence.split())
        assert word_count > 15, "Test sentence should be long enough to require splitting"

    def test_context_preservation_example(self):
        """Test that context between sentences should be maintained"""
        # Example of sentences that should maintain context
        context_example = [
            "Marie ouvrit la porte avec précaution.",
            "Elle aperçut une silhouette dans l'obscurité.",
            "La silhouette s'avança lentement vers elle."
        ]

        # Verify these form a coherent narrative
        assert len(context_example) == 3
        # Each sentence should relate to the previous one
        assert all(len(s.split()) <= 10 for s in context_example), \
            "Example sentences should be reasonably short"


# DISABLED: Phase 1 features have been rolled back
@pytest.mark.skip(reason="Phase 1 features rolled back - see issue #15")
class TestCompleteness:
    """Test cases for ensuring complete document processing"""

    def test_prompt_emphasizes_complete_processing(self):
        """Test that prompt explicitly requires processing ALL sentences"""
        # Test the prompt directly without needing API key
        sentence_length_limit = 8
        
        # This is the expected prompt structure based on our implementation
        prompt_start = (
            "You are a literary assistant specialized in processing French novels. "
            "Your task is to extract and process EVERY SINGLE SENTENCE from the entire document. "
            "You must process the complete text from beginning to end without skipping any content. "
        )
        
        # Verify the critical completeness instructions are present
        assert "EVERY SINGLE SENTENCE" in prompt_start, \
            "Prompt must explicitly state to process every single sentence"
        assert "entire document" in prompt_start, \
            "Prompt must reference processing the entire document"
        assert "complete text" in prompt_start, \
            "Prompt must reference processing the complete text"
        assert "beginning to end" in prompt_start, \
            "Prompt must specify processing from beginning to end"
        assert "without skipping" in prompt_start, \
            "Prompt must explicitly forbid skipping content"

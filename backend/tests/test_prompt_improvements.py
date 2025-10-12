"""
Test suite for Phase 1 Prompt Improvements
Tests the improved Gemini prompt for French novel sentence rewriting.
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


class TestPhase1PromptImprovements:
    """Test cases for Phase 1 prompt improvements"""

    @patch('google.genai.Client')
    def test_prompt_includes_grammatical_rules(self, mock_client, app_context):
        """Test that prompt includes linguistic rewriting requirements"""
        with app_context.test_request_context():
            prompt = GeminiService(sentence_length_limit=8).build_prompt()

            # Verify key components for linguistic rewriting (not segmentation)
            assert "French linguistic expert" in prompt
            assert "ZERO TOLERANCE FOR FRAGMENTS" in prompt
            assert "REWRITE and PARAPHRASE" in prompt
            assert "linguistically complete" in prompt
            assert "FORBIDDEN OUTPUT PATTERNS" in prompt
            assert "sentence fragments" in prompt
            assert "dependent clauses" in prompt
            assert "incomplete thoughts" in prompt
            assert "REWRITING STRATEGY" in prompt
            assert "IDENTIFY the core propositions" in prompt
            assert "EXTRACT each proposition" in prompt
            assert "ADD subjects/verbs/complements" in prompt
            assert "PARAPHRASE to simplify" in prompt
            assert "VERIFY each output sentence is grammatically independent" in prompt
            assert "GRAMMATICAL REQUIREMENTS" in prompt
            assert "Must have a SUBJECT" in prompt
            assert "Must have a CONJUGATED VERB" in prompt
            assert "Must express a COMPLETE THOUGHT" in prompt
            assert "Must be able to stand alone with ZERO context" in prompt
            assert "FRAGMENT DETECTION TEST" in prompt
            assert "JSON object" in prompt
            assert "VALIDATION CHECKLIST" in prompt

    @patch('google.genai.Client')
    def test_prompt_forbids_segmentation(self, mock_client, app_context):
        """Test that prompt explicitly forbids simple splitting/segmentation"""
        with app_context.test_request_context():
            prompt = GeminiService(sentence_length_limit=8).build_prompt()

            # Verify anti-segmentation instructions
            assert "NEVER split at commas, conjunctions, or punctuation alone" in prompt
            assert "FORBIDDEN OUTPUT PATTERNS" in prompt
            assert "CORRECT OUTPUT PATTERNS" in prompt
            
            # Verify explicit examples of forbidden fragments
            assert '"le standard d\'Elvis Presley"' in prompt
            assert '"dans la rue sombre"' in prompt
            assert '"et froide"' in prompt
            assert "Pour toujours et à jamais" in prompt
            assert "Avec le temps" in prompt
            
            # Verify examples of correct complete sentences
            assert "Le standard d'Elvis Presley joue à la radio" in prompt
            assert "La rue était sombre" in prompt
            
            # Verify transformation examples
            assert "WRONG (Segmentation approach)" in prompt
            assert "CORRECT (Rewriting approach)" in prompt

    @patch('google.genai.Client')
    def test_fragment_detection(self, mock_client, app_context):
        """Test that the service can detect sentence fragments"""
        with app_context.test_request_context():
            service = GeminiService(sentence_length_limit=8)
            
            # Test cases: fragments that should be detected
            fragments = [
                "le standard d'Elvis Presley,",  # Ends with comma
                "et froide",  # Conjunction start without completion
                "dans la rue sombre",  # Prepositional phrase without verb
                "It's Now or Never,",  # Fragment ending with comma
                "Pour toujours et à jamais",  # Prepositional phrase
                "Avec le temps",  # Prepositional phrase without verb
                "Dans quinze ans",  # Temporal expression without verb
                "De retour dans la chambre",  # Participial phrase
                "mais sans elle",  # Conjunction + prepositional phrase
                "sur le fauteuil",  # Prepositional phrase
                "dans sa collection",  # Prepositional phrase
                "avec son iPod",  # Prepositional phrase
            ]
            
            for fragment in fragments:
                assert service._is_likely_fragment(fragment), \
                    f"Should detect as fragment: {fragment}"
            
            # Test cases: complete sentences that should NOT be flagged
            complete_sentences = [
                "Il marchait lentement dans la rue.",
                "La rue était sombre et froide.",
                "Elvis chante une chanson.",
                "C'est maintenant ou jamais !",
                "Le standard d'Elvis Presley joue.",
                "Il est retourné dans la chambre.",
                "Le temps passera lentement.",
                "Dans quinze ans, ce sera différent.",
            ]
            
            for sentence in complete_sentences:
                assert not service._is_likely_fragment(sentence), \
                    f"Should NOT detect as fragment: {sentence}"

    @patch('google.genai.Client')
    def test_json_output_validation(self, mock_client, app_context, tmp_path):
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

        pdf_content = b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n%%EOF"
        temp_path = tmp_path / "test_prompt.pdf"
        temp_path.write_bytes(pdf_content)

        prompt = "Test prompt"
        sentences = gemini_service.generate_content_from_pdf(prompt, str(temp_path))

        assert isinstance(sentences, list)
        assert len(sentences) == 2
        assert sentences[0] == "Première phrase."
        assert sentences[1] == "Deuxième phrase."

    @patch('google.genai.Client')
    def test_invalid_json_handling(self, mock_client, app_context, tmp_path):
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

        pdf_content = b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n%%EOF"
        temp_path = tmp_path / "test_invalid_json.pdf"
        temp_path.write_bytes(pdf_content)

        prompt = "Test prompt"
        # Now raises GeminiAPIError instead of ValueError
        from app.services.gemini_service import GeminiAPIError
        with pytest.raises(GeminiAPIError, match="Failed to parse Gemini JSON response"):
            gemini_service.generate_content_from_pdf(prompt, str(temp_path))

    @patch('google.genai.Client')
    def test_empty_response_handling(self, mock_client, app_context, tmp_path):
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

        pdf_content = b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n%%EOF"
        temp_path = tmp_path / "test_empty.pdf"
        temp_path.write_bytes(pdf_content)

        prompt = "Test prompt"
        # Now raises GeminiAPIError instead of ValueError
        from app.services.gemini_service import GeminiAPIError
        with pytest.raises(GeminiAPIError, match="Gemini returned an empty response"):
            gemini_service.generate_content_from_pdf(prompt, str(temp_path))


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

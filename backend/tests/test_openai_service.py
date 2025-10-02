import pytest
import os
import sys
import json
from unittest.mock import MagicMock, patch
from flask import Flask

# Add the backend directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.services.openai_service import OpenAIService
from config import Config


# Mock Flask current_app for testing services
@pytest.fixture
def app_context():
    app = Flask(__name__)
    app.config.from_object(Config)
    # Set a dummy OpenAI API key for testing
    app.config['OPENAI_API_KEY'] = 'test-api-key'
    app.config['OPENAI_MAX_RETRIES'] = 3
    app.config['OPENAI_TIMEOUT'] = 60
    with app.app_context():
        yield app


@patch('app.services.openai_service.OpenAI')
def test_openai_service_initialization(mock_openai_client, app_context):
    """Test OpenAI service initialization with different model preferences"""
    # Mock the OpenAI client instance
    mock_client_instance = MagicMock()
    mock_openai_client.return_value = mock_client_instance
    
    # Test balanced mode
    service = OpenAIService(model_preference='balanced')
    assert service.model_name == 'gpt-4o-mini'
    
    # Test quality mode
    service = OpenAIService(model_preference='quality')
    assert service.model_name == 'gpt-4o'
    
    # Test speed mode
    service = OpenAIService(model_preference='speed')
    assert service.model_name == 'gpt-3.5-turbo'


@patch('app.services.openai_service.OpenAI')
def test_openai_service_build_prompt(mock_openai_client, app_context):
    """Test prompt building with different options"""
    # Mock the OpenAI client instance
    mock_client_instance = MagicMock()
    mock_openai_client.return_value = mock_client_instance
    
    service = OpenAIService(
        sentence_length_limit=12,
        ignore_dialogue=True,
        preserve_formatting=True,
        fix_hyphenation=True,
        min_sentence_length=3
    )
    
    prompt = service.build_prompt()
    
    # Check that key elements are in the prompt
    assert "12 words" in prompt
    assert "literary assistant" in prompt
    assert "French novels" in prompt
    assert "JSON object" in prompt
    assert "sentences" in prompt
    assert "Dialogue Handling" in prompt
    assert "Hyphenation" in prompt


@patch('app.services.openai_service.OpenAI')
def test_openai_service_generate_content_success(mock_openai_client, app_context, tmp_path):
    """Test successful content generation from PDF"""
    # Create a temporary PDF file
    pdf_file = tmp_path / "test.pdf"
    pdf_content = b"%PDF-1.4\nTest PDF content"
    pdf_file.write_bytes(pdf_content)
    
    # Mock OpenAI response
    mock_response = MagicMock()
    mock_message = MagicMock()
    mock_message.content = '{"sentences": ["Première phrase.", "Deuxième phrase."]}'
    mock_response.choices = [MagicMock(message=mock_message)]
    
    mock_client_instance = MagicMock()
    mock_client_instance.chat.completions.create.return_value = mock_response
    mock_openai_client.return_value = mock_client_instance
    
    # Test the service
    service = OpenAIService()
    prompt = "Test prompt"
    sentences = service.generate_content_from_pdf(prompt, str(pdf_file))
    
    # Verify results
    assert len(sentences) == 2
    assert sentences[0] == "Première phrase."
    assert sentences[1] == "Deuxième phrase."
    
    # Verify API was called
    mock_client_instance.chat.completions.create.assert_called_once()


@patch('app.services.openai_service.OpenAI')
def test_openai_service_generate_content_with_json_markers(mock_openai_client, app_context, tmp_path):
    """Test content generation with JSON code block markers"""
    pdf_file = tmp_path / "test.pdf"
    pdf_file.write_bytes(b"%PDF-1.4\nTest PDF content")
    
    # Mock response with JSON markers
    mock_response = MagicMock()
    mock_message = MagicMock()
    mock_message.content = '```json\n{"sentences": ["Sentence 1", "Sentence 2"]}\n```'
    mock_response.choices = [MagicMock(message=mock_message)]
    
    mock_client_instance = MagicMock()
    mock_client_instance.chat.completions.create.return_value = mock_response
    mock_openai_client.return_value = mock_client_instance
    
    service = OpenAIService()
    sentences = service.generate_content_from_pdf("test", str(pdf_file))
    
    assert len(sentences) == 2
    assert sentences[0] == "Sentence 1"


@patch('app.services.openai_service.OpenAI')
def test_openai_service_empty_response_error(mock_openai_client, app_context, tmp_path):
    """Test error handling for empty response (with retry)"""
    pdf_file = tmp_path / "test.pdf"
    pdf_file.write_bytes(b"%PDF-1.4\nTest PDF content")
    
    # Mock empty response
    mock_response = MagicMock()
    mock_message = MagicMock()
    mock_message.content = ""
    mock_response.choices = [MagicMock(message=mock_message)]
    
    mock_client_instance = MagicMock()
    mock_client_instance.chat.completions.create.return_value = mock_response
    mock_openai_client.return_value = mock_client_instance
    
    service = OpenAIService()
    
    # The retry decorator will retry 3 times, so we expect either ValueError or RetryError
    with pytest.raises(Exception):  # Accept either ValueError or RetryError
        service.generate_content_from_pdf("test", str(pdf_file))


@patch('app.services.openai_service.OpenAI')
def test_openai_service_invalid_json_error(mock_openai_client, app_context, tmp_path):
    """Test error handling for invalid JSON response (with retry)"""
    pdf_file = tmp_path / "test.pdf"
    pdf_file.write_bytes(b"%PDF-1.4\nTest PDF content")
    
    # Mock invalid JSON response
    mock_response = MagicMock()
    mock_message = MagicMock()
    mock_message.content = "This is not valid JSON"
    mock_response.choices = [MagicMock(message=mock_message)]
    
    mock_client_instance = MagicMock()
    mock_client_instance.chat.completions.create.return_value = mock_response
    mock_openai_client.return_value = mock_client_instance
    
    service = OpenAIService()
    
    # The retry decorator will retry 3 times, so we expect either ValueError or RetryError
    with pytest.raises(Exception):  # Accept either ValueError or RetryError
        service.generate_content_from_pdf("test", str(pdf_file))


@patch('app.services.openai_service.OpenAI')
def test_openai_service_missing_sentences_key(mock_openai_client, app_context, tmp_path):
    """Test error handling when sentences key is missing (with retry)"""
    pdf_file = tmp_path / "test.pdf"
    pdf_file.write_bytes(b"%PDF-1.4\nTest PDF content")
    
    # Mock response without sentences key
    mock_response = MagicMock()
    mock_message = MagicMock()
    mock_message.content = '{"results": ["Not a sentence list"]}'
    mock_response.choices = [MagicMock(message=mock_message)]
    
    mock_client_instance = MagicMock()
    mock_client_instance.chat.completions.create.return_value = mock_response
    mock_openai_client.return_value = mock_client_instance
    
    service = OpenAIService()
    
    # The retry decorator will retry 3 times, so we expect either ValueError or RetryError
    with pytest.raises(Exception):  # Accept either ValueError or RetryError
        service.generate_content_from_pdf("test", str(pdf_file))


@patch('app.services.openai_service.OpenAI')
def test_openai_service_empty_sentences_list(mock_openai_client, app_context, tmp_path):
    """Test error handling for empty sentences list (with retry)"""
    pdf_file = tmp_path / "test.pdf"
    pdf_file.write_bytes(b"%PDF-1.4\nTest PDF content")
    
    # Mock response with empty sentences
    mock_response = MagicMock()
    mock_message = MagicMock()
    mock_message.content = '{"sentences": []}'
    mock_response.choices = [MagicMock(message=mock_message)]
    
    mock_client_instance = MagicMock()
    mock_client_instance.chat.completions.create.return_value = mock_response
    mock_openai_client.return_value = mock_client_instance
    
    service = OpenAIService()
    
    # The retry decorator will retry 3 times, so we expect either ValueError or RetryError
    with pytest.raises(Exception):  # Accept either ValueError or RetryError
        service.generate_content_from_pdf("test", str(pdf_file))

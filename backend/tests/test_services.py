import pytest
import os
import sys
import json
from unittest.mock import MagicMock, patch
from werkzeug.datastructures import FileStorage
from io import BytesIO
from flask import Flask

# Add the backend directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.services.pdf_service import PDFService
from app.services.gemini_service import GeminiService
from app.services.user_settings_service import UserSettingsService
from config import Config

# Mock Flask current_app for testing services
@pytest.fixture
def app_context():
    app = Flask(__name__)
    app.config.from_object(Config)
    with app.app_context():
        yield app

@pytest.fixture
def mock_pdf_file():
    # Create a dummy PDF file in memory
    pdf_content = b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj 2 0 obj<</Type/Pages/Count 1/Kids[3 0 R]>>endobj 3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R/Contents 4 0 R>>endobj 4 0 obj<</Length 11>>stream\nBT/F1 12 Tf 72 720 Td(Hello World)ET\nendstream\nendobj\nxref\n0 5\n0000000000 65535 f\n0000000009 00000 n\n0000000059 00000 n\n0000000111 00000 n\n0000000200 00000 n\ntrailer<</Size 5/Root 1 0 R>>startxref 220\n%%EOF"
    return FileStorage(BytesIO(pdf_content), filename='test.pdf', content_type='application/pdf')

def test_pdf_service_save_and_delete_temp_file(mock_pdf_file):
    pdf_service = PDFService(mock_pdf_file)
    temp_path = pdf_service.save_to_temp()
    assert os.path.exists(temp_path)
    pdf_service.delete_temp_file()
    assert not os.path.exists(temp_path)

@patch('google.generativeai.upload_file')
@patch('google.generativeai.delete_file')
@patch('google.generativeai.GenerativeModel')
def test_gemini_service_upload_delete_and_generate_content(mock_generative_model, mock_delete_file, mock_upload_file, app_context):
    mock_gemini_file = MagicMock()
    mock_gemini_file.name = "files/mock_file_id"
    mock_upload_file.return_value = mock_gemini_file

    mock_response = MagicMock()
    mock_response.text = '```json\n{"sentences": ["Sentence 1", "Sentence 2"]}\n```'
    mock_generative_model.return_value.generate_content.return_value = mock_response

    gemini_service = GeminiService()

    # Test upload
    uploaded_file = gemini_service.upload_file("dummy_path.pdf", "dummy.pdf")
    mock_upload_file.assert_called_once_with(path="dummy_path.pdf", display_name="dummy.pdf")
    assert uploaded_file == mock_gemini_file

    # Test generate content
    prompt = "test prompt"
    sentences = gemini_service.generate_content(prompt, uploaded_file)
    mock_generative_model.return_value.generate_content.assert_called_once()
    assert sentences == ["Sentence 1", "Sentence 2"]

    # Test delete
    gemini_service.delete_file(uploaded_file.name)
    mock_delete_file.assert_called_once_with(uploaded_file.name)

@pytest.fixture
def mock_settings_file(tmp_path):
    settings_path = tmp_path / "user_settings.json"
    with open(settings_path, 'w') as f:
        json.dump({'sentence_length_limit': 10}, f)
    return settings_path

def test_user_settings_service(app_context, mock_settings_file):
    # Create the service and override its settings_file path
    settings_service = UserSettingsService()
    settings_service.settings_file = str(mock_settings_file)

    # Test get_settings
    settings = settings_service.get_settings()
    assert settings == {'sentence_length_limit': 10}

    # Test save_settings
    new_settings = {'sentence_length_limit': 15}
    settings_service.save_settings(new_settings)
    updated_settings = settings_service.get_settings()
    assert updated_settings == {'sentence_length_limit': 15}

import pytest
import os
import sys
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
    # Create a properly formatted dummy PDF file in memory
    pdf_content = b"""%PDF-1.4
1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj
2 0 obj<</Type/Pages/Count 1/Kids[3 0 R]>>endobj
3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R/Contents 4 0 R>>endobj
4 0 obj<</Length 44>>stream
BT
/F1 12 Tf
72 720 Td
(Hello World) Tj
ET
endstream
endobj
xref
0 5
0000000000 65535 f 
0000000009 00000 n 
0000000052 00000 n 
0000000101 00000 n 
0000000181 00000 n 
trailer<</Size 5/Root 1 0 R>>
startxref
273
%%EOF"""
    return FileStorage(BytesIO(pdf_content), filename='test.pdf', content_type='application/pdf')

def test_pdf_service_save_and_delete_temp_file(mock_pdf_file):
    pdf_service = PDFService(mock_pdf_file)
    temp_path = pdf_service.save_to_temp()
    assert os.path.exists(temp_path)
    pdf_service.delete_temp_file()
    assert not os.path.exists(temp_path)


def test_pdf_service_get_page_count(mock_pdf_file):
    """Test metadata-only page count extraction"""
    pdf_service = PDFService(mock_pdf_file)
    
    metadata = pdf_service.get_page_count()
    
    assert 'page_count' in metadata
    assert 'file_size' in metadata
    assert 'image_count' in metadata
    assert metadata['page_count'] == 1  # Mock PDF has 1 page
    assert metadata['file_size'] > 0
    assert isinstance(metadata['image_count'], int)


def test_pdf_service_get_page_count_with_stream():
    """Test get_page_count with a file stream"""
    from io import BytesIO
    
    # Create a minimal valid PDF with 2 pages
    pdf_content = b"""%PDF-1.4
1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj
2 0 obj<</Type/Pages/Count 2/Kids[3 0 R 4 0 R]>>endobj
3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R>>endobj
4 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R>>endobj
xref
0 5
0000000000 65535 f 
0000000009 00000 n 
0000000052 00000 n 
0000000110 00000 n 
0000000170 00000 n 
trailer<</Size 5/Root 1 0 R>>
startxref
230
%%EOF"""
    
    stream = BytesIO(pdf_content)
    pdf_service = PDFService(None)  # No file in constructor
    
    metadata = pdf_service.get_page_count(file_stream=stream)
    
    assert metadata['page_count'] == 2
    assert metadata['file_size'] > 0


def test_pdf_service_get_page_count_corrupted_pdf():
    """Test get_page_count with corrupted PDF"""
    from io import BytesIO
    
    # Create invalid PDF content
    invalid_content = b"Not a valid PDF file"
    stream = BytesIO(invalid_content)
    
    pdf_service = PDFService(None)
    
    with pytest.raises(RuntimeError, match="Invalid or corrupted PDF"):
        pdf_service.get_page_count(file_stream=stream)


@patch('app.services.gemini_service.genai.Client')
def test_gemini_service_prompt_includes_phase1_sections(mock_client, app_context):
    """Ensure the Gemini prompt contains the advanced literary guidance."""
    gemini_service = GeminiService(sentence_length_limit=8)
    prompt = gemini_service.build_prompt()

    assert "extract and process every single sentence" in prompt.lower()
    assert f"{gemini_service.sentence_length_limit} words" in prompt
    assert "**Rewriting Rules:**" in prompt
    assert "**Context-Awareness:**" in prompt
    assert "**Dialogue Handling:**" in prompt
    assert "**Style and Tone Preservation:**" in prompt
    assert "**Hyphenation & Formatting:**" in prompt
    assert "merge it with the previous or next sentence" in prompt
    assert '"sentences"' in prompt


@patch('app.services.gemini_service.genai.Client')
def test_gemini_service_initialization_basic(mock_client, app_context):
    """Test GeminiService initializes with only basic parameters"""
    service = GeminiService(sentence_length_limit=10)
    
    assert service.sentence_length_limit == 10
    assert service.model_name == GeminiService.MODEL_PREFERENCE_MAP['balanced']
    assert service.ignore_dialogue is False
    assert service.preserve_formatting is True
    assert service.fix_hyphenation is True
    assert service.min_sentence_length == 2


# NOTE: This test is disabled as it uses the old API that was replaced
# The new API uses generate_content_from_pdf with inline data
@patch('google.generativeai.upload_file')
@patch('google.generativeai.delete_file')
@patch('google.generativeai.GenerativeModel')
def _disabled_test_gemini_service_upload_delete_and_generate_content(mock_generative_model, mock_delete_file, mock_upload_file, app_context):
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

@patch('app.services.user_settings_service.UserSettings')
@patch('app.services.user_settings_service.db')
def test_user_settings_service(mock_db, mock_user_settings, app_context):
    defaults = {
        'sentence_length_limit': 8,
        'gemini_model': 'balanced',
        'ignore_dialogue': False,
        'preserve_formatting': True,
        'fix_hyphenation': True,
        'min_sentence_length': 2,
    }

    existing_settings = MagicMock()
    existing_settings.to_dict.return_value = defaults.copy()
    existing_settings.sentence_length_limit = defaults['sentence_length_limit']
    existing_settings.gemini_model = defaults['gemini_model']
    existing_settings.ignore_dialogue = defaults['ignore_dialogue']
    existing_settings.preserve_formatting = defaults['preserve_formatting']
    existing_settings.fix_hyphenation = defaults['fix_hyphenation']
    existing_settings.min_sentence_length = defaults['min_sentence_length']

    mock_query = MagicMock()
    mock_query.filter_by.return_value.first.return_value = existing_settings
    mock_user_settings.query = mock_query

    service = UserSettingsService()

    settings = service.get_user_settings(user_id=1)
    assert settings == defaults

    service.save_user_settings(1, {'sentence_length_limit': 12, 'ignore_dialogue': True})

    assert existing_settings.sentence_length_limit == 12
    assert existing_settings.ignore_dialogue is True
    mock_db.session.commit.assert_called()

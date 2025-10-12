"""Tests for P1 backend features."""
import pytest
import os
import sys
import json
from unittest.mock import MagicMock, patch
from flask import Flask

# Add the backend directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.services.gemini_service import GeminiService
from app.services.google_sheets_service import GoogleSheetsService
from app.schemas import ExportToSheetSchema, UserSettingsSchema, ProcessPdfOptionsSchema
from marshmallow import ValidationError
from config import Config


@pytest.fixture
def app_context():
    """Create Flask app context for testing"""
    app = Flask(__name__)
    app.config.from_object(Config)
    with app.app_context():
        yield app


class TestGeminiServiceP1Features:
    """Test advanced normalization features in GeminiService"""
    
    @patch('app.services.gemini_service.genai.Client')
    def test_gemini_service_initialization_with_advanced_options(self, mock_client, app_context):
        """Test GeminiService initializes with P1 advanced options"""
        service = GeminiService(
            sentence_length_limit=12,
            model_preference='quality',
            ignore_dialogue=True,
            preserve_formatting=False,
            fix_hyphenation=True,
            min_sentence_length=5
        )
        
        assert service.sentence_length_limit == 12
        assert service.model_name == 'gemini-2.5-pro'  # quality maps to this
        assert service.ignore_dialogue is True
        assert service.preserve_formatting is False
        assert service.fix_hyphenation is True
        assert service.min_sentence_length == 5
    
    @patch('app.services.gemini_service.genai.Client')
    def test_gemini_model_mapping(self, mock_client, app_context):
        """Test model preference mapping"""
        balanced_service = GeminiService(model_preference='balanced')
        quality_service = GeminiService(model_preference='quality')
        speed_service = GeminiService(model_preference='speed')

        assert balanced_service.model_name == 'gemini-2.5-flash'
        assert quality_service.model_name == 'gemini-2.5-pro'
        assert speed_service.model_name == 'gemini-2.5-flash-lite'
    
    @patch('app.services.gemini_service.genai.Client')
    def test_build_prompt_with_ignore_dialogue(self, mock_client, app_context):
        """Test prompt building with ignore_dialogue option"""
        service = GeminiService(
            sentence_length_limit=10,
            ignore_dialogue=True
        )
        prompt = service.build_prompt()
        
        assert 'keep it as-is without splitting' in prompt
        assert 'regardless of length' in prompt
    
    @patch('app.services.gemini_service.genai.Client')
    def test_build_prompt_without_ignore_dialogue(self, mock_client, app_context):
        """Test prompt building without ignore_dialogue option"""
        service = GeminiService(
            sentence_length_limit=10,
            ignore_dialogue=False
        )
        prompt = service.build_prompt()
        
        assert 'Do not split it unless absolutely necessary' in prompt
    
    @patch('app.services.gemini_service.genai.Client')
    def test_build_prompt_with_min_sentence_length(self, mock_client, app_context):
        """Test prompt building with minimum sentence length"""
        service = GeminiService(
            sentence_length_limit=10,
            min_sentence_length=5
        )
        prompt = service.build_prompt()
        
        assert 'shorter than 5 words' in prompt
        assert 'merge it with the previous or next sentence' in prompt
    
    @patch('app.services.gemini_service.genai.Client')
    def test_build_prompt_with_preserve_formatting(self, mock_client, app_context):
        """Test prompt building with preserve_formatting option"""
        service = GeminiService(
            sentence_length_limit=10,
            preserve_formatting=True
        )
        prompt = service.build_prompt()
        
        assert 'Preserve the original quotation marks' in prompt
        assert 'Keep the literary formatting intact' in prompt
    
    @patch('app.services.gemini_service.genai.Client')
    def test_build_prompt_with_fix_hyphenation(self, mock_client, app_context):
        """Test prompt building with fix_hyphenation option"""
        service = GeminiService(
            sentence_length_limit=10,
            fix_hyphenation=True
        )
        prompt = service.build_prompt()
        
        assert 'Hyphenation' in prompt
        assert 'rejoin them into a single word' in prompt


class TestExportToSheetSchema:
    """Test export schema validation with P1 features"""
    
    def test_basic_export_schema(self):
        """Test basic export schema validation"""
        schema = ExportToSheetSchema()
        data = {
            'sentences': ['Test sentence 1', 'Test sentence 2'],
            'sheetName': 'Test Sheet'
        }
        result = schema.load(data)
        
        assert result['sentences'] == data['sentences']
        assert result['sheetName'] == data['sheetName']
        assert result['mode'] == 'new'  # default value
    
    def test_append_mode_schema(self):
        """Test append mode export schema"""
        schema = ExportToSheetSchema()
        data = {
            'sentences': ['Test sentence 1'],
            'sheetName': 'Not used',
            'mode': 'append',
            'existingSheetId': '1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms',
            'tabName': 'Chapter 2',
            'createNewTab': True
        }
        result = schema.load(data)
        
        assert result['mode'] == 'append'
        assert result['existingSheetId'] == data['existingSheetId']
        assert result['tabName'] == data['tabName']
        assert result['createNewTab'] is True
    
    def test_sharing_settings_schema(self):
        """Test sharing settings in export schema"""
        schema = ExportToSheetSchema()
        data = {
            'sentences': ['Test'],
            'sheetName': 'Test',
            'sharing': {
                'addCollaborators': True,
                'collaboratorEmails': ['user@example.com', 'other@example.com'],
                'publicLink': False
            }
        }
        result = schema.load(data)
        
        assert result['sharing']['addCollaborators'] is True
        assert len(result['sharing']['collaboratorEmails']) == 2
        assert result['sharing']['publicLink'] is False
    
    def test_sentence_indices_schema(self):
        """Test sentence indices in export schema"""
        schema = ExportToSheetSchema()
        data = {
            'sentences': ['Test 1', 'Test 2', 'Test 3'],
            'sheetName': 'Test',
            'sentenceIndices': [0, 2]
        }
        result = schema.load(data)
        
        assert result['sentenceIndices'] == [0, 2]
    
    def test_invalid_mode_schema(self):
        """Test invalid mode validation"""
        schema = ExportToSheetSchema()
        data = {
            'sentences': ['Test'],
            'sheetName': 'Test',
            'mode': 'invalid_mode'
        }
        
        with pytest.raises(ValidationError) as exc_info:
            schema.load(data)
        
        assert 'mode' in exc_info.value.messages
    
    def test_folder_id_schema(self):
        """Test folder_id in export schema"""
        schema = ExportToSheetSchema()
        data = {
            'sentences': ['Test sentence'],
            'sheetName': 'Test Sheet',
            'folderId': '1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms'
        }
        result = schema.load(data)
        
        assert result['folderId'] == data['folderId']
        assert result['mode'] == 'new'
    
    def test_folder_id_null_schema(self):
        """Test null folder_id in export schema"""
        schema = ExportToSheetSchema()
        data = {
            'sentences': ['Test sentence'],
            'sheetName': 'Test Sheet',
            'folderId': None
        }
        result = schema.load(data)
        
        assert result['folderId'] is None



class TestUserSettingsSchema:
    """Test user settings schema with P1 features"""
    
    def test_basic_settings_schema(self):
        """Test basic settings schema validation"""
        schema = UserSettingsSchema()
        data = {
            'sentence_length_limit': 12
        }
        result = schema.load(data)
        
        assert result['sentence_length_limit'] == 12
        assert result['gemini_model'] == 'speed'  # default (changed from balanced)
        assert result['ignore_dialogue'] is False  # default
    
    def test_full_settings_schema(self):
        """Test full settings with P1 options"""
        schema = UserSettingsSchema()
        data = {
            'sentence_length_limit': 15,
            'gemini_model': 'quality',
            'ignore_dialogue': True,
            'preserve_formatting': False,
            'fix_hyphenation': True,
            'min_sentence_length': 5
        }
        result = schema.load(data)
        
        assert result['sentence_length_limit'] == 15
        assert result['gemini_model'] == 'quality'
        assert result['ignore_dialogue'] is True
        assert result['preserve_formatting'] is False
        assert result['fix_hyphenation'] is True
        assert result['min_sentence_length'] == 5
    
    def test_invalid_gemini_model(self):
        """Test invalid gemini_model validation"""
        schema = UserSettingsSchema()
        data = {
            'sentence_length_limit': 10,
            'gemini_model': 'ultra_fast'
        }
        
        with pytest.raises(ValidationError) as exc_info:
            schema.load(data)
        
        assert 'gemini_model' in exc_info.value.messages
    
    def test_invalid_sentence_length_limit(self):
        """Test invalid sentence_length_limit validation"""
        schema = UserSettingsSchema()
        data = {
            'sentence_length_limit': 100  # Too large
        }
        
        with pytest.raises(ValidationError) as exc_info:
            schema.load(data)
        
        assert 'sentence_length_limit' in exc_info.value.messages


class TestProcessPdfOptionsSchema:
    """Test process PDF options schema"""
    
    def test_basic_options_schema(self):
        """Test basic process PDF options"""
        schema = ProcessPdfOptionsSchema()
        data = {
            'sentence_length_limit': 10,
            'gemini_model': 'balanced'
        }
        result = schema.load(data)
        
        assert result['sentence_length_limit'] == 10
        assert result['gemini_model'] == 'balanced'
    
    def test_empty_options_schema(self):
        """Test empty process PDF options (all optional)"""
        schema = ProcessPdfOptionsSchema()
        data = {}
        result = schema.load(data)
        
        # Should succeed with empty data since all fields are optional
        assert result == {}


class TestGoogleSheetsServiceP1Features:
    """Test Google Sheets service with P1 features"""
    
    @patch('app.services.google_sheets_service.build')
    def test_export_with_sentence_indices(self, mock_build):
        """Test exporting only selected sentences"""
        # Mock the Google API clients
        mock_sheets = MagicMock()
        mock_drive = MagicMock()
        mock_build.side_effect = [mock_sheets, mock_drive]
        
        # Mock credentials
        mock_creds = MagicMock()
        
        # Setup spreadsheet creation mock
        mock_spreadsheet = {'spreadsheetId': 'test123'}
        mock_sheets.spreadsheets().create().execute.return_value = mock_spreadsheet
        
        service = GoogleSheetsService()
        sentences = ['Sentence 1', 'Sentence 2', 'Sentence 3', 'Sentence 4']
        
        # Export only indices 0 and 2
        url = service.export_to_sheet(
            creds=mock_creds,
            sentences=sentences,
            sheet_name='Test',
            sentence_indices=[0, 2]
        )
        
        # Verify the values update was called
        assert mock_sheets.spreadsheets().values().update.called
        
        # Get the call arguments
        call_args = mock_sheets.spreadsheets().values().update.call_args
        values_body = call_args[1]['body']['values']
        
        # Should have header + 2 sentences
        assert len(values_body) == 3  # header + 2 sentences
        assert values_body[1][1] == 'Sentence 1'
        assert values_body[2][1] == 'Sentence 3'
        
        assert url == 'https://docs.google.com/spreadsheets/d/test123'
    
    @patch('app.services.google_sheets_service.build')
    def test_export_with_folder_id(self, mock_build):
        """Test exporting to a specific folder"""
        # Mock the Google API clients
        mock_sheets = MagicMock()
        mock_drive = MagicMock()
        mock_build.side_effect = [mock_sheets, mock_drive]
        
        # Mock credentials
        mock_creds = MagicMock()
        
        # Setup spreadsheet creation mock
        mock_spreadsheet = {'spreadsheetId': 'test123'}
        mock_sheets.spreadsheets().create().execute.return_value = mock_spreadsheet
        
        # Setup drive file mock
        mock_file = {'parents': ['root']}
        mock_drive.files().get().execute.return_value = mock_file
        
        service = GoogleSheetsService()
        sentences = ['Test sentence']
        folder_id = '1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms'
        
        # Export with folder_id
        url = service.export_to_sheet(
            creds=mock_creds,
            sentences=sentences,
            sheet_name='Test Sheet',
            folder_id=folder_id
        )
        
        # Verify the drive update was called to move the file
        assert mock_drive.files().update.called
        
        # Get the call arguments for the update
        call_args = mock_drive.files().update.call_args
        assert call_args[1]['fileId'] == 'test123'
        assert call_args[1]['addParents'] == folder_id
        assert 'removeParents' in call_args[1]
        
        assert url == 'https://docs.google.com/spreadsheets/d/test123'
    
    @patch('app.services.google_sheets_service.build')
    def test_export_without_folder_id(self, mock_build):
        """Test exporting without folder_id (default location)"""
        # Mock the Google API clients
        mock_sheets = MagicMock()
        mock_drive = MagicMock()
        mock_build.side_effect = [mock_sheets, mock_drive]
        
        # Mock credentials
        mock_creds = MagicMock()
        
        # Setup spreadsheet creation mock
        mock_spreadsheet = {'spreadsheetId': 'test123'}
        mock_sheets.spreadsheets().create().execute.return_value = mock_spreadsheet
        
        service = GoogleSheetsService()
        sentences = ['Test sentence']
        
        # Export without folder_id
        url = service.export_to_sheet(
            creds=mock_creds,
            sentences=sentences,
            sheet_name='Test Sheet'
        )
        
        # Verify the drive update was NOT called
        assert not mock_drive.files().update.called
        
        assert url == 'https://docs.google.com/spreadsheets/d/test123'



if __name__ == '__main__':
    pytest.main([__file__, '-v'])

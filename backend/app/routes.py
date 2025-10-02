"""API routes for the French Novel Tool"""
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from marshmallow import ValidationError
from app import limiter
from .services.pdf_service import PDFService
from .services.gemini_service import GeminiService
from .services.openai_service import OpenAIService
from .services.google_sheets_service import GoogleSheetsService
from .services.history_service import HistoryService
from .services.user_settings_service import UserSettingsService
from .schemas import ExportToSheetSchema, UserSettingsSchema
from .utils.validators import validate_pdf_file
from .models import User

main_bp = Blueprint('main', __name__)
history_service = HistoryService()
user_settings_service = UserSettingsService()

# Initialize schemas
export_schema = ExportToSheetSchema()
settings_schema = UserSettingsSchema()


@main_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint for monitoring and load balancers"""
    from app.constants import API_VERSION, API_SERVICE_NAME
    return jsonify({
        'status': 'healthy',
        'service': API_SERVICE_NAME,
        'version': API_VERSION
    }), 200

@main_bp.route('/process-pdf', methods=['POST'])
@jwt_required()
@limiter.limit("10 per hour")
def process_pdf():
    """Process PDF file and extract/normalize sentences (requires authentication)"""
    # Get current user
    user_id = int(get_jwt_identity())  # Convert string to int
    user = User.query.get(user_id)
    
    if not user or not user.is_active:
        return jsonify({'error': 'User not found or inactive'}), 401
    
    if 'pdf_file' not in request.files:
        return jsonify({'error': 'No PDF file provided'}), 400

    file = request.files['pdf_file']
    original_filename = file.filename
    
    # Validate file
    try:
        validate_pdf_file(file)
    except ValidationError as e:
        return jsonify({'error': str(e)}), 400

    pdf_service = PDFService(file)
    ai_service = None

    try:
        temp_file_path = pdf_service.save_to_temp()

        # Get user-specific settings
        settings = user_settings_service.get_user_settings(user_id)
        
        # Override with request parameters if provided
        form_data = request.form
        sentence_length_limit = int(form_data.get('sentence_length_limit', settings.get('sentence_length_limit', 8)))
        ai_provider = form_data.get('ai_provider', settings.get('ai_provider', 'gemini'))
        gemini_model = form_data.get('gemini_model', settings.get('gemini_model', 'balanced'))
        ignore_dialogue = form_data.get('ignore_dialogue', str(settings.get('ignore_dialogue', False))).lower() == 'true'
        preserve_formatting = form_data.get('preserve_formatting', str(settings.get('preserve_formatting', True))).lower() == 'true'
        fix_hyphenation = form_data.get('fix_hyphenation', str(settings.get('fix_hyphenation', True))).lower() == 'true'
        min_sentence_length = int(form_data.get('min_sentence_length', settings.get('min_sentence_length', 3)))

        # Store processing settings for history
        processing_settings = {
            'sentence_length_limit': sentence_length_limit,
            'ai_provider': ai_provider,
            'gemini_model': gemini_model,
            'ignore_dialogue': ignore_dialogue,
            'preserve_formatting': preserve_formatting,
            'fix_hyphenation': fix_hyphenation,
            'min_sentence_length': min_sentence_length
        }

        # Select AI service based on provider
        if ai_provider == 'openai':
            if not current_app.config.get('OPENAI_API_KEY'):
                return jsonify({'error': 'OpenAI API key not configured'}), 500
                
            ai_service = OpenAIService(
                sentence_length_limit=sentence_length_limit,
                model_preference=gemini_model,  # Using same model preference keys
                ignore_dialogue=ignore_dialogue,
                preserve_formatting=preserve_formatting,
                fix_hyphenation=fix_hyphenation,
                min_sentence_length=min_sentence_length
            )
        else:  # Default to Gemini
            if not current_app.config.get('GEMINI_API_KEY'):
                return jsonify({'error': 'Gemini API key not configured'}), 500
                
            ai_service = GeminiService(
                sentence_length_limit=sentence_length_limit,
                model_preference=gemini_model,
                ignore_dialogue=ignore_dialogue,
                preserve_formatting=preserve_formatting,
                fix_hyphenation=fix_hyphenation,
                min_sentence_length=min_sentence_length
            )

        # Use the built-in prompt builder
        prompt = ai_service.build_prompt()

        processed_sentences = ai_service.generate_content_from_pdf(prompt, temp_file_path)

        # Add user-specific history entry with processing settings
        history_service.add_entry(
            user_id=user_id,
            original_filename=original_filename,
            processed_sentences_count=len(processed_sentences),
            error_message=None,
            processing_settings=processing_settings
        )

        current_app.logger.info(f'User {user.email} processed PDF: {original_filename}')
        return jsonify({'sentences': processed_sentences})

    except Exception as e:
        error_message = str(e)
        current_app.logger.exception(f'User {user.email} failed to process PDF {original_filename}')
        
        # Determine error code and failed step
        error_code = 'PROCESSING_ERROR'
        failed_step = 'normalize'
        
        if 'Gemini' in error_message or 'OpenAI' in error_message or 'API' in error_message:
            error_code = 'AI_API_ERROR'
        elif 'PDF' in error_message:
            error_code = 'INVALID_PDF'
            failed_step = 'extract'
        
        # Add error to user's history
        history_service.add_entry(
            user_id=user_id,
            original_filename=original_filename,
            processed_sentences_count=0,
            error_message=error_message,
            failed_step=failed_step,
            error_code=error_code
        )
        return jsonify({'error': error_message}), 500
    finally:
        pdf_service.delete_temp_file()

@main_bp.route('/export-to-sheet', methods=['POST'])
@jwt_required()
@limiter.limit("5 per hour")
def export_to_sheet():
    """Export sentences to Google Sheets (requires authentication)"""
    user_id = int(get_jwt_identity())  # Convert string to int
    user = User.query.get(user_id)
    
    if not user or not user.is_active:
        return jsonify({'error': 'User not found or inactive'}), 401
    
    try:
        # Validate request data
        data = export_schema.load(request.json)
    except ValidationError as e:
        return jsonify({'error': 'Invalid request data', 'details': e.messages}), 400
    
    try:
        sentences = data['sentences']
        sheet_name = data['sheetName']  # camelCase from frontend
        folder_id = data.get('folderId')  # camelCase from frontend
        
        # P1 new parameters
        mode = data.get('mode', 'new')
        existing_sheet_id = data.get('existingSheetId')
        tab_name = data.get('tabName')
        create_new_tab = data.get('createNewTab', False)
        headers = data.get('headers')
        column_order = data.get('columnOrder')
        sharing = data.get('sharing')
        sentence_indices = data.get('sentenceIndices')
        
        # Check if user has authorized Google Sheets access
        if not user.google_access_token:
            return jsonify({
                'error': 'Google Sheets access not authorized. Please log out and log in again to grant permissions.'
            }), 403
        
        # Get user's Google credentials
        from app.services.auth_service import AuthService
        auth_service = AuthService()
        
        try:
            creds = auth_service.get_user_credentials(user)
        except ValueError as e:
            return jsonify({
                'error': str(e)
            }), 403
        
        # Export to Google Sheets using user's credentials
        sheets_service = GoogleSheetsService()
        spreadsheet_url = sheets_service.export_to_sheet(
            creds=creds,
            sentences=sentences,
            sheet_name=sheet_name,
            folder_id=folder_id,
            mode=mode,
            existing_sheet_id=existing_sheet_id,
            tab_name=tab_name,
            create_new_tab=create_new_tab,
            headers=headers,
            column_order=column_order,
            sharing=sharing,
            sentence_indices=sentence_indices
        )
        
        # Update history with spreadsheet URL
        # Get the most recent history entry for this user without a spreadsheet_url
        from app.models import History
        recent_entry = History.query.filter_by(
            user_id=user_id,
            spreadsheet_url=None
        ).order_by(History.timestamp.desc()).first()
        
        if recent_entry:
            recent_entry.spreadsheet_url = spreadsheet_url
            from app import db
            db.session.commit()
        
        current_app.logger.info(f'User {user.email} exported to Google Sheets: {sheet_name}')
        return jsonify({
            'message': 'Export successful',
            'spreadsheet_url': spreadsheet_url
        })
        
    except Exception as e:
        current_app.logger.exception(f'User {user.email} failed to export to Google Sheets')
        return jsonify({'error': str(e)}), 500

@main_bp.route('/history', methods=['GET'])
@jwt_required()
def get_history():
    """Get processing history for current user (requires authentication)"""
    try:
        user_id = int(get_jwt_identity())  # Convert string to int
        user = User.query.get(user_id)
        
        if not user or not user.is_active:
            return jsonify({'error': 'User not found or inactive'}), 401
        
        # Get optional limit parameter
        limit = request.args.get('limit', type=int)
        
        # Get user-specific history
        entries = history_service.get_user_entries(user_id, limit=limit)
        return jsonify([entry.to_dict() for entry in entries])
        
    except Exception as e:
        current_app.logger.exception('Failed to get history')
        return jsonify({'error': str(e)}), 500


@main_bp.route('/history/<int:entry_id>', methods=['DELETE'])
@jwt_required()
def delete_history_entry(entry_id):
    """Delete a specific history entry (requires authentication)"""
    try:
        user_id = int(get_jwt_identity())  # Convert string to int
        user = User.query.get(user_id)
        
        if not user or not user.is_active:
            return jsonify({'error': 'User not found or inactive'}), 401
        
        # Delete entry (only if it belongs to the user)
        success = history_service.delete_entry(entry_id, user_id)
        
        if success:
            current_app.logger.info(f'User {user.email} deleted history entry {entry_id}')
            return jsonify({'message': 'History entry deleted'}), 200
        else:
            return jsonify({'error': 'History entry not found'}), 404
            
    except Exception as e:
        current_app.logger.exception('Failed to delete history entry')
        return jsonify({'error': str(e)}), 500

@main_bp.route('/settings', methods=['GET', 'POST'])
@jwt_required()
def user_settings():
    """Get or update user settings (requires authentication)"""
    user_id = int(get_jwt_identity())  # Convert string to int
    user = User.query.get(user_id)
    
    if not user or not user.is_active:
        return jsonify({'error': 'User not found or inactive'}), 401
    
    if request.method == 'GET':
        try:
            # Get user-specific settings
            settings = user_settings_service.get_user_settings(user_id)
            return jsonify(settings)
        except Exception as e:
            current_app.logger.exception(f'User {user.email} failed to get settings')
            return jsonify({'error': str(e)}), 500
            
    elif request.method == 'POST':
        try:
            # Validate settings data
            data = settings_schema.load(request.json)
            
            # Save user-specific settings
            settings = user_settings_service.save_user_settings(user_id, data)
            
            current_app.logger.info(f'User {user.email} updated settings')
            return jsonify({
                'message': 'Settings saved successfully',
                'settings': settings
            })
        except ValidationError as e:
            return jsonify({'error': 'Invalid settings data', 'details': e.messages}), 400
        except Exception as e:
            current_app.logger.exception(f'User {user.email} failed to save settings')
            return jsonify({'error': str(e)}), 500


@main_bp.route('/history/<int:entry_id>/retry', methods=['POST'])
@jwt_required()
@limiter.limit("5 per hour")
def retry_history_entry(entry_id):
    """Retry processing from failed step (requires authentication)"""
    user_id = int(get_jwt_identity())
    user = User.query.get(user_id)
    
    if not user or not user.is_active:
        return jsonify({'error': 'User not found or inactive'}), 401
    
    try:
        from app.models import History
        entry = History.query.filter_by(id=entry_id, user_id=user_id).first()
        
        if not entry:
            return jsonify({'error': 'History entry not found'}), 404
        
        if not entry.failed_step:
            return jsonify({'error': 'Entry did not fail - nothing to retry'}), 400
        
        # For now, return a message that this feature requires the original file
        # In a full implementation, you would store the file or allow re-upload
        return jsonify({
            'message': 'Retry functionality requires re-uploading the PDF file',
            'entry_id': entry_id,
            'settings': entry.processing_settings
        }), 200
        
    except Exception as e:
        current_app.logger.exception(f'User {user.email} failed to retry entry {entry_id}')
        return jsonify({'error': str(e)}), 500


@main_bp.route('/history/<int:entry_id>/duplicate', methods=['POST'])
@jwt_required()
@limiter.limit("5 per hour")
def duplicate_history_entry(entry_id):
    """Duplicate a processing run with same settings (requires authentication)"""
    user_id = int(get_jwt_identity())
    user = User.query.get(user_id)
    
    if not user or not user.is_active:
        return jsonify({'error': 'User not found or inactive'}), 401
    
    try:
        from app.models import History
        entry = History.query.filter_by(id=entry_id, user_id=user_id).first()
        
        if not entry:
            return jsonify({'error': 'History entry not found'}), 404
        
        if not entry.processing_settings:
            return jsonify({'error': 'No settings found for this entry'}), 400
        
        # Return the settings so the frontend can use them
        # In a full implementation with file storage, we would automatically reprocess
        return jsonify({
            'message': 'Use these settings to process a new PDF',
            'settings': entry.processing_settings,
            'original_filename': entry.original_filename
        }), 200
        
    except Exception as e:
        current_app.logger.exception(f'User {user.email} failed to duplicate entry {entry_id}')
        return jsonify({'error': str(e)}), 500
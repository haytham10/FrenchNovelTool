"""API routes for the French Novel Tool"""
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from marshmallow import ValidationError
from app import limiter
from .services.pdf_service import PDFService
from .services.gemini_service import GeminiService
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
    gemini_service = None

    try:
        temp_file_path = pdf_service.save_to_temp()

        # Get user-specific settings
        settings = user_settings_service.get_user_settings(user_id)
        sentence_length_limit = settings.get('sentence_length_limit', 8)

        gemini_service = GeminiService(sentence_length_limit=sentence_length_limit)

        prompt = (
            "You are a literary assistant specialized in processing French novels. "
            "Your task is to list the sentences from the provided text consecutively. "
            f"If a sentence is {sentence_length_limit} words long or less, add it to the list as is. "
            f"If a sentence is longer than {sentence_length_limit} words, you must rewrite it into "
            f"shorter sentences, each with {sentence_length_limit} words or fewer. "
            "\n\n"
            "**Rewriting Rules:**\n"
            "- Split long sentences at natural grammatical breaks, such as conjunctions "
            "(e.g., 'et', 'mais', 'donc', 'car', 'or'), subordinate clauses, "
            "or where a logical shift in thought occurs.\n"
            "- Do not break meaning; each new sentence must stand alone grammatically and semantically.\n"
            "\n"
            "**Context-Awareness:**\n"
            "- Ensure the rewritten sentences maintain the logical flow and connection to the preceding text. "
            "The output must read as a continuous, coherent narrative.\n"
            "\n"
            "**Dialogue Handling:**\n"
            "- If a sentence is enclosed in quotation marks (« », \" \", or ' '), treat it as dialogue. "
            "Do not split it unless absolutely necessary. "
            "If a split is unavoidable, do so in a way that maintains the natural cadence of speech.\n"
            "\n"
            "**Style and Tone Preservation:**\n"
            "- Maintain the literary tone and style of the original text. "
            "Avoid using overly simplistic language or modern idioms that would feel out of place.\n"
            "- Preserve the exact original meaning and use as many of the original French words as possible.\n"
            "\n"
            "**Output Format:**\n"
            "Present the final output as a JSON object with a single key 'sentences' "
            "which is an array of strings. "
            f"For example: {{\"sentences\": [\"Voici la première phrase.\", \"Et voici la deuxième.\"]}}"
        )

        processed_sentences = gemini_service.generate_content_from_pdf(prompt, temp_file_path)

        # Add user-specific history entry
        history_service.add_entry(
            user_id=user_id,
            original_filename=original_filename,
            processed_sentences_count=len(processed_sentences),
            error_message=None
        )

        current_app.logger.info(f'User {user.email} processed PDF: {original_filename}')
        return jsonify({'sentences': processed_sentences})

    except Exception as e:
        error_message = str(e)
        current_app.logger.exception(f'User {user.email} failed to process PDF {original_filename}')
        
        # Add error to user's history
        history_service.add_entry(
            user_id=user_id,
            original_filename=original_filename,
            processed_sentences_count=0,
            error_message=error_message
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
            folder_id=folder_id
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
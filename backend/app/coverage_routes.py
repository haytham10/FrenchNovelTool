"""API routes for Vocabulary Coverage Tool"""
import logging
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from marshmallow import ValidationError
from app import limiter, db
from app.models import WordList, CoverageRun, CoverageAssignment, UserSettings, User
from app.services.wordlist_service import WordListService
from app.services.auth_service import AuthService
from app.services.google_sheets_service import GoogleSheetsService
from app.schemas import (
    WordListCreateSchema,
    WordListUpdateSchema,
    CoverageRunCreateSchema,
    CoverageSwapSchema,
    CoverageExportSchema
)
from app.tasks import coverage_build_async

logger = logging.getLogger(__name__)

coverage_bp = Blueprint('coverage', __name__, url_prefix='/api/v1')


# ============================================================================
# WordList Management Endpoints
# ============================================================================

@coverage_bp.route('/wordlists', methods=['GET'])
@jwt_required()
def list_wordlists():
    """List all word lists accessible to the user (global + user's own) with pagination"""
    user_id = int(get_jwt_identity())
    
    # Get pagination parameters
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    per_page = min(per_page, 100)  # Max 100 per page
    
    wordlist_service = WordListService()
    wordlists_query = wordlist_service.get_user_wordlists_query(user_id, include_global=True)
    
    # Paginate
    paginated = wordlists_query.paginate(page=page, per_page=per_page, error_out=False)
    
    return jsonify({
        'wordlists': [wl.to_dict() for wl in paginated.items],
        'pagination': {
            'page': page,
            'per_page': per_page,
            'total': paginated.total,
            'pages': paginated.pages
        }
    }), 200


@coverage_bp.route('/wordlists', methods=['POST'])
@jwt_required()
@limiter.limit("10 per hour")
def create_wordlist():
    """Create a new word list (CSV upload or manual)"""
    user_id = int(get_jwt_identity())
    
    # Handle file upload
    if 'file' in request.files:
        file = request.files['file']
        if not file or not file.filename:
            return jsonify({'error': 'No file provided'}), 400
        
        # Read CSV file
        try:
            content = file.read().decode('utf-8')
            # Try to parse as CSV and extract column B if present. Fall back to line-based parsing.
            import csv
            words = []
            try:
                reader = csv.reader(content.splitlines())
                for row in reader:
                    if not row:
                        continue
                    # If there's at least 2 columns, use column B (index 1), else use first column
                    cell = row[1].strip() if len(row) > 1 and row[1].strip() else row[0].strip()
                    if cell:
                        words.append(cell)
            except Exception:
                # Fallback: one word per line
                words = [line.strip() for line in content.split('\n') if line.strip()]
        except Exception as e:
            logger.error(f"Error reading CSV file: {e}")
            return jsonify({'error': 'Invalid CSV file'}), 400
        
        name = request.form.get('name', file.filename)
        source_type = 'csv'
        source_ref = file.filename
    else:
        # JSON payload
        try:
            schema = WordListCreateSchema()
            data = schema.load(request.json)
        except ValidationError as e:
            return jsonify({'errors': e.messages}), 422
        
        name = data['name']
        source_type = data['source_type']
        source_ref = data.get('source_ref')
        words = data.get('words', [])
        
        if not words and source_type == 'manual':
            return jsonify({'error': 'No words provided for manual word list'}), 400

        # If source is Google Sheets and words not provided, fetch from sheet
        if source_type == 'google_sheet' and (not words or len(words) == 0):
            if not source_ref:
                return jsonify({'error': 'Missing Google Sheet ID (source_ref)'}), 400
            try:
                # Get user's Google credentials
                auth_service = AuthService()
                # We need the user for creds; coverage routes use JWT, fetch user via ID
                from app.models import User
                user = User.query.get(user_id)
                if not user or not user.google_access_token:
                    return jsonify({'error': 'Google Sheets access not authorized'}), 403
                creds = auth_service.get_user_credentials(user)

                sheets_service = GoogleSheetsService()
                # Respect include_header flag from request (default True)
                include_header = True
                if request.json:
                    include_header = request.json.get('include_header', True)
                elif request.form:
                    include_header = request.form.get('include_header', 'true').lower() == 'true'

                # Default: first sheet, auto-detect A/B with fallback
                words = sheets_service.fetch_words_from_spreadsheet(
                    creds,
                    spreadsheet_id=source_ref,
                    include_header=include_header
                )
                if not words:
                    return jsonify({'error': 'No words found in the Google Sheet (column B)'}), 400
            except Exception as e:
                logger.exception(f"Failed to fetch words from Google Sheets: {e}")
                return jsonify({'error': f'Failed to read Google Sheet: {str(e)}'}), 400
    
    # Ingest word list
    wordlist_service = WordListService()
    try:
        fold_diacritics = request.form.get('fold_diacritics', 'true').lower() == 'true'
        if 'file' not in request.files and request.json:
            fold_diacritics = request.json.get('fold_diacritics', True)
        
        wordlist, ingestion_report = wordlist_service.ingest_word_list(
            words=words,
            name=name,
            owner_user_id=user_id,
            source_type=source_type,
            source_ref=source_ref,
            fold_diacritics=fold_diacritics
        )
        
        db.session.commit()
        
        return jsonify({
            'wordlist': wordlist.to_dict(),
            'ingestion_report': ingestion_report
        }), 201
        
    except Exception as e:
        db.session.rollback()
        logger.exception(f"Error creating word list: {e}")
        return jsonify({'error': str(e)}), 500


@coverage_bp.route('/wordlists/<int:wordlist_id>', methods=['GET'])
@jwt_required()
def get_wordlist(wordlist_id):
    """Get details of a specific word list"""
    user_id = int(get_jwt_identity())
    
    wordlist = WordList.query.filter(
        db.and_(
            WordList.id == wordlist_id,
            db.or_(
                WordList.owner_user_id == user_id,
                WordList.owner_user_id.is_(None)  # Global lists
            )
        )
    ).first()
    
    if not wordlist:
        return jsonify({'error': 'WordList not found'}), 404
    
    return jsonify(wordlist.to_dict()), 200


@coverage_bp.route('/wordlists/<int:wordlist_id>', methods=['PATCH'])
@jwt_required()
def update_wordlist(wordlist_id):
    """Update a word list (owner only)"""
    user_id = int(get_jwt_identity())
    
    wordlist = WordList.query.filter_by(id=wordlist_id, owner_user_id=user_id).first()
    if not wordlist:
        return jsonify({'error': 'WordList not found or not authorized'}), 404
    
    try:
        schema = WordListUpdateSchema()
        data = schema.load(request.json)
    except ValidationError as e:
        return jsonify({'errors': e.messages}), 422
    
    if 'name' in data:
        wordlist.name = data['name']
    
    try:
        db.session.commit()
        return jsonify(wordlist.to_dict()), 200
    except Exception as e:
        db.session.rollback()
        logger.exception(f"Error updating word list: {e}")
        return jsonify({'error': str(e)}), 500


@coverage_bp.route('/wordlists/<int:wordlist_id>/refresh', methods=['POST'])
@jwt_required()
def refresh_wordlist(wordlist_id):
    """Refresh/populate words_json from source for a wordlist"""
    user_id = int(get_jwt_identity())
    
    # Get wordlist (must be owned by user or be global)
    wordlist = WordList.query.filter(
        db.and_(
            WordList.id == wordlist_id,
            db.or_(
                WordList.owner_user_id == user_id,
                WordList.owner_user_id.is_(None)  # Global lists
            )
        )
    ).first()
    
    if not wordlist:
        return jsonify({'error': 'WordList not found'}), 404
    
    # Get user for Google Sheets access
    from app.models import User
    user = User.query.get(user_id)
    
    try:
        wordlist_service = WordListService()
        refresh_report = wordlist_service.refresh_wordlist_from_source(wordlist, user)
        db.session.commit()
        
        return jsonify({
            'wordlist': wordlist.to_dict(),
            'refresh_report': refresh_report
        }), 200
    except Exception as e:
        db.session.rollback()
        logger.exception(f"Error refreshing word list: {e}")
        return jsonify({'error': str(e)}), 500


@coverage_bp.route('/wordlists/<int:wordlist_id>', methods=['DELETE'])
@jwt_required()
def delete_wordlist(wordlist_id):
    """Delete a word list (owner only)"""
    user_id = int(get_jwt_identity())
    
    wordlist_service = WordListService()
    success = wordlist_service.delete_wordlist(wordlist_id, user_id)
    
    if not success:
        return jsonify({'error': 'WordList not found or not authorized'}), 404
    
    try:
        db.session.commit()
        return jsonify({'message': 'WordList deleted successfully'}), 200
    except Exception as e:
        db.session.rollback()
        logger.exception(f"Error deleting word list: {e}")
        return jsonify({'error': str(e)}), 500


# ============================================================================
# Coverage Run Endpoints
# ============================================================================

@coverage_bp.route('/coverage/import-from-sheets', methods=['POST'])
@jwt_required()
@limiter.limit("10 per hour")
def import_sentences_from_sheets():
    """Import sentences from Google Sheets URL and create a temporary history entry"""
    user_id = int(get_jwt_identity())
    
    try:
        sheet_url = request.json.get('sheet_url')
        if not sheet_url:
            return jsonify({'error': 'sheet_url is required'}), 400
        
        # Extract spreadsheet ID from URL
        # Supports formats:
        # - https://docs.google.com/spreadsheets/d/SPREADSHEET_ID/edit...
        # - SPREADSHEET_ID (just the ID)
        import re
        match = re.search(r'/spreadsheets/d/([a-zA-Z0-9-_]+)', sheet_url)
        if match:
            spreadsheet_id = match.group(1)
        elif re.match(r'^[a-zA-Z0-9-_]+$', sheet_url):
            spreadsheet_id = sheet_url
        else:
            return jsonify({'error': 'Invalid Google Sheets URL format'}), 400
        
        # Get user credentials
        user = User.query.get(user_id)
        if not user or not user.google_access_token:
            return jsonify({'error': 'Google authentication required. Please sign in with Google first.'}), 401
        
        # Create credentials object
        from google.oauth2.credentials import Credentials
        from datetime import datetime
        
        creds = Credentials(
            token=user.google_access_token,
            refresh_token=user.google_refresh_token,
            token_uri='https://oauth2.googleapis.com/token',
            client_id=user.google_client_id or request.headers.get('X-Google-Client-ID'),
            client_secret=user.google_client_secret or request.headers.get('X-Google-Client-Secret')
        )
        
        # Check if token is expired and refresh if needed
        if user.google_token_expiry and datetime.utcnow() >= user.google_token_expiry:
            auth_service = AuthService()
            try:
                auth_service.refresh_google_token(user)
                db.session.commit()
                # Update creds with new token
                creds = Credentials(
                    token=user.google_access_token,
                    refresh_token=user.google_refresh_token,
                    token_uri='https://oauth2.googleapis.com/token',
                    client_id=user.google_client_id,
                    client_secret=user.google_client_secret
                )
            except Exception as e:
                logger.error(f"Failed to refresh Google token: {e}")
                return jsonify({'error': 'Failed to refresh Google authentication. Please sign in again.'}), 401
        
        # Fetch sentences from Google Sheets
        sheets_service = GoogleSheetsService()
        try:
            # Use fetch_words_from_spreadsheet but adapt it for sentences
            # We'll read column B (sentences) and column A (index - optional)
            from googleapiclient.discovery import build
            
            gs = build('sheets', 'v4', credentials=creds)
            
            # Get first sheet name
            spreadsheet = gs.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
            sheets = spreadsheet.get('sheets', [])
            if not sheets:
                return jsonify({'error': 'Spreadsheet has no sheets'}), 400
            
            sheet_title = sheets[0]['properties']['title']
            
            # Read columns A (Index) and B (Sentence)
            range_name = f"{sheet_title}!A:B"
            result = gs.spreadsheets().values().get(
                spreadsheetId=spreadsheet_id,
                range=range_name
            ).execute()
            
            values = result.get('values', [])
            if not values:
                return jsonify({'error': 'No data found in spreadsheet'}), 400
            
            # Parse sentences (skip header if present)
            sentences = []
            start_idx = 0
            
            # Check if first row is a header
            if len(values) > 0 and len(values[0]) >= 2:
                first_row = [str(cell).strip().lower() for cell in values[0]]
                if 'index' in first_row or 'sentence' in first_row:
                    start_idx = 1
            
            for row in values[start_idx:]:
                if len(row) >= 2:
                    sentence = str(row[1]).strip()
                    if sentence:
                        sentences.append(sentence)
                elif len(row) == 1:
                    # Only one column - assume it's the sentence
                    sentence = str(row[0]).strip()
                    # Skip if it looks like an index number
                    if sentence and not re.match(r'^\d+$', sentence):
                        sentences.append(sentence)
            
            if not sentences:
                return jsonify({'error': 'No sentences found in spreadsheet'}), 400
            
            logger.info(f"Imported {len(sentences)} sentences from Google Sheets {spreadsheet_id}")
            
            # Create a temporary History entry to store the sentences
            from app.models import History
            
            # Format sentences like the History model expects
            formatted_sentences = [
                {
                    'original': sentence,
                    'normalized': sentence  # Will be normalized during coverage analysis
                }
                for sentence in sentences
            ]
            
            history = History(
                user_id=user_id,
                original_filename=f"Google Sheets Import ({spreadsheet.get('properties', {}).get('title', 'Untitled')})",
                sentences=formatted_sentences,
                processed_sentences_count=len(sentences)
            )
            
            db.session.add(history)
            db.session.commit()
            
            return jsonify({
                'history_id': history.id,
                'sentence_count': len(sentences),
                'filename': history.original_filename
            }), 201
            
        except Exception as e:
            logger.exception(f"Error fetching sentences from Google Sheets: {e}")
            return jsonify({'error': f'Failed to fetch sentences from Google Sheets: {str(e)}'}), 500
    
    except Exception as e:
        db.session.rollback()
        logger.exception(f"Error importing from Google Sheets: {e}")
        return jsonify({'error': str(e)}), 500


@coverage_bp.route('/coverage/run', methods=['POST'])
@jwt_required()
@limiter.limit("20 per hour")
def create_coverage_run():
    """Create and start a new coverage run"""
    user_id = int(get_jwt_identity())
    
    try:
        schema = CoverageRunCreateSchema()
        data = schema.load(request.json)
    except ValidationError as e:
        return jsonify({'errors': e.messages}), 422
    
    # Get wordlist_id (provided, user default, or global default)
    wordlist_id = data.get('wordlist_id')
    if not wordlist_id:
        # Try user default
        user_settings = UserSettings.query.filter_by(user_id=user_id).first()
        if user_settings and user_settings.default_wordlist_id:
            wordlist_id = user_settings.default_wordlist_id
        else:
            # Try global default
            wordlist_service = WordListService()
            global_default = wordlist_service.get_global_default_wordlist()
            if global_default:
                wordlist_id = global_default.id
    
    # Create coverage run
    coverage_run = CoverageRun(
        user_id=user_id,
        mode=data['mode'],
        source_type=data['source_type'],
        source_id=data['source_id'],
        wordlist_id=wordlist_id,
        config_json=data.get('config'),
        status='pending'
    )
    
    try:
        db.session.add(coverage_run)
        db.session.commit()
        
        # Start async task
        task = coverage_build_async.apply_async(args=[coverage_run.id])
        
        coverage_run.celery_task_id = task.id
        db.session.commit()
        
        return jsonify({
            'coverage_run': coverage_run.to_dict(),
            'task_id': task.id
        }), 201
        
    except Exception as e:
        db.session.rollback()
        logger.exception(f"Error creating coverage run: {e}")
        return jsonify({'error': str(e)}), 500


@coverage_bp.route('/coverage/runs/<int:run_id>', methods=['GET'])
@jwt_required()
def get_coverage_run(run_id):
    """Get status and summary of a coverage run"""
    user_id = int(get_jwt_identity())
    
    coverage_run = CoverageRun.query.filter_by(id=run_id, user_id=user_id).first()
    if not coverage_run:
        return jsonify({'error': 'Coverage run not found'}), 404
    
    # Get assignments (paginated)
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    
    assignments_query = CoverageAssignment.query.filter_by(coverage_run_id=run_id)
    assignments_paginated = assignments_query.paginate(page=page, per_page=per_page, error_out=False)
    
    return jsonify({
        'coverage_run': coverage_run.to_dict(),
        'assignments': [a.to_dict() for a in assignments_paginated.items],
        'pagination': {
            'page': page,
            'per_page': per_page,
            'total': assignments_paginated.total,
            'pages': assignments_paginated.pages
        }
    }), 200


@coverage_bp.route('/coverage/runs/<int:run_id>/swap', methods=['POST'])
@jwt_required()
def swap_assignment(run_id):
    """Swap a word assignment to a different sentence (Coverage mode)"""
    user_id = int(get_jwt_identity())
    
    coverage_run = CoverageRun.query.filter_by(id=run_id, user_id=user_id).first()
    if not coverage_run:
        return jsonify({'error': 'Coverage run not found'}), 404
    
    try:
        schema = CoverageSwapSchema()
        data = schema.load(request.json)
    except ValidationError as e:
        return jsonify({'errors': e.messages}), 422
    
    # Find the assignment
    assignment = CoverageAssignment.query.filter_by(
        coverage_run_id=run_id,
        word_key=data['word_key']
    ).first()
    
    if not assignment:
        return jsonify({'error': 'Assignment not found'}), 404
    
    # Update assignment
    assignment.sentence_index = data['new_sentence_index']
    assignment.manual_edit = True
    
    try:
        db.session.commit()
        return jsonify(assignment.to_dict()), 200
    except Exception as e:
        db.session.rollback()
        logger.exception(f"Error swapping assignment: {e}")
        return jsonify({'error': str(e)}), 500


@coverage_bp.route('/coverage/runs/<int:run_id>/export', methods=['POST'])
@jwt_required()
@limiter.limit("10 per hour")
def export_coverage_run(run_id):
    """Export coverage run results to Google Sheets"""
    user_id = int(get_jwt_identity())
    
    coverage_run = CoverageRun.query.filter_by(id=run_id, user_id=user_id).first()
    if not coverage_run:
        return jsonify({'error': 'Coverage run not found'}), 404
    
    if coverage_run.status != 'completed':
        return jsonify({'error': 'Coverage run not completed'}), 400
    
    try:
        schema = CoverageExportSchema()
        data = schema.load(request.json)
    except ValidationError as e:
        return jsonify({'errors': e.messages}), 422
    
    # Get user for OAuth credentials
    user = User.query.get(user_id)
    if not user or not user.google_access_token:
        return jsonify({'error': 'Google OAuth not configured. Please connect your Google account in Settings.'}), 400
    
    try:
        # Get assignments
        assignments = CoverageAssignment.query.filter_by(coverage_run_id=run_id).all()
        
        # Prepare data for sheets
        if coverage_run.mode == 'coverage':
            # Coverage mode: word-to-sentence assignments
            rows = [['Word', 'Sentence', 'Score', 'Index']]  # Header
            for assignment in assignments:
                rows.append([
                    assignment.word_key,
                    assignment.sentence_text,
                    assignment.sentence_score or 0.0,
                    assignment.sentence_index
                ])
        else:
            # Filter mode: ranked sentences
            rows = [['Rank', 'Sentence', 'Score', 'Index']]  # Header
            sorted_assignments = sorted(assignments, key=lambda a: a.sentence_score or 0.0, reverse=True)
            for idx, assignment in enumerate(sorted_assignments, 1):
                rows.append([
                    idx,
                    assignment.sentence_text,
                    assignment.sentence_score or 0.0,
                    assignment.sentence_index
                ])
        
        # Create Google Sheets document
        sheets_service = GoogleSheetsService()
        sheet_name = data.get('sheet_name', f"Vocabulary Coverage - {coverage_run.id}")
        
        # Create spreadsheet
        spreadsheet = sheets_service.create_spreadsheet_from_rows(
            user,
            sheet_name,
            rows
        )
        
        return jsonify({
            'message': 'Export successful',
            'spreadsheet_id': spreadsheet.get('spreadsheetId'),
            'spreadsheet_url': spreadsheet.get('spreadsheetUrl')
        }), 200
        
    except Exception as e:
        logger.exception(f"Error exporting coverage run to Sheets: {e}")
        return jsonify({'error': f'Export failed: {str(e)}'}), 500


@coverage_bp.route('/coverage/runs/<int:run_id>/download', methods=['GET'])
@jwt_required()
def download_coverage_run(run_id):
    """Download coverage run results as CSV"""
    from flask import make_response
    import csv
    from io import StringIO
    
    user_id = int(get_jwt_identity())
    
    coverage_run = CoverageRun.query.filter_by(id=run_id, user_id=user_id).first()
    if not coverage_run:
        return jsonify({'error': 'Coverage run not found'}), 404
    
    if coverage_run.status != 'completed':
        return jsonify({'error': 'Coverage run not completed'}), 400
    
    try:
        # Get assignments
        assignments = CoverageAssignment.query.filter_by(coverage_run_id=run_id).all()
        
        # Create CSV in memory
        output = StringIO()
        writer = csv.writer(output)
        
        # Write data based on mode
        if coverage_run.mode == 'coverage':
            # Coverage mode: word-to-sentence assignments
            writer.writerow(['Word', 'Sentence', 'Score', 'Index'])
            for assignment in assignments:
                writer.writerow([
                    assignment.word_key,
                    assignment.sentence_text,
                    assignment.sentence_score or 0.0,
                    assignment.sentence_index
                ])
        else:
            # Filter mode: ranked sentences
            writer.writerow(['Rank', 'Sentence', 'Score', 'Index'])
            sorted_assignments = sorted(assignments, key=lambda a: a.sentence_score or 0.0, reverse=True)
            for idx, assignment in enumerate(sorted_assignments, 1):
                writer.writerow([
                    idx,
                    assignment.sentence_text,
                    assignment.sentence_score or 0.0,
                    assignment.sentence_index
                ])
        
        # Create response
        csv_data = output.getvalue()
        output.close()
        
        response = make_response(csv_data)
        response.headers['Content-Type'] = 'text/csv; charset=utf-8'
        response.headers['Content-Disposition'] = f'attachment; filename=coverage_run_{run_id}.csv'
        
        return response
        
    except Exception as e:
        logger.exception(f"Error downloading coverage run as CSV: {e}")
        return jsonify({'error': f'Download failed: {str(e)}'}), 500

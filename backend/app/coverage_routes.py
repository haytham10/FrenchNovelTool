"""API routes for Vocabulary Coverage Tool"""
import logging
import re
from flask import Blueprint, request, jsonify, send_from_directory, abort, current_app
from werkzeug.utils import safe_join
from flask_jwt_extended import jwt_required, get_jwt_identity
from marshmallow import ValidationError
from app import limiter, db
from app.models import WordList, CoverageRun, CoverageAssignment, UserSettings, User
from app.services.wordlist_service import WordListService
from app.services.auth_service import AuthService
from datetime import timezone
from app.services.google_sheets_service import GoogleSheetsService
from app.schemas import (
    WordListCreateSchema,
    WordListUpdateSchema,
    CoverageRunCreateSchema,
    CoverageSwapSchema,
    CoverageExportSchema
)
from app.tasks import coverage_build_async, batch_coverage_build_async

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
        # Respect include_header flag from request (default True)
        include_header = True
        if request.json:
            include_header = request.json.get('include_header', True)
        elif request.form:
            include_header = request.form.get('include_header', 'true').lower() == 'true'

        refresh_report = wordlist_service.refresh_wordlist_from_source(wordlist, user, include_header=include_header)
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
# Global Wordlist Management Endpoints
# ============================================================================

@coverage_bp.route('/wordlists/global/stats', methods=['GET'])
@jwt_required()
def get_global_wordlist_stats():
    """Get statistics about global wordlists"""
    from app.services.global_wordlist_manager import GlobalWordlistManager
    
    try:
        stats = GlobalWordlistManager.get_stats()
        return jsonify(stats), 200
    except Exception as e:
        logger.exception(f"Error getting global wordlist stats: {e}")
        return jsonify({'error': str(e)}), 500


@coverage_bp.route('/wordlists/global/default', methods=['GET'])
@jwt_required()
def get_global_default_wordlist():
    """Get the global default wordlist"""
    from app.services.global_wordlist_manager import GlobalWordlistManager
    
    try:
        default = GlobalWordlistManager.get_global_default()
        
        if not default:
            return jsonify({'error': 'No global default wordlist found'}), 404
        
        return jsonify(default.to_dict()), 200
    except Exception as e:
        logger.exception(f"Error getting global default wordlist: {e}")
        return jsonify({'error': str(e)}), 500


@coverage_bp.route('/wordlists/global', methods=['GET'])
@jwt_required()
def list_global_wordlists():
    """List all global wordlists (admin/info endpoint)"""
    from app.services.global_wordlist_manager import GlobalWordlistManager
    
    try:
        global_wordlists = GlobalWordlistManager.list_global_wordlists()
        
        return jsonify({
            'wordlists': [wl.to_dict() for wl in global_wordlists],
            'total': len(global_wordlists)
        }), 200
    except Exception as e:
        logger.exception(f"Error listing global wordlists: {e}")
        return jsonify({'error': str(e)}), 500


# ============================================================================
# Coverage Run Endpoints
# ============================================================================

@coverage_bp.route('/coverage/cost', methods=['GET'])
@jwt_required()
def get_coverage_cost():
    """Get the cost of running a coverage analysis"""
    from app.constants import COVERAGE_RUN_COST
    
    return jsonify({
        'cost': COVERAGE_RUN_COST,
        'currency': 'credits'
    }), 200


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
        
        # Create credentials object using application config as fallback for client_id/secret
        from google.oauth2.credentials import Credentials
        from datetime import datetime
        from flask import current_app

        client_id = current_app.config.get('GOOGLE_CLIENT_ID') or request.headers.get('X-Google-Client-ID')
        client_secret = current_app.config.get('GOOGLE_CLIENT_SECRET') or request.headers.get('X-Google-Client-Secret')

        # If user has no refresh token, we can still try with the access token (read-only short-lived)
        creds_kwargs = {
            'token': user.google_access_token,
            'token_uri': 'https://oauth2.googleapis.com/token',
        }
        if user.google_refresh_token:
            creds_kwargs['refresh_token'] = user.google_refresh_token
        if client_id:
            creds_kwargs['client_id'] = client_id
        if client_secret:
            creds_kwargs['client_secret'] = client_secret

        creds = Credentials(**creds_kwargs)

        # Check if token is expired and refresh if needed
        expiry_val = user.google_token_expiry
        if expiry_val and isinstance(expiry_val, datetime) and expiry_val.tzinfo is None:
            expiry_val = expiry_val.replace(tzinfo=timezone.utc)
        if expiry_val and datetime.now(timezone.utc) >= expiry_val:
            auth_service = AuthService()
            try:
                auth_service.refresh_google_token(user)
                db.session.commit()
                # Update creds with new token/refresh token
                creds_kwargs['token'] = user.google_access_token
                if user.google_refresh_token:
                    creds_kwargs['refresh_token'] = user.google_refresh_token
                creds = Credentials(**creds_kwargs)
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
    """Create and start a new coverage run (single source or batch)"""
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
    
    # For batch mode, store source_ids in config_json and use first source as source_id
    mode = data['mode']
    if mode == 'batch':
        source_ids = data['source_ids']
        config = data.get('config') or {}
        config['source_ids'] = source_ids
        # Use first source_id as the primary source_id for indexing
        source_id = source_ids[0]
    else:
        source_id = data['source_id']
        config = data.get('config')
    
    # Create coverage run
    coverage_run = CoverageRun(
        user_id=user_id,
        mode=mode,
        source_type=data['source_type'],
        source_id=source_id,
        wordlist_id=wordlist_id,
        config_json=config,
        status='pending'
    )
    
    try:
        db.session.add(coverage_run)
        db.session.commit()
        
        # Charge credits for coverage run
        from app.services.credit_service import CreditService
        from app.constants import COVERAGE_RUN_COST
        
        # For batch mode, charge per source (or use a multiplier)
        if mode == 'batch':
            cost = COVERAGE_RUN_COST * len(source_ids)
            description = f'Batch coverage run #{coverage_run.id} ({len(source_ids)} sources)'
        else:
            cost = COVERAGE_RUN_COST
            description = f'Coverage run #{coverage_run.id} ({mode} mode)'
        
        success, error_msg = CreditService.charge_coverage_run(
            user_id=user_id,
            coverage_run_id=coverage_run.id,
            amount=cost,
            description=description
        )
        
        if not success:
            # Rollback coverage run creation if credit charge failed
            db.session.delete(coverage_run)
            db.session.commit()
            return jsonify({'error': error_msg}), 402  # Payment Required
        
        # Start async task - use batch task for batch mode
        if mode == 'batch':
            from app.tasks import batch_coverage_build_async
            task = batch_coverage_build_async.apply_async(args=[coverage_run.id])
        else:
            task = coverage_build_async.apply_async(args=[coverage_run.id])
        
        coverage_run.celery_task_id = task.id
        db.session.commit()
        
        return jsonify({
            'coverage_run': coverage_run.to_dict(),
            'task_id': task.id,
            'credits_charged': cost
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

    learning_set = []
    if coverage_run.mode == 'coverage':
        stats = coverage_run.stats_json or {}
        learning_set = stats.get('learning_set') or []

        # Backward compatibility: derive a basic learning set if stats are missing
        if not learning_set:
            all_assignments = assignments_query.all()
            seen_sentences = set()
            ordered_assignments = []
            for assignment in all_assignments:
                if assignment.sentence_index not in seen_sentences:
                    seen_sentences.add(assignment.sentence_index)
                    ordered_assignments.append(assignment)
            ordered_assignments.sort(key=lambda a: a.sentence_index)
            learning_set = [
                {
                    'rank': rank,
                    'sentence_index': assignment.sentence_index,
                    'sentence_text': assignment.sentence_text,
                    'token_count': None,
                    'new_word_count': None,
                    'score': assignment.sentence_score,
                }
                for rank, assignment in enumerate(ordered_assignments, start=1)
            ]
    elif coverage_run.mode == 'batch':
        # For batch mode, use learning_set from stats_json (created by batch_coverage_mode)
        stats = coverage_run.stats_json or {}
        learning_set = stats.get('learning_set', [])

        # Fallback: build from assignments if stats don't have learning_set
        if not learning_set:
            all_assignments = assignments_query.all()
            # Remove duplicates and sort by sentence index
            seen_sentences = set()
            ordered_assignments = []
            for assignment in all_assignments:
                if assignment.sentence_index is not None and assignment.sentence_index not in seen_sentences:
                    seen_sentences.add(assignment.sentence_index)
                    ordered_assignments.append(assignment)
            ordered_assignments.sort(key=lambda a: a.sentence_index)

            learning_set = [
                {
                    'rank': rank,
                    'sentence_index': assignment.sentence_index,
                    'sentence_text': assignment.sentence_text,
                    'token_count': None,
                    'new_word_count': None,
                    'score': assignment.sentence_score,
                }
                for rank, assignment in enumerate(ordered_assignments, start=1)
            ]
    elif coverage_run.mode == 'filter':
        # Build learning set from assignments for filter mode
        all_assignments = assignments_query.all()
        # Sort by sentence index to maintain original order
        ordered_assignments = sorted(
            [a for a in all_assignments if a.sentence_index is not None],
            key=lambda a: a.sentence_index
        )

        learning_set = [
            {
                'rank': rank,
                'sentence_index': assignment.sentence_index,
                'sentence_text': assignment.sentence_text,
                'token_count': None,
                'new_word_count': None,
                'score': assignment.sentence_score,
            }
            for rank, assignment in enumerate(ordered_assignments, start=1)
        ]
    
    return jsonify({
        'coverage_run': coverage_run.to_dict(),
        'assignments': [a.to_dict() for a in assignments_paginated.items],
        'pagination': {
            'page': page,
            'per_page': per_page,
            'total': assignments_paginated.total,
            'pages': assignments_paginated.pages
        },
        'learning_set': learning_set
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
        
        # Helper to build a learning set fallback if stats missing
        def _build_learning_set_from_assignments(assignments_list):
            seen = set()
            ordered = []
            for assignment in assignments_list:
                if assignment.sentence_index not in seen:
                    seen.add(assignment.sentence_index)
                    ordered.append(assignment)
            ordered.sort(key=lambda a: a.sentence_index)
            return [
                {
                    'rank': rank,
                    'sentence_index': assignment.sentence_index,
                    'sentence_text': assignment.sentence_text,
                    'score': assignment.sentence_score,
                }
                for rank, assignment in enumerate(ordered, start=1)
            ]

        # Prepare data for sheets
        if coverage_run.mode == 'coverage':
            # Coverage mode: export the learning set (ranked sentences)
            stats = coverage_run.stats_json or {}
            learning_set = stats.get('learning_set') or _build_learning_set_from_assignments(assignments)

            rows = [['Rank', 'Sentence']]  # Header
            for entry in learning_set:
                rows.append([
                    entry.get('rank'),
                    entry.get('sentence_text')
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
        
        # Helper to build learning set fallback when stats missing
        def _build_learning_set_from_assignments(assignments_list):
            seen = set()
            ordered = []
            for assignment in assignments_list:
                if assignment.sentence_index not in seen:
                    seen.add(assignment.sentence_index)
                    ordered.append(assignment)
            ordered.sort(key=lambda a: a.sentence_index)
            return [
                {
                    'rank': rank,
                    'sentence_index': assignment.sentence_index,
                    'sentence_text': assignment.sentence_text,
                    'score': assignment.sentence_score,
                }
                for rank, assignment in enumerate(ordered, start=1)
            ]

        # Create CSV in memory
        output = StringIO()
        writer = csv.writer(output)
        
        # Write data based on mode
        if coverage_run.mode == 'coverage':
            stats = coverage_run.stats_json or {}
            learning_set = stats.get('learning_set') or _build_learning_set_from_assignments(assignments)

            writer.writerow(['Rank', 'Sentence'])
            for entry in learning_set:
                writer.writerow([
                    entry.get('rank'),
                    entry.get('sentence_text')
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


@coverage_bp.route('/coverage/runs/<int:run_id>/diagnosis', methods=['GET'])
@jwt_required()
def diagnose_coverage_run(run_id):
    """
    Diagnose why certain words were not covered in a coverage run.

    Analyzes uncovered words and categorizes them into:
    - Not in corpus: Words that don't appear in any source sentence
    - Only in long sentences: Words only found in 9+ word sentences (outside 4-8 range)
    - Only in short sentences: Words only found in 1-3 word sentences
    - In valid range but missed: Words in 4-8 word sentences that algorithm didn't select

    Returns JSON with counts and sample words (first 20-30) from each category.
    """
    user_id = int(get_jwt_identity())

    coverage_run = CoverageRun.query.filter_by(id=run_id, user_id=user_id).first()
    if not coverage_run:
        return jsonify({'error': 'Coverage run not found'}), 404

    if coverage_run.status != 'completed':
        return jsonify({'error': 'Coverage run must be completed for diagnosis'}), 400

    try:
        # Get the wordlist used for this run
        wordlist = WordList.query.get(coverage_run.wordlist_id)
        if not wordlist or not wordlist.words_json:
            return jsonify({'error': 'WordList not found or empty'}), 404

        wordlist_keys = set(wordlist.words_json)

        # Get covered words from assignments
        assignments = CoverageAssignment.query.filter_by(coverage_run_id=run_id).all()
        covered_words = set(a.word_key for a in assignments)

        # Calculate uncovered words
        uncovered_words = wordlist_keys - covered_words

        if not uncovered_words:
            return jsonify({
                'message': 'All words covered!',
                'total_words': len(wordlist_keys),
                'covered_words': len(covered_words),
                'uncovered_words': 0,
                'categories': {}
            }), 200

        # Get source sentences to analyze
        from app.models import History, Job
        sentences = []

        if coverage_run.source_type == 'history':
            history = History.query.get(coverage_run.source_id)
            if history and history.sentences:
                sentences = [s.get('normalized', s.get('original', '')) for s in history.sentences]
        elif coverage_run.source_type == 'job':
            job = Job.query.get(coverage_run.source_id)
            if job and job.chunk_results:
                for chunk_result in job.chunk_results:
                    chunk_sentences = chunk_result.get('sentences', [])
                    sentences.extend([s.get('normalized', s.get('original', '')) for s in chunk_sentences])

        if not sentences:
            return jsonify({'error': 'No source sentences found'}), 404

        # Initialize categories
        not_in_corpus = set()
        only_in_long_sentences = set()
        only_in_short_sentences = set()
        in_valid_but_missed = set()

        # Analyze each uncovered word
        from app.services.coverage_service import CoverageService
        from app.utils.linguistics import LinguisticsUtils

        # Create temporary coverage service for analysis
        config = coverage_run.config_json or {}
        temp_service = CoverageService(wordlist_keys=uncovered_words, config=config)

        # Build sentence index to tokenize all sentences
        sentence_index = temp_service.build_sentence_index(sentences)

        # Build word-to-sentence mapping
        word_to_sentences = {}
        for idx, info in sentence_index.items():
            token_count = info['token_count']
            sentence_words = temp_service.filter_content_words_only(
                info,
                uncovered_words,
                fold_diacritics=temp_service.fold_diacritics,
                handle_elisions=temp_service.handle_elisions
            )

            for word in sentence_words:
                if word not in word_to_sentences:
                    word_to_sentences[word] = {'short': 0, 'valid': 0, 'long': 0}

                if token_count < 4:
                    word_to_sentences[word]['short'] += 1
                elif token_count <= 8:
                    word_to_sentences[word]['valid'] += 1
                else:
                    word_to_sentences[word]['long'] += 1

        # Categorize uncovered words
        for word in uncovered_words:
            if word not in word_to_sentences:
                # Word doesn't appear in any sentence
                not_in_corpus.add(word)
            else:
                counts = word_to_sentences[word]

                if counts['valid'] > 0:
                    # Word appears in valid-length sentences but wasn't selected
                    in_valid_but_missed.add(word)
                elif counts['long'] > 0 and counts['short'] == 0:
                    # Word only appears in long sentences
                    only_in_long_sentences.add(word)
                elif counts['short'] > 0 and counts['long'] == 0:
                    # Word only appears in short sentences
                    only_in_short_sentences.add(word)
                else:
                    # Word appears in both short and long, but not in valid range
                    if counts['short'] > counts['long']:
                        only_in_short_sentences.add(word)
                    else:
                        only_in_long_sentences.add(word)

        # Sample words from each category (first 30)
        def sample_words(word_set, limit=30):
            return sorted(list(word_set))[:limit]

        categories = {
            'not_in_corpus': {
                'count': len(not_in_corpus),
                'sample_words': sample_words(not_in_corpus),
                'description': 'Words that do not appear in any source sentence'
            },
            'only_in_long_sentences': {
                'count': len(only_in_long_sentences),
                'sample_words': sample_words(only_in_long_sentences),
                'description': 'Words only found in sentences with 9+ words (outside 4-8 range)'
            },
            'only_in_short_sentences': {
                'count': len(only_in_short_sentences),
                'sample_words': sample_words(only_in_short_sentences),
                'description': 'Words only found in sentences with 1-3 words'
            },
            'in_valid_but_missed': {
                'count': len(in_valid_but_missed),
                'sample_words': sample_words(in_valid_but_missed),
                'description': 'Words in 4-8 word sentences that the algorithm did not select'
            }
        }

        # Generate recommendation
        recommendation = _generate_recommendation(categories, len(uncovered_words))

        return jsonify({
            'total_words': len(wordlist_keys),
            'covered_words': len(covered_words),
            'uncovered_words': len(uncovered_words),
            'coverage_percentage': (len(covered_words) / len(wordlist_keys) * 100) if wordlist_keys else 0,
            'categories': categories,
            'recommendation': recommendation
        }), 200

    except Exception as e:
        logger.exception(f"Error diagnosing coverage run {run_id}: {e}")
        return jsonify({'error': f'Diagnosis failed: {str(e)}'}), 500


def _generate_recommendation(categories, total_uncovered):
    """Generate a simple recommendation based on diagnosis results"""
    not_in_corpus = categories['not_in_corpus']['count']
    only_long = categories['only_in_long_sentences']['count']
    only_short = categories['only_in_short_sentences']['count']
    in_valid = categories['in_valid_but_missed']['count']

    recommendations = []

    if not_in_corpus > total_uncovered * 0.5:
        recommendations.append(f"{not_in_corpus} words ({not_in_corpus/total_uncovered*100:.0f}%) are not in your source material. Upload more novels or expand your corpus.")

    if only_long > total_uncovered * 0.3:
        recommendations.append(f"{only_long} words only appear in long sentences (9+ words). Consider adjusting the sentence length limit in future runs.")

    if only_short > total_uncovered * 0.2:
        recommendations.append(f"{only_short} words only appear in very short sentences (1-3 words). These may be function words or fragments.")

    if in_valid > total_uncovered * 0.2:
        recommendations.append(f"{in_valid} words are in valid-length sentences but weren't selected. The algorithm may need more iterations or the words might be in sentences competing with higher-scoring options.")

    if not recommendations:
        recommendations.append("Most uncovered words are due to corpus limitations or sentence length constraints. Consider uploading additional source material.")

    return " ".join(recommendations)


# Serve coverage logs without authentication (careful: ensure your deployment secures /logs if needed)
@coverage_bp.route('/logs/<path:filename>', methods=['GET'])
def serve_coverage_log(filename):
    """Serve a coverage log file from the backend/logs directory.

    This route intentionally does not require authentication per user's request.
    It validates the filename to prevent directory traversal and only allows
    files that match the pattern 'coverage_covered_*.txt' or 'coverage_uncovered_*.txt'.
    """
    logs_dir = current_app.config.get('COVERAGE_LOG_DIR', 'logs')

    # Normalize and validate filename to avoid directory traversal
    # Only allow coverage_covered_YYYYMMDD_HHMMSS.txt and coverage_uncovered_... patterns
    allowed_pattern = re.compile(r'^(coverage_(?:covered|uncovered)_[0-9]{8}_[0-9]{6}\.txt)$')
    match = allowed_pattern.match(filename)
    if not match:
        # If filename doesn't match the strict timestamped pattern, reject
        abort(404)

    # Use safe_join to construct the full path
    try:
        # send_from_directory will handle safe pathing but we double-check with safe_join
        safe_path = safe_join(logs_dir, filename)
        return send_from_directory(logs_dir, filename, as_attachment=True)
    except Exception as e:
        logger.exception(f"Error serving log file {filename}: {e}")
        abort(404)

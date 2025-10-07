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
                # Default: first sheet, column A, skip header
                words = sheets_service.fetch_words_from_spreadsheet(creds, spreadsheet_id=source_ref, column='A', include_header=False)
                if not words:
                    return jsonify({'error': 'No words found in the Google Sheet (column A)'}), 400
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
        spreadsheet = sheets_service.create_spreadsheet_from_sentences(
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

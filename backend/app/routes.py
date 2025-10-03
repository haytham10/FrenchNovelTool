"""API routes for the French Novel Tool"""
import json
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from marshmallow import ValidationError
from app import limiter, db
from .services.pdf_service import PDFService
from .services.gemini_service import GeminiService
from .services.google_sheets_service import GoogleSheetsService
from .services.history_service import HistoryService
from .services.user_settings_service import UserSettingsService
from .services.job_service import JobService
from .services.credit_service import CreditService
from .services.chunking_service import PDFChunkingService
from .schemas import ExportToSheetSchema, UserSettingsSchema
from .utils.validators import validate_pdf_file
from .models import User, Job
from .constants import JOB_STATUS_PENDING, JOB_STATUS_PROCESSING, ERROR_INSUFFICIENT_CREDITS
import PyPDF2

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


@main_bp.route('/extract-pdf-text', methods=['POST'])
@jwt_required()
@limiter.limit("20 per minute")
def extract_pdf_text():
    """Extract text from PDF for cost estimation (requires authentication)"""
    user_id = int(get_jwt_identity())
    user = User.query.get(user_id)
    
    if not user or not user.is_active:
        return jsonify({'error': 'User not found or inactive'}), 401
    
    if 'pdf_file' not in request.files:
        return jsonify({'error': 'No PDF file provided'}), 400

    file = request.files['pdf_file']
    
    # Validate file
    try:
        validate_pdf_file(file)
    except ValidationError as e:
        return jsonify({'error': str(e)}), 400

    pdf_service = PDFService(file)
    
    try:
        temp_file_path = pdf_service.save_to_temp()
        
        # Extract text from PDF
        text = ""
        with open(temp_file_path, 'rb') as pdf_file:
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
        
        # Return first 50000 characters for estimation (safety limit)
        text = text[:50000]
        
        return jsonify({'text': text, 'page_count': len(pdf_reader.pages)}), 200
        
    except Exception as e:
        current_app.logger.exception('Failed to extract PDF text')
        return jsonify({'error': str(e)}), 500
    finally:
        pdf_service.delete_temp_file()

@main_bp.route('/process-pdf', methods=['POST'])
@jwt_required()
@limiter.limit("10 per hour")
def process_pdf():
    """Process PDF file with credit system integration (requires authentication)"""
    # Get current user
    user_id = int(get_jwt_identity())
    user = User.query.get(user_id)
    
    if not user or not user.is_active:
        return jsonify({'error': 'User not found or inactive'}), 401
    
    # Check if job_id is provided (credit flow) or if it's direct processing (backward compatibility)
    job_id = request.form.get('job_id')
    
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
    job = None

    try:
        temp_file_path = pdf_service.save_to_temp()

        # Get user-specific settings and merge with any overrides from the request
        settings = user_settings_service.get_user_settings(user_id)

        form_data = request.form

        def _coerce_bool(value, default):
            if value is None:
                return default
            if isinstance(value, bool):
                return value
            return str(value).strip().lower() in {'1', 'true', 'yes', 'on'}

        def _coerce_int(value, default):
            try:
                return int(value)
            except (TypeError, ValueError):
                return default

        sentence_length_limit = _coerce_int(
            form_data.get('sentence_length_limit'),
            settings.get('sentence_length_limit', 8)
        )
        gemini_model = (form_data.get('gemini_model') or settings.get('gemini_model', 'balanced')).lower()
        if gemini_model not in {'balanced', 'quality', 'speed'}:
            gemini_model = 'balanced'
        ignore_dialogue = _coerce_bool(
            form_data.get('ignore_dialogue'),
            settings.get('ignore_dialogue', False)
        )
        preserve_formatting = _coerce_bool(
            form_data.get('preserve_formatting'),
            settings.get('preserve_formatting', True)
        )
        fix_hyphenation = _coerce_bool(
            form_data.get('fix_hyphenation'),
            settings.get('fix_hyphenation', True)
        )
        min_sentence_length = max(
            1,
            _coerce_int(
                form_data.get('min_sentence_length'),
                settings.get('min_sentence_length', 2)
            )
        )
        min_sentence_length = min(min_sentence_length, sentence_length_limit)

        # Store processing settings for history
        processing_settings = {
            'sentence_length_limit': sentence_length_limit,
            'gemini_model': gemini_model,
            'ignore_dialogue': ignore_dialogue,
            'preserve_formatting': preserve_formatting,
            'fix_hyphenation': fix_hyphenation,
            'min_sentence_length': min_sentence_length,
        }

        # If job_id provided, verify and update job status
        if job_id:
            job = Job.query.get(int(job_id))
            if not job or job.user_id != user_id:
                return jsonify({'error': 'Job not found or unauthorized'}), 404
            
            if job.status != JOB_STATUS_PENDING:
                return jsonify({'error': f'Job is in {job.status} status, cannot process'}), 400
        
        # Check if file should be processed asynchronously
        chunking_service = PDFChunkingService(temp_file_path)
        use_async = chunking_service.should_chunk()
        
        if use_async:
            # Large file - process asynchronously
            current_app.logger.info(
                f'Large PDF detected ({chunking_service.total_pages} pages), '
                f'using async processing for job {job_id if job else "new"}'
            )
            
            # Start async task
            from app.tasks import process_pdf_async
            
            # If no job was created yet, we need to create one
            if not job:
                # For backward compatibility, create a job if not provided
                estimated_tokens = JobService.estimate_tokens_heuristic(
                    chunking_service.extract_text_from_chunk(0, min(10, chunking_service.total_pages))
                )
                job = JobService.create_job(
                    user_id=user_id,
                    original_filename=original_filename,
                    model_preference=gemini_model,
                    estimated_tokens=estimated_tokens * (chunking_service.total_pages // 10 + 1),
                    processing_settings=processing_settings
                )
            
            # Update job to processing status
            JobService.start_job(job.id)
            
            # Submit async task
            task = process_pdf_async.apply_async(
                args=[user_id, job.id, temp_file_path, original_filename, processing_settings],
                task_id=f'job_{job.id}'
            )
            
            # Update job with task ID
            job.celery_task_id = task.id
            db.session.commit()
            
            # Don't delete temp file - the task will handle it
            pdf_service.temp_file_path = None
            
            return jsonify({
                'job_id': job.id,
                'status': 'processing',
                'async': True,
                'message': 'Large file detected. Processing asynchronously. Check job status for progress.'
            }), 202
        
        # Small file - process synchronously (existing logic)
        if job:
            JobService.start_job(job.id)

        gemini_service = GeminiService(
            sentence_length_limit=sentence_length_limit,
            model_preference=gemini_model,
            ignore_dialogue=ignore_dialogue,
            preserve_formatting=preserve_formatting,
            fix_hyphenation=fix_hyphenation,
            min_sentence_length=min_sentence_length,
        )

        # Use the built-in prompt builder
        prompt = gemini_service.build_prompt()

        # Log the processing attempt
        current_app.logger.info(f'User {user.email} attempting to process PDF: {original_filename}')
        
        # Process the PDF and get sentences
        processed_sentences = gemini_service.generate_content_from_pdf(prompt, temp_file_path)
        
        # Log successful processing
        current_app.logger.info(f'Successfully processed PDF: {original_filename}, extracted {len(processed_sentences)} sentences')
        
        # Add user-specific history entry with processing settings
        history_entry = history_service.add_entry(
            user_id=user_id,
            original_filename=original_filename,
            processed_sentences_count=len(processed_sentences),
            error_message=None,
            processing_settings=processing_settings
        )

        # If job exists, finalize it with actual token usage
        if job:
            # Get actual token count from Gemini response if available
            # For now, estimate from output
            actual_tokens = JobService.estimate_tokens_heuristic(' '.join(processed_sentences))
            
            # Complete the job
            JobService.complete_job(job.id, actual_tokens, history_entry.id)
            
            # Adjust credits based on actual usage
            CreditService.adjust_final_credits(
                user_id=user_id,
                job_id=job.id,
                reserved_amount=job.estimated_credits,
                actual_amount=JobService.calculate_credits(actual_tokens, job.model)
            )
            
            # Update history entry with job_id
            history_entry.job_id = job.id
            db.session.commit()

        current_app.logger.info(f'User {user.email} processed PDF: {original_filename}')
        return jsonify({
            'sentences': processed_sentences,
            'job_id': job.id if job else None
        })

    except json.JSONDecodeError as e:
        error_message = f"Failed to parse Gemini response: {str(e)}"
        current_app.logger.exception(f'User {user.email} failed to process PDF {original_filename} due to JSON parsing error')
        
        error_code = 'GEMINI_RESPONSE_ERROR'
        failed_step = 'parse_response'
        
        # If job exists, fail it and refund credits
        if job:
            JobService.fail_job(job.id, error_message, error_code)
            CreditService.refund_credits(
                user_id=user_id,
                job_id=job.id,
                amount=job.estimated_credits,
                description=f'Refund for failed job: {error_message}'
            )
        
        # Add error to user's history
        history_service.add_entry(
            user_id=user_id,
            original_filename=original_filename,
            processed_sentences_count=0,
            error_message=error_message,
            failed_step=failed_step,
            error_code=error_code
        )
        # Return a 422 status code for processing errors (Unprocessable Entity)
        return jsonify({
            'error': error_message,
            'error_code': error_code,
            'message': 'The PDF was processed, but we had trouble interpreting the results from our AI. Please try again or use a different PDF file.'
        }), 422
        
    except Exception as e:
        error_message = str(e)
        current_app.logger.exception(f'User {user.email} failed to process PDF {original_filename}')
        
        # Determine error code and failed step
        error_code = 'PROCESSING_ERROR'
        failed_step = 'normalize'
        
        if 'Gemini' in error_message or 'API' in error_message:
            error_code = 'GEMINI_API_ERROR'
        elif 'PDF' in error_message:
            error_code = 'INVALID_PDF'
            failed_step = 'extract'
        elif 'rate limit' in error_message.lower():
            error_code = 'RATE_LIMIT_EXCEEDED'
        
        # If job exists, fail it and refund credits
        if job:
            JobService.fail_job(job.id, error_message, error_code)
            CreditService.refund_credits(
                user_id=user_id,
                job_id=job.id,
                amount=job.estimated_credits,
                description=f'Refund for failed job: {error_message}'
            )
            
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



@main_bp.route('/jobs/<int:job_id>', methods=['GET'])
@jwt_required()
def get_job_status(job_id):
    """
    Get status of a processing job (supports async jobs).
    Includes progress tracking for chunked processing.
    """
    user_id = int(get_jwt_identity())
    
    job = Job.query.get(job_id)
    if not job:
        return jsonify({'error': 'Job not found'}), 404
    
    if job.user_id != user_id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    response = job.to_dict()
    
    # If job is processing and has a Celery task, check task status
    if job.status == JOB_STATUS_PROCESSING and job.celery_task_id:
        try:
            from celery.result import AsyncResult
            from celery_app import celery_app
            
            task = AsyncResult(job.celery_task_id, app=celery_app)
            
            # Add task state to response
            response['task_state'] = task.state
            response['task_info'] = task.info if task.info else {}
            
        except Exception as e:
            current_app.logger.warning(f'Failed to get task status for job {job_id}: {str(e)}')
    
    # If job is completed, include the result
    if job.status == 'completed' and job.history_id:
        from .models import History
        history = History.query.get(job.history_id)
        if history:
            response['result_url'] = f'/history/{history.id}'
    
    return jsonify(response), 200


@main_bp.route('/jobs/<int:job_id>/cancel', methods=['POST'])
@jwt_required()
def cancel_job(job_id):
    """Cancel a pending or processing job"""
    user_id = int(get_jwt_identity())
    
    job = Job.query.get(job_id)
    if not job:
        return jsonify({'error': 'Job not found'}), 404
    
    if job.user_id != user_id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    if job.status not in [JOB_STATUS_PENDING, JOB_STATUS_PROCESSING]:
        return jsonify({'error': f'Cannot cancel job in {job.status} status'}), 400
    
    try:
        # If job has a Celery task, revoke it
        if job.celery_task_id:
            from celery_app import celery_app
            celery_app.control.revoke(job.celery_task_id, terminate=True)
        
        # Cancel the job and refund credits
        JobService.cancel_job(job_id)
        CreditService.refund_credits(
            user_id=user_id,
            job_id=job_id,
            amount=job.estimated_credits,
            description='Refund for cancelled job'
        )
        
        return jsonify({'message': 'Job cancelled successfully'}), 200
        
    except Exception as e:
        current_app.logger.exception(f'Failed to cancel job {job_id}')
        return jsonify({'error': str(e)}), 500


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
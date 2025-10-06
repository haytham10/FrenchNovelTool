"""Celery tasks for asynchronous PDF processing"""
import logging
import os
from datetime import datetime
from typing import Dict, List
from typing import Optional
import base64
import tempfile
from app.pdf_compat import PdfReader
from celery import group, chord
from celery.exceptions import SoftTimeLimitExceeded

logger = logging.getLogger(__name__)

def get_celery():
    """Get celery instance (deferred import to avoid circular dependency)"""
    from app import celery
    # If the application hasn't initialised Celery (e.g., during unit tests
    # where create_app() isn't called), provide a lightweight stub that
    # supports the `.task` decorator used at module import time.
    if celery is None:
        class _DummyCelery:
            def task(self, *args, **kwargs):
                def decorator(func):
                    return func
                return decorator
        return _DummyCelery()
    return celery


def get_db():
    """Get database instance with connection retry logic"""
    from app import db
    return db


def emit_progress(job_id: int):
    """Emit job progress via WebSocket (deferred import to avoid circular dependency)"""
    try:
        from app.socket_events import emit_job_progress
        emit_job_progress(job_id)
    except Exception as e:
        logger.warning(f"Failed to emit WebSocket progress for job {job_id}: {e}")


def safe_db_commit(db, max_retries=3, retry_delay=1):
    """
    Safely commit database changes with retry logic for cloud databases.
    
    Handles transient network errors common with Supabase/Railway deployments.
    
    Args:
        db: SQLAlchemy database instance
        max_retries: Maximum number of commit attempts
        retry_delay: Delay between retries in seconds
        
    Returns:
        bool: True if commit succeeded, False otherwise
    """
    import time
    from sqlalchemy.exc import OperationalError, DBAPIError
    
    for attempt in range(max_retries):
        try:
            db.session.commit()
            return True
        except (OperationalError, DBAPIError) as e:
            db.session.rollback()
            if attempt < max_retries - 1:
                # Transient error - retry
                time.sleep(retry_delay * (attempt + 1))  # Exponential backoff
                continue
            else:
                # Max retries exceeded
                raise
    return False


def get_models():
    """Get models (deferred import)"""
    from app.models import Job, User
    return Job, User


def get_services():
    """Get services (deferred import)"""
    from app.services.pdf_service import PDFService
    from app.services.gemini_service import GeminiService
    from app.services.chunking_service import ChunkingService
    from app.services.job_service import JobService
    return PDFService, GeminiService, ChunkingService, JobService


def get_constants():
    """Get constants (deferred import)"""
    from app.constants import (
        JOB_STATUS_PROCESSING, JOB_STATUS_COMPLETED, JOB_STATUS_FAILED,
        MODEL_PREFERENCE_MAP
    )
    return JOB_STATUS_PROCESSING, JOB_STATUS_COMPLETED, JOB_STATUS_FAILED, MODEL_PREFERENCE_MAP


@get_celery().task(bind=True, name='app.tasks.process_chunk')
def process_chunk(self, chunk_info: Dict, user_id: int, settings: Dict) -> Dict:
    """
    Process a single PDF chunk with DB-backed state tracking.
    
    Args:
        chunk_info: Chunk metadata from JobChunk.get_chunk_metadata() or legacy dict
        user_id: User who initiated the job
        settings: Processing settings
        
    Returns:
        Dictionary with processed results:
        {
            'chunk_id': int,
            'sentences': [...],
            'tokens': int,
            'start_page': int,
            'end_page': int,
            'status': 'success' | 'failed',
            'error': str (if failed)
        }
    """
    db = get_db()
    chunk_db_record = None
    
    # Try to load JobChunk from DB if job_id provided
    job_id = chunk_info.get('job_id')
    chunk_id = chunk_info.get('chunk_id')
    
    if job_id is not None and chunk_id is not None:
        try:
            from app.models import JobChunk
            chunk_db_record = JobChunk.query.filter_by(
                job_id=job_id, 
                chunk_id=chunk_id
            ).first()
            
            if chunk_db_record:
                # Update status to processing
                chunk_db_record.status = 'processing'
                chunk_db_record.celery_task_id = self.request.id
                chunk_db_record.attempts += 1
                chunk_db_record.updated_at = datetime.utcnow()
                safe_db_commit(db)
                # Schedule a per-chunk watchdog to detect stuck processing tasks.
                try:
                    from flask import current_app
                    watchdog_seconds = int(current_app.config.get('CHUNK_WATCHDOG_SECONDS', 1800))
                    # Use delayed call to chunk_watchdog which will check DB state
                    # and either schedule a retry or mark the chunk failed.
                    try:
                        chunk_watchdog.apply_async(args=[chunk_db_record.job_id, chunk_db_record.chunk_id], countdown=watchdog_seconds)
                        logger.info(
                            "Scheduled chunk_watchdog for job %s chunk %s in %ss",
                            chunk_db_record.job_id, chunk_db_record.chunk_id, watchdog_seconds
                        )
                    except Exception as _e:
                        logger.warning("Failed to schedule chunk_watchdog for job %s chunk %s: %s", chunk_db_record.job_id, chunk_db_record.chunk_id, _e)
                except Exception:
                    # Non-fatal if config or scheduler not available
                    pass
        except Exception as e:
            logger.warning(f"Failed to load/update JobChunk for job={job_id} chunk={chunk_id}: {e}")
    
    try:
        # Get services
        _, GeminiService, _, _ = get_services()
        
        # Initialize services
        gemini_service = GeminiService(
            sentence_length_limit=settings['sentence_length_limit'],
            model_preference=settings['gemini_model'],
            ignore_dialogue=settings.get('ignore_dialogue', False),
            preserve_formatting=settings.get('preserve_formatting', True),
            fix_hyphenation=settings.get('fix_hyphenation', True),
            min_sentence_length=settings.get('min_sentence_length', 2),
        )
        
        # Extract text from chunk. Prefer in-memory base64 chunk data
        # (produced by ChunkingService) so workers do not rely on a shared
        # filesystem. Fallback to chunk_info['file_path'] when provided.
        text = ""
        if chunk_info.get('file_b64'):
            import io
            chunk_bytes = base64.b64decode(chunk_info['file_b64'])
            pdf_file = io.BytesIO(chunk_bytes)
            pdf_reader = PdfReader(pdf_file)
            for page in pdf_reader.pages:
                text += (page.extract_text() or "") + "\n"
        else:
            # Fallback to file path if present
            with open(chunk_info['file_path'], 'rb') as pdf_file:
                pdf_reader = PdfReader(pdf_file)
                for page in pdf_reader.pages:
                    text += (page.extract_text() or "") + "\n"
        
        # If no extractable text, fail this chunk early
        if not text.strip():
            # Cleanup chunk file before returning
            try:
                if os.path.exists(chunk_info['file_path']):
                    os.remove(chunk_info['file_path'])
            except Exception:
                pass
            
            error_result = {
                'chunk_id': chunk_info['chunk_id'],
                'status': 'failed',
                'error': 'No extractable text in PDF chunk (may be scanned/images only).',
                'start_page': chunk_info['start_page'],
                'end_page': chunk_info['end_page']
            }
            
            # Persist error to DB chunk record
            if chunk_db_record:
                try:
                    chunk_db_record.status = 'failed'
                    chunk_db_record.last_error = 'No extractable text in PDF chunk'
                    chunk_db_record.last_error_code = 'NO_TEXT'
                    chunk_db_record.updated_at = datetime.utcnow()
                    safe_db_commit(db)
                except Exception as e:
                    logger.warning(f"Failed to persist chunk error to DB: {e}")
            
            return error_result

        # Process with Gemini
        prompt = gemini_service.build_prompt()

        # Log basic chunk metadata before calling Gemini (avoid large text dumps)
        logger.info(
            "Processing chunk %s (job %s) pages=%s-%s page_count=%s text_len=%s",
            chunk_info.get('chunk_id'), chunk_info.get('job_id'), chunk_info.get('start_page'),
            chunk_info.get('end_page'), chunk_info.get('page_count'), (len(text) if text else 0),
        )
        
        # Process with Gemini (includes intelligent retry cascade)
        result = gemini_service.normalize_text(text, prompt)
        
        # Check if a fallback method was used and persist marker to DB
        fallback_method = result.get('_fallback_method')
        if fallback_method and chunk_db_record:
            try:
                # Map fallback method to error code for DB tracking
                if 'local_segmentation' in fallback_method:
                    error_code = 'GEMINI_LOCAL_FALLBACK'
                    error_msg = 'All Gemini retries failed; local fallback used'
                elif 'subchunk' in fallback_method:
                    error_code = 'GEMINI_SUBCHUNK_FALLBACK'
                    error_msg = f'Gemini succeeded via subchunk splitting'
                elif 'minimal_prompt' in fallback_method:
                    error_code = 'GEMINI_MINIMAL_PROMPT_FALLBACK'
                    error_msg = f'Gemini succeeded with minimal prompt'
                elif 'model_fallback' in fallback_method:
                    error_code = 'GEMINI_MODEL_FALLBACK'
                    error_msg = f'Gemini succeeded with model fallback: {fallback_method}'
                else:
                    error_code = 'GEMINI_FALLBACK'
                    error_msg = f'Gemini fallback method: {fallback_method}'
                
                chunk_db_record.last_error = error_msg[:1000]
                chunk_db_record.last_error_code = error_code
                chunk_db_record.updated_at = datetime.utcnow()
                safe_db_commit(db)
                logger.info(
                    'Chunk %s (job %s) processed with fallback: %s',
                    chunk_info.get('chunk_id'), chunk_info.get('job_id'), fallback_method
                )
            except Exception:
                logger.warning('Failed to persist fallback marker for chunk %s', chunk_info.get('chunk_id'))
        
        # Cleanup chunk file after processing only if a filesystem path was used
        try:
            fp = chunk_info.get('file_path')
            if fp and os.path.exists(fp):
                os.remove(fp)
        except Exception as e:
            logger.warning(f"Failed to cleanup chunk file {chunk_info.get('file_path')}: {e}")

        # Build result dict
        result_dict = {
            'chunk_id': chunk_info['chunk_id'],
            'sentences': result['sentences'],
            'tokens': result.get('tokens', 0),
            'start_page': chunk_info['start_page'],
            'end_page': chunk_info['end_page'],
            'status': 'success'
        }
        
        # Persist result to DB chunk record if available
        if chunk_db_record:
            try:
                chunk_db_record.status = 'success'
                chunk_db_record.result_json = result_dict
                chunk_db_record.processed_at = datetime.utcnow()
                chunk_db_record.updated_at = datetime.utcnow()
                chunk_db_record.last_error = None
                chunk_db_record.last_error_code = None
                safe_db_commit(db)
            except Exception as e:
                logger.warning(f"Failed to persist chunk result to DB: {e}")

        # On successful chunk processing, increment the job's processed_chunks
        # atomically and emit progress so the frontend progress bar advances.
        try:
            job_id = chunk_info.get('job_id')
            if job_id:
                db = get_db()
                Job, _ = get_models()
                # Use a simple atomic SQL increment to avoid race conditions
                from sqlalchemy import text
                db.session.execute(text("UPDATE jobs SET processed_chunks = COALESCE(processed_chunks,0) + 1 WHERE id = :id"), {"id": job_id})
                # Reload job to compute new progress
                job = Job.query.get(job_id)
                if job and job.total_chunks:
                    start_pct = 15
                    end_pct = 75
                    try:
                        pct = start_pct + int((job.processed_chunks / float(job.total_chunks)) * (end_pct - start_pct))
                    except Exception:
                        pct = start_pct
                    job.progress_percent = min(100, max(0, pct))
                    job.current_step = f"Processing chunks ({job.processed_chunks}/{job.total_chunks})"
                    safe_db_commit(db)
                    emit_progress(job_id)
        except Exception as e:
            logger.warning(f"Failed to update job progress for job {chunk_info.get('job_id')}: {e}")

        return result_dict
        
    except SoftTimeLimitExceeded:
        # Cleanup chunk file before returning
        try:
            fp = chunk_info.get('file_path')
            if fp and os.path.exists(fp):
                os.remove(fp)
        except Exception:
            pass
        
        error_result = {
            'chunk_id': chunk_info['chunk_id'],
            'status': 'failed',
            'error': 'Processing timeout exceeded',
            'start_page': chunk_info['start_page'],
            'end_page': chunk_info['end_page']
        }
        
        # Persist error to DB chunk record
        if chunk_db_record:
            try:
                chunk_db_record.status = 'failed'
                chunk_db_record.last_error = 'Processing timeout exceeded'
                chunk_db_record.last_error_code = 'TIMEOUT'
                chunk_db_record.updated_at = datetime.utcnow()
                safe_db_commit(db)
            except Exception as e:
                logger.warning(f"Failed to persist chunk error to DB: {e}")
        
        return error_result
    except Exception as e:
        # Decide whether to retry on transient errors
        from flask import current_app

        def _is_transient(err: Exception) -> bool:
            transient_types = (TimeoutError, ConnectionError)
            try:
                import requests  # type: ignore
                transient_types = transient_types + (requests.exceptions.RequestException,)
            except Exception:
                pass
            # Also check by class name to avoid importing optional libs
            name = err.__class__.__name__.lower()
            msg = str(err).lower()
            retryable_by_name = any(k in name for k in [
                'timeout', 'temporarilyunavailable', 'serviceunavailable', 'toomanyrequests', 'ratelimit', 'deadline'
            ])
            retryable_by_msg = any(k in msg for k in [
                'timeout', 'temporary', 'try again', 'rate limit', '429', 'unavailable', 'deadline'
            ])
            return isinstance(err, transient_types) or retryable_by_name or retryable_by_msg

        max_retries = int(current_app.config.get('CHUNK_TASK_MAX_RETRIES', current_app.config.get('GEMINI_MAX_RETRIES', 3)))
        base_delay = int(current_app.config.get('CHUNK_TASK_RETRY_DELAY', current_app.config.get('GEMINI_RETRY_DELAY', 1)))

        if _is_transient(e) and self.request.retries < max_retries:
            # Exponential backoff with jitter-like cap
            delay = min(base_delay * (2 ** self.request.retries), 60)
            logger.warning(
                "Chunk %s transient error, scheduling retry %s/%s in %ss: %s",
                chunk_info.get('chunk_id'), self.request.retries + 1, max_retries, delay, e
            )
            # Do NOT cleanup the file_path if present; we want it available for the retry
            raise self.retry(exc=e, countdown=delay, max_retries=max_retries)

        # Non-transient or retries exhausted: cleanup and return failed
        try:
            fp = chunk_info.get('file_path')
            if fp and os.path.exists(fp):
                os.remove(fp)
        except Exception:
            pass

        error_result = {
            'chunk_id': chunk_info['chunk_id'],
            'status': 'failed',
            'error': str(e),
            'start_page': chunk_info['start_page'],
            'end_page': chunk_info['end_page']
        }
        
        # Persist error to DB chunk record (mark as failed permanently)
        if chunk_db_record:
            try:
                chunk_db_record.status = 'failed'
                chunk_db_record.last_error = str(e)[:1000]  # Limit error length
                # Try to extract error code
                error_code = 'PROCESSING_ERROR'
                if 'timeout' in str(e).lower():
                    error_code = 'TIMEOUT'
                elif 'api' in str(e).lower() or 'gemini' in str(e).lower():
                    error_code = 'API_ERROR'
                elif 'rate limit' in str(e).lower():
                    error_code = 'RATE_LIMIT'
                chunk_db_record.last_error_code = error_code
                chunk_db_record.updated_at = datetime.utcnow()
                safe_db_commit(db)
            except Exception as db_err:
                logger.warning(f"Failed to persist chunk error to DB: {db_err}")
        
        return error_result


def merge_chunk_results(chunk_results: List[Dict]) -> List[Dict]:
    """
    Merge results from multiple chunks, handling overlap deduplication.
    
    Args:
        chunk_results: List of chunk results from process_chunk
        
    Returns:
        Merged list of sentences
    """
    # Sort chunks by chunk_id
    sorted_chunks = sorted(chunk_results, key=lambda x: x.get('chunk_id', 0))
    
    all_sentences = []
    seen_sentences = set()  # For deduplication
    
    for chunk in sorted_chunks:
        if chunk.get('status') != 'success':
            continue
        
        sentences = chunk.get('sentences', [])
        
        # For chunks with overlap, deduplicate sentences
        if chunk.get('chunk_id', 0) > 0:
            # Skip first few sentences that might be duplicates from overlap
            # Simple heuristic: skip sentences we've already seen
            for sentence in sentences:
                sentence_key = sentence.get('normalized', '')[:100]  # Use first 100 chars as key
                if sentence_key and sentence_key not in seen_sentences:
                    all_sentences.append(sentence)
                    seen_sentences.add(sentence_key)
        else:
            # First chunk: add all sentences
            for sentence in sentences:
                all_sentences.append(sentence)
                sentence_key = sentence.get('normalized', '')[:100]
                if sentence_key:
                    seen_sentences.add(sentence_key)
    
    return all_sentences


@get_celery().task(bind=True, name='app.tasks.finalize_job_results')
def finalize_job_results(self, chunk_results, job_id):
    """
    Finalize job after all chunks complete (chord callback).
    Implements automatic retry orchestration for failed chunks.
    
    Args:
        chunk_results: List of results from all process_chunk tasks
        job_id: Job ID to finalize
    """
    db = get_db()
    Job, User = get_models()
    from app.models import JobChunk
    JOB_STATUS_PROCESSING, JOB_STATUS_COMPLETED, JOB_STATUS_FAILED, _ = get_constants()
    
    try:
        logger.info(f"Job {job_id}: finalizing {len(chunk_results)} chunk results")
        
        # Load job and short-circuit if it's already finalized to make this idempotent
        job = Job.query.get(job_id)
        if job and job.status in (JOB_STATUS_COMPLETED, JOB_STATUS_FAILED):
            logger.info(f"Job {job_id}: already finalized with status={job.status}; skipping finalization")
            return {'status': 'already_finalized', 'job_id': job_id, 'final_status': job.status}

        # Load all chunks from DB to get latest state
        db_chunks = JobChunk.query.filter_by(job_id=job_id).order_by(JobChunk.chunk_id).all()
        
        # CRITICAL: Check if all chunks have reached a terminal state
        # If any chunks are still 'pending' or 'processing', we cannot finalize yet
        if db_chunks:
            non_terminal_chunks = [
                chunk for chunk in db_chunks 
                if chunk.status in ('pending', 'processing', 'retry_scheduled')
            ]
            
            if non_terminal_chunks:
                from flask import current_app
                max_finalize_retries = int(current_app.config.get('FINALIZE_MAX_RETRIES', 10))
                finalize_retry_delay = int(current_app.config.get('FINALIZE_RETRY_DELAY', 30))
                
                if self.request.retries < max_finalize_retries:
                    logger.warning(
                        f"Job {job_id}: {len(non_terminal_chunks)} chunks still in non-terminal state "
                        f"(statuses: {[c.status for c in non_terminal_chunks[:5]]}). "
                        f"Retrying finalization in {finalize_retry_delay}s (attempt {self.request.retries + 1}/{max_finalize_retries})"
                    )
                    raise self.retry(countdown=finalize_retry_delay, max_retries=max_finalize_retries)
                else:
                    # Max retries exceeded - force finalize with whatever we have
                    logger.error(
                        f"Job {job_id}: {len(non_terminal_chunks)} chunks still non-terminal after {max_finalize_retries} retries. "
                        f"Force-finalizing with available results. Non-terminal chunks: {[c.chunk_id for c in non_terminal_chunks]}"
                    )
                    # Mark stuck chunks as failed so they don't block finalization
                    for chunk in non_terminal_chunks:
                        chunk.status = 'failed'
                        chunk.last_error = 'Chunk stuck in processing state - force-finalized'
                        chunk.last_error_code = 'FINALIZE_TIMEOUT'
                        chunk.updated_at = datetime.utcnow()
                    safe_db_commit(db)
        
        # Build chunk results from DB if available, else use in-memory results
        if db_chunks:
            logger.info(f"Job {job_id}: loaded {len(db_chunks)} chunks from DB for finalization")
            chunk_results_final = []
            for chunk in db_chunks:
                if chunk.result_json:
                    # Use persisted result from DB
                    chunk_results_final.append(chunk.result_json)
                else:
                    # Find matching in-memory result
                    mem_result = next((r for r in chunk_results if r.get('chunk_id') == chunk.chunk_id), None)
                    if mem_result:
                        chunk_results_final.append(mem_result)
                    else:
                        # Chunk has no result - treat as failed
                        chunk_results_final.append({
                            'chunk_id': chunk.chunk_id,
                            'status': 'failed',
                            'error': chunk.last_error or 'No result available',
                            'start_page': chunk.start_page,
                            'end_page': chunk.end_page
                        })
            chunk_results = chunk_results_final
        
        # Merge chunk results
        all_sentences = merge_chunk_results(chunk_results)
        
        # Calculate metrics
        total_tokens = sum(r.get('tokens', 0) for r in chunk_results if r.get('status') == 'success')
        failed_chunks = [r['chunk_id'] for r in chunk_results if r.get('status') == 'failed']
        success_count = len([r for r in chunk_results if r.get('status') == 'success'])
        
        # Get job and check retry eligibility
        job = Job.query.get(job_id)
        if not job:
            raise ValueError(f"Job {job_id} not found")
        
        # Check if we should retry failed chunks automatically
        should_retry = False
        chunks_to_retry = []
        
        if failed_chunks and job.retry_count < job.max_retries:
            # Get failed chunks that can be retried from DB
            if db_chunks:
                for chunk in db_chunks:
                    if chunk.status == 'failed' and chunk.can_retry():
                        chunks_to_retry.append(chunk)
                        should_retry = True
        
        if should_retry and chunks_to_retry:
            # Orchestrate automatic retry round
            logger.info(f"Job {job_id}: starting retry round {job.retry_count + 1}/{job.max_retries} for {len(chunks_to_retry)} chunks")
            
            # Update job retry count
            job.retry_count += 1
            job.current_step = f"Retrying {len(chunks_to_retry)} failed chunks (attempt {job.retry_count}/{job.max_retries})"
            
            # Mark chunks as retry_scheduled
            retry_tasks = []
            settings = job.processing_settings or {}
            
            for chunk in chunks_to_retry:
                chunk.status = 'retry_scheduled'
                chunk.updated_at = datetime.utcnow()
                db.session.add(chunk)
                retry_tasks.append(
                    process_chunk.s(chunk.get_chunk_metadata(), job.user_id, settings)
                )
            
            safe_db_commit(db)
            emit_progress(job_id)
            
            # Dispatch retry tasks with new finalization callback
            from celery import group, chord
            callback = finalize_job_results.s(job_id=job_id)
            chord(retry_tasks)(callback)
            
            logger.info(f"Job {job_id}: dispatched {len(retry_tasks)} retry tasks")
            return {
                'status': 'retrying',
                'message': f'Retrying {len(chunks_to_retry)} failed chunks',
                'retry_round': job.retry_count
            }
        
        # No more retries - finalize job with current results
        if success_count == 0:
            job.status = JOB_STATUS_FAILED
            job.current_step = "Failed"
            job.error_message = "All chunks failed to process. Check API credentials or PDF content."
            # Add detailed failure reasons to the logs for diagnostics
            for r in chunk_results:
                logger.error("Job %s: chunk %s failed with error: %s", job_id, r.get('chunk_id'), r.get('error'))
        else:
            job.status = JOB_STATUS_COMPLETED
            job.current_step = "Completed"
        
        job.progress_percent = 100
        job.processed_chunks = len(chunk_results)
        job.actual_tokens = total_tokens
        job.gemini_tokens_used = total_tokens
        job.gemini_api_calls = success_count
        job.completed_at = datetime.utcnow()
        job.chunk_results = chunk_results
        job.failed_chunks = failed_chunks if failed_chunks else None
        
        # Calculate processing time
        if job.started_at:
            processing_time = (job.completed_at - job.started_at).total_seconds()
            job.processing_time_seconds = int(processing_time)
        
        # Create History entry for completed/partial jobs with results
        if success_count > 0:
            try:
                from app.models import History
                
                # Format sentences for History storage
                formatted_sentences = []
                for sentence in all_sentences:
                    if isinstance(sentence, dict):
                        formatted_sentences.append({
                            'normalized': sentence.get('normalized', ''),
                            'original': sentence.get('original', sentence.get('normalized', ''))
                        })
                    else:
                        formatted_sentences.append({
                            'normalized': str(sentence),
                            'original': str(sentence)
                        })
                
                # Collect chunk IDs for drill-down
                chunk_ids = [chunk.id for chunk in db_chunks] if db_chunks else []
                
                # Create history entry
                history_entry = History(
                    user_id=job.user_id,
                    job_id=job.id,
                    original_filename=job.original_filename,
                    processed_sentences_count=len(all_sentences),
                    sentences=formatted_sentences,
                    processing_settings=job.processing_settings,
                    exported_to_sheets=False,
                    spreadsheet_url=None,
                    export_sheet_url=None,
                    chunk_ids=chunk_ids
                )
                db.session.add(history_entry)
                db.session.flush()  # Get history.id
                
                # Link job to history
                job.history_id = history_entry.id
                safe_db_commit(db)
                
                logger.info(f"Job {job_id}: created history entry {history_entry.id} with {len(all_sentences)} sentences and {len(chunk_ids)} chunks")
            except Exception as hist_err:
                logger.error(f"Job {job_id}: failed to create history entry: {hist_err}")
                # Don't fail the job if history creation fails
        
        safe_db_commit(db)
        
        # Emit final WebSocket update
        emit_progress(job_id)
        
        logger.info(f"Job {job_id}: finalized status={job.status} sentences={len(all_sentences)}")
        
        return {
            'status': 'success',
            'sentences': all_sentences,
            'total_tokens': total_tokens,
            'chunks_processed': len(chunk_results),
            'failed_chunks': failed_chunks
        }
        
    except Exception as e:
        logger.error(f"Job {job_id}: finalization failed: {e}")
        
        # Mark job as failed
        try:
            job = Job.query.get(job_id)
            if job:
                job.status = JOB_STATUS_FAILED
                job.error_message = f"Finalization error: {str(e)[:512]}"
                job.completed_at = datetime.utcnow()
                safe_db_commit(db)
                emit_progress(job_id)
        except Exception:
            pass
        
        raise


@get_celery().task(bind=True, name='app.tasks.chunk_watchdog')
def chunk_watchdog(self, job_id: int, chunk_id: int):
    """Watchdog for individual chunk processing. If a chunk remains in
    'processing' state beyond the configured timeout, this task will either
    schedule a retry (if attempts < max_retries) or mark the chunk as failed
    so that finalization won't hang indefinitely.

    This task is scheduled from `process_chunk` when the chunk DB record is
    updated to 'processing'.
    """
    db = get_db()
    from app.models import JobChunk
    from flask import current_app

    try:
        chunk = JobChunk.query.filter_by(job_id=job_id, chunk_id=chunk_id).first()
        if not chunk:
            logger.warning("chunk_watchdog: chunk not found job=%s chunk=%s", job_id, chunk_id)
            return {'status': 'not_found'}

        # Only act if still in a non-terminal processing state
        if chunk.status not in ('processing', 'pending', 'retry_scheduled'):
            logger.info("chunk_watchdog: chunk %s/%s in terminal state '%s', no action", job_id, chunk_id, chunk.status)
            return {'status': 'ok', 'reason': 'terminal_state'}

        # Determine retry policy
        max_retries = int(current_app.config.get('CHUNK_TASK_MAX_RETRIES', 3))
        retry_delay = int(current_app.config.get('CHUNK_TASK_RETRY_DELAY', 2))

        if chunk.attempts < chunk.max_retries and chunk.attempts < max_retries:
            # Schedule a retry by marking the chunk for retry and dispatching process_chunk
            try:
                chunk.status = 'retry_scheduled'
                chunk.updated_at = datetime.utcnow()
                db.session.add(chunk)
                safe_db_commit(db)

                # Dispatch a retry attempt
                from app.tasks import process_chunk as process_chunk_task
                process_chunk_task.apply_async(args=[chunk.get_chunk_metadata(), chunk.job.user_id, (chunk.job.processing_settings or {})], countdown=retry_delay)

                logger.info("chunk_watchdog: scheduled retry for job %s chunk %s (attempts=%s)", job_id, chunk_id, chunk.attempts)
                return {'status': 'retry_scheduled'}
            except Exception as e:
                logger.error("chunk_watchdog: failed to schedule retry for job %s chunk %s: %s", job_id, chunk_id, e)
                # Fall through to marking failed

        # No retries left or scheduling failed: mark as failed so finalizer can proceed
        try:
            chunk.status = 'failed'
            chunk.last_error = 'Chunk stuck in processing - watchdog marked failed'
            chunk.last_error_code = 'WATCHDOG_FORCED_FAIL'
            chunk.updated_at = datetime.utcnow()
            db.session.add(chunk)
            safe_db_commit(db)
            logger.error("chunk_watchdog: marked job %s chunk %s as failed (no retries left)", job_id, chunk_id)
            return {'status': 'failed_marked'}
        except Exception as e:
            logger.error("chunk_watchdog: failed to mark chunk as failed for job %s chunk %s: %s", job_id, chunk_id, e)
            return {'status': 'error', 'error': str(e)}
    except Exception as exc:
        logger.exception("chunk_watchdog: unexpected error for job %s chunk %s: %s", job_id, chunk_id, exc)
        return {'status': 'error', 'error': str(exc)}


@get_celery().task(bind=True, name='app.tasks.reconcile_stuck_chunks')
def reconcile_stuck_chunks(self, age_seconds: Optional[int] = None, limit: int = 100):
    """Scan JobChunk rows for long-running 'processing' states and heal them.
    If age_seconds is None, use CHUNK_STUCK_THRESHOLD_SECONDS from config.
    Returns a summary dict of actions taken.
    """
    db = get_db()
    from app.models import JobChunk, Job
    from flask import current_app
    import time

    try:
        threshold = int(age_seconds or current_app.config.get('CHUNK_STUCK_THRESHOLD_SECONDS', 900))
        cutoff = datetime.utcnow().timestamp() - int(threshold)

        # Find stuck chunks
        stuck = db.session.execute(
            "SELECT id, job_id, chunk_id, status, attempts, updated_at FROM job_chunks WHERE status = 'processing' ORDER BY updated_at LIMIT :limit",
            {'limit': limit}
        ).fetchall()

        actions = []
        for row in stuck:
            chunk_id_db, job_id_db, chunk_num, status, attempts, updated_at = row
            # Compute age
            age = (datetime.utcnow() - updated_at).total_seconds() if updated_at else None
            if age is None or age < threshold:
                continue

            # Load ORM object to modify
            chunk = JobChunk.query.get(chunk_id_db)
            if not chunk:
                continue

            # If retry remains, schedule a retry (similar logic as chunk_watchdog)
            max_retries = int(current_app.config.get('CHUNK_TASK_MAX_RETRIES', 3))
            if chunk.attempts < chunk.max_retries and chunk.attempts < max_retries:
                chunk.status = 'retry_scheduled'
                chunk.updated_at = datetime.utcnow()
                db.session.add(chunk)
                safe_db_commit(db)
                from app.tasks import process_chunk as process_chunk_task
                process_chunk_task.apply_async(args=[chunk.get_chunk_metadata(), chunk.job.user_id, (chunk.job.processing_settings or {})], countdown=5)
                actions.append({'chunk_id': chunk.chunk_id, 'job_id': chunk.job_id, 'action': 'retry_scheduled'})
            else:
                chunk.status = 'failed'
                chunk.last_error = 'Reconciler: marked stuck chunk failed'
                chunk.last_error_code = 'RECONCILE_FAIL'
                chunk.updated_at = datetime.utcnow()
                db.session.add(chunk)
                safe_db_commit(db)
                actions.append({'chunk_id': chunk.chunk_id, 'job_id': chunk.job_id, 'action': 'marked_failed'})

        logger.info('Reconciled stuck chunks: %s', actions)
        return {'status': 'ok', 'actions': actions}
    except Exception as e:
        logger.exception('reconcile_stuck_chunks: failed: %s', e)
        return {'status': 'error', 'error': str(e)}


@get_celery().task(bind=True, name='app.tasks.process_pdf_async')
def process_pdf_async(self, job_id: int, file_path: str, user_id: int, settings: dict, file_b64: Optional[str] = None):
    """
    Process PDF asynchronously with chunking and progress tracking.
    
    Args:
        job_id: Database job ID
        file_path: Path to uploaded PDF in temp storage
        user_id: User who initiated the job
        settings: Processing settings (model, length limit, etc.)
    """
    # Get imports
    db = get_db()
    Job, User = get_models()
    reconstructed_path: Optional[str] = None
    _, _, ChunkingService, _ = get_services()
    JOB_STATUS_PROCESSING, JOB_STATUS_COMPLETED, JOB_STATUS_FAILED, _ = get_constants()
    
    chunking_service = ChunkingService()
    job = None
    chunks = []
    
    try:
        # Update job status to processing
        job = Job.query.get(job_id)
        if not job:
            raise ValueError(f"Job {job_id} not found")
        
        # Check if job was cancelled
        if job.is_cancelled:
            job.status = JOB_STATUS_FAILED
            job.error_message = "Job cancelled by user"
            safe_db_commit(db)
            return {'status': 'cancelled'}
        
        job.status = JOB_STATUS_PROCESSING
        job.started_at = datetime.utcnow()
        job.current_step = "Analyzing PDF"
        job.progress_percent = 5
        safe_db_commit(db)
        emit_progress(job_id)
        
        # Calculate chunks
        # Ensure file exists in this container; reconstruct if needed
        if not os.path.exists(file_path):
            if not file_b64:
                raise FileNotFoundError(f"File not found and no file_b64 provided: {file_path}")
            fd, reconstructed_path = tempfile.mkstemp(suffix='.pdf')
            os.close(fd)
            with open(reconstructed_path, 'wb') as _wf:
                _wf.write(base64.b64decode(file_b64))
            file_path = reconstructed_path

        # Calculate chunks
        with open(file_path, 'rb') as f:
            from app.pdf_compat import PdfReader
            page_count = len(PdfReader(f).pages)
        
        chunk_config = chunking_service.calculate_chunks(page_count)
        
        # Update job with chunk info
        job.total_chunks = chunk_config['num_chunks']
        job.current_step = f"Splitting into {chunk_config['num_chunks']} chunks"
        job.progress_percent = 10
        safe_db_commit(db)
        emit_progress(job_id)
        
        # Split PDF and persist chunks to DB
        try:
            chunk_db_ids = chunking_service.split_pdf_and_persist(
                file_path,
                chunk_config,
                job_id,
                db
            )
            logger.info(f"Job {job_id}: created {len(chunk_db_ids)} JobChunk rows in DB")
        except Exception as chunk_err:
            logger.error(f"Job {job_id}: failed to persist chunks to DB: {chunk_err}")
            # Fall back to legacy in-memory chunking
            chunks = chunking_service.split_pdf(file_path, chunk_config)
            chunk_db_ids = []
        
        if not chunk_db_ids:
            # Fall back to legacy chunking if DB persistence failed
            chunks = chunking_service.split_pdf(file_path, chunk_config)
        else:
            # Load chunks from DB for processing
            from app.models import JobChunk
            chunks = []
            for chunk_id in chunk_db_ids:
                chunk_record = JobChunk.query.get(chunk_id)
                if chunk_record:
                    chunks.append(chunk_record.get_chunk_metadata())
        
        # Attach job_id to each chunk so workers can emit per-chunk progress
        for c in chunks:
            c['job_id'] = job_id
        logger.info(
            "Job %s: chunking complete strategy=%s chunk_size=%s total_pages=%s num_chunks(expected)=%s num_chunks(actual)=%s",
            job_id,
            chunk_config.get('strategy'),
            chunk_config.get('chunk_size'),
            chunk_config.get('total_pages'),
            chunk_config.get('num_chunks'),
            len(chunks),
        )

        if not chunks:
            job = Job.query.get(job_id)
            job.status = JOB_STATUS_FAILED
            job.current_step = "Failed: No chunks produced"
            job.error_message = "Chunking produced zero chunks for a non-empty PDF."
            job.completed_at = datetime.utcnow()
            safe_db_commit(db)
            logger.error("Job %s: split_pdf returned zero chunks", job_id)
            return {'status': 'failed', 'error': 'No chunks produced'}
        
        # Check for cancellation again
        job = Job.query.get(job_id)
        if job.is_cancelled:
            chunking_service.cleanup_chunks(chunks)
            job.status = JOB_STATUS_FAILED
            job.error_message = "Job cancelled by user"
            safe_db_commit(db)
            return {'status': 'cancelled'}
        
        job.current_step = "Processing "
        job.progress_percent = 15
        safe_db_commit(db)
        emit_progress(job_id)
        
        # Process chunks in parallel if multiple chunks
        if len(chunks) == 1:
            # Single chunk - process directly (call underlying function)
            logger.info("Job %s: processing single chunk %s", job_id, chunks[0].get('file_path'))
            result = process_chunk.run(chunks[0], user_id, settings)
            chunk_results = [result]
            
            # Update progress as chunks complete
            job = Job.query.get(job_id)
            job.processed_chunks = len(chunk_results)
            job.progress_percent = 75
            job.current_step = "Merging results"
            safe_db_commit(db)
            emit_progress(job_id)
        else:
            # Multiple chunks - use chord for parallel processing
            logger.info(f"Job {job_id}: dispatching {len(chunks)} chunks for parallel processing")
            
            # Create a chord: group of chunk tasks + callback to finalize
            chunk_tasks = [
                process_chunk.s(chunk, user_id, settings)
                for chunk in chunks
            ]
            
            # Use chord to process all chunks in parallel, then call finalize_job_results
            callback = finalize_job_results.s(job_id=job_id)
            chord_result = chord(chunk_tasks)(callback)
            
            logger.info(f"Job {job_id}: dispatched {len(chunks)} chunks in parallel, chord_id={chord_result.id}")

            # Schedule a watchdog finalizer in case the chord callback fails to execute
            # (e.g., due to result-backend/chord unlock issues or worker crashes). The
            # watchdog will call finalize_job_results with an empty in-memory result list
            # which will cause finalization to read chunk rows from the DB. The timeout
            # is configurable via CHORD_WATCHDOG_SECONDS; fallback to a conservative value.
            try:
                from flask import current_app
                watchdog_default = max(1800, int(len(chunks) * 60))  # at least 30 minutes or 1min/chunk
                watchdog_seconds = int(current_app.config.get('CHORD_WATCHDOG_SECONDS', watchdog_default))
                # Schedule a delayed finalize_job_results call as a safety net
                finalize_job_results.apply_async(args=[[], job_id], countdown=watchdog_seconds)
                logger.info(f"Job {job_id}: scheduled finalize watchdog in {watchdog_seconds}s")
            except Exception as e:
                logger.warning(f"Job {job_id}: failed to schedule finalize watchdog: {e}")

            # Return early; finalize_job_results (either via chord or watchdog) will complete the job
            return {
                'status': 'dispatched',
                'message': f'{len(chunks)} chunks processing in parallel',
                'job_id': job_id,
                'chord_id': str(chord_result.id)
            }
        
        # For single-chunk jobs only: merge and finalize inline
        # (Multi-chunk jobs return early above; finalize_job_results handles completion)
        
        # Merge chunk results
        if not chunk_results:
            logger.error("Job %s: no chunk results produced; marking job as failed", job_id)
            job = Job.query.get(job_id)
            job.status = JOB_STATUS_FAILED
            job.error_message = "No chunks processed. See worker logs for details."
            job.completed_at = datetime.utcnow()
            job.progress_percent = 100
            safe_db_commit(db)
            emit_progress(job_id)
            return {'status': 'failed', 'error': 'No chunks processed'}
        all_sentences = merge_chunk_results(chunk_results)
        
        # Calculate metrics
        total_tokens = sum(r.get('tokens', 0) for r in chunk_results if r.get('status') == 'success')
        failed_chunks = [r['chunk_id'] for r in chunk_results if r.get('status') == 'failed']
        
        # Update job with results
        job = Job.query.get(job_id)
        success_count = len([r for r in chunk_results if r.get('status') == 'success'])
        if success_count == 0:
            job.status = JOB_STATUS_FAILED
            job.current_step = "Failed"
            job.error_message = "All chunks failed to process. Check API credentials or PDF content."
            # Add detailed failure reasons to the logs for diagnostics
            for r in chunk_results:
                logger.error("Job %s: chunk %s failed with error: %s", job_id, r.get('chunk_id'), r.get('error'))
        else:
            job.status = JOB_STATUS_COMPLETED
            job.current_step = "Completed"
        job.progress_percent = 100
        job.actual_tokens = total_tokens
        job.gemini_tokens_used = total_tokens
        job.gemini_api_calls = success_count
        job.completed_at = datetime.utcnow()
        job.chunk_results = chunk_results
        job.failed_chunks = failed_chunks if failed_chunks else None
        
        # Calculate processing time
        if job.started_at:
            processing_time = (job.completed_at - job.started_at).total_seconds()
            job.processing_time_seconds = int(processing_time)
        
        safe_db_commit(db)
        emit_progress(job_id)
        
        return {
            'status': 'success',
            'sentences': all_sentences,
            'total_tokens': total_tokens,
            'chunks_processed': len(chunk_results),
            'failed_chunks': failed_chunks
        }
        
    except Exception as e:
        # Update job as failed
        if job:
            job.status = JOB_STATUS_FAILED
            job.error_message = str(e)[:512]
            job.completed_at = datetime.utcnow()
            safe_db_commit(db)
        raise
        
    finally:
        # Cleanup temporary files
        if chunks:
            chunking_service.cleanup_chunks(chunks)
        
        # Cleanup uploaded PDF
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
            # Cleanup reconstructed file and chunks if any
            if reconstructed_path and os.path.exists(reconstructed_path):
                os.remove(reconstructed_path)
        except Exception:
            pass
        except Exception:
            pass

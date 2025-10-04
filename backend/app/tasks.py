"""Celery tasks for asynchronous PDF processing"""
import logging
import os
from datetime import datetime
from typing import Dict, List
from typing import Optional
import base64
import tempfile
import PyPDF2
from celery import group, chord
from celery.exceptions import SoftTimeLimitExceeded

logger = logging.getLogger(__name__)

def get_celery():
    """Get celery instance (deferred import to avoid circular dependency)"""
    from app import celery
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
    from app.models import Job, User, JobChunk
    return Job, User, JobChunk


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
    Process a single PDF chunk.
    
    Args:
        chunk_info: Chunk metadata from ChunkingService
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
    try:
        # Get services
        _, GeminiService, _, _ = get_services()
        Job, User, JobChunk = get_models()
        
        # Initialize services
        gemini_service = GeminiService(
            sentence_length_limit=settings['sentence_length_limit'],
            model_preference=settings['gemini_model'],
            ignore_dialogue=settings.get('ignore_dialogue', False),
            preserve_formatting=settings.get('preserve_formatting', True),
            fix_hyphenation=settings.get('fix_hyphenation', True),
            min_sentence_length=settings.get('min_sentence_length', 2),
        )
        
        # Extract text from persisted JobChunk when available
        import io
        db = get_db()
        jc = None
        job_chunk_id = chunk_info.get('job_chunk_id')
        if job_chunk_id:
            jc = JobChunk.query.get(job_chunk_id)
            if jc and jc.status == 'pending':
                jc.status = 'in_progress'
                jc.attempts = jc.attempts + 1
                safe_db_commit(db)

        text = ""
        if jc and jc.file_b64:
            chunk_bytes = base64.b64decode(jc.file_b64)
            pdf_file = io.BytesIO(chunk_bytes)
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            for page in pdf_reader.pages:
                text += (page.extract_text() or "") + "\n"
        elif chunk_info.get('file_b64'):
            chunk_bytes = base64.b64decode(chunk_info['file_b64'])
            pdf_file = io.BytesIO(chunk_bytes)
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            for page in pdf_reader.pages:
                text += (page.extract_text() or "") + "\n"
        else:
            # Fallback to file path if present
            with open(chunk_info['file_path'], 'rb') as pdf_file:
                pdf_reader = PyPDF2.PdfReader(pdf_file)
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
            
            return {
                'chunk_id': chunk_info['chunk_id'],
                'status': 'failed',
                'error': 'No extractable text in PDF chunk (may be scanned/images only).',
                'start_page': chunk_info['start_page'],
                'end_page': chunk_info['end_page']
            }

        # Process with Gemini
        prompt = gemini_service.build_prompt()
        result = gemini_service.normalize_text(text, prompt)
        
        # Cleanup chunk file after processing only if a filesystem path was used
        try:
            fp = chunk_info.get('file_path')
            if fp and os.path.exists(fp):
                os.remove(fp)
        except Exception as e:
            logger.warning(f"Failed to cleanup chunk file {chunk_info.get('file_path')}: {e}")
        
        # Update DB row on success
        try:
            if jc:
                jc.status = 'success'
                safe_db_commit(db)
        except Exception:
            pass

        return {
            'chunk_id': chunk_info['chunk_id'],
            'sentences': result['sentences'],
            'tokens': result.get('tokens', 0),
            'start_page': chunk_info['start_page'],
            'end_page': chunk_info['end_page'],
            'status': 'success'
        }
        
    except SoftTimeLimitExceeded:
        # Cleanup chunk file before returning
        try:
            if os.path.exists(chunk_info['file_path']):
                os.remove(chunk_info['file_path'])
        except Exception:
            pass
        
        # Update DB row when available
        try:
            db = get_db()
            _, _, JobChunk = get_models()
            jc = JobChunk.query.get(chunk_info.get('job_chunk_id')) if chunk_info.get('job_chunk_id') else None
            if jc:
                jc.status = 'failed'
                jc.last_error = 'Processing timeout exceeded'
                safe_db_commit(db)
        except Exception:
            pass

        return {
            'chunk_id': chunk_info['chunk_id'],
            'status': 'failed',
            'error': 'Processing timeout exceeded',
            'start_page': chunk_info['start_page'],
            'end_page': chunk_info['end_page']
        }
    except Exception as e:
        # Cleanup chunk file before returning
        try:
            if os.path.exists(chunk_info['file_path']):
                os.remove(chunk_info['file_path'])
        except Exception:
            pass
        
        # Update DB row when available
        try:
            db = get_db()
            _, _, JobChunk = get_models()
            jc = JobChunk.query.get(chunk_info.get('job_chunk_id')) if chunk_info.get('job_chunk_id') else None
            if jc:
                jc.status = 'failed'
                jc.last_error = str(e)[:1000]
                safe_db_commit(db)
        except Exception:
            pass

        return {
            'chunk_id': chunk_info['chunk_id'],
            'status': 'failed',
            'error': str(e),
            'start_page': chunk_info['start_page'],
            'end_page': chunk_info['end_page']
        }


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
    
    Args:
        chunk_results: List of results from all process_chunk tasks
        job_id: Job ID to finalize
    """
    db = get_db()
    Job, User, JobChunk = get_models()
    JOB_STATUS_PROCESSING, JOB_STATUS_COMPLETED, JOB_STATUS_FAILED, _ = get_constants()
    
    try:
        logger.info(f"Job {job_id}: finalizing {len(chunk_results)} chunk results")

        # Check if any failed chunks should be re-dispatched (durable retries)
        failed_chunk_ids = [r.get('chunk_id') for r in chunk_results if r.get('status') == 'failed']
        if failed_chunk_ids:
            job = Job.query.get(job_id)
            if job is None:
                raise ValueError(f"Job {job_id} not found")
            current_round = job.retry_count or 0
            max_rounds = job.max_retries or 3
            if current_round < max_rounds:
                failed_rows = JobChunk.query.filter(
                    JobChunk.job_id == job_id,
                    JobChunk.chunk_index.in_(failed_chunk_ids)
                ).all()
                redisp_tasks = [
                    process_chunk.s({
                        'chunk_id': row.chunk_index,
                        'job_chunk_id': row.id,
                        'start_page': row.start_page,
                        'end_page': row.end_page,
                    }, job.user_id, job.processing_settings or {})
                    for row in failed_rows
                ]
                if redisp_tasks:
                    job.retry_count = current_round + 1
                    safe_db_commit(db)
                    chord(redisp_tasks)(finalize_job_results.s(job_id=job_id))
                    logger.info(
                        "Job %s: re-dispatched %d failed chunks (round %d/%d)",
                        job_id, len(redisp_tasks), job.retry_count, max_rounds
                    )
                    return {'status': 'redispatched', 'failed_chunks': failed_chunk_ids, 'round': job.retry_count}

        # Merge chunk results
        all_sentences = merge_chunk_results(chunk_results)
        
        # Calculate metrics
        total_tokens = sum(r.get('tokens', 0) for r in chunk_results if r.get('status') == 'success')
        failed_chunks = [r['chunk_id'] for r in chunk_results if r.get('status') == 'failed']
        success_count = len([r for r in chunk_results if r.get('status') == 'success'])
        
        # Update job with results
        job = Job.query.get(job_id)
        if not job:
            raise ValueError(f"Job {job_id} not found")
        
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
    Job, User, JobChunk = get_models()
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
            page_count = len(PyPDF2.PdfReader(f).pages)
        
        chunk_config = chunking_service.calculate_chunks(page_count)
        
        # Update job with chunk info
        job.total_chunks = chunk_config['num_chunks']
        job.current_step = f"Splitting into {chunk_config['num_chunks']} chunks"
        job.progress_percent = 10
        safe_db_commit(db)
        emit_progress(job_id)

        # Split PDF into chunks and persist chunk rows
        chunks = chunking_service.split_pdf(file_path, chunk_config, job_id=job_id)
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
            
            # Return early; finalize_job_results will complete the job
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

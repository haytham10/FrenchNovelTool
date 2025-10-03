"""Celery tasks for asynchronous PDF processing"""
from celery import Task, group, chord
from celery.utils.log import get_task_logger
from typing import List, Dict, Any, Optional
import os
import tempfile
from datetime import datetime

from celery_app import celery_app
from app import create_app, db
from app.models import Job, User
from app.services.gemini_service import GeminiService
from app.services.chunking_service import PDFChunkingService
from app.services.history_service import HistoryService
from app.services.job_service import JobService
from app.services.credit_service import CreditService
from app.constants import (
    JOB_STATUS_PROCESSING,
    JOB_STATUS_COMPLETED,
    JOB_STATUS_FAILED
)

logger = get_task_logger(__name__)

# Create Flask app context for database operations
flask_app = create_app()


class DatabaseTask(Task):
    """Base task class that provides Flask app context"""
    _app = None

    @property
    def app_context(self):
        if self._app is None:
            self._app = flask_app.app_context()
            self._app.push()
        return self._app


@celery_app.task(base=DatabaseTask, bind=True, max_retries=3)
def process_pdf_chunk(
    self,
    job_id: int,
    chunk_index: int,
    pdf_path: str,
    start_page: int,
    end_page: int,
    settings: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Process a single chunk of a PDF file.
    
    Args:
        job_id: Job ID for tracking
        chunk_index: Index of this chunk (0-based)
        pdf_path: Path to the original PDF file
        start_page: Starting page (0-indexed, inclusive)
        end_page: Ending page (0-indexed, exclusive)
        settings: Processing settings
        
    Returns:
        Dictionary with processed sentences and metadata
    """
    chunk_path = None
    
    try:
        logger.info(f'Processing chunk {chunk_index} (pages {start_page}-{end_page}) for job {job_id}')
        
        # Extract chunk from PDF
        chunking_service = PDFChunkingService(pdf_path)
        chunk_path = chunking_service.extract_chunk(start_page, end_page)
        
        # Create GeminiService with user settings
        gemini_service = GeminiService(
            sentence_length_limit=settings.get('sentence_length_limit', 8),
            model_preference=settings.get('gemini_model', 'balanced'),
            ignore_dialogue=settings.get('ignore_dialogue', False),
            preserve_formatting=settings.get('preserve_formatting', True),
            fix_hyphenation=settings.get('fix_hyphenation', True),
            min_sentence_length=settings.get('min_sentence_length', 2)
        )
        
        # Build prompt and process chunk
        prompt = gemini_service.build_prompt()
        processed_sentences = gemini_service.generate_content_from_pdf(prompt, chunk_path)
        
        logger.info(
            f'Chunk {chunk_index} processed: {len(processed_sentences)} sentences '
            f'(pages {start_page}-{end_page})'
        )
        
        # Update progress in database
        with flask_app.app_context():
            job = Job.query.get(job_id)
            if job:
                job.completed_chunks = (job.completed_chunks or 0) + 1
                if job.total_chunks and job.total_chunks > 0:
                    job.progress_percent = int((job.completed_chunks / job.total_chunks) * 100)
                db.session.commit()
        
        return {
            'chunk_index': chunk_index,
            'start_page': start_page,
            'end_page': end_page,
            'sentences': processed_sentences,
            'sentence_count': len(processed_sentences)
        }
        
    except Exception as e:
        logger.error(f'Failed to process chunk {chunk_index}: {str(e)}')
        # Retry with exponential backoff
        raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))
        
    finally:
        # Cleanup chunk file
        if chunk_path:
            PDFChunkingService.cleanup_chunk(chunk_path)


@celery_app.task(base=DatabaseTask, bind=True)
def merge_chunk_results(self, results: List[Dict[str, Any]], job_id: int) -> Dict[str, Any]:
    """
    Merge results from all chunks into a single result.
    Idempotent operation - can be called multiple times safely.
    
    Args:
        results: List of chunk results
        job_id: Job ID
        
    Returns:
        Merged result dictionary
    """
    try:
        logger.info(f'Merging {len(results)} chunk results for job {job_id}')
        
        # Sort chunks by index to maintain order
        sorted_results = sorted(results, key=lambda x: x['chunk_index'])
        
        # Merge sentences in order
        all_sentences = []
        for chunk_result in sorted_results:
            all_sentences.extend(chunk_result['sentences'])
        
        logger.info(f'Merged {len(all_sentences)} total sentences for job {job_id}')
        
        return {
            'sentences': all_sentences,
            'total_chunks': len(results),
            'total_sentences': len(all_sentences)
        }
        
    except Exception as e:
        logger.error(f'Failed to merge chunk results for job {job_id}: {str(e)}')
        raise


@celery_app.task(base=DatabaseTask, bind=True, max_retries=3)
def process_pdf_async(
    self,
    user_id: int,
    job_id: int,
    pdf_path: str,
    original_filename: str,
    settings: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Main async task for processing a PDF.
    Determines if chunking is needed and orchestrates the processing.
    
    Args:
        user_id: User ID
        job_id: Job ID
        pdf_path: Path to the PDF file
        original_filename: Original filename
        settings: Processing settings
        
    Returns:
        Dictionary with processed sentences
    """
    try:
        logger.info(f'Starting async processing for job {job_id}, file: {original_filename}')
        
        with flask_app.app_context():
            # Update job status
            job = Job.query.get(job_id)
            if not job:
                raise ValueError(f'Job {job_id} not found')
            
            job.status = JOB_STATUS_PROCESSING
            job.started_at = datetime.utcnow()
            job.celery_task_id = self.request.id
            db.session.commit()
            
            # Check if chunking is needed
            chunking_service = PDFChunkingService(pdf_path)
            
            if chunking_service.should_chunk():
                # Large file - use chunked processing
                logger.info(f'Job {job_id}: Large file detected ({chunking_service.total_pages} pages), using chunked processing')
                
                chunks = chunking_service.calculate_chunks()
                job.total_chunks = len(chunks)
                job.completed_chunks = 0
                job.progress_percent = 0
                db.session.commit()
                
                # Create subtasks for each chunk
                chunk_tasks = []
                for idx, (start_page, end_page) in enumerate(chunks):
                    chunk_task = process_pdf_chunk.s(
                        job_id=job_id,
                        chunk_index=idx,
                        pdf_path=pdf_path,
                        start_page=start_page,
                        end_page=end_page,
                        settings=settings
                    )
                    chunk_tasks.append(chunk_task)
                
                # Execute chunks in parallel and merge results
                callback = merge_chunk_results.s(job_id=job_id)
                workflow = chord(chunk_tasks)(callback)
                
                # Wait for completion
                merged_result = workflow.get(timeout=3600)  # 1 hour timeout
                all_sentences = merged_result['sentences']
                
            else:
                # Small file - process directly
                logger.info(f'Job {job_id}: Small file ({chunking_service.total_pages} pages), processing directly')
                
                job.total_chunks = 1
                job.completed_chunks = 0
                job.progress_percent = 0
                db.session.commit()
                
                # Process entire PDF
                gemini_service = GeminiService(
                    sentence_length_limit=settings.get('sentence_length_limit', 8),
                    model_preference=settings.get('gemini_model', 'balanced'),
                    ignore_dialogue=settings.get('ignore_dialogue', False),
                    preserve_formatting=settings.get('preserve_formatting', True),
                    fix_hyphenation=settings.get('fix_hyphenation', True),
                    min_sentence_length=settings.get('min_sentence_length', 2)
                )
                
                prompt = gemini_service.build_prompt()
                all_sentences = gemini_service.generate_content_from_pdf(prompt, pdf_path)
                
                job.completed_chunks = 1
                job.progress_percent = 100
                db.session.commit()
            
            # Create history entry
            history_service = HistoryService()
            history_entry = history_service.add_entry(
                user_id=user_id,
                original_filename=original_filename,
                processed_sentences_count=len(all_sentences),
                error_message=None,
                processing_settings=settings
            )
            
            # Estimate actual token usage
            actual_tokens = JobService.estimate_tokens_heuristic(' '.join(all_sentences))
            
            # Complete the job
            job.status = JOB_STATUS_COMPLETED
            job.actual_tokens = actual_tokens
            job.actual_credits = JobService.calculate_credits(actual_tokens, job.model)
            job.completed_at = datetime.utcnow()
            job.history_id = history_entry.id
            job.progress_percent = 100
            db.session.commit()
            
            # Adjust credits based on actual usage
            CreditService.adjust_final_credits(
                user_id=user_id,
                job_id=job_id,
                reserved_amount=job.estimated_credits,
                actual_amount=job.actual_credits
            )
            
            logger.info(f'Job {job_id} completed successfully: {len(all_sentences)} sentences')
            
            return {
                'job_id': job_id,
                'sentences': all_sentences,
                'history_id': history_entry.id
            }
            
    except Exception as e:
        logger.error(f'Job {job_id} failed: {str(e)}')
        
        with flask_app.app_context():
            # Fail the job and refund credits
            job = Job.query.get(job_id)
            if job:
                JobService.fail_job(job_id, str(e), 'PROCESSING_ERROR')
                CreditService.refund_credits(
                    user_id=user_id,
                    job_id=job_id,
                    amount=job.estimated_credits,
                    description=f'Refund for failed job: {str(e)}'
                )
        
        raise
        
    finally:
        # Cleanup PDF file
        if pdf_path and os.path.exists(pdf_path):
            try:
                os.remove(pdf_path)
                logger.debug(f'Cleaned up PDF file: {pdf_path}')
            except Exception as e:
                logger.warning(f'Failed to cleanup PDF {pdf_path}: {str(e)}')


@celery_app.task(base=DatabaseTask)
def cleanup_old_jobs():
    """
    Periodic task to cleanup old completed/failed jobs.
    Removes jobs older than 24 hours.
    """
    try:
        from datetime import timedelta
        
        with flask_app.app_context():
            cutoff = datetime.utcnow() - timedelta(hours=24)
            
            old_jobs = Job.query.filter(
                Job.status.in_([JOB_STATUS_COMPLETED, JOB_STATUS_FAILED]),
                Job.completed_at < cutoff
            ).all()
            
            for job in old_jobs:
                db.session.delete(job)
            
            db.session.commit()
            
            logger.info(f'Cleaned up {len(old_jobs)} old jobs')
            
    except Exception as e:
        logger.error(f'Failed to cleanup old jobs: {str(e)}')

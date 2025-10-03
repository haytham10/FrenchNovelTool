"""Celery tasks for asynchronous PDF processing"""
import os
import tempfile
from typing import List
from flask import current_app
from celery import Task, group, chord
from app.celery_app import celery
from app import create_app, db
from app.models import Job, History, User
from app.services.pdf_service import PDFService
from app.services.gemini_service import GeminiService
from app.services.history_service import HistoryService
from app.services.job_service import JobService
from app.services.credit_service import CreditService
from app.constants import (
    JOB_STATUS_PROCESSING,
    JOB_STATUS_COMPLETED,
    JOB_STATUS_FAILED,
    CHUNK_THRESHOLD_PAGES,
    DEFAULT_CHUNK_SIZE_PAGES,
)


# Flask app context for Celery tasks
app = create_app()


class FlaskTask(Task):
    """Base task that runs within Flask application context"""
    
    def __call__(self, *args, **kwargs):
        with app.app_context():
            return self.run(*args, **kwargs)


@celery.task(base=FlaskTask, bind=True, name='app.tasks.process_pdf_async')
def process_pdf_async(self, job_id: int, pdf_path: str):
    """
    Asynchronous task to process a PDF file.
    
    Args:
        job_id: ID of the job to process
        pdf_path: Path to the temporary PDF file
        
    Returns:
        dict: Processing results with sentences and job information
    """
    job = None
    history_service = HistoryService()
    
    try:
        # Get job from database
        job = Job.query.get(job_id)
        if not job:
            raise ValueError(f"Job {job_id} not found")
        
        # Update job status to processing
        JobService.start_job(job_id)
        self.update_state(state='PROCESSING', meta={'progress': 0, 'status': 'Starting processing'})
        
        # Get page count
        pdf_service = PDFService(None)
        pdf_service.temp_file_path = pdf_path
        page_count = pdf_service.get_page_count(pdf_path)
        
        # Update job with page count
        job.page_count = page_count
        db.session.commit()
        
        current_app.logger.info(f"Processing job {job_id}: {job.original_filename}, {page_count} pages")
        
        # Check if chunking is needed
        if page_count > CHUNK_THRESHOLD_PAGES:
            current_app.logger.info(f"Job {job_id} requires chunking ({page_count} > {CHUNK_THRESHOLD_PAGES})")
            result = process_pdf_chunked(job_id, pdf_path, page_count)
        else:
            current_app.logger.info(f"Job {job_id} processing without chunking ({page_count} <= {CHUNK_THRESHOLD_PAGES})")
            result = process_pdf_single(job_id, pdf_path)
        
        return result
        
    except Exception as e:
        current_app.logger.exception(f"Failed to process job {job_id}")
        
        # Update job status to failed
        if job:
            error_message = str(e)
            error_code = 'PROCESSING_ERROR'
            
            if 'Gemini' in error_message or 'API' in error_message:
                error_code = 'GEMINI_API_ERROR'
            elif 'PDF' in error_message:
                error_code = 'INVALID_PDF'
            
            JobService.fail_job(job_id, error_message, error_code)
            
            # Refund credits
            CreditService.refund_credits(
                user_id=job.user_id,
                job_id=job_id,
                amount=job.estimated_credits,
                description=f'Refund for failed job: {error_message}'
            )
            
            # Add error to history
            history_service.add_entry(
                user_id=job.user_id,
                original_filename=job.original_filename,
                processed_sentences_count=0,
                error_message=error_message,
                failed_step='normalize',
                error_code=error_code
            )
        
        raise
    finally:
        # Clean up temporary file
        if pdf_path and os.path.exists(pdf_path):
            os.remove(pdf_path)


def process_pdf_single(job_id: int, pdf_path: str) -> dict:
    """
    Process a single PDF without chunking.
    
    Args:
        job_id: ID of the job
        pdf_path: Path to the PDF file
        
    Returns:
        dict: Processing results
    """
    job = Job.query.get(job_id)
    if not job:
        raise ValueError(f"Job {job_id} not found")
    
    # Get processing settings from job
    settings = job.processing_settings or {}
    
    # Create Gemini service
    gemini_service = GeminiService(
        sentence_length_limit=settings.get('sentence_length_limit', 8),
        model_preference=settings.get('gemini_model', 'balanced'),
        ignore_dialogue=settings.get('ignore_dialogue', False),
        preserve_formatting=settings.get('preserve_formatting', True),
        fix_hyphenation=settings.get('fix_hyphenation', True),
        min_sentence_length=settings.get('min_sentence_length', 2),
    )
    
    # Build prompt and process PDF
    prompt = gemini_service.build_prompt()
    current_app.logger.info(f"Processing single PDF for job {job_id}")
    
    processed_sentences = gemini_service.generate_content_from_pdf(prompt, pdf_path)
    
    current_app.logger.info(f"Job {job_id} processed {len(processed_sentences)} sentences")
    
    # Create history entry
    history_service = HistoryService()
    history_entry = history_service.add_entry(
        user_id=job.user_id,
        original_filename=job.original_filename,
        processed_sentences_count=len(processed_sentences),
        error_message=None,
        processing_settings=settings
    )
    
    # Calculate actual tokens and complete job
    actual_tokens = JobService.estimate_tokens_heuristic(' '.join(processed_sentences))
    JobService.complete_job(job_id, actual_tokens, history_entry.id)
    
    # Adjust credits
    CreditService.adjust_final_credits(
        user_id=job.user_id,
        job_id=job_id,
        reserved_amount=job.estimated_credits,
        actual_amount=JobService.calculate_credits(actual_tokens, job.model)
    )
    
    # Update history entry with job_id
    history_entry.job_id = job_id
    db.session.commit()
    
    return {
        'job_id': job_id,
        'sentences': processed_sentences,
        'status': 'completed'
    }


def process_pdf_chunked(job_id: int, pdf_path: str, page_count: int) -> dict:
    """
    Process a large PDF by splitting into chunks.
    
    Args:
        job_id: ID of the parent job
        pdf_path: Path to the PDF file
        page_count: Total number of pages
        
    Returns:
        dict: Processing results
    """
    job = Job.query.get(job_id)
    if not job:
        raise ValueError(f"Job {job_id} not found")
    
    # Calculate chunks
    chunk_size = DEFAULT_CHUNK_SIZE_PAGES
    total_chunks = (page_count + chunk_size - 1) // chunk_size  # Ceiling division
    
    # Update job with chunking information
    job.chunk_size = chunk_size
    job.total_chunks = total_chunks
    job.completed_chunks = 0
    job.progress_percent = 0.0
    db.session.commit()
    
    current_app.logger.info(f"Chunking job {job_id} into {total_chunks} chunks of {chunk_size} pages")
    
    # Process each chunk
    all_sentences = []
    pdf_service = PDFService(None)
    
    for chunk_index in range(total_chunks):
        start_page = chunk_index * chunk_size
        end_page = min(start_page + chunk_size, page_count)
        
        current_app.logger.info(f"Processing chunk {chunk_index + 1}/{total_chunks} (pages {start_page + 1}-{end_page})")
        
        # Split PDF for this chunk
        chunk_pdf_path = pdf_service.split_pdf_by_pages(pdf_path, start_page, end_page)
        
        try:
            # Process chunk
            chunk_result = process_pdf_chunk(job_id, chunk_pdf_path, chunk_index + 1, total_chunks)
            all_sentences.extend(chunk_result['sentences'])
            
            # Update progress
            job.completed_chunks = chunk_index + 1
            job.progress_percent = (chunk_index + 1) / total_chunks * 100
            db.session.commit()
            
        finally:
            # Clean up chunk file
            if os.path.exists(chunk_pdf_path):
                os.remove(chunk_pdf_path)
    
    current_app.logger.info(f"Job {job_id} completed all {total_chunks} chunks, total sentences: {len(all_sentences)}")
    
    # Create final history entry
    history_service = HistoryService()
    history_entry = history_service.add_entry(
        user_id=job.user_id,
        original_filename=job.original_filename,
        processed_sentences_count=len(all_sentences),
        error_message=None,
        processing_settings=job.processing_settings
    )
    
    # Complete job
    actual_tokens = JobService.estimate_tokens_heuristic(' '.join(all_sentences))
    JobService.complete_job(job_id, actual_tokens, history_entry.id)
    
    # Adjust credits
    CreditService.adjust_final_credits(
        user_id=job.user_id,
        job_id=job_id,
        reserved_amount=job.estimated_credits,
        actual_amount=JobService.calculate_credits(actual_tokens, job.model)
    )
    
    # Update history with job_id
    history_entry.job_id = job_id
    db.session.commit()
    
    return {
        'job_id': job_id,
        'sentences': all_sentences,
        'status': 'completed',
        'chunks_processed': total_chunks
    }


def process_pdf_chunk(job_id: int, chunk_pdf_path: str, chunk_number: int, total_chunks: int) -> dict:
    """
    Process a single chunk of a PDF.
    
    Args:
        job_id: ID of the parent job
        chunk_pdf_path: Path to the chunk PDF file
        chunk_number: Current chunk number (1-indexed)
        total_chunks: Total number of chunks
        
    Returns:
        dict: Chunk processing results
    """
    job = Job.query.get(job_id)
    if not job:
        raise ValueError(f"Job {job_id} not found")
    
    # Get processing settings
    settings = job.processing_settings or {}
    
    # Create Gemini service
    gemini_service = GeminiService(
        sentence_length_limit=settings.get('sentence_length_limit', 8),
        model_preference=settings.get('gemini_model', 'balanced'),
        ignore_dialogue=settings.get('ignore_dialogue', False),
        preserve_formatting=settings.get('preserve_formatting', True),
        fix_hyphenation=settings.get('fix_hyphenation', True),
        min_sentence_length=settings.get('min_sentence_length', 2),
    )
    
    # Build prompt and process chunk
    prompt = gemini_service.build_prompt()
    processed_sentences = gemini_service.generate_content_from_pdf(prompt, chunk_pdf_path)
    
    current_app.logger.info(
        f"Job {job_id} chunk {chunk_number}/{total_chunks} processed {len(processed_sentences)} sentences"
    )
    
    return {
        'sentences': processed_sentences,
        'chunk_number': chunk_number
    }

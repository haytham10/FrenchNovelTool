"""Celery tasks for asynchronous PDF processing"""
import os
from datetime import datetime
from typing import Dict, List
import PyPDF2
from celery import group, chord
from celery.exceptions import SoftTimeLimitExceeded
from app import db
from app.models import Job, User
from app.services.pdf_service import PDFService
from app.services.gemini_service import GeminiService
from app.services.chunking_service import ChunkingService
from app.services.job_service import JobService
from app.constants import (
    JOB_STATUS_PROCESSING, JOB_STATUS_COMPLETED, JOB_STATUS_FAILED,
    MODEL_PREFERENCE_MAP
)


def get_celery():
    """Get celery instance (deferred import to avoid circular dependency)"""
    from app import celery
    return celery


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
        # Initialize services
        gemini_service = GeminiService(
            sentence_length_limit=settings['sentence_length_limit'],
            model_preference=settings['gemini_model'],
            ignore_dialogue=settings.get('ignore_dialogue', False),
            preserve_formatting=settings.get('preserve_formatting', True),
            fix_hyphenation=settings.get('fix_hyphenation', True),
            min_sentence_length=settings.get('min_sentence_length', 2),
        )
        
        # Extract text from chunk
        text = ""
        with open(chunk_info['file_path'], 'rb') as pdf_file:
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
        
        # Process with Gemini
        prompt = gemini_service.build_prompt()
        result = gemini_service.normalize_text(text, prompt)
        
        return {
            'chunk_id': chunk_info['chunk_id'],
            'sentences': result['sentences'],
            'tokens': result.get('tokens', 0),
            'start_page': chunk_info['start_page'],
            'end_page': chunk_info['end_page'],
            'status': 'success'
        }
        
    except SoftTimeLimitExceeded:
        return {
            'chunk_id': chunk_info['chunk_id'],
            'status': 'failed',
            'error': 'Processing timeout exceeded',
            'start_page': chunk_info['start_page'],
            'end_page': chunk_info['end_page']
        }
    except Exception as e:
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


@get_celery().task(bind=True, name='app.tasks.process_pdf_async')
def process_pdf_async(self, job_id: int, file_path: str, user_id: int, settings: dict):
    """
    Process PDF asynchronously with chunking and progress tracking.
    
    Args:
        job_id: Database job ID
        file_path: Path to uploaded PDF in temp storage
        user_id: User who initiated the job
        settings: Processing settings (model, length limit, etc.)
    """
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
            db.session.commit()
            return {'status': 'cancelled'}
        
        job.status = JOB_STATUS_PROCESSING
        job.started_at = datetime.utcnow()
        job.current_step = "Analyzing PDF"
        job.progress_percent = 5
        db.session.commit()
        
        # Calculate chunks
        with open(file_path, 'rb') as f:
            page_count = len(PyPDF2.PdfReader(f).pages)
        
        chunk_config = chunking_service.calculate_chunks(page_count)
        
        # Update job with chunk info
        job.total_chunks = chunk_config['num_chunks']
        job.current_step = f"Splitting into {chunk_config['num_chunks']} chunks"
        job.progress_percent = 10
        db.session.commit()
        
        # Split PDF into chunks
        chunks = chunking_service.split_pdf(file_path, chunk_config)
        
        # Check for cancellation again
        job = Job.query.get(job_id)
        if job.is_cancelled:
            chunking_service.cleanup_chunks(chunks)
            job.status = JOB_STATUS_FAILED
            job.error_message = "Job cancelled by user"
            db.session.commit()
            return {'status': 'cancelled'}
        
        job.current_step = "Processing chunks"
        job.progress_percent = 15
        db.session.commit()
        
        # Process chunks in parallel if multiple chunks
        if len(chunks) == 1:
            # Single chunk - process directly
            result = process_chunk(chunks[0], user_id, settings)
            chunk_results = [result]
        else:
            # Multiple chunks - process in parallel using Celery group
            job_group = group([
                process_chunk.s(chunk, user_id, settings)
                for chunk in chunks
            ])
            results = job_group.apply_async()
            chunk_results = results.get()  # Wait for all chunks to complete
        
        # Update progress as chunks complete
        job = Job.query.get(job_id)
        job.processed_chunks = len(chunk_results)
        job.progress_percent = 75
        job.current_step = "Merging results"
        db.session.commit()
        
        # Merge chunk results
        all_sentences = merge_chunk_results(chunk_results)
        
        # Calculate metrics
        total_tokens = sum(r.get('tokens', 0) for r in chunk_results if r.get('status') == 'success')
        failed_chunks = [r['chunk_id'] for r in chunk_results if r.get('status') == 'failed']
        
        # Update job with results
        job = Job.query.get(job_id)
        job.status = JOB_STATUS_COMPLETED
        job.progress_percent = 100
        job.current_step = "Completed"
        job.actual_tokens = total_tokens
        job.gemini_tokens_used = total_tokens
        job.gemini_api_calls = len(chunk_results)
        job.completed_at = datetime.utcnow()
        job.chunk_results = chunk_results
        job.failed_chunks = failed_chunks if failed_chunks else None
        
        # Calculate processing time
        if job.started_at:
            processing_time = (job.completed_at - job.started_at).total_seconds()
            job.processing_time_seconds = int(processing_time)
        
        db.session.commit()
        
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
            db.session.commit()
        raise
        
    finally:
        # Cleanup temporary files
        if chunks:
            chunking_service.cleanup_chunks(chunks)
        
        # Cleanup uploaded PDF
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
        except Exception:
            pass

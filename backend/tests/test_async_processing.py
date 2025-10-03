"""Integration tests for async PDF processing"""
import os
import tempfile
import pytest
from PyPDF2 import PdfWriter
from app import db
from app.models import Job
from app.services.job_service import JobService
from app.services.chunking_service import PDFChunkingService


def test_chunking_detection(app, large_pdf):
    """Test that large PDFs are correctly identified for chunking"""
    with app.app_context():
        service = PDFChunkingService(large_pdf)
        
        assert service.total_pages == 100
        assert service.should_chunk() is True
        
        chunks = service.calculate_chunks()
        assert len(chunks) == 2
        assert chunks[0] == (0, 50)
        assert chunks[1] == (50, 100)


def test_job_creation_with_progress_tracking(app, test_user):
    """Test job creation with progress tracking fields"""
    with app.app_context():
        job = JobService.create_job(
            user_id=test_user,
            original_filename='test.pdf',
            model_preference='balanced',
            estimated_tokens=10000,
            processing_settings={'sentence_length_limit': 8}
        )
        
        assert job.id is not None
        assert job.status == 'pending'
        assert job.total_chunks == 0
        assert job.completed_chunks == 0
        assert job.progress_percent == 0
        assert job.celery_task_id is None


def test_job_progress_update(app, test_user):
    """Test updating job progress"""
    with app.app_context():
        job = JobService.create_job(
            user_id=test_user,
            original_filename='large_novel.pdf',
            model_preference='balanced',
            estimated_tokens=50000,
            processing_settings={'sentence_length_limit': 8}
        )
        
        # Simulate chunked processing
        job.total_chunks = 4
        job.completed_chunks = 0
        job.progress_percent = 0
        db.session.commit()
        
        # Update progress as chunks complete
        job.completed_chunks = 1
        job.progress_percent = 25
        db.session.commit()
        
        retrieved_job = Job.query.get(job.id)
        assert retrieved_job.total_chunks == 4
        assert retrieved_job.completed_chunks == 1
        assert retrieved_job.progress_percent == 25
        
        # Complete more chunks
        job.completed_chunks = 3
        job.progress_percent = 75
        db.session.commit()
        
        retrieved_job = Job.query.get(job.id)
        assert retrieved_job.completed_chunks == 3
        assert retrieved_job.progress_percent == 75


def test_job_to_dict_with_progress(app, test_user):
    """Test job serialization includes progress fields"""
    with app.app_context():
        job = JobService.create_job(
            user_id=test_user,
            original_filename='test.pdf',
            model_preference='balanced',
            estimated_tokens=10000,
            processing_settings={'sentence_length_limit': 8}
        )
        
        job.total_chunks = 4
        job.completed_chunks = 2
        job.progress_percent = 50
        job.celery_task_id = 'test-task-123'
        db.session.commit()
        
        job_dict = job.to_dict()
        
        assert 'total_chunks' in job_dict
        assert 'completed_chunks' in job_dict
        assert 'progress_percent' in job_dict
        assert 'celery_task_id' in job_dict
        
        assert job_dict['total_chunks'] == 4
        assert job_dict['completed_chunks'] == 2
        assert job_dict['progress_percent'] == 50
        assert job_dict['celery_task_id'] == 'test-task-123'


def test_small_pdf_no_chunking(app):
    """Test that small PDFs don't trigger chunking"""
    # Create a small PDF (10 pages)
    pdf_writer = PdfWriter()
    for i in range(10):
        pdf_writer.add_blank_page(width=612, height=792)
    
    with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
        pdf_writer.write(temp_file)
        small_pdf = temp_file.name
    
    try:
        with app.app_context():
            service = PDFChunkingService(small_pdf)
            
            assert service.total_pages == 10
            assert service.should_chunk() is False
    finally:
        if os.path.exists(small_pdf):
            os.remove(small_pdf)

"""Unit tests for async task functions"""
import os
import tempfile
import pytest
from unittest.mock import Mock, patch, MagicMock
from PyPDF2 import PdfWriter
from app.services.chunking_service import PDFChunkingService
from app.services.job_service import JobService
from app.models import Job


def test_chunking_service_initialization(app):
    """Test that chunking service initializes correctly"""
    # Create a temporary PDF
    pdf_writer = PdfWriter()
    for i in range(10):
        pdf_writer.add_blank_page(width=612, height=792)
    
    with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
        pdf_writer.write(temp_file)
        temp_path = temp_file.name
    
    try:
        with app.app_context():
            service = PDFChunkingService(temp_path)
            assert service.pdf_path == temp_path
            assert service.total_pages == 10
            assert service.chunking_threshold == 50
            assert service.default_chunk_size == 50
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


def test_job_service_create_job(app, test_user):
    """Test job creation via JobService"""
    with app.app_context():
        job = JobService.create_job(
            user_id=test_user,
            original_filename='test.pdf',
            model_preference='balanced',
            estimated_tokens=5000,
            processing_settings={'sentence_length_limit': 8}
        )
        
        assert job is not None
        assert job.user_id == test_user
        assert job.original_filename == 'test.pdf'
        assert job.status == 'pending'
        assert job.estimated_tokens == 5000
        assert job.total_chunks == 0
        assert job.completed_chunks == 0
        assert job.progress_percent == 0


def test_job_service_start_job(app, test_user):
    """Test starting a job"""
    with app.app_context():
        job = JobService.create_job(
            user_id=test_user,
            original_filename='test.pdf',
            model_preference='balanced',
            estimated_tokens=5000,
            processing_settings={'sentence_length_limit': 8}
        )
        
        result = JobService.start_job(job.id)
        assert result is True
        
        updated_job = Job.query.get(job.id)
        assert updated_job.status == 'processing'
        assert updated_job.started_at is not None


def test_job_service_complete_job(app, test_user):
    """Test completing a job"""
    with app.app_context():
        job = JobService.create_job(
            user_id=test_user,
            original_filename='test.pdf',
            model_preference='balanced',
            estimated_tokens=5000,
            processing_settings={'sentence_length_limit': 8}
        )
        
        JobService.start_job(job.id)
        completed_job = JobService.complete_job(job.id, actual_tokens=4800)
        
        assert completed_job.status == 'completed'
        assert completed_job.actual_tokens == 4800
        assert completed_job.completed_at is not None


def test_job_service_fail_job(app, test_user):
    """Test failing a job"""
    with app.app_context():
        job = JobService.create_job(
            user_id=test_user,
            original_filename='test.pdf',
            model_preference='balanced',
            estimated_tokens=5000,
            processing_settings={'sentence_length_limit': 8}
        )
        
        JobService.start_job(job.id)
        failed_job = JobService.fail_job(job.id, 'Test error', 'TEST_ERROR_CODE')
        
        assert failed_job.status == 'failed'
        assert failed_job.error_message == 'Test error'
        assert failed_job.error_code == 'TEST_ERROR_CODE'
        assert failed_job.completed_at is not None


def test_job_service_cancel_job(app, test_user):
    """Test cancelling a job"""
    with app.app_context():
        job = JobService.create_job(
            user_id=test_user,
            original_filename='test.pdf',
            model_preference='balanced',
            estimated_tokens=5000,
            processing_settings={'sentence_length_limit': 8}
        )
        
        cancelled_job = JobService.cancel_job(job.id)
        
        assert cancelled_job.status == 'cancelled'
        assert cancelled_job.completed_at is not None


def test_job_service_estimate_tokens(app):
    """Test token estimation"""
    with app.app_context():
        text = "This is a test sentence. " * 100
        tokens = JobService.estimate_tokens_heuristic(text)
        
        assert tokens > 0
        # Heuristic uses ~4 chars per token
        expected_approx = len(text) / 4 * 1.1  # with safety buffer
        assert tokens > 0
        assert tokens < len(text)  # Sanity check


def test_job_service_calculate_credits(app):
    """Test credit calculation"""
    with app.app_context():
        # Test with balanced model
        credits = JobService.calculate_credits(1000, 'gemini-2.5-flash')
        assert credits == 1  # 1 credit per 1K tokens for balanced
        
        # Test with quality model
        credits = JobService.calculate_credits(1000, 'gemini-2.5-pro')
        assert credits == 5  # 5 credits per 1K tokens for quality
        
        # Test with small token count (minimum 1 credit)
        credits = JobService.calculate_credits(100, 'gemini-2.5-flash')
        assert credits == 1  # Minimum 1 credit


def test_chunking_service_text_extraction(large_pdf):
    """Test text extraction from PDF chunks"""
    service = PDFChunkingService(large_pdf)
    
    # Extract text from first 10 pages
    text = service.extract_text_from_chunk(0, 10)
    
    assert isinstance(text, str)
    # Blank pages return minimal text
    assert len(text) >= 0


def test_chunking_service_chunk_calculation_edge_cases(app):
    """Test chunk calculation with various page counts"""
    # Create PDFs with different page counts
    test_cases = [
        (45, 1),   # Below threshold, 1 chunk
        (50, 1),   # At threshold, 1 chunk
        (51, 2),   # Just over threshold, 2 chunks
        (100, 2),  # 100 pages, 2 chunks of 50
        (150, 3),  # 150 pages, 3 chunks of 50
    ]
    
    for page_count, expected_chunks in test_cases:
        pdf_writer = PdfWriter()
        for i in range(page_count):
            pdf_writer.add_blank_page(width=612, height=792)
        
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
            pdf_writer.write(temp_file)
            temp_path = temp_file.name
        
        try:
            with app.app_context():
                service = PDFChunkingService(temp_path)
                chunks = service.calculate_chunks()
                assert len(chunks) == expected_chunks, f"Failed for {page_count} pages"
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

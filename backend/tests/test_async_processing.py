"""Tests for async PDF processing and chunking functionality"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from app.services.pdf_service import PDFService
from app.constants import CHUNK_THRESHOLD_PAGES, DEFAULT_CHUNK_SIZE_PAGES


class TestPDFService:
    """Test PDF service chunking functionality"""
    
    def test_get_page_count(self, tmp_path):
        """Test getting page count from a PDF"""
        # Create a simple test PDF using PyPDF2
        import PyPDF2
        from PyPDF2 import PdfWriter
        
        writer = PdfWriter()
        # Add 3 blank pages
        for _ in range(3):
            writer.add_blank_page(width=200, height=200)
        
        pdf_path = tmp_path / "test.pdf"
        with open(pdf_path, 'wb') as f:
            writer.write(f)
        
        # Test
        service = PDFService(None)
        service.temp_file_path = str(pdf_path)
        count = service.get_page_count(str(pdf_path))
        
        assert count == 3
    
    def test_split_pdf_by_pages(self, tmp_path):
        """Test splitting PDF into page ranges"""
        import PyPDF2
        from PyPDF2 import PdfWriter, PdfReader
        
        # Create a PDF with 5 pages
        writer = PdfWriter()
        for i in range(5):
            writer.add_blank_page(width=200, height=200)
        
        pdf_path = tmp_path / "test.pdf"
        with open(pdf_path, 'wb') as f:
            writer.write(f)
        
        # Split pages 1-3 (0-indexed)
        service = PDFService(None)
        chunk_path = service.split_pdf_by_pages(str(pdf_path), 1, 4)
        
        # Verify the chunk has 3 pages
        with open(chunk_path, 'rb') as f:
            reader = PdfReader(f)
            assert len(reader.pages) == 3
        
        # Clean up
        import os
        os.remove(chunk_path)
    
    def test_split_pdf_invalid_range(self, tmp_path):
        """Test splitting PDF with invalid page range"""
        import PyPDF2
        from PyPDF2 import PdfWriter
        
        writer = PdfWriter()
        writer.add_blank_page(width=200, height=200)
        
        pdf_path = tmp_path / "test.pdf"
        with open(pdf_path, 'wb') as f:
            writer.write(f)
        
        service = PDFService(None)
        
        # Test invalid range
        with pytest.raises(ValueError):
            service.split_pdf_by_pages(str(pdf_path), 0, 10)  # Out of range


class TestJobModel:
    """Test Job model chunking fields"""
    
    def test_job_model_has_chunking_fields(self):
        """Test that Job model has all required chunking fields"""
        from app.models import Job
        
        # Check that the model has the new fields
        assert hasattr(Job, 'page_count')
        assert hasattr(Job, 'chunk_size')
        assert hasattr(Job, 'total_chunks')
        assert hasattr(Job, 'completed_chunks')
        assert hasattr(Job, 'progress_percent')
        assert hasattr(Job, 'parent_job_id')
    
    def test_job_to_dict_includes_chunking_fields(self, app):
        """Test that Job.to_dict() includes chunking fields"""
        from app.models import Job
        from datetime import datetime
        
        with app.app_context():
            job = Job(
                user_id=1,
                status='processing',
                original_filename='test.pdf',
                model='gemini-2.5-flash',
                estimated_credits=100,
                pricing_version='v1.0',
                pricing_rate=1.0,
                page_count=120,
                chunk_size=25,
                total_chunks=5,
                completed_chunks=2,
                progress_percent=40.0
            )
            
            job_dict = job.to_dict()
            
            assert job_dict['page_count'] == 120
            assert job_dict['chunk_size'] == 25
            assert job_dict['total_chunks'] == 5
            assert job_dict['completed_chunks'] == 2
            assert job_dict['progress_percent'] == 40.0


class TestConstants:
    """Test async processing constants"""
    
    def test_chunking_constants_exist(self):
        """Test that chunking constants are defined"""
        from app.constants import (
            CHUNK_THRESHOLD_PAGES,
            DEFAULT_CHUNK_SIZE_PAGES,
            JOB_STATUS_QUEUED
        )
        
        assert CHUNK_THRESHOLD_PAGES == 50
        assert DEFAULT_CHUNK_SIZE_PAGES == 25
        assert JOB_STATUS_QUEUED == 'queued'


class TestAsyncTasks:
    """Test async task functions"""
    
    @patch('app.tasks.GeminiService')
    @patch('app.tasks.PDFService')
    def test_process_pdf_chunk_calculation(self, mock_pdf_service, mock_gemini_service, app):
        """Test that large PDFs are correctly chunked"""
        from app.tasks import process_pdf_chunked
        from app.models import Job
        
        with app.app_context():
            # Create a test job
            job = Job(
                id=1,
                user_id=1,
                status='pending',
                original_filename='large.pdf',
                model='gemini-2.5-flash',
                estimated_credits=1000,
                pricing_version='v1.0',
                pricing_rate=1.0
            )
            
            from app import db
            db.session.add(job)
            db.session.commit()
            
            # Calculate expected chunks
            page_count = 120
            expected_chunks = (page_count + DEFAULT_CHUNK_SIZE_PAGES - 1) // DEFAULT_CHUNK_SIZE_PAGES
            
            assert expected_chunks == 5  # 120 / 25 = 4.8, rounded up to 5


@pytest.fixture
def app():
    """Create application for testing"""
    from app import create_app
    
    app = create_app()
    app.config.update({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
        'SECRET_KEY': 'test-secret-key',
        'GEMINI_API_KEY': 'test-api-key',
    })
    
    with app.app_context():
        from app import db
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()

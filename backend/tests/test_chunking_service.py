"""Tests for PDF chunking service"""
import os
import tempfile
import pytest
from PyPDF2 import PdfWriter, PdfReader
from app.services.chunking_service import PDFChunkingService


def test_chunking_service_page_count(large_pdf):
    """Test that chunking service correctly counts pages"""
    service = PDFChunkingService(large_pdf)
    assert service.total_pages == 100


def test_chunking_threshold(large_pdf):
    """Test that chunking threshold is correctly applied"""
    service = PDFChunkingService(large_pdf)
    
    # Default threshold is 50 pages
    assert service.should_chunk() is True
    
    # Create a small PDF
    pdf_writer = PdfWriter()
    for i in range(10):
        pdf_writer.add_blank_page(width=612, height=792)
    
    with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
        pdf_writer.write(temp_file)
        small_pdf = temp_file.name
    
    small_service = PDFChunkingService(small_pdf)
    assert small_service.should_chunk() is False
    
    # Cleanup
    os.remove(small_pdf)


def test_calculate_chunks(large_pdf):
    """Test chunk calculation"""
    service = PDFChunkingService(large_pdf)
    
    # With default chunk size (50 pages), should get 2 chunks
    chunks = service.calculate_chunks(chunk_size_pages=50)
    assert len(chunks) == 2
    assert chunks[0] == (0, 50)
    assert chunks[1] == (50, 100)
    
    # With 25 pages per chunk, should get 4 chunks
    chunks = service.calculate_chunks(chunk_size_pages=25)
    assert len(chunks) == 4
    assert chunks[0] == (0, 25)
    assert chunks[1] == (25, 50)
    assert chunks[2] == (50, 75)
    assert chunks[3] == (75, 100)


def test_extract_chunk(large_pdf):
    """Test chunk extraction"""
    service = PDFChunkingService(large_pdf)
    
    # Extract first chunk (pages 0-50)
    chunk_path = service.extract_chunk(0, 50)
    
    try:
        # Verify chunk was created
        assert os.path.exists(chunk_path)
        
        # Verify chunk has correct number of pages
        with open(chunk_path, 'rb') as f:
            reader = PdfReader(f)
            assert len(reader.pages) == 50
    finally:
        # Cleanup
        if os.path.exists(chunk_path):
            os.remove(chunk_path)


def test_chunk_cleanup():
    """Test chunk file cleanup"""
    # Create a temporary file
    with tempfile.NamedTemporaryFile(delete=False, suffix='_chunk_0_50.pdf') as temp_file:
        temp_path = temp_file.name
        temp_file.write(b'test content')
    
    # Verify file exists
    assert os.path.exists(temp_path)
    
    # Cleanup
    PDFChunkingService.cleanup_chunk(temp_path)
    
    # Verify file was deleted
    assert not os.path.exists(temp_path)


def test_extract_text_from_chunk(large_pdf):
    """Test text extraction from chunk"""
    service = PDFChunkingService(large_pdf)
    
    # Extract text from first 10 pages
    text = service.extract_text_from_chunk(0, 10)
    
    # Blank pages should return empty or whitespace text
    assert isinstance(text, str)
    # Text might be empty or contain page markers
    assert len(text) >= 0

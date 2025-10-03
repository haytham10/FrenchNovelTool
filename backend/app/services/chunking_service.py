"""Service for chunking large PDFs into processable segments"""
import PyPDF2
from typing import List, Tuple
import tempfile
import os
from flask import current_app


class PDFChunkingService:
    """Service for splitting PDFs into chunks for parallel processing"""
    
    # Default: 50 pages per chunk for balanced processing
    DEFAULT_CHUNK_SIZE_PAGES = 50
    # Threshold: files larger than this will be chunked
    CHUNKING_THRESHOLD_PAGES = 50
    
    def __init__(self, pdf_path: str):
        """
        Initialize chunking service with a PDF file.
        
        Args:
            pdf_path: Path to the PDF file
        """
        self.pdf_path = pdf_path
        self.total_pages = self._get_page_count()
    
    def _get_page_count(self) -> int:
        """Get total number of pages in the PDF"""
        try:
            with open(self.pdf_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                return len(reader.pages)
        except Exception as e:
            current_app.logger.error(f'Failed to read PDF page count: {str(e)}')
            raise ValueError(f'Invalid PDF file: {str(e)}')
    
    def should_chunk(self) -> bool:
        """
        Determine if the PDF should be chunked based on size.
        
        Returns:
            True if PDF should be chunked, False otherwise
        """
        return self.total_pages > self.CHUNKING_THRESHOLD_PAGES
    
    def calculate_chunks(self, chunk_size_pages: int = DEFAULT_CHUNK_SIZE_PAGES) -> List[Tuple[int, int]]:
        """
        Calculate chunk ranges for the PDF.
        
        Args:
            chunk_size_pages: Number of pages per chunk
            
        Returns:
            List of (start_page, end_page) tuples (0-indexed, end is exclusive)
        """
        chunks = []
        for start_page in range(0, self.total_pages, chunk_size_pages):
            end_page = min(start_page + chunk_size_pages, self.total_pages)
            chunks.append((start_page, end_page))
        
        current_app.logger.info(
            f'Calculated {len(chunks)} chunks for PDF with {self.total_pages} pages '
            f'(chunk size: {chunk_size_pages})'
        )
        
        return chunks
    
    def extract_chunk(self, start_page: int, end_page: int) -> str:
        """
        Extract a chunk of pages from the PDF as a new temporary PDF file.
        
        Args:
            start_page: Starting page (0-indexed, inclusive)
            end_page: Ending page (0-indexed, exclusive)
            
        Returns:
            Path to the temporary PDF file containing the chunk
        """
        try:
            with open(self.pdf_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                writer = PyPDF2.PdfWriter()
                
                # Add pages to the writer
                for page_num in range(start_page, end_page):
                    if page_num < len(reader.pages):
                        writer.add_page(reader.pages[page_num])
                
                # Write to temporary file
                with tempfile.NamedTemporaryFile(
                    delete=False, 
                    suffix=f'_chunk_{start_page}_{end_page}.pdf'
                ) as temp_file:
                    writer.write(temp_file)
                    chunk_path = temp_file.name
                
                current_app.logger.info(
                    f'Extracted chunk pages {start_page}-{end_page} to {chunk_path}'
                )
                
                return chunk_path
                
        except Exception as e:
            current_app.logger.error(f'Failed to extract chunk {start_page}-{end_page}: {str(e)}')
            raise ValueError(f'Failed to extract PDF chunk: {str(e)}')
    
    def extract_text_from_chunk(self, start_page: int, end_page: int) -> str:
        """
        Extract text directly from a range of pages without creating a new PDF.
        More efficient for text extraction.
        
        Args:
            start_page: Starting page (0-indexed, inclusive)
            end_page: Ending page (0-indexed, exclusive)
            
        Returns:
            Extracted text from the chunk
        """
        try:
            text = ""
            with open(self.pdf_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                
                for page_num in range(start_page, end_page):
                    if page_num < len(reader.pages):
                        text += reader.pages[page_num].extract_text() + "\n"
            
            current_app.logger.info(
                f'Extracted text from chunk pages {start_page}-{end_page}: '
                f'{len(text)} characters'
            )
            
            return text
            
        except Exception as e:
            current_app.logger.error(f'Failed to extract text from chunk {start_page}-{end_page}: {str(e)}')
            raise ValueError(f'Failed to extract text from PDF chunk: {str(e)}')
    
    @staticmethod
    def cleanup_chunk(chunk_path: str):
        """
        Delete a temporary chunk file.
        
        Args:
            chunk_path: Path to the chunk file to delete
        """
        if chunk_path and os.path.exists(chunk_path):
            try:
                os.remove(chunk_path)
                current_app.logger.debug(f'Cleaned up chunk file: {chunk_path}')
            except Exception as e:
                current_app.logger.warning(f'Failed to cleanup chunk {chunk_path}: {str(e)}')

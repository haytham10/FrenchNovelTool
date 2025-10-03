"""PDF file handling service"""
import os
import tempfile
import PyPDF2


class PDFService:
    """Service for handling PDF file operations"""
    
    def __init__(self, file):
        """
        Initialize PDF service with uploaded file.
        
        Args:
            file: Werkzeug FileStorage object containing the uploaded PDF
        """
        self.file = file
        self.temp_file_path = None

    def save_to_temp(self):
        """
        Save uploaded PDF to a temporary file.
        
        Returns:
            str: Path to the temporary file
        """
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
            self.file.save(temp_file.name)
            self.temp_file_path = temp_file.name
        return self.temp_file_path

    def get_page_count(self, pdf_path=None):
        """
        Get the number of pages in the PDF.
        
        Args:
            pdf_path: Path to PDF file (uses temp_file_path if not provided)
            
        Returns:
            int: Number of pages in the PDF
        """
        path = pdf_path or self.temp_file_path
        if not path or not os.path.exists(path):
            raise ValueError("PDF file not found")
        
        with open(path, 'rb') as pdf_file:
            reader = PyPDF2.PdfReader(pdf_file)
            return len(reader.pages)

    def split_pdf_by_pages(self, pdf_path, start_page, end_page):
        """
        Extract a range of pages from a PDF and save to a temporary file.
        
        Args:
            pdf_path: Path to source PDF file
            start_page: Starting page number (0-indexed)
            end_page: Ending page number (exclusive, 0-indexed)
            
        Returns:
            str: Path to the temporary file containing the extracted pages
        """
        if not os.path.exists(pdf_path):
            raise ValueError(f"PDF file not found: {pdf_path}")
        
        with open(pdf_path, 'rb') as input_file:
            reader = PyPDF2.PdfReader(input_file)
            writer = PyPDF2.PdfWriter()
            
            # Validate page range
            total_pages = len(reader.pages)
            if start_page < 0 or end_page > total_pages or start_page >= end_page:
                raise ValueError(
                    f"Invalid page range: {start_page}-{end_page} (total pages: {total_pages})"
                )
            
            # Add pages to writer
            for page_num in range(start_page, end_page):
                writer.add_page(reader.pages[page_num])
            
            # Save to temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
                writer.write(temp_file)
                return temp_file.name

    def delete_temp_file(self):
        """Delete the temporary file if it exists"""
        if self.temp_file_path and os.path.exists(self.temp_file_path):
            os.remove(self.temp_file_path)


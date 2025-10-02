"""PDF file handling service"""
import os
import tempfile


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

    def delete_temp_file(self):
        """Delete the temporary file if it exists"""
        if self.temp_file_path and os.path.exists(self.temp_file_path):
            os.remove(self.temp_file_path)

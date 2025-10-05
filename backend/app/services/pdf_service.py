"""PDF file handling service"""
import os
import tempfile
import subprocess
import shutil
import io
import sys


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

    def extract_text_snippet(self, char_limit: int = 50000) -> tuple[str, int]:
        """
        Extract text up to `char_limit` characters from the saved temp PDF.

        Uses system `pdftotext` (poppler) when available for performance and
        falls back to PyPDF2 if not present.

        Returns:
            tuple: (text_snippet, page_count)
        """
        if not self.temp_file_path or not os.path.exists(self.temp_file_path):
            raise FileNotFoundError('Temporary PDF file not found')

        # Prefer pdftotext (fast C-based binary) when available
        pdftotext_path = shutil.which('pdftotext')
        if pdftotext_path:
            try:
                # Use -layout to preserve some layout (may help extraction quality)
                # Output to stdout by using '-' as output filename
                proc = subprocess.run([pdftotext_path, '-layout', self.temp_file_path, '-'],
                                      capture_output=True, check=True, timeout=30)
                out = proc.stdout.decode('utf-8', errors='replace')
                # Return snippet and page count if possible (pdftotext doesn't provide page count)
                snippet = out[:char_limit]
                # Fallback page_count via PyPDF2 if caller needs it
                try:
                    import PyPDF2
                    with open(self.temp_file_path, 'rb') as f:
                        reader = PyPDF2.PdfReader(f)
                        page_count = len(reader.pages)
                except Exception:
                    page_count = -1
                return snippet, page_count
            except subprocess.CalledProcessError:
                # Fall back to PyPDF2 on error
                pass
            except Exception:
                pass

        # Fallback: use PyPDF2 (slower but pure-Python)
        try:
            import PyPDF2
            text = ''
            with open(self.temp_file_path, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                for page in reader.pages:
                    try:
                        text += (page.extract_text() or '') + '\n'
                    except Exception:
                        continue
                    if len(text) >= char_limit:
                        break
                return text[:char_limit], len(reader.pages)
        except Exception as e:
            raise RuntimeError(f'Failed to extract text: {e}')

    def get_page_count(self, file_stream=None) -> dict:
        """
        Get metadata-only page count and file information without text extraction.
        
        This is a fast, lightweight operation that only reads PDF metadata,
        making it suitable for cost estimation before full processing.
        
        Args:
            file_stream: Optional seekable file-like stream. If not provided,
                        uses the uploaded file from initialization.
        
        Returns:
            dict: {
                'page_count': int,
                'file_size': int (bytes),
                'image_count': int (estimated, optional)
            }
            
        Raises:
            RuntimeError: If PDF is invalid or corrupted
        """
        try:
            import PyPDF2
            
            # Use provided stream or the instance file
            stream = file_stream if file_stream else self.file
            
            # Ensure stream is seekable and at start
            if hasattr(stream, 'seek'):
                stream.seek(0)
            
            # Read file size
            if hasattr(stream, 'content_length') and stream.content_length:
                file_size = stream.content_length
            else:
                # Read current position, seek to end, get size, seek back
                current_pos = stream.tell() if hasattr(stream, 'tell') else 0
                if hasattr(stream, 'seek'):
                    stream.seek(0, 2)  # Seek to end
                    file_size = stream.tell()
                    stream.seek(current_pos)  # Seek back
                else:
                    file_size = 0
            
            # Get page count using PyPDF2 (metadata-only, no text extraction)
            reader = PyPDF2.PdfReader(stream)
            page_count = len(reader.pages)
            
            # Optionally estimate image count by inspecting /XObject resources
            image_count = 0
            try:
                for page in reader.pages:
                    if '/Resources' in page and '/XObject' in page['/Resources']:
                        xobject = page['/Resources']['/XObject']
                        if hasattr(xobject, 'get_object'):
                            xobject = xobject.get_object()
                        # Count XObjects that are likely images
                        for obj in xobject.values() if hasattr(xobject, 'values') else []:
                            if hasattr(obj, 'get_object'):
                                obj = obj.get_object()
                            if hasattr(obj, 'get') and obj.get('/Subtype') == '/Image':
                                image_count += 1
            except Exception:
                # Image counting is optional, don't fail if it doesn't work
                pass
            
            return {
                'page_count': page_count,
                'file_size': file_size,
                'image_count': image_count
            }
            
        except PyPDF2.errors.PdfReadError as e:
            raise RuntimeError(f'Invalid or corrupted PDF file: {e}')
        except Exception as e:
            raise RuntimeError(f'Failed to read PDF metadata: {e}')

    def delete_temp_file(self):
        """Delete the temporary file if it exists"""
        if self.temp_file_path and os.path.exists(self.temp_file_path):
            os.remove(self.temp_file_path)

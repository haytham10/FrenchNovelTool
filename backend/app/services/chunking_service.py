"""Service for splitting large PDFs into processable chunks"""
import os
import io
import base64
from typing import List, Dict
from app.pdf_compat import PdfReader, PdfWriter


class ChunkingService:
    """Service for splitting large PDFs into processable chunks"""
    
    CHUNK_SIZES = {
        'small': {'max_pages': 30, 'chunk_size': 30, 'parallel': 1},
        'medium': {'max_pages': 100, 'chunk_size': 20, 'parallel': 3},
        'large': {'max_pages': 500, 'chunk_size': 15, 'parallel': 5},
    }
    
    OVERLAP_PAGES = 1  # Pages to overlap between chunks for context
    
    def calculate_chunks(self, page_count: int) -> Dict:
        """
        Determine optimal chunking strategy based on PDF size.
        
        Args:
            page_count: Total number of pages in PDF
            
        Returns:
            Dictionary with chunking configuration:
            {
                'chunk_size': int,       # Pages per chunk
                'num_chunks': int,       # Total chunks
                'parallel_workers': int, # Suggested parallel workers
                'strategy': str,         # 'small', 'medium', or 'large'
                'total_pages': int
            }
        """
        # Determine strategy based on page count
        if page_count <= self.CHUNK_SIZES['small']['max_pages']:
            strategy = 'small'
        elif page_count <= self.CHUNK_SIZES['medium']['max_pages']:
            strategy = 'medium'
        else:
            strategy = 'large'
        
        config = self.CHUNK_SIZES[strategy]
        chunk_size = config['chunk_size']
        
        # Calculate number of chunks (accounting for overlap)
        num_chunks = max(1, (page_count + chunk_size - 1) // chunk_size)
        
        return {
            'chunk_size': chunk_size,
            'num_chunks': num_chunks,
            'parallel_workers': config['parallel'],
            'strategy': strategy,
            'total_pages': page_count,
        }
    
    def split_pdf(self, pdf_path: str, chunk_config: Dict) -> List[Dict]:
        """
        Split PDF into chunks with context overlap.
        
        Args:
            pdf_path: Path to source PDF
            chunk_config: Output from calculate_chunks()
        
        Returns:
            List of chunk metadata:
            [
                {
                    'chunk_id': 0,
                    'file_path': '/tmp/chunk_0.pdf',
                    'start_page': 0,
                    'end_page': 19,
                    'page_count': 20,
                    'has_overlap': False
                },
                ...
            ]
        """
        chunks = []
        chunk_size = chunk_config['chunk_size']
        total_pages = chunk_config['total_pages']
        
        with open(pdf_path, 'rb') as pdf_file:
            pdf_reader = PdfReader(pdf_file)
            
            for i in range(chunk_config['num_chunks']):
                # Calculate page range with overlap
                start_page = max(0, i * chunk_size - (self.OVERLAP_PAGES if i > 0 else 0))
                end_page = min(total_pages, (i + 1) * chunk_size)
                
                # Create chunk PDF
                pdf_writer = PdfWriter()
                for page_num in range(start_page, end_page):
                    pdf_writer.add_page(pdf_reader.pages[page_num])
                
                # Write chunk PDF into memory and encode as base64 so the chunk
                # can be dispatched to other workers without requiring shared
                # filesystem access. This avoids cases where the creating
                # worker's /tmp files aren't visible to other workers.
                buf = io.BytesIO()
                pdf_writer.write(buf)
                chunk_bytes = buf.getvalue()
                chunk_b64 = base64.b64encode(chunk_bytes).decode('ascii')

                chunks.append({
                    'chunk_id': i,
                    # file_b64 contains the chunk PDF bytes encoded as base64.
                    # Workers should prefer this field when present.
                    'file_b64': chunk_b64,
                    # Preserve file_path=None to indicate no local temp file was
                    # created by the chunking service.
                    'file_path': None,
                    'start_page': start_page,
                    'end_page': end_page - 1,  # Inclusive
                    'page_count': end_page - start_page,
                    'has_overlap': i > 0,  # First chunk has no overlap
                })
        
        return chunks
    
    def split_pdf_and_persist(self, pdf_path: str, chunk_config: Dict, job_id: int, db) -> List[int]:
        """
        Split PDF into chunks and persist to database.
        
        Args:
            pdf_path: Path to source PDF
            chunk_config: Output from calculate_chunks()
            job_id: Job ID to associate chunks with
            db: SQLAlchemy database instance
            
        Returns:
            List of JobChunk IDs created
        """
        from app.models import JobChunk
        from datetime import datetime
        
        chunk_db_ids = []
        chunk_size = chunk_config['chunk_size']
        total_pages = chunk_config['total_pages']
        
        with open(pdf_path, 'rb') as pdf_file:
            pdf_reader = PdfReader(pdf_file)
            
            for i in range(chunk_config['num_chunks']):
                # Calculate page range with overlap
                start_page = max(0, i * chunk_size - (self.OVERLAP_PAGES if i > 0 else 0))
                end_page = min(total_pages, (i + 1) * chunk_size)
                
                # Create chunk PDF in memory
                pdf_writer = PdfWriter()
                for page_num in range(start_page, end_page):
                    pdf_writer.add_page(pdf_reader.pages[page_num])
                
                # Encode chunk as base64
                buf = io.BytesIO()
                pdf_writer.write(buf)
                chunk_bytes = buf.getvalue()
                chunk_b64 = base64.b64encode(chunk_bytes).decode('ascii')
                
                # Create JobChunk record in DB
                chunk = JobChunk(
                    job_id=job_id,
                    chunk_id=i,
                    start_page=start_page,
                    end_page=end_page - 1,  # Inclusive
                    page_count=end_page - start_page,
                    has_overlap=(i > 0),
                    file_b64=chunk_b64,
                    file_size_bytes=len(chunk_bytes),
                    status='pending',
                    attempts=0,
                    max_retries=3,
                    created_at=datetime.utcnow()
                )
                
                db.session.add(chunk)
                db.session.flush()  # Get chunk ID without committing
                chunk_db_ids.append(chunk.id)
        
        # Commit all chunks at once
        db.session.commit()
        
        return chunk_db_ids
    
    def cleanup_chunks(self, chunks: List[Dict]):
        """Delete temporary chunk files"""
        for chunk in chunks:
            try:
                # Only attempt filesystem cleanup if a file_path was created.
                fp = chunk.get('file_path')
                if fp:
                    if os.path.exists(fp):
                        os.remove(fp)
            except Exception as e:
                # Log but don't fail
                import logging
                logging.warning(f"Failed to cleanup chunk {chunk['chunk_id']}: {e}")

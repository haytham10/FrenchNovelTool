"""Service for splitting large PDFs into processable chunks"""
import os
import io
import base64
from typing import List, Dict
from app import db
from app.models import JobChunk
from PyPDF2 import PdfWriter, PdfReader


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
    
    def split_pdf(self, pdf_path: str, chunk_config: Dict, *, job_id: int) -> List[Dict]:
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

                # Persist chunk row for durable retries
                jc = JobChunk(
                    job_id=job_id,
                    chunk_index=i,
                    file_b64=chunk_b64,
                    file_size_bytes=len(chunk_bytes),
                    start_page=start_page,
                    end_page=end_page - 1,
                    status='pending',
                    attempts=0,
                )
                db.session.add(jc)
                db.session.flush()  # assign id without committing

                chunks.append({
                    'chunk_id': i,
                    'job_chunk_id': jc.id,
                    'job_id': job_id,
                    'start_page': start_page,
                    'end_page': end_page - 1,  # Inclusive
                    'page_count': end_page - start_page,
                    'has_overlap': i > 0,  # First chunk has no overlap
                })
        
        # Commit all chunk rows in one go
        db.session.commit()
        return chunks
    
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

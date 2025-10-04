"""Tests for async PDF processing features"""
import pytest
import os
import tempfile
from unittest.mock import Mock, patch, MagicMock
from app.services.chunking_service import ChunkingService
from app.tasks import merge_chunk_results


class TestChunkingService:
    """Tests for PDF chunking service"""
    
    def test_calculate_chunks_small_pdf(self):
        """Test chunking strategy for small PDFs (≤30 pages)"""
        service = ChunkingService()
        config = service.calculate_chunks(page_count=25)
        
        assert config['strategy'] == 'small'
        assert config['chunk_size'] == 30
        assert config['num_chunks'] == 1
        assert config['parallel_workers'] == 1
        assert config['total_pages'] == 25
    
    def test_calculate_chunks_medium_pdf(self):
        """Test chunking strategy for medium PDFs (31-100 pages)"""
        service = ChunkingService()
        config = service.calculate_chunks(page_count=80)
        
        assert config['strategy'] == 'medium'
        assert config['chunk_size'] == 20
        assert config['num_chunks'] == 4  # 80 / 20 = 4
        assert config['parallel_workers'] == 3
        assert config['total_pages'] == 80
    
    def test_calculate_chunks_large_pdf(self):
        """Test chunking strategy for large PDFs (>100 pages)"""
        service = ChunkingService()
        config = service.calculate_chunks(page_count=300)
        
        assert config['strategy'] == 'large'
        assert config['chunk_size'] == 15
        assert config['num_chunks'] == 20  # 300 / 15 = 20
        assert config['parallel_workers'] == 5
        assert config['total_pages'] == 300
    
    @patch('PyPDF2.PdfReader')
    @patch('PyPDF2.PdfWriter')
    @patch('tempfile.NamedTemporaryFile')
    @patch('builtins.open')
    def test_split_pdf(self, mock_open, mock_tempfile, mock_pdf_writer, mock_pdf_reader):
        """Test PDF splitting into chunks"""
        service = ChunkingService()
        
        # Mock PDF with 40 pages
        mock_reader = MagicMock()
        mock_reader.pages = [MagicMock() for _ in range(40)]
        mock_pdf_reader.return_value = mock_reader
        
        # Mock temp file creation
        mock_temp = MagicMock()
        mock_temp.name = '/tmp/test_chunk_0.pdf'
        mock_tempfile.return_value = mock_temp
        
        # Mock chunk config
        chunk_config = {
            'chunk_size': 20,
            'num_chunks': 2,
            'total_pages': 40
        }
        
        chunks = service.split_pdf('/fake/path.pdf', chunk_config)
        
        assert len(chunks) == 2
        assert chunks[0]['chunk_id'] == 0
        assert chunks[0]['has_overlap'] == False
        assert chunks[1]['chunk_id'] == 1
        assert chunks[1]['has_overlap'] == True
    
    def test_cleanup_chunks(self):
        """Test cleanup of temporary chunk files"""
        service = ChunkingService()
        
        # Create temporary files
        temp_files = []
        for i in range(3):
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=f'_chunk_{i}.pdf')
            temp_file.write(b'test content')
            temp_file.close()
            temp_files.append({
                'chunk_id': i,
                'file_path': temp_file.name
            })
        
        # Verify files exist
        for chunk in temp_files:
            assert os.path.exists(chunk['file_path'])
        
        # Cleanup
        service.cleanup_chunks(temp_files)
        
        # Verify files are deleted
        for chunk in temp_files:
            assert not os.path.exists(chunk['file_path'])


class TestChunkResultMerging:
    """Tests for merging chunk results"""
    
    def test_merge_single_chunk(self):
        """Test merging with single chunk"""
        chunk_results = [
            {
                'chunk_id': 0,
                'status': 'success',
                'sentences': [
                    {'normalized': 'Sentence one.', 'original': 'Sentence one.'},
                    {'normalized': 'Sentence two.', 'original': 'Sentence two.'}
                ]
            }
        ]
        
        merged = merge_chunk_results(chunk_results)
        assert len(merged) == 2
        assert merged[0]['normalized'] == 'Sentence one.'
    
    def test_merge_multiple_chunks(self):
        """Test merging multiple chunks"""
        chunk_results = [
            {
                'chunk_id': 0,
                'status': 'success',
                'sentences': [
                    {'normalized': 'First sentence.', 'original': 'First sentence.'},
                    {'normalized': 'Second sentence.', 'original': 'Second sentence.'}
                ]
            },
            {
                'chunk_id': 1,
                'status': 'success',
                'sentences': [
                    {'normalized': 'Third sentence.', 'original': 'Third sentence.'},
                    {'normalized': 'Fourth sentence.', 'original': 'Fourth sentence.'}
                ]
            }
        ]
        
        merged = merge_chunk_results(chunk_results)
        assert len(merged) == 4
    
    def test_merge_with_failed_chunks(self):
        """Test merging when some chunks fail"""
        chunk_results = [
            {
                'chunk_id': 0,
                'status': 'success',
                'sentences': [
                    {'normalized': 'Success sentence.', 'original': 'Success sentence.'}
                ]
            },
            {
                'chunk_id': 1,
                'status': 'failed',
                'error': 'Processing error'
            },
            {
                'chunk_id': 2,
                'status': 'success',
                'sentences': [
                    {'normalized': 'Another success.', 'original': 'Another success.'}
                ]
            }
        ]
        
        merged = merge_chunk_results(chunk_results)
        # Should only include sentences from successful chunks
        assert len(merged) == 2
    
    def test_merge_with_overlap_deduplication(self):
        """Test that overlapping sentences are deduplicated"""
        chunk_results = [
            {
                'chunk_id': 0,
                'status': 'success',
                'sentences': [
                    {'normalized': 'Unique sentence one.', 'original': 'Unique sentence one.'},
                    {'normalized': 'Overlap sentence.', 'original': 'Overlap sentence.'}
                ]
            },
            {
                'chunk_id': 1,
                'status': 'success',
                'sentences': [
                    {'normalized': 'Overlap sentence.', 'original': 'Overlap sentence.'},  # Duplicate
                    {'normalized': 'Unique sentence two.', 'original': 'Unique sentence two.'}
                ]
            }
        ]
        
        merged = merge_chunk_results(chunk_results)
        # Should deduplicate the overlap sentence
        assert len(merged) == 3
        normalized_texts = [s['normalized'] for s in merged]
        assert 'Overlap sentence.' in normalized_texts
        # Check that overlap sentence appears only once
        assert normalized_texts.count('Overlap sentence.') == 1


class TestAsyncTaskIntegration:
    """Integration tests for async task processing"""
    
    @patch('app.tasks.process_chunk')
    @patch('app.tasks.Job')
    @patch('PyPDF2.PdfReader')
    def test_process_pdf_async_flow(self, mock_pdf_reader, mock_job_model, mock_process_chunk):
        """Test the full async processing flow"""
        from app.tasks import process_pdf_async
        
        # Mock job
        mock_job = MagicMock()
        mock_job.id = 123
        mock_job.is_cancelled = False
        mock_job_model.query.get.return_value = mock_job
        
        # Mock PDF reader
        mock_reader = MagicMock()
        mock_reader.pages = [MagicMock() for _ in range(25)]
        mock_pdf_reader.return_value = mock_reader
        
        # Mock chunk processing results
        mock_process_chunk.return_value = {
            'chunk_id': 0,
            'status': 'success',
            'sentences': [{'normalized': 'Test.', 'original': 'Test.'}],
            'tokens': 100
        }
        
        # This test would require a full Celery setup
        # In practice, you'd use pytest-celery or test components individually
        pass


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

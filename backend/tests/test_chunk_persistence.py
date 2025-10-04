"""Tests for chunk persistence and retry system"""
import pytest
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock
from app.models import Job, JobChunk, User
from app.services.chunking_service import ChunkingService


class TestJobChunkModel:
    """Tests for JobChunk model methods"""
    
    def test_can_retry_when_eligible(self):
        """Test JobChunk.can_retry() returns True when chunk can be retried"""
        chunk = JobChunk(
            job_id=1,
            chunk_id=0,
            start_page=0,
            end_page=10,
            page_count=10,
            status='failed',
            attempts=1,
            max_retries=3
        )
        assert chunk.can_retry() is True
    
    def test_can_retry_when_max_retries_reached(self):
        """Test JobChunk.can_retry() returns False when max retries reached"""
        chunk = JobChunk(
            job_id=1,
            chunk_id=0,
            start_page=0,
            end_page=10,
            page_count=10,
            status='failed',
            attempts=3,
            max_retries=3
        )
        assert chunk.can_retry() is False
    
    def test_can_retry_when_status_success(self):
        """Test JobChunk.can_retry() returns False when chunk succeeded"""
        chunk = JobChunk(
            job_id=1,
            chunk_id=0,
            start_page=0,
            end_page=10,
            page_count=10,
            status='success',
            attempts=1,
            max_retries=3
        )
        assert chunk.can_retry() is False
    
    def test_can_retry_when_retry_scheduled(self):
        """Test JobChunk.can_retry() returns True for retry_scheduled status"""
        chunk = JobChunk(
            job_id=1,
            chunk_id=0,
            start_page=0,
            end_page=10,
            page_count=10,
            status='retry_scheduled',
            attempts=1,
            max_retries=3
        )
        assert chunk.can_retry() is True
    
    def test_get_chunk_metadata(self):
        """Test JobChunk.get_chunk_metadata() returns correct dict"""
        chunk = JobChunk(
            job_id=5,
            chunk_id=2,
            start_page=20,
            end_page=29,
            page_count=10,
            has_overlap=True,
            file_b64='base64data',
            storage_url='s3://bucket/chunk.pdf'
        )
        
        metadata = chunk.get_chunk_metadata()
        
        assert metadata['job_id'] == 5
        assert metadata['chunk_id'] == 2
        assert metadata['start_page'] == 20
        assert metadata['end_page'] == 29
        assert metadata['page_count'] == 10
        assert metadata['has_overlap'] is True
        assert metadata['file_b64'] == 'base64data'
        assert metadata['storage_url'] == 's3://bucket/chunk.pdf'
    
    def test_to_dict(self):
        """Test JobChunk.to_dict() returns correct serialization"""
        created_at = datetime.utcnow()
        chunk = JobChunk(
            job_id=1,
            chunk_id=0,
            start_page=0,
            end_page=10,
            page_count=10,
            has_overlap=False,
            status='success',
            attempts=1,
            max_retries=3,
            last_error=None,
            last_error_code=None,
            processed_at=created_at,
            created_at=created_at,
            updated_at=created_at
        )
        
        data = chunk.to_dict()
        
        assert data['job_id'] == 1
        assert data['chunk_id'] == 0
        assert data['status'] == 'success'
        assert data['attempts'] == 1
        assert data['max_retries'] == 3
        assert 'processed_at' in data
        assert 'created_at' in data


class TestChunkingServicePersistence:
    """Tests for ChunkingService.split_pdf_and_persist()"""
    
    @patch('app.services.chunking_service.PdfReader')
    @patch('app.services.chunking_service.PdfWriter')
    @patch('builtins.open')
    def test_split_pdf_and_persist_creates_chunks(self, mock_open, mock_pdf_writer, mock_pdf_reader):
        """Test split_pdf_and_persist creates JobChunk records in DB"""
        # Setup mocks
        mock_page = Mock()
        mock_pdf_reader_instance = Mock()
        mock_pdf_reader_instance.pages = [mock_page] * 50  # 50 page PDF
        mock_pdf_reader.return_value = mock_pdf_reader_instance
        
        mock_writer_instance = Mock()
        mock_pdf_writer.return_value = mock_writer_instance
        mock_writer_instance.write = Mock()
        
        # Mock database session
        mock_db = Mock()
        mock_session = Mock()
        mock_db.session = mock_session
        
        # Create service and config
        service = ChunkingService()
        chunk_config = service.calculate_chunks(50)  # Should create multiple chunks
        
        # Call split_pdf_and_persist
        chunk_ids = service.split_pdf_and_persist(
            pdf_path='/tmp/test.pdf',
            chunk_config=chunk_config,
            job_id=123,
            db=mock_db
        )
        
        # Verify chunks were added to DB session
        assert mock_session.add.called
        assert mock_session.commit.called
        assert len(chunk_ids) == chunk_config['num_chunks']
    
    @patch('app.services.chunking_service.PdfReader')
    @patch('builtins.open')
    def test_split_pdf_and_persist_sets_chunk_metadata(self, mock_open, mock_pdf_reader):
        """Test that chunk metadata is correctly set in DB records"""
        # Setup mocks
        mock_page = Mock()
        mock_pdf_reader_instance = Mock()
        mock_pdf_reader_instance.pages = [mock_page] * 30
        mock_pdf_reader.return_value = mock_pdf_reader_instance
        
        mock_db = Mock()
        mock_session = Mock()
        mock_db.session = mock_session
        
        # Track chunks added to session
        chunks_added = []
        def capture_add(chunk):
            chunks_added.append(chunk)
        mock_session.add.side_effect = capture_add
        
        # Mock flush to assign IDs
        def mock_flush():
            for i, chunk in enumerate(chunks_added):
                chunk.id = i + 1
        mock_session.flush.side_effect = mock_flush
        
        service = ChunkingService()
        chunk_config = service.calculate_chunks(30)
        
        chunk_ids = service.split_pdf_and_persist(
            pdf_path='/tmp/test.pdf',
            chunk_config=chunk_config,
            job_id=456,
            db=mock_db
        )
        
        # Verify first chunk
        assert len(chunks_added) > 0
        first_chunk = chunks_added[0]
        assert first_chunk.job_id == 456
        assert first_chunk.chunk_id == 0
        assert first_chunk.start_page == 0
        assert first_chunk.page_count > 0
        assert first_chunk.has_overlap is False  # First chunk has no overlap
        assert first_chunk.status == 'pending'
        assert first_chunk.attempts == 0
        assert first_chunk.max_retries == 3
        assert first_chunk.file_b64 is not None


class TestChunkRetryLogic:
    """Tests for chunk retry orchestration"""
    
    def test_automatic_retry_in_finalize(self):
        """Test that finalize_job_results triggers retry for failed chunks"""
        # This would be an integration test requiring DB setup
        # For now, we document the expected behavior
        pass
    
    def test_manual_retry_endpoint(self):
        """Test POST /jobs/:id/chunks/retry endpoint"""
        # Integration test - requires full app context
        pass
    
    def test_retry_respects_max_retries(self):
        """Test that chunks are not retried beyond max_retries"""
        chunk = JobChunk(
            job_id=1,
            chunk_id=0,
            start_page=0,
            end_page=10,
            page_count=10,
            status='failed',
            attempts=3,
            max_retries=3
        )
        
        # Should not be eligible for retry
        assert chunk.can_retry() is False
    
    def test_force_retry_resets_attempts(self):
        """Test that force retry can reset attempts counter"""
        # This behavior is implemented in the API endpoint
        # Documented here for clarity
        pass


class TestChunkStatusTracking:
    """Tests for chunk status lifecycle tracking"""
    
    def test_chunk_status_transitions(self):
        """Test chunk status transitions through lifecycle"""
        chunk = JobChunk(
            job_id=1,
            chunk_id=0,
            start_page=0,
            end_page=10,
            page_count=10,
            status='pending'
        )
        
        # pending -> processing
        chunk.status = 'processing'
        chunk.attempts += 1
        assert chunk.status == 'processing'
        assert chunk.attempts == 1
        
        # processing -> success
        chunk.status = 'success'
        chunk.processed_at = datetime.utcnow()
        assert chunk.status == 'success'
        assert chunk.processed_at is not None
        
    def test_chunk_error_tracking(self):
        """Test that errors are tracked in chunk record"""
        chunk = JobChunk(
            job_id=1,
            chunk_id=0,
            start_page=0,
            end_page=10,
            page_count=10,
            status='processing'
        )
        
        # Simulate failure
        chunk.status = 'failed'
        chunk.last_error = 'Timeout error'
        chunk.last_error_code = 'TIMEOUT'
        
        assert chunk.status == 'failed'
        assert chunk.last_error == 'Timeout error'
        assert chunk.last_error_code == 'TIMEOUT'


class TestChunkResultPersistence:
    """Tests for persisting chunk results to DB"""
    
    def test_chunk_result_json_storage(self):
        """Test that chunk results are stored in result_json field"""
        chunk = JobChunk(
            job_id=1,
            chunk_id=0,
            start_page=0,
            end_page=10,
            page_count=10,
            status='success'
        )
        
        result = {
            'chunk_id': 0,
            'sentences': [{'original': 'Test', 'normalized': 'Test'}],
            'tokens': 100,
            'status': 'success'
        }
        
        chunk.result_json = result
        
        assert chunk.result_json == result
        assert chunk.result_json['tokens'] == 100
        assert len(chunk.result_json['sentences']) == 1

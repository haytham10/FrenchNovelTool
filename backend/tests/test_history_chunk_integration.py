"""Tests for History-Chunk integration and dynamic sentence retrieval"""
import os
import sys
import pytest
from unittest.mock import MagicMock, patch

# Ensure backend package is importable during tests (same pattern used in other tests)
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.services.history_service import HistoryService


class TestHistoryChunkIntegration:
    """Test History service integration with JobChunk for dynamic data retrieval"""

    @pytest.fixture
    def mock_db(self):
        """Mock database session"""
        with patch('app.services.history_service.db') as mock:
            yield mock

    @pytest.fixture
    def history_service(self, mock_db):
        """Create HistoryService instance"""
        return HistoryService()

    @pytest.fixture
    def mock_history_entry(self):
        """Create mock History entry"""
        # Use a plain MagicMock instead of spec=History to avoid triggering
        # Flask-SQLAlchemy descriptors which require an application context.
        entry = MagicMock()
        entry.id = 1
        entry.user_id = 100
        entry.job_id = 50
        entry.original_filename = "test.pdf"
        entry.processed_sentences_count = 3
        entry.chunk_ids = [1, 2, 3]
        entry.sentences = [
            {'normalized': 'Old sentence 1', 'original': 'Old sentence 1'},
            {'normalized': 'Old sentence 2', 'original': 'Old sentence 2'},
            {'normalized': 'Old sentence 3', 'original': 'Old sentence 3'}
        ]
        entry.to_dict_with_sentences.return_value = {
            'id': 1,
            'sentences': entry.sentences,
            'chunk_ids': entry.chunk_ids,
            'original_filename': entry.original_filename
        }
        return entry

    @pytest.fixture
    def mock_chunks_success(self):
        """Create mock successful JobChunk records"""
        chunks = []
        for i in range(3):
            # Avoid spec=JobChunk for the same reason as above
            chunk = MagicMock()
            chunk.id = i + 1
            chunk.chunk_id = i
            chunk.status = 'success'
            chunk.result_json = {
                'sentences': [
                    {
                        'normalized': f'New sentence {i+1}',
                        'original': f'Original sentence {i+1}'
                    }
                ]
            }
            chunk.to_dict.return_value = {
                'id': chunk.id,
                'chunk_id': chunk.chunk_id,
                'status': chunk.status
            }
            chunks.append(chunk)
        return chunks

    @pytest.fixture
    def mock_chunks_mixed(self):
        """Create mock JobChunk records with mixed statuses"""
        chunks = []

        # Chunk 0: success
        chunk0 = MagicMock()
        chunk0.id = 1
        chunk0.chunk_id = 0
        chunk0.status = 'success'
        chunk0.result_json = {
            'sentences': [{'normalized': 'Chunk 0 sentence', 'original': 'Chunk 0 sentence'}]
        }
        chunk0.to_dict.return_value = {'id': 1, 'chunk_id': 0, 'status': 'success'}
        chunks.append(chunk0)

        # Chunk 1: failed (no result)
        chunk1 = MagicMock()
        chunk1.id = 2
        chunk1.chunk_id = 1
        chunk1.status = 'failed'
        chunk1.result_json = None
        chunk1.to_dict.return_value = {'id': 2, 'chunk_id': 1, 'status': 'failed'}
        chunks.append(chunk1)

        # Chunk 2: success
        chunk2 = MagicMock()
        chunk2.id = 3
        chunk2.chunk_id = 2
        chunk2.status = 'success'
        chunk2.result_json = {
            'sentences': [{'normalized': 'Chunk 2 sentence', 'original': 'Chunk 2 sentence'}]
        }
        chunk2.to_dict.return_value = {'id': 3, 'chunk_id': 2, 'status': 'success'}
        chunks.append(chunk2)

        return chunks

    def test_rebuild_sentences_from_chunks_all_success(self, history_service, mock_history_entry, mock_chunks_success):
        """Test rebuilding sentences from all successful chunks"""
        with patch.object(history_service, 'get_entry_by_id', return_value=mock_history_entry):
            with patch('app.services.history_service.JobChunk') as mock_chunk_model:
                mock_query = MagicMock()
                mock_query.filter.return_value.order_by.return_value.all.return_value = mock_chunks_success
                mock_chunk_model.query = mock_query

                result = history_service.rebuild_sentences_from_chunks(1, 100)

                assert result is not None
                assert len(result) == 3
                assert result[0]['normalized'] == 'New sentence 1'
                assert result[1]['normalized'] == 'New sentence 2'
                assert result[2]['normalized'] == 'New sentence 3'

    def test_rebuild_sentences_from_chunks_mixed_status(self, history_service, mock_history_entry, mock_chunks_mixed):
        """Test rebuilding sentences from chunks with mixed success/failure status"""
        with patch.object(history_service, 'get_entry_by_id', return_value=mock_history_entry):
            with patch('app.services.history_service.JobChunk') as mock_chunk_model:
                mock_query = MagicMock()
                mock_query.filter.return_value.order_by.return_value.all.return_value = mock_chunks_mixed
                mock_chunk_model.query = mock_query

                result = history_service.rebuild_sentences_from_chunks(1, 100)

                # Should only include successful chunks (0 and 2)
                assert result is not None
                assert len(result) == 2
                assert result[0]['normalized'] == 'Chunk 0 sentence'
                assert result[1]['normalized'] == 'Chunk 2 sentence'

    def test_rebuild_sentences_from_chunks_no_chunks(self, history_service, mock_history_entry):
        """Test rebuilding when entry has no chunks"""
        mock_history_entry.chunk_ids = None

        with patch.object(history_service, 'get_entry_by_id', return_value=mock_history_entry):
            result = history_service.rebuild_sentences_from_chunks(1, 100)
            assert result is None

    def test_get_entry_with_details_uses_live_chunks(self, history_service, mock_history_entry, mock_chunks_success):
        """Test that get_entry_with_details uses live chunk data when requested"""
        with patch.object(history_service, 'get_entry_by_id', return_value=mock_history_entry):
            with patch('app.services.history_service.JobChunk') as mock_chunk_model:
                mock_query = MagicMock()
                mock_query.filter.return_value.order_by.return_value.all.return_value = mock_chunks_success
                mock_chunk_model.query = mock_query

                result = history_service.get_entry_with_details(1, 100, use_live_chunks=True)

                assert result is not None
                assert result['sentences_source'] == 'live_chunks'
                # Should have new sentences from chunks, not old snapshot
                assert len(result['sentences']) == 3
                assert result['sentences'][0]['normalized'] == 'New sentence 1'

    def test_get_entry_with_details_uses_snapshot(self, history_service, mock_history_entry, mock_chunks_success):
        """Test that get_entry_with_details uses snapshot when requested"""
        with patch.object(history_service, 'get_entry_by_id', return_value=mock_history_entry):
            with patch('app.services.history_service.JobChunk') as mock_chunk_model:
                mock_query = MagicMock()
                mock_query.filter.return_value.order_by.return_value.all.return_value = mock_chunks_success
                mock_chunk_model.query = mock_query

                result = history_service.get_entry_with_details(1, 100, use_live_chunks=False)

                assert result is not None
                assert result['sentences_source'] == 'snapshot'
                # Should have old sentences from snapshot
                assert result['sentences'][0]['normalized'] == 'Old sentence 1'

    def test_refresh_from_chunks(self, history_service, mock_history_entry, mock_chunks_success, mock_db):
        """Test refreshing History snapshot from current chunk data"""
        with patch.object(history_service, 'get_entry_by_id', return_value=mock_history_entry):
            with patch('app.services.history_service.JobChunk') as mock_chunk_model:
                mock_query = MagicMock()
                mock_query.filter.return_value.order_by.return_value.all.return_value = mock_chunks_success
                mock_chunk_model.query = mock_query

                result = history_service.refresh_from_chunks(1, 100)

                assert result is not None
                # Entry should be updated with new sentences
                assert mock_history_entry.processed_sentences_count == 3
                assert len(mock_history_entry.sentences) == 3
                assert mock_history_entry.sentences[0]['normalized'] == 'New sentence 1'
                # Should commit changes
                mock_db.session.commit.assert_called_once()

    def test_refresh_from_chunks_no_entry(self, history_service):
        """Test refresh when entry doesn't exist"""
        with patch.object(history_service, 'get_entry_by_id', return_value=None):
            result = history_service.refresh_from_chunks(1, 100)
            assert result is None

    def test_rebuild_sentences_handles_string_sentences(self, history_service, mock_history_entry):
        """Test that rebuild_sentences_from_chunks handles string sentences (not just dicts)"""
        chunk = MagicMock()
        chunk.id = 1
        chunk.chunk_id = 0
        chunk.status = 'success'
        chunk.result_json = {
            'sentences': ['String sentence 1', 'String sentence 2']  # Strings, not dicts
        }

        with patch.object(history_service, 'get_entry_by_id', return_value=mock_history_entry):
            with patch('app.services.history_service.JobChunk') as mock_chunk_model:
                mock_query = MagicMock()
                mock_query.filter.return_value.order_by.return_value.all.return_value = [chunk]
                mock_chunk_model.query = mock_query

                result = history_service.rebuild_sentences_from_chunks(1, 100)

                assert result is not None
                assert len(result) == 2
                # Should convert strings to dict format
                assert result[0]['normalized'] == 'String sentence 1'
                assert result[0]['original'] == 'String sentence 1'
 

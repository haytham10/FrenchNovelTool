"""Tests for WebSocket real-time job progress updates"""
import pytest
import os
import sys
from unittest.mock import MagicMock, patch
from flask import Flask
from flask_socketio import SocketIOTestClient

# Add the backend directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, socketio
from app.models import Job, User
from config import Config


@pytest.fixture
def app():
    """Create test Flask app with SocketIO"""
    app = create_app(Config)
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    return app


@pytest.fixture
def socketio_client(app):
    """Create SocketIO test client"""
    return socketio.test_client(app)


@pytest.fixture
def mock_token():
    """Mock JWT token for testing"""
    return "mock_jwt_token_for_testing"


@pytest.fixture
def mock_job():
    """Create a mock job for testing"""
    job = MagicMock(spec=Job)
    job.id = 1
    job.user_id = 123
    job.status = 'processing'
    job.progress_percent = 50
    job.current_step = 'Processing '
    job.to_dict.return_value = {
        'id': 1,
        'user_id': 123,
        'status': 'processing',
        'progress_percent': 50,
        'current_step': 'Processing '
    }
    return job


def test_socketio_initialized(app):
    """Test that SocketIO is properly initialized"""
    assert socketio is not None
    assert hasattr(socketio, 'emit')
    assert hasattr(socketio, 'on')


def test_emit_job_progress_helper():
    """Test the emit_job_progress helper function"""
    from app.socket_events import emit_job_progress
    
    # Should not raise an exception even without database
    # (will log warning but continue gracefully)
    with patch('app.socket_events.Job') as mock_job_model:
        mock_job_model.query.get.return_value = None
        emit_job_progress(999)  # Non-existent job


def test_websocket_connect_requires_token(app):
    """Test that WebSocket connection requires JWT authentication"""
    from app.socket_events import handle_connect

    # Patch decode_token and disconnect locally so the test doesn't need a request context
    with patch('app.socket_events.decode_token') as mock_decode, patch('app.socket_events.disconnect') as mock_disconnect:
        # Test with no token provided in auth dict
        result = handle_connect({})
        assert result is False
        mock_disconnect.assert_called_once()

    # Now test with a valid token
    with patch('app.socket_events.decode_token') as mock_decode, patch('app.socket_events.disconnect') as mock_disconnect:
        mock_decode.return_value = {'sub': '123'}
        result = handle_connect({'token': 'valid_token'})
        assert result is True


def test_emit_progress_in_tasks():
    """Test that tasks.py has emit_progress calls"""
    from app import tasks
    
    # Verify the helper function exists
    assert hasattr(tasks, 'emit_progress')
    
    # Verify it's callable
    assert callable(tasks.emit_progress)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

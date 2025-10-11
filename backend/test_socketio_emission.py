#!/usr/bin/env python3
"""
Test Socket.IO emission from a Celery worker context.
This script simulates the emission that happens in process_chunk tasks.

Usage:
    python test_socketio_emission.py [job_id]
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from app.models import Job
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_emission(job_id: int):
    """Test Socket.IO emission for a specific job"""
    app = create_app()
    
    with app.app_context():
        # Import after app context is created
        from app.socket_events import emit_job_progress
        from app import socketio
        
        logger.info(f"=" * 60)
        logger.info(f"Testing Socket.IO emission for job {job_id}")
        logger.info(f"=" * 60)
        
        # Check job exists
        job = Job.query.get(job_id)
        if not job:
            logger.error(f"Job {job_id} not found in database")
            return False
        
        logger.info(f"Job found: ID={job.id}, status={job.status}, progress={job.progress_percent}%")
        
        # Check Socket.IO configuration
        logger.info(f"\nSocket.IO Configuration:")
        logger.info(f"  Message queue: {socketio.server.manager_class if hasattr(socketio.server, 'manager_class') else 'N/A'}")
        logger.info(f"  Redis URL: {app.config.get('CELERY_BROKER_URL')}")
        logger.info(f"  Async mode: {socketio.async_mode}")
        
        # Try to emit
        logger.info(f"\nAttempting to emit job_progress...")
        try:
            emit_job_progress(job_id)
            logger.info(f"✅ Emission completed successfully")
            return True
        except Exception as e:
            logger.error(f"❌ Emission failed: {e}", exc_info=True)
            return False


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python test_socketio_emission.py <job_id>")
        print("\nExample: python test_socketio_emission.py 73")
        sys.exit(1)
    
    try:
        job_id = int(sys.argv[1])
    except ValueError:
        print(f"Error: '{sys.argv[1]}' is not a valid job ID (must be an integer)")
        sys.exit(1)
    
    success = test_emission(job_id)
    sys.exit(0 if success else 1)

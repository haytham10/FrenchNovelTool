#!/usr/bin/env python
"""
Celery worker entry point for async PDF processing
Run with: celery -A worker worker --loglevel=info
"""

from app.celery_app import celery
from app import create_app

# Create Flask app to initialize extensions
app = create_app()

if __name__ == '__main__':
    celery.start()

"""Celery application entrypoint for the worker process.

This module builds the Flask app using the application factory, which in turn
initializes the module-level `celery` instance in `app.__init__`. We then
re-export that Celery instance for the worker process to use.

Usage:
    celery -A celery_worker.celery worker --loglevel=info
"""
from app import create_app


# Build the Flask app; this sets `app.celery` via the factory.
_flask_app = create_app()

# Import the configured Celery instance from the app package.
from app import celery  # noqa: E402  (import after create_app)

# Import tasks so Celery registers them with the configured app instance.
import app.tasks  # noqa: F401,E402


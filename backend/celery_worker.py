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

# Preload spaCy model in the parent process to take advantage of copy-on-write
# memory sharing across forked Celery workers. This avoids N separate large model
# loads and mitigates OOM/SIGKILL under load.
try:  # Import lazily; if spaCy isn't used in this deployment, this is a no-op
    from app.utils.linguistics import preload_spacy  # noqa: E402

    preload_spacy()  # Uses env vars SPACY_MODEL and SPACY_DISABLE defaults
except Exception:  # noqa: E722 - best-effort preload; don't block worker start
    pass

# Import the configured Celery instance from the app package.
from app import celery  # noqa: E402  (import after create_app)

# Import tasks so Celery registers them with the configured app instance.
import app.tasks  # noqa: F401,E402


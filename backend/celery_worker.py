"""Celery application entrypoint for the worker process.

This module builds the Flask app using the application factory, which in turn
initializes the module-level `celery` instance in `app.__init__`. We then
re-export that Celery instance for the worker process to use.

Usage:
    celery -A celery_worker.celery worker --loglevel=info
"""
from app import create_app
import os
import logging

# Build the Flask app; this sets `app.celery` via the factory.
_flask_app = create_app()

# Preload spaCy model in the parent process to take advantage of copy-on-write
# memory sharing across forked Celery workers. This can consume a significant
# amount of memory for large models (e.g., fr_core_news_md) and in constrained
# environments (like small Railway containers) may cause the worker to be OOM-killed.
# Make this behavior opt-in via the PRELOAD_SPACY env var (default: false).
try:
    preload_enabled = os.getenv('PRELOAD_SPACY', 'false').lower() in ('1', 'true', 'yes')
    if preload_enabled:
        from app.utils.linguistics import preload_spacy  # noqa: E402
        try:
            logging.getLogger(__name__).info('Preloading spaCy model in parent process')
            preload_spacy()  # Uses env vars SPACY_MODEL and SPACY_DISABLE defaults
            logging.getLogger(__name__).info('spaCy preload completed')
        except Exception as e:  # noqa: E722 - best-effort preload; don't block worker start
            logging.getLogger(__name__).warning('spaCy preload failed (continuing without preload): %s', e)
    else:
        logging.getLogger(__name__).info('PRELOAD_SPACY not enabled; skipping spaCy preload')
except Exception as e:
    # In the unlikely event the import machinery fails, log but continue startup
    logging.getLogger(__name__).warning('Error checking PRELOAD_SPACY env var: %s', e)

# Import the configured Celery instance from the app package.
from app import celery  # noqa: E402  (import after create_app)

# Import tasks so Celery registers them with the configured app instance.
try:
    import app.tasks  # noqa: F401,E402
except Exception as e:
    # Log the error and re-raise so the worker process fails visibly
    logging.getLogger(__name__).exception('Failed to import Celery tasks during startup: %s', e)
    raise


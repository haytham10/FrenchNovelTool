"""Celery application factory and configuration"""
from celery import Celery
from flask import Flask


def make_celery(app: Flask) -> Celery:
    """
    Factory function to create Celery instance with Flask context.

    Args:
        app: Flask application instance

    Returns:
        Configured Celery instance
    """
    celery = Celery(
        app.import_name,
        backend=app.config["CELERY_RESULT_BACKEND"],
        broker=app.config["CELERY_BROKER_URL"],
        include=["app.tasks"],  # Ensure task modules are registered
    )

    # Update Celery config from Flask config
    # Optimized for 8GB RAM / 8 vCPU Railway infrastructure
    celery.conf.update(
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        timezone="UTC",
        enable_utc=True,
        task_track_started=True,
        task_send_sent_event=True,
        worker_send_task_events=True,
    result_expires=7200,  # 2 hours - longer retention for complex jobs
    task_time_limit=1200,  # 20 minutes max per task
    task_soft_time_limit=1140,  # Soft limit at 19 minutes
        # Prefetch fewer tasks to reduce memory bursts on large PDFs
        worker_prefetch_multiplier=1,
        # Recycle children more frequently to mitigate memory growth
        worker_max_tasks_per_child=50,
        task_acks_late=True,  # Acknowledge after task completion
        task_reject_on_worker_lost=True,  # Re-queue if worker crashes
        # Memory cap: 900MB per worker (8GB / 8 workers with headroom)
        worker_max_memory_per_child=int(app.config.get("WORKER_MAX_MEMORY_MB", 900)) * 1024,
        # Retain existing startup retry behavior for broker connections.
        # Celery 6.0+ changes how connection retries on startup are handled;
        # setting this to True preserves the previous behavior and silences
        # the deprecation warning about broker_connection_retry.
        broker_connection_retry_on_startup=True,
    )

    # Enable eager execution in tests to avoid broker/backend dependencies
    try:
        import os
        if app.config.get("TESTING", False) or os.getenv("CELERY_TASK_ALWAYS_EAGER", "false").lower() == "true":
            celery.conf.task_always_eager = True
            celery.conf.task_eager_propagates = True
            # Use in-memory transports to prevent any network calls during tests
            celery.conf.broker_url = "memory://"
            celery.conf.result_backend = "cache+memory://"
    except Exception:
        pass

    # Make Celery tasks work with Flask app context
    class ContextTask(celery.Task):
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)

    celery.Task = ContextTask
    return celery

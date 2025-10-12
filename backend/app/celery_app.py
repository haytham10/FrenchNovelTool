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
        backend=app.config['CELERY_RESULT_BACKEND'],
        broker=app.config['CELERY_BROKER_URL'],
        include=['app.tasks'],  # Ensure task modules are registered
    )
    
    # Update Celery config from Flask config
    # Optimized for 8GB RAM / 8 vCPU Railway infrastructure
    celery.conf.update(
        task_serializer='json',
        accept_content=['json'],
        result_serializer='json',
        timezone='UTC',
        enable_utc=True,
        task_track_started=True,
        task_send_sent_event=True,
        worker_send_task_events=True,
        result_expires=7200,  # 2 hours - longer retention for complex jobs
        task_time_limit=3600,  # 60 minutes max per task - handle large PDFs
        task_soft_time_limit=3300,  # Soft limit at 55 minutes
        worker_prefetch_multiplier=2,  # Prefetch more tasks for better throughput
        worker_max_tasks_per_child=100,  # More tasks before recycling
        task_acks_late=True,  # Acknowledge after task completion
        task_reject_on_worker_lost=True,  # Re-queue if worker crashes
    # Memory cap: 900MB per worker (8GB / 8 workers with headroom)
    worker_max_memory_per_child=int(app.config.get('WORKER_MAX_MEMORY_MB', 900)) * 1024,
        # Retain existing startup retry behavior for broker connections.
        # Celery 6.0+ changes how connection retries on startup are handled;
        # setting this to True preserves the previous behavior and silences
        # the deprecation warning about broker_connection_retry.
        broker_connection_retry_on_startup=True,
    )
    
    # Make Celery tasks work with Flask app context
    class ContextTask(celery.Task):
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)
    
    celery.Task = ContextTask
    return celery

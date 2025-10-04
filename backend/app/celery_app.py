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
    )
    
    # Update Celery config from Flask config
    celery.conf.update(
        task_serializer='json',
        accept_content=['json'],
        result_serializer='json',
        timezone='UTC',
        enable_utc=True,
        task_track_started=True,
        task_send_sent_event=True,
        worker_send_task_events=True,
        result_expires=3600,  # 1 hour
        task_time_limit=1800,  # 30 minutes max per task
        task_soft_time_limit=1500,  # Soft limit at 25 minutes
        worker_prefetch_multiplier=1,  # Fair task distribution
        worker_max_tasks_per_child=50,  # Prevent memory leaks
        task_acks_late=True,  # Acknowledge after task completion
        task_reject_on_worker_lost=True,  # Re-queue if worker crashes
    )
    
    # Make Celery tasks work with Flask app context
    class ContextTask(celery.Task):
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)
    
    celery.Task = ContextTask
    return celery

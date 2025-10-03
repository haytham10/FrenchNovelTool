"""Celery application for background task processing"""
from celery import Celery
import os
from dotenv import load_dotenv

load_dotenv()

def make_celery():
    """Create and configure Celery instance"""
    redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
    
    celery = Celery(
        'frenchnoveltool',
        broker=redis_url,
        backend=redis_url,
        include=['app.tasks']
    )
    
    # Configuration
    celery.conf.update(
        task_serializer='json',
        accept_content=['json'],
        result_serializer='json',
        timezone='UTC',
        enable_utc=True,
        task_track_started=True,
        task_time_limit=3600,  # 1 hour hard limit
        task_soft_time_limit=3300,  # 55 minutes soft limit
        worker_prefetch_multiplier=1,  # Process one task at a time to avoid memory issues
        worker_max_tasks_per_child=50,  # Restart worker after 50 tasks to prevent memory leaks
        result_expires=3600,  # Results expire after 1 hour
        task_acks_late=True,  # Acknowledge task after completion for better reliability
        task_reject_on_worker_lost=True,
    )
    
    return celery

celery_app = make_celery()

"""Celery application configuration for async task processing"""
import os
from celery import Celery

def make_celery(app_name=__name__):
    """Create and configure Celery application"""
    redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379/0')

    # Allow development environments to run without Redis by falling back to
    # Celery's in-memory transport and executing tasks eagerly.
    use_in_memory = redis_url.startswith('memory://')
    broker_url = 'memory://' if use_in_memory else redis_url
    backend_url = 'cache+memory://' if use_in_memory else redis_url

    celery = Celery(
        app_name,
        broker=broker_url,
        backend=backend_url,
        include=['app.tasks']
    )
    
    celery.conf.update(
        task_serializer='json',
        accept_content=['json'],
        result_serializer='json',
        timezone='UTC',
        enable_utc=True,
        task_track_started=True,
        task_time_limit=3600,  # 1 hour hard limit
        task_soft_time_limit=3000,  # 50 minutes soft limit
        worker_prefetch_multiplier=1,
        worker_max_tasks_per_child=50,
    )

    if use_in_memory:
        celery.conf.update(
            task_always_eager=True,
            task_ignore_result=False,
        )
    
    return celery


celery = make_celery('frenchnovel')

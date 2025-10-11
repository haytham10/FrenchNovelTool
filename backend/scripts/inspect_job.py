"""Quick diagnostic script to inspect Job and JobChunk statuses.

Usage:
  python backend/scripts/inspect_job.py            # shows last 20 jobs
  python backend/scripts/inspect_job.py <job_id>  # shows details for a specific job

Run from repository root.
"""
import sys
from datetime import datetime

from app import create_app


def fmt(dt):
    return dt.isoformat() + 'Z' if dt else None


def main():
    app = create_app()
    with app.app_context():
        from app.models import Job, JobChunk
        from app.extensions import db

        if len(sys.argv) > 1:
            try:
                job_id = int(sys.argv[1])
            except Exception:
                print('Invalid job id')
                return
            job = Job.query.get(job_id)
            if not job:
                print(f'Job {job_id} not found')
                return
            print('Job:')
            print(f'  id: {job.id}')
            print(f'  user_id: {job.user_id}')
            print(f'  status: {job.status}')
            print(f'  progress_percent: {job.progress_percent}')
            print(f'  current_step: {job.current_step}')
            print(f'  total_chunks: {job.total_chunks} processed_chunks: {job.processed_chunks}')
            print(f'  started_at: {fmt(job.started_at)} completed_at: {fmt(job.completed_at)}')
            print(f'  celery_task_id: {job.celery_task_id}')
            print(f'  error_message: {job.error_message}')
            print('\nChunks:')
            chunks = JobChunk.query.filter_by(job_id=job.id).order_by(JobChunk.chunk_id).all()
            if not chunks:
                print('  (no DB-persisted chunks found)')
            for c in chunks:
                print(f"  chunk_id={c.chunk_id} id={c.id} status={c.status} attempts={c.attempts} last_error={c.last_error} updated_at={fmt(c.updated_at)}")
        else:
            # list recent jobs
            recent = Job.query.order_by(Job.created_at.desc()).limit(20).all()
            print('Recent jobs:')
            for j in recent:
                print(f"  id={j.id} status={j.status} progress={j.progress_percent} chunks={j.total_chunks} processed={j.processed_chunks} started_at={fmt(j.started_at)} celery_task_id={j.celery_task_id}")


if __name__ == '__main__':
    main()

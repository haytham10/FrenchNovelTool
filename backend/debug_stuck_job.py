#!/usr/bin/env python3
"""
Debug script to check job status and chunk processing for stuck jobs.

Usage:
    python debug_stuck_job.py <job_id>
    
This will:
1. Show current job status in database
2. Show all chunks and their status
3. Check if Celery task is still running
4. Show recent progress updates
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from app.models import Job, JobChunk
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def debug_job(job_id: int):
    """Debug a stuck job"""
    app = create_app()
    
    with app.app_context():
        logger.info(f"=" * 80)
        logger.info(f"Debugging Job {job_id}")
        logger.info(f"=" * 80)
        
        # Check job exists
        job = Job.query.get(job_id)
        if not job:
            logger.error(f"❌ Job {job_id} not found in database")
            return
        
        # Show job details
        logger.info(f"\n📋 JOB STATUS:")
        logger.info(f"  ID: {job.id}")
        logger.info(f"  Status: {job.status}")
        logger.info(f"  Progress: {job.progress_percent}%")
        logger.info(f"  Current Step: {job.current_step}")
        logger.info(f"  Created: {job.created_at}")
        logger.info(f"  Updated: {job.updated_at}")
        logger.info(f"  Total Chunks: {job.total_chunks}")
        logger.info(f"  Processed Chunks: {job.processed_chunks}")
        logger.info(f"  Celery Task ID: {job.celery_task_id}")
        logger.info(f"  Error Message: {job.error_message}")
        logger.info(f"  Is Cancelled: {job.is_cancelled}")
        
        # Check time since last update
        if job.updated_at:
            time_since_update = datetime.utcnow() - job.updated_at
            logger.info(f"  Time Since Update: {time_since_update}")
            
            if time_since_update.total_seconds() > 300:  # 5 minutes
                logger.warning(f"  ⚠️  Job hasn't updated in over 5 minutes!")
        
        # Check if chunks exist
        chunks = JobChunk.query.filter_by(job_id=job_id).order_by(JobChunk.chunk_id).all()
        
        if chunks:
            logger.info(f"\n📦 CHUNKS ({len(chunks)} total):")
            for chunk in chunks:
                logger.info(f"\n  Chunk {chunk.chunk_id}:")
                logger.info(f"    Status: {chunk.status}")
                logger.info(f"    Attempts: {chunk.attempts}/{chunk.max_retries}")
                logger.info(f"    Pages: {chunk.start_page}-{chunk.end_page}")
                logger.info(f"    Celery Task ID: {chunk.celery_task_id}")
                logger.info(f"    Created: {chunk.created_at}")
                logger.info(f"    Updated: {chunk.updated_at}")
                logger.info(f"    Processed: {chunk.processed_at}")
                logger.info(f"    Last Error: {chunk.last_error}")
                logger.info(f"    Last Error Code: {chunk.last_error_code}")
                
                if chunk.updated_at:
                    time_since_chunk_update = datetime.utcnow() - chunk.updated_at
                    logger.info(f"    Time Since Update: {time_since_chunk_update}")
                    
                    if time_since_chunk_update.total_seconds() > 300 and chunk.status == 'processing':
                        logger.warning(f"    ⚠️  Chunk stuck in processing for over 5 minutes!")
        else:
            logger.info(f"\n❌ No chunks found for job {job_id}")
        
        # Check Celery task status if available
        if job.celery_task_id:
            logger.info(f"\n🔍 CELERY TASK STATUS:")
            try:
                from app import celery
                from celery.result import AsyncResult
                
                task_result = AsyncResult(job.celery_task_id, app=celery)
                logger.info(f"  Task ID: {job.celery_task_id}")
                logger.info(f"  State: {task_result.state}")
                logger.info(f"  Ready: {task_result.ready()}")
                logger.info(f"  Successful: {task_result.successful() if task_result.ready() else 'N/A'}")
                
                if task_result.ready() and task_result.failed():
                    logger.error(f"  Error: {task_result.info}")
                    logger.error(f"  Traceback: {task_result.traceback}")
                elif task_result.state == 'PENDING':
                    logger.warning(f"  ⚠️  Task is PENDING - may not have been picked up by worker")
                
            except Exception as e:
                logger.error(f"  ❌ Failed to check Celery task: {e}")
        
        # Recommendations
        logger.info(f"\n💡 RECOMMENDATIONS:")
        
        if job.status == 'pending' and job.progress_percent == 0:
            logger.info("  • Job is pending - check if Celery worker is running")
            logger.info("  • Run: railway logs --service=<worker-service-id>")
        
        elif job.status == 'processing' and job.progress_percent == 15:
            logger.info("  • Job stuck at 15% (chunking complete, processing not started)")
            logger.info("  • Check Celery worker logs for errors")
            logger.info("  • Verify Redis connection from worker")
            logger.info("  • Check if process_chunk task was dispatched")
        
        elif job.status == 'processing' and chunks:
            stuck_chunks = [c for c in chunks if c.status == 'processing' and c.updated_at and 
                          (datetime.utcnow() - c.updated_at).total_seconds() > 300]
            if stuck_chunks:
                logger.info(f"  • {len(stuck_chunks)} chunk(s) stuck in processing")
                logger.info("  • Check worker logs for Gemini API errors or timeouts")
                logger.info("  • Verify Gemini API key is valid and has quota")
        
        logger.info(f"\n" + "=" * 80)


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python debug_stuck_job.py <job_id>")
        print("\nExample: python debug_stuck_job.py 74")
        sys.exit(1)
    
    try:
        job_id = int(sys.argv[1])
    except ValueError:
        print(f"Error: '{sys.argv[1]}' is not a valid job ID (must be an integer)")
        sys.exit(1)
    
    debug_job(job_id)

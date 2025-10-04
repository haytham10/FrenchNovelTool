-- Fix Production Database Schema for Async Processing
-- Run this SQL script on Railway PostgreSQL database
--
-- Usage:
--   railway connect postgres
--   Then paste these commands

-- Add async processing columns to jobs table
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS current_step VARCHAR(100);
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS total_chunks INTEGER;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS processed_chunks INTEGER DEFAULT 0;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS chunk_results JSONB;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS failed_chunks JSONB;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS processing_settings JSONB;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS celery_task_id VARCHAR(155);
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS progress_percent INTEGER DEFAULT 0;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS is_cancelled BOOLEAN DEFAULT FALSE;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS cancelled_at TIMESTAMP;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS cancelled_by INTEGER;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS processing_time_seconds INTEGER;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS retry_count INTEGER DEFAULT 0;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS max_retries INTEGER DEFAULT 3;

-- Add foreign key constraint for cancelled_by (if not exists)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'jobs_cancelled_by_fkey'
    ) THEN
        ALTER TABLE jobs ADD CONSTRAINT jobs_cancelled_by_fkey 
            FOREIGN KEY (cancelled_by) REFERENCES users(id);
    END IF;
END $$;

-- Create index on celery_task_id for faster lookups
CREATE INDEX IF NOT EXISTS idx_jobs_celery_task_id ON jobs(celery_task_id);

-- Verify columns exist
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_name = 'jobs'
ORDER BY ordinal_position;

-- Count existing jobs
SELECT status, COUNT(*) 
FROM jobs 
GROUP BY status;

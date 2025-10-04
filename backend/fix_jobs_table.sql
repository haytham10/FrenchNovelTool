-- Fix Production Database Schema for Async Processing
-- Run this SQL script on Supabase or Railway PostgreSQL database
--
-- This script is idempotent - safe to run multiple times
--
-- Usage (Supabase SQL Editor):
--   1. Open Supabase Dashboard → SQL Editor
--   2. Create New Query
--   3. Paste this entire script
--   4. Click "Run"
--
-- Usage (Railway CLI):
--   railway run --service backend psql $DATABASE_URL < fix_jobs_table.sql
--
-- Usage (railway connect postgres):
--   railway connect postgres
--   \i fix_jobs_table.sql

BEGIN;

-- Add async processing columns to jobs table (all idempotent with IF NOT EXISTS)
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
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS gemini_api_calls INTEGER DEFAULT 0;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS gemini_tokens_used INTEGER DEFAULT 0;

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

-- Create index on celery_task_id for faster job status lookups
CREATE INDEX IF NOT EXISTS ix_jobs_celery_task_id ON jobs(celery_task_id);

-- Create index on status + created_at for efficient job queries
CREATE INDEX IF NOT EXISTS idx_jobs_status_created ON jobs(status, created_at DESC);

-- Create index on user_id + status for user-specific job queries
CREATE INDEX IF NOT EXISTS idx_jobs_user_status ON jobs(user_id, status);

COMMIT;

-- Verification queries
-- These will show column info and existing data
\echo '\n📋 Verification: Checking jobs table columns...'
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_name = 'jobs'
  AND column_name IN (
    'current_step', 'total_chunks', 'processed_chunks', 'celery_task_id',
    'progress_percent', 'is_cancelled', 'retry_count', 'gemini_api_calls'
  )
ORDER BY column_name;

\echo '\n📊 Verification: Checking existing jobs...'
SELECT status, COUNT(*) as count
FROM jobs 
GROUP BY status
ORDER BY status;

\echo '\n📈 Verification: Checking indexes...'
SELECT indexname, indexdef
FROM pg_indexes
WHERE tablename = 'jobs'
  AND indexname LIKE '%celery%' OR indexname LIKE '%status%'
ORDER BY indexname;

\echo '\n✅ Script completed successfully!'
\echo 'If you see the async columns above, your database is ready for async processing.'


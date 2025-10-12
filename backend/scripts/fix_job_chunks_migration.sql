-- fix_job_chunks_migration.sql
-- Safe script to inspect and remove conflicting indexes created during a partial migration
-- Usage: psql "$DATABASE_URL" -f fix_job_chunks_migration.sql
-- IMPORTANT: Take a DB backup/snapshot before running in production.

BEGIN;

-- Show current alembic version
SELECT 'alembic_version' as source, version_num FROM alembic_version;

-- Show whether table exists
SELECT 'table_exists' as source, EXISTS(
  SELECT 1 FROM information_schema.tables WHERE table_name='job_chunks'
) as job_chunks_exists;

-- List existing indexes on job_chunks
SELECT indexname, indexdef FROM pg_indexes WHERE tablename='job_chunks';

-- Drop problematic indexes if they exist
-- These drops are safe (do not remove table data), they only remove index structures.
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_indexes WHERE tablename='job_chunks' AND indexname='ix_job_chunks_job_id') THEN
    RAISE NOTICE 'Dropping index ix_job_chunks_job_id';
    EXECUTE 'DROP INDEX IF EXISTS ix_job_chunks_job_id';
  ELSE
    RAISE NOTICE 'Index ix_job_chunks_job_id not present';
  END IF;

  IF EXISTS (SELECT 1 FROM pg_indexes WHERE tablename='job_chunks' AND indexname='ix_job_chunks_status') THEN
    RAISE NOTICE 'Dropping index ix_job_chunks_status';
    EXECUTE 'DROP INDEX IF EXISTS ix_job_chunks_status';
  ELSE
    RAISE NOTICE 'Index ix_job_chunks_status not present';
  END IF;

  IF EXISTS (SELECT 1 FROM pg_indexes WHERE tablename='job_chunks' AND indexname='idx_job_chunk_unique') THEN
    RAISE NOTICE 'Dropping index idx_job_chunk_unique';
    EXECUTE 'DROP INDEX IF EXISTS idx_job_chunk_unique';
  ELSE
    RAISE NOTICE 'Index idx_job_chunk_unique not present';
  END IF;
END$$;

-- Show indexes after cleanup
SELECT indexname, indexdef FROM pg_indexes WHERE tablename='job_chunks';

COMMIT;

-- After running this script, re-run your migration (e.g. in the backend container):
-- flask db upgrade

-- If the migration still fails and the table already has the expected schema, you can stamp the migration as applied:
-- UPDATE alembic_version SET version_num = 'ba1e2c3d4f56';
-- But only do that if you have verified the schema manually.

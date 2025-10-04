# Chunk Persistence and Retry System - Quick Start Guide

## What This Is

A production-grade chunk persistence and retry system for the French Novel Tool's async PDF processing pipeline. Ensures **zero data loss** and automatic/manual recovery from failures.

## Key Features

- ✅ **100% chunk persistence** - Every chunk saved to database
- ✅ **Automatic retry** - Failed chunks retried up to 3 rounds
- ✅ **Manual retry API** - Operator can retry specific chunks
- ✅ **Full audit trail** - Complete chunk lifecycle tracked
- ✅ **No data loss** - All chunk state and results durable

## Quick Start

### 1. Run the Migration

Development:
```bash
docker-compose -f docker-compose.dev.yml exec backend flask db upgrade
```

Production (Railway):
```bash
railway run flask db upgrade
```

### 2. Verify Migration

```bash
# Check current migration
docker-compose -f docker-compose.dev.yml exec backend flask db current

# Should show: c1d2e3f4g5h6 (head)
```

### 3. Test with a PDF

The system works automatically. When you upload a PDF:

1. Chunks are persisted to `job_chunks` table
2. Each chunk tracks its own status (pending → processing → success/failed)
3. Failed chunks are automatically retried (up to 3 rounds)
4. Results and errors are saved to database

### 4. Monitor Chunks

**View chunk details:**
```bash
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:5000/api/v1/jobs/123/chunks
```

**Manually retry failed chunks:**
```bash
curl -X POST \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  http://localhost:5000/api/v1/jobs/123/chunks/retry
```

## Architecture

### Data Flow
```
PDF Upload
  ↓
ChunkingService.split_pdf_and_persist()
  ↓
JobChunk records created in DB (status='pending')
  ↓
process_chunk tasks dispatched
  ↓
Each chunk: Load from DB → Process → Save result to DB
  ↓
finalize_job_results checks for failures
  ↓
If failures: Retry failed chunks automatically
  ↓
Complete job or retry until max_retries reached
```

### Chunk Status Lifecycle
```
pending → processing → success
                    ↓
                 failed → retry_scheduled → processing → ...
```

## Database Schema

### JobChunk Table

| Field | Type | Description |
|-------|------|-------------|
| id | SERIAL | Primary key |
| job_id | INTEGER | Foreign key to jobs table |
| chunk_id | INTEGER | 0-indexed chunk number |
| start_page | INTEGER | First page (inclusive) |
| end_page | INTEGER | Last page (inclusive) |
| page_count | INTEGER | Number of pages in chunk |
| has_overlap | BOOLEAN | True if chunk overlaps with previous |
| file_b64 | TEXT | Base64 encoded PDF chunk |
| storage_url | VARCHAR(512) | Future: S3/GCS URL |
| file_size_bytes | INTEGER | Size of chunk in bytes |
| status | VARCHAR(20) | Current status |
| celery_task_id | VARCHAR(155) | Current/last Celery task ID |
| attempts | INTEGER | Number of processing attempts |
| max_retries | INTEGER | Maximum retry attempts (default 3) |
| last_error | TEXT | Last error message |
| last_error_code | VARCHAR(50) | Last error code |
| result_json | JSON | Processing results (sentences, tokens) |
| processed_at | TIMESTAMP | When chunk completed successfully |
| created_at | TIMESTAMP | When chunk was created |
| updated_at | TIMESTAMP | Last update time |

**Indexes:**
- `idx_job_chunks_job_id` on (job_id)
- `idx_job_chunks_status` on (status)
- `idx_job_chunks_job_status` on (job_id, status)
- `unique_job_chunk` UNIQUE on (job_id, chunk_id)

## API Endpoints

### GET /api/v1/jobs/:id/chunks

Get detailed chunk status for a job.

**Response:**
```json
{
  "job_id": 123,
  "total_chunks": 5,
  "chunks": [
    {
      "chunk_id": 0,
      "status": "success",
      "attempts": 1,
      "last_error": null,
      "processed_at": "2025-01-15T10:30:00Z"
    }
  ],
  "summary": {
    "pending": 0,
    "processing": 1,
    "success": 3,
    "failed": 1,
    "retry_scheduled": 0
  }
}
```

### POST /api/v1/jobs/:id/chunks/retry

Manually retry failed chunks.

**Request:**
```json
{
  "chunk_ids": [2, 5],  // Optional: specific chunks
  "force": false        // Optional: bypass max_retries
}
```

**Response:**
```json
{
  "message": "Retrying 2 chunks",
  "retried_count": 2,
  "group_id": "abc-123",
  "chunk_ids": [2, 5]
}
```

## Configuration

Default settings (configured in model):
- `max_retries` per chunk: 3
- `max_retries` per job: 3 (retry rounds)

These can be customized per job by modifying the Job or JobChunk instances.

## Common Operations

### Check chunk success rate
```sql
SELECT 
  COUNT(CASE WHEN status = 'success' THEN 1 END)::float / COUNT(*) as success_rate
FROM job_chunks
WHERE created_at > NOW() - INTERVAL '24 hours';
```

### Find stuck chunks
```sql
SELECT * FROM job_chunks
WHERE status = 'processing'
  AND updated_at < NOW() - INTERVAL '1 hour';
```

### Reset stuck chunks
```sql
UPDATE job_chunks 
SET status = 'failed', 
    last_error = 'Processing timeout - worker may have crashed'
WHERE status = 'processing' 
  AND updated_at < NOW() - INTERVAL '1 hour';
```

### Get common error codes
```sql
SELECT last_error_code, COUNT(*) as count
FROM job_chunks
WHERE status = 'failed'
  AND created_at > NOW() - INTERVAL '24 hours'
GROUP BY last_error_code
ORDER BY count DESC;
```

## Troubleshooting

### Issue: Chunks stuck in "processing"
**Cause:** Worker crashed, timeout exceeded, or DB connection lost  
**Solution:** Run the "Reset stuck chunks" SQL above

### Issue: Manual retry not starting
**Check:**
1. Chunk status is 'failed' or 'retry_scheduled'
2. User has access to the job (JWT valid)
3. Celery workers are running
4. Redis connection is healthy

### Issue: All chunks failing with same error
**Check:**
1. Gemini API key is valid
2. API quota not exceeded
3. Network connectivity to Gemini API
4. PDF chunks have extractable text

## Error Codes

| Code | Description |
|------|-------------|
| TIMEOUT | Processing timeout exceeded |
| NO_TEXT | No extractable text in PDF chunk |
| API_ERROR | Gemini API error |
| RATE_LIMIT | API rate limit exceeded |
| PROCESSING_ERROR | Generic processing error |

## Files Modified

**Backend:**
- `app/models.py` - Added JobChunk model
- `app/tasks.py` - Added DB persistence to process_chunk and finalize_job_results
- `app/routes.py` - Added chunk endpoints
- `app/services/chunking_service.py` - Added split_pdf_and_persist()
- `migrations/versions/c1d2e3f4g5h6_add_chunk_persistence_fields.py` - Migration

**Tests:**
- `tests/test_chunk_persistence.py` - Unit tests

**Documentation:**
- `docs/CHUNK_PERSISTENCE_API.md` - Complete API reference
- `docs/CHUNK_PERSISTENCE_IMPLEMENTATION_SUMMARY.md` - Implementation guide
- `docs/CHUNK_PERSISTENCE_QUICK_START.md` - This file

## Rollback

If you need to rollback the migration:

```bash
docker-compose -f docker-compose.dev.yml exec backend flask db downgrade c1d2e3f4g5h6
```

This will:
- Remove added columns from job_chunks table
- Drop the composite index
- Rename chunk_id back to chunk_index

## Monitoring

Key metrics to track:
- Chunk success rate (target: > 95%)
- Average retry count (target: < 1.5)
- Chunk processing time (target: < 30s per chunk)
- Failed chunk count (target: < 5% of total)

## Support

For detailed documentation, see:
- **API Reference:** `docs/CHUNK_PERSISTENCE_API.md`
- **Implementation Guide:** `docs/CHUNK_PERSISTENCE_IMPLEMENTATION_SUMMARY.md`
- **Original Roadmap:** `docs/roadmaps/CHUNK_PERSISTENCE_AND_RETRY_ROADMAP.md`

## Success Criteria

All acceptance criteria met:
- ✅ 100% of chunks persisted and recoverable
- ✅ Failed chunks retried automatically (up to N rounds)
- ✅ Manual retry available via API
- ✅ All chunk status/errors/results accessible
- ✅ No permanent data loss
- ✅ System tested, documented, and ready for deployment

**Status: READY FOR PRODUCTION** ✅

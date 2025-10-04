# Chunk Persistence and Retry API Documentation

## Overview

The chunk persistence and retry system provides robust tracking and recovery for PDF processing chunks. All chunks are persisted to the database, enabling automatic and manual retries, audit trails, and detailed status tracking.

## Database Schema

### JobChunk Table

```sql
CREATE TABLE job_chunks (
    id SERIAL PRIMARY KEY,
    job_id INTEGER NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    chunk_id INTEGER NOT NULL,  -- 0-indexed chunk number
    
    -- Chunk metadata
    start_page INTEGER NOT NULL,
    end_page INTEGER NOT NULL,
    page_count INTEGER NOT NULL,
    has_overlap BOOLEAN DEFAULT FALSE,
    
    -- Chunk payload
    file_b64 TEXT,              -- Base64 encoded PDF chunk data
    storage_url VARCHAR(512),   -- Future: S3/GCS URL
    file_size_bytes INTEGER,
    
    -- Processing state
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
        -- Values: 'pending', 'processing', 'success', 'failed', 'retry_scheduled'
    celery_task_id VARCHAR(155),  -- Current/last Celery task ID
    
    -- Retry tracking
    attempts INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3,
    last_error TEXT,
    last_error_code VARCHAR(50),
    
    -- Results (when successful)
    result_json JSON,  -- {sentences: [...], tokens: 123, status: 'success'}
    processed_at TIMESTAMP,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT unique_job_chunk UNIQUE(job_id, chunk_id),
    INDEX idx_job_chunks_job_id (job_id),
    INDEX idx_job_chunks_status (status),
    INDEX idx_job_chunks_job_status (job_id, status)
);
```

## API Endpoints

### GET /api/v1/jobs/:job_id/chunks

Get detailed chunk status for a job.

**Authentication:** Required (JWT)

**Request:**
```http
GET /api/v1/jobs/123/chunks
Authorization: Bearer <token>
```

**Response (200 OK):**
```json
{
  "job_id": 123,
  "total_chunks": 5,
  "chunks": [
    {
      "id": 1,
      "job_id": 123,
      "chunk_id": 0,
      "start_page": 0,
      "end_page": 19,
      "page_count": 20,
      "has_overlap": false,
      "status": "success",
      "attempts": 1,
      "max_retries": 3,
      "last_error": null,
      "last_error_code": null,
      "processed_at": "2025-01-15T10:30:00Z",
      "created_at": "2025-01-15T10:25:00Z",
      "updated_at": "2025-01-15T10:30:00Z"
    },
    {
      "id": 2,
      "job_id": 123,
      "chunk_id": 1,
      "start_page": 19,
      "end_page": 39,
      "page_count": 21,
      "has_overlap": true,
      "status": "failed",
      "attempts": 3,
      "max_retries": 3,
      "last_error": "API rate limit exceeded",
      "last_error_code": "RATE_LIMIT",
      "processed_at": null,
      "created_at": "2025-01-15T10:25:00Z",
      "updated_at": "2025-01-15T10:28:00Z"
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

**Error Responses:**
- `404 Not Found` - Job not found or access denied

---

### POST /api/v1/jobs/:job_id/chunks/retry

Manually retry failed chunks for a job.

**Authentication:** Required (JWT)

**Request Body (optional):**
```json
{
  "chunk_ids": [1, 3, 5],  // Optional: specific chunks to retry
  "force": false           // Optional: force retry even if max_retries exceeded
}
```

**Request Examples:**

1. Retry all eligible failed chunks:
```http
POST /api/v1/jobs/123/chunks/retry
Authorization: Bearer <token>
Content-Type: application/json

{}
```

2. Retry specific chunks:
```http
POST /api/v1/jobs/123/chunks/retry
Authorization: Bearer <token>
Content-Type: application/json

{
  "chunk_ids": [1, 3]
}
```

3. Force retry (ignore max_retries):
```http
POST /api/v1/jobs/123/chunks/retry
Authorization: Bearer <token>
Content-Type: application/json

{
  "force": true
}
```

**Response (200 OK):**
```json
{
  "message": "Retrying 2 chunks",
  "retried_count": 2,
  "group_id": "abc-123-def-456",
  "chunk_ids": [1, 3]
}
```

**Response when no chunks eligible (200 OK):**
```json
{
  "message": "No chunks eligible for retry",
  "retried_count": 0
}
```

**Error Responses:**
- `404 Not Found` - Job not found or access denied

---

## Chunk Status Lifecycle

```
pending → processing → success
                    ↓
                 failed → retry_scheduled → processing → ...
```

### Status Descriptions

- **pending**: Chunk created but not yet started
- **processing**: Chunk is currently being processed by a worker
- **success**: Chunk processed successfully, results stored in `result_json`
- **failed**: Chunk processing failed (see `last_error` and `last_error_code`)
- **retry_scheduled**: Chunk scheduled for automatic or manual retry

### Error Codes

Common error codes in `last_error_code`:

- `TIMEOUT` - Processing timeout exceeded
- `NO_TEXT` - No extractable text in PDF chunk
- `API_ERROR` - Gemini API error
- `RATE_LIMIT` - API rate limit exceeded
- `PROCESSING_ERROR` - Generic processing error

---

## Automatic Retry Behavior

### Default Configuration

- **Max Retries per Chunk**: 3 attempts
- **Job-Level Retry Rounds**: 3 rounds
- **Retry Triggers**: Automatic on chunk failure

### Retry Logic

1. When `finalize_job_results` detects failed chunks:
   - Check if job retry count < max retries (default 3)
   - Find chunks where `status='failed'` and `attempts < max_retries`
   - Mark eligible chunks as `retry_scheduled`
   - Dispatch new processing tasks
   - Increment job retry_count

2. Process continues until:
   - All chunks succeed, OR
   - Job retry_count reaches max_retries

### Example Flow

```
Job starts with 5 chunks:
  Round 0: Chunk 2 fails (network error)
  → Automatic retry round 1: Chunk 2 retried
  Round 1: Chunk 2 succeeds
  → Job completes successfully

Job with persistent failures:
  Round 0: Chunk 3 fails
  → Retry round 1: Chunk 3 fails again
  → Retry round 2: Chunk 3 fails again
  → Retry round 3: Chunk 3 fails again
  → Job completes with 1 failed chunk (partial success)
```

---

## Manual Retry Use Cases

### Use Case 1: Retry after API quota reset

If chunks failed due to quota/rate limits:

```bash
# Wait for quota to reset, then retry
curl -X POST http://localhost:5000/api/v1/jobs/123/chunks/retry \
  -H "Authorization: Bearer $TOKEN"
```

### Use Case 2: Retry specific problematic chunks

If only certain chunks failed:

```bash
curl -X POST http://localhost:5000/api/v1/jobs/123/chunks/retry \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"chunk_ids": [2, 5]}'
```

### Use Case 3: Force retry exhausted chunks

If chunks exhausted retries but you want to try again:

```bash
curl -X POST http://localhost:5000/api/v1/jobs/123/chunks/retry \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"force": true}'
```

---

## Integration with Existing Job API

### GET /api/v1/jobs/:job_id

The existing job status endpoint now includes chunk information:

```json
{
  "id": 123,
  "status": "completed",
  "total_chunks": 5,
  "processed_chunks": 5,
  "failed_chunks": [2],  // Array of failed chunk IDs
  "retry_count": 2,      // Number of retry rounds executed
  "chunk_results": [     // Legacy field, still populated
    {
      "chunk_id": 0,
      "status": "success",
      "sentences": [...],
      "tokens": 1234
    }
  ]
}
```

---

## WebSocket Progress Events

Chunk processing emits real-time progress via WebSocket:

```javascript
socket.on('job_progress', (data) => {
  console.log(data);
  // {
  //   job_id: 123,
  //   progress_percent: 40,
  //   current_step: "Processing chunks (2/5)",
  //   processed_chunks: 2,
  //   total_chunks: 5
  // }
});
```

---

## Database Queries

### Get all failed chunks for a job

```sql
SELECT * FROM job_chunks 
WHERE job_id = 123 AND status = 'failed'
ORDER BY chunk_id;
```

### Get chunks eligible for retry

```sql
SELECT * FROM job_chunks 
WHERE job_id = 123 
  AND status = 'failed' 
  AND attempts < max_retries
ORDER BY chunk_id;
```

### Get processing summary for all jobs

```sql
SELECT 
  j.id,
  j.status,
  COUNT(c.id) as total_chunks,
  SUM(CASE WHEN c.status = 'success' THEN 1 ELSE 0 END) as success_chunks,
  SUM(CASE WHEN c.status = 'failed' THEN 1 ELSE 0 END) as failed_chunks,
  SUM(CASE WHEN c.status = 'processing' THEN 1 ELSE 0 END) as processing_chunks
FROM jobs j
LEFT JOIN job_chunks c ON c.job_id = j.id
GROUP BY j.id, j.status;
```

---

## Migration Guide

### Running the Migration

Development:
```bash
docker-compose -f docker-compose.dev.yml exec backend flask db upgrade
```

Production (Railway):
```bash
railway run flask db upgrade
```

Production (Vercel/Serverless):
```bash
# Run migration from local with production DB URL
DATABASE_URL=<production-url> flask db upgrade
```

### Rollback

If needed, rollback the migration:
```bash
flask db downgrade -1
```

---

## Performance Considerations

### Database Indexes

The migration creates these indexes for optimal performance:

- `idx_job_chunks_job_id` - Fast lookup by job
- `idx_job_chunks_status` - Fast filtering by status
- `idx_job_chunks_job_status` - Composite index for job+status queries
- `unique_job_chunk` - Ensures chunk_id uniqueness per job

### Storage

- **Small PDFs**: Chunks stored as base64 in `file_b64` (< 1MB per chunk)
- **Large PDFs**: Future option to use `storage_url` for S3/GCS storage

### Query Optimization

Recommended queries use indexed columns:

```sql
-- ✅ Good: Uses index
SELECT * FROM job_chunks WHERE job_id = 123;

-- ✅ Good: Uses composite index
SELECT * FROM job_chunks WHERE job_id = 123 AND status = 'failed';

-- ❌ Avoid: Full table scan
SELECT * FROM job_chunks WHERE last_error LIKE '%timeout%';
```

---

## Monitoring and Observability

### Key Metrics to Track

1. **Chunk Success Rate**
```sql
SELECT 
  COUNT(CASE WHEN status = 'success' THEN 1 END)::float / COUNT(*) as success_rate
FROM job_chunks
WHERE created_at > NOW() - INTERVAL '24 hours';
```

2. **Average Retry Count**
```sql
SELECT AVG(attempts) as avg_attempts
FROM job_chunks
WHERE status = 'success'
  AND created_at > NOW() - INTERVAL '24 hours';
```

3. **Common Error Codes**
```sql
SELECT last_error_code, COUNT(*) as count
FROM job_chunks
WHERE status = 'failed'
  AND created_at > NOW() - INTERVAL '24 hours'
GROUP BY last_error_code
ORDER BY count DESC;
```

---

## Troubleshooting

### Chunk stuck in "processing" status

Possible causes:
- Worker crashed
- Task timeout exceeded
- Database connection lost

Solution:
```sql
-- Reset stuck chunks (older than 1 hour)
UPDATE job_chunks 
SET status = 'failed', 
    last_error = 'Processing timeout - worker may have crashed'
WHERE status = 'processing' 
  AND updated_at < NOW() - INTERVAL '1 hour';
```

### Manual retry not starting

Check:
1. Chunk status is 'failed' or 'retry_scheduled'
2. User has access to the job
3. Celery workers are running
4. Redis connection is healthy

### All chunks failing with same error

Check:
1. Gemini API key is valid
2. API quota not exceeded
3. Network connectivity to Gemini API
4. PDF chunks have extractable text

---

## Future Enhancements

### Planned Features

1. **Object Storage Integration**
   - Store large chunk blobs in S3/GCS
   - Use `storage_url` instead of `file_b64`

2. **Advanced Retry Strategies**
   - Exponential backoff between retry rounds
   - Priority queue for failed chunks
   - Selective retry based on error code

3. **Analytics Dashboard**
   - Real-time chunk processing metrics
   - Error rate trends
   - Performance heatmaps by time of day

4. **Chunk-Level Notifications**
   - Email/webhook on chunk failure
   - Slack integration for monitoring
   - PagerDuty integration for critical failures

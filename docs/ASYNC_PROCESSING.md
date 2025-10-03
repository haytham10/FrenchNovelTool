# Asynchronous Processing & Chunking for Large PDFs

This document describes how asynchronous processing and PDF chunking works for large files (>50 pages).

## Overview

The system now supports asynchronous processing of PDF files using Celery and Redis. Large PDFs (>50 pages) are automatically split into chunks to prevent timeouts and improve reliability.

## Architecture

### Components

1. **Flask API** - Receives PDF uploads and creates jobs
2. **Celery Workers** - Process PDFs asynchronously in the background
3. **Redis** - Message broker and result backend for Celery
4. **PostgreSQL** - Stores job status and results

### Processing Flow

#### Small PDFs (<= 50 pages)
1. User uploads PDF via `/process-pdf` endpoint
2. API processes PDF synchronously (backward compatible)
3. Returns sentences immediately

#### Large PDFs (> 50 pages)
1. User uploads PDF via `/process-pdf` endpoint
2. API returns `202 Accepted` with `job_id`
3. Celery worker picks up task from queue
4. Worker splits PDF into chunks (default 25 pages each)
5. Each chunk is processed sequentially
6. Results are merged and saved
7. Job status is updated to `completed`
8. Frontend polls `/jobs/{job_id}` for status updates

## Configuration

### Constants (in `app/constants.py`)

```python
CHUNK_THRESHOLD_PAGES = 50  # PDFs with more than 50 pages will be chunked
DEFAULT_CHUNK_SIZE_PAGES = 25  # Process 25 pages per chunk
```

### Environment Variables

```bash
REDIS_URL=redis://localhost:6379/0  # Redis connection for Celery
```

## Running the System

### Development

1. Start Redis:
```bash
docker run -d -p 6379:6379 redis:7-alpine
```

2. Start Celery worker:
```bash
cd backend
celery -A worker worker --loglevel=info
```

3. Start Flask API:
```bash
cd backend
python run.py
```

### Production (Docker Compose)

The `docker-compose.yml` includes a Celery worker service:

```yaml
celery:
  build: ./backend
  command: celery -A worker worker --loglevel=info
  environment:
    - REDIS_URL=redis://redis:6379/0
  depends_on:
    - redis
    - db
```

Start everything:
```bash
docker-compose up
```

## API Endpoints

### POST /process-pdf

**Request:**
```
Content-Type: multipart/form-data

pdf_file: <file>
job_id: <optional>
async: true|false (default: auto-detect based on page count)
```

**Response (Async - Large PDF):**
```json
{
  "job_id": 123,
  "status": "queued",
  "page_count": 150,
  "message": "PDF processing started. Check job status for progress."
}
```
Status Code: `202 Accepted`

**Response (Sync - Small PDF):**
```json
{
  "sentences": ["Sentence 1", "Sentence 2", ...],
  "job_id": 123
}
```
Status Code: `200 OK`

### GET /jobs/{job_id}

Get job status and progress.

**Response:**
```json
{
  "job": {
    "id": 123,
    "status": "processing",
    "original_filename": "large_book.pdf",
    "page_count": 150,
    "chunk_size": 25,
    "total_chunks": 6,
    "completed_chunks": 3,
    "progress_percent": 50.0,
    "created_at": "2025-01-03T10:00:00Z",
    "started_at": "2025-01-03T10:00:05Z"
  },
  "result": null
}
```

When completed:
```json
{
  "job": {
    "id": 123,
    "status": "completed",
    "progress_percent": 100.0,
    ...
  },
  "result": {
    "sentences_count": 1250,
    "spreadsheet_url": null
  }
}
```

## Frontend Integration

### Job Progress Polling

Use the `useJobStatus` hook to automatically poll job status:

```typescript
import { useJobStatus } from '@/lib/queries';

function MyComponent({ jobId }) {
  const { data: jobStatus } = useJobStatus(jobId);
  
  const job = jobStatus?.job;
  const result = jobStatus?.result;
  
  if (job?.status === 'processing') {
    return <div>Progress: {job.progress_percent}%</div>;
  }
  
  if (job?.status === 'completed') {
    return <div>Done! {result?.sentences_count} sentences processed</div>;
  }
  
  return <div>Status: {job?.status}</div>;
}
```

### Job Progress Dialog

Use the pre-built `JobProgressDialog` component:

```typescript
import JobProgressDialog from '@/components/JobProgressDialog';

function MyComponent() {
  const [jobId, setJobId] = useState<number | null>(null);
  const [showProgress, setShowProgress] = useState(false);
  
  const handleComplete = (result) => {
    console.log('Processing complete:', result);
    setShowProgress(false);
  };
  
  return (
    <>
      {/* Your upload UI */}
      <JobProgressDialog
        open={showProgress}
        jobId={jobId}
        onClose={() => setShowProgress(false)}
        onComplete={handleComplete}
      />
    </>
  );
}
```

## Database Schema

### Job Model Extensions

New fields added to the `jobs` table:

- `page_count` - Total pages in PDF
- `chunk_size` - Pages per chunk (if chunked)
- `total_chunks` - Total number of chunks
- `completed_chunks` - Number of completed chunks
- `progress_percent` - Overall progress (0-100)
- `parent_job_id` - For future sub-job support

## Monitoring

### Check Worker Status

```bash
celery -A worker inspect active
celery -A worker inspect stats
```

### View Job Logs

Worker logs show chunk processing:
```
[2025-01-03 10:00:05] INFO: Processing job 123: large_book.pdf, 150 pages
[2025-01-03 10:00:05] INFO: Job 123 requires chunking (150 > 50)
[2025-01-03 10:00:05] INFO: Chunking job 123 into 6 chunks of 25 pages
[2025-01-03 10:00:10] INFO: Processing chunk 1/6 (pages 1-25)
[2025-01-03 10:01:05] INFO: Job 123 chunk 1/6 processed 45 sentences
[2025-01-03 10:01:05] INFO: Processing chunk 2/6 (pages 26-50)
...
[2025-01-03 10:05:30] INFO: Job 123 completed all 6 chunks, total sentences: 1250
```

## Error Handling

### Chunk Failures

If a chunk fails:
- Error is logged
- Job status is set to `failed`
- Credits are refunded
- Error message stored in job record

### Worker Failures

If worker crashes:
- Celery will retry the task (up to 3 times by default)
- If all retries fail, job is marked as failed
- Frontend will show error message from polling

## Performance Considerations

### Chunk Size

- Default: 25 pages per chunk
- Smaller chunks = more API calls but faster failure recovery
- Larger chunks = fewer API calls but longer processing time per chunk

### Polling Interval

- Frontend polls every 2 seconds
- Stops polling when job is completed/failed
- Use `refetchInterval` option to adjust

## Migration Guide

### Database Migration

Run the migration to add new fields:

```bash
cd backend
flask db upgrade
```

### Updating Existing Code

The changes are backward compatible:

1. Small PDFs continue to work synchronously
2. Existing `/process-pdf` calls work unchanged
3. New async flow only activates for large PDFs or when `async=true`

### Gradual Rollout

1. Deploy backend with new code
2. Run database migration
3. Start Celery worker
4. Update frontend to show progress UI
5. Monitor logs for issues

## Troubleshooting

### Worker not picking up jobs

1. Check Redis connection:
   ```bash
   redis-cli ping
   ```

2. Check worker status:
   ```bash
   celery -A worker inspect active
   ```

3. Check environment variables in worker process

### Jobs stuck in "queued" status

1. Ensure Celery worker is running
2. Check worker logs for errors
3. Verify Redis is accessible

### Progress not updating

1. Check `/jobs/{job_id}` endpoint directly
2. Verify database updates are happening
3. Check for errors in worker logs

## Future Enhancements

- Parallel chunk processing (using Celery groups/chords)
- Resume from failed chunk
- Configurable chunk size per request
- Progress notifications via WebSocket
- Job cancellation support

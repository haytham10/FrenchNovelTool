# Async PDF Processing API Documentation

## Overview

The async PDF processing feature enables processing of large PDF documents (100-500 pages) in the background using Celery task queues. This provides better user experience with real-time progress tracking, cancellation support, and resilient error handling.

## Architecture

### Components

- **Flask API**: Handles job creation, status queries, and cancellation
- **Celery Workers**: Execute background PDF processing tasks
- **Redis**: Message broker and result backend
- **Flower**: Web UI for monitoring Celery tasks (http://localhost:5555)

### Processing Flow

```
1. Client uploads PDF → POST /api/v1/jobs/confirm (creates job, reserves credits)
2. Client starts processing → POST /api/v1/process-pdf-async (enqueues task)
3. Server returns job_id immediately
4. Client polls → GET /api/v1/jobs/<job_id> (gets progress)
5. Celery worker processes PDF in chunks
6. Client receives completion or error status
7. Client finalizes job → POST /api/v1/jobs/<job_id>/finalize
```

## API Endpoints

### 1. Start Async Processing

**Endpoint**: `POST /api/v1/process-pdf-async`

**Authentication**: Required (JWT)

**Rate Limit**: 10 per hour

**Request**:
```
Content-Type: multipart/form-data

Parameters:
- pdf_file: File (required)
- job_id: int (required) - From /jobs/confirm
- sentence_length_limit: int (optional)
- gemini_model: string (optional) - 'balanced', 'quality', or 'speed'
- ignore_dialogue: boolean (optional)
- preserve_formatting: boolean (optional)
- fix_hyphenation: boolean (optional)
- min_sentence_length: int (optional)
```

**Response** (202 Accepted):
```json
{
  "job_id": 123,
  "task_id": "job_123_1696378800.123456",
  "status": "pending",
  "message": "PDF processing started"
}
```

### 2. Get Job Status

**Endpoint**: `GET /api/v1/jobs/<job_id>`

**Authentication**: Required (JWT)

**Response**:
```json
{
  "id": 123,
  "user_id": 1,
  "status": "processing",
  "original_filename": "novel.pdf",
  "model": "gemini-2.5-flash",
  "estimated_credits": 100,
  "created_at": "2025-10-04T10:00:00Z",
  "started_at": "2025-10-04T10:00:05Z",
  
  // Progress tracking
  "progress_percent": 45,
  "current_step": "Processing chunk 5/10",
  "total_chunks": 10,
  "processed_chunks": 4,
  
  // Celery task info
  "celery_task_id": "job_123_1696378800.123456",
  "task_state": {
    "state": "PROGRESS",
    "info": {}
  },
  
  // Performance metrics
  "processing_time_seconds": 120,
  "gemini_api_calls": 4,
  "gemini_tokens_used": 50000
}
```

**Status Values**:
- `pending`: Job created, waiting to start
- `processing`: Currently processing
- `completed`: Successfully completed
- `failed`: Processing failed
- `cancelled`: Cancelled by user

### 3. Cancel Job

**Endpoint**: `POST /api/v1/jobs/<job_id>/cancel`

**Authentication**: Required (JWT)

**Response**:
```json
{
  "message": "Job cancelled successfully",
  "job_id": 123,
  "status": "cancelled"
}
```

**Notes**:
- Only jobs with status `pending` or `processing` can be cancelled
- Credits are automatically refunded
- Celery task is terminated

## Chunking Strategy

PDFs are automatically chunked based on size:

| PDF Size | Chunk Size | Parallel Workers | Strategy |
|----------|-----------|-----------------|----------|
| ≤30 pages | 30 pages | 1 | Single chunk |
| 31-100 pages | 20 pages | 3 | Medium chunks |
| 101-500 pages | 15 pages | 5 | Small chunks |

**Overlap**: 1 page overlap between chunks for context preservation

## Error Handling

### Chunk-Level Failures

- Failed chunks are recorded in `failed_chunks` array
- Other chunks continue processing
- Partial results are returned

### Retry Logic

- Automatic retry on transient failures (network errors)
- Max 3 retries per task
- Exponential backoff

### Timeout Protection

- Soft time limit: 25 minutes per task
- Hard time limit: 30 minutes per task

## Frontend Integration

### React Hook

```typescript
import { useJobPolling } from '@/lib/useJobPolling';

function MyComponent() {
  const { job, loading, error } = useJobPolling({
    jobId: 123,
    interval: 2000, // Poll every 2 seconds
    onComplete: (job) => {
      console.log('Job completed!', job);
    },
  });

  return (
    <div>
      {job && (
        <>
          <p>Status: {job.status}</p>
          <p>Progress: {job.progress_percent}%</p>
        </>
      )}
    </div>
  );
}
```

### Progress Dialog

```typescript
import JobProgressDialog from '@/components/JobProgressDialog';

function MyComponent() {
  const [jobId, setJobId] = useState<number | null>(null);
  const [dialogOpen, setDialogOpen] = useState(false);

  const handleComplete = (job) => {
    // Handle completed job
    setDialogOpen(false);
  };

  return (
    <JobProgressDialog
      jobId={jobId}
      open={dialogOpen}
      onClose={() => setDialogOpen(false)}
      onComplete={handleComplete}
    />
  );
}
```

## Deployment

### Docker Compose

Services are configured in `docker-compose.yml`:

```bash
# Start all services
docker-compose up -d

# Scale workers
docker-compose up -d --scale celery-worker=4

# View Flower monitoring UI
open http://localhost:5555
```

### Environment Variables

```bash
# Redis
REDIS_URL=redis://localhost:6379/0

# Flower UI (production)
FLOWER_USER=admin
FLOWER_PASSWORD=secure-password-here
FLOWER_PORT=5555
```

### Monitoring

**Flower Dashboard**: http://localhost:5555
- Real-time task monitoring
- Worker status
- Task history and statistics

## Performance Tuning

### Worker Concurrency

Adjust based on available CPU cores:

```bash
# Development (4 workers)
celery -A app.celery_app:celery worker --concurrency=4

# Production (8 workers)
celery -A app.celery_app:celery worker --concurrency=8
```

### Memory Management

```bash
# Restart worker after 50 tasks (prevent memory leaks)
celery -A app.celery_app:celery worker --max-tasks-per-child=50
```

### Redis Memory Limit

```bash
# Limit Redis memory (in docker-compose.yml)
redis-server --maxmemory 256mb --maxmemory-policy allkeys-lru
```

## Troubleshooting

### Worker Not Picking Up Tasks

1. Check Redis connection:
   ```bash
   redis-cli ping
   ```

2. Check worker logs:
   ```bash
   docker-compose logs celery-worker
   ```

3. Restart workers:
   ```bash
   docker-compose restart celery-worker
   ```

### Tasks Stuck in Pending

1. Check Celery worker status in Flower
2. Check Redis memory usage
3. Increase worker concurrency

### High Memory Usage

1. Reduce `--max-tasks-per-child`
2. Reduce worker concurrency
3. Increase chunk size (processes fewer chunks in parallel)

## Migration from Sync to Async

### Gradual Rollout

1. **Phase 1**: Deploy async infrastructure (Celery, Redis)
2. **Phase 2**: Test with internal users
3. **Phase 3**: Feature flag rollout (10% → 50% → 100%)
4. **Phase 4**: Deprecate sync endpoint

### Backwards Compatibility

- Sync endpoint (`/process-pdf`) still available
- Clients can choose sync or async based on file size
- Recommended: Use async for PDFs > 30 pages

## Security Considerations

1. **Task Isolation**: Each task runs in isolated process
2. **Temporary Files**: Auto-cleanup after processing
3. **Credit System**: Jobs reserve credits before processing
4. **Rate Limiting**: Prevents abuse of async endpoints
5. **Authentication**: All endpoints require JWT

## Best Practices

1. **Always use job confirmation flow** for credit tracking
2. **Poll at reasonable intervals** (2-5 seconds)
3. **Handle all terminal states** (completed, failed, cancelled)
4. **Show progress to users** via progress bar
5. **Allow cancellation** for long-running jobs
6. **Clean up UI state** on completion/error

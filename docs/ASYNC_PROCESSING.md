# Async PDF Processing Documentation

## Overview

The French Novel Tool now supports asynchronous processing for large PDF files. This allows the system to handle novel-length documents (100+ pages) efficiently without timing out or consuming excessive resources.

## Architecture

### Components

1. **Chunking Service** (`app/services/chunking_service.py`)
   - Splits large PDFs into manageable chunks (default: 50 pages per chunk)
   - Configurable threshold for when chunking is triggered
   - Efficient text extraction and chunk management

2. **Celery Tasks** (`app/tasks.py`)
   - Async task orchestration using Celery
   - Parallel chunk processing with automatic retries
   - Idempotent merge operations for chunk results

3. **Job Tracking** (Enhanced `Job` model)
   - Progress tracking (total_chunks, completed_chunks, progress_percent)
   - Celery task ID for status monitoring
   - Comprehensive error tracking

4. **API Endpoints**
   - `POST /process-pdf` - Automatically detects large files and processes async
   - `GET /jobs/<job_id>` - Check job status and progress
   - `POST /jobs/<job_id>/cancel` - Cancel running jobs

## Configuration

### Environment Variables

```bash
# Celery/Redis Configuration
REDIS_URL=redis://localhost:6379/0

# Async Processing Settings
ASYNC_PROCESSING_ENABLED=True
CHUNKING_THRESHOLD_PAGES=50    # Files larger than this will be chunked
CHUNK_SIZE_PAGES=50             # Pages per chunk
MAX_WORKERS=4                   # Concurrent worker processes
WORKER_MEMORY_LIMIT_MB=2048     # Memory limit per worker (2GB)
TASK_TIMEOUT_SECONDS=3600       # Task timeout (1 hour)
```

## How It Works

### Small Files (<= 50 pages)
1. File uploaded via `POST /process-pdf`
2. Processed synchronously (existing behavior)
3. Returns sentences immediately
4. Response: `200 OK` with sentences

### Large Files (> 50 pages)
1. File uploaded via `POST /process-pdf`
2. System detects file size exceeds threshold
3. Creates async job and returns job ID
4. Response: `202 Accepted` with job_id
5. Background processing:
   - PDF split into chunks
   - Chunks processed in parallel
   - Results merged idempotently
   - Job marked as completed
6. Client polls `GET /jobs/<job_id>` for status

### Progress Tracking

The job object includes:
```json
{
  "id": 123,
  "status": "processing",
  "total_chunks": 4,
  "completed_chunks": 2,
  "progress_percent": 50,
  "original_filename": "novel.pdf"
}
```

## Deployment

### Running Celery Worker

**Development:**
```bash
cd backend
./start-worker.sh
```

**Docker Compose:**
```bash
docker-compose -f docker-compose.dev.yml up celery-worker
```

**Production (systemd):**
```ini
[Unit]
Description=French Novel Tool Celery Worker
After=network.target redis.service

[Service]
Type=simple
User=www-data
WorkingDirectory=/app/backend
Environment="PATH=/app/backend/.venv/bin"
ExecStart=/app/backend/.venv/bin/celery -A celery_app.celery_app worker \
    --loglevel=info \
    --concurrency=4 \
    --max-tasks-per-child=50
Restart=always

[Install]
WantedBy=multi-user.target
```

### Monitoring

**Check Worker Status:**
```bash
celery -A celery_app.celery_app inspect active
celery -A celery_app.celery_app inspect stats
```

**Monitor Jobs:**
```bash
celery -A celery_app.celery_app flower  # Web UI on port 5555
```

## Resource Management

### Memory Limits
- Workers restart after 50 tasks to prevent memory leaks
- Memory limit per worker: 2GB (configurable)
- Tasks have soft/hard time limits to prevent runaway processes

### Retry Logic
- Chunk processing retries up to 3 times with exponential backoff
- Failed jobs automatically refund credits
- Comprehensive error logging for debugging

### Cleanup
- Temporary PDF files automatically cleaned up
- Completed jobs cleaned up after 24 hours (periodic task)
- Failed jobs retain error information for debugging

## Error Handling

### Error Codes
- `CHUNK_PROCESSING_ERROR` - Failed to process a chunk
- `TASK_TIMEOUT` - Task exceeded time limit
- `PROCESSING_ERROR` - General processing error

### Failure Scenarios
1. **Chunk Processing Failure**: Retries with backoff, then fails entire job
2. **Merge Failure**: Job marked as failed, credits refunded
3. **Worker Crash**: Task re-queued if `acks_late=True`
4. **Timeout**: Soft limit warning, then hard kill and refund

## Performance Metrics

### Expected Performance
- Small files (<50 pages): < 30 seconds
- Medium files (50-100 pages): 1-2 minutes
- Large files (100-200 pages): 2-5 minutes
- Very large files (200+ pages): 5-10 minutes

### Optimization
- Parallel chunk processing reduces total time
- Each chunk processed independently
- Results cached in Redis for fast retrieval

## API Examples

### Submit Large PDF for Processing
```bash
curl -X POST http://localhost:5000/api/v1/process-pdf \
  -H "Authorization: Bearer $TOKEN" \
  -F "pdf_file=@large_novel.pdf" \
  -F "job_id=123"
```

Response (async):
```json
{
  "job_id": 123,
  "status": "processing",
  "async": true,
  "message": "Large file detected. Processing asynchronously. Check job status for progress."
}
```

### Check Job Status
```bash
curl http://localhost:5000/api/v1/jobs/123 \
  -H "Authorization: Bearer $TOKEN"
```

Response:
```json
{
  "id": 123,
  "status": "processing",
  "total_chunks": 4,
  "completed_chunks": 2,
  "progress_percent": 50,
  "original_filename": "large_novel.pdf",
  "created_at": "2025-01-01T12:00:00Z",
  "started_at": "2025-01-01T12:00:05Z"
}
```

### Cancel Job
```bash
curl -X POST http://localhost:5000/api/v1/jobs/123/cancel \
  -H "Authorization: Bearer $TOKEN"
```

## Troubleshooting

### Common Issues

**Worker Not Starting:**
- Check Redis is running: `redis-cli ping`
- Verify environment variables are set
- Check logs: `tail -f logs/celery.log`

**Jobs Stuck in Processing:**
- Check worker status: `celery -A celery_app.celery_app inspect active`
- Restart workers: `systemctl restart celery-worker`
- Check task timeout settings

**High Memory Usage:**
- Reduce `MAX_WORKERS`
- Reduce `CHUNK_SIZE_PAGES`
- Lower `WORKER_MEMORY_LIMIT_MB`

**Slow Processing:**
- Increase `MAX_WORKERS` (if resources available)
- Check Gemini API rate limits
- Monitor Redis performance

## Best Practices

1. **Resource Planning**: Allocate 2GB RAM per worker
2. **Scaling**: Add more workers for higher throughput
3. **Monitoring**: Use Flower for real-time worker monitoring
4. **Backups**: Redis persistence enabled for job state
5. **Logging**: Centralized logging for distributed workers
6. **Testing**: Test with various file sizes before production

## Future Enhancements

- [ ] WebSocket/SSE for real-time progress updates
- [ ] Priority queues for premium users
- [ ] Automatic scaling based on queue depth
- [ ] Result caching for duplicate files
- [ ] Distributed tracing for debugging
- [ ] Performance dashboards and metrics

## Credits Integration

The async processing system integrates seamlessly with the credit system:
- Credits reserved when job created
- Credits adjusted based on actual token usage
- Automatic refunds on failure or cancellation
- Transparent billing for chunked processing

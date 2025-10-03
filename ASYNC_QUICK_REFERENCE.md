# Quick Reference: Async PDF Processing (PR #36)

## For Developers

### How It Works
- **Small PDFs (≤50 pages)**: Processed synchronously (instant response with sentences)
- **Large PDFs (>50 pages)**: Processed asynchronously (returns job_id, poll for status)

### API Response Changes

#### Small PDF (Synchronous)
```json
POST /api/v1/process-pdf
→ HTTP 200 OK
{
  "sentences": ["Sentence 1.", "Sentence 2.", ...]
}
```

#### Large PDF (Asynchronous)
```json
POST /api/v1/process-pdf
→ HTTP 202 Accepted
{
  "job_id": 123,
  "status": "processing",
  "async": true,
  "message": "Large file detected. Processing asynchronously..."
}
```

### New Endpoints

#### Check Job Status
```bash
GET /api/v1/jobs/<job_id>
Authorization: Bearer <token>

Response:
{
  "id": 123,
  "status": "processing|completed|failed",
  "total_chunks": 4,
  "completed_chunks": 2,
  "progress_percent": 50,
  "original_filename": "novel.pdf",
  "created_at": "2025-10-03T12:00:00Z",
  "started_at": "2025-10-03T12:00:05Z",
  "completed_at": null  // or timestamp when done
}
```

#### Cancel Job
```bash
POST /api/v1/jobs/<job_id>/cancel
Authorization: Bearer <token>

Response:
{
  "message": "Job cancelled successfully"
}
```

### Frontend Integration

```typescript
import { processPdf, getJob } from '@/lib/api';

// Upload PDF
const result = await processPdf(file);

if ('job_id' in result) {
  // Async processing - poll for status
  const jobId = result.job_id;
  
  const interval = setInterval(async () => {
    const job = await getJob(jobId);
    console.log(`Progress: ${job.progress_percent}%`);
    
    if (job.status === 'completed') {
      clearInterval(interval);
      // Handle completion
    } else if (job.status === 'failed') {
      clearInterval(interval);
      // Handle error
    }
  }, 2000); // Poll every 2 seconds
  
} else {
  // Sync processing - sentences available immediately
  const sentences = result;
}
```

## For DevOps

### Environment Variables
```bash
# Required
REDIS_URL=redis://localhost:6379/0

# Optional (with defaults)
ASYNC_PROCESSING_ENABLED=True
CHUNKING_THRESHOLD_PAGES=50
CHUNK_SIZE_PAGES=50
MAX_WORKERS=4
WORKER_MEMORY_LIMIT_MB=2048
TASK_TIMEOUT_SECONDS=3600
```

### Start Celery Worker

**Development:**
```bash
cd backend
celery -A app.celery_app.celery_app worker --loglevel=info
```

**Production (systemd):**
```bash
sudo systemctl start frenchnoveltool-celery
sudo systemctl enable frenchnoveltool-celery  # Start on boot
```

**Production (Docker):**
```bash
docker-compose up -d celery-worker
```

### Monitoring

**Check worker status:**
```bash
celery -A app.celery_app.celery_app inspect ping
celery -A app.celery_app.celery_app inspect active
celery -A app.celery_app.celery_app inspect stats
```

**View logs:**
```bash
# Systemd
journalctl -u frenchnoveltool-celery -f

# Docker
docker-compose logs -f celery-worker

# File
tail -f /var/log/frenchnoveltool/celery.log
```

**Monitor with Flower (Web UI):**
```bash
pip install flower
celery -A app.celery_app.celery_app flower --port=5555
# Access: http://localhost:5555
```

### Scaling

**Increase workers:**
```bash
# In .env
MAX_WORKERS=8

# Restart worker
sudo systemctl restart frenchnoveltool-celery
```

**Multiple worker instances:**
```bash
# Instance 1
celery -A app.celery_app.celery_app worker --hostname=worker1@%h

# Instance 2
celery -A app.celery_app.celery_app worker --hostname=worker2@%h
```

### Troubleshooting

**Jobs stuck in "processing":**
```bash
# Check worker
sudo systemctl status frenchnoveltool-celery

# Restart worker
sudo systemctl restart frenchnoveltool-celery

# Check Redis
redis-cli ping
```

**High memory usage:**
```bash
# Reduce workers in .env
MAX_WORKERS=2
WORKER_MEMORY_LIMIT_MB=1024

# Restart
sudo systemctl restart frenchnoveltool-celery
```

**Redis errors:**
```bash
# Development fallback (in-memory)
REDIS_URL=memory://

# Production - check Redis
sudo systemctl status redis
```

## For Testing

### Test Async Processing
```bash
cd backend

# Upload a large PDF (>50 pages)
curl -X POST http://localhost:5000/api/v1/process-pdf \
  -H "Authorization: Bearer $TOKEN" \
  -F "pdf_file=@large_document.pdf"

# Should return HTTP 202 with job_id
```

### Run Tests
```bash
cd backend
pytest tests/test_async_processing.py -v
pytest tests/test_chunking_service.py -v
```

### Verify Deployment
```bash
cd backend
./verify-deployment.sh
```

## Configuration Presets

### Development (Fast, Low Memory)
```bash
ASYNC_PROCESSING_ENABLED=True
CHUNKING_THRESHOLD_PAGES=10   # Lower threshold for testing
CHUNK_SIZE_PAGES=10
MAX_WORKERS=2
REDIS_URL=memory://             # No Redis required
```

### Production (Balanced)
```bash
ASYNC_PROCESSING_ENABLED=True
CHUNKING_THRESHOLD_PAGES=50
CHUNK_SIZE_PAGES=50
MAX_WORKERS=4
WORKER_MEMORY_LIMIT_MB=2048
REDIS_URL=redis://localhost:6379/0
```

### High Volume (Maximum Performance)
```bash
ASYNC_PROCESSING_ENABLED=True
CHUNKING_THRESHOLD_PAGES=25    # Smaller chunks, more parallelism
CHUNK_SIZE_PAGES=25
MAX_WORKERS=8
WORKER_MEMORY_LIMIT_MB=2048
REDIS_URL=redis://localhost:6379/0
```

## Key Metrics

### Expected Performance
| File Size | Pages | Processing Time |
|-----------|-------|-----------------|
| Small     | <50   | <30 seconds     |
| Medium    | 50-100 | 1-2 minutes    |
| Large     | 100-200 | 2-5 minutes   |
| Very Large | 200+  | 5-10 minutes   |

### Resource Usage (per worker)
- **Memory**: ~500MB baseline + ~1.5GB per active chunk
- **CPU**: 50-100% during processing
- **Disk**: Temporary files cleaned up automatically

## Support

- **Documentation**: See `docs/ASYNC_PROCESSING.md`
- **Deployment**: See `PR_MERGE_CHECKLIST.md`
- **Troubleshooting**: See `docs/DEPLOYMENT_ASYNC.md`

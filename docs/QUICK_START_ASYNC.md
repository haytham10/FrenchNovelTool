# Quick Start: Async Processing for Large PDFs

## For Developers

### Starting the System

**Option 1: Docker Compose (Recommended)**
```bash
# Start all services including Celery worker
docker-compose up

# Or for development with hot reload
docker-compose -f docker-compose.dev.yml up
```

**Option 2: Manual Start**
```bash
# Terminal 1: Redis
docker run -d -p 6379:6379 redis:7-alpine

# Terminal 2: Backend API
cd backend
python run.py

# Terminal 3: Celery Worker (NEW!)
cd backend
celery -A worker worker --loglevel=info

# Terminal 4: Frontend
cd frontend
npm run dev
```

### Database Migration

Run once after pulling the code:
```bash
cd backend
flask db upgrade
```

## For Users

### How It Works

**Small PDFs (≤50 pages)**
- Works exactly as before
- Immediate processing
- Results returned right away

**Large PDFs (>50 pages)**
- Upload starts processing in the background
- Progress dialog shows real-time updates
- You can close the dialog and let it run
- Get notified when complete

### Using the Frontend

1. **Upload a large PDF** via the normal upload flow
2. **Progress dialog appears** automatically showing:
   - Current chunk being processed (e.g., "Processing chunk 3 of 6")
   - Overall progress percentage
   - Total pages and chunk information
3. **Options:**
   - Wait and watch the progress
   - Click "Run in Background" to continue working
   - Check job status in History tab

### API Usage

**For API Developers:**

```bash
# Upload and start processing
curl -X POST http://localhost:5000/api/v1/process-pdf \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "pdf_file=@large_book.pdf" \
  -F "job_id=123"

# Response for large PDF:
{
  "job_id": 123,
  "status": "queued",
  "page_count": 150,
  "message": "PDF processing started. Check job status for progress."
}

# Poll job status
curl http://localhost:5000/api/v1/jobs/123 \
  -H "Authorization: Bearer YOUR_TOKEN"

# Response:
{
  "job": {
    "id": 123,
    "status": "processing",
    "progress_percent": 50.0,
    "completed_chunks": 3,
    "total_chunks": 6,
    ...
  }
}
```

## Configuration

### Environment Variables

Add to your `.env` file:
```bash
# Redis connection (required for async processing)
REDIS_URL=redis://localhost:6379/0

# Optional: Adjust chunking behavior
CHUNK_THRESHOLD_PAGES=50    # Default: 50
DEFAULT_CHUNK_SIZE_PAGES=25  # Default: 25
```

### Adjusting Chunk Size

In `backend/app/constants.py`:
```python
CHUNK_THRESHOLD_PAGES = 50  # PDFs larger than this will be chunked
DEFAULT_CHUNK_SIZE_PAGES = 25  # Pages per chunk
```

Smaller chunks = faster failure recovery, more API calls
Larger chunks = fewer API calls, longer per-chunk processing

## Monitoring

### Check Worker Status
```bash
celery -A worker inspect active
celery -A worker inspect stats
```

### View Logs
```bash
# Worker logs
docker logs french-novel-celery -f

# API logs  
docker logs french-novel-backend -f
```

### Check Job in Database
```bash
# Using SQLite
sqlite3 app.db "SELECT id, status, progress_percent, completed_chunks, total_chunks FROM jobs WHERE id=123;"

# Using psql (if using PostgreSQL)
psql $DATABASE_URL -c "SELECT id, status, progress_percent, completed_chunks, total_chunks FROM jobs WHERE id=123;"
```

## Troubleshooting

### Worker Not Picking Up Jobs

1. Check if worker is running:
   ```bash
   docker ps | grep celery
   ```

2. Check Redis connection:
   ```bash
   redis-cli ping
   # Should respond: PONG
   ```

3. Check environment variables:
   ```bash
   docker exec french-novel-celery env | grep REDIS_URL
   ```

### Job Stuck in "queued"

1. Restart Celery worker:
   ```bash
   docker-compose restart celery
   ```

2. Check worker logs for errors:
   ```bash
   docker logs french-novel-celery --tail 100
   ```

### Progress Not Updating

1. Check the `/jobs/{job_id}` endpoint directly:
   ```bash
   curl http://localhost:5000/api/v1/jobs/123 -H "Authorization: Bearer TOKEN"
   ```

2. Verify database updates:
   ```bash
   sqlite3 app.db "SELECT * FROM jobs WHERE id=123;"
   ```

## Performance Tips

### For Small PDFs
- No change needed, works as before
- Synchronous processing is faster for small files

### For Large PDFs
- Adjust chunk size based on your needs:
  - 10 pages: Faster failure recovery, more progress updates
  - 50 pages: Fewer API calls, better for stable connections

### Scaling Workers
```bash
# Run multiple workers for parallel processing
celery -A worker worker --concurrency=4

# Or use autoscale
celery -A worker worker --autoscale=10,3
```

## Migration from Previous Version

### No Code Changes Required!

The system is fully backward compatible:
- Existing frontend code works unchanged
- Small PDFs process synchronously (no change)
- Large PDFs automatically use async (new behavior)

### Only Need:

1. **Update backend dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Run database migration:**
   ```bash
   flask db upgrade
   ```

3. **Start Celery worker:**
   ```bash
   celery -A worker worker --loglevel=info
   ```

## Testing

### Test Small PDF
```bash
# Should return sentences immediately
curl -X POST http://localhost:5000/api/v1/process-pdf \
  -H "Authorization: Bearer TOKEN" \
  -F "pdf_file=@small_10_pages.pdf"
```

### Test Large PDF
```bash
# Should return job_id with 202 status
curl -X POST http://localhost:5000/api/v1/process-pdf \
  -H "Authorization: Bearer TOKEN" \
  -F "pdf_file=@large_100_pages.pdf"
```

### Monitor Processing
```bash
# Watch job progress
watch -n 2 'curl -s http://localhost:5000/api/v1/jobs/123 -H "Authorization: Bearer TOKEN" | jq .job.progress_percent'
```

## Support

- **Documentation**: See `docs/ASYNC_PROCESSING.md`
- **Implementation Details**: See `IMPLEMENTATION_SUMMARY.md`
- **Issues**: Check GitHub Issues
- **Logs**: Check worker and API logs for errors

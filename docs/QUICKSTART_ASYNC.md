# Quick Start: Large PDF Processing

Get async PDF processing up and running in 5 minutes.

## Prerequisites

- Docker and Docker Compose installed
- Gemini API key

## Setup

### 1. Clone and Configure

```bash
git clone https://github.com/haytham10/FrenchNovelTool.git
cd FrenchNovelTool

# Configure backend
cp backend/.env.example backend/.env
# Edit backend/.env and add your GEMINI_API_KEY
```

### 2. Start Services

```bash
# Start all services (backend, frontend, Redis, Celery worker)
docker-compose -f docker-compose.dev.yml up -d

# Check services are running
docker-compose -f docker-compose.dev.yml ps
```

### 3. Run Migrations

```bash
docker-compose -f docker-compose.dev.yml exec backend flask db upgrade
```

## Verify Installation

### Check Health

```bash
# API health
curl http://localhost:5000/api/v1/health

# Expected response:
# {"status": "healthy", "service": "French Novel Tool API", "version": "1.0.0"}

# Worker status
docker-compose -f docker-compose.dev.yml exec celery-worker \
  celery -A celery_app.celery_app inspect ping

# Expected response:
# {
#   "celery@<hostname>": {"ok": "pong"}
# }
```

### Access Services

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:5000
- **Redis**: localhost:6379

## Test Large PDF Processing

### Option 1: Using the Frontend

1. Open http://localhost:3000
2. Login with Google
3. Upload a PDF >50 pages
4. System will automatically:
   - Detect it's a large file
   - Process asynchronously
   - Show progress updates

### Option 2: Using API Directly

```bash
# 1. Get auth token (replace with your auth flow)
TOKEN="your-jwt-token"

# 2. Upload large PDF
curl -X POST http://localhost:5000/api/v1/process-pdf \
  -H "Authorization: Bearer $TOKEN" \
  -F "pdf_file=@large_novel.pdf"

# Response (async):
# {
#   "job_id": 123,
#   "status": "processing",
#   "async": true,
#   "message": "Large file detected. Processing asynchronously..."
# }

# 3. Check progress
curl http://localhost:5000/api/v1/jobs/123 \
  -H "Authorization: Bearer $TOKEN"

# Response:
# {
#   "id": 123,
#   "status": "processing",
#   "total_chunks": 4,
#   "completed_chunks": 2,
#   "progress_percent": 50
# }

# 4. Keep polling until status is "completed"
# Then retrieve results from history or directly from job
```

## Monitoring

### View Worker Logs

```bash
# Follow worker logs
docker-compose -f docker-compose.dev.yml logs -f celery-worker

# You should see:
# - "Processing chunk X (pages Y-Z)"
# - "Chunk X processed: N sentences"
# - "Merged M total sentences"
```

### Monitor with Flower

```bash
# Install Flower
docker-compose -f docker-compose.dev.yml exec celery-worker pip install flower

# Start Flower
docker-compose -f docker-compose.dev.yml exec celery-worker \
  celery -A celery_app.celery_app flower --port=5555

# Access at http://localhost:5555
```

## Configuration

### Adjust Processing Settings

Edit `backend/.env`:

```bash
# Process files >100 pages asynchronously (instead of 50)
CHUNKING_THRESHOLD_PAGES=100

# Larger chunks for faster processing (if you have resources)
CHUNK_SIZE_PAGES=100

# More workers for higher throughput
MAX_WORKERS=8
```

Restart services:
```bash
docker-compose -f docker-compose.dev.yml restart
```

## Troubleshooting

### Workers Not Processing Jobs

**Check Redis connection:**
```bash
docker-compose -f docker-compose.dev.yml exec redis redis-cli ping
# Should return "PONG"
```

**Check worker is running:**
```bash
docker-compose -f docker-compose.dev.yml ps celery-worker
# Status should be "Up"
```

**Restart worker:**
```bash
docker-compose -f docker-compose.dev.yml restart celery-worker
```

### Jobs Stuck in "processing"

**Check active tasks:**
```bash
docker-compose -f docker-compose.dev.yml exec celery-worker \
  celery -A celery_app.celery_app inspect active
```

**Cancel stuck job:**
```bash
curl -X POST http://localhost:5000/api/v1/jobs/123/cancel \
  -H "Authorization: Bearer $TOKEN"
```

### High Memory Usage

Reduce resources in `backend/.env`:
```bash
MAX_WORKERS=2              # Fewer workers
CHUNK_SIZE_PAGES=25        # Smaller chunks
WORKER_MEMORY_LIMIT_MB=1024 # Less memory per worker
```

## Next Steps

- **Production Deployment**: See [DEPLOYMENT_ASYNC.md](DEPLOYMENT_ASYNC.md)
- **Architecture Details**: See [ASYNC_PROCESSING.md](ASYNC_PROCESSING.md)
- **Full Documentation**: See [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md)

## Common Use Cases

### Processing Multiple Large Files

```bash
# Submit multiple jobs
for file in *.pdf; do
  curl -X POST http://localhost:5000/api/v1/process-pdf \
    -H "Authorization: Bearer $TOKEN" \
    -F "pdf_file=@$file"
done

# Check all job statuses
curl http://localhost:5000/api/v1/me/jobs \
  -H "Authorization: Bearer $TOKEN"
```

### Custom Processing Settings

```bash
# Process with custom settings
curl -X POST http://localhost:5000/api/v1/process-pdf \
  -H "Authorization: Bearer $TOKEN" \
  -F "pdf_file=@novel.pdf" \
  -F "sentence_length_limit=10" \
  -F "gemini_model=quality" \
  -F "ignore_dialogue=true"
```

## Performance Benchmarks

On a system with:
- 4 CPU cores
- 8GB RAM
- 4 Celery workers

Expected performance:
- 50 pages: 30-60 seconds
- 100 pages: 1-2 minutes
- 200 pages: 3-5 minutes
- 500 pages: 8-15 minutes

## Support

Need help?
1. Check [Troubleshooting](#troubleshooting) section
2. View logs: `docker-compose logs`
3. Review documentation in `docs/`
4. Open GitHub issue

## Clean Up

Stop all services:
```bash
docker-compose -f docker-compose.dev.yml down
```

Remove volumes (⚠️ deletes all data):
```bash
docker-compose -f docker-compose.dev.yml down -v
```

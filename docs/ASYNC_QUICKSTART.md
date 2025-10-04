# Quick Start Guide - Async PDF Processing

## Local Development Setup

### Prerequisites

- Docker & Docker Compose
- Python 3.12+
- Node.js 18+
- Redis (or use Docker)

### 1. Install Dependencies

```bash
# Backend
cd backend
pip install -r requirements.txt

# Frontend
cd frontend
npm install
```

### 2. Start Services with Docker Compose

```bash
# Development mode (with hot reload)
docker-compose -f docker-compose.dev.yml up

# This starts:
# - Backend (Flask) on http://localhost:5000
# - Frontend (Next.js) on http://localhost:3000
# - Redis on localhost:6379
# - Celery Worker(s)
# - Flower (task monitor) on http://localhost:5555
```

### 3. Run Database Migrations

```bash
# In backend container
docker-compose -f docker-compose.dev.yml exec backend flask db upgrade
```

### 4. Verify Services

```bash
# Check all services are running
docker-compose -f docker-compose.dev.yml ps

# Check Celery workers
docker-compose -f docker-compose.dev.yml exec celery-worker celery -A app.celery_app:celery inspect active

# Check Flower UI
open http://localhost:5555
```

---

## Manual Setup (Without Docker)

### 1. Start Redis

```bash
# macOS
brew install redis
brew services start redis

# Ubuntu
sudo apt-get install redis-server
sudo systemctl start redis

# Or use Docker
docker run -d -p 6379:6379 redis:7-alpine
```

### 2. Start Backend

```bash
cd backend

# Install dependencies
pip install -r requirements.txt

# Set environment variables
export FLASK_ENV=development
export SECRET_KEY=dev-secret-key
export DATABASE_URL=sqlite:///app.db
export REDIS_URL=redis://localhost:6379/0
export GEMINI_API_KEY=your-api-key-here

# Run migrations
flask db upgrade

# Start Flask
python run.py
```

### 3. Start Celery Worker

```bash
# In a new terminal
cd backend

# Start worker
celery -A app.celery_app:celery worker --loglevel=info --concurrency=4
```

### 4. Start Flower (Optional)

```bash
# In a new terminal
cd backend

# Start Flower
celery -A app.celery_app:celery flower --port=5555
```

### 5. Start Frontend

```bash
cd frontend

# Set environment variables
export NEXT_PUBLIC_API_BASE_URL=http://localhost:5000/api/v1

# Start Next.js dev server
npm run dev
```

---

## Testing Async Processing

### 1. Create a Job

```bash
# Using curl
curl -X POST http://localhost:5000/api/v1/jobs/confirm \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Sample text for estimation...",
    "page_count": 100,
    "filename": "test.pdf",
    "model": "balanced"
  }'

# Response:
{
  "job_id": 1,
  "estimated_tokens": 5000,
  "estimated_credits": 5,
  "reserved": true
}
```

### 2. Start Async Processing

```bash
curl -X POST http://localhost:5000/api/v1/process-pdf-async \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -F "pdf_file=@/path/to/test.pdf" \
  -F "job_id=1"

# Response:
{
  "job_id": 1,
  "task_id": "job_1_1696378800.123",
  "status": "pending",
  "message": "PDF processing started"
}
```

### 3. Poll Job Status

```bash
curl http://localhost:5000/api/v1/jobs/1 \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"

# Response (in progress):
{
  "id": 1,
  "status": "processing",
  "progress_percent": 45,
  "current_step": "Processing chunk 5/10",
  "total_chunks": 10,
  "processed_chunks": 4,
  ...
}

# Response (completed):
{
  "id": 1,
  "status": "completed",
  "progress_percent": 100,
  "processing_time_seconds": 120,
  "gemini_tokens_used": 50000,
  ...
}
```

### 4. Cancel Job (Optional)

```bash
curl -X POST http://localhost:5000/api/v1/jobs/1/cancel \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"

# Response:
{
  "message": "Job cancelled successfully",
  "job_id": 1,
  "status": "cancelled"
}
```

---

## Frontend Integration Example

### Using React Hooks

```tsx
import { useState } from 'react';
import { useJobPolling } from '@/lib/useJobPolling';
import JobProgressDialog from '@/components/JobProgressDialog';
import { processPdfAsync, confirmJob } from '@/lib/api';

function UploadPage() {
  const [jobId, setJobId] = useState<number | null>(null);
  const [showProgress, setShowProgress] = useState(false);

  const handleUpload = async (file: File) => {
    try {
      // 1. Confirm job and reserve credits
      const confirmation = await confirmJob({
        text: extractedText,
        page_count: pageCount,
        filename: file.name,
        model: 'balanced'
      });

      // 2. Start async processing
      const response = await processPdfAsync({
        job_id: confirmation.job_id,
        pdf_file: file,
        sentence_length_limit: 8,
        gemini_model: 'balanced'
      });

      // 3. Show progress dialog
      setJobId(response.job_id);
      setShowProgress(true);
    } catch (error) {
      console.error('Upload failed:', error);
    }
  };

  const handleComplete = (job) => {
    console.log('Job completed!', job);
    setShowProgress(false);
    // Navigate to results page or show success message
  };

  return (
    <>
      <input
        type="file"
        accept=".pdf"
        onChange={(e) => e.target.files?.[0] && handleUpload(e.target.files[0])}
      />

      <JobProgressDialog
        jobId={jobId}
        open={showProgress}
        onClose={() => setShowProgress(false)}
        onComplete={handleComplete}
      />
    </>
  );
}
```

---

## Monitoring & Debugging

### View Flower Dashboard

```bash
open http://localhost:5555

# Login (production only):
# Username: admin (from FLOWER_USER env var)
# Password: admin (from FLOWER_PASSWORD env var)
```

### Check Worker Status

```bash
# List active tasks
celery -A app.celery_app:celery inspect active

# List registered tasks
celery -A app.celery_app:celery inspect registered

# Ping workers
celery -A app.celery_app:celery inspect ping
```

### View Logs

```bash
# Docker Compose
docker-compose logs -f celery-worker
docker-compose logs -f backend

# Manual setup
# Worker logs in terminal where worker is running
# Backend logs in Flask terminal
```

### Check Redis

```bash
# Connect to Redis CLI
redis-cli

# Check keys
> KEYS *

# Get queue length
> LLEN celery

# Monitor commands
> MONITOR
```

---

## Common Issues

### Workers not picking up tasks

**Symptom**: Tasks stay in pending state

**Solution**:
```bash
# 1. Check Redis is running
redis-cli ping
# Should return: PONG

# 2. Check worker is running
docker-compose ps celery-worker

# 3. Check worker logs
docker-compose logs celery-worker

# 4. Restart worker
docker-compose restart celery-worker
```

### Import errors in tasks.py

**Symptom**: `ImportError` or circular import

**Solution**: Tasks use deferred imports to avoid circular dependencies. Imports are done inside task functions.

### Database locked errors (SQLite)

**Symptom**: `database is locked` errors

**Solution**:
```bash
# Use PostgreSQL for production/heavy testing
export DATABASE_URL=postgresql://user:pass@localhost/dbname

# Or reduce worker concurrency for SQLite
celery -A app.celery_app:celery worker --concurrency=1
```

### High memory usage

**Symptom**: Worker memory growing over time

**Solution**:
```bash
# Restart worker after N tasks
celery -A app.celery_app:celery worker --max-tasks-per-child=50

# Reduce concurrency
celery -A app.celery_app:celery worker --concurrency=2
```

---

## Testing

### Run Backend Tests

```bash
cd backend

# All tests
pytest

# Async processing tests only
pytest tests/test_async_processing.py -v

# With coverage
pytest --cov=app --cov-report=html
```

### Run Frontend Tests

```bash
cd frontend

# Lint
npm run lint

# Type check
npm run type-check
```

---

## Environment Variables Reference

### Backend

```bash
# Core
FLASK_ENV=development
SECRET_KEY=your-secret-key

# Database
DATABASE_URL=sqlite:///app.db  # or PostgreSQL URL

# Redis & Celery
REDIS_URL=redis://localhost:6379/0

# Gemini API
GEMINI_API_KEY=your-api-key
GEMINI_MODEL=gemini-2.5-flash

# Google OAuth (optional for local dev)
GOOGLE_CLIENT_ID=your-client-id
GOOGLE_CLIENT_SECRET=your-client-secret

# Feature Flags
ASYNC_PROCESSING_ENABLED=true
RATELIMIT_ENABLED=false  # Disable for local dev
```

### Frontend

```bash
# API
NEXT_PUBLIC_API_BASE_URL=http://localhost:5000/api/v1

# Google OAuth (optional)
NEXT_PUBLIC_GOOGLE_CLIENT_ID=your-client-id
```

---

## Next Steps

1. **Read the full documentation**: [ASYNC_PDF_PROCESSING.md](./ASYNC_PDF_PROCESSING.md)
2. **Review the rollout plan**: [ASYNC_ROLLOUT_PLAN.md](./ASYNC_ROLLOUT_PLAN.md)
3. **Check the roadmap**: [6-async-pdf-processing-roadmap.md](./roadmaps/6-async-pdf-processing-roadmap.md)

---

## Support

- **GitHub Issues**: https://github.com/haytham10/FrenchNovelTool/issues
- **Documentation**: `/docs` directory
- **Flower UI**: http://localhost:5555

---

**Happy Coding! 🚀**

# Performance Optimizations for 8GB RAM / 8 vCPU Railway Infrastructure

## Overview
Optimized French Novel Tool for **full throttle performance** on upgraded Railway infrastructure (8GB RAM / 8 vCPU per service).

## Changes Applied

### 1. Celery Worker Configuration (`railway-worker-entrypoint.sh`)
**Before:**
- Concurrency: 4 workers
- Max tasks per child: 50
- Task time limit: 30 minutes
- Prefetch multiplier: 1 (default)

**After:**
- **Concurrency: 8 workers** (fully utilizing 8 vCPU)
- **Max tasks per child: 100** (less recycling overhead)
- **Max memory per child: 900MB** (8GB / 8 workers with headroom)
- **Task time limit: 60 minutes** (handle large PDFs)
- **Prefetch multiplier: 2** (better throughput)

### 2. Celery Configuration (`backend/app/celery_app.py`)
**Before:**
- Result expiration: 1 hour
- Task time limit: 30 minutes
- Max tasks per child: 50
- Prefetch multiplier: 1

**After:**
- **Result expiration: 2 hours** (more time for complex jobs)
- **Task time limit: 60 minutes**
- **Max tasks per child: 100**
- **Prefetch multiplier: 2**
- **Worker max memory: 900MB per worker**

### 3. Task Retry & Timeout Configuration (`backend/config.py`)
**Before:**
- Chunk task retries: 2
- Chunk retry delay: 5 seconds
- Chunk watchdog: 5 minutes
- Chunk stuck threshold: 6 minutes
- Finalize retries: 5
- Gemini timeout: 3 minutes

**After:**
- **Chunk task retries: 4** (more resilience)
- **Chunk retry delay: 3 seconds** (faster recovery)
- **Chunk watchdog: 10 minutes** (handle large chunks)
- **Chunk stuck threshold: 12 minutes**
- **Finalize retries: 10** (handle complex jobs)
- **Gemini timeout: 5 minutes** (process larger texts)

### 4. Database Connection Pool (`backend/config.py`)
**Before:**
- Pool size: 10 connections
- Max overflow: 5
- Pool recycle: 1 hour
- Statement timeout: 30 seconds

**After:**
- **Pool size: 20 connections** (support 8 concurrent workers)
- **Max overflow: 10** (better burst capacity)
- **Pool recycle: 30 minutes** (fresher connections)
- **Statement timeout: 60 seconds** (large operations)

### 5. PDF Chunking Strategy (`backend/app/services/chunking_service.py`)
**Before:**
```python
CHUNK_SIZES = {
    'small': {'max_pages': 30, 'chunk_size': 30, 'parallel': 1},
    'medium': {'max_pages': 100, 'chunk_size': 20, 'parallel': 3},
    'large': {'max_pages': 500, 'chunk_size': 15, 'parallel': 5},
}
OVERLAP_PAGES = 1
```

**After:**
```python
CHUNK_SIZES = {
    'small': {'max_pages': 50, 'chunk_size': 50, 'parallel': 2},
    'medium': {'max_pages': 200, 'chunk_size': 40, 'parallel': 6},
    'large': {'max_pages': 1000, 'chunk_size': 30, 'parallel': 8},
}
OVERLAP_PAGES = 2  # Better context continuity
```

### 6. Redis Configuration (`docker-compose.yml`)
**Before:**
- Max memory: 256MB

**After:**
- **Max memory: 2GB** (handle larger job queues)

### 7. Docker Compose Worker Settings
**Added environment variables:**
```yaml
- PRELOAD_SPACY=true              # Memory sharing across workers
- WORKER_MAX_MEMORY_MB=900        # Per-worker memory cap
- CELERY_CONCURRENCY=8            # 8 concurrent workers
- DB_POOL_SIZE=20                 # Larger connection pool
- DB_MAX_OVERFLOW=10              # More burst capacity
```

## Performance Improvements

### Throughput
- **8x concurrent workers** vs 4 (200% increase)
- **Larger chunks** (30-50 pages vs 15-30) = fewer API calls
- **Prefetch multiplier 2** = workers always have tasks ready

### Memory Efficiency
- **spaCy preloading** enabled for copy-on-write memory sharing
- **900MB per worker** with automatic recycling after 100 tasks
- **2GB Redis** for large job queues and result caching

### Reliability
- **4 retry attempts** vs 2 for transient failures
- **10 finalize retries** vs 5 for complex jobs
- **12-minute stuck threshold** vs 6 minutes for large chunks

### Database Performance
- **20 connection pool** vs 10 (supports 8 workers + API server)
- **60-second statement timeout** vs 30s for large coverage builds
- **30-minute connection recycle** vs 1 hour for freshness

## Expected Capacity

### PDF Processing
- **Small PDFs (< 50 pages):** Process in ~30 seconds with 50-page chunks
- **Medium PDFs (50-200 pages):** Process in 2-3 minutes with 40-page chunks and 6-way parallelism
- **Large PDFs (200-1000 pages):** Process in 5-10 minutes with 30-page chunks and 8-way parallelism

### Coverage Analysis
- **Can handle 20,000+ sentence corpora** with improved memory management
- **8 concurrent coverage builds** vs previous 2-4

### Concurrent Jobs
- **Up to 8 simultaneous users** processing PDFs in parallel
- **Each worker handles 100 tasks** before recycling (prevents memory leaks)

## Environment Variables for Railway

Add these to your Railway worker service:

```bash
# Worker Configuration
CELERY_CONCURRENCY=8
WORKER_MAX_MEMORY_MB=900

# Database
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=10
DB_POOL_RECYCLE=1800

# Task Timeouts
CHUNK_TASK_MAX_RETRIES=4
CHUNK_WATCHDOG_SECONDS=600
CHUNK_STUCK_THRESHOLD_SECONDS=720
FINALIZE_MAX_RETRIES=10
GEMINI_CALL_TIMEOUT_SECONDS=300

# Performance
PRELOAD_SPACY=true
```

## Monitoring Recommendations

1. **Railway Metrics Dashboard:**
   - Watch memory usage per worker (should stay ~700-900MB)
   - Monitor CPU usage (should utilize all 8 vCPUs)
   - Track active connections to Redis and Postgres

2. **Celery Flower:**
   - Monitor task throughput (tasks/minute)
   - Watch for worker recycling (every 100 tasks)
   - Check for stuck tasks (> 12 minutes)

3. **Database Connections:**
   - Monitor active connections (should be < 20 per worker service)
   - Watch for connection pool exhaustion warnings

## Rollback Instructions

If you need to revert to conservative settings:

```bash
# In railway-worker-entrypoint.sh or environment
CELERY_CONCURRENCY=4
WORKER_MAX_MEMORY_MB=512
DB_POOL_SIZE=10
CHUNK_TASK_MAX_RETRIES=2
```

## Next Steps

1. **Deploy to Railway** and monitor initial performance
2. **Test with large PDFs** (500+ pages) to validate chunking strategy
3. **Monitor memory usage** - adjust WORKER_MAX_MEMORY_MB if needed
4. **Fine-tune if needed:**
   - Increase/decrease concurrency based on actual CPU usage
   - Adjust chunk sizes if Gemini rate limits are hit
   - Tune DB pool size based on connection metrics

## Notes

- All changes are **backward compatible** - old jobs will continue to work
- **spaCy preloading** significantly reduces memory footprint for coverage analysis
- **Larger chunks** mean fewer Gemini API calls = lower costs
- **Aggressive timeouts** ensure stuck jobs don't block the queue

---

**Optimized on:** October 9, 2025
**Target Infrastructure:** Railway 8GB RAM / 8 vCPU per service

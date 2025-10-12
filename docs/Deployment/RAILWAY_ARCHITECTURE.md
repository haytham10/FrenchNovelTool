# Railway Deployment Architecture

## System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                        Railway Project                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌────────────────┐         ┌────────────────┐                  │
│  │  Backend API   │         │ Celery Worker  │                  │
│  │  (Flask)       │         │                │                  │
│  ├────────────────┤         ├────────────────┤                  │
│  │ - Gunicorn     │         │ - Celery       │                  │
│  │ - 4 workers    │         │ - 2 workers    │                  │
│  │ - Port 8000    │         │ - Background   │                  │
│  │ - Health check │         │ - Task exec    │                  │
│  └────────┬───────┘         └────────┬───────┘                  │
│           │                          │                           │
│           │    ┌─────────────────────┴────────┐                 │
│           │    │                               │                 │
│           │    ▼                               ▼                 │
│           │  ┌────────────────┐     ┌────────────────┐          │
│           │  │ Redis          │     │ Redis          │          │
│           │  │ (Message Queue)│     │ (Result Store) │          │
│           │  └────────────────┘     └────────────────┘          │
│           │                                                      │
│           ▼                                                      │
│  ┌──────────────────────────────────────────────────┐           │
│  │         Supabase PostgreSQL Database             │           │
│  │  - Connection pooling (10 connections)           │           │
│  │  - SSL/TLS enabled                               │           │
│  │  - Auto-reconnect on failures                    │           │
│  └──────────────────────────────────────────────────┘           │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘

        ▲                                    ▲
        │                                    │
        │ HTTP/HTTPS                        │ PostgreSQL (SSL)
        │                                    │
┌───────┴────────┐                  ┌────────┴─────────┐
│   Frontend     │                  │    Supabase      │
│  (Vercel/etc)  │                  │   (External)     │
└────────────────┘                  └──────────────────┘
```

## Data Flow

### Async PDF Processing Flow

```
1. Frontend → Backend API
   POST /api/v1/process-pdf-async
   ├─ File uploaded
   ├─ Job created in database
   └─ Returns: { job_id: 123, status: "pending" }

2. Backend API → Celery Worker
   ├─ Task queued in Redis
   ├─ Worker picks up task
   └─ Processing starts

3. Celery Worker → Database
   ├─ Updates job.status = "processing"
   ├─ Updates job.progress_percent (0-100)
   ├─ Updates job.current_step ("Processing chunk 5/10")
   └─ Safe commits with retry logic

4. Frontend → Backend API (polling)
   GET /api/v1/jobs/123
   └─ Returns: { status: "processing", progress: 45, ... }

5. Worker completes → Database
   ├─ Updates job.status = "completed"
   ├─ Stores results in job.chunk_results
   └─ Commits changes

6. Frontend polls again
   GET /api/v1/jobs/123
   └─ Returns: { status: "completed", sentences: [...] }
```

## Connection Pooling Strategy

```
┌─────────────────────────────────────────────────────────┐
│ Supabase PostgreSQL (Cloud)                             │
│  Max connections: 100 (Free tier)                       │
└─────────────────────────────────────────────────────────┘
                    ▲
                    │
        ┌───────────┼───────────┐
        │           │           │
        ▼           ▼           ▼
    ┌──────┐   ┌──────┐   ┌──────┐
    │ API  │   │ API  │   │Worker│
    │ (10) │   │ (10) │   │ (10) │
    └──────┘   └──────┘   └──────┘
    
Total: 30 connections for 2 API + 1 Worker
Leaves 70 connections for scaling

Pool Settings per Container:
- pool_size: 10 (base connections)
- max_overflow: 5 (burst to 15)
- pool_recycle: 3600 (recycle hourly)
- pool_pre_ping: true (test before use)
```

## Redis Architecture

```
┌────────────────────────────────────────┐
│   Railway Managed Redis                │
│   (In-memory, Persistent)              │
├────────────────────────────────────────┤
│                                        │
│  Database 0: Celery Broker (tasks)    │
│  ├─ Queued tasks                       │
│  ├─ Task metadata                      │
│  └─ Worker heartbeats                  │
│                                        │
│  Database 0: Celery Results           │
│  ├─ Task results (1 hour TTL)         │
│  ├─ Progress updates                   │
│  └─ Task status                        │
│                                        │
│  (Same Redis, different purposes)      │
│                                        │
└────────────────────────────────────────┘
```

## Health Check Flow

```
Load Balancer → /api/v1/health
                    │
                    ├─ Check Database
                    │  ├─ Execute: SELECT 1
                    │  ├─ Timeout: 5 seconds
                    │  └─ Result: ok / error
                    │
                    ├─ Check Redis
                    │  ├─ Execute: PING
                    │  ├─ Timeout: 5 seconds
                    │  └─ Result: ok / error
                    │
                    └─ Return Status
                       ├─ 200 if all healthy
                       ├─ 503 if any unhealthy
                       └─ JSON with details
```

## Error Handling & Retry Strategy

```
Database Commit Attempt
    ├─ Try 1: Immediate
    │  └─ Network error → Retry
    ├─ Try 2: Wait 1 second
    │  └─ Network error → Retry
    ├─ Try 3: Wait 2 seconds
    │  └─ Success or final failure
    └─ Rollback on failure

Celery Task Execution
    ├─ Soft time limit: 25 minutes
    ├─ Hard time limit: 30 minutes
    ├─ Max retries: 3
    └─ Retry delay: Exponential backoff

Connection Pool Behavior
    ├─ Pre-ping before use
    ├─ Auto-reconnect on failure
    ├─ Recycle connections hourly
    └─ Max burst: pool_size + max_overflow
```

## Deployment Sequence

```
Step 1: Create Railway Project
    └─ Connect GitHub repo

Step 2: Deploy Backend
    ├─ Dockerfile.web detected
    ├─ Environment variables set
    └─ Health check: /api/v1/health

Step 3: Add Redis
    ├─ Railway dashboard → Add Redis
    └─ REDIS_URL auto-injected

Step 4: Run Migrations
    ├─ railway run flask db upgrade
    └─ railway run python verify_migrations.py

Step 5: Deploy Worker
    ├─ New service → Dockerfile.railway-worker
    ├─ Copy all env vars from backend
    └─ Worker starts processing tasks

Step 6: Verify
    ├─ Check health endpoint
    ├─ Test async upload
    └─ Monitor logs
```

## Monitoring Points

```
┌─────────────────────────────────────────┐
│ Key Metrics to Monitor                  │
├─────────────────────────────────────────┤
│                                         │
│ Backend API:                            │
│  ├─ Request rate (requests/sec)        │
│  ├─ Response time (p50, p95, p99)      │
│  ├─ Error rate (4xx, 5xx)              │
│  └─ Database pool usage                │
│                                         │
│ Celery Worker:                          │
│  ├─ Tasks processed/sec                │
│  ├─ Active tasks                       │
│  ├─ Failed tasks                       │
│  └─ Memory usage                       │
│                                         │
│ Database:                               │
│  ├─ Active connections                 │
│  ├─ Query time                         │
│  └─ Lock wait time                     │
│                                         │
│ Redis:                                  │
│  ├─ Queue length                       │
│  ├─ Memory usage                       │
│  └─ Hit rate                           │
│                                         │
└─────────────────────────────────────────┘
```

## Scaling Strategies

### Horizontal Scaling (Recommended)

```
Single Worker (Current)
    └─ 2 concurrent tasks

Scale to 3 Workers
    ├─ Worker 1: 2 concurrent
    ├─ Worker 2: 2 concurrent
    └─ Worker 3: 2 concurrent
    = 6 concurrent tasks

Adjust DB Pool:
    pool_size = workers × concurrency × 2
    = 3 × 2 × 2 = 12
```

### Vertical Scaling

```
Railway Plan         CPU    Memory   Connections
─────────────────────────────────────────────────
Starter (Free)       1      512MB    pool_size: 5
Hobby ($5)           2      1GB      pool_size: 10
Pro ($20)            4      4GB      pool_size: 20
```

## Security Configuration

```
┌───────────────────────────────────────┐
│ Security Layers                       │
├───────────────────────────────────────┤
│                                       │
│ 1. HTTPS/TLS (Railway)                │
│    └─ Auto-managed certificates       │
│                                       │
│ 2. Database SSL (Supabase)            │
│    ├─ sslmode=require                 │
│    └─ Auto-added by config.py         │
│                                       │
│ 3. Redis TLS (Optional)               │
│    ├─ rediss:// protocol              │
│    └─ Set REDIS_TLS=true if needed    │
│                                       │
│ 4. JWT Authentication                 │
│    ├─ Access token: 1 hour            │
│    └─ Refresh token: 30 days          │
│                                       │
│ 5. Rate Limiting                      │
│    ├─ 10 uploads/hour per user        │
│    └─ Redis-backed counters           │
│                                       │
└───────────────────────────────────────┘
```

## File Locations Reference

```
Backend Configuration:
├─ config.py                  → Connection pools, Redis SSL
├─ app/__init__.py            → Flask app factory
├─ app/routes.py              → API endpoints + health check
├─ app/tasks.py               → Celery tasks + safe commits
└─ celery_worker.py           → Worker entrypoint

Docker:
├─ Dockerfile.web             → Backend API image
├─ Dockerfile.railway-worker  → Worker image (Railway-optimized)
├─ railway-worker-entrypoint.sh → Worker startup script
└─ railway.json / railway.worker.json → Railway configs

Database:
├─ migrations/                → Alembic migrations
├─ fix_jobs_table.sql         → Manual schema fix
└─ verify_migrations.py       → Schema verification tool

Documentation:
├─ docs/Deployment/RAILWAY_DEPLOYMENT.md → Full guide
├─ docs/Deployment/RAILWAY_QUICK_CHECKLIST.md → Quick ref
└─ DEPLOYMENT_FIXES_README.md → Summary

Troubleshooting:
└─ troubleshoot.py            → Automated diagnostics
```

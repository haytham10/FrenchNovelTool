# Debugging Stuck Progress Bar at 15%

## Current Situation

- Frontend shows 15% progress and "Real-time updates active"
- WebSocket is connected and user joined room `job_74`
- Job was created and async processing started
- **But**: No Celery worker logs are visible in your output

## Key Issue

You're looking at the **backend API (web server) logs**, but the actual PDF processing happens in the **Celery worker service** which runs separately on Railway. We need to check the worker logs.

## Step-by-Step Debugging

### Step 1: Check Railway Worker Logs

The Celery worker is a **separate Railway service**. You need to view its logs:

```bash
# List your Railway services
railway service

# Find the worker service (should be named something like "celery-worker" or "worker")
# Then view its logs:
railway logs --service=<worker-service-name>

# Or if you know the service ID:
railway logs --service=586db72f-fbda-4f21-9e7e-27b0678c7867
```

Look for:
- `Task app.tasks.process_pdf_async[job_74_...]` received
- `[EMIT_PROGRESS]` log messages
- Any errors or exceptions

### Step 2: Run Debug Script on Railway

SSH into your Railway backend service and run the debug script:

```bash
# SSH into backend service (where you can access the database)
railway ssh --project=74c8a7e1-9d75-4544-a7d1-e2bfd3056495 \
  --environment=6fb72cc1-f69f-4c15-8536-0f80f66a513e

# Once inside:
cd /app
python debug_stuck_job.py 74
```

This will show:
- Current job status in database
- Whether chunks were created
- If chunks are stuck in processing
- Celery task state

### Step 3: Check if Celery Workers Are Running

```bash
# SSH into worker service
railway ssh --service=<worker-service-id>

# Check if Celery process is running
ps aux | grep celery

# Check Celery inspect
celery -A celery_worker.celery inspect active
celery -A celery_worker.celery inspect registered
```

## Common Causes of 15% Stuck

Based on the code, 15% means:
1. ✅ Job was created
2. ✅ PDF was uploaded
3. ✅ Chunking completed
4. ❌ **Processing hasn't started**

Possible reasons:

### Cause 1: Celery Worker Not Running
**Symptoms:** No task logs at all
**Fix:** Restart the worker service on Railway

### Cause 2: Celery Task Not Picked Up
**Symptoms:** Task shows as PENDING in Celery
**Fix:** Check Redis connection, verify worker is connected to same Redis

### Cause 3: Task Started but Errored Immediately
**Symptoms:** Worker logs show errors
**Fix:** Check the specific error in worker logs

### Cause 4: Database Connection Issue
**Symptoms:** Worker can't read job/chunks from database
**Fix:** Check DATABASE_URL in worker environment

### Cause 5: Socket.IO Emissions Failing Silently
**Symptoms:** Task is running but no progress updates
**Fix:** Our logging changes should now show this - check for `[EMIT_PROGRESS]` logs

## What the Debug Script Will Tell You

```
📋 JOB STATUS:
  Status: processing
  Progress: 15%
  Current Step: Processing 
  Celery Task ID: <task-id>
  
📦 CHUNKS (1 total):
  Chunk 0:
    Status: pending | processing | success | failed
    Celery Task ID: <chunk-task-id>
    Last Error: <if any>
    
🔍 CELERY TASK STATUS:
  State: PENDING | STARTED | SUCCESS | FAILURE
  Ready: True/False
```

## Next Steps Based on Debug Output

### If job status is "pending":
→ Celery task never started - worker issue

### If job status is "processing" but no chunks:
→ Chunking failed - check for errors in process_pdf_async task

### If chunks exist but status is "pending":
→ process_chunk task not dispatched - check chord/task creation

### If chunks status is "processing" for >5 minutes:
→ Gemini API call stuck or failed - check worker logs for timeout

### If chunks status is "failed":
→ Check chunk.last_error for details

## Quick Fix to Try

If you can't access Railway logs easily, try re-running the job:

1. Cancel the stuck job (if there's a cancel button)
2. Upload the PDF again
3. Watch both:
   - Frontend browser console for WebSocket events
   - Railway worker logs for task execution

## Files to Help Debug

1. `debug_stuck_job.py` - Run on Railway to check database state
2. `test_socketio_emission.py` - Test Socket.IO emissions manually
3. `frontend/test-websocket.js` - Test frontend WebSocket in browser

## Railway Services to Check

1. **Backend API** (port 5000) - Handles HTTP requests, WebSocket connections
2. **Celery Worker** - Processes PDF tasks (this is where processing happens!)
3. **Flower** - Celery monitoring dashboard (if deployed)
4. **Redis** - Message broker for both Celery and Socket.IO
5. **PostgreSQL** - Database

Make sure all 5 services are running and healthy!

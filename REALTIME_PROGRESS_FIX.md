# Real-Time Progress Bar Not Updating - Diagnosis and Fix

## Problem
The progress bar on the frontend is not updating in real-time during PDF processing. The job completes successfully, but progress updates are not visible until completion.

## Root Cause Analysis

Looking at the logs provided:
1. ✅ PDF processing is working correctly
2. ✅ Gemini API calls are being made successfully
3. ✅ Chunks are being processed
4. ❌ **No Socket.IO emission logs visible**

The issue is that Socket.IO progress emissions from Celery workers were not being logged, making it impossible to diagnose whether emissions are happening or failing silently.

## Changes Made

### 1. Enhanced Logging in `socket_events.py`

**Changed:**
```python
# Before (DEBUG level - not visible in production logs)
logger.debug(f'Emitted job_progress for job {job_id}: {job.progress_percent}% - {job.current_step}')

# After (INFO level with more context)
logger.info(f'Emitting job_progress to room={room}: progress={job.progress_percent}%, step={job.current_step}, status={job.status}')
socketio.emit('job_progress', job.to_dict(), room=room, namespace='/')
logger.info(f'Successfully emitted job_progress for job {job_id}')
```

**Why:** DEBUG logs are not shown in production (Railway). Changing to INFO level makes emissions visible in logs.

### 2. Enhanced Error Handling in `socket_events.py`

**Changed:**
```python
# Before
except Exception as e:
    logger.error(f'Error emitting job progress for job {job_id}: {e}')

# After
except Exception as e:
    logger.error(f'Error emitting job progress for job {job_id}: {e}', exc_info=True)
```

**Why:** `exc_info=True` adds full stack trace to error logs, making debugging easier.

### 3. Enhanced Logging in `tasks.py`

**Changed:**
```python
# Before
def emit_progress(job_id: int):
    try:
        from app.socket_events import emit_job_progress
        emit_job_progress(job_id)
    except Exception as e:
        logger.warning(f"Failed to emit WebSocket progress for job {job_id}: {e}")

# After
def emit_progress(job_id: int):
    try:
        logger.info(f"[EMIT_PROGRESS] Starting emission for job {job_id}")
        from app.socket_events import emit_job_progress
        emit_job_progress(job_id)
        logger.info(f"[EMIT_PROGRESS] Completed emission for job {job_id}")
    except Exception as e:
        logger.error(f"[EMIT_PROGRESS] Failed to emit WebSocket progress for job {job_id}: {e}", exc_info=True)
```

**Why:** Track the entire emission lifecycle to diagnose failures.

## What to Look For in New Logs

When you run a new test, you should now see logs like:

```
[EMIT_PROGRESS] Starting emission for job 73
Emitting job_progress to room=job_73: progress=25%, step=Processing chunks (1/4), status=processing
Successfully emitted job_progress for job 73
[EMIT_PROGRESS] Completed emission for job 73
```

If you **don't** see these logs, it means `emit_progress()` is not being called at all (logic issue).

If you see errors like:
```
[EMIT_PROGRESS] Failed to emit WebSocket progress for job 73: [error details]
Error emitting job progress for job 73: [error details with stack trace]
```

Then we have an emission failure (Socket.IO/Redis issue).

## Potential Issues to Investigate

### 1. Socket.IO + Redis Message Queue
Socket.IO is configured with Redis as message queue:
```python
socketio.init_app(
    app,
    cors_allowed_origins=origins,
    message_queue=app.config.get('CELERY_BROKER_URL'),  # Redis URL
    async_mode='eventlet'
)
```

**Verify:**
- Redis is accessible from Celery workers
- `eventlet` is installed (`requirements.txt` line 23: ✅)
- Socket.IO can emit through Redis message queue

### 2. Frontend WebSocket Connection

The frontend connects to Socket.IO and joins the job room:
```typescript
socket.emit('join_job', { job_id: jobId, token });
socket.on('job_progress', handleJobProgress);
```

**Verify:**
- Frontend successfully connects to WebSocket
- Frontend successfully joins job room
- Frontend is listening for `job_progress` events

### 3. Namespace Mismatch

Socket.IO uses namespaces. The backend emits to `namespace='/'` (default), and the frontend connects to the default namespace.

**Current setup:**
```python
# Backend
socketio.emit('job_progress', job.to_dict(), room=room, namespace='/')

# Frontend
const socket: Socket = io(process.env.NEXT_PUBLIC_API_URL, {
  path: '/socket.io/',  // Default namespace
  // ...
});
```

This should work, but verify no namespace configuration mismatch.

## Next Steps

### 1. Deploy and Test
Deploy the changes to Railway and run a small PDF test.

### 2. Check Logs
Look for the new `[EMIT_PROGRESS]` logs:

```bash
# SSH into Railway worker service
railway ssh --project=74c8a7e1-9d75-4544-a7d1-e2bfd3056495 \
  --environment=6fb72cc1-f69f-4c15-8536-0f80f66a513e \
  --service=586db72f-fbda-4f21-9e7e-27b0678c7867

# Follow logs
tail -f /app/logs/app.log
# Or if using Railway's log viewer, just watch the service logs
```

### 3. Check Frontend Browser Console
Open browser DevTools and check:
```javascript
// Should see WebSocket connection logs
// Look for 'job_progress' events being received
```

### 4. Verify Redis Connection
Ensure Celery workers can communicate with Redis:

```bash
# In Railway worker SSH
python3 -c "
import os
from app import create_app
app = create_app()
with app.app_context():
    from app import socketio
    print('Socket.IO message queue:', socketio.server.manager_class)
    print('Redis URL:', app.config.get('CELERY_BROKER_URL'))
"
```

## Possible Root Causes and Solutions

### If logs show emissions but frontend doesn't receive them:

**Cause:** Socket.IO message queue not working (Redis communication issue)

**Solution:**
1. Verify Redis is accessible from both web server and Celery workers
2. Check Railway network configuration
3. Ensure `eventlet` workers are used for the web server:
   ```bash
   # In Dockerfile.web CMD or railway.json
   gunicorn --worker-class eventlet -w 1 --bind 0.0.0.0:${PORT:-5000} run:app
   ```

### If logs show no emissions:

**Cause:** `emit_progress()` not being called or failing silently

**Solution:**
1. Check the logic in `process_chunk` task around line 393
2. Ensure `safe_db_commit()` is succeeding
3. Verify the SQL update is working:
   ```python
   db.session.execute(text("UPDATE jobs SET processed_chunks = COALESCE(processed_chunks,0) + 1 WHERE id = :id"), {"id": job_id})
   ```

### If logs show errors:

**Cause:** Database query failing, Socket.IO not initialized, or Redis connection issue

**Solution:** Fix based on the specific error message (now visible with `exc_info=True`)

## Files Modified

1. `backend/app/socket_events.py` - Enhanced logging and error handling
2. `backend/app/tasks.py` - Enhanced logging in `emit_progress()`

## Deployment Command

```bash
# From backend directory
git add app/socket_events.py app/tasks.py
git commit -m "fix: enhance Socket.IO emission logging for real-time progress debugging"
git push origin normalizer-optimization

# Railway will auto-deploy
```

## Testing Checklist

- [ ] Deploy changes to Railway
- [ ] Run a small PDF test (15 pages)
- [ ] Check Railway worker logs for `[EMIT_PROGRESS]` messages
- [ ] Check Railway worker logs for Socket.IO emission logs
- [ ] Check browser console for WebSocket connection
- [ ] Check browser console for `job_progress` events
- [ ] Verify progress bar updates in real-time
- [ ] If still not working, collect new logs and diagnose further

---

**Status:** Changes committed and ready for deployment. Next: Deploy to Railway and collect new diagnostic logs.

# WebSocket Progress Updates - Comprehensive Fix

## Current Situation (Oct 11, 2025 11:07 AM)

After deploying enhanced logging:
- ✅ WebSocket connects successfully
- ✅ User joins job room
- ❌ Progress bar completely missing from UI
- ❌ Shows "Processing PDF in background..." with no percentage
- ❌ No `[EMIT_PROGRESS]` logs in worker (code not deployed to worker yet)

## Root Causes Identified

### 1. Worker Service Not Redeployed
Railway has **3 separate services**:
- **Backend API** (`Dockerfile.web`) - ✅ Redeployed with new logs
- **Celery Worker** (`Dockerfile.railway-worker`) - ❌ **Still running old code**
- **Flower** (`Dockerfile.flower`) - Not critical

The worker logs show NO `[EMIT_PROGRESS]` prefix, proving the new code isn't deployed there.

### 2. Initial Job State Not Displayed
The frontend receives the initial `job_progress` event when joining the room, but if `progress_percent` is 0 or null, the UI shows no progress.

## Fix Applied

### Enhanced Logging in `handle_join_job`

Added `[JOIN_JOB]` prefix to all logs in the join handler to track:
- When join request received
- User authentication
- Initial job state being sent
- The actual progress values being sent

Now you'll see:
```
[JOIN_JOB] Received join request for job 75
[JOIN_JOB] User 2 joined room job_75
[JOIN_JOB] Sending initial state for job 75: status=processing, progress=15%, step=Processing chunks
[JOIN_JOB] Initial state sent for job 75
```

## Action Plan

### Step 1: Commit New Changes
```bash
cd H:\WORK\TIRED
git add backend/app/socket_events.py
git commit -m "feat: add detailed JOIN_JOB logging for WebSocket debugging"
git push origin normalizer-optimization
```

### Step 2: Force Redeploy ALL Services

Railway might only redeploy the service linked to GitHub. You need to manually trigger worker redeploy:

**Option A: Railway Dashboard**
1. Go to Railway dashboard
2. Find the "Celery Worker" service
3. Click "Deploy" → "Redeploy"

**Option B: Railway CLI**
```bash
# List services to find worker service name/ID
railway service

# Redeploy worker specifically
railway redeploy --service=<worker-service-name-or-id>
```

### Step 3: Verify Worker Has New Code

After redeployment:
```bash
# SSH into worker
railway ssh --service=<worker-service-id>

# Check if new code exists
grep -A 2 "\[EMIT_PROGRESS\]" /app/app/tasks.py
# Should show:
# logger.info(f"[EMIT_PROGRESS] Starting emission for job {job_id}")

grep -A 2 "\[JOIN_JOB\]" /app/app/socket_events.py
# Should show the new logging

# Exit SSH
exit
```

### Step 4: Test with Small PDF

1. Upload a small PDF (15 pages)
2. Watch **Backend API logs** for `[JOIN_JOB]` messages
3. Watch **Worker logs** for `[EMIT_PROGRESS]` messages

### Expected Logs After Full Deployment

**Backend API Service:**
```
[2025-10-11 11:XX:XX] INFO in socket_events: WebSocket connected: user_id=2
[2025-10-11 11:XX:XX] INFO in socket_events: [JOIN_JOB] Received join request for job 75
[2025-10-11 11:XX:XX] INFO in socket_events: [JOIN_JOB] User 2 joined room job_75
[2025-10-11 11:XX:XX] INFO in socket_events: [JOIN_JOB] Sending initial state for job 75: status=processing, progress=15%, step=Analyzing PDF
[2025-10-11 11:XX:XX] INFO in socket_events: [JOIN_JOB] Initial state sent for job 75
```

**Celery Worker Service:**
```
[2025-10-11 11:XX:XX] INFO in tasks: Job 75: created 1 JobChunk rows in DB
[2025-10-11 11:XX:XX] INFO in tasks: Job 75: processing single chunk
[2025-10-11 11:XX:XX] INFO in tasks: [EMIT_PROGRESS] Starting emission for job 75
[2025-10-11 11:XX:XX] INFO in socket_events: Emitting job_progress to room=job_75: progress=25%, step=Processing chunks (1/1), status=processing
[2025-10-11 11:XX:XX] INFO in socket_events: Successfully emitted job_progress for job 75
[2025-10-11 11:XX:XX] INFO in tasks: [EMIT_PROGRESS] Completed emission for job 75
```

## Troubleshooting Matrix

| Symptoms | Cause | Solution |
|----------|-------|----------|
| No `[EMIT_PROGRESS]` logs | Worker not redeployed | Manually redeploy worker service |
| `[JOIN_JOB]` logs but progress=0% | Job hasn't started processing | Check if Celery task was dispatched |
| Initial state sent but UI shows no progress | Frontend issue | Check browser console for WebSocket events |
| "Emitting job_progress" but frontend doesn't update | Redis message queue issue | Check Redis connection from both services |

## Files Modified

1. `backend/app/socket_events.py` - Enhanced `handle_join_job` with detailed logging
2. `backend/app/tasks.py` - Already has `[EMIT_PROGRESS]` logging (from previous commit)

## Next Steps

1. **Commit the new socket_events.py changes**
2. **Manually redeploy the worker service** (this is critical!)
3. **Test and collect logs** from both services
4. **Share the logs** - we'll know exactly what's happening

---

**The key issue is the worker service not being redeployed. Once that's done, we'll have full visibility!**

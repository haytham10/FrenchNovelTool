# Critical Fix: Deploy Enhanced Logging to See Socket.IO Emissions

## Problem Identified

Looking at the Railway worker logs you shared, I noticed **the enhanced logging I added is NOT deployed yet**!

Evidence:
- No `[EMIT_PROGRESS]` logs (I added these in tasks.py line 66)
- No "Emitting job_progress to room=" logs (I added these in socket_events.py)
- The worker is still running the OLD code without our diagnostic logging

## Files That Need to Be Deployed

1. `backend/app/socket_events.py` - Enhanced logging with INFO level
2. `backend/app/tasks.py` - Added `[EMIT_PROGRESS]` prefix

## Deployment Steps

### 1. Commit the changes:
```bash
cd H:\WORK\TIRED
git add backend/app/socket_events.py backend/app/tasks.py
git commit -m "fix: add enhanced logging for Socket.IO emission debugging"
git push origin normalizer-optimization
```

### 2. Wait for Railway auto-deployment
Railway should automatically detect the push and redeploy both:
- Backend API service
- Celery worker service

Check deployment status:
```bash
railway status
```

### 3. Verify deployment
```bash
# Check if new code is deployed
railway logs --service=<worker-service-id> --tail

# Look for the new log format when processing a job
```

### 4. Run a new test
Upload a small PDF (15 pages) and watch for these new logs:

**In worker logs, you should now see:**
```
[EMIT_PROGRESS] Starting emission for job <id>
Emitting job_progress to room=job_<id>: progress=X%, step=..., status=processing
Successfully emitted job_progress for job <id>
[EMIT_PROGRESS] Completed emission for job <id>
```

## What the Logs Will Tell Us

### If you see the logs:
✅ **Emissions are working** - problem is frontend WebSocket or Redis message queue

### If you don't see the logs:
❌ **`emit_progress()` not being called** - logic issue in tasks.py

### If you see errors:
🔍 **Specific error message** will tell us exactly what's failing

## Quick Deployment Check

After deploying, SSH into worker and verify the code:

```bash
railway ssh --service=<worker-service-id>

# Check if the new code is there
cd /app
grep -n "\[EMIT_PROGRESS\]" app/tasks.py
# Should show line 66: logger.info(f"[EMIT_PROGRESS] Starting emission for job {job_id}")

grep -n "Emitting job_progress to room" app/socket_events.py
# Should show the new logging line
```

## Additional Fix Applied

I also added `db.session.expire_all()` in `socket_events.py` to ensure we're reading fresh data from the database when emitting progress. This prevents stale session issues in Celery workers.

---

**NEXT STEP: Commit and push the changes, then test again!**

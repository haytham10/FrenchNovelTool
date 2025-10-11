# Quick Verification Checklist

## After Deployment - Immediate Checks

### 1. Verify Worker Service Redeployed (CRITICAL)

First, find your Celery Worker service ID:
```bash
# List all Railway services to find the worker
railway service list

# Look for a service named like "celery-worker", "worker", "backend-worker", etc.
# Note the Service ID (format: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx)
```

Then verify new code is deployed:
```bash
# SSH into Railway worker (replace with your service ID from above)
railway ssh --service=<celery-worker-id>

# Check for new code (should find multiple matches)
# Note: Path is /app/app/tasks.py for standard Railway deployments
grep "from app.task_config import" /app/app/tasks.py

# Expected output:
# from app.task_config import VALIDATION_DISCARD_FAILURES
# from app.task_config import CHUNK_WATCHDOG_SECONDS
# from app.task_config import CHUNK_TASK_MAX_RETRIES, CHUNK_TASK_RETRY_DELAY
# ... (7 total imports)
```

**If not found:** Worker didn't redeploy. Go to Railway dashboard and manually redeploy the Celery Worker service.

### 2. Test Job Processing

Upload a small PDF (15 pages) and watch logs in real-time.

#### Expected Backend API Logs:
```
[2025-XX-XX XX:XX:XX] INFO in socket_events: WebSocket connected: user_id=X
[2025-XX-XX XX:XX:XX] INFO in socket_events: [JOIN_JOB] Received join request for job XX
[2025-XX-XX XX:XX:XX] INFO in socket_events: [JOIN_JOB] User X joined room job_XX
[2025-XX-XX XX:XX:XX] INFO in socket_events: [JOIN_JOB] Sending initial state for job XX: status=processing, progress=5%, step=Analyzing PDF
[2025-XX-XX XX:XX:XX] INFO in socket_events: [JOIN_JOB] Initial state sent for job XX
```

#### Expected Celery Worker Logs:
```
[2025-XX-XX XX:XX:XX] INFO in tasks: Job XX: created 1 JobChunk rows in DB
[2025-XX-XX XX:XX:XX] INFO in tasks: Chunk X: STAGE 1 (Preprocessing) → 150 sentences
[2025-XX-XX XX:XX:XX] INFO in tasks: Chunk X: STAGE 2 (AI Normalization) → 200 sentences
[2025-XX-XX XX:XX:XX] INFO in tasks: Chunk X: STAGE 3 (Validation) → 180/200 sentences passed (90.0%) - Pipeline: 150 input → 200 gemini → 180 final
[2025-XX-XX XX:XX:XX] INFO in tasks: [EMIT_PROGRESS] Starting emission for job XX
[2025-XX-XX XX:XX:XX] INFO in socket_events: Emitting job_progress to room=job_XX: progress=25%, step=Processing chunks (1/1), status=processing
[2025-XX-XX XX:XX:XX] INFO in socket_events: Successfully emitted job_progress for job XX
[2025-XX-XX XX:XX:XX] INFO in tasks: [EMIT_PROGRESS] Completed emission for job XX
```

#### Expected Frontend Console (Browser DevTools):
```
[WebSocket] Job XX: 5% - Analyzing PDF (processing)
[WebSocket] Job XX: 15% - Splitting into 1 chunks (processing)
[WebSocket] Job XX: 25% - Processing chunks (1/1) (processing)
[WebSocket] Job XX: 75% - Merging results (processing)
[WebSocket] Job XX: 100% - Completed (completed)
```

### 3. Red Flags - What Should NOT Appear

❌ **Worker Logs Missing:**
- No `STAGE 1`, `STAGE 2`, `STAGE 3` logs → Worker not redeployed
- No `[EMIT_PROGRESS]` logs → Worker not redeployed

❌ **Error Logs:**
```
RuntimeError: Working outside of application context
AttributeError: 'NoneType' object has no attribute 'config'
```
→ These indicate the `task_config` fix didn't deploy

❌ **Frontend Console:**
```
WebSocket connection failed
WebSocket disconnected: io server disconnect
```
→ Check Redis connection and eventlet configuration

❌ **Validation Warnings:**
```
Low validation pass rate for chunk X: 25.0%
Validation pass rate critically low (25.0%)
```
→ This is expected for some PDFs, but if ALL chunks fail, check PDF quality

### 4. Success Indicators

✅ **Worker logs show:**
- `from app.task_config import` (confirms new code deployed)
- 3-stage normalization pipeline
- `[EMIT_PROGRESS]` messages
- WebSocket emissions successful

✅ **Frontend shows:**
- Progress bar visible from 5%
- Real-time updates
- Reaches 100% on completion

✅ **Database:**
- History entry created
- Sentences array populated
- No stuck jobs in `processing` state

### 5. Performance Baselines

For a **15-page PDF** (typical):
- **Total time:** 1-3 minutes
- **Chunk processing:** 30-90 seconds
- **Validation pass rate:** 70-95%
- **Final sentence count:** 100-300 sentences

For a **100-page PDF**:
- **Total time:** 5-15 minutes
- **Chunks:** 2-3 (30-50 pages each)
- **Parallel processing:** All chunks process simultaneously
- **Validation pass rate:** 65-90%
- **Final sentence count:** 800-2000 sentences

### 6. Common Issues & Quick Fixes

| Issue | Quick Check | Fix |
|-------|-------------|-----|
| No progress updates | Check worker logs for `[EMIT_PROGRESS]` | Redeploy worker service |
| Worker logs show `RuntimeError` | Check for `task_config` imports | Redeploy worker service |
| Validation failing all sentences | Check logs for pass rate % | Adjust `VALIDATION_MIN_WORDS` env var |
| Job stuck at 15% | Check for chunk processing errors | Check Gemini API quota/limits |
| Frontend shows 0% forever | Check browser console for WebSocket errors | Verify Redis connection |

### 7. Emergency Recovery

If job is stuck, first get your backend URL and job ID:
```bash
# Get your Railway backend URL from Railway dashboard
# Or use CLI to find it:
railway env | grep RAILWAY_PUBLIC_DOMAIN

# Get stuck job ID from:
# - Frontend URL (e.g., /jobs/123 shows job ID 123)
# - API response when job was created
# - Database query if you have access
```

Then force recovery:
```bash
# Option 1: Force finalize via admin endpoint
# Replace YOUR_BACKEND_URL with your actual Railway backend URL
# Replace JOB_ID with the actual job ID number
curl -X POST https://YOUR_BACKEND_URL/api/v1/admin/jobs/JOB_ID/force-finalize \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"

# Option 2: Reconcile stuck chunks (affects all jobs)
curl -X POST https://YOUR_BACKEND_URL/api/v1/admin/reconcile-stuck-chunks \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

**Getting JWT Token:**
- Log into frontend
- Open browser DevTools → Application/Storage → LocalStorage
- Copy the `access_token` value

### 8. Monitoring Commands

First, get your Celery Worker service ID:
```bash
# List all Railway services
railway service list
# Look for service named "celery-worker", "worker", or similar
# Note the Service ID (format: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx)
```

Then use these monitoring commands (replace `<worker-id>` with actual ID from above):
```bash
# Watch worker logs in real-time
railway logs --service=<worker-id> --tail 100 --follow

# Check for errors only
railway logs --service=<worker-id> --tail 200 | grep -E "(ERROR|CRITICAL|exception)"

# Check validation stats
railway logs --service=<worker-id> --tail 200 | grep "validation pass rate"

# Check WebSocket emissions
railway logs --service=<worker-id> --tail 200 | grep "EMIT_PROGRESS"

# Check normalization pipeline
railway logs --service=<worker-id> --tail 200 | grep "STAGE"
```

## Summary

**If you see:**
1. ✅ `task_config` imports in worker code
2. ✅ 3-stage normalization logs
3. ✅ `[EMIT_PROGRESS]` messages
4. ✅ WebSocket emissions successful
5. ✅ Frontend progress bar updating

**Then all fixes are working correctly.**

**If not, check:** `DEPLOYMENT_GUIDE.md` for detailed troubleshooting.

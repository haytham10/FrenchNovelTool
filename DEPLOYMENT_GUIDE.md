# Deployment Guide for Critical Fixes

## Summary of Changes

This commit fixes 5 critical issues preventing progress updates, job processing, and results delivery.

## Files Changed

### Backend
1. **`backend/app/task_config.py`** (NEW)
   - Global configuration module for Celery tasks
   - Reads directly from environment variables
   - Eliminates dependency on Flask `current_app` context

2. **`backend/app/tasks.py`** (MODIFIED)
   - Replaced all `current_app.config.get()` calls with `task_config` imports
   - Fixed 7 instances where Flask context wasn't guaranteed
   - Added enhanced normalization pipeline logging
   - Added critical validation failure detection (fails chunk if <30% pass rate)
   - Tracks sentence counts through all 3 normalization stages

### Frontend
3. **`frontend/src/lib/useJobWebSocket.ts`** (MODIFIED)
   - Added debug logging for WebSocket progress updates
   - Logs job progress in format: `[WebSocket] Job X: Y% - Step (status)`
   - Helps diagnose progress display issues

### Documentation
4. **`CRITICAL_ISSUES_ANALYSIS.md`** (NEW)
   - Comprehensive analysis of all 5 critical issues
   - Detailed fix recommendations
   - Testing checklist
   - Monitoring recommendations

5. **`DEPLOYMENT_GUIDE.md`** (THIS FILE)

## Deployment Steps

### 1. Verify Environment Variables

Ensure these are set in Railway/production environment:

```bash
# Validation Configuration
VALIDATION_DISCARD_FAILURES=True
VALIDATION_ENABLED=True
VALIDATION_MIN_WORDS=4
VALIDATION_MAX_WORDS=8
VALIDATION_REQUIRE_VERB=True

# Celery Task Configuration  
CHUNK_TASK_MAX_RETRIES=4
CHUNK_TASK_RETRY_DELAY=3
CHUNK_WATCHDOG_SECONDS=600
CHUNK_STUCK_THRESHOLD_SECONDS=720

# Finalization Configuration
FINALIZE_MAX_RETRIES=10
FINALIZE_RETRY_DELAY=15

# Chord/Watchdog Configuration
CHORD_WATCHDOG_SECONDS=300

# Gemini Configuration
GEMINI_MAX_RETRIES=3
GEMINI_RETRY_DELAY=1
GEMINI_CALL_TIMEOUT_SECONDS=300

# Worker Configuration
WORKER_MAX_MEMORY_MB=900
```

### 2. Deploy Backend Changes

**Option A: Railway Dashboard**
1. Push code to GitHub: `git push origin <branch>`
2. Railway auto-deploys the Backend API service
3. **CRITICAL:** Manually redeploy Celery Worker service:
   - Go to Railway dashboard
   - Select "Celery Worker" service  
   - Click "Deploy" → "Redeploy"

**Option B: Railway CLI**
```bash
# Push code
git push origin <branch>

# List services to find worker service ID
railway service list
# Look for a service named "celery-worker", "worker", or "backend-worker"
# Note the Service ID (format: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx)

# Manually redeploy worker (replace with actual service ID from above)
railway redeploy --service=<celery-worker-service-id>
```

### 3. Deploy Frontend Changes

**Vercel (Automatic)**
```bash
git push origin <branch>
# Vercel auto-deploys
```

### 4. Verify Deployment

#### A. Check Backend API Service Logs

Look for initialization logs:
```
[2025-XX-XX XX:XX:XX] INFO in socket_events: WebSocket connected: user_id=X
```

#### B. Check Celery Worker Service Logs

**CRITICAL: Verify new code is deployed**

SSH into worker (or check Railway logs):
```bash
# Look for the new task_config imports
grep "from app.task_config import" /app/app/tasks.py
# Should show multiple lines with imports

# Verify enhanced logging is present
grep "\[EMIT_PROGRESS\]" /app/app/tasks.py
# Should show: logger.info(f"[EMIT_PROGRESS] Starting emission for job {job_id}")
```

If not found, **worker didn't redeploy** - go back to Step 2 and manually redeploy.

### 5. Test with Small PDF

1. **Upload:** 15-page PDF
2. **Monitor Backend Logs:** Should see:
   ```
   [JOIN_JOB] Received join request for job XX
   [JOIN_JOB] User Y joined room job_XX
   [JOIN_JOB] Sending initial state for job XX: status=processing, progress=5%, step=Analyzing PDF
   [JOIN_JOB] Initial state sent for job XX
   ```

3. **Monitor Worker Logs:** Should see:
   ```
   Job XX: STAGE 1 (Preprocessing) → N sentences
   Job XX: STAGE 2 (AI Normalization) → M sentences  
   Job XX: STAGE 3 (Validation) → K/M sentences passed (XX.X%) - Pipeline: N input → M gemini → K final
   [EMIT_PROGRESS] Starting emission for job XX
   Emitting job_progress to room=job_XX: progress=25%, step=Processing chunks (1/1), status=processing
   Successfully emitted job_progress for job XX
   [EMIT_PROGRESS] Completed emission for job XX
   ```

4. **Check Frontend:** Browser console should show:
   ```
   [WebSocket] Job XX: 5% - Analyzing PDF (processing)
   [WebSocket] Job XX: 25% - Processing chunks (1/1) (processing)
   [WebSocket] Job XX: 100% - Completed (completed)
   ```

5. **Verify UI:** 
   - Progress bar visible from 5%
   - Updates in real-time
   - Reaches 100% on completion

## Rollback Plan

If issues occur:

### Backend Rollback
```bash
# Identify last good commit
git log --oneline -10

# Revert to last good commit
git revert <commit-hash>
git push origin <branch>

# Or hard reset (destructive)
git reset --hard <commit-hash>
git push -f origin <branch>

# Manually redeploy worker service again
railway redeploy --service=<celery-worker-service-id>
```

### Frontend Rollback
```bash
# Vercel has automatic rollback in dashboard
# Or via CLI:
vercel rollback <deployment-url>
```

## Common Issues After Deployment

### Issue: Progress still not updating

**Diagnosis:**
```bash
# Check worker logs for [EMIT_PROGRESS]
railway logs --service=<worker-id> --tail 100 | grep EMIT_PROGRESS
```

**Solutions:**
- If no `[EMIT_PROGRESS]` logs: Worker not redeployed - redeploy manually
- If `[EMIT_PROGRESS]` logs but no `Emitting job_progress`: Check Redis connection
- If emissions logged but frontend doesn't update: Check WebSocket connection in browser console

### Issue: Validation failing too many sentences

**Diagnosis:**
```bash
# Check worker logs for "Low validation pass rate"
railway logs --service=<worker-id> | grep "validation pass rate"
```

**Solutions:**
- If pass rate 30-70%: Normal for some PDFs, job will complete with partial results
- If pass rate <30%: Job will fail with `VALIDATION_FAILED` error - check PDF quality
- Adjust `VALIDATION_MIN_WORDS` and `VALIDATION_MAX_WORDS` if needed

### Issue: Jobs stuck in processing

**Diagnosis:**
```bash
# Check if chunks are stuck
railway logs --service=<worker-id> | grep "chunk_watchdog"
```

**Solutions:**
- Watchdog should auto-retry stuck chunks (up to 4 times)
- If chunks keep timing out: Increase `CHUNK_WATCHDOG_SECONDS` or `GEMINI_CALL_TIMEOUT_SECONDS`
- Check Gemini API quota/rate limits

## Monitoring Recommendations

Set up alerts for:
1. **High validation failure rate** (>50% chunks failing validation)
2. **Stuck jobs** (jobs in processing state >1 hour)
3. **WebSocket disconnections** (track reconnection rate)
4. **Worker memory usage** (alert at >80% of 900MB limit)

## Success Criteria

Deployment is successful when:
- [ ] Small PDF (15 pages) processes in <2 minutes
- [ ] Progress bar updates in real-time (visible at 5%, 25%, 75%, 100%)
- [ ] Worker logs show all 3 normalization stages
- [ ] Validation pass rate >70% for clean PDFs
- [ ] History entry created with sentences
- [ ] No `current_app` errors in worker logs
- [ ] WebSocket emissions logged and working

## Next Steps

After successful deployment:
1. Monitor for 24 hours
2. Review validation metrics
3. Tune `VALIDATION_*` settings if needed
4. Document any new issues
5. Plan performance optimizations based on real usage

## Support

If issues persist after following this guide:
1. Collect logs from all 3 services (Backend API, Celery Worker, Frontend)
2. Check browser console for WebSocket errors
3. Verify all environment variables are set correctly
4. Review `CRITICAL_ISSUES_ANALYSIS.md` for deeper diagnosis

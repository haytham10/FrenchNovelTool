# Async Processing Deployment - Quick Reference

## 🚀 Deployment Checklist

### [ ] Phase 1: Fix Database (10 minutes)
```bash
railway connect postgres
```
Then paste contents of `backend/fix_jobs_table.sql` and run.

**Verify**:
```sql
SELECT column_name FROM information_schema.columns 
WHERE table_name = 'jobs' AND column_name IN ('current_step', 'celery_task_id', 'progress_percent');
```
Should return 3 rows.

---

### [ ] Phase 2: Deploy Redis (5 minutes)
1. Railway Dashboard → New → Database → Add Redis
2. Verify `REDIS_URL` appears in backend service environment variables

**Test**:
```bash
railway run python -c "import redis, os; r = redis.from_url(os.getenv('REDIS_URL')); print('OK' if r.ping() else 'FAIL')"
```

---

### [ ] Phase 3: Deploy Celery Worker (30 minutes)

**Railway Setup**:
1. Dashboard → New → Empty Service
2. Name: `celery-worker`
3. Connect GitHub repo
4. Root Directory: `backend`
5. Dockerfile Path: `Dockerfile.worker`

**Environment Variables** (copy from backend service):
- ✅ `DATABASE_URL` (auto-injected)
- ✅ `REDIS_URL` (auto-injected)
- ⚠️ `GEMINI_API_KEY` (copy from backend)
- ⚠️ `SECRET_KEY` (copy from backend)
- ⚠️ `GOOGLE_CLIENT_ID` (copy from backend)
- ⚠️ `GOOGLE_CLIENT_SECRET` (copy from backend)
- ⚠️ `FRONTEND_URL` (copy from backend)

**Deploy**:
```bash
git add backend/Dockerfile.worker
git commit -m "Add Celery worker Dockerfile"
git push origin main
```

**Verify** in Railway logs for `celery-worker`:
```
[INFO/MainProcess] Connected to redis://...
[INFO/MainProcess] celery@hostname ready.
```

---

### [ ] Phase 4: Test Backend (10 minutes)

**Reserve Credits**:
```bash
curl -X POST https://api.frenchnoveltool.com/api/v1/credits/reserve \
  -H "Authorization: Bearer YOUR_JWT" \
  -H "Content-Type: application/json" \
  -d '{"estimated_tokens": 5000}'
```

**Start Async Processing**:
```bash
curl -X POST https://api.frenchnoveltool.com/api/v1/process-pdf-async \
  -H "Authorization: Bearer YOUR_JWT" \
  -F "pdf_file=@test.pdf" \
  -F "job_id=JOB_ID_FROM_RESERVE"
```

Expected response (HTTP 202):
```json
{
  "job_id": 123,
  "task_id": "job_123_1234567890.123",
  "status": "pending",
  "message": "PDF processing started"
}
```

**Poll Job Status**:
```bash
curl https://api.frenchnoveltool.com/api/v1/jobs/123 \
  -H "Authorization: Bearer YOUR_JWT"
```

Expected response:
```json
{
  "id": 123,
  "status": "processing",
  "progress_percent": 45,
  "current_step": "Processing chunk 3 of 5",
  "total_chunks": 5,
  "processed_chunks": 2
}
```

---

### [ ] Phase 5: Update Frontend (2-3 hours)

#### File 1: `frontend/src/lib/queries.ts`

**Add Job Status Hook**:
```typescript
export function useJobStatus(jobId: number | null, enabled = true) {
  return useQuery({
    queryKey: ['job-status', jobId],
    queryFn: async () => {
      const response = await api.get(`/jobs/${jobId}`);
      return response.data;
    },
    enabled: !!jobId && enabled,
    refetchInterval: 2000, // Poll every 2 seconds
  });
}
```

**Update Process PDF Hook**:
```typescript
export function useProcessPdf() {
  const queryClient = useQueryClient();
  const { enqueueSnackbar } = useSnackbar();

  return useMutation({
    mutationFn: (request: ProcessPdfAsyncRequest) => processPdfAsync(request),
    
    onSuccess: (data) => {
      enqueueSnackbar(`Processing started (Job ID: ${data.job_id})`, { variant: 'info' });
      queryClient.invalidateQueries({ queryKey: queryKeys.history });
    },
    
    onError: (error) => {
      enqueueSnackbar(
        getApiErrorMessage(error, 'Failed to start PDF processing'),
        { variant: 'error' }
      );
    },
  });
}
```

#### File 2: `frontend/src/app/page.tsx`

**Add State**:
```typescript
const [currentJobId, setCurrentJobId] = useState<number | null>(null);
const jobStatus = useJobStatus(currentJobId, currentJobId !== null);
```

**Update Upload Handler**:
```typescript
const handleFileUpload = async (file: File) => {
  try {
    setIsProcessing(true);
    
    // Step 1: Reserve credits
    const reservation = await reserveCreditsForJob({ estimated_tokens: 5000 });
    
    // Step 2: Start async processing
    const result = await processPdfMutation.mutateAsync({
      file,
      job_id: reservation.job_id,
      sentence_length_limit: settings.sentenceLengthLimit,
      gemini_model: settings.geminiModel,
      ignore_dialogue: settings.ignoreDialogue,
      preserve_formatting: settings.preserveFormatting,
      fix_hyphenation: settings.fixHyphenation,
      min_sentence_length: settings.minSentenceLength,
    });
    
    setCurrentJobId(result.job_id);
    
  } catch (error) {
    console.error('Upload failed:', error);
    setIsProcessing(false);
  }
};
```

**Add Completion Effect**:
```typescript
useEffect(() => {
  if (jobStatus.data?.status === 'completed') {
    // Fetch results
    api.get(`/jobs/${currentJobId}`).then(response => {
      // Update processing store with sentences
      processingStore.setSentences(response.data.sentences);
      enqueueSnackbar('PDF processing completed!', { variant: 'success' });
      setCurrentJobId(null);
      setIsProcessing(false);
    });
  } else if (jobStatus.data?.status === 'failed') {
    enqueueSnackbar(`Processing failed: ${jobStatus.data.error_message}`, { variant: 'error' });
    setCurrentJobId(null);
    setIsProcessing(false);
  }
}, [jobStatus.data?.status]);
```

**Add Progress UI**:
```typescript
{jobStatus.data?.status === 'processing' && (
  <Box sx={{ width: '100%', mt: 2 }}>
    <LinearProgress 
      variant="determinate" 
      value={jobStatus.data.progress_percent || 0} 
    />
    <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
      {jobStatus.data.current_step} ({jobStatus.data.progress_percent}%)
    </Typography>
    <Typography variant="caption" color="text.secondary">
      Chunk {jobStatus.data.processed_chunks} of {jobStatus.data.total_chunks}
    </Typography>
  </Box>
)}
```

---

### [ ] Phase 6: Test End-to-End (30 minutes)

1. **Deploy Frontend**:
```bash
git add frontend/src/lib/queries.ts frontend/src/app/page.tsx
git commit -m "Switch to async PDF processing"
git push origin main
```

2. **Test in Browser**:
   - [ ] Upload a small PDF (5 pages)
   - [ ] See "Processing started (Job ID: 123)" notification
   - [ ] Progress bar appears and updates
   - [ ] After completion, see "PDF processing completed!" notification
   - [ ] Sentences appear in UI for editing

3. **Test Large PDF**:
   - [ ] Upload a 50-page PDF
   - [ ] Should NOT timeout
   - [ ] Progress shows "Processing chunk X of Y"
   - [ ] Completes successfully after 2-3 minutes

---

## 🐛 Troubleshooting

### Worker Not Starting
**Check Railway logs** → Look for:
```
[ERROR] Connection refused (Redis)
```
**Solution**: Verify `REDIS_URL` is set in worker environment variables.

### Database Column Errors
**Error**: `column "current_step" does not exist`  
**Solution**: Re-run `fix_jobs_table.sql` on Railway database.

### Frontend Still Timing Out
**Symptom**: 502 errors after 30 seconds  
**Cause**: Frontend still calling synchronous `/process-pdf` endpoint  
**Solution**: Verify `useProcessPdf()` calls `processPdfAsync()`, not `processPdf()`.

### Job Stuck in "pending"
**Check**:
1. Celery worker logs (should show task execution)
2. Redis connection (worker must connect to Redis)
3. Database columns exist (worker updates `progress_percent`)

**Debug**:
```bash
# Railway worker logs
railway logs --service celery-worker

# Should see:
[INFO/ForkPoolWorker-1] Task app.tasks.process_pdf_async[...] received
[INFO/ForkPoolWorker-1] Task app.tasks.process_pdf_async[...] succeeded
```

---

## 📊 Monitoring

### Worker Health
```bash
railway logs --service celery-worker --tail
```

### Redis Status
```bash
railway run python -c "import redis, os; r = redis.from_url(os.getenv('REDIS_URL')); print(r.info('server'))"
```

### Database Jobs
```bash
railway run python -c "from app import create_app, db; from app.models import Job; app = create_app(); app.app_context().push(); print(Job.query.filter_by(status='processing').count(), 'jobs processing')"
```

### Flower UI (Optional)
Deploy `Dockerfile.flower` as separate service, then access:
```
https://flower-YOUR_APP.up.railway.app
```

---

## ⚡ Quick Fixes

### Restart Worker
```bash
railway restart --service celery-worker
```

### Clear Redis Queue
```bash
railway run python -c "import redis, os; r = redis.from_url(os.getenv('REDIS_URL')); r.flushdb(); print('Queue cleared')"
```

### Cancel All Jobs
```bash
railway run python -c "from app import create_app, db; from app.models import Job; app = create_app(); app.app_context().push(); Job.query.filter(Job.status.in_(['pending', 'processing'])).update({'status': 'cancelled', 'is_cancelled': True}); db.session.commit(); print('All jobs cancelled')"
```

---

## 🎯 Success Criteria

- [x] Database has all async columns
- [x] Redis provisioned and reachable
- [x] Celery worker running and connected to Redis
- [x] `/process-pdf-async` returns HTTP 202 with job_id
- [x] `/jobs/<id>` returns progress updates
- [x] Frontend polls job status every 2 seconds
- [x] Progress bar shows live updates
- [x] Large PDF (50+ pages) completes without timeout
- [x] Processed sentences appear in UI after completion

---

## 📞 Support

If stuck, check:
1. **Railway Logs**: Dashboard → Service → Logs
2. **Celery Tasks**: `backend/app/tasks.py` lines 160-305
3. **API Endpoint**: `backend/app/routes.py` lines 630-752
4. **Frontend Hook**: `frontend/src/lib/queries.ts` line 111

**Common Issues Doc**: `docs/roadmaps/ASYNC_DEPLOYMENT_PLAN.md`  
**Implementation Status**: `docs/roadmaps/ASYNC_IMPLEMENTATION_STATUS.md`

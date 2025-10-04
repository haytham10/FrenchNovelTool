# Async Processing Implementation Status

## 🎉 Good News: The Code is Already Written!

Your colleague merged PR #40 which included a **complete async processing implementation**. You don't need to write any backend task code - just deploy the infrastructure and wire up the frontend.

---

## ✅ Already Implemented (In Your Codebase)

### Backend - Celery Tasks
**File**: `backend/app/tasks.py` (305 lines)

```python
@get_celery().task(bind=True, name='app.tasks.process_chunk')
def process_chunk(self, chunk_info, user_id, settings):
    """Process a single PDF chunk with Gemini"""
    # - Opens chunk temp file
    # - Extracts text with PyPDF2
    # - Calls GeminiService.normalize_text()
    # - Returns processed sentences
    # - Handles timeout errors gracefully
    
@get_celery().task(bind=True, name='app.tasks.process_pdf_async')  
def process_pdf_async(self, job_id, file_path, user_id, settings):
    """Main async task orchestrator"""
    # 1. Updates job status to 'processing' (5% progress)
    # 2. Calculates optimal chunk configuration (10% progress)
    # 3. Splits PDF into chunks (15% progress)
    # 4. Processes chunks in parallel using Celery groups
    # 5. Merges results with deduplication (75% progress)
    # 6. Updates job as 'completed' with results (100% progress)
    # 7. Handles cancellation checks at each step
    # 8. Cleans up temp files in finally block
```

**Features**:
- ✅ Parallel chunk processing
- ✅ Progress tracking (0-100%)
- ✅ Cancellation support
- ✅ Error handling with retry logic
- ✅ Automatic temp file cleanup
- ✅ Overlap deduplication

### Backend - API Endpoints
**File**: `backend/app/routes.py`

```python
@main_bp.route('/process-pdf-async', methods=['POST'])
@jwt_required()
@limiter.limit("10 per hour")
def process_pdf_async_endpoint():
    """Start async PDF processing"""
    # 1. Validates job_id and user authorization
    # 2. Validates PDF file
    # 3. Saves PDF to temp storage
    # 4. Enqueues Celery task: process_pdf_async.apply_async()
    # 5. Returns HTTP 202 with job_id and task_id
    
@main_bp.route('/jobs/<int:job_id>', methods=['GET'])
@jwt_required()  
def get_job_status(job_id):
    """Get job status and progress"""
    # 1. Checks user authorization
    # 2. Fetches job from database
    # 3. Gets Celery task state if processing
    # 4. Returns job.to_dict() with all async fields
    
@main_bp.route('/jobs/<int:job_id>/cancel', methods=['POST'])
@jwt_required()
def cancel_job(job_id):
    """Cancel running job"""
    # 1. Marks job.is_cancelled = True
    # 2. Revokes Celery task
    # 3. Task checks is_cancelled flag at each step
```

### Backend - Database Schema
**File**: `backend/app/models.py`

```python
class Job(db.Model):
    # Async processing fields
    celery_task_id = db.Column(db.String(155), index=True)
    progress_percent = db.Column(db.Integer, default=0)  # 0-100
    current_step = db.Column(db.String(100))  # "Processing chunk 5/10"
    total_chunks = db.Column(db.Integer)
    processed_chunks = db.Column(db.Integer, default=0)
    chunk_results = db.Column(db.JSON)  # Array of chunk results
    failed_chunks = db.Column(db.JSON)  # Array of failed chunk IDs
    is_cancelled = db.Column(db.Boolean, default=False)
    cancelled_at = db.Column(db.DateTime)
    cancelled_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    processing_time_seconds = db.Column(db.Integer)
    
    def to_dict(self):
        # Returns all fields above + more for API responses
```

### Backend - Celery Configuration
**File**: `backend/app/celery_app.py`

```python
def make_celery(app):
    """Create Celery instance with Flask app context"""
    celery = Celery(
        app.import_name,
        broker=app.config['CELERY_BROKER_URL'],  # Redis
        backend=app.config['CELERY_RESULT_BACKEND'],  # Redis
    )
    celery.conf.update(
        task_serializer='json',
        result_serializer='json',
        accept_content=['json'],
        task_track_started=True,
        task_time_limit=1800,  # 30 minutes max
        task_soft_time_limit=1500,  # 25 minutes soft limit
    )
    
    class ContextTask(celery.Task):
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)
    
    celery.Task = ContextTask
    return celery
```

**File**: `backend/config.py`

```python
CELERY_BROKER_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
CELERY_RESULT_BACKEND = os.getenv('REDIS_URL', 'redis://localhost:6379/1')
```

### Backend - Dependencies
**File**: `backend/requirements.txt`

```
celery==5.3.4
redis==5.0.1
flower==2.0.1
```

### Frontend - API Functions
**File**: `frontend/src/lib/api.ts`

```typescript
// Line 141 - OLD synchronous endpoint (causing timeouts)
export async function processPdf(file: File, options?: ProcessPdfOptions): Promise<string[]> {
  const response = await api.post('/process-pdf', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    onUploadProgress: options?.onUploadProgress
  });
  return response.data.sentences || [];
}

// Line 408 - NEW async endpoint (ready to use!)
export async function processPdfAsync(request: ProcessPdfAsyncRequest): Promise<ProcessPdfAsyncResponse> {
  const formData = new FormData();
  formData.append('pdf_file', request.file);
  formData.append('job_id', request.job_id.toString());
  // ... append all settings
  
  const response = await api.post('/process-pdf-async', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  });
  return response.data; // { job_id, task_id, status, message }
}
```

---

## ❌ NOT Deployed (Infrastructure Gaps)

### 1. Redis - Message Broker
**Status**: Not provisioned on Railway  
**Required For**: Celery task queue  
**Action**: Add Redis database service on Railway  
**Time**: 5 minutes

### 2. Celery Worker - Background Processor
**Status**: Not running (no service deployed)  
**Required For**: Processing async tasks  
**Action**: Deploy worker service with `Dockerfile.worker`  
**Time**: 30 minutes

### 3. Database Schema - Missing Columns
**Status**: Migration marked applied but columns don't exist  
**Required For**: Storing job progress and async metadata  
**Action**: Run `fix_jobs_table.sql` on Railway database  
**Time**: 10 minutes

### 4. Frontend - Using Wrong Endpoint
**Status**: Calls synchronous `/process-pdf` instead of async `/process-pdf-async`  
**Required For**: Actually using the async infrastructure  
**Action**: Update `useProcessPdf()` hook to use `processPdfAsync()`  
**Time**: 2 hours (includes polling UI)

---

## 🔧 What You Need to Do

### Priority 1: Database Fix (10 minutes)
```bash
railway connect postgres
# Paste contents of backend/fix_jobs_table.sql
```

This adds the missing columns like `current_step`, `total_chunks`, `celery_task_id`, etc.

### Priority 2: Deploy Redis (5 minutes)
1. Railway dashboard → New → Database → Add Redis
2. Railway automatically sets `REDIS_URL` environment variable
3. Backend already configured to use `REDIS_URL` in `config.py`

### Priority 3: Deploy Celery Worker (30 minutes)
1. Railway dashboard → New → Empty Service
2. Name: `celery-worker`
3. Connect to GitHub repo
4. Root Directory: `backend`
5. Dockerfile Path: `Dockerfile.worker`
6. Copy environment variables from backend service:
   - `DATABASE_URL` (auto)
   - `REDIS_URL` (auto)
   - `GEMINI_API_KEY`
   - `SECRET_KEY`
   - `GOOGLE_CLIENT_ID`
   - `GOOGLE_CLIENT_SECRET`
   - `FRONTEND_URL`

### Priority 4: Update Frontend (2-3 hours)

#### Step 1: Update React Query Hook
**File**: `frontend/src/lib/queries.ts`

Change from:
```typescript
export function useProcessPdf() {
  return useMutation({
    mutationFn: ({ file, options }) => processPdf(file, options),
    // ...
  });
}
```

To:
```typescript
export function useProcessPdf() {
  return useMutation({
    mutationFn: (request: ProcessPdfAsyncRequest) => processPdfAsync(request),
    // ...
  });
}
```

#### Step 2: Add Job Status Polling Hook
**File**: `frontend/src/lib/queries.ts`

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

#### Step 3: Update Page Component
**File**: `frontend/src/app/page.tsx`

Add state for tracking current job:
```typescript
const [currentJobId, setCurrentJobId] = useState<number | null>(null);
const jobStatus = useJobStatus(currentJobId);
```

Update the file upload handler to:
1. Reserve credits (get job_id)
2. Call `processPdfAsync({ file, job_id, ...settings })`
3. Set `currentJobId` from response
4. Poll job status every 2 seconds
5. When status === 'completed', fetch results and update UI

#### Step 4: Add Progress UI
```typescript
{jobStatus.data?.status === 'processing' && (
  <Box sx={{ width: '100%', mt: 2 }}>
    <LinearProgress 
      variant="determinate" 
      value={jobStatus.data.progress_percent} 
    />
    <Typography variant="caption" color="text.secondary">
      {jobStatus.data.current_step} ({jobStatus.data.progress_percent}%)
    </Typography>
  </Box>
)}
```

---

## 📊 Comparison: Before vs After

| Aspect | Before (Synchronous) | After (Async) |
|--------|---------------------|---------------|
| **Max PDF Size** | ~10 pages (30s timeout) | Unlimited (30min task limit) |
| **User Feedback** | Spinner, no progress | Live progress: "Processing chunk 3/5 (60%)" |
| **Timeout Behavior** | Hard fail at 30s | No HTTP timeout (task runs in background) |
| **Cancellation** | Not possible | User can cancel anytime |
| **Retry Logic** | None | Automatic retry on transient failures |
| **Parallel Processing** | No | Yes (chunks processed in parallel) |
| **Monitoring** | None | Flower UI shows all tasks |

---

## 🎯 Success Metrics

After deployment, you should be able to:

1. ✅ Upload a 100-page PDF without timeout
2. ✅ See real-time progress: "Processing chunk 5/10 (50%)"
3. ✅ Cancel a long-running job mid-processing
4. ✅ View job history showing completed async jobs
5. ✅ Access Flower UI to monitor worker health
6. ✅ Process multiple PDFs concurrently (worker handles queue)

---

## 📝 Quick Start Commands

### Deploy Infrastructure
```bash
# Fix database schema
railway connect postgres
# Paste fix_jobs_table.sql contents

# Verify columns exist
SELECT column_name FROM information_schema.columns WHERE table_name = 'jobs';

# Deploy worker (Railway will auto-detect Dockerfile.worker)
git add backend/Dockerfile.worker backend/Dockerfile.flower
git commit -m "Add Celery worker and Flower Dockerfiles"
git push origin main
```

### Test Async Endpoint Manually
```bash
# Reserve credits
curl -X POST https://api.frenchnoveltool.com/api/v1/credits/reserve \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"estimated_tokens": 5000}'

# Start async processing
curl -X POST https://api.frenchnoveltool.com/api/v1/process-pdf-async \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "pdf_file=@test.pdf" \
  -F "job_id=123"

# Poll status
curl https://api.frenchnoveltool.com/api/v1/jobs/123 \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Monitor Worker Health
```bash
# Check Railway logs for celery-worker service
# Look for: "[INFO/MainProcess] celery@hostname ready."

# Access Flower UI (if deployed)
# Navigate to: https://flower.your-railway-app.dev
```

---

## 🚨 Known Issues & Solutions

### Issue 1: Database Columns Missing
**Symptom**: `column "current_step" of relation "jobs" does not exist`  
**Solution**: Run `fix_jobs_table.sql` on production database  
**Status**: Fix prepared, ready to execute

### Issue 2: Worker Timeout (30s)
**Symptom**: `[CRITICAL] WORKER TIMEOUT (pid:2)` in Railway logs  
**Solution**: Use async processing (this entire deployment plan)  
**Status**: Code ready, infrastructure needs deployment

### Issue 3: Frontend Using Wrong Endpoint
**Symptom**: PDFs still timing out after deploying worker  
**Solution**: Update `useProcessPdf()` to call `processPdfAsync()`  
**Status**: Code change needed in frontend

---

## 📚 References

- **Celery Documentation**: https://docs.celeryproject.org/
- **Flask-Celery Integration**: https://flask.palletsprojects.com/en/stable/patterns/celery/
- **Railway Redis**: https://docs.railway.app/databases/redis
- **Flower Monitoring**: https://flower.readthedocs.io/

---

## ⏰ Estimated Timeline

| Phase | Task | Time | Complexity |
|-------|------|------|-----------|
| 1 | Fix database schema | 10 min | Low |
| 2 | Deploy Redis on Railway | 5 min | Low |
| 3 | Deploy Celery worker | 30 min | Medium |
| 4 | Update frontend hooks | 1 hour | Medium |
| 5 | Add progress UI | 1 hour | Medium |
| 6 | Test end-to-end | 30 min | Low |
| 7 | Deploy Flower (optional) | 30 min | Low |

**Total**: ~3.5 hours (or 1.5 hours if skipping Flower)

---

## 🎉 Final Notes

You're **95% done**! The heavy lifting (implementing Celery tasks, chunking logic, database schema) has already been completed in PR #40. You just need to:

1. **Deploy the infrastructure** (Redis + worker)
2. **Fix the database** (add missing columns)
3. **Wire up the frontend** (use async endpoint instead of sync)

Once these steps are complete, you'll have production-grade async processing that can handle PDFs of any size without timeouts.

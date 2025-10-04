# Async PDF Processing Deployment Plan

## Problem Statement
Railway enforces a **30-second hard HTTP timeout** that cannot be overridden, causing all PDF processing requests to fail with worker timeouts. The async processing infrastructure was implemented in PR #40 but has not been deployed.

## Current State

### ✅ Implemented (Code Ready)
- **Backend Celery Tasks** (`backend/app/tasks.py`):
  - `process_chunk()` - Processes individual PDF chunks in parallel
  - `process_pdf_async()` - Main async task with chunking, progress tracking, cancellation support
  - `merge_chunk_results()` - Deduplicates overlapping chunk results
  
- **Backend API Endpoints** (`backend/app/routes.py`):
  - `/api/v1/process-pdf-async` - Async endpoint (returns job_id, HTTP 202 Accepted)
  - `/api/v1/process-pdf` - Synchronous endpoint (currently used, timing out)
  
- **Frontend API Functions** (`frontend/src/lib/api.ts`):
  - `processPdfAsync()` - Calls async endpoint (line 408)
  - `processPdf()` - Calls synchronous endpoint (line 141, **currently used**)

- **Database Schema** (`backend/app/models.py`):
  - `Job` model with 15+ async fields: `celery_task_id`, `progress_percent`, `current_step`, `total_chunks`, `processed_chunks`, `is_cancelled`, etc.
  - **CRITICAL**: Missing columns in production database (see issue below)

- **Celery Configuration** (`backend/app/celery_app.py`):
  - `make_celery()` factory with Flask app context integration
  - Task time limits: 1800s hard, 1500s soft
  - ContextTask for proper Flask request context

- **Dependencies** (`backend/requirements.txt`):
  - celery==5.3.4
  - redis==5.0.1
  - flower==2.0.1 (monitoring UI)

### ❌ Not Deployed (Infrastructure Missing)
1. **Redis** - Message broker for Celery (required)
2. **Celery Worker** - Background worker process (required)
3. **Flower** - Monitoring UI (optional but recommended)

### ⚠️ Database Schema Out of Sync
Production database is missing columns despite migration marked as applied:
- `current_step` column doesn't exist
- `total_chunks`, `processed_chunks`, and other async fields likely missing
- Migration `48fd2dc76953` marked as applied but columns not created

---

## Deployment Steps

### Phase 1: Fix Database Schema (CRITICAL - Do First)

#### Option A: Direct SQL Execution (Fastest)
```bash
# Connect to Railway PostgreSQL
railway connect postgres

# Run SQL to add missing columns
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS current_step VARCHAR(255);
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS total_chunks INTEGER;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS processed_chunks INTEGER DEFAULT 0;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS chunk_results JSONB;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS failed_chunks JSONB;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS processing_settings JSONB;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS celery_task_id VARCHAR(255);
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS progress_percent INTEGER DEFAULT 0;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS is_cancelled BOOLEAN DEFAULT FALSE;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS cancelled_at TIMESTAMP;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS cancelled_by INTEGER REFERENCES users(id);
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS processing_time_seconds INTEGER;

# Verify columns exist
\d jobs
```

#### Option B: Re-run Migration (Safer but Slower)
```bash
# Downgrade to previous migration
railway run flask db downgrade 7ba2d39f4b83

# Upgrade back to current
railway run flask db upgrade head

# Verify schema
railway run flask db current
```

**Validation**: After either option, verify with:
```bash
railway run python -c "from app import create_app, db; from app.models import Job; app = create_app(); app.app_context().push(); print(Job.__table__.columns.keys())"
```

---

### Phase 2: Deploy Redis on Railway

#### Step 1: Add Redis Service
1. Go to Railway dashboard → Your project
2. Click **"New"** → **"Database"** → **"Add Redis"**
3. Railway will provision a Redis instance and expose `REDIS_URL` environment variable

#### Step 2: Update Backend Environment Variables
Railway automatically injects `REDIS_URL` into your backend service. Verify in `backend/config.py`:

```python
# Current config.py (lines 99-102)
CELERY_BROKER_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
CELERY_RESULT_BACKEND = os.getenv('REDIS_URL', 'redis://localhost:6379/1')
```

This already uses `REDIS_URL` - no code changes needed!

#### Step 3: Verify Redis Connection
```bash
railway run python -c "import redis; import os; r = redis.from_url(os.getenv('REDIS_URL')); r.ping(); print('Redis connected!')"
```

---

### Phase 3: Deploy Celery Worker Service

#### Step 1: Create Worker Dockerfile
Create `backend/Dockerfile.worker`:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Run Celery worker
CMD ["celery", "-A", "app.celery", "worker", "--loglevel=info", "--concurrency=2"]
```

**Key settings**:
- `--loglevel=info` - Detailed logs for debugging
- `--concurrency=2` - 2 worker processes (adjust based on Railway plan)

#### Step 2: Create Worker Service on Railway
1. Railway dashboard → **"New"** → **"Empty Service"**
2. Name it `celery-worker`
3. Connect to same GitHub repo
4. Set **Root Directory**: `backend`
5. Set **Dockerfile Path**: `Dockerfile.worker`

#### Step 3: Configure Worker Environment Variables
Copy all environment variables from your backend service:
- `DATABASE_URL` (automatically provided by Railway)
- `REDIS_URL` (automatically provided by Railway)
- `GEMINI_API_KEY`
- `SECRET_KEY`
- `GOOGLE_CLIENT_ID`
- `GOOGLE_CLIENT_SECRET`
- `FRONTEND_URL`

**Important**: The worker needs access to the same database and Redis as the web service.

#### Step 4: Deploy Worker
```bash
# Trigger deployment
git commit --allow-empty -m "Deploy Celery worker"
git push origin main
```

Railway will automatically detect `Dockerfile.worker` and deploy.

#### Step 5: Verify Worker is Running
Check Railway logs for:
```
[INFO/MainProcess] celery@hostname ready.
[INFO/MainProcess] Connected to redis://...
```

---

### Phase 4: Update Frontend to Use Async Endpoint

#### Step 1: Create New React Query Hook
Edit `frontend/src/lib/queries.ts`:

```typescript
/**
 * Async PDF Processing with Job Polling
 */
export function useProcessPdfAsync() {
  const queryClient = useQueryClient();
  const { enqueueSnackbar } = useSnackbar();

  return useMutation({
    mutationFn: (request: ProcessPdfAsyncRequest) => processPdfAsync(request),
    
    onSuccess: (data) => {
      enqueueSnackbar(`Processing started (Job ID: ${data.job_id})`, { variant: 'info' });
      // Invalidate history to show new job
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

/**
 * Poll Job Status
 */
export function useJobStatus(jobId: number | null, options?: { enabled?: boolean; refetchInterval?: number }) {
  return useQuery({
    queryKey: ['job-status', jobId],
    queryFn: () => getJobStatus(jobId!),
    enabled: !!jobId && (options?.enabled ?? true),
    refetchInterval: options?.refetchInterval ?? 2000, // Poll every 2 seconds
  });
}
```

#### Step 2: Add Job Status API Function
Edit `frontend/src/lib/api.ts`:

```typescript
export interface JobStatus {
  id: number;
  status: 'pending' | 'processing' | 'completed' | 'failed' | 'cancelled';
  progress_percent: number;
  current_step: string;
  total_chunks?: number;
  processed_chunks?: number;
  error_message?: string;
  started_at?: string;
  completed_at?: string;
  processing_time_seconds?: number;
}

export async function getJobStatus(jobId: number): Promise<JobStatus> {
  const response = await api.get(`/jobs/${jobId}/status`);
  return response.data;
}
```

#### Step 3: Update Page Component
Edit `frontend/src/app/page.tsx`:

Replace:
```typescript
const processPdfMutation = useProcessPdf();
```

With:
```typescript
const processPdfMutation = useProcessPdfAsync();
const [currentJobId, setCurrentJobId] = useState<number | null>(null);
const jobStatus = useJobStatus(currentJobId, { 
  enabled: currentJobId !== null,
  refetchInterval: 2000 
});
```

Update the upload handler:
```typescript
const handleFileUpload = async (file: File) => {
  try {
    setIsProcessing(true);
    
    // Step 1: Reserve credits (if using credit system)
    const reservation = await reserveCreditsForJob({ estimated_tokens: 5000 });
    
    // Step 2: Start async processing
    const result = await processPdfMutation.mutateAsync({
      file,
      job_id: reservation.job_id,
      sentence_length_limit: 8,
      gemini_model: 'balanced',
      // ... other settings
    });
    
    setCurrentJobId(result.job_id);
    
    // Step 3: Poll for completion (handled by useJobStatus hook)
    // When status === 'completed', fetch results and update UI
    
  } catch (error) {
    console.error('Upload failed:', error);
  } finally {
    setIsProcessing(false);
  }
};

// Add effect to handle job completion
useEffect(() => {
  if (jobStatus.data?.status === 'completed') {
    // Fetch processed sentences from history
    // Update processing store
    enqueueSnackbar('PDF processing completed!', { variant: 'success' });
    setCurrentJobId(null);
  } else if (jobStatus.data?.status === 'failed') {
    enqueueSnackbar(`Processing failed: ${jobStatus.data.error_message}`, { variant: 'error' });
    setCurrentJobId(null);
  }
}, [jobStatus.data?.status]);
```

#### Step 4: Add Progress Indicator
```typescript
{jobStatus.data?.status === 'processing' && (
  <Box sx={{ width: '100%', mt: 2 }}>
    <LinearProgress variant="determinate" value={jobStatus.data.progress_percent} />
    <Typography variant="caption" color="text.secondary">
      {jobStatus.data.current_step} ({jobStatus.data.progress_percent}%)
    </Typography>
  </Box>
)}
```

---

### Phase 5: Backend API Enhancement (Add Job Status Endpoint)

Edit `backend/app/routes.py` - Add this endpoint:

```python
@main_bp.route('/jobs/<int:job_id>/status', methods=['GET'])
@jwt_required()
def get_job_status(job_id):
    """Get status of an async processing job"""
    user_id = int(get_jwt_identity())
    
    job = Job.query.get(job_id)
    if not job:
        return jsonify({'error': 'Job not found'}), 404
    
    if job.user_id != user_id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    return jsonify({
        'id': job.id,
        'status': job.status,
        'progress_percent': job.progress_percent or 0,
        'current_step': job.current_step or 'Pending',
        'total_chunks': job.total_chunks,
        'processed_chunks': job.processed_chunks,
        'error_message': job.error_message,
        'started_at': job.started_at.isoformat() if job.started_at else None,
        'completed_at': job.completed_at.isoformat() if job.completed_at else None,
        'processing_time_seconds': job.processing_time_seconds,
    }), 200
```

Also add endpoint to fetch completed results:

```python
@main_bp.route('/jobs/<int:job_id>/results', methods=['GET'])
@jwt_required()
def get_job_results(job_id):
    """Get results of a completed job"""
    user_id = int(get_jwt_identity())
    
    job = Job.query.get(job_id)
    if not job:
        return jsonify({'error': 'Job not found'}), 404
    
    if job.user_id != user_id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    if job.status != JOB_STATUS_COMPLETED:
        return jsonify({'error': f'Job is {job.status}, not completed'}), 400
    
    # Get history record for processed sentences
    history = History.query.filter_by(job_id=job.id).first()
    if not history:
        return jsonify({'error': 'Results not found'}), 404
    
    return jsonify({
        'sentences': history.processed_data.get('sentences', []),
        'total_tokens': job.actual_tokens,
        'processing_time': job.processing_time_seconds,
    }), 200
```

---

### Phase 6: Optional - Deploy Flower Monitoring UI

#### Step 1: Create Flower Dockerfile
Create `backend/Dockerfile.flower`:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Expose Flower port
EXPOSE 5555

CMD ["celery", "-A", "app.celery", "flower", "--port=5555"]
```

#### Step 2: Create Flower Service on Railway
1. Railway dashboard → **"New"** → **"Empty Service"**
2. Name it `flower-monitor`
3. Set **Dockerfile Path**: `Dockerfile.flower`
4. Add environment variables: `DATABASE_URL`, `REDIS_URL`
5. Expose port `5555` (Railway will provide public URL)

#### Step 3: Access Flower UI
Navigate to the Railway-provided URL (e.g., `https://flower-monitor.up.railway.app`) to monitor:
- Active tasks
- Worker status
- Task history
- Failure rates

---

## Testing & Validation

### 1. Test Redis Connection
```bash
railway run python -c "import redis; import os; r = redis.from_url(os.getenv('REDIS_URL')); print('Redis OK' if r.ping() else 'Redis FAIL')"
```

### 2. Test Celery Worker is Listening
```bash
# In Railway logs for celery-worker service, look for:
[INFO/MainProcess] Connected to redis://...
[INFO/MainProcess] mingle: searching for neighbors
[INFO/MainProcess] celery@hostname ready.
```

### 3. Test Async Endpoint Manually
```bash
# Create a job first (via credit reservation)
curl -X POST https://api.frenchnoveltool.com/api/v1/credits/reserve \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"estimated_tokens": 5000}'

# Start async processing
curl -X POST https://api.frenchnoveltool.com/api/v1/process-pdf-async \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -F "pdf_file=@test.pdf" \
  -F "job_id=123" \
  -F "sentence_length_limit=8"

# Expected response (HTTP 202):
{
  "job_id": 123,
  "task_id": "job_123_1234567890.123",
  "status": "pending",
  "message": "PDF processing started"
}

# Poll job status
curl https://api.frenchnoveltool.com/api/v1/jobs/123/status \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"

# Expected response:
{
  "id": 123,
  "status": "processing",
  "progress_percent": 45,
  "current_step": "Processing chunk 3 of 5",
  "total_chunks": 5,
  "processed_chunks": 2
}
```

### 4. Test End-to-End with Frontend
1. Upload a PDF via the web UI
2. Verify job appears in history immediately (status: pending)
3. Watch progress bar update every 2 seconds
4. Verify completion notification appears
5. Check that sentences are available for editing/export

---

## Rollback Plan (If Issues Occur)

### If Async Processing Breaks
1. **Frontend**: Revert to synchronous endpoint temporarily
   ```typescript
   // In queries.ts, switch back to:
   const processPdfMutation = useProcessPdf(); // Old synchronous version
   ```

2. **Backend**: Keep async infrastructure running but don't use it
   - No code changes needed
   - Simply reverting frontend is enough

### If Database Schema Issues Persist
1. Connect to Railway database directly
2. Manually drop problematic columns
3. Re-run migration from scratch:
   ```bash
   railway run flask db downgrade base
   railway run flask db upgrade head
   ```

### If Redis Causes Issues
1. Remove Redis service from Railway
2. Celery will fail gracefully (tasks will error but won't crash the app)
3. Frontend will stay on synchronous processing

---

## Performance Expectations

### Before (Synchronous)
- ❌ 30-second hard timeout on Railway
- ❌ All PDFs >10 pages fail
- ❌ User gets 502 Bad Gateway errors
- ❌ No progress feedback during processing

### After (Async with Celery)
- ✅ No HTTP timeout (task runs in background worker)
- ✅ Can process PDFs of any length (1800s task limit = 30 minutes)
- ✅ Real-time progress updates every 2 seconds
- ✅ Parallel chunk processing (2x faster for large PDFs)
- ✅ Cancellation support (user can cancel long-running jobs)
- ✅ Retry logic for transient failures
- ✅ Monitoring via Flower UI

### Estimated Processing Times (Post-Deployment)
- **10-page PDF**: 30-60 seconds (1 chunk)
- **50-page PDF**: 2-3 minutes (3-5 chunks, parallel processing)
- **200-page PDF**: 10-15 minutes (15-20 chunks, parallel processing)
- **500-page PDF**: 20-30 minutes (40-50 chunks, parallel processing)

---

## Cost Implications (Railway)

### Current (Web Service Only)
- **Starter Plan**: ~$5/month
- **1 service**: Backend (web)

### After Deployment
- **Starter Plan**: ~$5/month base + usage
- **3 services**:
  1. Backend (web) - $5 base
  2. Celery Worker - ~$5-10/month (depends on usage)
  3. Redis - Free (Railway included)
  4. Flower (optional) - ~$5/month

**Total**: ~$15-20/month for full async processing infrastructure

**Alternative**: Use Railway's Hobby plan ($10/month) which includes:
- Higher resource limits
- More generous free tier
- Multiple services included

---

## Success Criteria

### Phase 1: Database Fix
- [ ] All Job model columns exist in production database
- [ ] No more "column does not exist" errors in logs
- [ ] Can create jobs with async fields (celery_task_id, progress_percent, etc.)

### Phase 2: Redis Deployment
- [ ] Redis service running on Railway
- [ ] `REDIS_URL` environment variable set
- [ ] Backend can connect to Redis (verified with ping)

### Phase 3: Celery Worker Deployment
- [ ] Worker service running on Railway
- [ ] Logs show "celery@hostname ready"
- [ ] Worker connected to same Redis and PostgreSQL as web service

### Phase 4: Frontend Update
- [ ] `useProcessPdfAsync()` hook implemented
- [ ] `useJobStatus()` polling hook implemented
- [ ] Page component shows progress bar during processing
- [ ] Notifications for completion/failure

### Phase 5: Backend API
- [ ] `/jobs/<id>/status` endpoint returns job progress
- [ ] `/jobs/<id>/results` endpoint returns processed sentences
- [ ] Proper authorization checks (user owns job)

### Phase 6: End-to-End Testing
- [ ] Can upload PDF and receive job_id immediately (HTTP 202)
- [ ] Progress updates every 2 seconds
- [ ] Large PDF (100+ pages) completes without timeout
- [ ] Processed sentences available after completion
- [ ] Can export results to Google Sheets

---

## Timeline

### Immediate (Today)
1. ✅ **Fix database schema** (30 minutes)
2. ✅ **Deploy Redis** (10 minutes)
3. ✅ **Deploy Celery worker** (1 hour)

### Short-term (This Week)
4. ✅ **Update frontend to async endpoint** (2-3 hours)
5. ✅ **Add job status API endpoints** (1 hour)
6. ✅ **Test end-to-end** (1 hour)

### Optional (Next Week)
7. 🔲 **Deploy Flower monitoring** (30 minutes)
8. 🔲 **Add job cancellation UI** (1 hour)
9. 🔲 **Optimize chunk sizing** (2 hours)

---

## Next Steps

**Start with Phase 1** - Fix the database schema first, as this is blocking job creation. Then proceed sequentially through the phases.

Run this command to begin:
```bash
railway connect postgres
```

Once connected, paste the ALTER TABLE commands from Phase 1, Option A.

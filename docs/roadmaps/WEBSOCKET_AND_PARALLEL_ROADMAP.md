# WebSocket Real-Time Updates & Parallel Chunk Execution Roadmap

**Status:** Planning  
**Priority:** High  
**Estimated Effort:** 2-3 days  
**Dependencies:** Flask, Celery, Next.js 15, React Query v5, Gunicorn, eventlet

---

## Codebase Analysis Summary

### Current Architecture
- **Backend**: Flask 3.x + Celery + SQLAlchemy with async job processing
- **Frontend**: Next.js 15 (App Router) + React Query v5 + Material-UI v7
- **Database**: PostgreSQL (Supabase) with `Job` and `History` models
- **Jobs System**: Full credit-based async processing with chunking support
- **Current Polling**: `useJobStatus` hook polls `/jobs/{id}` every 2s until completion
- **Gunicorn**: Currently uses default sync workers (needs eventlet for WebSocket)

### Key Findings
1. **Job Model Already Comprehensive**: Has `history_id` FK, `chunk_results` JSON, progress tracking
2. **History Model Limitation**: Stores only metadata (no `sentences` field) - needs schema update
3. **Sequential Chunk Processing**: Current implementation processes chunks one-by-one in `tasks.py`
4. **No WebSocket Infrastructure**: No Flask-SocketIO or socket event handlers
5. **Sync Job Creation**: `process_pdf_async_endpoint` already handles job creation and task dispatch

---

## Overview

This roadmap covers three major improvements:

1. **WebSocket-Based Job Progress Updates**: Replace polling (`GET /api/v1/jobs/{id}`) with real-time WebSocket events for instant progress updates.
2. **Parallel Chunk Execution**: Refactor Celery task orchestration to process PDF chunks in parallel instead of sequentially.
3. **Jobs-to-History Integration**: Automatically save completed job results (including sentences) to History for persistent access and delayed export.

---

## Mission 1: WebSocket-Based Job Progress Updates

### Goals
- Eliminate redundant polling requests to `/api/v1/jobs/{id}` (every 2 seconds).
- Push real-time progress updates to connected clients as chunks complete.
- Reduce server load and improve frontend responsiveness.

### Architecture

```
┌─────────────────┐         WebSocket         ┌──────────────────┐
│  Next.js Client │◄──────────────────────────►│  Flask SocketIO  │
│  (socket.io)    │    job_progress events     │   (eventlet)     │
└─────────────────┘                            └──────────────────┘
                                                        │
                                                        │ emits progress
                                                        ▼
                                               ┌──────────────────┐
                                               │  Celery Worker   │
                                               │  (tasks.py)      │
                                               └──────────────────┘
```

---

## Phase 1: Backend WebSocket Setup

### Step 1.1: Install Dependencies

**File:** `backend/requirements.txt`

```diff
+ flask-socketio==5.3.6
+ eventlet==0.36.1
+ python-socketio==5.11.1
```

**Action:**
```bash
cd backend
pip install flask-socketio==5.3.6 eventlet==0.36.1
```

---

### Step 1.2: Initialize SocketIO in Application Factory

**File:** `backend/app/__init__.py`

**Import at top:**
```python
from flask_socketio import SocketIO
```

**After initializing other extensions (db, jwt, migrate, etc.):**
```python
# Initialize extensions
db = SQLAlchemy()
migrate = Migrate()
jwt = JWTManager()
limiter = Limiter(key_func=get_remote_address)
socketio = SocketIO(cors_allowed_origins="*")  # Add this
```

**In `create_app()` function, after `limiter.init_app(app)`:**
```python
def create_app():
    app = Flask(__name__)
    # ...existing config loading...
    
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    limiter.init_app(app)
    socketio.init_app(app, 
                      cors_allowed_origins=app.config.get('CORS_ORIGINS', '*'),
                      message_queue=app.config.get('CELERY_BROKER_URL'),  # For multi-worker sync
                      async_mode='eventlet')
    
    # ...rest of setup...
    return app
```

**Export socketio:**
```python
from app import socketio  # Make it importable
```

---

### Step 1.3: Create SocketIO Event Handlers

**File:** `backend/app/socket_events.py` (new file)

```python
"""WebSocket event handlers for real-time job updates"""
from flask import request
from flask_socketio import emit, join_room, leave_room, disconnect
from flask_jwt_extended import decode_token
from app import socketio
from app.models import Job
import logging

logger = logging.getLogger(__name__)


@socketio.on('connect')
def handle_connect(auth):
    """Handle client connection with JWT authentication"""
    try:
        # Extract JWT from auth dict or query string
        token = auth.get('token') if auth else request.args.get('token')
        
        if not token:
            logger.warning('WebSocket connection attempt without token')
            disconnect()
            return False
        
        # Verify JWT token
        decoded = decode_token(token)
        user_id = int(decoded['sub'])
        
        logger.info(f'WebSocket connected: user_id={user_id}')
        return True
        
    except Exception as e:
        logger.error(f'WebSocket auth failed: {e}')
        disconnect()
        return False


@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnect"""
    logger.info('WebSocket client disconnected')


@socketio.on('join_job')
def handle_join_job(data):
    """Subscribe client to job-specific room for progress updates
    
    Args:
        data: {'job_id': int, 'token': str}
    """
    try:
        job_id = data.get('job_id')
        token = data.get('token')
        
        if not job_id or not token:
            emit('error', {'message': 'Missing job_id or token'})
            return
        
        # Verify user owns this job
        decoded = decode_token(token)
        user_id = int(decoded['sub'])
        
        job = Job.query.get(job_id)
        if not job:
            emit('error', {'message': f'Job {job_id} not found'})
            return
            
        if job.user_id != user_id:
            emit('error', {'message': 'Unauthorized access to job'})
            return
        
        # Join job-specific room
        room = f'job_{job_id}'
        join_room(room)
        
        logger.info(f'User {user_id} joined room {room}')
        
        # Send initial job state
        emit('job_progress', job.to_dict(), room=room)
        
    except Exception as e:
        logger.error(f'Error joining job room: {e}')
        emit('error', {'message': 'Failed to join job room'})


@socketio.on('leave_job')
def handle_leave_job(data):
    """Unsubscribe client from job room
    
    Args:
        data: {'job_id': int}
    """
    try:
        job_id = data.get('job_id')
        if not job_id:
            return
        
        room = f'job_{job_id}'
        leave_room(room)
        logger.info(f'Client left room {room}')
        
    except Exception as e:
        logger.error(f'Error leaving job room: {e}')


def emit_job_progress(job_id, progress_data):
    """Emit job progress update to all clients in job room
    
    Args:
        job_id: Job ID
        progress_data: Dict with progress info (status, progress_percent, current_step, etc.)
    """
    room = f'job_{job_id}'
    socketio.emit('job_progress', progress_data, room=room, namespace='/')
    logger.debug(f'Emitted progress to {room}: {progress_data}')
```

---

### Step 1.4: Register SocketIO Handlers in App Factory

**File:** `backend/app/__init__.py`

**At the end of `create_app()`, before `return app`:**
```python
def create_app():
    # ...existing setup...
    
    # Register blueprints
    from app.routes import main_bp
    from app.auth_routes import auth_bp
    from app.credit_routes import credit_bp
    app.register_blueprint(main_bp, url_prefix='/api/v1')
    app.register_blueprint(auth_bp, url_prefix='/api/v1/auth')
    app.register_blueprint(credit_bp, url_prefix='/api/v1')
    
    # Register SocketIO event handlers
    from app import socket_events  # Import to register handlers
    
    return app
```

---

### Step 1.5: Emit Progress Updates from Celery Tasks

**File:** `backend/app/tasks.py`

**Import at top:**
```python
from app.socket_events import emit_job_progress
```

**Update progress emission points (replace `safe_db_commit(db)` calls with both commit + emit):**

**Example 1: After updating job status to processing:**
```python
job.status = JOB_STATUS_PROCESSING
job.started_at = datetime.now(timezone.utc)
job.current_step = "Analyzing PDF"
job.progress_percent = 5
safe_db_commit(db)

# Emit WebSocket update
emit_job_progress(job_id, {
    'job_id': job_id,
    'status': job.status,
    'progress_percent': job.progress_percent,
    'current_step': job.current_step,
})
```

**Example 2: After processing each chunk:**
```python
job.processed_chunks = idx
if job.total_chunks:
    pct = 15 + int((idx / job.total_chunks) * 60)
    job.progress_percent = max(job.progress_percent or 15, pct)
    job.current_step = f"Processed {idx}/{job.total_chunks} chunks"
safe_db_commit(db)

# Emit WebSocket update
emit_job_progress(job_id, {
    'job_id': job_id,
    'status': job.status,
    'progress_percent': job.progress_percent,
    'current_step': job.current_step,
    'processed_chunks': job.processed_chunks,
    'total_chunks': job.total_chunks,
})
```

**Example 3: On job completion:**
```python
job.status = JOB_STATUS_COMPLETED
job.progress_percent = 100
job.current_step = "Completed"
job.completed_at = datetime.now(timezone.utc)
safe_db_commit(db)

# Emit final update
emit_job_progress(job_id, job.to_dict())
```

**Example 4: On job failure:**
```python
job.status = JOB_STATUS_FAILED
job.error_message = "All chunks failed to process..."
job.completed_at = datetime.now(timezone.utc)
safe_db_commit(db)

# Emit failure update
emit_job_progress(job_id, job.to_dict())
```

---

### Step 1.6: Update Gunicorn to Use Eventlet Worker

**File:** `backend/Dockerfile.web`

**Update CMD line:**
```dockerfile
CMD ["gunicorn", "--worker-class", "eventlet", "-w", "1", "--bind", "0.0.0.0:${PORT:-5000}", "--timeout", "300", "--access-logfile", "-", "--error-logfile", "-", "run:app"]
```

**Note:** Use `-w 1` for eventlet (single worker with async I/O). For scaling, use multiple instances behind a load balancer.

---

### Step 1.7: Update run.py for Local Development

**File:** `backend/run.py`

```python
from app import create_app, socketio

app = create_app()

if __name__ == '__main__':
    # Use socketio.run() instead of app.run() for WebSocket support
    socketio.run(app, debug=True, port=5000, allow_unsafe_werkzeug=True)
```

---

### Step 1.8: Update Railway Configuration

**File:** `backend/railway.json`

**Remove `startCommand` if present (let Docker CMD handle it):**
```json
{
  "$schema": "https://railway.app/railway.schema.json",
  "build": {
    "builder": "DOCKERFILE",
    "dockerfilePath": "backend/Dockerfile.web"
  },
  "deploy": {
    "numReplicas": 1,
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 3,
    "healthcheckPath": "/api/v1/health",
    "healthcheckTimeout": 30
  }
}
```

---

## Phase 2: Frontend WebSocket Integration

### Step 2.1: Install Socket.IO Client

**File:** `frontend/package.json`

```bash
cd frontend
npm install socket.io-client@4.7.2
```

---

### Step 2.2: Create WebSocket Hook

**File:** `frontend/src/lib/useJobWebSocket.ts` (new file)

```typescript
/**
 * Hook for WebSocket-based job progress updates
 */
import { useEffect, useState, useCallback, useRef } from 'react';
import { io, Socket } from 'socket.io-client';
import { Job } from './api';

interface UseJobWebSocketOptions {
  jobId: number | null;
  token: string | null;
  enabled?: boolean;
  onProgress?: (job: Partial<Job>) => void;
  onComplete?: (job: Job) => void;
  onError?: (job: Job) => void;
}

interface UseJobWebSocketResult {
  job: Partial<Job> | null;
  connected: boolean;
  error: string | null;
}

export function useJobWebSocket({
  jobId,
  token,
  enabled = true,
  onProgress,
  onComplete,
  onError,
}: UseJobWebSocketOptions): UseJobWebSocketResult {
  const [job, setJob] = useState<Partial<Job> | null>(null);
  const [connected, setConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const socketRef = useRef<Socket | null>(null);

  useEffect(() => {
    if (!enabled || !jobId || !token) {
      return;
    }

    // Connect to WebSocket server
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:5000';
    const socket = io(apiUrl, {
      auth: { token },
      query: { token },
      transports: ['websocket', 'polling'], // Fallback to polling if WebSocket fails
    });

    socketRef.current = socket;

    // Connection handlers
    socket.on('connect', () => {
      console.log('WebSocket connected');
      setConnected(true);
      setError(null);

      // Join job room
      socket.emit('join_job', { job_id: jobId, token });
    });

    socket.on('disconnect', () => {
      console.log('WebSocket disconnected');
      setConnected(false);
    });

    socket.on('connect_error', (err) => {
      console.error('WebSocket connection error:', err);
      setError('Failed to connect to server');
      setConnected(false);
    });

    // Job progress updates
    socket.on('job_progress', (data: Partial<Job>) => {
      console.log('Job progress update:', data);
      setJob(data);

      if (onProgress) {
        onProgress(data);
      }

      // Check terminal states
      if (data.status === 'completed' && onComplete) {
        onComplete(data as Job);
      } else if (data.status === 'failed' && onError) {
        onError(data as Job);
      }
    });

    // Error events
    socket.on('error', (data: { message: string }) => {
      console.error('WebSocket error:', data.message);
      setError(data.message);
    });

    // Cleanup
    return () => {
      if (socketRef.current) {
        socketRef.current.emit('leave_job', { job_id: jobId });
        socketRef.current.disconnect();
        socketRef.current = null;
      }
    };
  }, [enabled, jobId, token, onProgress, onComplete, onError]);

  return {
    job,
    connected,
    error,
  };
}
```

---

### Step 2.3: Update JobProgressDialog to Use WebSocket

**File:** `frontend/src/components/JobProgressDialog.tsx`

**Replace `useJobPolling` with `useJobWebSocket`:**

```typescript
import { useJobWebSocket } from '@/lib/useJobWebSocket';
import { useAuth } from './AuthContext';

export default function JobProgressDialog({
  jobId,
  open,
  onClose,
  onComplete,
  onError,
}: JobProgressDialogProps) {
  const { user } = useAuth();
  const [cancelling, setCancelling] = React.useState(false);

  // Use WebSocket instead of polling
  const { job, connected, error: wsError } = useJobWebSocket({
    jobId,
    token: user?.token || null,
    enabled: open && jobId !== null,
    onComplete: (completedJob) => {
      if (onComplete) {
        onComplete(completedJob);
      }
    },
    onError: (failedJob) => {
      if (onError) {
        onError(failedJob);
      }
    },
  });

  // Rest of component stays the same...
  const canCancel = job && ['pending', 'processing'].includes(job.status || '');
  const isTerminal = job && ['completed', 'failed', 'cancelled'].includes(job.status || '');
  const progressPercent = job?.progress_percent ?? 0;

  // ...existing render code...
}
```

---

### Step 2.4: Add WebSocket Status Indicator (Optional)

**In `JobProgressDialog` render:**

```tsx
<DialogTitle>
  <Stack direction="row" alignItems="center" spacing={2}>
    {getStatusIcon()}
    <Typography variant="h6">PDF Processing</Typography>
    <Chip
      label={job?.status ?? 'initializing'}
      color={getStatusColor()}
      size="small"
    />
    {/* WebSocket connection indicator */}
    {connected && (
      <Tooltip title="Real-time updates active">
        <Chip icon={<WifiIcon />} label="Live" color="success" size="small" />
      </Tooltip>
    )}
  </Stack>
</DialogTitle>
```

---

### Step 2.5: Update Main Page to Use WebSocket (Optional)

**File:** `frontend/src/app/page.tsx`

**If you want to replace polling on the main page too:**

```typescript
// Replace useJobStatus with useJobWebSocket
const { job: jobData, connected } = useJobWebSocket({
  jobId: pollingJobId,
  token: user?.token || null,
  enabled: !!pollingJobId,
});

// Update useEffect to use jobData instead of jobStatus.data
useEffect(() => {
  if (!jobData) return;

  const status = jobData.status;
  const progress = jobData.progress_percent || 0;
  const currentStep = jobData.current_step || 'Processing...';

  // ...rest of logic...
}, [jobData?.status, jobData?.progress_percent, jobData?.current_step, pollingJobId]);
```

---

## Phase 3: Testing & Deployment

### Step 3.1: Local Testing

**Backend:**
```bash
cd backend
python run.py  # Should show "Socket.IO started"
```

**Frontend:**
```bash
cd frontend
npm run dev
```

**Test:**
1. Upload a PDF and start a job.
2. Open browser DevTools → Network → WS (WebSocket tab).
3. Verify WebSocket connection established.
4. Watch for `job_progress` events in real time.
5. Confirm progress bar updates instantly.

---

### Step 3.2: Update Environment Variables

**Railway (Backend):**
- No new env vars needed (uses existing `CELERY_BROKER_URL` for message queue sync).

**Vercel (Frontend):**
- Ensure `NEXT_PUBLIC_API_URL` points to your Railway backend (e.g., `https://api.frenchnoveltool.com`).

---

### Step 3.3: Deploy Backend

```bash
git add .
git commit -m "feat: add WebSocket support for real-time job progress"
git push origin master
```

Railway will auto-deploy with the new Dockerfile CMD (eventlet worker).

---

### Step 3.4: Deploy Frontend

```bash
cd frontend
vercel --prod
```

---

### Step 3.5: Verify Production

1. Open production frontend.
2. Upload a PDF.
3. Check browser DevTools → Network → WS.
4. Confirm WebSocket connects to `wss://api.frenchnoveltool.com`.
5. Verify progress updates in real time.

---

## Mission 2: Parallel Chunk Execution

### Goals
- Process multiple PDF chunks concurrently instead of sequentially.
- Reduce total job processing time (e.g., 4 chunks: 2 minutes → 30 seconds).
- Utilize Celery worker pool for parallel task execution.

---

## Phase 4: Refactor Celery Orchestration

### Step 4.1: Update Worker Concurrency

**File:** `backend/Dockerfile.worker` (or Railway worker config)

**Update Celery startup command:**
```dockerfile
CMD ["celery", "-A", "app.celery_app", "worker", "--loglevel=info", "--concurrency=4"]
```

**Or in `docker-compose.dev.yml`:**
```yaml
celery-worker:
  command: celery -A app.celery_app worker --loglevel=info --concurrency=4
```

---

### Step 4.2: Refactor process_pdf_async to Use Celery Chord

**File:** `backend/app/tasks.py`

**Replace sequential loop with parallel chord:**

**Import at top:**
```python
from celery import chord
```

**Replace the chunk processing section:**

```python
# OLD (sequential):
# else:
#     chunk_results = []
#     total = len(chunks)
#     for idx, chunk in enumerate(chunks, start=1):
#         result = process_chunk.run(chunk, user_id, settings)
#         chunk_results.append(result)
#         # ...update progress...

# NEW (parallel with chord):
else:
    # Create a chord: group of chunk tasks + callback to finalize
    chunk_tasks = [
        process_chunk.s(chunk, user_id, settings)
        for chunk in chunks
    ]
    
    # Use chord to process all chunks in parallel, then call finalize_job
    callback = finalize_job_results.s(job_id=job_id)
    chord_result = chord(chunk_tasks)(callback)
    
    logger.info(f"Job {job_id}: dispatched {len(chunks)} chunks in parallel")
    
    # Return early; finalize_job_results will complete the job
    return {
        'status': 'dispatched',
        'message': f'{len(chunks)} chunks processing in parallel',
        'job_id': job_id
    }
```

---

### Step 4.3: Create Finalize Job Callback Task

**File:** `backend/app/tasks.py`

**Add new task after `process_chunk`:**

```python
@get_celery().task(bind=True, name='app.tasks.finalize_job_results')
def finalize_job_results(self, chunk_results, job_id):
    """
    Finalize job after all chunks complete (chord callback).
    
    Args:
        chunk_results: List of results from all process_chunk tasks
        job_id: Job ID to finalize
    """
    db = get_db()
    Job, User = get_models()
    JOB_STATUS_PROCESSING, JOB_STATUS_COMPLETED, JOB_STATUS_FAILED, _ = get_constants()
    
    try:
        logger.info(f"Job {job_id}: finalizing {len(chunk_results)} chunk results")
        
        # Merge chunk results
        all_sentences = merge_chunk_results(chunk_results)
        
        # Calculate metrics
        total_tokens = sum(r.get('tokens', 0) for r in chunk_results if r.get('status') == 'success')
        failed_chunks = [r['chunk_id'] for r in chunk_results if r.get('status') == 'failed']
        success_count = len([r for r in chunk_results if r.get('status') == 'success'])
        
        # Update job with results
        job = Job.query.get(job_id)
        if not job:
            raise ValueError(f"Job {job_id} not found")
        
        if success_count == 0:
            job.status = JOB_STATUS_FAILED
            job.current_step = "Failed"
            job.error_message = "All chunks failed to process. Check API credentials or PDF content."
        else:
            job.status = JOB_STATUS_COMPLETED
            job.current_step = "Completed"
        
        job.progress_percent = 100
        job.actual_tokens = total_tokens
        job.gemini_tokens_used = total_tokens
        job.gemini_api_calls = success_count
        job.completed_at = datetime.now(timezone.utc)
        job.chunk_results = chunk_results
        job.failed_chunks = failed_chunks if failed_chunks else None
        
        # Calculate processing time
        if job.started_at:
            processing_time = (job.completed_at - job.started_at).total_seconds()
            job.processing_time_seconds = int(processing_time)
        
        safe_db_commit(db)
        
        # Emit final WebSocket update
        emit_job_progress(job_id, job.to_dict())
        
        logger.info(f"Job {job_id}: finalized status={job.status} sentences={len(all_sentences)}")
        
        return {
            'status': 'success',
            'sentences': all_sentences,
            'total_tokens': total_tokens,
            'chunks_processed': len(chunk_results),
            'failed_chunks': failed_chunks
        }
        
    except Exception as e:
        logger.error(f"Job {job_id}: finalization failed: {e}")
        
        # Mark job as failed
        try:
            job = Job.query.get(job_id)
            if job:
                job.status = JOB_STATUS_FAILED
                job.error_message = f"Finalization error: {str(e)[:512]}"
                job.completed_at = datetime.now(timezone.utc)
                safe_db_commit(db)
                emit_job_progress(job_id, job.to_dict())
        except Exception:
            pass
        
        raise
```

---

### Step 4.4: Update process_chunk to Emit Progress

**File:** `backend/app/tasks.py`

**In `process_chunk`, after successful processing:**

```python
@get_celery().task(bind=True, name='app.tasks.process_chunk')
def process_chunk(self, chunk_info: Dict, user_id: int, settings: Dict) -> Dict:
    """Process a single PDF chunk."""
    try:
        # ...existing chunk processing logic...
        
        result = {
            'chunk_id': chunk_info['chunk_id'],
            'sentences': result['sentences'],
            'tokens': result.get('tokens', 0),
            'start_page': chunk_info['start_page'],
            'end_page': chunk_info['end_page'],
            'status': 'success'
        }
        
        # Emit progress update (optional, for per-chunk updates)
        # Note: job_id not directly available; would need to pass it or query
        # For now, finalize_job_results will emit final update
        
        return result
        
    except Exception as e:
        logger.error(f"Chunk {chunk_info['chunk_id']} failed: {e}")
        return {
            'chunk_id': chunk_info['chunk_id'],
            'status': 'failed',
            'error': str(e),
            'start_page': chunk_info['start_page'],
            'end_page': chunk_info['end_page']
        }
```

---

### Step 4.5: Handle Single-Chunk Case

**File:** `backend/app/tasks.py`

**Keep single-chunk path synchronous (no chord overhead):**

```python
if len(chunks) == 1:
    # Single chunk - process directly (call underlying function)
    logger.info("Job %s: processing single chunk %s", job_id, chunks[0].get('file_path'))
    result = process_chunk.run(chunks[0], user_id, settings)
    chunk_results = [result]
    
    # Continue with existing finalization logic inline
    all_sentences = merge_chunk_results(chunk_results)
    # ...existing completion code...
    
else:
    # Multiple chunks - use chord for parallel processing
    # ...chord code from Step 4.2...
```

---

## Phase 5: Testing & Validation

### Step 5.1: Unit Test Chord Logic

**File:** `backend/tests/test_async_processing.py`

**Add test for parallel execution:**

```python
def test_parallel_chunk_processing():
    """Test that multiple chunks are dispatched in parallel"""
    from app.tasks import process_pdf_async
    from unittest.mock import patch, MagicMock
    
    with patch('app.tasks.chord') as mock_chord:
        # Mock chord to verify it's called
        mock_chord_result = MagicMock()
        mock_chord.return_value = mock_chord_result
        
        # Call with multi-chunk PDF
        # ...test setup...
        
        # Verify chord was called with multiple chunk tasks
        assert mock_chord.called
        chunk_tasks = mock_chord.call_args[0][0]
        assert len(chunk_tasks) > 1
```

---

### Step 5.2: Manual Testing

**Test multi-chunk PDF:**
1. Upload a 60+ page PDF (should create 3+ chunks).
2. Watch Celery worker logs for parallel execution:
   ```
   [INFO] Job 59: chunk 1 status=success
   [INFO] Job 59: chunk 2 status=success  # Overlapping timestamps
   [INFO] Job 59: chunk 3 status=success
   ```
3. Verify total processing time is reduced (e.g., 3 chunks × 20s → ~25s total).

**Compare with sequential:**
- Before: chunks processed at T+0s, T+20s, T+40s (total 60s)
- After: chunks processed at T+0s, T+0s, T+0s (total ~20s)

---

### Step 5.3: Load Testing

**Optional: Stress test with concurrent jobs:**

```bash
# Start multiple jobs simultaneously
for i in {1..5}; do
  curl -X POST https://api.frenchnoveltool.com/api/v1/process-pdf-async \
    -H "Authorization: Bearer $TOKEN" \
    -F "pdf_file=@test.pdf" &
done
```

Monitor:
- Worker concurrency (should handle 4 chunks at once).
- Queue depth in Redis/RabbitMQ.
- Response times and error rates.

---

## Rollout Plan

### Week 1: WebSocket Implementation
- [ ] Day 1-2: Backend setup (Steps 1.1-1.7)
- [ ] Day 3: Frontend integration (Steps 2.1-2.3)
- [ ] Day 4: Testing and debugging
- [ ] Day 5: Deploy to production

### Week 2: Parallel Execution
- [ ] Day 1-2: Refactor orchestration (Steps 4.1-4.4)
- [ ] Day 3: Testing (Steps 5.1-5.2)
- [ ] Day 4: Load testing and optimization
- [ ] Day 5: Deploy to production

---

## Success Metrics

### WebSocket
- ✅ Polling requests to `/jobs/{id}` reduced by 95%+
- ✅ Progress updates appear < 100ms after backend state change
- ✅ Server CPU/memory usage reduced by 20-30%
- ✅ No increase in failed connections (maintain 99%+ WebSocket uptime)

### Parallel Execution
- ✅ Multi-chunk jobs complete 50-70% faster
- ✅ Worker utilization increases from 25% to 80%+
- ✅ No increase in chunk failure rate
- ✅ Celery queue depth stays < 10 under normal load

---

## Rollback Plan

### If WebSocket Issues
1. Revert Dockerfile CMD to standard Gunicorn worker.
2. Re-enable polling on frontend (keep `useJobStatus` hook).
3. Remove SocketIO imports from backend.

### If Parallel Execution Issues
1. Revert `process_pdf_async` to sequential loop.
2. Set worker concurrency back to 1.
3. Remove chord and finalize_job_results task.

---

---

## Mission 3: Jobs to History Integration

### Goals
- Automatically save completed jobs to the History table for persistent access.
- Allow users to view processed sentences from historical jobs.
- Enable exporting historical job results to Google Sheets (if not already exported).
- Provide a unified "Processing History" view combining both sync and async jobs.

### Architecture

```
┌─────────────────┐
│  Completed Job  │
│   (Job model)   │
└────────┬────────┘
         │ on completion
         ▼
┌─────────────────┐
│ Create History  │
│     Entry       │
└────────┬────────┘
         │
         ▼
┌─────────────────┐         ┌──────────────────┐
│ History Table   │◄────────┤  Frontend UI     │
│ - sentences     │         │  - View Results  │
│ - settings      │         │  - Export Dialog │
│ - export status │         └──────────────────┘
└─────────────────┘
```

---

## Phase 6: Backend History Integration

### Step 6.1: Add Sentences Storage to History Model

**File:** `backend/app/models.py`

**Current State:** 
- `Job` model already has `history_id` field (line 151)
- `History` model has `job_id` field for reverse relationship (line 49)
- `History` model lacks `sentences` field to store processed results

**Add to `History` model after `processing_settings` field (around line 58):**
```python
class History(db.Model):
    # ...existing fields...
    processing_settings = db.Column(db.JSON)  # Store all settings for duplicate/retry
    
    # NEW: Store processed sentences for viewing and re-export
    sentences = db.Column(db.JSON, nullable=True)  # Array of {normalized: str, original: str}
    exported_to_sheets = db.Column(db.Boolean, default=False, nullable=False)
    export_sheet_url = db.Column(db.String(256), nullable=True)  # Alias for spreadsheet_url
```

**Update `to_dict()` method:**
```python
def to_dict(self):
    return {
        'id': self.id,
        'job_id': self.job_id,
        'timestamp': self.timestamp.isoformat() + 'Z',
        'original_filename': self.original_filename,
        'processed_sentences_count': self.processed_sentences_count,
        'spreadsheet_url': self.spreadsheet_url,
        'error_message': self.error_message,
        'failed_step': self.failed_step,
        'error_code': self.error_code,
        'error_details': self.error_details,
        'settings': self.processing_settings,
        # NEW fields
        'sentences': self.sentences,
        'exported_to_sheets': self.exported_to_sheets,
        'export_sheet_url': self.export_sheet_url or self.spreadsheet_url,
    }
```

**Run migration:**
```bash
cd backend
flask db migrate -m "Add sentences and export tracking to History model"
flask db upgrade
```

---

### Step 6.2: Save Job Results to History on Completion

**Current State:**
- Sync endpoint (`/process-pdf`) already creates History via `history_service.add_entry()` (line 239)
- Async endpoint (`/process-pdf-async`) does NOT create History - only Job record
- Job completion happens in `tasks.py:process_pdf_async` (line 207-425)

**Option A: Update tasks.py to create History (Recommended)**

**File:** `backend/app/tasks.py`

**After job completion (around line 395), add History creation:**
```python
# Around line 392-400 (after job.status = JOB_STATUS_COMPLETED)
if success_count > 0 and job.status == JOB_STATUS_COMPLETED:
    # Create History entry from completed job
    try:
        from app.models import History
        from app.services.history_service import HistoryService
        
        # Format sentences for history storage
        formatted_sentences = []
        for sentence in all_sentences:
            if isinstance(sentence, dict):
                formatted_sentences.append({
                    'normalized': sentence.get('normalized', ''),
                    'original': sentence.get('original', sentence.get('normalized', ''))
                })
            else:
                formatted_sentences.append({
                    'normalized': str(sentence),
                    'original': str(sentence)
                })
        
        # Create history entry
        history_entry = History(
            user_id=job.user_id,
            job_id=job.id,
            original_filename=job.original_filename,
            processed_sentences_count=len(all_sentences),
            sentences=formatted_sentences,
            processing_settings=job.processing_settings,
            exported_to_sheets=False,
            spreadsheet_url=None,
        )
        db.session.add(history_entry)
        db.session.flush()  # Get history.id
        
        # Link job to history
        job.history_id = history_entry.id
        safe_db_commit(db)
        
        logger.info(f"Job {job_id}: created history entry {history_entry.id} with {len(all_sentences)} sentences")
    except Exception as e:
        logger.error(f"Job {job_id}: failed to create history entry: {e}")
        # Don't fail the job if history creation fails
```

**Option B: Add endpoint to retrieve job results later**
Create `GET /jobs/{id}/results` to fetch `chunk_results` from Job model and convert to sentences on-demand.

---

### Step 6.3: Add History Detail Endpoint

**File:** `backend/app/routes.py`

**Current State:**
- `GET /history` exists (line 435) - returns list without sentences
- `DELETE /history/{id}` exists (line 458) - deletes entry
- No detail endpoint yet

**Add new endpoint after `get_history()` (around line 456):**
```python
@main_bp.route('/history/<int:entry_id>', methods=['GET'])
@jwt_required()
def get_history_detail(entry_id):
    """Get detailed history entry including full sentences"""
    try:
        user_id = int(get_jwt_identity())
        user = User.query.get(user_id)
        
        if not user or not user.is_active:
            return jsonify({'error': 'User not found or inactive'}), 401
        
        # Get entry using history_service
        entry = history_service.get_entry_by_id(entry_id, user_id)
        
        if not entry:
            return jsonify({'error': 'History entry not found'}), 404
        
        # Return full details including sentences
        response = entry.to_dict()
        return jsonify(response), 200
        
    except Exception as e:
        current_app.logger.exception('Failed to get history detail')
        return jsonify({'error': str(e)}), 500
```

---

### Step 6.4: Add Export from History Endpoint

**File:** `backend/app/routes.py`

**Add endpoint to export historical results:**
```python
@main_bp.route('/history/<int:entry_id>/export', methods=['POST'])
@jwt_required()
@limiter.limit("20 per hour")
def export_history_to_sheets(entry_id):
    """Export historical job results to Google Sheets"""
    user_id = int(get_jwt_identity())
    user = User.query.get(user_id)
    
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    entry = History.query.get_or_404(entry_id)
    
    if entry.user_id != user_id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    if entry.exported_to_sheets:
        return jsonify({
            'message': 'Already exported',
            'sheet_url': entry.export_sheet_url
        }), 200
    
    if not entry.sentences:
        return jsonify({'error': 'No sentences to export'}), 400
    
    try:
        # Use GoogleSheetsService to export
        from app.services.google_sheets_service import GoogleSheetsService
        from app.services.auth_service import AuthService
        
        auth_service = AuthService()
        credentials = auth_service.get_user_credentials(user)
        
        sheets_service = GoogleSheetsService(credentials)
        
        # Create spreadsheet
        spreadsheet_title = f"{entry.original_filename} - Processed"
        sheet_url = sheets_service.create_spreadsheet_with_sentences(
            entry.sentences,
            spreadsheet_title
        )
        
        # Update history entry
        entry.exported_to_sheets = True
        entry.export_sheet_url = sheet_url
        db.session.commit()
        
        return jsonify({
            'message': 'Export successful',
            'sheet_url': sheet_url
        }), 200
        
    except Exception as e:
        current_app.logger.exception(f'Export failed for history entry {entry_id}')
        return jsonify({'error': str(e)}), 500
```

---

### Step 6.5: Update History Model's to_dict() for Frontend

**File:** `backend/app/models.py`

**Current State:** History.to_dict() already returns most fields (line 64-76)

**Update to include sentence count and job link:**
```python
def to_dict(self):
    return {
        'id': self.id,
        'job_id': self.job_id,
        'timestamp': self.timestamp.isoformat() + 'Z',
        'original_filename': self.original_filename,
        'processed_sentences_count': self.processed_sentences_count,
        'spreadsheet_url': self.spreadsheet_url,
        'error_message': self.error_message,
        'failed_step': self.failed_step,
        'error_code': self.error_code,
        'error_details': self.error_details,
        'settings': self.processing_settings,
        # NEW: Include sentences and export status
        'sentences': self.sentences,
        'sentence_count': len(self.sentences) if self.sentences else self.processed_sentences_count or 0,
        'exported_to_sheets': self.exported_to_sheets,
        'export_sheet_url': self.export_sheet_url or self.spreadsheet_url,
    }
```

**Note:** Existing `GET /history` endpoint (line 435-455) already uses `entry.to_dict()`, so no changes needed there.

---

## Phase 7: Frontend History Enhancements

### Step 7.1: Add History Detail API Function

**File:** `frontend/src/lib/api.ts`

**Add new API functions:**
```typescript
export interface HistoryDetail {
  id: number;
  original_filename: string;
  created_at: string;
  processing_settings: Record<string, any>;
  gemini_tokens_used: number;
  processing_time_seconds: number;
  sentences: Array<{ normalized: string; original: string }>;
  exported_to_sheets: boolean;
  export_sheet_url: string | null;
  status: string;
}

export async function getHistoryDetail(entryId: number): Promise<HistoryDetail> {
  const response = await api.get(`/history/${entryId}`);
  return response.data;
}

export async function exportHistoryToSheets(entryId: number): Promise<{ sheet_url: string }> {
  const response = await api.post(`/history/${entryId}/export`);
  return response.data;
}
```

---

### Step 7.2: Add React Query Hooks for History Detail

**File:** `frontend/src/lib/queries.ts`

**Add hooks:**
```typescript
export function useHistoryDetail(entryId: number | null) {
  return useQuery({
    queryKey: ['history-detail', entryId],
    queryFn: () => (entryId ? getHistoryDetail(entryId) : null),
    enabled: !!entryId,
    staleTime: 1000 * 60 * 5, // 5 minutes
  });
}

export function useExportHistoryToSheets() {
  const queryClient = useQueryClient();
  const { enqueueSnackbar } = useSnackbar();

  return useMutation({
    mutationFn: (entryId: number) => exportHistoryToSheets(entryId),
    onSuccess: (data, entryId) => {
      enqueueSnackbar('Exported to Google Sheets successfully!', { variant: 'success' });
      // Invalidate history to refresh export status
      queryClient.invalidateQueries({ queryKey: queryKeys.history });
      queryClient.invalidateQueries({ queryKey: ['history-detail', entryId] });
    },
    onError: (error: any) => {
      enqueueSnackbar(
        `Export failed: ${getApiErrorMessage(error)}`,
        { variant: 'error' }
      );
    },
  });
}
```

---

### Step 7.3: Create History Detail Dialog Component

**File:** `frontend/src/components/HistoryDetailDialog.tsx` (new file)

```typescript
/**
 * History Detail Dialog - View and export historical job results
 */
import React from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Typography,
  Box,
  Chip,
  Stack,
  CircularProgress,
  Alert,
  IconButton,
  Tooltip,
} from '@mui/material';
import { Close, FileDownload, OpenInNew } from '@mui/icons-material';
import { useHistoryDetail, useExportHistoryToSheets } from '@/lib/queries';
import ResultsTable from './ResultsTable';

interface HistoryDetailDialogProps {
  entryId: number | null;
  open: boolean;
  onClose: () => void;
}

export default function HistoryDetailDialog({
  entryId,
  open,
  onClose,
}: HistoryDetailDialogProps) {
  const { data: entry, isLoading, error } = useHistoryDetail(entryId);
  const exportMutation = useExportHistoryToSheets();

  const handleExport = () => {
    if (entryId) {
      exportMutation.mutate(entryId);
    }
  };

  const handleOpenSheet = () => {
    if (entry?.export_sheet_url) {
      window.open(entry.export_sheet_url, '_blank');
    }
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="lg" fullWidth>
      <DialogTitle>
        <Stack direction="row" alignItems="center" justifyContent="space-between">
          <Typography variant="h6">Processing History Detail</Typography>
          <IconButton onClick={onClose} size="small">
            <Close />
          </IconButton>
        </Stack>
      </DialogTitle>

      <DialogContent>
        {isLoading && (
          <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
            <CircularProgress />
          </Box>
        )}

        {error && (
          <Alert severity="error">Failed to load history details</Alert>
        )}

        {entry && (
          <Stack spacing={3}>
            {/* File info */}
            <Box>
              <Typography variant="subtitle2" color="text.secondary">
                File
              </Typography>
              <Typography variant="body1" fontWeight={600}>
                {entry.original_filename}
              </Typography>
            </Box>

            {/* Metadata */}
            <Stack direction="row" spacing={2} flexWrap="wrap">
              <Chip
                label={`${entry.sentences.length} sentences`}
                color="primary"
                size="small"
              />
              <Chip
                label={`${entry.gemini_tokens_used.toLocaleString()} tokens`}
                size="small"
              />
              {entry.processing_time_seconds && (
                <Chip
                  label={`${entry.processing_time_seconds}s processing time`}
                  size="small"
                />
              )}
              {entry.exported_to_sheets && (
                <Chip
                  label="Exported to Sheets"
                  color="success"
                  size="small"
                  icon={<OpenInNew />}
                  onClick={handleOpenSheet}
                  clickable
                />
              )}
            </Stack>

            {/* Processing settings */}
            <Box>
              <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                Processing Settings
              </Typography>
              <Box sx={{ pl: 2 }}>
                <Typography variant="body2">
                  Sentence Length: {entry.processing_settings?.sentence_length_limit || 8} words
                </Typography>
                <Typography variant="body2">
                  Model: {entry.processing_settings?.gemini_model || 'balanced'}
                </Typography>
                <Typography variant="body2">
                  Ignore Dialogue: {entry.processing_settings?.ignore_dialogue ? 'Yes' : 'No'}
                </Typography>
              </Box>
            </Box>

            {/* Results table */}
            <Box>
              <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                Processed Sentences
              </Typography>
              <ResultsTable
                sentences={entry.sentences}
                onSentenceUpdate={() => {}} // Read-only
                readOnly
              />
            </Box>
          </Stack>
        )}
      </DialogContent>

      <DialogActions>
        {entry && !entry.exported_to_sheets && (
          <Button
            startIcon={<FileDownload />}
            onClick={handleExport}
            disabled={exportMutation.isPending}
            variant="contained"
          >
            {exportMutation.isPending ? 'Exporting...' : 'Export to Sheets'}
          </Button>
        )}
        {entry?.export_sheet_url && (
          <Button
            startIcon={<OpenInNew />}
            onClick={handleOpenSheet}
            variant="outlined"
          >
            Open Sheet
          </Button>
        )}
        <Button onClick={onClose}>Close</Button>
      </DialogActions>
    </Dialog>
  );
}
```

---

### Step 7.4: Update History Page to Use Detail Dialog

**File:** `frontend/src/app/history/page.tsx`

**Current State:**
- Simple page (line 1-31) that renders `<HistoryTable />` component
- HistoryTable.tsx (700+ lines) handles all logic, state, and UI

**Option A: Add dialog to HistoryTable.tsx (Recommended)**

**File:** `frontend/src/components/HistoryTable.tsx`

**Add state after existing state declarations (around line 60):**
```typescript
const [detailDialogOpen, setDetailDialogOpen] = useState(false);
const [selectedEntryId, setSelectedEntryId] = useState<number | null>(null);
```

**Add "View Details" action to each row (find the actions section around line 400+):**
```typescript
<Tooltip title="View Details">
  <IconButton 
    size="small" 
    onClick={() => {
      setSelectedEntryId(entry.id);
      setDetailDialogOpen(true);
    }}
  >
    <Eye size={18} />
  </IconButton>
</Tooltip>
```

**Add dialog at end of component before closing tag:**
```typescript
<HistoryDetailDialog
  entryId={selectedEntryId}
  open={detailDialogOpen}
  onClose={() => {
    setDetailDialogOpen(false);
    setSelectedEntryId(null);
  }}
/>
```

---

### Step 7.5: Update ResultsTable for Read-Only Mode

**File:** `frontend/src/components/ResultsTable.tsx`

**Current State:**
- Component accepts `sentences: string[]` (line 13)
- Has `onSentencesChange` callback (line 14)
- Inline editing supported (line 87-106)
- No `readOnly` prop currently

**Add readOnly prop to interface (around line 13):**
```typescript
interface ResultsTableProps {
  sentences: string[];
  originalSentences?: string[];
  onSentencesChange?: (sentences: string[]) => void;
  onExportSelected?: (selectedIndices: number[]) => void;
  advancedOptions?: AdvancedNormalizationOptions;
  readOnly?: boolean;  // NEW
}
```

**Update component signature (line 45):**
```typescript
export default function ResultsTable({ 
  sentences, 
  originalSentences = [], 
  onSentencesChange, 
  onExportSelected, 
  advancedOptions,
  readOnly = false  // NEW
}: ResultsTableProps) {
```

**Conditionally disable editing (around line 88):**
```typescript
const startEdit = (index: number, sentence: string) => {
  if (readOnly) return;  // NEW
  setEditingIndex(index);
  setEditValue(sentence);
};
```

**Disable edit button when readOnly (find Edit button around line 200+):**
```typescript
<IconButton
  size="small"
  onClick={() => startEdit(item.index, item.sentence)}
  disabled={readOnly}  // NEW
>
  <Edit2 size={16} />
</IconButton>
```

**Note:** For HistoryDetailDialog, pass sentences in `{normalized, original}` format instead of `string[]`.

---

## Phase 8: Testing & Deployment

### Step 8.1: Database Migration

**Create and run migration:**
```bash
cd backend
flask db migrate -m "Add history integration for completed jobs"
flask db upgrade
```

---

### Step 8.2: Unit Tests

**File:** `backend/tests/test_history_integration.py` (new file)

```python
"""Tests for job-to-history integration"""
import pytest
from app.models import Job, History
from app.services.history_service import HistoryService

def test_create_history_from_job(app, db_session, test_user):
    """Test creating history entry from completed job"""
    # Create a completed job
    job = Job(
        user_id=test_user.id,
        original_filename='test.pdf',
        status='completed',
        processing_settings={'sentence_length_limit': 12},
        gemini_tokens_used=1000,
        processing_time_seconds=30,
    )
    db_session.add(job)
    db_session.commit()
    
    sentences = [
        {'normalized': 'First sentence.', 'original': 'First sentence.'},
        {'normalized': 'Second sentence.', 'original': 'Second sentence.'},
    ]
    
    # Create history entry
    history = HistoryService.create_from_job(job, sentences)
    
    assert history.user_id == test_user.id
    assert history.original_filename == 'test.pdf'
    assert len(history.sentences) == 2
    assert history.exported_to_sheets == False
    
    # Link should be established
    job.history_id = history.id
    db_session.commit()
    
    assert job.history.id == history.id
```

---

### Step 8.3: Manual Testing

**Test flow:**
1. Upload a PDF and process it via async endpoint.
2. Wait for job to complete.
3. Check `/api/v1/history` - verify entry was created.
4. Open History page in frontend.
5. Click "View Details" on the new entry.
6. Verify sentences are displayed.
7. Click "Export to Sheets" (if not already exported).
8. Verify export succeeds and sheet URL is saved.
9. Click "Open Sheet" to verify data.

---

### Step 8.4: Deploy

```bash
# Backend
git add .
git commit -m "feat: add job-to-history integration with export support"
git push origin master

# Frontend
cd frontend
vercel --prod
```

---

## Success Metrics (Mission 3)

- ✅ 100% of completed jobs automatically saved to History
- ✅ Users can view full sentence results from any historical job
- ✅ Export-to-Sheets works for historical jobs (not just active sessions)
- ✅ History page shows export status for each entry
- ✅ No data loss between Job and History tables

---

## Rollback Plan (Mission 3)

1. Remove `HistoryService.create_from_job()` calls from `finalize_job_results`.
2. Revert `/history/<id>` and `/history/<id>/export` endpoints.
3. Remove `HistoryDetailDialog` component from frontend.
4. Roll back database migration if needed.

---

## Future Enhancements

- [ ] Add Redis pub/sub for multi-instance WebSocket sync (when scaling > 1 backend replica)
- [ ] Implement adaptive chunk sizing based on server load
- [ ] Add per-chunk progress within each chunk task (sub-progress bar)
- [ ] Use Celery signals (`task_prerun`, `task_postrun`) for automatic progress emission
- [ ] Add WebSocket reconnection with exponential backoff on frontend
- [ ] Implement WebSocket heartbeat/ping-pong for connection health monitoring
- [ ] Add bulk export for multiple history entries
- [ ] Add search/filter in History page (by filename, date, export status)
- [ ] Add ability to re-process historical PDFs with different settings
- [ ] Add download option for history results (CSV/JSON)

---

## Notes

- **Eventlet vs Gevent:** Eventlet chosen for better compatibility with Flask-SocketIO and simpler deployment.
- **Worker Count:** Use `-w 1` with eventlet (async I/O within one process). For horizontal scaling, run multiple instances behind a load balancer.
- **Message Queue:** Set `message_queue=CELERY_BROKER_URL` in SocketIO init for multi-instance message sync (if deploying > 1 backend replica).
- **Celery Concurrency:** Start with `--concurrency=4`. Adjust based on server CPU cores and memory.
- **Chord vs Group:** Chord includes a callback for finalization. Use `group().apply_async()` if you don't need a callback (but you do for our use case).

---

## References

- [Flask-SocketIO Documentation](https://flask-socketio.readthedocs.io/)
- [Celery Canvas Documentation](https://docs.celeryq.dev/en/stable/userguide/canvas.html)
- [Socket.IO Client (React)](https://socket.io/docs/v4/client-api/)
- [Eventlet WSGI Server](https://eventlet.readthedocs.io/)

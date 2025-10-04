# Async PDF Processing & Deployment Roadmap

**Last Updated:** October 4, 2025  
**Status:** Planning Phase  
**Priority:** P1 - High Priority

---

## 📋 Executive Summary

This roadmap outlines the implementation of **scalable asynchronous PDF processing** for novel-length documents (100-500 pages) using a task queue architecture. The current synchronous processing blocks requests for up to 60 seconds, causing poor UX and potential timeouts. This document covers:

1. **Background processing** with Celery + Redis
2. **Automatic chunking** for large documents
3. **Progress tracking** with WebSocket/SSE
4. **Resource management** and error recovery
5. **Production deployment** strategies (PaaS vs VPS vs Serverless)

---

## 🎯 Problem Statement

### Current Architecture Issues
```
User Upload (50MB PDF, 300 pages)
    ↓
Synchronous Flask Route (blocks for 45-60s)
    ↓
GeminiService processes entire PDF in one call
    ↓
Response (timeout risk, no progress feedback)
```

**Pain Points:**
- ❌ **Blocking requests**: User waits 30-60s with no feedback
- ❌ **Timeout risk**: Vercel/Heroku 30s limits kill long requests
- ❌ **No resumability**: Network error = start over
- ❌ **Memory spikes**: Large PDFs loaded entirely in RAM
- ❌ **No concurrency**: One user blocks the worker
- ❌ **Poor UX**: No progress indication or cancellation

### Target Architecture
```
User Upload (50MB PDF, 300 pages)
    ↓
POST /process-pdf → Returns job_id (< 1s)
    ↓
Celery Worker picks up task (background)
    ├── Chunk PDF into 10-page segments
    ├── Process chunks in parallel (5 workers)
    ├── Update progress via WebSocket
    ├── Handle retries on Gemini API errors
    └── Save results to DB + notify user
    ↓
Frontend polls or listens for completion
```

**Benefits:**
- ✅ **Instant response**: API returns job_id in < 1s
- ✅ **Real-time progress**: "Processing page 45/300 (15%)"
- ✅ **Fault tolerance**: Retry failed chunks, not entire PDF
- ✅ **Scalability**: Add more workers for concurrency
- ✅ **Better UX**: Cancel jobs, resume on error

---

## 🏗️ Architecture Design

### Component Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Task Queue** | Celery 5.3+ | Async job orchestration |
| **Message Broker** | Redis 7.x | Queue backend + result storage |
| **Worker Pool** | Celery workers (4-8) | Execute background tasks |
| **Progress Tracking** | Redis + WebSocket/SSE | Real-time updates |
| **Chunking** | PyPDF2 + custom logic | Split large PDFs |
| **Monitoring** | Flower + Prometheus | Worker health, metrics |

### Database Schema Additions

```python
class Job(db.Model):
    """Enhanced job model with progress tracking"""
    # Existing fields...
    
    # Progress tracking
    progress_percent = db.Column(db.Integer, default=0)  # 0-100
    current_step = db.Column(db.String(100))  # "Chunking PDF", "Processing chunk 5/10"
    total_chunks = db.Column(db.Integer)
    processed_chunks = db.Column(db.Integer, default=0)
    
    # Resource management
    chunk_results = db.Column(db.JSON)  # [{chunk_id: 1, sentences: [...], status: 'done'}]
    failed_chunks = db.Column(db.JSON)  # [2, 7] - chunk IDs that failed
    retry_count = db.Column(db.Integer, default=0)
    max_retries = db.Column(db.Integer, default=3)
    
    # Cancellation support
    is_cancelled = db.Column(db.Boolean, default=False)
    cancelled_at = db.Column(db.DateTime)
    cancelled_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    
    # Performance metrics
    processing_time_seconds = db.Column(db.Integer)
    gemini_api_calls = db.Column(db.Integer, default=0)
    gemini_tokens_used = db.Column(db.Integer, default=0)
```

### Chunking Strategy

**Intelligent PDF Chunking:**
1. **Small PDFs (< 30 pages)**: Process as single chunk
2. **Medium PDFs (30-100 pages)**: Split into 20-page chunks
3. **Large PDFs (100-500 pages)**: Split into 15-page chunks, process 5 in parallel
4. **Preserve context**: Include 1-page overlap between chunks for sentence continuity

**Chunk Size Calculation:**
```python
def calculate_optimal_chunks(page_count: int, model: str) -> dict:
    """
    Determine chunk size based on page count and model limits.
    
    Gemini 2.5 Flash: ~1M token context
    Average novel page: ~500 tokens
    Safe chunk size: 15 pages (~7500 tokens) with headroom for prompt
    """
    if page_count <= 30:
        return {'chunk_size': page_count, 'num_chunks': 1, 'parallel': 1}
    elif page_count <= 100:
        return {'chunk_size': 20, 'num_chunks': (page_count // 20) + 1, 'parallel': 3}
    else:
        return {'chunk_size': 15, 'num_chunks': (page_count // 15) + 1, 'parallel': 5}
```

---

## 🚀 Implementation Roadmap

### Phase 1: Celery Integration (Week 1-2)

**Goal:** Replace synchronous processing with async tasks

#### 1.1 Install Celery Dependencies
```bash
# backend/requirements.txt
celery[redis]==5.3.4
flower==2.0.1  # Web UI for monitoring
celery-progress==0.3  # Progress bar helpers
redis==5.0.1  # Already installed
```

#### 1.2 Create Celery App
**`backend/app/celery_app.py`:**
```python
from celery import Celery
from flask import Flask

def make_celery(app: Flask) -> Celery:
    """Factory function to create Celery instance with Flask context"""
    celery = Celery(
        app.import_name,
        backend=app.config['CELERY_RESULT_BACKEND'],
        broker=app.config['CELERY_BROKER_URL'],
    )
    
    # Update Celery config from Flask config
    celery.conf.update(
        task_serializer='json',
        accept_content=['json'],
        result_serializer='json',
        timezone='UTC',
        enable_utc=True,
        task_track_started=True,
        task_send_sent_event=True,
        worker_send_task_events=True,
        result_expires=3600,  # 1 hour
        task_time_limit=1800,  # 30 minutes max
        task_soft_time_limit=1500,  # Soft limit at 25 minutes
        worker_prefetch_multiplier=1,  # Fair task distribution
        worker_max_tasks_per_child=50,  # Prevent memory leaks
    )
    
    # Make Celery tasks work with Flask app context
    class ContextTask(celery.Task):
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)
    
    celery.Task = ContextTask
    return celery
```

#### 1.3 Update Config
**`backend/config.py`:**
```python
class Config:
    # ... existing config ...
    
    # Celery Configuration
    CELERY_BROKER_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
    CELERY_RESULT_BACKEND = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
    CELERY_TASK_IGNORE_RESULT = False  # We need results for progress tracking
```

#### 1.4 Initialize in App Factory
**`backend/app/__init__.py`:**
```python
from app.celery_app import make_celery

# After creating Flask app
celery = make_celery(app)
```

#### 1.5 Create Background Tasks
**`backend/app/tasks.py`:**
```python
from app import celery, db
from app.models import Job, User
from app.services.pdf_service import PDFService
from app.services.gemini_service import GeminiService
from app.services.chunking_service import ChunkingService
from app.constants import JOB_STATUS_PROCESSING, JOB_STATUS_COMPLETED, JOB_STATUS_FAILED
import PyPDF2
from celery import current_task

@celery.task(bind=True, name='app.tasks.process_pdf_async')
def process_pdf_async(self, job_id: int, file_path: str, user_id: int, settings: dict):
    """
    Process PDF asynchronously with progress tracking.
    
    Args:
        job_id: Database job ID
        file_path: Path to uploaded PDF in temp storage
        user_id: User who initiated the job
        settings: Processing settings (model, length limit, etc.)
    """
    try:
        # Update job status
        job = Job.query.get(job_id)
        job.status = JOB_STATUS_PROCESSING
        job.current_step = "Analyzing PDF structure"
        db.session.commit()
        
        # Extract page count
        with open(file_path, 'rb') as pdf_file:
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            page_count = len(pdf_reader.pages)
        
        # Calculate chunking strategy
        chunking_service = ChunkingService()
        chunk_config = chunking_service.calculate_chunks(page_count, settings.get('gemini_model'))
        
        job.total_chunks = chunk_config['num_chunks']
        job.current_step = f"Processing {chunk_config['num_chunks']} chunks"
        db.session.commit()
        
        # Update progress: 10% (analysis done)
        self.update_state(
            state='PROGRESS',
            meta={'current': 10, 'total': 100, 'step': 'PDF analyzed'}
        )
        
        # Process chunks (simplified - full implementation in Phase 2)
        all_sentences = []
        for i, chunk in enumerate(chunking_service.split_pdf(file_path, chunk_config)):
            # Process chunk with Gemini
            gemini_service = GeminiService(
                sentence_length_limit=settings.get('sentence_length_limit', 8),
                model_preference=settings.get('gemini_model', 'balanced'),
            )
            
            chunk_result = gemini_service.process_text_from_pdf(chunk['file_path'])
            all_sentences.extend(chunk_result['sentences'])
            
            # Update progress
            progress = 10 + int((i + 1) / chunk_config['num_chunks'] * 80)
            job.processed_chunks = i + 1
            job.progress_percent = progress
            db.session.commit()
            
            self.update_state(
                state='PROGRESS',
                meta={'current': progress, 'total': 100, 'step': f'Chunk {i+1}/{chunk_config["num_chunks"]}'}
            )
            
            # Check for cancellation
            job = Job.query.get(job_id)
            if job.is_cancelled:
                raise Exception("Job cancelled by user")
        
        # Finalize job
        job.status = JOB_STATUS_COMPLETED
        job.progress_percent = 100
        job.actual_tokens = sum(chunk.get('tokens', 0) for chunk in all_sentences)
        job.completed_at = datetime.utcnow()
        db.session.commit()
        
        return {
            'status': 'success',
            'sentences': all_sentences,
            'total_tokens': job.actual_tokens,
        }
        
    except Exception as e:
        job = Job.query.get(job_id)
        job.status = JOB_STATUS_FAILED
        job.error_message = str(e)
        db.session.commit()
        raise
```

#### 1.6 Update Routes
**`backend/app/routes.py`:**
```python
from app.tasks import process_pdf_async
import os
import tempfile

@main_bp.route('/process-pdf', methods=['POST'])
@jwt_required()
@limiter.limit("10 per hour")
def process_pdf():
    """Initiate async PDF processing (returns job_id immediately)"""
    user_id = int(get_jwt_identity())
    user = User.query.get(user_id)
    
    if 'pdf_file' not in request.files:
        return jsonify({'error': 'No PDF file provided'}), 400
    
    file = request.files['pdf_file']
    
    # Validate file
    validate_pdf_file(file)
    
    # Save to persistent temp storage (not NamedTemporaryFile which auto-deletes)
    temp_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'processing')
    os.makedirs(temp_dir, exist_ok=True)
    temp_path = os.path.join(temp_dir, f"{uuid.uuid4()}.pdf")
    file.save(temp_path)
    
    # Get settings
    settings = user_settings_service.get_user_settings(user_id)
    settings.update(request.form.to_dict())  # Override with form data
    
    # Create job record
    job = Job(
        user_id=user_id,
        original_filename=file.filename,
        status=JOB_STATUS_PENDING,
        model=settings.get('gemini_model', 'balanced'),
        estimated_credits=0,  # Will be calculated in task
        pricing_version='1.0',
        pricing_rate=1.0,
    )
    db.session.add(job)
    db.session.commit()
    
    # Dispatch async task
    task = process_pdf_async.delay(job.id, temp_path, user_id, settings)
    
    return jsonify({
        'job_id': job.id,
        'task_id': task.id,
        'status': 'pending',
        'message': 'PDF processing started',
    }), 202  # HTTP 202 Accepted
```

#### 1.7 Add Job Status Endpoint
**`backend/app/routes.py`:**
```python
@main_bp.route('/jobs/<int:job_id>', methods=['GET'])
@jwt_required()
def get_job_status(job_id):
    """Get job status and progress"""
    user_id = int(get_jwt_identity())
    job = Job.query.get_or_404(job_id)
    
    if job.user_id != user_id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    # Get Celery task state if available
    task_state = None
    if job.status == JOB_STATUS_PROCESSING:
        from app import celery
        task = celery.AsyncResult(str(job.id))  # Assuming task_id = job_id
        task_state = {
            'state': task.state,
            'info': task.info if task.info else {}
        }
    
    return jsonify({
        'job_id': job.id,
        'status': job.status,
        'progress_percent': job.progress_percent,
        'current_step': job.current_step,
        'processed_chunks': job.processed_chunks,
        'total_chunks': job.total_chunks,
        'created_at': job.created_at.isoformat(),
        'completed_at': job.completed_at.isoformat() if job.completed_at else None,
        'error_message': job.error_message,
        'task_state': task_state,
    })

@main_bp.route('/jobs/<int:job_id>/cancel', methods=['POST'])
@jwt_required()
def cancel_job(job_id):
    """Cancel a running job"""
    user_id = int(get_jwt_identity())
    job = Job.query.get_or_404(job_id)
    
    if job.user_id != user_id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    if job.status not in [JOB_STATUS_PENDING, JOB_STATUS_PROCESSING]:
        return jsonify({'error': 'Job cannot be cancelled'}), 400
    
    job.is_cancelled = True
    job.cancelled_at = datetime.utcnow()
    job.status = 'cancelled'
    db.session.commit()
    
    # Revoke Celery task
    from app import celery
    celery.control.revoke(str(job.id), terminate=True)
    
    return jsonify({'message': 'Job cancelled'})
```

**Success Criteria:**
- ✅ `/process-pdf` returns in < 1s with job_id
- ✅ Celery worker processes PDF in background
- ✅ `/jobs/<id>` returns real-time progress
- ✅ Job cancellation works without orphan tasks

---

### Phase 2: Chunking Service (Week 2-3)

**Goal:** Implement intelligent PDF chunking with context preservation

#### 2.1 Create Chunking Service
**`backend/app/services/chunking_service.py`:**
```python
import os
import tempfile
from typing import List, Dict
import PyPDF2
from PyPDF2 import PdfWriter, PdfReader

class ChunkingService:
    """Service for splitting large PDFs into processable chunks"""
    
    CHUNK_SIZES = {
        'small': {'max_pages': 30, 'chunk_size': 30, 'parallel': 1},
        'medium': {'max_pages': 100, 'chunk_size': 20, 'parallel': 3},
        'large': {'max_pages': 500, 'chunk_size': 15, 'parallel': 5},
    }
    
    OVERLAP_PAGES = 1  # Pages to overlap between chunks for context
    
    def calculate_chunks(self, page_count: int, model: str = 'balanced') -> Dict:
        """
        Calculate optimal chunking strategy.
        
        Args:
            page_count: Total pages in PDF
            model: Gemini model (affects context window)
        
        Returns:
            {
                'chunk_size': int,
                'num_chunks': int,
                'parallel_workers': int,
                'strategy': 'small' | 'medium' | 'large'
            }
        """
        if page_count <= 30:
            strategy = 'small'
        elif page_count <= 100:
            strategy = 'medium'
        else:
            strategy = 'large'
        
        config = self.CHUNK_SIZES[strategy]
        chunk_size = config['chunk_size']
        
        # Calculate chunks with overlap
        num_chunks = max(1, (page_count + chunk_size - 1) // chunk_size)
        
        return {
            'chunk_size': chunk_size,
            'num_chunks': num_chunks,
            'parallel_workers': config['parallel'],
            'strategy': strategy,
            'total_pages': page_count,
        }
    
    def split_pdf(self, pdf_path: str, chunk_config: Dict) -> List[Dict]:
        """
        Split PDF into chunks with context overlap.
        
        Args:
            pdf_path: Path to source PDF
            chunk_config: Output from calculate_chunks()
        
        Returns:
            List of chunk metadata:
            [
                {
                    'chunk_id': 0,
                    'file_path': '/tmp/chunk_0.pdf',
                    'start_page': 0,
                    'end_page': 19,
                    'page_count': 20,
                },
                ...
            ]
        """
        chunks = []
        chunk_size = chunk_config['chunk_size']
        total_pages = chunk_config['total_pages']
        
        with open(pdf_path, 'rb') as pdf_file:
            pdf_reader = PdfReader(pdf_file)
            
            for i in range(chunk_config['num_chunks']):
                start_page = i * chunk_size
                end_page = min(start_page + chunk_size + self.OVERLAP_PAGES, total_pages)
                
                # Skip if we've exceeded total pages
                if start_page >= total_pages:
                    break
                
                # Create chunk PDF
                pdf_writer = PdfWriter()
                for page_num in range(start_page, end_page):
                    pdf_writer.add_page(pdf_reader.pages[page_num])
                
                # Save chunk to temp file
                chunk_path = tempfile.NamedTemporaryFile(
                    delete=False,
                    suffix=f'_chunk_{i}.pdf'
                ).name
                
                with open(chunk_path, 'wb') as chunk_file:
                    pdf_writer.write(chunk_file)
                
                chunks.append({
                    'chunk_id': i,
                    'file_path': chunk_path,
                    'start_page': start_page,
                    'end_page': end_page - 1,  # Inclusive
                    'page_count': end_page - start_page,
                    'has_overlap': i > 0,  # First chunk has no overlap
                })
        
        return chunks
    
    def cleanup_chunks(self, chunks: List[Dict]):
        """Delete temporary chunk files"""
        for chunk in chunks:
            try:
                if os.path.exists(chunk['file_path']):
                    os.remove(chunk['file_path'])
            except Exception as e:
                # Log but don't fail
                print(f"Failed to delete chunk {chunk['chunk_id']}: {e}")
```

#### 2.2 Parallel Chunk Processing
**Update `backend/app/tasks.py`:**
```python
from celery import group
from app.services.chunking_service import ChunkingService

@celery.task(name='app.tasks.process_chunk')
def process_chunk(chunk: Dict, settings: Dict) -> Dict:
    """Process a single PDF chunk (can run in parallel)"""
    gemini_service = GeminiService(
        sentence_length_limit=settings.get('sentence_length_limit', 8),
        model_preference=settings.get('gemini_model', 'balanced'),
        ignore_dialogue=settings.get('ignore_dialogue', False),
        preserve_formatting=settings.get('preserve_formatting', True),
    )
    
    result = gemini_service.process_text_from_pdf(chunk['file_path'])
    
    # Cleanup chunk file
    try:
        os.remove(chunk['file_path'])
    except:
        pass
    
    return {
        'chunk_id': chunk['chunk_id'],
        'sentences': result['sentences'],
        'tokens': result.get('tokens', 0),
        'start_page': chunk['start_page'],
        'end_page': chunk['end_page'],
    }

@celery.task(bind=True, name='app.tasks.process_pdf_async')
def process_pdf_async(self, job_id: int, file_path: str, user_id: int, settings: dict):
    """Enhanced with parallel chunk processing"""
    try:
        job = Job.query.get(job_id)
        job.status = JOB_STATUS_PROCESSING
        db.session.commit()
        
        # Split into chunks
        chunking_service = ChunkingService()
        
        with open(file_path, 'rb') as f:
            page_count = len(PyPDF2.PdfReader(f).pages)
        
        chunk_config = chunking_service.calculate_chunks(page_count, settings.get('gemini_model'))
        chunks = chunking_service.split_pdf(file_path, chunk_config)
        
        job.total_chunks = len(chunks)
        db.session.commit()
        
        # Process chunks in parallel using Celery group
        chunk_tasks = group(
            process_chunk.s(chunk, settings) for chunk in chunks
        )
        
        results = chunk_tasks.apply_async()
        
        # Wait for all chunks with progress updates
        processed = 0
        all_results = []
        
        for result in results.iterate():
            processed += 1
            job.processed_chunks = processed
            job.progress_percent = int((processed / len(chunks)) * 90)  # 90% for processing
            db.session.commit()
            
            self.update_state(
                state='PROGRESS',
                meta={
                    'current': job.progress_percent,
                    'total': 100,
                    'step': f'Processed {processed}/{len(chunks)} chunks'
                }
            )
            
            all_results.append(result)
        
        # Sort results by chunk_id and combine sentences
        all_results.sort(key=lambda x: x['chunk_id'])
        combined_sentences = []
        
        for result in all_results:
            combined_sentences.extend(result['sentences'])
        
        # Deduplicate overlapping sentences (simple heuristic)
        combined_sentences = deduplicate_sentences(combined_sentences)
        
        # Finalize
        job.status = JOB_STATUS_COMPLETED
        job.progress_percent = 100
        job.completed_at = datetime.utcnow()
        db.session.commit()
        
        # Cleanup
        os.remove(file_path)
        
        return {'status': 'success', 'sentences': combined_sentences}
        
    except Exception as e:
        job = Job.query.get(job_id)
        job.status = JOB_STATUS_FAILED
        job.error_message = str(e)
        db.session.commit()
        raise

def deduplicate_sentences(sentences: List[str]) -> List[str]:
    """Remove duplicate sentences from chunk overlaps"""
    seen = set()
    unique = []
    
    for sentence in sentences:
        normalized = sentence.strip().lower()
        if normalized not in seen:
            seen.add(normalized)
            unique.append(sentence)
    
    return unique
```

**Success Criteria:**
- ✅ 300-page PDF splits into 20 chunks
- ✅ 5 chunks process in parallel (2-3x speedup)
- ✅ Overlap sentences deduplicated correctly
- ✅ Progress updates every chunk completion

---

### Phase 3: Frontend Integration (Week 3-4)

**Goal:** Real-time progress UI with job management

#### 3.1 Job Status Hook
**`frontend/src/lib/queries.ts`:**
```typescript
export function useJobStatus(jobId: number | null, enabled: boolean = true) {
  return useQuery({
    queryKey: ['job-status', jobId],
    queryFn: async () => {
      if (!jobId) return null;
      const response = await api.get(`/jobs/${jobId}`);
      return response.data;
    },
    enabled: enabled && !!jobId,
    refetchInterval: (data) => {
      // Poll every 2s if processing, stop if completed/failed
      if (!data) return false;
      return ['pending', 'processing'].includes(data.status) ? 2000 : false;
    },
  });
}

export function useCancelJob() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async (jobId: number) => {
      return await api.post(`/jobs/${jobId}/cancel`);
    },
    onSuccess: (_, jobId) => {
      queryClient.invalidateQueries({ queryKey: ['job-status', jobId] });
    },
  });
}
```

#### 3.2 Progress Dialog Component
**`frontend/src/components/ProcessingProgressDialog.tsx`:**
```typescript
import React from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  LinearProgress,
  Typography,
  Box,
  Alert,
} from '@mui/material';
import { useJobStatus, useCancelJob } from '@/lib/queries';

interface Props {
  jobId: number | null;
  open: boolean;
  onClose: () => void;
  onComplete: (sentences: string[]) => void;
}

export default function ProcessingProgressDialog({ jobId, open, onClose, onComplete }: Props) {
  const { data: job, isLoading } = useJobStatus(jobId, open);
  const cancelMutation = useCancelJob();
  
  React.useEffect(() => {
    if (job?.status === 'completed') {
      // Fetch results and close
      onComplete(job.sentences || []);
    }
  }, [job?.status]);
  
  const handleCancel = () => {
    if (jobId && window.confirm('Are you sure you want to cancel this job?')) {
      cancelMutation.mutate(jobId);
    }
  };
  
  if (!job) return null;
  
  return (
    <Dialog open={open} maxWidth="sm" fullWidth disableEscapeKeyDown>
      <DialogTitle>Processing PDF</DialogTitle>
      <DialogContent>
        <Box sx={{ mb: 2 }}>
          <Typography variant="body2" color="text.secondary" gutterBottom>
            {job.current_step || 'Starting...'}
          </Typography>
          <LinearProgress 
            variant="determinate" 
            value={job.progress_percent || 0} 
            sx={{ height: 8, borderRadius: 4 }}
          />
          <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
            {job.progress_percent || 0}% complete
            {job.total_chunks > 0 && ` • ${job.processed_chunks || 0}/${job.total_chunks} chunks`}
          </Typography>
        </Box>
        
        {job.status === 'failed' && (
          <Alert severity="error" sx={{ mt: 2 }}>
            {job.error_message || 'Processing failed'}
          </Alert>
        )}
      </DialogContent>
      <DialogActions>
        {job.status === 'processing' && (
          <Button onClick={handleCancel} color="error" disabled={cancelMutation.isPending}>
            Cancel
          </Button>
        )}
        <Button onClick={onClose} disabled={job.status === 'processing'}>
          {job.status === 'completed' ? 'Done' : 'Close'}
        </Button>
      </DialogActions>
    </Dialog>
  );
}
```

#### 3.3 Update Main Page
**`frontend/src/app/page.tsx`:**
```typescript
const [processingJobId, setProcessingJobId] = useState<number | null>(null);
const [progressDialogOpen, setProgressDialogOpen] = useState(false);

const handleUpload = async (file: File) => {
  const formData = new FormData();
  formData.append('pdf_file', file);
  
  try {
    // Upload and get job_id
    const response = await api.post('/process-pdf', formData);
    const jobId = response.data.job_id;
    
    setProcessingJobId(jobId);
    setProgressDialogOpen(true);
  } catch (error) {
    enqueueSnackbar('Upload failed', { variant: 'error' });
  }
};

const handleProcessingComplete = (sentences: string[]) => {
  setResults(sentences);
  setProgressDialogOpen(false);
  enqueueSnackbar('Processing complete!', { variant: 'success' });
};

return (
  <>
    {/* ... existing UI ... */}
    
    <ProcessingProgressDialog
      jobId={processingJobId}
      open={progressDialogOpen}
      onClose={() => setProgressDialogOpen(false)}
      onComplete={handleProcessingComplete}
    />
  </>
);
```

**Success Criteria:**
- ✅ Progress bar updates in real-time
- ✅ "Processing chunk 5/20" message visible
- ✅ Cancel button works without errors
- ✅ Completed jobs auto-load results

---

### Phase 4: Deployment Strategy (Week 4-6)

**Goal:** Choose optimal deployment platform and implement CI/CD

#### Option 1: Railway (Recommended for MVP)
**Pros:**
- ✅ Redis + PostgreSQL + Celery workers in one project
- ✅ Auto-deploy from GitHub
- ✅ $5-20/month for small scale
- ✅ Built-in monitoring and logs
- ✅ Easy horizontal scaling

**Setup:**
```yaml
# railway.toml
[build]
builder = "DOCKERFILE"
dockerfilePath = "backend/Dockerfile"

[deploy]
startCommand = "celery -A app.celery_app worker --loglevel=info"
healthcheckPath = "/api/v1/health"
healthcheckTimeout = 300
restartPolicyType = "ON_FAILURE"

[services.backend]
  command = "gunicorn -w 4 -b 0.0.0.0:5000 run:app"
  
[services.celery-worker]
  command = "celery -A app.celery_app worker --loglevel=info --concurrency=4"
  
[services.celery-beat]
  command = "celery -A app.celery_app beat --loglevel=info"
  
[services.flower]
  command = "celery -A app.celery_app flower --port=5555"
```

**Deployment Steps:**
1. Connect GitHub repo to Railway
2. Add services: backend, celery-worker, redis, postgres
3. Set environment variables (GEMINI_API_KEY, etc.)
4. Deploy: `railway up`
5. Monitor: Access Flower UI at `https://<app>.up.railway.app:5555`

**Cost Estimate:**
- Backend (1 instance): $5/month
- Celery workers (2 instances): $10/month
- Redis (256MB): $3/month
- PostgreSQL (1GB): $5/month
- **Total: ~$23/month** (with generous free tier for first month)

---

#### Option 2: DigitalOcean App Platform + Managed Redis
**Pros:**
- ✅ More control than Railway
- ✅ Managed Redis/PostgreSQL
- ✅ Predictable pricing ($12-48/month)
- ✅ Better for 100+ concurrent users

**Setup:**
```yaml
# .do/app.yaml
name: french-novel-tool
region: nyc

services:
  - name: backend
    github:
      repo: username/FrenchNovelTool
      branch: main
      deploy_on_push: true
    dockerfile_path: backend/Dockerfile
    http_port: 5000
    instance_count: 1
    instance_size_slug: basic-xs  # $5/month
    envs:
      - key: REDIS_URL
        scope: RUN_TIME
        value: ${redis.REDIS_URL}
      - key: DATABASE_URL
        scope: RUN_TIME
        value: ${db.DATABASE_URL}
  
  - name: celery-worker
    github:
      repo: username/FrenchNovelTool
      branch: main
    dockerfile_path: backend/Dockerfile
    run_command: celery -A app.celery_app worker --loglevel=info --concurrency=4
    instance_count: 2
    instance_size_slug: basic-xs
    envs:
      - key: REDIS_URL
        scope: RUN_TIME
        value: ${redis.REDIS_URL}

databases:
  - name: db
    engine: PG
    production: true
    cluster_name: french-novel-db
    
  - name: redis
    engine: REDIS
    production: true
```

Deploy: `doctl apps create --spec .do/app.yaml`

**Cost Estimate:**
- Backend: $5/month
- Celery workers (2x): $10/month
- PostgreSQL: $15/month (managed)
- Redis: $15/month (managed)
- **Total: ~$45/month**

---

#### Option 3: AWS ECS Fargate (Enterprise Scale)
**Pros:**
- ✅ Best for high traffic (1000+ concurrent)
- ✅ Auto-scaling based on queue depth
- ✅ AWS ecosystem integration (S3, SQS)
- ✅ Pay-per-use model

**Cons:**
- ❌ Complex setup (Terraform recommended)
- ❌ Higher baseline cost ($50+/month)
- ❌ Requires DevOps expertise

**Architecture:**
```
ALB (Load Balancer)
  ↓
ECS Service (Backend) - 2-10 tasks
  ↓
ElastiCache Redis (Multi-AZ)
  ↓
ECS Service (Celery Workers) - Auto-scaling 2-20 tasks
  ↓
RDS PostgreSQL (Multi-AZ)
  ↓
S3 (PDF storage)
```

**Cost Estimate (medium traffic):**
- Fargate tasks: $30/month
- ElastiCache: $15/month
- RDS PostgreSQL: $25/month
- ALB: $20/month
- **Total: ~$90/month** (scales up with usage)

---

#### Recommended Path
**For Current Stage (MVP with < 100 users):**
→ **Railway** (easiest, cheapest, fastest to deploy)

**For Growth Stage (100-1000 users):**
→ **DigitalOcean App Platform** (better performance, managed DBs)

**For Enterprise (1000+ users):**
→ **AWS ECS Fargate** (full auto-scaling, global CDN)

---

### Phase 5: Monitoring & Observability (Week 5-6)

#### 5.1 Install Monitoring Stack
```bash
# backend/requirements.txt
prometheus-client==0.19.0
sentry-sdk[flask]==1.38.0
```

#### 5.2 Celery Metrics
**`backend/app/celery_app.py`:**
```python
from prometheus_client import Counter, Histogram

# Metrics
celery_tasks_total = Counter('celery_tasks_total', 'Total tasks processed', ['task_name', 'status'])
celery_task_duration = Histogram('celery_task_duration_seconds', 'Task duration', ['task_name'])

@celery.task(bind=True)
def process_pdf_async(self, job_id, file_path, user_id, settings):
    start_time = time.time()
    
    try:
        # ... processing logic ...
        celery_tasks_total.labels(task_name='process_pdf_async', status='success').inc()
    except Exception as e:
        celery_tasks_total.labels(task_name='process_pdf_async', status='failed').inc()
        raise
    finally:
        duration = time.time() - start_time
        celery_task_duration.labels(task_name='process_pdf_async').observe(duration)
```

#### 5.3 Sentry Integration
**`backend/app/__init__.py`:**
```python
import sentry_sdk
from sentry_sdk.integrations.flask import FlaskIntegration
from sentry_sdk.integrations.celery import CeleryIntegration

sentry_sdk.init(
    dsn=os.getenv('SENTRY_DSN'),
    integrations=[
        FlaskIntegration(),
        CeleryIntegration(),
    ],
    traces_sample_rate=0.1,  # 10% of transactions
    profiles_sample_rate=0.1,
    environment=os.getenv('FLASK_ENV', 'production'),
)
```

#### 5.4 Flower Dashboard
Access at `https://your-app.railway.app/flower` to monitor:
- Active tasks
- Task history
- Worker health
- Queue depth
- Success/failure rates

---

## 📈 Performance Benchmarks

### Expected Performance Improvements

| Metric | Current (Sync) | Target (Async) |
|--------|---------------|----------------|
| **API Response Time** | 30-60s | < 1s |
| **User Feedback Delay** | No progress | Real-time updates |
| **Concurrent Processing** | 1 job at a time | 5-10 parallel |
| **Large PDF (300 pages)** | 60s blocked | 45s background |
| **Failure Recovery** | Restart from scratch | Resume from chunk |
| **Resource Usage** | Spike + crash | Smooth distribution |

### Scalability Targets
- **10 users**: 1 worker, Railway basic
- **100 users**: 3-5 workers, DigitalOcean
- **1000 users**: Auto-scaling 5-20 workers, AWS Fargate

---

## 🔐 Security Considerations

1. **File Storage**:
   - Use signed URLs for S3/CloudFlare R2
   - Auto-delete temp files after 24h
   - Virus scan PDFs before processing

2. **Rate Limiting**:
   - Keep current per-user limits (10/hour)
   - Add per-IP limits to prevent abuse
   - Track concurrent jobs per user (max 3)

3. **Secrets Management**:
   - Use environment variables (Railway/DO built-in)
   - AWS Secrets Manager for production
   - Rotate API keys quarterly

---

## 📝 Migration Plan

### From Sync to Async (Zero Downtime)

**Week 1-2: Parallel Deployment**
1. Deploy Celery workers alongside existing sync endpoint
2. Add feature flag: `ASYNC_PROCESSING_ENABLED=false`
3. Test async flow with beta users (10%)

**Week 3: Gradual Rollout**
1. Enable async for 50% of users (A/B test)
2. Monitor error rates, compare performance
3. Gather user feedback on progress UI

**Week 4: Full Migration**
1. Enable async for 100% of users
2. Deprecate sync endpoint (return 410 Gone)
3. Remove old code after 2 weeks

---

## ✅ Success Metrics

**Technical Metrics:**
- [ ] 95th percentile API response < 2s
- [ ] Job failure rate < 2%
- [ ] Worker utilization 50-70% (not over/under)
- [ ] Zero data loss on chunk failures

**User Experience:**
- [ ] Progress updates every 2-5 seconds
- [ ] Cancel job works in < 1s
- [ ] 90% of users see "faster than before" in surveys
- [ ] Support tickets re: timeouts reduced by 80%

---

## 🚧 Future Enhancements (P2+)

1. **Distributed Caching**:
   - Cache processed chunks in Redis (24h TTL)
   - Skip re-processing identical PDFs

2. **Smart Retry**:
   - Exponential backoff for Gemini API
   - Fallback to cheaper model on quota errors

3. **Batch Processing**:
   - Allow users to upload 5-10 PDFs at once
   - Process in priority queue

4. **Real-time WebSockets**:
   - Replace polling with Socket.IO
   - Push progress updates instantly

5. **Multi-region Deployment**:
   - Deploy workers in EU/US/APAC
   - Route jobs to nearest region

---

## 📚 References & Resources

### Documentation
- [Celery Best Practices](https://docs.celeryq.dev/en/stable/userguide/tasks.html#best-practices)
- [Railway Deployment Guide](https://docs.railway.app/guides/deployment)
- [DigitalOcean App Platform](https://docs.digitalocean.com/products/app-platform/)
- [Flower Monitoring](https://flower.readthedocs.io/)

### Libraries
- `celery==5.3.4`: Task queue
- `redis==5.0.1`: Message broker
- `flower==2.0.1`: Monitoring UI
- `prometheus-client==0.19.0`: Metrics export
- `sentry-sdk==1.38.0`: Error tracking

### Similar Implementations
- [How Notion Processes Large Files](https://www.notion.so/blog/how-we-sped-up-notion-in-the-browser)
- [Scaling Background Jobs at Stripe](https://stripe.com/blog/scaling-background-jobs)

---

## 🤝 Team & Timeline

**Total Effort:** 4-6 weeks (1 developer)

| Phase | Duration | Owner | Status |
|-------|----------|-------|--------|
| Celery Integration | 1.5 weeks | Backend Dev | 🔴 Not Started |
| Chunking Service | 1 week | Backend Dev | 🔴 Not Started |
| Frontend Progress UI | 1 week | Frontend Dev | 🔴 Not Started |
| Deployment Setup | 1 week | DevOps | 🔴 Not Started |
| Monitoring | 0.5 weeks | DevOps | 🔴 Not Started |
| Testing & Rollout | 1 week | Full Team | 🔴 Not Started |

---

**Next Steps:**
1. Review this roadmap with team
2. Choose deployment platform (Railway recommended)
3. Create GitHub issues for Phase 1 tasks
4. Set up development environment with Redis
5. Begin Celery integration

**Questions? Contact:** [Your Email/Slack Channel]

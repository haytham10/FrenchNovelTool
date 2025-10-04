# Chunk Persistence and Retry System — Production Roadmap

**Created**: October 4, 2025  
**Status**: Planning  
**Priority**: High (Production Reliability)  
**Estimated Effort**: 3-5 days (iterative rollout)

---

## Executive Summary

This roadmap details how to build a production-grade chunk persistence and retry system that ensures **no chunk is permanently lost** and failed chunks can be automatically or manually retried until successful.

### Current State (Problems)
- ✅ Chunks are created in-memory (base64) — self-contained, no filesystem dependencies
- ✅ Chunks have in-task retry logic for transient errors (exponential backoff)
- ❌ **If all retries fail, the chunk is excluded from final result forever**
- ❌ No persistent record of which chunks failed/succeeded for a job
- ❌ No way to re-process failed chunks after job completes
- ❌ No audit trail for chunk processing attempts/errors

### Target State (Solution)
- ✅ **DB-backed `JobChunk` model** — persistent record for every chunk
- ✅ **Chunk lifecycle tracking** — pending → processing → success | failed | retry_scheduled
- ✅ **Automatic orchestrated retries** — finalize re-dispatches failed chunks up to N rounds
- ✅ **Manual retry API** — UI button to retry specific failed chunks on demand
- ✅ **Audit trail** — store attempts, errors, timestamps for debugging/analytics
- ✅ **Optional: Object storage** — store large chunk blobs in S3/GCS instead of DB base64

---

## Architecture Overview

### Data Model — JobChunk Table

```sql
CREATE TABLE job_chunks (
    id SERIAL PRIMARY KEY,
    job_id INTEGER NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    chunk_id INTEGER NOT NULL,  -- 0-indexed chunk number
    
    -- Chunk metadata
    start_page INTEGER NOT NULL,
    end_page INTEGER NOT NULL,
    page_count INTEGER NOT NULL,
    has_overlap BOOLEAN DEFAULT FALSE,
    
    -- Chunk payload (choose one approach)
    file_b64 TEXT,              -- Base64 chunk PDF (for small chunks)
    storage_url VARCHAR(512),   -- S3/GCS URL (for large chunks, future)
    
    -- Processing state
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
        -- 'pending', 'processing', 'success', 'failed', 'retry_scheduled'
    celery_task_id VARCHAR(155),  -- Current/last task processing this chunk
    
    -- Retry tracking
    attempts INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3,
    last_error TEXT,
    last_error_code VARCHAR(50),
    
    -- Results (when successful)
    result_json JSON,  -- {sentences: [...], tokens: 123}
    processed_at TIMESTAMP,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    -- Indexes
    CONSTRAINT unique_job_chunk UNIQUE(job_id, chunk_id)
);

CREATE INDEX idx_job_chunks_job_id ON job_chunks(job_id);
CREATE INDEX idx_job_chunks_status ON job_chunks(status);
CREATE INDEX idx_job_chunks_job_status ON job_chunks(job_id, status);
```

**Migration file**: `migrations/versions/YYYYMMDD_add_job_chunks_persistence.py` (extend existing `ba1e2c3d4f56` or create new)

---

## Implementation Phases

### Phase 1: Database Model and Migration (Day 1)
**Goal**: Add `JobChunk` model and migrate existing `job_chunks` table to production schema.

#### 1.1 Update SQLAlchemy Model

**File**: `backend/app/models.py`

```python
class JobChunk(db.Model):
    """Model for tracking individual PDF chunk processing"""
    __tablename__ = 'job_chunks'
    
    id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(db.Integer, db.ForeignKey('jobs.id', ondelete='CASCADE'), nullable=False, index=True)
    chunk_id = db.Column(db.Integer, nullable=False)  # 0-indexed
    
    # Chunk metadata
    start_page = db.Column(db.Integer, nullable=False)
    end_page = db.Column(db.Integer, nullable=False)
    page_count = db.Column(db.Integer, nullable=False)
    has_overlap = db.Column(db.Boolean, default=False)
    
    # Chunk payload
    file_b64 = db.Column(db.Text)  # Base64 PDF chunk
    storage_url = db.Column(db.String(512))  # Future: S3/GCS URL
    
    # Processing state
    status = db.Column(db.String(20), nullable=False, default='pending', index=True)
    celery_task_id = db.Column(db.String(155))
    
    # Retry tracking
    attempts = db.Column(db.Integer, default=0)
    max_retries = db.Column(db.Integer, default=3)
    last_error = db.Column(db.Text)
    last_error_code = db.Column(db.String(50))
    
    # Results
    result_json = db.Column(db.JSON)  # {sentences: [...], tokens: 123}
    processed_at = db.Column(db.DateTime)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Constraints
    __table_args__ = (
        db.UniqueConstraint('job_id', 'chunk_id', name='unique_job_chunk'),
        db.Index('idx_job_chunks_job_status', 'job_id', 'status'),
    )
    
    def __repr__(self):
        return f'<JobChunk job_id={self.job_id} chunk_id={self.chunk_id} status={self.status}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'job_id': self.job_id,
            'chunk_id': self.chunk_id,
            'start_page': self.start_page,
            'end_page': self.end_page,
            'page_count': self.page_count,
            'status': self.status,
            'attempts': self.attempts,
            'max_retries': self.max_retries,
            'last_error': self.last_error,
            'last_error_code': self.last_error_code,
            'processed_at': self.processed_at.isoformat() + 'Z' if self.processed_at else None,
            'created_at': self.created_at.isoformat() + 'Z',
        }
    
    def can_retry(self) -> bool:
        """Check if chunk can be retried"""
        return self.status in ['failed', 'retry_scheduled'] and self.attempts < self.max_retries
    
    def get_chunk_metadata(self) -> Dict:
        """Build chunk metadata dict for process_chunk task"""
        return {
            'chunk_id': self.chunk_id,
            'job_id': self.job_id,
            'file_b64': self.file_b64,
            'storage_url': self.storage_url,
            'start_page': self.start_page,
            'end_page': self.end_page,
            'page_count': self.page_count,
            'has_overlap': self.has_overlap,
        }
```

#### 1.2 Create Migration

**File**: `backend/migrations/versions/YYYYMMDD_add_chunk_persistence_fields.py`

```python
"""Add persistence fields to job_chunks table

Revision ID: abc123def456
Revises: ba1e2c3d4f56
Create Date: 2025-10-04 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = 'abc123def456'
down_revision = 'ba1e2c3d4f56'
branch_labels = None
depends_on = None


def upgrade():
    # Check if columns already exist (idempotent migration)
    conn = op.get_bind()
    
    # Add new columns if they don't exist
    columns_to_add = [
        ('file_b64', sa.Text()),
        ('storage_url', sa.String(512)),
        ('celery_task_id', sa.String(155)),
        ('last_error', sa.Text()),
        ('last_error_code', sa.String(50)),
        ('result_json', postgresql.JSON()),
        ('processed_at', sa.DateTime()),
        ('updated_at', sa.DateTime(), {'server_default': sa.text('NOW()')}),
    ]
    
    for col_name, col_type, *extras in columns_to_add:
        # Check if column exists
        result = conn.execute(sa.text(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name='job_chunks' AND column_name=:col"
        ), {"col": col_name}).fetchone()
        
        if not result:
            kwargs = extras[0] if extras else {}
            op.add_column('job_chunks', sa.Column(col_name, col_type, **kwargs))
    
    # Add composite index if not exists
    result = conn.execute(sa.text(
        "SELECT to_regclass('public.idx_job_chunks_job_status')"
    )).scalar()
    
    if not result:
        op.create_index(
            'idx_job_chunks_job_status',
            'job_chunks',
            ['job_id', 'status']
        )


def downgrade():
    # Drop added columns and index
    op.drop_index('idx_job_chunks_job_status', table_name='job_chunks')
    
    columns_to_drop = [
        'file_b64', 'storage_url', 'celery_task_id',
        'last_error', 'last_error_code', 'result_json',
        'processed_at', 'updated_at'
    ]
    
    for col in columns_to_drop:
        op.drop_column('job_chunks', col)
```

#### 1.3 Run Migration

```bash
# Development
docker-compose -f docker-compose.dev.yml exec backend flask db migrate -m "Add chunk persistence fields"
docker-compose -f docker-compose.dev.yml exec backend flask db upgrade

# Production (Railway/Vercel)
railway run flask db upgrade
```

---

### Phase 2: Persist Chunks on Split (Day 1-2)
**Goal**: When splitting a PDF, create `JobChunk` DB rows instead of returning ephemeral dicts.

#### 2.1 Update ChunkingService

**File**: `backend/app/services/chunking_service.py`

```python
def split_pdf_and_persist(self, pdf_path: str, chunk_config: Dict, job_id: int, db) -> List[int]:
    """
    Split PDF into chunks and persist to database.
    
    Args:
        pdf_path: Path to source PDF
        chunk_config: Output from calculate_chunks()
        job_id: Job ID to associate chunks with
        db: SQLAlchemy database instance
        
    Returns:
        List of JobChunk IDs created
    """
    from app.models import JobChunk
    
    chunk_ids = []
    chunk_size = chunk_config['chunk_size']
    total_pages = chunk_config['total_pages']
    
    with open(pdf_path, 'rb') as pdf_file:
        pdf_reader = PdfReader(pdf_file)
        
        for i in range(chunk_config['num_chunks']):
            # Calculate page range with overlap
            start_page = max(0, i * chunk_size - (self.OVERLAP_PAGES if i > 0 else 0))
            end_page = min(total_pages, (i + 1) * chunk_size)
            
            # Create chunk PDF in memory
            pdf_writer = PdfWriter()
            for page_num in range(start_page, end_page):
                pdf_writer.add_page(pdf_reader.pages[page_num])
            
            # Encode chunk as base64
            buf = io.BytesIO()
            pdf_writer.write(buf)
            chunk_bytes = buf.getvalue()
            chunk_b64 = base64.b64encode(chunk_bytes).decode('ascii')
            
            # Create JobChunk row
            chunk = JobChunk(
                job_id=job_id,
                chunk_id=i,
                start_page=start_page,
                end_page=end_page - 1,  # Inclusive
                page_count=end_page - start_page,
                has_overlap=i > 0,
                file_b64=chunk_b64,
                status='pending',
                attempts=0,
                max_retries=chunk_config.get('max_retries', 3),
            )
            
            db.session.add(chunk)
            db.session.flush()  # Get chunk.id
            chunk_ids.append(chunk.id)
    
    db.session.commit()
    return chunk_ids
```

#### 2.2 Update process_pdf_async Task

**File**: `backend/app/tasks.py`

```python
@get_celery().task(bind=True, name='app.tasks.process_pdf_async')
def process_pdf_async(self, job_id: int, file_path: str, user_id: int, settings: dict, file_b64: Optional[str] = None):
    """Process PDF asynchronously with DB-backed chunk persistence"""
    db = get_db()
    Job, User = get_models()
    from app.models import JobChunk  # Import JobChunk
    _, _, ChunkingService, _ = get_services()
    JOB_STATUS_PROCESSING, JOB_STATUS_COMPLETED, JOB_STATUS_FAILED, _ = get_constants()
    
    chunking_service = ChunkingService()
    job = None
    
    try:
        # ... (existing job setup code) ...
        
        # Split PDF and persist chunks to DB
        chunk_db_ids = chunking_service.split_pdf_and_persist(
            file_path, 
            chunk_config, 
            job_id,
            db
        )
        
        logger.info(f"Job {job_id}: created {len(chunk_db_ids)} JobChunk rows in DB")
        
        # Update job
        job.total_chunks = len(chunk_db_ids)
        job.current_step = f"Processing {len(chunk_db_ids)} chunks"
        job.progress_percent = 15
        safe_db_commit(db)
        emit_progress(job_id)
        
        # Dispatch chunk tasks (read from DB)
        if len(chunk_db_ids) == 1:
            # Single chunk
            chunk = JobChunk.query.get(chunk_db_ids[0])
            result = process_chunk.run(chunk.get_chunk_metadata(), user_id, settings)
            chunk_results = [result]
            # ... update progress ...
        else:
            # Multiple chunks - dispatch parallel tasks
            chunk_tasks = []
            for chunk_db_id in chunk_db_ids:
                chunk = JobChunk.query.get(chunk_db_id)
                chunk.status = 'processing'  # Mark as dispatched
                chunk_tasks.append(
                    process_chunk.s(chunk.get_chunk_metadata(), user_id, settings)
                )
            safe_db_commit(db)
            
            # Use chord
            callback = finalize_job_results.s(job_id=job_id)
            chord_result = chord(chunk_tasks)(callback)
            
            logger.info(f"Job {job_id}: dispatched {len(chunk_tasks)} chunks, chord_id={chord_result.id}")
            return {'status': 'dispatched', 'job_id': job_id, 'chord_id': str(chord_result.id)}
        
        # ... (rest of single-chunk handling) ...
```

---

### Phase 3: Update process_chunk to Use DB (Day 2)
**Goal**: `process_chunk` reads from and updates the `JobChunk` row instead of just returning a result dict.

#### 3.1 Modify process_chunk Task

**File**: `backend/app/tasks.py`

```python
@get_celery().task(bind=True, name='app.tasks.process_chunk')
def process_chunk(self, chunk_info: Dict, user_id: int, settings: Dict) -> Dict:
    """
    Process a single PDF chunk with DB-backed state tracking.
    
    Args:
        chunk_info: Chunk metadata from JobChunk.get_chunk_metadata()
        user_id: User who initiated the job
        settings: Processing settings
        
    Returns:
        Result dict (for chord compatibility)
    """
    db = get_db()
    from app.models import JobChunk
    
    job_id = chunk_info.get('job_id')
    chunk_id = chunk_info.get('chunk_id')
    
    # Load JobChunk row
    chunk = JobChunk.query.filter_by(job_id=job_id, chunk_id=chunk_id).first()
    if not chunk:
        logger.error(f"JobChunk not found: job_id={job_id}, chunk_id={chunk_id}")
        return {
            'chunk_id': chunk_id,
            'status': 'failed',
            'error': 'Chunk record not found in database'
        }
    
    # Update chunk status to processing
    chunk.status = 'processing'
    chunk.attempts += 1
    chunk.celery_task_id = self.request.id
    safe_db_commit(db)
    
    try:
        # Get services
        _, GeminiService, _, _ = get_services()
        
        gemini_service = GeminiService(
            sentence_length_limit=settings['sentence_length_limit'],
            model_preference=settings['gemini_model'],
            ignore_dialogue=settings.get('ignore_dialogue', False),
            preserve_formatting=settings.get('preserve_formatting', True),
            fix_hyphenation=settings.get('fix_hyphenation', True),
            min_sentence_length=settings.get('min_sentence_length', 2),
        )
        
        # Extract text from chunk (prefer DB-stored base64)
        text = ""
        if chunk.file_b64:
            import io
            chunk_bytes = base64.b64decode(chunk.file_b64)
            pdf_file = io.BytesIO(chunk_bytes)
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            for page in pdf_reader.pages:
                text += (page.extract_text() or "") + "\n"
        elif chunk.storage_url:
            # Future: download from S3/GCS
            raise NotImplementedError("Storage URL not yet supported")
        else:
            raise ValueError("Chunk has no payload (file_b64 or storage_url)")
        
        if not text.strip():
            chunk.status = 'failed'
            chunk.last_error = 'No extractable text in PDF chunk'
            chunk.last_error_code = 'NO_TEXT'
            safe_db_commit(db)
            
            return {
                'chunk_id': chunk_id,
                'status': 'failed',
                'error': chunk.last_error,
                'start_page': chunk.start_page,
                'end_page': chunk.end_page
            }
        
        # Process with Gemini
        prompt = gemini_service.build_prompt()
        result = gemini_service.normalize_text(text, prompt)
        
        # Update chunk with success
        chunk.status = 'success'
        chunk.result_json = {
            'sentences': result['sentences'],
            'tokens': result.get('tokens', 0)
        }
        chunk.processed_at = datetime.utcnow()
        chunk.last_error = None
        chunk.last_error_code = None
        safe_db_commit(db)
        
        # Emit progress update
        try:
            from sqlalchemy import text
            db.session.execute(
                text("UPDATE jobs SET processed_chunks = COALESCE(processed_chunks,0) + 1 WHERE id = :id"),
                {"id": job_id}
            )
            Job, _ = get_models()
            job = Job.query.get(job_id)
            if job and job.total_chunks:
                pct = 15 + int((job.processed_chunks / float(job.total_chunks)) * 60)
                job.progress_percent = min(100, max(0, pct))
                job.current_step = f"Processing chunks ({job.processed_chunks}/{job.total_chunks})"
                safe_db_commit(db)
                emit_progress(job_id)
        except Exception as e:
            logger.warning(f"Failed to update job progress: {e}")
        
        return {
            'chunk_id': chunk_id,
            'sentences': result['sentences'],
            'tokens': result.get('tokens', 0),
            'start_page': chunk.start_page,
            'end_page': chunk.end_page,
            'status': 'success'
        }
        
    except SoftTimeLimitExceeded:
        chunk.status = 'failed'
        chunk.last_error = 'Processing timeout exceeded'
        chunk.last_error_code = 'TIMEOUT'
        safe_db_commit(db)
        
        return {
            'chunk_id': chunk_id,
            'status': 'failed',
            'error': chunk.last_error,
            'start_page': chunk.start_page,
            'end_page': chunk.end_page
        }
        
    except Exception as e:
        # Classify error and decide retry
        def _is_transient(err: Exception) -> bool:
            # ... (existing classification logic) ...
            pass
        
        from flask import current_app
        max_retries = int(current_app.config.get('CHUNK_TASK_MAX_RETRIES', 3))
        
        if _is_transient(e) and chunk.can_retry():
            # Mark for retry (orchestrator will re-dispatch)
            chunk.status = 'retry_scheduled'
            chunk.last_error = str(e)[:2000]
            chunk.last_error_code = 'TRANSIENT_ERROR'
            safe_db_commit(db)
            
            # Still raise retry for in-task retry
            base_delay = int(current_app.config.get('CHUNK_TASK_RETRY_DELAY', 1))
            delay = min(base_delay * (2 ** chunk.attempts), 60)
            logger.warning(
                f"Chunk {chunk_id} transient error, retry {chunk.attempts}/{max_retries} in {delay}s: {e}"
            )
            raise self.retry(exc=e, countdown=delay, max_retries=max_retries)
        
        # Non-transient or retries exhausted
        chunk.status = 'failed'
        chunk.last_error = str(e)[:2000]
        chunk.last_error_code = 'PROCESSING_ERROR'
        safe_db_commit(db)
        
        return {
            'chunk_id': chunk_id,
            'status': 'failed',
            'error': chunk.last_error,
            'start_page': chunk.start_page,
            'end_page': chunk.end_page
        }
```

---

### Phase 4: Orchestrated Retry in Finalization (Day 2-3)
**Goal**: `finalize_job_results` detects failed chunks and re-dispatches them automatically for up to N retry rounds.

#### 4.1 Add Retry Orchestration

**File**: `backend/app/tasks.py`

```python
@get_celery().task(bind=True, name='app.tasks.finalize_job_results')
def finalize_job_results(self, chunk_results, job_id, retry_round=0):
    """
    Finalize job with automatic chunk retry orchestration.
    
    Args:
        chunk_results: Results from process_chunk tasks
        job_id: Job ID
        retry_round: Current retry round (0 = first attempt)
    """
    db = get_db()
    Job, User = get_models()
    from app.models import JobChunk
    JOB_STATUS_PROCESSING, JOB_STATUS_COMPLETED, JOB_STATUS_FAILED, _ = get_constants()
    
    MAX_RETRY_ROUNDS = 2  # Allow 2 additional retry rounds after initial attempt
    
    try:
        logger.info(f"Job {job_id}: finalizing round {retry_round}, {len(chunk_results)} results")
        
        # Load all chunks from DB for authoritative status
        chunks = JobChunk.query.filter_by(job_id=job_id).order_by(JobChunk.chunk_id).all()
        
        # Identify failed chunks that can be retried
        failed_chunks = [c for c in chunks if c.status in ['failed', 'retry_scheduled'] and c.can_retry()]
        success_chunks = [c for c in chunks if c.status == 'success']
        permanent_failures = [c for c in chunks if c.status == 'failed' and not c.can_retry()]
        
        logger.info(
            f"Job {job_id}: success={len(success_chunks)}, "
            f"retryable_failures={len(failed_chunks)}, "
            f"permanent_failures={len(permanent_failures)}"
        )
        
        # If there are retryable failures and we haven't exceeded retry rounds
        if failed_chunks and retry_round < MAX_RETRY_ROUNDS:
            logger.info(f"Job {job_id}: scheduling retry round {retry_round + 1} for {len(failed_chunks)} chunks")
            
            # Update job status
            job = Job.query.get(job_id)
            job.current_step = f"Retrying {len(failed_chunks)} failed chunks (round {retry_round + 1})"
            job.retry_count = retry_round + 1
            safe_db_commit(db)
            emit_progress(job_id)
            
            # Re-dispatch failed chunks with exponential backoff
            retry_tasks = []
            for chunk in failed_chunks:
                chunk.status = 'retry_scheduled'
                safe_db_commit(db)
                
                # Get user_id and settings from job
                settings = job.processing_settings or {}
                user_id = job.user_id
                
                retry_tasks.append(
                    process_chunk.s(chunk.get_chunk_metadata(), user_id, settings)
                )
            
            # Dispatch retry chord with countdown (exponential backoff)
            countdown = min(10 * (2 ** retry_round), 300)  # Max 5 minutes
            callback = finalize_job_results.s(job_id=job_id, retry_round=retry_round + 1)
            
            chord_result = chord(retry_tasks)(callback.set(countdown=countdown))
            
            logger.info(
                f"Job {job_id}: dispatched {len(retry_tasks)} retry tasks, "
                f"chord_id={chord_result.id}, countdown={countdown}s"
            )
            
            return {
                'status': 'retrying',
                'retry_round': retry_round + 1,
                'chunks_to_retry': len(retry_tasks)
            }
        
        # No more retries — finalize with available results
        logger.info(f"Job {job_id}: finalizing with {len(success_chunks)} successful chunks")
        
        # Merge successful chunk results
        all_sentences = []
        total_tokens = 0
        
        for chunk in success_chunks:
            if chunk.result_json:
                sentences = chunk.result_json.get('sentences', [])
                all_sentences.extend(sentences)
                total_tokens += chunk.result_json.get('tokens', 0)
        
        # Update job
        job = Job.query.get(job_id)
        
        if len(success_chunks) == 0:
            job.status = JOB_STATUS_FAILED
            job.current_step = "Failed"
            job.error_message = f"All {len(chunks)} chunks failed. Check chunk error details."
        elif len(permanent_failures) > 0:
            job.status = JOB_STATUS_COMPLETED  # Partial success
            job.current_step = "Completed (with failures)"
            job.error_message = f"{len(permanent_failures)} chunks failed permanently after {retry_round + 1} rounds."
        else:
            job.status = JOB_STATUS_COMPLETED
            job.current_step = "Completed"
        
        job.progress_percent = 100
        job.processed_chunks = len(success_chunks)
        job.actual_tokens = total_tokens
        job.gemini_tokens_used = total_tokens
        job.gemini_api_calls = len(success_chunks)
        job.completed_at = datetime.utcnow()
        
        # Store chunk results reference (for backward compat)
        job.chunk_results = [
            {'chunk_id': c.chunk_id, 'status': c.status}
            for c in chunks
        ]
        job.failed_chunks = [c.chunk_id for c in permanent_failures] if permanent_failures else None
        
        # Calculate processing time
        if job.started_at:
            processing_time = (job.completed_at - job.started_at).total_seconds()
            job.processing_time_seconds = int(processing_time)
        
        safe_db_commit(db)
        emit_progress(job_id)
        
        logger.info(
            f"Job {job_id}: finalized status={job.status}, "
            f"sentences={len(all_sentences)}, retries={retry_round}"
        )
        
        return {
            'status': 'success',
            'sentences': all_sentences,
            'total_tokens': total_tokens,
            'chunks_processed': len(success_chunks),
            'failed_chunks': [c.chunk_id for c in permanent_failures],
            'retry_rounds': retry_round
        }
        
    except Exception as e:
        logger.error(f"Job {job_id}: finalization failed: {e}")
        
        try:
            job = Job.query.get(job_id)
            if job:
                job.status = JOB_STATUS_FAILED
                job.error_message = f"Finalization error: {str(e)[:512]}"
                job.completed_at = datetime.utcnow()
                safe_db_commit(db)
                emit_progress(job_id)
        except Exception:
            pass
        
        raise
```

---

### Phase 5: Manual Retry API (Day 3)
**Goal**: Provide API endpoint and UI to manually retry specific failed chunks.

#### 5.1 Add Manual Retry Endpoint

**File**: `backend/app/routes.py`

```python
@main_bp.route('/jobs/<int:job_id>/chunks/retry', methods=['POST'])
@jwt_required()
def retry_failed_chunks(job_id):
    """
    Manually retry failed chunks for a job.
    
    Request body:
    {
        "chunk_ids": [2, 5, 7],  // Optional: specific chunks, or retry all failed
        "force": false            // Force retry even if max_retries exceeded
    }
    """
    from app.models import JobChunk
    from app.tasks import process_chunk
    from celery import group
    
    user_id = int(get_jwt_identity())
    
    # Verify job ownership
    job = Job.query.filter_by(id=job_id, user_id=user_id).first()
    if not job:
        return jsonify({'error': 'Job not found or access denied'}), 404
    
    data = request.get_json() or {}
    chunk_ids = data.get('chunk_ids')  # Optional list
    force = data.get('force', False)
    
    # Query failed chunks
    query = JobChunk.query.filter_by(job_id=job_id)
    
    if chunk_ids:
        query = query.filter(JobChunk.chunk_id.in_(chunk_ids))
    else:
        # Retry all failed chunks
        query = query.filter(JobChunk.status.in_(['failed', 'retry_scheduled']))
    
    chunks_to_retry = query.all()
    
    # Filter by retry eligibility
    if not force:
        chunks_to_retry = [c for c in chunks_to_retry if c.can_retry()]
    
    if not chunks_to_retry:
        return jsonify({
            'message': 'No chunks eligible for retry',
            'retried_count': 0
        }), 200
    
    # Dispatch retry tasks
    retry_tasks = []
    settings = job.processing_settings or {}
    
    for chunk in chunks_to_retry:
        chunk.status = 'retry_scheduled'
        if force:
            chunk.attempts = 0  # Reset attempts if forced
        db.session.add(chunk)
        
        retry_tasks.append(
            process_chunk.s(chunk.get_chunk_metadata(), user_id, settings)
        )
    
    db.session.commit()
    
    # Dispatch tasks (no chord callback — let user check status)
    group_result = group(retry_tasks).apply_async()
    
    # Update job status
    job.current_step = f"Manually retrying {len(chunks_to_retry)} chunks"
    job.status = 'processing'
    job.retry_count += 1
    db.session.commit()
    
    emit_progress(job_id)
    
    logger.info(f"Job {job_id}: manually retrying {len(chunks_to_retry)} chunks, group_id={group_result.id}")
    
    return jsonify({
        'message': f'Retrying {len(chunks_to_retry)} chunks',
        'retried_count': len(chunks_to_retry),
        'group_id': str(group_result.id),
        'chunk_ids': [c.chunk_id for c in chunks_to_retry]
    }), 200


@main_bp.route('/jobs/<int:job_id>/chunks', methods=['GET'])
@jwt_required()
def get_job_chunks(job_id):
    """Get detailed chunk status for a job"""
    from app.models import JobChunk
    
    user_id = int(get_jwt_identity())
    
    # Verify job ownership
    job = Job.query.filter_by(id=job_id, user_id=user_id).first()
    if not job:
        return jsonify({'error': 'Job not found or access denied'}), 404
    
    chunks = JobChunk.query.filter_by(job_id=job_id).order_by(JobChunk.chunk_id).all()
    
    return jsonify({
        'job_id': job_id,
        'total_chunks': len(chunks),
        'chunks': [c.to_dict() for c in chunks],
        'summary': {
            'pending': sum(1 for c in chunks if c.status == 'pending'),
            'processing': sum(1 for c in chunks if c.status == 'processing'),
            'success': sum(1 for c in chunks if c.status == 'success'),
            'failed': sum(1 for c in chunks if c.status == 'failed'),
            'retry_scheduled': sum(1 for c in chunks if c.status == 'retry_scheduled'),
        }
    }), 200
```

#### 5.2 Add to API Documentation

**File**: `backend/API_DOCUMENTATION.md`

Add new endpoints:

```markdown
### GET /api/v1/jobs/:id/chunks
Get detailed status of all chunks for a job.

**Response**:
```json
{
  "job_id": 123,
  "total_chunks": 10,
  "chunks": [
    {
      "id": 456,
      "chunk_id": 0,
      "status": "success",
      "attempts": 1,
      "processed_at": "2025-10-04T10:15:00Z",
      ...
    }
  ],
  "summary": {
    "success": 8,
    "failed": 2,
    "retry_scheduled": 0
  }
}
```

### POST /api/v1/jobs/:id/chunks/retry
Manually retry failed chunks.

**Request**:
```json
{
  "chunk_ids": [2, 7],  // Optional
  "force": false
}
```

**Response**:
```json
{
  "message": "Retrying 2 chunks",
  "retried_count": 2,
  "group_id": "abc-123-def",
  "chunk_ids": [2, 7]
}
```
```

---

### Phase 6: Frontend Integration (Day 4)
**Goal**: Show chunk status in UI and provide retry button.

#### 6.1 Add Chunk Status Component

**File**: `frontend/src/components/JobChunkStatus.tsx`

```typescript
import { useState, useEffect } from 'react';
import { Box, Typography, LinearProgress, Button, Chip, Alert } from '@mui/material';
import { api } from '@/lib/api';

interface ChunkStatusProps {
  jobId: number;
  onRetry?: () => void;
}

export default function JobChunkStatus({ jobId, onRetry }: ChunkStatusProps) {
  const [chunks, setChunks] = useState<any[]>([]);
  const [summary, setSummary] = useState<any>({});
  const [loading, setLoading] = useState(true);
  
  useEffect(() => {
    loadChunks();
  }, [jobId]);
  
  const loadChunks = async () => {
    try {
      const { data } = await api.get(`/jobs/${jobId}/chunks`);
      setChunks(data.chunks);
      setSummary(data.summary);
    } catch (error) {
      console.error('Failed to load chunks:', error);
    } finally {
      setLoading(false);
    }
  };
  
  const handleRetry = async (chunkIds?: number[]) => {
    try {
      await api.post(`/jobs/${jobId}/chunks/retry`, { chunk_ids: chunkIds });
      loadChunks();
      onRetry?.();
    } catch (error) {
      console.error('Retry failed:', error);
    }
  };
  
  if (loading) return <LinearProgress />;
  
  const hasFailures = summary.failed > 0;
  
  return (
    <Box>
      <Typography variant="h6">Chunk Processing Details</Typography>
      
      <Box display="flex" gap={1} my={2}>
        <Chip label={`Success: ${summary.success || 0}`} color="success" size="small" />
        <Chip label={`Failed: ${summary.failed || 0}`} color="error" size="small" />
        <Chip label={`Processing: ${summary.processing || 0}`} color="info" size="small" />
        <Chip label={`Pending: ${summary.pending || 0}`} color="default" size="small" />
      </Box>
      
      {hasFailures && (
        <Alert severity="warning" action={
          <Button color="inherit" size="small" onClick={() => handleRetry()}>
            Retry All Failed
          </Button>
        }>
          {summary.failed} chunk(s) failed. You can retry them manually.
        </Alert>
      )}
      
      {/* Optionally show detailed chunk list */}
    </Box>
  );
}
```

#### 6.2 Integrate into Job Details Page

**File**: `frontend/src/app/history/page.tsx` (or job details modal)

```typescript
import JobChunkStatus from '@/components/JobChunkStatus';

// Inside job details render:
{job.status === 'completed' && job.failed_chunks?.length > 0 && (
  <JobChunkStatus 
    jobId={job.id} 
    onRetry={() => refetchJobStatus()} 
  />
)}
```

---

### Phase 7: Object Storage (Optional — Day 5+)
**Goal**: Store large chunk blobs in S3/GCS instead of DB base64 for scalability.

#### 7.1 Add Storage Service

**File**: `backend/app/services/storage_service.py`

```python
"""Service for storing chunk files in cloud object storage"""
import os
from typing import Optional
from google.cloud import storage  # or boto3 for S3
import logging

logger = logging.getLogger(__name__)


class StorageService:
    """Upload/download chunk PDFs to/from cloud storage"""
    
    def __init__(self):
        self.bucket_name = os.getenv('CHUNK_STORAGE_BUCKET')
        self.use_storage = os.getenv('USE_OBJECT_STORAGE', 'false').lower() == 'true'
        
        if self.use_storage:
            self.client = storage.Client()
            self.bucket = self.client.bucket(self.bucket_name)
    
    def upload_chunk(self, chunk_bytes: bytes, job_id: int, chunk_id: int) -> Optional[str]:
        """
        Upload chunk PDF to object storage.
        
        Returns:
            Storage URL (gs:// or s3://) or None if storage disabled
        """
        if not self.use_storage:
            return None
        
        blob_name = f"jobs/{job_id}/chunks/chunk_{chunk_id}.pdf"
        blob = self.bucket.blob(blob_name)
        blob.upload_from_string(chunk_bytes, content_type='application/pdf')
        
        # Return gs:// URL or signed URL
        return f"gs://{self.bucket_name}/{blob_name}"
    
    def download_chunk(self, storage_url: str) -> bytes:
        """Download chunk PDF from object storage"""
        # Parse gs:// or s3:// URL
        blob_name = storage_url.replace(f"gs://{self.bucket_name}/", "")
        blob = self.bucket.blob(blob_name)
        return blob.download_as_bytes()
    
    def delete_chunk(self, storage_url: str):
        """Delete chunk from storage"""
        blob_name = storage_url.replace(f"gs://{self.bucket_name}/", "")
        blob = self.bucket.blob(blob_name)
        blob.delete()
```

#### 7.2 Update ChunkingService

```python
def split_pdf_and_persist(self, pdf_path: str, chunk_config: Dict, job_id: int, db, use_storage=False) -> List[int]:
    """Split PDF with optional object storage"""
    from app.services.storage_service import StorageService
    
    storage_service = StorageService() if use_storage else None
    # ... (chunk creation loop) ...
    
    for i in range(chunk_config['num_chunks']):
        # ... create chunk PDF ...
        
        chunk_bytes = buf.getvalue()
        
        # Upload to storage or encode base64
        if storage_service and storage_service.use_storage:
            storage_url = storage_service.upload_chunk(chunk_bytes, job_id, i)
            chunk = JobChunk(
                # ... other fields ...
                storage_url=storage_url,
                file_b64=None,  # Don't store in DB
            )
        else:
            chunk_b64 = base64.b64encode(chunk_bytes).decode('ascii')
            chunk = JobChunk(
                # ... other fields ...
                file_b64=chunk_b64,
                storage_url=None,
            )
```

#### 7.3 Update process_chunk

```python
# In process_chunk task:
if chunk.storage_url:
    from app.services.storage_service import StorageService
    storage_service = StorageService()
    chunk_bytes = storage_service.download_chunk(chunk.storage_url)
    pdf_file = io.BytesIO(chunk_bytes)
    # ... extract text ...
elif chunk.file_b64:
    chunk_bytes = base64.b64decode(chunk.file_b64)
    # ... (existing code) ...
```

---

## Configuration and Environment Variables

Add to `.env` / Railway environment:

```bash
# Chunk retry configuration
CHUNK_TASK_MAX_RETRIES=3
CHUNK_TASK_RETRY_DELAY=2  # seconds
MAX_RETRY_ROUNDS=2  # Orchestrated retry rounds in finalize_job_results

# Object storage (optional Phase 7)
USE_OBJECT_STORAGE=false
CHUNK_STORAGE_BUCKET=your-bucket-name
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json  # For GCS
# AWS_ACCESS_KEY_ID=...  # For S3
# AWS_SECRET_ACCESS_KEY=...
```

---

## Testing Strategy

### Unit Tests

**File**: `backend/tests/test_chunk_persistence.py`

```python
import pytest
from app.models import Job, JobChunk
from app.services.chunking_service import ChunkingService

def test_split_pdf_creates_job_chunks(db, sample_pdf):
    """Test that split_pdf_and_persist creates JobChunk rows"""
    job = Job(user_id=1, original_filename='test.pdf', model='gemini-2.5-flash', ...)
    db.session.add(job)
    db.session.commit()
    
    service = ChunkingService()
    chunk_config = service.calculate_chunks(100)
    chunk_ids = service.split_pdf_and_persist(sample_pdf, chunk_config, job.id, db)
    
    assert len(chunk_ids) == chunk_config['num_chunks']
    
    chunks = JobChunk.query.filter_by(job_id=job.id).all()
    assert len(chunks) == chunk_config['num_chunks']
    assert all(c.status == 'pending' for c in chunks)
    assert all(c.file_b64 is not None for c in chunks)

def test_chunk_can_retry_logic():
    """Test JobChunk.can_retry() method"""
    chunk = JobChunk(attempts=0, max_retries=3, status='failed')
    assert chunk.can_retry() is True
    
    chunk.attempts = 3
    assert chunk.can_retry() is False
    
    chunk.status = 'success'
    assert chunk.can_retry() is False

def test_manual_retry_endpoint(client, auth_headers, db):
    """Test POST /jobs/:id/chunks/retry"""
    # Create job with failed chunks
    job = Job(...)
    db.session.add(job)
    db.session.commit()
    
    chunk1 = JobChunk(job_id=job.id, chunk_id=0, status='failed', attempts=1, ...)
    chunk2 = JobChunk(job_id=job.id, chunk_id=1, status='success', ...)
    db.session.add_all([chunk1, chunk2])
    db.session.commit()
    
    response = client.post(
        f'/api/v1/jobs/{job.id}/chunks/retry',
        headers=auth_headers,
        json={}
    )
    
    assert response.status_code == 200
    data = response.get_json()
    assert data['retried_count'] == 1
    assert 0 in data['chunk_ids']
```

### Integration Tests

```python
def test_end_to_end_retry_flow(celery_worker, db, sample_pdf):
    """Test full retry orchestration flow"""
    # 1. Create job and chunks
    # 2. Simulate chunk failure
    # 3. Trigger finalize_job_results
    # 4. Verify retry round dispatched
    # 5. Verify eventual completion
    pass
```

---

## Rollout Plan

### Week 1: Core Infrastructure
- **Day 1**: Phase 1 + 2 (DB model, migration, persist chunks on split)
- **Day 2**: Phase 3 (update process_chunk to use DB)
- **Day 3**: Phase 4 (orchestrated retry in finalize)

### Week 2: User-Facing Features
- **Day 4**: Phase 5 (manual retry API)
- **Day 5**: Phase 6 (frontend chunk status + retry UI)

### Week 3+: Optimization (Optional)
- **Future**: Phase 7 (object storage for scalability)

### Deployment Strategy
1. **Development**: Test all phases in local Docker environment
2. **Staging**: Deploy to Railway staging with real Gemini calls
3. **Production**: Blue-green deploy with database migration
   - Run migration during low-traffic window
   - Monitor error rates and retry metrics
   - Gradual rollout (10% → 50% → 100% traffic)

---

## Monitoring and Observability

### Key Metrics to Track

```python
# Add to backend/app/utils/metrics.py
from prometheus_client import Counter, Histogram, Gauge

chunk_processing_total = Counter(
    'chunk_processing_total',
    'Total chunks processed',
    ['status']  # success, failed, retry
)

chunk_retry_rounds = Histogram(
    'chunk_retry_rounds',
    'Number of retry rounds per job',
    buckets=[0, 1, 2, 3, 5]
)

chunk_processing_duration = Histogram(
    'chunk_processing_duration_seconds',
    'Time to process a chunk',
    ['status']
)

active_chunks_gauge = Gauge(
    'active_chunks',
    'Number of chunks currently processing',
    ['job_id']
)
```

### Logging

```python
# Structured logging for chunk events
logger.info(
    "Chunk lifecycle event",
    extra={
        'event': 'chunk_failed',
        'job_id': job_id,
        'chunk_id': chunk_id,
        'attempts': chunk.attempts,
        'error_code': chunk.last_error_code,
        'retry_eligible': chunk.can_retry()
    }
)
```

### Alerts

- **High chunk failure rate**: > 20% of chunks failing
- **Stuck jobs**: Job in processing state > 30 minutes with no chunk progress
- **Retry exhaustion**: Job completes with > 3 permanent failures

---

## Migration Path for Existing Jobs

For jobs created before Phase 1 deployment:

```python
# One-time migration script: backend/scripts/backfill_job_chunks.py
"""Backfill JobChunk rows for existing jobs"""

from app import create_app, db
from app.models import Job, JobChunk

app = create_app()
with app.app_context():
    # Find completed jobs without chunks
    jobs_without_chunks = Job.query.filter(
        ~Job.id.in_(db.session.query(JobChunk.job_id).distinct())
    ).all()
    
    for job in jobs_without_chunks:
        if job.chunk_results:
            # Reconstruct JobChunk rows from job.chunk_results
            for chunk_data in job.chunk_results:
                chunk = JobChunk(
                    job_id=job.id,
                    chunk_id=chunk_data['chunk_id'],
                    status=chunk_data.get('status', 'success'),
                    # ... populate from chunk_data ...
                )
                db.session.add(chunk)
    
    db.session.commit()
    print(f"Backfilled chunks for {len(jobs_without_chunks)} jobs")
```

---

## Success Criteria

- ✅ **Zero permanent data loss**: All chunks persisted in DB before processing
- ✅ **Automatic recovery**: Failed chunks retried up to N rounds without manual intervention
- ✅ **User control**: Manual retry button in UI for edge cases
- ✅ **Observability**: Chunk-level status visible in UI and logs
- ✅ **Scalability**: Object storage option for large PDFs (Phase 7)

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| DB storage limits for base64 | Implement Phase 7 (object storage) when chunks > 1MB |
| Migration downtime | Use idempotent migrations + zero-downtime deploy |
| Retry storms | Exponential backoff + max retry rounds limit |
| Partial failures UX | Show partial completion status + retry button |
| Concurrency bugs | Use DB-level atomic updates (UPDATE ... RETURNING) |

---

## Future Enhancements

1. **Smart retry scheduling**: ML-based prediction of retry success probability
2. **Chunk-level caching**: Cache Gemini results by content hash to avoid re-processing duplicates
3. **Priority queues**: User-requested retries jump to front of queue
4. **Webhook notifications**: Alert users when manual retry needed
5. **Admin dashboard**: View all failed chunks across users for debugging

---

## References

- **Current implementation**: `backend/app/tasks.py`, `backend/app/services/chunking_service.py`
- **Migration guide**: `backend/migrations/versions/ba1e2c3d4f56_add_job_chunks_table.py`
- **Celery retry docs**: https://docs.celeryproject.org/en/stable/userguide/tasks.html#retrying
- **PostgreSQL RETURNING**: https://www.postgresql.org/docs/current/dml-returning.html

---

**End of Roadmap** — Ready for implementation 🚀

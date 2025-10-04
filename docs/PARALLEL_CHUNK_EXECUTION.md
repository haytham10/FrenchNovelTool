# Parallel Chunk Execution Implementation

## Overview
This document describes the implementation of parallel chunk execution for PDF processing jobs, replacing the previous sequential processing approach with Celery's chord primitive for concurrent task execution.

## Changes Made

### 1. Core Task Modifications (`backend/app/tasks.py`)

#### Added Chord Import
```python
from celery import group, chord
```

#### New Task: `finalize_job_results`
A new Celery task that acts as the chord callback, executing after all chunk tasks complete:

**Responsibilities:**
- Merges chunk results from all parallel tasks
- Calculates aggregate metrics (total tokens, failed chunks)
- Updates job status (COMPLETED or FAILED)
- Persists final results to database
- Emits WebSocket progress update for real-time UI feedback

**Signature:**
```python
@get_celery().task(bind=True, name='app.tasks.finalize_job_results')
def finalize_job_results(self, chunk_results, job_id)
```

**Error Handling:**
- Marks job as FAILED if all chunks fail
- Marks job as COMPLETED if at least one chunk succeeds
- Logs detailed failure reasons for debugging
- Safe database commit with retry logic
- Emits WebSocket updates even on failure

#### Modified Task: `process_pdf_async`
Refactored multi-chunk processing path to use parallel execution:

**Before (Sequential):**
```python
for idx, chunk in enumerate(chunks, start=1):
    result = process_chunk.run(chunk, user_id, settings)
    chunk_results.append(result)
    # Update progress...
```

**After (Parallel with Chord):**
```python
if len(chunks) == 1:
    # Single chunk - process directly (no chord overhead)
    result = process_chunk.run(chunks[0], user_id, settings)
    # Continue with inline finalization...
else:
    # Multiple chunks - dispatch in parallel
    chunk_tasks = [process_chunk.s(chunk, user_id, settings) for chunk in chunks]
    callback = finalize_job_results.s(job_id=job_id)
    chord_result = chord(chunk_tasks)(callback)
    # Return early; finalize_job_results completes the job
    return {'status': 'dispatched', 'job_id': job_id, 'chord_id': str(chord_result.id)}
```

**Key Design Decision:**
- Single-chunk jobs remain synchronous (no chord overhead)
- Multi-chunk jobs dispatch tasks in parallel and return immediately
- Finalization happens in callback task, not in orchestrator

#### Modified Task: `process_chunk`
Added automatic cleanup of temporary chunk files:

**Changes:**
- Cleans up chunk PDF file after successful processing
- Cleans up chunk PDF file on timeout errors
- Cleans up chunk PDF file on general exceptions
- Logs cleanup failures but doesn't fail the task

**Impact:**
- Prevents orphaned temporary files
- Reduces disk space usage
- Essential for parallel execution (orchestrator returns early)

### 2. Worker Concurrency Configuration

#### Updated: `backend/railway-worker-entrypoint.sh`
Changed default concurrency from 2 to 4 workers:
```bash
--concurrency=${CELERY_CONCURRENCY:-4}
```

#### Existing Configurations (Already Set):
- `docker-compose.dev.yml`: `--concurrency=4`
- `docker-compose.yml`: `--concurrency=4`
- `backend/celery-entrypoint.sh`: `--concurrency=4`

### 3. Test Coverage (`backend/tests/test_async_processing.py`)

Added test stubs for new functionality:
- `test_parallel_chunk_dispatch`: Validates chord usage for multi-chunk jobs
- `test_finalize_with_all_success`: Tests finalization with all chunks succeeding
- `test_finalize_with_partial_failures`: Tests finalization with mixed results
- `test_finalize_with_all_failures`: Tests finalization when all chunks fail

**Note:** Full integration tests require Celery test infrastructure (pytest-celery)

## Expected Performance Improvements

### Before (Sequential Processing)
- 4 chunks × 30 seconds each = **120 seconds total**
- Worker utilization: 25% (1 of 4 workers busy)

### After (Parallel Processing)
- 4 chunks × 30 seconds in parallel = **~30 seconds total**
- Worker utilization: 100% (4 workers processing simultaneously)
- **75% reduction in processing time**

### Actual Improvement Formula
For N chunks with average processing time T and W workers:
- **Sequential:** Total Time = N × T
- **Parallel:** Total Time = ⌈N / W⌉ × T

With 4 workers:
- 2 chunks: 50% faster
- 4 chunks: 75% faster
- 8 chunks: 75% faster (limited by worker count)

## Architecture Flow

### Single-Chunk Job Flow
```
process_pdf_async
  ├─> process_chunk.run() (synchronous)
  ├─> merge_chunk_results()
  ├─> Update job status
  ├─> emit_progress()
  └─> Return success
```

### Multi-Chunk Job Flow (NEW)
```
process_pdf_async
  ├─> Create chord: [process_chunk.s() × N]
  ├─> Set callback: finalize_job_results.s()
  └─> Return 'dispatched'

[Parallel Execution]
  ├─> process_chunk (Worker 1)
  ├─> process_chunk (Worker 2)
  ├─> process_chunk (Worker 3)
  └─> process_chunk (Worker 4)

finalize_job_results (callback)
  ├─> merge_chunk_results()
  ├─> Calculate metrics
  ├─> Update job status
  ├─> emit_progress()
  └─> Return success
```

## WebSocket Integration

### Progress Updates
- **Before chunking:** `emit_progress()` in orchestrator
- **During parallel processing:** No per-chunk updates (would cause race conditions)
- **After completion:** `emit_progress()` in finalize_job_results

### Real-Time Status
Jobs in parallel execution show:
- `status: 'processing'`
- `current_step: 'Processing'` (set before chord dispatch)
- Progress updates happen when finalize callback completes

## Error Handling

### Chunk Task Failures
- Each `process_chunk` task handles its own errors
- Failed chunks return `{status: 'failed', error: '...', chunk_id: N}`
- Successful chunks return `{status: 'success', sentences: [...], tokens: N}`

### Finalization Logic
```python
success_count = len([r for r in chunk_results if r.get('status') == 'success'])

if success_count == 0:
    job.status = JOB_STATUS_FAILED
    job.error_message = "All chunks failed to process..."
else:
    job.status = JOB_STATUS_COMPLETED
    job.failed_chunks = [r['chunk_id'] for r in chunk_results if r.get('status') == 'failed']
```

### Database Safety
- Uses `safe_db_commit()` with retry logic
- Handles transient network errors (common in cloud deployments)
- Rolls back on persistent failures

## Rollback Plan

### If Critical Issues Arise

#### Option 1: Emergency Rollback (Quick)
Revert to sequential processing by modifying `process_pdf_async`:

```python
# Comment out parallel path
# else:
#     chunk_tasks = [...]
#     chord_result = chord(chunk_tasks)(callback)
#     return {'status': 'dispatched', ...}

# Restore sequential loop
else:
    chunk_results = []
    for idx, chunk in enumerate(chunks, start=1):
        result = process_chunk.run(chunk, user_id, settings)
        chunk_results.append(result)
        # Update progress...
```

#### Option 2: Git Revert (Clean)
```bash
# Revert the parallel execution commit
git revert <commit-hash>

# Redeploy backend and worker
make deploy
```

#### Option 3: Environment Variable Toggle (Future Enhancement)
Could add a feature flag:
```python
ENABLE_PARALLEL_CHUNKS = os.getenv('ENABLE_PARALLEL_CHUNKS', 'true').lower() == 'true'

if ENABLE_PARALLEL_CHUNKS and len(chunks) > 1:
    # Use chord
else:
    # Use sequential
```

### Rollback Checklist
- [ ] Monitor Celery worker logs for task failures
- [ ] Check Flower dashboard for stuck tasks
- [ ] Verify Redis memory usage (chord state storage)
- [ ] Test with sample multi-chunk PDF
- [ ] Monitor job completion rates
- [ ] Check WebSocket events in browser console

## Monitoring & Validation

### Key Metrics to Monitor
1. **Job Processing Time:** Should decrease by 50-70% for multi-chunk jobs
2. **Worker Utilization:** Should increase to 80-100% during peak load
3. **Chord Callback Success Rate:** Should be ~100%
4. **Temporary File Count:** Should remain stable (cleanup working)

### Validation Steps
1. **Single-Chunk Job:**
   - Upload small PDF (≤30 pages)
   - Verify synchronous processing (no chord)
   - Check job completes successfully

2. **Multi-Chunk Job:**
   - Upload large PDF (>30 pages, e.g., 80 pages)
   - Verify chord dispatch in logs: `"dispatched N chunks in parallel"`
   - Check Flower for parallel tasks
   - Verify finalize callback executes
   - Check WebSocket progress updates
   - Verify job completes with correct sentence count

3. **Failure Scenarios:**
   - Simulate API timeout (invalid Gemini key)
   - Verify partial failures handled correctly
   - Check failed_chunks recorded
   - Verify WebSocket error propagation

### Celery Commands
```bash
# Monitor worker activity
celery -A celery_worker.celery inspect active

# Check registered tasks
celery -A celery_worker.celery inspect registered

# Monitor task stats
celery -A celery_worker.celery inspect stats

# View Flower dashboard
open http://localhost:5555
```

## Deployment Considerations

### Railway Deployment
Set environment variable for concurrency:
```bash
CELERY_CONCURRENCY=4
```

### Docker Deployment
Already configured in docker-compose files:
```yaml
celery-worker:
  command: celery -A app.celery_app:celery worker --loglevel=info --concurrency=4
```

### Resource Requirements
- **Redis:** Stores chord state; ensure sufficient memory
- **Database:** Increased concurrent writes; ensure connection pool sized appropriately
- **Worker Memory:** Each worker processes 1 chunk; monitor memory per task

### Environment Variables
- `CELERY_CONCURRENCY`: Worker pool size (default: 4)
- `REDIS_URL`: Celery broker and result backend
- `DATABASE_URL`: PostgreSQL connection string

## Known Limitations

1. **WebSocket Progress Granularity:**
   - No per-chunk progress updates during parallel execution
   - Only see final progress when all chunks complete
   - Future: Could add intermediate updates with task state polling

2. **Worker Pool Constraints:**
   - Maximum parallelism = worker concurrency (4 workers)
   - PDFs with >4 chunks will process in batches
   - Future: Auto-scale workers based on queue depth

3. **Chunk File Cleanup:**
   - Relies on process_chunk tasks completing
   - Orphaned files possible if worker crashes mid-task
   - Future: Add periodic cleanup job for stale temp files

4. **Testing Coverage:**
   - Integration tests are placeholders
   - Full Celery test infrastructure needed
   - Future: Add pytest-celery for comprehensive testing

## Future Enhancements

1. **Dynamic Concurrency:**
   - Auto-scale workers based on queue size
   - Adjust chunk size based on available workers

2. **Progress Streaming:**
   - Emit WebSocket updates as each chunk completes
   - Requires task state tracking and periodic polling

3. **Adaptive Chunking:**
   - Adjust chunk size based on historical processing times
   - Optimize for target completion time

4. **Failure Recovery:**
   - Retry individual failed chunks
   - Graceful degradation (complete job with partial results)

5. **Resource Monitoring:**
   - Track memory usage per chunk
   - Prevent OOM by limiting concurrent chunks

## References

- [Celery Chord Documentation](https://docs.celeryproject.org/en/stable/userguide/canvas.html#chord)
- [WebSocket and Parallel Roadmap](./roadmaps/WEBSOCKET_AND_PARALLEL_ROADMAP.md)
- [Async PDF Processing Roadmap](./roadmaps/6-async-pdf-processing-roadmap.md)
- [Celery Best Practices](https://docs.celeryproject.org/en/stable/userguide/tasks.html#tips-and-best-practices)

## Contact

For issues or questions about this implementation:
- Review the [WEBSOCKET_AND_PARALLEL_ROADMAP.md](./roadmaps/WEBSOCKET_AND_PARALLEL_ROADMAP.md)
- Check Celery worker logs for task-specific errors
- Monitor Flower dashboard for task states
- Review WebSocket events in browser developer console

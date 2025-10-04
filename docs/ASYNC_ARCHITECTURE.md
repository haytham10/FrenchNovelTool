# Async PDF Processing - Visual Guide

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Client Application                           │
│                         (Next.js Frontend)                           │
└────────────────────┬─────────────────────────┬──────────────────────┘
                     │                         │
                     │ 1. Upload PDF           │ 2. Poll Status
                     │    /jobs/confirm        │    /jobs/:id
                     ▼                         │
┌─────────────────────────────────────────────┼──────────────────────┐
│                     Flask API                │                      │
│  ┌──────────────────────────────────────────┘                      │
│  │                                                                  │
│  │  POST /process-pdf-async → Enqueue Task                         │
│  │  GET  /jobs/:id          → Query Status                         │
│  │  POST /jobs/:id/cancel   → Revoke Task                          │
│  │                                                                  │
│  └──────────────────┬───────────────────────────────────────┬──────┘
│                     │                                        │
│                     │ 3. Queue Task                          │ 4. Update Status
│                     ▼                                        │
│  ┌─────────────────────────────────────────────────────┐    │
│  │                     Redis                            │    │
│  │  ┌─────────────────────────────────────┐            │    │
│  │  │  Task Queue                          │            │    │
│  │  │  - Job ID                            │            │    │
│  │  │  - PDF Path                          │            │    │
│  │  │  - User Settings                     │            │    │
│  │  └─────────────────────────────────────┘            │    │
│  └──────────────────┬───────────────────────────────────┘    │
│                     │                                        │
│                     │ 5. Dequeue                             │
│                     ▼                                        │
│  ┌─────────────────────────────────────────────────────┐    │
│  │              Celery Workers (x4)                     │    │
│  │                                                      │    │
│  │  process_pdf_async()                                │    │
│  │    ├─ Analyze PDF (page count)                      │    │
│  │    ├─ Calculate chunks (15-30 pages each)           │    │
│  │    ├─ Split PDF with 1-page overlap                 │    │
│  │    │                                                 │    │
│  │    └─ Parallel Processing ────────────┐             │    │
│  │         │                              │             │    │
│  │         ▼                              ▼             │    │
│  │    process_chunk(0)              process_chunk(1)   │    │
│  │    process_chunk(2)              process_chunk(3)   │    │
│  │         │                              │             │    │
│  │         └──────────┬───────────────────┘             │    │
│  │                    │                                 │    │
│  │                    ▼                                 │    │
│  │    merge_chunk_results()                            │    │
│  │      - Deduplicate overlaps                         │    │
│  │      - Handle failed chunks                         │    │
│  │      - Calculate metrics                            │    │
│  │                    │                                 │    │
│  └────────────────────┼─────────────────────────────────┘    │
│                       │                                      │
│                       │ 6. Save Results                      │
│                       ▼                                      │
│  ┌─────────────────────────────────────────────────────┐    │
│  │                  PostgreSQL                          │◄───┘
│  │                                                      │
│  │  Jobs Table:                                         │
│  │    - id, status, progress_percent                   │
│  │    - current_step, total_chunks                     │
│  │    - chunk_results, failed_chunks                   │
│  │    - processing_time_seconds                        │
│  │    - gemini_tokens_used                             │
│  └──────────────────────────────────────────────────────┘
│
│  ┌─────────────────────────────────────────────────────┐
│  │              Flower Monitoring                       │
│  │              (http://localhost:5555)                 │
│  │                                                      │
│  │  - Real-time task monitoring                        │
│  │  - Worker status and metrics                        │
│  │  - Task history and retries                         │
│  │  - Manual task control                              │
│  └──────────────────────────────────────────────────────┘
└──────────────────────────────────────────────────────────┘
```

## Processing Flow

```
User Uploads PDF (300 pages)
        │
        ▼
┌────────────────────┐
│ Job Confirmation   │  Reserve credits based on estimation
│ /jobs/confirm      │  → job_id: 123, estimated_credits: 100
└────────┬───────────┘
         │
         ▼
┌────────────────────┐
│ Start Async        │  Enqueue Celery task
│ /process-pdf-async │  → task_id, status: pending
└────────┬───────────┘
         │
         ▼
┌────────────────────┐
│ Celery Worker      │  Status: processing
│ process_pdf_async  │  Progress: 0%
└────────┬───────────┘
         │
         ├─ Analyzing PDF (5%)
         │  → Page count: 300
         │
         ├─ Calculate chunks (10%)
         │  → Strategy: large (15 pages/chunk)
         │  → Total chunks: 20
         │
         ├─ Splitting PDF (15%)
         │  → Creating temp files with overlap
         │
         ├─ Processing chunks (15-75%)
         │  ┌─────────────┐ ┌─────────────┐
         │  │ Chunk 0     │ │ Chunk 1     │ ...
         │  │ Pages 0-14  │ │ Pages 14-29 │
         │  │ Status: ✓   │ │ Status: ✓   │
         │  └─────────────┘ └─────────────┘
         │  → processed_chunks: 4/20
         │  → current_step: "Processing chunk 4/20"
         │
         ├─ Merging results (75-90%)
         │  → Deduplicating overlaps
         │  → Handling failed chunks: [7, 15]
         │
         └─ Finalizing (90-100%)
            → total_tokens: 150,000
            → processing_time: 180s
            → Status: completed
```

## Chunking Strategy

### Size-Based Strategy

```
PDF Pages: 25        → Strategy: small
├─ Chunk size: 30
├─ Chunks: 1
├─ Workers: 1
└─ Processing time: ~12s

PDF Pages: 100       → Strategy: medium
├─ Chunk size: 20
├─ Chunks: 5
├─ Workers: 3
└─ Processing time: ~25s

PDF Pages: 300       → Strategy: large
├─ Chunk size: 15
├─ Chunks: 20
├─ Workers: 5
└─ Processing time: ~90s
```

### Overlap & Deduplication

```
Chunk 0: Pages 0-14  ────────────┐
                                 │ Overlap: Page 14
Chunk 1: Pages 14-29 ────────────┘
                                 │ Overlap: Page 29
Chunk 2: Pages 29-44 ────────────┘

After Processing:
├─ Extract sentences from each chunk
├─ Use first 100 chars as deduplication key
├─ Skip duplicate sentences from overlaps
└─ Result: Merged, deduplicated sentence list
```

## State Diagram

```
          ┌─────────┐
          │ pending │
          └────┬────┘
               │ Worker picks up task
               ▼
        ┌─────────────┐
        │ processing  │◄──┐
        └──┬────┬──┬──┘   │ Retry on
           │    │  │      │ transient
           │    │  │      │ failure
   Success │    │  │ Timeout/Error
           │    │  └──────┘
           │    │
           │    │ User cancels
           │    ▼
           │  ┌───────────┐
           │  │ cancelled │
           │  └───────────┘
           │
           ▼
    ┌───────────┐
    │ completed │
    └───────────┘
           │
           ▼
    ┌───────────┐
    │ finalized │  Credits adjusted
    └───────────┘
```

## Error Handling

```
┌─────────────────────────────────────────────────┐
│              Error Scenarios                     │
├─────────────────────────────────────────────────┤
│                                                  │
│  1. Chunk Processing Failure                    │
│     ├─ Retry up to 3 times                      │
│     ├─ Mark chunk as failed                     │
│     ├─ Continue with other chunks               │
│     └─ Partial results returned                 │
│                                                  │
│  2. Worker Crash                                │
│     ├─ Task re-queued (acks_late=True)          │
│     ├─ Picked up by another worker              │
│     └─ Processing continues                     │
│                                                  │
│  3. Timeout (30 min)                            │
│     ├─ Soft timeout at 25 min (warning)         │
│     ├─ Hard timeout at 30 min (terminate)       │
│     ├─ Job marked as failed                     │
│     └─ Credits refunded                         │
│                                                  │
│  4. User Cancellation                           │
│     ├─ Set job.is_cancelled = True              │
│     ├─ Revoke Celery task                       │
│     ├─ Cleanup temp files                       │
│     └─ Refund credits                           │
│                                                  │
│  5. API Rate Limit (Gemini)                     │
│     ├─ Exponential backoff                      │
│     ├─ Retry with delay                         │
│     └─ Max 3 retries                            │
│                                                  │
└─────────────────────────────────────────────────┘
```

## Monitoring Dashboard (Flower)

```
┌────────────────────────────────────────────────────────────┐
│  Flower - Celery Monitoring (http://localhost:5555)        │
├────────────────────────────────────────────────────────────┤
│                                                             │
│  Workers:                                                   │
│  ┌──────────────────────────────────────────────────┐      │
│  │ celery@worker1    Status: ● Online  Load: 75%   │      │
│  │ celery@worker2    Status: ● Online  Load: 60%   │      │
│  │ celery@worker3    Status: ● Online  Load: 80%   │      │
│  │ celery@worker4    Status: ● Online  Load: 45%   │      │
│  └──────────────────────────────────────────────────┘      │
│                                                             │
│  Active Tasks: 12                                          │
│  ┌──────────────────────────────────────────────────┐      │
│  │ process_pdf_async[job_123]   Running  Progress: 45% │   │
│  │ process_chunk[chunk_5]       Running  Progress: 80% │   │
│  │ process_chunk[chunk_7]       Running  Progress: 60% │   │
│  └──────────────────────────────────────────────────┘      │
│                                                             │
│  Queue Depth: 3                                            │
│  Success Rate: 96.5% (last 24h)                            │
│  Average Processing Time: 92s                              │
│                                                             │
└────────────────────────────────────────────────────────────┘
```

## Deployment Architecture

```
Production Environment
┌─────────────────────────────────────────────────────┐
│                                                      │
│  ┌────────────┐      ┌────────────┐                │
│  │   NGINX    │◄────▶│ Let's      │                │
│  │ (Reverse   │      │ Encrypt    │                │
│  │  Proxy)    │      │ (SSL)      │                │
│  └──────┬─────┘      └────────────┘                │
│         │                                           │
│         ├─────────────┬──────────────┐              │
│         │             │              │              │
│         ▼             ▼              ▼              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐         │
│  │ Backend  │  │ Backend  │  │ Backend  │         │
│  │ (Flask)  │  │ (Flask)  │  │ (Flask)  │         │
│  │ :5000    │  │ :5001    │  │ :5002    │         │
│  └─────┬────┘  └─────┬────┘  └─────┬────┘         │
│        │             │              │              │
│        └─────────────┼──────────────┘              │
│                      │                             │
│         ┌────────────┼────────────┐                │
│         │            │            │                │
│         ▼            ▼            ▼                │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐          │
│  │ Celery   │ │ Celery   │ │ Celery   │          │
│  │ Worker 1 │ │ Worker 2 │ │ Worker 3 │          │
│  └─────┬────┘ └─────┬────┘ └─────┬────┘          │
│        │            │            │                │
│        └────────────┼────────────┘                │
│                     │                             │
│         ┌───────────┼───────────┐                 │
│         │           │           │                 │
│         ▼           ▼           ▼                 │
│  ┌─────────────────────────────────┐             │
│  │          Redis                   │             │
│  │   (Message Broker + Backend)    │             │
│  └──────────────┬──────────────────┘             │
│                 │                                 │
│                 ▼                                 │
│  ┌─────────────────────────────────┐             │
│  │       PostgreSQL                 │             │
│  │   (Jobs, Users, History)        │             │
│  └──────────────────────────────────┘             │
│                                                    │
│  ┌─────────────────────────────────┐             │
│  │          Flower                  │             │
│  │    (Monitoring - :5555)         │             │
│  │    Password Protected            │             │
│  └──────────────────────────────────┘             │
│                                                    │
└────────────────────────────────────────────────────┘
```

## Resource Requirements

```
┌────────────────────────────────────────────────────┐
│             Resource Allocation                     │
├────────────────────────────────────────────────────┤
│                                                     │
│  Backend (Flask):                                  │
│  ├─ CPU: 1-2 cores                                 │
│  ├─ Memory: 512MB - 1GB                            │
│  └─ Instances: 2-3 (load balanced)                 │
│                                                     │
│  Celery Workers:                                   │
│  ├─ CPU: 2-4 cores per worker                      │
│  ├─ Memory: 1-2GB per worker                       │
│  ├─ Workers: 4-8 (based on load)                   │
│  └─ Concurrency: 4 tasks per worker                │
│                                                     │
│  Redis:                                            │
│  ├─ CPU: 1 core                                    │
│  ├─ Memory: 256MB-512MB                            │
│  └─ Persistence: Enabled (AOF)                     │
│                                                     │
│  PostgreSQL:                                       │
│  ├─ CPU: 2 cores                                   │
│  ├─ Memory: 2-4GB                                  │
│  └─ Storage: 20GB+                                 │
│                                                     │
│  Total (Medium Load):                              │
│  ├─ CPU: 12-16 cores                               │
│  ├─ Memory: 8-16GB                                 │
│  └─ Storage: 50GB+                                 │
│                                                     │
└────────────────────────────────────────────────────┘
```

---

**For detailed implementation, see**:
- [ASYNC_PDF_PROCESSING.md](./ASYNC_PDF_PROCESSING.md)
- [ASYNC_IMPLEMENTATION_SUMMARY.md](./ASYNC_IMPLEMENTATION_SUMMARY.md)

# Async Processing Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           ASYNC PDF PROCESSING FLOW                          │
└─────────────────────────────────────────────────────────────────────────────┘

┌──────────────┐
│   Frontend   │
│  (Next.js)   │
└──────┬───────┘
       │
       │ 1. Upload PDF (>50 pages)
       ▼
┌──────────────────────────────────────────────────────────┐
│                    Flask API Server                      │
│  ┌────────────────────────────────────────────────────┐  │
│  │  POST /process-pdf                                 │  │
│  │  • Validate PDF                                    │  │
│  │  • Get page count (e.g., 150 pages)                │  │
│  │  • Check if > 50 pages → Yes, use async           │  │
│  │  • Create Job record (status='pending')           │  │
│  │  • Calculate chunks: 150/25 = 6 chunks            │  │
│  └────────────┬───────────────────────────────────────┘  │
│               │                                           │
│               │ 2. Enqueue task                          │
│               ▼                                           │
│  ┌────────────────────────────────────────────────────┐  │
│  │  Celery Task Queue                                 │  │
│  │  • task_id: abc123                                 │  │
│  │  • job_id: 123                                     │  │
│  │  • status: 'queued'                                │  │
│  └────────────────────────────────────────────────────┘  │
└──────────────┬───────────────────────────────────────────┘
               │
               │ 3. Return 202 Accepted
               │    { job_id: 123, status: 'queued' }
               ▼
┌──────────────────────────────────────────────────────────┐
│                    Frontend                              │
│  ┌────────────────────────────────────────────────────┐  │
│  │  JobProgressDialog                                 │  │
│  │  • Shows job_id: 123                               │  │
│  │  • Starts polling every 2 seconds                  │  │
│  └────────────────────────────────────────────────────┘  │
└──────────────┬───────────────────────────────────────────┘
               │
               │ 4. Poll: GET /jobs/123
               │    (every 2 seconds)
               ▼
┌──────────────────────────────────────────────────────────────┐
│                      Redis Queue                             │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐             │
│  │  Task 1    │  │  Task 2    │  │  Task 3    │  ...        │
│  │  job_id:123│  │  job_id:124│  │  job_id:125│             │
│  └────────────┘  └────────────┘  └────────────┘             │
└──────────────┬───────────────────────────────────────────────┘
               │
               │ 5. Worker picks up task
               ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                          Celery Worker                                  │
│                                                                         │
│  ┌───────────────────────────────────────────────────────────────┐     │
│  │  process_pdf_async(job_id=123, pdf_path='/tmp/xyz.pdf')      │     │
│  │                                                               │     │
│  │  1. Get Job from DB → status='queued'                        │     │
│  │  2. Update status → 'processing'                             │     │
│  │  3. Get page_count → 150 pages                               │     │
│  │  4. Check if chunking needed → Yes (150 > 50)                │     │
│  │  5. Call process_pdf_chunked()                               │     │
│  └───────────────────────────────────────────────────────────────┘     │
│                                                                         │
│  ┌───────────────────────────────────────────────────────────────┐     │
│  │  process_pdf_chunked()                                        │     │
│  │                                                               │     │
│  │  total_chunks = ceil(150 / 25) = 6 chunks                    │     │
│  │  Update job: { total_chunks: 6, chunk_size: 25 }             │     │
│  │                                                               │     │
│  │  FOR each chunk (1 to 6):                                    │     │
│  │    ┌─────────────────────────────────────────────────┐       │     │
│  │    │ Chunk 1: Pages 1-25                              │       │     │
│  │    │ • Split PDF → /tmp/chunk1.pdf                    │       │     │
│  │    │ • Process with Gemini API                        │       │     │
│  │    │ • Get sentences → 45 sentences                   │       │     │
│  │    │ • Update: completed_chunks=1, progress=16.7%     │       │     │
│  │    └─────────────────────────────────────────────────┘       │     │
│  │                                                               │     │
│  │    ┌─────────────────────────────────────────────────┐       │     │
│  │    │ Chunk 2: Pages 26-50                             │       │     │
│  │    │ • Split PDF → /tmp/chunk2.pdf                    │       │     │
│  │    │ • Process with Gemini API                        │       │     │
│  │    │ • Get sentences → 50 sentences                   │       │     │
│  │    │ • Update: completed_chunks=2, progress=33.3%     │       │     │
│  │    └─────────────────────────────────────────────────┘       │     │
│  │                                                               │     │
│  │    ... (continue for chunks 3-6)                             │     │
│  │                                                               │     │
│  │  Merge all sentences → 1,250 total sentences                 │     │
│  │  Create history entry                                        │     │
│  │  Complete job: status='completed', progress=100%             │     │
│  └───────────────────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────────────────┘
               │
               │ 6. Job completed in DB
               ▼
┌──────────────────────────────────────────────────────────┐
│                PostgreSQL Database                       │
│  ┌────────────────────────────────────────────────────┐  │
│  │  jobs table:                                       │  │
│  │  id: 123                                           │  │
│  │  status: 'completed'                               │  │
│  │  page_count: 150                                   │  │
│  │  total_chunks: 6                                   │  │
│  │  completed_chunks: 6                               │  │
│  │  progress_percent: 100.0                           │  │
│  │  ...                                               │  │
│  └────────────────────────────────────────────────────┘  │
│  ┌────────────────────────────────────────────────────┐  │
│  │  history table:                                    │  │
│  │  job_id: 123                                       │  │
│  │  processed_sentences_count: 1250                   │  │
│  │  ...                                               │  │
│  └────────────────────────────────────────────────────┘  │
└──────────────┬───────────────────────────────────────────┘
               │
               │ 7. Next poll gets completed status
               ▼
┌──────────────────────────────────────────────────────────┐
│                    Frontend                              │
│  ┌────────────────────────────────────────────────────┐  │
│  │  JobProgressDialog                                 │  │
│  │  • Status: 'completed'                             │  │
│  │  • Progress: 100%                                  │  │
│  │  • Sentences: 1,250                                │  │
│  │  • Shows success message                           │  │
│  │  • Calls onComplete callback                       │  │
│  └────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────┘


═══════════════════════════════════════════════════════════════════════════

                        COMPONENT INTERACTIONS

┌─────────────┐      ┌─────────────┐      ┌─────────────┐
│   Frontend  │◄────►│  Flask API  │◄────►│  PostgreSQL │
│  (Next.js)  │      │   Server    │      │  Database   │
└─────────────┘      └─────┬───────┘      └─────────────┘
                           │
                           ▼
                     ┌─────────────┐
                     │    Redis    │
                     │   (Queue)   │
                     └─────┬───────┘
                           │
                           ▼
                     ┌─────────────┐
                     │   Celery    │
                     │   Worker    │
                     └─────┬───────┘
                           │
                           ▼
                     ┌─────────────┐
                     │   Gemini    │
                     │     API     │
                     └─────────────┘


═══════════════════════════════════════════════════════════════════════════

                          STATUS TRANSITIONS

    pending → queued → processing → completed
                ↓           ↓            ↓
                └─────→ failed ←─────────┘
                        or
                     cancelled


═══════════════════════════════════════════════════════════════════════════

                        PROGRESS CALCULATION

    progress_percent = (completed_chunks / total_chunks) × 100

    Example for 6 chunks:
    • Chunk 1 done: 1/6 = 16.7%
    • Chunk 2 done: 2/6 = 33.3%
    • Chunk 3 done: 3/6 = 50.0%
    • Chunk 4 done: 4/6 = 66.7%
    • Chunk 5 done: 5/6 = 83.3%
    • Chunk 6 done: 6/6 = 100.0% ✓


═══════════════════════════════════════════════════════════════════════════

                            POLLING FLOW

    Frontend                        Backend
       │                               │
       ├─── GET /jobs/123 ────────────►│
       │                               │ Check DB
       │◄──── { progress: 16.7% } ─────┤
       │                               │
       │ Wait 2 seconds                │
       │                               │
       ├─── GET /jobs/123 ────────────►│
       │                               │ Check DB
       │◄──── { progress: 33.3% } ─────┤
       │                               │
       │ Wait 2 seconds                │
       │                               │
       ├─── GET /jobs/123 ────────────►│
       │                               │ Check DB
       │◄──── { progress: 50.0% } ─────┤
       │                               │
       ... continues until status='completed' or 'failed'
       │                               │
       ├─── GET /jobs/123 ────────────►│
       │                               │ Check DB
       │◄── { status: 'completed' } ───┤
       │                               │
       └─ Stop polling ✓               │


```

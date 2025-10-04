# WebSocket Implementation - Visual Architecture

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Client (Browser)                             │
│  ┌────────────────────────────────────────────────────────────┐    │
│  │  Next.js Application (http://localhost:3000)               │    │
│  │                                                              │    │
│  │  ┌────────────────────┐    ┌──────────────────────────┐   │    │
│  │  │  page.tsx          │    │  JobProgressDialog.tsx   │   │    │
│  │  │  ─────────         │    │  ─────────────────────   │   │    │
│  │  │  - Upload PDF      │    │  - Show progress         │   │    │
│  │  │  - Show progress   │    │  - Real-time updates     │   │    │
│  │  │  - WebSocket conn  │    │  - Cancel job            │   │    │
│  │  └─────────┬──────────┘    └───────────┬──────────────┘   │    │
│  │            │                            │                   │    │
│  │            └────────────┬───────────────┘                   │    │
│  │                         │                                   │    │
│  │              ┌──────────▼──────────────┐                   │    │
│  │              │  useJobWebSocket.ts     │                   │    │
│  │              │  ──────────────────     │                   │    │
│  │              │  - WebSocket manager    │                   │    │
│  │              │  - Auto-reconnect       │                   │    │
│  │              │  - Event handlers       │                   │    │
│  │              │  - Room subscription    │                   │    │
│  │              └──────────┬──────────────┘                   │    │
│  └─────────────────────────┼─────────────────────────────────┘    │
└────────────────────────────┼──────────────────────────────────────┘
                             │
                    WebSocket Connection
                    (socket.io-client)
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    Backend Server (Flask)                            │
│  ┌────────────────────────────────────────────────────────────┐    │
│  │  Flask-SocketIO (eventlet worker)                          │    │
│  │                                                              │    │
│  │  ┌─────────────────────────────────────────────────────┐   │    │
│  │  │  socket_events.py                                   │   │    │
│  │  │  ────────────────                                   │   │    │
│  │  │  ┌─────────────────────────────────────────────┐   │   │    │
│  │  │  │  @socketio.on('connect')                    │   │   │    │
│  │  │  │  - Verify JWT token                         │   │   │    │
│  │  │  │  - Authenticate user                        │   │   │    │
│  │  │  └─────────────────────────────────────────────┘   │   │    │
│  │  │  ┌─────────────────────────────────────────────┐   │   │    │
│  │  │  │  @socketio.on('join_job')                   │   │   │    │
│  │  │  │  - Validate job ownership                   │   │   │    │
│  │  │  │  - Join room: job_{job_id}                  │   │   │    │
│  │  │  │  - Send initial job state                   │   │   │    │
│  │  │  └─────────────────────────────────────────────┘   │   │    │
│  │  │  ┌─────────────────────────────────────────────┐   │   │    │
│  │  │  │  emit_job_progress(job_id)                  │   │   │    │
│  │  │  │  - Get job from DB                          │   │   │    │
│  │  │  │  - Emit to room: job_{job_id}               │   │   │    │
│  │  │  │  - Event: 'job_progress'                    │   │   │    │
│  │  │  └─────────────────────────────────────────────┘   │   │    │
│  │  └─────────────────────────────────────────────────────┘   │    │
│  │                                                              │    │
│  │  ┌─────────────────────────────────────────────────────┐   │    │
│  │  │  REST API Routes                                    │   │    │
│  │  │  ───────────────                                    │   │    │
│  │  │  - POST /api/v1/jobs/confirm  (Create job)         │   │    │
│  │  │  - POST /api/v1/process-pdf   (Upload & dispatch)  │   │    │
│  │  │  - GET  /api/v1/jobs/{id}     (Fallback - unused)  │   │    │
│  │  └─────────────────────────────────────────────────────┘   │    │
│  └─────────────────────────┬────────────────────────────────────┘    │
└────────────────────────────┼──────────────────────────────────────┘
                             │
                    Celery Task Dispatch
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    Celery Worker (Background)                        │
│  ┌────────────────────────────────────────────────────────────┐    │
│  │  tasks.py - process_pdf_async()                            │    │
│  │                                                              │    │
│  │  Progress Checkpoints:                                      │    │
│  │  ┌────────────────────────────────────────────────────┐    │    │
│  │  │  5%   → emit_progress(job_id)  "Analyzing PDF"     │    │    │
│  │  │  10%  → emit_progress(job_id)  "Splitting chunks"  │    │    │
│  │  │  15%  → emit_progress(job_id)  "Processing chunks" │    │    │
│  │  │  20%  → emit_progress(job_id)  "Chunk 1/5"         │    │    │
│  │  │  35%  → emit_progress(job_id)  "Chunk 2/5"         │    │    │
│  │  │  50%  → emit_progress(job_id)  "Chunk 3/5"         │    │    │
│  │  │  65%  → emit_progress(job_id)  "Chunk 4/5"         │    │    │
│  │  │  75%  → emit_progress(job_id)  "Chunk 5/5"         │    │    │
│  │  │  75%  → emit_progress(job_id)  "Merging results"   │    │    │
│  │  │  100% → emit_progress(job_id)  "Completed"         │    │    │
│  │  └────────────────────────────────────────────────────┘    │    │
│  │                                                              │    │
│  │  Each emit_progress() calls:                                │    │
│  │  1. Update Job in PostgreSQL                                │    │
│  │  2. socketio.emit('job_progress', job.to_dict(),            │    │
│  │                   room=f'job_{job_id}')                     │    │
│  └────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────┘
                             ▲
                             │
                    Message Queue (Redis)
                             │
                             │
    (Multi-instance message sync for production scaling)
```

## Data Flow Sequence

```
User Action                    Backend Event                   Frontend Update
───────────                    ─────────────                   ───────────────

1. Upload PDF
   └──────────────────────────> Create Job (ID: 123)
                                Dispatch Celery Task
                                                                
2. WebSocket Connect
   └──────────────────────────> Validate JWT
                                Accept connection
                                                                Connected ✓

3. Join Job Room
   └──────────────────────────> Verify ownership
                                Add to room: job_123
                                ───────────────────────────────> Initial state

4. [Celery] Start Processing
                                Update: 5% "Analyzing"
                                emit_job_progress(123)
                                ───────────────────────────────> Progress: 5%
                                                                "Analyzing PDF"

5. [Celery] Calculate Chunks
                                Update: 10% "Splitting"
                                emit_job_progress(123)
                                ───────────────────────────────> Progress: 10%
                                                                "Splitting chunks"

6. [Celery] Process Chunk 1
                                Update: 20% "Chunk 1/5"
                                emit_job_progress(123)
                                ───────────────────────────────> Progress: 20%
                                                                "Chunk 1/5"

7. [Celery] Process Chunk 2
                                Update: 35% "Chunk 2/5"
                                emit_job_progress(123)
                                ───────────────────────────────> Progress: 35%
                                                                "Chunk 2/5"

   ... (chunks 3, 4, 5 similar) ...

8. [Celery] Merge Results
                                Update: 75% "Merging"
                                emit_job_progress(123)
                                ───────────────────────────────> Progress: 75%
                                                                "Merging results"

9. [Celery] Complete
                                Update: 100% "Completed"
                                emit_job_progress(123)
                                ───────────────────────────────> Progress: 100%
                                                                "Completed ✓"
                                                                Show results
                                                                Leave room

Total time: ~60 seconds
WebSocket events: 10 events
HTTP polling requests: 0 ✨
Update latency: <100ms per event
```

## Component Interaction

```
┌──────────────────┐
│   User Browser   │
│                  │
│  ┌────────────┐  │
│  │  UI State  │◄─┼──── Real-time Updates (<100ms)
│  └────────────┘  │
│        │         │
│  ┌─────▼──────┐  │
│  │ WebSocket  │  │
│  │   Hook     │  │
│  └─────┬──────┘  │
└────────┼─────────┘
         │ socket.io
         │ protocol
         ▼
┌──────────────────┐
│  Flask Server    │
│                  │
│  ┌────────────┐  │
│  │ SocketIO   │  │
│  │ Extension  │  │
│  └─────┬──────┘  │
│        │         │
│  ┌─────▼──────┐  │
│  │  Eventlet  │  │
│  │  Worker    │  │
│  └────────────┘  │
└──────────────────┘
         ▲
         │ emit_progress()
         │
┌──────────────────┐
│  Celery Worker   │
│                  │
│  ┌────────────┐  │
│  │   Task     │  │
│  │ Processing │  │
│  └─────┬──────┘  │
│        │         │
│  ┌─────▼──────┐  │
│  │ PostgreSQL │  │
│  │   (Jobs)   │  │
│  └────────────┘  │
└──────────────────┘
```

## Security Model

```
┌─────────────────────────────────────────────────────────┐
│  WebSocket Connection Lifecycle                         │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  1. Client initiates connection                         │
│     ├─ Socket.IO client sends JWT in auth object       │
│     └─ Token format: { token: "eyJ..." }               │
│                                                          │
│  2. Server validates token                              │
│     ├─ decode_token(token)                             │
│     ├─ Extract user_id from 'sub' claim                │
│     ├─ Verify signature & expiration                   │
│     └─ Accept or reject connection                     │
│                                                          │
│  3. Client joins job room                               │
│     ├─ Emit 'join_job' with job_id and token          │
│     ├─ Server verifies job ownership:                  │
│     │   job.user_id == decoded_user_id                │
│     └─ Add to room: job_{job_id}                       │
│                                                          │
│  4. Room isolation ensures privacy                      │
│     ├─ Only subscribed clients in room receive events  │
│     ├─ User A cannot see User B's job updates         │
│     └─ Authorization checked on every join_job         │
│                                                          │
│  5. Progress updates broadcast to room                  │
│     ├─ socketio.emit('job_progress', data,            │
│     │                room=f'job_{job_id}')             │
│     └─ Only clients in that room receive event        │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

## Performance Comparison

### Before (Polling)
```
Time:   0s    2s    4s    6s    8s   10s   12s   14s   16s   18s   20s
        │     │     │     │     │     │     │     │     │     │     │
HTTP:   GET───GET───GET───GET───GET───GET───GET───GET───GET───GET───GET
        │     │     │     │     │     │     │     │     │     │     │
Data:   5%    5%    5%    10%   10%   15%   15%   20%   20%   20%   35%
        └─┬─┘ └─┬─┘ └─┬─┘ └─┬─┘ └─┬─┘ └─┬─┘ └─┬─┘ └─┬─┘ └─┬─┘ └─┬─┘ └─┬─┘
         2s    2s    2s    2s    2s    2s    2s    2s    2s    2s    2s
         
Latency: 0-2 seconds (average 1s)
Requests: 10 in 20 seconds
Efficiency: Wasted requests when no change
```

### After (WebSocket)
```
Time:   0s    2s    4s    6s    8s   10s   12s   14s   16s   18s   20s
        │           │     │           │           │           │     │
WS:    [──────────────────────────────────────────────────────────────]
        │           │     │           │           │           │     │
Event:  5%─────────10%───15%─────────20%─────────35%─────────50%───65%
        └───<100ms──┘     └───<100ms──┘           └───<100ms──┘
        
Latency: <100ms (instant)
Events: 7 in 20 seconds (only when changed)
Efficiency: Perfect (no wasted bandwidth)
```

## Scaling Strategy

```
                         Load Balancer
                              │
                 ┌────────────┼────────────┐
                 │            │            │
            Instance 1    Instance 2   Instance 3
                 │            │            │
                 └────────────┼────────────┘
                              │
                         Redis (Message Queue)
                              │
                     Message Sync for WebSocket
                     
Each instance:
- Runs eventlet worker (-w 1)
- Connects to shared Redis
- Syncs WebSocket events across instances
- Client can connect to any instance
```

---

**Architecture Version**: 1.0  
**Last Updated**: January 10, 2025  
**Status**: Production Ready ✅

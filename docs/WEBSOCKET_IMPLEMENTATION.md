# WebSocket Real-Time Job Progress Updates

## Overview

The FrenchNovelTool now uses WebSocket-based real-time updates for job progress instead of polling. This provides instant feedback to users as their PDFs are processed, reduces server load, and improves overall user experience.

## Architecture

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

## Backend Implementation

### Dependencies

- **Flask-SocketIO** (5.3.6): WebSocket support for Flask
- **eventlet** (0.35.2): Async I/O for WebSocket connections
- **python-socketio** (5.11.2): Core Socket.IO library

### Key Files

#### `backend/app/__init__.py`
- Initializes SocketIO extension
- Configures CORS for WebSocket connections
- Uses eventlet async mode
- Message queue support for multi-instance deployments

#### `backend/app/socket_events.py`
- **Event Handlers:**
  - `connect`: JWT authentication for WebSocket connections
  - `disconnect`: Cleanup on client disconnect
  - `join_job`: Subscribe client to job-specific room
  - `leave_job`: Unsubscribe from job room
- **Helper Function:**
  - `emit_job_progress(job_id)`: Broadcast progress to all subscribed clients

#### `backend/app/tasks.py`
- Emits progress at key checkpoints:
  - 5% - Job started, analyzing PDF
  - 10% - Chunks calculated
  - 15% - Processing chunks
  - Per-chunk progress (15% → 75%)
  - 75% - Merging results
  - 100% - Completed or failed

### Authentication

WebSocket connections use JWT tokens for authentication:

```python
# Client sends token during connection
socket = io(url, {
  auth: { token: accessToken }
})

# Server validates token
decoded = decode_token(token)
user_id = int(decoded['sub'])
```

### Room-Based Updates

Each job has a dedicated room for broadcasting updates:

```python
room = f'job_{job_id}'
socketio.emit('job_progress', job.to_dict(), room=room)
```

Only clients who have joined the room receive updates, ensuring privacy and efficiency.

### Deployment Configuration

#### Development (`run.py`)
```python
socketio.run(app, debug=True, port=5000, allow_unsafe_werkzeug=True)
```

#### Production (`Dockerfile.web`)
```dockerfile
CMD ["gunicorn", "--worker-class", "eventlet", "-w", "1", ...]
```

**Note:** Use `-w 1` with eventlet (async I/O in single process). For horizontal scaling, run multiple instances behind a load balancer.

## Frontend Implementation

### Dependencies

- **socket.io-client** (4.7.2): WebSocket client library

### Key Files

#### `frontend/src/lib/useJobWebSocket.ts`

Custom React hook for WebSocket job updates:

```typescript
const { job, connected, error } = useJobWebSocket({
  jobId: 123,
  enabled: true,
  onProgress: (job) => {
    console.log(`Progress: ${job.progress_percent}%`);
  },
  onComplete: (job) => {
    console.log('Job completed!');
  },
  onError: (job) => {
    console.error('Job failed:', job.error_message);
  },
});
```

**Features:**
- Automatic reconnection (5 attempts with exponential backoff)
- JWT authentication
- Room-based subscriptions
- Terminal state detection (completed, failed, cancelled)

#### `frontend/src/app/page.tsx`

Replaced polling with WebSocket:

```typescript
// Before: Polling every 2 seconds
const jobStatus = useJobStatus(pollingJobId);

// After: Real-time WebSocket updates
const { job, connected } = useJobWebSocket({
  jobId: wsJobId,
  onComplete: handleComplete,
  onError: handleError,
});
```

**Connection Status Indicator:**
- Green pulsing dot: Connected and receiving real-time updates
- Yellow dot: Connecting/reconnecting

## Event Flow

### 1. Job Creation
```
Client → POST /api/v1/jobs/confirm → Backend creates Job
Client → POST /api/v1/process-pdf → Backend dispatches Celery task
Client → WebSocket: join_job(job_id) → Subscribe to updates
```

### 2. Progress Updates
```
Celery Worker → Updates Job in DB
Celery Worker → emit_job_progress(job_id)
SocketIO → job_progress event → Client (job room)
Client → Updates UI in real-time
```

### 3. Completion
```
Celery Worker → Job status = 'completed'
Celery Worker → emit_job_progress(job_id)
Client → onComplete callback → Extract sentences, show success
Client → WebSocket: leave_job(job_id)
```

## Error Handling

### Backend
- Failed token validation → Disconnect client
- Missing job_id → Emit error event
- Unauthorized job access → Emit error event
- Emit failures → Logged but don't crash worker

### Frontend
- Connection errors → Show "Connecting..." status
- Reconnection failures → Fallback to polling (future enhancement)
- Network timeouts → Automatic reconnect with backoff

## Performance Optimizations

### Polling Reduction
- **Before:** 1 request every 2 seconds × job duration
- **After:** 0 polling requests (100% reduction)
- **Example:** 60-second job = 30 requests → 0 requests

### Server Load
- No more `/api/v1/jobs/{id}` polling endpoints hit
- WebSocket maintains single persistent connection
- Progress emitted only when state changes (not on interval)

### Scalability
- Message queue sync for multi-instance deployments
- Room-based isolation prevents cross-job interference
- Eventlet async I/O handles many concurrent connections

## Testing

### Manual Testing
1. Start backend: `cd backend && python run.py`
2. Start frontend: `cd frontend && npm run dev`
3. Upload a PDF and observe:
   - WebSocket connection indicator (green pulse)
   - Real-time progress updates (no delay)
   - Network tab shows no polling requests

### Automated Tests
```bash
cd backend
pytest tests/test_websocket.py -v
```

Tests verify:
- SocketIO initialization
- JWT authentication
- Event handlers
- Progress emission

## Troubleshooting

### WebSocket not connecting
**Symptoms:** Connection status shows "Connecting..." indefinitely

**Fixes:**
1. Check CORS configuration in `backend/config.py`
2. Verify JWT token is valid
3. Ensure eventlet worker is running (not sync worker)
4. Check browser console for errors

### Progress updates not showing
**Symptoms:** Connected but no progress updates

**Fixes:**
1. Verify client joined job room (`join_job` event)
2. Check Celery worker logs for `emit_progress` calls
3. Ensure job_id matches between frontend and backend
4. Verify user owns the job (authorization check)

### Production deployment issues
**Symptoms:** Works in dev but not in production

**Fixes:**
1. Ensure Gunicorn uses `--worker-class eventlet`
2. Set `CELERY_BROKER_URL` for message queue sync
3. Configure proper CORS origins (not just `*`)
4. Check firewall allows WebSocket connections

## Migration from Polling

### Removed Files
- `frontend/src/lib/useJobPolling.ts` (can be kept as fallback)

### Updated Files
- `frontend/src/app/page.tsx`: Replaced `useJobStatus` with `useJobWebSocket`
- Backend emits progress at all checkpoints in `tasks.py`

### Backwards Compatibility
The REST API endpoint `GET /api/v1/jobs/{id}` still exists and works. Clients can fall back to polling if WebSocket fails.

## Future Enhancements

1. **Automatic fallback:** Detect WebSocket failure and revert to polling
2. **Reconnection UI:** Show reconnection attempts to user
3. **Multi-job support:** Track multiple jobs simultaneously
4. **Job cancellation:** Real-time cancel via WebSocket
5. **Heartbeat:** Detect stale connections and cleanup

## References

- [Flask-SocketIO Documentation](https://flask-socketio.readthedocs.io/)
- [Socket.IO Client Documentation](https://socket.io/docs/v4/client-api/)
- [Eventlet Documentation](https://eventlet.readthedocs.io/)
- [WebSocket RFC 6455](https://tools.ietf.org/html/rfc6455)

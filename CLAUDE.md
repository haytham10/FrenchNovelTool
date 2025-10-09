# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**French Novel Tool** is an AI-powered full-stack application for processing French novel PDFs using Google Gemini AI to normalize sentence length and export results to Google Sheets. The system includes a vocabulary coverage analysis feature for optimized language learning.

**Tech Stack:**
- **Backend:** Flask 3.0 + SQLAlchemy + PostgreSQL + Celery (async task processing) + Redis + Flask-SocketIO
- **Frontend:** Next.js 15 (App Router) + React 19 + TypeScript + Material-UI v7 + TanStack Query + Zustand
- **AI/NLP:** Google Gemini AI, spaCy (French lemmatization)
- **Deployment:** Railway (backend + Celery + Flower) + Vercel (frontend)

## Architecture

### Backend Service-Oriented Architecture

The backend follows an **Application Factory Pattern** with service layer encapsulation:

1. **App Factory:** `backend/app/__init__.py` - Creates Flask app via `create_app()`, initializes extensions (db, jwt, limiter, socketio, celery)
2. **Service Layer:** `backend/app/services/` - All business logic lives here:
   - `auth_service.py` - Google OAuth and JWT authentication
   - `pdf_service.py` - PDF text extraction
   - `chunking_service.py` - Intelligent PDF splitting (30-50 page chunks with overlap)
   - `gemini_service.py` - AI sentence normalization with fallback cascade
   - `google_sheets_service.py` - Google Sheets/Drive integration
   - `credit_service.py` - Usage tracking and credit accounting
   - `job_service.py` - Job orchestration and cost estimation
   - `coverage_service.py` - Vocabulary coverage analysis (filter/coverage modes)
   - `wordlist_service.py` - Word list management
   - `history_service.py` - Processing history tracking
   - `user_settings_service.py` - User preferences

3. **Blueprint-Based Routing:** Routes organized into blueprints at `/api/v1`:
   - `routes.py` (main_bp) - PDF processing, jobs, history, settings
   - `auth_routes.py` (auth_bp) - Authentication endpoints
   - `credit_routes.py` (credit_bp) - Credit management
   - `coverage_routes.py` (coverage_bp) - Vocabulary coverage

4. **Celery Task Layer:** `backend/app/tasks.py` - Asynchronous processing:
   - `process_pdf_async` - Main orchestrator for PDF jobs
   - `process_chunk` - Parallel chunk processing with DB-backed state
   - `finalize_job_results` - Chord callback with automatic retry orchestration
   - `chunk_watchdog` - Monitors stuck chunks and triggers retries
   - `coverage_build_async` - Async vocabulary coverage analysis
   - `batch_coverage_build_async` - Multi-source batch analysis

5. **Database Models:** `backend/app/models.py`:
   - `User` - User accounts with Google OAuth tokens
   - `Job` - PDF processing jobs with status tracking
   - `JobChunk` - Individual chunk state with retry logic
   - `History` - Completed processing results
   - `CreditLedger` - Transaction history
   - `CoverageRun` - Coverage analysis runs
   - `CoverageAssignment` - Word-to-sentence mappings
   - `WordList` - Custom vocabulary lists

### Frontend Architecture

1. **App Router:** `frontend/src/app/` - Next.js 15 SSR pages with Material-UI
2. **API Client:** `frontend/src/lib/api.ts` - Centralized axios client with JWT token auto-refresh interceptor
3. **State Management:**
   - **Zustand Stores:** `frontend/src/stores/` - Global client state
     - `useProcessingStore.ts` - PDF processing state
     - `useHistoryStore.ts` - History records
     - `useSettingsStore.ts` - User settings
     - `useCreditStore.ts` - Credit balance
   - **TanStack Query:** `frontend/src/lib/queries.ts` - Server state caching
4. **Real-Time Updates:**
   - `frontend/src/lib/useJobWebSocket.ts` - Job progress via Socket.IO
   - `frontend/src/lib/useCoverageWebSocket.ts` - Coverage progress via Socket.IO

### Data Flow: PDF Processing

1. **Upload:** User uploads PDF → `POST /api/v1/process-pdf`
2. **Estimation:** Backend estimates cost → `JobService.estimate_job()`
3. **Chunking:** PDF split into 30-50 page chunks → `ChunkingService.split_pdf_and_persist()`
4. **Parallel Processing:** Celery chord dispatches chunks → `process_chunk` tasks run in parallel
5. **AI Normalization:** Each chunk processed by Gemini → `GeminiService.normalize_text()` with fallback cascade
6. **Real-Time Progress:** Workers update `Job.progress_percent` → Socket.IO emits updates → Frontend progress bar
7. **Finalization:** `finalize_job_results` chord callback merges results → Creates `History` entry
8. **Export:** User exports to Google Sheets → `GoogleSheetsService.create_sheet()`

### Critical Infrastructure Optimizations (Railway 8GB/8vCPU)

**Celery Workers:**
- 8 concurrent workers with 2x prefetch multiplier
- 900MB memory cap per worker
- 60-minute task timeout
- Adaptive chunking: 50 pages (small PDFs), 40 pages (medium), 30 pages (large) with 2-page overlap

**Database Connection Pooling:**
- 20 base connections + 10 overflow
- 30-minute connection recycling
- 60s statement timeout for large queries
- Pre-ping enabled for cloud reliability

**Task Reliability:**
- DB-backed chunk state tracking (`JobChunk` model)
- Automatic retry orchestration (up to 4 retries with exponential backoff)
- Chunk watchdog (10-minute timeout detection)
- Finalization watchdog (safety net for chord failures)
- `safe_db_commit()` helper for transient error retry

## Development Commands

### Backend Development

```bash
# Install dependencies
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
pip install -r requirements-dev.txt  # For development

# Database migrations (ALWAYS use Flask-Migrate, NEVER db.create_all())
flask db migrate -m "Description of migration"
flask db upgrade

# Run development server
flask run

# Run tests with coverage
pytest
pytest --cov=app --cov-report=html

# Linting and formatting
black .
flake8
```

### Frontend Development

```bash
cd frontend
npm install
npm run dev      # Development server
npm run build    # Production build
npm run lint     # ESLint
```

### Docker Development (Local Only)

```bash
# Quick start with hot reload (for local development only)
./dev-setup.sh      # Unix/macOS
dev-setup.bat       # Windows

# Or manually:
docker-compose -f docker-compose.dev.yml up --build

# Database migrations in container:
docker-compose -f docker-compose.dev.yml exec backend flask db migrate -m "Description"
docker-compose -f docker-compose.dev.yml exec backend flask db upgrade
```

**Note:** Docker Compose is for local development only. Production uses separate Railway services.

### Running a Single Test

```bash
cd backend
pytest tests/test_specific_file.py::test_function_name -v
```

## Critical Development Conventions

### Backend

1. **Database Migrations:** `db.create_all()` is explicitly disabled in `backend/app/__init__.py`. ALWAYS use Flask-Migrate for schema changes.

2. **Service Instantiation:** Most services are instantiated per-request. Notable exceptions:
   - `HistoryService` - Module-level instance
   - `UserSettingsService` - Module-level instance
   - `GeminiService` - Created per-request with user settings

3. **JWT Identity:** `get_jwt_identity()` returns a string. Always convert to int:
   ```python
   user_id = int(get_jwt_identity())
   ```

4. **Rate Limiting Order:** Always put `@jwt_required()` before `@limiter.limit()`:
   ```python
   @jwt_required()
   @limiter.limit("10 per minute")
   def protected_endpoint():
       pass
   ```

5. **File Validation:** Use `utils/validators.validate_pdf_file()` which checks magic bytes, not just filename extensions.

6. **Celery Task Patterns:**
   - Use `safe_db_commit()` for all DB writes (handles transient errors)
   - Chunks delivered as base64 in `chunk_info['file_b64']` (avoids shared filesystem)
   - DB-backed state tracking via `JobChunk` model (enables retry logic)
   - All tasks support idempotency (can be safely retried)

7. **Error Handling in Tasks:**
   - Transient errors (timeout, rate limit) trigger automatic retry
   - Non-transient errors fail chunk immediately
   - Watchdog tasks detect stuck chunks and force retry/fail

### Frontend

1. **Component Structure:** Use functional components with hooks (no class components)

2. **API Calls:** Always use the centralized `api.ts` client (handles token refresh automatically)

3. **Type Safety:** Shared types in `frontend/src/lib/types.ts`

4. **State Management Pattern:**
   - **Zustand:** UI state, temporary form data
   - **TanStack Query:** Server data with caching/invalidation

5. **Real-Time Updates:** Use WebSocket hooks for job/coverage progress

## Testing Guidelines

### Backend Tests (`backend/tests/`)

- Use `pytest` fixtures for database setup
- Mock external APIs (Gemini, Google Sheets)
- Test service layer directly (unit tests)
- Test routes with Flask test client (integration tests)
- Coverage target: 80%+

**Example Test Pattern:**
```python
def test_process_pdf_success(client, auth_headers, mock_gemini):
    """Test successful PDF processing"""
    with open('tests/fixtures/sample.pdf', 'rb') as f:
        data = {'pdf_file': (f, 'sample.pdf')}
        response = client.post(
            '/api/v1/process-pdf',
            data=data,
            headers=auth_headers
        )
    assert response.status_code == 200
    assert 'job_id' in response.json
```

### Pre-Commit Hooks

Install for automatic formatting:
```bash
cd backend
pip install pre-commit
pre-commit install
```

## Project-Specific Patterns

### Credit System (Two-Phase Commit)

1. **Estimate:** Calculate cost without reservation
2. **Reserve:** Soft-reserve credits when job confirmed
3. **Finalize:** Adjust balance based on actual usage
4. **Ledger:** All transactions logged in `CreditLedger`

### Vocabulary Coverage Modes

1. **Filter Mode:** Find sentences with ≥95% common words (4-8 words) - ideal for rapid drilling
2. **Coverage Mode:** Greedy algorithm selects minimal sentence set covering all target words
3. **Batch Mode:** Analyze multiple sources with quality scoring and sentence limit

### Google OAuth Flow

1. Frontend initiates Google OAuth → Gets auth code
2. Backend receives code → Validates with Google → Creates/updates `User`
3. Backend generates JWT access + refresh tokens
4. Frontend stores tokens → Axios interceptor handles refresh
5. Google tokens stored in `User.google_access_token/google_refresh_token`

## Configuration

### Environment Variables

**Backend (`backend/.env`):**
- `SECRET_KEY`, `JWT_SECRET_KEY` - Security keys
- `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` - OAuth credentials
- `GEMINI_API_KEY` - AI model access
- `DATABASE_URL` - PostgreSQL connection string
- `REDIS_URL` - Redis for Celery broker/result backend
- `CORS_ORIGINS` - Allowed frontend origins (comma-separated)

**Frontend (`frontend/.env.local`):**
- `NEXT_PUBLIC_API_URL` - Backend API URL
- `NEXT_PUBLIC_GOOGLE_CLIENT_ID` - Google OAuth client ID

### Performance Configuration

Railway deployment optimizations in `backend/config.py`:
- `CELERY_CONCURRENCY=8` - Worker parallelism
- `DB_POOL_SIZE=20` - Connection pool for 8 workers
- `CHUNK_TASK_MAX_RETRIES=4` - Retry attempts
- `GEMINI_CALL_TIMEOUT_SECONDS=300` - 5-minute LLM timeout
- `CHUNK_WATCHDOG_SECONDS=600` - 10-minute stuck detection

## Common Debugging Patterns

### Celery Task Monitoring

```bash
# Check Celery worker status
docker-compose -f docker-compose.dev.yml exec celery celery -A backend.app.celery_app:celery inspect active

# Monitor task queue
docker-compose -f docker-compose.dev.yml exec celery celery -A backend.app.celery_app:celery inspect registered
```

### Database Query Debugging

Enable SQL logging in `config.py`:
```python
SQLALCHEMY_ECHO = True  # Logs all SQL queries
```

### WebSocket Connection Issues

Check Socket.IO connection in browser console:
```javascript
// frontend/src/lib/useJobWebSocket.ts
// Look for connection events: 'connect', 'disconnect', 'job_progress'
```

## Key Files Reference

- `backend/app/__init__.py` - Application factory, extension initialization
- `backend/app/routes.py` - Main REST API endpoints
- `backend/app/tasks.py` - Celery async tasks with retry logic
- `backend/app/services/gemini_service.py` - AI normalization with fallback cascade
- `backend/app/services/chunking_service.py` - Adaptive PDF chunking
- `backend/app/celery_app.py` - Celery factory with Flask context
- `backend/config.py` - Environment-driven configuration
- `frontend/src/lib/api.ts` - Centralized API client with token refresh
- `frontend/src/lib/queries.ts` - TanStack Query hooks
- `frontend/src/stores/*.ts` - Zustand state management

## Database Schema Notes

- **User:** Stores Google OAuth tokens (`google_access_token`, `google_refresh_token`, `google_token_expiry`)
- **Job:** Tracks processing jobs with `status` (pending/processing/completed/failed), `retry_count`, `chunk_results`
- **JobChunk:** Individual chunk state with `status`, `attempts`, `last_error`, `result_json`
- **History:** Denormalized results for fast retrieval with `sentences` JSON array
- **CoverageRun:** Analysis runs with `mode` (filter/coverage/batch), `status`, `stats_json`
- **CoverageAssignment:** Word-to-sentence mappings for coverage results

## Deployment Architecture

### Production Setup

**Railway Services (3 separate services):**
1. **Backend API** (`Dockerfile.web`)
   - Flask web server (Gunicorn)
   - Serves REST API at `/api/v1`
   - Handles HTTP requests and WebSocket connections

2. **Celery Workers** (`Dockerfile.railway-worker`)
   - 8 concurrent workers for async PDF processing
   - Executes `process_chunk`, `finalize_job_results`, `coverage_build_async` tasks
   - Optimized for 8GB RAM / 8 vCPU

3. **Flower** (`Dockerfile.flower`)
   - Celery task monitoring dashboard
   - View active tasks, worker status, task history
   - Access via Railway public URL

**Railway Add-ons:**
- **PostgreSQL** - Primary database (use Railway's Postgres plugin)
- **Redis** - Celery broker/result backend + rate limiting

**Vercel (Frontend):**
- Next.js 15 application deployed to Vercel
- Static assets served via CDN
- Environment variable: `NEXT_PUBLIC_API_URL` points to Railway backend URL

### Deployment Steps

**Railway Backend Setup:**
1. Create new Railway project with 3 services
2. Link GitHub repo to each service
3. Configure Dockerfiles:
   - Backend: `backend/Dockerfile.web`
   - Celery: `backend/Dockerfile.railway-worker`
   - Flower: `backend/Dockerfile.flower`
4. Add PostgreSQL and Redis plugins
5. Set environment variables (see Configuration section)
6. Deploy all services
7. Run migrations in backend service: `flask db upgrade`

**Vercel Frontend Setup:**
1. Import GitHub repo to Vercel
2. Set root directory to `frontend/`
3. Configure environment variables:
   - `NEXT_PUBLIC_API_URL` - Railway backend URL (e.g., `https://your-backend.railway.app`)
   - `NEXT_PUBLIC_GOOGLE_CLIENT_ID` - Google OAuth client ID
4. Deploy

**Critical Configuration:**
- Ensure `CORS_ORIGINS` in backend includes Vercel frontend URL
- Configure WebSocket connection URL in frontend to point to Railway backend
- Set `REDIS_URL` and `DATABASE_URL` from Railway plugin connection strings

### Deployment Dockerfiles

- `backend/Dockerfile.web` - Flask API server with Gunicorn
- `backend/Dockerfile.railway-worker` - Celery worker with spaCy models
- `backend/Dockerfile.flower` - Flower monitoring dashboard
- `backend/Dockerfile.dev` - Local development (hot reload)

**Note:** Docker Compose (`docker-compose.yml`, `docker-compose.dev.yml`) is for local development only, not used in production.
- don't write summarizing documents everytime you change something
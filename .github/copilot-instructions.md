# Copilot Instructions: French Novel Tool

## Project Overview
Flask + Next.js app for processing French novel PDFs using Google Gemini AI to normalize sentence length and export to Google Sheets. JWT auth with Google OAuth, Material-UI v7 frontend, service-oriented backend architecture.

## Architecture Essentials

### Backend Structure (Flask + SQLAlchemy)
- **Application Factory Pattern**: App created via `create_app()` in `backend/app/__init__.py`
- **Service Layer**: All business logic in `backend/app/services/` (e.g., auth, gemini, pdf, google_sheets, history, user_settings, credits, jobs, vocabulary coverage).
- **Blueprint-based Routing**: Routes organized into multiple blueprints (main, auth, credits, coverage) registered at `/api/v1`.
- **Database Migrations**: Flask-Migrate only, never use `db.create_all()` (see comment in `__init__.py`)
- **Extensions**: SQLAlchemy (db), JWT (jwt), Limiter (limiter), Migrate (migrate) - all initialized in `__init__.py`

### Frontend Structure (Next.js 15 + TypeScript)
- **App Router**: Pages in `frontend/src/app/`, Material-UI v7 with Emotion
- **State Management**: Zustand stores (`useProcessingStore`, `useHistoryStore`, `useSettingsStore`) for global state
- **API Client**: Centralized in `frontend/src/lib/api.ts` with auto token refresh interceptor
- **React Query**: TanStack Query for server state (`frontend/src/lib/queries.ts`)
- **Context**: AuthContext for user authentication state

### Data Flow Pattern
1. User uploads PDF → `POST /api/v1/process-pdf` (jwt_required, rate limited)
2. PDFService extracts text → GeminiService normalizes sentences → HistoryService saves record
3. Frontend stores results in ProcessingStore → User edits inline → ExportDialog → GoogleSheetsService creates spreadsheet
4. All Google API calls use user's OAuth tokens (stored in User model: google_access_token, google_refresh_token)

## Critical Development Workflows

### Database Changes
```bash
# ALWAYS use migrations, never db.create_all()
docker-compose -f docker-compose.dev.yml exec backend flask db migrate -m "Description"
docker-compose -f docker-compose.dev.yml exec backend flask db upgrade
# Copilot instructions — French Novel Tool (concise)

Purpose: make AI coding agents productive quickly by summarizing architecture, key files, commands, and project-specific conventions.

- Big picture: a Flask backend (SQLAlchemy + Flask-Migrate) + Celery workers for async PDF processing, and a Next.js (TS) frontend.
- Core data flow: upload PDF -> PDFService (extract/metadata) -> ChunkingService -> Celery tasks (process_chunk) -> GeminiService (LLM normalize) -> finalize_job_results -> History -> optional Google Sheets export.

Key files (quick jump):
- `backend/app/__init__.py` — create_app(), extension init (db, jwt, limiter, socketio, celery).
- `backend/app/routes.py` — main REST endpoints (process-pdf, estimate-pdf, extract-pdf-text) and admin endpoints that trigger Celery tasks.
- `backend/app/tasks.py` — Celery tasks (names: `app.tasks.process_chunk`, `app.tasks.finalize_job_results`, `app.tasks.chunk_watchdog`) and orchestration patterns (chord, retry, watchdog).
- `backend/app/services/` — business logic (PDFService, GeminiService, ChunkingService, JobService, GoogleSheetsService).
- `backend/app/schemas.py` — Marshmallow validation for requests/responses.
- `backend/config.py` — environment-driven configuration (CORS origin expansion, Celery/Redis, DB pooling, GEMINI_* vars).

Developer workflows & explicit commands:
- Start dev stack (hot reload): `./dev-setup.sh` (Unix) or `dev-setup.bat` (Windows); or `docker-compose -f docker-compose.dev.yml up`.
- DB migrations (inside dev container):
    - `docker-compose -f docker-compose.dev.yml exec backend flask db migrate -m "msg"`
    - `docker-compose -f docker-compose.dev.yml exec backend flask db upgrade`
- Tests / lint:
    - Backend: `cd backend && pytest --cov=app --cov-report=html`
    - Frontend lint: `cd frontend && npm run lint`
    - Install pre-commit hooks: `cd backend && pre-commit install`.

Project-specific conventions (do not deviate):
- Always use Flask-Migrate; `db.create_all()` is disabled in `backend/app/__init__.py`.
- Services are instantiated per-request (see `routes.py` where GeminiService is created from user settings). HistoryService and UserSettingsService are the few module-level instances.
- JWT: `get_jwt_identity()` returns a string; convert to int (e.g., `user_id = int(get_jwt_identity())`).
- Rate limiting: always put `@jwt_required()` before `@limiter.limit()` on protected endpoints (see `routes.py`).
- File validation: use `utils/validators.validate_pdf_file()` (checks magic bytes, size), not filename extension alone.

Celery + reliability notes (practical patterns):
- Tasks use chords and group patterns; finalization is idempotent: `finalize_job_results` will early-exit if job already finalized.
- Chunks may be delivered as base64 in `chunk_info['file_b64']` (workers prefer in-memory bytes over shared FS).
- DB writes use `safe_db_commit()` retry helper — treat DB operations as potentially transient in cloud deployments.

Integration & secrets:
- GEMINI_API_KEY controls LLM calls (`config.py`), model selection via user settings maps to internal model names in `JobService`.
- Google OAuth tokens (access/refresh) are stored on the `User` model and used for Google Sheets exports via `GoogleSheetsService`.
- Redis (REDIS_URL) used for Celery broker/result backend and for rate limiter storage in production.

When making changes: reference these files for examples and tests: `backend/app/tasks.py` (retry/watchdog patterns), `backend/app/routes.py` (auth + rate limiting + job flow), and `backend/app/services/gemini_service.py` (LLM retries and fallbacks).

If anything here is unclear or you want deeper examples (small patches, tests, or expanded task wiring), tell me which area to expand and I will iterate.

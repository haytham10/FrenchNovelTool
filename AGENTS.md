# Agent Guidelines for French Novel Tool

## Build/Lint/Test Commands

**Backend:**
- `cd backend && pytest` - Run all tests with coverage
- `cd backend && pytest tests/test_file.py::test_function -v` - Run single test
- `cd backend && black .` - Format Python code
- `cd backend && flake8` - Lint Python code
- `flask db migrate -m "description" && flask db upgrade` - Database migrations

**Frontend:**
- `cd frontend && npm run dev` - Development server
- `cd frontend && npm run build` - Production build
- `cd frontend && npm run lint` - ESLint

**Docker:**
- `make dev` - Start development environment
- `make test` - Run backend tests in container
- `make lint` - Run linters in containers

## Code Style Guidelines

**Python:**
- Black formatting (100 char line length)
- Flake8 linting (ignore E203, W503)
- Use Flask-Migrate for DB schema changes (NEVER db.create_all())
- Service layer pattern: business logic in `backend/app/services/`
- JWT identity: `user_id = int(get_jwt_identity())`
- Rate limiting: `@jwt_required()` before `@limiter.limit()`

**TypeScript/React:**
- Functional components with hooks (no class components)
- Centralized API client in `frontend/src/lib/api.ts`
- Zustand for UI state, TanStack Query for server state
- Type safety with shared types in `frontend/src/lib/types.ts`

**Error Handling:**
- Use `safe_db_commit()` for all DB writes in Celery tasks
- Transient errors trigger automatic retry, non-transient fail immediately
- File validation via `utils/validators.validate_pdf_file()` (magic bytes, not extensions)

**Architecture:**
- Backend: Application Factory Pattern with service layer
- Frontend: Next.js 15 App Router with Material-UI
- Real-time updates via Socket.IO WebSocket hooks
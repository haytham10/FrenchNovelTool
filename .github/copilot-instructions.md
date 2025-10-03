# Copilot Instructions: French Novel Tool

## Project Overview
Flask + Next.js app for processing French novel PDFs using Google Gemini AI to normalize sentence length and export to Google Sheets. JWT auth with Google OAuth, Material-UI v7 frontend, service-oriented backend architecture.

## Architecture Essentials

### Backend Structure (Flask + SQLAlchemy)
- **Application Factory Pattern**: App created via `create_app()` in `backend/app/__init__.py`
- **Service Layer**: All business logic in `backend/app/services/` (6 services: auth, gemini, pdf, google_sheets, history, user_settings)
- **Blueprint-based Routing**: Two blueprints registered at `/api/v1` (main_bp) and `/api/v1/auth` (auth_bp)
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
```

### Running the Stack
```bash
# Development (hot reload, debug mode)
./dev-setup.sh  # Unix
dev-setup.bat   # Windows
# Or: docker-compose -f docker-compose.dev.yml up

# Production
docker-compose up --build
# Or: make prod
```

### Testing & Linting
```bash
# Backend (from backend/)
pytest --cov=app --cov-report=html
# Pre-commit hooks run Black (100 char line limit), Flake8, Bandit

# Frontend (from frontend/)
npm run lint
```

## Project-Specific Conventions

### Authentication Flow
- **JWT + Google OAuth**: Frontend gets Google token → backend validates with AuthService → creates JWT access/refresh tokens
- **Token Storage**: Access token in memory/localStorage, refresh token in httpOnly cookie (see `frontend/src/lib/auth.ts`)
- **Protected Routes**: Use `@jwt_required()` decorator, current user via `get_jwt_identity()` (returns user_id as string, must convert to int)
- **Token Refresh**: Automatic via axios interceptor on 401 responses

### Rate Limiting Pattern
```python
@main_bp.route('/process-pdf', methods=['POST'])
@jwt_required()
@limiter.limit("10 per hour")  # Applied AFTER @jwt_required
def process_pdf():
    # Limits are per-endpoint, configured in route decorator
```

### Validation Pattern
- **Marshmallow Schemas**: All request/response validation in `backend/app/schemas.py`
- **File Uploads**: Use `validate_pdf_file()` from `utils/validators.py` (checks extension, size, and PDF magic bytes)
- **Example**:
```python
from .schemas import ExportToSheetSchema
schema = ExportToSheetSchema()
data = schema.load(request.json)  # Raises ValidationError if invalid
```

### Service Instantiation
- Services are instantiated per-request (NOT singletons): `gemini_service = GeminiService(sentence_length_limit=12)`
- Exception: HistoryService and UserSettingsService created at module level in routes.py

### Error Handling
- Centralized handlers in `backend/app/utils/error_handlers.py` (registered in `create_app()`)
- Custom CORS handling in `backend/app/utils/cors_handlers.py` (adds OPTIONS preflight support)
- Frontend: ErrorBoundary component for React errors, toast notifications via notistack

### Configuration Pattern
- **Environment Variables**: Backend loads from `.env` via python-dotenv, frontend from `.env.local`
- **CORS Handling**: Auto-includes www/apex variants (see `config.py` `_with_www_variants()`)
- **Constants**: Centralized in `backend/app/constants.py` (API_VERSION, SERVICE_NAME, status codes)

## Key Files to Reference

### When Adding New Endpoints
- `backend/app/routes.py` - Main API routes (process-pdf, export-to-sheet, history, settings)
- `backend/app/auth_routes.py` - Auth routes (login, refresh, logout, google-auth)
- `backend/app/schemas.py` - Add validation schema for new endpoint

### When Modifying Database Schema
- `backend/app/models.py` - User, History, UserSettings models
- Run migrations (see Database Changes above)
- Update corresponding schemas in `schemas.py`

### When Adding Frontend Features
- `frontend/src/lib/api.ts` - Add API function (auto-includes auth header)
- `frontend/src/lib/queries.ts` - Add React Query hooks if needed
- State in Zustand stores (`frontend/src/stores/`) for complex state

### Docker & Deployment
- `docker-compose.dev.yml` - Development stack (hot reload, exposed ports)
- `docker-compose.yml` - Production stack (health checks, restart policies)
- `Makefile` - Convenient commands (make dev, make prod, make test)
- `backend/vercel.json` + `frontend/vercel.json` - Serverless deployment config

## Dependencies & Integration Points

### External APIs
- **Google Gemini AI**: Configured via `GEMINI_API_KEY`, model selection in UserSettings (balanced/quality/speed maps to gemini-2.5-flash/pro/lite)
- **Google Sheets API**: Uses user's OAuth tokens, scopes defined in `config.py` (spreadsheets + drive.file)
- **Redis**: Required for rate limiting in production (RATELIMIT_STORAGE_URI), optional in dev (falls back to memory://)

### Critical Dependencies
- Backend: Flask 3.x, SQLAlchemy, Flask-JWT-Extended, Flask-Limiter, google-genai SDK, tenacity (retry logic)
- Frontend: Next.js 15, React 19, Material-UI v7, TanStack Query v5, Zustand, axios

## Common Pitfalls

1. **Database Migration**: Never call `db.create_all()` - it's explicitly disabled (see `backend/app/__init__.py:55`)
2. **User ID Type**: `get_jwt_identity()` returns string, must convert to int: `user_id = int(get_jwt_identity())`
3. **Rate Limiting Order**: Apply `@limiter.limit()` AFTER `@jwt_required()` decorator
4. **Service Instantiation**: GeminiService takes settings in constructor, create new instance per request with user's settings
5. **CORS**: Don't add origins manually, use CORS_ORIGINS env var (auto-expands www/apex variants)
6. **File Validation**: Always use `validate_pdf_file()`, don't rely on extension alone
7. **Frontend API Calls**: Use functions from `lib/api.ts` or React Query hooks from `lib/queries.ts`, don't create raw axios calls

## Style & Formatting

- **Python**: Black formatter (100 char line), PEP 8, type hints encouraged, docstrings required for services
- **TypeScript**: ESLint config in `eslint.config.mjs`, strict mode enabled
- **Commit Messages**: Conventional commits (feat/fix/docs/style/refactor/test/chore)
- **Pre-commit Hooks**: Auto-format with Black, Flake8, Bandit (install: `cd backend && pre-commit install`)

## Testing Notes

- Backend: pytest with coverage (`pytest --cov=app --cov-report=html`)
- Test config in `backend/pyproject.toml` ([tool.pytest.ini_options])
- Coverage reports in `htmlcov/` (gitignored)
- Frontend: ESLint only (no test suite currently)

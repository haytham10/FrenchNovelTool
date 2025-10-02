# Backend Improvement Roadmap

This document outlines a strategic roadmap for improving the backend of the French Novel Tool. The focus is on enhancing scalability, maintainability, security, and performance.

---

## Current State Analysis

### Strengths
- ✅ Well-structured Flask application with blueprints
- ✅ JWT authentication with Google OAuth integration
- ✅ Rate limiting with Redis support
- ✅ Database migrations with Alembic
- ✅ Good error handling with retry logic (Gemini service)
- ✅ User-specific settings and history tracking
- ✅ Clean separation of concerns (services, routes, models)

### Weaknesses
- ⚠️ Using SQLite in production (not suitable for scale)
- ⚠️ Synchronous PDF processing (long-running requests)
- ⚠️ No comprehensive test suite
- ⚠️ Limited monitoring and observability
- ⚠️ No API documentation
- ⚠️ Environment-specific configuration could be improved
- ⚠️ No database connection pooling configured

---

## Phase 1: Foundation & Code Quality (Short-Term, 2-4 weeks)

**Objective:** Improve code quality, testing, and developer experience.

### 1.1 Testing Infrastructure
- [ ] **Set up pytest framework**
    - Action: Install pytest, pytest-flask, pytest-cov
    - Implementation: Create `tests/` directory structure with `conftest.py`
    - Priority: HIGH

- [ ] **Write unit tests for services**
    - Action: Test each service in isolation with mocked dependencies
    - Files to test:
        - `app/services/gemini_service.py` (mock API calls)
        - `app/services/auth_service.py` (mock Google OAuth)
        - `app/services/google_sheets_service.py` (mock Google Sheets API)
        - `app/services/pdf_service.py` (test file handling)
    - Target: 80%+ coverage for services
    - Priority: HIGH

- [ ] **Write integration tests for API endpoints**
    - Action: Test all routes with test client
    - Test scenarios:
        - Authentication flow (login, token refresh, logout)
        - PDF processing with mock file
        - History CRUD operations
        - Settings management
        - Error cases (unauthorized, invalid data, etc.)
    - Priority: HIGH

- [ ] **Add test database configuration**
    - Action: Use in-memory SQLite for tests
    - Implementation: Create `config.TestConfig` class
    - Priority: MEDIUM

### 1.2 API Documentation
- [ ] **Implement OpenAPI/Swagger documentation**
    - Action: Install flask-swagger-ui or flasgger
    - Implementation: Add docstrings to all routes with OpenAPI spec
    - Benefit: Auto-generated interactive API docs at `/api/docs`
    - Priority: MEDIUM

- [ ] **Document all request/response schemas**
    - Action: Expand Marshmallow schemas with descriptions
    - Files: `app/schemas.py`
    - Priority: MEDIUM

### 1.3 Error Handling & Logging
- [ ] **Centralize error handling**
    - Action: Create custom exception classes
    - Implementation:
        ```python
        # app/exceptions.py
        class APIException(Exception): pass
        class ValidationError(APIException): pass
        class AuthenticationError(APIException): pass
        class ExternalServiceError(APIException): pass
        ```
    - Register error handlers in `app/__init__.py`
    - Priority: MEDIUM

- [ ] **Implement structured logging (JSON)**
    - Action: Configure Python logging to output JSON
    - Implementation: Use `python-json-logger` package
    - Benefit: Better parsing in log aggregation tools
    - Priority: LOW

- [ ] **Add request ID tracking**
    - Action: Add middleware to generate unique request IDs
    - Implementation: Include request_id in all logs and error responses
    - Priority: LOW

### 1.4 Configuration Management
- [ ] **Create environment-specific configs**
    - Action: Expand `config.py` with multiple config classes
    - Implementation:
        ```python
        class DevelopmentConfig(Config): ...
        class TestingConfig(Config): ...
        class ProductionConfig(Config): ...
        ```
    - Priority: MEDIUM

- [ ] **Validate required environment variables on startup**
    - Action: Add startup check that fails fast if critical vars missing
    - Priority: MEDIUM

---

## Phase 2: Performance & Scalability (Mid-Term, 1-2 months)

**Objective:** Prepare the application for production-scale traffic and concurrent users.

### 2.1 Database Migration
- [ ] **Migrate to PostgreSQL**
    - Action: Set up PostgreSQL server (local or cloud)
    - Implementation:
        - Update `SQLALCHEMY_DATABASE_URI` in production config
        - Test all Alembic migrations on PostgreSQL
        - Add connection pooling configuration
    - Benefits:
        - Better concurrent performance
        - ACID compliance
        - Advanced features (full-text search, JSON columns)
    - Priority: HIGH

- [ ] **Optimize database queries**
    - Action: Add indexes to frequently queried columns
    - Columns to index:
        - `History.user_id`, `History.timestamp`
        - `UserSettings.user_id`
    - Tool: Use Flask-DebugToolbar to profile queries
    - Priority: MEDIUM

- [ ] **Implement database connection pooling**
    - Action: Configure SQLAlchemy pool settings
    - Settings: `pool_size`, `max_overflow`, `pool_recycle`
    - Priority: MEDIUM

### 2.2 Asynchronous Processing
- [ ] **Implement Celery for background tasks**
    - Action: Install Celery and configure with Redis broker
    - Implementation:
        - Create `app/tasks.py` for Celery tasks
        - Move PDF processing to background task
        - Move Google Sheets export to background task
    - Priority: HIGH

- [ ] **Update API endpoints for async pattern**
    - Action: `/process-pdf` returns job_id immediately
    - New endpoints:
        - `POST /process-pdf` → returns `{"job_id": "..."}`
        - `GET /jobs/<job_id>` → returns status and result
    - Frontend will poll job status
    - Priority: HIGH

- [ ] **Add job status tracking**
    - Action: Store job status in Redis or database
    - States: `pending`, `processing`, `completed`, `failed`
    - Priority: HIGH

### 2.3 Caching Layer
- [ ] **Implement Redis caching**
    - Action: Cache frequently accessed data
    - Cache candidates:
        - User settings (TTL: 5 minutes)
        - User profile data (TTL: 10 minutes)
    - Use Flask-Caching extension
    - Priority: MEDIUM

- [ ] **Cache Gemini API responses (optional)**
    - Action: Hash (prompt + PDF) and cache results
    - Benefit: Save API costs for duplicate requests
    - Consideration: Storage size vs. cost savings
    - Priority: LOW

### 2.4 Rate Limiting Enhancements
- [ ] **Implement per-user rate limiting**
    - Action: Create different limits for different endpoints
    - Current: Fixed limits per endpoint
    - Improved: User-based limits with premium tier support
    - Priority: MEDIUM

- [ ] **Add rate limit headers to responses**
    - Headers: `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`
    - Priority: LOW

---

## Phase 3: Security & Production Readiness (Long-Term, 2-3 months)

**Objective:** Harden security, add monitoring, and prepare for production deployment.

### 3.1 Security Hardening
- [ ] **Implement security headers**
    - Action: Use Flask-Talisman
    - Headers to add:
        - Content-Security-Policy
        - Strict-Transport-Security (HSTS)
        - X-Content-Type-Options
        - X-Frame-Options
    - Priority: HIGH

- [ ] **Add input validation for all endpoints**
    - Action: Use Marshmallow schemas for all request validation
    - Current: Partial validation
    - Target: 100% of endpoints validated
    - Priority: HIGH

- [ ] **Implement CSRF protection**
    - Action: Add CSRF tokens for state-changing operations
    - Use Flask-WTF or Flask-SeaSurf
    - Priority: MEDIUM

- [ ] **Add SQL injection protection audit**
    - Action: Review all raw SQL queries (if any)
    - Current: Using SQLAlchemy ORM (safe), but audit for raw queries
    - Priority: MEDIUM

- [ ] **Implement file upload security**
    - Action: Add virus scanning for uploaded PDFs
    - Tool: ClamAV integration or cloud scanning service
    - Priority: MEDIUM

- [ ] **Add dependency vulnerability scanning**
    - Action: Integrate `pip-audit` or Snyk into CI/CD
    - Run on every commit
    - Priority: MEDIUM

- [ ] **Implement secret rotation mechanism**
    - Action: Support rotating JWT secrets without downtime
    - Implementation: Accept multiple valid JWT secrets
    - Priority: LOW

### 3.2 Monitoring & Observability
- [ ] **Implement application metrics**
    - Action: Use Prometheus client for Python
    - Metrics to track:
        - Request duration
        - Request count by endpoint
        - Error rate
        - Gemini API call duration and errors
        - Database query duration
    - Priority: HIGH

- [ ] **Add health check enhancements**
    - Current: Basic `/health` endpoint
    - Enhanced: Check database, Redis, and external API connectivity
    - Return detailed status for each dependency
    - Priority: MEDIUM

- [ ] **Implement distributed tracing**
    - Action: Use OpenTelemetry or Jaeger
    - Benefit: Trace requests through services and external APIs
    - Priority: LOW

- [ ] **Set up error tracking**
    - Action: Integrate Sentry or similar service
    - Benefit: Automatic error reporting with context
    - Priority: MEDIUM

### 3.3 Performance Monitoring
- [ ] **Add APM (Application Performance Monitoring)**
    - Tools: New Relic, Datadog, or Elastic APM
    - Track: Slow queries, endpoint performance, memory usage
    - Priority: MEDIUM

- [ ] **Implement query performance logging**
    - Action: Log slow database queries (>100ms)
    - Tool: SQLAlchemy events
    - Priority: LOW

### 3.4 API Versioning
- [ ] **Formalize API versioning strategy**
    - Current: `/api/v1/` prefix exists
    - Implementation: Document versioning policy
    - Plan for `/api/v2/` migration path
    - Priority: LOW

---

## Phase 4: Advanced Features (Future, 3+ months)

**Objective:** Add sophisticated features for power users and enterprise.

### 4.1 Batch Processing
- [ ] **Implement batch PDF processing**
    - Action: Allow users to upload multiple PDFs as a batch job
    - Track batch progress and allow partial results
    - Priority: MEDIUM

### 4.2 Webhooks
- [ ] **Add webhook support**
    - Action: Allow users to register webhooks for job completion
    - Useful for integrations and automation
    - Priority: LOW

### 4.3 Advanced User Management
- [ ] **Implement user roles and permissions**
    - Roles: Free, Premium, Admin
    - Different rate limits and features per role
    - Priority: MEDIUM

- [ ] **Add team/organization support**
    - Allow multiple users to share resources
    - Priority: LOW

### 4.4 Analytics
- [ ] **Add usage analytics dashboard**
    - Track: PDFs processed, API calls, popular features
    - Dashboard for admin users
    - Priority: LOW

---

## Success Metrics

### Phase 1 Success Criteria
- ✅ 80%+ test coverage
- ✅ API documentation available
- ✅ Zero manual configuration steps for development

### Phase 2 Success Criteria
- ✅ PDF processing completes without timeout for files up to 50MB
- ✅ System handles 100+ concurrent users
- ✅ 95th percentile response time < 200ms (excluding PDF processing)

### Phase 3 Success Criteria
- ✅ Zero critical security vulnerabilities
- ✅ 99.9% uptime
- ✅ Automatic alerting on errors
- ✅ Full observability (logs, metrics, traces)

---

## Estimated Timeline

- **Phase 1**: 2-4 weeks (can start immediately)
- **Phase 2**: 1-2 months (after Phase 1 completion)
- **Phase 3**: 2-3 months (parallel with Phase 2)
- **Phase 4**: Ongoing (as needed)

**Total to production-ready**: ~3-4 months with dedicated development

---

## Priority Legend
- **HIGH**: Critical for production readiness or major user impact
- **MEDIUM**: Important for quality and maintainability
- **LOW**: Nice-to-have improvements

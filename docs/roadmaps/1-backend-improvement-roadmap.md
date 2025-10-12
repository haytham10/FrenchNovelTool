# Backend Improvement Roadmap

**Last Updated:** October 2, 2025

This roadmap focuses on backend reliability, testing, performance, and production readiness.

---

## 📊 Current State (October 2025)

### ✅ Implemented & Working
- Flask application with Blueprint architecture
- JWT authentication with Google OAuth 2.0
- User model with OAuth token storage
- Rate limiting with Flask-Limiter (Redis optional)
- Database migrations with Flask-Migrate/Alembic
- User-specific settings and processing history
- Service layer architecture (clean separation)
- Retry logic for Gemini API calls (tenacity)
- Comprehensive error handling and logging
- Input validation with Marshmallow schemas
- CORS configuration for frontend
- Docker containerization
- Enhanced JSON parsing with fallback mechanisms

### ⚠️ Current Issues & Gaps
- **Production errors**: JSON parsing failures in GeminiService (partially fixed)
- **No test coverage**: Zero unit/integration tests
- **SQLite in production**: Not suitable for concurrent users
- **Synchronous processing**: Long PDFs block requests (up to 60s)
- **No API documentation**: Endpoints not formally documented
- **Limited monitoring**: No error tracking, no performance metrics
- **Manual deployment**: No CI/CD pipeline
- **No database pooling**: Connection management not optimized

---

## 🔴 P0 - Critical (Weeks 1-4)

**Objective:** Fix production issues and establish testing foundation

### 1. Testing Infrastructure (Week 1-2)
**Priority: CRITICAL** - Cannot deploy confidently without tests

#### Unit Tests
- [ ] **Install pytest framework**
  ```bash
  pip install pytest pytest-flask pytest-cov pytest-mock faker
  ```
- [ ] **Create test structure**
  ```
  tests/
    conftest.py          # Fixtures and test config
    test_services/
      test_gemini_service.py
      test_auth_service.py
      test_google_sheets_service.py
      test_pdf_service.py
    test_routes/
      test_auth_routes.py
      test_main_routes.py
    test_models.py
  ```
- [ ] **Write service tests** (80% coverage target)
  - Mock Gemini API responses (success, malformed JSON, timeout)
  - Mock Google OAuth (token exchange, refresh, errors)
  - Mock Sheets API (create, append, errors)
  - Test PDF file handling (valid, corrupt, oversized)
- [ ] **Add test database configuration**
  ```python
  # config.py
  class TestConfig(Config):
      TESTING = True
      SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
  ```

#### Integration Tests
- [ ] **Test authentication flow**
  - Google login → JWT creation → Protected endpoint access
  - Token refresh flow
  - Expired token handling
  - Invalid token rejection
- [ ] **Test PDF processing pipeline**
  - Upload → Extract → Normalize → Store history
  - Error scenarios (invalid PDF, Gemini timeout, JSON parse failure)
  - Rate limiting enforcement
- [ ] **Test Sheets export**
  - Create new sheet → Export sentences → Update history
  - OAuth token refresh during export
  - Folder creation and permissions

**Success Criteria:**
- ✅ 80%+ code coverage on services
- ✅ All critical paths have integration tests
- ✅ Tests run in < 30 seconds
- ✅ CI pipeline can run tests automatically

### 2. Production Error Fixes (Week 2)
**Priority: CRITICAL** - Directly impacting users

- [x] **Improve JSON parsing in GeminiService** (COMPLETED)
  - Multi-level fallback parsing
  - Brace-matching extraction
  - Regex-based sentence extraction
  - Better error logging

- [ ] **Add response validation**
  ```python
  def validate_gemini_response(data: dict) -> bool:
      \"\"\"Validate structure before processing\"\"\"
      if not isinstance(data, dict):
          return False
      if 'sentences' not in data:
          return False
      if not isinstance(data['sentences'], list):
          return False
      return True
  ```

- [ ] **Implement response caching**
  - Hash (PDF content + prompt) → Cache result for 24h
  - Reduce duplicate API calls
  - Save costs on repeated documents

- [ ] **Add retry logic for transient failures**
  ```python
  @retry(
      stop=stop_after_attempt(3),
      wait=wait_exponential(min=2, max=30),
      retry=retry_if_exception_type((ConnectionError, TimeoutError)),
      before_sleep=before_sleep_log(logger, logging.WARNING)
  )
  ```

### 3. API Documentation (Week 3)
**Priority: HIGH** - Essential for frontend developers and future maintainers

- [ ] **Install and configure Flask-RESTX or flasgger**
  ```bash
  pip install flask-restx
  ```
- [ ] **Document all endpoints with OpenAPI spec**
  - Request/response schemas
  - Authentication requirements
  - Error codes and messages
  - Example requests/responses
- [ ] **Generate interactive API docs**
  - Accessible at `/api/docs`
  - Try-it-out functionality
  - Auto-generated from code annotations
- [ ] **Document authentication flow**
  - OAuth 2.0 flow diagram
  - Token usage examples
  - Refresh token process

**Example:**
```python
@main_bp.route('/process-pdf')
@api.doc(
    description='Process PDF and normalize sentences',
    responses={
        200: 'Success',
        401: 'Unauthorized',
        422: 'Processing error',
        500: 'Server error'
    },
    security='Bearer'
)
@api.expect(pdf_upload_model)
@api.marshal_with(sentences_response_model)
def process_pdf():
    pass
```

### 4. Error Tracking & Logging (Week 4)
**Priority: HIGH** - Need visibility into production issues

- [ ] **Integrate Sentry for error tracking**
  ```python
  import sentry_sdk
  from sentry_sdk.integrations.flask import FlaskIntegration
  
  sentry_sdk.init(
      dsn=os.getenv('SENTRY_DSN'),
      integrations=[FlaskIntegration()],
      environment=os.getenv('FLASK_ENV', 'production')
  )
  ```
- [ ] **Add structured logging**
  ```python
  import structlog
  
  logger.info('pdf_processing_started', 
      user_id=user.id,
      filename=filename,
      file_size=file_size,
      model=gemini_model
  )
  ```
- [ ] **Create custom exceptions**
  ```python
  # app/exceptions.py
  class APIException(Exception):
      status_code = 500
  
  class GeminiAPIError(APIException):
      status_code = 502
  
  class PDFProcessingError(APIException):
      status_code = 422
  ```
- [ ] **Add error context to responses**
  ```json
  {
    \"error\": \"Failed to parse AI response\",
    \"error_code\": \"GEMINI_PARSE_ERROR\",
    \"request_id\": \"abc123\",
    \"timestamp\": \"2025-10-02T10:30:00Z\"
  }
  ```

---

## 🟠 P1 - High Priority (Weeks 5-8)

**Objective:** Production database, async processing, CI/CD automation

### 5. PostgreSQL Migration (Week 5)
**Priority: HIGH** - Essential for production deployment

- [ ] **Set up PostgreSQL**
  - Local: Docker container
  - Production: Supabase or AWS RDS
  ```yaml
  # docker-compose.yml
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: frenchnovel
      POSTGRES_USER: app
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
  ```

- [ ] **Update configuration**
  ```python
  # config.py
  class ProductionConfig(Config):
      SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL')
      SQLALCHEMY_ENGINE_OPTIONS = {
          'pool_size': 10,
          'pool_recycle': 3600,
          'pool_pre_ping': True,
      }
  ```

- [ ] **Test all migrations**
  ```bash
  # Fresh install
  flask db upgrade
  
  # Verify data integrity
  pytest tests/test_migrations.py
  ```

- [ ] **Create backup strategy**
  - Daily automated backups
  - Point-in-time recovery capability
  - Backup restoration testing

### 6. Async Job Processing (Week 6-7)
**Priority: HIGH** - Critical for user experience

- [ ] **Install Celery + Redis**
  ```bash
  pip install celery redis
  ```

- [ ] **Create Celery app**
  ```python
  # app/celery_app.py
  from celery import Celery
  
  celery = Celery(
      'frenchnovel',
      broker=os.getenv('REDIS_URL'),
      backend=os.getenv('REDIS_URL')
  )
  ```

- [ ] **Convert PDF processing to async task**
  ```python
  # app/tasks.py
  @celery.task(bind=True)
  def process_pdf_async(self, user_id, file_path, settings):
      self.update_state(state='PROCESSING', meta={'progress': 0})
      
      # Extract text
      self.update_state(meta={'progress': 25})
      
      # Call Gemini
      self.update_state(meta={'progress': 75})
      
      # Save results
      return {'sentences': [...], 'job_id': self.request.id}
  ```

- [ ] **Update API endpoints**
  ```python
  @main_bp.route('/process-pdf', methods=['POST'])
  def process_pdf():
      # Start async task
      task = process_pdf_async.delay(user_id, file_path, settings)
      
      return jsonify({
          'job_id': task.id,
          'status': 'pending'
      }), 202
  
  @main_bp.route('/jobs/<job_id>', methods=['GET'])
  def get_job_status(job_id):
      task = process_pdf_async.AsyncResult(job_id)
      
      return jsonify({
          'status': task.state,
          'progress': task.info.get('progress', 0),
          'result': task.result if task.ready() else None
      })
  ```

- [ ] **Add job cleanup**
  - Remove completed jobs after 24h
  - Cancel abandoned jobs after 1h
  - Track job metrics (avg duration, failure rate)

### 7. CI/CD Pipeline (Week 8)
**Priority: HIGH** - Automation is essential

- [ ] **Create GitHub Actions workflows**
  
  **`.github/workflows/backend-ci.yml`:**
  ```yaml
  name: Backend CI
  
  on: [push, pull_request]
  
  jobs:
    test:
      runs-on: ubuntu-latest
      services:
        postgres:
          image: postgres:15
          env:
            POSTGRES_PASSWORD: test
          options: >-
            --health-cmd pg_isready
            --health-interval 10s
      
      steps:
        - uses: actions/checkout@v3
        - uses: actions/setup-python@v4
          with:
            python-version: '3.10'
        
        - name: Install dependencies
          run: |
            cd backend
            pip install -r requirements.txt
            pip install -r requirements-dev.txt
        
        - name: Run linters
          run: |
            cd backend
            flake8 app tests
            black --check app tests
        
        - name: Run tests
          run: |
            cd backend
            pytest --cov=app --cov-report=xml
        
        - name: Upload coverage
          uses: codecov/codecov-action@v3
  ```

- [ ] **Add security scanning**
  ```yaml
  - name: Security scan
    run: |
      pip install safety bandit
      safety check
      bandit -r app/
  ```

- [ ] **Create deployment workflow**
  - Automatic deploy to staging on push to `develop`
  - Manual approval for production deploy
  - Rollback capability

---

## 🟡 P2 - Medium Priority (Weeks 9-12)

### 8. Performance Optimizations
- [ ] **Add database indexes**
  ```python
  # Analyze slow queries
  Index('idx_history_user_timestamp', History.user_id, History.timestamp.desc())
  Index('idx_users_email', User.email)
  ```

- [ ] **Implement caching layer**
  ```python
  from flask_caching import Cache
  
  cache = Cache(config={'CACHE_TYPE': 'redis'})
  
  @cache.cached(timeout=300, key_prefix='user_settings')
  def get_user_settings(user_id):
      pass
  ```

- [ ] **Optimize Gemini API usage**
  - Batch similar requests
  - Use streaming responses for large PDFs
  - Implement request deduplication

### 9. Security Enhancements
- [ ] **Add security headers** (Flask-Talisman)
  - Content-Security-Policy
  - Strict-Transport-Security
  - X-Frame-Options

- [ ] **Implement CSRF protection**
  - For state-changing endpoints
  - Token validation

- [ ] **Add rate limiting per user**
  ```python
  @limiter.limit(\"10 per hour\", key_func=lambda: str(get_jwt_identity()))
  ```

- [ ] **Audit and update dependencies**
  ```bash
  pip-audit
  pip list --outdated
  ```

### 10. Monitoring & Observability
- [ ] **Add application metrics**
  ```python
  from prometheus_flask_exporter import PrometheusMetrics
  
  metrics = PrometheusMetrics(app)
  ```

- [ ] **Create health check endpoint**
  ```python
  @main_bp.route('/health')
  def health_check():
      return jsonify({
          'status': 'healthy',
          'database': check_database(),
          'redis': check_redis(),
          'gemini_api': check_gemini_api()
      })
  ```

- [ ] **Set up log aggregation**
  - Centralize logs from all instances
  - Set up alerts for errors
  - Create dashboards for metrics

---

## 📊 Success Metrics

### Code Quality
- ✅ 80%+ test coverage
- ✅ Zero critical security vulnerabilities
- ✅ All linters passing (flake8, black, bandit)
- ✅ API documentation complete

### Performance
- ✅ < 100ms response time for non-processing endpoints
- ✅ < 5s for async job creation
- ✅ 99% uptime in production

### Developer Experience
- ✅ CI/CD pipeline runs in < 5 minutes
- ✅ Local setup in < 10 minutes
- ✅ Clear documentation for all features
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

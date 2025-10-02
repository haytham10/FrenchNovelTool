# Backend Improvement Roadmap

This document outlines a strategic roadmap for improving the backend of the French Novel Tool. The focus is on enhancing scalability, maintainability, security, and performance.

---

## Phase 1: Strengthening the Foundation (Short-Term)

**Objective:** Improve robustness, developer experience, and prepare for future scaling.

- [ ] **Centralize and Enhance Error Handling:**
    -   **Action:** Refactor all API endpoints to use the centralized error handlers in `app/utils/error_handlers.py`.
    -   **Implementation:** Register custom exception handlers on the Flask app instance to automatically catch common errors (e.g., `ValidationError`, `NotFound`, generic `Exception`) and return standardized JSON error responses. This will remove repetitive `try...except` blocks from the routes.

- [ ] **Improve Configuration Management:**
    -   **Action:** Make the application configuration environment-aware.
    -   **Implementation:** Modify `config.py` to use environment variables (e.g., `FLASK_ENV`) to load different configurations for `development`, `testing`, and `production`. This includes database URIs, secret keys, and external service credentials.

- [ ] **Expand Test Coverage:**
    -   **Action:** Increase unit and integration test coverage for critical components.
    -   **Implementation:**
        -   Write unit tests for all services in `app/services/`.
        -   Create integration tests for all API endpoints in `app/routes.py` and `app/auth_routes.py`, mocking external API calls.
        -   Set up a testing database and configure Flask to use it during tests.

- [ ] **Adopt a Structured Logging Format:**
    -   **Action:** Switch from plain text logs to a structured format like JSON.
    -   **Implementation:** Configure Python's `logging` module to use a JSON formatter. This will make logs machine-readable and easier to parse, search, and analyze in a production logging system.

---

## Phase 2: Performance and Scalability (Mid-Term)

**Objective:** Prepare the application for higher traffic and more complex, long-running tasks.

- [ ] **Transition to a Production-Ready Database:**
    -   **Action:** Migrate from SQLite to a more robust database like PostgreSQL.
    -   **Implementation:**
        -   Set up a PostgreSQL server (e.g., using Docker or a managed service).
        -   Update the `SQLALCHEMY_DATABASE_URI` in the production configuration.
        -   Use Alembic to manage the migration of the existing schema and data.

- [ ] **Implement Asynchronous Task Processing:**
    -   **Action:** Offload long-running tasks (like PDF processing and Gemini API calls) to a background worker.
    -   **Implementation:**
        -   Integrate a task queue like **Celery** with a message broker such as **Redis**.
        -   The `/process-pdf` endpoint will add a job to the queue and immediately return a `202 Accepted` response with a job ID.
        -   The frontend will then poll a new `/status/<job_id>` endpoint to get the result. This prevents server timeouts and improves responsiveness.

- [ ] **Optimize Database Queries:**
    -   **Action:** Analyze and optimize database interactions to reduce latency.
    -   **Implementation:** Use `SQLAlchemy-Utils` or Flask-DebugToolbar to inspect queries. Add database indexes to frequently queried columns (e.g., foreign keys like `user_id` in the `History` table). Use more efficient query patterns where needed.

---

## Phase 3: Advanced Features & Security Hardening (Long-Term)

**Objective:** Enhance security posture and add advanced capabilities.

- [ ] **Comprehensive Security Hardening:**
    -   **Action:** Implement additional security best practices.
    -   **Implementation:**
        -   **Input Validation:** Add more rigorous validation on all incoming data, not just request bodies but also query parameters and headers.
        -   **Security Headers:** Use a library like `Flask-Talisman` to automatically add security headers (e.g., CSP, HSTS, X-Content-Type-Options).
        -   **Dependency Scanning:** Integrate a tool like `Snyk` or `pip-audit` into the CI/CD pipeline to scan for vulnerabilities in dependencies.

- [ ] **Implement API Versioning:**
    -   **Action:** Introduce a more formal API versioning strategy.
    -   **Implementation:** While the `/api/v1` prefix exists, formalize it using Flask Blueprints. For example, structure the project so that future versions (`/api/v2`) can be developed alongside v1 without breaking the existing frontend.

- [ ] **Introduce a Caching Layer:**
    -   **Action:** Implement caching for frequently accessed, non-dynamic data.
    -   **Implementation:** Use a cache like Redis or Memcached to store results of expensive operations. For example, user settings or the results of processing a commonly used public domain text could be cached to reduce database load and API response times.

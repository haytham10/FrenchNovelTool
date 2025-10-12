# DevOps & Infrastructure Roadmap

**Last Updated:** October 2, 2025

Focus: CI/CD automation, monitoring, deployment, and reliability.

---

## 📊 Current State

### ✅ Implemented
- Docker containers (frontend + backend)
- docker-compose for local development
- Environment variable configuration
- Redis for rate limiting
- Health checks in containers
- Separate dev/prod Dockerfiles

### ⚠️ Missing
- No CI/CD pipeline (manual deployment)
- No automated testing in pipeline
- No monitoring or alerting
- No centralized logging
- No staging environment
- Secrets in .env files (not secure)
- No infrastructure as code
- No rollback capability

---

## 🔴 P0 - Critical (Weeks 1-4)

### Week 1-2: GitHub Actions CI Pipeline
**Automate testing and validation**

#### Backend CI Workflow
`.github/workflows/backend-ci.yml`:
```yaml
name: Backend CI

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main, develop ]

jobs:
  test:
    runs-on: ubuntu-latest
    
    services:
      postgres:
        image: postgres:15-alpine
        env:
          POSTGRES_PASSWORD: test
          POSTGRES_DB: test_db
        ports:
          - 5432:5432
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
      
      redis:
        image: redis:7-alpine
        ports:
          - 6379:6379
    
    steps:
      - uses: actions/checkout@v4
      
      - uses: actions/setup-python@v5
        with:
          python-version: '3.10'
          cache: 'pip'
      
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
      
      - name: Security scan
        run: |
          cd backend
          bandit -r app/
          safety check
      
      - name: Run tests
        run: |
          cd backend
          pytest --cov=app --cov-report=xml --cov-report=term
        env:
          DATABASE_URL: postgresql://postgres:test@localhost:5432/test_db
          REDIS_URL: redis://localhost:6379
      
      - name: Upload coverage
        uses: codecov/codecov-action@v4
        with:
          file: ./backend/coverage.xml
```

#### Frontend CI Workflow
`.github/workflows/frontend-ci.yml`:
```yaml
name: Frontend CI

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main, develop ]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v4
      
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
          cache-dependency-path: frontend/package-lock.json
      
      - name: Install dependencies
        run: |
          cd frontend
          npm ci
      
      - name: Run linter
        run: |
          cd frontend
          npm run lint
      
      - name: Type check
        run: |
          cd frontend
          npx tsc --noEmit
      
      - name: Run tests
        run: |
          cd frontend
          npm test -- --coverage
      
      - name: Build
        run: |
          cd frontend
          npm run build
```

### Week 3: Docker Registry & CD Pipeline
**Automate deployment**

#### Build and Push Containers
`.github/workflows/docker-build.yml`:
```yaml
name: Build Docker Images

on:
  push:
    branches: [ main ]
    tags: [ 'v*' ]

jobs:
  build:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3
      
      - name: Login to GitHub Container Registry
        uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}
      
      - name: Build and push backend
        uses: docker/build-push-action@v5
        with:
          context: ./backend
          push: true
          tags: |
            ghcr.io/${{ github.repository }}/backend:latest
            ghcr.io/${{ github.repository }}/backend:${{ github.sha }}
          cache-from: type=gha
          cache-to: type=gha,mode=max
      
      - name: Build and push frontend
        uses: docker/build-push-action@v5
        with:
          context: ./frontend
          push: true
          tags: |
            ghcr.io/${{ github.repository }}/frontend:latest
            ghcr.io/${{ github.repository }}/frontend:${{ github.sha }}
```

### Week 4: Secret Management
**Secure configuration**

- [ ] **Use GitHub Secrets**
  - Store all sensitive values in GitHub repository secrets
  - Never commit secrets to code
  - Rotate secrets regularly

- [ ] **Environment-specific secrets**
  ```
  # Development
  DEV_DATABASE_URL
  DEV_REDIS_URL
  
  # Staging
  STAGING_DATABASE_URL
  STAGING_REDIS_URL
  
  # Production
  PROD_DATABASE_URL
  PROD_REDIS_URL
  PROD_SENTRY_DSN
  ```

- [ ] **Runtime secret injection**
  ```yaml
  # docker-compose.prod.yml
  backend:
    image: ghcr.io/user/backend:latest
    environment:
      DATABASE_URL: ${DATABASE_URL}
      JWT_SECRET_KEY: ${JWT_SECRET_KEY}
    secrets:
      - gemini_api_key
  
  secrets:
    gemini_api_key:
      external: true
  ```

---

## 🟠 P1 - High Priority (Weeks 5-8)

### Week 5: Error Tracking (Sentry)
**Monitor production errors**

- [ ] **Set up Sentry project**
  ```bash
  # Backend
  pip install sentry-sdk[flask]
  
  # Frontend
  npm install @sentry/nextjs
  ```

- [ ] **Configure Sentry**
  ```python
  # backend/app/__init__.py
  import sentry_sdk
  from sentry_sdk.integrations.flask import FlaskIntegration
  
  sentry_sdk.init(
      dsn=os.getenv('SENTRY_DSN'),
      integrations=[FlaskIntegration()],
      environment=os.getenv('FLASK_ENV'),
      traces_sample_rate=0.1,
      profiles_sample_rate=0.1,
  )
  ```

- [ ] **Set up alerts**
  - Email on new errors
  - Slack notifications for critical issues
  - Daily error digest

### Week 6: Logging Infrastructure
**Centralize logs**

- [ ] **Structured JSON logging**
  ```python
  import structlog
  
  structlog.configure(
      processors=[
          structlog.processors.TimeStamper(fmt=\"iso\"),
          structlog.processors.StackInfoRenderer(),
          structlog.processors.format_exc_info,
          structlog.processors.JSONRenderer()
      ]
  )
  
  logger = structlog.get_logger()
  logger.info(\"pdf_processed\", 
      user_id=user.id,
      filename=filename,
      duration_ms=duration,
      sentences_count=len(sentences)
  )
  ```

- [ ] **Log aggregation**
  - Use Loki + Grafana (self-hosted)
  - Or CloudWatch Logs (AWS)
  - Or Datadog/New Relic (SaaS)

- [ ] **Log retention policy**
  - Keep 30 days online
  - Archive 90 days to S3
  - Delete after 1 year

### Week 7-8: Monitoring & Metrics
**Application observability**

- [ ] **Add Prometheus metrics**
  ```python
  from prometheus_flask_exporter import PrometheusMetrics
  
  metrics = PrometheusMetrics(app)
  
  # Custom metrics
  pdf_processing_duration = metrics.histogram(
      'pdf_processing_duration_seconds',
      'Time spent processing PDF'
  )
  
  @pdf_processing_duration.time()
  def process_pdf():
      ...
  ```

- [ ] **Create Grafana dashboards**
  - Request rate and latency
  - Error rates by endpoint
  - Database connection pool usage
  - Celery queue length
  - API quota usage (Gemini)

- [ ] **Set up alerts**
  ```yaml
  # alerts.yml
  - alert: HighErrorRate
    expr: rate(http_requests_total{status=~\"5..\"}[5m]) > 0.05
    for: 5m
    annotations:
      summary: \"High error rate detected\"
  
  - alert: SlowProcessing
    expr: histogram_quantile(0.95, pdf_processing_duration_seconds) > 60
    for: 10m
    annotations:
      summary: \"PDF processing is slow\"
  ```

---

## 🟡 P2 - Medium Priority (Weeks 9-12)

### Week 9: Staging Environment
**Test before production**

- [ ] **Create staging stack**
  ```yaml
  # docker-compose.staging.yml
  version: '3.8'
  
  services:
    backend-staging:
      image: ghcr.io/user/backend:develop
      environment:
        FLASK_ENV: staging
        DATABASE_URL: ${STAGING_DB_URL}
    
    frontend-staging:
      image: ghcr.io/user/frontend:develop
      environment:
        NEXT_PUBLIC_API_BASE_URL: https://api-staging.example.com
  ```

- [ ] **Staging deployment pipeline**
  - Auto-deploy on merge to `develop`
  - Run integration tests
  - Notify team in Slack

### Week 10: Infrastructure as Code
**Reproducible infrastructure**

- [ ] **Terraform for cloud resources**
  ```hcl
  # main.tf
  resource \"aws_db_instance\" \"postgres\" {
    identifier = \"frenchnovel-db\"
    engine     = \"postgres\"
    instance_class = \"db.t3.micro\"
    allocated_storage = 20
  }
  
  resource \"aws_elasticache_cluster\" \"redis\" {
    cluster_id = \"frenchnovel-redis\"
    engine     = \"redis\"
    node_type  = \"cache.t3.micro\"
  }
  ```

- [ ] **Version control infrastructure**
  - Commit Terraform configs to repo
  - Use Terraform Cloud or AWS CloudFormation
  - Review changes before apply

### Week 11-12: Deployment Automation
**Zero-downtime deployments**

- [ ] **Blue-green deployment**
  - Run two environments (blue/green)
  - Deploy to inactive environment
  - Run smoke tests
  - Switch traffic if tests pass
  - Keep old version for rollback

- [ ] **Database migration automation**
  ```yaml
  deploy:
    steps:
      - name: Run migrations
        run: |
          docker run backend flask db upgrade
      
      - name: Deploy new version
        run: |
          docker-compose up -d --no-deps backend
      
      - name: Wait for health check
        run: |
          ./scripts/wait-for-health.sh
      
      - name: Switch traffic
        run: |
          ./scripts/switch-traffic.sh
  ```

---

## 📊 Success Metrics

### Automation
- ✅ 100% of deploys via CI/CD
- ✅ Zero manual deployments
- ✅ < 5 min from push to deploy

### Reliability
- ✅ 99.9% uptime
- ✅ < 5 min mean time to detection (MTTD)
- ✅ < 30 min mean time to recovery (MTTR)

### Observability
- ✅ All errors tracked in Sentry
- ✅ All logs centralized
- ✅ Key metrics dashboards available
- ✅ Alerts configured for critical issues

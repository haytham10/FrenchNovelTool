# DevOps & Infrastructure Improvement Roadmap

This document outlines a strategic roadmap for improving the DevOps practices and infrastructure of the French Novel Tool. The goal is to automate processes, improve reliability, and create a scalable and secure production environment.

---

## Current State Analysis

### Strengths
- ✅ Docker containerization (frontend + backend)
- ✅ Docker Compose setup for local development
- ✅ Separate dev and prod Dockerfiles
- ✅ Health checks configured
- ✅ Redis for rate limiting
- ✅ Environment variable configuration
- ✅ Volume mounts for persistence

### Weaknesses
- ⚠️ No CI/CD pipeline
- ⚠️ No automated testing in pipeline
- ⚠️ Secrets in environment files (not secure for production)
- ⚠️ No centralized logging
- ⚠️ No monitoring or alerting
- ⚠️ Single-instance deployment (no scaling)
- ⚠️ No infrastructure as code
- ⚠️ No staging environment
- ⚠️ Manual deployment process

---

## Phase 1: CI/CD & Automation (Short-Term, 2-3 weeks)

**Objective:** Automate build, test, and deployment processes.

### 1.1 Continuous Integration
- [ ] **Set up GitHub Actions workflows**
    - Action: Create `.github/workflows/` directory
    - Priority: HIGH

- [ ] **Create backend CI workflow**
    - File: `.github/workflows/backend-ci.yml`
    - Steps:
        1. Checkout code
        2. Set up Python 3.10
        3. Install dependencies
        4. Run linters (flake8, black --check)
        5. Run type checking (mypy)
        6. Run pytest with coverage
        7. Upload coverage to Codecov
    - Trigger: On push to `main`, `develop`, and PRs
    - Priority: HIGH

- [ ] **Create frontend CI workflow**
    - File: `.github/workflows/frontend-ci.yml`
    - Steps:
        1. Checkout code
        2. Set up Node.js 20
        3. Install dependencies (`npm ci`)
        4. Run linter (`npm run lint`)
        5. Run type checking (`tsc --noEmit`)
        6. Run tests (`npm test`)
        7. Build (`npm run build`)
    - Trigger: On push to `main`, `develop`, and PRs
    - Priority: HIGH

- [ ] **Add code quality checks**
    - Action: Integrate SonarCloud or CodeClimate
    - Checks: Code smells, duplication, complexity
    - Priority: MEDIUM

- [ ] **Add security scanning**
    - Backend: `pip-audit` for Python dependencies
    - Frontend: `npm audit` for Node dependencies
    - Docker: Trivy or Snyk for container scanning
    - Priority: HIGH

### 1.2 Continuous Deployment
- [ ] **Create Docker build and push workflow**
    - File: `.github/workflows/docker-build.yml`
    - Steps:
        1. Build Docker images (backend + frontend)
        2. Tag with commit SHA and `latest`
        3. Push to container registry (Docker Hub or GHCR)
    - Trigger: On push to `main` after CI passes
    - Priority: HIGH

- [ ] **Set up container registry**
    - Options:
        - GitHub Container Registry (ghcr.io) - Free for public repos
        - Docker Hub - Familiar, widely supported
        - AWS ECR / GCP Container Registry - If using cloud
    - Priority: HIGH

- [ ] **Create deployment workflow**
    - File: `.github/workflows/deploy.yml`
    - Steps:
        1. SSH into production server
        2. Pull latest images
        3. Run database migrations
        4. Restart containers with zero-downtime
    - Trigger: Manual approval or automatic after tests pass
    - Priority: HIGH

- [ ] **Implement blue-green deployment**
    - Action: Run two environments, switch traffic after validation
    - Benefit: Zero-downtime deployments
    - Priority: MEDIUM

### 1.3 Secret Management
- [ ] **Use GitHub Secrets for CI/CD**
    - Action: Store all secrets in GitHub repository secrets
    - Secrets needed:
        - `DOCKER_USERNAME`, `DOCKER_PASSWORD`
        - `SSH_PRIVATE_KEY` for deployment
        - `PRODUCTION_HOST`
    - Priority: HIGH

- [ ] **Implement production secret management**
    - Options:
        - Docker Swarm secrets
        - HashiCorp Vault
        - AWS Secrets Manager / GCP Secret Manager
    - Action: Remove `.env` files from production, use secrets injection
    - Priority: HIGH

---

## Phase 2: Monitoring & Observability (Mid-Term, 1 month)

**Objective:** Gain visibility into application health and performance.

### 2.1 Logging Infrastructure
- [ ] **Centralize logs**
    - Action: Aggregate logs from all containers
    - Solution Options:
        - **ELK Stack** (Elasticsearch, Logstash, Kibana)
        - **Loki + Grafana** (lighter alternative)
        - **Cloud solution** (AWS CloudWatch, GCP Cloud Logging)
    - Priority: HIGH

- [ ] **Configure structured logging**
    - Backend: Already outputs JSON logs (from roadmap)
    - Frontend: Send browser errors to logging service
    - Priority: MEDIUM

- [ ] **Set up log retention policy**
    - Action: Keep logs for 30-90 days
    - Compress or archive older logs
    - Priority: MEDIUM

### 2.2 Metrics & Monitoring
- [ ] **Deploy Prometheus + Grafana**
    - Action: Add to `docker-compose.yml`
    - Prometheus: Scrape metrics from backend
    - Grafana: Visualize metrics with dashboards
    - Priority: HIGH

- [ ] **Configure application metrics**
    - Backend: Expose `/metrics` endpoint (use `prometheus-flask-exporter`)
    - Metrics:
        - Request count, duration, errors
        - Gemini API call duration
        - Database query duration
        - Queue depth (if Celery is added)
    - Priority: HIGH

- [ ] **Set up infrastructure metrics**
    - Action: Use Prometheus Node Exporter
    - Metrics: CPU, memory, disk, network
    - Priority: MEDIUM

- [ ] **Create Grafana dashboards**
    - Dashboards:
        - Application overview (requests, errors, latency)
        - Infrastructure health (CPU, memory, disk)
        - Business metrics (PDFs processed, users, exports)
    - Priority: MEDIUM

### 2.3 Alerting
- [ ] **Configure alert rules**
    - Action: Use Grafana Alerting or Prometheus Alertmanager
    - Alerts:
        - Error rate > 5% for 5 minutes
        - Response time > 5s (p95) for 5 minutes
        - Disk usage > 85%
        - Service down (health check failed)
        - High memory usage (> 90%)
    - Priority: HIGH

- [ ] **Set up notification channels**
    - Options: Email, Slack, PagerDuty, Discord
    - Priority: HIGH

- [ ] **Create on-call rotation**
    - Action: Define who responds to alerts
    - Tool: PagerDuty or Opsgenie
    - Priority: LOW (for team size)

### 2.4 Error Tracking
- [ ] **Integrate Sentry**
    - Action: Add Sentry SDK to backend and frontend
    - Benefits:
        - Automatic error reporting
        - Stack traces with context
        - User impact tracking
        - Release tracking
    - Priority: HIGH

- [ ] **Configure error notifications**
    - Action: Alert on new or frequent errors
    - Priority: MEDIUM

---

## Phase 3: Scalability & High Availability (Mid-Term, 1-2 months)

**Objective:** Support growth and ensure reliability.

### 3.1 Load Balancing
- [ ] **Deploy reverse proxy / load balancer**
    - Options:
        - **Nginx** (simple, efficient)
        - **Traefik** (Docker-native, auto-discovery)
        - **Cloud load balancer** (AWS ALB, GCP LB)
    - Features:
        - SSL termination
        - Rate limiting
        - Request routing
        - Static file serving (frontend assets)
    - Priority: HIGH

- [ ] **Configure SSL/TLS certificates**
    - Action: Use Let's Encrypt (free, auto-renewal)
    - Tool: Certbot or Traefik ACME
    - Priority: HIGH

- [ ] **Implement HTTPS redirect**
    - Action: Redirect all HTTP to HTTPS
    - Priority: HIGH

### 3.2 Container Orchestration
- [ ] **Evaluate orchestration needs**
    - Options:
        - **Docker Swarm** (simple, built into Docker)
        - **Kubernetes** (powerful, complex, overkill for small scale)
        - **Nomad** (middle ground)
    - Recommendation: Start with Docker Swarm
    - Priority: MEDIUM

- [ ] **Set up Docker Swarm cluster** (if chosen)
    - Action: Initialize swarm, add worker nodes
    - Benefits:
        - Service replication
        - Auto-restart failed containers
        - Rolling updates
        - Load balancing
    - Priority: MEDIUM

- [ ] **Create Docker Stack file**
    - File: `docker-stack.yml` (similar to docker-compose but for Swarm)
    - Define:
        - Service replicas (e.g., 3x backend instances)
        - Update strategy (rolling)
        - Resource limits
    - Priority: MEDIUM

### 3.3 Database Scaling
- [ ] **Set up PostgreSQL replication**
    - Action: Configure primary-replica setup
    - Benefit: Read queries can use replicas
    - Priority: LOW (depends on load)

- [ ] **Implement connection pooling**
    - Action: Use PgBouncer
    - Benefit: Reduce database connection overhead
    - Priority: MEDIUM

- [ ] **Set up automated backups**
    - Action: Daily backups to cloud storage (S3, GCS)
    - Retention: 30 days
    - Test restore process
    - Priority: HIGH

### 3.4 Caching & CDN
- [ ] **Deploy Redis Cluster** (if high scale)
    - Action: For caching and rate limiting at scale
    - Current: Single Redis instance
    - Priority: LOW

- [ ] **Set up CDN for frontend assets**
    - Action: Use Cloudflare or AWS CloudFront
    - Benefit: Faster load times globally
    - Priority: LOW

---

## Phase 4: Infrastructure as Code (Long-Term, 2 months)

**Objective:** Make infrastructure reproducible and version-controlled.

### 4.1 Terraform / Pulumi
- [ ] **Choose IaC tool**
    - Options:
        - **Terraform** (widely used, declarative)
        - **Pulumi** (code-based, flexible)
        - **Ansible** (configuration management)
    - Recommendation: Terraform
    - Priority: MEDIUM

- [ ] **Define infrastructure as code**
    - Resources to define:
        - Compute instances (VMs or cloud servers)
        - Networking (VPC, security groups)
        - Load balancers
        - Databases (managed PostgreSQL)
        - Storage (S3 buckets for backups)
        - DNS records
    - Priority: MEDIUM

- [ ] **Set up Terraform state management**
    - Action: Store state in cloud backend (S3 + DynamoDB)
    - Benefit: Team collaboration, state locking
    - Priority: MEDIUM

### 4.2 Configuration Management
- [ ] **Use Ansible for server configuration**
    - Action: Define playbooks for server setup
    - Tasks:
        - Install Docker
        - Configure firewall
        - Set up log rotation
        - Install monitoring agents
    - Priority: LOW

---

## Phase 5: Advanced Topics (Future, 3+ months)

**Objective:** Prepare for enterprise scale and sophisticated operations.

### 5.1 Multi-Environment Setup
- [ ] **Create staging environment**
    - Action: Mirror production setup
    - Purpose: Test deployments before production
    - Priority: HIGH

- [ ] **Implement environment parity**
    - Action: Use same Docker images for dev, staging, prod
    - Only config differs
    - Priority: MEDIUM

- [ ] **Set up preview environments**
    - Action: Create temporary environment for each PR
    - Tool: Heroku Review Apps, Vercel, or custom
    - Priority: LOW

### 5.2 Disaster Recovery
- [ ] **Create disaster recovery plan**
    - Document:
        - RTO (Recovery Time Objective): 1 hour
        - RPO (Recovery Point Objective): 1 hour
        - Backup restore procedures
        - Failover steps
    - Priority: MEDIUM

- [ ] **Implement automated failover**
    - Action: If primary fails, automatically switch to backup
    - Requires: Multi-region setup
    - Priority: LOW

- [ ] **Test disaster recovery**
    - Action: Regular DR drills (quarterly)
    - Priority: MEDIUM

### 5.3 Cost Optimization
- [ ] **Set up cost monitoring**
    - Action: Track cloud costs by service
    - Tool: Cloud provider dashboards
    - Priority: MEDIUM

- [ ] **Implement auto-scaling**
    - Action: Scale containers based on load
    - Metrics: CPU, memory, request queue depth
    - Priority: LOW

- [ ] **Use spot/preemptible instances**
    - Action: For non-critical workloads
    - Benefit: 60-80% cost savings
    - Priority: LOW

### 5.4 Compliance & Security
- [ ] **Implement audit logging**
    - Action: Log all admin actions
    - Priority: MEDIUM

- [ ] **Set up vulnerability scanning**
    - Action: Regular scans of infrastructure
    - Tool: AWS Inspector, Nessus
    - Priority: MEDIUM

- [ ] **Achieve compliance certifications** (if needed)
    - Examples: SOC 2, GDPR, HIPAA
    - Priority: LOW (depends on customer requirements)

---

## Recommended Production Architecture

### Small Scale (0-1000 users)
```
[Cloudflare CDN]
       ↓
[Nginx Load Balancer + SSL]
       ↓
[Docker Swarm - 2 nodes]
   - 2x Frontend containers
   - 3x Backend containers
   - 1x Redis
   - Managed PostgreSQL
       ↓
[Centralized Logging] [Monitoring]
```

### Medium Scale (1000-10000 users)
```
[Cloudflare CDN]
       ↓
[Cloud Load Balancer]
       ↓
[Kubernetes Cluster - 3-5 nodes]
   - Auto-scaled Frontend
   - Auto-scaled Backend
   - Celery workers
   - Redis Cluster
   - Managed PostgreSQL (replicated)
       ↓
[ELK Stack] [Prometheus/Grafana] [Sentry]
```

---

## Success Metrics

### Phase 1 Success Criteria
- ✅ All commits trigger automated CI checks
- ✅ Deployments are automated with single command/click
- ✅ Secrets not stored in code or plain text files
- ✅ Docker images built and published automatically

### Phase 2 Success Criteria
- ✅ Centralized logging with search capability
- ✅ Real-time monitoring dashboards
- ✅ Alerts configured and tested
- ✅ Mean time to detect (MTTD) issues < 5 minutes

### Phase 3 Success Criteria
- ✅ System handles 100+ concurrent users without degradation
- ✅ Zero-downtime deployments
- ✅ 99.9% uptime
- ✅ Automated database backups with tested restore

### Phase 4 Success Criteria
- ✅ Infrastructure reproducible via code
- ✅ New environment can be provisioned in < 30 minutes
- ✅ Infrastructure changes are version-controlled and reviewed

---

## Estimated Timeline

- **Phase 1**: 2-3 weeks (immediate automation)
- **Phase 2**: 1 month (parallel with Phase 1)
- **Phase 3**: 1-2 months (scaling preparation)
- **Phase 4**: 2 months (IaC implementation)
- **Phase 5**: Ongoing (as needed)

**Total to production-ready**: ~3-4 months

---

## Estimated Costs (Monthly)

### Minimal Production Setup
- Compute: $20-50 (2x small VMs or 1 cloud instance)
- Database: $15-30 (managed PostgreSQL basic tier)
- Monitoring: $0 (self-hosted) or $20 (Datadog/New Relic starter)
- CDN: $0-10 (Cloudflare free tier often sufficient)
- **Total: $35-110/month**

### Medium Scale Setup
- Compute: $100-300 (auto-scaled instances)
- Database: $50-150 (production-grade managed PostgreSQL)
- Monitoring: $50-100 (SaaS monitoring)
- CDN: $20-50
- Load Balancer: $15-30
- **Total: $235-630/month**

---

## Priority Legend
- **HIGH**: Critical for production deployment
- **MEDIUM**: Important for reliability and scale
- **LOW**: Nice-to-have or future optimization

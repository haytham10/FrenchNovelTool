# Railway Environment Variables - 8GB RAM / 8 vCPU Optimized Configuration

## Required Variables

### Authentication & Security
SECRET_KEY=<generate-with-python-secrets>
JWT_SECRET_KEY=<generate-with-python-secrets>
GOOGLE_CLIENT_ID=<your-google-oauth-client-id>
GOOGLE_CLIENT_SECRET=<your-google-oauth-client-secret>

### External APIs
GEMINI_API_KEY=<your-gemini-api-key>
GEMINI_MODEL=gemini-2.5-flash

### Database
DATABASE_URL=<railway-postgres-connection-string>

### Redis
REDIS_URL=<railway-redis-connection-string>

### Frontend
CORS_ORIGINS=https://your-frontend-domain.railway.app,https://your-custom-domain.com

## Performance Optimization Variables (8GB RAM / 8 vCPU)

### Celery Worker Configuration
CELERY_CONCURRENCY=8                    # Match vCPU count
WORKER_MAX_MEMORY_MB=900                # ~900MB per worker (8GB / 8 workers with headroom)
PRELOAD_SPACY=true                      # Enable memory sharing for spaCy models

### Database Connection Pool
DB_POOL_SIZE=20                         # Support 8 workers + API server
DB_MAX_OVERFLOW=10                      # Additional burst capacity
DB_POOL_RECYCLE=1800                    # Recycle connections every 30 minutes
DB_CONNECT_TIMEOUT=15                   # Connection timeout in seconds

### Task Retry & Timeout Configuration
CHUNK_TASK_MAX_RETRIES=4                # Retry failed chunks up to 4 times
CHUNK_TASK_RETRY_DELAY=3                # Wait 3 seconds between retries
CHUNK_WATCHDOG_SECONDS=600              # 10-minute watchdog for stuck chunks
CHUNK_STUCK_THRESHOLD_SECONDS=720       # Mark chunks as stuck after 12 minutes
FINALIZE_MAX_RETRIES=10                 # Retry finalization up to 10 times
FINALIZE_RETRY_DELAY=15                 # Wait 15 seconds between finalize retries

### LLM Configuration
GEMINI_MAX_RETRIES=4                    # Retry Gemini API calls up to 4 times
GEMINI_RETRY_DELAY=3                    # Wait 3 seconds between Gemini retries
GEMINI_CALL_TIMEOUT_SECONDS=300         # 5-minute timeout for Gemini API calls

### Rate Limiting
RATELIMIT_ENABLED=True
RATELIMIT_DEFAULT=100 per hour

### File Upload
MAX_FILE_SIZE=104857600                 # 100MB max file size (in bytes)

## Optional Variables

### Logging
LOG_LEVEL=INFO                          # DEBUG for development, INFO for production
LOG_FILE=/app/logs/app.log

### JWT Tokens
JWT_ACCESS_TOKEN_EXPIRES_HOURS=1        # Access token valid for 1 hour
JWT_REFRESH_TOKEN_EXPIRES_DAYS=30       # Refresh token valid for 30 days

### Redis TLS (if using Upstash or similar)
REDIS_TLS=false                         # Set to 'true' if Redis requires TLS

### Flower Monitoring (if enabled)
FLOWER_USER=admin
FLOWER_PASSWORD=<secure-password>
FLOWER_PORT=5555

## Railway Service Configuration

### Worker Service
Deploy with these settings in Railway dashboard:
- **Memory:** 8GB
- **vCPU:** 8
- **Replicas:** 1-2 (scale based on load)
- **Health Check Path:** None (worker doesn't expose HTTP)

### Backend API Service
- **Memory:** 4GB
- **vCPU:** 4
- **Replicas:** 1-2
- **Health Check Path:** /api/v1/health

### Frontend Service
- **Memory:** 2GB
- **vCPU:** 2
- **Replicas:** 1-2
- **Health Check Path:** /

## Environment-Specific Overrides

### Development
```bash
FLASK_ENV=development
LOG_LEVEL=DEBUG
CELERY_CONCURRENCY=2                    # Lower for local development
WORKER_MAX_MEMORY_MB=512
PRELOAD_SPACY=false
```

### Staging
```bash
FLASK_ENV=production
LOG_LEVEL=INFO
CELERY_CONCURRENCY=4                    # Half capacity for cost savings
WORKER_MAX_MEMORY_MB=512
```

### Production (Full Throttle)
```bash
FLASK_ENV=production
LOG_LEVEL=INFO
CELERY_CONCURRENCY=8                    # Full capacity
WORKER_MAX_MEMORY_MB=900
PRELOAD_SPACY=true
DB_POOL_SIZE=20
```

## Monitoring Variables

### Prometheus/Metrics (if enabled)
METRICS_ENABLED=true
METRICS_PORT=9090

### Sentry Error Tracking (if enabled)
SENTRY_DSN=<your-sentry-dsn>
SENTRY_ENVIRONMENT=production

## Security Best Practices

1. **Never commit these values to Git** - use Railway's environment variable management
2. **Rotate secrets regularly** - especially SECRET_KEY and JWT_SECRET_KEY
3. **Use strong passwords** - for FLOWER_PASSWORD and database credentials
4. **Limit CORS_ORIGINS** - only include trusted domains
5. **Enable HTTPS** - Railway provides this by default

## Generating Secrets

```python
# Generate SECRET_KEY and JWT_SECRET_KEY
import secrets
print(secrets.token_urlsafe(32))
```

## Verifying Configuration

After deployment, check:

```bash
# View Celery worker info
celery -A celery_worker.celery inspect stats

# Check database connections
psql $DATABASE_URL -c "SELECT count(*) FROM pg_stat_activity WHERE datname = current_database();"

# Monitor Redis memory
redis-cli --url $REDIS_URL INFO memory
```

## Performance Tuning Tips

1. **Monitor memory usage** - adjust WORKER_MAX_MEMORY_MB if workers are getting killed
2. **Watch task queue length** - increase CELERY_CONCURRENCY if queue backs up
3. **Check database pool** - increase DB_POOL_SIZE if seeing connection errors
4. **Tune chunk sizes** - modify ChunkingService.CHUNK_SIZES if hitting Gemini limits

## Troubleshooting

### Workers Getting Killed (SIGKILL)
- **Cause:** Memory limit exceeded
- **Fix:** Reduce CELERY_CONCURRENCY or increase WORKER_MAX_MEMORY_MB

### Database Connection Errors
- **Cause:** Pool exhaustion
- **Fix:** Increase DB_POOL_SIZE and DB_MAX_OVERFLOW

### Slow Task Processing
- **Cause:** Not enough workers
- **Fix:** Increase CELERY_CONCURRENCY (up to vCPU count)

### Gemini API Timeouts
- **Cause:** Large chunks or rate limits
- **Fix:** Increase GEMINI_CALL_TIMEOUT_SECONDS or reduce chunk sizes

---

**Last Updated:** October 9, 2025  
**Target Infrastructure:** Railway 8GB RAM / 8 vCPU

# Deployment Guide for Async Processing

This guide covers deploying the French Novel Tool with async PDF processing capabilities.

## Prerequisites

- PostgreSQL database
- Redis server (6.0+)
- Python 3.9+
- Node.js 18+
- Sufficient resources (see Resource Requirements)

## Resource Requirements

### Minimum (Small-Medium Workloads)
- **Web Server**: 1 CPU, 1GB RAM
- **Celery Worker**: 1 worker, 2GB RAM
- **Redis**: 512MB RAM
- **Database**: 1GB storage

### Recommended (Production)
- **Web Server**: 2 CPUs, 2GB RAM
- **Celery Workers**: 4 workers, 2GB RAM each (8GB total)
- **Redis**: 2GB RAM (persistent storage)
- **Database**: 10GB storage with backups

### High-Volume (Enterprise)
- **Web Server**: 4 CPUs, 4GB RAM (auto-scaling)
- **Celery Workers**: 8-16 workers, 2GB RAM each
- **Redis**: 4GB RAM (cluster mode)
- **Database**: 50GB+ storage with replication

## Deployment Methods

### Method 1: Docker Compose (Recommended for Development)

1. **Clone the repository:**
   ```bash
   git clone https://github.com/haytham10/FrenchNovelTool.git
   cd FrenchNovelTool
   ```

2. **Configure environment:**
   ```bash
   cp backend/.env.example backend/.env
   # Edit backend/.env with your settings
   ```

3. **Start services:**
   ```bash
   docker-compose -f docker-compose.dev.yml up -d
   ```

   This starts:
   - Flask backend (port 5000)
   - Next.js frontend (port 3000)
   - Redis (port 6379)
   - Celery worker

4. **Run migrations:**
   ```bash
   docker-compose -f docker-compose.dev.yml exec backend flask db upgrade
   ```

### Method 2: Systemd Services (Recommended for Production)

#### 1. Install Dependencies

```bash
# Install system packages
sudo apt-get update
sudo apt-get install -y python3.9 python3-pip postgresql redis-server

# Install Python dependencies
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

#### 2. Configure Services

**Flask API Service** (`/etc/systemd/system/frenchnoveltool-api.service`):
```ini
[Unit]
Description=French Novel Tool API
After=network.target postgresql.service redis.service

[Service]
Type=simple
User=www-data
WorkingDirectory=/var/www/frenchnoveltool/backend
Environment="PATH=/var/www/frenchnoveltool/backend/.venv/bin"
ExecStart=/var/www/frenchnoveltool/backend/.venv/bin/gunicorn \
    -w 4 \
    -b 0.0.0.0:5000 \
    --timeout 30 \
    --access-logfile /var/log/frenchnoveltool/access.log \
    --error-logfile /var/log/frenchnoveltool/error.log \
    run:app
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**Celery Worker Service** (`/etc/systemd/system/frenchnoveltool-celery.service`):
```ini
[Unit]
Description=French Novel Tool Celery Worker
After=network.target redis.service

[Service]
Type=simple
User=www-data
WorkingDirectory=/var/www/frenchnoveltool/backend
Environment="PATH=/var/www/frenchnoveltool/backend/.venv/bin"
ExecStart=/var/www/frenchnoveltool/backend/.venv/bin/celery \
    -A celery_app.celery_app worker \
    --loglevel=info \
    --concurrency=4 \
    --max-tasks-per-child=50 \
    --max-memory-per-child=2048000 \
    --time-limit=3600 \
    --soft-time-limit=3300 \
    --logfile=/var/log/frenchnoveltool/celery.log
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**Celery Beat Service (Optional - for periodic tasks)** (`/etc/systemd/system/frenchnoveltool-celery-beat.service`):
```ini
[Unit]
Description=French Novel Tool Celery Beat
After=network.target redis.service

[Service]
Type=simple
User=www-data
WorkingDirectory=/var/www/frenchnoveltool/backend
Environment="PATH=/var/www/frenchnoveltool/backend/.venv/bin"
ExecStart=/var/www/frenchnoveltool/backend/.venv/bin/celery \
    -A celery_app.celery_app beat \
    --loglevel=info \
    --logfile=/var/log/frenchnoveltool/celery-beat.log
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

#### 3. Enable and Start Services

```bash
# Create log directory
sudo mkdir -p /var/log/frenchnoveltool
sudo chown www-data:www-data /var/log/frenchnoveltool

# Reload systemd
sudo systemctl daemon-reload

# Enable services
sudo systemctl enable frenchnoveltool-api
sudo systemctl enable frenchnoveltool-celery
sudo systemctl enable frenchnoveltool-celery-beat  # Optional

# Start services
sudo systemctl start frenchnoveltool-api
sudo systemctl start frenchnoveltool-celery
sudo systemctl start frenchnoveltool-celery-beat  # Optional

# Check status
sudo systemctl status frenchnoveltool-api
sudo systemctl status frenchnoveltool-celery
```

### Method 3: Cloud Platforms (Heroku, AWS, etc.)

#### Heroku

1. **Add Procfile:**
   ```
   web: cd backend && gunicorn -w 4 -b 0.0.0.0:$PORT run:app
   worker: cd backend && celery -A celery_app.celery_app worker --loglevel=info --concurrency=4
   ```

2. **Add Redis addon:**
   ```bash
   heroku addons:create heroku-redis:premium-0
   ```

3. **Configure environment:**
   ```bash
   heroku config:set ASYNC_PROCESSING_ENABLED=True
   heroku config:set CHUNKING_THRESHOLD_PAGES=50
   heroku config:set MAX_WORKERS=4
   ```

4. **Scale workers:**
   ```bash
   heroku ps:scale web=2 worker=2
   ```

#### AWS Elastic Beanstalk

1. **Create `.ebextensions/celery.config`:**
   ```yaml
   files:
     "/opt/elasticbeanstalk/tasks/taillogs.d/celery.conf":
       mode: "000644"
       content: |
         /var/log/celery/*.log
   
   commands:
     01_celery_worker:
       command: |
         supervisorctl restart celery-worker
   
   container_commands:
     01_migrate:
       command: "source /var/app/venv/*/bin/activate && flask db upgrade"
       leader_only: true
   ```

2. **Deploy:**
   ```bash
   eb init -p python-3.9 frenchnoveltool
   eb create production-env
   eb setenv REDIS_URL=redis://your-redis-endpoint:6379/0
   eb deploy
   ```

## Configuration

### Environment Variables

See `backend/.env.example` for all configuration options. Key settings:

```bash
# Enable async processing
ASYNC_PROCESSING_ENABLED=True

# Chunking configuration
CHUNKING_THRESHOLD_PAGES=50      # Trigger async for files > 50 pages
CHUNK_SIZE_PAGES=50              # Process 50 pages per chunk

# Worker configuration
MAX_WORKERS=4                    # 4 concurrent workers
WORKER_MEMORY_LIMIT_MB=2048     # 2GB per worker
TASK_TIMEOUT_SECONDS=3600       # 1 hour max per task
```

### Database Migrations

After deployment, always run migrations:

```bash
# Docker
docker-compose exec backend flask db upgrade

# Systemd
cd /var/www/frenchnoveltool/backend
source .venv/bin/activate
flask db upgrade

# Heroku
heroku run flask db upgrade
```

## Monitoring

### Health Checks

**API Health:**
```bash
curl http://localhost:5000/api/v1/health
```

**Worker Status:**
```bash
celery -A celery_app.celery_app inspect active
celery -A celery_app.celery_app inspect stats
```

**Redis Status:**
```bash
redis-cli ping
```

### Logging

Logs are available at:
- **API**: `/var/log/frenchnoveltool/access.log` and `error.log`
- **Celery**: `/var/log/frenchnoveltool/celery.log`
- **System**: `journalctl -u frenchnoveltool-api -f`

### Monitoring Tools

1. **Flower** (Celery monitoring web UI):
   ```bash
   pip install flower
   celery -A celery_app.celery_app flower --port=5555
   ```
   Access at: http://localhost:5555

2. **Prometheus** (metrics):
   - Configure celery-exporter for metrics
   - Set up Grafana dashboards

3. **Sentry** (error tracking):
   ```bash
   pip install sentry-sdk[flask]
   ```

## Scaling

### Horizontal Scaling (Multiple Workers)

**Docker Compose:**
```yaml
celery-worker:
  deploy:
    replicas: 4
```

**Kubernetes:**
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: celery-worker
spec:
  replicas: 4
  template:
    spec:
      containers:
      - name: worker
        image: frenchnoveltool-backend:latest
        command: ["celery", "-A", "celery_app.celery_app", "worker"]
```

**Systemd:**
Create multiple service files:
- `frenchnoveltool-celery@1.service`
- `frenchnoveltool-celery@2.service`
- etc.

### Vertical Scaling (More Resources)

Increase worker concurrency:
```bash
# Edit service file
ExecStart=... --concurrency=8  # Was 4, now 8
```

Increase memory limits:
```bash
WORKER_MEMORY_LIMIT_MB=4096  # 4GB instead of 2GB
```

## Troubleshooting

### Workers Not Processing

1. **Check worker status:**
   ```bash
   celery -A celery_app.celery_app inspect active
   ```

2. **Check Redis connection:**
   ```bash
   redis-cli ping
   ```

3. **View worker logs:**
   ```bash
   tail -f /var/log/frenchnoveltool/celery.log
   ```

4. **Restart workers:**
   ```bash
   sudo systemctl restart frenchnoveltool-celery
   ```

### High Memory Usage

1. Reduce workers: `MAX_WORKERS=2`
2. Reduce chunk size: `CHUNK_SIZE_PAGES=25`
3. Enable worker restarts: `--max-tasks-per-child=25`

### Slow Processing

1. Increase workers: `MAX_WORKERS=8`
2. Check Gemini API rate limits
3. Monitor Redis performance
4. Consider caching frequently processed files

## Security Considerations

1. **Environment Variables**: Never commit `.env` files
2. **Redis**: Use authentication (`requirepass`)
3. **API Keys**: Rotate Gemini API keys regularly
4. **HTTPS**: Always use SSL in production
5. **Rate Limiting**: Enable to prevent abuse
6. **File Validation**: Malicious PDF protection is built-in

## Backup and Recovery

### Database Backups

```bash
# PostgreSQL
pg_dump frenchnoveltool > backup.sql

# Restore
psql frenchnoveltool < backup.sql
```

### Redis Persistence

Configure in `redis.conf`:
```
save 900 1
save 300 10
save 60 10000
```

## Performance Tuning

### Recommended Settings for Different Scales

**Small (<100 jobs/day):**
- 1 worker, 2GB RAM
- CHUNK_SIZE_PAGES=50
- No special Redis config

**Medium (100-1000 jobs/day):**
- 4 workers, 2GB RAM each
- CHUNK_SIZE_PAGES=50
- Redis maxmemory 2GB

**Large (1000+ jobs/day):**
- 8-16 workers, 2GB RAM each
- CHUNK_SIZE_PAGES=25 (more chunks, more parallelism)
- Redis cluster mode
- Load balancer for API

## Rollback Procedure

1. **Stop services:**
   ```bash
   sudo systemctl stop frenchnoveltool-api
   sudo systemctl stop frenchnoveltool-celery
   ```

2. **Revert code:**
   ```bash
   git checkout <previous-version>
   ```

3. **Rollback migrations (if needed):**
   ```bash
   flask db downgrade
   ```

4. **Restart services:**
   ```bash
   sudo systemctl start frenchnoveltool-api
   sudo systemctl start frenchnoveltool-celery
   ```

## Support

For issues:
1. Check logs first
2. Review documentation
3. Open GitHub issue with logs and reproduction steps

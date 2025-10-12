# Railway Deployment Guide - Async PDF Processing with Supabase

This guide covers deploying the French Novel Tool to Railway with async processing support, using Supabase for PostgreSQL and Railway's managed Redis.

## 🎯 Overview

**Architecture:**
- **Frontend**: Deployed separately (Vercel/Netlify)
- **Backend API**: Railway service (Flask + Gunicorn)
- **Celery Worker**: Railway service (async task processing)
- **Redis**: Railway managed service (message broker)
- **PostgreSQL**: Supabase managed database

**Key Features:**
- ✅ Async PDF processing with progress tracking
- ✅ Auto-scaling with Railway
- ✅ Connection pooling for Supabase
- ✅ SSL/TLS for all connections
- ✅ Health checks and monitoring

---

## 📋 Prerequisites

Before deploying, ensure you have:

1. **Railway Account** - Sign up at https://railway.app
2. **Supabase Account** - Sign up at https://supabase.com
3. **Supabase PostgreSQL Database** - Project created with connection string
4. **Google Cloud Project** - With Gemini API key and OAuth credentials
5. **GitHub Repository** - Code pushed to GitHub

---

## 🚀 Deployment Steps

### Step 1: Create Railway Project

1. Go to https://railway.app
2. Click **"New Project"**
3. Select **"Deploy from GitHub repo"**
4. Choose your repository: `haytham10/FrenchNovelTool`
5. Railway will create a project and detect the backend

### Step 2: Add Redis Service

1. In your Railway project, click **"New"** → **"Database"** → **"Add Redis"**
2. Railway provisions Redis and auto-injects `REDIS_URL` into all services
3. Note: No additional configuration needed - backend auto-detects Redis

### Step 3: Configure Backend Service

1. In Railway dashboard, select your **backend** service
2. Go to **Settings** → **Root Directory**: Set to `backend`
3. Go to **Variables** and add environment variables:

```bash
# Flask
SECRET_KEY=<generate-random-string>
JWT_SECRET_KEY=<generate-different-random-string>
FLASK_ENV=production

# Supabase Database (get from Supabase dashboard)
DATABASE_URL=postgresql://postgres:[PASSWORD]@db.[PROJECT-REF].supabase.co:5432/postgres

# Database Connection Pool (for production stability)
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=5
DB_POOL_RECYCLE=3600
DB_CONNECT_TIMEOUT=10

# Redis (auto-injected by Railway, verify it exists)
# REDIS_URL=redis://...  (automatically set by Railway)

# Google Gemini API
GEMINI_API_KEY=<your-gemini-api-key>
GEMINI_MODEL=gemini-2.5-flash

# Google OAuth
GOOGLE_CLIENT_ID=<your-client-id>.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=<your-client-secret>

# CORS (update with your frontend domain)
CORS_ORIGINS=https://your-frontend-domain.com

# Rate Limiting
RATELIMIT_ENABLED=true
RATELIMIT_DEFAULT=100 per hour

# Logging
LOG_LEVEL=INFO
```

4. Click **"Deploy"** to apply changes

### Step 4: Run Database Migrations

After backend deploys successfully:

1. Go to backend service → **Settings** → **Deploy Triggers**
2. Or use Railway CLI:

```bash
# Install Railway CLI
npm install -g @railway/cli

# Login
railway login

# Link to your project
railway link

# Run migrations
railway run --service backend flask db upgrade

# Verify migrations
railway run --service backend python verify_migrations.py
```

**Expected Output:**
```
✅ All verifications passed!
🎉 Database is ready for async processing
```

### Step 5: Deploy Celery Worker Service

1. In Railway project, click **"New"** → **"Empty Service"**
2. Name it `celery-worker`
3. Connect to same GitHub repository
4. **Settings**:
   - **Root Directory**: `backend`
   - **Dockerfile Path**: `Dockerfile.railway-worker`
5. **Variables** - Copy ALL environment variables from backend service:
   - Copy `DATABASE_URL`, `REDIS_URL`, `GEMINI_API_KEY`, `SECRET_KEY`, etc.
   - Add: `CELERY_CONCURRENCY=2` (adjust based on Railway plan)
6. Click **"Deploy"**

### Step 6: Verify Deployment

#### Check Backend Health
```bash
curl https://your-backend-url.railway.app/api/v1/health
```

**Expected Response:**
```json
{
  "status": "healthy",
  "service": "French Novel Tool API",
  "version": "1.0.0",
  "checks": {
    "database": "ok",
    "redis": "ok"
  }
}
```

#### Check Worker Logs
1. Go to Railway → `celery-worker` service → **Deployments**
2. Click on latest deployment → **View Logs**
3. Look for:
```
✅ Redis is ready!
✅ Database is ready!
✅ Migrations completed successfully
🎯 Starting Celery worker...
[INFO/MainProcess] celery@hostname ready.
```

#### Test Async Processing

Use the `/process-pdf-async` endpoint instead of `/process-pdf`:

1. Reserve credits: `POST /api/v1/credits/reserve`
2. Upload PDF: `POST /api/v1/process-pdf-async` (returns `job_id`)
3. Poll status: `GET /api/v1/jobs/{job_id}` (every 2 seconds)
4. Get results when `status: "completed"`

---

## 🔧 Troubleshooting

### Issue: "column does not exist" errors

**Cause:** Migrations not applied to Supabase database

**Solution:**
```bash
# Option 1: Run migrations via Railway
railway run --service backend flask db upgrade

# Option 2: Apply SQL directly to Supabase
# 1. Connect to Supabase SQL Editor
# 2. Run contents of backend/fix_jobs_table.sql

# Verify
railway run --service backend python verify_migrations.py
```

### Issue: Worker not connecting to Redis

**Symptoms:** Worker logs show `redis.exceptions.ConnectionError`

**Solution:**
1. Check `REDIS_URL` is set in worker environment variables
2. Verify Redis service is running in Railway dashboard
3. Check worker logs for connection details
4. If using Redis with SSL, ensure `REDIS_TLS=true` is NOT set (Railway Redis doesn't need it)

### Issue: Database connection pool exhausted

**Symptoms:** `TimeoutError: QueuePool limit of size 10 overflow 5 reached`

**Solution:**
```bash
# Increase pool size in backend + worker env vars
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=10

# Or reduce worker concurrency
CELERY_CONCURRENCY=1
```

### Issue: Jobs stuck in "processing" status

**Cause:** Worker crashed or task lost

**Solution:**
1. Check worker logs for errors
2. Restart worker service in Railway
3. Cancel stuck jobs via API: `POST /api/v1/jobs/{job_id}/cancel`
4. Check Celery task time limits (default: 30 min)

### Issue: SSL connection errors to Supabase

**Symptoms:** `ssl.SSLError` or `certificate verify failed`

**Solution:**
- Ensure `DATABASE_URL` includes Supabase domain
- Config already adds `sslmode=require` automatically for Supabase URLs
- Check `backend/config.py` lines 86-90 for SSL logic

### Issue: Health check returns 503

**Cause:** Database or Redis unreachable

**Solution:**
1. Check service logs for connection errors
2. Verify `DATABASE_URL` and `REDIS_URL` are correct
3. Test connections manually:
```bash
railway run --service backend python -c "
from app import create_app, db
app = create_app()
with app.app_context():
    db.session.execute(db.text('SELECT 1'))
print('DB OK')
"
```

---

## 📊 Monitoring

### Railway Metrics

Railway provides built-in metrics:
- **CPU Usage** - Monitor worker CPU (should be <80%)
- **Memory** - Monitor for memory leaks
- **Network** - Track Redis/DB bandwidth

### Application Logs

**Backend Logs:**
```bash
railway logs --service backend
```

**Worker Logs:**
```bash
railway logs --service celery-worker
```

**Filter for errors:**
```bash
railway logs --service backend | grep ERROR
```

### Job Status Endpoint

Poll job status to monitor processing:
```bash
curl -H "Authorization: Bearer $TOKEN" \
  https://your-backend-url.railway.app/api/v1/jobs/123
```

**Response:**
```json
{
  "id": 123,
  "status": "processing",
  "progress_percent": 45,
  "current_step": "Processing chunk 5/10",
  "total_chunks": 10,
  "processed_chunks": 5
}
```

---

## 🔄 Updating Deployment

### Code Changes

1. Push changes to GitHub
2. Railway auto-deploys both backend and worker
3. Check deployment status in Railway dashboard
4. Monitor logs for errors

### Database Schema Changes

```bash
# Create migration locally
cd backend
flask db migrate -m "Description of change"

# Push to GitHub
git add migrations/versions/*.py
git commit -m "Add migration: description"
git push

# After Railway deploys, run migration
railway run --service backend flask db upgrade

# Verify
railway run --service backend python verify_migrations.py
```

### Environment Variable Changes

1. Railway dashboard → Service → Variables
2. Add/update variable
3. Service auto-redeploys
4. Check logs to verify new values

---

## 📈 Scaling

### Horizontal Scaling (Multiple Workers)

Railway Pro plan allows multiple replicas:

1. Railway dashboard → `celery-worker` → **Settings**
2. **Replicas**: Increase from 1 to 2-4
3. Adjust `DB_POOL_SIZE` to accommodate:
   - Formula: `DB_POOL_SIZE = replicas * CELERY_CONCURRENCY * 2`
   - Example: 3 replicas × 2 concurrency × 2 = 12 pool size

### Vertical Scaling (More Resources)

Upgrade Railway plan for more CPU/memory per service.

---

## 🛡️ Security Checklist

- [ ] `SECRET_KEY` and `JWT_SECRET_KEY` are strong random strings
- [ ] `DATABASE_URL` password is secure (Supabase generated)
- [ ] CORS_ORIGINS only includes your actual frontend domain(s)
- [ ] Rate limiting enabled (`RATELIMIT_ENABLED=true`)
- [ ] SSL enabled for Supabase (automatic via config)
- [ ] Environment variables are private (not committed to Git)

---

## 📚 Additional Resources

- **Railway Docs**: https://docs.railway.app
- **Supabase Docs**: https://supabase.com/docs
- **Celery Docs**: https://docs.celeryproject.org
- **Flask Docs**: https://flask.palletsprojects.com

---

## 🆘 Support

If deployment fails after following this guide:

1. Check Railway service logs for errors
2. Run `verify_migrations.py` to check database
3. Verify all environment variables are set correctly
4. Review health check endpoint response
5. Check GitHub Issues for similar problems

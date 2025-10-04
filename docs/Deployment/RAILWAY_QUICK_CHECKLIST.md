# Railway Deployment Quick Checklist ✅

Use this checklist to deploy the async PDF processing system to Railway with Supabase.

## Pre-Deployment

- [ ] Supabase project created
- [ ] Supabase connection string copied (from Settings → Database)
- [ ] Google Gemini API key obtained
- [ ] Google OAuth credentials configured
- [ ] Code pushed to GitHub repository

## Railway Setup (15 minutes)

### 1. Create Project
- [ ] New Railway project created from GitHub repo
- [ ] Backend service auto-detected

### 2. Add Redis
- [ ] Redis database added to project
- [ ] Verify `REDIS_URL` appears in backend variables

### 3. Configure Backend Service
- [ ] Root directory set to `backend`
- [ ] Environment variables added (see template below)
- [ ] Backend deployed successfully

### 4. Run Migrations
- [ ] Migrations run: `railway run --service backend flask db upgrade`
- [ ] Verification passed: `railway run --service backend python verify_migrations.py`

### 5. Deploy Worker
- [ ] New service created: `celery-worker`
- [ ] Root directory set to `backend`
- [ ] Dockerfile path set to `Dockerfile.railway-worker`
- [ ] Environment variables copied from backend
- [ ] Worker deployed successfully
- [ ] Worker logs show "celery@hostname ready"

### 6. Verify Deployment
- [ ] Health check passes: `curl https://backend-url/api/v1/health`
- [ ] Database connection: `"database": "ok"`
- [ ] Redis connection: `"redis": "ok"`

## Environment Variables Template

Copy these to Railway backend + worker services:

```bash
# Required - Fill in your values
DATABASE_URL=postgresql://postgres:PASSWORD@db.PROJECT.supabase.co:5432/postgres
SECRET_KEY=generate-random-string-here
JWT_SECRET_KEY=different-random-string-here
GEMINI_API_KEY=your-gemini-api-key
GOOGLE_CLIENT_ID=your-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-secret
CORS_ORIGINS=https://your-frontend.com

# Optional - Use defaults or customize
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=5
DB_POOL_RECYCLE=3600
CELERY_CONCURRENCY=2
RATELIMIT_ENABLED=true
LOG_LEVEL=INFO
FLASK_ENV=production
```

## Post-Deployment Testing

- [ ] Create test user account (via frontend)
- [ ] Reserve credits: `POST /api/v1/credits/reserve`
- [ ] Upload small PDF: `POST /api/v1/process-pdf-async`
- [ ] Poll job status: `GET /api/v1/jobs/{job_id}`
- [ ] Verify job completes: `status: "completed"`
- [ ] Check worker logs for task execution
- [ ] Test job cancellation: `POST /api/v1/jobs/{job_id}/cancel`

## Troubleshooting

If something fails, check:

1. **Backend logs**: `railway logs --service backend`
2. **Worker logs**: `railway logs --service celery-worker`
3. **Database**: Run `verify_migrations.py`
4. **Health check**: Should return 200 with all checks "ok"

Common issues:
- "column does not exist" → Run migrations
- Worker connection error → Check REDIS_URL in worker env vars
- Job stuck → Restart worker service
- 503 health check → Check DATABASE_URL and REDIS_URL

## Success Criteria

You're done when:

✅ Health check returns `{"status": "healthy", "checks": {"database": "ok", "redis": "ok"}}`  
✅ Worker logs show "celery@hostname ready"  
✅ Async PDF upload returns 202 with job_id  
✅ Job status polling shows progress updates  
✅ Large PDF (50+ pages) completes without timeout  
✅ No errors in Railway logs for 5 minutes after test

---

**Estimated Time**: 15-30 minutes  
**Difficulty**: Intermediate

For detailed instructions, see [RAILWAY_DEPLOYMENT.md](./RAILWAY_DEPLOYMENT.md)

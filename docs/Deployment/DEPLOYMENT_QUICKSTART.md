# 🚀 Quick Deployment Guide

**Time to deploy: ~30 minutes**

This is a condensed version of the full [DEPLOYMENT.md](DEPLOYMENT.md) guide. Use this for quick reference during deployment.

## Prerequisites Check

- [ ] Vercel account
- [ ] Supabase account  
- [ ] Domain name with DNS access
- [ ] Google Cloud project with Gemini API + OAuth credentials
- [ ] Vercel CLI installed: `npm install -g vercel`

---

## 5-Step Deployment

### 1️⃣ Supabase Setup (5 min)

```bash
# Create project at https://supabase.com
# Get connection string from Settings → Database → Connection string (URI)
# Format: postgresql://postgres:[PASSWORD]@db.[REF].supabase.co:5432/postgres

# Run migrations
cd backend
export DATABASE_URL="postgresql://postgres:..."
pip install -r requirements.txt
flask db upgrade
```

### 2️⃣ Configure Environment (5 min)

**Backend** (`backend/.env.production`):
```bash
FLASK_ENV=production
SECRET_KEY=$(python -c "import secrets; print(secrets.token_hex(32))")
JWT_SECRET_KEY=$(python -c "import secrets; print(secrets.token_hex(32))")
DATABASE_URL=postgresql://postgres:...
GEMINI_API_KEY=your-gemini-key
GOOGLE_CLIENT_ID=your-client-id
GOOGLE_CLIENT_SECRET=your-client-secret
CORS_ORIGINS=https://frenchnoveltool.com
RATELIMIT_ENABLED=False
```

**Frontend** (`frontend/.env.production`):
```bash
NEXT_PUBLIC_API_BASE_URL=https://api.frenchnoveltool.com/api/v1
NEXT_PUBLIC_GOOGLE_CLIENT_ID=your-client-id
```

### 3️⃣ DNS Setup (2 min)

Add CNAME records to your domain:

| Type  | Name | Value                  |
|-------|------|------------------------|
| CNAME | @    | cname.vercel-dns.com   |
| CNAME | api  | cname.vercel-dns.com   |

### 4️⃣ Deploy Backend (5 min)

```bash
cd backend
vercel login
vercel --prod

# In Vercel dashboard:
# - Settings → Environment Variables → Add all from .env.production
# - Settings → Domains → Add api.frenchnoveltool.com
```

Test: `curl https://api.frenchnoveltool.com/api/v1/health`

### 5️⃣ Deploy Frontend (5 min)

```bash
cd frontend
vercel --prod

# In Vercel dashboard:
# - Settings → Environment Variables → Add all from .env.production
# - Settings → Domains → Add frenchnoveltool.com
```

Test: Open https://frenchnoveltool.com

---

## 6️⃣ Configure Google OAuth (5 min)

In [Google Cloud Console](https://console.cloud.google.com):

1. **APIs & Services** → **Credentials** → Your OAuth Client
2. Add **Authorized JavaScript origins**:
   ```
   https://frenchnoveltool.com
   ```
3. Add **Authorized redirect URIs**:
   ```
   https://frenchnoveltool.com
   https://frenchnoveltool.com/auth/callback
   https://api.frenchnoveltool.com/api/v1/auth/google/callback
   ```
4. **OAuth consent screen** → Add authorized domain:
   ```
   frenchnoveltool.com
   ```

---

## 7️⃣ Test Complete Workflow (5 min)

- [ ] Visit https://frenchnoveltool.com
- [ ] Login with Google
- [ ] Upload PDF
- [ ] Process document
- [ ] Edit a sentence
- [ ] Export to Google Sheets
- [ ] Verify in Google Drive

---

## Common Issues

| Issue | Solution |
|-------|----------|
| CORS errors | Update `CORS_ORIGINS` in backend Vercel env vars |
| OAuth fails | Check redirect URIs match exactly in Google Console |
| Database errors | Verify `DATABASE_URL` in Vercel env vars |
| Build fails | Check Vercel logs, ensure all dependencies in requirements.txt |

---

## Quick Commands

```bash
# Redeploy backend
cd backend && vercel --prod

# Redeploy frontend
cd frontend && vercel --prod

# Run new database migration
cd backend
export DATABASE_URL="postgresql://..."
flask db upgrade

# View Vercel logs
vercel logs [project-url]

# Test health
curl https://api.frenchnoveltool.com/api/v1/health
```

---

## Need More Details?

See additional documentation:
- 📘 [DEPLOYMENT.md](DEPLOYMENT.md) - Full deployment guide with troubleshooting
- 📋 [DEPLOYMENT_CHECKLIST.md](DEPLOYMENT_CHECKLIST.md) - Complete task checklist
- 🏗️ [DEPLOYMENT_ARCHITECTURE.md](DEPLOYMENT_ARCHITECTURE.md) - System architecture and diagrams

---

**Estimated total time: 30 minutes** (excluding DNS propagation)

🎉 **Ready to go live!**

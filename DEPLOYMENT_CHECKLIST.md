# 📋 Deployment Checklist: French Novel Tool

This checklist covers all necessary tasks to deploy the French Novel Tool with minimal configuration for a single user, using Vercel for hosting, Supabase for database, and the domain https://frenchnoveltool.com.

> **Quick Links:**
> - 📘 [Full Deployment Guide](DEPLOYMENT.md) - Comprehensive step-by-step instructions
> - ⚡ [Quick Start Guide](DEPLOYMENT_QUICKSTART.md) - 30-minute condensed version

---

## 1️⃣ Database Migration (Supabase Setup)

- [ ] Create a Supabase project at https://supabase.com
- [ ] Get PostgreSQL connection string from Supabase (Settings → Database → Connection string)
- [ ] Update local `.env` with `DATABASE_URL` 
- [ ] Install backend dependencies: `cd backend && pip install -r requirements.txt`
- [ ] Run database migrations:
  ```bash
  cd backend
  export DATABASE_URL=postgresql://postgres:...your-supabase-url...
  flask db upgrade
  ```
- [ ] Create database indexes for frequently queried fields (see DEPLOYMENT.md Step 1.4)
- [ ] Test database connection from local environment

## 2️⃣ Environment Configuration

- [ ] Create `.env.production` file for backend (use `backend/.env.production.example` as template):
  - [ ] Generate and set `SECRET_KEY` (use: `python -c "import secrets; print(secrets.token_hex(32))"`)
  - [ ] Generate and set `JWT_SECRET_KEY` (different from SECRET_KEY)
  - [ ] Set `DATABASE_URL` to your Supabase connection string
  - [ ] Set `GEMINI_API_KEY`
  - [ ] Set `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET`
  - [ ] Set `CORS_ORIGINS=https://frenchnoveltool.com`
  - [ ] Set `RATELIMIT_ENABLED=False` (single user deployment)
  
- [ ] Create `.env.production` file for frontend (use `frontend/.env.production.example` as template):
  - [ ] Set `NEXT_PUBLIC_API_BASE_URL=https://api.frenchnoveltool.com/api/v1`
  - [ ] Set `NEXT_PUBLIC_GOOGLE_CLIENT_ID` (must match backend)

## 3️⃣ Domain Setup

- [ ] Confirm ownership of frenchnoveltool.com
- [ ] Prepare DNS configuration for Vercel:
  - [ ] Add CNAME record: `@` → `cname.vercel-dns.com` (for frenchnoveltool.com)
  - [ ] Add CNAME record: `api` → `cname.vercel-dns.com` (for api.frenchnoveltool.com)
- [ ] Wait for DNS propagation (verify with `dig frenchnoveltool.com`)

## 4️⃣ Backend Deployment

- [ ] Install Vercel CLI: `npm install -g vercel`
- [ ] Login to Vercel: `vercel login`
- [ ] Deploy backend to Vercel:
  ```bash
  cd backend
  vercel --prod
  ```
- [ ] Add environment variables in Vercel project settings (Settings → Environment Variables):
  - [ ] Add all variables from `.env.production`
  - [ ] Verify `FLASK_ENV=production`
  - [ ] Verify `DATABASE_URL` is set correctly
- [ ] Configure custom domain in Vercel:
  - [ ] Go to Settings → Domains
  - [ ] Add `api.frenchnoveltool.com`
  - [ ] Wait for SSL certificate provisioning
- [ ] Test backend deployment: `curl https://api.frenchnoveltool.com/api/v1/health`

## 5️⃣ Frontend Deployment

- [ ] Deploy frontend to Vercel:
  ```bash
  cd frontend
  vercel --prod
  ```
- [ ] Add environment variables in Vercel project settings:
  - [ ] Add `NEXT_PUBLIC_API_BASE_URL`
  - [ ] Add `NEXT_PUBLIC_GOOGLE_CLIENT_ID`
- [ ] Configure custom domain in Vercel:
  - [ ] Go to Settings → Domains
  - [ ] Add `frenchnoveltool.com`
  - [ ] Optionally add `www.frenchnoveltool.com` (will redirect to root)
  - [ ] Wait for SSL certificate provisioning
- [ ] Test frontend deployment: Open https://frenchnoveltool.com

## 6️⃣ Google OAuth Configuration

- [ ] Update Google Cloud OAuth redirect URIs:
  - [ ] Go to [Google Cloud Console](https://console.cloud.google.com)
  - [ ] Navigate to APIs & Services → Credentials
  - [ ] Click on your OAuth 2.0 Client ID
  - [ ] Add Authorized JavaScript origins:
    - [ ] `https://frenchnoveltool.com`
  - [ ] Add Authorized redirect URIs:
    - [ ] `https://frenchnoveltool.com`
    - [ ] `https://frenchnoveltool.com/auth/callback`
    - [ ] `https://api.frenchnoveltool.com/api/v1/auth/google/callback`
- [ ] Update Google Cloud credentials:
  - [ ] Go to OAuth consent screen
  - [ ] Add `frenchnoveltool.com` to authorized domains
- [ ] Verify OAuth scopes include:
  - [ ] openid, email, profile
  - [ ] https://www.googleapis.com/auth/spreadsheets
  - [ ] https://www.googleapis.com/auth/drive.file

## 7️⃣ Security & Testing

- [ ] Verify CORS settings in backend allow only frenchnoveltool.com
- [ ] Test complete PDF upload workflow:
  - [ ] Login with Google account
  - [ ] Upload a test PDF file
  - [ ] Process document with default settings
  - [ ] Verify results display correctly
- [ ] Test Google OAuth login flow:
  - [ ] Logout
  - [ ] Login again
  - [ ] Verify session persistence
- [ ] Test Google Sheets export functionality:
  - [ ] Export results to Google Sheets
  - [ ] Verify sheet appears in Google Drive
  - [ ] Check formatting and data integrity
- [ ] Test inline editing:
  - [ ] Edit a sentence in results
  - [ ] Verify changes save
- [ ] Test history functionality:
  - [ ] View processed documents in history
  - [ ] Verify status indicators
- [ ] Verify rate limiting is disabled (check logs for no rate limit warnings)

## 8️⃣ Docker Configuration (Local Development)

- [ ] Updated `docker-compose.dev.yml` to use Supabase for local development:
  ```yml
  backend:
    environment:
      - DATABASE_URL=${DATABASE_URL:-sqlite:///app.db}
  ```
- [ ] Test local development with Supabase:
  ```bash
  # Set DATABASE_URL in backend/.env
  docker-compose -f docker-compose.dev.yml up
  ```

## 9️⃣ Post-Deployment

- [ ] Create client account in the application:
  - [ ] Login with client's Google account
  - [ ] Grant necessary permissions
- [ ] Verify all features work with the client account:
  - [ ] PDF upload ✓
  - [ ] Processing ✓
  - [ ] Editing ✓
  - [ ] Export to Sheets ✓
  - [ ] History ✓
- [ ] Set up monitoring:
  - [ ] Enable Vercel Analytics (optional)
  - [ ] Check Vercel logs periodically
- [ ] Configure Supabase backups:
  - [ ] Go to Supabase Dashboard → Database → Backups
  - [ ] Verify automatic backups are enabled (default: 7 days)
  - [ ] Optionally configure manual backup schedule

## 🔟 Documentation

- [ ] Review user documentation:
  - [ ] [README.md](README.md) - Project overview
  - [ ] [API Documentation](backend/API_DOCUMENTATION.md) - API reference
- [ ] Document deployment architecture:
  - [ ] Frontend: Vercel (frenchnoveltool.com)
  - [ ] Backend: Vercel (api.frenchnoveltool.com)
  - [ ] Database: Supabase (PostgreSQL)
- [ ] Document update process:
  - [ ] Backend updates: `cd backend && vercel --prod`
  - [ ] Frontend updates: `cd frontend && vercel --prod`
  - [ ] Database migrations: See DEPLOYMENT.md "Database Migrations" section

---

## ✅ Priority Tasks (If Time Constrained)

Focus on these critical tasks first:

1. ✅ Supabase database setup and migration
2. ✅ Backend deployment with proper environment variables
3. ✅ Frontend deployment with proper API URL configuration
4. ✅ Google OAuth configuration update for new domain
5. ✅ Testing the complete workflow with a real PDF

---

## 📚 Additional Resources

- 📘 [Full Deployment Guide](DEPLOYMENT.md) - Complete step-by-step instructions with troubleshooting
- ⚡ [Quick Start Guide](DEPLOYMENT_QUICKSTART.md) - 30-minute condensed deployment
- 🏗️ [Deployment Architecture](DEPLOYMENT_ARCHITECTURE.md) - Architecture diagrams and system overview
- 🔧 [Configuration Guide](README.md#-configuration) - Environment variables reference
- 🤝 [Contributing Guide](CONTRIBUTING.md) - Development setup
- 📖 [API Documentation](backend/API_DOCUMENTATION.md) - Complete API reference

---

## 🆘 Troubleshooting

If you encounter issues during deployment, refer to the [Troubleshooting section](DEPLOYMENT.md#troubleshooting) in the full deployment guide, which covers:

- Database connection errors
- Vercel deployment failures
- CORS errors
- OAuth login failures
- Environment variable issues

---

## ✨ Deployment Complete!

Once all items are checked off, your French Novel Tool should be live and fully functional at https://frenchnoveltool.com!

**Need help?** Refer to:
- [DEPLOYMENT.md](DEPLOYMENT.md) for detailed instructions
- [DEPLOYMENT_QUICKSTART.md](DEPLOYMENT_QUICKSTART.md) for quick reference
- Vercel dashboard logs for runtime errors
- Supabase dashboard logs for database issues

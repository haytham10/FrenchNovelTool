# 🚀 Deployment Guide for French Novel Tool

This guide covers the complete deployment process for the French Novel Tool using Vercel for hosting and Supabase for the database.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Database Setup (Supabase)](#1-database-setup-supabase)
3. [Environment Configuration](#2-environment-configuration)
4. [Domain Setup](#3-domain-setup)
5. [Backend Deployment](#4-backend-deployment)
6. [Frontend Deployment](#5-frontend-deployment)
7. [Google OAuth Configuration](#6-google-oauth-configuration)
8. [Post-Deployment Testing](#7-post-deployment-testing)
9. [Local Development with Supabase](#8-local-development-with-supabase)
10. [Troubleshooting](#troubleshooting)

---

## Prerequisites

Before starting, ensure you have:

- [ ] A Vercel account (https://vercel.com)
- [ ] A Supabase account (https://supabase.com)
- [ ] Domain name (e.g., frenchnoveltool.com) with DNS access
- [ ] Google Cloud project with:
  - Gemini API enabled
  - OAuth 2.0 credentials configured
  - Drive & Sheets API enabled
- [ ] Vercel CLI installed: `npm install -g vercel`

---

## 1️⃣ Database Setup (Supabase)

### Step 1: Create Supabase Project

1. Go to https://supabase.com and sign in
2. Click "New Project"
3. Fill in project details:
   - **Name**: french-novel-tool
   - **Database Password**: (generate a strong password and save it securely)
   - **Region**: Choose closest to your users
   - **Pricing Plan**: Free tier is sufficient for single-user deployment

### Step 2: Get Database Connection String

1. In your Supabase project, go to **Settings** → **Database**
2. Scroll to **Connection string** section
3. Select **URI** tab
4. Copy the connection string - it looks like:
   ```
   postgresql://postgres:[YOUR-PASSWORD]@db.[YOUR-PROJECT-REF].supabase.co:5432/postgres
   ```
5. Replace `[YOUR-PASSWORD]` with your actual database password
6. Save this connection string - you'll need it for deployment

### Step 3: Run Database Migrations

From your local environment:

```bash
cd backend

# Set database URL
export DATABASE_URL="postgresql://postgres:[YOUR-PASSWORD]@db.[YOUR-PROJECT-REF].supabase.co:5432/postgres"

# Install dependencies if not already installed
pip install -r requirements.txt

# Run migrations
flask db upgrade
```

### Step 4: Create Database Indexes (Optional, for performance)

Connect to your Supabase database and run:

```sql
-- Index for user email lookups
CREATE INDEX IF NOT EXISTS idx_user_email ON "user"(email);

-- Index for history queries by user
CREATE INDEX IF NOT EXISTS idx_history_user_id ON history(user_id);

-- Index for history queries by creation date
CREATE INDEX IF NOT EXISTS idx_history_created_at ON history(created_at DESC);
```

You can run these in the Supabase SQL Editor:
1. Go to **SQL Editor** in your Supabase dashboard
2. Create a new query
3. Paste the SQL above
4. Click **Run**

### Step 5: Verify Database Connection

Test the connection from your local machine:

```bash
cd backend
python -c "from app import create_app, db; app = create_app(); app.app_context().push(); print('Connection successful!')"
```

---

## 2️⃣ Environment Configuration

### Backend Environment Variables

1. Copy the production template:
   ```bash
   cd backend
   cp .env.production.example .env.production
   ```

2. Edit `.env.production` with your values:
   ```bash
   # Generate secure keys
   SECRET_KEY=$(python -c "import secrets; print(secrets.token_hex(32))")
   JWT_SECRET_KEY=$(python -c "import secrets; print(secrets.token_hex(32))")
   
   # Edit the file
   nano .env.production
   ```

3. Required values to update:
   - `SECRET_KEY` - Generate a secure random string
   - `JWT_SECRET_KEY` - Generate another secure random string (different from SECRET_KEY)
   - `DATABASE_URL` - Your Supabase connection string from Step 1
   - `GEMINI_API_KEY` - Your Google Gemini API key
   - `GOOGLE_CLIENT_ID` - Your Google OAuth client ID
   - `GOOGLE_CLIENT_SECRET` - Your Google OAuth client secret
   - `CORS_ORIGINS` - Set to `https://frenchnoveltool.com`

### Frontend Environment Variables

1. Copy the production template:
   ```bash
   cd frontend
   cp .env.production.example .env.production
   ```

2. Edit `.env.production`:
   ```bash
   NEXT_PUBLIC_API_BASE_URL=https://api.frenchnoveltool.com/api/v1
   NEXT_PUBLIC_GOOGLE_CLIENT_ID=your-google-client-id.apps.googleusercontent.com
   ```

---

## 3️⃣ Domain Setup

### DNS Configuration

Configure your domain DNS with these records:

1. **Root domain** (frenchnoveltool.com):
   - Type: `CNAME`
   - Name: `@` or leave blank
   - Value: `cname.vercel-dns.com`
   
2. **API subdomain** (api.frenchnoveltool.com):
   - Type: `CNAME`
   - Name: `api`
   - Value: `cname.vercel-dns.com`

**Note**: DNS propagation can take up to 48 hours but usually completes within a few minutes.

### Verify DNS Configuration

```bash
# Check root domain
dig frenchnoveltool.com

# Check API subdomain
dig api.frenchnoveltool.com
```

---

## 4️⃣ Backend Deployment

### Step 1: Login to Vercel

```bash
vercel login
```

### Step 2: Deploy Backend

```bash
cd backend

# Deploy to production
vercel --prod

# When prompted:
# - Set up and deploy? Yes
# - Which scope? (Select your account)
# - Link to existing project? No
# - What's your project's name? french-novel-backend
# - In which directory is your code located? ./
```

### Step 3: Add Environment Variables in Vercel

Go to your Vercel project dashboard:

1. Navigate to **Settings** → **Environment Variables**
2. Add all variables from your `.env.production` file:

   ```
   FLASK_ENV=production
   SECRET_KEY=your-production-secret-key
   JWT_SECRET_KEY=your-jwt-secret-key
   DATABASE_URL=postgresql://postgres:...
   GEMINI_API_KEY=your-gemini-api-key
   GOOGLE_CLIENT_ID=your-google-client-id
   GOOGLE_CLIENT_SECRET=your-google-client-secret
   CORS_ORIGINS=https://frenchnoveltool.com
   LOG_LEVEL=INFO
   RATELIMIT_ENABLED=False
   ```

3. Click **Save**

### Step 4: Configure Custom Domain

1. In Vercel project dashboard, go to **Settings** → **Domains**
2. Add domain: `api.frenchnoveltool.com`
3. Vercel will verify DNS configuration
4. Wait for SSL certificate to be issued (usually 1-2 minutes)

### Step 5: Verify Backend Deployment

```bash
curl https://api.frenchnoveltool.com/api/v1/health
```

Expected response:
```json
{"status": "ok"}
```

---

## 5️⃣ Frontend Deployment

### Step 1: Deploy Frontend

```bash
cd frontend

# Deploy to production
vercel --prod

# When prompted:
# - Set up and deploy? Yes
# - Which scope? (Select your account)
# - Link to existing project? No
# - What's your project's name? french-novel-frontend
# - In which directory is your code located? ./
```

### Step 2: Add Environment Variables in Vercel

Go to your frontend Vercel project dashboard:

1. Navigate to **Settings** → **Environment Variables**
2. Add:
   ```
   NEXT_PUBLIC_API_BASE_URL=https://api.frenchnoveltool.com/api/v1
   NEXT_PUBLIC_GOOGLE_CLIENT_ID=your-google-client-id.apps.googleusercontent.com
   ```

3. Click **Save**
4. Trigger a redeploy: **Deployments** → **Redeploy** (latest deployment)

### Step 3: Configure Custom Domain

1. In Vercel project dashboard, go to **Settings** → **Domains**
2. Add domain: `frenchnoveltool.com`
3. Optionally add: `www.frenchnoveltool.com` (will redirect to root domain)
4. Vercel will verify DNS configuration
5. Wait for SSL certificate to be issued

### Step 4: Verify Frontend Deployment

Open https://frenchnoveltool.com in your browser

---

## 6️⃣ Google OAuth Configuration

### Step 1: Update OAuth Redirect URIs

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Select your project
3. Navigate to **APIs & Services** → **Credentials**
4. Click on your OAuth 2.0 Client ID
5. Add Authorized JavaScript origins:
   ```
   https://frenchnoveltool.com
   ```

6. Add Authorized redirect URIs:
   ```
   https://frenchnoveltool.com
   https://frenchnoveltool.com/auth/callback
   https://api.frenchnoveltool.com/api/v1/auth/google/callback
   ```

7. Click **Save**

### Step 2: Update OAuth Consent Screen

1. Go to **OAuth consent screen**
2. Under **Authorized domains**, add:
   ```
   frenchnoveltool.com
   ```

3. Click **Save**

### Step 3: Verify OAuth Scopes

Ensure these scopes are requested:
- `openid`
- `email`
- `profile`
- `https://www.googleapis.com/auth/spreadsheets`
- `https://www.googleapis.com/auth/drive.file`

---

## 7️⃣ Post-Deployment Testing

### Test Checklist

Run through this checklist to verify everything works:

- [ ] **Homepage loads**: Visit https://frenchnoveltool.com
- [ ] **Google OAuth login**: Click login and authenticate
- [ ] **Upload PDF**: Upload a sample French novel PDF
- [ ] **Process document**: Start processing and verify results
- [ ] **Edit sentences**: Test inline editing functionality
- [ ] **Export to Sheets**: Create a new Google Sheet with results
- [ ] **View history**: Check that document appears in history
- [ ] **Settings**: Adjust sentence length settings
- [ ] **Logout/Login**: Verify session persistence

### Test a Complete Workflow

1. **Login** with Google account
2. **Upload** a test PDF file
3. **Process** the document with default settings
4. **Edit** a sentence in the results
5. **Export** to Google Sheets
6. **Verify** the export appears in Google Drive
7. **Check history** shows the processed document

### Performance Testing

```bash
# Test API response time
time curl https://api.frenchnoveltool.com/api/v1/health

# Should respond in < 500ms
```

### Error Monitoring

Check Vercel logs for any errors:

1. Go to Vercel dashboard
2. Select your project (backend or frontend)
3. Click **Logs** tab
4. Monitor for errors during testing

---

## 8️⃣ Local Development with Supabase

### Using Docker Compose with Supabase

Update your local `.env` file in the backend directory:

```bash
cd backend
cp .env.example .env
nano .env
```

Set `DATABASE_URL` to your Supabase connection string:

```bash
DATABASE_URL=postgresql://postgres:[PASSWORD]@db.[PROJECT-REF].supabase.co:5432/postgres
```

Run with Docker Compose:

```bash
cd ..  # Back to project root
docker-compose -f docker-compose.dev.yml up
```

The compose file will use the `DATABASE_URL` from your `.env` file.

### Manual Local Development

```bash
# Backend
cd backend
source .venv/bin/activate  # Or .venv\Scripts\activate on Windows
export DATABASE_URL="postgresql://postgres:[PASSWORD]@db.[PROJECT-REF].supabase.co:5432/postgres"
flask --app run.py run

# Frontend (in another terminal)
cd frontend
npm run dev
```

---

## 🔟 Troubleshooting

### Common Issues

#### 1. Database Connection Errors

**Error**: `could not connect to server`

**Solutions**:
- Verify your Supabase project is active
- Check DATABASE_URL is correct
- Ensure password has no special characters that need URL encoding
- Verify your IP is not blocked by Supabase (they allow all by default)

#### 2. Vercel Deployment Fails

**Error**: Build fails on Vercel

**Solutions**:
- Check build logs in Vercel dashboard
- Ensure all environment variables are set
- Verify `vercel.json` is in the correct directory
- For backend: Ensure `run.py` exists and is correct

#### 3. CORS Errors

**Error**: `Access-Control-Allow-Origin` errors in browser console

**Solutions**:
- Verify `CORS_ORIGINS` environment variable in backend includes your frontend domain
- Ensure it's set to `https://frenchnoveltool.com` (no trailing slash)
- Redeploy backend after updating environment variables

#### 4. OAuth Login Fails

**Error**: "redirect_uri_mismatch" or "invalid_client"

**Solutions**:
- Verify redirect URIs in Google Cloud Console match exactly
- Ensure `GOOGLE_CLIENT_ID` is the same in both backend and frontend
- Check that domain is added to authorized domains in OAuth consent screen

#### 5. Database Migrations Don't Run

**Error**: Tables don't exist

**Solutions**:
```bash
# Run migrations manually
cd backend
export DATABASE_URL="your-supabase-url"
flask db upgrade
```

#### 6. Environment Variables Not Loading

**Error**: Application can't find config values

**Solutions**:
- In Vercel: Go to Settings → Environment Variables and verify all are set
- After adding/updating environment variables, trigger a new deployment
- For local development: Ensure `.env` file exists and is loaded

### Getting Help

If you encounter issues not covered here:

1. Check Vercel logs (Dashboard → Logs)
2. Check Supabase logs (Dashboard → Logs)
3. Review browser console for frontend errors
4. Check backend logs in Vercel

### Health Check Endpoints

Use these endpoints to diagnose issues:

```bash
# Backend health check
curl https://api.frenchnoveltool.com/api/v1/health

# Test database connection (after implementing health check endpoint)
curl https://api.frenchnoveltool.com/api/v1/health/db
```

---

## 📊 Monitoring & Maintenance

### Vercel Analytics

Enable Vercel Analytics for basic monitoring:

1. Go to your Vercel project
2. Navigate to **Analytics** tab
3. Enable analytics (free tier available)

### Database Backups

Supabase automatically backs up your database:

1. Go to your Supabase project
2. Navigate to **Database** → **Backups**
3. Configure backup retention (free tier: 7 days)

### Manual Database Backup

```bash
# Export database
pg_dump "postgresql://postgres:[PASSWORD]@db.[PROJECT-REF].supabase.co:5432/postgres" > backup.sql

# Restore from backup
psql "postgresql://postgres:[PASSWORD]@db.[PROJECT-REF].supabase.co:5432/postgres" < backup.sql
```

---

## 🔄 Updating the Application

### Deploy Backend Updates

```bash
cd backend
git pull origin main
vercel --prod
```

### Deploy Frontend Updates

```bash
cd frontend
git pull origin main
vercel --prod
```

### Database Migrations

When adding new database changes:

```bash
cd backend
export DATABASE_URL="your-supabase-url"

# Create migration
flask db migrate -m "Description of changes"

# Review migration file
cat migrations/versions/[latest].py

# Apply migration
flask db upgrade
```

---

## 📝 Production Checklist

Before going live, ensure:

- [ ] All environment variables are set in Vercel
- [ ] Database migrations have run successfully
- [ ] Custom domains are configured with SSL
- [ ] Google OAuth is properly configured
- [ ] CORS settings allow only your domain
- [ ] Rate limiting is disabled (single user deployment)
- [ ] All tests pass
- [ ] Client account can login and use all features
- [ ] Google Sheets export works
- [ ] PDF upload and processing works
- [ ] Error logging is working
- [ ] Backups are configured

---

## 🎉 You're Done!

Your French Novel Tool should now be live at https://frenchnoveltool.com!

For questions or issues, refer to:
- [API Documentation](backend/API_DOCUMENTATION.md)
- [Contributing Guide](CONTRIBUTING.md)
- [README](README.md)

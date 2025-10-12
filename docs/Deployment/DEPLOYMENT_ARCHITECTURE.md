# 🏗️ Deployment Architecture

This document provides a visual overview of the French Novel Tool deployment architecture.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         USERS / CLIENT                           │
│                    (Single User Access)                          │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             │ HTTPS
                             │
                    ┌────────▼─────────┐
                    │  Domain Names    │
                    │  ─────────────   │
                    │  frenchnoveltool │
                    │     .com         │
                    │  api.frenchnovel │
                    │     tool.com     │
                    └────────┬─────────┘
                             │
            ┌────────────────┴────────────────┐
            │                                  │
            │                                  │
    ┌───────▼────────┐              ┌─────────▼─────────┐
    │   FRONTEND     │              │     BACKEND       │
    │   (Next.js)    │──────────────│    (Flask)        │
    │                │     API      │                   │
    │  Vercel        │    Calls     │   Vercel          │
    │  Serverless    │              │   Serverless      │
    │                │              │   Python          │
    └────────────────┘              └─────────┬─────────┘
                                              │
                                              │
                            ┌─────────────────┼─────────────────┐
                            │                 │                 │
                    ┌───────▼────────┐ ┌──────▼──────┐ ┌───────▼────────┐
                    │   DATABASE     │ │   GEMINI    │ │  GOOGLE APIS   │
                    │  (PostgreSQL)  │ │     AI      │ │  Sheets/Drive  │
                    │                │ │             │ │                │
                    │   Supabase     │ │  Google     │ │   OAuth 2.0    │
                    │   Managed      │ │  Cloud      │ │   Integration  │
                    └────────────────┘ └─────────────┘ └────────────────┘
```

## Component Details

### Frontend (frenchnoveltool.com)
- **Technology**: Next.js 15 (React 19)
- **Hosting**: Vercel Serverless
- **Features**:
  - Material-UI v7 components
  - Dark/light theme support
  - Responsive design
  - Google OAuth integration
  - PDF upload interface
  - Results editing and export

### Backend (api.frenchnoveltool.com)
- **Technology**: Flask 3.0
- **Hosting**: Vercel Serverless (Python)
- **Features**:
  - RESTful API (v1)
  - JWT authentication
  - PDF processing
  - Google Sheets export
  - User settings management
  - Rate limiting (disabled for single-user)

### Database (Supabase)
- **Technology**: PostgreSQL
- **Managed by**: Supabase
- **Features**:
  - User authentication data
  - Document processing history
  - User settings
  - OAuth tokens
  - Automatic backups

### External Services
- **Google Gemini AI**: Sentence normalization
- **Google Sheets API**: Export functionality
- **Google Drive API**: File organization
- **Google OAuth 2.0**: User authentication

## Data Flow

### 1. User Authentication
```
User → Frontend → Google OAuth → Backend → Database
                                    ↓
                              Generate JWT
                                    ↓
                              Frontend (store token)
```

### 2. PDF Processing
```
User uploads PDF → Frontend → Backend
                               ↓
                        Extract text
                               ↓
                        Gemini AI (normalize)
                               ↓
                        Save to Database
                               ↓
                        Return results → Frontend
```

### 3. Google Sheets Export
```
User requests export → Frontend → Backend
                                   ↓
                          Get OAuth tokens (Database)
                                   ↓
                          Google Sheets API
                                   ↓
                          Create spreadsheet
                                   ↓
                          Return sheet URL → Frontend
```

## Security Features

### Network Security
- ✅ HTTPS everywhere (SSL/TLS)
- ✅ CORS restricted to production domain
- ✅ Security headers (CSP, X-Frame-Options, etc.)

### Application Security
- ✅ JWT token-based authentication
- ✅ OAuth 2.0 for Google services
- ✅ Input validation and sanitization
- ✅ File size and type restrictions
- ✅ Rate limiting (optional, disabled for single-user)

### Data Security
- ✅ PostgreSQL with Supabase security
- ✅ Encrypted connections to database
- ✅ OAuth tokens stored encrypted
- ✅ Automatic database backups

## Scalability Notes

### Current Configuration (Single User)
- Rate limiting: **Disabled**
- Database connections: **Minimal**
- Serverless: **Auto-scales as needed**

### Future Scaling (If Needed)
To support multiple users:
1. Enable rate limiting in backend
2. Add Redis for distributed rate limiting
3. Implement user quotas
4. Add monitoring and analytics
5. Consider CDN for static assets

## Environment Variables

### Backend (.env.production)
```env
FLASK_ENV=production
SECRET_KEY=<generated>
JWT_SECRET_KEY=<generated>
DATABASE_URL=postgresql://...
GEMINI_API_KEY=<google-api-key>
GOOGLE_CLIENT_ID=<oauth-client-id>
GOOGLE_CLIENT_SECRET=<oauth-secret>
CORS_ORIGINS=https://frenchnoveltool.com
RATELIMIT_ENABLED=False
```

### Frontend (.env.production)
```env
NEXT_PUBLIC_API_BASE_URL=https://api.frenchnoveltool.com/api/v1
NEXT_PUBLIC_GOOGLE_CLIENT_ID=<oauth-client-id>
```

## Deployment Workflow

```
┌──────────────┐
│  Developer   │
└──────┬───────┘
       │
       │ git push
       │
┌──────▼───────┐
│   GitHub     │
└──────┬───────┘
       │
       │ Manual deploy
       │
┌──────▼───────┐
│  Vercel CLI  │
│              │
│ vercel --prod│
└──────┬───────┘
       │
   ┌───┴────┐
   │        │
┌──▼───┐ ┌──▼───┐
│Front │ │Back  │
│end   │ │end   │
└──────┘ └──────┘
```

## Monitoring & Logs

### Vercel Dashboard
- View deployment logs
- Monitor function execution
- Track error rates
- View analytics (optional)

### Supabase Dashboard
- Monitor database performance
- View query logs
- Check connection pool
- Manage backups

## Cost Estimate (Monthly)

For single-user deployment:

| Service | Plan | Cost |
|---------|------|------|
| Vercel (Frontend) | Hobby | **$0** |
| Vercel (Backend) | Hobby | **$0** |
| Supabase | Free Tier | **$0** |
| Domain | Annual | ~$12/year |
| Google APIs | Usage-based | ~$0* |

**Total: ~$1/month** (domain only)

*Google API costs are minimal for single-user usage with free tier quotas.

### Potential Upgrades

If you need more resources:
- Vercel Pro: $20/month (more bandwidth, advanced features)
- Supabase Pro: $25/month (more storage, compute)
- Google Cloud: Pay-as-you-go for API usage

## Backup & Disaster Recovery

### Database Backups
- **Automatic**: Supabase (7 days retention on free tier)
- **Manual**: Export via `pg_dump` (see DEPLOYMENT.md)

### Application Recovery
- **Frontend**: Redeploy from Git via Vercel
- **Backend**: Redeploy from Git via Vercel
- **Database**: Restore from Supabase backup

### Recovery Time Objective (RTO)
- Frontend/Backend: ~5 minutes (redeploy)
- Database: ~10-30 minutes (restore from backup)

## Performance Characteristics

### Response Times (Expected)
- Frontend page load: < 2 seconds
- API health check: < 200ms
- PDF upload: < 1 second
- PDF processing: 30-120 seconds (depends on size)
- Sheets export: 3-10 seconds

### Limits (Vercel Free Tier)
- Function execution: 10 seconds max
- Function size: 50 MB
- Bandwidth: 100 GB/month
- Invocations: Unlimited

### Limits (Supabase Free Tier)
- Database size: 500 MB
- Bandwidth: 5 GB
- API requests: Unlimited
- Connection pooling: 60 connections

## Support & Maintenance

### Regular Tasks
- [ ] Monitor Vercel logs weekly
- [ ] Check Supabase backups monthly
- [ ] Review Google API usage monthly
- [ ] Update dependencies quarterly
- [ ] Renew domain annually

### Emergency Contacts
- Vercel Support: https://vercel.com/support
- Supabase Support: https://supabase.com/support
- Google Cloud Support: https://cloud.google.com/support

---

## Related Documentation

- 📘 [Full Deployment Guide](DEPLOYMENT.md)
- ⚡ [Quick Start Guide](DEPLOYMENT_QUICKSTART.md)
- 📋 [Deployment Checklist](DEPLOYMENT_CHECKLIST.md)
- 📖 [README](README.md)
- 🔧 [API Documentation](backend/API_DOCUMENTATION.md)

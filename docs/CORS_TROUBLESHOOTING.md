# CORS Troubleshooting Guide

## Common CORS Errors and Solutions

### Error: "Response to preflight request doesn't pass access control check"

**Symptoms:**
```
Access to XMLHttpRequest at 'https://api.frenchnoveltool.com/api/v1/jobs/confirm' 
from origin 'https://www.frenchnoveltool.com' has been blocked by CORS policy: 
Response to preflight request doesn't pass access control check: 
It does not have HTTP ok status.
```

**Root Cause:**
The frontend origin is not in the backend's `CORS_ORIGINS` whitelist, OR Flask-Limiter is blocking OPTIONS preflight requests.

**Common Causes:**
1. Missing frontend origin in `CORS_ORIGINS` environment variable
2. **Flask-Limiter blocking OPTIONS requests** (most common with correct CORS config)
3. Incorrect protocol (http vs https) or subdomain mismatch

**Solution:**

**A. If Origins Are Correctly Set (Most Common Issue):**

The issue is that `@jwt_required()` and `@limiter.limit()` decorators are blocking OPTIONS preflight requests. This is fixed in `backend/app/__init__.py`:

```python
# 1. Exempt OPTIONS from rate limiting
def _get_remote_address_for_limiter():
    """Exempt OPTIONS requests from rate limiting"""
    from flask import request
    if request.method == 'OPTIONS':
        return '__OPTIONS_EXEMPT__'
    return get_remote_address()

limiter = Limiter(
    key_func=_get_remote_address_for_limiter,
    default_limits=[]
)

# 2. Handle OPTIONS requests globally (bypass all decorators)
@app.before_request
def handle_preflight():
    from flask import request, make_response
    if request.method == 'OPTIONS':
        # Return 200 OK for all OPTIONS requests
        # Flask-CORS will add the appropriate headers
        response = make_response('', 200)
        return response
```

**After deploying this fix, restart your Railway backend service.**

---

**B. If Origins Are Missing:**

1. **Update Railway Backend Service Environment Variables:**
   ```bash
   CORS_ORIGINS=https://www.frenchnoveltool.com,https://frenchnoveltool.com,http://localhost:3000,http://127.0.0.1:3000
   ```

2. **Restart the Backend Service** (Railway auto-restarts on env var changes)

3. **Verify the Fix:**
   - Open browser DevTools → Network tab
   - Trigger the request again
   - Check the preflight OPTIONS request response headers:
     ```
     Access-Control-Allow-Origin: https://www.frenchnoveltool.com
     Access-Control-Allow-Credentials: true
     ```

---

## CORS Configuration Architecture

### Backend (Flask-CORS)

**Location:** `backend/app/__init__.py`

```python
# Origins are parsed from CORS_ORIGINS environment variable
origins = [origin.strip() for origin in origins_config.split(',') if origin.strip()]

# Applied to both Flask-CORS and Socket.IO
CORS(app, origins=origins, supports_credentials=True)
socketio.init_app(app, cors_allowed_origins=origins)
```

**Environment Variable Format:**
```bash
# Comma-separated list of allowed origins
CORS_ORIGINS=https://www.example.com,https://example.com,http://localhost:3000
```

---

## Preflight Request Flow

1. **Browser Sends OPTIONS Request:**
   ```
   OPTIONS /api/v1/jobs/confirm HTTP/1.1
   Origin: https://www.frenchnoveltool.com
   Access-Control-Request-Method: POST
   Access-Control-Request-Headers: authorization,content-type
   ```

2. **Backend Checks Origin:**
   - If origin is in `CORS_ORIGINS` → Return 200 OK with CORS headers
   - If origin is NOT in `CORS_ORIGINS` → Return 403/500 (preflight fails)

3. **Browser Evaluates Response:**
   - If preflight succeeds (200 OK + valid headers) → Send actual POST request
   - If preflight fails → Block request and show CORS error

4. **Actual Request (if preflight succeeds):**
   ```
   POST /api/v1/jobs/confirm HTTP/1.1
   Origin: https://www.frenchnoveltool.com
   Authorization: Bearer <token>
   Content-Type: application/json
   ```

---

## Common Mistakes

### ❌ Rate Limiter Blocks OPTIONS Requests
```python
# WRONG - rate limiter blocks preflight requests
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[]
)
```

### ✅ Exempt OPTIONS from Rate Limiting
```python
# CORRECT - OPTIONS requests bypass rate limiter
def _get_remote_address_for_limiter():
    if request.method == 'OPTIONS':
        return None  # Exempt OPTIONS
    return get_remote_address()

limiter = Limiter(
    key_func=_get_remote_address_for_limiter,
    default_limits=[]
)
```

---

### ❌ Using Wildcard with Credentials
```python
# WRONG - doesn't work with credentials
CORS(app, origins='*', supports_credentials=True)
```

### ✅ Correct Configuration
```python
# CORRECT - explicit origins list
CORS(app, origins=['https://www.example.com'], supports_credentials=True)
```

---

### ❌ Missing www or Protocol
```bash
# WRONG - mismatched origins
CORS_ORIGINS=example.com                    # Missing protocol
CORS_ORIGINS=http://www.example.com         # Wrong protocol (http vs https)
CORS_ORIGINS=https://example.com            # Missing www subdomain
```

### ✅ Correct Origins
```bash
# CORRECT - include all variations
CORS_ORIGINS=https://www.example.com,https://example.com
```

---

### ❌ Adding Origins After Route Handlers
```python
# WRONG - CORS middleware must be initialized before routes
app.register_blueprint(routes_bp)
CORS(app, origins=origins)  # Too late!
```

### ✅ Correct Order
```python
# CORRECT - CORS before blueprints
CORS(app, origins=origins, supports_credentials=True)
app.register_blueprint(routes_bp)
```

---

## Debugging CORS Issues

### 1. Check Backend Logs
```bash
# Railway logs will show CORS rejections
2025-01-10 10:30:15 WARNING: CORS origin 'https://www.example.com' not in allowed origins
```

### 2. Inspect Preflight Request
In browser DevTools → Network tab:
- Find the OPTIONS request with the same URL as your failed request
- Check the **Response Headers** section:
  - Should include `Access-Control-Allow-Origin`
  - Should include `Access-Control-Allow-Credentials: true`

### 3. Verify Environment Variable
```bash
# In Railway service shell
echo $CORS_ORIGINS
# Should output: https://www.frenchnoveltool.com,https://frenchnoveltool.com,...
```

### 4. Test with cURL
```bash
# Simulate preflight request
curl -X OPTIONS \
  https://api.frenchnoveltool.com/api/v1/jobs/confirm \
  -H "Origin: https://www.frenchnoveltool.com" \
  -H "Access-Control-Request-Method: POST" \
  -H "Access-Control-Request-Headers: authorization,content-type" \
  -v
```

Look for `< Access-Control-Allow-Origin:` in the response headers.

---

## Production Checklist

- [ ] `CORS_ORIGINS` includes production frontend URL (with and without www)
- [ ] `CORS_ORIGINS` includes development URLs for local testing
- [ ] Backend service restarted after environment variable update
- [ ] Browser cache cleared (or test in incognito mode)
- [ ] Preflight OPTIONS request returns 200 OK
- [ ] Actual request includes `Authorization` header
- [ ] Response includes `Access-Control-Allow-Origin` matching the request origin

---

## Related Files

- **CORS Configuration:** `backend/app/__init__.py`
- **Environment Config:** `backend/config.py`
- **Railway Template:** `RAILWAY_ENV_TEMPLATE.md`
- **Frontend API Client:** `frontend/src/lib/api.ts`

---

## Additional Resources

- [MDN: CORS](https://developer.mozilla.org/en-US/docs/Web/HTTP/CORS)
- [Flask-CORS Documentation](https://flask-cors.readthedocs.io/)
- [Understanding Preflight Requests](https://developer.mozilla.org/en-US/docs/Glossary/Preflight_request)

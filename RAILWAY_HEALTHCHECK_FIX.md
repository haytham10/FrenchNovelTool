# Railway Healthcheck Fix - Global Wordlist Feature

## Problem Identified

The Railway backend service was failing healthchecks during deployment. The root causes were:

1. **Logging Permission Error**: The app tried to write logs to `/tmp/app.log`, but the non-root user (`appuser`) in the Docker container lacked permissions.
2. **Background Thread Context Error**: The global wordlist initializer ran in a background thread without a Flask application context, causing it to crash when trying to use `app.logger` or access the database.

## Fixes Applied

### 1. Fixed Logging Path (`backend/app/__init__.py`)

**Changed**: Logging now writes to `/app/logs/app.log` instead of `/tmp/app.log`.

```python
def configure_logging(app):
    """Configure application logging"""
    if not app.debug and not app.testing:
        # The Dockerfile creates /app/logs and chowns it to appuser.
        # This path is guaranteed to be writable.
        log_dir = '/app/logs'
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        
        log_file = os.path.join(log_dir, 'app.log')
        # ... rest of logging config
```

**Why**: The Dockerfile already creates `/app/logs` and sets proper ownership for `appuser`.

### 2. Added `skip_logging` Parameter (`backend/app/__init__.py`)

**Changed**: The `create_app()` factory now accepts an optional `skip_logging=False` parameter.

```python
def create_app(config_class=Config, skip_logging=False):
    # ...
    if not skip_logging:
        configure_logging(app)
```

**Why**: Scripts (like the seed script) can now create an app instance without needing file-based logging, avoiding permission issues.

### 3. Fixed Background Thread App Context (`backend/app/__init__.py`)

**Changed**: The `initialize_global_wordlist()` function now wraps all operations in `with app.app_context()`.

```python
def initialize_global_wordlist(app):
    """
    Ensure global default wordlist exists on app startup.
    This is idempotent and safe to run on every startup.
    
    NOTE: This runs in a background thread, so it needs an app context.
    """
    with app.app_context():
        try:
            from app.services.global_wordlist_manager import GlobalWordlistManager
            
            # This will create the wordlist if it doesn't exist
            wordlist = GlobalWordlistManager.ensure_global_default_exists()
            # ... rest of function
```

**Why**: Background threads in Flask need an explicit application context to access `app.logger`, the database (`db.session`), and other Flask extensions.

### 4. Updated Seed Script (`backend/scripts/seed_global_wordlist_v2.py`)

**Changed**: The seed script now calls `create_app(skip_logging=True)`.

```python
def seed_global_wordlist(force_recreate: bool = False):
    app = create_app(skip_logging=True)  # Skip file logging
    with app.app_context():
        # ... seeding logic
```

**Why**: When running as a one-off command (via Railway CLI or deploy command), the script doesn't need file-based logging and should avoid permission issues.

## Deployment Strategy

### Option 1: Automatic Seeding on Deploy (Recommended)

Add this to your Railway backend service's **Deploy Command**:

```bash
flask db upgrade && python scripts/seed_global_wordlist_v2.py
```

**How it works**:
- `flask db upgrade`: Ensures the database schema is up-to-date.
- `&&`: Only proceeds if migrations succeed.
- `python scripts/seed_global_wordlist_v2.py`: Seeds the global wordlist.
- The script is **idempotent** (safe to run multiple times).

**Advantages**:
- Runs once per deployment, not on every container start.
- Safe for horizontal scaling (multiple replicas won't race).
- Database is guaranteed to be ready (migrations complete first).

### Option 2: Manual Seeding (One-Time Setup)

If you prefer manual control, run this once via Railway CLI:

```bash
railway run --service backend python scripts/seed_global_wordlist_v2.py
```

**Advantages**:
- Explicit control over when seeding happens.
- No deployment delay.

**Disadvantages**:
- Must remember to run after fresh database setups or major migrations.

### Option 3: Background Thread on Startup (Current Implementation)

The current code runs `initialize_global_wordlist()` in a background daemon thread when the app starts.

**Advantages**:
- Fully automatic.
- No deploy command needed.

**Disadvantages**:
- Slight delay before global wordlist is available (usually <1 second).
- If the database is temporarily unavailable at startup, the wordlist won't be created (though the app will still start).

## Verification

After deploying these fixes:

1. **Check healthcheck passes**:
   ```bash
   curl https://your-backend.railway.app/api/v1/health
   ```
   Expected response: `{"status": "healthy", ...}`

2. **Verify global wordlist exists**:
   ```bash
   curl https://your-backend.railway.app/api/v1/coverage/global-wordlist/default
   ```
   Expected: JSON object with the global wordlist details.

3. **Check logs** (Railway dashboard):
   - Look for: `"Global default wordlist ready: French 2K (v1.0.0) (ID: X, 2000 words)"`
   - Should appear within 1-2 seconds of startup.

## Rollback Plan

If issues persist:

1. **Disable background initialization** (emergency):
   - Comment out the background thread code in `backend/app/__init__.py` (lines 110-119).
   - Rely solely on deploy-time seeding.

2. **Revert to synchronous initialization**:
   - Replace the threading code with a direct call: `initialize_global_wordlist(app)`.
   - This will block startup but guarantee the wordlist exists before serving requests.

## Summary

✅ **Fixed**: Logging permission error  
✅ **Fixed**: Background thread context error  
✅ **Updated**: Seed script for Railway compatibility  
✅ **Recommended**: Use deploy-time seeding for production reliability

The app should now start successfully and pass healthchecks on Railway.

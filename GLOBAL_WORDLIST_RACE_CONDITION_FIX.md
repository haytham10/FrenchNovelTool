# Global Wordlist Duplicate Creation Fix

## Problem

When running with **multiple Gunicorn workers** (e.g., 4 workers in production), each worker was independently initializing the global default wordlist during startup. This caused a **race condition** where all workers would:

1. Check if a global default exists (finds nothing)
2. Start creating a new global wordlist
3. Commit their wordlist to the database

This resulted in **4 duplicate wordlists** being created (one per worker).

### Logs Showing the Issue

```
[2025-10-10 19:18:27 +0000] [3] [INFO] Booting worker with pid: 3
[2025-10-10 19:18:27 +0000] [4] [INFO] Booting worker with pid: 4
[2025-10-10 19:18:27 +0000] [5] [INFO] Booting worker with pid: 5
[2025-10-10 19:18:27 +0000] [6] [INFO] Booting worker with pid: 6

[2025-10-10 19:18:36,596] INFO: Created global default wordlist: French 2K (v1.0.0) (ID: 3)
[2025-10-10 19:18:36,616] INFO: Created global default wordlist: French 2K (v1.0.0) (ID: 4)
[2025-10-10 19:18:36,707] INFO: Created global default wordlist: French 2K (v1.0.0) (ID: 5)
[2025-10-10 19:18:36,862] INFO: Created global default wordlist: French 2K (v1.0.0) (ID: 6)
```

Each worker created a separate wordlist with IDs 3, 4, 5, and 6.

---

## Solution

### PostgreSQL Advisory Locks

The fix uses **PostgreSQL advisory locks** to ensure only **one worker** creates the global wordlist, while other workers wait.

**Implementation in `global_wordlist_manager.py`:**

```python
@staticmethod
def ensure_global_default_exists() -> WordList:
    # Quick check first
    existing = WordList.query.filter_by(is_global_default=True).first()
    if existing:
        return existing
    
    # Use advisory lock to coordinate between workers
    ADVISORY_LOCK_ID = 123456789
    
    # Try to acquire lock (non-blocking)
    lock_acquired = db.session.execute(
        db.text("SELECT pg_try_advisory_lock(:lock_id)"),
        {"lock_id": ADVISORY_LOCK_ID}
    ).scalar()
    
    if not lock_acquired:
        # Another worker is creating - wait for it to finish
        db.session.execute(
            db.text("SELECT pg_advisory_lock(:lock_id)"),
            {"lock_id": ADVISORY_LOCK_ID}
        )
        
        # Check if other worker succeeded
        existing = WordList.query.filter_by(is_global_default=True).first()
        
        # Release lock
        db.session.execute(
            db.text("SELECT pg_advisory_unlock(:lock_id)"),
            {"lock_id": ADVISORY_LOCK_ID}
        )
        
        return existing
    
    # This worker won the race - create the wordlist
    try:
        wordlist = GlobalWordlistManager.create_from_file(...)
        return wordlist
    finally:
        # Always release lock
        db.session.execute(
            db.text("SELECT pg_advisory_unlock(:lock_id)"),
            {"lock_id": ADVISORY_LOCK_ID}
        )
```

### How It Works

1. **Worker 1** tries to acquire lock → **SUCCESS** → Creates wordlist
2. **Worker 2** tries to acquire lock → **FAILS** → Waits for Worker 1
3. **Worker 3** tries to acquire lock → **FAILS** → Waits for Worker 1
4. **Worker 4** tries to acquire lock → **FAILS** → Waits for Worker 1
5. **Worker 1** finishes and releases lock
6. **Workers 2-4** acquire lock sequentially, see wordlist exists, and return it

**Result:** Only **1 wordlist** is created, even with 4 workers.

---

## Cleanup Existing Duplicates

If you already have duplicate wordlists in your database, use the cleanup script:

```bash
# SSH into Railway backend service or run locally
cd /app
python cleanup_duplicate_wordlists.py
```

**What it does:**
- Finds all wordlists marked as `is_global_default=True`
- Keeps the oldest one (lowest ID)
- Unmarks duplicates as non-default
- Provides SQL commands to delete duplicates if desired

**Example output:**
```
Current state:
Found 4 wordlist(s) marked as default:
  - ID 3: French 2K (v1.0.0) (1464 words)
  - ID 4: French 2K (v1.0.0) (1464 words)
  - ID 5: French 2K (v1.0.0) (1464 words)
  - ID 6: French 2K (v1.0.0) (1464 words)

Cleanup complete!
✓ Kept default: French 2K (v1.0.0) (ID: 3)
✓ Unmarked 3 duplicate(s)
  Duplicate IDs: 4, 5, 6
```

---

## Prevention

With the fix in place, the new logs will show:

```
[2025-10-10 20:00:27 +0000] [3] [INFO] Booting worker with pid: 3
[2025-10-10 20:00:27 +0000] [4] [INFO] Booting worker with pid: 4
[2025-10-10 20:00:27 +0000] [5] [INFO] Booting worker with pid: 5
[2025-10-10 20:00:27 +0000] [6] [INFO] Booting worker with pid: 6

[2025-10-10 20:00:30,123] INFO: Created global default wordlist: French 2K (v1.0.0) (ID: 7)
[2025-10-10 20:00:30,150] INFO: Another worker is creating the global wordlist. Waiting...
[2025-10-10 20:00:30,170] INFO: Global wordlist created by another worker: French 2K (v1.0.0) (ID: 7)
[2025-10-10 20:00:30,180] INFO: Global wordlist created by another worker: French 2K (v1.0.0) (ID: 7)
[2025-10-10 20:00:30,190] INFO: Global wordlist created by another worker: French 2K (v1.0.0) (ID: 7)
```

Only **1 wordlist created**, workers 2-4 reuse it.

---

## Files Modified

1. **`backend/app/services/global_wordlist_manager.py`**
   - Added PostgreSQL advisory lock logic
   - Added `cleanup_duplicate_defaults()` utility method

2. **`backend/cleanup_duplicate_wordlists.py`** (NEW)
   - Standalone cleanup script for existing duplicates

---

## Alternative Solutions Considered

1. **Retry Logic**: Workers retry on failure, but still creates duplicates temporarily
2. **Unique Constraint**: Can't work because `is_global_default` is a boolean, not unique value
3. **Single Worker Init**: Would require significant architectural changes to Gunicorn
4. **File-based Lock**: Doesn't work across Railway container restarts
5. **Redis Lock**: Requires Redis connection during startup (adds dependency)

**PostgreSQL advisory locks** are the cleanest solution because:
- Built into PostgreSQL (no extra dependencies)
- Session-scoped (auto-released on disconnect)
- Non-blocking option available (`pg_try_advisory_lock`)
- Works across all workers in the same database

---

## Testing

To verify the fix works:

1. Delete all global wordlists:
   ```sql
   DELETE FROM word_lists WHERE owner_user_id IS NULL;
   ```

2. Restart the Railway backend service

3. Check logs - should see only **1 wordlist created**

4. Query database:
   ```sql
   SELECT id, name, is_global_default, normalized_count 
   FROM word_lists 
   WHERE owner_user_id IS NULL;
   ```
   
   Should return **only 1 row**.

---

## Related Documentation

- **PostgreSQL Advisory Locks**: https://www.postgresql.org/docs/current/functions-admin.html#FUNCTIONS-ADVISORY-LOCKS
- **Global Wordlist Implementation**: `GLOBAL_WORDLIST_IMPLEMENTATION.md`
- **Multi-Worker Architecture**: `.github/copilot-instructions.md` (Gunicorn section)

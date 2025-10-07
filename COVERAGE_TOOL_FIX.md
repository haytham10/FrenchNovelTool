# Vocabulary Coverage Tool - Complete Fix Guide

## Problem Diagnosis

**Root Cause**: Your WordList "French 2K" has only `canonical_samples` (20 words) but no `words_json` field populated. The coverage algorithm needs the full normalized word list to match against sentences.

**Evidence from logs**:
```
WordList 2 has no words_json, using 20 canonical samples
Filter mode pass 1 (4-word): 0/0 sentences selected  ← Only 20 words to match!
```

---

## Immediate Fix Options

### **Option 1: API Endpoint (Recommended)**

I've added a new endpoint to refresh wordlists. Call it from your frontend or via curl:

**API Request:**
```bash
POST https://your-app.com/api/v1/coverage/wordlists/2/refresh
Authorization: Bearer YOUR_JWT_TOKEN
```

**What it does**:
- Fetches full word list from Google Sheets (using your source_ref)
- Normalizes all words (handles diacritics, elisions, variants)
- Populates `words_json` with the complete normalized array
- Updates `normalized_count` to reflect actual word count

---

### **Option 2: Railway CLI (Direct Database Fix)**

Connect to your Railway database and run this SQL:

```bash
# Connect to Railway
railway login
railway link
railway connect postgres

# Run update query (replace <full_words_json_array> with actual data)
UPDATE word_lists 
SET words_json = '["le","la","un","une","et","de",...full array...]'::jsonb,
    normalized_count = (json_array_length(words_json)),
    updated_at = NOW()
WHERE id = 2;
```

---

### **Option 3: Auto-Refresh in Coverage Task**

The coverage task will now **automatically attempt to refresh** wordlists that have no `words_json` if:
- The wordlist has `source_type = 'google_sheet'`
- The wordlist has a valid `source_ref` (Sheet ID)
- The user has a Google access token

**Code added to tasks.py** (lines 1210-1227):
```python
if wordlist.source_type == 'google_sheet' and wordlist.source_ref:
    logger.info(f"Attempting to refresh WordList {wordlist_id}")
    user = User.query.get(coverage_run.user_id)
    if user and user.google_access_token:
        wordlist_service = WordListService()
        refresh_report = wordlist_service.refresh_wordlist_from_source(wordlist, user)
        # Now uses full words_json!
```

**To trigger**: Just run a new coverage analysis - it will auto-refresh and work!

---

## Changes Made

### **Backend Improvements**

1. **WordListService.refresh_wordlist_from_source()** (`wordlist_service.py`)
   - Fetches words from Google Sheets or uses canonical_samples
   - Normalizes words (handles diacritics, elisions, multi-token entries)
   - Populates `words_json` with full array
   - Returns refresh report with status

2. **New API Endpoint** (`coverage_routes.py`)
   ```python
   POST /api/v1/coverage/wordlists/<id>/refresh
   ```
   - Manually triggers wordlist refresh
   - Requires JWT authentication
   - Returns updated wordlist + refresh report

3. **Auto-Refresh in Coverage Task** (`tasks.py`)
   - Automatically refreshes wordlist if `words_json` is empty
   - Only works if user has Google Sheets access
   - Falls back to canonical_samples if refresh fails

4. **Utility Script** (`scripts/refresh_wordlists.py`)
   - Command-line tool to refresh wordlists
   - Can refresh all or specific wordlist
   - Useful for maintenance/migrations

---

## Testing the Fix

### **1. Check Current State**
```bash
GET /api/v1/coverage/wordlists/2
```

**Expected Response:**
```json
{
  "id": 2,
  "name": "French 2K",
  "normalized_count": 20,  ← Should be ~2000!
  "canonical_samples": ["le", "la", "un", ...],
  "source_type": "google_sheet",
  "source_ref": "YOUR_SHEET_ID"
}
```

### **2. Refresh the Wordlist**
```bash
POST /api/v1/coverage/wordlists/2/refresh
Authorization: Bearer <your_token>
```

**Expected Response:**
```json
{
  "wordlist": {
    "id": 2,
    "normalized_count": 1998,  ← Full count!
    ...
  },
  "refresh_report": {
    "status": "refreshed",
    "word_count": 1998,
    "source": "google_sheet"
  }
}
```

### **3. Run Coverage Again**
Now run a coverage analysis - should see proper results:
```
Processing 1569 sentences with word list 'French 2K'
Loaded 1998 words from stored words_json  ← Fixed!
Filter mode pass 1 (4-word): 342/1569 sentences selected  ← Results!
```

---

## Frontend UI Enhancement (Next Step)

I'll add a "Refresh" button to the wordlist management UI:

```tsx
// In WordListCard component
<Button 
  onClick={() => refreshWordlistMutation.mutate(wordlist.id)}
  disabled={refreshWordlistMutation.isLoading}
>
  {refreshWordlistMutation.isLoading ? 'Refreshing...' : 'Refresh from Source'}
</Button>
```

This lets users manually refresh wordlists if they update the Google Sheet.

---

## Preventing Future Issues

### **New Wordlists**
The `ingest_word_list()` method now **always** populates `words_json`:
```python
wordlist = WordList(
    words_json=sorted(list(normalized_keys)),  # Full list stored
    normalized_count=len(normalized_keys),
    canonical_samples=samples[:20]  # Just for preview
)
```

### **Data Validation**
Coverage task now validates:
- ✓ Sentences are not empty
- ✓ WordList has either `words_json` or `canonical_samples`
- ✓ WordList keys set is not empty
- ✓ Auto-refresh attempted if possible

---

## Error Handling Improvements

### **Better Logging**
```python
logger.warning(f"WordList {id} has no words_json, using {len(canonical_samples)} canonical samples")
logger.info(f"Attempting to refresh WordList {id} from Google Sheets source")
logger.info(f"Successfully refreshed WordList {id}: {word_count} words")
```

### **Graceful Fallbacks**
1. Try `words_json` (full list)
2. If empty, try auto-refresh from Google Sheets
3. If refresh fails, fall back to `canonical_samples`
4. If all fail, raise clear error message

---

## Next Steps

1. **Deploy these changes to Railway**
2. **Run the refresh endpoint** for wordlist ID 2
3. **Test coverage tool** - should now work properly
4. **Add frontend UI** for wordlist refresh button
5. **(Optional)** Add word count display in wordlist cards

Let me know when you want me to:
- Add the frontend refresh button
- Improve the coverage results UI
- Add export/download features
- Enhance the algorithm further

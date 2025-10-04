# History Integration Migration Guide

## Overview

This migration adds comprehensive history tracking for completed jobs, integrating with the chunk persistence system to provide detailed job results, chunk-level drill-down, and the ability to export historical results to Google Sheets.

## Database Changes

### New Fields in `history` Table

1. **sentences** (JSON, nullable)
   - Stores processed sentence results as array of `{normalized: str, original: str}`
   - Enables re-export of historical results without reprocessing
   - Populated automatically on job completion

2. **exported_to_sheets** (BOOLEAN, default: false, not null)
   - Tracks whether this history entry has been exported
   - Updated when user exports via new `/history/{id}/export` endpoint

3. **export_sheet_url** (VARCHAR 256, nullable)
   - Stores URL of exported sheet (separate from legacy `spreadsheet_url`)
   - Allows tracking multiple exports

4. **chunk_ids** (JSON, nullable)
   - Array of JobChunk IDs associated with this history entry
   - Enables chunk-level drill-down and retry analysis

### Migration File

**File:** `backend/migrations/versions/d2e3f4g5h6i7_add_sentences_to_history.py`

The migration is **idempotent** and safe to run multiple times. It:
- Adds new columns only if they don't exist
- Creates index on `exported_to_sheets` for performance
- Does not modify existing data

## Running the Migration

### Development

```bash
cd backend
docker-compose -f ../docker-compose.dev.yml exec backend flask db upgrade
```

Or if running locally:

```bash
cd backend
flask db upgrade
```

### Production

The migration will run automatically on deployment via the Railway deployment script. To run manually:

```bash
cd backend
flask db upgrade
```

## New Features

### 1. Automatic History Creation

When an async job completes successfully:
- History entry is automatically created with sentences and chunk references
- No manual action required from users or developers
- Linked to Job via `job.history_id`

### 2. History Detail View

Users can view detailed history including:
- All processed sentences
- Processing settings used
- Chunk-level status (success/failed/retry)
- Error details per chunk
- Processing timestamps

**API Endpoint:** `GET /api/v1/history/{entry_id}`

### 3. Export Historical Results

Users can export results from any previous job:
- No need to reprocess the PDF
- Same export functionality as current processing
- Tracks export status separately

**API Endpoint:** `POST /api/v1/history/{entry_id}/export`

### 4. Chunk Drill-Down

Users can view chunk-level details:
- Which chunks succeeded/failed
- Retry attempts and errors
- Page ranges for each chunk

**API Endpoint:** `GET /api/v1/history/{entry_id}/chunks`

## Backward Compatibility

### For Existing History Entries

- Old history entries will have `sentences: null`
- They can still be viewed, but cannot be exported
- New jobs will automatically populate sentences

### For Sync Jobs (Non-Chunked)

- Sync job processing flow is unchanged
- History creation works as before
- New fields are optional and backward compatible

### For Frontend

- New `HistoryDetailDialog` component added
- Existing `HistoryTable` component enhanced
- Legacy export flow still works

## Testing Checklist

After migration, verify:

- [ ] New async jobs create history entries with sentences
- [ ] History detail endpoint returns full data
- [ ] Export from history works for new entries
- [ ] Chunk drill-down shows correct status
- [ ] Old history entries still display correctly
- [ ] Sync jobs continue to work

## Rollback

If needed, rollback the migration:

```bash
cd backend
flask db downgrade
```

This will:
- Remove new columns from history table
- Drop the exported index
- Preserve all existing data (sentences will be lost)

## Performance Considerations

### Database Size

- Sentences stored as JSON in PostgreSQL
- Average increase: ~50-200 KB per history entry
- For 1000 jobs: ~50-200 MB additional storage
- Indexed `exported_to_sheets` field for fast queries

### Query Performance

- New index on `exported_to_sheets` improves filter queries
- Chunk lookup uses existing job_id index
- JSON fields efficiently stored in PostgreSQL

## Next Steps

1. Monitor history entry sizes in production
2. Consider adding pagination to chunk details if jobs have >100 chunks
3. Add cleanup job to remove old sentences after N days (optional)
4. Add user preference for sentence storage (opt-in/opt-out)

## Support

For issues or questions:
- Check logs for migration errors
- Verify database connection before migration
- Contact team if data inconsistencies appear

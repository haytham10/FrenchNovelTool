# History System Update - Dynamic Chunk Integration

## Overview

This update transforms the History system to leverage JobChunk persistence as the **source of truth** for job results, while maintaining a stable snapshot for performance. The system now dynamically retrieves the latest chunk data, supports manual refresh after chunk retries, and automatically uses live data for exports.

## What Changed

### Backend Changes

#### 1. HistoryService Enhancements

**New Methods:**
- `rebuild_sentences_from_chunks(entry_id, user_id)` - Rebuild sentences from current JobChunk results
- `refresh_from_chunks(entry_id, user_id)` - Update History snapshot from latest chunk data

**Updated Methods:**
- `get_entry_with_details(entry_id, user_id, use_live_chunks=True)` - Now fetches from chunks by default
  - Returns `sentences_source` field: `'live_chunks'` or `'snapshot'`
  - Dynamically merges results from successful chunks
  - Falls back to snapshot if chunks unavailable

#### 2. New API Endpoints

**POST /api/v1/history/{entry_id}/refresh**
- Refreshes History snapshot from current JobChunk results
- Use after chunk retries to update persisted data
- Returns updated entry with new sentence count

**Response:**
```json
{
  "message": "History snapshot refreshed from chunks",
  "sentences_count": 145,
  "entry": { /* full history detail */ }
}
```

#### 3. Updated API Endpoints

**GET /api/v1/history/{entry_id}**
- Now returns live chunk data by default (when available)
- Includes `sentences_source` field in response
- Backward compatible - uses snapshot if no chunks

**Response:**
```json
{
  "id": 1,
  "sentences": [...],
  "chunks": [...],
  "sentences_source": "live_chunks",  // NEW
  "chunk_ids": [1, 2, 3]
}
```

**POST /api/v1/history/{entry_id}/export**
- Now uses live chunk data by default
- Falls back to snapshot for backward compatibility
- Returns source indicator and sentence count

**Response:**
```json
{
  "spreadsheet_url": "https://...",
  "sentences_source": "live_chunks",  // NEW
  "sentences_count": 145              // NEW
}
```

**POST /api/v1/jobs/{job_id}/chunks/retry**
- Now includes note about refresh capability
- Indicates export will use updated chunk results automatically

### Frontend Changes

#### 1. API Client (`frontend/src/lib/api.ts`)

**New Function:**
```typescript
export async function refreshHistoryFromChunks(entryId: number): Promise<{
  message: string;
  sentences_count: number;
  entry: HistoryDetail;
}>
```

**Updated Interfaces:**
```typescript
export interface HistoryDetail extends ProcessingHistory {
  sentences: Array<{ normalized: string; original: string }>;
  chunk_ids: number[];
  chunks: ChunkDetail[];
  sentences_source?: 'snapshot' | 'live_chunks';  // NEW
}
```

#### 2. React Query Hooks (`frontend/src/lib/queries.ts`)

**New Hook:**
```typescript
export function useRefreshHistoryFromChunks()
```
- Mutation hook for refreshing history
- Auto-invalidates related queries
- Shows success notification with sentence count

**Updated Hook:**
```typescript
export function useExportHistoryToSheets()
```
- Now shows source in success notification
- "using latest chunk results" if source is live_chunks

#### 3. UI Components (`frontend/src/components/HistoryDetailDialog.tsx`)

**New Features:**
- **Data Source Indicator** - Shows whether viewing live chunks or snapshot
- **Refresh Button** - Manually refresh snapshot from chunks
- **Live Status** - Visual feedback during refresh operation

**UI Elements:**
```tsx
<Chip 
  label={entry.sentences_source === 'live_chunks' ? 'Live Chunks' : 'Snapshot'}
  color={entry.sentences_source === 'live_chunks' ? 'info' : 'default'}
  icon={<Database />}
/>

<Button
  startIcon={<RefreshCw />}
  onClick={handleRefreshFromChunks}
  disabled={refreshMutation.isPending}
>
  {refreshMutation.isPending ? 'Refreshing...' : 'Refresh'}
</Button>
```

## Data Flow

### Historical Flow (Before)
```
1. Job completes → Create History with sentence snapshot
2. Chunks retried → History snapshot UNCHANGED
3. Export from History → Uses OLD snapshot
```

### New Flow (After)
```
1. Job completes → Create History with sentence snapshot + chunk IDs
2. View History → Dynamically fetch from chunks (live data)
3. Chunks retried → Live data reflects changes immediately
4. Export → Uses live chunk data automatically
5. Manual refresh → Update snapshot if needed
```

## Use Cases

### 1. View Latest Results After Chunk Retry
```
User → Views history detail
System → Fetches sentences from current chunk state
Display → Shows "Live Chunks" indicator with refresh button
```

### 2. Export After Chunk Retry
```
User → Clicks "Export to Sheets"
System → Rebuilds sentences from successful chunks
Export → Creates spreadsheet with latest data
Response → Indicates "using latest chunk results"
```

### 3. Update Snapshot for Performance
```
User → Clicks "Refresh" button
System → Calls POST /history/{id}/refresh
Backend → Rebuilds from chunks and updates snapshot
Cache → Invalidated, shows updated data
Notification → "History refreshed: 145 sentences from chunks"
```

### 4. Backward Compatibility
```
Old History Entry (no chunk_ids)
↓
get_entry_with_details
↓
sentences_source = 'snapshot'
↓
Uses static snapshot (no live data available)
```

## Migration & Compatibility

### Backward Compatible
✅ Existing history entries work unchanged
✅ Snapshot still stored and available
✅ Graceful fallback if no chunks
✅ No breaking changes to existing API contracts

### Forward Compatible
✅ New entries use live chunks by default
✅ Export automatically uses latest data
✅ UI shows data source clearly
✅ Manual refresh available when needed

## Performance Considerations

### Why Keep Snapshot?
1. **Fast Reads** - Snapshot in History table for quick access
2. **Fallback** - Works even if chunks deleted/archived
3. **Versioning** - Point-in-time record of results
4. **Backward Compat** - Existing entries still work

### Why Use Live Chunks?
1. **Accuracy** - Always shows latest results after retries
2. **Drill-Down** - Access chunk-level details
3. **Retry Support** - See updated results immediately
4. **Audit Trail** - Full processing history

### Best of Both Worlds
- **Default Behavior** - Fetch from live chunks (most accurate)
- **Fallback** - Use snapshot if chunks unavailable
- **Manual Refresh** - Update snapshot when needed
- **Smart Export** - Always uses latest available data

## Testing

### Backend Tests (`backend/tests/test_history_chunk_integration.py`)

**Test Coverage:**
- ✅ Rebuild sentences from all successful chunks
- ✅ Rebuild from mixed success/failed chunks
- ✅ Get entry with live chunks vs snapshot
- ✅ Refresh history snapshot
- ✅ Handle string vs dict sentence formats
- ✅ Handle missing chunks gracefully

### Manual Testing Checklist

- [ ] View history detail shows "Live Chunks" indicator
- [ ] Refresh button updates snapshot successfully
- [ ] Export uses live chunk data
- [ ] Export shows "using latest chunk results" notification
- [ ] Old history entries show "Snapshot" indicator
- [ ] Retry chunks, then export shows updated results
- [ ] Refresh after retry updates sentence count

## API Examples

### Refresh History Snapshot
```bash
curl -X POST http://localhost:5000/api/v1/history/123/refresh \
  -H "Authorization: Bearer <token>"
```

**Response:**
```json
{
  "message": "History snapshot refreshed from chunks",
  "sentences_count": 145,
  "entry": {
    "id": 123,
    "sentences": [...],
    "processed_sentences_count": 145
  }
}
```

### Export with Live Data
```bash
curl -X POST http://localhost:5000/api/v1/history/123/export \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"sheetName": "My Export"}'
```

**Response:**
```json
{
  "message": "Export successful",
  "spreadsheet_url": "https://docs.google.com/spreadsheets/d/...",
  "sentences_source": "live_chunks",
  "sentences_count": 145
}
```

## Benefits

### For Users
✅ Always see latest results after chunk retries
✅ Export reflects updated data automatically
✅ Clear indicator of data freshness
✅ Manual refresh option for control
✅ No need to reprocess PDFs

### For Developers
✅ Single source of truth (JobChunk)
✅ Easier debugging and audit trails
✅ Backward compatible implementation
✅ Well-tested functionality
✅ Clear data flow

### For System
✅ Scalable architecture
✅ Performance optimized (snapshot + live)
✅ Reliable retry workflows
✅ Auditable processing history
✅ Versioning support ready

## Future Enhancements

### Potential Additions
- [ ] Auto-refresh indicator when chunks updated
- [ ] Snapshot version tracking
- [ ] Diff view between snapshot and live
- [ ] Scheduled auto-refresh jobs
- [ ] Export history with chunk metadata

### Performance Optimizations
- [ ] Cache live chunk results
- [ ] Lazy load chunk details
- [ ] Pagination for large jobs
- [ ] Chunk data compression

## Conclusion

This update successfully transforms the History system to leverage chunk persistence as the source of truth while maintaining backward compatibility and performance. The system now provides:

1. **Accuracy** - Live data from current chunk state
2. **Flexibility** - Manual refresh when needed
3. **Performance** - Snapshot fallback for fast reads
4. **Transparency** - Clear data source indicators
5. **Compatibility** - Works with existing data

Users can now confidently retry failed chunks and immediately see updated results in their history, with automatic propagation to exports and clear visual feedback in the UI.

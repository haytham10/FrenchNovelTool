# History-Chunk Integration Update - Visual Summary

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         Frontend UI                              │
├─────────────────────────────────────────────────────────────────┤
│  HistoryDetailDialog                                             │
│  ┌────────────────────────────────────────────┐                 │
│  │  📄 File: test.pdf                          │                 │
│  │  ⏰ Processed: 2 hours ago                  │                 │
│  │  📊 Sentences: 145                          │                 │
│  │  💾 Data Source: [Live Chunks] 🔵          │  ← NEW!         │
│  │     [Refresh 🔄] button                    │  ← NEW!         │
│  │  ✅ Export Status: Exported                │                 │
│  └────────────────────────────────────────────┘                 │
│                                                                   │
│  Actions:                                                        │
│  • View sentences (live from chunks)                            │
│  • Refresh snapshot (update from chunks)      ← NEW!            │
│  • Export to Sheets (uses live data)          ← ENHANCED!       │
└─────────────────────────────────────────────────────────────────┘
                              ↕
┌─────────────────────────────────────────────────────────────────┐
│                      Backend API Layer                           │
├─────────────────────────────────────────────────────────────────┤
│  Endpoints:                                                      │
│                                                                   │
│  GET /history/{id}                                              │
│    → Returns: { sentences: [...], sentences_source: "live" }   │
│    → Fetches from JobChunks by default        ← ENHANCED!       │
│                                                                   │
│  POST /history/{id}/refresh                   ← NEW!            │
│    → Updates snapshot from current chunks                        │
│    → Returns updated entry with new count                        │
│                                                                   │
│  POST /history/{id}/export                                      │
│    → Uses live chunk data                      ← ENHANCED!       │
│    → Returns: { url, sentences_source, count }                  │
│                                                                   │
│  POST /jobs/{id}/chunks/retry                                   │
│    → Note: Export auto-uses new results       ← ENHANCED!       │
└─────────────────────────────────────────────────────────────────┘
                              ↕
┌─────────────────────────────────────────────────────────────────┐
│                    HistoryService Layer                          │
├─────────────────────────────────────────────────────────────────┤
│  Methods:                                                        │
│                                                                   │
│  rebuild_sentences_from_chunks()              ← NEW!            │
│    → Merges results from successful chunks                       │
│    → Handles string and dict formats                             │
│    → Ordered by chunk_id                                         │
│                                                                   │
│  get_entry_with_details(use_live_chunks=True) ← ENHANCED!       │
│    → Default: fetch from chunks                                  │
│    → Fallback: use snapshot                                      │
│    → Returns sentences_source indicator                          │
│                                                                   │
│  refresh_from_chunks()                        ← NEW!            │
│    → Update snapshot from chunks                                 │
│    → Update sentence count                                       │
│    → Commit to database                                          │
└─────────────────────────────────────────────────────────────────┘
                              ↕
┌─────────────────────────────────────────────────────────────────┐
│                      Database Layer                              │
├─────────────────────────────────────────────────────────────────┤
│  History Table                    JobChunk Table                 │
│  ┌──────────────────┐            ┌──────────────────┐           │
│  │ id: 1            │            │ id: 1            │           │
│  │ job_id: 50       │◄───────────│ job_id: 50       │           │
│  │ sentences: [...]  │            │ chunk_id: 0      │           │
│  │   (snapshot)     │            │ status: success  │           │
│  │ chunk_ids: [1,2,3]│───────────►│ result_json: {   │           │
│  │                  │            │   sentences: [...] │           │
│  │ FAST READ 📈      │            │ }                │           │
│  │ Point-in-time    │            │                  │           │
│  │ Versioning       │            │ SOURCE OF TRUTH ⭐│           │
│  └──────────────────┘            │ Live data        │           │
│                                   │ Retry support    │           │
│                                   └──────────────────┘           │
│                                   ┌──────────────────┐           │
│                                   │ id: 2            │           │
│                                   │ chunk_id: 1      │           │
│                                   │ status: success  │           │
│                                   │ result_json: {...}│           │
│                                   └──────────────────┘           │
│                                   ┌──────────────────┐           │
│                                   │ id: 3            │           │
│                                   │ chunk_id: 2      │           │
│                                   │ status: success  │           │
│                                   │ result_json: {...}│           │
│                                   └──────────────────┘           │
└─────────────────────────────────────────────────────────────────┘
```

## Data Flow Comparison

### Before (Static Snapshot)
```
┌─────────┐    ┌─────────┐    ┌─────────┐
│ Process │───►│ Create  │───►│ History │
│ PDF     │    │ History │    │ (fixed) │
└─────────┘    └─────────┘    └─────────┘
                                    │
                                    │ Never changes
                                    ↓
                              ┌─────────┐
                              │ Export  │
                              │ (old)   │
                              └─────────┘

┌──────────────┐
│ Retry Chunks │ ───► Chunks updated
└──────────────┘      History unchanged ❌
                      Export shows old data ❌
```

### After (Live + Snapshot)
```
┌─────────┐    ┌──────────┐    ┌──────────┐
│ Process │───►│ Create   │───►│ History  │
│ PDF     │    │ Snapshot │    │ Snapshot │
└─────────┘    └──────────┘    └──────────┘
      │                              ↕
      │                         (optional refresh)
      ↓                              ↕
┌──────────┐                    ┌─────────┐
│ Create   │                    │ View    │
│ Chunks   │───────────────────►│ (live)  │
└──────────┘                    └─────────┘
      │                              │
      │                              ↓
      │                         ┌─────────┐
      │                         │ Export  │
      └────────────────────────►│ (live)  │
                                └─────────┘

┌──────────────┐
│ Retry Chunks │ ───► Chunks updated
└──────────────┘      View shows new data ✅
                      Export shows new data ✅
                      Can refresh snapshot ✅
```

## User Journey

### Scenario 1: Normal Processing
```
User uploads PDF
    ↓
Job processes successfully
    ↓
History created with snapshot + chunk_ids
    ↓
User views history
    ↓
System shows: "Data Source: Live Chunks 🔵"
    ↓
User exports → Gets current data ✅
```

### Scenario 2: Chunk Retry
```
Some chunks failed initially
    ↓
User clicks "Retry failed chunks"
    ↓
Chunks reprocess successfully
    ↓
User views same history entry
    ↓
System auto-fetches from updated chunks
    ↓
User sees: "Data Source: Live Chunks 🔵"
    ↓
User exports → Gets UPDATED data ✅
    ↓
User clicks "Refresh" → Snapshot updated ✅
```

### Scenario 3: Old Entry
```
User has old history (no chunks)
    ↓
User views entry
    ↓
System shows: "Data Source: Snapshot ⚪"
    ↓
No refresh button (no chunks available)
    ↓
User exports → Gets snapshot data ✅
```

## Key Indicators

### Live Chunks Indicator 🔵
```
┌─────────────────────────────────┐
│ Data Source: [Live Chunks] 🔵    │
│ [Refresh 🔄]                     │
└─────────────────────────────────┘

Meaning:
• Viewing current chunk data
• Reflects all retries
• Export will use this data
• Can update snapshot
```

### Snapshot Indicator ⚪
```
┌─────────────────────────────────┐
│ Data Source: [Snapshot] ⚪        │
│ (no refresh button)              │
└─────────────────────────────────┘

Meaning:
• Viewing saved snapshot
• No chunks available
• Export uses snapshot
• Backward compatible
```

## API Response Comparison

### Before
```json
{
  "id": 1,
  "sentences": [...],
  "chunks": [...]
}
```

### After
```json
{
  "id": 1,
  "sentences": [...],         // ← From live chunks!
  "sentences_source": "live_chunks",  // ← NEW!
  "chunks": [...]
}
```

### Export Response - Before
```json
{
  "spreadsheet_url": "https://..."
}
```

### Export Response - After
```json
{
  "spreadsheet_url": "https://...",
  "sentences_source": "live_chunks",  // ← NEW!
  "sentences_count": 145              // ← NEW!
}
```

## Benefits Summary

### 🎯 Accuracy
- Always shows latest results
- Reflects chunk retries immediately
- No stale data

### 🚀 Performance
- Snapshot for fast reads
- Fallback when needed
- Optimal query patterns

### 🔄 Flexibility
- Manual refresh option
- Live or snapshot choice
- User control

### 📊 Transparency
- Clear data source
- Visual indicators
- Informed decisions

### 🔙 Compatibility
- Old entries work
- No breaking changes
- Graceful degradation

## Files Modified

```
backend/
  app/
    services/
      history_service.py          ← rebuild, refresh methods
    routes.py                     ← new endpoint, updated export
  tests/
    test_history_chunk_integration.py  ← complete test suite

frontend/
  src/
    lib/
      api.ts                      ← new function, updated types
      queries.ts                  ← new hook
    components/
      HistoryDetailDialog.tsx     ← UI refresh button

docs/
  HISTORY_CHUNK_INTEGRATION_UPDATE.md  ← comprehensive docs
  HISTORY_CHUNK_INTEGRATION_VISUAL.md  ← this file
```

## Conclusion

This update successfully implements the "Update History System to Leverage Chunk Persistence" requirements by:

✅ Using JobChunks as source of truth for job results
✅ Dynamically fetching latest data by default
✅ Providing manual refresh capability
✅ Maintaining backward compatibility
✅ Delivering clear visual feedback

The system now provides the best of both worlds: **live accuracy** with **snapshot performance**.

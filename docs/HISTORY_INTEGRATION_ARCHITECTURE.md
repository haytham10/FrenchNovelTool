# History Integration Architecture Diagram

## System Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          User Interface (Frontend)                       │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌──────────────────┐         ┌──────────────────────────────────┐    │
│  │  HistoryTable    │         │    HistoryDetailDialog           │    │
│  │  Component       │────────▶│                                   │    │
│  │                  │         │  • File Information               │    │
│  │  • View Details  │         │  • Processing Settings            │    │
│  │    👁 Button     │         │  • Sentences Accordion            │    │
│  └──────────────────┘         │  • Chunks Accordion               │    │
│                                │  • Export Button                 │    │
│                                └──────────────────────────────────┘    │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
                                       │
                                       │ API Calls
                                       │
┌─────────────────────────────────────▼─────────────────────────────────────┐
│                       API Layer (React Query Hooks)                        │
├───────────────────────────────────────────────────────────────────────────┤
│                                                                            │
│  useHistoryDetail(id)          getHistoryDetail(id)                       │
│  ───────────────────────────▶  GET /api/v1/history/{id}                   │
│                                                                            │
│  useHistoryChunks(id)          getHistoryChunks(id)                       │
│  ───────────────────────────▶  GET /api/v1/history/{id}/chunks            │
│                                                                            │
│  useExportHistoryToSheets()    exportHistoryToSheets(id, data)            │
│  ───────────────────────────▶  POST /api/v1/history/{id}/export           │
│                                                                            │
└───────────────────────────────────────────────────────────────────────────┘
                                       │
                                       │ HTTP/JSON
                                       │
┌─────────────────────────────────────▼─────────────────────────────────────┐
│                        Backend API (Flask Routes)                          │
├───────────────────────────────────────────────────────────────────────────┤
│                                                                            │
│  GET /history/{id}             POST /history/{id}/export                  │
│  ─────────────────────────▶    ───────────────────────────────▶          │
│  • Authenticate user           • Authenticate user                        │
│  • Verify ownership            • Verify ownership                         │
│  • Get entry + chunks          • Get entry sentences                      │
│                                • Call GoogleSheetsService                 │
│  GET /history/{id}/chunks      • Mark as exported                         │
│  ─────────────────────────▶                                               │
│  • Authenticate user                                                      │
│  • Verify ownership                                                       │
│  • Get chunk details                                                      │
│                                                                            │
└───────────────────────────────────────────────────────────────────────────┘
                                       │
                                       │ Service Calls
                                       │
┌─────────────────────────────────────▼─────────────────────────────────────┐
│                         Service Layer (Business Logic)                     │
├───────────────────────────────────────────────────────────────────────────┤
│                                                                            │
│  ┌─────────────────────────────────────────────────────────────┐         │
│  │              HistoryService                                  │         │
│  │                                                              │         │
│  │  get_entry_with_details(id, user_id)                        │         │
│  │  ├─ Get History by ID                                       │         │
│  │  ├─ Get linked JobChunks                                    │         │
│  │  └─ Return combined data                                    │         │
│  │                                                              │         │
│  │  get_chunk_details(id, user_id)                             │         │
│  │  ├─ Get History by ID                                       │         │
│  │  ├─ Get JobChunks by chunk_ids                              │         │
│  │  └─ Return chunk list                                       │         │
│  │                                                              │         │
│  │  mark_exported(id, user_id, url)                            │         │
│  │  ├─ Get History by ID                                       │         │
│  │  ├─ Update exported_to_sheets = True                        │         │
│  │  └─ Update export_sheet_url                                 │         │
│  └─────────────────────────────────────────────────────────────┘         │
│                                                                            │
└───────────────────────────────────────────────────────────────────────────┘
                                       │
                                       │ Database Queries
                                       │
┌─────────────────────────────────────▼─────────────────────────────────────┐
│                       Database Layer (PostgreSQL)                          │
├───────────────────────────────────────────────────────────────────────────┤
│                                                                            │
│  ┌──────────────────────────┐         ┌──────────────────────────┐       │
│  │    history table         │         │    job_chunks table      │       │
│  │                          │         │                          │       │
│  │  • id (PK)              │         │  • id (PK)              │       │
│  │  • user_id (FK)         │◀───┐    │  • job_id (FK)          │       │
│  │  • job_id (FK)          │    │    │  • chunk_id             │       │
│  │  • original_filename    │    │    │  • start_page           │       │
│  │  • processed_sentences  │    │    │  • end_page             │       │
│  │  • sentences (JSON) ⭐  │    │    │  • status               │       │
│  │  • exported_to_sheets ⭐│    │    │  • attempts             │       │
│  │  • export_sheet_url ⭐  │    │    │  • last_error           │       │
│  │  • chunk_ids (JSON) ⭐  │────┘    │  • result_json          │       │
│  │  • processing_settings │         │  • processed_at         │       │
│  │  • timestamp            │         │                          │       │
│  └──────────────────────────┘         └──────────────────────────┘       │
│                                                                            │
│  Index: idx_history_exported ON history(exported_to_sheets) ⭐            │
│                                                                            │
└───────────────────────────────────────────────────────────────────────────┘

⭐ = New fields/indexes added by this feature
```

## Job Completion Flow

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    PDF Upload & Processing                               │
└─────────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ 1. Create Job                                                            │
│    • status = 'pending'                                                  │
│    • Create JobChunk records in DB                                      │
└─────────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ 2. Process Chunks in Parallel (Celery Tasks)                            │
│    • Each chunk: pending → processing → success/failed                  │
│    • Results stored in JobChunk.result_json                             │
│    • Errors stored in JobChunk.last_error                               │
└─────────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ 3. Finalize Job (finalize_job_results task)                             │
│    • Load all JobChunks from DB                                         │
│    • Merge chunk results → all_sentences                                │
│    • Check for retryable failures                                       │
│    • Update Job.status = 'completed'                                    │
│    • Calculate metrics (tokens, time)                                   │
└─────────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ 4. Create History Entry ⭐ NEW                                          │
│    • Format sentences: [{normalized, original}, ...]                    │
│    • Collect chunk_ids: [123, 124, 125]                                │
│    • Create History record with:                                        │
│      - sentences (full data)                                            │
│      - chunk_ids (for drill-down)                                       │
│      - processing_settings                                              │
│      - exported_to_sheets = False                                       │
│    • Set Job.history_id = history_entry.id                             │
│    • Commit to database                                                 │
└─────────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ 5. User Can Now:                                                         │
│    • View job in History list                                           │
│    • Click "View Details" → HistoryDetailDialog                         │
│    • See all sentences                                                   │
│    • See chunk status                                                    │
│    • Export to Google Sheets                                            │
└─────────────────────────────────────────────────────────────────────────┘
```

## Export from History Flow

```
┌──────────────────────────────────────────────────────────────────────┐
│ User clicks "Export to Sheets" in HistoryDetailDialog               │
└──────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────────────┐
│ Frontend: useExportHistoryToSheets() mutation                        │
│ POST /api/v1/history/{id}/export                                     │
│ { sheetName: "...", folderId: "..." }                               │
└──────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────────────┐
│ Backend: export_history_to_sheets(entry_id)                          │
│ 1. Get History entry (verify ownership)                             │
│ 2. Extract entry.sentences                                           │
│ 3. Get user's Google credentials                                     │
└──────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────────────┐
│ GoogleSheetsService.export_to_sheet()                                │
│ • Create new Google Sheet                                            │
│ • Populate with sentences                                            │
│ • Return spreadsheet_url                                             │
└──────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────────────┐
│ HistoryService.mark_exported()                                        │
│ • Set exported_to_sheets = True                                      │
│ • Set export_sheet_url = spreadsheet_url                             │
│ • Commit to database                                                  │
└──────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────────────┐
│ Frontend: Update UI                                                   │
│ • Show success snackbar                                              │
│ • Invalidate queries (refresh data)                                  │
│ • Display "Open Sheet" button                                        │
│ • Show "Exported" badge                                              │
└──────────────────────────────────────────────────────────────────────┘
```

## Data Relationships

```
┌─────────────┐
│    User     │
└──────┬──────┘
       │ 1:N
       │
       ▼
┌─────────────┐      1:1      ┌──────────────┐
│   History   │◀──────────────│     Job      │
│             │               │              │
│ sentences ⭐│               │ history_id   │
│ chunk_ids ⭐│               │              │
└──────┬──────┘               └───────┬──────┘
       │                              │
       │ N:M (via chunk_ids)         │ 1:N
       │                              │
       │                              ▼
       │                       ┌──────────────┐
       └──────────────────────▶│  JobChunk    │
                               │              │
                               │ status       │
                               │ attempts     │
                               │ result_json  │
                               │ last_error   │
                               └──────────────┘
```

## Component Interaction

```
HistoryTable
    │
    │ user clicks 👁
    │
    ▼
HistoryDetailDialog
    │
    ├─▶ useHistoryDetail(entryId)
    │       │
    │       └─▶ GET /history/{id}
    │               │
    │               └─▶ HistoryService.get_entry_with_details()
    │                       │
    │                       ├─▶ History.query.get(id)
    │                       └─▶ JobChunk.query.filter(...)
    │
    ├─▶ useHistoryChunks(entryId)
    │       │
    │       └─▶ GET /history/{id}/chunks
    │               │
    │               └─▶ HistoryService.get_chunk_details()
    │                       │
    │                       └─▶ JobChunk.query.filter(...)
    │
    └─▶ useExportHistoryToSheets()
            │
            └─▶ POST /history/{id}/export
                    │
                    ├─▶ GoogleSheetsService.export_to_sheet()
                    └─▶ HistoryService.mark_exported()
```

## Key Advantages

✅ **Persistent Storage**: Sentences stored in DB, no reprocessing needed
✅ **Detailed Visibility**: Chunk-level drill-down for failure analysis
✅ **Flexible Export**: Export anytime, multiple times if needed
✅ **Backward Compatible**: Works with old history, new jobs enhance it
✅ **Scalable**: JSON storage efficient, indexed for performance
✅ **Auditable**: Full trail of processing attempts and results

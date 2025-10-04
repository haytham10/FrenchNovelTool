# History Integration Feature - Quick Start

## 🎯 What This Feature Does

Automatically saves all completed job results to the History table, allowing users to:
- **View** detailed results of any previous job
- **Export** to Google Sheets without reprocessing
- **Analyze** chunk-level processing status
- **Retry** failed chunks or entire jobs

## 🚀 Quick Start

### For Users

1. **Process a PDF** as usual - History entry is created automatically
2. **Go to History page** to see all your past jobs
3. **Click the 👁 (eye) icon** to view details
4. **In the detail dialog:**
   - See all processed sentences
   - View chunk processing status
   - Export to Google Sheets
   - Track export status

### For Developers

#### Run the Migration

```bash
cd backend
flask db upgrade  # Runs d2e3f4g5h6i7_add_sentences_to_history.py
```

#### Test the Feature

```python
# 1. Process a PDF (creates History entry)
POST /api/v1/process-pdf
# -> Creates Job -> Processes chunks -> Creates History

# 2. View history detail
GET /api/v1/history/123
# -> Returns sentences, chunks, settings

# 3. Export from history
POST /api/v1/history/123/export
# -> Exports to Google Sheets
```

## 📊 Database Schema Changes

```sql
-- Added to history table:
ALTER TABLE history ADD COLUMN sentences JSON;
ALTER TABLE history ADD COLUMN exported_to_sheets BOOLEAN DEFAULT FALSE;
ALTER TABLE history ADD COLUMN export_sheet_url VARCHAR(256);
ALTER TABLE history ADD COLUMN chunk_ids JSON;

-- Index for performance:
CREATE INDEX idx_history_exported ON history(exported_to_sheets);
```

## 🔌 API Endpoints

### GET /history/{id}
Get detailed history with sentences and chunks.

**Response:**
```json
{
  "id": 123,
  "sentences": [{"normalized": "...", "original": "..."}],
  "chunk_ids": [456, 457],
  "chunks": [...],
  "exported_to_sheets": false
}
```

### GET /history/{id}/chunks
Get chunk processing details.

**Response:**
```json
{
  "chunks": [
    {
      "chunk_id": 0,
      "status": "success",
      "attempts": 1,
      "start_page": 0,
      "end_page": 4
    }
  ]
}
```

### POST /history/{id}/export
Export historical results to Google Sheets.

**Request:**
```json
{
  "sheetName": "My Export",
  "folderId": "optional-drive-folder-id"
}
```

**Response:**
```json
{
  "spreadsheet_url": "https://docs.google.com/..."
}
```

## 🎨 Frontend Components

### HistoryDetailDialog
Material-UI dialog showing:
- File info and processing date
- Processing settings used
- All sentences in expandable table
- Chunk status breakdown
- Export button

**Usage:**
```tsx
import HistoryDetailDialog from '@/components/HistoryDetailDialog';

<HistoryDetailDialog
  entryId={123}
  open={isOpen}
  onClose={() => setIsOpen(false)}
/>
```

### React Query Hooks
```tsx
import { useHistoryDetail, useHistoryChunks, useExportHistoryToSheets } from '@/lib/queries';

const { data: detail } = useHistoryDetail(entryId);
const { data: chunks } = useHistoryChunks(entryId);
const exportMutation = useExportHistoryToSheets();

exportMutation.mutate({ entryId, data: { sheetName: "Export" } });
```

## 📁 File Structure

```
backend/
├── app/
│   ├── models.py                 # Updated History model
│   ├── tasks.py                  # Auto-create History on completion
│   ├── routes.py                 # 3 new endpoints
│   └── services/
│       └── history_service.py    # 3 new methods
└── migrations/versions/
    └── d2e3f4g5h6i7_*.py         # Migration

frontend/
├── src/
│   ├── components/
│   │   ├── HistoryDetailDialog.tsx  # New component
│   │   └── HistoryTable.tsx         # Updated
│   └── lib/
│       ├── api.ts                # New functions
│       └── queries.ts            # New hooks

docs/
├── HISTORY_INTEGRATION_IMPLEMENTATION.md  # Full details
└── HISTORY_INTEGRATION_MIGRATION.md       # Migration guide
```

## 🧪 Testing Checklist

After deployment:

- [ ] Upload and process a test PDF
- [ ] Verify history entry has `sentences` populated
- [ ] Click "View details" in History table
- [ ] Verify detail dialog opens with data
- [ ] Expand sentences accordion
- [ ] Expand chunks accordion (if multi-chunk job)
- [ ] Click "Export to Sheets"
- [ ] Verify export works and status updates
- [ ] Check exported sheet has correct data

## 🔍 Troubleshooting

### History Entry Missing Sentences
- Old entries created before this feature: Normal
- New entries after deployment: Check logs for errors

### Detail Dialog Empty
- Check browser console for API errors
- Verify user is authenticated
- Check entry belongs to current user

### Export Fails
- Verify Google Sheets authorization
- Check rate limit (5/hour)
- View error message in snackbar

### Chunks Not Showing
- Only async jobs have chunks
- Sync jobs won't have chunk data
- Check `chunk_ids` is not null

## 📚 Documentation

- **Implementation Details**: `docs/HISTORY_INTEGRATION_IMPLEMENTATION.md`
- **Migration Guide**: `docs/HISTORY_INTEGRATION_MIGRATION.md`
- **API Reference**: `backend/API_DOCUMENTATION.md`

## 🤝 Support

Questions? Issues?
1. Check implementation docs
2. Review migration guide
3. Check API documentation
4. Examine error logs

## ✅ Success Criteria

- [x] All async jobs create History entries
- [x] History detail shows sentences and chunks
- [x] Export from history works
- [x] Chunk drill-down displays status
- [x] Backward compatible with old history
- [x] No breaking changes

---

**Version**: 1.0.0  
**Status**: Ready for Deployment  
**Last Updated**: 2025-01-15

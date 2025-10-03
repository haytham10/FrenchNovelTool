# Google Drive Folder Selection Feature

## Overview
Users can now select a Google Drive folder when exporting processed sentences to Google Sheets. This allows for better organization and control over where exported spreadsheets are stored.

## How It Works

### Frontend Components

#### DriveFolderPicker Component
- **Location**: `frontend/src/components/DriveFolderPicker.tsx`
- **Purpose**: Provides a UI for selecting Google Drive folders using the Google Picker API
- **Features**:
  - "Select Folder" button that opens Google Drive folder picker
  - "Clear" button to remove folder selection
  - Displays selected folder name
  - Handles Google API authentication via OAuth2

#### ExportDialog Component
- **Location**: `frontend/src/components/ExportDialog.tsx`
- **Integration**: Includes DriveFolderPicker with clear handler
- **Export Options**: Passes folder ID and name as part of export options

### Backend Support

#### Google Sheets Service
- **Location**: `backend/app/services/google_sheets_service.py`
- **Method**: `export_to_sheet()`
- **Parameters**:
  - `folder_id` (optional): Google Drive folder ID where the spreadsheet should be created
  - If provided, the newly created spreadsheet is moved to the specified folder
  - If not provided, spreadsheet is created in the default location (root of My Drive)

#### API Endpoint
- **Endpoint**: `POST /api/v1/export-to-sheet`
- **Schema**: `ExportToSheetSchema` in `backend/app/schemas.py`
- **Fields**:
  - `folderId` (string, optional): Google Drive folder ID
  - Validates folder ID length (max 255 characters)
  - Allows null values (no folder selection)

### Data Flow

1. User clicks "Select Folder" in ExportDialog
2. DriveFolderPicker loads Google Picker API
3. User authenticates with Google OAuth (if not already authenticated)
4. User selects folder from Google Drive picker
5. Folder ID and name are stored in ExportDialog state
6. User clicks "Export"
7. Frontend sends export request with all options including `folderId`
8. Backend creates spreadsheet and moves it to specified folder (if folderId provided)
9. Backend returns spreadsheet URL

### Implementation Details

#### Frontend API Interface
```typescript
export interface ExportToSheetRequest {
  sentences: string[];
  sheetName: string;
  folderId?: string | null;
  mode?: 'new' | 'append';
  existingSheetId?: string;
  tabName?: string;
  createNewTab?: boolean;
  headers?: string[];
  columnOrder?: string[];
  sharing?: {
    addCollaborators?: boolean;
    collaboratorEmails?: string[];
    publicLink?: boolean;
  };
  sentenceIndices?: number[];
}
```

#### Backend Schema Validation
```python
class ExportToSheetSchema(Schema):
    # ... other fields
    folderId = fields.String(
        allow_none=True,
        validate=validate.Length(max=255)
    )
```

#### Backend Implementation
```python
if folder_id:
    # Move the file to the specified folder
    file_id = spreadsheet_id
    file = drive_service.files().get(fileId=file_id, fields='parents').execute()
    previous_parents = ",".join(file.get('parents'))
    drive_service.files().update(
        fileId=file_id,
        addParents=folder_id,
        removeParents=previous_parents,
        fields='id, parents'
    ).execute()
```

## User Settings Integration

Users can optionally set a `default_folder_id` in their settings (`/settings` page) to have a default folder for exports. However, the folder picker provides a more user-friendly way to select folders.

## Testing

### Backend Tests
- **File**: `backend/tests/test_p1_features.py`
- **Test Cases**:
  - `test_folder_id_schema`: Validates folder ID in schema
  - `test_folder_id_null_schema`: Validates null folder ID
  - `test_export_with_folder_id`: Tests export with folder selection
  - `test_export_without_folder_id`: Tests export without folder (default location)

### Manual Testing Checklist
- [ ] Select folder from Drive picker
- [ ] Export to selected folder
- [ ] Verify spreadsheet appears in correct folder
- [ ] Clear folder selection
- [ ] Export without folder selection (should go to root)
- [ ] Test with "new spreadsheet" mode
- [ ] Test with "append" mode (if supported)
- [ ] Verify error handling for invalid folder IDs
- [ ] Verify error handling for folders without write permission

## Error Handling

- **Missing Google API Credentials**: User sees warning that folder selection is disabled
- **API Not Loaded**: Error message displayed when trying to open picker
- **Permission Errors**: Backend returns appropriate error if user lacks access to selected folder
- **Invalid Folder ID**: Schema validation prevents invalid folder IDs from being sent to backend

## Dependencies

### Frontend
- Google Picker API (`https://apis.google.com/js/api.js`)
- Google Identity Services (`https://accounts.google.com/gsi/client`)
- Environment Variables:
  - `NEXT_PUBLIC_GOOGLE_CLIENT_ID`
  - `NEXT_PUBLIC_GOOGLE_API_KEY`

### Backend
- Google Drive API v3
- User's OAuth credentials (stored in User model)
- Required OAuth scopes:
  - `https://www.googleapis.com/auth/drive.file`

## Future Enhancements

- [ ] Remember last selected folder per user
- [ ] Allow creating new folders from picker
- [ ] Folder picker integration in settings page
- [ ] Bulk folder organization for history entries
- [ ] Folder breadcrumb display in export dialog

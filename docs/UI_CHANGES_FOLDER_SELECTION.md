# UI Changes - Google Drive Folder Selection

## Export Dialog - Before Changes

```
┌─────────────────────────────────────────────────────────┐
│  📥 Export to Google Sheets                             │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  Export Destination                                     │
│  ○ Create new spreadsheet                              │
│     Creates a fresh Google Sheets file                 │
│  ○ Append to existing spreadsheet                      │
│     Add to an existing sheet or create a new tab       │
│                                                         │
│  Spreadsheet Name *                                     │
│  ┌───────────────────────────────────────────────────┐ │
│  │ French Novel Sentences                            │ │
│  └───────────────────────────────────────────────────┘ │
│  The name of the Google Sheets file                    │
│                                                         │
│  Google Drive Destination (Optional)                    │
│  ┌─────────────────┐                                   │
│  │ Select Folder   │                                   │
│  └─────────────────┘                                   │
│                                                         │
│  ────────────────────────────────────────────────────  │
│                                                         │
│  [Advanced Options ▼]                                  │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

## Export Dialog - After Changes

```
┌─────────────────────────────────────────────────────────┐
│  📥 Export to Google Sheets                             │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  Export Destination                                     │
│  ○ Create new spreadsheet                              │
│     Creates a fresh Google Sheets file                 │
│  ○ Append to existing spreadsheet                      │
│     Add to an existing sheet or create a new tab       │
│                                                         │
│  Spreadsheet Name *                                     │
│  ┌───────────────────────────────────────────────────┐ │
│  │ French Novel Sentences                            │ │
│  └───────────────────────────────────────────────────┘ │
│  The name of the Google Sheets file                    │
│                                                         │
│  Google Drive Destination (Optional)                    │
│  ┌─────────────────┐  ┌───────┐                        │
│  │ Select Folder   │  │ Clear │  ← NEW!                │
│  └─────────────────┘  └───────┘                        │
│  Selected: My Project Folder    ← Shows selected folder│
│                                                         │
│  ────────────────────────────────────────────────────  │
│                                                         │
│  [Advanced Options ▼]                                  │
│                                                         │
│  📊 Export Summary                                      │
│  [New Sheet] [French Novel Sentences]                  │
│  [📁 My Project Folder]          ← Shows in summary    │
│                                                         │
│                                    ┌────────┐ ┌────────┐│
│                                    │ Cancel │ │ Export ││
│                                    └────────┘ └────────┘│
└─────────────────────────────────────────────────────────┘
```

## Key UI Improvements

### 1. Clear Button
- **Location**: Next to "Select Folder" button
- **Visibility**: Only appears when a folder is selected
- **Function**: Removes folder selection with one click
- **Benefit**: Better UX - users don't need to select a new folder to cancel

### 2. Selected Folder Display
- **Already existed but now functional**
- Shows "Selected: [Folder Name]" below buttons
- Updates when folder is selected or cleared
- Provides visual confirmation of selection

### 3. Export Summary Enhancement
- **Already existed but now shows folder**
- Displays folder chip with 📁 icon
- Shows folder name in summary section
- Helps users verify their selections before exporting

## Google Picker Integration Flow

```
User clicks "Select Folder"
         │
         ▼
Google Picker Dialog Opens
┌────────────────────────────┐
│  🔍 Select a folder        │
├────────────────────────────┤
│  📁 My Drive               │
│    📁 Projects             │
│    📁 Documents            │
│    📁 Novel Exports  ←     │
│    📁 Archives             │
│                            │
│        [Cancel] [Select]   │
└────────────────────────────┘
         │
         ▼
Folder ID and Name stored
         │
         ▼
UI Updates:
- Shows "Selected: Novel Exports"
- "Clear" button appears
- Folder chip added to summary
```

## Data Flow Changes

### Before Changes
```
ExportDialog (collects all options)
         │
         ▼
page.tsx handleExport()
         │
         ▼  Only 3 fields passed:
         │  - sentences
         │  - sheetName
         │  - folderId
         ▼
Backend /export-to-sheet
```

### After Changes
```
ExportDialog (collects all options)
         │
         ▼
page.tsx handleExport()
         │
         ▼  ALL fields passed:
         │  - sentences, sheetName, folderId
         │  - mode, existingSheetId, tabName
         │  - headers, columnOrder, sharing
         ▼
Backend /export-to-sheet
         │
         ▼
Full export configuration honored
```

## Component Hierarchy

```
ExportDialog
  ├─ Export Mode Selection (Radio Group)
  ├─ Spreadsheet Name (TextField)
  ├─ DriveFolderPicker ← ENHANCED
  │    ├─ Select Folder (Button)
  │    ├─ Clear (Button) ← NEW
  │    └─ Selected Display (Typography)
  ├─ Advanced Options (Accordion)
  │    ├─ Custom Headers
  │    └─ Sharing Settings
  └─ Export Summary ← NOW INCLUDES FOLDER
       └─ Chips showing all selections
```

## Error Handling UI

### Missing Credentials
```
┌─────────────────────────────────────────────────────────┐
│  Google Drive Destination (Optional)                    │
│  ┌─────────────────┐                                    │
│  │ Select Folder   │ (disabled)                         │
│  └─────────────────┘                                    │
│  ⚠ Google API credentials are not configured.           │
│     Folder selection is disabled.                       │
└─────────────────────────────────────────────────────────┘
```

### Permission Error (Backend)
```
┌─────────────────────────────────────────────────────────┐
│  ❌ Export Failed                                        │
│                                                         │
│  You do not have permission to create files in the      │
│  selected folder. Please choose a different folder or   │
│  contact the folder owner for access.                   │
│                                                         │
│                                    [Close]              │
└─────────────────────────────────────────────────────────┘
```

## Mobile Responsive Behavior

The folder picker buttons stack vertically on mobile:

```
Mobile View:
┌─────────────────────────┐
│ Google Drive Destination│
│ ┌─────────────────────┐ │
│ │   Select Folder     │ │
│ └─────────────────────┘ │
│ ┌─────────────────────┐ │
│ │      Clear          │ │
│ └─────────────────────┘ │
│ Selected: My Folder     │
└─────────────────────────┘
```

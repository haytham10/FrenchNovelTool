# Three-Column Wizard Layout - Coverage Analysis Screen

## Overview

The Coverage Analysis screen has been redesigned to follow a "One Job, One Screen" philosophy, separating configuration, source selection, and execution/review into three distinct visual columns. This creates a natural left-to-right workflow that reduces cognitive load and makes the user feel in control at every stage.

## Layout Structure

```
┌────────────────────────────────────────────────────────────────────────────┐
│                     Vocabulary Coverage Tool                               │
├────────────────┬────────────────────┬───────────────────────────────────────┤
│   COLUMN 1     │    COLUMN 2        │           COLUMN 3                    │
│  CONFIGURE     │  SELECT SOURCE     │        RUN & REVIEW                   │
│                │                    │                                       │
│ ┌──────────┐   │ ┌──────────────┐  │  ┌─────────────────────────────────┐ │
│ │ Analysis │   │ │ Search Bar   │  │  │                                 │ │
│ │ Mode     │   │ └──────────────┘  │  │    STATE 1: INITIAL             │ │
│ └──────────┘   │                    │  │    Large "Run" Button           │ │
│                │ ┌──────────────┐  │  │    + Credit Cost Display        │ │
│ ┌──────────┐   │ │ Import from  │  │  │                                 │ │
│ │ Word     │   │ │ Sheets       │  │  └─────────────────────────────────┘ │
│ │ List     │   │ └──────────────┘  │                                       │
│ └──────────┘   │                    │  ┌─────────────────────────────────┐ │
│                │ ┌──────────────┐  │  │                                 │ │
│ ┌──────────┐   │ │ Source 1     │◄─┤  │    STATE 2: PROCESSING          │ │
│ │ Sentence │   │ │ PDF Icon     │  │  │    Progress Bar (Live)          │ │
│ │ Limit    │   │ └──────────────┘  │  │    + Cancel Button              │ │
│ │ Slider   │   │                    │  │                                 │ │
│ └──────────┘   │ ┌──────────────┐  │  └─────────────────────────────────┘ │
│                │ │ Source 2     │  │                                       │
│ (Static,       │ │ Sheets Icon  │  │  ┌─────────────────────────────────┐ │
│  Always        │ └──────────────┘  │  │                                 │ │
│  Visible)      │                    │  │    STATE 3: RESULTS             │ │
│                │ (Scrollable        │  │    • KPI Cards (3)              │ │
│                │  Card List)        │  │    • Download CSV Button        │ │
│                │                    │  │    • Export to Sheets Button    │ │
│                │                    │  │    • Results Preview            │ │
│                │                    │  │                                 │ │
│                │                    │  └─────────────────────────────────┘ │
└────────────────┴────────────────────┴───────────────────────────────────────┘
│                                                                              │
│                        FULL RESULTS SECTION                                  │
│                     (Appears below on completion)                            │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │ Learning Set Table / Filter Results Table                              │ │
│  │ (Full paginated results with all data)                                 │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────────────────┘
```

## Column Details

### Column 1: Configure Analysis
**Purpose:** Static configuration panel that's always visible

**Components:**
- **Analysis Mode Dropdown** with help icon (?)
  - Options: Coverage Mode, Filter Mode
  - Help icon opens modal with detailed explanations
- **Target Word List Dropdown**
  - Shows word list name + word count (e.g., "French 2k (2206 words)")
  - Default list marked with ★
  - "+ Upload New List (.csv)" option at bottom
- **Learning Set Size Slider** (Coverage mode only)
  - Range: 100, 250, 500, 1000 (∞)
  - Text input for custom values (50-999)
  - Visual markers at key points

**Design Features:**
- Sticky positioning (stays at top when scrolling on mobile)
- Numbered chip "1" for clarity
- Clean white space between elements
- Generous padding (3 spacing units)

### Column 2: Select Source
**Purpose:** Interactive list of available source texts

**Components:**
- **Search Bar** at top
  - Placeholder: "Search by name or ID..."
  - Search icon prefix
- **Import from Google Sheets Button**
  - Cloud upload icon
  - Full-width, outlined style
- **Source Card List**
  - Scrollable container
  - Clean card-based UI (not dense list)
  - Each card shows:
    - Icon (PDF or Sheets icon) - large, primary color
    - Filename (bold, truncated with ellipsis if long)
    - Metadata: "ID #999 • 15,803 sentences • MM/DD/YYYY"
    - Radio button for selection
  - Selected state: blue border (2px), selected background
  - Hover state: primary border, subtle shadow

**Design Features:**
- Numbered chip "2" for clarity
- Cards provide visual breathing room
- Clear selection feedback
- Limited to 50 results for performance

### Column 3: Run & Review
**Purpose:** Dynamic column that transforms based on state

#### State 1: Initial (No Run)
- Numbered chip "3" with "Run Analysis"
- Large, prominent button:
  - Text: "Run Vocabulary Coverage"
  - Gradient background (blue to cyan)
  - Play icon
  - Size: large (py: 3, px: 6)
  - Dramatic shadow effect
- Credit cost chip below button
- Helpful text if no source selected

#### State 2: Processing
- Header changes to "Processing..."
- Live progress bar with percentage
- "Live Updates" chip (green) when WebSocket connected
- "Reconnecting..." chip (warning) when disconnected
- Cancel button (currently disabled/placeholder)
- Text: "Cancellation coming soon"

#### State 3: Completed
- Header: "Results"
- **KPI Cards** (3 for coverage, 2 for filter):
  - Sentences Selected (always)
  - Words Covered (coverage only)
  - Vocabulary Coverage % (coverage only)
  - Acceptance Ratio (filter only)
  - Cards styled with outlined variant
  - Large numbers (h4 variant)
- **Action Buttons** (horizontal stack):
  - Download CSV (outlined)
  - Export to Sheets (outlined)
  - Both full-width within their container
- **Results Preview**:
  - Shows first 10 entries from Learning Set or Filter results
  - "View Full Results Below" button for scrolling
- **Start New Analysis** button at bottom

#### State 4: Failed
- Header: "Failed"
- Error alert with message
- "Try Again" button to reset

**Design Features:**
- Column height fills available space
- Flex layout with proper spacing
- Visual hierarchy through typography
- Clear state transitions

## Responsive Behavior

**Desktop (md and up):**
- Three columns side-by-side
- Grid layout: `repeat(3, 1fr)`
- Gap: 3 spacing units
- Column 1 is sticky on scroll

**Mobile (xs):**
- Columns stack vertically
- Single column layout
- All columns full-width
- Natural top-to-bottom flow

## Visual Design Principles

### Colors
- **Primary Action Color:** Vibrant blue (#2196F3) with gradient to cyan (#21CBF3)
- **Selected State:** Primary blue border, action.selected background
- **Hover State:** Primary border, subtle shadow
- **Disabled State:** action.disabledBackground, no shadow

### Typography
- **Column Headers:** h6, fontWeight 600
- **KPI Numbers:** h4, fontWeight 600
- **Body Text:** body2
- **Secondary Text:** caption, color text.secondary

### Spacing
- **Between Columns:** 3 units (24px)
- **Card Padding:** 2 units (16px)
- **Column Padding:** 3 units (24px)
- **Stack Spacing:** 2-3 units depending on content

### Icons
- PDF Icon (Description) for PDF sources
- Sheets Icon (TableChart) for spreadsheet sources
- Help Icon (HelpOutline) for mode explanations
- Play Icon (PlayArrow) for run button
- Download Icon (Download) for export actions
- Upload Icon (Upload, CloudUpload) for imports

### Interactive Elements
- All buttons have proper focus states
- Hover effects on cards
- Smooth transitions (all 0.2s)
- Clear disabled states
- Loading states with spinners

## User Flow

1. **Configure (Column 1)**
   - User selects analysis mode
   - Chooses or uploads word list
   - Sets sentence limit (if coverage mode)

2. **Select (Column 2)**
   - User searches for source
   - Clicks on a source card to select
   - Or imports from Google Sheets

3. **Run (Column 3)**
   - User clicks large "Run" button
   - System validates credits
   - Starts processing with live updates
   - Shows completion with KPI cards
   - User can download or export results

4. **Review (Full Results Section)**
   - Appears below three columns when complete
   - Shows full paginated results
   - Supports filtering and sorting

## Implementation Details

### Key State Variables
- `mode`: 'coverage' | 'filter'
- `selectedWordListId`: number | ''
- `sourceId`: string (history ID)
- `currentRunId`: number | null
- `sentenceCap`: number (0 = unlimited)
- `historySearch`: string
- `showHelpDialog`: boolean

### Data Loading
- Word lists: React Query with ['wordlists'] key
- History: React Query with ['history', 'forCoverage'] key
- Coverage run: React Query with ['coverageRun', runId] key
- Real-time updates: WebSocket via useCoverageWebSocket hook

### Responsive Grid
Using CSS Grid:
```typescript
sx={{
  display: 'grid',
  gridTemplateColumns: { xs: '1fr', md: 'repeat(3, 1fr)' },
  gap: 3,
  minHeight: '70vh',
}}
```

## Accessibility

- Numbered chips (1, 2, 3) provide clear progression
- Help icon with tooltip for mode explanations
- Clear focus states on all interactive elements
- Proper semantic HTML (headings, sections)
- ARIA labels where needed
- Keyboard navigation support

## Future Enhancements

1. **Cancel functionality** - Currently placeholder
2. **Drag-and-drop** for source selection
3. **Keyboard shortcuts** (e.g., Ctrl+Enter to run)
4. **Save configuration presets**
5. **Quick re-run** with last settings
6. **Export history** integration

## Testing Checklist

- [ ] All three columns render correctly
- [ ] Mode selection updates UI appropriately
- [ ] Word list selection works
- [ ] Sentence limit slider functions
- [ ] Source search filters correctly
- [ ] Source card selection visual feedback
- [ ] Run button enables/disables based on state
- [ ] Credit validation works
- [ ] Processing state shows live updates
- [ ] KPI cards display correct data
- [ ] Export buttons function
- [ ] Results preview shows correct data
- [ ] Full results section appears
- [ ] Start new analysis resets state
- [ ] Help dialog opens and closes
- [ ] Responsive layout works on mobile
- [ ] All error states handled gracefully

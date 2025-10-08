# Wizard Stepper Implementation

## Overview
Converted the Coverage Analysis page from a three-column simultaneous layout to a sequential wizard stepper with navigation buttons.

## Changes Made

### 1. **Added Material-UI Stepper Components**
- Imported `Stepper`, `Step`, `StepLabel` from `@mui/material`
- Added navigation icons: `ArrowBack`, `ArrowForward`

### 2. **Created Wizard Infrastructure**
```typescript
const WIZARD_STEPS = ['Configure', 'Select Source', 'Run & Review'] as const;
const [activeStep, setActiveStep] = useState<number>(currentRunId ? 2 : 0);
```

### 3. **Navigation Handlers**
- `handleStepBack()` - Decrements active step (minimum 0)
- `handleStepNext()` - Increments active step (maximum 2)
- `isNextDisabled` - Validates step progression:
  - Step 0 (Configure): Always allows next
  - Step 1 (Select Source): Requires sourceId to be selected
  - Step 2 (Run & Review): Final step (disabled)

### 4. **Step Content Structure**

#### **Step 0: Configure Analysis**
- Analysis mode selector (Coverage/Filter)
- Word list dropdown with default indicator (★)
- Upload new word list functionality
- Learning set size slider (Coverage mode only)
- Custom sentence cap input

#### **Step 1: Select Source**
- Search bar for filtering history
- Import from Google Sheets button
- Scrollable list of processing history
- Radio button selection for source
- Visual indicators (PDF/Sheets icons)
- Selected state highlighting

#### **Step 2: Run & Review**
Multiple sub-states:
- **Initial**: Big "Run Vocabulary Coverage" button with cost display
- **Loading**: Circular progress indicator
- **Processing**: Linear progress bar with live WebSocket updates
- **Completed**: KPI cards, action buttons, results preview
- **Failed**: Error message with retry option

### 5. **Navigation UI**
Bottom navigation bar with:
- **Back button**: Disabled on step 0, shows arrow icon
- **Next button**: Disabled when validation fails, shows arrow icon
  - Label changes to "Finish" on final step

### 6. **State Management**
- Active step updates automatically when run starts (`currentRunId` changes)
- "Start New Analysis" resets to step 0
- URL parameters (`?runId=X`) still work - jumps to step 2

### 7. **Preserved Functionality**
All original features maintained:
- ✅ Credit system integration
- ✅ WebSocket live updates
- ✅ Google Sheets import/export
- ✅ CSV download
- ✅ Word list upload
- ✅ Processing history filtering
- ✅ Full results section below wizard
- ✅ Help dialog for analysis modes
- ✅ Info panel with mode descriptions

## User Experience Flow

1. **Step 1: Configure**
   - User selects analysis mode (Coverage/Filter)
   - Chooses word list or uploads new one
   - Sets sentence cap (Coverage mode only)
   - Clicks "Next"

2. **Step 2: Select Source**
   - User searches/filters processing history
   - Selects a source document (or imports from Sheets)
   - Clicks "Next"

3. **Step 3: Run & Review**
   - User clicks "Run Vocabulary Coverage"
   - Watches live progress
   - Reviews results when complete
   - Downloads CSV or exports to Sheets
   - Clicks "Finish" or "Start New Analysis"

## Technical Details

### Layout Changes
- **Before**: 3-column grid (`gridTemplateColumns: 'repeat(3, 1fr)'`)
- **After**: Single-column Paper with conditional rendering based on `activeStep`

### Validation Logic
```typescript
const isNextDisabled = React.useMemo(() => {
  if (activeStep === 0) return false;
  if (activeStep === 1) return !sourceId;
  return true;
}, [activeStep, sourceId]);
```

### Auto-progression
```typescript
useEffect(() => {
  if (currentRunId && activeStep < 2) {
    setActiveStep(2); // Jump to results when run starts
  }
}, [currentRunId, activeStep]);
```

## Benefits

1. **Improved User Flow**: Sequential steps guide users through the process
2. **Better Mobile UX**: Single column works better on small screens
3. **Clearer State**: Users always know where they are in the process
4. **Focused Attention**: One task at a time, less overwhelming
5. **Validation Feedback**: Next button disabled until requirements met
6. **Flexible Navigation**: Users can go back to change settings

## File Modified
- `frontend/src/app/coverage/page.tsx` (1,200+ lines)

## Testing Checklist
- [ ] Step navigation works (Back/Next buttons)
- [ ] Validation prevents skipping step 2 without source
- [ ] URL parameter `?runId=X` jumps to step 2
- [ ] Run starts and jumps to step 2 automatically
- [ ] "Start New Analysis" resets to step 0
- [ ] All original features still work (export, download, etc.)
- [ ] Mobile responsive (single column layout)
- [ ] WebSocket updates work during processing
- [ ] Error states display correctly

# Batch Analysis UI - Visual Guide

## Before (Single Source Mode)

```
┌─────────────────────────────────────────────┐
│  Select a Source                            │
│  Choose a previously processed document     │
├─────────────────────────────────────────────┤
│  🔍 Search by name or ID...                 │
├─────────────────────────────────────────────┤
│  ┌───────────────────────────────────────┐  │
│  │ 📄 Novel A.pdf               (○)     │  │  ← Radio Button
│  │ ID #1 • 5000 sentences • 12/1/24     │  │
│  └───────────────────────────────────────┘  │
│  ┌───────────────────────────────────────┐  │
│  │ 📄 Novel B.pdf               ( )     │  │
│  │ ID #2 • 3000 sentences • 12/2/24     │  │
│  └───────────────────────────────────────┘  │
│  ┌───────────────────────────────────────┐  │
│  │ 📄 Novel C.pdf               ( )     │  │
│  │ ID #3 • 2000 sentences • 12/3/24     │  │
│  └───────────────────────────────────────┘  │
└─────────────────────────────────────────────┘
```

## After (Batch Mode Enabled)

```
┌─────────────────────────────────────────────┐
│  Select Sources                             │
│  Select multiple novels for batch analysis  │
│  (minimum 2 required)                       │
├─────────────────────────────────────────────┤
│  🔘 Batch Analysis Mode                     │  ← Toggle Switch
│     Process multiple novels sequentially    │
│     for maximum coverage efficiency         │
│                              [3 selected]    │  ← Count Chip
├─────────────────────────────────────────────┤
│  🔍 Search by name or ID...                 │
├─────────────────────────────────────────────┤
│  ┌───────────────────────────────────────┐  │
│  │ 📄 Novel A.pdf               [✓]     │  │  ← Checkbox
│  │ ID #1 • 5000 sentences • 12/1/24     │  │
│  └───────────────────────────────────────┘  │
│  ┌───────────────────────────────────────┐  │
│  │ 📄 Novel B.pdf               [✓]     │  │
│  │ ID #2 • 3000 sentences • 12/2/24     │  │
│  └───────────────────────────────────────┘  │
│  ┌───────────────────────────────────────┐  │
│  │ 📄 Novel C.pdf               [✓]     │  │
│  │ ID #3 • 2000 sentences • 12/3/24     │  │
│  └───────────────────────────────────────┘  │
└─────────────────────────────────────────────┘
```

## Run Button Changes

### Single Mode
```
┌─────────────────────────────┐
│   ▶ Run Coverage Analysis   │
└─────────────────────────────┘

This will start the analysis and may
take a few minutes.
```

### Batch Mode
```
┌─────────────────────────────┐
│   ▶ Run Batch Analysis      │
└─────────────────────────────┘

Batch mode will process 3 sources
sequentially for maximum coverage.
```

## Results Display - NEW!

### Batch Analysis Summary Card

```
┌─────────────────────────────────────────────────────┐
│  📊 Batch Analysis Summary                          │
│  Sequential processing of 3 sources                 │
├─────────────────────────────────────────────────────┤
│  Coverage by Source:                                │
│                                                     │
│  ┌─────────────────────────────────────────────┐   │
│  │ Source 1 (ID: 1)         350 sentences      │   │
│  │                          1200 new words     │   │
│  └─────────────────────────────────────────────┘   │
│                                                     │
│  ┌─────────────────────────────────────────────┐   │
│  │ Source 2 (ID: 2)         120 sentences      │   │
│  │                          750 new words      │   │
│  └─────────────────────────────────────────────┘   │
│                                                     │
│  ┌─────────────────────────────────────────────┐   │
│  │ Source 3 (ID: 3)         30 sentences       │   │
│  │                          50 new words       │   │
│  └─────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────┘
```

## Key UI Elements

### 1. Batch Mode Toggle
- **Component**: Material-UI Switch
- **Label**: "Batch Analysis Mode"
- **Description**: "Process multiple novels sequentially for maximum coverage efficiency"
- **Effect**: Changes selection UI from radio buttons to checkboxes

### 2. Selected Count Chip
- **Component**: Material-UI Chip
- **Visibility**: Only shown in batch mode
- **Color**: Green if ≥2 selected, gray otherwise
- **Text**: "{count} selected"

### 3. Selection Cards
- **Border**: Thicker blue border when selected
- **Background**: Light blue tint when selected
- **Selector**: Radio button (single) or Checkbox (batch)
- **Hover Effect**: Blue border preview

### 4. Validation
- **Single Mode**: Requires 1 source selected
- **Batch Mode**: Requires minimum 2 sources selected
- **Next Button**: Disabled until requirement met

### 5. Source Breakdown Card
- **Appearance**: Light blue background with blue border
- **Content**: Shows contribution per source
- **Chips**: Count chips for sentences and words
- **Order**: Matches processing order

## User Flow Diagram

```
START
  ↓
[Step 1: Configure]
  • Select mode (Coverage/Filter)
  • Choose wordlist
  • Set options
  ↓
[Step 2: Select Source(s)]
  • Toggle: Single ⟷ Batch
  • Select source(s)
  • Validate: 1+ (single) or 2+ (batch)
  ↓
[Step 3: Run & Review]
  • Click "Run Batch Analysis"
  • Progress bar shows completion
  • WebSocket updates in real-time
  ↓
[Results]
  • KPI cards (sentences, words, coverage)
  • Batch Summary (if batch mode)
    - Source breakdown
    - Sequential reduction visible
  • Learning Set table
  • Export options (CSV, Sheets)
  ↓
END
```

## Color Scheme

- **Primary Blue**: #2196F3 (buttons, selected borders)
- **Success Green**: #4CAF50 (chips, covered words)
- **Background Selected**: rgba(33, 150, 243, 0.08)
- **Border Selected**: #2196F3, 2px
- **Border Hover**: #2196F3, 1px

## Responsive Behavior

### Desktop (>= 900px)
- Full-width cards with icons on left
- 3 cards per row for KPIs
- Side-by-side action buttons

### Tablet (600-900px)
- Full-width cards
- 2 cards per row for KPIs
- Stacked action buttons

### Mobile (< 600px)
- Full-width everything
- 1 card per row
- Stacked all buttons
- Smaller chips and text

## Accessibility

- **Keyboard Navigation**: Full tab support
- **Screen Readers**: Proper ARIA labels
- **Focus Indicators**: Visible focus rings
- **Color Contrast**: WCAG AA compliant
- **Touch Targets**: Minimum 44x44px

## Animation

- **Toggle Switch**: Smooth slide animation (200ms)
- **Card Selection**: Border and background fade (150ms)
- **Chip Appearance**: Scale-in animation (200ms)
- **Progress Bar**: Determinate linear progress

## Technical Implementation

### State Management

```typescript
const [isBatchMode, setIsBatchMode] = useState(false);
const [sourceId, setSourceId] = useState('');          // Single mode
const [selectedSourceIds, setSelectedSourceIds] = useState<number[]>([]);  // Batch mode

const handleBatchModeToggle = () => {
  setIsBatchMode(!isBatchMode);
  setSourceId('');
  setSelectedSourceIds([]);
};

const handleToggleSourceSelection = (historyId: number) => {
  if (isBatchMode) {
    // Multi-select logic
    setSelectedSourceIds(prev => 
      prev.includes(historyId) 
        ? prev.filter(id => id !== historyId)
        : [...prev, historyId]
    );
  } else {
    // Single-select logic
    setSourceId(String(historyId));
  }
};
```

### Validation Logic

```typescript
const isNextDisabled = useMemo(() => {
  if (activeStep === 1) {
    if (isBatchMode) {
      return selectedSourceIds.length < 2;  // Batch needs 2+
    } else {
      return !sourceId;  // Single needs 1
    }
  }
  return false;
}, [activeStep, sourceId, selectedSourceIds, isBatchMode]);
```

## Summary

The UI changes are minimal yet impactful:
1. **One toggle switch** to enable batch mode
2. **Radio → Checkbox** transition for multi-select
3. **Count chip** for visual feedback
4. **Source breakdown card** in results
5. **Dynamic labels** that adapt to mode

The design maintains consistency with the existing Material-UI theme while adding the powerful batch analysis capability in an intuitive way.

# Coverage Analysis Wizard - Visual Flow

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    Vocabulary Coverage Tool                              │
│  Analyze sentences based on high-frequency vocabulary. Perfect for      │
│  creating optimized language learning materials.                        │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│  Stepper Progress Bar:                                                   │
│  ━━━━━━━━━━━━━━━━━━━●━━━━━━━━━━━━━━━━━━━━━○━━━━━━━━━━━━━━━━━━━━━━○     │
│     Configure          Select Source         Run & Review               │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│                                                                           │
│  STEP CONTENT (Conditional rendering based on activeStep)               │
│                                                                           │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                                                                   │   │
│  │  activeStep === 0: Configure Analysis                           │   │
│  │  • Analysis Mode (Coverage/Filter) dropdown                     │   │
│  │  • Target Word List dropdown                                    │   │
│  │  • Upload New List button                                       │   │
│  │  • Learning Set Size slider (if Coverage mode)                  │   │
│  │                                                                   │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                           │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                                                                   │   │
│  │  activeStep === 1: Select Source                                │   │
│  │  • Search bar                                                    │   │
│  │  • Import from Sheets button                                    │   │
│  │  • Scrollable list of processing history                        │   │
│  │    ┌─────────────────────────────────────────────┐             │   │
│  │    │ [PDF Icon] Filename                [Radio]  │ ← Selected  │   │
│  │    │ ID #123 • 500 sentences • 10/8/25           │             │   │
│  │    └─────────────────────────────────────────────┘             │   │
│  │                                                                   │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                           │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                                                                   │   │
│  │  activeStep === 2: Run & Review                                 │   │
│  │                                                                   │   │
│  │  STATE: Initial (no currentRunId)                               │   │
│  │  ┌───────────────────────────────────────────────────────┐     │   │
│  │  │  [Big "Run Vocabulary Coverage" button]                │     │   │
│  │  │  Costs 100 Credits                                     │     │   │
│  │  └───────────────────────────────────────────────────────┘     │   │
│  │                                                                   │   │
│  │  STATE: Processing                                              │   │
│  │  ┌───────────────────────────────────────────────────────┐     │   │
│  │  │  Analyzing vocabulary...                         45%   │     │   │
│  │  │  ▓▓▓▓▓▓▓▓▓▓▓▓▓▓░░░░░░░░░░░░░░                        │     │   │
│  │  │  [Live Updates] chip                                   │     │   │
│  │  └───────────────────────────────────────────────────────┘     │   │
│  │                                                                   │   │
│  │  STATE: Completed                                               │   │
│  │  ┌───────────────────────────────────────────────────────┐     │   │
│  │  │  [KPI Cards: Sentences Selected, Words Covered, etc.]  │     │   │
│  │  │  [Download CSV] [Export to Sheets]                     │     │   │
│  │  │  Preview Results (first 10 rows)                       │     │   │
│  │  │  [Start New Analysis]                                  │     │   │
│  │  └───────────────────────────────────────────────────────┘     │   │
│  │                                                                   │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                           │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│  Navigation Buttons:                                                     │
│                                                                           │
│  [← Back]                                            [Next →]            │
│   (disabled on step 0)            (disabled when validation fails)      │
│                                              (shows "Finish" on step 2)  │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│  Full Results Section (only visible when coverageRun.status === 'completed')
│                                                                           │
│  Full Results                                                            │
│  ─────────────────────────────────────────────────────────────────      │
│  [Complete table with all results]                                      │
└─────────────────────────────────────────────────────────────────────────┘
```

## State Flow Diagram

```
┌─────────────┐
│   Start     │
│ (activeStep │
│    = 0)     │
└──────┬──────┘
       │
       ▼
┌─────────────────────┐
│  Step 0: Configure  │
│  ─────────────────  │
│  • Select mode      │
│  • Choose word list │
│  • Set sentence cap │
└──────┬──────────────┘
       │ [Next] (always enabled)
       ▼
┌─────────────────────┐
│ Step 1: Select Src  │
│ ──────────────────  │
│ • Search history    │
│ • Import from Sheets│
│ • Select source     │
└──────┬──────────────┘
       │ [Next] (disabled if !sourceId)
       ▼
┌─────────────────────┐
│ Step 2: Run & Review│
│ ──────────────────  │
│ • Click Run button  │
│   ↓                 │
│ • Processing (45%)  │◄────┐ WebSocket
│   ↓                 │     │ updates
│ • View Results      │─────┘
│ • Export/Download   │
└──────┬──────────────┘
       │ [Start New Analysis]
       ▼
┌─────────────┐
│  Reset to   │
│  Step 0     │
└─────────────┘
```

## Validation Rules

| Step | Condition              | Next Button State |
|------|------------------------|-------------------|
| 0    | Any state              | ✅ Enabled        |
| 1    | No source selected     | ❌ Disabled       |
| 1    | Source selected        | ✅ Enabled        |
| 2    | Final step             | ❌ Disabled       |

## Auto-progression Triggers

1. **URL Parameter**: `?runId=123` → Auto-jump to Step 2
2. **Run Started**: `currentRunId` changes from null → Auto-jump to Step 2
3. **New Analysis**: "Start New Analysis" clicked → Reset to Step 0

## Responsive Behavior

- Desktop: Full-width single column (maxWidth: xl container)
- Mobile: Same layout, optimized for vertical scrolling
- Step content: Conditional max-width (600px) for configure step
- Source list: Scrollable with fixed height

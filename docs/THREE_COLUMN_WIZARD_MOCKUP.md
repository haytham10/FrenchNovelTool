# Three-Column Wizard Layout - Visual Mockup

## Desktop View (Before Running)

```
╔════════════════════════════════════════════════════════════════════════════════════╗
║                         Vocabulary Coverage Tool                                   ║
║     Analyze sentences based on high-frequency vocabulary                           ║
╠═══════════════════════╦═══════════════════════╦════════════════════════════════════╣
║   ① CONFIGURE         ║   ② SELECT SOURCE     ║   ③ RUN ANALYSIS                   ║
╠═══════════════════════╬═══════════════════════╬════════════════════════════════════╣
║                       ║                       ║                                    ║
║ Analysis Mode     [?] ║ 🔍 Search by name...  ║                                    ║
║ ┌───────────────────┐ ║ ┌───────────────────┐ ║         ┌──────────────────┐       ║
║ │ Coverage Mode   ▼ │ ║ │ ☁ Import from     │ ║         │                  │       ║
║ └───────────────────┘ ║ │   Google Sheets   │ ║         │                  │       ║
║                       ║ └───────────────────┘ ║         │                  │       ║
║ Target Word List      ║                       ║         │      ▶ RUN       │       ║
║ ┌───────────────────┐ ║ ┏━━━━━━━━━━━━━━━━━━┓ ║         │   VOCABULARY     │       ║
║ │ French 2k ★     ▼ │ ║ ┃ 📄 Novel.pdf     ┃ ║         │    COVERAGE      │       ║
║ └───────────────────┘ ║ ┃ ID #123 • 1.5k   ┃ ║         │                  │       ║
║                       ║ ┃ sentences • 1/5  ┃◄╋━━━━━━━━▶│                  │       ║
║ + Upload New List     ║ ┗━━━━━━━━━━━━━━━━━━┛ ║         └──────────────────┘       ║
║                       ║                       ║                                    ║
║ Learning Set Size     ║ ┌──────────────────┐ ║        [ Costs 2 Credits ]         ║
║ ├─────●────────────┤  ║ │ 📊 Sheet Import  │ ║                                    ║
║ 100  500  1000  ∞     ║ │ ID #124 • 800    │ ║   Select a source from Column 2    ║
║                       ║ │ sentences • 1/6  │ ║        to continue                 ║
║ 500 sentences         ║ └──────────────────┘ ║                                    ║
║                       ║                       ║                                    ║
║                       ║ ┌──────────────────┐ ║                                    ║
║                       ║ │ 📄 Book.pdf      │ ║                                    ║
║  (Static Config)      ║ │ ID #125 • 2.1k   │ ║       (Initial State)              ║
║                       ║ │ sentences • 1/7  │ ║                                    ║
║                       ║ └──────────────────┘ ║                                    ║
║                       ║                       ║                                    ║
║                       ║   (Scrollable)        ║                                    ║
╚═══════════════════════╩═══════════════════════╩════════════════════════════════════╝
```

## Desktop View (Processing)

```
╔════════════════════════════════════════════════════════════════════════════════════╗
║                         Vocabulary Coverage Tool                                   ║
╠═══════════════════════╦═══════════════════════╦════════════════════════════════════╣
║   ① CONFIGURE         ║   ② SELECT SOURCE     ║   ③ PROCESSING...                  ║
╠═══════════════════════╬═══════════════════════╬════════════════════════════════════╣
║                       ║                       ║                                    ║
║ Analysis Mode     [?] ║ 🔍 Search by name...  ║ Analyzing vocabulary...            ║
║ ┌───────────────────┐ ║                       ║                                    ║
║ │ Coverage Mode   ▼ │ ║ ┏━━━━━━━━━━━━━━━━━━┓ ║ ████████████░░░░░░░░  67%          ║
║ └───────────────────┘ ║ ┃ 📄 Novel.pdf   ✓ ┃ ║                                    ║
║                       ║ ┃ ID #123 • 1.5k   ┃ ║ [ ✓ Live Updates ]                 ║
║ Target Word List      ║ ┃ sentences • 1/5  ┃ ║                                    ║
║ ┌───────────────────┐ ║ ┗━━━━━━━━━━━━━━━━━━┛ ║                                    ║
║ │ French 2k ★     ▼ │ ║                       ║                                    ║
║ └───────────────────┘ ║ ┌──────────────────┐ ║                                    ║
║                       ║ │ 📊 Sheet Import  │ ║                                    ║
║ + Upload New List     ║ │ ID #124 • 800    │ ║                                    ║
║                       ║ │ sentences • 1/6  │ ║                                    ║
║ Learning Set Size     ║ └──────────────────┘ ║                                    ║
║ ├─────●────────────┤  ║                       ║      ┌──────────────────┐          ║
║ 100  500  1000  ∞     ║ ┌──────────────────┐ ║      │  ⊗ Cancel Run    │          ║
║                       ║ │ 📄 Book.pdf      │ ║      │  (Coming soon)   │          ║
║ 500 sentences         ║ │ ID #125 • 2.1k   │ ║      └──────────────────┘          ║
║                       ║ │ sentences • 1/7  │ ║                                    ║
║                       ║ └──────────────────┘ ║                                    ║
║  (Static Config)      ║                       ║    (Processing State)              ║
║                       ║   (Scrollable)        ║                                    ║
╚═══════════════════════╩═══════════════════════╩════════════════════════════════════╝
```

## Desktop View (Results)

```
╔════════════════════════════════════════════════════════════════════════════════════╗
║                         Vocabulary Coverage Tool                                   ║
╠═══════════════════════╦═══════════════════════╦════════════════════════════════════╣
║   ① CONFIGURE         ║   ② SELECT SOURCE     ║   ③ RESULTS                        ║
╠═══════════════════════╬═══════════════════════╬════════════════════════════════════╣
║                       ║                       ║                                    ║
║ Analysis Mode     [?] ║ 🔍 Search by name...  ║ ┌────────────────────┐             ║
║ ┌───────────────────┐ ║                       ║ │ Sentences Selected │             ║
║ │ Coverage Mode   ▼ │ ║ ┏━━━━━━━━━━━━━━━━━━┓ ║ │       487          │             ║
║ └───────────────────┘ ║ ┃ 📄 Novel.pdf   ✓ ┃ ║ └────────────────────┘             ║
║                       ║ ┃ ID #123 • 1.5k   ┃ ║                                    ║
║ Target Word List      ║ ┃ sentences • 1/5  ┃ ║ ┌────────────────────┐             ║
║ ┌───────────────────┐ ║ ┗━━━━━━━━━━━━━━━━━━┛ ║ │  Words Covered     │             ║
║ │ French 2k ★     ▼ │ ║                       ║ │      1,856         │             ║
║ └───────────────────┘ ║ ┌──────────────────┐ ║ └────────────────────┘             ║
║                       ║ │ 📊 Sheet Import  │ ║                                    ║
║ + Upload New List     ║ │ ID #124 • 800    │ ║ ┌────────────────────┐             ║
║                       ║ │ sentences • 1/6  │ ║ │ Vocabulary Cov. %  │             ║
║ Learning Set Size     ║ └──────────────────┘ ║ │      92.8%         │             ║
║ ├─────●────────────┤  ║                       ║ └────────────────────┘             ║
║ 100  500  1000  ∞     ║ ┌──────────────────┐ ║                                    ║
║                       ║ │ 📄 Book.pdf      │ ║ ┌──────────┬──────────┐            ║
║ 500 sentences         ║ │ ID #125 • 2.1k   │ ║ │ Download │  Export  │            ║
║                       ║ │ sentences • 1/7  │ ║ │   CSV    │ to Sheet │            ║
║                       ║ └──────────────────┘ ║ └──────────┴──────────┘            ║
║                       ║                       ║                                    ║
║  (Static Config)      ║   (Scrollable)        ║ Preview Results                    ║
║                       ║                       ║ • Sentence 1...                    ║
║                       ║                       ║ • Sentence 2...                    ║
║                       ║                       ║ • Sentence 3...                    ║
║                       ║                       ║ [View Full Results Below]          ║
║                       ║                       ║                                    ║
║                       ║                       ║ [Start New Analysis]               ║
╚═══════════════════════╩═══════════════════════╩════════════════════════════════════╝
```

## Mobile View (Stacked)

```
╔════════════════════════════════════╗
║   Vocabulary Coverage Tool         ║
╠════════════════════════════════════╣
║                                    ║
║  ① CONFIGURE                       ║
║  ────────────────────────────────  ║
║                                    ║
║  Analysis Mode              [?]    ║
║  ┌──────────────────────────────┐  ║
║  │ Coverage Mode              ▼ │  ║
║  └──────────────────────────────┘  ║
║                                    ║
║  Target Word List                  ║
║  ┌──────────────────────────────┐  ║
║  │ French 2k ★                ▼ │  ║
║  └──────────────────────────────┘  ║
║                                    ║
║  + Upload New List (.csv)          ║
║                                    ║
║  Learning Set Size                 ║
║  ├──────●─────────────────────┤    ║
║  100   500   1000            ∞     ║
║                                    ║
║  500 sentences                     ║
║                                    ║
╠════════════════════════════════════╣
║                                    ║
║  ② SELECT SOURCE                   ║
║  ────────────────────────────────  ║
║                                    ║
║  🔍 Search by name or ID...        ║
║                                    ║
║  ┌──────────────────────────────┐  ║
║  │ ☁ Import from Google Sheets │  ║
║  └──────────────────────────────┘  ║
║                                    ║
║  ┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓  ║
║  ┃ 📄 Novel.pdf                ┃  ║
║  ┃ ID #123 • 1.5k sentences    ┃  ║
║  ┃ 1/5/2025                 ◉  ┃  ║
║  ┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛  ║
║                                    ║
║  ┌────────────────────────────────┐║
║  │ 📊 Sheet Import               │║
║  │ ID #124 • 800 sentences    ○ │║
║  │ 1/6/2025                      │║
║  └────────────────────────────────┘║
║                                    ║
╠════════════════════════════════════╣
║                                    ║
║  ③ RUN ANALYSIS                    ║
║  ────────────────────────────────  ║
║                                    ║
║                                    ║
║      ┌──────────────────────┐      ║
║      │                      │      ║
║      │        ▶ RUN         │      ║
║      │     VOCABULARY       │      ║
║      │      COVERAGE        │      ║
║      │                      │      ║
║      └──────────────────────┘      ║
║                                    ║
║       [ Costs 2 Credits ]          ║
║                                    ║
║  Select a source from above to     ║
║  continue                          ║
║                                    ║
╚════════════════════════════════════╝
```

## Key Visual Elements

### Icons Used
- 📄 PDF document icon
- 📊 Spreadsheet/Sheets icon
- 🔍 Search magnifying glass
- ☁ Cloud upload
- ▶ Play/Run button
- ⊗ Cancel button
- ✓ Checkmark/selected
- ◉ ○ Radio buttons (selected/unselected)
- [?] Help/info icon
- ▼ Dropdown arrow
- ● Slider handle
- ★ Star (default indicator)

### Color Scheme Indicators
- ┏━━━┓ Selected state (blue border)
- ┌───┐ Normal state (gray border)
- ████░ Progress bar (filled/unfilled)
- [ text ] Chip/badge
- ├───┤ Slider track

### Typography Hierarchy
- ╔═══╗ Main headers (h3-h4)
- ║ ① ║ Numbered sections (h6)
- Large buttons use larger text
- KPI numbers are prominent (h4)
- Secondary info uses smaller text

### Spacing
- Generous white space between elements
- Consistent padding within cards
- Clear visual separation between columns
- Grouped related elements

### Interactive States
1. **Default:** Clean, minimal borders
2. **Hover:** Slightly darker border, subtle shadow
3. **Selected:** Blue border, selected background
4. **Disabled:** Grayed out, reduced opacity
5. **Loading:** Spinner or progress indicator
6. **Error:** Red accent, alert styling

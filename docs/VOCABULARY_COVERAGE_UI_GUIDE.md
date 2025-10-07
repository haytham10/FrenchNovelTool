# Vocabulary Coverage Tool - UI Screenshots & Visual Guide

## Overview

This document provides a visual guide to the Vocabulary Coverage Tool's user interface. Since we're in a development environment, this serves as a reference for the implemented UI components and their visual appearance.

## 1. Settings Page - Word List Management

### Location
`/settings` → Vocabulary Coverage Settings section

### Visual Layout

```
┌─────────────────────────────────────────────────────────────┐
│ 📚 Vocabulary Coverage Settings                              │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│ Default Word List                                             │
│ ┌───────────────────────────────────────────────────────┐   │
│ │ Select: [French 2K Default (2000 words) (default) ▼] │   │
│ └───────────────────────────────────────────────────────┘   │
│ ℹ️ Select the default word list for vocabulary coverage      │
│    analysis. Manage word lists on the Coverage page.         │
│                                                               │
│ ─────────────────────────────────────────────────────────   │
│                                                               │
│ Upload New Word List                                          │
│ ┌──────────────┬──────────────────────────┐                 │
│ │ CSV File ✓   │ Google Sheets Link       │                 │
│ └──────────────┴──────────────────────────┘                 │
│                                                               │
│ [Choose CSV File]  [filename.csv]  [Upload]                  │
│                                                               │
│ ─────────────────────────────────────────────────────────   │
│                                                               │
│ Manage Word Lists                                             │
│                                                               │
│ ┌───────────────────────────────────────────────────────┐   │
│ │ French 2K Default                                  🗑️ │   │
│ │ 2000 words • CSV Upload • Global Default • Your Default │ │
│ └───────────────────────────────────────────────────────┘   │
│                                                               │
│ ┌───────────────────────────────────────────────────────┐   │
│ │ My Custom List                                      🗑️ │   │
│ │ 1500 words • Google Sheets                            │   │
│ └───────────────────────────────────────────────────────┘   │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

### Key Elements
- **Default Word List Dropdown**: Shows all accessible lists with counts
- **Upload Tabs**: Switch between CSV file upload and Google Sheets import
- **Word Lists Grid**: Click to select as default, trash icon to delete
- **Visual Indicators**: Chips showing "Global Default" and "Your Default"

## 2. Coverage Page - Configuration

### Location
`/coverage`

### Visual Layout

```
┌─────────────────────────────────────────────────────────────┐
│ Home > Vocabulary Coverage                                   │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│ Vocabulary Coverage Tool                                      │
│ Analyze sentences based on high-frequency vocabulary.         │
│                                                               │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ Configuration                                             │ │
│ │                                                           │ │
│ │ Analysis Mode                                             │ │
│ │ ┌─────────────────────────────────────────────────────┐ │ │
│ │ │ Filter Mode - High-density vocabulary sentences ▼  │ │ │
│ │ └─────────────────────────────────────────────────────┘ │ │
│ │ ℹ️ Filter Mode: Prioritizes 4-word sentences...          │ │
│ │                                                           │ │
│ │ Word List                                                 │ │
│ │ ┌─────────────────────────────────────────────────────┐ │ │
│ │ │ French 2K Default (2000 words) (default)         ▼ │ │ │
│ │ └─────────────────────────────────────────────────────┘ │ │
│ │                                                           │ │
│ │ Or upload a new word list (CSV):                         │ │
│ │ [Choose File]  [filename.csv]  [Upload]                  │ │
│ │                                                           │ │
│ │ ───────────────────────────────────────────────────────  │ │
│ │                                                           │ │
│ │ Select Source (From History)                             │ │
│ │ ┌─────────────────────────────────────────────────────┐ │ │
│ │ │ 🔍 Search by PDF name or ID                         │ │ │
│ │ └─────────────────────────────────────────────────────┘ │ │
│ │                                                           │ │
│ │ ┌─────────────────────────────────────────────────────┐ │ │
│ │ │ ✓ Novel_Chapter1.pdf                                │ │ │
│ │ │   ID #45 • Job #23 • 2 hours ago • 1234 sentences   │ │ │
│ │ ├─────────────────────────────────────────────────────┤ │ │
│ │ │   Novel_Chapter2.pdf                                │ │ │
│ │ │   ID #44 • Job #22 • 5 hours ago • 987 sentences    │ │ │
│ │ └─────────────────────────────────────────────────────┘ │ │
│ │                                                           │ │
│ │ [▶️ Run Vocabulary Coverage]                              │ │
│ └─────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### Key Elements
- **Mode Selector**: Dropdown with inline description
- **Word List Selector**: Shows default with visual indicator
- **Source Selector**: Searchable history list with details
- **Run Button**: Large, primary action button

## 3. Coverage Page - Results (Filter Mode)

### Visual Layout

```
┌─────────────────────────────────────────────────────────────┐
│ Results                                                       │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│ Status: [Completed ✓]                                        │
│                                                               │
│ [📥 Download CSV]  [📥 Export to Sheets]                     │
│                                                               │
│ ─────────────────────────────────────────────────────────   │
│                                                               │
│ Statistics:                                                   │
│   Total sentences: 1234                                       │
│   Passed filter: 567                                          │
│   Selected: 500                                               │
│   Acceptance ratio: 45.9%                                     │
│                                                               │
│ ─────────────────────────────────────────────────────────   │
│                                                               │
│ Top Sentences                                                 │
│                                                               │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ Total: 500 | Avg Length: 4.2w | Avg Score: 8.7 | 3.2-10 │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                               │
│ 🔍 [Search sentences...]                                     │
│                                                               │
│ ┌───┬───────────────────────────┬───────┬────────┬────────┐ │
│ │ # │ Sentence                  │ Score │ Length │ Actions│ │
│ ├───┼───────────────────────────┼───────┼────────┼────────┤ │
│ │⭐1│ Je vais à la maison.      │ 9.8   │ [4w]   │   🚫  │ │
│ │   │                           │ ████  │        │        │ │
│ ├───┼───────────────────────────┼───────┼────────┼────────┤ │
│ │⭐2│ Elle mange du pain.       │ 9.5   │ [4w]   │   🚫  │ │
│ │   │                           │ ███▓  │        │        │ │
│ ├───┼───────────────────────────┼───────┼────────┼────────┤ │
│ │ 3│ Il est très bien.         │ 8.2   │ [4w]   │   🚫  │ │
│ │   │                           │ ██▓   │        │        │ │
│ └───┴───────────────────────────┴───────┴────────┴────────┘ │
│                                                               │
│ [< Previous]  Page 1 of 20  [Next >]  [25 per page ▼]      │
│                                                               │
│ Showing 25 of 500 sentences                                   │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

### Key Elements
- **Stats Summary Panel**: Total, avg length, avg score, score range
- **Search Bar**: Filter sentences by text
- **Results Table**:
  - Rank column with star indicators for top 10
  - Sentence text
  - Score with visual progress bar
  - Word count chip (color-coded: green=4w, blue=3w)
  - Exclude button
- **Pagination**: Controls at bottom

## 4. Coverage Page - Results (Coverage Mode)

### Visual Layout

```
┌─────────────────────────────────────────────────────────────┐
│ Results                                                       │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│ Statistics:                                                   │
│   Total words: 2000                                           │
│   Covered: 1847                                               │
│   Uncovered: 153                                              │
│   Selected sentences: 524                                     │
│                                                               │
│ ─────────────────────────────────────────────────────────   │
│                                                               │
│ Word Assignments                                              │
│                                                               │
│ 🔍 [Search by word or sentence...]                           │
│                                                               │
│ ┌──────┬──────────────────────────┬───────┬───────┬────────┐│
│ │ Word │ Assigned Sentence        │ Score │ Index │ Actions││
│ ├──────┼──────────────────────────┼───────┼───────┼────────┤│
│ │maison│ Je vais à la maison.     │ 8.5   │  142  │   ⇄   ││
│ │      │ Matched: maison          │       │       │        ││
│ ├──────┼──────────────────────────┼───────┼───────┼────────┤│
│ │manger│ Elle mange du pain.      │ 7.8   │  89   │   ⇄   ││
│ │(man.)│ Matched: mange           │       │       │        ││
│ │Manual│                           │       │       │        ││
│ ├──────┼──────────────────────────┼───────┼───────┼────────┤│
│ │bien  │ Il est très bien ici.    │ 6.2   │  201  │   ⇄   ││
│ │      │ Matched: bien            │       │       │        ││
│ └──────┴──────────────────────────┴───────┴───────┴────────┘│
│                                                               │
│ [< Previous]  Page 1 of 75  [Next >]  [25 per page ▼]       │
│                                                               │
│ Showing 25 of 1847 assignments                               │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

### Key Elements
- **Word Column**: Shows normalized word with original in parentheses
- **Manual Indicator**: Orange chip for manually edited assignments
- **Matched Surface**: Shows actual word form found in sentence
- **Swap Button**: Allows reassigning to different sentence
- **Search**: Filter by word or sentence text

## 5. Job Progress Dialog - Coverage CTA

### Visual Layout

```
┌─────────────────────────────────────────────────────────────┐
│ ✓ PDF Processing                            [Completed]      │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│ File: Novel_Chapter1.pdf                                     │
│                                                               │
│ ✓ Processing completed successfully!                         │
│   Time: 45s                                                   │
│   Tokens used: 12,345                                         │
│                                                               │
├─────────────────────────────────────────────────────────────┤
│                            [📚 Run Vocabulary Coverage] [Close]│
└─────────────────────────────────────────────────────────────┘
```

### Key Elements
- **Success Alert**: Green background with metrics
- **Coverage CTA**: Primary button appears on success
- **Disabled During Processing**: Button only shows when complete

## 6. History Detail Dialog - Coverage CTA

### Visual Layout

```
┌─────────────────────────────────────────────────────────────┐
│ Novel_Chapter1.pdf                                      [✕]  │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│ ID: #45  •  Job: #23  •  2 hours ago                        │
│ Status: ✓ Completed  •  1234 sentences                      │
│                                                               │
│ [Show Sentences ▼]  [Show Chunks ▼]                         │
│                                                               │
│ ... (sentences and chunks) ...                               │
│                                                               │
├─────────────────────────────────────────────────────────────┤
│ [Open Sheet]  [Copy Link]    [Close] [📚 Vocabulary Coverage]│
│                                       [📥 Export to Sheets]  │
└─────────────────────────────────────────────────────────────┘
```

### Key Elements
- **Coverage Button**: Appears with Export button when entry has sentences
- **Positioned Right**: In button group with export options

## 7. Coverage Run Dialog (CTA Modal)

### Visual Layout

```
┌─────────────────────────────────────────────────────────────┐
│ 📚 Run Vocabulary Coverage                                   │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│ ℹ️ Source: Novel_Chapter1.pdf                                │
│                                                               │
│ Analysis Mode                                                 │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ Filter Mode - High-density vocabulary sentences      ▼ │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                               │
│ 💡 Filter Mode: Prioritizes 4-word sentences...              │
│                                                               │
│ Word List                                                     │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ French 2K Default (2000 words) (default)             ▼ │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                               │
├─────────────────────────────────────────────────────────────┤
│                                [Cancel] [▶️ Run Coverage]    │
└─────────────────────────────────────────────────────────────┘
```

### Key Elements
- **Source Info**: Shows what will be analyzed
- **Mode Selection**: Quick dropdown
- **Word List Selection**: With default indicator
- **Inline Help**: Mode description shown
- **Action Buttons**: Cancel and Run

## UI Design Principles

### Color Coding
- **Green (Success)**: 4-word sentences, completed status, success indicators
- **Blue (Primary)**: 3-word sentences, primary actions, links
- **Orange (Warning)**: Manual edits, pending status
- **Red (Error)**: Failed status, delete actions
- **Gray (Default)**: Other word counts, disabled states

### Visual Hierarchy
1. **Page Title**: Large (h3), dark color
2. **Section Headers**: Medium (h5-h6), semi-bold
3. **Body Text**: Regular size, standard weight
4. **Helper Text**: Small (caption), secondary color
5. **Stats**: Large numbers, medium labels

### Responsive Breakpoints
- **Desktop (lg)**: Full layout with side-by-side panels
- **Tablet (md)**: Stacked panels, full-width tables
- **Mobile (xs)**: Single column, simplified tables

### Interactive Elements
- **Hover States**: Background color change on table rows
- **Loading States**: Circular progress indicators
- **Empty States**: Centered message with icon
- **Error States**: Red alert boxes with retry options

## Accessibility Features

- **ARIA Labels**: All interactive elements labeled
- **Keyboard Navigation**: Tab order logical, Enter to activate
- **Screen Reader Support**: Status announcements for async operations
- **Color Contrast**: WCAG AA compliant
- **Focus Indicators**: Visible focus rings on all interactive elements

## Mobile Optimizations

- **Touch Targets**: Minimum 44px for buttons and links
- **Scrollable Tables**: Horizontal scroll on mobile
- **Collapsible Sections**: Accordions for long content
- **Simplified Navigation**: Bottom sheet patterns for dialogs
- **Optimized Forms**: Native input types for better keyboard

---

This visual guide provides a comprehensive reference for the UI implementation. The actual rendered components follow Material-UI v7 design principles with custom theming and styling.

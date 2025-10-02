# UX & Design Roadmap

**Last Updated:** October 2, 2025

Focus: User experience improvements, accessibility, and design polish.

---

## 📊 Current State

### ✅ Completed (Phase 1)
- Clean Material-UI design
- Responsive layout
- Google OAuth integration
- File upload with drag-and-drop
- Snackbar notifications
- Loading states
- Onboarding for new users
- Feature highlights on landing page
- Tooltips for complex features
- Empty states with guidance

### ⚠️ Needs Improvement
- Export process could be more intuitive
- No dark mode
- Basic settings page
- Limited history features (no search/filter)
- No progress indication during long operations
- Generic error messages
- No keyboard shortcuts
- Missing accessibility features

---

## 🔴 P0 - Critical (Weeks 1-4)

### Week 1-2: Enhanced Upload Experience
**Make file upload delightful**

- [ ] **File preview**
  ```typescript
  <FileUpload>
    <FilePreview 
      name="novel.pdf"
      size="2.3 MB"
      thumbnail={pdfThumbnail}
      onRemove={handleRemove}
    />
  </FileUpload>
  ```

- [ ] **Better validation feedback**
  - Show clear error for oversized files
  - Warn about corrupted PDFs
  - Suggest fixes for common issues
  - Preview first page of PDF

- [ ] **Drag-and-drop improvements**
  - Highlight drop zone on drag over
  - Show allowed file types
  - Support multiple files (queue)
  - Progress bar per file

### Week 2-3: Processing Experience
**Show what's happening**

- [ ] **Multi-stage progress**
  ```typescript
  const stages = [
    { name: 'Uploading', progress: 25 },
    { name: 'Analyzing', progress: 50 },
    { name: 'Rewriting', progress: 75 },
    { name: 'Finalizing', progress: 100 }
  ];
  
  <ProgressStepper 
    stages={stages}
    current={currentStage}
  />
  ```

- [ ] **Estimated time remaining**
  ```typescript
  <Typography variant="caption">
    Estimated time: {estimateRemaining(startTime, progress)}
  </Typography>
  ```

- [ ] **Fun facts while waiting**
  - "Did you know? The average French novel has..."
  - "Tip: You can adjust sentence length in settings"
  - Rotate tips every 10 seconds

- [ ] **Cancellation**
  - Show "Cancel" button during processing
  - Confirm before canceling
  - Clean up resources on cancel

### Week 3: Results Display Improvements
**Make results actionable**

- [ ] **Enhanced table**
  ```typescript
  <ResultsTable>
    <TableRow>
      <TableCell width="5%">#</TableCell>
      <TableCell width="85%">
        Sentence
        <CopyButton />
        <EditButton />
      </TableCell>
      <TableCell width="10%">
        <Chip label="Rewritten" size="small" />
      </TableCell>
    </TableRow>
  </ResultsTable>
  ```

- [ ] **Inline editing**
  - Double-click to edit
  - Enter to save, Esc to cancel
  - Show unsaved indicator
  - Undo/redo support

- [ ] **Quick actions**
  - Copy individual sentence
  - Delete sentence
  - Mark as favorite
  - Add note/comment

### Week 4: Error Messages
**Make errors helpful**

- [ ] **Error templates**
  ```typescript
  const ERROR_MESSAGES = {
    NETWORK_ERROR: {
      title: \"Connection Lost\",
      message: \"Check your internet connection and try again.\",
      actions: [
        { label: \"Retry\", onClick: retry },
        { label: \"Save Draft\", onClick: saveDraft }
      ]
    },
    FILE_TOO_LARGE: {
      title: \"File Too Large\",
      message: \"Maximum file size is 50MB. Try compressing your PDF.\",
      actions: [
        { label: \"Learn How\", onClick: showHelp }
      ]
    },
    // ... more error types
  };
  ```

- [ ] **Contextual help**
  - Link to relevant documentation
  - Show similar successful examples
  - Suggest alternative approaches

---

## 🟠 P1 - High Priority (Weeks 5-8)

### Week 5: Search & Filter
**Find what you need quickly**

- [ ] **Results search**
  ```typescript
  <SearchBar 
    placeholder=\"Search sentences...\"
    debounceMs={300}
    onSearch={handleSearch}
  />
  ```

- [ ] **Advanced filters**
  - Show only rewritten sentences
  - Filter by length range
  - Filter by word content
  - Filter by position in document

- [ ] **History search**
  - Search by filename
  - Filter by date range
  - Filter by status (success/failed)
  - Sort by date/name/status

### Week 6: Sentence Statistics
**Show insights**

```typescript
<StatisticsPanel>
  <Stat label="Total Sentences" value={234} />
  <Stat label="Original" value={156} color="blue" />
  <Stat label="Rewritten" value={78} color="green" />
  <Stat label="Avg Length" value="7.3 words" />
  <Stat label="Longest" value="14 words" />
</StatisticsPanel>

<LengthDistributionChart data={lengthDistribution} />
```

### Week 7: Export Improvements
**Streamline export flow**

- [ ] **Export wizard**
  ```typescript
  <ExportWizard>
    <Step1 title="Choose Format">
      <FormatSelector options={['Google Sheets', 'CSV', 'DOCX']} />
    </Step1>
    <Step2 title="Configure Options">
      <SheetOptions />
    </Step2>
    <Step3 title="Review & Export">
      <Preview />
    </Step3>
  </ExportWizard>
  ```

- [ ] **Quick export**
  - "Export with last settings" button
  - Keyboard shortcut (Ctrl+E)
  - Show export history

- [ ] **Export preview**
  - Show how it will look
  - Preview first 10 rows
  - Confirm before creating

### Week 8: Accessibility
**WCAG 2.1 AA compliance**

- [ ] **Keyboard shortcuts**
  ```typescript
  const shortcuts = {
    'Ctrl+U': 'Upload file',
    'Ctrl+P': 'Process PDF',
    'Ctrl+E': 'Export results',
    'Ctrl+S': 'Save settings',
    '?': 'Show keyboard shortcuts'
  };
  
  <KeyboardShortcutsDialog shortcuts={shortcuts} />
  ```

- [ ] **Screen reader support**
  ```typescript
  <div role="status" aria-live="polite" aria-atomic="true">
    {processing ? 'Processing PDF, please wait' : 'Ready to process'}
  </div>
  ```

- [ ] **Focus indicators**
  - Visible focus rings
  - Logical tab order
  - Skip to main content link

---

## 🟡 P2 - Medium Priority (Weeks 9-12)

### Week 9: Dark Mode
**Eye comfort for night work**

```typescript
const theme = createTheme({
  palette: {
    mode: userPreference === 'dark' ? 'dark' : 'light',
  },
});

<IconButton onClick={toggleDarkMode}>
  {darkMode ? <LightModeIcon /> : <DarkModeIcon />}
</IconButton>
```

### Week 10: Batch Operations
**Work with multiple items**

- [ ] **Multi-select**
  - Checkbox column in tables
  - Select all/none
  - Select range (Shift+click)

- [ ] **Batch actions**
  - Delete selected
  - Export selected
  - Copy selected
  - Move to folder

### Week 11: Advanced Settings
**Power user features**

- [ ] **Settings organization**
  ```typescript
  <SettingsPage>
    <SettingsSection title="Processing">
      <SentenceLengthSlider />
      <ModelSelector />
      <AdvancedOptions />
    </SettingsSection>
    
    <SettingsSection title="Export">
      <DefaultFolder />
      <SheetNamePattern />
      <AutoExport />
    </SettingsSection>
    
    <SettingsSection title="Interface">
      <ThemeSelector />
      <Language />
      <KeyboardShortcuts />
    </SettingsSection>
  </SettingsPage>
  ```

- [ ] **Preset profiles**
  - "Academic" (longer sentences, formal)
  - "Quick Read" (shorter sentences, simple)
  - "Literary" (preserve style, longer OK)
  - Custom presets (save your settings)

### Week 12: Onboarding Polish
**Help new users succeed**

- [ ] **Interactive tutorial**
  ```typescript
  <Tour
    steps={[
      { target: '#upload', content: 'Start by uploading a PDF...' },
      { target: '#settings', content: 'Adjust sentence length here...' },
      { target: '#process', content: 'Click to process...' }
    ]}
  />
  ```

- [ ] **Sample PDF**
  - Provide test document
  - "Try it now" with sample
  - Show expected results

- [ ] **Video walkthrough**
  - 2-minute intro video
  - Embedded in app
  - Covers basic workflow

---

## 📊 Success Metrics

### Usability
- ✅ 90%+ users complete first upload successfully
- ✅ < 3 clicks to export
- ✅ < 5 seconds to find history item

### Accessibility
- ✅ Zero critical a11y violations (axe-core)
- ✅ All features work with keyboard
- ✅ Screen reader compatible

### Satisfaction
- ✅ 4.5+ star user rating
- ✅ 80%+ would recommend
- ✅ < 10% support requests about UX

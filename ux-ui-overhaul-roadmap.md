# French Novel Tool — UX/UI Overhaul Roadmap (Prioritized)

Context
Process French novel PDFs, normalize sentence length with Google Gemini AI, and export the results to Google Sheets through a polished web interface.

Priority definitions
- P0 Critical path: Must ship for a smooth login → export flow.
- P1 High: Quality-of-life, reliability, and control improvements.
- P2 Medium: Delight, scale, and advanced workflows.
- P3 Nice-to-have: Future polish and extensions.

Success metrics
- [ ] Time to first successful export < 3 minutes
- [ ] Export success rate > 98%
- [ ] Google integration error rate < 1%
- [ ] Onboarding completion rate > 85%
- [ ] Accessibility WCAG 2.1 AA baseline passes for core flow

Acceptance criteria (P0)
- [ ] A new user can sign in, connect Google, upload a PDF, configure normalization, review, and export to Sheets in under 3 minutes.
- [ ] Every long-running step shows live status, ETA, and supports cancel/retry.
- [ ] After export, user sees a working Sheet link and a History entry with success/failed status.
- [ ] Keyboard navigation and screen reader labels work for core pages (Upload, Review, Export, History).

---

## P0 — Critical Path (Foundation)

### 1) Onboarding & Authentication
- [ ] Replace landing with focused “Sign in with Google” CTA and clear scope explanations.
- [ ] OAuth: request least-privilege scopes (Drive folder picker + Sheets write).
- [ ] First-run wizard:
  - [ ] Pick default Drive destination folder (optional).
  - [ ] Set sheet naming pattern (e.g., “French Novel Sentences – {MM-DD}”).
  - [ ] Choose default sentence length limit (slider with sensible default).
- [ ] Privacy/Terms links; data retention summary.

### 2) Information Architecture & Global Navigation
- [ ] Global top nav: Dashboard, Process, History, Settings, Integrations, Help.
- [ ] Header badges: Google connection status (Connected/Not Connected), profile menu, theme toggle.
- [ ] Constrain content width (e.g., max-w-6xl) and unify page titles/subtitles.

### 3) Processing Flow (Stepper)
- [ ] 4-step stepper: Upload → Analyze → Normalize → Export/Done.
- [ ] Persist progress across refresh (local storage/server state).
- [ ] Route guards to prevent skipping mandatory steps.

### 4) Upload & Analyze
- [ ] Drag-and-drop upload (PDF only), multi-file disabled for P0 (single file).
- [ ] Validation: file type, size, page count; show friendly errors.
- [ ] Background job states with live progress: Queued → Extracting → Analyzing.
- [ ] OCR detection: surface hint if scanned PDF likely; toggle (informational placeholder ok in P0).

### 5) Normalize (Core Controls)
- [ ] Sentence length limit slider + preset chips (8, 12, 16).
- [ ] Token/time estimate placeholder; disable Export until normalization complete.
- [ ] Save selected settings with the processing run.

### 6) Review Results (Table — Core)
- [ ] Virtualized table (index + normalized sentence).
- [ ] Search/filter box (client-side).
- [ ] Sort by index; sticky header; zebra rows.
- [ ] Inline edit per row (Enter to save, Esc to cancel).
- [ ] Multi-select and delete/restore selected (optional for P0 if time-boxed).

### 7) Export to Google Sheets
- [ ] Folder picker modal (Google Drive Picker) with breadcrumb.
- [ ] Sheet name input with pattern helper and validation (illegal characters, duplicates).
- [ ] “Create new sheet” (append disabled for P0).
- [ ] Progress indicator; success toast; “Open in Google Sheets” + “Copy link”.

### 8) History
- [ ] Table: Timestamp, Filename, Sentences, Spreadsheet Link, Status, Error.
- [ ] Filters: status and search by filename.
- [ ] Row actions: Open sheet (if exists), View details/logs (basic).

### 9) Settings (Basics)
- [ ] Sentence length default setting with help text and presets.
- [ ] Default Drive folder and default sheet name pattern.
- [ ] “Save” button: primary style + confirmation toast.

### 10) Feedback & Error Handling
- [ ] Toasts: success, warning, error.
- [ ] Inline validation messages near fields.
- [ ] Retry buttons for failed jobs (Analyze/Export).
- [ ] Global banner if Google connection lost; “Reconnect” action.

### 11) Accessibility (Baseline)
- [ ] Semantic landmarks (header/nav/main/section).
- [ ] Labels for stepper, progress bars, and upload control.
- [ ] Keyboard navigation for upload, table row edit, export form.
- [ ] Color contrast meets 4.5:1 for text.

### 12) Design System (Minimum)
- [ ] Select UI library (Material 3 or shadcn/ui + Tailwind) and lock tokens (colors, spacing, radius).
- [ ] Typography scale standardized; button, input, card, table primitives.
- [ ] Light and dark theme parity for core components.

### 13) Performance & Reliability (Baseline)
- [ ] Web Workers or async processing to keep UI responsive on parsing.
- [ ] Debounce search/filter.
- [ ] Graceful handling for PDFs up to N pages (define N; e.g., 400).

### 14) Observability & QA (P0)
- [ ] Frontend error tracking (Sentry) and basic performance traces.
- [ ] E2E happy-path (Upload → Export) test (Playwright/Cypress).
- [ ] Accessibility automated checks (axe) in CI.

---

## P1 — High Priority (Quality & Control)

### 1) Advanced Normalization Controls
- [ ] Live preview: paste sample text and see split result.
- [ ] Options: ignore dialogues (—), preserve quotes/punctuation, fix hyphenations, min sentence length.
- [ ] Model selector (Gemini mode: balanced/quality/speed).

### 2) Export Enhancements
- [ ] Append to existing Sheet (choose tab or create new tab).
- [ ] Customizable headers and column order.
- [ ] Share settings: add collaborators; toggle “Anyone with link can view.”

### 3) Results Table Power-User Features
- [ ] Original vs Normalized toggle per row.
- [ ] Highlight “long sentences” with length meter.
- [ ] Bulk actions: approve all, export selected only.
- [ ] Column resize; keyboard multi-select with Shift.

### 4) History & Retry
- [ ] Robust error logs: show step that failed and error code.
- [ ] “Retry from failed step” and “Duplicate run with same settings.”

### 5) Usability, Copy, and States
- [ ] Empty states with illustrations and primary CTA.
- [ ] Loading skeletons across tables and cards.
- [ ] Microcopy audit: action-oriented labels; consistent tone.

### 6) Integrations UX
- [ ] Token expiration: silent refresh + “Reconnect” prompt.
- [ ] Quotas surfaced; troubleshooting guide modal.

### 7) Testing & Reliability
- [ ] Integration tests with mocked Google APIs + one live env.
- [ ] Visual regression tests for critical screens.
- [ ] Performance budget and regression guardrails.

### 8) Docs & Help
- [ ] In-app tooltips and “How normalization works” guide with examples.
- [ ] Troubleshooting pages: Drive permissions, OAuth errors, quota exceeded.
- [ ] Changelog surfaced in-app.

---

## P2 — Medium Priority (Delight & Scale)

### 1) Batch & Long-Running Jobs
- [ ] Batch processing multiple PDFs with queue and per-file status.
- [ ] Email notifications or in-app alerts for long jobs.
- [ ] Pause/resume processing; safe resume after refresh.

### 2) Dashboard & Analytics
- [ ] Usage cards: files processed, avg normalization time, tokens estimate.
- [ ] Funnel metrics: Connect → Upload → Configure → Review → Export → Success.

### 3) Collaboration & Profiles
- [ ] Saved normalization profiles (e.g., “Dialogue-heavy novels”).
- [ ] Share settings profiles with teammates.

### 4) Localization & Internationalization
- [ ] UI i18n; French UI option.
- [ ] Locale-aware dates/numbers.

### 5) Privacy & Data Control
- [ ] Data retention controls (auto-delete source and processed text after N days).
- [ ] “Delete my data” self-service.

### 6) Theming & Motion
- [ ] Polished dark mode tokens; elevation and focus states.
- [ ] Subtle page and table transitions respecting prefers-reduced-motion.

---

## P3 — Nice-to-have (Future)

- [ ] API endpoints for automation (upload, run, export).
- [ ] Alternative LLM backends (adapter pattern).
- [ ] Smart language detector with auto-warnings if non-French content dominates.
- [ ] Import from Google Drive directly (no local upload).
- [ ] Inline collaborative review (comments per sentence).
- [ ] Admin console for quotas, audit log, user roles.

---

## Design Deliverables (supporting all priorities)

- [ ] High-fidelity mockups for: Onboarding, Process (all steps), Review table, Export panel, History, Settings, Integrations.
- [ ] Component library spec: buttons, inputs, selects, tables, toasts, banners, stepper, modals.
- [ ] Iconography set and illustration style.
- [ ] Content style guide and microcopy patterns.
- [ ] Accessibility annotations (focus order, landmarks, labels).

---

## Engineering Notes

- [ ] Use route-based code splitting; persist state in URL where helpful (e.g., ?step=review).
- [ ] Job queue and retries with backoff for Gemini/Drive/Sheets.
- [ ] Error categories: user-permission, quota, network, validation, unknown.
- [ ] Content Security Policy configured for Google APIs and CDN.

---

## Open Questions

- [ ] Single-user vs multi-user/teams now?
- [ ] Default: create new sheet or append to a master?
- [ ] Data retention default (e.g., 30/60/90 days)?
- [ ] Any pricing/billing planned (affects onboarding copy and limits)?
- [ ] Should edited sentences in Review override normalization in export by default?

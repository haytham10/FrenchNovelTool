## UI/UX To‑Do (Stunning and Scalable)

A prioritized backlog to build a beautiful, fast, and maintainable UI using Next.js 15, React 19, TypeScript, MUI v7, and Tailwind v4.

### Milestones
- M1: Foundations, Navigation, Core flows (Upload → Process → Results)
- M2: History, Settings, Polishing, Empty/Error states
- M3: Motion, Advanced components, A11y, Internationalization

### 1 Design System & Foundations (M1)
- [ ] Tokens: color/spacing/typography/radius/shadows synchronized across MUI theme and Tailwind
- [ ] Typography scale (display → caption) with responsive sizes
- [ ] Color scheme: light/dark + high-contrast; gradient and neon accent palette
- [ ] Elevation & glassmorphism surfaces (blur, translucency) for cards/overlays
- [x] Iconography with lucide-react: adopt as primary icon set
- [x] Icon wrapper component (size tokens, strokeWidth, color, aria-label)
- [ ] Icon sizing scale (12, 16, 20, 24, 28, 32) via design tokens
- [ ] Theming rules: map icon colors to semantic tokens (info/success/warn/error)
- [ ] Grid/breakpoints (xs…xl) and spacing rhythm
- [ ] Component naming conventions and folder structure (`src/components/ui`, `src/components/composite`)
- [ ] Storybook setup for component previews and visual regression

### 2 App Shell & Navigation (M1)
- [x] Responsive header with logo, primary nav, CTAs, theme switcher
- [ ] Sidebar on desktop; bottom tab bar on mobile
- [ ] Breadcrumbs for deep pages (History detail, Settings subsections)
- [ ] Command palette (Ctrl/Cmd+K) for quick actions and navigation
- [ ] Global search input with suggestions
- [ ] Route-level loading and error boundaries

### 3 Landing/Home (M1)
- [x] Hero section with gradient background, animated blobs/particles, subtle parallax
- [ ] Primary CTA (Upload PDF), secondary CTA (View History)
- [ ] “How it works” steps with illustrations
- [ ] Social proof/status badges (fast, secure, AI‑powered)

### 4 File Upload & Processing Flow (M1)
- [ ] Drag & drop zone with type validation and size hints
- [ ] Progress indicators (linear stepper: Upload → Analyze → Normalize → Done)
- [ ] Skeleton screens and shimmer placeholders
- [ ] Error states (file too large/invalid type/network) with recovery actions
- [ ] Success confirmation with confetti and next‑step prompts (Export / Review)

### 5 Results & Review (M1)
- [ ] Results table with sticky header, column resizing, virtualization for large lists
- [ ] Side panel for sentence detail/preview and quick edits
- [ ] Bulk actions (select, delete, export)
- [ ] Inline filters (length, status) and search
- [ ] Export CTA group (Google Sheets / CSV) with status toasts

### 6 History (M2)
- [ ] Paginated, searchable history table (filename, date, status, actions)
- [ ] Row expansion for run details and metrics
- [ ] Compare runs (diff of settings/results)
- [ ] Batch actions (delete, export again)

### 7 Settings (M2)
- [ ] Structured sections: General, Limits, Integrations (Google), Appearance
- [ ] Form validation, inline feedback, optimistic save with undo
- [ ] Test connection for Google integrations
- [ ] Import/export settings JSON

### 8 Components Library (Ongoing)
- [ ] Buttons: primary/secondary/tertiary, destructive, icon-only
- [ ] Inputs: text, number, file, select, slider, switches, segmented controls
- [ ] Data: table, tabs, accordion, breadcrumb, chip, tooltip, popover
- [ ] Feedback: toast/snackbar, dialog, drawer, progress (circular/linear), empty states
- [ ] Layout: container, grid, card, modal, split panes (resizable)
 - [x] Icon primitives: `Icon` wrapper, `IconButton` variants (sizes, states)
 - [ ] Icons catalog page (searchable list of lucide icons for designers/devs)

### Next Tasks (M1 Priority)
- [x] Add route-level boundaries: create `app/error.tsx` and `app/loading.tsx`; same for `app/history` and `app/settings`
- [x] Build skeletons: upload card skeleton and results table skeleton (virtualized placeholder rows)
- [x] Implement empty states: home (no files), history (no items), results (no sentences)
- [x] Add progress stepper UI for pipeline (Upload → Analyze → Normalize → Done)
- [x] Breadcrumb component and integration on History detail and Settings subsections
- [x] Command palette (Ctrl/Cmd+K) with navigation/actions using lucide icons
- [x] Global search in header (overlay) with typeahead; route to results page
- [ ] Storybook setup and stories for Icon, IconButton, ThemeToggle, Header, Skeletons
- [x] Storybook setup and stories for Icon, IconButton, ThemeToggle, Header, Skeletons
- [x] Tailwind + MUI token alignment (CSS vars), define icon sizing tokens

### M1 Status
- [x] Foundations: theme + tokens, icons, header, hero
- [x] App shell: header, command palette, breadcrumbs (history, settings)
- [x] Core flows: upload stepper, skeletons, empty states, results wiring
- [x] Route boundaries: loading/error for root, history, settings
- [x] Storybook coverage
- [x] Token alignment (Tailwind + MUI)

### 9 Motion & Micro‑interactions (M3)
- [ ] Page transitions (fade/slide) and shared element transitions for key flows
- [ ] Hover and press states with springy feel
- [ ] Lottie animations for success/empty states
- [ ] Subtle 3D tilt/parallax on hero cards

### 10 Accessibility (M2)
- [ ] Keyboard navigation and focus order validation
- [ ] ARIA roles and labels for all interactive controls
- [ ] Focus visible styles with sufficient contrast
- [ ] Screen reader announcements for toasts/errors
- [ ] Color contrast AA/AAA checks; high‑contrast theme
 - [ ] Icons: aria-hidden for decorative, aria-label/title for informative icons

### 11 Theming (M2)
- [ ] Theme switcher (light/dark/auto)
- [ ] Per‑user persisted preference
- [ ] CSS variables driven by MUI theme; Tailwind plugin alignment

### 12 Performance (M1→M3)
- [ ] Route‑level code splitting and lazy components
- [ ] Virtualized long lists (results, history)
- [ ] Image optimization and icon sprite
- [ ] Avoid layout shift; skeletons and content placeholders

### 13 Internationalization (M3)
- [ ] i18n framework (copy extraction, locale switcher)
- [ ] RTL support audit
- [ ] Dates/numbers localization

### 14 Observability & QA (M2)
- [ ] Visual regression via Storybook/Test runner
- [ ] UX metrics (Web Vitals) and user timing marks
- [ ] Session replay/analytics (privacy‑aware)
 - [ ] Storybook snapshots for `Icon` wrapper (light/dark, sizes, states)

### 15 Cool Elements & Delight (Sprinkles)
- [ ] Glassmorphism cards and frosted headers
- [ ] Gradient borders and neon accent shadows
- [ ] Particle/constellation background toggle on landing
- [ ] Docked action bar on results page
- [ ] Quick actions (hover toolbars) and contextual menus

### 16 Tech Tasks for Scalability (Ongoing)
- [ ] Component docs (props, usage, a11y notes)
- [ ] Strict TypeScript types and generics for UI primitives
- [ ] Centralized API error handling with friendly UI states
- [ ] State management boundaries (server vs client; query caching)
- [ ] UI testing: critical flows (upload, results, export)

### Acceptance Criteria (per feature)
- Looks polished in light/dark, responsive from 360px → 1440px+
- Meets a11y AA for contrast and keyboard operability
- Smooth transitions (<150ms) and no jank; CLS < 0.1
- Documented in Storybook with examples and edge cases



# Frontend Improvement Roadmap

This document provides a strategic roadmap for enhancing the frontend of the French Novel Tool. The focus is on improving user experience, performance, code quality, and maintainability.

---

## Current State Analysis

### Strengths
- ✅ Modern Next.js 15 with React 19
- ✅ TypeScript for type safety
- ✅ Material-UI (MUI) component library
- ✅ Proper authentication context
- ✅ Clean separation of concerns (components, lib, app)
- ✅ Snackbar notifications (notistack)
- ✅ Google OAuth integration

### Weaknesses
- ⚠️ No centralized state management beyond Context API
- ⚠️ Limited error boundary implementation
- ⚠️ No automated testing
- ⚠️ Performance issues with large result sets
- ⚠️ Synchronous processing UX (loading states block UI)
- ⚠️ No offline support or PWA features
- ⚠️ Accessibility could be improved
- ⚠️ No code splitting for heavy components

---

## Phase 1: User Experience & Code Quality (Short-Term, 2-4 weeks)

**Objective:** Improve immediate user experience and establish code quality foundations.

### 1.1 Enhanced User Feedback
- [ ] **Improve loading states**
    - Action: Replace generic spinners with skeleton screens
    - Current: `CircularProgress` for everything
    - Improved: `ResultsSkeleton` for results, specific loaders for each action
    - Files: All page components
    - Priority: HIGH

- [ ] **Better error messages**
    - Action: Parse backend error responses and show actionable messages
    - Implementation:
        ```tsx
        // Instead of: "Request failed"
        // Show: "Your session expired. Please log in again."
        ```
    - Priority: HIGH

- [ ] **Add progress indicators for file upload**
    - Action: Show upload progress percentage
    - Use: XMLHttpRequest progress events
    - Priority: MEDIUM

- [ ] **Implement optimistic UI updates**
    - Action: Update UI immediately, rollback on error
    - Use cases: Delete history entry, update settings
    - Priority: MEDIUM

### 1.2 Accessibility (a11y)
- [ ] **Keyboard navigation audit**
    - Action: Ensure all interactive elements are keyboard accessible
    - Test: Navigate entire app with Tab/Shift+Tab
    - Priority: HIGH

- [ ] **Add ARIA labels and roles**
    - Action: Add descriptive labels to all icon buttons and interactive elements
    - Tool: eslint-plugin-jsx-a11y
    - Priority: HIGH

- [ ] **Improve focus management**
    - Action: Visible focus indicators on all interactive elements
    - CSS: Ensure `:focus-visible` styles are clear
    - Priority: MEDIUM

- [ ] **Add screen reader support**
    - Action: Test with NVDA/JAWS
    - Add `role`, `aria-label`, `aria-describedby` where needed
    - Priority: MEDIUM

- [ ] **Implement skip links**
    - Action: Add "Skip to main content" link
    - Priority: LOW

### 1.3 Component Refactoring
- [ ] **Create reusable UI component library**
    - Action: Extract common patterns into `components/ui/`
    - Components to create:
        - `Button` (with variants: primary, secondary, danger)
        - `Input` (with error states, helper text)
        - `Card` (container component)
        - `Badge` (for status indicators)
        - `Table` (with sorting, pagination)
    - Priority: MEDIUM

- [ ] **Break down large components**
    - Files to refactor:
        - `app/page.tsx` (main page is 174 lines)
        - `app/history/page.tsx`
        - `components/HistoryTable.tsx`
    - Extract smaller sub-components
    - Priority: MEDIUM

- [ ] **Implement compound components pattern**
    - Action: For complex components like tables
    - Example:
        ```tsx
        <Table>
          <Table.Header>...</Table.Header>
          <Table.Body>...</Table.Body>
        </Table>
        ```
    - Priority: LOW

### 1.4 State Management
- [ ] **Implement global state management**
    - Action: Install and configure Zustand or Jotai
    - Reason: Context API is sufficient for auth, but app state needs better solution
    - Stores to create:
        - `useProcessingStore` (sentences, loading states)
        - `useHistoryStore` (cache history data)
        - `useSettingsStore` (user settings)
    - Priority: HIGH

- [ ] **Implement data fetching library**
    - Action: Use TanStack Query (React Query)
    - Benefits:
        - Automatic caching
        - Background refetching
        - Optimistic updates
        - Proper loading/error states
    - Priority: HIGH

---

## Phase 2: Performance & Responsiveness (Mid-Term, 1-2 months)

**Objective:** Make the application fast, responsive, and handle large datasets efficiently.

### 2.1 Async Processing UX
- [ ] **Implement polling for PDF processing**
    - Action: Support async job pattern from backend
    - Flow:
        1. Upload PDF → receive job_id
        2. Show processing animation
        3. Poll `/jobs/<job_id>` every 2 seconds
        4. Display results when complete
    - Priority: HIGH

- [ ] **Add cancellable operations**
    - Action: Allow users to cancel long-running jobs
    - Implementation: Abort controller for fetch requests
    - Priority: MEDIUM

### 2.2 Performance Optimization
- [ ] **Virtualize large lists**
    - Action: Use `@tanstack/react-virtual` for ResultsTable
    - Benefit: Render only visible rows (handle 10k+ sentences)
    - Files: `ResultsTable.tsx`, `HistoryTable.tsx`
    - Priority: HIGH

- [ ] **Implement code splitting**
    - Action: Lazy load heavy components
    - Components to lazy load:
        - `DriveFolderPicker` (only needed for export)
        - `CommandPalette` (only needed when invoked)
        - Settings page
        - History page
    - Use: `next/dynamic`
    - Priority: MEDIUM

- [ ] **Optimize bundle size**
    - Action: Analyze bundle with `@next/bundle-analyzer`
    - Steps:
        1. Find large dependencies
        2. Replace or tree-shake where possible
        3. Use lighter alternatives
    - Priority: MEDIUM

- [ ] **Implement image optimization**
    - Action: Use Next.js `<Image>` component for all images
    - Priority: LOW

- [ ] **Add service worker for offline support**
    - Action: Implement basic PWA features
    - Features:
        - Cache app shell
        - Offline page
        - Background sync for failed exports
    - Priority: LOW

### 2.3 Data Management
- [ ] **Implement data pagination**
    - Action: Paginate history table and results
    - Backend support needed: `/history?page=1&limit=50`
    - Priority: MEDIUM

- [ ] **Add client-side caching**
    - Action: Cache API responses in memory/localStorage
    - Use: TanStack Query built-in caching
    - Priority: MEDIUM

- [ ] **Implement infinite scroll for history**
    - Action: Load more history as user scrolls
    - Better UX than traditional pagination
    - Priority: LOW

---

## Phase 3: Testing & Quality Assurance (Mid-Term, 1-2 months)

**Objective:** Establish comprehensive testing to prevent regressions.

### 3.1 Unit Testing
- [ ] **Set up testing framework**
    - Action: Configure Jest + React Testing Library
    - Already available in Next.js, just needs setup
    - Priority: HIGH

- [ ] **Test utility functions**
    - Files to test:
        - `lib/api.ts` (mock axios)
        - `lib/auth.ts` (localStorage operations)
        - Any validation functions
    - Target: 90%+ coverage for utilities
    - Priority: HIGH

- [ ] **Test React components**
    - Components to test:
        - `AuthContext` (authentication logic)
        - `FileUpload` (file handling)
        - `ResultsTable` (data display)
        - Form components
    - Priority: HIGH

- [ ] **Test custom hooks**
    - If any custom hooks are created
    - Use `@testing-library/react-hooks`
    - Priority: MEDIUM

### 3.2 Integration Testing
- [ ] **Set up E2E testing framework**
    - Action: Install Playwright or Cypress
    - Recommendation: Playwright (better for Next.js)
    - Priority: HIGH

- [ ] **Create critical path tests**
    - Test scenarios:
        1. **Happy path**: Login → Upload PDF → View results → Export
        2. **Error handling**: Login fail, upload fail, export fail
        3. **Settings**: Change settings, verify applied to processing
        4. **History**: View history, delete entry
    - Priority: HIGH

- [ ] **Add visual regression testing**
    - Action: Use Playwright screenshots or Percy
    - Catch unintended UI changes
    - Priority: LOW

### 3.3 Code Quality Tools
- [ ] **Configure ESLint strictly**
    - Action: Add more strict rules
    - Rules to add:
        - `@typescript-eslint/strict-type-checked`
        - `jsx-a11y/recommended`
        - React hooks rules
    - Priority: MEDIUM

- [ ] **Add Prettier**
    - Action: Install and configure Prettier
    - Auto-format on save
    - Priority: MEDIUM

- [ ] **Set up pre-commit hooks**
    - Action: Use Husky + lint-staged
    - Run: Linting, type checking, tests before commit
    - Priority: MEDIUM

- [ ] **Add type checking in CI**
    - Action: Run `tsc --noEmit` in GitHub Actions
    - Fail build on type errors
    - Priority: HIGH

---

## Phase 4: Advanced Features & UX Polish (Long-Term, 2-3 months)

**Objective:** Add sophisticated features and polish the user experience.

### 4.1 Advanced UI Features
- [ ] **Implement command palette**
    - Current: Basic `CommandPalette` exists
    - Enhanced: Make it more powerful
    - Features:
        - Search history
        - Quick actions (upload, export, settings)
        - Keyboard shortcuts displayed
    - Priority: MEDIUM

- [ ] **Add dark mode**
    - Action: Implement theme toggle
    - Use: MUI theme system
    - Persist preference in localStorage
    - Priority: MEDIUM

- [ ] **Implement drag-and-drop file upload**
    - Current: Uses react-dropzone
    - Enhanced: Better visual feedback
    - Priority: LOW

- [ ] **Add keyboard shortcuts**
    - Shortcuts:
        - `Cmd/Ctrl + K`: Open command palette
        - `Cmd/Ctrl + U`: Upload file
        - `Cmd/Ctrl + E`: Export results
        - `Cmd/Ctrl + H`: View history
    - Priority: MEDIUM

### 4.2 Data Visualization
- [ ] **Add charts for analytics**
    - Action: Use recharts or Chart.js
    - Charts:
        - Processing history over time
        - Sentence count distribution
        - Processing time trends
    - Priority: LOW

- [ ] **Implement sentence diff viewer**
    - Action: Show before/after for rewritten sentences
    - Highlight changes
    - Priority: LOW

### 4.3 Collaboration Features
- [ ] **Add shareable links**
    - Action: Generate shareable links for processed results
    - Store results with unique ID
    - Priority: LOW

- [ ] **Implement export formats**
    - Current: Only Google Sheets
    - Add: CSV, JSON, TXT download
    - Priority: MEDIUM

### 4.4 Mobile Optimization
- [ ] **Responsive design audit**
    - Action: Test on mobile devices
    - Fix: Any layout issues on small screens
    - Priority: HIGH

- [ ] **Optimize for touch**
    - Action: Ensure touch targets are large enough (44px min)
    - Priority: MEDIUM

- [ ] **Add mobile-specific UX**
    - Features:
        - Swipe gestures for navigation
        - Mobile-optimized file picker
    - Priority: LOW

---

## Phase 5: Documentation & Developer Experience (Ongoing)

**Objective:** Make the codebase maintainable and onboarding easy.

### 5.1 Component Documentation
- [ ] **Set up Storybook**
    - Action: Install and configure Storybook
    - Document all reusable components
    - Include: Props, variants, usage examples
    - Priority: MEDIUM

- [ ] **Add JSDoc comments**
    - Action: Document complex functions and components
    - Priority: LOW

### 5.2 Developer Tools
- [ ] **Add development proxy**
    - Action: Ensure `next.config.ts` proxies API calls in dev
    - Avoid CORS issues in development
    - Priority: LOW

- [ ] **Create component generator**
    - Action: Script to generate boilerplate for new components
    - Tool: Plop.js
    - Priority: LOW

### 5.3 Deployment
- [ ] **Optimize production build**
    - Action: Configure Next.js for optimal production build
    - Settings:
        - Enable compression
        - Optimize fonts
        - Configure caching headers
    - Priority: MEDIUM

- [ ] **Add build-time type checking**
    - Action: Fail build if TypeScript errors exist
    - Already configured in Next.js, verify it's enforced
    - Priority: HIGH

---

## Success Metrics

### Phase 1 Success Criteria
- ✅ All interactive elements keyboard accessible
- ✅ Consistent loading states across app
- ✅ Centralized state management implemented
- ✅ Zero accessibility errors in automated tools

### Phase 2 Success Criteria
- ✅ Handle 10,000+ sentences in results table without lag
- ✅ Initial page load < 2 seconds
- ✅ Async processing implemented (no UI blocking)
- ✅ Lighthouse score > 90 (Performance, Accessibility)

### Phase 3 Success Criteria
- ✅ 80%+ test coverage for critical paths
- ✅ E2E tests passing for happy path
- ✅ Zero TypeScript errors
- ✅ Automated tests run on every commit

### Phase 4 Success Criteria
- ✅ Mobile-responsive (all features work on phone)
- ✅ Dark mode implemented
- ✅ Keyboard shortcuts documented and working
- ✅ User satisfaction > 4.5/5

---

## Estimated Timeline

- **Phase 1**: 2-4 weeks (immediate improvements)
- **Phase 2**: 1-2 months (performance work)
- **Phase 3**: 1-2 months (can overlap with Phase 2)
- **Phase 4**: 2-3 months (polish and advanced features)
- **Phase 5**: Ongoing (documentation)

**Total to production-ready**: ~3-4 months with dedicated development

---

## Priority Legend
- **HIGH**: Critical for user experience or production readiness
- **MEDIUM**: Important for quality and maintainability
- **LOW**: Nice-to-have improvements

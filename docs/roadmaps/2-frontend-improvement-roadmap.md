# Frontend Improvement Roadmap# Frontend Improvement Roadmap



**Last Updated:** October 2, 2025This document provides a strategic roadmap for enhancing the frontend of the French Novel Tool. The focus is on improving user experience, performance, code quality, and maintainability.



Focus: State management, performance, user experience, and production readiness.---



---## Current State Analysis



## 📊 Current State### Strengths

- ✅ Modern Next.js 15 with React 19

### ✅ Working Well- ✅ TypeScript for type safety

- Next.js 15 + React 19 + TypeScript- ✅ Material-UI (MUI) component library

- Material-UI v7 components- ✅ Proper authentication context

- Google OAuth authentication- ✅ Clean separation of concerns (components, lib, app)

- File upload with drag-and-drop- ✅ Snackbar notifications (notistack)

- Responsive design- ✅ Google OAuth integration

- Error boundaries

- Snackbar notifications### Weaknesses

- ⚠️ No centralized state management beyond Context API

### ⚠️ Needs Improvement- ⚠️ Limited error boundary implementation

- No centralized state management- ⚠️ No automated testing

- No API data caching- ⚠️ Performance issues with large result sets

- Synchronous processing UX (blocks UI)- ⚠️ Synchronous processing UX (loading states block UI)

- Generic loading states- ⚠️ No offline support or PWA features

- No automated tests- ⚠️ Accessibility could be improved

- Large bundle size- ⚠️ No code splitting for heavy components

- Poor error messages

- Missing accessibility features---



---## Phase 1: User Experience & Code Quality (Short-Term, 2-4 weeks)



## 🔴 P0 - Critical (Weeks 1-4)**Objective:** Improve immediate user experience and establish code quality foundations.



### Week 1: State Management### 1.1 Enhanced User Feedback

**Install Zustand for scalable state**- [ ] **Improve loading states**

    - Action: Replace generic spinners with skeleton screens

```bash    - Current: `CircularProgress` for everything

npm install zustand    - Improved: `ResultsSkeleton` for results, specific loaders for each action

```    - Files: All page components

    - Priority: HIGH

Create stores:

- `useProcessingStore` - PDF processing state- [ ] **Better error messages**

- `useHistoryStore` - Processing history cache    - Action: Parse backend error responses and show actionable messages

- `useSettingsStore` - User settings (with localStorage persistence)    - Implementation:

        ```tsx

### Week 1-2: Data Fetching with React Query        // Instead of: "Request failed"

**Install TanStack Query for proper data management**        // Show: "Your session expired. Please log in again."

        ```

```bash    - Priority: HIGH

npm install @tanstack/react-query @tanstack/react-query-devtools

```- [ ] **Add progress indicators for file upload**

    - Action: Show upload progress percentage

Benefits:    - Use: XMLHttpRequest progress events

- Automatic caching    - Priority: MEDIUM

- Background refetching

- Optimistic updates- [ ] **Implement optimistic UI updates**

- Better loading/error states    - Action: Update UI immediately, rollback on error

    - Use cases: Delete history entry, update settings

Create hooks:    - Priority: MEDIUM

- `useHistory()` - Fetch history with caching

- `useSettings()` - Fetch/update settings### 1.2 Accessibility (a11y)

- `useProcessPdf()` - Process with progress tracking- [ ] **Keyboard navigation audit**

- `useExportToSheet()` - Export with optimistic updates    - Action: Ensure all interactive elements are keyboard accessible

    - Test: Navigate entire app with Tab/Shift+Tab

### Week 2-3: Async Processing UI    - Priority: HIGH

**Support backend async jobs**

- [ ] **Add ARIA labels and roles**

- Implement job polling (check status every 2s)    - Action: Add descriptive labels to all icon buttons and interactive elements

- Show progress indicators    - Tool: eslint-plugin-jsx-a11y

- Allow navigation during processing    - Priority: HIGH

- Notify when complete

- [ ] **Improve focus management**

```typescript    - Action: Visible focus indicators on all interactive elements

const { data: job } = useJobStatus(jobId, {    - CSS: Ensure `:focus-visible` styles are clear

  refetchInterval: (data) =>     - Priority: MEDIUM

    data?.status === 'processing' ? 2000 : false

});- [ ] **Add screen reader support**

```    - Action: Test with NVDA/JAWS

    - Add `role`, `aria-label`, `aria-describedby` where needed

### Week 3: Error Handling    - Priority: MEDIUM

**Better user feedback**

- [ ] **Implement skip links**

- Parse backend error responses    - Action: Add "Skip to main content" link

- Show actionable error messages    - Priority: LOW

- Add retry buttons for retryable errors

- Implement error boundaries### 1.3 Component Refactoring

- Log errors to Sentry- [ ] **Create reusable UI component library**

    - Action: Extract common patterns into `components/ui/`

### Week 4: Loading States    - Components to create:

**Replace spinners with skeletons**        - `Button` (with variants: primary, secondary, danger)

        - `Input` (with error states, helper text)

- Create skeleton components for tables/cards        - `Card` (container component)

- Use suspense boundaries        - `Badge` (for status indicators)

- Show progress percentages        - `Table` (with sorting, pagination)

- Add "estimated time remaining"    - Priority: MEDIUM



---- [ ] **Break down large components**

    - Files to refactor:

## 🟠 P1 - High Priority (Weeks 5-8)        - `app/page.tsx` (main page is 174 lines)

        - `app/history/page.tsx`

### Week 5-6: Performance        - `components/HistoryTable.tsx`

**Optimize for large datasets**    - Extract smaller sub-components

    - Priority: MEDIUM

- Virtualize tables (react-virtual) for 1000+ sentences

- Code split heavy components (dynamic imports)- [ ] **Implement compound components pattern**

- Analyze and reduce bundle size    - Action: For complex components like tables

- Implement pagination for history    - Example:

- Optimize images and assets        ```tsx

        <Table>

### Week 7: Testing          <Table.Header>...</Table.Header>

**Add automated tests**          <Table.Body>...</Table.Body>

        </Table>

```bash        ```

npm install -D @testing-library/react jest    - Priority: LOW

```

### 1.4 State Management

- Unit tests for components- [ ] **Implement global state management**

- Integration tests for user flows      - Action: Install and configure Zustand or Jotai

- Mock API responses    - Reason: Context API is sufficient for auth, but app state needs better solution

- Test error scenarios    - Stores to create:

- Target: 70% coverage        - `useProcessingStore` (sentences, loading states)

        - `useHistoryStore` (cache history data)

### Week 8: Accessibility        - `useSettingsStore` (user settings)

**WCAG 2.1 AA compliance**    - Priority: HIGH



- Add ARIA labels to all interactive elements- [ ] **Implement data fetching library**

- Implement keyboard navigation    - Action: Use TanStack Query (React Query)

- Test with screen readers    - Benefits:

- Add focus indicators        - Automatic caching

- Use semantic HTML        - Background refetching

- Install eslint-plugin-jsx-a11y        - Optimistic updates

        - Proper loading/error states

---    - Priority: HIGH



## 🟡 P2 - Medium Priority (Weeks 9-12)---



### Advanced Features## Phase 2: Performance & Responsiveness (Mid-Term, 1-2 months)

- Inline editing for sentences (double-click to edit)

- Search and filter results (debounced)**Objective:** Make the application fast, responsive, and handle large datasets efficiently.

- Batch operations (select multiple, delete/export)

- Sentence statistics dashboard### 2.1 Async Processing UX

- Export to multiple formats (CSV, DOCX)- [ ] **Implement polling for PDF processing**

    - Action: Support async job pattern from backend

### PWA Support    - Flow:

- Add service worker for offline support        1. Upload PDF → receive job_id

- Create app manifest        2. Show processing animation

- Cache app shell        3. Poll `/jobs/<job_id>` every 2 seconds

- Show offline indicator        4. Display results when complete

- Queue failed requests for retry    - Priority: HIGH



### Design Polish- [ ] **Add cancellable operations**

- Add micro-animations (hover, transitions)    - Action: Allow users to cancel long-running jobs

- Improve empty states    - Implementation: Abort controller for fetch requests

- Add dark mode toggle    - Priority: MEDIUM

- Better mobile experience

- Loading state variations### 2.2 Performance Optimization

- [ ] **Virtualize large lists**

---    - Action: Use `@tanstack/react-virtual` for ResultsTable

    - Benefit: Render only visible rows (handle 10k+ sentences)

## 📊 Success Metrics    - Files: `ResultsTable.tsx`, `HistoryTable.tsx`

    - Priority: HIGH

### Performance

- Lighthouse score > 90- [ ] **Implement code splitting**

- First Contentful Paint < 1.5s    - Action: Lazy load heavy components

- Bundle size < 200KB (gzipped)    - Components to lazy load:

        - `DriveFolderPicker` (only needed for export)

### Quality        - `CommandPalette` (only needed when invoked)

- 70%+ test coverage        - Settings page

- Zero a11y violations        - History page

- All ESLint rules passing    - Use: `next/dynamic`

    - Priority: MEDIUM

### UX

- Clear error messages- [ ] **Optimize bundle size**

- Loading feedback for all operations    - Action: Analyze bundle with `@next/bundle-analyzer`

- Keyboard navigation works    - Steps:

- Mobile responsive        1. Find large dependencies

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

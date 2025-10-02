# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added - P0 UX/UI Overhaul

#### Core Features
- **Normalize Controls Component**: Interactive sentence length slider (5-20 words) with quick presets (8, 12, 16)
- **Inline Editing**: Edit sentences directly in results table with keyboard shortcuts (Enter to save, Esc to cancel)
- **Status Indicators**: Visual feedback in history table (Success ✓, Failed ✗, Processing ⟳) with colored icons
- **Debounced Search**: 300ms debounced filtering in results and history tables for better performance

#### API & Backend Integration
- **API Client** (`lib/api.ts`): Axios-based client with automatic token refresh
- **Authentication Utilities** (`lib/auth.ts`): Token management with localStorage
- **TypeScript Types** (`lib/types.ts`): Shared type definitions for consistency
- **Custom Hooks** (`lib/hooks.ts`): `useDebounce` and `useLocalStorage` hooks

#### Accessibility Improvements
- Semantic landmarks: `<main>`, `<header>`, `<nav>` elements
- ARIA labels on interactive elements (upload, stepper, table actions)
- Keyboard navigation support throughout
- Screen reader announcements for stepper states
- Focus management for inline editing

#### UI/UX Enhancements
- Sticky table headers for better scrolling experience
- Zebra striping on table rows for readability
- Filter count display (showing X of Y items)
- Responsive design improvements
- Light/dark theme parity

#### Developer Experience
- Clean TypeScript types throughout
- Reusable component patterns
- Comprehensive error handling
- Build validation passing

### Changed
- Updated History table to use backend field names (`timestamp`, `original_filename`, `processed_sentences_count`)
- Enhanced ResultsTable with inline editing capabilities
- Improved FileUpload component with accessibility features
- Updated UploadStepper with ARIA labels and state announcements
- Expanded README with comprehensive feature list

### Fixed
- Type mismatches between frontend and backend data models
- React Hook dependency warnings
- Missing lib directory causing build failures
- Google Fonts loading issues in sandboxed environment

## Technical Details

### Bundle Analysis
- Main page: 246 kB (First Load JS)
- History page: 209 kB (First Load JS)
- Settings page: 204 kB (First Load JS)
- Shared chunks: 102 kB

### Performance Optimizations
- Debounced search (300ms delay)
- Memoized filtered/sorted data
- Sticky headers with maxHeight containers
- Optimized re-renders with React.useMemo

### Dependencies Added
- `react-window` and `@types/react-window` (for future virtualization)

### Accessibility Compliance
- WCAG 2.1 AA baseline for core workflows
- Semantic HTML structure
- Keyboard navigation
- ARIA labels and roles
- Focus management

## Definition of Done (P0) ✓

All P0 requirements from the UX/UI Overhaul Roadmap have been implemented:

1. ✓ User can authenticate, upload PDF, normalize, review, and export
2. ✓ Clear status and feedback throughout the flow
3. ✓ History records with status indicators
4. ✓ Accessible with keyboard navigation
5. ✓ Build passes successfully
6. ✓ Documentation updated

## Next Steps (P1 Priority)

1. First-run wizard for onboarding
2. Progress indicators for long-running operations
3. Virtualization for 5k+ item tables
4. E2E testing with Playwright
5. Accessibility audit with axe
6. Performance monitoring
7. Help/Integrations pages
8. Privacy/Terms links

# Frontend Improvement Roadmap

This document provides a strategic roadmap for enhancing the frontend of the French Novel Tool. The focus is on improving user experience, performance, code quality, and maintainability.

---

## Phase 1: Code Quality and User Experience Foundations (Short-Term)

**Objective:** Refine the existing codebase, improve developer experience, and address immediate UX gaps.

- [ ] **Implement a Consistent State Management Solution:**
    -   **Action:** Centralize application state management instead of relying solely on React Context for everything.
    -   **Implementation:** Introduce a lightweight state management library like **Zustand** or **Jotai**. This will simplify state logic, reduce prop-drilling, and make the application easier to debug, especially as more features are added. `AuthContext` can remain, but UI state, form data, and API results should be managed here.

- [ ] **Refactor Components for Reusability and Simplicity:**
    -   **Action:** Break down large components into smaller, single-purpose components.
    -   **Implementation:**
        -   Analyze components like `SettingsForm.tsx` and `HistoryTable.tsx` and extract smaller, reusable pieces (e.g., `Input`, `Button`, `Table.Row`).
        -   Establish a clear folder structure for components (e.g., `components/ui` for generic elements, `components/features` for feature-specific composites).

- [ ] **Enhance User Feedback and Error Handling:**
    -   **Action:** Provide more informative feedback to the user during application events.
    -   **Implementation:**
        -   Use a library like **`react-hot-toast`** to display non-blocking notifications for success (`Export successful!`), error (`Failed to process PDF`), and loading states.
        -   Replace generic `alert()` calls with these toasts.
        -   In API calls, parse the error response from the backend and display a user-friendly message.

- [ ] **Improve Accessibility (a11y):**
    -   **Action:** Ensure the application is usable by people with disabilities.
    -   **Implementation:**
        -   Use semantic HTML elements (`<nav>`, `<main>`, `<button>`).
        -   Ensure all interactive elements are keyboard-navigable and have clear focus states.
        -   Add `aria-label` attributes to icon buttons.
        -   Use a tool like `eslint-plugin-jsx-a11y` to automatically catch common accessibility issues.

---

## Phase 2: Performance Optimization and Advanced Features (Mid-Term)

**Objective:** Make the application faster, more responsive, and more powerful.

- [ ] **Optimize PDF Processing on the Frontend:**
    -   **Action:** Implement asynchronous polling for the PDF processing workflow.
    -   **Implementation:** This aligns with the backend's move to background workers.
        -   When a user uploads a PDF, the frontend will receive a `job_id`.
        -   The UI will show a "processing" state and poll a `/status/<job_id>` endpoint every few seconds.
        -   This prevents the UI from freezing and provides a much better user experience for large files.

- [ ] **Virtualize Large Lists:**
    -   **Action:** Improve the performance of the `ResultsTable` and `HistoryTable` when displaying hundreds or thousands of sentences.
    -   **Implementation:** Integrate a library like **`@tanstack/react-virtual`** to only render the rows that are currently visible in the viewport. This will dramatically reduce the number of DOM nodes and improve rendering performance.

- [ ] **Code-Splitting and Lazy Loading:**
    -   **Action:** Reduce the initial bundle size of the application.
    -   **Implementation:** Use Next.js's `dynamic()` import to lazy-load components that are not critical for the initial page view. Good candidates include the `DriveFolderPicker`, `CommandPalette`, or complex parts of the `settings` page.

- [ ] **Implement an Offline Mode/Progressive Web App (PWA) Features:**
    -   **Action:** Allow users to continue using parts of the application even with an unstable internet connection.
    -   **Implementation:** Add a service worker to cache application assets and API data (like history). This would allow a user to view their past results even when offline.

---

## Phase 3: Modernization and Testing (Long-Term)

**Objective:** Ensure long-term maintainability, stability, and a modern technology stack.

- [ ] **Introduce End-to-End (E2E) Testing:**
    -   **Action:** Automate testing of critical user flows.
    -   **Implementation:** Set up a testing framework like **Cypress** or **Playwright**. Create test scripts for key user journeys:
        1.  User logs in.
        2.  User uploads a PDF and sees the results.
        3.  User exports results to Google Sheets.
        4.  User changes a setting and verifies it's applied.

- [ ] **Upgrade to the Latest Next.js Version and Features:**
    -   **Action:** Migrate from the `pages` router to the `app` router if not already done, and adopt modern Next.js patterns.
    -   **Implementation:** Plan a migration to the Next.js App Router to take advantage of Server Components, improved data fetching, and layout capabilities. This is a significant undertaking but offers long-term performance and development benefits.

- [ ] **Establish a Design System and Component Library:**
    -   **Action:** Formalize the UI components into a documented design system.
    -   **Implementation:** Use a tool like **Storybook** to create an interactive component library. This documents each UI component's props and states, making it easier for developers to discover and reuse components, and ensuring visual consistency across the application.

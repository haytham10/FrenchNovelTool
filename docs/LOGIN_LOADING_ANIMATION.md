# Login Loading Animation Feature

## Overview
This feature adds a full-page visual loading overlay and error toast notifications during Google OAuth authentication to improve user experience and provide clear feedback during the login process.

## Implementation Details

### Files Modified
1. **frontend/src/components/AuthContext.tsx**
   - Added `isAuthenticating` state to track when login/authentication is in progress
   - Updated `AuthContextValue` type to include `isAuthenticating: boolean`
   - Modified `loginWithCredential` to set `isAuthenticating` to `true` during login and `false` when complete
   - Modified `loginWithCode` to set `isAuthenticating` to `true` during login and `false` when complete
   - Integrated `notistack` to display error toast notifications on login failure
   - Renders `AuthLoadingOverlay` component when `isAuthenticating` is true

2. **frontend/src/components/Providers.tsx**
   - Reordered provider hierarchy to place `SnackbarProvider` before `AuthProvider`
   - This allows `AuthProvider` to use `useSnackbar` hook for error notifications

3. **frontend/src/components/AuthLoadingOverlay.tsx** (NEW)
   - Created full-page loading overlay component
   - Uses MUI `Backdrop` with blur effect for modern appearance
   - Displays circular progress indicator with "Signing you in..." message
   - Accessible with proper ARIA attributes

### User Experience Flow

1. **Before Login**: User sees the "Sign in with Google" button in the header
2. **During Login**: 
   - User clicks "Sign in with Google"
   - Google OAuth popup appears
   - After user selects account and consents, the popup closes
   - **Full-page loading overlay appears** with blur backdrop and loading message
   - Backend exchanges tokens and fetches user info
3. **After Login Success**: The overlay disappears and user's avatar menu appears
4. **After Login Failure**: The overlay disappears and an error toast notification is displayed

### Accessibility
- Uses MUI's `Backdrop` component with proper z-index layering
- Loading overlay includes descriptive text for screen readers
- Toast notifications are announced by screen readers via notistack
- Keyboard navigation remains functional during loading state

### Technical Notes
- The `isAuthenticating` state is independent from `isLoading` (which tracks initial app load)
- The full-page overlay blocks all interaction during authentication
- Both Google OAuth flows (credential and authorization code) show the loading overlay
- Error handling uses `getApiErrorMessage` utility to provide user-friendly error messages
- Toast notifications automatically dismiss after a few seconds
- Proper error handling ensures overlay always disappears via `finally` block

## Testing
- Build verification: ✅ Passes (no errors)
- Linting: ✅ Passes (no new warnings)
- Type checking: ✅ Passes (included in build process)

## Related Issues
- Part of UX/UI Overhaul Phase D: Engagement & Help (#22)
- Implements loading animation/skeleton when logging in (when fetching user info from backend)
- Addresses user feedback for full-page loading state instead of header-only skeleton

"use client";

import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import { setTokens, clearTokens, getAccessToken } from '@/lib/auth';
import { loginWithGoogle, getCurrentUser, logout as logoutApi, getApiErrorMessage } from '@/lib/api';
import { GoogleOAuthProvider, googleLogout, type CredentialResponse } from '@react-oauth/google';
import { useSnackbar } from 'notistack';
import AuthLoadingOverlay from './AuthLoadingOverlay';

type AuthUser = { id: number; email: string; name: string; avatarUrl?: string } | null;

type AuthContextValue = {
  user: AuthUser;
  isLoading: boolean;
  isAuthenticating: boolean;
  loginWithCredential: (response: CredentialResponse) => Promise<void>;
  loginWithCode: (code: string) => Promise<void>;
  logout: () => void;
};

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}

export default function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<AuthUser>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isAuthenticating, setIsAuthenticating] = useState(false);
  const [loadingMessage, setLoadingMessage] = useState<string>('');
  const { enqueueSnackbar } = useSnackbar();

  // Load user from stored token on mount
  useEffect(() => {
    const loadUser = async () => {
  const token = getAccessToken();
  // Check for stored token (no debug logging)
      
      if (token) {
        try {
          setLoadingMessage('Verifying authentication...');
          // Fetching user info (no debug logging)
          const userData = await getCurrentUser();
          
          setUser({
            id: userData.id,
            email: userData.email,
            name: userData.name,
            avatarUrl: userData.picture,
          });
          // User restored from token
        } catch (error) {
          console.error('[AuthContext] Failed to load user:', error);
          if (error && typeof error === 'object' && 'response' in error) {
            const axiosError = error as { response?: { data?: unknown; status?: number } };
            console.error('[AuthContext] Error response:', axiosError.response?.data);
            console.error('[AuthContext] Error status:', axiosError.response?.status);
          }
          // Clearing invalid tokens
          clearTokens();
        }
      } else {
        // No token found; user needs to login
      }
      setIsLoading(false);
      setLoadingMessage('');
    };

    loadUser();
  }, []);

  const loginWithCredential = useCallback(async (response: CredentialResponse) => {
    // response.credential is a JWT ID token from Google (legacy flow)
    if (!response.credential) {
      console.error('[AuthContext] No credential in response');
      return;
    }

    try {
  setIsAuthenticating(true);
  setLoadingMessage('Authenticating with Google...');
      // Call backend to exchange Google token for our JWT
      const loginResponse = await loginWithGoogle(response.credential);
      
  // Storing tokens in localStorage
      // Store JWT tokens and session token
      setTokens(loginResponse.access_token, loginResponse.refresh_token, loginResponse.session_token);
      
      // Set user from backend response
      setUser({
        id: loginResponse.user.id,
        email: loginResponse.user.email,
        name: loginResponse.user.name,
        avatarUrl: loginResponse.user.picture,
      });

  // Login successful
    } catch (error) {
      console.error('[AuthContext] Login failed:', error);
      enqueueSnackbar(
        getApiErrorMessage(error, 'Authentication failed. Please try again.'),
        { variant: 'error' }
      );
      clearTokens();
      setUser(null);
    } finally {
      setIsAuthenticating(false);
      setLoadingMessage('');
    }
  }, [enqueueSnackbar]);

  const loginWithCode = useCallback(async (code: string) => {
    // OAuth authorization code flow (recommended - includes Sheets/Drive access)
    try {
  setIsAuthenticating(true);
  setLoadingMessage('Completing authentication...');
      // Call backend to exchange authorization code for our JWT
      const loginResponse = await loginWithGoogle(undefined, code);
      
  // Storing tokens in localStorage
      // Store JWT tokens and session token
      setTokens(loginResponse.access_token, loginResponse.refresh_token, loginResponse.session_token);
      
      // Set user from backend response
      setUser({
        id: loginResponse.user.id,
        email: loginResponse.user.email,
        name: loginResponse.user.name,
        avatarUrl: loginResponse.user.picture,
      });

  // Login successful
    } catch (error) {
      console.error('[AuthContext] Login with code failed:', error);
      enqueueSnackbar(
        getApiErrorMessage(error, 'Authentication failed. Please try again.'),
        { variant: 'error' }
      );
      clearTokens();
      setUser(null);
    } finally {
      setIsAuthenticating(false);
      setLoadingMessage('');
    }
  }, [enqueueSnackbar]);

  const logout = useCallback(async () => {
    // Revoke session on backend
    try {
      await logoutApi();
    } catch (error) {
      console.error('Failed to revoke session on backend:', error);
      // Continue with logout even if backend call fails
    }
    
    // Clear frontend state
    googleLogout();
    clearTokens();
    setUser(null);
  }, []);

  const value = useMemo<AuthContextValue>(() => ({ user, isLoading, isAuthenticating, loginWithCredential, loginWithCode, logout }), [user, isLoading, isAuthenticating, loginWithCredential, loginWithCode, logout]);

  const clientId = process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID || '';

  return (
    <GoogleOAuthProvider clientId={clientId}>
      <AuthContext.Provider value={value}>
        {children}
        <AuthLoadingOverlay open={isAuthenticating || isLoading} message={loadingMessage} />
      </AuthContext.Provider>
    </GoogleOAuthProvider>
  );
}



"use client";

import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import { setTokens, clearTokens, getAccessToken } from '@/lib/auth';
import { loginWithGoogle, getCurrentUser } from '@/lib/api';
import { GoogleOAuthProvider, googleLogout, type CredentialResponse } from '@react-oauth/google';

type AuthUser = { id: number; email: string; name: string; avatarUrl?: string } | null;

type AuthContextValue = {
  user: AuthUser;
  isLoading: boolean;
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

  // Load user from stored token on mount
  useEffect(() => {
    const loadUser = async () => {
      const token = getAccessToken();
      console.log('[AuthContext] Checking for stored token...', token ? 'Found' : 'Not found');
      
      if (token) {
        try {
          console.log('[AuthContext] Fetching user info from /auth/me...');
          console.log('[AuthContext] Using token:', token.substring(0, 50) + '...');
          const userData = await getCurrentUser();
          
          setUser({
            id: userData.id,
            email: userData.email,
            name: userData.name,
            avatarUrl: userData.picture,
          });
          console.log('[AuthContext] User restored from token:', userData.email);
        } catch (error) {
          console.error('[AuthContext] Failed to load user:', error);
          if (error && typeof error === 'object' && 'response' in error) {
            const axiosError = error as { response?: { data?: unknown; status?: number } };
            console.error('[AuthContext] Error response:', axiosError.response?.data);
            console.error('[AuthContext] Error status:', axiosError.response?.status);
          }
          console.log('[AuthContext] Clearing invalid tokens');
          clearTokens();
        }
      } else {
        console.log('[AuthContext] No token found, user needs to login');
      }
      setIsLoading(false);
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
      console.log('[AuthContext] Exchanging Google ID token for JWT (legacy flow)...');
      // Call backend to exchange Google token for our JWT
      const loginResponse = await loginWithGoogle(response.credential);
      
      console.log('[AuthContext] Storing tokens in localStorage...');
      // Store JWT tokens
      setTokens(loginResponse.access_token, loginResponse.refresh_token);
      
      // Set user from backend response
      setUser({
        id: loginResponse.user.id,
        email: loginResponse.user.email,
        name: loginResponse.user.name,
        avatarUrl: loginResponse.user.picture,
      });

      console.log('[AuthContext] Login successful:', loginResponse.user.email);
      console.log('[AuthContext] Has Sheets access:', loginResponse.has_sheets_access);
    } catch (error) {
      console.error('[AuthContext] Login failed:', error);
      clearTokens();
      setUser(null);
    }
  }, []);

  const loginWithCode = useCallback(async (code: string) => {
    // OAuth authorization code flow (recommended - includes Sheets/Drive access)
    try {
      console.log('[AuthContext] Exchanging authorization code for tokens...');
      // Call backend to exchange authorization code for our JWT
      const loginResponse = await loginWithGoogle(undefined, code);
      
      console.log('[AuthContext] Storing tokens in localStorage...');
      // Store JWT tokens
      setTokens(loginResponse.access_token, loginResponse.refresh_token);
      
      // Set user from backend response
      setUser({
        id: loginResponse.user.id,
        email: loginResponse.user.email,
        name: loginResponse.user.name,
        avatarUrl: loginResponse.user.picture,
      });

      console.log('[AuthContext] Login successful:', loginResponse.user.email);
      console.log('[AuthContext] Has Sheets access:', loginResponse.has_sheets_access);
    } catch (error) {
      console.error('[AuthContext] Login with code failed:', error);
      clearTokens();
      setUser(null);
    }
  }, []);

  const logout = useCallback(() => {
    console.log('[AuthContext] Logging out...');
    googleLogout();
    clearTokens();
    setUser(null);
    console.log('[AuthContext] Logout complete');
  }, []);

  const value = useMemo<AuthContextValue>(() => ({ user, isLoading, loginWithCredential, loginWithCode, logout }), [user, isLoading, loginWithCredential, loginWithCode, logout]);

  const clientId = process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID || '';

  return (
    <GoogleOAuthProvider clientId={clientId}>
      <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
    </GoogleOAuthProvider>
  );
}



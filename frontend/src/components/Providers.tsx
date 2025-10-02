"use client";

import type { ReactNode } from 'react';
import { AppRouterCacheProvider } from '@mui/material-nextjs/v15-appRouter';
import { ThemeProvider } from '@mui/material/styles';
import { SnackbarProvider } from 'notistack';
import { createContext, useEffect, useMemo, useState } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { getTheme, getSystemThemePreference, type PaletteMode } from '../theme';
import AuthProvider from './AuthContext';

// Create a client
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60 * 5, // 5 minutes
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
});

export const ColorModeContext = createContext<{ mode: PaletteMode; toggle: () => void }>({ mode: 'light', toggle: () => {} });

export default function Providers({ children }: { children: ReactNode }) {
  const [mode, setMode] = useState<PaletteMode>('light');
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
    // Auto-detect system preference on first load
    const stored = typeof window !== 'undefined' ? (localStorage.getItem('theme-mode') as PaletteMode | null) : null;
    
    if (stored) {
      setMode(stored);
      if (typeof document !== 'undefined') {
        document.documentElement.setAttribute('data-theme', stored);
      }
    } else {
      // Use system preference if no stored preference
      const systemPreference = getSystemThemePreference();
      setMode(systemPreference);
      if (typeof document !== 'undefined') {
        document.documentElement.setAttribute('data-theme', systemPreference);
      }
    }
  }, []);

  const toggle = () => {
    setMode((prev) => {
      const next = prev === 'light' ? 'dark' : 'light';
      if (typeof window !== 'undefined') localStorage.setItem('theme-mode', next);
      if (typeof document !== 'undefined') {
        document.documentElement.setAttribute('data-theme', next);
      }
      return next;
    });
  };

  const theme = useMemo(() => getTheme(mode), [mode]);

  // Prevent flash of unstyled content
  if (!mounted) {
    return null;
  }

  return (
    <AppRouterCacheProvider>
      <QueryClientProvider client={queryClient}>
        <ColorModeContext.Provider value={{ mode, toggle }}>
          <AuthProvider>
            <ThemeProvider theme={theme}>
              <SnackbarProvider maxSnack={3}>
                {children}
              </SnackbarProvider>
            </ThemeProvider>
          </AuthProvider>
        </ColorModeContext.Provider>
      </QueryClientProvider>
    </AppRouterCacheProvider>
  );
}

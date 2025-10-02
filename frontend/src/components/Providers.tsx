"use client";

import type { ReactNode } from 'react';
import { AppRouterCacheProvider } from '@mui/material-nextjs/v15-appRouter';
import { ThemeProvider } from '@mui/material/styles';
import { SnackbarProvider } from 'notistack';
import { createContext, useEffect, useMemo, useState } from 'react';
import { getTheme, type PaletteMode } from '../theme';
import AuthProvider from './AuthContext';

export const ColorModeContext = createContext<{ mode: PaletteMode; toggle: () => void }>({ mode: 'light', toggle: () => {} });

export default function Providers({ children }: { children: ReactNode }) {
  const [mode, setMode] = useState<PaletteMode>('light');

  useEffect(() => {
    const stored = typeof window !== 'undefined' ? (localStorage.getItem('theme-mode') as PaletteMode | null) : null;
    if (stored) setMode(stored);
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

  return (
    <AppRouterCacheProvider>
      <ColorModeContext.Provider value={{ mode, toggle }}>
        <AuthProvider>
          <ThemeProvider theme={theme}>
            <SnackbarProvider maxSnack={3}>
              {children}
            </SnackbarProvider>
          </ThemeProvider>
        </AuthProvider>
      </ColorModeContext.Provider>
    </AppRouterCacheProvider>
  );
}

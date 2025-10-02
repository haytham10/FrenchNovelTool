import { createTheme } from '@mui/material/styles';
import type { PaletteMode } from '@mui/material';

export function getTheme(mode: PaletteMode) {
  const isDarkMode = mode === 'dark';

  return createTheme({
    palette: {
      mode,
      primary: { main: isDarkMode ? '#7c9cff' : '#3b82f6' },
      secondary: { main: isDarkMode ? '#7dd3fc' : '#06b6d4' },
      success: { main: '#22c55e' },
      warning: { main: '#f59e0b' },
      error: { main: '#ef4444' },
      background: {
        default: isDarkMode ? '#0b1220' : '#f7f8fb',
        paper: isDarkMode ? '#0f172a' : '#ffffff',
      },
    },
    shape: { borderRadius: 12 },
    typography: {
      fontFamily: 'Inter, system-ui, -apple-system, Segoe UI, Roboto, Arial, "Noto Sans", "Helvetica Neue", sans-serif',
      h1: { fontSize: '2.75rem', fontWeight: 800, letterSpacing: '-0.02em' },
      h2: { fontSize: '2rem', fontWeight: 700, letterSpacing: '-0.01em' },
      h3: { fontSize: '1.5rem', fontWeight: 700 },
      subtitle1: { fontSize: '1.125rem', fontWeight: 500 },
      body1: { fontSize: '1rem', lineHeight: 1.65 },
      button: { textTransform: 'none', fontWeight: 600 },
    },
    components: {
      MuiPaper: {
        styleOverrides: {
          root: {
            backdropFilter: 'saturate(140%) blur(8px)',
          },
        },
      },
      MuiButton: {
        defaultProps: { disableElevation: true },
        styleOverrides: {
          root: { borderRadius: 12 },
        },
      },
    },
  });
}

export type { PaletteMode };

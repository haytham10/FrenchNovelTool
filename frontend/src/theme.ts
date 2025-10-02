import { createTheme } from '@mui/material/styles';
import type { PaletteMode } from '@mui/material';
import { tokens, rgbToHex } from './styles/tokens';

/**
 * Create MUI theme based on design tokens
 * Ensures consistency between MUI components and custom CSS
 */
export function getTheme(mode: PaletteMode) {
  const isDarkMode = mode === 'dark';
  const colorScheme = isDarkMode ? tokens.colors.dark : tokens.colors.light;

  return createTheme({
    palette: {
      mode,
      primary: { main: rgbToHex(colorScheme.primary) },
      secondary: { main: rgbToHex(colorScheme.secondary) },
      success: { main: rgbToHex(colorScheme.success) },
      warning: { main: rgbToHex(colorScheme.warning) },
      error: { main: rgbToHex(colorScheme.error) },
      background: {
        default: rgbToHex(colorScheme.bgDefault),
        paper: rgbToHex(colorScheme.bgPaper),
      },
      text: {
        primary: rgbToHex(colorScheme.text.primary),
        secondary: rgbToHex(colorScheme.text.secondary),
      },
    },
    shape: { borderRadius: parseInt(tokens.radius.md) * 16 }, // 12px
    typography: {
      fontFamily: tokens.typography.fontFamily,
      h1: { 
        fontSize: tokens.typography.fontSize['5xl'], 
        fontWeight: tokens.typography.fontWeight.extrabold, 
        letterSpacing: tokens.typography.letterSpacing.tight 
      },
      h2: { 
        fontSize: tokens.typography.fontSize['4xl'], 
        fontWeight: tokens.typography.fontWeight.bold, 
        letterSpacing: tokens.typography.letterSpacing.tight 
      },
      h3: { 
        fontSize: tokens.typography.fontSize['2xl'], 
        fontWeight: tokens.typography.fontWeight.bold 
      },
      h4: { 
        fontSize: tokens.typography.fontSize.xl, 
        fontWeight: tokens.typography.fontWeight.bold 
      },
      h5: { 
        fontSize: tokens.typography.fontSize.lg, 
        fontWeight: tokens.typography.fontWeight.semibold 
      },
      h6: { 
        fontSize: tokens.typography.fontSize.base, 
        fontWeight: tokens.typography.fontWeight.semibold 
      },
      subtitle1: { 
        fontSize: tokens.typography.fontSize.lg, 
        fontWeight: tokens.typography.fontWeight.medium 
      },
      body1: { 
        fontSize: tokens.typography.fontSize.base, 
        lineHeight: tokens.typography.lineHeight.relaxed 
      },
      body2: { 
        fontSize: tokens.typography.fontSize.sm, 
        lineHeight: tokens.typography.lineHeight.normal 
      },
      button: { 
        textTransform: 'none', 
        fontWeight: tokens.typography.fontWeight.semibold 
      },
    },
    spacing: 8, // 8px baseline grid
    components: {
      MuiContainer: {
        defaultProps: {
          maxWidth: 'lg',
        },
        styleOverrides: {
          root: {
            maxWidth: `${tokens.layout.maxWidth} !important`,
          },
        },
      },
      MuiPaper: {
        styleOverrides: {
          root: {
            backdropFilter: 'saturate(140%) blur(8px)',
          },
        },
      },
      MuiButton: {
        defaultProps: { 
          disableElevation: true,
        },
        styleOverrides: {
          root: { 
            borderRadius: parseInt(tokens.radius.md) * 16, // 12px
            transition: `all ${tokens.transition.normal} ${tokens.transition.easing.default}`,
          },
        },
      },
      MuiTextField: {
        styleOverrides: {
          root: {
            '& .MuiOutlinedInput-root': {
              borderRadius: parseInt(tokens.radius.base) * 16, // 8px
            },
          },
        },
      },
    },
  });
}

/**
 * Detect system theme preference
 * Returns 'light' or 'dark' based on user's OS preference
 */
export function getSystemThemePreference(): PaletteMode {
  if (typeof window === 'undefined') return 'light';
  
  const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
  return mediaQuery.matches ? 'dark' : 'light';
}

export type { PaletteMode };

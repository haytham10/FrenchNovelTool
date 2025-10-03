/**
 * Design Tokens
 * Central source of truth for all design values
 * These tokens are used by both MUI theme and CSS variables
 */

export const tokens = {
  // Color tokens (RGB values for CSS variables)
  colors: {
    light: {
      primary: { r: 79, g: 70, b: 229 },       // #4f46e5 - More distinctive indigo
      secondary: { r: 236, g: 72, b: 153 },    // #ec4899 - Pink accent for French flair
      tertiary: { r: 6, g: 182, b: 212 },      // #06b6d4 - Cyan for accents
      success: { r: 34, g: 197, b: 94 },       // #22c55e
      warning: { r: 245, g: 158, b: 11 },      // #f59e0b
      error: { r: 239, g: 68, b: 68 },         // #ef4444
      bgDefault: { r: 247, g: 248, b: 251 },   // #f7f8fb
      bgPaper: { r: 255, g: 255, b: 255 },     // #ffffff
      ring: { r: 99, g: 102, b: 241 },         // #6366f1 (indigo-500)
      text: {
        primary: { r: 17, g: 24, b: 39 },      // #111827
        secondary: { r: 107, g: 114, b: 128 }, // #6b7280
      },
    },
    dark: {
      primary: { r: 129, g: 140, b: 248 },     // #818cf8 - Lighter indigo for dark mode
      secondary: { r: 244, g: 114, b: 182 },   // #f472b6 - Pink accent for dark mode
      tertiary: { r: 125, g: 211, b: 252 },    // #7dd3fc - Cyan for dark mode
      success: { r: 34, g: 197, b: 94 },       // #22c55e
      warning: { r: 251, g: 191, b: 36 },      // #fbbf24
      error: { r: 248, g: 113, b: 113 },       // #f87171
      bgDefault: { r: 11, g: 18, b: 32 },      // #0b1220
      bgPaper: { r: 15, g: 23, b: 42 },        // #0f172a
      ring: { r: 165, g: 180, b: 252 },        // #a5b4fc (indigo-300)
      text: {
        primary: { r: 248, g: 250, b: 252 },   // #f8fafc
        secondary: { r: 148, g: 163, b: 184 }, // #94a3b8
      },
    },
  },

  // Typography scale
  typography: {
    fontFamily: 'var(--font-inter), Inter, system-ui, -apple-system, Segoe UI, Roboto, Arial, "Noto Sans", "Helvetica Neue", sans-serif',
    // French-literature inspired serif for headings
    serifFamily: 'var(--font-libre-baskerville), "Libre Baskerville", "Playfair Display", Georgia, "Times New Roman", serif',
    fontSize: {
      xs: '0.75rem',      // 12px
      sm: '0.875rem',     // 14px
      base: '1rem',       // 16px
      lg: '1.125rem',     // 18px
      xl: '1.25rem',      // 20px
      '2xl': '1.5rem',    // 24px
      '3xl': '1.875rem',  // 30px
      '4xl': '2rem',      // 32px
      '5xl': '2.75rem',   // 44px
    },
    fontWeight: {
      normal: 400,
      medium: 500,
      semibold: 600,
      bold: 700,
      extrabold: 800,
    },
    lineHeight: {
      tight: 1.25,
      normal: 1.5,
      relaxed: 1.65,
    },
    letterSpacing: {
      tight: '-0.02em',
      normal: '0',
      wide: '0.025em',
    },
  },

  // Spacing scale (8px baseline grid)
  spacing: {
    0: '0',
    0.5: '0.125rem',  // 2px
    1: '0.25rem',     // 4px
    1.5: '0.375rem',  // 6px
    2: '0.5rem',      // 8px (baseline)
    2.5: '0.625rem',  // 10px
    3: '0.75rem',     // 12px
    4: '1rem',        // 16px (2 * baseline)
    5: '1.25rem',     // 20px
    6: '1.5rem',      // 24px (3 * baseline)
    8: '2rem',        // 32px (4 * baseline)
    10: '2.5rem',     // 40px (5 * baseline)
    12: '3rem',       // 48px (6 * baseline)
    16: '4rem',       // 64px (8 * baseline)
    20: '5rem',       // 80px (10 * baseline)
    24: '6rem',       // 96px (12 * baseline)
  },

  // Border radius scale
  radius: {
    none: '0',
    sm: '0.25rem',    // 4px
    base: '0.5rem',   // 8px
    md: '0.75rem',    // 12px
    lg: '1rem',       // 16px
    xl: '1.5rem',     // 24px
    '2xl': '2rem',    // 32px
    full: '9999px',
  },

  // Elevation/Shadow scale
  elevation: {
    0: 'none',
    1: '0 1px 2px 0 rgb(0 0 0 / 0.05)',
    2: '0 1px 3px 0 rgb(0 0 0 / 0.1), 0 1px 2px -1px rgb(0 0 0 / 0.1)',
    3: '0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1)',
    4: '0 10px 15px -3px rgb(0 0 0 / 0.1), 0 4px 6px -4px rgb(0 0 0 / 0.1)',
    5: '0 20px 25px -5px rgb(0 0 0 / 0.1), 0 8px 10px -6px rgb(0 0 0 / 0.1)',
    6: '0 25px 50px -12px rgb(0 0 0 / 0.25)',
  },

  // Layout
  layout: {
    maxWidth: '1200px',
    containerPadding: {
      mobile: '1rem',     // 16px
      tablet: '2rem',     // 32px
      desktop: '3rem',    // 48px
    },
    headerHeight: '64px',
  },

  // Transitions
  transition: {
    fast: '150ms',
    normal: '300ms',
    slow: '500ms',
    easing: {
      default: 'cubic-bezier(0.4, 0, 0.2, 1)',
      in: 'cubic-bezier(0.4, 0, 1, 1)',
      out: 'cubic-bezier(0, 0, 0.2, 1)',
      inOut: 'cubic-bezier(0.4, 0, 0.2, 1)',
    },
  },
} as const;

// Helper to convert RGB object to CSS variable format
export const rgbToCssVar = (rgb: { r: number; g: number; b: number }) => 
  `${rgb.r} ${rgb.g} ${rgb.b}`;

// Helper to get hex color from RGB
export const rgbToHex = (rgb: { r: number; g: number; b: number }) => 
  `#${rgb.r.toString(16).padStart(2, '0')}${rgb.g.toString(16).padStart(2, '0')}${rgb.b.toString(16).padStart(2, '0')}`;

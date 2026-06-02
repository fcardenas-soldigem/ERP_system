import { extendTheme } from '@chakra-ui/react';

// ─── Color Palette ────────────────────────────────────────────────────────────
// Inspired by Linear (slate), Stripe (indigo/trust), Ramp (green/finance),
// Notion (clean neutrals). Primary is a slate-blue that reads professional
// without falling into the generic purple trap.

const colors = {
  // Primary — slate blue (Linear-inspired, not purple)
  primary: {
    50:  '#eff4ff',
    100: '#dbe8fe',
    200: '#bfd3fe',
    300: '#93b4fd',
    400: '#608af9',
    500: '#3b6feb',  // brand primary
    600: '#2554d1',
    700: '#1d44b8',
    800: '#1e3a95',
    900: '#1e3376',
  },

  // Neutral — warm slate (Notion/Linear gray scale)
  neutral: {
    0:   '#ffffff',
    50:  '#f8f9fb',
    100: '#f1f3f6',
    200: '#e4e8ef',
    300: '#d0d6e1',
    400: '#a9b3c2',
    500: '#7b8899',
    600: '#5c6879',
    700: '#43505f',
    800: '#2e3845',
    900: '#1a2230',
  },

  // Success — finance green (Ramp-inspired)
  success: {
    50:  '#f0fdf5',
    100: '#dcfce9',
    200: '#bbf7d3',
    300: '#86efb4',
    400: '#4ade80',
    500: '#22c55e',
    600: '#16a34a',
    700: '#15803d',
    800: '#166534',
    900: '#14532d',
  },

  // Warning — amber
  warning: {
    50:  '#fffbeb',
    100: '#fef3c7',
    200: '#fde68a',
    300: '#fcd34d',
    400: '#fbbf24',
    500: '#f59e0b',
    600: '#d97706',
    700: '#b45309',
    800: '#92400e',
    900: '#78350f',
  },

  // Error — red (clear, never orange)
  error: {
    50:  '#fff1f2',
    100: '#ffe4e6',
    200: '#fecdd3',
    300: '#fda4af',
    400: '#fb7185',
    500: '#f43f5e',
    600: '#e11d48',
    700: '#be123c',
    800: '#9f1239',
    900: '#881337',
  },
};

// ─── Typography ───────────────────────────────────────────────────────────────
// Inter as primary UI font (Google Fonts or system install).
// Scale follows a 1.250 Major Third ratio (10 → 12 → 14 → 16 → 20 → 24 → 30 → 36 → 48).

const fonts = {
  heading: `'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif`,
  body:    `'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif`,
  mono:    `'JetBrains Mono', 'Fira Code', 'Cascadia Code', monospace`,
};

const fontSizes = {
  '2xs': '0.625rem',  // 10px
  xs:    '0.75rem',   // 12px
  sm:    '0.875rem',  // 14px
  md:    '1rem',      // 16px  ← body
  lg:    '1.125rem',  // 18px
  xl:    '1.25rem',   // 20px  ← h6
  '2xl': '1.5rem',    // 24px  ← h5
  '3xl': '1.875rem',  // 30px  ← h4
  '4xl': '2.25rem',   // 36px  ← h3
  '5xl': '3rem',      // 48px  ← h2
  '6xl': '3.75rem',   // 60px  ← h1
};

const fontWeights = {
  normal:   400,
  medium:   500,
  semibold: 600,
  bold:     700,
};

const lineHeights = {
  none:     1,
  tight:    1.2,   // headings
  snug:     1.35,
  normal:   1.5,   // body
  relaxed:  1.625,
};

const letterSpacings = {
  tighter: '-0.03em',
  tight:   '-0.015em',
  normal:  '0em',
  wide:    '0.01em',
};

// ─── Spacing (4px base) ───────────────────────────────────────────────────────

const space = {
  px:  '1px',
  0.5: '0.125rem',  // 2px
  1:   '0.25rem',   // 4px
  1.5: '0.375rem',  // 6px
  2:   '0.5rem',    // 8px
  2.5: '0.625rem',  // 10px
  3:   '0.75rem',   // 12px
  3.5: '0.875rem',  // 14px
  4:   '1rem',      // 16px
  5:   '1.25rem',   // 20px
  6:   '1.5rem',    // 24px
  7:   '1.75rem',   // 28px
  8:   '2rem',      // 32px
  9:   '2.25rem',   // 36px
  10:  '2.5rem',    // 40px
  12:  '3rem',      // 48px
  14:  '3.5rem',    // 56px
  16:  '4rem',      // 64px
  20:  '5rem',      // 80px
  24:  '6rem',      // 96px
  28:  '7rem',      // 112px
  32:  '8rem',      // 128px
};

// ─── Border Radius ────────────────────────────────────────────────────────────
// Hierarchy: cards use md/lg, buttons use md, badges use sm, inputs use md.
// No uniform bubbly radius on everything (AI slop pattern).

const radii = {
  none:  '0',
  sm:    '0.25rem',  // 4px  — tags, badges
  md:    '0.375rem', // 6px  — inputs, buttons (default)
  lg:    '0.5rem',   // 8px  — cards, dropdowns
  xl:    '0.75rem',  // 12px — modals, large cards
  '2xl': '1rem',     // 16px — feature sections
  full:  '9999px',   // pills
};

// ─── Shadows ──────────────────────────────────────────────────────────────────
// Minimal elevation system. Linear uses very subtle shadows.

const shadows = {
  xs:   '0 1px 2px 0 rgba(0,0,0,0.05)',
  sm:   '0 1px 3px 0 rgba(0,0,0,0.07), 0 1px 2px -1px rgba(0,0,0,0.07)',
  md:   '0 4px 6px -1px rgba(0,0,0,0.06), 0 2px 4px -2px rgba(0,0,0,0.06)',
  lg:   '0 10px 15px -3px rgba(0,0,0,0.06), 0 4px 6px -4px rgba(0,0,0,0.06)',
  xl:   '0 20px 25px -5px rgba(0,0,0,0.08), 0 8px 10px -6px rgba(0,0,0,0.08)',
  // Floating panels (dropdowns, popovers)
  float: '0 4px 24px rgba(0,0,0,0.10)',
  // Focus rings
  outline: '0 0 0 3px rgba(59,111,235,0.35)',
};

// ─── Component Overrides ──────────────────────────────────────────────────────

const components = {
  Button: {
    baseStyle: {
      fontWeight: 'medium',
      borderRadius: 'md',
      _focus: { boxShadow: 'outline' },
    },
    defaultProps: { colorScheme: 'primary' },
  },

  Input: {
    defaultProps: { focusBorderColor: 'primary.500' },
    baseStyle: {
      field: {
        borderRadius: 'md',
        _focus: { boxShadow: 'outline' },
      },
    },
  },

  Select: {
    defaultProps: { focusBorderColor: 'primary.500' },
  },

  Textarea: {
    defaultProps: { focusBorderColor: 'primary.500' },
  },

  Card: {
    baseStyle: {
      container: {
        borderRadius: 'lg',
        boxShadow: 'sm',
        border: '1px solid',
        borderColor: 'neutral.200',
      },
    },
  },

  Badge: {
    baseStyle: {
      borderRadius: 'sm',
      fontWeight: 'medium',
      fontSize: 'xs',
      textTransform: 'none',
      letterSpacing: 'normal',
    },
  },

  Heading: {
    baseStyle: {
      fontWeight: 'semibold',
      letterSpacing: 'tight',
      lineHeight: 'tight',
    },
  },

  Table: {
    variants: {
      simple: {
        th: {
          fontSize: 'xs',
          fontWeight: 'semibold',
          color: 'neutral.500',
          textTransform: 'uppercase',
          letterSpacing: 'wide',
          borderColor: 'neutral.200',
          px: 4,
          py: 3,
        },
        td: {
          borderColor: 'neutral.200',
          px: 4,
          py: 3,
          fontSize: 'sm',
        },
      },
    },
  },
};

// ─── Global Styles ────────────────────────────────────────────────────────────

const styles = {
  global: (props) => ({
    body: {
      bg: props.colorMode === 'dark' ? 'neutral.900' : 'neutral.50',
      color: props.colorMode === 'dark' ? 'neutral.100' : 'neutral.800',
      fontSize: 'md',
      lineHeight: 'normal',
      fontFeatureSettings: '"cv02", "cv03", "cv04", "cv11"', // Inter OpenType features
    },
    // Tabular numbers in all table cells and stat numbers
    'td, [data-stat]': {
      fontVariantNumeric: 'tabular-nums',
    },
    // Better focus visibility
    '*:focus-visible': {
      outline: 'none',
      boxShadow: 'outline',
    },
  }),
};

// ─── Theme Config ─────────────────────────────────────────────────────────────

const config = {
  initialColorMode: 'light',
  useSystemColorMode: false,
};

// ─── Semantic Tokens ──────────────────────────────────────────────────────────
// These let components use semantic names that auto-switch in dark mode.

const semanticTokens = {
  colors: {
    'bg.default':     { default: 'neutral.50',  _dark: 'neutral.900' },
    'bg.surface':     { default: 'white',        _dark: 'neutral.800' },
    'bg.subtle':      { default: 'neutral.100',  _dark: 'neutral.800' },
    'border.default': { default: 'neutral.200',  _dark: 'neutral.700' },
    'text.default':   { default: 'neutral.800',  _dark: 'neutral.100' },
    'text.subtle':    { default: 'neutral.500',  _dark: 'neutral.400' },
    'text.muted':     { default: 'neutral.400',  _dark: 'neutral.500' },
  },
};

const theme = extendTheme({
  colors,
  fonts,
  fontSizes,
  fontWeights,
  lineHeights,
  letterSpacings,
  space,
  radii,
  shadows,
  components,
  styles,
  config,
  semanticTokens,
});

export default theme;

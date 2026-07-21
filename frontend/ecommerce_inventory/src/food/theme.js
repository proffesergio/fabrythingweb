import { createTheme } from '@mui/material/styles';

// "Spice market" identity — warm, appetizing. Food photography reads as
// appetizing on warm surfaces, so the dark mode below is a warm charcoal
// (roasted-coffee browns), never the blue-grey of a generic dark theme.
export const FOOD = {
  canvas: '#FDF8F3',   // soft warm white
  surface: '#FFFFFF',
  ink: '#241812',      // roasted espresso (warm near-black)
  muted: '#8C7B6E',    // warm taupe
  line: '#EFE6DC',     // warm hairline
  primary: '#E8452B',  // chili tomato — appetite, CTAs
  primaryDeep: '#C4361F',
  turmeric: '#F4A62A', // ratings, highlights
  cardamom: '#2F7D4F', // open / veg / success
};

// Dark counterpart. `primary` is lifted deliberately: #E8452B on a dark surface
// goes muddy and fails contrast for text, so dark mode uses a brighter chili.
export const FOOD_DARK = {
  canvas: '#17110E',   // warm charcoal, not blue-grey
  surface: '#211915',
  ink: '#F6EDE5',      // warm off-white
  muted: '#AD9C8E',    // readable warm taupe on dark
  line: '#33261F',
  primary: '#FF6B4F',
  primaryDeep: '#E8452B',
  turmeric: '#FFBC4D',
  cardamom: '#4CAF7A',
};

// Components that need a raw colour (not a palette slot) should call this
// rather than importing FOOD directly, or they will stay light in dark mode.
export const foodTokens = (mode) => (mode === 'dark' ? FOOD_DARK : FOOD);

const display = "'Bricolage Grotesque', 'Plus Jakarta Sans', sans-serif";
const body = "'Plus Jakarta Sans', 'Inter', system-ui, sans-serif";

export function getFoodTheme(mode = 'light') {
  const isDark = mode === 'dark';
  const C = foodTokens(mode);

  return createTheme({
    palette: {
      mode: isDark ? 'dark' : 'light',
      primary: { main: C.primary, dark: C.primaryDeep, contrastText: '#FFFFFF' },
      secondary: { main: C.turmeric, contrastText: '#3A2A05' },
      success: { main: C.cardamom, contrastText: '#FFFFFF' },
      warning: { main: C.turmeric },
      error: { main: isDark ? '#F2665F' : '#D64541' },
      background: { default: C.canvas, paper: C.surface },
      text: { primary: C.ink, secondary: C.muted },
      divider: C.line,
    },
    typography: {
      fontFamily: body,
      h1: { fontFamily: display, fontWeight: 800, letterSpacing: '-0.02em' },
      h2: { fontFamily: display, fontWeight: 800, letterSpacing: '-0.02em' },
      h3: { fontFamily: display, fontWeight: 800, letterSpacing: '-0.02em' },
      h4: { fontFamily: display, fontWeight: 800, letterSpacing: '-0.02em' },
      h5: { fontFamily: display, fontWeight: 700, letterSpacing: '-0.01em' },
      h6: { fontFamily: display, fontWeight: 700 },
      subtitle1: { fontWeight: 600 },
      subtitle2: { fontWeight: 600 },
      button: { textTransform: 'none', fontWeight: 700, letterSpacing: 0 },
      overline: { fontWeight: 700, letterSpacing: '0.14em' },
    },
    shape: { borderRadius: 16 },
    components: {
      MuiCssBaseline: {
        styleOverrides: {
          body: { backgroundColor: C.canvas },
        },
      },
      MuiButton: {
        styleOverrides: {
          root: { borderRadius: 12, padding: '10px 20px', boxShadow: 'none' },
          containedPrimary: {
            background: `linear-gradient(180deg, ${C.primary}, ${C.primaryDeep})`,
            '&:hover': {
              background: C.primaryDeep,
              boxShadow: `0 8px 20px ${isDark ? 'rgba(255,107,79,0.32)' : 'rgba(232,69,43,0.30)'}`,
            },
          },
        },
      },
      MuiCard: {
        styleOverrides: {
          root: {
            backgroundImage: 'none',
            borderRadius: 22,
            border: `1px solid ${C.line}`,
            // A pale drop shadow is invisible on a dark canvas — deepen it so
            // cards still separate from the background.
            boxShadow: isDark
              ? '0 6px 22px rgba(0,0,0,0.45)'
              : '0 6px 22px rgba(120,60,20,0.06)',
          },
        },
      },
      MuiPaper: { styleOverrides: { root: { backgroundImage: 'none' } } },
      MuiAppBar: {
        styleOverrides: {
          root: {
            backgroundColor: isDark ? 'rgba(23,17,14,0.86)' : 'rgba(253,248,243,0.86)',
            backdropFilter: 'blur(14px)',
            WebkitBackdropFilter: 'blur(14px)',
            color: C.ink,
            boxShadow: `inset 0 -1px 0 0 ${C.line}`,
          },
        },
      },
      MuiChip: {
        styleOverrides: {
          root: { borderRadius: 999, fontWeight: 700, fontFamily: body },
        },
      },
      MuiOutlinedInput: {
        styleOverrides: {
          root: {
            borderRadius: 14,
            backgroundColor: C.surface,
            '& fieldset': { borderColor: C.line },
          },
        },
      },
      MuiDialog: { styleOverrides: { paper: { borderRadius: 24 } } },
    },
  });
}

export default getFoodTheme();

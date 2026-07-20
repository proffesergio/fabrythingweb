import { createTheme } from '@mui/material/styles';

// "Spice market" identity — warm, appetizing, light-forward. Deliberately not the
// dark-tech food-app default: food photography reads as appetizing on warm surfaces.
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

const display = "'Bricolage Grotesque', 'Plus Jakarta Sans', sans-serif";
const body = "'Plus Jakarta Sans', 'Inter', system-ui, sans-serif";

export function getFoodTheme() {
  return createTheme({
    palette: {
      mode: 'light',
      primary: { main: FOOD.primary, dark: FOOD.primaryDeep, contrastText: '#FFFFFF' },
      secondary: { main: FOOD.turmeric, contrastText: '#3A2A05' },
      success: { main: FOOD.cardamom, contrastText: '#FFFFFF' },
      warning: { main: FOOD.turmeric },
      error: { main: '#D64541' },
      background: { default: FOOD.canvas, paper: FOOD.surface },
      text: { primary: FOOD.ink, secondary: FOOD.muted },
      divider: FOOD.line,
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
          body: { backgroundColor: FOOD.canvas },
        },
      },
      MuiButton: {
        styleOverrides: {
          root: { borderRadius: 12, padding: '10px 20px', boxShadow: 'none' },
          containedPrimary: {
            background: `linear-gradient(180deg, ${FOOD.primary}, ${FOOD.primaryDeep})`,
            '&:hover': { background: FOOD.primaryDeep, boxShadow: '0 8px 20px rgba(232,69,43,0.30)' },
          },
        },
      },
      MuiCard: {
        styleOverrides: {
          root: {
            backgroundImage: 'none',
            borderRadius: 22,
            border: `1px solid ${FOOD.line}`,
            boxShadow: '0 6px 22px rgba(120,60,20,0.06)',
          },
        },
      },
      MuiPaper: { styleOverrides: { root: { backgroundImage: 'none' } } },
      MuiAppBar: {
        styleOverrides: {
          root: {
            backgroundColor: 'rgba(253,248,243,0.86)',
            backdropFilter: 'blur(14px)',
            WebkitBackdropFilter: 'blur(14px)',
            color: FOOD.ink,
            boxShadow: `inset 0 -1px 0 0 ${FOOD.line}`,
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
            backgroundColor: FOOD.surface,
            '& fieldset': { borderColor: FOOD.line },
          },
        },
      },
      MuiDialog: { styleOverrides: { paper: { borderRadius: 24 } } },
    },
  });
}

export default getFoodTheme();

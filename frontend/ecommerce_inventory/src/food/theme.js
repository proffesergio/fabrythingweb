import { createTheme } from '@mui/material/styles';

// Dark, immersive food-app theme — deliberately distinct from the storefront
// (clothing) theme so selecting "Food" visibly switches the whole experience.
export function getFoodTheme() {
  return createTheme({
    palette: {
      mode: 'dark',
      primary: { main: '#FF6B35', light: '#FF8C5F', dark: '#E14E1D', contrastText: '#FFFFFF' },
      secondary: { main: '#FFC93C', contrastText: '#1A1200' },
      background: { default: '#0E0F12', paper: '#17191F' },
      text: { primary: '#F5F6F7', secondary: '#9BA1AC' },
      divider: '#262A32',
      success: { main: '#22C55E' }, warning: { main: '#F59E0B' }, error: { main: '#EF4444' },
    },
    typography: {
      fontFamily: "'Inter','Roboto','Helvetica Neue',sans-serif",
      h1: { fontWeight: 800, letterSpacing: '-0.03em' },
      h4: { fontWeight: 800 }, h5: { fontWeight: 700 }, h6: { fontWeight: 700 },
      button: { textTransform: 'none', fontWeight: 700 },
    },
    shape: { borderRadius: 16 },
    components: {
      MuiButton: {
        styleOverrides: {
          root: { borderRadius: 999, padding: '10px 22px', boxShadow: 'none' },
          containedPrimary: { background: 'linear-gradient(135deg,#FF8C5F,#E14E1D)' },
        },
      },
      MuiCard: { styleOverrides: { root: { backgroundImage: 'none', border: '1px solid #262A32', borderRadius: 20 } } },
      MuiPaper: { styleOverrides: { root: { backgroundImage: 'none' } } },
      MuiAppBar: {
        styleOverrides: {
          root: {
            backgroundColor: 'rgba(14,15,18,0.85)', backdropFilter: 'blur(14px)',
            WebkitBackdropFilter: 'blur(14px)', color: '#F5F6F7', boxShadow: '0 1px 0 0 #262A32',
          },
        },
      },
      MuiChip: { styleOverrides: { root: { borderRadius: 999, fontWeight: 600 } } },
      MuiOutlinedInput: { styleOverrides: { root: { borderRadius: 12 } } },
    },
  });
}

export default getFoodTheme();

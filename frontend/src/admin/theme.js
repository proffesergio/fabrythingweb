import { createTheme } from '@mui/material/styles';

export const controlCenterTheme = createTheme({
  palette: {
    mode: 'dark',
    primary: { main: '#58d6e7' },
    secondary: { main: '#e85d4a' },
    background: { default: '#0b1016', paper: '#111a24' },
    text: { primary: '#eef4fa', secondary: '#a7b8c8' },
    divider: '#293747',
  },
  shape: { borderRadius: 8 },
  typography: { fontFamily: "Roboto, 'Segoe UI', sans-serif", button: { textTransform: 'none' } },
  components: {
    MuiPaper: { styleOverrides: { root: { backgroundImage: 'none' } } },
    MuiCard: { styleOverrides: { root: { border: '1px solid #293747', boxShadow: 'none' } } },
    MuiListItemIcon: { styleOverrides: { root: { minWidth: 34 } } },
  },
});

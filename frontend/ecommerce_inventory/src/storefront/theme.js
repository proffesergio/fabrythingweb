import { createTheme } from "@mui/material/styles";

export function getStorefrontTheme(mode) {
    const isDark = mode === 'dark';

    return createTheme({
        palette: {
            mode,
            primary: {
                main:          isDark ? '#818CF8' : '#4F46E5',
                light:         isDark ? '#A5B4FC' : '#6366F1',
                dark:          isDark ? '#6366F1' : '#3730A3',
                contrastText:  '#FFFFFF',
            },
            secondary: {
                main:          '#E85D4A',   // brand coral — kept for all CTAs
                light:         '#FF7B6A',
                dark:          '#C44535',
                contrastText:  '#FFFFFF',
            },
            background: {
                default: isDark ? '#0F172A' : '#F8FAFC',
                paper:   isDark ? '#1E293B' : '#FFFFFF',
            },
            text: {
                primary:   isDark ? '#F1F5F9' : '#0F172A',
                secondary: isDark ? '#94A3B8' : '#64748B',
            },
            divider:  isDark ? '#334155' : '#E2E8F0',
            success:  { main: '#10B981' },
            warning:  { main: '#F59E0B' },
            error:    { main: '#EF4444' },
            info:     { main: isDark ? '#38BDF8' : '#0EA5E9' },
        },
        typography: {
            fontFamily: "'Inter', 'Roboto', 'Helvetica Neue', sans-serif",
            h1: { fontWeight: 800, letterSpacing: '-0.025em' },
            h2: { fontWeight: 700, letterSpacing: '-0.02em' },
            h3: { fontWeight: 700, letterSpacing: '-0.01em' },
            h4: { fontWeight: 700 },
            h5: { fontWeight: 600 },
            h6: { fontWeight: 600 },
            button: { textTransform: 'none', fontWeight: 600 },
        },
        shape: { borderRadius: 10 },
        components: {
            MuiButton: {
                styleOverrides: {
                    root: {
                        borderRadius: 10,
                        padding: '10px 24px',
                        fontSize: '0.95rem',
                        boxShadow: 'none',
                        '&:hover': { boxShadow: 'none' },
                    },
                    containedPrimary: {
                        background: isDark
                            ? 'linear-gradient(135deg,#818CF8,#6366F1)'
                            : 'linear-gradient(135deg,#6366F1,#4F46E5)',
                        '&:hover': {
                            background: isDark
                                ? 'linear-gradient(135deg,#A5B4FC,#818CF8)'
                                : 'linear-gradient(135deg,#4F46E5,#3730A3)',
                        },
                    },
                    containedSecondary: {
                        background: 'linear-gradient(135deg,#E85D4A,#C44535)',
                        '&:hover': { background: 'linear-gradient(135deg,#C44535,#A33020)' },
                    },
                },
            },
            MuiCard: {
                styleOverrides: {
                    root: {
                        backgroundImage: 'none',
                        boxShadow: isDark
                            ? '0 1px 3px rgba(0,0,0,0.35)'
                            : '0 1px 3px rgba(0,0,0,0.06)',
                        border: `1px solid ${isDark ? '#334155' : '#E2E8F0'}`,
                        transition: 'box-shadow 0.2s ease, border-color 0.2s ease, transform 0.2s ease',
                        '&:hover': {
                            boxShadow: isDark
                                ? '0 8px 24px rgba(0,0,0,0.5)'
                                : '0 8px 24px rgba(0,0,0,0.09)',
                            borderColor: isDark ? '#475569' : '#C7D2FE',
                        },
                    },
                },
            },
            MuiAppBar: {
                styleOverrides: {
                    root: {
                        backgroundColor: isDark
                            ? 'rgba(15,23,42,0.82)'
                            : 'rgba(255,255,255,0.82)',
                        backdropFilter: 'blur(14px)',
                        WebkitBackdropFilter: 'blur(14px)',
                        color: isDark ? '#F1F5F9' : '#0F172A',
                        boxShadow: `0 1px 0 0 ${isDark ? '#334155' : '#E2E8F0'}`,
                    },
                },
            },
            MuiPaper: {
                styleOverrides: {
                    root: { backgroundImage: 'none' },
                },
            },
            MuiDrawer: {
                styleOverrides: {
                    paper: { backgroundImage: 'none' },
                },
            },
            MuiChip: {
                styleOverrides: {
                    root: { borderRadius: 8, fontWeight: 500 },
                },
            },
            MuiOutlinedInput: {
                styleOverrides: {
                    root: { borderRadius: 10 },
                },
            },
        },
    });
}

export default getStorefrontTheme('light');

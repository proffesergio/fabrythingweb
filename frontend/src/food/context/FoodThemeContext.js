import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import { ThemeProvider } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';
import { getFoodTheme } from '../theme';

const KEY = 'food_theme';

const Ctx = createContext({ mode: 'light', toggleMode: () => {}, setMode: () => {} });
export const useFoodTheme = () => useContext(Ctx);

// Read the stored choice once, up front, so the first paint is already correct
// — flipping the theme after mount produces a visible white flash in dark mode.
// With no stored choice we follow the OS setting rather than forcing light.
function initialMode() {
  try {
    const saved = localStorage.getItem(KEY);
    if (saved === 'light' || saved === 'dark') return saved;
    return window.matchMedia?.('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
  } catch {
    return 'light';
  }
}

export function FoodThemeProvider({ children }) {
  const [mode, setModeState] = useState(initialMode);

  const setMode = useCallback((next) => {
    setModeState(next);
    try { localStorage.setItem(KEY, next); } catch { /* private mode — session only */ }
  }, []);

  const toggleMode = useCallback(
    () => setMode(mode === 'dark' ? 'light' : 'dark'),
    [mode, setMode]
  );

  // Follow the OS only while the user hasn't made an explicit choice.
  useEffect(() => {
    const mq = window.matchMedia?.('(prefers-color-scheme: dark)');
    if (!mq) return undefined;
    const onChange = (e) => {
      if (!localStorage.getItem(KEY)) setModeState(e.matches ? 'dark' : 'light');
    };
    mq.addEventListener?.('change', onChange);
    return () => mq.removeEventListener?.('change', onChange);
  }, []);

  const theme = useMemo(() => getFoodTheme(mode), [mode]);
  const value = useMemo(() => ({ mode, setMode, toggleMode }), [mode, setMode, toggleMode]);

  return (
    <Ctx.Provider value={value}>
      <ThemeProvider theme={theme}>
        {/* CssBaseline repaints the page background when the mode flips;
            without it the <body> keeps the old canvas colour. */}
        <CssBaseline />
        {children}
      </ThemeProvider>
    </Ctx.Provider>
  );
}

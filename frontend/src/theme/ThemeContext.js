import React, { createContext, useContext, useEffect, useMemo, useState } from 'react';
import { createTheme, responsiveFontSizes } from '@mui/material/styles';
import { ThemeProvider } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';

const MODE_KEY = 'attendx-theme-mode';
const ThemeModeContext = createContext({ mode: 'light', toggleMode: () => {}, setMode: () => {} });

export const useThemeMode = () => useContext(ThemeModeContext);

/** Central theme factory — navy/orange AttendX identity, both color modes. */
export function createAppTheme(mode) {
  const dark = mode === 'dark';
  const theme = createTheme({
    palette: {
      mode,
      primary: { main: '#1976d2', light: '#42a5f5', dark: '#1565c0' },
      secondary: { main: '#f97316', light: '#fb923c', dark: '#ea580c' },
      background: dark
        ? { default: '#0f172a', paper: '#1e293b' }
        : { default: '#f5f5f5', paper: '#ffffff' },
      text: dark
        ? { primary: '#e2e8f0', secondary: '#94a3b8' }
        : { primary: '#212E46', secondary: '#64748b' },
      success: { main: '#16a34a' },
      warning: { main: '#d97706' },
      error: { main: '#dc2626' },
      divider: dark ? 'rgba(255,255,255,0.12)' : 'rgba(15,23,42,0.08)',
    },
    typography: {
      fontFamily: '"Inter", "Roboto", "Helvetica", "Arial", sans-serif',
      h1: { fontWeight: 700, letterSpacing: '-0.03em' },
      h2: { fontWeight: 700, letterSpacing: '-0.03em' },
      h3: { fontWeight: 700, letterSpacing: '-0.025em' },
      h4: { fontWeight: 700, letterSpacing: '-0.02em' },
      h5: { fontWeight: 600 },
      h6: { fontWeight: 600 },
      button: { fontWeight: 600 },
    },
    shape: { borderRadius: 12 },
    components: {
      MuiButton: {
        styleOverrides: { root: { textTransform: 'none', borderRadius: 10, paddingInline: 18 } },
      },
      MuiCard: {
        styleOverrides: {
          root: {
            borderRadius: 16,
            boxShadow: dark
              ? '0 10px 30px -12px rgba(0,0,0,0.6)'
              : '0 10px 30px -12px rgba(15,23,42,0.12)',
          },
        },
      },
      MuiPaper: {
        styleOverrides: { rounded: { borderRadius: 14 } },
      },
      MuiTextField: {
        styleOverrides: { root: { '& .MuiOutlinedInput-root': { borderRadius: 10 } } },
      },
      MuiChip: {
        styleOverrides: { root: { fontWeight: 600 } },
      },
    },
  });
  return responsiveFontSizes(theme);
}

export function ThemeModeProvider({ children }) {
  const [mode, setMode] = useState(() => {
    try {
      const saved = localStorage.getItem(MODE_KEY);
      return saved === 'dark' || saved === 'light' ? saved : 'light';
    } catch {
      return 'light';
    }
  });

  useEffect(() => {
    try { localStorage.setItem(MODE_KEY, mode); } catch { /* storage may be disabled */ }
  }, [mode]);

  const value = useMemo(() => ({
    mode,
    setMode,
    toggleMode: () => setMode((m) => (m === 'light' ? 'dark' : 'light')),
  }), [mode]);

  const theme = useMemo(() => createAppTheme(mode), [mode]);

  return (
    <ThemeModeContext.Provider value={value}>
      <ThemeProvider theme={theme}>
        <CssBaseline />
        {children}
      </ThemeProvider>
    </ThemeModeContext.Provider>
  );
}

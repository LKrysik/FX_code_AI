'use client';

import React from 'react';
import { ThemeProvider as MuiThemeProvider } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';
import { createTheme } from '@mui/material/styles';
import { Inter } from 'next/font/google';

const inter = Inter({ subsets: ['latin'] });

const theme = createTheme({
  palette: {
    mode: 'dark',
    primary: {
      main: '#00d4aa', // Professional crypto green
      light: '#33e0bd',
      dark: '#00a67a',
      contrastText: '#ffffff',
    },
    secondary: {
      main: '#6366f1', // Modern indigo
      light: '#818cf8',
      dark: '#4f46e5',
      contrastText: '#ffffff',
    },
    error: {
      main: '#ef4444', // Modern red
      light: '#f87171',
      dark: '#dc2626',
    },
    warning: {
      main: '#f59e0b', // Modern amber
      light: '#fbbf24',
      dark: '#d97706',
    },
    info: {
      main: '#3b82f6', // Modern blue
      light: '#60a5fa',
      dark: '#2563eb',
    },
    success: {
      main: '#10b981', // Modern emerald
      light: '#34d399',
      dark: '#059669',
    },
    background: {
      default: '#0f172a', // Modern dark slate
      paper: '#1e293b', // Lighter slate for cards
    },
    text: {
      primary: '#f8fafc', // Almost white
      secondary: '#cbd5e1', // Light gray
    },
    divider: '#334155', // Slate divider
    // Custom trading colors
    bullish: {
      main: '#00d4aa',
      light: '#33e0bd',
      dark: '#00a67a',
    },
    bearish: {
      main: '#ef4444',
      light: '#f87171',
      dark: '#dc2626',
    },
    pump: {
      main: '#f59e0b',
      light: '#fbbf24',
      dark: '#d97706',
    },
    dump: {
      main: '#8b5cf6',
      light: '#a78bfa',
      dark: '#7c3aed',
    },
  },
  typography: {
    fontFamily: inter.style.fontFamily,
    h1: {
      fontSize: '2.5rem',
      fontWeight: 600,
      lineHeight: 1.2,
    },
    h2: {
      fontSize: '2rem',
      fontWeight: 600,
      lineHeight: 1.3,
    },
    h3: {
      fontSize: '1.75rem',
      fontWeight: 600,
      lineHeight: 1.4,
    },
    h4: {
      fontSize: '1.5rem',
      fontWeight: 500,
      lineHeight: 1.4,
    },
    h5: {
      fontSize: '1.25rem',
      fontWeight: 500,
      lineHeight: 1.5,
    },
    h6: {
      fontSize: '1.125rem',
      fontWeight: 500,
      lineHeight: 1.5,
    },
    body1: {
      fontSize: '1rem',
      lineHeight: 1.6,
    },
    body2: {
      fontSize: '0.875rem',
      lineHeight: 1.5,
    },
    caption: {
      fontSize: '0.75rem',
      lineHeight: 1.4,
    },
  },
  components: {
    MuiCssBaseline: {
      styleOverrides: {
        body: {
          scrollbarWidth: 'thin',
          '&::-webkit-scrollbar': {
            width: '8px',
          },
          '&::-webkit-scrollbar-track': {
            background: '#0f172a',
          },
          '&::-webkit-scrollbar-thumb': {
            background: '#475569',
            borderRadius: '4px',
          },
          '&::-webkit-scrollbar-thumb:hover': {
            background: '#64748b',
          },
        },
        '@keyframes pulse': {
          '0%': {
            opacity: 1,
          },
          '50%': {
            opacity: 0.5,
          },
          '100%': {
            opacity: 1,
          },
        },
        '@keyframes fadeIn': {
          '0%': {
            opacity: 0,
            transform: 'translateY(10px)',
          },
          '100%': {
            opacity: 1,
            transform: 'translateY(0)',
          },
        },
      },
    },
    MuiDrawer: {
      styleOverrides: {
        paper: {
          backgroundColor: '#1e293b',
          borderRight: '1px solid #334155',
          backgroundImage: 'linear-gradient(180deg, #1e293b 0%, #0f172a 100%)',
          // Ensure drawer doesn't interfere with main content
          position: 'fixed',
          top: 0,
          left: 0,
          height: '100vh',
          overflowX: 'hidden',
          zIndex: 1200, // Below AppBar (1300)
        },
      },
    },
    MuiAppBar: {
      styleOverrides: {
        root: {
          backgroundColor: '#1e293b',
          borderBottom: '1px solid #334155',
          boxShadow: '0 1px 3px rgba(0,0,0,0.1), 0 1px 2px rgba(0,0,0,0.06)',
          backdropFilter: 'blur(8px)',
          zIndex: 1300, // Above drawer
        },
      },
    },
    // Fix for main content area
    MuiBox: {
      styleOverrides: {
        root: {
          '&.main-content': {
            marginLeft: 0,
            '@media (min-width: 960px)': {
              marginLeft: '280px', // drawerWidth
            },
            transition: 'margin 0.2s ease-in-out',
          },
        },
      },
    },
    MuiCard: {
      styleOverrides: {
        root: {
          backgroundColor: '#1e293b',
          border: '1px solid #334155',
          borderRadius: '12px',
          boxShadow: '0 4px 6px -1px rgba(0,0,0,0.1), 0 2px 4px -1px rgba(0,0,0,0.06)',
          transition: 'all 0.2s ease-in-out',
          '&:hover': {
            boxShadow: '0 10px 15px -3px rgba(0,0,0,0.1), 0 4px 6px -2px rgba(0,0,0,0.05)',
            transform: 'translateY(-1px)',
          },
        },
      },
    },
    MuiChip: {
      styleOverrides: {
        root: {
          borderRadius: '6px',
          fontWeight: 500,
        },
        colorSuccess: {
          backgroundColor: '#4caf50',
          color: '#000',
        },
        colorError: {
          backgroundColor: '#ff4444',
          color: '#fff',
        },
        colorWarning: {
          backgroundColor: '#ff9800',
          color: '#000',
        },
        colorInfo: {
          backgroundColor: '#2196f3',
          color: '#fff',
        },
      },
    },
    MuiButton: {
      styleOverrides: {
        root: {
          borderRadius: '6px',
          textTransform: 'none',
          fontWeight: 500,
        },
        containedPrimary: {
          backgroundColor: '#00d4aa',
          '&:hover': {
            backgroundColor: '#00a67a',
          },
        },
        containedSecondary: {
          backgroundColor: '#ff6b35',
          '&:hover': {
            backgroundColor: '#e55a2b',
          },
        },
      },
    },
    MuiTableHead: {
      styleOverrides: {
        root: {
          backgroundColor: '#0f172a',
          '& .MuiTableCell-head': {
            fontWeight: 600,
            borderBottom: '2px solid #334155',
            color: '#f8fafc',
          },
        },
      },
    },
    MuiTableRow: {
      styleOverrides: {
        root: {
          '&:hover': {
            backgroundColor: 'rgba(255, 255, 255, 0.05)',
          },
          '&:nth-of-type(even)': {
            backgroundColor: 'rgba(255, 255, 255, 0.02)',
          },
        },
      },
    },
    MuiTableCell: {
      styleOverrides: {
        root: {
          borderBottom: '1px solid #334155',
        },
      },
    },
    MuiAlert: {
      styleOverrides: {
        root: {
          borderRadius: '8px',
        },
        standardSuccess: {
          backgroundColor: 'rgba(76, 175, 80, 0.1)',
          border: '1px solid #4caf50',
        },
        standardError: {
          backgroundColor: 'rgba(255, 68, 68, 0.1)',
          border: '1px solid #ff4444',
        },
        standardWarning: {
          backgroundColor: 'rgba(255, 152, 0, 0.1)',
          border: '1px solid #ff9800',
        },
        standardInfo: {
          backgroundColor: 'rgba(33, 150, 243, 0.1)',
          border: '1px solid #2196f3',
        },
      },
    },
  },
});

interface ThemeProviderProps {
  children: React.ReactNode;
}

export default function ThemeProvider({ children }: ThemeProviderProps) {
  return (
    <MuiThemeProvider theme={theme}>
      <CssBaseline />
      {children}
    </MuiThemeProvider>
  );
}
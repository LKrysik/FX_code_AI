'use client';

import React, { useState } from 'react';
import {
  AppBar,
  Toolbar,
  Typography,
  Drawer,
  List,
  ListItem,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Box,
  IconButton,
  useTheme,
  useMediaQuery,
  Chip,
  Tooltip,
} from '@mui/material';
import {
  Menu as MenuIcon,
  Dashboard as DashboardIcon,
  Build as BuildIcon,
  ShowChart as ChartIcon,
  Settings as SettingsIcon,
  PlayArrow as PlayIcon,
  Assessment as AssessmentIcon,
  Security as SecurityIcon,
  Storage as StorageIcon,
  TrendingUp as TrendingUpIcon,
  History as HistoryIcon,
} from '@mui/icons-material';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { UserMenu } from '@/components/auth';
import { useKeyboardShortcuts } from '@/hooks/useKeyboardShortcuts';
import { useWebSocketConnection } from '@/stores/websocketStore';
import { Alert, Button, Collapse } from '@mui/material';
import { Refresh as RefreshIcon } from '@mui/icons-material';
import dynamic from 'next/dynamic';

// Debug panel - only loaded in development mode
const DebugPanel = dynamic(
  () => import('@/components/debug/DebugPanel').then(mod => mod.DebugPanel),
  { ssr: false }
);

// Error display components (Story 0-5)
const ErrorToastStack = dynamic(
  () => import('@/components/errors').then(mod => mod.ErrorToastStack),
  { ssr: false }
);

const CriticalErrorModal = dynamic(
  () => import('@/components/errors').then(mod => mod.CriticalErrorModal),
  { ssr: false }
);

// Connection Status Indicator (Story 0-6)
const ConnectionStatusIndicator = dynamic(
  () => import('@/components/common/ConnectionStatusIndicator').then(mod => mod.ConnectionStatusIndicator),
  { ssr: false }
);

const drawerWidth = 280;

const menuItems = [
  {
    text: 'Dashboard',
    icon: <DashboardIcon />,
    path: '/',
    description: 'Trading dashboard and overview'
  },
  {
    text: 'Live Trading',
    icon: <PlayIcon />,
    path: '/trading',
    description: 'Real trading with live funds'
  },
  {
    text: 'Paper Trading',
    icon: <ChartIcon />,
    path: '/paper',
    description: 'Simulated trading with virtual funds'
  },
  {
    text: 'Backtesting',
    icon: <AssessmentIcon />,
    path: '/backtesting',
    description: 'Historical strategy testing'
  },
  {
    text: 'Session History',
    icon: <HistoryIcon />,
    path: '/session-history',
    description: 'Review past trading sessions and performance'
  },
  {
    text: 'Data Collection',
    icon: <StorageIcon />,
    path: '/data-collection',
    description: 'Market data collection and storage'
  },
  {
    text: 'Indicators',
    icon: <TrendingUpIcon />,
    path: '/indicators',
    description: 'Technical indicators management'
  },
  {
    text: 'Strategy Builder',
    icon: <BuildIcon />,
    path: '/strategy-builder',
    description: 'Visual strategy creation and editing'
  },
  {
    text: 'Risk Management',
    icon: <SecurityIcon />,
    path: '/risk-management',
    description: 'Risk monitoring and position management'
  },
  {
    text: 'Settings',
    icon: <SettingsIcon />,
    path: '/settings',
    description: 'Application configuration'
  },
];

interface LayoutProps {
  children: React.ReactNode;
}

export default function Layout({ children }: LayoutProps) {
  const [drawerOpen, setDrawerOpen] = useState(false);
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));
  const pathname = usePathname();

  // AC2: WebSocket connection status from store
  const { isConnected, connectionStatus } = useWebSocketConnection();

  // Reconnection countdown state
  const [reconnectCountdown, setReconnectCountdown] = useState<number | null>(null);

  // SY-01: Global keyboard shortcuts
  useKeyboardShortcuts();

  // AC2: Reconnection countdown timer
  React.useEffect(() => {
    if (connectionStatus === 'disconnected' && !isConnected) {
      setReconnectCountdown(5);
      const interval = setInterval(() => {
        setReconnectCountdown(prev => {
          if (prev === null || prev <= 1) {
            clearInterval(interval);
            return null;
          }
          return prev - 1;
        });
      }, 1000);
      return () => clearInterval(interval);
    } else {
      setReconnectCountdown(null);
    }
  }, [connectionStatus, isConnected]);

  // Manual reconnect handler
  const handleManualReconnect = () => {
    // Trigger reconnect via websocket service
    window.location.reload();
  };

  const handleDrawerToggle = () => {
    setDrawerOpen(!drawerOpen);
  };

  const drawer = (
    <Box sx={{ width: drawerWidth, height: '100%', display: 'flex', flexDirection: 'column' }}>
      <Box sx={{ px: 2, py: 2, borderBottom: `1px solid ${theme.palette.divider}` }}>
        <Typography variant="h6" component="div" sx={{ fontWeight: 'bold' }}>
          Crypto Trading Bot
        </Typography>
        <Typography variant="caption" color="text.secondary">
          Market Analysis System
        </Typography>
      </Box>

      <List sx={{ flex: 1, px: 1 }}>
        {menuItems.map((item) => {
          const isActive = pathname === item.path;
          return (
            <ListItem key={item.text} disablePadding>
              <Tooltip title={item.description} placement="right">
                <ListItemButton
                  component={Link}
                  href={item.path}
                  selected={isActive}
                  onClick={() => isMobile && setDrawerOpen(false)}
                  sx={{
                    mx: 1,
                    mb: 0.5,
                    borderRadius: 2,
                    '&.Mui-selected': {
                      backgroundColor: theme.palette.primary.main + '20',
                      '&:hover': {
                        backgroundColor: theme.palette.primary.main + '30',
                      },
                    },
                  }}
                >
                  <ListItemIcon sx={{
                    color: isActive ? theme.palette.primary.main : 'inherit',
                    minWidth: 40
                  }}>
                    {item.icon}
                  </ListItemIcon>
                  <ListItemText
                    primary={item.text}
                    primaryTypographyProps={{
                      fontSize: '0.95rem',
                      fontWeight: isActive ? 600 : 400,
                    }}
                  />
                  {isActive && (
                    <Chip
                      label="Active"
                      size="small"
                      color="primary"
                      variant="outlined"
                      sx={{ fontSize: '0.7rem', height: 20 }}
                    />
                  )}
                </ListItemButton>
              </Tooltip>
            </ListItem>
          );
        })}
      </List>

      <Box sx={{ px: 2, py: 2, borderTop: `1px solid ${theme.palette.divider}` }}>
        <Typography variant="caption" color="text.secondary">
          Version 1.0.0
        </Typography>
      </Box>
    </Box>
  );

  return (
    <Box sx={{ display: 'flex', minHeight: '100vh' }}>
      {/* App Bar */}
      <AppBar
        position="fixed"
        sx={{
          width: { md: `calc(100% - ${drawerWidth}px)` },
          ml: { md: `${drawerWidth}px` },
          zIndex: theme.zIndex.drawer + 1,
        }}
      >
        <Toolbar>
          <IconButton
            color="inherit"
            aria-label="open drawer"
            edge="start"
            onClick={handleDrawerToggle}
            sx={{ mr: 2, display: { md: 'none' } }}
          >
            <MenuIcon />
          </IconButton>

          <Typography variant="h6" noWrap component="div" sx={{ flexGrow: 1 }}>
            {menuItems.find(item => item.path === pathname)?.text || 'Market Analysis System'}
          </Typography>

          {/* Status indicators - Story 0-6: ConnectionStatusIndicator with popover */}
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <ConnectionStatusIndicator />
            <UserMenu />
          </Box>
        </Toolbar>
      </AppBar>

      {/* Navigation Drawer */}
      <Box
        component="nav"
        sx={{ width: { md: drawerWidth }, flexShrink: { md: 0 } }}
      >
        {/* Mobile drawer */}
        <Drawer
          variant="temporary"
          open={drawerOpen}
          onClose={handleDrawerToggle}
          ModalProps={{
            keepMounted: true, // Better open performance on mobile
          }}
          sx={{
            display: { xs: 'block', md: 'none' },
            '& .MuiDrawer-paper': {
              boxSizing: 'border-box',
              width: drawerWidth,
            },
          }}
        >
          {drawer}
        </Drawer>

        {/* Desktop drawer */}
        <Drawer
          variant="permanent"
          sx={{
            display: { xs: 'none', md: 'block' },
            '& .MuiDrawer-paper': {
              boxSizing: 'border-box',
              width: drawerWidth,
              position: 'fixed',
              height: '100vh',
            },
          }}
          open
        >
          {drawer}
        </Drawer>
      </Box>

      {/* Main Content */}
      <Box
        component="main"
        sx={{
          flexGrow: 1,
          width: { md: `calc(100% - ${drawerWidth}px)` },
          minHeight: '100vh',
          backgroundColor: theme.palette.background.default,
        }}
      >
        {/* Spacer for fixed AppBar */}
        <Toolbar />

        {/* AC2: WebSocket Disconnection Banner */}
        <Collapse in={!isConnected && connectionStatus !== 'connecting'}>
          <Alert
            severity="warning"
            sx={{ borderRadius: 0 }}
            action={
              <Button
                color="inherit"
                size="small"
                startIcon={<RefreshIcon />}
                onClick={handleManualReconnect}
              >
                Reconnect Now
              </Button>
            }
          >
            Connection lost. {reconnectCountdown !== null
              ? `Reconnecting in ${reconnectCountdown}s...`
              : 'Click to reconnect manually.'}
          </Alert>
        </Collapse>

        {/* Page Content */}
        <Box sx={{ p: 3 }}>
          {children}
        </Box>
      </Box>

      {/* Debug Panel - Development Only (AC5: Dev-only guard) */}
      {process.env.NODE_ENV === 'development' && <DebugPanel />}

      {/* Story 0-5: Error Display Components */}
      {/* AC1: Toast notifications for API errors */}
      <ErrorToastStack />

      {/* AC3: Critical error modal (full-screen blocking) */}
      <CriticalErrorModal />
    </Box>
  );
}
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
} from '@mui/icons-material';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { UserMenu } from '@/components/auth';

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
    description: 'Live and paper trading sessions'
  },
  {
    text: 'Backtesting',
    icon: <AssessmentIcon />,
    path: '/backtesting',
    description: 'Historical strategy testing'
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

          {/* Status indicators */}
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <Chip
              label="Backend: Connected"
              size="small"
              color="success"
              variant="outlined"
              sx={{ fontSize: '0.7rem' }}
            />
            <Chip
              label="WebSocket: Connected"
              size="small"
              color="success"
              variant="outlined"
              sx={{ fontSize: '0.7rem' }}
            />
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

        {/* Page Content */}
        <Box sx={{ p: 3 }}>
          {children}
        </Box>
      </Box>
    </Box>
  );
}
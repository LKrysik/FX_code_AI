'use client';

import React, { useState } from 'react';
import dynamic from 'next/dynamic';
import { Box, Typography, CircularProgress, Tabs, Tab, Paper, Button, Chip } from '@mui/material';
import { SystemStatusIndicator } from '@/components/common/SystemStatusIndicator';
import { Settings as SettingsIcon } from '@mui/icons-material';
import { useRouter } from 'next/navigation';

// Dynamically import workspace components with SSR disabled
const TradeWorkspace = dynamic(() => import('@/components/workspace/TradeWorkspace').then(mod => mod.TradeWorkspace), {
  ssr: false,
  loading: () => (
    <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '400px' }}>
      <Box sx={{ textAlign: 'center' }}>
        <CircularProgress size={40} sx={{ mb: 2 }} />
        <Typography variant="body1">
          Loading workspace...
        </Typography>
      </Box>
    </Box>
  )
});

// Legacy dashboard (keeping for backward compatibility during transition)
const PumpDumpDashboard = dynamic(() => import('./PumpDumpDashboard'), {
  ssr: false,
  loading: () => (
    <Box sx={{ flexGrow: 1, p: 3 }}>
      <Typography variant="h4" component="h1" gutterBottom>
        Trading Dashboard
      </Typography>
      <Box sx={{ display: 'flex', alignItems: 'center', mb: 3 }}>
        <CircularProgress size={20} sx={{ mr: 2 }} />
        <Typography variant="body1">
          Loading dashboard...
        </Typography>
      </Box>
    </Box>
  )
});

type WorkspaceMode = 'trade' | 'legacy';

export default function Page() {
  const router = useRouter();
  const [mode, setMode] = useState<WorkspaceMode>('trade'); // Default to new unified workspace

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', height: '100vh' }}>
      {/* HEADER: Workspace Selector + System Status */}
      <Paper
        sx={{
          borderBottom: 1,
          borderColor: 'divider',
          bgcolor: 'background.paper',
          px: 2,
          py: 1
        }}
        elevation={1}
      >
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
            <Typography variant="h5" fontWeight="bold" color="primary">
              FX Trading Bot
            </Typography>
            <Chip
              label="NEW WORKSPACE"
              color="success"
              size="small"
              sx={{ display: mode === 'trade' ? 'inline-flex' : 'none' }}
            />
          </Box>

          <Tabs value={mode} onChange={(_, v) => setMode(v)}>
            <Tab
              value="trade"
              label="UNIFIED WORKSPACE"
              sx={{ fontWeight: 'bold' }}
            />
            <Tab
              value="legacy"
              label="Legacy Dashboard"
              sx={{ fontSize: '0.875rem' }}
            />
          </Tabs>

          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
            <SystemStatusIndicator compact />
            <Button
              variant="outlined"
              size="small"
              startIcon={<SettingsIcon />}
              onClick={() => router.push('/settings')}
            >
              Settings
            </Button>
          </Box>
        </Box>
      </Paper>

      {/* WORKSPACE CONTENT */}
      <Box sx={{ flex: 1, overflow: 'hidden', bgcolor: 'background.default' }}>
        {mode === 'trade' ? (
          <TradeWorkspace />
        ) : (
          <PumpDumpDashboard />
        )}
      </Box>
    </Box>
  );
}
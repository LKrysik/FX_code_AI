'use client';

import React from 'react';
import dynamic from 'next/dynamic';
import { Box, Typography, CircularProgress } from '@mui/material';

// Dynamically import the dashboard component with SSR disabled to prevent hydration errors
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

// Re-export the component for Next.js routing
export default function Page() {
  return <PumpDumpDashboard />;
}
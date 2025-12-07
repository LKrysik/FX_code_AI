'use client';

import React, { useState } from 'react';
import {
  Box,
  Typography,
  Snackbar,
  Alert,
  Tabs,
  Tab,
  Paper,
} from '@mui/material';
import {
  Tune as VariantsIcon,
  Compare as CompareIcon,
} from '@mui/icons-material';
import { VariantManager } from '@/components/indicators/VariantManager';
import { VariantComparison } from '@/components/indicators/VariantComparison';


export default function IndicatorsPage() {
  const [activeTab, setActiveTab] = useState(0);
  const [snackbar, setSnackbar] = useState<{open: boolean, message: string, severity: 'success' | 'error' | 'info'}>({
    open: false,
    message: '',
    severity: 'info'
  });



  return (
    <Box>
      {/* Tabs */}
      <Paper sx={{ mb: 3 }}>
        <Tabs
          value={activeTab}
          onChange={(_, newValue) => setActiveTab(newValue)}
          sx={{ borderBottom: 1, borderColor: 'divider' }}
        >
          <Tab label="Variant Manager" icon={<VariantsIcon />} iconPosition="start" />
          <Tab label="Compare Variants" icon={<CompareIcon />} iconPosition="start" />
        </Tabs>
      </Paper>

      {/* Tab 0: Variant Manager */}
      {activeTab === 0 && (
        <VariantManager
        onVariantCreated={(variant) => {
          setSnackbar({
            open: true,
            message: `Variant "${variant.name}" created successfully`,
            severity: 'success'
          });
        }}
        onVariantUpdated={(variant) => {
          setSnackbar({
            open: true,
            message: `Variant "${variant.name}" updated successfully`,
            severity: 'success'
          });
        }}
        onVariantDeleted={(variantId) => {
          setSnackbar({
            open: true,
            message: 'Variant deleted successfully',
            severity: 'success'
          });
        }}
      />
      )}

      {/* Tab 1: Compare Variants */}
      {activeTab === 1 && (
        <VariantComparison />
      )}

      {/* Snackbar for notifications */}
      <Snackbar
        open={snackbar.open}
        autoHideDuration={4000}
        onClose={() => setSnackbar(prev => ({ ...prev, open: false }))}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
      >
        <Alert
          onClose={() => setSnackbar(prev => ({ ...prev, open: false }))}
          severity={snackbar.severity}
          variant="filled"
          sx={{ width: '100%' }}
        >
          {snackbar.message}
        </Alert>
      </Snackbar>
    </Box>
  );
}
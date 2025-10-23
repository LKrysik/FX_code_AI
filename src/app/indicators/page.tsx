'use client';

import React, { useState } from 'react';
import {
  Box,
  Typography,
  Snackbar,
  Alert,
} from '@mui/material';
import { VariantManager } from '@/components/indicators/VariantManager';


export default function IndicatorsPage() {
  const [activeTab, setActiveTab] = useState<'variants'>('variants');
  const [snackbar, setSnackbar] = useState<{open: boolean, message: string, severity: 'success' | 'error' | 'info'}>({
    open: false,
    message: '',
    severity: 'info'
  });



  return (
    <Box>
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
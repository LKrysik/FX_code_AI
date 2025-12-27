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
  ShowChart as ChartIcon,
  Analytics as AnalyticsIcon,
} from '@mui/icons-material';
import { VariantManager } from '@/components/indicators/VariantManager';
import { VariantComparison } from '@/components/indicators/VariantComparison';
import { VariantChartPreview } from '@/components/indicators/VariantChartPreview';
import { SignalCountTest } from '@/components/indicators/SignalCountTest';
import { IndicatorVariant } from '@/types/strategy';
import { Logger } from '@/services/frontendLogService';


export default function IndicatorsPage() {
  const [activeTab, setActiveTab] = useState(0);
  const [selectedVariant, setSelectedVariant] = useState<IndicatorVariant | null>(null);
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
          <Tab label="Preview on Chart" icon={<ChartIcon />} iconPosition="start" />
          <Tab label="Signal Count Test" icon={<AnalyticsIcon />} iconPosition="start" />
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

      {/* Tab 2: Preview on Chart (IV-01) */}
      {activeTab === 2 && (
        <VariantChartPreview
          variant={selectedVariant}
          onPumpDetected={(pump) => {
            Logger.info('IndicatorsPage.onPumpDetected', { message: 'Pump detected', pump });
          }}
        />
      )}

      {/* Tab 3: Signal Count Test (IV-04) */}
      {activeTab === 3 && (
        <SignalCountTest
          variant={selectedVariant}
          onVariantSelect={(v) => setSelectedVariant(v)}
        />
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
'use client';

import React, { useState } from 'react';
import {
  Alert,
  AlertTitle,
  Box,
  Button,
  Collapse,
  IconButton,
  Typography,
  Chip,
} from '@mui/material';
import {
  CloudOff as CloudOffIcon,
  Refresh as RefreshIcon,
  Warning as WarningIcon,
  Info as InfoIcon,
  Close as CloseIcon,
  ExpandMore as ExpandMoreIcon,
  ExpandLess as ExpandLessIcon,
} from '@mui/icons-material';
import { shouldUseMockData, isDebugMode } from '@/utils/config';

interface DataModeAlertProps {
  showDetails?: boolean;
  onDismiss?: () => void;
  persistent?: boolean;
}

export function DataModeAlert({ showDetails = false, onDismiss, persistent = false }: DataModeAlertProps) {
  const [expanded, setExpanded] = useState(false);
  const [dismissed, setDismissed] = useState(false);

  const isUsingMockData = shouldUseMockData();
  const debugMode = isDebugMode();

  // Don't show if not using mock data and not in debug mode
  if (!isUsingMockData && !debugMode) {
    return null;
  }

  // Don't show if dismissed and not persistent
  if (dismissed && !persistent) {
    return null;
  }

  const handleDismiss = () => {
    setDismissed(true);
    onDismiss?.();
  };

  const getSeverity = () => {
    if (debugMode) return 'info';
    return 'warning';
  };

  const getTitle = () => {
    if (debugMode) return 'Debug Mode Active';
    return 'Demo Data Mode';
  };

  const getMessage = () => {
    if (debugMode) {
      return 'Application is running in debug mode with additional logging and mock data.';
    }
    return 'Currently displaying demo data. Connect to a live backend for real trading data.';
  };

  return (
    <Collapse in={!dismissed || persistent}>
      <Alert
        severity={getSeverity()}
        sx={{ mb: 2 }}
        action={
          <Box sx={{ display: 'flex', gap: 1, alignItems: 'center' }}>
            {showDetails && (
              <IconButton
                size="small"
                onClick={() => setExpanded(!expanded)}
                sx={{ color: 'inherit' }}
              >
                {expanded ? <ExpandLessIcon /> : <ExpandMoreIcon />}
              </IconButton>
            )}
            {!persistent && (
              <IconButton
                size="small"
                onClick={handleDismiss}
                sx={{ color: 'inherit' }}
              >
                <CloseIcon />
              </IconButton>
            )}
          </Box>
        }
      >
        <AlertTitle sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          {debugMode ? <InfoIcon fontSize="small" /> : <WarningIcon fontSize="small" />}
          {getTitle()}
        </AlertTitle>

        <Typography variant="body2" sx={{ mb: 1 }}>
          {getMessage()}
        </Typography>

        <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
          <Chip
            size="small"
            label={debugMode ? 'Debug Mode' : 'Demo Data'}
            color={debugMode ? 'info' : 'warning'}
            variant="outlined"
          />

          {isUsingMockData && !debugMode && (
            <Chip
              size="small"
              label="Mock Data"
              color="warning"
              variant="filled"
            />
          )}

          {debugMode && (
            <Chip
              size="small"
              label="Extra Logging"
              color="info"
              variant="outlined"
            />
          )}
        </Box>

        <Collapse in={expanded}>
          <Box sx={{ mt: 2 }}>
            <Typography variant="body2" sx={{ mb: 1, fontWeight: 'bold' }}>
              What this means:
            </Typography>

            <Box component="ul" sx={{ pl: 2, m: 0 }}>
              {debugMode ? (
                <>
                  <li>
                    <Typography variant="body2">
                      Enhanced logging is enabled for debugging purposes
                    </Typography>
                  </li>
                  <li>
                    <Typography variant="body2">
                      Mock data is being used for testing scenarios
                    </Typography>
                  </li>
                  <li>
                    <Typography variant="body2">
                      Some features may behave differently than in production
                    </Typography>
                  </li>
                </>
              ) : (
                <>
                  <li>
                    <Typography variant="body2">
                      All displayed data is simulated for demonstration
                    </Typography>
                  </li>
                  <li>
                    <Typography variant="body2">
                      Trading actions will not affect real accounts
                    </Typography>
                  </li>
                  <li>
                    <Typography variant="body2">
                      Connect to a live backend to access real market data
                    </Typography>
                  </li>
                </>
              )}
            </Box>

            <Box sx={{ mt: 2 }}>
              <Typography variant="body2" sx={{ mb: 1, fontWeight: 'bold' }}>
                To switch modes:
              </Typography>

              <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                <Button
                  size="small"
                  variant="outlined"
                  startIcon={<RefreshIcon />}
                  onClick={() => window.location.reload()}
                >
                  Reload Page
                </Button>

                <Typography variant="caption" color="text.secondary">
                  Or update NEXT_PUBLIC_ENABLE_MOCK_DATA in your environment
                </Typography>
              </Box>
            </Box>
          </Box>
        </Collapse>
      </Alert>
    </Collapse>
  );
}
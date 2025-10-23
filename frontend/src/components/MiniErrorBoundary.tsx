'use client';

import React, { Component, ErrorInfo, ReactNode } from 'react';
import {
  Box,
  Alert,
  AlertTitle,
  Button,
  Collapse,
  IconButton,
} from '@mui/material';
import {
  Error as ErrorIcon,
  Refresh as RefreshIcon,
  ExpandMore as ExpandMoreIcon,
  ExpandLess as ExpandLessIcon,
} from '@mui/icons-material';
import { errorLog } from '@/utils/config';

interface Props {
  children: ReactNode;
  title?: string;
  showDetails?: boolean;
  onRetry?: () => void;
}

interface State {
  hasError: boolean;
  error: Error | null;
  errorInfo: ErrorInfo | null;
  showDetails: boolean;
}

class MiniErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null,
      showDetails: props.showDetails || false,
    };
  }

  static getDerivedStateFromError(error: Error): State {
    return {
      hasError: true,
      error,
      errorInfo: null,
      showDetails: false,
    };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    this.setState({
      error,
      errorInfo,
    });

    errorLog('MiniErrorBoundary caught an error', { error, errorInfo });
  }

  handleRetry = () => {
    this.setState({
      hasError: false,
      error: null,
      errorInfo: null,
    });

    if (this.props.onRetry) {
      this.props.onRetry();
    }
  };

  toggleDetails = () => {
    this.setState(prev => ({ showDetails: !prev.showDetails }));
  };

  render() {
    if (this.state.hasError) {
      return (
        <Alert
          severity="error"
          sx={{ mb: 2 }}
          action={
            <Box sx={{ display: 'flex', gap: 1 }}>
              <IconButton
                size="small"
                onClick={this.toggleDetails}
                sx={{ color: 'inherit' }}
              >
                {this.state.showDetails ? <ExpandLessIcon /> : <ExpandMoreIcon />}
              </IconButton>
              <IconButton
                size="small"
                onClick={this.handleRetry}
                sx={{ color: 'inherit' }}
              >
                <RefreshIcon />
              </IconButton>
            </Box>
          }
        >
          <AlertTitle sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <ErrorIcon fontSize="small" />
            {this.props.title || 'Component Error'}
          </AlertTitle>

          <Box sx={{ mt: 1 }}>
            <strong>Error:</strong> {this.state.error?.message}
          </Box>

          <Collapse in={this.state.showDetails}>
            <Box sx={{ mt: 2 }}>
              <Box component="pre" sx={{ fontSize: '0.75rem', fontFamily: 'monospace', bgcolor: 'grey.100', p: 1, borderRadius: 1, overflow: 'auto' }}>
                {this.state.error?.stack}
              </Box>

              {this.state.errorInfo && (
                <Box sx={{ mt: 1 }}>
                  <strong>Component Stack:</strong>
                  <Box component="pre" sx={{ fontSize: '0.75rem', fontFamily: 'monospace', bgcolor: 'grey.100', p: 1, borderRadius: 1, overflow: 'auto', maxHeight: 100 }}>
                    {this.state.errorInfo.componentStack}
                  </Box>
                </Box>
              )}
            </Box>
          </Collapse>
        </Alert>
      );
    }

    return this.props.children;
  }
}

export default MiniErrorBoundary;
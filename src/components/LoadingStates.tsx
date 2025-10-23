import React from 'react';
import {
  Box,
  CircularProgress,
  LinearProgress,
  Typography,
  Skeleton,
  Alert,
  Chip,
  Fade,
} from '@mui/material';
import {
  Refresh as RefreshIcon,
  Wifi as WifiIcon,
  WifiOff as WifiOffIcon,
  AccessTime as TimeIcon,
} from '@mui/icons-material';

interface LoadingSpinnerProps {
  size?: number;
  message?: string;
  overlay?: boolean;
}

export function LoadingSpinner({ size = 40, message, overlay = false }: LoadingSpinnerProps) {
  const content = (
    <Box
      sx={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        gap: 2,
        p: 2,
      }}
    >
      <CircularProgress size={size} />
      {message && (
        <Typography variant="body2" color="text.secondary">
          {message}
        </Typography>
      )}
    </Box>
  );

  if (overlay) {
    return (
      <Fade in>
        <Box
          sx={{
            position: 'absolute',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            bgcolor: 'rgba(255, 255, 255, 0.8)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 1000,
          }}
        >
          {content}
        </Box>
      </Fade>
    );
  }

  return content;
}

interface DataStatusIndicatorProps {
  isLoading: boolean;
  isStale: boolean;
  lastUpdated: number | null;
  error: Error | null;
  onRetry?: () => void;
  dataSource?: 'live' | 'cached' | 'mock';
}

export function DataStatusIndicator({
  isLoading,
  isStale,
  lastUpdated,
  error,
  onRetry,
  dataSource = 'live'
}: DataStatusIndicatorProps) {
  const getStatusColor = () => {
    if (error) return 'error';
    if (isLoading) return 'info';
    if (isStale) return 'warning';
    return 'success';
  };

  const getStatusIcon = () => {
    if (error) return <WifiOffIcon fontSize="small" />;
    if (isLoading) return <RefreshIcon fontSize="small" />;
    return <WifiIcon fontSize="small" />;
  };

  const getStatusText = () => {
    if (error) return 'Error';
    if (isLoading) return 'Loading...';
    if (isStale) return 'Stale';
    return 'Live';
  };

  const getDataSourceText = () => {
    switch (dataSource) {
      case 'live': return 'Live Data';
      case 'cached': return 'Cached';
      case 'mock': return 'Demo Data';
      default: return 'Unknown';
    }
  };

  const formatLastUpdated = () => {
    if (!lastUpdated) return 'Never';
    const now = Date.now();
    const diff = now - lastUpdated;
    const minutes = Math.floor(diff / 60000);
    const seconds = Math.floor((diff % 60000) / 1000);

    if (minutes > 0) {
      return `${minutes}m ${seconds}s ago`;
    }
    return `${seconds}s ago`;
  };

  return (
    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
      <Chip
        size="small"
        color={getStatusColor()}
        icon={getStatusIcon()}
        label={getStatusText()}
        variant={isStale ? 'outlined' : 'filled'}
      />

      <Chip
        size="small"
        label={getDataSourceText()}
        variant="outlined"
        sx={{
          bgcolor: dataSource === 'mock' ? 'warning.light' : 'transparent',
          color: dataSource === 'mock' ? 'warning.contrastText' : 'text.secondary',
        }}
      />

      {lastUpdated && (
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
          <TimeIcon fontSize="small" color="action" />
          <Typography variant="caption" color="text.secondary">
            {formatLastUpdated()}
          </Typography>
        </Box>
      )}

      {error && onRetry && (
        <Chip
          size="small"
          label="Retry"
          onClick={onRetry}
          sx={{ cursor: 'pointer' }}
        />
      )}
    </Box>
  );
}

interface SkeletonLoaderProps {
  variant?: 'text' | 'rectangular' | 'circular';
  width?: number | string;
  height?: number | string;
  count?: number;
}

export function SkeletonLoader({
  variant = 'rectangular',
  width = '100%',
  height = 40,
  count = 1
}: SkeletonLoaderProps) {
  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
      {Array.from({ length: count }, (_, i) => (
        <Skeleton
          key={i}
          variant={variant}
          width={width}
          height={height}
          animation="wave"
        />
      ))}
    </Box>
  );
}

interface TableSkeletonProps {
  rows?: number;
  columns?: number;
}

export function TableSkeleton({ rows = 5, columns = 4 }: TableSkeletonProps) {
  return (
    <Box>
      {/* Header */}
      <Box sx={{ display: 'flex', gap: 2, mb: 2 }}>
        {Array.from({ length: columns }, (_, i) => (
          <Skeleton key={i} variant="rectangular" width={120} height={24} />
        ))}
      </Box>

      {/* Rows */}
      {Array.from({ length: rows }, (_, rowIndex) => (
        <Box key={rowIndex} sx={{ display: 'flex', gap: 2, mb: 1 }}>
          {Array.from({ length: columns }, (_, colIndex) => (
            <Skeleton
              key={colIndex}
              variant="rectangular"
              width={colIndex === 0 ? 200 : 120}
              height={40}
            />
          ))}
        </Box>
      ))}
    </Box>
  );
}

interface ProgressBarProps {
  value?: number;
  label?: string;
  color?: 'primary' | 'secondary' | 'error' | 'info' | 'success' | 'warning';
}

export function ProgressBar({ value, label, color = 'primary' }: ProgressBarProps) {
  return (
    <Box sx={{ width: '100%', mb: 2 }}>
      {label && (
        <Typography variant="body2" sx={{ mb: 1 }}>
          {label}
        </Typography>
      )}
      <LinearProgress
        variant={value !== undefined ? 'determinate' : 'indeterminate'}
        value={value}
        color={color}
        sx={{ height: 8, borderRadius: 4 }}
      />
    </Box>
  );
}

interface ErrorAlertProps {
  error: Error;
  onRetry?: () => void;
  title?: string;
}

export function ErrorAlert({ error, onRetry, title = 'Error loading data' }: ErrorAlertProps) {
  return (
    <Alert
      severity="error"
      action={
        onRetry && (
          <Chip
            size="small"
            label="Retry"
            onClick={onRetry}
            sx={{ cursor: 'pointer' }}
          />
        )
      }
      sx={{ mb: 2 }}
    >
      <Typography variant="body2" sx={{ fontWeight: 'bold' }}>
        {title}
      </Typography>
      <Typography variant="body2">
        {error.message}
      </Typography>
    </Alert>
  );
}
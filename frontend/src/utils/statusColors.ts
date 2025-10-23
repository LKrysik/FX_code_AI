import { Theme } from '@mui/material/styles';

// Status color utilities for consistent theming
export const getStatusColor = (status: string, theme: Theme) => {
  switch (status.toLowerCase()) {
    case 'success':
    case 'completed':
    case 'active':
    case 'running':
    case 'connected':
      return theme.palette.success.main;
    case 'error':
    case 'failed':
    case 'disconnected':
    case 'unhealthy':
      return theme.palette.error.main;
    case 'warning':
    case 'degraded':
    case 'stale':
    case 'pending':
      return theme.palette.warning.main;
    case 'info':
    case 'loading':
    case 'connecting':
      return theme.palette.info.main;
    default:
      return theme.palette.text.secondary;
  }
};

export const getTradingSignalColor = (signalType: string, theme: Theme) => {
  switch (signalType.toLowerCase()) {
    case 'pump':
    case 'bullish':
      return theme.palette.pump?.main || theme.palette.success.main;
    case 'dump':
    case 'bearish':
      return theme.palette.dump?.main || theme.palette.error.main;
    case 'neutral':
    case 'sideways':
      return theme.palette.info.main;
    default:
      return theme.palette.text.secondary;
  }
};

export const getRiskLevelColor = (riskLevel: string, theme: Theme) => {
  switch (riskLevel.toLowerCase()) {
    case 'low':
      return theme.palette.success.main;
    case 'medium':
      return theme.palette.warning.main;
    case 'high':
      return theme.palette.error.main;
    default:
      return theme.palette.text.secondary;
  }
};

export const getDifficultyColor = (difficulty: string, theme: Theme) => {
  switch (difficulty.toLowerCase()) {
    case 'beginner':
      return theme.palette.success.main;
    case 'intermediate':
      return theme.palette.warning.main;
    case 'advanced':
      return theme.palette.error.main;
    default:
      return theme.palette.text.secondary;
  }
};

// Price change color utilities
export const getPriceChangeColor = (change: number, theme: Theme) => {
  if (change > 0) {
    return theme.palette.bullish?.main || theme.palette.success.main;
  } else if (change < 0) {
    return theme.palette.bearish?.main || theme.palette.error.main;
  }
  return theme.palette.text.secondary;
};

// Performance indicator colors
export const getPerformanceColor = (value: number, theme: Theme) => {
  if (value > 0) {
    return theme.palette.success.main;
  } else if (value < 0) {
    return theme.palette.error.main;
  }
  return theme.palette.text.secondary;
};

// Connection status colors
export const getConnectionStatusColor = (status: string, theme: Theme) => {
  switch (status.toLowerCase()) {
    case 'connected':
    case 'online':
      return theme.palette.success.main;
    case 'connecting':
    case 'reconnecting':
      return theme.palette.warning.main;
    case 'disconnected':
    case 'offline':
    case 'error':
      return theme.palette.error.main;
    default:
      return theme.palette.text.secondary;
  }
};
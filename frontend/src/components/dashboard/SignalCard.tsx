/**
 * SignalCard Component
 * ====================
 * Story 1A-1: Prominent display of individual trading signals
 *
 * AC2: Signal display includes: type, symbol, timestamp, and key indicator value
 * AC5: Signal display uses prominent styling (not buried in UI)
 */

'use client';

import React from 'react';
import {
  Card,
  CardContent,
  Box,
  Typography,
  Chip,
  LinearProgress,
} from '@mui/material';
import {
  TrendingUp as PumpIcon,
  TrendingDown as DumpIcon,
} from '@mui/icons-material';

export interface SignalCardProps {
  id: string;
  symbol: string;
  signalType: 'pump' | 'dump';
  magnitude: number;
  confidence: number;
  timestamp: string;
  strategy?: string;
  onClick?: () => void;
}

/**
 * Get signal type styling based on pump/dump
 */
const getSignalTypeConfig = (signalType: 'pump' | 'dump') => {
  if (signalType === 'pump') {
    return {
      icon: PumpIcon,
      color: '#10B981', // Green
      bgColor: 'rgba(16, 185, 129, 0.1)',
      borderColor: 'rgba(16, 185, 129, 0.3)',
      label: 'PUMP',
    };
  }
  return {
    icon: DumpIcon,
    color: '#EF4444', // Red
    bgColor: 'rgba(239, 68, 68, 0.1)',
    borderColor: 'rgba(239, 68, 68, 0.3)',
    label: 'DUMP',
  };
};

/**
 * Format timestamp to human-readable format
 */
const formatTimestamp = (timestamp: string): string => {
  try {
    const date = new Date(timestamp);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffSecs = Math.floor(diffMs / 1000);

    if (diffSecs < 60) return `${diffSecs}s ago`;
    if (diffSecs < 3600) return `${Math.floor(diffSecs / 60)}m ago`;
    if (diffSecs < 86400) return `${Math.floor(diffSecs / 3600)}h ago`;

    return date.toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit',
    });
  } catch {
    return timestamp;
  }
};

/**
 * SignalCard - Prominent display for a single trading signal
 */
export const SignalCard: React.FC<SignalCardProps> = ({
  id,
  symbol,
  signalType,
  magnitude,
  confidence,
  timestamp,
  strategy,
  onClick,
}) => {
  const config = getSignalTypeConfig(signalType);
  const IconComponent = config.icon;

  return (
    <Card
      onClick={onClick}
      sx={{
        mb: 1.5,
        cursor: onClick ? 'pointer' : 'default',
        border: `2px solid ${config.borderColor}`,
        backgroundColor: config.bgColor,
        transition: 'all 0.2s ease-in-out',
        '&:hover': onClick ? {
          transform: 'translateY(-2px)',
          boxShadow: `0 4px 12px ${config.borderColor}`,
        } : {},
      }}
    >
      <CardContent sx={{ p: 2, '&:last-child': { pb: 2 } }}>
        {/* Header: Signal Type + Symbol */}
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 1 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <IconComponent sx={{ color: config.color, fontSize: 28 }} />
            <Box>
              <Typography
                variant="h6"
                sx={{
                  fontWeight: 700,
                  color: config.color,
                  lineHeight: 1,
                }}
              >
                {symbol}
              </Typography>
              <Chip
                label={config.label}
                size="small"
                sx={{
                  mt: 0.5,
                  height: 20,
                  fontSize: '0.7rem',
                  fontWeight: 600,
                  backgroundColor: config.color,
                  color: 'white',
                }}
              />
            </Box>
          </Box>

          {/* Timestamp */}
          <Typography
            variant="caption"
            sx={{
              color: 'text.secondary',
              fontSize: '0.75rem',
            }}
          >
            {formatTimestamp(timestamp)}
          </Typography>
        </Box>

        {/* Magnitude Display */}
        <Box sx={{ mb: 1.5 }}>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 0.5 }}>
            <Typography variant="body2" color="text.secondary">
              Magnitude
            </Typography>
            <Typography
              variant="h5"
              sx={{
                fontWeight: 700,
                color: config.color,
              }}
            >
              {magnitude >= 0 ? '+' : ''}{magnitude.toFixed(2)}%
            </Typography>
          </Box>
        </Box>

        {/* Confidence Bar */}
        <Box>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.5 }}>
            <Typography variant="caption" color="text.secondary">
              Confidence
            </Typography>
            <Typography
              variant="caption"
              sx={{
                fontWeight: 600,
                color: confidence >= 70 ? 'success.main' : confidence >= 40 ? 'warning.main' : 'error.main',
              }}
            >
              {confidence.toFixed(0)}%
            </Typography>
          </Box>
          <LinearProgress
            variant="determinate"
            value={confidence}
            sx={{
              height: 6,
              borderRadius: 3,
              backgroundColor: 'rgba(0,0,0,0.1)',
              '& .MuiLinearProgress-bar': {
                backgroundColor: confidence >= 70 ? '#10B981' : confidence >= 40 ? '#F59E0B' : '#EF4444',
                borderRadius: 3,
              },
            }}
          />
        </Box>

        {/* Strategy (if provided) */}
        {strategy && (
          <Typography
            variant="caption"
            sx={{
              display: 'block',
              mt: 1,
              color: 'text.secondary',
              fontSize: '0.7rem',
            }}
          >
            Strategy: {strategy}
          </Typography>
        )}
      </CardContent>
    </Card>
  );
};

export default SignalCard;

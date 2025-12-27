/**
 * SignalCard Component
 * ====================
 * Story 1A-1: Prominent display of individual trading signals
 * Story 1A-4: Human Vocabulary Labels (AC2 - centralized vocabulary)
 * Story 1A-6: Signal Type Color Coding (AC1-5)
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
  useTheme,
} from '@mui/material';
import {
  TrendingUp as PumpIcon,
  TrendingDown as DumpIcon,
} from '@mui/icons-material';

// Import centralized vocabulary (Story 1A-4: Human Vocabulary Labels - AC2)
import { getSignalVocabulary, SignalType } from '@/utils/stateVocabulary';
// Import color system (Story 1A-6: Signal Type Color Coding)
import { getSignalColorPalette, getSignalColorConfig } from '@/theme/signalColors';

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
 * Uses centralized vocabulary for labels (Story 1A-4 AC2)
 * Uses color system for light/dark mode (Story 1A-6)
 */
const getSignalTypeConfig = (signalType: 'pump' | 'dump', isDarkMode: boolean) => {
  // Get human-readable label from centralized vocabulary
  const vocabulary = getSignalVocabulary(signalType);
  // Get color palette for current mode (Story 1A-6: AC5 - light/dark mode)
  const colorConfig = getSignalColorConfig(signalType);
  const colors = getSignalColorPalette(signalType, isDarkMode ? 'dark' : 'light');

  return {
    icon: signalType === 'pump' ? PumpIcon : DumpIcon,
    color: colors.icon,
    bgColor: colors.bg,
    borderColor: colors.border,
    textColor: colors.text,
    label: vocabulary.label,
    emoji: colorConfig.icon, // AC4: Color-blind friendly icon
    primaryColor: colorConfig.primary,
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
 * Story 1A-6: Uses theme-aware colors for light/dark mode support
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
  const theme = useTheme();
  const isDarkMode = theme.palette.mode === 'dark';
  const config = getSignalTypeConfig(signalType, isDarkMode);
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
                label={`${config.emoji} ${config.label}`}
                size="small"
                sx={{
                  mt: 0.5,
                  height: 22,
                  fontSize: '0.7rem',
                  fontWeight: 600,
                  backgroundColor: config.primaryColor,
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

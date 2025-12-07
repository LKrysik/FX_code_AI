'use client';

/**
 * IndicatorParameterDocs Component (IV-03, SB-04)
 * ===============================================
 *
 * Provides documentation and explanations for indicator parameters.
 * Used in:
 * - SB-04: Variant tooltips ("PumpFast" = t1=5s, t3=30s, d=15s)
 * - IV-03: Parameter docs (What does t1, t3, d do? What's the effect of change?)
 *
 * Features:
 * - Parameter definitions with descriptions
 * - Effects of parameter changes
 * - Recommended values for different use cases
 * - Predefined variant explanations (PumpFast, PumpMedium, PumpSlow)
 *
 * Related: docs/UI_BACKLOG.md - IV-03, SB-04
 */

import React from 'react';
import {
  Box,
  Paper,
  Typography,
  Tooltip,
  Chip,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  Divider,
  alpha,
} from '@mui/material';
import {
  Info as InfoIcon,
  Speed as SpeedIcon,
  Timer as TimerIcon,
  TrendingUp as TrendingUpIcon,
  Warning as WarningIcon,
} from '@mui/icons-material';

// ============================================================================
// Types
// ============================================================================

export interface ParameterDoc {
  name: string;
  shortName: string;
  unit: string;
  description: string;
  effect: string;
  increaseEffect: string;
  decreaseEffect: string;
  recommended: {
    fast: number;
    medium: number;
    slow: number;
  };
  warningThresholds?: {
    min?: number;
    max?: number;
    warning: string;
  };
}

export interface VariantPreset {
  name: string;
  description: string;
  parameters: Record<string, number>;
  useCase: string;
  color: string;
}

// ============================================================================
// Parameter Documentation Database
// ============================================================================

export const PARAMETER_DOCS: Record<string, ParameterDoc> = {
  // Time window parameters
  t1: {
    name: 'Time Window 1 (t1)',
    shortName: 't1',
    unit: 'seconds',
    description: 'Short-term lookback period for immediate price movement detection.',
    effect: 'Determines how far back to look when calculating immediate price changes.',
    increaseEffect: 'More smoothing, slower signal detection, fewer false positives',
    decreaseEffect: 'Faster signal detection, more noise, more false positives',
    recommended: {
      fast: 5,
      medium: 15,
      slow: 30,
    },
    warningThresholds: {
      min: 1,
      max: 60,
      warning: 't1 < 3s may cause excessive noise; t1 > 30s may miss fast pumps',
    },
  },
  t2: {
    name: 'Time Window 2 (t2)',
    shortName: 't2',
    unit: 'seconds',
    description: 'Medium-term lookback period for trend confirmation.',
    effect: 'Used to confirm the direction of the overall trend.',
    increaseEffect: 'More stable trend detection, slower to react to reversals',
    decreaseEffect: 'Faster trend detection, more sensitive to reversals',
    recommended: {
      fast: 15,
      medium: 30,
      slow: 60,
    },
  },
  t3: {
    name: 'Time Window 3 (t3)',
    shortName: 't3',
    unit: 'seconds',
    description: 'Long-term lookback period for baseline comparison.',
    effect: 'Provides the reference baseline for calculating magnitude of movement.',
    increaseEffect: 'Larger baseline = smaller relative movements = fewer signals',
    decreaseEffect: 'Smaller baseline = larger relative movements = more signals',
    recommended: {
      fast: 30,
      medium: 60,
      slow: 120,
    },
    warningThresholds: {
      min: 10,
      max: 300,
      warning: 't3 should be 2-4x larger than t1 for optimal detection',
    },
  },
  d: {
    name: 'Delay/Smoothing (d)',
    shortName: 'd',
    unit: 'seconds',
    description: 'Delay or smoothing factor applied to calculations.',
    effect: 'Reduces noise by averaging values over this period.',
    increaseEffect: 'Smoother output, delayed signals, fewer false positives',
    decreaseEffect: 'Faster response, more noise, earlier signals',
    recommended: {
      fast: 5,
      medium: 15,
      slow: 30,
    },
  },
  window: {
    name: 'Window Size',
    shortName: 'window',
    unit: 'seconds',
    description: 'General lookback window for indicator calculation.',
    effect: 'Defines the period over which the indicator aggregates data.',
    increaseEffect: 'More data points, smoother values, slower reaction',
    decreaseEffect: 'Fewer data points, more volatile values, faster reaction',
    recommended: {
      fast: 10,
      medium: 30,
      slow: 60,
    },
  },
  threshold: {
    name: 'Threshold',
    shortName: 'threshold',
    unit: '%',
    description: 'Minimum percentage change to trigger a signal.',
    effect: 'Filters out small movements, only significant moves pass.',
    increaseEffect: 'Fewer signals, only major movements detected',
    decreaseEffect: 'More signals, minor movements also detected',
    recommended: {
      fast: 2,
      medium: 5,
      slow: 10,
    },
    warningThresholds: {
      min: 0.5,
      max: 20,
      warning: 'threshold < 1% will generate many false signals',
    },
  },
  decay: {
    name: 'Decay Rate',
    shortName: 'decay',
    unit: 'factor',
    description: 'How quickly the indicator value decays over time.',
    effect: 'Controls how long signals persist after initial detection.',
    increaseEffect: 'Faster decay = signals fade quickly',
    decreaseEffect: 'Slower decay = signals persist longer',
    recommended: {
      fast: 0.95,
      medium: 0.9,
      slow: 0.8,
    },
  },
};

// ============================================================================
// Predefined Variant Presets (SB-04)
// ============================================================================

export const VARIANT_PRESETS: Record<string, VariantPreset> = {
  PumpFast: {
    name: 'PumpFast',
    description: 'Aggressive detection for rapid pumps (memecoins, low-cap)',
    parameters: {
      t1: 5,
      t3: 30,
      d: 5,
      threshold: 3,
    },
    useCase: 'Ideal for: Memecoins, micro-cap tokens with explosive movements',
    color: '#f44336', // red
  },
  PumpMedium: {
    name: 'PumpMedium',
    description: 'Balanced detection for typical pump/dump events',
    parameters: {
      t1: 15,
      t3: 60,
      d: 15,
      threshold: 5,
    },
    useCase: 'Ideal for: Mid-cap altcoins, typical crypto volatility',
    color: '#ff9800', // orange
  },
  PumpSlow: {
    name: 'PumpSlow',
    description: 'Conservative detection for larger, slower pumps',
    parameters: {
      t1: 30,
      t3: 120,
      d: 30,
      threshold: 10,
    },
    useCase: 'Ideal for: Large-cap coins (BTC, ETH), sustained movements',
    color: '#4caf50', // green
  },
  VelocityFast: {
    name: 'VelocityFast',
    description: 'Rapid velocity detection for momentum trading',
    parameters: {
      window: 10,
      decay: 0.95,
    },
    useCase: 'Ideal for: Scalping, short-term momentum plays',
    color: '#2196f3', // blue
  },
  VelocityMedium: {
    name: 'VelocityMedium',
    description: 'Balanced velocity for swing trading',
    parameters: {
      window: 30,
      decay: 0.9,
    },
    useCase: 'Ideal for: Swing trades, trend following',
    color: '#9c27b0', // purple
  },
};

// ============================================================================
// Helper Functions
// ============================================================================

export function getParameterDoc(paramName: string): ParameterDoc | undefined {
  return PARAMETER_DOCS[paramName.toLowerCase()];
}

export function getVariantPreset(variantName: string): VariantPreset | undefined {
  // Try exact match first
  if (VARIANT_PRESETS[variantName]) {
    return VARIANT_PRESETS[variantName];
  }
  // Try case-insensitive match
  const key = Object.keys(VARIANT_PRESETS).find(
    (k) => k.toLowerCase() === variantName.toLowerCase()
  );
  return key ? VARIANT_PRESETS[key] : undefined;
}

export function formatParameterValue(param: string, value: number): string {
  const doc = getParameterDoc(param);
  if (!doc) return `${value}`;
  return `${value}${doc.unit === 'seconds' ? 's' : doc.unit === '%' ? '%' : ''}`;
}

// ============================================================================
// Components
// ============================================================================

/**
 * Tooltip content for a single parameter
 */
interface ParameterTooltipContentProps {
  param: string;
  value?: number;
}

export const ParameterTooltipContent: React.FC<ParameterTooltipContentProps> = ({
  param,
  value,
}) => {
  const doc = getParameterDoc(param);
  if (!doc) {
    return (
      <Typography variant="body2">
        Unknown parameter: {param}
      </Typography>
    );
  }

  return (
    <Box sx={{ p: 1, maxWidth: 350 }}>
      <Typography variant="subtitle2" fontWeight="bold" gutterBottom>
        {doc.name}
      </Typography>
      <Typography variant="body2" sx={{ mb: 1 }}>
        {doc.description}
      </Typography>

      {value !== undefined && (
        <Chip
          label={`Current: ${formatParameterValue(param, value)}`}
          size="small"
          color="primary"
          sx={{ mb: 1 }}
        />
      )}

      <Divider sx={{ my: 1 }} />

      <Box sx={{ mb: 1 }}>
        <Typography variant="caption" fontWeight="bold" color="success.main">
          Increase effect:
        </Typography>
        <Typography variant="caption" display="block">
          {doc.increaseEffect}
        </Typography>
      </Box>

      <Box sx={{ mb: 1 }}>
        <Typography variant="caption" fontWeight="bold" color="error.main">
          Decrease effect:
        </Typography>
        <Typography variant="caption" display="block">
          {doc.decreaseEffect}
        </Typography>
      </Box>

      <Divider sx={{ my: 1 }} />

      <Typography variant="caption" fontWeight="bold">
        Recommended values:
      </Typography>
      <Box sx={{ display: 'flex', gap: 1, mt: 0.5 }}>
        <Chip label={`Fast: ${doc.recommended.fast}`} size="small" sx={{ bgcolor: '#f44336', color: 'white' }} />
        <Chip label={`Med: ${doc.recommended.medium}`} size="small" sx={{ bgcolor: '#ff9800', color: 'white' }} />
        <Chip label={`Slow: ${doc.recommended.slow}`} size="small" sx={{ bgcolor: '#4caf50', color: 'white' }} />
      </Box>

      {doc.warningThresholds && (
        <Box sx={{ mt: 1, p: 1, bgcolor: alpha('#ff9800', 0.1), borderRadius: 1 }}>
          <Typography variant="caption" color="warning.main">
            <WarningIcon sx={{ fontSize: 12, mr: 0.5, verticalAlign: 'middle' }} />
            {doc.warningThresholds.warning}
          </Typography>
        </Box>
      )}
    </Box>
  );
};

/**
 * Variant preset tooltip (SB-04)
 */
interface VariantPresetTooltipContentProps {
  variantName: string;
}

export const VariantPresetTooltipContent: React.FC<VariantPresetTooltipContentProps> = ({
  variantName,
}) => {
  const preset = getVariantPreset(variantName);
  if (!preset) {
    return (
      <Typography variant="body2">
        Unknown variant: {variantName}
      </Typography>
    );
  }

  return (
    <Box sx={{ p: 1, maxWidth: 350 }}>
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
        <SpeedIcon sx={{ color: preset.color }} />
        <Typography variant="subtitle2" fontWeight="bold" sx={{ color: preset.color }}>
          {preset.name}
        </Typography>
      </Box>

      <Typography variant="body2" sx={{ mb: 1 }}>
        {preset.description}
      </Typography>

      <Divider sx={{ my: 1 }} />

      <Typography variant="caption" fontWeight="bold" display="block" sx={{ mb: 0.5 }}>
        Parameters:
      </Typography>
      <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5, mb: 1 }}>
        {Object.entries(preset.parameters).map(([key, value]) => (
          <Chip
            key={key}
            label={`${key}=${formatParameterValue(key, value)}`}
            size="small"
            variant="outlined"
            sx={{ fontSize: '0.7rem', borderColor: preset.color, color: preset.color }}
          />
        ))}
      </Box>

      <Box sx={{ p: 1, bgcolor: alpha(preset.color, 0.1), borderRadius: 1 }}>
        <Typography variant="caption">
          <TrendingUpIcon sx={{ fontSize: 12, mr: 0.5, verticalAlign: 'middle' }} />
          {preset.useCase}
        </Typography>
      </Box>
    </Box>
  );
};

/**
 * Full parameter documentation panel (IV-03)
 */
interface ParameterDocsPanelProps {
  parameters?: Record<string, number>;
  showAll?: boolean;
}

export const ParameterDocsPanel: React.FC<ParameterDocsPanelProps> = ({
  parameters,
  showAll = false,
}) => {
  const paramsToShow = showAll
    ? Object.keys(PARAMETER_DOCS)
    : parameters
    ? Object.keys(parameters)
    : [];

  if (paramsToShow.length === 0) {
    return (
      <Typography variant="body2" color="text.secondary">
        No parameters to display
      </Typography>
    );
  }

  return (
    <Paper sx={{ p: 2, mt: 2 }}>
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
        <InfoIcon color="primary" />
        <Typography variant="h6">Parameter Documentation</Typography>
      </Box>

      <Table size="small">
        <TableHead>
          <TableRow>
            <TableCell><strong>Parameter</strong></TableCell>
            <TableCell><strong>Current</strong></TableCell>
            <TableCell><strong>Description</strong></TableCell>
            <TableCell><strong>Recommended</strong></TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {paramsToShow.map((param) => {
            const doc = getParameterDoc(param);
            const value = parameters?.[param];
            if (!doc) return null;

            return (
              <TableRow key={param}>
                <TableCell>
                  <Tooltip title={<ParameterTooltipContent param={param} value={value} />} arrow>
                    <Chip
                      label={doc.shortName}
                      size="small"
                      icon={<TimerIcon sx={{ fontSize: 14 }} />}
                      sx={{ cursor: 'help' }}
                    />
                  </Tooltip>
                </TableCell>
                <TableCell>
                  {value !== undefined ? (
                    <Typography variant="body2" fontWeight="bold">
                      {formatParameterValue(param, value)}
                    </Typography>
                  ) : (
                    <Typography variant="body2" color="text.secondary">
                      -
                    </Typography>
                  )}
                </TableCell>
                <TableCell>
                  <Typography variant="caption">{doc.effect}</Typography>
                </TableCell>
                <TableCell>
                  <Box sx={{ display: 'flex', gap: 0.5 }}>
                    <Chip label={`${doc.recommended.fast}`} size="small" sx={{ bgcolor: '#f44336', color: 'white', fontSize: '0.65rem', height: 18 }} />
                    <Chip label={`${doc.recommended.medium}`} size="small" sx={{ bgcolor: '#ff9800', color: 'white', fontSize: '0.65rem', height: 18 }} />
                    <Chip label={`${doc.recommended.slow}`} size="small" sx={{ bgcolor: '#4caf50', color: 'white', fontSize: '0.65rem', height: 18 }} />
                  </Box>
                </TableCell>
              </TableRow>
            );
          })}
        </TableBody>
      </Table>

      <Box sx={{ mt: 2, p: 1.5, bgcolor: 'grey.50', borderRadius: 1 }}>
        <Typography variant="caption" color="text.secondary">
          <strong>Legend:</strong> Red = Fast (aggressive), Orange = Medium (balanced), Green = Slow (conservative)
        </Typography>
      </Box>
    </Paper>
  );
};

/**
 * Compact variant chip with tooltip (SB-04)
 */
interface VariantChipProps {
  variantName: string;
  showTooltip?: boolean;
  size?: 'small' | 'medium';
}

export const VariantChip: React.FC<VariantChipProps> = ({
  variantName,
  showTooltip = true,
  size = 'small',
}) => {
  const preset = getVariantPreset(variantName);

  const chip = (
    <Chip
      label={variantName}
      size={size}
      icon={<SpeedIcon sx={{ fontSize: size === 'small' ? 14 : 18 }} />}
      sx={{
        bgcolor: preset ? alpha(preset.color, 0.15) : undefined,
        color: preset?.color,
        borderColor: preset?.color,
        cursor: showTooltip ? 'help' : 'default',
      }}
      variant="outlined"
    />
  );

  if (!showTooltip || !preset) {
    return chip;
  }

  return (
    <Tooltip title={<VariantPresetTooltipContent variantName={variantName} />} arrow>
      {chip}
    </Tooltip>
  );
};

export default ParameterDocsPanel;

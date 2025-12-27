/**
 * Variant Comparison Component (IV-02)
 * =====================================
 *
 * Side-by-side comparison of indicator variants.
 * Helps traders understand differences between Fast, Medium, Slow variants.
 *
 * Features:
 * - Select 2 variants to compare
 * - Side-by-side parameter comparison
 * - Highlighted differences
 * - Description comparison
 * - Use case recommendations
 *
 * Related: docs/UI_BACKLOG.md (IV-02)
 */

import React, { useState, useEffect } from 'react';
import {
  Box,
  Paper,
  Typography,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Grid,
  Chip,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Alert,
  CircularProgress,
  IconButton,
  Tooltip,
  Divider,
  Stack,
} from '@mui/material';
import { Logger } from '@/services/frontendLogService';
import {
  Compare as CompareIcon,
  SwapHoriz as SwapIcon,
  ArrowForward as ArrowIcon,
  Info as InfoIcon,
  CheckCircle as SameIcon,
  ChangeCircle as DifferentIcon,
} from '@mui/icons-material';
import { IndicatorVariant } from '@/types/strategy';
import { apiService } from '@/services/api';

// ============================================================================
// Types
// ============================================================================

interface VariantComparisonProps {
  variants?: IndicatorVariant[];
  onVariantsLoad?: (variants: IndicatorVariant[]) => void;
}

interface ParameterDiff {
  name: string;
  leftValue: any;
  rightValue: any;
  isDifferent: boolean;
  percentDiff?: number;
}

// ============================================================================
// Constants
// ============================================================================

const VARIANT_SPEED_DESCRIPTIONS: Record<string, string> = {
  Fast: 'Reacts quickly to market changes. Best for volatile markets and scalping.',
  Medium: 'Balanced sensitivity. Good for swing trading and general use.',
  Slow: 'Filters out noise. Best for trend following and longer timeframes.',
};

// ============================================================================
// Component
// ============================================================================

export const VariantComparison: React.FC<VariantComparisonProps> = ({
  variants: propVariants,
  onVariantsLoad,
}) => {
  const [variants, setVariants] = useState<IndicatorVariant[]>(propVariants || []);
  const [loading, setLoading] = useState(!propVariants);
  const [error, setError] = useState<string | null>(null);

  const [leftVariantId, setLeftVariantId] = useState<string>('');
  const [rightVariantId, setRightVariantId] = useState<string>('');

  // ========================================
  // Data Loading
  // ========================================

  useEffect(() => {
    if (propVariants) {
      setVariants(propVariants);
      setLoading(false);
      return;
    }

    const loadVariants = async () => {
      setLoading(true);
      setError(null);

      try {
        const data = await apiService.getVariants();

        // Transform backend data to frontend format
        const transformedVariants: IndicatorVariant[] = data.map((variant: any) => ({
          id: variant.variant_id ?? variant.id,
          name: variant.name,
          baseType: variant.base_indicator_type || variant.baseType,
          type: variant.variant_type || variant.type || 'general',
          description: variant.description,
          parameters: variant.parameters || {},
          isActive: true,
        }));

        setVariants(transformedVariants);
        onVariantsLoad?.(transformedVariants);

        // Auto-select first two variants if available
        if (transformedVariants.length >= 2) {
          setLeftVariantId(transformedVariants[0].id);
          setRightVariantId(transformedVariants[1].id);
        } else if (transformedVariants.length === 1) {
          setLeftVariantId(transformedVariants[0].id);
        }
      } catch (err) {
        Logger.error('VariantComparison.loadVariants', 'Failed to load variants', { error: err });
        setError('Failed to load variants');
      } finally {
        setLoading(false);
      }
    };

    loadVariants();
  }, [propVariants, onVariantsLoad]);

  // ========================================
  // Derived Data
  // ========================================

  const leftVariant = variants.find((v) => v.id === leftVariantId);
  const rightVariant = variants.find((v) => v.id === rightVariantId);

  const getParameterDiffs = (): ParameterDiff[] => {
    if (!leftVariant || !rightVariant) return [];

    const allParams = new Set([
      ...Object.keys(leftVariant.parameters || {}),
      ...Object.keys(rightVariant.parameters || {}),
    ]);

    return Array.from(allParams).map((paramName) => {
      const leftVal = leftVariant.parameters?.[paramName];
      const rightVal = rightVariant.parameters?.[paramName];
      const isDifferent = leftVal !== rightVal;

      let percentDiff: number | undefined;
      if (isDifferent && typeof leftVal === 'number' && typeof rightVal === 'number' && leftVal !== 0) {
        percentDiff = ((rightVal - leftVal) / leftVal) * 100;
      }

      return {
        name: paramName,
        leftValue: leftVal,
        rightValue: rightVal,
        isDifferent,
        percentDiff,
      };
    });
  };

  const parameterDiffs = getParameterDiffs();
  const differentCount = parameterDiffs.filter((d) => d.isDifferent).length;
  const sameCount = parameterDiffs.filter((d) => !d.isDifferent).length;

  // ========================================
  // Handlers
  // ========================================

  const handleSwap = () => {
    const temp = leftVariantId;
    setLeftVariantId(rightVariantId);
    setRightVariantId(temp);
  };

  const getSpeedCategory = (name: string): 'Fast' | 'Medium' | 'Slow' | null => {
    const lowerName = name.toLowerCase();
    if (lowerName.includes('fast')) return 'Fast';
    if (lowerName.includes('medium')) return 'Medium';
    if (lowerName.includes('slow')) return 'Slow';
    return null;
  };

  const formatValue = (value: any): string => {
    if (value === undefined || value === null) return 'N/A';
    if (typeof value === 'boolean') return value ? 'Yes' : 'No';
    if (typeof value === 'number') return value.toFixed(value % 1 === 0 ? 0 : 4);
    if (typeof value === 'object') return JSON.stringify(value);
    return String(value);
  };

  // ========================================
  // Render
  // ========================================

  if (loading) {
    return (
      <Paper sx={{ p: 3, display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: 200 }}>
        <CircularProgress size={24} sx={{ mr: 2 }} />
        <Typography variant="body2" color="text.secondary">
          Loading variants...
        </Typography>
      </Paper>
    );
  }

  if (error) {
    return (
      <Paper sx={{ p: 3 }}>
        <Alert severity="error">{error}</Alert>
      </Paper>
    );
  }

  if (variants.length < 2) {
    return (
      <Paper sx={{ p: 3 }}>
        <Alert severity="info">
          At least 2 variants are required for comparison. Create more variants first.
        </Alert>
      </Paper>
    );
  }

  return (
    <Paper sx={{ p: 3 }}>
      {/* Header */}
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 3 }}>
        <CompareIcon color="primary" />
        <Typography variant="h6">Variant Comparison (IV-02)</Typography>
      </Box>

      {/* Variant Selectors */}
      <Grid container spacing={2} alignItems="center" sx={{ mb: 3 }}>
        <Grid item xs={5}>
          <FormControl fullWidth size="small">
            <InputLabel>Left Variant</InputLabel>
            <Select
              value={leftVariantId}
              onChange={(e) => setLeftVariantId(e.target.value)}
              label="Left Variant"
            >
              {variants.map((variant) => (
                <MenuItem key={variant.id} value={variant.id} disabled={variant.id === rightVariantId}>
                  {variant.name}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
        </Grid>

        <Grid item xs={2} sx={{ textAlign: 'center' }}>
          <Tooltip title="Swap variants">
            <IconButton onClick={handleSwap} color="primary">
              <SwapIcon />
            </IconButton>
          </Tooltip>
        </Grid>

        <Grid item xs={5}>
          <FormControl fullWidth size="small">
            <InputLabel>Right Variant</InputLabel>
            <Select
              value={rightVariantId}
              onChange={(e) => setRightVariantId(e.target.value)}
              label="Right Variant"
            >
              {variants.map((variant) => (
                <MenuItem key={variant.id} value={variant.id} disabled={variant.id === leftVariantId}>
                  {variant.name}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
        </Grid>
      </Grid>

      {/* Comparison Stats */}
      {leftVariant && rightVariant && (
        <>
          <Stack direction="row" spacing={2} sx={{ mb: 3 }}>
            <Chip
              icon={<SameIcon />}
              label={`${sameCount} same`}
              color="success"
              variant="outlined"
              size="small"
            />
            <Chip
              icon={<DifferentIcon />}
              label={`${differentCount} different`}
              color="warning"
              variant="outlined"
              size="small"
            />
          </Stack>

          {/* Side by Side Info */}
          <Grid container spacing={3} sx={{ mb: 3 }}>
            {/* Left Variant Info */}
            <Grid item xs={6}>
              <Paper variant="outlined" sx={{ p: 2 }}>
                <Typography variant="subtitle1" fontWeight={600} gutterBottom>
                  {leftVariant.name}
                </Typography>
                {getSpeedCategory(leftVariant.name) && (
                  <Chip
                    label={getSpeedCategory(leftVariant.name)}
                    size="small"
                    color={
                      getSpeedCategory(leftVariant.name) === 'Fast'
                        ? 'error'
                        : getSpeedCategory(leftVariant.name) === 'Slow'
                        ? 'success'
                        : 'warning'
                    }
                    sx={{ mb: 1 }}
                  />
                )}
                <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                  {leftVariant.description || 'No description'}
                </Typography>
                {getSpeedCategory(leftVariant.name) && (
                  <Typography variant="caption" color="text.secondary" sx={{ fontStyle: 'italic' }}>
                    {VARIANT_SPEED_DESCRIPTIONS[getSpeedCategory(leftVariant.name)!]}
                  </Typography>
                )}
                <Typography variant="caption" display="block" sx={{ mt: 1 }}>
                  Base: {leftVariant.baseType}
                </Typography>
              </Paper>
            </Grid>

            {/* Right Variant Info */}
            <Grid item xs={6}>
              <Paper variant="outlined" sx={{ p: 2 }}>
                <Typography variant="subtitle1" fontWeight={600} gutterBottom>
                  {rightVariant.name}
                </Typography>
                {getSpeedCategory(rightVariant.name) && (
                  <Chip
                    label={getSpeedCategory(rightVariant.name)}
                    size="small"
                    color={
                      getSpeedCategory(rightVariant.name) === 'Fast'
                        ? 'error'
                        : getSpeedCategory(rightVariant.name) === 'Slow'
                        ? 'success'
                        : 'warning'
                    }
                    sx={{ mb: 1 }}
                  />
                )}
                <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                  {rightVariant.description || 'No description'}
                </Typography>
                {getSpeedCategory(rightVariant.name) && (
                  <Typography variant="caption" color="text.secondary" sx={{ fontStyle: 'italic' }}>
                    {VARIANT_SPEED_DESCRIPTIONS[getSpeedCategory(rightVariant.name)!]}
                  </Typography>
                )}
                <Typography variant="caption" display="block" sx={{ mt: 1 }}>
                  Base: {rightVariant.baseType}
                </Typography>
              </Paper>
            </Grid>
          </Grid>

          {/* Parameter Comparison Table */}
          <Typography variant="subtitle2" gutterBottom>
            Parameter Comparison
          </Typography>
          <TableContainer component={Paper} variant="outlined">
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell sx={{ fontWeight: 600 }}>Parameter</TableCell>
                  <TableCell align="center" sx={{ fontWeight: 600, bgcolor: 'primary.light', color: 'white' }}>
                    {leftVariant.name}
                  </TableCell>
                  <TableCell align="center" sx={{ width: 40 }}></TableCell>
                  <TableCell align="center" sx={{ fontWeight: 600, bgcolor: 'secondary.light', color: 'white' }}>
                    {rightVariant.name}
                  </TableCell>
                  <TableCell align="center">Diff</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {parameterDiffs.map((diff) => (
                  <TableRow
                    key={diff.name}
                    sx={{
                      bgcolor: diff.isDifferent ? 'warning.light' : 'transparent',
                      '& td': { opacity: diff.isDifferent ? 1 : 0.7 },
                    }}
                  >
                    <TableCell>
                      <Typography variant="body2" fontWeight={diff.isDifferent ? 600 : 400}>
                        {diff.name}
                      </Typography>
                    </TableCell>
                    <TableCell align="center">
                      <Typography variant="body2" fontFamily="monospace">
                        {formatValue(diff.leftValue)}
                      </Typography>
                    </TableCell>
                    <TableCell align="center">
                      {diff.isDifferent ? (
                        <ArrowIcon fontSize="small" color="action" />
                      ) : (
                        <Typography variant="body2" color="text.secondary">
                          =
                        </Typography>
                      )}
                    </TableCell>
                    <TableCell align="center">
                      <Typography variant="body2" fontFamily="monospace">
                        {formatValue(diff.rightValue)}
                      </Typography>
                    </TableCell>
                    <TableCell align="center">
                      {diff.isDifferent ? (
                        diff.percentDiff !== undefined ? (
                          <Chip
                            label={`${diff.percentDiff >= 0 ? '+' : ''}${diff.percentDiff.toFixed(0)}%`}
                            size="small"
                            color={diff.percentDiff >= 0 ? 'info' : 'error'}
                            sx={{ fontSize: '0.7rem' }}
                          />
                        ) : (
                          <DifferentIcon fontSize="small" color="warning" />
                        )
                      ) : (
                        <SameIcon fontSize="small" color="success" />
                      )}
                    </TableCell>
                  </TableRow>
                ))}
                {parameterDiffs.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={5} align="center">
                      <Typography variant="body2" color="text.secondary">
                        No parameters to compare
                      </Typography>
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </TableContainer>

          {/* Recommendation */}
          {getSpeedCategory(leftVariant.name) && getSpeedCategory(rightVariant.name) && (
            <Alert severity="info" sx={{ mt: 2 }}>
              <Typography variant="body2">
                <strong>Recommendation:</strong> Use{' '}
                <strong>{getSpeedCategory(leftVariant.name) === 'Fast' ? leftVariant.name : rightVariant.name}</strong>{' '}
                for scalping/volatile markets.{' '}
                Use{' '}
                <strong>{getSpeedCategory(leftVariant.name) === 'Slow' ? leftVariant.name : rightVariant.name}</strong>{' '}
                for trend following/stable markets.
              </Typography>
            </Alert>
          )}
        </>
      )}
    </Paper>
  );
};

export default VariantComparison;

'use client';

/**
 * Symbol Recommendation Panel (TS-03)
 * ===================================
 *
 * Recommends symbols based on their suitability for pump/dump trading.
 * Analyzes volume, volatility, and recent activity to suggest best candidates.
 *
 * Features:
 * - Fetches symbol data from exchange API
 * - Calculates pump suitability score
 * - Shows recommendations with reasons
 * - Color-coded recommendation levels
 * - Quick add to trading session
 * - Mock data fallback for development
 *
 * Related: docs/UI_BACKLOG.md - TS-03
 */

import React, { useState, useEffect, useCallback } from 'react';
import {
  Box,
  Paper,
  Typography,
  Card,
  CardContent,
  Chip,
  LinearProgress,
  Alert,
  IconButton,
  Tooltip,
  Grid,
  Stack,
  Divider,
  Button,
} from '@mui/material';
import { Logger } from '@/services/frontendLogService';
import {
  TrendingUp as TrendingUpIcon,
  Speed as SpeedIcon,
  Info as InfoIcon,
  Refresh as RefreshIcon,
  Add as AddIcon,
  Star as StarIcon,
  StarBorder as StarBorderIcon,
  TipsAndUpdates as TipsIcon,
  BarChart as VolumeIcon,
  ShowChart as VolatilityIcon,
  FlashOn as PumpIcon,
} from '@mui/icons-material';

// ============================================================================
// TYPES
// ============================================================================

export interface SymbolAnalysis {
  symbol: string;
  price: number;
  volume24h: number;
  change24h: number;
  volatility: number;
  liquidity: number;
  pumpScore: number;
  recommendationLevel: 'excellent' | 'good' | 'moderate' | 'poor';
  reasons: string[];
}

export interface SymbolRecommendationProps {
  selectedSymbols?: string[];
  onAddSymbol?: (symbol: string) => void;
  onRemoveSymbol?: (symbol: string) => void;
  maxRecommendations?: number;
}

// ============================================================================
// SCORE CALCULATION
// ============================================================================

function calculatePumpScore(data: {
  volume24h: number;
  change24h: number;
  volatility: number;
  liquidity: number;
}): { score: number; reasons: string[] } {
  const reasons: string[] = [];
  let score = 0;

  // Volume score (0-30 points)
  // High volume = better liquidity for quick entries/exits
  if (data.volume24h > 100000000) {
    score += 30;
    reasons.push('Excellent volume (>$100M) - great liquidity');
  } else if (data.volume24h > 50000000) {
    score += 25;
    reasons.push('High volume (>$50M) - good liquidity');
  } else if (data.volume24h > 10000000) {
    score += 15;
    reasons.push('Moderate volume (>$10M)');
  } else if (data.volume24h > 1000000) {
    score += 5;
    reasons.push('Low volume - may have slippage');
  } else {
    reasons.push('Very low volume - avoid for pump trading');
  }

  // Volatility score (0-30 points)
  // Moderate volatility is ideal for pumps
  if (data.volatility >= 3 && data.volatility <= 10) {
    score += 30;
    reasons.push('Ideal volatility (3-10%) - good pump potential');
  } else if (data.volatility > 10 && data.volatility <= 20) {
    score += 20;
    reasons.push('High volatility - strong moves but risky');
  } else if (data.volatility > 1 && data.volatility < 3) {
    score += 10;
    reasons.push('Low volatility - less pump activity');
  } else if (data.volatility > 20) {
    score += 5;
    reasons.push('Extreme volatility - very risky');
  } else {
    reasons.push('Minimal volatility - not suitable for pumps');
  }

  // Recent movement score (0-20 points)
  // Recent activity indicates active trading
  const absChange = Math.abs(data.change24h);
  if (absChange >= 5 && absChange <= 15) {
    score += 20;
    reasons.push('Active 24h movement - market attention');
  } else if (absChange > 15) {
    score += 10;
    reasons.push('Major 24h move - may be overbought/oversold');
  } else if (absChange >= 2) {
    score += 15;
    reasons.push('Moderate 24h change');
  } else {
    score += 5;
    reasons.push('Flat price action');
  }

  // Liquidity score (0-20 points)
  if (data.liquidity >= 80) {
    score += 20;
    reasons.push('Excellent liquidity - tight spreads');
  } else if (data.liquidity >= 50) {
    score += 15;
    reasons.push('Good liquidity');
  } else if (data.liquidity >= 20) {
    score += 10;
    reasons.push('Moderate liquidity');
  } else {
    score += 0;
    reasons.push('Poor liquidity - wide spreads');
  }

  return { score, reasons };
}

function getRecommendationLevel(score: number): 'excellent' | 'good' | 'moderate' | 'poor' {
  if (score >= 80) return 'excellent';
  if (score >= 60) return 'good';
  if (score >= 40) return 'moderate';
  return 'poor';
}

function getRecommendationColor(level: string): 'success' | 'info' | 'warning' | 'error' {
  switch (level) {
    case 'excellent': return 'success';
    case 'good': return 'info';
    case 'moderate': return 'warning';
    default: return 'error';
  }
}

// ============================================================================
// MOCK DATA
// ============================================================================

const generateMockSymbolData = (): SymbolAnalysis[] => {
  const mockSymbols = [
    { symbol: 'SOL_USDT', price: 145.23, volume24h: 850000000, change24h: 7.5, volatility: 8.2, liquidity: 85 },
    { symbol: 'ETH_USDT', price: 2450.00, volume24h: 2500000000, change24h: 3.2, volatility: 4.5, liquidity: 95 },
    { symbol: 'DOGE_USDT', price: 0.125, volume24h: 450000000, change24h: 12.8, volatility: 15.3, liquidity: 75 },
    { symbol: 'PEPE_USDT', price: 0.0000125, volume24h: 320000000, change24h: 18.5, volatility: 22.1, liquidity: 60 },
    { symbol: 'LINK_USDT', price: 15.80, volume24h: 180000000, change24h: 4.2, volatility: 6.1, liquidity: 78 },
    { symbol: 'AVAX_USDT', price: 38.50, volume24h: 220000000, change24h: 5.8, volatility: 7.8, liquidity: 72 },
    { symbol: 'MATIC_USDT', price: 0.92, volume24h: 150000000, change24h: 2.1, volatility: 5.2, liquidity: 70 },
    { symbol: 'ARB_USDT', price: 1.15, volume24h: 180000000, change24h: 6.5, volatility: 9.1, liquidity: 65 },
    { symbol: 'OP_USDT', price: 2.35, volume24h: 95000000, change24h: 8.2, volatility: 10.5, liquidity: 62 },
    { symbol: 'INJ_USDT', price: 28.90, volume24h: 120000000, change24h: 9.8, volatility: 11.2, liquidity: 58 },
  ];

  return mockSymbols.map(data => {
    const { score, reasons } = calculatePumpScore(data);
    return {
      ...data,
      pumpScore: score,
      recommendationLevel: getRecommendationLevel(score),
      reasons,
    };
  }).sort((a, b) => b.pumpScore - a.pumpScore);
};

// ============================================================================
// COMPONENT
// ============================================================================

export function SymbolRecommendation({
  selectedSymbols = [],
  onAddSymbol,
  onRemoveSymbol,
  maxRecommendations = 5,
}: SymbolRecommendationProps) {
  const [recommendations, setRecommendations] = useState<SymbolAnalysis[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // ========================================
  // Data Loading
  // ========================================

  const loadRecommendations = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080';
      const response = await fetch(`${apiUrl}/api/exchange/symbols`);

      if (response.ok) {
        const result = await response.json();
        const symbolsData = result.data?.symbols || result.symbols || [];

        // Transform API data to SymbolAnalysis
        const analyzed: SymbolAnalysis[] = symbolsData.map((s: any) => {
          const data = {
            volume24h: s.volume24h || s.quoteVolume || 0,
            change24h: s.change24h || s.priceChangePercent || 0,
            volatility: Math.abs(s.change24h || 0) * 1.5, // Estimate volatility
            liquidity: Math.min(100, (s.volume24h || 0) / 10000000), // Estimate liquidity
          };

          const { score, reasons } = calculatePumpScore(data);

          return {
            symbol: s.symbol,
            price: s.price || s.lastPrice || 0,
            ...data,
            pumpScore: score,
            recommendationLevel: getRecommendationLevel(score),
            reasons,
          };
        });

        // Sort by pump score and take top recommendations
        const sorted = analyzed.sort((a, b) => b.pumpScore - a.pumpScore);
        setRecommendations(sorted.slice(0, maxRecommendations * 2)); // Keep more for filtering
      } else if (response.status === 404) {
        // API not available, use mock data
        Logger.info('SymbolRecommendation.loadRecommendations', 'API not available, using mock data');
        setRecommendations(generateMockSymbolData());
      } else {
        throw new Error(`API error: ${response.status}`);
      }
    } catch (err) {
      Logger.error('SymbolRecommendation.loadRecommendations', 'Failed to load recommendations', { error: err });
      // Use mock data as fallback
      setRecommendations(generateMockSymbolData());
    } finally {
      setLoading(false);
    }
  }, [maxRecommendations]);

  useEffect(() => {
    loadRecommendations();
  }, [loadRecommendations]);

  // ========================================
  // Handlers
  // ========================================

  const isSelected = (symbol: string) => selectedSymbols.includes(symbol);

  const handleToggleSymbol = (symbol: string) => {
    if (isSelected(symbol)) {
      onRemoveSymbol?.(symbol);
    } else {
      onAddSymbol?.(symbol);
    }
  };

  // ========================================
  // Render
  // ========================================

  if (loading) {
    return (
      <Paper sx={{ p: 2 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
          <TipsIcon color="primary" />
          <Typography variant="subtitle1" fontWeight={600}>
            Symbol Recommendations
          </Typography>
        </Box>
        <LinearProgress />
        <Typography variant="body2" color="text.secondary" sx={{ mt: 1, textAlign: 'center' }}>
          Analyzing symbols for pump trading suitability...
        </Typography>
      </Paper>
    );
  }

  if (error) {
    return (
      <Paper sx={{ p: 2 }}>
        <Alert severity="error">{error}</Alert>
      </Paper>
    );
  }

  // Filter to show top recommendations not already selected
  const topRecommendations = recommendations
    .filter(r => !isSelected(r.symbol))
    .slice(0, maxRecommendations);

  return (
    <Paper sx={{ p: 2 }}>
      {/* Header */}
      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 2 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <TipsIcon color="primary" />
          <Typography variant="subtitle1" fontWeight={600}>
            Symbol Recommendations
          </Typography>
          <Chip
            label="Pump Trading"
            size="small"
            color="warning"
            variant="outlined"
          />
        </Box>
        <Tooltip title="Refresh recommendations">
          <IconButton size="small" onClick={loadRecommendations}>
            <RefreshIcon fontSize="small" />
          </IconButton>
        </Tooltip>
      </Box>

      {/* Info Alert */}
      <Alert severity="info" sx={{ mb: 2 }} icon={<InfoIcon />}>
        <Typography variant="body2">
          Symbols ranked by pump trading suitability: volume, volatility, and recent activity.
        </Typography>
      </Alert>

      {/* Recommendations Grid */}
      {topRecommendations.length === 0 ? (
        <Box sx={{ textAlign: 'center', py: 3 }}>
          <Typography variant="body2" color="text.secondary">
            All recommended symbols are already selected!
          </Typography>
        </Box>
      ) : (
        <Grid container spacing={2}>
          {topRecommendations.map((rec, index) => (
            <Grid item xs={12} key={rec.symbol}>
              <Card
                variant="outlined"
                sx={{
                  borderColor: index === 0 ? 'success.main' : 'divider',
                  borderWidth: index === 0 ? 2 : 1,
                }}
              >
                <CardContent sx={{ py: 1.5, '&:last-child': { pb: 1.5 } }}>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                    {/* Symbol Info */}
                    <Box sx={{ flex: 1 }}>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 0.5 }}>
                        {index === 0 && <StarIcon fontSize="small" sx={{ color: 'warning.main' }} />}
                        <Typography variant="subtitle2" fontWeight={600}>
                          {rec.symbol.replace('_', '/')}
                        </Typography>
                        <Chip
                          label={rec.recommendationLevel.toUpperCase()}
                          size="small"
                          color={getRecommendationColor(rec.recommendationLevel)}
                        />
                      </Box>

                      {/* Score Bar */}
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                        <Typography variant="caption" color="text.secondary">
                          Score:
                        </Typography>
                        <LinearProgress
                          variant="determinate"
                          value={rec.pumpScore}
                          color={getRecommendationColor(rec.recommendationLevel)}
                          sx={{ flex: 1, height: 6, borderRadius: 3 }}
                        />
                        <Typography variant="caption" fontWeight={600}>
                          {rec.pumpScore}%
                        </Typography>
                      </Box>

                      {/* Metrics */}
                      <Stack direction="row" spacing={1} flexWrap="wrap" sx={{ mb: 1 }}>
                        <Chip
                          icon={<VolumeIcon />}
                          label={`$${(rec.volume24h / 1000000).toFixed(0)}M vol`}
                          size="small"
                          variant="outlined"
                        />
                        <Chip
                          icon={<VolatilityIcon />}
                          label={`${rec.volatility.toFixed(1)}% vol`}
                          size="small"
                          variant="outlined"
                        />
                        <Chip
                          label={`${rec.change24h >= 0 ? '+' : ''}${rec.change24h.toFixed(1)}%`}
                          size="small"
                          color={rec.change24h >= 0 ? 'success' : 'error'}
                          variant="outlined"
                        />
                      </Stack>

                      {/* Top Reason */}
                      {rec.reasons.length > 0 && (
                        <Typography variant="caption" color="text.secondary" sx={{ fontStyle: 'italic' }}>
                          {rec.reasons[0]}
                        </Typography>
                      )}
                    </Box>

                    {/* Add Button */}
                    <Box sx={{ ml: 2 }}>
                      <Button
                        variant="contained"
                        size="small"
                        startIcon={<AddIcon />}
                        onClick={() => handleToggleSymbol(rec.symbol)}
                        color={getRecommendationColor(rec.recommendationLevel)}
                      >
                        Add
                      </Button>
                    </Box>
                  </Box>
                </CardContent>
              </Card>
            </Grid>
          ))}
        </Grid>
      )}

      {/* Legend */}
      <Divider sx={{ my: 2 }} />
      <Box sx={{ display: 'flex', justifyContent: 'center', gap: 2, flexWrap: 'wrap' }}>
        <Typography variant="caption" color="text.secondary">
          <Chip label="EXCELLENT" size="small" color="success" sx={{ height: 18 }} /> 80-100
        </Typography>
        <Typography variant="caption" color="text.secondary">
          <Chip label="GOOD" size="small" color="info" sx={{ height: 18 }} /> 60-79
        </Typography>
        <Typography variant="caption" color="text.secondary">
          <Chip label="MODERATE" size="small" color="warning" sx={{ height: 18 }} /> 40-59
        </Typography>
        <Typography variant="caption" color="text.secondary">
          <Chip label="POOR" size="small" color="error" sx={{ height: 18 }} /> 0-39
        </Typography>
      </Box>
    </Paper>
  );
}

export default SymbolRecommendation;

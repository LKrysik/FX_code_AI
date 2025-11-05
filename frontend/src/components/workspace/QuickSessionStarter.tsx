/**
 * QuickSessionStarter Component
 *
 * Simplified session starter with smart defaults and auto-remember.
 * Reduces session start from 15+ clicks to 1-2 clicks.
 *
 * Features:
 * - Auto-remembers last used settings
 * - Progressive disclosure (advanced settings collapsed)
 * - Real-time validation
 * - One-click start for repeat sessions
 */

'use client';

import React, { useState, useEffect } from 'react';
import {
  Box,
  Button,
  FormControlLabel,
  Radio,
  RadioGroup,
  Checkbox,
  TextField,
  Typography,
  Collapse,
  Alert,
  CircularProgress,
  Chip,
  Paper,
} from '@mui/material';
import {
  PlayArrow as StartIcon,
  ExpandMore as ExpandIcon,
  ExpandLess as CollapseIcon,
  CheckCircle as SuccessIcon,
} from '@mui/icons-material';
import { useSmartDefaults } from '@/hooks/useSmartDefaults';
import { apiService } from '@/services/api';

export interface SessionConfig {
  session_type: 'paper' | 'live';
  symbols: string[];
  strategy_ids: string[];
  budget: number;
  config?: {
    max_position_size_pct?: number;
    stop_loss_pct?: number;
    order_type?: string;
    slippage_tolerance?: number;
  };
}

interface QuickSessionStarterProps {
  onStart: (config: SessionConfig) => Promise<void>;
  disabled?: boolean;
  currentSession?: any;
}

export const QuickSessionStarter: React.FC<QuickSessionStarterProps> = ({
  onStart,
  disabled = false,
  currentSession,
}) => {
  // Smart defaults with auto-remember
  const [mode, setMode] = useSmartDefaults<'paper' | 'live'>({
    key: 'sessionMode',
    defaultValue: 'paper',
    validator: (v) => ['paper', 'live'].includes(v),
  });

  const [selectedSymbols, setSelectedSymbols] = useSmartDefaults<string[]>({
    key: 'tradingSymbols',
    defaultValue: ['BTC_USDT', 'ETH_USDT'],
    validator: (v) => Array.isArray(v) && v.length > 0,
  });

  const [strategyId, setStrategyId] = useSmartDefaults<string>({
    key: 'lastUsedStrategy',
    defaultValue: '',
  });

  const [budget, setBudget] = useSmartDefaults<number>({
    key: 'tradingBudget',
    defaultValue: 1000,
    validator: (v) => typeof v === 'number' && v > 0,
  });

  // Advanced settings (collapsed by default)
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [maxPositionSize, setMaxPositionSize] = useState(10);
  const [stopLossPct, setStopLossPct] = useState(5);

  // State
  const [strategies, setStrategies] = useState<any[]>([]);
  const [availableSymbols, setAvailableSymbols] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [starting, setStarting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [validationError, setValidationError] = useState<string | null>(null);

  // Load strategies and symbols
  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setLoading(true);
    try {
      const [strategiesData, symbolsData] = await Promise.all([
        apiService.get4SectionStrategies().catch(() => []),
        apiService.getSymbols().catch(() => ['BTC_USDT', 'ETH_USDT', 'ADA_USDT', 'SOL_USDT', 'DOT_USDT']),
      ]);

      setStrategies(strategiesData || []);
      setAvailableSymbols(symbolsData || []);

      // Auto-select first strategy if none selected
      if (!strategyId && strategiesData && strategiesData.length > 0) {
        setStrategyId(strategiesData[0].id);
      }
    } catch (err: any) {
      console.error('Failed to load data:', err);
      setError('Failed to load strategies');
    } finally {
      setLoading(false);
    }
  };

  // Real-time validation
  useEffect(() => {
    if (selectedSymbols.length === 0) {
      setValidationError('Select at least one symbol');
    } else if (!strategyId) {
      setValidationError('Select a strategy');
    } else if (budget <= 0) {
      setValidationError('Budget must be positive');
    } else {
      setValidationError(null);
    }
  }, [selectedSymbols, strategyId, budget]);

  const handleSymbolToggle = (symbol: string) => {
    setSelectedSymbols(prev =>
      prev.includes(symbol)
        ? prev.filter(s => s !== symbol)
        : [...prev, symbol]
    );
  };

  const handleStart = async () => {
    if (validationError) return;

    setStarting(true);
    setError(null);

    try {
      const config: SessionConfig = {
        session_type: mode,
        symbols: selectedSymbols,
        strategy_ids: [strategyId],
        budget: budget,
        config: {
          max_position_size_pct: maxPositionSize,
          stop_loss_pct: stopLossPct,
          order_type: 'market',
          slippage_tolerance: 0.1,
        },
      };

      await onStart(config);
    } catch (err: any) {
      console.error('Failed to start session:', err);
      setError(err.message || 'Failed to start session');
    } finally {
      setStarting(false);
    }
  };

  // Quick restart with same settings
  const handleQuickRestart = () => {
    if (currentSession) {
      handleStart();
    }
  };

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', p: 4 }}>
        <CircularProgress size={32} />
      </Box>
    );
  }

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
      <Typography variant="h6" sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
        Quick Start
        {currentSession && (
          <Chip label="Session Active" color="success" size="small" icon={<SuccessIcon />} />
        )}
      </Typography>

      {error && (
        <Alert severity="error" onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      {/* MODE: Paper/Live */}
      <Box>
        <Typography variant="body2" gutterBottom color="text.secondary">
          Mode:
        </Typography>
        <RadioGroup value={mode} onChange={(e) => setMode(e.target.value as 'paper' | 'live')}>
          <FormControlLabel
            value="paper"
            control={<Radio size="small" />}
            label={
              <Box>
                <Typography variant="body2">Paper Trading</Typography>
                <Typography variant="caption" color="text.secondary">
                  Risk-free simulation
                </Typography>
              </Box>
            }
          />
          <FormControlLabel
            value="live"
            control={<Radio size="small" />}
            label={
              <Box>
                <Typography variant="body2">Live Trading</Typography>
                <Typography variant="caption" color="warning.main">
                  Real money - be careful!
                </Typography>
              </Box>
            }
          />
        </RadioGroup>
      </Box>

      {/* SYMBOLS: Top symbols as checkboxes */}
      <Box>
        <Typography variant="body2" gutterBottom color="text.secondary">
          Symbols: ({selectedSymbols.length} selected)
        </Typography>
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.5 }}>
          {availableSymbols.slice(0, 5).map(symbol => (
            <FormControlLabel
              key={symbol}
              control={
                <Checkbox
                  size="small"
                  checked={selectedSymbols.includes(symbol)}
                  onChange={() => handleSymbolToggle(symbol)}
                />
              }
              label={<Typography variant="body2">{symbol.replace('_', '/')}</Typography>}
            />
          ))}
          {availableSymbols.length > 5 && (
            <Typography variant="caption" color="text.secondary" sx={{ ml: 4 }}>
              + {availableSymbols.length - 5} more symbols
            </Typography>
          )}
        </Box>
      </Box>

      {/* STRATEGY: Dropdown */}
      <TextField
        select
        label="Strategy"
        value={strategyId}
        onChange={(e) => setStrategyId(e.target.value)}
        SelectProps={{ native: true }}
        size="small"
        fullWidth
        helperText={
          strategies.length === 0
            ? 'No strategies available. Create one first.'
            : 'Last used strategy auto-selected'
        }
      >
        <option value="">Select strategy...</option>
        {strategies.map(s => (
          <option key={s.id} value={s.id}>
            {s.strategy_name || s.name}
          </option>
        ))}
      </TextField>

      {/* BUDGET */}
      <TextField
        type="number"
        label="Budget (USD)"
        value={budget}
        onChange={(e) => setBudget(Number(e.target.value))}
        size="small"
        fullWidth
        InputProps={{
          startAdornment: <Typography sx={{ mr: 1 }}>$</Typography>,
        }}
        helperText="Total capital for this session"
      />

      {/* ADVANCED SETTINGS (collapsed) */}
      <Button
        size="small"
        onClick={() => setShowAdvanced(!showAdvanced)}
        endIcon={showAdvanced ? <CollapseIcon /> : <ExpandIcon />}
        sx={{ alignSelf: 'flex-start' }}
      >
        Advanced Settings
      </Button>

      <Collapse in={showAdvanced}>
        <Paper sx={{ p: 2, bgcolor: 'background.default' }}>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
            <TextField
              label="Max Position Size (%)"
              type="number"
              value={maxPositionSize}
              onChange={(e) => setMaxPositionSize(Number(e.target.value))}
              size="small"
              fullWidth
              helperText="% of budget per position"
            />
            <TextField
              label="Stop Loss (%)"
              type="number"
              value={stopLossPct}
              onChange={(e) => setStopLossPct(Number(e.target.value))}
              size="small"
              fullWidth
              helperText="Automatic stop loss"
            />
          </Box>
        </Paper>
      </Collapse>

      {/* VALIDATION ERROR */}
      {validationError && (
        <Alert severity="warning" sx={{ fontSize: '0.875rem' }}>
          {validationError}
        </Alert>
      )}

      {/* START BUTTON */}
      <Button
        variant="contained"
        size="large"
        startIcon={starting ? <CircularProgress size={20} color="inherit" /> : <StartIcon />}
        onClick={handleStart}
        disabled={disabled || !!validationError || starting || strategies.length === 0}
        fullWidth
        sx={{ py: 1.5 }}
      >
        {starting ? 'STARTING...' : 'START SESSION'}
      </Button>

      {disabled && currentSession && (
        <Alert severity="info" sx={{ fontSize: '0.875rem' }}>
          <Typography variant="body2" gutterBottom>
            Session already running: <strong>{currentSession.session_id}</strong>
          </Typography>
          <Typography variant="caption">
            Stop current session before starting a new one, or use Quick Restart to restart with same settings.
          </Typography>
          <Button
            size="small"
            variant="outlined"
            onClick={handleQuickRestart}
            sx={{ mt: 1 }}
          >
            Quick Restart
          </Button>
        </Alert>
      )}

      {/* HELP TEXT */}
      <Typography variant="caption" color="text.secondary" sx={{ textAlign: 'center' }}>
        Your settings are automatically saved for next time
      </Typography>
    </Box>
  );
};

export default QuickSessionStarter;

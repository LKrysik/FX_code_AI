/**
 * Session Configuration Dialog
 * ============================
 *
 * Comprehensive session configuration for Live/Paper/Backtest modes.
 * Integrates with real backend APIs for strategy/symbol selection.
 *
 * Features:
 * - Strategy selection (multi-select table with metadata)
 * - Symbol selection (chip interface with real-time prices)
 * - Budget and risk configuration
 * - Backtest-specific options (session selection, acceleration factor)
 * - Form validation
 * - Real API integration (GET /api/strategies, GET /api/exchange/symbols)
 *
 * Related: docs/frontend/TARGET_STATE_TRADING_INTERFACE.md
 * Related: docs/frontend/BACKEND_ENDPOINTS_READY.md
 */

import React, { useState, useEffect } from 'react';
import { Logger } from '@/services/frontendLogService';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Box,
  Typography,
  TextField,
  Chip,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Checkbox,
  Paper,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Slider,
  Alert,
  CircularProgress,
  Tabs,
  Tab,
  Divider,
  Tooltip,
} from '@mui/material';
import {
  CheckCircle as CheckIcon,
  Warning as WarningIcon,
  Info as InfoIcon,
} from '@mui/icons-material';

// ============================================================================
// Types
// ============================================================================

export interface Strategy {
  id: string;
  strategy_name: string;
  description: string;
  direction: 'long' | 'short' | 'both';
  enabled: boolean;
  category?: string;
  tags?: string[];
  // Performance metrics (if available)
  win_rate?: number;
  avg_profit?: number;
  total_trades?: number;
}

export interface SymbolInfo {
  symbol: string;
  name: string;
  price: number;
  volume24h: number;
  change24h: number;
  exchange: string;
}

export interface DataCollectionSession {
  session_id: string;
  symbols: string[];
  data_types: string[];
  status: string;
  start_time: string;
  end_time: string;
  records_collected: number;
  duration?: string;
}

export interface SessionConfig {
  session_type: 'live' | 'paper' | 'backtest';
  symbols: string[];
  strategy_config: {
    strategies: string[];
  };
  config: {
    budget: {
      global_cap: number;
      allocations: Record<string, number>;
    };
    stop_loss_percent?: number;
    take_profit_percent?: number;
    max_position_size?: number;
    session_id?: string; // For backtest
    acceleration_factor?: number; // For backtest
  };
  idempotent: boolean;
}

export interface SessionConfigDialogProps {
  open: boolean;
  mode: 'live' | 'paper' | 'backtest';
  onClose: () => void;
  onSubmit: (config: SessionConfig) => void;
}

// ============================================================================
// Component
// ============================================================================

export const SessionConfigDialog: React.FC<SessionConfigDialogProps> = ({
  open,
  mode,
  onClose,
  onSubmit,
}) => {
  // ========================================
  // State Management
  // ========================================

  // Data Loading States
  const [strategiesLoading, setStrategiesLoading] = useState(false);
  const [symbolsLoading, setSymbolsLoading] = useState(false);
  const [sessionsLoading, setSessionsLoading] = useState(false);

  // Data
  const [strategies, setStrategies] = useState<Strategy[]>([]);
  const [symbols, setSymbols] = useState<SymbolInfo[]>([]);
  const [dataSessions, setDataSessions] = useState<DataCollectionSession[]>([]);

  // Selections
  const [selectedStrategies, setSelectedStrategies] = useState<string[]>([]);
  const [selectedSymbols, setSelectedSymbols] = useState<string[]>([]);

  // Configuration
  const [globalBudget, setGlobalBudget] = useState<number>(1000);
  const [maxPositionSize, setMaxPositionSize] = useState<number>(100);
  const [stopLoss, setStopLoss] = useState<number>(5.0);
  const [takeProfit, setTakeProfit] = useState<number>(10.0);

  // Backtest-specific
  const [backtestSessionId, setBacktestSessionId] = useState<string>('');
  const [accelerationFactor, setAccelerationFactor] = useState<number>(10);

  // UI State
  const [activeTab, setActiveTab] = useState<number>(0);
  const [validationErrors, setValidationErrors] = useState<string[]>([]);

  // ========================================
  // Effects: Data Loading
  // ========================================

  /**
   * Load strategies from GET /api/strategies
   * Requires JWT authentication.
   * FIX: Added AbortController cleanup to prevent state updates after unmount
   */
  useEffect(() => {
    if (!open) return;

    const abortController = new AbortController();
    let isMounted = true;

    const fetchStrategies = async () => {
      setStrategiesLoading(true);
      // Clear previous errors when fetching fresh data
      setValidationErrors([]);

      try {
        // Cache auth token to avoid repeated localStorage access
        const authToken = localStorage.getItem('authToken');
        const headers: HeadersInit = {
          'Content-Type': 'application/json',
        };

        if (authToken) {
          headers['Authorization'] = `Bearer ${authToken}`;
        }

        const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080';
        const response = await fetch(`${apiUrl}/api/strategies`, {
          headers,
          signal: abortController.signal,
        });

        if (!response.ok) {
          if (response.status === 401) {
            throw new Error('Authentication required. Please log in.');
          }
          throw new Error(`Failed to load strategies: ${response.status}`);
        }

        const result = await response.json();

        // Type-safe null check
        if (!result) {
          throw new Error('Empty response from strategies API');
        }

        const data = result.data || result;
        if (!data || !Array.isArray(data.strategies)) {
          throw new Error('Invalid response format from strategies API');
        }

        // Only update state if component is still mounted
        if (isMounted) {
          setStrategies(data.strategies);
        }
      } catch (error) {
        // Don't show error for aborted requests
        if (error instanceof Error && error.name === 'AbortError') {
          return;
        }

        Logger.error('SessionConfigDialog.loadStrategies', { message: 'Failed to load strategies', error });

        // Type-safe error message extraction
        const errorMessage = error instanceof Error
          ? error.message
          : 'Unknown error occurred';

        if (isMounted) {
          setValidationErrors([`Strategy loading error: ${errorMessage}`]);
        }
      } finally {
        if (isMounted) {
          setStrategiesLoading(false);
        }
      }
    };

    fetchStrategies();

    // Cleanup: abort fetch and prevent state updates on unmount
    return () => {
      isMounted = false;
      abortController.abort();
    };
  }, [open]);

  /**
   * Load symbols from GET /api/exchange/symbols
   * No authentication required (public endpoint with caching).
   * FIX: Added AbortController cleanup to prevent state updates after unmount
   */
  useEffect(() => {
    if (!open) return;

    const abortController = new AbortController();
    let isMounted = true;

    const fetchSymbols = async () => {
      setSymbolsLoading(true);

      try {
        const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080';
        const response = await fetch(`${apiUrl}/api/exchange/symbols`, {
          signal: abortController.signal,
        });

        if (!response.ok) {
          throw new Error(`Failed to load symbols: ${response.status}`);
        }

        const result = await response.json();

        // Type-safe null check
        if (!result) {
          throw new Error('Empty response from symbols API');
        }

        const data = result.data || result;
        if (!data || !Array.isArray(data.symbols)) {
          throw new Error('Invalid response format from symbols API');
        }

        // Only update state if component is still mounted
        if (isMounted) {
          setSymbols(data.symbols);
        }
      } catch (error) {
        // Don't show error for aborted requests
        if (error instanceof Error && error.name === 'AbortError') {
          return;
        }

        Logger.error('SessionConfigDialog.loadSymbols', { message: 'Failed to load symbols', error });

        // Type-safe error message extraction
        const errorMessage = error instanceof Error
          ? error.message
          : 'Unknown error occurred';

        if (isMounted) {
          setValidationErrors((prev) => [...prev, `Symbol loading error: ${errorMessage}`]);
        }
      } finally {
        if (isMounted) {
          setSymbolsLoading(false);
        }
      }
    };

    fetchSymbols();

    // Cleanup: abort fetch and prevent state updates on unmount
    return () => {
      isMounted = false;
      abortController.abort();
    };
  }, [open]);

  /**
   * Load data collection sessions for backtest mode.
   * GET /api/data-collection/sessions?limit=50
   * FIX: Added AbortController cleanup and removed backtestSessionId from deps to prevent infinite loop
   */
  useEffect(() => {
    if (!open || mode !== 'backtest') return;

    const abortController = new AbortController();
    let isMounted = true;

    const fetchSessions = async () => {
      setSessionsLoading(true);

      try {
        const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080';
        const response = await fetch(
          `${apiUrl}/api/data-collection/sessions?limit=50`,
          { signal: abortController.signal }
        );

        if (!response.ok) {
          throw new Error(`Failed to load sessions: ${response.status}`);
        }

        const result = await response.json();

        // Type-safe null check
        if (!result) {
          throw new Error('Empty response from sessions API');
        }

        const sessions = result.data?.sessions || result.sessions || [];

        if (!Array.isArray(sessions)) {
          throw new Error('Invalid response format from sessions API');
        }

        // Only update state if component is still mounted
        if (isMounted) {
          setDataSessions(sessions);

          // Auto-select first session ONLY if user hasn't manually selected one yet
          // FIX: Check current state value instead of using it in deps
          setBacktestSessionId((currentValue) => {
            if (!currentValue && sessions.length > 0) {
              return sessions[0].session_id;
            }
            return currentValue;
          });
        }
      } catch (error) {
        // Don't show error for aborted requests
        if (error instanceof Error && error.name === 'AbortError') {
          return;
        }

        Logger.error('SessionConfigDialog.loadSessions', { message: 'Failed to load data sessions', error });

        // Type-safe error message extraction
        const errorMessage = error instanceof Error
          ? error.message
          : 'Unknown error occurred';

        if (isMounted) {
          setValidationErrors((prev) => [...prev, `Session loading error: ${errorMessage}`]);
        }
      } finally {
        if (isMounted) {
          setSessionsLoading(false);
        }
      }
    };

    fetchSessions();

    // Cleanup: abort fetch and prevent state updates on unmount
    return () => {
      isMounted = false;
      abortController.abort();
    };
  }, [open, mode]); // Removed backtestSessionId from deps to prevent infinite loop

  // ========================================
  // Event Handlers
  // ========================================

  const toggleStrategy = (strategyId: string) => {
    setSelectedStrategies((prev) =>
      prev.includes(strategyId)
        ? prev.filter((id) => id !== strategyId)
        : [...prev, strategyId]
    );
  };

  const toggleSymbol = (symbol: string) => {
    setSelectedSymbols((prev) =>
      prev.includes(symbol) ? prev.filter((s) => s !== symbol) : [...prev, symbol]
    );
  };

  const selectTopSymbols = (count: number) => {
    // FIX ERROR 23: Check if symbols array has enough elements
    if (symbols.length === 0) {
      setValidationErrors(['No symbols available to select.']);
      return;
    }

    const actualCount = Math.min(count, symbols.length);
    const top = symbols.slice(0, actualCount).map((s) => s.symbol);
    setSelectedSymbols(top);

    // Inform user if fewer symbols available than requested
    if (actualCount < count) {
      setValidationErrors([`Only ${actualCount} symbols available (requested ${count}).`]);
    } else {
      // Clear any previous errors
      setValidationErrors([]);
    }
  };

  const clearSymbols = () => {
    setSelectedSymbols([]);
  };

  const handleSubmit = () => {
    // Validate
    const errors: string[] = [];

    if (selectedStrategies.length === 0) {
      errors.push('Please select at least one strategy.');
    }

    if (selectedSymbols.length === 0) {
      errors.push('Please select at least one symbol.');
    }

    // FIX ERROR 18: Check for NaN vulnerability
    if (!Number.isFinite(globalBudget) || globalBudget <= 0) {
      errors.push('Global budget must be a valid number greater than 0.');
    }

    // FIX ERROR 19: Validate maxPositionSize
    if (!Number.isFinite(maxPositionSize) || maxPositionSize <= 0) {
      errors.push('Max position size must be a valid number greater than 0.');
    }

    // FIX ERROR 22: Validate max position vs global budget
    if (Number.isFinite(maxPositionSize) && Number.isFinite(globalBudget) && maxPositionSize > globalBudget) {
      errors.push('Max position size cannot exceed global budget.');
    }

    if (mode === 'backtest' && !backtestSessionId) {
      errors.push('Please select a data collection session for backtesting.');
    }

    // FIX ERROR 18: Check for NaN in stop loss
    if (!Number.isFinite(stopLoss) || stopLoss < 0 || stopLoss > 100) {
      errors.push('Stop loss must be a valid number between 0 and 100.');
    }

    // FIX ERROR 18: Check for NaN in take profit
    if (!Number.isFinite(takeProfit) || takeProfit < 0 || takeProfit > 1000) {
      errors.push('Take profit must be a valid number between 0 and 1000.');
    }

    // FIX ERROR 20: Validate acceleration factor for backtest
    if (mode === 'backtest' && (!Number.isFinite(accelerationFactor) || accelerationFactor <= 0)) {
      errors.push('Acceleration factor must be a valid number greater than 0.');
    }

    if (errors.length > 0) {
      setValidationErrors(errors);
      // FIX ERROR 21: Scroll to top to show errors
      window.scrollTo({ top: 0, behavior: 'smooth' });
      return;
    }

    // Build config
    const config: SessionConfig = {
      session_type: mode,
      symbols: selectedSymbols,
      strategy_config: {
        strategies: selectedStrategies,
      },
      config: {
        budget: {
          global_cap: globalBudget,
          allocations: {},
        },
        stop_loss_percent: stopLoss,
        take_profit_percent: takeProfit,
        max_position_size: maxPositionSize,
        ...(mode === 'backtest' && {
          session_id: backtestSessionId,
          acceleration_factor: accelerationFactor,
        }),
      },
      idempotent: true,
    };

    // Clear errors and submit
    setValidationErrors([]);
    onSubmit(config);
  };

  const handleClose = () => {
    // FIX ERROR 30: Reset all form state to prevent confusion on re-open
    setValidationErrors([]);
    setSelectedStrategies([]);
    setSelectedSymbols([]);
    setGlobalBudget(1000);
    setMaxPositionSize(100);
    setStopLoss(5.0);
    setTakeProfit(10.0);
    setBacktestSessionId('');
    setAccelerationFactor(10);
    setActiveTab(0);
    onClose();
  };

  // ========================================
  // Render Helpers
  // ========================================

  const renderValidationErrors = () => {
    if (validationErrors.length === 0) return null;

    return (
      <Alert severity="error" sx={{ mb: 2 }} onClose={() => setValidationErrors([])}>
        <Typography variant="body2" fontWeight="bold" gutterBottom>
          Please fix the following errors:
        </Typography>
        <ul style={{ margin: 0, paddingLeft: 20 }}>
          {validationErrors.map((error, idx) => (
            <li key={idx}>{error}</li>
          ))}
        </ul>
      </Alert>
    );
  };

  const renderStrategiesTab = () => (
    <Box>
      <Typography variant="h6" gutterBottom>
        Select Strategies
      </Typography>
      <Typography variant="body2" color="text.secondary" gutterBottom>
        Choose one or more strategies to use in this session.
      </Typography>

      {strategiesLoading ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
          <CircularProgress />
        </Box>
      ) : strategies.length === 0 ? (
        <Alert severity="warning" sx={{ mt: 2 }}>
          No strategies available. Please create strategies first.
        </Alert>
      ) : (
        <TableContainer component={Paper} sx={{ mt: 2, maxHeight: 400 }}>
          <Table stickyHeader size="small">
            <TableHead>
              <TableRow>
                <TableCell padding="checkbox">Select</TableCell>
                <TableCell>Name</TableCell>
                <TableCell>Direction</TableCell>
                <TableCell>Category</TableCell>
                <TableCell align="right">Win Rate</TableCell>
                <TableCell align="right">Avg Profit</TableCell>
                <TableCell>Status</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {strategies.map((strategy) => (
                <TableRow
                  key={strategy.id}
                  hover
                  sx={{ cursor: 'pointer' }}
                  selected={selectedStrategies.includes(strategy.id)}
                >
                  <TableCell padding="checkbox">
                    <Checkbox
                      checked={selectedStrategies.includes(strategy.id)}
                      onChange={() => toggleStrategy(strategy.id)}
                    />
                  </TableCell>
                  <TableCell>
                    <Typography variant="body2" fontWeight="medium">
                      {strategy.strategy_name}
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      {strategy.description}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <Chip
                      label={strategy.direction.toUpperCase()}
                      size="small"
                      color={
                        // FIX ERROR 32: Handle 'both' direction properly
                        strategy.direction === 'long' ? 'success' :
                        strategy.direction === 'short' ? 'error' :
                        strategy.direction === 'both' ? 'info' : 'default'
                      }
                    />
                  </TableCell>
                  <TableCell>{strategy.category || 'N/A'}</TableCell>
                  <TableCell align="right">
                    {strategy.win_rate !== undefined ? `${strategy.win_rate.toFixed(1)}%` : 'N/A'}
                  </TableCell>
                  <TableCell align="right">
                    {strategy.avg_profit !== undefined ? `$${strategy.avg_profit.toFixed(2)}` : 'N/A'}
                  </TableCell>
                  <TableCell>
                    {strategy.enabled ? (
                      <Chip label="Active" size="small" color="success" icon={<CheckIcon />} />
                    ) : (
                      <Chip label="Inactive" size="small" color="default" />
                    )}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      )}

      <Typography variant="body2" color="primary" sx={{ mt: 2 }}>
        Selected: {selectedStrategies.length} / {strategies.length}
      </Typography>
    </Box>
  );

  const renderSymbolsTab = () => (
    <Box>
      <Typography variant="h6" gutterBottom>
        Select Symbols
      </Typography>
      <Typography variant="body2" color="text.secondary" gutterBottom>
        Choose one or more trading pairs to monitor.
      </Typography>

      <Box sx={{ display: 'flex', gap: 1, mb: 2, mt: 2 }}>
        <Button size="small" variant="outlined" onClick={() => selectTopSymbols(3)}>
          Top 3
        </Button>
        <Button size="small" variant="outlined" onClick={() => selectTopSymbols(5)}>
          Top 5
        </Button>
        <Button size="small" variant="outlined" onClick={clearSymbols}>
          Clear All
        </Button>
      </Box>

      {symbolsLoading ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
          <CircularProgress />
        </Box>
      ) : symbols.length === 0 ? (
        <Alert severity="warning" sx={{ mt: 2 }}>
          No symbols available. Check backend configuration.
        </Alert>
      ) : (
        <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1, mt: 2 }}>
          {symbols.map((symbolInfo) => {
            const isSelected = selectedSymbols.includes(symbolInfo.symbol);
            return (
              <Tooltip
                key={symbolInfo.symbol}
                title={
                  <Box>
                    <Typography variant="caption">
                      {/* FIX ERROR 33: Safe price display with null check and dynamic precision */}
                      Price: ${
                        symbolInfo.price != null
                          ? symbolInfo.price < 1
                            ? symbolInfo.price.toFixed(6)
                            : symbolInfo.price.toFixed(2)
                          : 'N/A'
                      }
                    </Typography>
                    <br />
                    <Typography variant="caption">
                      {/* FIX ERROR 34: Better volume formatting */}
                      24h Volume: ${
                        symbolInfo.volume24h != null
                          ? symbolInfo.volume24h >= 1000000
                            ? `${(symbolInfo.volume24h / 1000000).toFixed(2)}M`
                            : `${(symbolInfo.volume24h / 1000).toFixed(2)}K`
                          : 'N/A'
                      }
                    </Typography>
                    <br />
                    <Typography variant="caption">
                      24h Change: {symbolInfo.change24h != null ? symbolInfo.change24h.toFixed(2) : 'N/A'}%
                    </Typography>
                  </Box>
                }
              >
                <Chip
                  label={
                    <Box>
                      <Typography variant="body2" component="span" fontWeight="medium">
                        {symbolInfo.name}
                      </Typography>
                      <Typography
                        variant="caption"
                        component="span"
                        sx={{ ml: 1 }}
                        color="text.secondary"
                      >
                        {/* FIX ERROR 33: Safe price display in chip label */}
                        ${
                          symbolInfo.price != null
                            ? symbolInfo.price < 1
                              ? symbolInfo.price.toFixed(6)
                              : symbolInfo.price.toFixed(2)
                            : 'N/A'
                        }
                      </Typography>
                    </Box>
                  }
                  clickable
                  color={isSelected ? 'primary' : 'default'}
                  onClick={() => toggleSymbol(symbolInfo.symbol)}
                  sx={{
                    height: 'auto',
                    py: 1,
                    px: 2,
                    '& .MuiChip-label': {
                      display: 'block',
                      whiteSpace: 'normal',
                    },
                  }}
                />
              </Tooltip>
            );
          })}
        </Box>
      )}

      <Typography variant="body2" color="primary" sx={{ mt: 2 }}>
        Selected: {selectedSymbols.length} / {symbols.length}
      </Typography>

      {selectedSymbols.length > 0 && (
        <Box sx={{ mt: 2 }}>
          <Typography variant="body2" fontWeight="medium" gutterBottom>
            Selected Symbols:
          </Typography>
          <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
            {selectedSymbols.map((symbol) => (
              <Chip
                key={symbol}
                label={symbol}
                size="small"
                color="primary"
                onDelete={() => toggleSymbol(symbol)}
              />
            ))}
          </Box>
        </Box>
      )}
    </Box>
  );

  const renderConfigTab = () => (
    <Box>
      <Typography variant="h6" gutterBottom>
        Budget & Risk Configuration
      </Typography>

      <Box sx={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 2, mt: 2 }}>
        <TextField
          label="Global Budget (USDT)"
          type="number"
          value={globalBudget}
          onChange={(e) => {
            // FIX ERROR 18: Prevent NaN by validating input
            const value = e.target.value;
            const num = Number(value);
            // Only update if it's a valid number or empty string (for clearing)
            if (value === '' || Number.isFinite(num)) {
              setGlobalBudget(value === '' ? 0 : num);
            }
          }}
          helperText="Total capital allocated for this session"
          fullWidth
          error={!Number.isFinite(globalBudget) || globalBudget < 0}
        />

        <TextField
          label="Max Position Size (USDT)"
          type="number"
          value={maxPositionSize}
          onChange={(e) => {
            // FIX ERROR 19: Prevent NaN in maxPositionSize
            const value = e.target.value;
            const num = Number(value);
            if (value === '' || Number.isFinite(num)) {
              setMaxPositionSize(value === '' ? 0 : num);
            }
          }}
          helperText="Maximum size per single position"
          fullWidth
          error={!Number.isFinite(maxPositionSize) || maxPositionSize < 0}
        />

        <TextField
          label="Stop Loss (%)"
          type="number"
          value={stopLoss}
          onChange={(e) => {
            // FIX ERROR 18: Prevent NaN in stopLoss
            const value = e.target.value;
            const num = Number(value);
            if (value === '' || Number.isFinite(num)) {
              setStopLoss(value === '' ? 0 : num);
            }
          }}
          helperText="Automatic stop loss percentage"
          fullWidth
          inputProps={{ min: 0, max: 100, step: 0.1 }}
          error={!Number.isFinite(stopLoss) || stopLoss < 0 || stopLoss > 100}
        />

        <TextField
          label="Take Profit (%)"
          type="number"
          value={takeProfit}
          onChange={(e) => {
            // FIX ERROR 18: Prevent NaN in takeProfit
            const value = e.target.value;
            const num = Number(value);
            if (value === '' || Number.isFinite(num)) {
              setTakeProfit(value === '' ? 0 : num);
            }
          }}
          helperText="Automatic take profit percentage"
          fullWidth
          inputProps={{ min: 0, max: 1000, step: 0.1 }}
          error={!Number.isFinite(takeProfit) || takeProfit < 0 || takeProfit > 1000}
        />
      </Box>

      {mode === 'backtest' && (
        <>
          <Divider sx={{ my: 3 }} />

          <Typography variant="h6" gutterBottom>
            Backtest Configuration
          </Typography>

          <FormControl fullWidth sx={{ mt: 2 }}>
            <InputLabel id="backtest-session-label">Data Collection Session</InputLabel>
            <Select
              labelId="backtest-session-label"
              value={backtestSessionId}
              label="Data Collection Session"
              onChange={(e) => setBacktestSessionId(e.target.value)}
              disabled={sessionsLoading}
            >
              {sessionsLoading ? (
                <MenuItem disabled>Loading sessions...</MenuItem>
              ) : dataSessions.length === 0 ? (
                <MenuItem disabled>No sessions available</MenuItem>
              ) : (
                dataSessions.map((session) => (
                  <MenuItem key={session.session_id} value={session.session_id}>
                    <Box>
                      <Typography variant="body2">{session.session_id}</Typography>
                      <Typography variant="caption" color="text.secondary">
                        {new Date(session.start_time).toLocaleString()} -{' '}
                        {session.records_collected.toLocaleString()} records - {session.duration || 'N/A'}
                      </Typography>
                    </Box>
                  </MenuItem>
                ))
              )}
            </Select>
          </FormControl>

          <Box sx={{ mt: 3 }}>
            <Typography variant="body2" gutterBottom>
              Acceleration Factor: {accelerationFactor}x
            </Typography>
            <Slider
              value={accelerationFactor}
              onChange={(_, value) => setAccelerationFactor(value as number)}
              min={1}
              max={100}
              step={1}
              marks={[
                { value: 1, label: '1x' },
                { value: 10, label: '10x' },
                { value: 50, label: '50x' },
                { value: 100, label: '100x' },
              ]}
              valueLabelDisplay="auto"
            />
            <Typography variant="caption" color="text.secondary">
              Higher acceleration = faster replay (1x = real-time, 100x = 100× faster)
            </Typography>
          </Box>
        </>
      )}

      {mode === 'live' && (
        <Alert severity="warning" sx={{ mt: 3 }} icon={<WarningIcon />}>
          <Typography variant="body2" fontWeight="bold">
            LIVE TRADING MODE
          </Typography>
          <Typography variant="caption">
            This will use REAL MONEY on the exchange. Please verify all settings carefully.
          </Typography>
        </Alert>
      )}

      {mode === 'paper' && (
        <Alert severity="info" sx={{ mt: 3 }} icon={<InfoIcon />}>
          <Typography variant="body2">
            Paper trading mode uses simulated money. Trades are virtual but data is real.
          </Typography>
        </Alert>
      )}
    </Box>
  );

  // ========================================
  // Render
  // ========================================

  return (
    <Dialog
      open={open}
      onClose={handleClose}
      maxWidth="md"
      fullWidth
      PaperProps={{
        sx: { minHeight: '70vh' },
      }}
    >
      <DialogTitle>
        <Box>
          <Typography variant="inherit" component="span" sx={{ display: 'block', mb: 0.5 }}>
            Configure {mode === 'live' ? 'Live' : mode === 'paper' ? 'Paper' : 'Backtest'} Session
          </Typography>
          <Typography variant="body2" color="text.secondary" component="span" sx={{ display: 'block' }}>
            Set up strategies, symbols, and risk parameters for your trading session
          </Typography>
        </Box>
      </DialogTitle>

      <DialogContent dividers>
        {renderValidationErrors()}

        <Box sx={{ borderBottom: 1, borderColor: 'divider', mb: 3 }}>
          <Tabs value={activeTab} onChange={(_, newValue) => setActiveTab(newValue)}>
            <Tab label={`1. Strategies (${selectedStrategies.length})`} />
            <Tab label={`2. Symbols (${selectedSymbols.length})`} />
            <Tab label="3. Configuration" />
          </Tabs>
        </Box>

        <Box sx={{ minHeight: 400 }}>
          {activeTab === 0 && renderStrategiesTab()}
          {activeTab === 1 && renderSymbolsTab()}
          {activeTab === 2 && renderConfigTab()}
        </Box>
      </DialogContent>

      <DialogActions>
        <Button onClick={handleClose} color="inherit">
          Cancel
        </Button>
        <Button onClick={handleSubmit} variant="contained" color="primary">
          Start Session
        </Button>
      </DialogActions>
    </Dialog>
  );
};

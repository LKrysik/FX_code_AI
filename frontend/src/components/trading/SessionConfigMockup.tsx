/**
 * ⚠️ MOCKUP COMPONENT - NOT FOR PRODUCTION USE ⚠️
 * ===================================================
 *
 * Unified Session Configuration UI Mockup
 *
 * TODO: This is a visual mockup with artificial data for presentation purposes.
 * TODO: Implement real functionality before using in production:
 *
 * 1. Replace mock data with real API calls
 * 2. Implement actual session creation logic
 * 3. Connect to backend REST endpoints (/api/sessions/start)
 * 4. Add proper form validation
 * 5. Integrate with TradingStore and DashboardStore
 * 6. Remove all MOCKUP labels and warnings
 * 7. Add comprehensive error handling
 * 8. Implement budget and risk management controls
 *
 * Created: 2025-11-18
 * Issue: Insufficient UI for configuring strategies, symbols, and session parameters
 *
 * This mockup addresses user requirements for:
 * - Live trading session configuration
 * - Paper trading session configuration
 * - Backtest session configuration
 * - Strategy selection and management
 * - Symbol selection with real-time validation
 * - Budget allocation and risk parameters
 */

'use client';

import React, { useState } from 'react';
import {
  Box,
  Paper,
  Typography,
  TextField,
  Button,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Chip,
  Alert,
  AlertTitle,
  Divider,
  Grid,
  Checkbox,
  FormControlLabel,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Card,
  CardContent,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  IconButton,
  Tooltip,
  Switch,
  Slider,
} from '@mui/material';
import { Logger } from '@/services/frontendLogService';
import {
  ExpandMore as ExpandMoreIcon,
  Add as AddIcon,
  Delete as DeleteIcon,
  Warning as WarningIcon,
  Info as InfoIcon,
  CheckCircle as CheckCircleIcon,
  Error as ErrorIcon,
  Settings as SettingsIcon,
  TrendingUp as TrendingUpIcon,
  AttachMoney as AttachMoneyIcon,
  Speed as SpeedIcon,
  Storage as StorageIcon,
} from '@mui/icons-material';

// ⚠️ MOCKUP DATA - Replace with real API calls
const MOCK_STRATEGIES = [
  { id: 'strategy_001', name: 'Pump Detection v2', description: 'Detects rapid price increases', enabled: true, winRate: 68 },
  { id: 'strategy_002', name: 'Dump Detection v2', description: 'Detects rapid price decreases', enabled: true, winRate: 72 },
  { id: 'strategy_003', name: 'Volume Surge', description: 'Trades on volume anomalies', enabled: false, winRate: 55 },
  { id: 'strategy_004', name: 'Mean Reversion', description: 'Statistical mean reversion strategy', enabled: false, winRate: 61 },
  { id: 'strategy_005', name: 'Trend Following', description: 'Follows medium-term trends', enabled: false, winRate: 59 },
];

// ⚠️ MOCKUP DATA - Replace with real exchange API
const MOCK_SYMBOLS = [
  'BTC_USDT', 'ETH_USDT', 'BNB_USDT', 'SOL_USDT', 'XRP_USDT',
  'ADA_USDT', 'DOGE_USDT', 'MATIC_USDT', 'DOT_USDT', 'AVAX_USDT',
  'LINK_USDT', 'UNI_USDT', 'ATOM_USDT', 'LTC_USDT', 'XLM_USDT',
];

// ⚠️ MOCKUP DATA - Replace with real historical sessions from QuestDB
const MOCK_DATA_SESSIONS = [
  { id: 'session_20251118_120530_abc123', timestamp: '2025-11-18 12:05:30', symbols: ['BTC_USDT', 'ETH_USDT'], records: 15420 },
  { id: 'session_20251117_093245_def456', timestamp: '2025-11-17 09:32:45', symbols: ['BTC_USDT'], records: 8932 },
  { id: 'session_20251116_184512_ghi789', timestamp: '2025-11-16 18:45:12', symbols: ['ETH_USDT', 'BNB_USDT', 'SOL_USDT'], records: 22103 },
];

type SessionMode = 'live' | 'paper' | 'backtest';

interface SessionConfigMockupProps {
  onSessionStart?: (config: any) => void;
  onCancel?: () => void;
}

/**
 * ⚠️ MOCKUP COMPONENT
 *
 * Unified session configuration component for live trading, paper trading, and backtesting.
 *
 * TODO: Connect to real backend APIs:
 * - GET /api/strategies - fetch available strategies
 * - GET /api/exchange/symbols - fetch tradeable symbols
 * - GET /api/data-collection/sessions - fetch historical sessions (for backtest)
 * - POST /api/sessions/start - create and start session
 */
export const SessionConfigMockup: React.FC<SessionConfigMockupProps> = ({ onSessionStart, onCancel }) => {
  // ⚠️ MOCKUP STATE - Replace with proper state management (Zustand stores)
  const [mode, setMode] = useState<SessionMode>('paper');
  const [selectedStrategies, setSelectedStrategies] = useState<string[]>(['strategy_001', 'strategy_002']);
  const [selectedSymbols, setSelectedSymbols] = useState<string[]>(['BTC_USDT', 'ETH_USDT']);
  const [globalBudget, setGlobalBudget] = useState<number>(1000);
  const [maxPositionSize, setMaxPositionSize] = useState<number>(100);
  const [stopLossPercent, setStopLossPercent] = useState<number>(5);
  const [takeProfitPercent, setTakeProfitPercent] = useState<number>(10);
  const [backtestSessionId, setBacktestSessionId] = useState<string>('');
  const [accelerationFactor, setAccelerationFactor] = useState<number>(10);
  const [autoStart, setAutoStart] = useState<boolean>(true);

  // ⚠️ MOCKUP HANDLER - Replace with real session creation logic
  const handleStartSession = () => {
    // TODO: Validate form inputs
    // TODO: Call POST /api/sessions/start with proper config
    // TODO: Handle errors and loading states
    // TODO: Redirect to dashboard on success

    const mockConfig = {
      mode,
      strategies: selectedStrategies,
      symbols: selectedSymbols,
      config: {
        global_budget: globalBudget,
        max_position_size: maxPositionSize,
        stop_loss_percent: stopLossPercent,
        take_profit_percent: takeProfitPercent,
        session_id: mode === 'backtest' ? backtestSessionId : undefined,
        acceleration_factor: mode === 'backtest' ? accelerationFactor : undefined,
        auto_start: autoStart,
      }
    };

    Logger.info('SessionConfigMockup.startSession', 'MOCKUP: Would start session with config', mockConfig);

    if (onSessionStart) {
      onSessionStart(mockConfig);
    }
  };

  const toggleStrategy = (strategyId: string) => {
    setSelectedStrategies(prev =>
      prev.includes(strategyId)
        ? prev.filter(id => id !== strategyId)
        : [...prev, strategyId]
    );
  };

  const toggleSymbol = (symbol: string) => {
    setSelectedSymbols(prev =>
      prev.includes(symbol)
        ? prev.filter(s => s !== symbol)
        : [...prev, symbol]
    );
  };

  return (
    <Box sx={{ p: 3, maxWidth: 1200, mx: 'auto' }}>
      {/* ⚠️ MOCKUP WARNING BANNER */}
      <Alert severity="warning" sx={{ mb: 3 }}>
        <AlertTitle><strong>⚠️ MOCKUP COMPONENT - NOT FUNCTIONAL</strong></AlertTitle>
        This is a visual prototype with artificial data. All selections and actions are simulated.
        This component requires full backend integration before production use.
      </Alert>

      <Paper sx={{ p: 3 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', mb: 3 }}>
          <SettingsIcon sx={{ mr: 1, color: 'primary.main' }} />
          <Typography variant="h5" sx={{ fontWeight: 'bold' }}>
            Session Configuration
          </Typography>
        </Box>

        <Divider sx={{ mb: 3 }} />

        {/* MODE SELECTION */}
        <Grid container spacing={3}>
          <Grid item xs={12}>
            <FormControl fullWidth>
              <InputLabel>Trading Mode</InputLabel>
              <Select
                value={mode}
                label="Trading Mode"
                onChange={(e) => setMode(e.target.value as SessionMode)}
              >
                <MenuItem value="live">
                  🔴 Live Trading (Real Money - Use with caution!)
                </MenuItem>
                <MenuItem value="paper">
                  📝 Paper Trading (Simulated - Recommended for testing)
                </MenuItem>
                <MenuItem value="backtest">
                  ⏪ Backtest (Historical Data Replay)
                </MenuItem>
              </Select>
            </FormControl>

            {mode === 'live' && (
              <Alert severity="error" sx={{ mt: 2 }}>
                <AlertTitle><strong>WARNING: Real Money Trading</strong></AlertTitle>
                Live trading mode uses real funds. Ensure you understand the risks and have tested your strategies in paper mode first.
              </Alert>
            )}

            {mode === 'paper' && (
              <Alert severity="info" sx={{ mt: 2 }}>
                <AlertTitle><strong>Paper Trading Mode</strong></AlertTitle>
                Simulated trading with virtual funds. Perfect for testing strategies without risk.
              </Alert>
            )}

            {mode === 'backtest' && (
              <Alert severity="info" sx={{ mt: 2 }}>
                <AlertTitle><strong>Backtest Mode</strong></AlertTitle>
                Test strategies against historical data to evaluate performance before live deployment.
              </Alert>
            )}
          </Grid>

          {/* BACKTEST-SPECIFIC: Session Selection */}
          {mode === 'backtest' && (
            <Grid item xs={12}>
              <Card sx={{ bgcolor: 'background.default' }}>
                <CardContent>
                  <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                    <StorageIcon sx={{ mr: 1 }} />
                    <Typography variant="h6">Historical Data Session</Typography>
                    <Chip label="MOCKUP DATA" size="small" color="warning" sx={{ ml: 2 }} />
                  </Box>

                  <FormControl fullWidth sx={{ mb: 2 }}>
                    <InputLabel>Select Data Collection Session</InputLabel>
                    <Select
                      value={backtestSessionId}
                      label="Select Data Collection Session"
                      onChange={(e) => setBacktestSessionId(e.target.value)}
                    >
                      {/* ⚠️ MOCKUP DATA - Replace with GET /api/data-collection/sessions */}
                      {MOCK_DATA_SESSIONS.map(session => (
                        <MenuItem key={session.id} value={session.id}>
                          {session.timestamp} - {session.symbols.join(', ')} ({session.records.toLocaleString()} records)
                        </MenuItem>
                      ))}
                    </Select>
                  </FormControl>

                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                    <SpeedIcon />
                    <Typography variant="body2" sx={{ flex: 1 }}>
                      Acceleration Factor: {accelerationFactor}x
                    </Typography>
                    <Box sx={{ width: 200 }}>
                      <Slider
                        value={accelerationFactor}
                        onChange={(_, value) => setAccelerationFactor(value as number)}
                        min={1}
                        max={100}
                        marks={[
                          { value: 1, label: '1x' },
                          { value: 10, label: '10x' },
                          { value: 100, label: '100x' },
                        ]}
                      />
                    </Box>
                  </Box>

                  <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
                    ⚠️ MOCKUP: Acceleration factor controls how fast historical data is replayed.
                    Higher values = faster backtest, but may consume more resources.
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
          )}

          {/* STRATEGY SELECTION */}
          <Grid item xs={12}>
            <Accordion defaultExpanded>
              <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                <Box sx={{ display: 'flex', alignItems: 'center', width: '100%' }}>
                  <TrendingUpIcon sx={{ mr: 1 }} />
                  <Typography variant="h6" sx={{ flex: 1 }}>
                    Trading Strategies ({selectedStrategies.length} selected)
                  </Typography>
                  <Chip label="MOCKUP DATA" size="small" color="warning" />
                </Box>
              </AccordionSummary>
              <AccordionDetails>
                <Alert severity="info" sx={{ mb: 2 }}>
                  ⚠️ MOCKUP: These strategies are artificial examples.
                  TODO: Replace with GET /api/strategies to fetch real strategies from QuestDB.
                </Alert>

                <List>
                  {/* ⚠️ MOCKUP DATA - Replace with real strategy list */}
                  {MOCK_STRATEGIES.map(strategy => (
                    <ListItem
                      key={strategy.id}
                      sx={{
                        border: 1,
                        borderColor: 'divider',
                        borderRadius: 1,
                        mb: 1,
                        bgcolor: selectedStrategies.includes(strategy.id) ? 'action.selected' : 'background.paper',
                      }}
                    >
                      <ListItemIcon>
                        <Checkbox
                          checked={selectedStrategies.includes(strategy.id)}
                          onChange={() => toggleStrategy(strategy.id)}
                        />
                      </ListItemIcon>
                      <ListItemText
                        primary={
                          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                            {strategy.name}
                            {strategy.enabled ? (
                              <Chip label="Enabled" size="small" color="success" />
                            ) : (
                              <Chip label="Disabled" size="small" color="default" />
                            )}
                            <Chip label={`${strategy.winRate}% Win Rate`} size="small" color="info" />
                          </Box>
                        }
                        secondary={strategy.description}
                      />
                    </ListItem>
                  ))}
                </List>
              </AccordionDetails>
            </Accordion>
          </Grid>

          {/* SYMBOL SELECTION */}
          <Grid item xs={12}>
            <Accordion defaultExpanded>
              <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                <Box sx={{ display: 'flex', alignItems: 'center', width: '100%' }}>
                  <AttachMoneyIcon sx={{ mr: 1 }} />
                  <Typography variant="h6" sx={{ flex: 1 }}>
                    Trading Symbols ({selectedSymbols.length} selected)
                  </Typography>
                  <Chip label="MOCKUP DATA" size="small" color="warning" />
                </Box>
              </AccordionSummary>
              <AccordionDetails>
                <Alert severity="info" sx={{ mb: 2 }}>
                  ⚠️ MOCKUP: These symbols are hardcoded examples.
                  TODO: Replace with GET /api/exchange/symbols to fetch real tradeable pairs from MEXC.
                </Alert>

                <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1, mb: 2 }}>
                  {/* ⚠️ MOCKUP DATA - Replace with real exchange symbols */}
                  {MOCK_SYMBOLS.map(symbol => (
                    <Chip
                      key={symbol}
                      label={symbol}
                      color={selectedSymbols.includes(symbol) ? 'primary' : 'default'}
                      onClick={() => toggleSymbol(symbol)}
                      onDelete={selectedSymbols.includes(symbol) ? () => toggleSymbol(symbol) : undefined}
                      deleteIcon={selectedSymbols.includes(symbol) ? <DeleteIcon /> : undefined}
                    />
                  ))}
                </Box>

                <Box sx={{ display: 'flex', gap: 1 }}>
                  <Button
                    size="small"
                    variant="outlined"
                    onClick={() => setSelectedSymbols(MOCK_SYMBOLS.slice(0, 5))}
                  >
                    Select Top 5
                  </Button>
                  <Button
                    size="small"
                    variant="outlined"
                    onClick={() => setSelectedSymbols([])}
                  >
                    Clear All
                  </Button>
                </Box>
              </AccordionDetails>
            </Accordion>
          </Grid>

          {/* BUDGET AND RISK MANAGEMENT */}
          <Grid item xs={12}>
            <Accordion>
              <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                <Box sx={{ display: 'flex', alignItems: 'center', width: '100%' }}>
                  <AttachMoneyIcon sx={{ mr: 1 }} />
                  <Typography variant="h6" sx={{ flex: 1 }}>
                    Budget & Risk Management
                  </Typography>
                  <Chip label="MOCKUP INPUTS" size="small" color="warning" />
                </Box>
              </AccordionSummary>
              <AccordionDetails>
                <Grid container spacing={2}>
                  <Grid item xs={12} sm={6}>
                    <TextField
                      fullWidth
                      label="Global Budget (USDT)"
                      type="number"
                      value={globalBudget}
                      onChange={(e) => setGlobalBudget(Number(e.target.value))}
                      InputProps={{
                        startAdornment: <Typography sx={{ mr: 1 }}>$</Typography>,
                      }}
                      helperText="Total capital available for trading"
                    />
                  </Grid>

                  <Grid item xs={12} sm={6}>
                    <TextField
                      fullWidth
                      label="Max Position Size (USDT)"
                      type="number"
                      value={maxPositionSize}
                      onChange={(e) => setMaxPositionSize(Number(e.target.value))}
                      InputProps={{
                        startAdornment: <Typography sx={{ mr: 1 }}>$</Typography>,
                      }}
                      helperText="Maximum size per individual position"
                    />
                  </Grid>

                  <Grid item xs={12} sm={6}>
                    <TextField
                      fullWidth
                      label="Stop Loss (%)"
                      type="number"
                      value={stopLossPercent}
                      onChange={(e) => setStopLossPercent(Number(e.target.value))}
                      InputProps={{
                        endAdornment: <Typography>%</Typography>,
                      }}
                      helperText="Automatic stop loss threshold"
                    />
                  </Grid>

                  <Grid item xs={12} sm={6}>
                    <TextField
                      fullWidth
                      label="Take Profit (%)"
                      type="number"
                      value={takeProfitPercent}
                      onChange={(e) => setTakeProfitPercent(Number(e.target.value))}
                      InputProps={{
                        endAdornment: <Typography>%</Typography>,
                      }}
                      helperText="Automatic take profit threshold"
                    />
                  </Grid>

                  <Grid item xs={12}>
                    <Alert severity="warning">
                      ⚠️ MOCKUP: These values are not validated or persisted.
                      TODO: Add proper validation and connect to backend risk management system.
                    </Alert>
                  </Grid>
                </Grid>
              </AccordionDetails>
            </Accordion>
          </Grid>

          {/* ADVANCED OPTIONS */}
          <Grid item xs={12}>
            <FormControlLabel
              control={
                <Switch
                  checked={autoStart}
                  onChange={(e) => setAutoStart(e.target.checked)}
                />
              }
              label="Auto-start session after creation"
            />
          </Grid>

          {/* ACTION BUTTONS */}
          <Grid item xs={12}>
            <Divider sx={{ my: 2 }} />
            <Box sx={{ display: 'flex', gap: 2, justifyContent: 'flex-end' }}>
              <Button
                variant="outlined"
                onClick={onCancel}
              >
                Cancel
              </Button>
              <Button
                variant="contained"
                color="primary"
                size="large"
                onClick={handleStartSession}
                disabled={selectedStrategies.length === 0 || selectedSymbols.length === 0 || (mode === 'backtest' && !backtestSessionId)}
                startIcon={<TrendingUpIcon />}
              >
                {mode === 'live' && '🔴 Start Live Trading'}
                {mode === 'paper' && '📝 Start Paper Trading'}
                {mode === 'backtest' && '⏪ Start Backtest'}
              </Button>
            </Box>

            <Alert severity="warning" sx={{ mt: 2 }}>
              ⚠️ MOCKUP: Button click only logs to console.
              TODO: Implement POST /api/sessions/start with proper error handling and loading states.
            </Alert>
          </Grid>
        </Grid>
      </Paper>
    </Box>
  );
};

export default SessionConfigMockup;

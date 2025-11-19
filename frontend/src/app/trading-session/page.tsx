'use client';

/**
 * ⚠️ MOCKUP: Complete Trading Session Configuration Page
 * =======================================================
 *
 * FULL INTERFACE for configuring and starting trading sessions.
 * Works for: Live Trading, Paper Trading, Backtesting
 *
 * TODO LIST FOR PRODUCTION:
 * ========================
 * 1. Replace MOCK_STRATEGIES with GET /api/strategies
 * 2. Replace MOCK_SYMBOLS with GET /api/exchange/symbols
 * 3. Replace MOCK_DATA_SESSIONS with GET /api/data-collection/sessions
 * 4. Implement real POST /api/sessions/start
 * 5. Add form validation (min 1 strategy, min 1 symbol)
 * 6. Add loading states during API calls
 * 7. Add error handling and user feedback
 * 8. Remove all "MOCKUP" warnings
 * 9. Connect to TradingStore for session state
 * 10. Add redirect to dashboard after successful start
 *
 * Created: 2025-11-18
 * Purpose: Complete interface for session configuration with real controls
 */

import React, { useState } from 'react';
import {
  Box,
  Container,
  Paper,
  Typography,
  Button,
  ToggleButton,
  ToggleButtonGroup,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Checkbox,
  FormControlLabel,
  Chip,
  Alert,
  AlertTitle,
  Divider,
  Grid,
  Card,
  CardContent,
  CardHeader,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  Slider,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
} from '@mui/material';
import {
  PlayArrow as PlayArrowIcon,
  Stop as StopIcon,
  Settings as SettingsIcon,
  TrendingUp as TrendingUpIcon,
  AttachMoney as AttachMoneyIcon,
  Speed as SpeedIcon,
  Storage as StorageIcon,
  CheckCircle as CheckCircleIcon,
  Warning as WarningIcon,
  Delete as DeleteIcon,
} from '@mui/icons-material';
import { useRouter } from 'next/navigation';

// ============================================================================
// ⚠️ MOCKUP DATA - Replace with real API calls
// ============================================================================

// TODO: Replace with GET /api/strategies
const MOCK_STRATEGIES = [
  {
    id: 'pump_v2',
    name: 'Pump Detection v2',
    description: 'Detects rapid price increases using TWPA velocity',
    winRate: 68.5,
    avgProfit: 2.3,
    enabled: true,
    category: 'momentum'
  },
  {
    id: 'dump_v2',
    name: 'Dump Detection v2',
    description: 'Identifies sharp price drops for short positions',
    winRate: 72.1,
    avgProfit: 1.8,
    enabled: true,
    category: 'momentum'
  },
  {
    id: 'volume_surge',
    name: 'Volume Surge Strategy',
    description: 'Trades on abnormal volume spikes',
    winRate: 55.2,
    avgProfit: 3.1,
    enabled: false,
    category: 'volume'
  },
  {
    id: 'mean_reversion',
    name: 'Mean Reversion',
    description: 'Statistical mean reversion with Bollinger Bands',
    winRate: 61.3,
    avgProfit: 1.5,
    enabled: false,
    category: 'statistical'
  },
  {
    id: 'trend_following',
    name: 'Trend Following',
    description: 'Medium-term trend detection with EMA crossover',
    winRate: 59.7,
    avgProfit: 2.8,
    enabled: false,
    category: 'trend'
  },
  {
    id: 'arbitrage_simple',
    name: 'Simple Arbitrage',
    description: 'Cross-exchange price difference exploitation',
    winRate: 82.4,
    avgProfit: 0.8,
    enabled: false,
    category: 'arbitrage'
  },
];

// TODO: Replace with GET /api/exchange/symbols
const MOCK_SYMBOLS = [
  { symbol: 'BTC_USDT', name: 'Bitcoin', price: 50250, volume24h: 1250000000, change24h: 2.5 },
  { symbol: 'ETH_USDT', name: 'Ethereum', price: 3150, volume24h: 850000000, change24h: 3.2 },
  { symbol: 'BNB_USDT', name: 'Binance Coin', price: 425, volume24h: 320000000, change24h: -1.2 },
  { symbol: 'SOL_USDT', name: 'Solana', price: 125, volume24h: 280000000, change24h: 5.8 },
  { symbol: 'XRP_USDT', name: 'Ripple', price: 0.85, volume24h: 450000000, change24h: 1.5 },
  { symbol: 'ADA_USDT', name: 'Cardano', price: 0.52, volume24h: 180000000, change24h: -0.8 },
  { symbol: 'DOGE_USDT', name: 'Dogecoin', price: 0.12, volume24h: 320000000, change24h: 4.2 },
  { symbol: 'MATIC_USDT', name: 'Polygon', price: 1.15, volume24h: 150000000, change24h: 2.1 },
  { symbol: 'DOT_USDT', name: 'Polkadot', price: 8.50, volume24h: 120000000, change24h: -2.5 },
  { symbol: 'AVAX_USDT', name: 'Avalanche', price: 42, volume24h: 180000000, change24h: 3.8 },
];

// TODO: Replace with GET /api/data-collection/sessions
const MOCK_DATA_SESSIONS = [
  {
    id: 'session_20251118_120530',
    date: '2025-11-18 12:05:30',
    symbols: ['BTC_USDT', 'ETH_USDT'],
    duration: '2h 15m',
    records: 15420,
    status: 'completed'
  },
  {
    id: 'session_20251117_093245',
    date: '2025-11-17 09:32:45',
    symbols: ['BTC_USDT'],
    duration: '1h 30m',
    records: 8932,
    status: 'completed'
  },
  {
    id: 'session_20251116_184512',
    date: '2025-11-16 18:45:12',
    symbols: ['ETH_USDT', 'BNB_USDT', 'SOL_USDT'],
    duration: '3h 45m',
    records: 22103,
    status: 'completed'
  },
  {
    id: 'session_20251115_143022',
    date: '2025-11-15 14:30:22',
    symbols: ['BTC_USDT', 'ETH_USDT', 'ADA_USDT', 'XRP_USDT'],
    duration: '4h 20m',
    records: 31245,
    status: 'completed'
  },
];

// ============================================================================
// Main Component
// ============================================================================

type TradingMode = 'live' | 'paper' | 'backtest';

export default function TradingSessionPage() {
  const router = useRouter();

  // ⚠️ MOCKUP STATE - Real app would use Zustand stores
  const [mode, setMode] = useState<TradingMode>('paper');
  const [selectedStrategies, setSelectedStrategies] = useState<string[]>(['pump_v2', 'dump_v2']);
  const [selectedSymbols, setSelectedSymbols] = useState<string[]>(['BTC_USDT', 'ETH_USDT']);
  const [globalBudget, setGlobalBudget] = useState(1000);
  const [maxPositionSize, setMaxPositionSize] = useState(100);
  const [stopLoss, setStopLoss] = useState(5);
  const [takeProfit, setTakeProfit] = useState(10);
  const [backtestSessionId, setBacktestSessionId] = useState('session_20251118_120530');
  const [accelerationFactor, setAccelerationFactor] = useState(10);
  const [showAdvanced, setShowAdvanced] = useState(false);

  // Session status
  const [isSessionRunning, setIsSessionRunning] = useState(false);
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(null);

  // ========================================
  // Event Handlers
  // ========================================

  const handleStrategyToggle = (strategyId: string) => {
    setSelectedStrategies(prev =>
      prev.includes(strategyId)
        ? prev.filter(id => id !== strategyId)
        : [...prev, strategyId]
    );
  };

  const handleSymbolToggle = (symbol: string) => {
    setSelectedSymbols(prev =>
      prev.includes(symbol)
        ? prev.filter(s => s !== symbol)
        : [...prev, symbol]
    );
  };

  const handleStartSession = () => {
    // ⚠️ MOCKUP: Only logs to console - TODO: Implement real POST /api/sessions/start
    const sessionConfig = {
      mode,
      strategies: selectedStrategies,
      symbols: selectedSymbols,
      config: {
        global_budget: globalBudget,
        max_position_size: maxPositionSize,
        stop_loss_percent: stopLoss,
        take_profit_percent: takeProfit,
        ...(mode === 'backtest' && {
          session_id: backtestSessionId,
          acceleration_factor: accelerationFactor,
        }),
      },
    };

    console.log('⚠️ MOCKUP: Would start session with config:', sessionConfig);

    // Simulate session start
    setIsSessionRunning(true);
    setCurrentSessionId(`exec_${Date.now()}_mockup`);

    alert(`⚠️ MOCKUP MODE\n\nSession would start with:\n- Mode: ${mode}\n- Strategies: ${selectedStrategies.length}\n- Symbols: ${selectedSymbols.length}\n\nCheck console for full config.`);

    // TODO: Replace with:
    // const response = await apiService.startSession(sessionConfig);
    // router.push('/dashboard');
  };

  const handleStopSession = () => {
    // ⚠️ MOCKUP: Only stops local state - TODO: Implement real POST /api/sessions/stop
    console.log('⚠️ MOCKUP: Would stop session:', currentSessionId);

    setIsSessionRunning(false);
    setCurrentSessionId(null);

    // TODO: Replace with:
    // await apiService.stopSession(currentSessionId);
  };

  // Validation
  const canStart = selectedStrategies.length > 0 &&
                   selectedSymbols.length > 0 &&
                   (mode !== 'backtest' || backtestSessionId !== '');

  // ========================================
  // Render
  // ========================================

  return (
    <Container maxWidth="xl" sx={{ py: 4 }}>
      {/* ⚠️ MOCKUP WARNING BANNER */}
      <Alert severity="warning" sx={{ mb: 3 }}>
        <AlertTitle><strong>⚠️ MOCKUP INTERFACE - All Data is Artificial</strong></AlertTitle>
        This is a complete functional interface with MOCKUP data. All controls work, but selections
        are not sent to backend. See code comments (TODO) for implementation requirements.
      </Alert>

      {/* Header */}
      <Box sx={{ mb: 4 }}>
        <Typography variant="h4" gutterBottom sx={{ fontWeight: 'bold' }}>
          Configure Trading Session
        </Typography>
        <Typography variant="body1" color="text.secondary">
          Complete configuration interface for Live Trading, Paper Trading, and Backtesting
        </Typography>
      </Box>

      <Grid container spacing={3}>
        {/* LEFT COLUMN: Configuration */}
        <Grid item xs={12} lg={8}>
          {/* Mode Selection */}
          <Card sx={{ mb: 3 }}>
            <CardHeader
              title="1. Select Trading Mode"
              avatar={<SettingsIcon color="primary" />}
            />
            <CardContent>
              <ToggleButtonGroup
                value={mode}
                exclusive
                onChange={(_, newMode) => newMode && setMode(newMode)}
                fullWidth
                disabled={isSessionRunning}
              >
                <ToggleButton value="live" color="error">
                  🔴 Live Trading<br/>
                  <Typography variant="caption">(Real Money)</Typography>
                </ToggleButton>
                <ToggleButton value="paper" color="primary">
                  📝 Paper Trading<br/>
                  <Typography variant="caption">(Simulated)</Typography>
                </ToggleButton>
                <ToggleButton value="backtest">
                  ⏪ Backtest<br/>
                  <Typography variant="caption">(Historical)</Typography>
                </ToggleButton>
              </ToggleButtonGroup>

              {mode === 'live' && (
                <Alert severity="error" sx={{ mt: 2 }}>
                  <strong>WARNING: Real Money Trading</strong><br/>
                  Live mode uses real funds. Test strategies in paper mode first!
                </Alert>
              )}

              {mode === 'paper' && (
                <Alert severity="info" sx={{ mt: 2 }}>
                  Paper trading simulates real trading with virtual funds. Perfect for testing!
                </Alert>
              )}

              {mode === 'backtest' && (
                <Alert severity="info" sx={{ mt: 2 }}>
                  Backtest mode replays historical data to evaluate strategy performance.
                </Alert>
              )}
            </CardContent>
          </Card>

          {/* Backtest Session Selection */}
          {mode === 'backtest' && (
            <Card sx={{ mb: 3 }}>
              <CardHeader
                title="Historical Data Session"
                subheader="⚠️ MOCKUP DATA - TODO: Replace with GET /api/data-collection/sessions"
                avatar={<StorageIcon color="primary" />}
              />
              <CardContent>
                <FormControl fullWidth sx={{ mb: 2 }}>
                  <InputLabel>Data Collection Session</InputLabel>
                  <Select
                    value={backtestSessionId}
                    label="Data Collection Session"
                    onChange={(e) => setBacktestSessionId(e.target.value)}
                    disabled={isSessionRunning}
                  >
                    {MOCK_DATA_SESSIONS.map(session => (
                      <MenuItem key={session.id} value={session.id}>
                        {session.date} - {session.symbols.join(', ')} ({session.records.toLocaleString()} records)
                      </MenuItem>
                    ))}
                  </Select>
                </FormControl>

                <Typography variant="body2" gutterBottom>
                  Acceleration Factor: {accelerationFactor}x
                </Typography>
                <Slider
                  value={accelerationFactor}
                  onChange={(_, val) => setAccelerationFactor(val as number)}
                  min={1}
                  max={100}
                  marks={[
                    { value: 1, label: '1x' },
                    { value: 10, label: '10x' },
                    { value: 50, label: '50x' },
                    { value: 100, label: '100x' },
                  ]}
                  disabled={isSessionRunning}
                />
                <Typography variant="caption" color="text.secondary">
                  Higher acceleration = faster backtest, but may consume more resources
                </Typography>
              </CardContent>
            </Card>
          )}

          {/* Strategy Selection */}
          <Card sx={{ mb: 3 }}>
            <CardHeader
              title={`2. Select Strategies (${selectedStrategies.length} selected)`}
              subheader="⚠️ MOCKUP DATA - TODO: Replace with GET /api/strategies"
              avatar={<TrendingUpIcon color="primary" />}
            />
            <CardContent>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell padding="checkbox"></TableCell>
                    <TableCell>Strategy</TableCell>
                    <TableCell>Win Rate</TableCell>
                    <TableCell>Avg Profit</TableCell>
                    <TableCell>Status</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {MOCK_STRATEGIES.map(strategy => (
                    <TableRow
                      key={strategy.id}
                      sx={{
                        backgroundColor: selectedStrategies.includes(strategy.id) ? 'action.selected' : 'inherit',
                        cursor: 'pointer',
                      }}
                      onClick={() => !isSessionRunning && handleStrategyToggle(strategy.id)}
                    >
                      <TableCell padding="checkbox">
                        <Checkbox
                          checked={selectedStrategies.includes(strategy.id)}
                          disabled={isSessionRunning}
                        />
                      </TableCell>
                      <TableCell>
                        <Typography variant="body2" fontWeight="bold">{strategy.name}</Typography>
                        <Typography variant="caption" color="text.secondary">{strategy.description}</Typography>
                      </TableCell>
                      <TableCell>{strategy.winRate.toFixed(1)}%</TableCell>
                      <TableCell>+{strategy.avgProfit}%</TableCell>
                      <TableCell>
                        {strategy.enabled ? (
                          <Chip label="Active" size="small" color="success" />
                        ) : (
                          <Chip label="Inactive" size="small" />
                        )}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>

          {/* Symbol Selection */}
          <Card sx={{ mb: 3 }}>
            <CardHeader
              title={`3. Select Symbols (${selectedSymbols.length} selected)`}
              subheader="⚠️ MOCKUP DATA - TODO: Replace with GET /api/exchange/symbols"
              avatar={<AttachMoneyIcon color="primary" />}
            />
            <CardContent>
              <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1, mb: 2 }}>
                {MOCK_SYMBOLS.map(item => (
                  <Chip
                    key={item.symbol}
                    label={`${item.symbol} ($${item.price.toLocaleString()})`}
                    color={selectedSymbols.includes(item.symbol) ? 'primary' : 'default'}
                    onClick={() => !isSessionRunning && handleSymbolToggle(item.symbol)}
                    onDelete={selectedSymbols.includes(item.symbol) ? () => handleSymbolToggle(item.symbol) : undefined}
                    deleteIcon={<DeleteIcon />}
                    disabled={isSessionRunning}
                  />
                ))}
              </Box>

              <Stack direction="row" spacing={1}>
                <Button
                  size="small"
                  variant="outlined"
                  onClick={() => setSelectedSymbols(MOCK_SYMBOLS.slice(0, 3).map(s => s.symbol))}
                  disabled={isSessionRunning}
                >
                  Top 3
                </Button>
                <Button
                  size="small"
                  variant="outlined"
                  onClick={() => setSelectedSymbols([])}
                  disabled={isSessionRunning}
                >
                  Clear All
                </Button>
              </Stack>
            </CardContent>
          </Card>

          {/* Budget & Risk Management */}
          <Card sx={{ mb: 3 }}>
            <CardHeader
              title="4. Budget & Risk Management"
              subheader="⚠️ MOCKUP - Values not validated"
              avatar={<AttachMoneyIcon color="primary" />}
            />
            <CardContent>
              <Grid container spacing={2}>
                <Grid item xs={12} sm={6}>
                  <TextField
                    fullWidth
                    label="Global Budget (USDT)"
                    type="number"
                    value={globalBudget}
                    onChange={(e) => setGlobalBudget(Number(e.target.value))}
                    disabled={isSessionRunning}
                    helperText="Total capital available"
                  />
                </Grid>
                <Grid item xs={12} sm={6}>
                  <TextField
                    fullWidth
                    label="Max Position Size (USDT)"
                    type="number"
                    value={maxPositionSize}
                    onChange={(e) => setMaxPositionSize(Number(e.target.value))}
                    disabled={isSessionRunning}
                    helperText="Per position limit"
                  />
                </Grid>
                <Grid item xs={12} sm={6}>
                  <TextField
                    fullWidth
                    label="Stop Loss (%)"
                    type="number"
                    value={stopLoss}
                    onChange={(e) => setStopLoss(Number(e.target.value))}
                    disabled={isSessionRunning}
                    helperText="Auto stop loss"
                  />
                </Grid>
                <Grid item xs={12} sm={6}>
                  <TextField
                    fullWidth
                    label="Take Profit (%)"
                    type="number"
                    value={takeProfit}
                    onChange={(e) => setTakeProfit(Number(e.target.value))}
                    disabled={isSessionRunning}
                    helperText="Auto take profit"
                  />
                </Grid>
              </Grid>
            </CardContent>
          </Card>
        </Grid>

        {/* RIGHT COLUMN: Summary & Actions */}
        <Grid item xs={12} lg={4}>
          <Card sx={{ position: 'sticky', top: 80 }}>
            <CardHeader
              title="Session Summary"
              avatar={<CheckCircleIcon color="success" />}
            />
            <CardContent>
              <List dense>
                <ListItem>
                  <ListItemText
                    primary="Mode"
                    secondary={mode.toUpperCase()}
                  />
                </ListItem>
                <ListItem>
                  <ListItemText
                    primary="Strategies"
                    secondary={`${selectedStrategies.length} selected`}
                  />
                </ListItem>
                <ListItem>
                  <ListItemText
                    primary="Symbols"
                    secondary={`${selectedSymbols.length} selected`}
                  />
                </ListItem>
                <ListItem>
                  <ListItemText
                    primary="Budget"
                    secondary={`$${globalBudget} USDT`}
                  />
                </ListItem>
                <ListItem>
                  <ListItemText
                    primary="Max Position"
                    secondary={`$${maxPositionSize} USDT`}
                  />
                </ListItem>
                <ListItem>
                  <ListItemText
                    primary="Risk Controls"
                    secondary={`SL: ${stopLoss}% / TP: ${takeProfit}%`}
                  />
                </ListItem>
              </List>

              <Divider sx={{ my: 2 }} />

              {/* Validation Messages */}
              {!canStart && (
                <Alert severity="warning" sx={{ mb: 2 }}>
                  {selectedStrategies.length === 0 && 'Select at least 1 strategy\n'}
                  {selectedSymbols.length === 0 && 'Select at least 1 symbol\n'}
                  {mode === 'backtest' && !backtestSessionId && 'Select data session\n'}
                </Alert>
              )}

              {/* Action Buttons */}
              <Stack spacing={2}>
                {!isSessionRunning ? (
                  <Button
                    variant="contained"
                    color="primary"
                    size="large"
                    fullWidth
                    startIcon={<PlayArrowIcon />}
                    onClick={handleStartSession}
                    disabled={!canStart}
                  >
                    Start {mode.toUpperCase()} Session
                  </Button>
                ) : (
                  <Button
                    variant="contained"
                    color="error"
                    size="large"
                    fullWidth
                    startIcon={<StopIcon />}
                    onClick={handleStopSession}
                  >
                    Stop Session
                  </Button>
                )}

                <Button
                  variant="outlined"
                  size="large"
                  fullWidth
                  onClick={() => router.push('/dashboard')}
                >
                  Go to Dashboard
                </Button>
              </Stack>

              {isSessionRunning && (
                <Alert severity="success" sx={{ mt: 2 }}>
                  <Typography variant="body2" fontWeight="bold">
                    Session Running
                  </Typography>
                  <Typography variant="caption">
                    ID: {currentSessionId}
                  </Typography>
                </Alert>
              )}

              <Alert severity="warning" sx={{ mt: 2 }}>
                <Typography variant="caption">
                  ⚠️ MOCKUP: Button only logs to console and shows alert.
                  TODO: Implement POST /api/sessions/start
                </Typography>
              </Alert>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Container>
  );
}

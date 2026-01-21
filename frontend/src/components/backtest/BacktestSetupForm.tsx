/**
 * Backtest Setup Form Component
 * =============================
 * Story: 1b-1-backtest-session-setup
 *
 * Allows traders to configure and start a backtest session with:
 * - Strategy selection (AC1)
 * - Symbol selection (AC2)
 * - Date range selection (AC3)
 * - Data availability validation (AC4)
 * - Incomplete data warnings (AC5)
 * - Start button with redirect (AC6)
 * - Field validation errors (AC7)
 * - Disabled state until all fields filled (AC8)
 */

'use client';

import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { useRouter } from 'next/navigation';
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
  FormHelperText,
  Alert,
  AlertTitle,
  Divider,
  Grid,
  CircularProgress,
  Chip,
  LinearProgress,
  Tooltip,
  IconButton,
  Collapse,
} from '@mui/material';
import { DatePicker } from '@mui/x-date-pickers/DatePicker';
import { LocalizationProvider } from '@mui/x-date-pickers/LocalizationProvider';
import { AdapterDateFns } from '@mui/x-date-pickers/AdapterDateFns';
import {
  PlayArrow as PlayArrowIcon,
  Warning as WarningIcon,
  CheckCircle as CheckCircleIcon,
  Error as ErrorIcon,
  Refresh as RefreshIcon,
  Info as InfoIcon,
  ExpandMore as ExpandMoreIcon,
  ExpandLess as ExpandLessIcon,
} from '@mui/icons-material';
import { Logger } from '@/services/frontendLogService';
import {
  backtestApi,
  DataAvailabilityResponse,
  StrategyListItem,
  DataCollectionSession,
} from '@/services/backtestApi';
import { format, subDays, isValid, parseISO } from 'date-fns';

// =============================================================================
// Types
// =============================================================================

export interface BacktestSetupFormProps {
  onBacktestStarted?: (sessionId: string) => void;
  defaultStrategy?: string;
  defaultSymbol?: string;
  defaultStartDate?: Date;
  defaultEndDate?: Date;
}

interface FormState {
  strategyId: string;
  symbol: string;
  startDate: Date | null;
  endDate: Date | null;
  dataSessionId: string;
  accelerationFactor: number;
  initialBalance: number;
}

interface FormErrors {
  strategyId?: string;
  symbol?: string;
  startDate?: string;
  endDate?: string;
  dataSessionId?: string;
  general?: string;
}

// =============================================================================
// Component
// =============================================================================

export const BacktestSetupForm: React.FC<BacktestSetupFormProps> = ({
  onBacktestStarted,
  defaultStrategy = '',
  defaultSymbol = '',
  defaultStartDate,
  defaultEndDate,
}) => {
  const router = useRouter();

  // ---------------------------------------------------------------------------
  // Form State
  // ---------------------------------------------------------------------------
  const [formState, setFormState] = useState<FormState>({
    strategyId: defaultStrategy,
    symbol: defaultSymbol,
    startDate: defaultStartDate || subDays(new Date(), 7),
    endDate: defaultEndDate || new Date(),
    dataSessionId: '',
    accelerationFactor: 10,
    initialBalance: 10000,
  });

  const [errors, setErrors] = useState<FormErrors>({});
  const [touched, setTouched] = useState<Record<string, boolean>>({});

  // ---------------------------------------------------------------------------
  // Data Loading State
  // ---------------------------------------------------------------------------
  const [strategies, setStrategies] = useState<StrategyListItem[]>([]);
  const [symbols, setSymbols] = useState<string[]>([]);
  const [dataSessions, setDataSessions] = useState<DataCollectionSession[]>([]);

  const [loadingStrategies, setLoadingStrategies] = useState(false);
  const [loadingSymbols, setLoadingSymbols] = useState(false);
  const [loadingDataSessions, setLoadingDataSessions] = useState(false);

  // ---------------------------------------------------------------------------
  // Data Availability State
  // ---------------------------------------------------------------------------
  const [dataAvailability, setDataAvailability] = useState<DataAvailabilityResponse | null>(null);
  const [checkingAvailability, setCheckingAvailability] = useState(false);
  const [showDataDetails, setShowDataDetails] = useState(false);

  // ---------------------------------------------------------------------------
  // Submission State
  // ---------------------------------------------------------------------------
  const [isSubmitting, setIsSubmitting] = useState(false);

  // ---------------------------------------------------------------------------
  // Data Loading Effects
  // ---------------------------------------------------------------------------

  // Load strategies on mount
  useEffect(() => {
    const loadStrategies = async () => {
      setLoadingStrategies(true);
      try {
        const data = await backtestApi.getStrategies();
        setStrategies(data);
      } catch (error) {
        Logger.error('BacktestSetupForm.loadStrategies', { error });
        setErrors((prev) => ({
          ...prev,
          general: 'Failed to load strategies. Please try again.',
        }));
      } finally {
        setLoadingStrategies(false);
      }
    };

    loadStrategies();
  }, []);

  // Load symbols on mount
  useEffect(() => {
    const loadSymbols = async () => {
      setLoadingSymbols(true);
      try {
        const data = await backtestApi.getSymbols();
        setSymbols(data);
      } catch (error) {
        Logger.error('BacktestSetupForm.loadSymbols', { error });
      } finally {
        setLoadingSymbols(false);
      }
    };

    loadSymbols();
  }, []);

  // Load data collection sessions on mount
  useEffect(() => {
    const loadDataSessions = async () => {
      setLoadingDataSessions(true);
      try {
        const data = await backtestApi.getDataCollectionSessions();
        setDataSessions(data);
      } catch (error) {
        Logger.error('BacktestSetupForm.loadDataSessions', { error });
      } finally {
        setLoadingDataSessions(false);
      }
    };

    loadDataSessions();
  }, []);

  // ---------------------------------------------------------------------------
  // Data Availability Check
  // ---------------------------------------------------------------------------

  // Check data availability when symbol or dates change
  useEffect(() => {
    const checkAvailability = async () => {
      if (!formState.symbol || !formState.startDate || !formState.endDate) {
        setDataAvailability(null);
        return;
      }

      if (!isValid(formState.startDate) || !isValid(formState.endDate)) {
        return;
      }

      setCheckingAvailability(true);
      try {
        const result = await backtestApi.checkDataAvailability({
          symbol: formState.symbol,
          start_date: format(formState.startDate, 'yyyy-MM-dd'),
          end_date: format(formState.endDate, 'yyyy-MM-dd'),
        });
        setDataAvailability(result);
      } catch (error) {
        Logger.error('BacktestSetupForm.checkAvailability', { error });
        setDataAvailability(null);
      } finally {
        setCheckingAvailability(false);
      }
    };

    // Debounce the check
    const timeoutId = setTimeout(checkAvailability, 500);
    return () => clearTimeout(timeoutId);
  }, [formState.symbol, formState.startDate, formState.endDate]);

  // ---------------------------------------------------------------------------
  // Validation
  // ---------------------------------------------------------------------------

  const validateForm = useCallback((): FormErrors => {
    const newErrors: FormErrors = {};

    // AC7: Validation errors highlight missing fields
    if (!formState.strategyId) {
      newErrors.strategyId = 'Please select a strategy';
    }

    if (!formState.symbol) {
      newErrors.symbol = 'Please select a trading symbol';
    }

    if (!formState.startDate) {
      newErrors.startDate = 'Please select a start date';
    } else if (!isValid(formState.startDate)) {
      newErrors.startDate = 'Invalid start date';
    }

    if (!formState.endDate) {
      newErrors.endDate = 'Please select an end date';
    } else if (!isValid(formState.endDate)) {
      newErrors.endDate = 'Invalid end date';
    }

    // Validate date range
    if (formState.startDate && formState.endDate) {
      if (formState.startDate >= formState.endDate) {
        newErrors.endDate = 'End date must be after start date';
      }

      const daysDiff =
        (formState.endDate.getTime() - formState.startDate.getTime()) /
        (1000 * 60 * 60 * 24);
      if (daysDiff > 365) {
        newErrors.endDate = 'Date range cannot exceed 365 days';
      }

      if (formState.endDate > new Date()) {
        newErrors.endDate = 'End date cannot be in the future';
      }
    }

    return newErrors;
  }, [formState]);

  // Run validation whenever form state changes
  useEffect(() => {
    const newErrors = validateForm();
    setErrors(newErrors);
  }, [validateForm]);

  // ---------------------------------------------------------------------------
  // AC8: Start button disabled until all fields filled
  // ---------------------------------------------------------------------------

  const isFormValid = useMemo(() => {
    return (
      !!formState.strategyId &&
      !!formState.symbol &&
      formState.startDate !== null &&
      formState.endDate !== null &&
      isValid(formState.startDate) &&
      isValid(formState.endDate) &&
      Object.keys(validateForm()).length === 0
    );
  }, [formState, validateForm]);

  // ---------------------------------------------------------------------------
  // Event Handlers
  // ---------------------------------------------------------------------------

  const handleFieldChange = <K extends keyof FormState>(
    field: K,
    value: FormState[K]
  ) => {
    setFormState((prev) => ({ ...prev, [field]: value }));
    setTouched((prev) => ({ ...prev, [field]: true }));
  };

  const handleBlur = (field: string) => {
    setTouched((prev) => ({ ...prev, [field]: true }));
  };

  // AC6: "Start Backtest" button starts session and redirects to dashboard
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    // Mark all fields as touched
    setTouched({
      strategyId: true,
      symbol: true,
      startDate: true,
      endDate: true,
    });

    const validationErrors = validateForm();
    if (Object.keys(validationErrors).length > 0) {
      setErrors(validationErrors);
      return;
    }

    setIsSubmitting(true);
    setErrors({});

    try {
      const result = await backtestApi.startBacktest({
        strategy_id: formState.strategyId,
        symbol: formState.symbol,
        start_date: format(formState.startDate!, 'yyyy-MM-dd'),
        end_date: format(formState.endDate!, 'yyyy-MM-dd'),
        session_id: formState.dataSessionId || undefined,
        config: {
          acceleration_factor: formState.accelerationFactor,
          initial_balance: formState.initialBalance,
        },
      });

      Logger.info('BacktestSetupForm.backtestStarted', {
        session_id: result.session_id,
        strategy_id: formState.strategyId,
        symbol: formState.symbol,
      });

      // Callback if provided
      if (onBacktestStarted) {
        onBacktestStarted(result.session_id);
      }

      // Redirect to dashboard with session_id
      router.push(`/dashboard?mode=backtest&session_id=${result.session_id}`);
    } catch (error: any) {
      Logger.error('BacktestSetupForm.submitError', { error: error.message });
      setErrors({
        general: error.message || 'Failed to start backtest. Please try again.',
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  // ---------------------------------------------------------------------------
  // Render Helpers
  // ---------------------------------------------------------------------------

  const renderDataAvailabilityStatus = () => {
    if (checkingAvailability) {
      return (
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <CircularProgress size={20} />
          <Typography variant="body2" color="text.secondary">
            Checking data availability...
          </Typography>
        </Box>
      );
    }

    if (!dataAvailability) {
      return null;
    }

    // AC4 & AC5: Data availability validation and warnings
    const { data_quality, coverage_pct, total_records, quality_issues } = dataAvailability;

    return (
      <Box sx={{ mt: 2 }}>
        <Alert
          severity={
            data_quality === 'good'
              ? 'success'
              : data_quality === 'warning'
              ? 'warning'
              : 'error'
          }
          icon={
            data_quality === 'good' ? (
              <CheckCircleIcon />
            ) : data_quality === 'warning' ? (
              <WarningIcon />
            ) : (
              <ErrorIcon />
            )
          }
          action={
            <IconButton
              size="small"
              onClick={() => setShowDataDetails(!showDataDetails)}
            >
              {showDataDetails ? <ExpandLessIcon /> : <ExpandMoreIcon />}
            </IconButton>
          }
        >
          <AlertTitle>
            {data_quality === 'good'
              ? 'Data Available'
              : data_quality === 'warning'
              ? 'Data Partially Available'
              : 'Data Unavailable'}
          </AlertTitle>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
            <Chip
              label={`${coverage_pct.toFixed(1)}% Coverage`}
              size="small"
              color={
                coverage_pct >= 90 ? 'success' : coverage_pct >= 50 ? 'warning' : 'error'
              }
            />
            <Typography variant="body2">
              {total_records.toLocaleString()} records found
            </Typography>
          </Box>
        </Alert>

        <Collapse in={showDataDetails}>
          <Paper sx={{ p: 2, mt: 1, bgcolor: 'background.default' }}>
            <Typography variant="subtitle2" gutterBottom>
              Data Quality Details
            </Typography>

            <Box sx={{ mb: 2 }}>
              <Typography variant="caption" color="text.secondary">
                Coverage
              </Typography>
              <LinearProgress
                variant="determinate"
                value={coverage_pct}
                color={
                  coverage_pct >= 90
                    ? 'success'
                    : coverage_pct >= 50
                    ? 'warning'
                    : 'error'
                }
                sx={{ height: 8, borderRadius: 4, mt: 0.5 }}
              />
            </Box>

            {quality_issues.length > 0 && (
              <Box>
                <Typography variant="caption" color="text.secondary">
                  Issues:
                </Typography>
                <ul style={{ margin: '4px 0', paddingLeft: '20px' }}>
                  {quality_issues.map((issue, idx) => (
                    <li key={idx}>
                      <Typography variant="caption">{issue}</Typography>
                    </li>
                  ))}
                </ul>
              </Box>
            )}

            {dataAvailability.missing_ranges.length > 0 && (
              <Box sx={{ mt: 1 }}>
                <Typography variant="caption" color="text.secondary">
                  Missing Data Ranges:
                </Typography>
                <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5, mt: 0.5 }}>
                  {dataAvailability.missing_ranges.slice(0, 5).map((range, idx) => (
                    <Chip
                      key={idx}
                      label={`${range.start} - ${range.end} (${range.gap_hours}h gap)`}
                      size="small"
                      color="warning"
                      variant="outlined"
                    />
                  ))}
                  {dataAvailability.missing_ranges.length > 5 && (
                    <Chip
                      label={`+${dataAvailability.missing_ranges.length - 5} more`}
                      size="small"
                      variant="outlined"
                    />
                  )}
                </Box>
              </Box>
            )}
          </Paper>
        </Collapse>
      </Box>
    );
  };

  // ---------------------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------------------

  return (
    <LocalizationProvider dateAdapter={AdapterDateFns}>
      <Paper sx={{ p: 3, maxWidth: 800, mx: 'auto' }}>
        <Typography variant="h5" gutterBottom sx={{ fontWeight: 'bold' }}>
          Configure Backtest Session
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
          Set up a backtest to evaluate your trading strategy against historical data.
        </Typography>

        <Divider sx={{ mb: 3 }} />

        {/* General Error */}
        {errors.general && (
          <Alert severity="error" sx={{ mb: 3 }}>
            {errors.general}
          </Alert>
        )}

        <form onSubmit={handleSubmit}>
          <Grid container spacing={3}>
            {/* AC1: Strategy Selection */}
            <Grid item xs={12}>
              <FormControl
                fullWidth
                error={touched.strategyId && !!errors.strategyId}
              >
                <InputLabel id="strategy-select-label">
                  Trading Strategy *
                </InputLabel>
                <Select
                  labelId="strategy-select-label"
                  value={formState.strategyId}
                  label="Trading Strategy *"
                  onChange={(e) => handleFieldChange('strategyId', e.target.value)}
                  onBlur={() => handleBlur('strategyId')}
                  disabled={loadingStrategies}
                  startAdornment={
                    loadingStrategies ? (
                      <CircularProgress size={20} sx={{ mr: 1 }} />
                    ) : null
                  }
                >
                  {strategies.length === 0 && !loadingStrategies && (
                    <MenuItem disabled>
                      <Typography variant="body2" color="text.secondary">
                        No strategies available. Please create a strategy first.
                      </Typography>
                    </MenuItem>
                  )}
                  {strategies.map((strategy) => (
                    <MenuItem key={strategy.id} value={strategy.id}>
                      <Box>
                        <Typography variant="body1">
                          {strategy.strategy_name}
                        </Typography>
                        {strategy.description && (
                          <Typography variant="caption" color="text.secondary">
                            {strategy.description}
                          </Typography>
                        )}
                      </Box>
                    </MenuItem>
                  ))}
                </Select>
                {touched.strategyId && errors.strategyId && (
                  <FormHelperText error>{errors.strategyId}</FormHelperText>
                )}
              </FormControl>
            </Grid>

            {/* AC2: Symbol Selection */}
            <Grid item xs={12} md={6}>
              <FormControl
                fullWidth
                error={touched.symbol && !!errors.symbol}
              >
                <InputLabel id="symbol-select-label">Trading Symbol *</InputLabel>
                <Select
                  labelId="symbol-select-label"
                  value={formState.symbol}
                  label="Trading Symbol *"
                  onChange={(e) => handleFieldChange('symbol', e.target.value)}
                  onBlur={() => handleBlur('symbol')}
                  disabled={loadingSymbols}
                  startAdornment={
                    loadingSymbols ? (
                      <CircularProgress size={20} sx={{ mr: 1 }} />
                    ) : null
                  }
                >
                  {symbols.map((symbol) => (
                    <MenuItem key={symbol} value={symbol}>
                      {symbol}
                    </MenuItem>
                  ))}
                </Select>
                {touched.symbol && errors.symbol && (
                  <FormHelperText error>{errors.symbol}</FormHelperText>
                )}
              </FormControl>
            </Grid>

            {/* Data Collection Session (Optional) */}
            <Grid item xs={12} md={6}>
              <FormControl fullWidth>
                <InputLabel id="data-session-select-label">
                  Data Source (Optional)
                </InputLabel>
                <Select
                  labelId="data-session-select-label"
                  value={formState.dataSessionId}
                  label="Data Source (Optional)"
                  onChange={(e) => handleFieldChange('dataSessionId', e.target.value)}
                  disabled={loadingDataSessions}
                  startAdornment={
                    loadingDataSessions ? (
                      <CircularProgress size={20} sx={{ mr: 1 }} />
                    ) : null
                  }
                >
                  <MenuItem value="">
                    <em>Auto-detect from QuestDB</em>
                  </MenuItem>
                  {dataSessions.map((session) => (
                    <MenuItem key={session.session_id} value={session.session_id}>
                      <Box>
                        <Typography variant="body2">
                          {session.session_id}
                        </Typography>
                        <Typography variant="caption" color="text.secondary">
                          {session.symbols?.join(', ')} -{' '}
                          {(session.records_collected || 0).toLocaleString()} records
                        </Typography>
                      </Box>
                    </MenuItem>
                  ))}
                </Select>
                <FormHelperText>
                  Select a specific data collection session or let the system auto-detect
                </FormHelperText>
              </FormControl>
            </Grid>

            {/* AC3: Date Range Selection */}
            <Grid item xs={12} md={6}>
              <DatePicker
                label="Start Date *"
                value={formState.startDate}
                onChange={(date) => handleFieldChange('startDate', date)}
                maxDate={formState.endDate || new Date()}
                slotProps={{
                  textField: {
                    fullWidth: true,
                    error: touched.startDate && !!errors.startDate,
                    helperText: touched.startDate && errors.startDate,
                    onBlur: () => handleBlur('startDate'),
                  },
                }}
              />
            </Grid>

            <Grid item xs={12} md={6}>
              <DatePicker
                label="End Date *"
                value={formState.endDate}
                onChange={(date) => handleFieldChange('endDate', date)}
                minDate={formState.startDate || undefined}
                maxDate={new Date()}
                slotProps={{
                  textField: {
                    fullWidth: true,
                    error: touched.endDate && !!errors.endDate,
                    helperText: touched.endDate && errors.endDate,
                    onBlur: () => handleBlur('endDate'),
                  },
                }}
              />
            </Grid>

            {/* Data Availability Status */}
            <Grid item xs={12}>
              {renderDataAvailabilityStatus()}
            </Grid>

            {/* Advanced Options */}
            <Grid item xs={12}>
              <Divider sx={{ my: 1 }} />
              <Typography variant="subtitle2" sx={{ mb: 2 }}>
                Advanced Options
              </Typography>
            </Grid>

            <Grid item xs={12} md={6}>
              <TextField
                fullWidth
                label="Acceleration Factor"
                type="number"
                value={formState.accelerationFactor}
                onChange={(e) =>
                  handleFieldChange(
                    'accelerationFactor',
                    Math.max(1, Math.min(100, parseInt(e.target.value) || 1))
                  )
                }
                inputProps={{ min: 1, max: 100 }}
                helperText="Speed multiplier for backtest execution (1x - 100x)"
              />
            </Grid>

            <Grid item xs={12} md={6}>
              <TextField
                fullWidth
                label="Initial Balance (USDT)"
                type="number"
                value={formState.initialBalance}
                onChange={(e) =>
                  handleFieldChange(
                    'initialBalance',
                    Math.max(100, parseFloat(e.target.value) || 10000)
                  )
                }
                inputProps={{ min: 100 }}
                helperText="Starting capital for the backtest simulation"
              />
            </Grid>

            {/* Submit Button */}
            <Grid item xs={12}>
              <Divider sx={{ my: 2 }} />
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <Typography variant="caption" color="text.secondary">
                  * Required fields
                </Typography>
                <Button
                  type="submit"
                  variant="contained"
                  color="primary"
                  size="large"
                  disabled={!isFormValid || isSubmitting}
                  startIcon={
                    isSubmitting ? (
                      <CircularProgress size={20} color="inherit" />
                    ) : (
                      <PlayArrowIcon />
                    )
                  }
                  sx={{ minWidth: 200 }}
                >
                  {isSubmitting ? 'Starting Backtest...' : 'Start Backtest'}
                </Button>
              </Box>
            </Grid>

            {/* Helpful Info */}
            {!isFormValid && (
              <Grid item xs={12}>
                <Alert severity="info" icon={<InfoIcon />}>
                  <Typography variant="body2">
                    Please fill in all required fields to start the backtest.
                    {dataAvailability?.data_quality === 'error' &&
                      ' Note: Historical data may not be available for the selected configuration.'}
                  </Typography>
                </Alert>
              </Grid>
            )}
          </Grid>
        </form>
      </Paper>
    </LocalizationProvider>
  );
};

export default BacktestSetupForm;

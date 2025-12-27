'use client';

import React, { useState, useEffect, useMemo } from 'react';
import {
  Box,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Chip,
  Typography,
  Paper,
  Grid,
  Alert,
  CircularProgress,
  TextField,
  InputAdornment,
  IconButton,
  Tooltip,
  LinearProgress,
} from '@mui/material';
import { Logger } from '@/services/frontendLogService';
import {
  Search as SearchIcon,
  CheckCircle as CheckCircleIcon,
  Warning as WarningIcon,
  Error as ErrorIcon,
  Refresh as RefreshIcon,
  Storage as StorageIcon,
  Timeline as TimelineIcon,
  CalendarToday as CalendarIcon,
} from '@mui/icons-material';
import { apiService } from '@/services/api';

/**
 * SessionSelector Component
 *
 * ✅ FEATURE: Complete session selection with data preview and validation
 *
 * Features:
 * - Real-time session list from QuestDB (/api/data-collection/sessions)
 * - Session preview with statistics (records, symbols, duration)
 * - Quality validation (minimum records check, data completeness)
 * - Auto-refresh every 30 seconds
 * - Search/filter by session ID, symbols, or date
 * - Visual quality indicators (good/warning/error)
 *
 * Usage:
 *   <SessionSelector
 *     value={selectedSessionId}
 *     onChange={(sessionId) => setSelectedSessionId(sessionId)}
 *     requiredSymbols={['BTC_USDT', 'ETH_USDT']}
 *     minRecords={1000}
 *   />
 */

interface DataCollectionSession {
  session_id: string;
  symbols: string[];
  status: string;
  start_time?: string;
  end_time?: string;
  records_collected?: number;
  prices_count?: number;
  orderbook_count?: number;
  duration_seconds?: number;
  created_at: string;
}

interface SessionSelectorProps {
  value: string;
  onChange: (sessionId: string) => void;
  requiredSymbols?: string[];
  minRecords?: number;
  autoRefresh?: boolean;
  refreshInterval?: number;
  error?: boolean;
  helperText?: string;
  disabled?: boolean;
}

export const SessionSelector: React.FC<SessionSelectorProps> = ({
  value,
  onChange,
  requiredSymbols = [],
  minRecords = 100,
  autoRefresh = true,
  refreshInterval = 30000, // 30 seconds
  error = false,
  helperText,
  disabled = false,
}) => {
  const [sessions, setSessions] = useState<DataCollectionSession[]>([]);
  const [loading, setLoading] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');

  // Load sessions from API
  const loadSessions = async () => {
    setLoading(true);
    setLoadError(null);

    try {
      const response = await apiService.getDataCollectionSessions(50, true);
      const sessionsList = response?.sessions || [];

      // Filter only completed sessions (valid for backtest)
      const completedSessions = sessionsList.filter((s: DataCollectionSession) =>
        s.status === 'completed' && (s.records_collected || 0) > 0
      );

      setSessions(completedSessions);
    } catch (err: any) {
      Logger.error('SessionSelector.loadSessions', { message: 'Failed to load data collection sessions', error: err });
      setLoadError(err.message || 'Failed to load sessions');
      setSessions([]);
    } finally {
      setLoading(false);
    }
  };

  // Initial load
  useEffect(() => {
    loadSessions();
  }, []);

  // Auto-refresh
  useEffect(() => {
    if (!autoRefresh) return;

    const interval = setInterval(() => {
      loadSessions();
    }, refreshInterval);

    return () => clearInterval(interval);
  }, [autoRefresh, refreshInterval]);

  // Filter sessions by search term
  const filteredSessions = useMemo(() => {
    if (!searchTerm) return sessions;

    const term = searchTerm.toLowerCase();
    return sessions.filter((session) => {
      // Search by session_id
      if (session.session_id.toLowerCase().includes(term)) return true;

      // Search by symbols
      if (session.symbols?.some(s => s.toLowerCase().includes(term))) return true;

      // Search by date
      if (session.start_time?.includes(term) || session.created_at?.includes(term)) return true;

      return false;
    });
  }, [sessions, searchTerm]);

  // Get selected session details
  const selectedSession = useMemo(() => {
    return sessions.find(s => s.session_id === value);
  }, [sessions, value]);

  // Validate session quality
  const validateSession = (session: DataCollectionSession): {
    isValid: boolean;
    quality: 'good' | 'warning' | 'error';
    issues: string[];
  } => {
    const issues: string[] = [];
    let quality: 'good' | 'warning' | 'error' = 'good';

    // Check minimum records
    const recordCount = session.records_collected || session.prices_count || 0;
    if (recordCount < minRecords) {
      issues.push(`Low record count: ${recordCount} (minimum: ${minRecords})`);
      quality = 'error';
    } else if (recordCount < minRecords * 2) {
      issues.push(`Warning: Only ${recordCount} records (recommended: ${minRecords * 2}+)`);
      quality = 'warning';
    }

    // Check required symbols
    if (requiredSymbols.length > 0) {
      const missingSymbols = requiredSymbols.filter(
        reqSymbol => !session.symbols?.includes(reqSymbol)
      );

      if (missingSymbols.length > 0) {
        issues.push(`Missing symbols: ${missingSymbols.join(', ')}`);
        quality = 'warning';
      }
    }

    // Check if session is too old (> 30 days)
    if (session.created_at) {
      const ageInDays = (Date.now() - new Date(session.created_at).getTime()) / (1000 * 60 * 60 * 24);
      if (ageInDays > 30) {
        issues.push(`Session is ${Math.floor(ageInDays)} days old`);
        quality = quality === 'error' ? 'error' : 'warning';
      }
    }

    return {
      isValid: quality !== 'error',
      quality,
      issues,
    };
  };

  // Get quality indicator icon
  const getQualityIcon = (quality: 'good' | 'warning' | 'error') => {
    switch (quality) {
      case 'good':
        return <CheckCircleIcon color="success" fontSize="small" />;
      case 'warning':
        return <WarningIcon color="warning" fontSize="small" />;
      case 'error':
        return <ErrorIcon color="error" fontSize="small" />;
    }
  };

  return (
    <Box>
      {/* Session Selector */}
      <FormControl fullWidth error={error} disabled={disabled}>
        <InputLabel>Data Collection Session (Historical Data Source)</InputLabel>
        <Select
          value={value}
          label="Data Collection Session (Historical Data Source)"
          onChange={(e) => onChange(e.target.value)}
          renderValue={(selected) => {
            const session = sessions.find(s => s.session_id === selected);
            if (!session) return selected || 'Select a session';

            const validation = validateSession(session);
            return (
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                {getQualityIcon(validation.quality)}
                <Typography variant="body2">
                  {session.session_id}
                </Typography>
                <Chip
                  label={`${(session.records_collected || 0).toLocaleString()} records`}
                  size="small"
                  color="primary"
                  variant="outlined"
                />
              </Box>
            );
          }}
        >
          {/* Search field */}
          <Box sx={{ p: 1, position: 'sticky', top: 0, bgcolor: 'background.paper', zIndex: 1, borderBottom: 1, borderColor: 'divider' }}>
            <TextField
              fullWidth
              size="small"
              placeholder="Search by session ID, symbols, or date..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              onClick={(e) => e.stopPropagation()}
              InputProps={{
                startAdornment: (
                  <InputAdornment position="start">
                    <SearchIcon fontSize="small" />
                  </InputAdornment>
                ),
                endAdornment: loading ? (
                  <InputAdornment position="end">
                    <CircularProgress size={20} />
                  </InputAdornment>
                ) : (
                  <InputAdornment position="end">
                    <Tooltip title="Refresh sessions">
                      <IconButton size="small" onClick={(e) => { e.stopPropagation(); loadSessions(); }}>
                        <RefreshIcon fontSize="small" />
                      </IconButton>
                    </Tooltip>
                  </InputAdornment>
                ),
              }}
            />
          </Box>

          {/* Loading state */}
          {loading && sessions.length === 0 && (
            <MenuItem disabled>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, width: '100%', justifyContent: 'center', py: 2 }}>
                <CircularProgress size={20} />
                <Typography variant="body2" color="text.secondary">
                  Loading sessions...
                </Typography>
              </Box>
            </MenuItem>
          )}

          {/* Error state */}
          {loadError && (
            <MenuItem disabled>
              <Alert severity="error" sx={{ width: '100%' }}>
                {loadError}
              </Alert>
            </MenuItem>
          )}

          {/* Empty state */}
          {!loading && !loadError && filteredSessions.length === 0 && (
            <MenuItem disabled>
              <Typography variant="body2" color="text.secondary">
                {searchTerm
                  ? `No sessions match "${searchTerm}"`
                  : 'No data collection sessions available. Please collect data first.'}
              </Typography>
            </MenuItem>
          )}

          {/* Session list */}
          {filteredSessions.map((session) => {
            const validation = validateSession(session);

            return (
              <MenuItem key={session.session_id} value={session.session_id}>
                <Box sx={{ width: '100%' }}>
                  {/* Header */}
                  <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 0.5 }}>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      {getQualityIcon(validation.quality)}
                      <Typography variant="body2" fontWeight="bold">
                        {session.session_id}
                      </Typography>
                    </Box>
                    <Chip
                      label={session.status}
                      size="small"
                      color="success"
                      variant="outlined"
                    />
                  </Box>

                  {/* Stats */}
                  <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap', mb: 0.5 }}>
                    <Chip
                      icon={<StorageIcon />}
                      label={`${(session.records_collected || 0).toLocaleString()} records`}
                      size="small"
                      variant="outlined"
                    />
                    <Chip
                      icon={<TimelineIcon />}
                      label={`${session.symbols?.length || 0} symbols`}
                      size="small"
                      variant="outlined"
                    />
                    {session.duration_seconds && (
                      <Chip
                        icon={<CalendarIcon />}
                        label={`${Math.floor(session.duration_seconds / 60)}min`}
                        size="small"
                        variant="outlined"
                      />
                    )}
                  </Box>

                  {/* Symbols */}
                  <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap', mb: 0.5 }}>
                    {session.symbols?.slice(0, 5).map(symbol => (
                      <Chip key={symbol} label={symbol} size="small" />
                    ))}
                    {session.symbols && session.symbols.length > 5 && (
                      <Chip label={`+${session.symbols.length - 5} more`} size="small" variant="outlined" />
                    )}
                  </Box>

                  {/* Date */}
                  <Typography variant="caption" color="text.secondary">
                    {session.start_time
                      ? new Date(session.start_time).toLocaleString()
                      : new Date(session.created_at).toLocaleString()}
                  </Typography>

                  {/* Validation issues */}
                  {validation.issues.length > 0 && (
                    <Alert severity={validation.quality === 'error' ? 'error' : 'warning'} sx={{ mt: 1 }}>
                      <Typography variant="caption">
                        {validation.issues.join('; ')}
                      </Typography>
                    </Alert>
                  )}
                </Box>
              </MenuItem>
            );
          })}
        </Select>

        {/* Helper text */}
        {helperText && (
          <Typography variant="caption" color="text.secondary" sx={{ mt: 0.5, display: 'block' }}>
            {helperText}
          </Typography>
        )}
      </FormControl>

      {/* Selected Session Preview */}
      {selectedSession && (
        <Paper sx={{ p: 2, mt: 2, bgcolor: 'background.default' }}>
          <Typography variant="subtitle2" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <StorageIcon fontSize="small" />
            Selected Session Preview
          </Typography>

          <Grid container spacing={2}>
            <Grid item xs={12} sm={6}>
              <Box>
                <Typography variant="caption" color="text.secondary">
                  Session ID:
                </Typography>
                <Typography variant="body2" fontFamily="monospace" fontSize="0.85rem">
                  {selectedSession.session_id}
                </Typography>
              </Box>
            </Grid>

            <Grid item xs={12} sm={6}>
              <Box>
                <Typography variant="caption" color="text.secondary">
                  Status:
                </Typography>
                <Box sx={{ mt: 0.5 }}>
                  <Chip label={selectedSession.status} size="small" color="success" />
                </Box>
              </Box>
            </Grid>

            <Grid item xs={12} sm={6}>
              <Box>
                <Typography variant="caption" color="text.secondary">
                  Total Records:
                </Typography>
                <Typography variant="body2" fontWeight="bold">
                  {(selectedSession.records_collected || 0).toLocaleString()}
                </Typography>
              </Box>
            </Grid>

            <Grid item xs={12} sm={6}>
              <Box>
                <Typography variant="caption" color="text.secondary">
                  Duration:
                </Typography>
                <Typography variant="body2">
                  {selectedSession.duration_seconds
                    ? `${Math.floor(selectedSession.duration_seconds / 60)} minutes`
                    : 'N/A'}
                </Typography>
              </Box>
            </Grid>

            <Grid item xs={12}>
              <Box>
                <Typography variant="caption" color="text.secondary" gutterBottom>
                  Symbols ({selectedSession.symbols?.length || 0}):
                </Typography>
                <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap', mt: 0.5 }}>
                  {selectedSession.symbols?.map(symbol => (
                    <Chip key={symbol} label={symbol} size="small" />
                  ))}
                </Box>
              </Box>
            </Grid>

            <Grid item xs={12}>
              <Box>
                <Typography variant="caption" color="text.secondary">
                  Collection Date:
                </Typography>
                <Typography variant="body2">
                  {selectedSession.start_time
                    ? new Date(selectedSession.start_time).toLocaleString()
                    : new Date(selectedSession.created_at).toLocaleString()}
                </Typography>
              </Box>
            </Grid>

            {/* Validation summary */}
            {(() => {
              const validation = validateSession(selectedSession);
              return validation.issues.length > 0 ? (
                <Grid item xs={12}>
                  <Alert severity={validation.quality === 'error' ? 'error' : 'warning'}>
                    <Typography variant="caption" component="div">
                      <strong>Quality Issues:</strong>
                      <ul style={{ margin: '4px 0', paddingLeft: '20px' }}>
                        {validation.issues.map((issue, idx) => (
                          <li key={idx}>{issue}</li>
                        ))}
                      </ul>
                    </Typography>
                  </Alert>
                </Grid>
              ) : (
                <Grid item xs={12}>
                  <Alert severity="success">
                    <Typography variant="caption">
                      ✓ Session data quality is good. Ready for backtesting.
                    </Typography>
                  </Alert>
                </Grid>
              );
            })()}
          </Grid>
        </Paper>
      )}

      {/* No session selected */}
      {!selectedSession && value && (
        <Alert severity="warning" sx={{ mt: 2 }}>
          <Typography variant="body2">
            Selected session "{value}" not found. It may have been deleted.
          </Typography>
        </Alert>
      )}

      {/* Instructions */}
      {!value && (
        <Alert severity="info" sx={{ mt: 2 }}>
          <Typography variant="body2">
            <strong>Select a data collection session</strong> to use as historical data source for backtesting.
            <br />
            Sessions must have at least {minRecords.toLocaleString()} records to be valid.
          </Typography>
        </Alert>
      )}
    </Box>
  );
};

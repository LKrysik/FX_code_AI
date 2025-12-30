'use client';

/**
 * Connection Status Indicator Component
 * =====================================
 * Story 0-6: Provides always-visible WebSocket connection status
 * with click-to-expand details popover.
 *
 * AC1: Always visible in header/navbar
 * AC2: Green = connected, Yellow = reconnecting, Red = disconnected
 * AC3: Click shows connection details (last message time; latency requires future ping/pong impl)
 * AC4: Updates within 2 seconds of connection change
 * AC5: Shows "disabled" state when WebSocket intentionally off
 *
 * SEC-0-3: Added state sync status display and Force Sync button
 */

import React, { useState, useEffect, useRef } from 'react';
import {
  Box,
  Chip,
  Popover,
  Typography,
  List,
  ListItem,
  ListItemText,
  Button,
  Divider,
  keyframes,
  CircularProgress,
} from '@mui/material';
import {
  FiberManualRecord as DotIcon,
  Refresh as RefreshIcon,
  Warning as WarningIcon,
  Sync as SyncIcon,
} from '@mui/icons-material';
import { useWebSocketConnection, useWebSocketStore } from '@/stores/websocketStore';
import { wsService } from '@/services/websocket';

// Pulsing animation for connecting state
const pulse = keyframes`
  0% { opacity: 1; }
  50% { opacity: 0.4; }
  100% { opacity: 1; }
`;

interface ConnectionDetails {
  status: string;
  latency: number | null;
  lastMessageTime: number | null;
  url: string;
  reconnectAttempts: number;
}

export function ConnectionStatusIndicator() {
  const { isConnected, connectionStatus, reconnectAttempts, maxReconnectAttempts, nextRetryAt } = useWebSocketConnection();
  // SEC-0-3: Track sync status
  const syncStatus = useWebSocketStore(state => state.syncStatus);
  const lastSyncTime = useWebSocketStore(state => state.lastSyncTime);
  const [isSyncing, setIsSyncing] = useState(false);
  const [anchorEl, setAnchorEl] = useState<HTMLElement | null>(null);
  // BUG-008-3: Countdown timer state (AC2)
  const [countdown, setCountdown] = useState<number | null>(null);
  const [details, setDetails] = useState<ConnectionDetails>({
    status: connectionStatus,
    latency: null,
    lastMessageTime: null,
    url: 'ws://***:8000/ws',
    reconnectAttempts: 0,
  });

  // BUG-008-3: Update countdown timer every second (AC2)
  useEffect(() => {
    if (nextRetryAt && connectionStatus === 'reconnecting') {
      const updateCountdown = () => {
        const remaining = Math.max(0, Math.ceil((nextRetryAt - Date.now()) / 1000));
        setCountdown(remaining);
      };
      updateCountdown();
      const interval = setInterval(updateCountdown, 1000);
      return () => clearInterval(interval);
    } else {
      setCountdown(null);
    }
  }, [nextRetryAt, connectionStatus]);

  // Track last message time
  const lastMessageRef = useRef<number | null>(null);

  // Update details when connection status changes (AC4: within 2 seconds)
  useEffect(() => {
    setDetails(prev => ({
      ...prev,
      status: connectionStatus,
    }));
  }, [connectionStatus]);

  // Track last message time on connection
  // Note: Real latency measurement requires ping/pong implementation (future enhancement)
  useEffect(() => {
    if (isConnected) {
      lastMessageRef.current = Date.now();
      setDetails(prev => ({
        ...prev,
        lastMessageTime: Date.now(),
        // Latency intentionally not set - would require ping/pong measurement
      }));
    }
  }, [isConnected]);

  // Get color based on status (AC2)
  const getStatusColor = (): string => {
    switch (connectionStatus) {
      case 'connected':
        return '#10B981'; // Green
      case 'connecting':
        return '#F59E0B'; // Yellow/Amber
      case 'reconnecting':
        return '#F59E0B'; // Yellow/Amber (BUG-008-3)
      case 'slow':
        return '#F59E0B'; // Yellow/Amber
      case 'disconnected':
        return '#EF4444'; // Red
      case 'error':
        return '#EF4444'; // Red
      case 'disabled':
        return '#6B7280'; // Gray
      default:
        return '#6B7280';
    }
  };

  // Get label based on status
  const getStatusLabel = (): string => {
    switch (connectionStatus) {
      case 'connected':
        return 'Connected';
      case 'connecting':
        return 'Connecting...';
      case 'reconnecting':
        // BUG-008-3: Show attempt count and countdown (AC2)
        const countdownText = countdown !== null && countdown > 0 ? ` (${countdown}s)` : '';
        return `Reconnecting ${reconnectAttempts}/${maxReconnectAttempts}${countdownText}`;
      case 'slow':
        return 'Slow Connection';
      case 'disconnected':
        return 'Disconnected';
      case 'error':
        return 'Error';
      case 'disabled':
        return 'Disabled';
      default:
        return 'Unknown';
    }
  };

  // Get chip color for MUI
  const getChipColor = (): 'success' | 'warning' | 'error' | 'default' => {
    switch (connectionStatus) {
      case 'connected':
        return 'success';
      case 'connecting':
      case 'reconnecting': // BUG-008-3
      case 'slow':
        return 'warning';
      case 'disconnected':
      case 'error':
        return 'error';
      case 'disabled':
      default:
        return 'default';
    }
  };

  // Handle popover open/close (AC3)
  const handleClick = (event: React.MouseEvent<HTMLElement>) => {
    setAnchorEl(event.currentTarget);
  };

  const handleClose = () => {
    setAnchorEl(null);
  };

  // Manual reconnect handler
  const handleReconnect = () => {
    handleClose();
    // Trigger reconnect - in real implementation, use wsService.reconnect()
    window.location.reload();
  };

  // SEC-0-3: Force sync handler
  const handleForceSync = async () => {
    setIsSyncing(true);
    try {
      await wsService.forceStateSync();
    } finally {
      setIsSyncing(false);
    }
  };

  // SEC-0-3: Format last sync time
  const formatLastSync = () => {
    if (!lastSyncTime) return 'Never';
    const diff = Date.now() - new Date(lastSyncTime).getTime();
    if (diff < 1000) return 'Just now';
    if (diff < 60000) return `${Math.floor(diff / 1000)}s ago`;
    if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`;
    return new Date(lastSyncTime).toLocaleTimeString();
  };

  // SEC-0-3: Get sync status display
  const getSyncStatusDisplay = () => {
    switch (syncStatus) {
      case 'syncing':
        return { label: 'Syncing...', color: '#F59E0B' };
      case 'synced':
        return { label: 'Synced', color: '#10B981' };
      case 'failed':
        return { label: 'Sync Failed', color: '#EF4444' };
      default:
        return { label: 'Not synced', color: '#6B7280' };
    }
  };

  const open = Boolean(anchorEl);
  const id = open ? 'connection-status-popover' : undefined;

  // Format last message time
  const formatLastMessage = () => {
    if (!details.lastMessageTime) return 'N/A';
    const diff = Date.now() - details.lastMessageTime;
    if (diff < 1000) return 'Just now';
    if (diff < 60000) return `${Math.floor(diff / 1000)}s ago`;
    if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`;
    return new Date(details.lastMessageTime).toLocaleTimeString();
  };

  return (
    <>
      {/* AC1: Always visible indicator */}
      <Chip
        aria-describedby={id}
        icon={
          <DotIcon
            sx={{
              fontSize: 12,
              color: getStatusColor(),
              // BUG-008-3: Pulse animation for connecting and reconnecting
              animation: (connectionStatus === 'connecting' || connectionStatus === 'reconnecting')
                ? `${pulse} 1.5s ease-in-out infinite`
                : 'none',
            }}
          />
        }
        label={getStatusLabel()}
        size="small"
        color={getChipColor()}
        variant="outlined"
        onClick={handleClick}
        sx={{
          cursor: 'pointer',
          fontSize: '0.75rem',
          // BUG-008-3: Mobile responsive - prevent label overflow
          maxWidth: { xs: 150, sm: 200, md: 'none' },
          '& .MuiChip-label': {
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            whiteSpace: 'nowrap',
          },
          '&:hover': {
            backgroundColor: 'action.hover',
          },
        }}
      />

      {/* AC3: Connection details popover */}
      <Popover
        id={id}
        open={open}
        anchorEl={anchorEl}
        onClose={handleClose}
        anchorOrigin={{
          vertical: 'bottom',
          horizontal: 'right',
        }}
        transformOrigin={{
          vertical: 'top',
          horizontal: 'right',
        }}
      >
        {/* BUG-008-3: Mobile responsive popover */}
        <Box sx={{ p: 2, minWidth: { xs: 220, sm: 250 }, maxWidth: { xs: 280, sm: 320 } }}>
          <Typography variant="subtitle2" sx={{ fontWeight: 'bold', mb: 1 }}>
            Connection Status
          </Typography>
          <Divider sx={{ mb: 1 }} />

          <List dense disablePadding>
            <ListItem disableGutters>
              <ListItemText
                primary="Status"
                secondary={
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                    <DotIcon sx={{ fontSize: 12, color: getStatusColor() }} />
                    <span>{getStatusLabel()}</span>
                  </Box>
                }
              />
            </ListItem>

            <ListItem disableGutters>
              <ListItemText
                primary="Latency"
                secondary={details.latency ? `${details.latency}ms` : 'Not measured'}
              />
            </ListItem>

            <ListItem disableGutters>
              <ListItemText
                primary="Last Message"
                secondary={formatLastMessage()}
              />
            </ListItem>

            <ListItem disableGutters>
              <ListItemText
                primary="WebSocket URL"
                secondary={details.url}
              />
            </ListItem>

            {/* SEC-0-3: State sync status */}
            <ListItem disableGutters>
              <ListItemText
                primary="State Sync"
                secondary={
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                    <DotIcon sx={{ fontSize: 12, color: getSyncStatusDisplay().color }} />
                    <span>{getSyncStatusDisplay().label}</span>
                  </Box>
                }
              />
            </ListItem>

            <ListItem disableGutters>
              <ListItemText
                primary="Last Synced"
                secondary={formatLastSync()}
              />
            </ListItem>

            {/* BUG-008-3: Reconnection progress details (AC2) */}
            {connectionStatus === 'reconnecting' && (
              <>
                <ListItem disableGutters>
                  <ListItemText
                    primary="Reconnect Attempt"
                    secondary={`${reconnectAttempts} of ${maxReconnectAttempts}`}
                  />
                </ListItem>
                {countdown !== null && countdown > 0 && (
                  <ListItem disableGutters>
                    <ListItemText
                      primary="Next Retry In"
                      secondary={`${countdown} seconds`}
                    />
                  </ListItem>
                )}
              </>
            )}
          </List>

          {/* BUG-008-3: Reconnecting progress bar (AC2) */}
          {connectionStatus === 'reconnecting' && (
            <Box sx={{ mt: 1, p: 1, bgcolor: 'warning.light', borderRadius: 1 }}>
              <Typography variant="caption" sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                <RefreshIcon sx={{ fontSize: 14, animation: 'spin 1s linear infinite', '@keyframes spin': { from: { transform: 'rotate(0deg)' }, to: { transform: 'rotate(360deg)' } } }} />
                Attempting to reconnect... ({reconnectAttempts}/{maxReconnectAttempts})
              </Typography>
            </Box>
          )}

          {/* Show warning for non-connected states (but not when reconnecting, as it has its own message) */}
          {connectionStatus !== 'connected' && connectionStatus !== 'disabled' && connectionStatus !== 'reconnecting' && (
            <Box sx={{ mt: 1, p: 1, bgcolor: 'warning.light', borderRadius: 1 }}>
              <Typography variant="caption" sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                <WarningIcon sx={{ fontSize: 14 }} />
                Real-time data may be stale
              </Typography>
            </Box>
          )}

          {/* AC5: Disabled state message */}
          {connectionStatus === 'disabled' && (
            <Box sx={{ mt: 1, p: 1, bgcolor: 'grey.100', borderRadius: 1 }}>
              <Typography variant="caption">
                WebSocket is intentionally disabled
              </Typography>
            </Box>
          )}

          {/* Reconnect button for non-connected states */}
          {!isConnected && connectionStatus !== 'disabled' && (
            <Button
              fullWidth
              size="small"
              variant="outlined"
              startIcon={<RefreshIcon />}
              onClick={handleReconnect}
              sx={{ mt: 2 }}
            >
              Reconnect Now
            </Button>
          )}

          {/* SEC-0-3: Force Sync button (Task 4.4) */}
          {isConnected && (
            <Button
              fullWidth
              size="small"
              variant="outlined"
              color={syncStatus === 'failed' ? 'error' : 'primary'}
              startIcon={isSyncing ? <CircularProgress size={16} /> : <SyncIcon />}
              onClick={handleForceSync}
              disabled={isSyncing}
              sx={{ mt: 2 }}
            >
              {isSyncing ? 'Syncing...' : 'Force Sync'}
            </Button>
          )}
        </Box>
      </Popover>
    </>
  );
}

export default ConnectionStatusIndicator;

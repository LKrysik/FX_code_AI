'use client';

import React, { useEffect, useState, useCallback } from 'react';
import { useVisibilityAwareInterval } from '@/hooks/useVisibilityAwareInterval';
import {
  Box,
  Chip,
  Tooltip,
  CircularProgress,
  Typography,
  Alert,
} from '@mui/material';
import {
  Wifi as WifiIcon,
  WifiOff as WifiOffIcon,
  CloudOff as CloudOffIcon,
  CheckCircle as CheckCircleIcon,
  Error as ErrorIcon,
  Warning as WarningIcon,
} from '@mui/icons-material';
import { apiService } from '@/services/api';
import { wsService } from '@/services/websocket';
import { useWebSocketStore } from '@/stores/websocketStore';
import { useHealthStore } from '@/stores/healthStore';
import { useSmartCache } from '@/hooks/useSmartCache';
import { debugLog, errorLog, config } from '@/utils/config';
import {
  SystemStatusType,
  WebSocketStatusType,
  OverallStatusType,
  getOverallStatusColor,
  getOverallStatusIcon,
  getOverallStatusText,
  getWebSocketStatusColor,
  getWebSocketStatusIcon,
  getWebSocketStatusText,
  getBackendStatusColor,
  getBackendStatusText,
} from '@/utils/statusUtils';

export interface SystemStatus {
  backend: SystemStatusType;
  websocket: WebSocketStatusType;
  readOnlyMode: boolean;
  lastChecked: number;
  highLoad?: boolean;
}

// Re-export for backward compatibility
export type { SystemStatusType, WebSocketStatusType, OverallStatusType };
export {
  getOverallStatusColor as getStatusColor,
  getOverallStatusIcon as getStatusIcon,
  getOverallStatusText as getStatusText,
  getWebSocketStatusColor,
  getWebSocketStatusIcon,
  getBackendStatusColor,
  getBackendStatusText,
};

// Unified Status Chip Component
export interface StatusChipProps {
  status: OverallStatusType | WebSocketStatusType | SystemStatusType;
  type: 'overall' | 'websocket' | 'backend';
  size?: 'small' | 'medium';
  showIcon?: boolean;
  compact?: boolean;
}

export const StatusChip: React.FC<StatusChipProps> = ({
  status,
  type,
  size = 'small',
  showIcon = true,
  compact = false
}) => {
  let color: 'success' | 'warning' | 'error' | 'default';
  let icon: React.ReactNode;
  let label: string;

  switch (type) {
    case 'overall':
      color = getStatusColor(status as OverallStatusType);
      icon = showIcon ? getStatusIcon(status as OverallStatusType) : undefined;
      label = compact ? status.toString() : getStatusText(status as OverallStatusType);
      break;
    case 'websocket':
      color = getWebSocketStatusColor(status as WebSocketStatusType);
      icon = showIcon ? getWebSocketStatusIcon(status as WebSocketStatusType) : undefined;
      label = compact ? status.toString() : getWebSocketStatusText(status as WebSocketStatusType);
      break;
    case 'backend':
      color = getBackendStatusColor(status as SystemStatusType);
      icon = showIcon ? getStatusIcon(status as OverallStatusType) : undefined;
      label = compact ? status.toString() : getBackendStatusText(status as SystemStatusType);
      break;
  }

  return (
    <Chip
      size={size}
      color={color}
      icon={icon}
      label={label}
      variant="outlined"
    />
  );
};

// Status Alert Component for detailed status display
export interface StatusAlertProps {
  status: OverallStatusType;
  title?: string;
  message?: string;
  showDetails?: boolean;
  backendStatus?: SystemStatusType;
  websocketStatus?: WebSocketStatusType;
  lastChecked?: number;
}

export const StatusAlert: React.FC<StatusAlertProps> = ({
  status,
  title,
  message,
  showDetails = false,
  backendStatus,
  websocketStatus,
  lastChecked
}) => {
  const defaultTitle = getStatusText(status);
  const defaultMessage = status === 'healthy'
    ? 'All systems are operating normally.'
    : status === 'warning'
    ? 'Some systems may be experiencing issues.'
    : 'Critical system errors detected.';

  return (
    <Alert
      severity={status === 'healthy' ? 'success' : status === 'warning' ? 'warning' : 'error'}
      sx={{ mb: 2 }}
    >
      <Typography variant="body2" sx={{ fontWeight: 'bold', mb: 1 }}>
        {title || defaultTitle}
      </Typography>
      <Typography variant="body2" sx={{ mb: showDetails ? 2 : 0 }}>
        {message || defaultMessage}
      </Typography>

      {showDetails && (
        <Box sx={{ mt: 1 }}>
          {backendStatus && (
            <Typography variant="caption" display="block" color="text.secondary">
              Backend: {getBackendStatusText(backendStatus)}
            </Typography>
          )}
          {websocketStatus && (
            <Typography variant="caption" display="block" color="text.secondary">
              WebSocket: {getWebSocketStatusText(websocketStatus)}
            </Typography>
          )}
          {lastChecked && (
            <Typography variant="caption" display="block" color="text.secondary">
              Last Checked: {new Date(lastChecked).toLocaleTimeString()}
            </Typography>
          )}
        </Box>
      )}
    </Alert>
  );
};

// Compact Status Display for headers/toolbars
export interface CompactStatusDisplayProps {
  backendStatus: SystemStatusType;
  websocketStatus: WebSocketStatusType;
  showLabels?: boolean;
  size?: 'small' | 'medium';
}

export const CompactStatusDisplay: React.FC<CompactStatusDisplayProps> = ({
  backendStatus,
  websocketStatus,
  showLabels = true,
  size = 'small'
}) => {
  return (
    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
      {showLabels && (
        <Typography variant="caption" color="text.secondary">
          Backend:
        </Typography>
      )}
      <StatusChip
        status={backendStatus}
        type="backend"
        size={size}
        compact={true}
      />

      {showLabels && (
        <Typography variant="caption" color="text.secondary">
          WebSocket:
        </Typography>
      )}
      <StatusChip
        status={websocketStatus}
        type="websocket"
        size={size}
        compact={true}
      />
    </Box>
  );
};

// Direct WebSocket health subscription for SystemStatusIndicator
let healthWsSubscribed = false;

interface SystemStatus {
  backend: 'healthy' | 'degraded' | 'unhealthy' | 'unknown';
  websocket: 'connected' | 'disconnected' | 'connecting' | 'error';
  readOnlyMode: boolean;
  lastChecked: number;
  highLoad?: boolean;
}

interface SystemStatusIndicatorProps {
  showDetails?: boolean;
  compact?: boolean;
}

export function SystemStatusIndicator({ showDetails = false, compact = false }: SystemStatusIndicatorProps) {
  const [systemStatus, setSystemStatus] = useState<SystemStatus>({
    backend: 'unknown',
    websocket: 'connecting',
    readOnlyMode: false,
    lastChecked: 0,
  });

  // Log initial component mount
  useEffect(() => {
    console.log('🚀 SystemStatusIndicator - Component INITIAL MOUNT:', {
      initialState: systemStatus,
      timestamp: new Date().toISOString()
    });
  }, []);

  // Cache health check for 30 seconds
  const fetchHealth = React.useCallback(async () => {
    try {
      console.log('SystemStatusIndicator - Fetching health data from API...');
      const health = await apiService.healthCheck();
      console.log('SystemStatusIndicator - Health API response:', health);

      // Degradation info is included in the health response
      const degradation = health?.data?.degradation_info || {};
      console.log('SystemStatusIndicator - Degradation info:', degradation);

      return { health, degradation };
    } catch (error) {
      console.error('SystemStatusIndicator - Health API call failed:', error);
      // Return fallback data to prevent crashes
      return {
        health: { status: 'unknown', data: { status: 'unknown' } },
        degradation: { unavailable_services: [], degraded_services: [], healthy_services: 0, total_services: 0 }
      };
    }
  }, []);

  const { data: healthData, loading: healthLoading, error: healthError } = useSmartCache(
    'system-health',
    fetchHealth,
    { ttl: 30000 }
  );

  // Log health data errors
  useEffect(() => {
    if (healthError) {
      console.error('SystemStatusIndicator - Health data error:', healthError);
    }
  }, [healthError]);

  // Use reactive WebSocket store with error handling
  const { connectionStatus, isConnected, lastError } = useWebSocketStore();

  // Use health store for real-time health notifications with error handling
  const { healthStatus, addHealthAlert, getOverallStatus: getHealthOverallStatus } = useHealthStore();

  // Debug WebSocket store values
  useEffect(() => {
    console.log('🔌 SystemStatusIndicator - WebSocket Store Values:', {
      connectionStatus,
      isConnected,
      lastError,
      timestamp: new Date().toISOString()
    });
  }, [connectionStatus, isConnected, lastError]);

  // Debug health store values
  useEffect(() => {
    console.log('🏥 SystemStatusIndicator - Health Store Values:', {
      healthStatus,
      timestamp: new Date().toISOString()
    });
  }, [healthStatus]);

  // Consolidated status update - prevents race conditions between WebSocket and API updates
  // Use useMemo to compute derived values and reduce re-renders
  const computedStatus = React.useMemo(() => {
    try {
      console.log('🔄 SystemStatusIndicator - Computing status with:', {
        connectionStatus,
        isConnected,
        healthData: healthData ? 'present' : 'null',
        healthStatus: healthStatus ? 'present' : 'null',
        healthDataStatus: healthData?.health?.status,
        healthStoreStatus: healthStatus?.status
      });

      // Get health status with error handling
      let healthOverallStatus = 'unknown';
      try {
        healthOverallStatus = getHealthOverallStatus();
      } catch (error) {
        console.error('SystemStatusIndicator - Error getting health overall status:', error);
      }

      // Use API health data as primary source if available, fallback to store
      let backendStatus: 'healthy' | 'degraded' | 'unhealthy' | 'unknown' = 'unknown';
      if (healthData?.health?.status) {
        const apiStatus = healthData.health.status;
        backendStatus = (apiStatus === 'healthy' || apiStatus === 'ok') ? 'healthy' :
                       apiStatus === 'degraded' ? 'degraded' :
                       apiStatus === 'unhealthy' ? 'unhealthy' : 'unknown';
      } else {
        backendStatus = healthOverallStatus === 'healthy' ? 'healthy' :
                       healthOverallStatus === 'degraded' ? 'degraded' :
                       healthOverallStatus === 'unhealthy' ? 'unhealthy' : 'unknown';
      }

      // WebSocket takes priority over API for real-time status
      const websocketStatus = connectionStatus === 'disabled' ? 'disconnected' : connectionStatus;

      // API health data for additional details
      let highLoad = false;
      let lastChecked = healthStatus?.lastUpdated || Date.now();

      if (healthData) {
        highLoad = Boolean(
          healthData.degradation?.degraded_services?.length > 0 ||
          healthData.degradation?.unavailable_services?.length > 0
        );
        lastChecked = Date.now();
      }

      const result = {
        backend: backendStatus,
        websocket: websocketStatus,
        highLoad,
        lastChecked,
      };

      console.log('✅ SystemStatusIndicator - Computed status result:', result);
      return result;
    } catch (error) {
      console.error('SystemStatusIndicator - Critical error in computedStatus:', error);
      return {
        backend: 'unknown' as const,
        websocket: (connectionStatus === 'disabled' ? 'disconnected' : connectionStatus) || 'unknown',
        highLoad: false,
        lastChecked: Date.now(),
      };
    }
  }, [connectionStatus, healthStatus?.lastUpdated, healthData]); // Remove getHealthOverallStatus from deps

  // Update system status only when computed values change
  useEffect(() => {
    console.log('SystemStatusIndicator - ===== STATUS UPDATE TRIGGERED =====');
    console.log('SystemStatusIndicator - New computed status:', computedStatus);

    setSystemStatus(prev => ({
      ...prev,
      ...computedStatus,
      readOnlyMode: false, // no automatic read-only
    }));

    console.log('SystemStatusIndicator - ===== STATUS UPDATE COMPLETED =====');
  }, [computedStatus]);

  // Direct WebSocket health subscription for redundancy
  useEffect(() => {
    console.log('SystemStatusIndicator - Component mounted');

    // Check WebSocket service initialization
    console.log('🔧 SystemStatusIndicator - WebSocket service check:', {
      wsService: !!wsService,
      isWebSocketConnected: wsService?.isWebSocketConnected?.(),
      config: {
        wsUrl: config.wsUrl,
        isProduction: config.isProduction
      },
      timestamp: new Date().toISOString()
    });

    // Subscribe to health updates directly if not already subscribed
    if (!healthWsSubscribed) {
      console.log('SystemStatusIndicator - Setting up direct WebSocket health subscription');

      const healthCallbacks = {
        onHealthUpdate: (data: any) => {
          console.log('🏥 SystemStatusIndicator - Health callback triggered:', {
            messageType: data?.type,
            hasData: !!data?.data,
            dataKeys: data?.data ? Object.keys(data.data) : [],
            timestamp: new Date().toISOString()
          });

          if (data && data.data) {
            const healthData = data.data;
            console.log('📊 SystemStatusIndicator - Processing health data:', {
              status: healthData.status,
              degradationInfo: healthData.degradation_info,
              components: healthData.components,
              timestamp: new Date().toISOString()
            });

            const overallStatus = healthData.status === 'healthy' ? 'healthy' :
                                healthData.status === 'degraded' ? 'degraded' :
                                healthData.status === 'unhealthy' ? 'unhealthy' : 'unknown';

            console.log('🔄 SystemStatusIndicator - Updating health store with status:', overallStatus);

            // Update health store directly
            useHealthStore.getState().setHealthStatus({
              status: overallStatus,
              lastUpdated: Date.now()
            });

            console.log('✅ SystemStatusIndicator - Health store updated successfully');
          } else {
            console.log('⚠️ SystemStatusIndicator - No health data in message');
          }
        }
      };

      // Set up WebSocket callbacks for health updates
      wsService.setCallbacks({
        onConnect: () => {
          console.log('🔗 SystemStatusIndicator - WebSocket CONNECTED for health updates');
          console.log('🔗 SystemStatusIndicator - Subscribing to health streams...');
        },
        onDisconnect: (reason: string) => {
          console.log('🔌 SystemStatusIndicator - WebSocket DISCONNECTED:', reason);
        },
        onError: (error: any) => {
          console.log('❌ SystemStatusIndicator - WebSocket ERROR:', error);
        },
        onHealthCheck: (data: any) => {
          console.log('🏥 SystemStatusIndicator - Direct WebSocket health message received:', {
            type: data?.type,
            stream: data?.stream,
            hasData: !!data?.data,
            dataKeys: data?.data ? Object.keys(data.data) : [],
            timestamp: new Date().toISOString(),
            fullMessage: data
          });

          // Handle both alert and status updates
          if (data && data.type === 'response' && data.status === 'comprehensive_health_check') {
            console.log('✅ SystemStatusIndicator - Processing comprehensive_health_check message');
            healthCallbacks.onHealthUpdate(data);
          } else if (data && data.type === 'health_update') {
            console.log('✅ SystemStatusIndicator - Processing health_update message');
            healthCallbacks.onHealthUpdate(data);
          } else if (data && data.alert_id) {
            console.log('🚨 SystemStatusIndicator - Processing health alert');
          } else {
            console.log('❓ SystemStatusIndicator - Unknown health message type:', data?.type, data?.status);
          }
        }
      });

      // Subscribe to health stream
      console.log('📡 [SystemStatusIndicator] Subscribing to WebSocket streams:', {
        health_check: {},
        timestamp: new Date().toISOString(),
        component: 'SystemStatusIndicator'
      });

      wsService.subscribe('health_check', {});
      healthWsSubscribed = true;

      console.log('✅ [SystemStatusIndicator] WebSocket subscriptions completed:', {
        subscribed_streams: ['health_check'],
        component: 'SystemStatusIndicator',
        timestamp: new Date().toISOString()
      });

      // Log subscription summary after subscribing
      setTimeout(() => wsService.logSubscriptionSummary(), 100);

      // Test backend connectivity
      setTimeout(() => {
        console.log('🔍 SystemStatusIndicator - Testing backend connectivity...');

        // Test WebSocket connectivity
        if (wsService.isWebSocketConnected()) {
          console.log('✅ SystemStatusIndicator - Backend WebSocket is connected');
        } else {
          console.log('❌ SystemStatusIndicator - Backend WebSocket is NOT connected');
          console.log('🔍 SystemStatusIndicator - WebSocket state:', {
            isConnected: wsService.isWebSocketConnected(),
            connectionStatus,
            config: {
              wsUrl: config.wsUrl,
              isProduction: config.isProduction
            }
          });
        }

        // Test HTTP API connectivity
        console.log('🌐 SystemStatusIndicator - Testing HTTP API connectivity...');
        apiService.healthCheck()
          .then(response => {
            console.log('✅ SystemStatusIndicator - HTTP API is accessible:', {
              status: response?.status,
              hasData: !!response?.data,
              timestamp: new Date().toISOString()
            });
          })
          .catch(error => {
            console.log('❌ SystemStatusIndicator - HTTP API is NOT accessible:', {
              error: error?.message || error,
              timestamp: new Date().toISOString()
            });
          });

      }, 2000);
    }

    return () => {
      console.log('SystemStatusIndicator - Component unmounting, cleaning up...');
      // Clear any intervals or subscriptions here if needed
      // Note: Zustand stores handle their own cleanup
    };
  }, []);

  // Performance monitoring - log re-render causes (only log significant changes)
  const renderCount = React.useRef(0);
  renderCount.current += 1;

  // Log only when status actually changes to reduce console spam
  const prevStatusRef = React.useRef(systemStatus);
  React.useEffect(() => {
    const prevStatus = prevStatusRef.current;
    if (prevStatus.backend !== systemStatus.backend || prevStatus.websocket !== systemStatus.websocket) {
      console.log(`SystemStatusIndicator - Status changed (Render #${renderCount.current}):`, {
        from: prevStatus,
        to: systemStatus,
        timestamp: new Date().toISOString()
      });
      prevStatusRef.current = systemStatus;
    }
  }, [systemStatus]);

  const getOverallStatus = (): 'healthy' | 'warning' | 'error' => {
    if (systemStatus.backend === 'unhealthy' || systemStatus.websocket === 'error') {
      return 'error';
    }
    if (systemStatus.backend === 'degraded' || systemStatus.websocket === 'disconnected' || systemStatus.highLoad) {
      return 'warning';
    }
    if (systemStatus.backend === 'healthy' && systemStatus.websocket === 'connected') {
      return 'healthy';
    }
    return 'warning';
  };

  const getStatusIcon = () => {
    const status = getOverallStatus();
    switch (status) {
      case 'healthy':
        return <CheckCircleIcon fontSize="small" />;
      case 'warning':
        return <WarningIcon fontSize="small" />;
      case 'error':
        return <ErrorIcon fontSize="small" />;
    }
  };

  const getStatusColor = () => {
    const status = getOverallStatus();
    switch (status) {
      case 'healthy':
        return 'success';
      case 'warning':
        return 'warning';
      case 'error':
        return 'error';
    }
  };

  const getStatusText = () => {
    // Debug logging to see current status values
    console.log('🔍 SystemStatusIndicator - getStatusText called with:', {
      backend: systemStatus.backend,
      websocket: systemStatus.websocket,
      readOnlyMode: systemStatus.readOnlyMode,
      connectionStatus,
      isConnected,
      timestamp: new Date().toISOString()
    });

    // Log the decision path with detailed reasoning
    console.log('🎯 SystemStatusIndicator - Status decision logic:', {
      readOnlyMode: systemStatus.readOnlyMode,
      backend_unhealthy: systemStatus.backend === 'unhealthy',
      websocket_error: systemStatus.websocket === 'error',
      backend_degraded: systemStatus.backend === 'degraded',
      websocket_disconnected: systemStatus.websocket === 'disconnected',
      healthy_and_connected: systemStatus.backend === 'healthy' && systemStatus.websocket === 'connected',
      fallback_to_checking: true
    });

    if (systemStatus.readOnlyMode) {
      console.log('📝 SystemStatusIndicator - Returning "Read-Only"');
      return 'Read-Only';
    }
    if (systemStatus.backend === 'unhealthy') {
      console.log('❌ SystemStatusIndicator - Returning "Backend Error"');
      return 'Backend Error';
    }
    if (systemStatus.websocket === 'error') {
      console.log('🔌 SystemStatusIndicator - Returning "Connection Error"');
      return 'Connection Error';
    }
    if (systemStatus.backend === 'degraded') {
      console.log('⚠️ SystemStatusIndicator - Returning "Degraded"');
      return 'Degraded';
    }
    if (systemStatus.websocket === 'disconnected') {
      console.log('🔌 SystemStatusIndicator - Returning "Disconnected"');
      return 'Disconnected';
    }
    if (systemStatus.backend === 'healthy' && systemStatus.websocket === 'connected') {
      console.log('✅ SystemStatusIndicator - Returning "All Systems Operational"');
      return 'All Systems Operational';
    }

    console.log('⏳ SystemStatusIndicator - Falling back to "Checking..." - conditions not met');
    return 'Checking...';
  };

  const getWebSocketStatusIcon = () => {
    switch (systemStatus.websocket) {
      case 'connected':
        return <WifiIcon fontSize="small" color="success" />;
      case 'connecting':
        return <CircularProgress size={16} color="warning" />;
      case 'disconnected':
        return <WifiOffIcon fontSize="small" color="warning" />;
      case 'error':
        return <CloudOffIcon fontSize="small" color="error" />;
    }
  };

  if (compact) {
    return (
      <Tooltip title={
        <Box>
          <Typography variant="body2" sx={{ fontWeight: 'bold', mb: 1 }}>
            System Status
          </Typography>
          <Typography variant="caption" display="block">
            Backend: {systemStatus.backend}
          </Typography>
          <Typography variant="caption" display="block">
            WebSocket: {systemStatus.websocket}
          </Typography>
          {systemStatus.readOnlyMode && (
            <Typography variant="caption" display="block" sx={{ color: 'warning.main' }}>
              Read-Only Mode Active
            </Typography>
          )}
        </Box>
      }>
        <Chip
          size="small"
          color={getStatusColor()}
          icon={getStatusIcon()}
          label={getStatusText()}
          sx={{ cursor: 'pointer' }}
        />
      </Tooltip>
    );
  }

  // Log final render values
  const finalStatusText = getStatusText();
  console.log('🎨 SystemStatusIndicator - RENDERING with status:', {
    finalStatusText,
    overallStatus: getOverallStatus(),
    statusColor: getStatusColor(),
    timestamp: new Date().toISOString()
  });

  return (
    <Box sx={{ mb: 2 }}>
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
        <Chip
          color={getStatusColor()}
          icon={getStatusIcon()}
          label={finalStatusText}
        />

        <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
          {getWebSocketStatusIcon()}
          <Typography variant="caption" color="text.secondary">
            WebSocket
          </Typography>
        </Box>

        {healthLoading && (
          <CircularProgress size={16} color="inherit" />
        )}
      </Box>

      {systemStatus.readOnlyMode && (
        <Alert severity="warning" sx={{ mb: 1 }}>
          <Typography variant="body2">
            System is in read-only mode. Some features may be limited.
          </Typography>
        </Alert>
      )}

      {showDetails && (
        <Box sx={{ mt: 1 }}>
          <Typography variant="caption" color="text.secondary" display="block">
            Backend Status: {systemStatus.backend}
          </Typography>
          <Typography variant="caption" color="text.secondary" display="block">
            WebSocket: {systemStatus.websocket}
          </Typography>
          <Typography variant="caption" color="text.secondary" display="block">
            Last Checked: {new Date(systemStatus.lastChecked).toLocaleTimeString()}
          </Typography>
        </Box>
      )}
    </Box>
  );
}

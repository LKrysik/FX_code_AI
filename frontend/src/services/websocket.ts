import { config, debugLog, errorLog } from '@/utils/config';
import { useWebSocketStore } from '@/stores/websocketStore';
import { authService } from '@/services/authService';
import { recordWebSocketMessage } from '@/hooks/usePerformanceMonitor';
import { categorizeError, logUnifiedError, getErrorRecoveryStrategy, type UnifiedError } from '@/utils/statusUtils';
import { useDebugStore } from '@/stores/debugStore';
import { Logger } from './frontendLogService';

export interface WSMessage {
  type: string;
  stream?: string;
  data?: any;
  session_id?: string;
  timestamp?: string;
  id?: string; // Request ID for correlation
  [key: string]: any;
}

export interface WSCallbacks {
  onConnect?: () => void;
  onDisconnect?: (reason: string) => void;
  onError?: (error: any) => void;
  onMarketData?: (data: any) => void;
  onIndicators?: (data: any) => void;
  onSignals?: (data: any) => void;
  onSessionUpdate?: (data: any) => void;
  onStrategyUpdate?: (data: any) => void;
  onHealthCheck?: (data: any) => void;
  // COH-001-4: Clean dependency boundary - store subscribes to service
  onStateSync?: (data: { positions?: any[]; activeSignals?: any[]; timestamp: string }) => void;
  onNotification?: (notification: { type: 'success' | 'error' | 'warning' | 'info'; message: string; autoHide?: boolean }) => void;
}

class WebSocketService {
  private socket: WebSocket | null = null;
  private isAuthenticated = false;
  private isConnected = false;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 1000;

  private getReconnectDelay(): number {
    const baseDelay = 1000; // 1 second
    const maxDelay = 30000; // 30 seconds
    const delay = baseDelay * Math.pow(2, this.reconnectAttempts);
    return Math.min(delay, maxDelay);
  }
  private callbacks: WSCallbacks = {};
  private pendingRequests: Map<string, { resolve: Function; reject: Function; timeout: NodeJS.Timeout }> = new Map();
  private requestIdCounter = 0;
  private sessionUpdateListeners: Set<(message: WSMessage) => void> = new Set();
  private listenerMetadata = new Map<(message: WSMessage) => void, {
    component: string;
    addedAt: number;
    stackTrace?: string;
  }>();
  private activeSubscriptions: Map<string, any> = new Map();
  private pendingSubscriptions: Map<string, any> = new Map();
  private heartbeatTimer: NodeJS.Timeout | null = null;
  private pongTimeout: NodeJS.Timeout | null = null;
  private debounceTimer: NodeJS.Timeout | null = null;
  private heartbeatInterval = 30000; // 30 seconds
  // BUG-005-2: Increased from 10s to 30s to handle normal network latency
  private heartbeatTimeout = 30000; // 30 seconds - time to wait for pong response
  private missedPongs = 0; // BUG-005-2: Track missed pong responses
  private maxMissedPongs = 3; // BUG-005-2: Force reconnect after this many missed pongs

  constructor() {
    try {
      const url = config.wsUrl;
      if (!url || url === 'disabled' || url === 'none') {
        debugLog('WebSocket disabled by configuration');
        this.debouncedStoreUpdate(() => {
          useWebSocketStore.getState().setConnected(false);
          useWebSocketStore.getState().setConnectionStatus('disabled');
        });
        return;
      }
      // Check if we have auth credentials and authenticate first
      this.initializeWithAuth();
    } catch (e: any) {
      errorLog('WebSocket initialization failed', e);
      this.debouncedStoreUpdate(() => {
        useWebSocketStore.getState().setConnected(false);
        useWebSocketStore.getState().setConnectionStatus('error');
        useWebSocketStore.getState().setLastError(e.toString());
      });
    }
  }

  private async initializeWithAuth(): Promise<void> {
    try {
      // Check if we already have valid authentication
      if (!authService.isAuthenticated()) {
        debugLog('No authentication available, connecting without auth');
        this.isAuthenticated = false;
      } else {
        debugLog('Found existing authentication, verifying session...');
        const sessionValid = await authService.ensureSession();
        this.isAuthenticated = sessionValid;
        if (!sessionValid) {
          debugLog('Stored authentication invalid, proceeding without auth');
        }
      }

      this.connect();
    } catch (error) {
      errorLog('Authentication check failed', error);
      this.connect(); // Connect anyway for WebSocket functionality
    }
  }

  private connect(): void {
    try {
      const wsUrl = config.wsUrl.replace(/^http/, 'ws');
      debugLog('Connecting to WebSocket server...', { url: wsUrl });

      this.socket = new WebSocket(wsUrl);

      this.setupEventHandlers();
    } catch (error) {
      const wsUrl = config.wsUrl?.replace(/^http/, 'ws');
      const unifiedError = categorizeError(error, 'WebSocket instantiation');
      logUnifiedError(unifiedError);
      this.safeStoreUpdate(() => {
        useWebSocketStore.getState().setConnectionStatus('error');
        useWebSocketStore.getState().setLastError(`Failed to create WebSocket connection to ${wsUrl}. ${unifiedError.message}`);
      }, 'create websocket error');
    }
  }


  private generateClientId(): string {
    return `client_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  private safeStoreUpdate(action: () => void, context: string) {
    try {
      action();
    } catch (error) {
      errorLog(`Store update failed in ${context}`, error);
    }
  }

  private debouncedStoreUpdate = (action: () => void, delay: number = 50) => {
    if (this.debounceTimer) clearTimeout(this.debounceTimer);
    this.debounceTimer = setTimeout(() => {
      this.safeStoreUpdate(action, 'debounced update');
    }, delay);
  };

  private setupEventHandlers(): void {
    if (!this.socket) return;

    // Connection events
    this.socket.onopen = () => {
      Logger.info('websocket.connection_opened', {
        url: this.socket?.url,
        readyState: this.socket?.readyState,
        timestamp: new Date().toISOString()
      });
      debugLog('WebSocket connected');
      this.reconnectAttempts = 0; // Reset on successful connection
      this.safeStoreUpdate(() => {
        useWebSocketStore.getState().setConnectionStatus('connecting');
      }, 'connection open');
      // Backend sends welcome message immediately, no handshake needed
      // Heartbeat will start after receiving welcome message
    };

    this.socket.onclose = (event) => {
      debugLog(`WebSocket disconnected: ${event.code} ${event.reason}`, { code: event.code, reason: event.reason, wasConnected: this.isConnected });
      this.isConnected = false;
      this.safeStoreUpdate(() => {
        useWebSocketStore.getState().setConnected(false);
        useWebSocketStore.getState().setConnectionStatus('disconnected');
      }, 'connection close');
      this.callbacks.onDisconnect?.(event.reason || 'Unknown reason');
      this.stopHeartbeat();

      // Auto-reconnect if not intentionally closed
      if (event.code !== 1000 && this.reconnectAttempts < this.maxReconnectAttempts) {
        const disconnectError = {
          code: event.code,
          reason: event.reason || 'Connection closed unexpectedly',
          message: `WebSocket disconnected with code ${event.code}`
        };
        const unifiedError = categorizeError(disconnectError, 'WebSocket disconnect');
        const recoveryStrategy = getErrorRecoveryStrategy(unifiedError);

        if (recoveryStrategy.shouldRetry) {
          const delay = this.getReconnectDelay();
          setTimeout(() => {
            this.reconnectAttempts++;
            debugLog(`Attempting to reconnect (${this.reconnectAttempts}/${this.maxReconnectAttempts}) with exponential backoff delay ${delay}ms`);
            this.connect();
          }, delay);
        } else {
          logUnifiedError(unifiedError);
        }
      }
    };

    this.socket.onerror = (error) => {
      const unifiedError = categorizeError(error, 'WebSocket connection');
      logUnifiedError(unifiedError);
      
      this.safeStoreUpdate(() => {
        useWebSocketStore.getState().setConnectionStatus('error');
        useWebSocketStore.getState().setLastError(`Connection error: ${unifiedError.message}`);
      }, 'connection error');
      this.callbacks.onError?.(error);
    };

    // Message handler
    this.socket.onmessage = (event) => {
      try {
        const message: WSMessage = JSON.parse(event.data);
        debugLog('Received message', message);
        recordWebSocketMessage(); // Record performance metric

        // Log WebSocket messages for debugging
        this.logWebSocketMessage(message, 'received');

        this.handleMessage(message);
      } catch (error) {
        errorLog('Failed to parse WebSocket message', error);
      }
    };
  }

  private handleMessage(message: WSMessage): void {
    // [DEBUG] Capture message for debug panel (dev mode only)
    if (process.env.NODE_ENV === 'development') {
      try {
        useDebugStore.getState().addMessage({
          type: message.type,
          stream: message.stream,
          timestamp: new Date().toISOString(),
          payload: message,
        });
      } catch {
        // Silently ignore debug store errors
      }
    }

    // Handle handshake response first (backend sends 'status: connected')
    if (message.type === 'status' && message.status === 'connected') {
      this.handleHandshakeResponse(message);
      return;
    }

    // Handle request/response correlation
    if (message.id && this.pendingRequests.has(message.id)) {
      const { resolve, reject, timeout } = this.pendingRequests.get(message.id)!;
      clearTimeout(timeout);
      this.pendingRequests.delete(message.id);

      if (message.type === 'error') {
        reject(new Error(message.error_message || 'Request failed'));
      } else {
        resolve(message);
      }
      return;
    }

    // Filter messages before processing - only handle relevant system status messages
    if (!this.isRelevantMessage(message)) {
      debugLog('Filtered out irrelevant message', message.type);
      return;
    }

    // Handle broadcast messages
    switch (message.type) {
      case 'market_data':
        // Update connection status when receiving data messages
        if (!this.isConnected) {
          Logger.info('websocket.connection_confirmed', { source: 'market_data' });
          this.isConnected = true;
          this.safeStoreUpdate(() => {
            useWebSocketStore.getState().setConnected(true);
            useWebSocketStore.getState().setConnectionStatus('connected');
          }, 'market data confirmation');
        }
        this.callbacks.onMarketData?.(message);
        break;
      case 'indicators':
        // Update connection status when receiving indicator messages
        if (!this.isConnected) {
          Logger.info('websocket.connection_confirmed', { source: 'indicators' });
          this.isConnected = true;
          this.safeStoreUpdate(() => {
            useWebSocketStore.getState().setConnected(true);
            useWebSocketStore.getState().setConnectionStatus('connected');
          }, 'indicators confirmation');
        }
        this.callbacks.onIndicators?.(message);
        break;
      case 'signal':
      case 'signals':
        // [SIGNAL-FLOW] Debug logging for E2E verification (Story 0-2)
        Logger.debug('websocket.signal_received', {
          type: message.type,
          signal_type: message.data?.signal_type,
          symbol: message.data?.symbol,
          section: message.data?.section,
          timestamp: message.timestamp,
          latency_ms: message.timestamp ? Date.now() - new Date(message.timestamp).getTime() : 'N/A',
          indicators: message.data?.indicators,
        });
        // Update connection status when receiving signal messages
        if (!this.isConnected) {
          Logger.info('websocket.connection_confirmed', { source: 'signals' });
          this.isConnected = true;
          this.safeStoreUpdate(() => {
            useWebSocketStore.getState().setConnected(true);
            useWebSocketStore.getState().setConnectionStatus('connected');
          }, 'signals confirmation');
        }
        this.callbacks.onSignals?.(message);
        break;
      case 'session_status':
      case 'session_update':
        this.emitSessionUpdate(message);
        break;
      case 'strategy_status':
      case 'strategy_update':
        this.callbacks.onStrategyUpdate?.(message);
        break;
      case 'health_check':
      case 'comprehensive_health_check':
        // Update connection status when receiving health messages
        if (!this.isConnected) {
          Logger.info('websocket.connection_confirmed', { source: 'health_check' });
          this.isConnected = true;
          this.safeStoreUpdate(() => {
            useWebSocketStore.getState().setConnected(true);
            useWebSocketStore.getState().setConnectionStatus('connected');
          }, 'health confirmation');
        }
        this.callbacks.onHealthCheck?.(message);
        break;
      case 'data':
        this.handleDataMessage(message);
        break;
      case 'execution_result':
        // Forward execution_result messages to session update listeners
        // This ensures completion/failure events are processed by the UI
        this.emitSessionUpdate(message);
        break;
      // BUG-007 fix: State machine broadcast messages
      case 'state_change':
      case 'instance_added':
      case 'instance_removed':
      case 'full_update':
        // Forward state machine messages to session update listeners
        // This enables real-time state updates for dashboard components
        this.emitSessionUpdate(message);
        break;
      default:
        debugLog('Unhandled message type', message.type, message);
    }

    // Handle pong response - BUG-005-2: Properly reset missed pong counter
    if (message.type === 'status' && message.status === 'pong') {
      if (this.pongTimeout) {
        clearTimeout(this.pongTimeout);
        this.pongTimeout = null;
      }
      // BUG-005-2: Reset missed pongs counter on successful pong
      this.missedPongs = 0;
      debugLog('[Heartbeat] Pong received, missed pong counter reset to 0');
    }
  }

  private isRelevantMessage(message: WSMessage): boolean {
    // Filter messages to only process those relevant to system status and subscribed streams
    const relevantTypes = [
      'market_data',
      'indicators',
      'signal',
      'signals',
      'session_status',
      'session_update',
      'strategy_status',
      'strategy_update',
      'health_check',
      'comprehensive_health_check',
      'data',
      'execution_result',
      'status', // For pong responses
      // BUG-007 fix: State machine broadcast messages
      'state_change',
      'instance_added',
      'instance_removed',
      'full_update'
    ];

    // Check if message type is relevant
    if (!relevantTypes.includes(message.type)) {
      return false;
    }

    // For data stream messages, check if we're subscribed to that stream
    if (message.stream) {
      const isSubscribed = this.activeSubscriptions.has(message.stream) ||
                          this.pendingSubscriptions.has(message.stream);
      if (!isSubscribed) {
        return false;
      }
    }

    return true;
  }

  private handleDataMessage(message: WSMessage): void {
    const stream = message.stream;
    if (stream === 'execution_status') {
      Logger.debug('websocket.execution_status_received', {
        records_collected: message.data?.records_collected,
        progress_percentage: message.data?.progress_percentage,
        session_id: message.session_id,
        timestamp: new Date().toISOString()
      });
      this.emitSessionUpdate(message);
      return;
    }

    if (stream === 'execution_result') {
      Logger.debug('websocket.execution_result_received', {
        session_id: message.session_id,
        timestamp: new Date().toISOString()
      });
      this.emitSessionUpdate(message);
      return;
    }

    if (stream === 'market_data') {
      this.callbacks.onMarketData?.(message);
    } else if (stream === 'indicators') {
      this.callbacks.onIndicators?.(message);
    } else if (stream === 'signals') {
      // [SIGNAL-FLOW] Debug logging for data stream signals (Story 0-2)
      const signalData = message.data || message;
      const messageTimestamp = message.timestamp || signalData.timestamp;
      const latencyMs = messageTimestamp
        ? Date.now() - new Date(messageTimestamp).getTime()
        : null;
      Logger.debug('websocket.signal_data_stream_received', {
        type: message.type,
        stream: message.stream,
        signal_type: signalData.signal_type,
        symbol: signalData.symbol,
        section: signalData.section || signalData.signal_type,
        timestamp: messageTimestamp,
        latency_ms: latencyMs,
        indicators: signalData.indicators || signalData.indicator_values,
        received_at: new Date().toISOString()
      });
      this.callbacks.onSignals?.(message);
    } else if (stream === 'strategy_status' || stream === 'strategy_update') {
      this.callbacks.onStrategyUpdate?.(message);
    } else if (stream === 'health_check' || stream === 'comprehensive_health_check') {
      this.callbacks.onHealthCheck?.(message);
    } else {
      debugLog('Unhandled data stream', stream, message);
    }
  }

  private emitSessionUpdate(message: WSMessage): void {
    try {
      this.callbacks.onSessionUpdate?.(message);
    } finally {
      for (const handler of Array.from(this.sessionUpdateListeners)) {
        try {
          handler(message);
        } catch (error) {
          errorLog('Session update listener error', error);
        }
      }
    }
  }

  private sendSubscription(stream: string, params: any = {}): void {
    if (!this.socket || !this.isConnected) {
      return;
    }

    const message: WSMessage = {
      type: 'subscribe',
      stream,
      params,
      timestamp: new Date().toISOString()
    };

    debugLog(`Subscribing to ${stream}`, params);
    this.sendMessage(message);
  }

  private flushSubscriptions(): void {
    if (!this.socket || !this.isConnected) {
      return;
    }

    for (const [stream, params] of Array.from(this.activeSubscriptions.entries())) {
      this.sendSubscription(stream, params);
    }

    if (this.pendingSubscriptions.size > 0) {
      for (const [stream, params] of Array.from(this.pendingSubscriptions.entries())) {
        this.activeSubscriptions.set(stream, params);
        this.sendSubscription(stream, params);
      }
      this.pendingSubscriptions.clear();
    }
  }

  private handleHandshakeResponse(message: WSMessage): void {
    // Backend sends 'status: connected' instead of 'handshake_ack'
    if (message.type === 'status' && message.status === 'connected') {
      debugLog('Handshake accepted', message);
      this.isConnected = true;
      this.safeStoreUpdate(() => {
        useWebSocketStore.getState().setConnected(true);
        useWebSocketStore.getState().setConnectionStatus('connected');
      }, 'handshake response');
      this.flushSubscriptions();
      this.startHeartbeat(); // Start heartbeat after successful handshake

      // SEC-0-3: Request state sync after reconnection
      this.requestStateSync().catch(err => {
        Logger.warn('websocket.state_sync_failed', { error: String(err) });
      });

      this.callbacks.onConnect?.();
    } else {
      errorLog('Handshake rejected', message);
      this.safeStoreUpdate(() => {
        useWebSocketStore.getState().setConnectionStatus('error');
        useWebSocketStore.getState().setLastError('Handshake rejected');
      }, 'handshake rejected');
      this.socket?.close(1002, 'Handshake rejected');
    }
  }

  /**
   * SEC-0-3: Request state sync from backend after WebSocket reconnection.
   * Fetches complete state snapshot and updates Zustand stores.
   * Includes timeout, retry logic, and user notifications (AC4, AC5).
   */
  public async requestStateSync(retryCount = 0): Promise<void> {
    const MAX_RETRIES = 3;
    const TIMEOUT_MS = 10000; // 10 second timeout

    Logger.info('websocket.state_sync_requested', { attempt: retryCount + 1, maxRetries: MAX_RETRIES });

    // Skip state sync during SSR - relative URLs don't work without browser context
    if (typeof window === 'undefined') {
      Logger.debug('websocket.state_sync_skipped', { reason: 'not_in_browser_context' });
      return;
    }

    // Update sync status to 'syncing'
    this.safeStoreUpdate(() => {
      useWebSocketStore.getState().setSyncStatus?.('syncing');
    }, 'sync status start');

    try {
      // Create AbortController for timeout
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), TIMEOUT_MS);

      // Fetch state snapshot via REST API using absolute URL
      const baseUrl = window.location.origin;
      const response = await fetch(`${baseUrl}/api/state/snapshot`, {
        method: 'GET',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
        },
        signal: controller.signal,
      });

      clearTimeout(timeoutId);

      if (!response.ok) {
        throw new Error(`State sync failed: ${response.status}`);
      }

      const result = await response.json();
      if (!result.success || !result.data) {
        throw new Error('Invalid state snapshot response');
      }

      const snapshot = result.data;
      Logger.info('websocket.state_snapshot_received', {
        timestamp: snapshot.timestamp,
        positions: snapshot.positions?.length || 0,
        signals: snapshot.active_signals?.length || 0,
        state: snapshot.state_machine_state
      });

      // Update stores with snapshot data
      this.safeStoreUpdate(() => {
        // Update dashboard store with positions if available
        const { useDashboardStore } = require('@/stores/dashboardStore');
        if (useDashboardStore && snapshot.positions) {
          useDashboardStore.getState().setPositions?.(snapshot.positions);
        }

        // Update signals if available
        if (useDashboardStore && snapshot.active_signals) {
          useDashboardStore.getState().setActiveSignals?.(snapshot.active_signals);
        }

        // Mark sync as complete
        useWebSocketStore.getState().setLastSyncTime?.(new Date(snapshot.timestamp));
        useWebSocketStore.getState().setSyncStatus?.('synced');
      }, 'state sync');

      // SEC-0-3 AC4: Show success notification
      this.showStateSyncNotification('success', 'State synchronized');
      Logger.info('websocket.state_sync_completed', { status: 'success' });

    } catch (error: any) {
      const isTimeout = error.name === 'AbortError';
      const errorMsg = isTimeout ? 'State sync timeout' : (error.message || 'Unknown error');
      Logger.error('websocket.state_sync_error', { error: errorMsg, isTimeout }, error instanceof Error ? error : undefined);

      // Retry logic for timeout or network errors
      if (retryCount < MAX_RETRIES - 1 && (isTimeout || error.message?.includes('fetch'))) {
        Logger.info('websocket.state_sync_retrying', { attempt: retryCount + 2, maxRetries: MAX_RETRIES });
        const backoffDelay = Math.min(1000 * Math.pow(2, retryCount), 5000);
        await new Promise(resolve => setTimeout(resolve, backoffDelay));
        return this.requestStateSync(retryCount + 1);
      }

      // All retries exhausted or non-retryable error
      this.safeStoreUpdate(() => {
        useWebSocketStore.getState().setSyncStatus?.('failed');
      }, 'sync status failed');

      // SEC-0-3 AC5: Show failure notification with refresh suggestion
      this.showStateSyncNotification('error', 'State sync failed - please refresh the page');
    }
  }

  /**
   * SEC-0-3: Show notification for state sync status using uiStore
   */
  private showStateSyncNotification(type: 'success' | 'error' | 'warning' | 'info', message: string): void {
    try {
      const { useUIStore } = require('@/stores/uiStore');
      useUIStore.getState().addNotification({
        type,
        message,
        autoHide: type === 'success', // Auto-hide success, keep errors visible
      });
    } catch (err) {
      // Fallback to Logger if store not available
      Logger.info('websocket.notification_fallback', { type, message });
    }
  }

  /**
   * SEC-0-3: Force manual state sync - for use with Force Sync button
   */
  public async forceStateSync(): Promise<boolean> {
    Logger.info('websocket.force_state_sync_requested', {});
    try {
      await this.requestStateSync(0);
      return useWebSocketStore.getState().syncStatus === 'synced';
    } catch {
      return false;
    }
  }

  // Public methods
  // ✅ EDGE CASE FIX: Added input validation
  public setCallbacks(callbacks: WSCallbacks): void {
    // Validate input - skip if null/undefined
    if (!callbacks || typeof callbacks !== 'object') {
      return;
    }
    this.callbacks = { ...this.callbacks, ...callbacks };
  }

  public isWebSocketConnected(): boolean {
    return this.isConnected && this.socket?.readyState === WebSocket.OPEN;
  }

  public async authenticate(token: string): Promise<void> {
    if (!this.socket || !this.isConnected) {
      throw new Error('WebSocket not connected');
    }

    const requestId = this.generateRequestId();
    const message: WSMessage = {
      type: 'auth',
      token: token,
      id: requestId,
      timestamp: new Date().toISOString()
    };

    return new Promise((resolve, reject) => {
      // Set up timeout
      const timeout = setTimeout(() => {
        this.pendingRequests.delete(requestId);
        reject(new Error('Authentication timeout'));
      }, 10000);

      // Store the promise handlers
      this.pendingRequests.set(requestId, { resolve, reject, timeout });

      // Send the message
      this.sendMessage(message);
    });
  }

  private generateRequestId(): string {
    return `req_${++this.requestIdCounter}_${Date.now()}`;
  }

  private sendMessage(message: WSMessage): void {
    if (!this.socket || (!this.isConnected && message.type !== 'handshake')) {
      errorLog('Cannot send message: WebSocket not connected');
      return;
    }

    try {
      const messageString = JSON.stringify(message);
      this.socket.send(messageString);
      debugLog('Sent message', message);
    } catch (error) {
      errorLog('Failed to send WebSocket message', error);
    }
  }

  private startHeartbeat(): void {
    this.stopHeartbeat(); // Ensure no duplicate
    this.heartbeatTimer = setInterval(() => this.heartbeat(), this.heartbeatInterval);
  }

  private stopHeartbeat(): void {
    if (this.heartbeatTimer) {
      clearInterval(this.heartbeatTimer);
      this.heartbeatTimer = null;
    }
    if (this.pongTimeout) {
      clearTimeout(this.pongTimeout);
      this.pongTimeout = null;
    }
    if (this.debounceTimer) {
      clearTimeout(this.debounceTimer);
      this.debounceTimer = null;
    }
    // BUG-005-2: Reset missed pongs counter when stopping heartbeat
    this.missedPongs = 0;
  }

  // Removed duplicate heartbeat method - using public one below

  // ✅ EDGE CASE FIX: Added input validation
  public subscribe(stream: string, params: any = {}): void {
    // Validate stream name
    if (!stream || typeof stream !== 'string' || stream.trim().length === 0) {
      debugLog('Invalid stream name for subscription, skipping');
      return;
    }

    Logger.info('websocket.subscribe_request', {
      stream,
      params,
      timestamp: new Date().toISOString()
    });

    this.activeSubscriptions.set(stream, params);
    this.pendingSubscriptions.delete(stream);

    if (!this.socket || !this.isConnected) {
      Logger.debug('websocket.subscription_queued', {
        stream,
        isConnected: this.isConnected,
        socketExists: !!this.socket
      });
      this.pendingSubscriptions.set(stream, params);
      return;
    }

    this.sendSubscription(stream, params);
  }

  // ✅ EDGE CASE FIX: Added input validation
  public unsubscribe(stream: string): void {
    // Validate stream name
    if (!stream || typeof stream !== 'string') {
      return;
    }

    this.activeSubscriptions.delete(stream);
    this.pendingSubscriptions.delete(stream);

    if (!this.socket || !this.isConnected) {
      return;
    }

    const message: WSMessage = {
      type: 'unsubscribe',
      stream: stream,
      timestamp: new Date().toISOString()
    };

    debugLog(`Unsubscribing from ${stream}`);
    this.sendMessage(message);
  }

  public async loginAndConnect(username: string, password: string): Promise<void> {
    try {
      debugLog('Attempting to login and connect', { username });
      
      // Login via REST API
      const loginResult = await authService.login(username, password);
      this.isAuthenticated = true;
      
      debugLog('Login successful, connecting WebSocket');
      
      // Now connect or reconnect WebSocket
      if (this.socket && this.socket.readyState === WebSocket.OPEN) {
        this.disconnect();
      }
      this.connect();
      
    } catch (error: any) {
      if (error.response && error.response.data) {
        throw new Error(error.response.data.error_message || 'Login failed due to server error.');
      }
      errorLog('Login failed', error);
      this.isAuthenticated = false;
      throw error;
    }
  }

  public async sendCommand(command: string, params: any = {}): Promise<any> {
    // For session management commands, use REST API with authentication
    if (['start_session', 'stop_session'].includes(command)) {
      if (!this.isAuthenticated) {
        throw new Error('Authentication required for session commands. Please login first.');
      }

      debugLog(`Sending ${command} command via authenticated REST API`, params);
      
      try {
        const endpoint = command === 'start_session' ? '/sessions/start' : '/sessions/stop';
        const response = await authService.apiCall(endpoint, {
          method: 'POST',
          body: JSON.stringify(params),
        });

        if (!response.ok) {
          const errorData = await response.json().catch(() => ({}));
          throw new Error(errorData.error_message || `${command} failed`);
        }

        return await response.json();
      } catch (error: any) {
        // If we get an auth error, mark as unauthenticated
        if (error.message.includes('401') || error.message.includes('authentication')) {
          this.isAuthenticated = false;
          throw new Error('Authentication expired. Please login again.');
        }
        throw error;
      }
    } else {
      // For other commands, use WebSocket
      if (!this.socket || !this.isConnected) {
        throw new Error('Cannot send command: WebSocket not connected');
      }

      const message: WSMessage = {
        type: 'command',
        action: command, // Backend expects 'action' field
        params: params,
        timestamp: new Date().toISOString(),
      };

      debugLog(`Sending command via WebSocket: ${command}`, params);
      this.sendMessage(message);
    }
  }

  /**
   * BUG-005-2: Enhanced heartbeat with pong timeout handling
   * - Sends heartbeat message to backend
   * - Sets pong timeout (30 seconds) to detect missed responses
   * - Tracks missed pongs and forces reconnect after 3 consecutive misses
   */
  public heartbeat(): void {
    if (!this.socket || !this.isConnected) return;

    // Clear any existing pong timeout before sending new heartbeat
    if (this.pongTimeout) {
      clearTimeout(this.pongTimeout);
      this.pongTimeout = null;
    }

    const message: WSMessage = {
      type: 'heartbeat',
      timestamp: new Date().toISOString()
    };

    this.sendMessage(message);

    // BUG-005-2: Set pong timeout - expect response within 30 seconds
    this.pongTimeout = setTimeout(() => {
      this.missedPongs++;
      Logger.warn('websocket.heartbeat_missed_pong', { missedPongs: this.missedPongs, maxMissedPongs: this.maxMissedPongs });

      // Force reconnect if too many missed pongs
      if (this.missedPongs >= this.maxMissedPongs) {
        Logger.error('websocket.heartbeat_reconnect', { reason: 'too_many_missed_pongs', missedPongs: this.missedPongs });
        this.missedPongs = 0; // Reset counter before reconnect
        this.reconnect();
      }
    }, this.heartbeatTimeout);
  }

  // Add method to check authentication status
  public isAuthenticationRequired(): boolean {
    return !this.isAuthenticated;
  }

  // Add method to get current auth status
  public getAuthStatus(): { isAuthenticated: boolean; user?: any } {
    return {
      isAuthenticated: this.isAuthenticated,
      user: authService.getCurrentUser()
    };
  }



  // ✅ EDGE CASE FIX: Added input validation
  public addSessionUpdateListener(
    listener: (message: WSMessage) => void,
    componentName = 'unknown'
  ): () => void {
    // Validate listener is a function
    if (!listener || typeof listener !== 'function') {
      // Return no-op cleanup function
      return () => {};
    }

    this.sessionUpdateListeners.add(listener);
    this.listenerMetadata.set(listener, {
      component: componentName,
      addedAt: Date.now(),
      stackTrace: process.env.NODE_ENV === 'development' ? new Error().stack : undefined
    });

    // Warn if too many listeners (potential leak)
    if (this.sessionUpdateListeners.size > 50) {
      Logger.warn('websocket.high_listener_count', { count: this.sessionUpdateListeners.size, warning: 'possible_memory_leak' });
    }

    return () => {
      this.sessionUpdateListeners.delete(listener);
      this.listenerMetadata.delete(listener);
    };
  }

  public clearSessionUpdateListeners(): void {
    this.sessionUpdateListeners.clear();
    this.listenerMetadata.clear();
  }

  // Debug method for development
  public getListenerStats(): { count: number; components: Record<string, number> } {
    const components: Record<string, number> = {};
    // Use Array.from to handle iterator compatibility
    Array.from(this.listenerMetadata.values()).forEach(meta => {
      components[meta.component] = (components[meta.component] || 0) + 1;
    });
    return { count: this.sessionUpdateListeners.size, components };
  }

  public logSubscriptionSummary(): void {
    const summary = {
      activeSubscriptions: Object.fromEntries(this.activeSubscriptions),
      pendingSubscriptions: Object.fromEntries(this.pendingSubscriptions),
      listenerStats: this.getListenerStats(),
      connectionStatus: {
        isConnected: this.isConnected,
        socketReadyState: this.socket?.readyState,
        reconnectAttempts: this.reconnectAttempts
      },
      timestamp: new Date().toISOString()
    };

    Logger.info('websocket.subscription_summary', summary);
  }

  public disconnect(): void {
    if (this.socket) {
      debugLog('Disconnecting WebSocket');
      this.socket.close(1000, 'Client disconnect');
      this.socket = null;
      this.isConnected = false;
      // Do not reset isAuthenticated here, it persists across disconnects
    }
    this.stopHeartbeat();
  }

  public reconnect(): void {
    debugLog('Reconnecting WebSocket');
    this.disconnect();
    // Reset reconnect attempts for manual reconnect
    this.reconnectAttempts = 0;
    setTimeout(() => this.connect(), 1000);
  }

  // Add logout method
  public async logout(): Promise<void> {
    try {
      await authService.logout();
    } catch (error) {
      debugLog('Logout error (non-critical)', error);
    } finally {
      this.isAuthenticated = false;
      this.disconnect();
    }
  }

  private logWebSocketMessage(message: WSMessage, direction: 'sent' | 'received'): void {
    try {
      const logEntry = {
        timestamp: new Date().toISOString(),
        direction,
        type: message.type,
        stream: message.stream,
        data: message.data,
        id: message.id,
        session_id: message.session_id,
        client_id: this.generateClientId()
      };

      // Detailed structured logging
      Logger.debug('websocket.message', {
        direction,
        type: message.type,
        stream: message.stream ?? 'N/A',  // BUG-007.5: Graceful fallback for undefined stream
        hasData: !!message.data,
        dataKeys: message.data ? Object.keys(message.data) : [],
        timestamp: logEntry.timestamp,
        client_id: logEntry.client_id
      });

      // Log subscription details
      if (message.type === 'subscribe') {
        Logger.debug('websocket.subscribe', {
          stream: message.stream,
          params: message.data,
          timestamp: new Date().toISOString()
        });
      }

      // Log handshake details
      if (message.type === 'status' && message.status === 'connected') {
        Logger.info('websocket.handshake_completed', {
          status: message.status,
          client_id: message.client_id,
          timestamp: new Date().toISOString()
        });
      }

      // Log health updates
      if (message.type === 'health_update' || message.stream === 'health_check') {
        Logger.debug('websocket.health_update', {
          direction,
          type: message.type,
          stream: message.stream,
          status: message.data?.status,
          degradation: message.data?.degradation_info,
          timestamp: new Date().toISOString()
        });
      }

      // In browser environment, we can't write to files directly
      // Store in localStorage for debugging purposes
      if (typeof window !== 'undefined') {
        const existingLogs = localStorage.getItem('websocket_logs') || '[]';
        const logs = JSON.parse(existingLogs);
        logs.push(logEntry);

        // Keep only last 100 messages to prevent memory issues
        if (logs.length > 100) {
          logs.splice(0, logs.length - 100);
        }

        localStorage.setItem('websocket_logs', JSON.stringify(logs));
      }
    } catch (error) {
      Logger.error('websocket.log_message_failed', {}, error instanceof Error ? error : undefined);
    }
  }
}

// Create singleton instance
export const wsService = new WebSocketService();

// Types are already exported above

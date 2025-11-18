import { config, debugLog, errorLog } from '@/utils/config';
import { useWebSocketStore } from '@/stores/websocketStore';
import { authService } from '@/services/authService'; // Import the new auth service
import { recordWebSocketMessage } from '@/hooks/usePerformanceMonitor';
import { categorizeError, logUnifiedError, getErrorRecoveryStrategy, type UnifiedError } from '@/utils/statusUtils';

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
  private heartbeatTimeout = 10000; // 10 seconds

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
      console.log('🔗 [WebSocket] CONNECTION OPENED', {
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
          console.log('🔗 [WebSocket] Connection confirmed via market data');
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
          console.log('🔗 [WebSocket] Connection confirmed via indicators');
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
        // Update connection status when receiving signal messages
        if (!this.isConnected) {
          console.log('🔗 [WebSocket] Connection confirmed via signals');
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
          console.log('🔗 [WebSocket] Connection confirmed via health message');
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
      default:
        debugLog('Unhandled message type', message.type, message);
    }

    // Handle pong response
    if (message.type === 'status' && message.status === 'pong') {
      if (this.pongTimeout) {
        clearTimeout(this.pongTimeout);
        this.pongTimeout = null;
      }
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
      'status' // For pong responses
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
      console.log('📊 [FRONTEND] RECEIVED execution_status message', {
        records_collected: message.data?.records_collected,
        progress_percentage: message.data?.progress_percentage,
        session_id: message.session_id,
        timestamp: new Date().toISOString()
      });
      this.emitSessionUpdate(message);
      return;
    }

    if (stream === 'execution_result') {
      console.log('📊 [FRONTEND] RECEIVED execution_result message', {
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

  // Public methods
  public setCallbacks(callbacks: WSCallbacks): void {
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
  }

  // Removed duplicate heartbeat method - using public one below

  public subscribe(stream: string, params: any = {}): void {
    console.log('🎧 [WebSocket] SUBSCRIBE REQUEST', {
      stream,
      params,
      timestamp: new Date().toISOString()
    });

    this.activeSubscriptions.set(stream, params);
    this.pendingSubscriptions.delete(stream);

    if (!this.socket || !this.isConnected) {
      console.log('⏳ [WebSocket] Connection not ready, queuing subscription', {
        stream,
        isConnected: this.isConnected,
        socketExists: !!this.socket
      });
      this.pendingSubscriptions.set(stream, params);
      return;
    }

    this.sendSubscription(stream, params);
  }

  public unsubscribe(stream: string): void {
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

  public heartbeat(): void {
    if (!this.socket || !this.isConnected) return;

    const message: WSMessage = {
      type: 'heartbeat',
      timestamp: new Date().toISOString()
    };

    this.sendMessage(message);
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



  public addSessionUpdateListener(
    listener: (message: WSMessage) => void,
    componentName = 'unknown'
  ): () => void {
    this.sessionUpdateListeners.add(listener);
    this.listenerMetadata.set(listener, {
      component: componentName,
      addedAt: Date.now(),
      stackTrace: process.env.NODE_ENV === 'development' ? new Error().stack : undefined
    });

    // Warn if too many listeners (potential leak)
    if (this.sessionUpdateListeners.size > 50) {
      console.warn(`WebSocket: High listener count (${this.sessionUpdateListeners.size}) - possible memory leak`);
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

    console.log('📊 [WebSocket] SUBSCRIPTION SUMMARY:');
    console.log('├── Active Subscriptions:', summary.activeSubscriptions);
    console.log('├── Pending Subscriptions:', summary.pendingSubscriptions);
    console.log('├── Listener Stats:', summary.listenerStats);
    console.log('├── Connection Status:', summary.connectionStatus);
    console.log('└── Timestamp:', summary.timestamp);
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

      // Detailed console logging with emojis for visibility
      const emoji = direction === 'received' ? '📨' : '📤';
      console.log(`${emoji} [WebSocket ${direction.toUpperCase()}]`, {
        type: message.type,
        stream: message.stream,
        hasData: !!message.data,
        dataKeys: message.data ? Object.keys(message.data) : [],
        timestamp: logEntry.timestamp,
        client_id: logEntry.client_id
      });

      // Log subscription details
      if (message.type === 'subscribe') {
        console.log(`🎧 [SUBSCRIBE] Frontend subscribing to: ${message.stream}`, {
          stream: message.stream,
          params: message.data,
          timestamp: new Date().toISOString()
        });
      }

      // Log handshake details
      if (message.type === 'status' && message.status === 'connected') {
        console.log(`🤝 [HANDSHAKE] Frontend handshake completed`, {
          status: message.status,
          client_id: message.client_id,
          timestamp: new Date().toISOString()
        });
      }

      // Log health updates
      if (message.type === 'health_update' || message.stream === 'health_check') {
        console.log(`🏥 [HEALTH] ${direction.toUpperCase()} health update`, {
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
      console.error('❌ Failed to log WebSocket message:', error);
    }
  }
}

// Create singleton instance
export const wsService = new WebSocketService();

// Types are already exported above

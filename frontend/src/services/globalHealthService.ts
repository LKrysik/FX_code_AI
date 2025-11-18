import React from 'react';
import { useHealthStore } from '@/stores/healthStore';
import { useWebSocketStore } from '@/stores/websocketStore';
import { wsService } from './websocket';
import { apiService } from './api';

interface HealthStatus {
  backend: 'healthy' | 'degraded' | 'unhealthy' | 'unknown';
  websocket: 'connected' | 'disconnected' | 'connecting' | 'error' | 'disabled';
  overall: 'healthy' | 'degraded' | 'unhealthy' | 'unknown';
  lastUpdated: number;
}

class GlobalHealthService {
  private static instance: GlobalHealthService;
  private subscribers: Set<(status: HealthStatus) => void> = new Set();
  private healthCheckInterval: NodeJS.Timeout | null = null;
  private isInitialized = false;

  private constructor() {}

  static getInstance(): GlobalHealthService {
    if (!GlobalHealthService.instance) {
      GlobalHealthService.instance = new GlobalHealthService();
    }
    return GlobalHealthService.instance;
  }

  initialize(): void {
    if (this.isInitialized) return;

    this.isInitialized = true;
    this.setupWebSocketHealth();
    this.setupPeriodicHealthCheck();
  }

  private setupWebSocketHealth(): void {
    // Listen to WebSocket health updates
    wsService.addSessionUpdateListener((message) => {
      if (message.type === 'health_check' || message.stream === 'health_check') {
        this.updateHealthFromWebSocket(message);
      }
    });

    // Listen to WebSocket connection status changes
    const unsubscribe = useWebSocketStore.subscribe(
      (state) => state.connectionStatus,
      (connectionStatus) => {
        this.updateWebSocketStatus(connectionStatus);
      }
    );

    // Store unsubscribe function for cleanup
    this.cleanupFunctions.push(unsubscribe);
  }

  private setupPeriodicHealthCheck(): void {
    // Reduced frequency - only backup check every 5 minutes
    this.healthCheckInterval = setInterval(async () => {
      try {
        const healthData = await apiService.healthCheck();
        this.updateHealthFromAPI(healthData);
      } catch (error) {
        console.warn('Global health check failed:', error);
      }
    }, 5 * 60 * 1000); // 5 minutes
  }

  private updateHealthFromWebSocket(message: any): void {
    const data = message.data || message;
    const backendStatus = this.mapBackendStatus(data.status);

    const healthStatus: HealthStatus = {
      backend: backendStatus,
      websocket: 'connected', // If we received this via WebSocket, connection is good
      overall: this.calculateOverallStatus(backendStatus, 'connected'),
      lastUpdated: Date.now(),
    };

    this.notifySubscribers(healthStatus);
    this.updateHealthStore(healthStatus);
  }

  private updateHealthFromAPI(healthData: any): void {
    const backendStatus = this.mapBackendStatus(healthData?.data?.status);
    const websocketStatus = useWebSocketStore.getState().connectionStatus;

    const healthStatus: HealthStatus = {
      backend: backendStatus,
      websocket: websocketStatus,
      overall: this.calculateOverallStatus(backendStatus, websocketStatus),
      lastUpdated: Date.now(),
    };

    this.notifySubscribers(healthStatus);
    this.updateHealthStore(healthStatus);
  }

  private updateWebSocketStatus(connectionStatus: string): void {
    const backendStatus = useHealthStore.getState().healthStatus.status as any;
    const websocketStatus = this.mapWebSocketStatus(connectionStatus);

    const healthStatus: HealthStatus = {
      backend: backendStatus,
      websocket: websocketStatus,
      overall: this.calculateOverallStatus(backendStatus, websocketStatus),
      lastUpdated: Date.now(),
    };

    this.notifySubscribers(healthStatus);
  }

  private mapBackendStatus(status?: string): 'healthy' | 'degraded' | 'unhealthy' | 'unknown' {
    switch (status) {
      case 'healthy':
      case 'ok':
        return 'healthy';
      case 'degraded':
      case 'warning':
        return 'degraded';
      case 'unhealthy':
      case 'error':
        return 'unhealthy';
      default:
        return 'unknown';
    }
  }

  private mapWebSocketStatus(status: string): 'connected' | 'disconnected' | 'connecting' | 'error' {
    switch (status) {
      case 'connected':
        return 'connected';
      case 'connecting':
        return 'connecting';
      case 'disconnected':
        return 'disconnected';
      case 'error':
        return 'error';
      default:
        return 'disconnected';
    }
  }

  private calculateOverallStatus(
    backend: 'healthy' | 'degraded' | 'unhealthy' | 'unknown',
    websocket: 'connected' | 'disconnected' | 'connecting' | 'error' | 'disabled'
  ): 'healthy' | 'degraded' | 'unhealthy' | 'unknown' {
    // WebSocket connection is critical for real-time features
    if (websocket === 'error' || websocket === 'disconnected') {
      return 'degraded';
    }

    // Backend status determines overall health
    if (backend === 'unhealthy') return 'unhealthy';
    if (backend === 'degraded') return 'degraded';
    if (backend === 'healthy') return 'healthy';

    return 'unknown';
  }

  private updateHealthStore(healthStatus: HealthStatus): void {
    useHealthStore.getState().setHealthStatus({
      status: healthStatus.overall,
    });
  }

  subscribe(callback: (status: HealthStatus) => void): () => void {
    this.subscribers.add(callback);
    return () => this.subscribers.delete(callback);
  }

  private notifySubscribers(status: HealthStatus): void {
    this.subscribers.forEach(callback => {
      try {
        callback(status);
      } catch (error) {
        console.error('Health subscriber error:', error);
      }
    });
  }

  getCurrentStatus(): HealthStatus {
    const healthStore = useHealthStore.getState();
    const wsStore = useWebSocketStore.getState();

    return {
      backend: healthStore.healthStatus.status as any,
      websocket: this.mapWebSocketStatus(wsStore.connectionStatus),
      overall: healthStore.getOverallStatus() as any,
      lastUpdated: healthStore.healthStatus.lastUpdated,
    };
  }

  private cleanupFunctions: (() => void)[] = [];

  destroy(): void {
    if (this.healthCheckInterval) {
      clearInterval(this.healthCheckInterval);
      this.healthCheckInterval = null;
    }

    this.cleanupFunctions.forEach(cleanup => cleanup());
    this.cleanupFunctions = [];
    this.subscribers.clear();
    this.isInitialized = false;
  }
}

// Export singleton instance
export const globalHealthService = GlobalHealthService.getInstance();

// React hook for using global health service
export function useGlobalHealth() {
  const [healthStatus, setHealthStatus] = React.useState<HealthStatus>(
    globalHealthService.getCurrentStatus()
  );

  React.useEffect(() => {
    // Initialize service
    globalHealthService.initialize();

    // Subscribe to updates
    const unsubscribe = globalHealthService.subscribe(setHealthStatus);

    // Cleanup
    return () => {
      unsubscribe();
    };
  }, []);

  return healthStatus;
}

// Auto-initialize when module is imported
if (typeof window !== 'undefined') {
  globalHealthService.initialize();
}
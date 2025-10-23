import { create } from 'zustand';
import { devtools } from 'zustand/middleware';

export interface HealthAlert {
  alert_id: string;
  alert_name: string;
  level: 'info' | 'warning' | 'error' | 'critical';
  message: string;
  timestamp: string;
  service?: string;
  details?: Record<string, any>;
}

export interface HealthStatus {
  status: 'healthy' | 'degraded' | 'unhealthy' | 'unknown';
  lastUpdated: number;
  alerts: HealthAlert[];
  services: Record<string, 'healthy' | 'degraded' | 'unhealthy' | 'unknown'>;
}

interface HealthStore {
  healthStatus: HealthStatus;
  setHealthStatus: (status: Partial<HealthStatus>) => void;
  addHealthAlert: (alert: HealthAlert) => void;
  clearHealthAlerts: () => void;
  updateServiceStatus: (service: string, status: 'healthy' | 'degraded' | 'unhealthy' | 'unknown') => void;
  getOverallStatus: () => 'healthy' | 'degraded' | 'unhealthy' | 'unknown';
}

const initialHealthStatus: HealthStatus = {
  status: 'unknown',
  lastUpdated: 0,
  alerts: [],
  services: {},
};

export const useHealthStore = create<HealthStore>()(
  devtools(
    (set, get) => ({
      healthStatus: initialHealthStatus,

      setHealthStatus: (updates) =>
        set((state) => {
          const newHealthStatus = {
            ...state.healthStatus,
            ...updates,
            lastUpdated: Date.now(),
          };

          // If status is being updated, also update the overall status calculation
          if (updates.status) {
            // The getOverallStatus method will use this updated status
            // No additional action needed as it's computed dynamically
          }

          return {
            healthStatus: newHealthStatus,
          };
        }),

      addHealthAlert: (alert) =>
        set((state) => {
          const newAlerts = [alert, ...state.healthStatus.alerts].slice(0, 50); // Keep last 50 alerts
          return {
            healthStatus: {
              ...state.healthStatus,
              alerts: newAlerts,
              lastUpdated: Date.now(),
            },
          };
        }),

      clearHealthAlerts: () =>
        set((state) => ({
          healthStatus: {
            ...state.healthStatus,
            alerts: [],
            lastUpdated: Date.now(),
          },
        })),

      updateServiceStatus: (service, status) =>
        set((state) => ({
          healthStatus: {
            ...state.healthStatus,
            services: {
              ...state.healthStatus.services,
              [service]: status,
            },
            lastUpdated: Date.now(),
          },
        })),

      getOverallStatus: () => {
        const { status, alerts, services } = get().healthStatus;

        // If we have a stored status from backend (via WebSocket), prioritize it
        if (status && status !== 'unknown') {
          return status;
        }

        // Fallback to alert-based calculation
        // Check for critical alerts
        const hasCriticalAlerts = alerts.some(alert => alert.level === 'critical' || alert.level === 'error');
        if (hasCriticalAlerts) return 'unhealthy';

        // Check for warning alerts
        const hasWarningAlerts = alerts.some(alert => alert.level === 'warning');
        if (hasWarningAlerts) return 'degraded';

        // Check service statuses
        const serviceStatuses = Object.values(services);
        if (serviceStatuses.includes('unhealthy')) return 'unhealthy';
        if (serviceStatuses.includes('degraded')) return 'degraded';
        if (serviceStatuses.includes('unknown')) return 'unknown';

        return 'healthy';
      },
    }),
    {
      name: 'health-store',
    }
  )
);
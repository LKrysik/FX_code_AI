/**
 * UI Store
 * ========
 * Manages global UI state: dialogs, notifications, loading states, theme
 * Replaces scattered UI state management
 */

import { create } from 'zustand';
import { devtools } from 'zustand/middleware';
import { UIState } from './types';

const initialState = {
  // Global UI States
  sidebarOpen: true,
  theme: 'dark' as const,

  // Dialog/Modal States
  dialogs: {
    strategyBuilder: false,
    backtestConfig: false,
    riskManagement: false,
    emergencyStop: false,
  },

  // Notification States
  notifications: [] as UIState['notifications'],

  // Loading States
  globalLoading: false,
  loadingStates: {} as Record<string, boolean>,
};

export const useUIStore = create<UIState>()(
  devtools(
    (set, get) => ({
      ...initialState,

      // Actions
      setSidebarOpen: (open: boolean) => {
        set({ sidebarOpen: open });
      },

      setTheme: (theme: UIState['theme']) => {
        set({ theme });
        // Persist theme preference
        if (typeof window !== 'undefined') {
          localStorage.setItem('theme', theme);
        }
      },

      openDialog: (dialog: keyof UIState['dialogs']) => {
        set(state => ({
          dialogs: {
            ...state.dialogs,
            [dialog]: true,
          },
        }));
      },

      closeDialog: (dialog: keyof UIState['dialogs']) => {
        set(state => ({
          dialogs: {
            ...state.dialogs,
            [dialog]: false,
          },
        }));
      },

      addNotification: (notification: Omit<UIState['notifications'][0], 'id' | 'timestamp'>) => {
        const id = `notification_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
        const newNotification = {
          ...notification,
          id,
          timestamp: Date.now(),
          autoHide: notification.autoHide !== false, // Default to true
        };

        set(state => ({
          notifications: [...state.notifications, newNotification],
        }));

        // Auto-remove notification after 5 seconds if autoHide is true
        if (newNotification.autoHide) {
          setTimeout(() => {
            get().removeNotification(id);
          }, 5000);
        }
      },

      removeNotification: (id: string) => {
        set(state => ({
          notifications: state.notifications.filter(n => n.id !== id),
        }));
      },

      clearNotifications: () => {
        set({ notifications: [] });
      },

      setGlobalLoading: (loading: boolean) => {
        set({ globalLoading: loading });
      },

      setLoadingState: (key: string, loading: boolean) => {
        set(state => ({
          loadingStates: {
            ...state.loadingStates,
            [key]: loading,
          },
        }));
      },

      reset: () => {
        set(initialState);
      },
    }),
    {
      name: 'ui-store',
      enabled: process.env.NODE_ENV === 'development',
    }
  )
);

// Selectors for optimized re-renders
export const useSidebarOpen = () => useUIStore(state => state.sidebarOpen);
export const useTheme = () => useUIStore(state => state.theme);
export const useDialogs = () => useUIStore(state => state.dialogs);
export const useNotifications = () => useUIStore(state => state.notifications);
export const useGlobalLoading = () => useUIStore(state => state.globalLoading);
export const useLoadingStates = () => useUIStore(state => state.loadingStates);

// Actions
export const useUIActions = () => useUIStore(state => ({
  setSidebarOpen: state.setSidebarOpen,
  setTheme: state.setTheme,
  openDialog: state.openDialog,
  closeDialog: state.closeDialog,
  addNotification: state.addNotification,
  removeNotification: state.removeNotification,
  clearNotifications: state.clearNotifications,
  setGlobalLoading: state.setGlobalLoading,
  setLoadingState: state.setLoadingState,
  reset: state.reset,
}));

// Computed selectors
export const useIsDialogOpen = (dialog: keyof UIState['dialogs']) => {
  return useUIStore(state => state.dialogs[dialog]);
};

export const useHasNotifications = () => {
  return useUIStore(state => state.notifications.length > 0);
};

export const useNotificationCount = () => {
  return useUIStore(state => state.notifications.length);
};

export const useIsLoading = (key?: string) => {
  // Always call hook unconditionally - selector handles the logic
  return useUIStore(state =>
    key ? (state.loadingStates[key] || false) : state.globalLoading
  );
};

// Initialize theme from localStorage
if (typeof window !== 'undefined') {
  const savedTheme = localStorage.getItem('theme') as UIState['theme'];
  if (savedTheme && (savedTheme === 'light' || savedTheme === 'dark')) {
    useUIStore.getState().setTheme(savedTheme);
  }
}
import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';
import { csrfService } from '@/services/csrfService';

export interface User {
  user_id: string;
  username: string;
  permissions: string[];
}

export interface AuthState {
  // State
  user: User | null;
  accessToken: string | null;
  refreshToken: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
  tokenExpiry: number | null; // Timestamp when access token expires
  refreshTimer: NodeJS.Timeout | null;

  // Actions
  login: (username: string, password: string) => Promise<boolean>;
  logout: () => Promise<void>;
  refreshToken: () => Promise<boolean>;
  clearError: () => void;
  checkAuth: () => Promise<void>;
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080';

// Helper function to schedule token refresh
const scheduleTokenRefresh = (tokenExpiry: number, refreshTokenFn: () => Promise<boolean>) => {
  const now = Date.now();
  const timeUntilExpiry = tokenExpiry - now;

  // Refresh 5 minutes before expiry, or immediately if already expired
  const refreshTime = Math.max(timeUntilExpiry - (5 * 60 * 1000), 0);

  if (refreshTime > 0) {
    return setTimeout(async () => {
      const success = await refreshTokenFn();
      if (!success) {
        console.warn('Automatic token refresh failed');
      }
    }, refreshTime);
  }

  return null;
};

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      // Initial state
      user: null,
      accessToken: null,
      refreshToken: null,
      isAuthenticated: false,
      isLoading: false,
      error: null,
      tokenExpiry: null,
      refreshTimer: null,

      // Login action
      login: async (username: string, password: string): Promise<boolean> => {
        set({ isLoading: true, error: null });

        try {
          const response = await fetch(`${API_BASE_URL}/api/v1/auth/login`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
            },
            credentials: 'include', // Include cookies
            body: JSON.stringify({ username, password }),
          });

          const data = await response.json();

          if (!response.ok) {
            throw new Error(data.error_message || 'Login failed');
          }

          const { access_token, refresh_token, user } = data.data;

          // Calculate token expiry time (access tokens are valid for token_expiry_hours)
          const tokenExpiry = Date.now() + (auth_handler.token_expiry_hours * 60 * 60 * 1000);

          // Clear any existing refresh timer
          const { refreshTimer } = get();
          if (refreshTimer) {
            clearTimeout(refreshTimer);
          }

          // Schedule automatic token refresh
          const newRefreshTimer = scheduleTokenRefresh(tokenExpiry, () => get().refreshToken());

          set({
            user,
            accessToken: access_token,
            refreshToken: refresh_token,
            isAuthenticated: true,
            isLoading: false,
            error: null,
            tokenExpiry,
            refreshTimer: newRefreshTimer,
          });

          // Fetch new CSRF token after successful login
          try {
            await csrfService.refreshToken();
          } catch (csrfError) {
            console.warn('Failed to fetch CSRF token after login:', csrfError);
          }

          return true;
        } catch (error) {
          const errorMessage = error instanceof Error ? error.message : 'Login failed';
          set({
            user: null,
            accessToken: null,
            refreshToken: null,
            isAuthenticated: false,
            isLoading: false,
            error: errorMessage,
          });
          return false;
        }
      },

      // Logout action
      logout: async (): Promise<void> => {
        const { accessToken } = get();

        set({ isLoading: true, error: null });

        try {
          if (accessToken) {
            await fetch(`${API_BASE_URL}/api/v1/auth/logout`, {
              method: 'POST',
              headers: {
                'Authorization': `Bearer ${accessToken}`,
              },
              credentials: 'include',
            });
          }
        } catch (error) {
          // Ignore logout errors
          console.warn('Logout request failed:', error);
        }

        // Clear refresh timer
        const { refreshTimer } = get();
        if (refreshTimer) {
          clearTimeout(refreshTimer);
        }

        // Clear CSRF token on logout
        csrfService.clearToken();

        // Clear state regardless of API response
        set({
          user: null,
          accessToken: null,
          refreshToken: null,
          isAuthenticated: false,
          isLoading: false,
          error: null,
          tokenExpiry: null,
          refreshTimer: null,
        });
      },

      // Refresh token action
      refreshToken: async (): Promise<boolean> => {
        const { refreshToken: currentRefreshToken } = get();

        if (!currentRefreshToken) {
          set({ error: 'No refresh token available' });
          return false;
        }

        try {
          const response = await fetch(`${API_BASE_URL}/api/v1/auth/refresh`, {
            method: 'POST',
            credentials: 'include', // Include refresh token cookie
          });

          const data = await response.json();

          if (!response.ok) {
            throw new Error(data.error_message || 'Token refresh failed');
          }

          const { access_token, refresh_token, user } = data.data;

          // Calculate new token expiry time
          const tokenExpiry = Date.now() + (auth_handler.token_expiry_hours * 60 * 60 * 1000);

          // Clear existing refresh timer
          const { refreshTimer } = get();
          if (refreshTimer) {
            clearTimeout(refreshTimer);
          }

          // Schedule new automatic token refresh
          const newRefreshTimer = scheduleTokenRefresh(tokenExpiry, () => get().refreshToken());

          set({
            user,
            accessToken: access_token,
            refreshToken: refresh_token,
            isAuthenticated: true,
            error: null,
            tokenExpiry,
            refreshTimer: newRefreshTimer,
          });

          return true;
        } catch (error) {
          const errorMessage = error instanceof Error ? error.message : 'Token refresh failed';
          set({
            user: null,
            accessToken: null,
            refreshToken: null,
            isAuthenticated: false,
            error: errorMessage,
          });
          return false;
        }
      },

      // Clear error
      clearError: () => set({ error: null }),

      // Check authentication status
      checkAuth: async (): Promise<void> => {
        const { accessToken, refreshToken: storedRefreshToken, tokenExpiry } = get();

        if (!accessToken && !storedRefreshToken) {
          set({ isAuthenticated: false });
          return;
        }

        // Check if token is expired
        const now = Date.now();
        if (tokenExpiry && now >= tokenExpiry) {
          // Token is expired, try to refresh
          if (storedRefreshToken) {
            await get().refreshToken();
          } else {
            set({ isAuthenticated: false });
          }
          return;
        }

        // If we have a valid access token, validate it
        if (accessToken) {
          try {
            const response = await fetch(`${API_BASE_URL}/health`, {
              headers: {
                'Authorization': `Bearer ${accessToken}`,
              },
            });

            if (response.ok) {
              set({ isAuthenticated: true });
              // Restore refresh timer if we have expiry info
              if (tokenExpiry && !get().refreshTimer) {
                const refreshTimer = scheduleTokenRefresh(tokenExpiry, () => get().refreshToken());
                set({ refreshTimer });
              }
            } else {
              // Token might be expired, try refresh
              if (storedRefreshToken) {
                await get().refreshToken();
              } else {
                set({ isAuthenticated: false });
              }
            }
          } catch (error) {
            // Network error, try refresh
            if (storedRefreshToken) {
              await get().refreshToken();
            } else {
              set({ isAuthenticated: false });
            }
          }
        } else if (storedRefreshToken) {
          // No access token but have refresh token, try to refresh
          await get().refreshToken();
        }
      },
    }),
    {
      name: 'auth-storage',
      storage: createJSONStorage(() => localStorage),
      // Only persist these fields
      partialize: (state) => ({
        user: state.user,
        accessToken: state.accessToken,
        refreshToken: state.refreshToken,
        isAuthenticated: state.isAuthenticated,
        tokenExpiry: state.tokenExpiry,
      }),
    }
  )
);

// Helper hook to get auth headers
export const useAuthHeaders = () => {
  const accessToken = useAuthStore((state) => state.accessToken);

  return {
    'Authorization': accessToken ? `Bearer ${accessToken}` : '',
    'Content-Type': 'application/json',
  };
};

// Helper hook to check permissions
export const useHasPermission = (permission: string) => {
  const user = useAuthStore((state) => state.user);
  return user?.permissions?.includes(permission) ?? false;
};
import { config, debugLog, errorLog } from '@/utils/config';

interface User {
  user_id: string;
  username: string;
  permissions: string[];
}
/**
 * AuthService
 * =============
 * Handles JWT authentication, including login, token refresh, and automatic
 * authorization for API calls.
 */
class AuthService {
  private token: string | null = null; private refreshToken: string | null = null; private currentUser: User | null = null;

  constructor() {
    if (typeof window !== 'undefined') {
      // Tokens are in HttpOnly cookies, load user from localStorage
      const userStr = localStorage.getItem('current_user');
      if (userStr) {
        try {
          this.currentUser = JSON.parse(userStr);
        } catch (e) {
          console.warn('Failed to parse current_user from localStorage', e);
        }
      }
    }
  }

  private getApiUrl(path: string): string {
    // Ensure the path starts with a slash
    const formattedPath = path.startsWith('/') ? path : `/${path}`;
    return `${config.apiUrl}${formattedPath}`;
  }

  async login(username: string, password: string): Promise<any> {
    debugLog('Attempting login...', { username });
    try {
      const response = await fetch(this.getApiUrl('/api/v1/auth/login'), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify({ username, password }),
      });

      const data = await response.json();
      console.log('Login response status:', response.status, response.ok);
      console.log('Login raw response data:', data);
      debugLog('Login response data:', data);
      if (!response.ok) {
        throw new Error(data.error_message || 'Login failed');
      }

      // Store user info (tokens are in HttpOnly cookies)
      this.currentUser = data.data.user;
      this.token = data.data.access_token || null;
      this.refreshToken = data.data.refresh_token || null;
      localStorage.setItem('current_user', JSON.stringify(this.currentUser));

      debugLog('Login successful', { user: data.user });
      return data;
    } catch (error) {
      errorLog('Login error:', error);
      throw error;
    }
  }

  async refreshAccessToken(): Promise<any> {
    if (!this.refreshToken) {
      throw new Error('No refresh token available.');
    }
    debugLog('Refreshing access token...');
    try {
      const response = await fetch(this.getApiUrl('/api/v1/auth/refresh'), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify({ refresh_token: this.refreshToken }),
      });

      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.error_message || 'Token refresh failed');
      }

      // Update user info (tokens are in HttpOnly cookies)
      this.currentUser = data.data.user;
      localStorage.setItem('current_user', JSON.stringify(this.currentUser));

      debugLog('Token refresh successful');
      return data;
    } catch (error) {
      errorLog('Token refresh error:', error);
      // Clear tokens on refresh failure to force re-login
      this.logout();
      throw error;
    }
  }

  logout(): void {
    debugLog('Logging out');
    this.token = null;
    this.refreshToken = null;
    this.currentUser = null;
    localStorage.removeItem('current_user');
  }

  getAuthHeaders(): Record<string, string> {
    // Tokens are sent automatically via HttpOnly cookies
    return {
      'Content-Type': 'application/json',
    };
  }

  isAuthenticated(): boolean {
    return !!this.currentUser;
  }


  getCurrentUser(): User | null {
    return this.currentUser;
  }

  // Helper method for authenticated API calls
  async apiCall(path: string, options: RequestInit = {}): Promise<Response> {
    const headers = {
      ...this.getAuthHeaders(),
      ...options.headers,
    };

    try {
      let response = await fetch(this.getApiUrl(path), { ...options, headers, credentials: 'include' });

      // If we get a 401 and have a refresh token, try to refresh and retry
      if (response.status === 401 && this.refreshToken) {
        debugLog('Received 401, attempting token refresh...');
        await this.refreshAccessToken();

        // Retry the original request with the new token
        debugLog('Retrying original API call...', { path });
        response = await fetch(this.getApiUrl(path), {
          ...options,
          headers: {
            ...this.getAuthHeaders(),
            ...options.headers,
          },
          credentials: 'include',
        });
      }

      return response;
    } catch (error) {
      errorLog('API call error:', error);
      throw error;
    }
  }

  async ensureSession(): Promise<boolean> {
    if (typeof window === 'undefined') {
      return this.isAuthenticated();
    }

    if (!this.isAuthenticated()) {
      return false;
    }

    try {
      const response = await fetch(this.getApiUrl('/api/v1/auth/refresh'), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
      });

      if (!response.ok) {
        throw new Error(`Session check failed: ${response.status}`);
      }

      const data = await response.json();
      this.currentUser = data?.data?.user || this.currentUser;
      this.token = data?.data?.access_token || this.token;
      this.refreshToken = data?.data?.refresh_token || this.refreshToken;

      if (this.currentUser) {
        localStorage.setItem('current_user', JSON.stringify(this.currentUser));
      }

      return true;
    } catch (error) {
      debugLog('ensureSession failed, clearing auth state', error);
      this.logout();
      return false;
    }
  }
}

// Create a singleton instance
export const authService = new AuthService();

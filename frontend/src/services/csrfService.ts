/**
 * CSRF Token Service
 * ===================
 * Handles CSRF token fetching, storage, and automatic injection into API requests.
 *
 * Architecture:
 * - Fetches tokens from backend GET /csrf-token endpoint
 * - Stores tokens in memory (not localStorage for security)
 * - Automatically refreshes on expiry (403 csrf_expired errors)
 * - Thread-safe with single-inflight request deduplication
 *
 * Usage:
 *   await csrfService.initialize();  // On app startup
 *   const token = await csrfService.getToken();  // Get current token
 *   await csrfService.refreshToken();  // Force refresh
 */

import { config } from '@/utils/config';

interface CsrfTokenResponse {
  type: string;
  data: {
    token: string;
    expires_in: number; // Backend returns relative seconds from now
  };
}

class CsrfService {
  private token: string | null = null;
  private expiresAt: number | null = null;
  private refreshPromise: Promise<string> | null = null;

  /**
   * Initialize CSRF service by fetching initial token
   * Should be called on app startup
   */
  async initialize(): Promise<void> {
    try {
      await this.fetchNewToken();
    } catch (error) {
      console.error('[CSRF] Failed to initialize CSRF token:', error);
      // Don't throw - allow app to start even if CSRF fetch fails
      // Token will be fetched on first request
    }
  }

  /**
   * Get current CSRF token, refreshing if expired or missing
   * Thread-safe - multiple simultaneous calls will deduplicate to single request
   */
  async getToken(): Promise<string> {
    // If token exists and not expired, return it
    if (this.token && this.expiresAt && Date.now() < this.expiresAt) {
      return this.token;
    }

    // If refresh already in progress, wait for it
    if (this.refreshPromise) {
      return this.refreshPromise;
    }

    // Otherwise, fetch new token
    return this.fetchNewToken();
  }

  /**
   * Force refresh of CSRF token
   * Used when backend returns 403 csrf_expired error
   */
  async refreshToken(): Promise<string> {
    // Clear existing token
    this.token = null;
    this.expiresAt = null;

    // If refresh already in progress, wait for it
    if (this.refreshPromise) {
      return this.refreshPromise;
    }

    return this.fetchNewToken();
  }

  /**
   * Clear stored token (e.g., on logout)
   */
  clearToken(): void {
    this.token = null;
    this.expiresAt = null;
    this.refreshPromise = null;
  }

  /**
   * Internal: Fetch new token from backend
   * Deduplicates simultaneous requests
   */
  private async fetchNewToken(): Promise<string> {
    // Create new fetch promise
    this.refreshPromise = this.doFetchToken();

    try {
      const token = await this.refreshPromise;
      return token;
    } finally {
      this.refreshPromise = null;
    }
  }

  /**
   * Internal: Actual token fetch implementation
   */
  private async doFetchToken(): Promise<string> {
    try {
      const response = await fetch(`${config.apiUrl}/csrf-token`, {
        method: 'GET',
        credentials: 'include', // Include cookies
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        throw new Error(`CSRF token fetch failed: ${response.status} ${response.statusText}`);
      }

      const data: CsrfTokenResponse = await response.json();

      if (!data.data?.token || !data.data?.expires_in) {
        throw new Error('Invalid CSRF token response: missing token or expires_in');
      }

      // Store token and calculate absolute expiry time from relative expires_in
      this.token = data.data.token;
      this.expiresAt = Date.now() + (data.data.expires_in * 1000); // Convert relative seconds to absolute ms timestamp

      console.debug('[CSRF] Token fetched successfully', {
        expires_at: new Date(this.expiresAt).toISOString(),
        expires_in_seconds: data.data.expires_in,
      });

      return this.token;
    } catch (error) {
      console.error('[CSRF] Failed to fetch token:', error);
      throw error;
    }
  }

  /**
   * Check if current token is valid (exists and not expired)
   */
  isTokenValid(): boolean {
    return !!(this.token && this.expiresAt && Date.now() < this.expiresAt);
  }

  /**
   * Get token expiry timestamp
   */
  getTokenExpiry(): number | null {
    return this.expiresAt;
  }
}

// Export singleton instance
export const csrfService = new CsrfService();
export default csrfService;

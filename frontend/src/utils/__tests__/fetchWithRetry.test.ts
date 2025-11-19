/**
 * Unit tests for fetchWithRetry utility
 *
 * Tests cover:
 * - Successful requests (no retry)
 * - Server errors with retry (5xx)
 * - Client errors without retry (4xx)
 * - Network errors with retry
 * - AbortController cancellation
 * - Exponential backoff timing
 */

import { fetchWithRetry, FetchRetryError, isFetchRetryError, isAbortError } from '../fetchWithRetry';

// Mock Response class for Node.js environment
class MockResponse {
  ok: boolean;
  status: number;
  statusText: string;
  body: any;

  constructor(body: any, init: { status: number; statusText?: string } = { status: 200 }) {
    this.body = body;
    this.status = init.status;
    this.statusText = init.statusText || (init.status === 200 ? 'OK' : 'Error');
    this.ok = init.status >= 200 && init.status < 300;
  }

  async json() {
    return this.body;
  }

  async text() {
    return String(this.body);
  }
}

// Make MockResponse available globally
(global as any).Response = MockResponse;

describe('fetchWithRetry', () => {
  beforeEach(() => {
    // Clear all mocks before each test
    jest.clearAllMocks();
    jest.restoreAllMocks();
  });

  describe('successful requests', () => {
    it('returns response immediately on success', async () => {
      const mockResponse = new Response('success', { status: 200 });
      global.fetch = jest.fn().mockResolvedValue(mockResponse);

      const response = await fetchWithRetry('https://api.example.com/data');

      expect(response).toBe(mockResponse);
      expect(global.fetch).toHaveBeenCalledTimes(1);
    });

    it('does not retry on successful request', async () => {
      global.fetch = jest.fn().mockResolvedValue(
        new Response('success', { status: 200 })
      );

      await fetchWithRetry('https://api.example.com/data', { maxRetries: 3 });

      expect(global.fetch).toHaveBeenCalledTimes(1);
    });
  });

  describe('client errors (4xx)', () => {
    it('does not retry on 401 Unauthorized', async () => {
      const mockResponse = new Response('unauthorized', { status: 401 });
      global.fetch = jest.fn().mockResolvedValue(mockResponse);

      const response = await fetchWithRetry('https://api.example.com/data');

      expect(response.status).toBe(401);
      expect(global.fetch).toHaveBeenCalledTimes(1);
    });

    it('does not retry on 404 Not Found', async () => {
      const mockResponse = new Response('not found', { status: 404 });
      global.fetch = jest.fn().mockResolvedValue(mockResponse);

      const response = await fetchWithRetry('https://api.example.com/data');

      expect(response.status).toBe(404);
      expect(global.fetch).toHaveBeenCalledTimes(1);
    });

    it('does not retry on 400 Bad Request', async () => {
      global.fetch = jest.fn().mockResolvedValue(
        new Response('bad request', { status: 400 })
      );

      const response = await fetchWithRetry('https://api.example.com/data', {
        maxRetries: 3,
      });

      expect(response.status).toBe(400);
      expect(global.fetch).toHaveBeenCalledTimes(1);
    });
  });

  describe('server errors (5xx)', () => {
    it('retries on 500 Internal Server Error', async () => {
      global.fetch = jest
        .fn()
        .mockResolvedValueOnce(new Response('error', { status: 500 }))
        .mockResolvedValueOnce(new Response('error', { status: 500 }))
        .mockResolvedValueOnce(new Response('success', { status: 200 }));

      const response = await fetchWithRetry('https://api.example.com/data', {
        maxRetries: 3,
        baseDelay: 10, // Short delay for testing
      });

      expect(response.status).toBe(200);
      expect(global.fetch).toHaveBeenCalledTimes(3);
    });

    it('retries on 503 Service Unavailable', async () => {
      global.fetch = jest
        .fn()
        .mockResolvedValueOnce(new Response('error', { status: 503 }))
        .mockResolvedValueOnce(new Response('success', { status: 200 }));

      const response = await fetchWithRetry('https://api.example.com/data', {
        maxRetries: 2,
        baseDelay: 10,
      });

      expect(response.status).toBe(200);
      expect(global.fetch).toHaveBeenCalledTimes(2);
    });

    it('throws FetchRetryError after exhausting retries', async () => {
      global.fetch = jest.fn().mockResolvedValue(
        new Response('error', { status: 500 })
      );

      await expect(
        fetchWithRetry('https://api.example.com/data', {
          maxRetries: 2,
          baseDelay: 10,
        })
      ).rejects.toThrow(FetchRetryError);

      expect(global.fetch).toHaveBeenCalledTimes(3); // Initial + 2 retries
    });
  });

  describe('network errors', () => {
    it('retries on network error', async () => {
      global.fetch = jest
        .fn()
        .mockRejectedValueOnce(new Error('Network error'))
        .mockResolvedValueOnce(new Response('success', { status: 200 }));

      const response = await fetchWithRetry('https://api.example.com/data', {
        maxRetries: 2,
        baseDelay: 10,
      });

      expect(response.status).toBe(200);
      expect(global.fetch).toHaveBeenCalledTimes(2);
    });

    it('throws FetchRetryError after exhausting retries on network error', async () => {
      global.fetch = jest.fn().mockRejectedValue(new Error('Network error'));

      await expect(
        fetchWithRetry('https://api.example.com/data', {
          maxRetries: 2,
          baseDelay: 10,
        })
      ).rejects.toThrow(FetchRetryError);

      expect(global.fetch).toHaveBeenCalledTimes(3);
    });
  });

  describe('AbortController', () => {
    it('does not retry on AbortError', async () => {
      const abortError = new Error('Aborted');
      abortError.name = 'AbortError';

      global.fetch = jest.fn().mockRejectedValue(abortError);

      await expect(
        fetchWithRetry('https://api.example.com/data', { maxRetries: 3 })
      ).rejects.toThrow('Aborted');

      expect(global.fetch).toHaveBeenCalledTimes(1);
    });

    it('respects AbortSignal from options', async () => {
      const controller = new AbortController();
      global.fetch = jest.fn().mockImplementation(async () => {
        controller.abort();
        const abortError = new Error('Aborted');
        abortError.name = 'AbortError';
        throw abortError;
      });

      await expect(
        fetchWithRetry('https://api.example.com/data', {
          signal: controller.signal,
        })
      ).rejects.toThrow('Aborted');

      expect(global.fetch).toHaveBeenCalledTimes(1);
    });
  });

  describe('exponential backoff', () => {
    it('uses exponential backoff delays', async () => {
      const startTime = Date.now();
      const delays: number[] = [];

      global.fetch = jest
        .fn()
        .mockRejectedValueOnce(new Error('Error 1'))
        .mockRejectedValueOnce(new Error('Error 2'))
        .mockResolvedValueOnce(new Response('success', { status: 200 }));

      // Mock setTimeout to capture delays
      const originalSetTimeout = global.setTimeout;
      global.setTimeout = jest.fn((fn, delay) => {
        delays.push(delay as number);
        return originalSetTimeout(fn as () => void, 0); // Execute immediately for test speed
      }) as any;

      await fetchWithRetry('https://api.example.com/data', {
        maxRetries: 3,
        baseDelay: 100,
      });

      // Restore setTimeout
      global.setTimeout = originalSetTimeout;

      expect(delays).toEqual([
        100, // First retry: 100ms
        200, // Second retry: 200ms
      ]);
    });

    it('respects custom baseDelay', async () => {
      const delays: number[] = [];

      global.fetch = jest
        .fn()
        .mockRejectedValueOnce(new Error('Error'))
        .mockResolvedValueOnce(new Response('success', { status: 200 }));

      const originalSetTimeout = global.setTimeout;
      global.setTimeout = jest.fn((fn, delay) => {
        delays.push(delay as number);
        return originalSetTimeout(fn as () => void, 0);
      }) as any;

      await fetchWithRetry('https://api.example.com/data', {
        maxRetries: 2,
        baseDelay: 500,
      });

      global.setTimeout = originalSetTimeout;

      expect(delays).toEqual([500]);
    });
  });

  describe('FetchRetryError', () => {
    it('includes attempt count in error', async () => {
      global.fetch = jest.fn().mockRejectedValue(new Error('Network error'));

      try {
        await fetchWithRetry('https://api.example.com/data', {
          maxRetries: 2,
          baseDelay: 10,
        });
        fail('Should have thrown FetchRetryError');
      } catch (error) {
        expect(isFetchRetryError(error)).toBe(true);
        if (isFetchRetryError(error)) {
          expect(error.attemptCount).toBe(3); // Initial + 2 retries
        }
      }
    });

    it('includes last error in FetchRetryError', async () => {
      const networkError = new Error('Connection refused');
      global.fetch = jest.fn().mockRejectedValue(networkError);

      try {
        await fetchWithRetry('https://api.example.com/data', {
          maxRetries: 1,
          baseDelay: 10,
        });
        fail('Should have thrown FetchRetryError');
      } catch (error) {
        if (isFetchRetryError(error)) {
          expect(error.lastError).toBe(networkError);
        }
      }
    });
  });

  describe('helper functions', () => {
    it('isFetchRetryError identifies FetchRetryError', () => {
      const error = new FetchRetryError('Test error', 3, null);
      expect(isFetchRetryError(error)).toBe(true);
      expect(isFetchRetryError(new Error('Regular error'))).toBe(false);
      expect(isFetchRetryError('not an error')).toBe(false);
    });

    it('isAbortError identifies AbortError', () => {
      const abortError = new Error('Aborted');
      abortError.name = 'AbortError';

      expect(isAbortError(abortError)).toBe(true);
      expect(isAbortError(new Error('Regular error'))).toBe(false);
      expect(isAbortError('not an error')).toBe(false);
    });
  });

  describe('configuration', () => {
    it('respects custom maxRetries', async () => {
      global.fetch = jest.fn().mockRejectedValue(new Error('Network error'));

      await expect(
        fetchWithRetry('https://api.example.com/data', {
          maxRetries: 5,
          baseDelay: 10,
        })
      ).rejects.toThrow(FetchRetryError);

      expect(global.fetch).toHaveBeenCalledTimes(6); // Initial + 5 retries
    });

    it('works with maxRetries=0 (no retry)', async () => {
      global.fetch = jest.fn().mockRejectedValue(new Error('Network error'));

      await expect(
        fetchWithRetry('https://api.example.com/data', {
          maxRetries: 0,
          baseDelay: 10,
        })
      ).rejects.toThrow(FetchRetryError);

      expect(global.fetch).toHaveBeenCalledTimes(1); // Only initial attempt
    });

    it('passes through fetch options', async () => {
      const mockResponse = new Response('success', { status: 200 });
      global.fetch = jest.fn().mockResolvedValue(mockResponse);

      const headers = { 'Authorization': 'Bearer token123' };
      await fetchWithRetry('https://api.example.com/data', {
        method: 'POST',
        headers,
        body: JSON.stringify({ test: 'data' }),
      });

      expect(global.fetch).toHaveBeenCalledWith(
        'https://api.example.com/data',
        expect.objectContaining({
          method: 'POST',
          headers,
          body: JSON.stringify({ test: 'data' }),
        })
      );
    });
  });
});

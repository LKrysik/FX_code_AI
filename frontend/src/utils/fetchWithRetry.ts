/**
 * Fetch utility with exponential backoff retry mechanism
 *
 * Automatically retries failed requests with exponential delays:
 * - Attempt 1: immediate
 * - Attempt 2: 1s delay
 * - Attempt 3: 2s delay
 * - Attempt 4: 4s delay
 *
 * Only retries server errors (5xx) and network errors.
 * Does not retry client errors (4xx) or aborted requests.
 */

export interface FetchWithRetryOptions extends RequestInit {
  maxRetries?: number;
  baseDelay?: number;
}

export class FetchRetryError extends Error {
  constructor(
    message: string,
    public readonly attemptCount: number,
    public readonly lastError: Error | null
  ) {
    super(message);
    this.name = 'FetchRetryError';

    // Maintain proper prototype chain for instanceof checks
    // https://github.com/Microsoft/TypeScript/wiki/Breaking-Changes#extending-built-ins-like-error-array-and-map-may-no-longer-work
    Object.setPrototypeOf(this, FetchRetryError.prototype);
  }
}

/**
 * Fetch with automatic retry for transient errors
 *
 * @param url - The URL to fetch
 * @param options - Fetch options including retry configuration
 * @returns Promise resolving to Response
 * @throws FetchRetryError if all retries exhausted
 * @throws AbortError if request was aborted (not retried)
 */
export async function fetchWithRetry(
  url: string,
  options: FetchWithRetryOptions = {}
): Promise<Response> {
  const {
    maxRetries = 3,
    baseDelay = 1000,
    ...fetchOptions
  } = options;

  let lastError: Error | null = null;
  let attempt = 0;

  for (attempt = 0; attempt <= maxRetries; attempt++) {
    try {
      const response = await fetch(url, fetchOptions);

      // Success - return immediately
      if (response.ok) {
        return response;
      }

      // Client errors (4xx) - don't retry, return immediately
      // User might need to fix authentication, permissions, etc.
      if (response.status >= 400 && response.status < 500) {
        return response;
      }

      // Server errors (5xx) - will retry
      lastError = new Error(`Server error: ${response.status} ${response.statusText}`);

      // If we have retries left, wait before next attempt
      if (attempt < maxRetries) {
        const delay = baseDelay * Math.pow(2, attempt); // Exponential backoff
        await new Promise(resolve => setTimeout(resolve, delay));
        continue;
      }

      // No more retries - throw error
      throw new FetchRetryError(
        `Fetch failed after ${attempt + 1} attempts: ${lastError.message}`,
        attempt + 1,
        lastError
      );

    } catch (error) {
      // AbortError - user cancelled, don't retry
      if (error instanceof Error && error.name === 'AbortError') {
        throw error;
      }

      // FetchRetryError - already wrapped, re-throw
      if (error instanceof FetchRetryError) {
        throw error;
      }

      // Network errors - will retry
      lastError = error instanceof Error
        ? error
        : new Error('Unknown network error');

      // If we have retries left, wait before next attempt
      if (attempt < maxRetries) {
        const delay = baseDelay * Math.pow(2, attempt);
        await new Promise(resolve => setTimeout(resolve, delay));
        continue;
      }

      // No more retries - throw wrapped error
      throw new FetchRetryError(
        `Fetch failed after ${attempt + 1} attempts: ${lastError.message}`,
        attempt + 1,
        lastError
      );
    }
  }

  // Fallback (should never reach here due to throws above)
  throw new FetchRetryError(
    `Fetch failed after ${attempt} attempts`,
    attempt,
    lastError
  );
}

/**
 * Check if an error is a FetchRetryError
 */
export function isFetchRetryError(error: unknown): error is FetchRetryError {
  return error instanceof FetchRetryError;
}

/**
 * Check if an error is an AbortError
 */
export function isAbortError(error: unknown): error is Error {
  return error instanceof Error && error.name === 'AbortError';
}

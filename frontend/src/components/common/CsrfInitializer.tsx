'use client';

/**
 * CSRF Token Initializer Component
 * ==================================
 * Initializes CSRF token service on app startup.
 * Automatically fetches initial CSRF token when component mounts.
 *
 * Architecture:
 * - Runs once on app initialization
 * - Non-blocking - app continues loading even if CSRF fetch fails
 * - Tokens will be fetched on-demand if initial fetch fails
 *
 * Usage:
 *   Add to root layout or app component
 */

import { useEffect, useState } from 'react';
import { csrfService } from '@/services/csrfService';
import { Logger } from '@/services/frontendLogService';

export default function CsrfInitializer() {
  const [initialized, setInitialized] = useState(false);

  useEffect(() => {
    const initializeCsrf = async () => {
      try {
        Logger.debug('CsrfInitializer.init', 'Initializing CSRF service...');
        await csrfService.initialize();
        Logger.debug('CsrfInitializer.init', 'CSRF service initialized successfully');
        setInitialized(true);
      } catch (error) {
        Logger.warn('CsrfInitializer.init', { message: 'Failed to initialize CSRF service (will retry on first request)', error });
        // Don't block app initialization - token will be fetched on first request
        setInitialized(true);
      }
    };

    initializeCsrf();
  }, []);

  // This component doesn't render anything
  return null;
}

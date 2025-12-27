'use client';

import { useEffect } from 'react';
import { frontendLogService } from '@/services/frontendLogService';

/**
 * Initializes the frontend error logging service.
 * Place this component in the root layout to capture all errors.
 *
 * This component renders nothing - it only initializes the logging service.
 */
export default function FrontendLogInitializer() {
  useEffect(() => {
    // Initialize on mount
    frontendLogService.init();

    // Cleanup on unmount (rarely happens for root component)
    return () => {
      frontendLogService.destroy();
    };
  }, []);

  return null;
}

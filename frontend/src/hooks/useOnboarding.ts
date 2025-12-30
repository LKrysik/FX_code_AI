/**
 * useOnboarding Hook
 * ==================
 * Story 1A-7: First-Visit Onboarding Tooltip (AC1, AC4)
 *
 * Manages first-visit onboarding state using localStorage.
 * Determines if the user has seen the onboarding tooltip and
 * provides functions to dismiss or reset it.
 *
 * @example
 * ```tsx
 * const { showOnboarding, dismissOnboarding } = useOnboarding();
 *
 * if (showOnboarding) {
 *   return <WelcomeTooltip onDismiss={dismissOnboarding} />;
 * }
 * ```
 */

import { useState, useCallback } from 'react';
import { Logger } from '@/services/frontendLogService';

const STORAGE_KEY = 'hasSeenOnboarding';

export interface UseOnboardingReturn {
  /** Whether to show onboarding (true on first visit) */
  showOnboarding: boolean;
  /** Call to dismiss onboarding and persist the choice */
  dismissOnboarding: () => void;
  /** Call to reset onboarding (show again on next visit) */
  resetOnboarding: () => void;
}

/**
 * Safely read from localStorage
 */
function getStorageValue(): boolean {
  try {
    const value = localStorage.getItem(STORAGE_KEY);
    return value === 'true';
  } catch (error) {
    Logger.warn('useOnboarding.localStorage_read_failed', {
      message: 'Failed to read localStorage',
    });
    return false;
  }
}

/**
 * Safely write to localStorage
 */
function setStorageValue(value: boolean): void {
  try {
    if (value) {
      localStorage.setItem(STORAGE_KEY, 'true');
    } else {
      localStorage.removeItem(STORAGE_KEY);
    }
  } catch (error) {
    Logger.warn('useOnboarding.localStorage_write_failed', {
      message: 'Failed to write to localStorage',
    });
  }
}

/**
 * Hook to manage first-visit onboarding state
 *
 * - Checks localStorage for `hasSeenOnboarding` flag
 * - Shows tooltip if flag is not set
 * - Sets flag after dismissal
 * - Provides reset option for settings page
 *
 * @returns UseOnboardingReturn
 */
export function useOnboarding(): UseOnboardingReturn {
  const [hasSeenOnboarding, setHasSeenOnboarding] = useState<boolean>(() => {
    return getStorageValue();
  });

  /**
   * Dismiss onboarding and persist to localStorage
   * Called when user clicks "Got it!" button
   */
  const dismissOnboarding = useCallback(() => {
    setStorageValue(true);
    setHasSeenOnboarding(true);
  }, []);

  /**
   * Reset onboarding state (for settings page)
   * Allows user to see the onboarding again
   */
  const resetOnboarding = useCallback(() => {
    setStorageValue(false);
    setHasSeenOnboarding(false);
  }, []);

  return {
    showOnboarding: !hasSeenOnboarding,
    dismissOnboarding,
    resetOnboarding,
  };
}

export default useOnboarding;

/**
 * Error Components Index
 * ======================
 * Centralized exports for error display components.
 *
 * Story: 0-5-error-display-pattern
 */

export { ErrorToast, ErrorToastStack } from './ErrorToast';
export { WebSocketBanner, GenericBanner } from './ErrorBanner';
export {
  CriticalErrorModal,
  useCriticalErrorStore,
  triggerCriticalError,
  type CriticalError,
  type CriticalErrorType,
} from './CriticalErrorModal';

// Error severity levels (from story spec)
export const ERROR_SEVERITY = {
  INFO: 'info',
  WARNING: 'warning',
  ERROR: 'error',
  CRITICAL: 'critical',
} as const;

export type ErrorSeverity = typeof ERROR_SEVERITY[keyof typeof ERROR_SEVERITY];

// Auto-dismiss configuration
export const ERROR_AUTO_DISMISS: Record<ErrorSeverity, number | null> = {
  info: 3000,
  warning: 5000,
  error: null, // Persist until dismissed
  critical: null, // Never auto-dismiss (requires action)
};

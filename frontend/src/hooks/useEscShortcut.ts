/**
 * useEscShortcut Hook
 * ====================
 * Story: 1b-8-emergency-stop-button
 *
 * Global keyboard shortcut hook for triggering emergency stop via Escape key.
 * This hook integrates with the settings store to respect user preferences.
 *
 * Acceptance Criteria:
 * - AC3: Pressing Esc key shows confirmation dialog
 * - AC10: Settings option to toggle "Esc to stop session" on/off
 */

import { useEffect, useCallback, useState, useRef } from 'react';
import { Logger } from '@/services/frontendLogService';

export interface UseEscShortcutOptions {
  /** Whether the shortcut is enabled (default: true) */
  enabled?: boolean;
  /** Callback when Esc is pressed */
  onEscPress: () => void;
  /** Whether a session is currently active (only trigger when true) */
  isSessionActive?: boolean;
  /** Prevent triggering when inside input/textarea elements */
  preventInInputs?: boolean;
  /** Prevent triggering when a dialog is already open */
  preventWhenDialogOpen?: boolean;
  /** Current dialog open state (to prevent double-triggering) */
  isDialogOpen?: boolean;
}

export interface UseEscShortcutReturn {
  /** Whether the shortcut is currently active */
  isActive: boolean;
  /** Whether the shortcut is enabled in settings */
  isEnabled: boolean;
  /** Manually trigger the Esc action */
  triggerEsc: () => void;
  /** Last time Esc was pressed (for debugging) */
  lastTriggered: Date | null;
}

/**
 * Hook for handling global Esc key shortcut for emergency stop
 *
 * Features:
 * - Respects settings preference for enabling/disabling
 * - Only triggers when session is active
 * - Prevents triggering inside input elements
 * - Debounces rapid key presses
 *
 * Usage:
 * ```tsx
 * const { isActive } = useEscShortcut({
 *   enabled: settings.shortcuts.shortcutsEnabled,
 *   onEscPress: () => setShowConfirmDialog(true),
 *   isSessionActive: currentSession !== null,
 *   isDialogOpen: showConfirmDialog,
 * });
 * ```
 */
export function useEscShortcut(options: UseEscShortcutOptions): UseEscShortcutReturn {
  const {
    enabled = true,
    onEscPress,
    isSessionActive = false,
    preventInInputs = true,
    preventWhenDialogOpen = true,
    isDialogOpen = false,
  } = options;

  const [lastTriggered, setLastTriggered] = useState<Date | null>(null);
  const debounceRef = useRef<number>(0);
  const callbackRef = useRef(onEscPress);

  // Keep callback ref up to date
  useEffect(() => {
    callbackRef.current = onEscPress;
  }, [onEscPress]);

  // Whether the shortcut is currently active (enabled + session active)
  const isActive = enabled && isSessionActive;

  const triggerEsc = useCallback(() => {
    if (!enabled) {
      Logger.debug('useEscShortcut.trigger_blocked', {
        reason: 'shortcut_disabled',
        message: 'Esc shortcut is disabled in settings',
      });
      return;
    }

    if (!isSessionActive) {
      Logger.debug('useEscShortcut.trigger_blocked', {
        reason: 'no_active_session',
        message: 'No active session to stop',
      });
      return;
    }

    if (preventWhenDialogOpen && isDialogOpen) {
      Logger.debug('useEscShortcut.trigger_blocked', {
        reason: 'dialog_already_open',
        message: 'Confirmation dialog is already open',
      });
      return;
    }

    Logger.info('useEscShortcut.triggered', {
      message: 'Esc shortcut triggered for emergency stop',
    });

    setLastTriggered(new Date());
    callbackRef.current();
  }, [enabled, isSessionActive, preventWhenDialogOpen, isDialogOpen]);

  const handleKeyDown = useCallback((event: KeyboardEvent) => {
    // Only handle Escape key
    if (event.key !== 'Escape') return;

    // Check if disabled
    if (!enabled) return;

    // Check if session is active
    if (!isSessionActive) return;

    // Check if dialog is already open (handled by dialog's own key handler)
    if (preventWhenDialogOpen && isDialogOpen) return;

    // Check if we're in an input element
    if (preventInInputs) {
      const target = event.target as HTMLElement | null;
      const tagName = target?.tagName?.toLowerCase();

      // Skip if inside input, textarea, select, or contenteditable
      if (
        tagName === 'input' ||
        tagName === 'textarea' ||
        tagName === 'select' ||
        target?.isContentEditable
      ) {
        Logger.debug('useEscShortcut.blocked_in_input', {
          element: tagName,
          message: 'Esc shortcut blocked - focus is on input element',
        });
        return;
      }
    }

    // Debounce rapid key presses (prevent double-triggering)
    const now = Date.now();
    if (now - debounceRef.current < 300) {
      Logger.debug('useEscShortcut.debounced', {
        message: 'Esc shortcut debounced - too rapid',
      });
      return;
    }
    debounceRef.current = now;

    // Prevent default browser behavior
    event.preventDefault();
    event.stopPropagation();

    triggerEsc();
  }, [enabled, isSessionActive, preventInInputs, preventWhenDialogOpen, isDialogOpen, triggerEsc]);

  // Add/remove global keyboard listener
  useEffect(() => {
    if (enabled && isSessionActive) {
      window.addEventListener('keydown', handleKeyDown);

      Logger.debug('useEscShortcut.listener_added', {
        message: 'Global Esc listener registered',
      });

      return () => {
        window.removeEventListener('keydown', handleKeyDown);
        Logger.debug('useEscShortcut.listener_removed', {
          message: 'Global Esc listener unregistered',
        });
      };
    }
  }, [enabled, isSessionActive, handleKeyDown]);

  return {
    isActive,
    isEnabled: enabled,
    triggerEsc,
    lastTriggered,
  };
}

export default useEscShortcut;

/**
 * Keyboard Shortcuts Hook (SY-01)
 * ================================
 *
 * Global keyboard shortcuts for the trading application.
 *
 * Features:
 * - ESC: Emergency stop all sessions
 * - C: Close current position
 * - D: Navigate to Dashboard
 * - T: Navigate to Trading Session
 * - S: Navigate to Session History
 * - +/-: Zoom in/out chart
 * - F: Toggle fullscreen
 *
 * Related: docs/UI_BACKLOG.md (SY-01, KEYBOARD SHORTCUTS)
 */

import { useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { Logger } from '@/services/frontendLogService';

export interface KeyboardShortcuts {
  emergencyStop: string;
  closePosition: string;
  goToDashboard: string;
  goToTrading: string;
  goToHistory: string;
  zoomIn: string;
  zoomOut: string;
  fullscreen: string;
  shortcutsEnabled: boolean;
}

interface UseKeyboardShortcutsOptions {
  shortcuts?: KeyboardShortcuts;
  onEmergencyStop?: () => void;
  onClosePosition?: () => void;
  onZoomIn?: () => void;
  onZoomOut?: () => void;
  onFullscreen?: () => void;
}

const DEFAULT_SHORTCUTS: KeyboardShortcuts = {
  emergencyStop: 'Escape',
  closePosition: 'c',
  goToDashboard: 'd',
  goToTrading: 't',
  goToHistory: 's',
  zoomIn: '+',
  zoomOut: '-',
  fullscreen: 'f',
  shortcutsEnabled: true,
};

export function useKeyboardShortcuts(options: UseKeyboardShortcutsOptions = {}) {
  const router = useRouter();
  const {
    shortcuts = DEFAULT_SHORTCUTS,
    onEmergencyStop,
    onClosePosition,
    onZoomIn,
    onZoomOut,
    onFullscreen,
  } = options;

  const handleKeyDown = useCallback(
    (event: KeyboardEvent) => {
      // Don't trigger shortcuts when typing in input fields
      const target = event.target as HTMLElement;
      if (
        target.tagName === 'INPUT' ||
        target.tagName === 'TEXTAREA' ||
        target.isContentEditable
      ) {
        return;
      }

      // Don't trigger if shortcuts are disabled
      if (!shortcuts.shortcutsEnabled) {
        return;
      }

      const key = event.key;

      // Emergency Stop - ESC
      if (key === shortcuts.emergencyStop) {
        event.preventDefault();
        Logger.warn('useKeyboardShortcuts.emergency_stop', 'Emergency Stop triggered');
        if (onEmergencyStop) {
          onEmergencyStop();
        } else {
          // Default: show alert
          const confirmed = window.confirm('EMERGENCY STOP: Stop all trading sessions?');
          if (confirmed) {
            // Call emergency stop API
            fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080'}/api/paper-trading/emergency-stop`, {
              method: 'POST',
            }).catch((err) => Logger.error('useKeyboardShortcuts.emergency_stop_failed', { message: 'Emergency stop API call failed' }, err instanceof Error ? err : undefined));
          }
        }
        return;
      }

      // Close Position - C
      if (key.toLowerCase() === shortcuts.closePosition.toLowerCase()) {
        event.preventDefault();
        Logger.info('useKeyboardShortcuts.close_position', 'Close Position triggered');
        if (onClosePosition) {
          onClosePosition();
        }
        return;
      }

      // Navigation shortcuts
      if (key.toLowerCase() === shortcuts.goToDashboard.toLowerCase()) {
        event.preventDefault();
        Logger.debug('useKeyboardShortcuts.navigate', 'Navigate to Dashboard');
        router.push('/dashboard');
        return;
      }

      if (key.toLowerCase() === shortcuts.goToTrading.toLowerCase()) {
        event.preventDefault();
        Logger.debug('useKeyboardShortcuts.navigate', 'Navigate to Trading Session');
        router.push('/trading-session');
        return;
      }

      if (key.toLowerCase() === shortcuts.goToHistory.toLowerCase()) {
        event.preventDefault();
        Logger.debug('useKeyboardShortcuts.navigate', 'Navigate to Session History');
        router.push('/session-history');
        return;
      }

      // Zoom shortcuts
      if (key === shortcuts.zoomIn || (key === '=' && event.shiftKey)) {
        event.preventDefault();
        Logger.debug('useKeyboardShortcuts.zoom', 'Zoom In');
        if (onZoomIn) {
          onZoomIn();
        }
        return;
      }

      if (key === shortcuts.zoomOut) {
        event.preventDefault();
        Logger.debug('useKeyboardShortcuts.zoom', 'Zoom Out');
        if (onZoomOut) {
          onZoomOut();
        }
        return;
      }

      // Fullscreen - F
      if (key.toLowerCase() === shortcuts.fullscreen.toLowerCase()) {
        event.preventDefault();
        Logger.debug('useKeyboardShortcuts.fullscreen', 'Toggle Fullscreen');
        if (onFullscreen) {
          onFullscreen();
        } else {
          // Default: toggle document fullscreen
          if (!document.fullscreenElement) {
            document.documentElement.requestFullscreen().catch((err) => Logger.error('useKeyboardShortcuts.fullscreen_failed', { message: 'Failed to enter fullscreen' }, err instanceof Error ? err : undefined));
          } else {
            document.exitFullscreen().catch((err) => Logger.error('useKeyboardShortcuts.fullscreen_failed', { message: 'Failed to exit fullscreen' }, err instanceof Error ? err : undefined));
          }
        }
        return;
      }
    },
    [shortcuts, router, onEmergencyStop, onClosePosition, onZoomIn, onZoomOut, onFullscreen]
  );

  useEffect(() => {
    document.addEventListener('keydown', handleKeyDown);
    return () => {
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [handleKeyDown]);

  return {
    shortcuts,
    isEnabled: shortcuts.shortcutsEnabled,
  };
}

export default useKeyboardShortcuts;

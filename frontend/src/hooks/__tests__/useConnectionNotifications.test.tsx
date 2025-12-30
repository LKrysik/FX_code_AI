/**
 * useConnectionNotifications Hook Tests
 * Story BUG-008-3: Graceful Degradation UI
 *
 * Tests cover:
 * - AC5: Toast notifications for connection events
 *   - Notification on connection loss
 *   - Notification on reconnection success
 *   - Notification on permanent failure
 */

import React from 'react';
import { renderHook, act } from '@testing-library/react';
import '@testing-library/jest-dom';

// Mock dependencies before importing the hook
const mockAddNotification = jest.fn();
const mockSetCallbacks = jest.fn();

jest.mock('@/services/websocket', () => ({
  wsService: {
    setCallbacks: (callbacks: any) => mockSetCallbacks(callbacks),
  },
}));

jest.mock('@/stores/uiStore', () => ({
  useUIStore: jest.fn((selector) => {
    if (selector.toString().includes('addNotification')) {
      return mockAddNotification;
    }
    return mockAddNotification;
  }),
}));

let mockConnectionStatus = 'connected';
let mockReconnectAttempts = 0;
const mockMaxReconnectAttempts = 5;

jest.mock('@/stores/websocketStore', () => ({
  useWebSocketStore: jest.fn((selector) => {
    const state = {
      connectionStatus: mockConnectionStatus,
      reconnectAttempts: mockReconnectAttempts,
      maxReconnectAttempts: mockMaxReconnectAttempts,
    };
    return selector(state);
  }),
}));

jest.mock('@/services/frontendLogService', () => ({
  Logger: {
    debug: jest.fn(),
    info: jest.fn(),
    warn: jest.fn(),
    error: jest.fn(),
  },
}));

// Import hook after mocks are set up
import { useConnectionNotifications } from '../useConnectionNotifications';

describe('useConnectionNotifications Hook', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockConnectionStatus = 'connected';
    mockReconnectAttempts = 0;
  });

  describe('AC5: Toast notifications for connection events', () => {
    it('registers notification callback with wsService on mount', () => {
      renderHook(() => useConnectionNotifications());

      expect(mockSetCallbacks).toHaveBeenCalledWith(
        expect.objectContaining({
          onNotification: expect.any(Function),
        })
      );
    });

    it('forwards wsService notifications to uiStore', () => {
      renderHook(() => useConnectionNotifications());

      // Get the callback that was passed to wsService
      const callbacks = mockSetCallbacks.mock.calls[0][0];

      // Simulate a notification from wsService
      act(() => {
        callbacks.onNotification({
          type: 'warning',
          message: 'Test notification',
          autoHide: true,
        });
      });

      expect(mockAddNotification).toHaveBeenCalledWith({
        type: 'warning',
        message: 'Test notification',
        autoHide: true,
      });
    });

    it('shows warning notification on connection loss (connected -> disconnected)', () => {
      // Start connected
      mockConnectionStatus = 'connected';
      const { rerender } = renderHook(() => useConnectionNotifications());

      // Clear initial calls
      mockAddNotification.mockClear();

      // Simulate disconnect
      mockConnectionStatus = 'disconnected';
      rerender();

      expect(mockAddNotification).toHaveBeenCalledWith(
        expect.objectContaining({
          type: 'warning',
          message: expect.stringContaining('Connection lost'),
          autoHide: false,
        })
      );
    });

    it('shows success notification on reconnection (reconnecting -> connected)', () => {
      // Start in reconnecting state
      mockConnectionStatus = 'reconnecting';
      mockReconnectAttempts = 2;
      const { rerender } = renderHook(() => useConnectionNotifications());

      // Clear initial calls
      mockAddNotification.mockClear();

      // Simulate successful reconnection
      mockConnectionStatus = 'connected';
      mockReconnectAttempts = 0;
      rerender();

      expect(mockAddNotification).toHaveBeenCalledWith(
        expect.objectContaining({
          type: 'success',
          message: 'Connection restored',
          autoHide: true,
        })
      );
    });

    it('shows error notification on permanent failure (max reconnects reached)', () => {
      // Start with max reconnects reached
      mockConnectionStatus = 'disconnected';
      mockReconnectAttempts = 5; // Equal to max

      renderHook(() => useConnectionNotifications());

      expect(mockAddNotification).toHaveBeenCalledWith(
        expect.objectContaining({
          type: 'error',
          message: expect.stringContaining('Unable to connect'),
          autoHide: false,
        })
      );
    });

    it('shows warning on slow connection', () => {
      // Start connected
      mockConnectionStatus = 'connected';
      const { rerender } = renderHook(() => useConnectionNotifications());

      // Clear initial calls
      mockAddNotification.mockClear();

      // Simulate slow connection
      mockConnectionStatus = 'slow';
      rerender();

      expect(mockAddNotification).toHaveBeenCalledWith(
        expect.objectContaining({
          type: 'warning',
          message: expect.stringContaining('Slow connection'),
          autoHide: true,
        })
      );
    });

    it('shows notification on final reconnection attempt', () => {
      // Start reconnecting
      mockConnectionStatus = 'reconnecting';
      mockReconnectAttempts = 4;
      const { rerender } = renderHook(() => useConnectionNotifications());

      // Clear initial calls
      mockAddNotification.mockClear();

      // Simulate final attempt
      mockReconnectAttempts = 5; // Final attempt
      rerender();

      expect(mockAddNotification).toHaveBeenCalledWith(
        expect.objectContaining({
          type: 'error',
          message: expect.stringContaining('Final reconnection attempt'),
        })
      );
    });

    it('does not show duplicate disconnect notifications', () => {
      // Start connected
      mockConnectionStatus = 'connected';
      const { rerender } = renderHook(() => useConnectionNotifications());

      // Clear initial calls
      mockAddNotification.mockClear();

      // First disconnect
      mockConnectionStatus = 'disconnected';
      rerender();

      const firstCallCount = mockAddNotification.mock.calls.length;

      // Second "disconnect" (shouldn't trigger new notification)
      mockConnectionStatus = 'disconnected';
      rerender();

      // Should not have added another notification
      expect(mockAddNotification.mock.calls.length).toBe(firstCallCount);
    });

    it('does not show connect notification when already connected', () => {
      // Start already connected
      mockConnectionStatus = 'connected';

      renderHook(() => useConnectionNotifications());

      // Should not show "Connection restored" on initial connected state
      expect(mockAddNotification).not.toHaveBeenCalledWith(
        expect.objectContaining({
          message: 'Connection restored',
        })
      );
    });
  });

  describe('Edge cases', () => {
    it('handles error state transition', () => {
      // Start connected
      mockConnectionStatus = 'connected';
      const { rerender } = renderHook(() => useConnectionNotifications());

      // Clear initial calls
      mockAddNotification.mockClear();

      // Simulate error
      mockConnectionStatus = 'error';
      rerender();

      expect(mockAddNotification).toHaveBeenCalledWith(
        expect.objectContaining({
          type: 'warning',
          message: expect.stringContaining('Connection lost'),
        })
      );
    });

    it('handles transition from error to connected', () => {
      // Start in error state
      mockConnectionStatus = 'error';
      const { rerender } = renderHook(() => useConnectionNotifications());

      // Clear initial calls
      mockAddNotification.mockClear();

      // Simulate recovery
      mockConnectionStatus = 'connected';
      rerender();

      expect(mockAddNotification).toHaveBeenCalledWith(
        expect.objectContaining({
          type: 'success',
          message: 'Connection restored',
        })
      );
    });
  });
});

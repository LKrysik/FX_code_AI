/**
 * useEscShortcut Hook Tests
 * ==========================
 * Story: 1b-8-emergency-stop-button
 *
 * Tests for:
 * - AC3: Pressing Esc key triggers callback
 * - AC10: Settings option to toggle "Esc to stop session" on/off
 * - Blocking when session inactive
 * - Blocking in input elements
 * - Debouncing rapid key presses
 */

import { renderHook, act } from '@testing-library/react';
import { useEscShortcut } from '../useEscShortcut';

// Mock the logger
jest.mock('@/services/frontendLogService', () => ({
  Logger: {
    info: jest.fn(),
    debug: jest.fn(),
    warn: jest.fn(),
    error: jest.fn(),
  },
}));

describe('useEscShortcut', () => {
  const mockOnEscPress = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
    jest.useFakeTimers();
  });

  afterEach(() => {
    jest.useRealTimers();
  });

  const simulateEscPress = (target?: HTMLElement) => {
    const event = new KeyboardEvent('keydown', {
      key: 'Escape',
      bubbles: true,
      cancelable: true,
    });

    if (target) {
      Object.defineProperty(event, 'target', { value: target });
    }

    window.dispatchEvent(event);
  };

  const simulateOtherKeyPress = () => {
    window.dispatchEvent(
      new KeyboardEvent('keydown', {
        key: 'a',
        bubbles: true,
        cancelable: true,
      })
    );
  };

  describe('Basic Functionality', () => {
    it('calls onEscPress when Escape is pressed', () => {
      renderHook(() =>
        useEscShortcut({
          onEscPress: mockOnEscPress,
          enabled: true,
          isSessionActive: true,
        })
      );

      simulateEscPress();

      expect(mockOnEscPress).toHaveBeenCalledTimes(1);
    });

    it('does not call onEscPress for other keys', () => {
      renderHook(() =>
        useEscShortcut({
          onEscPress: mockOnEscPress,
          enabled: true,
          isSessionActive: true,
        })
      );

      simulateOtherKeyPress();

      expect(mockOnEscPress).not.toHaveBeenCalled();
    });

    it('returns isActive as true when enabled and session active', () => {
      const { result } = renderHook(() =>
        useEscShortcut({
          onEscPress: mockOnEscPress,
          enabled: true,
          isSessionActive: true,
        })
      );

      expect(result.current.isActive).toBe(true);
      expect(result.current.isEnabled).toBe(true);
    });

    it('updates lastTriggered when Esc is pressed', () => {
      const { result } = renderHook(() =>
        useEscShortcut({
          onEscPress: mockOnEscPress,
          enabled: true,
          isSessionActive: true,
        })
      );

      expect(result.current.lastTriggered).toBeNull();

      simulateEscPress();

      expect(result.current.lastTriggered).toBeInstanceOf(Date);
    });
  });

  describe('AC10: Enable/Disable Toggle', () => {
    it('does not trigger when disabled', () => {
      renderHook(() =>
        useEscShortcut({
          onEscPress: mockOnEscPress,
          enabled: false,
          isSessionActive: true,
        })
      );

      simulateEscPress();

      expect(mockOnEscPress).not.toHaveBeenCalled();
    });

    it('returns isActive as false when disabled', () => {
      const { result } = renderHook(() =>
        useEscShortcut({
          onEscPress: mockOnEscPress,
          enabled: false,
          isSessionActive: true,
        })
      );

      expect(result.current.isActive).toBe(false);
      expect(result.current.isEnabled).toBe(false);
    });

    it('responds to enabled prop changes', () => {
      const { result, rerender } = renderHook(
        ({ enabled }) =>
          useEscShortcut({
            onEscPress: mockOnEscPress,
            enabled,
            isSessionActive: true,
          }),
        { initialProps: { enabled: false } }
      );

      expect(result.current.isEnabled).toBe(false);

      rerender({ enabled: true });

      expect(result.current.isEnabled).toBe(true);
    });
  });

  describe('Session Active Requirement', () => {
    it('does not trigger when no session is active', () => {
      renderHook(() =>
        useEscShortcut({
          onEscPress: mockOnEscPress,
          enabled: true,
          isSessionActive: false,
        })
      );

      simulateEscPress();

      expect(mockOnEscPress).not.toHaveBeenCalled();
    });

    it('returns isActive as false when session inactive', () => {
      const { result } = renderHook(() =>
        useEscShortcut({
          onEscPress: mockOnEscPress,
          enabled: true,
          isSessionActive: false,
        })
      );

      expect(result.current.isActive).toBe(false);
    });

    it('starts triggering when session becomes active', () => {
      const { rerender } = renderHook(
        ({ isSessionActive }) =>
          useEscShortcut({
            onEscPress: mockOnEscPress,
            enabled: true,
            isSessionActive,
          }),
        { initialProps: { isSessionActive: false } }
      );

      simulateEscPress();
      expect(mockOnEscPress).not.toHaveBeenCalled();

      rerender({ isSessionActive: true });

      simulateEscPress();
      expect(mockOnEscPress).toHaveBeenCalledTimes(1);
    });
  });

  describe('Input Element Blocking', () => {
    it('does not trigger when focused on input element', () => {
      renderHook(() =>
        useEscShortcut({
          onEscPress: mockOnEscPress,
          enabled: true,
          isSessionActive: true,
          preventInInputs: true,
        })
      );

      const input = document.createElement('input');
      document.body.appendChild(input);

      simulateEscPress(input);

      expect(mockOnEscPress).not.toHaveBeenCalled();

      document.body.removeChild(input);
    });

    it('does not trigger when focused on textarea', () => {
      renderHook(() =>
        useEscShortcut({
          onEscPress: mockOnEscPress,
          enabled: true,
          isSessionActive: true,
          preventInInputs: true,
        })
      );

      const textarea = document.createElement('textarea');
      document.body.appendChild(textarea);

      simulateEscPress(textarea);

      expect(mockOnEscPress).not.toHaveBeenCalled();

      document.body.removeChild(textarea);
    });

    it('triggers when not in input and preventInInputs is true', () => {
      renderHook(() =>
        useEscShortcut({
          onEscPress: mockOnEscPress,
          enabled: true,
          isSessionActive: true,
          preventInInputs: true,
        })
      );

      const div = document.createElement('div');
      document.body.appendChild(div);

      simulateEscPress(div);

      expect(mockOnEscPress).toHaveBeenCalled();

      document.body.removeChild(div);
    });

    it('triggers in input when preventInInputs is false', () => {
      renderHook(() =>
        useEscShortcut({
          onEscPress: mockOnEscPress,
          enabled: true,
          isSessionActive: true,
          preventInInputs: false,
        })
      );

      const input = document.createElement('input');
      document.body.appendChild(input);

      simulateEscPress(input);

      expect(mockOnEscPress).toHaveBeenCalled();

      document.body.removeChild(input);
    });
  });

  describe('Dialog Open Prevention', () => {
    it('does not trigger when dialog is already open', () => {
      renderHook(() =>
        useEscShortcut({
          onEscPress: mockOnEscPress,
          enabled: true,
          isSessionActive: true,
          preventWhenDialogOpen: true,
          isDialogOpen: true,
        })
      );

      simulateEscPress();

      expect(mockOnEscPress).not.toHaveBeenCalled();
    });

    it('triggers when dialog is closed', () => {
      renderHook(() =>
        useEscShortcut({
          onEscPress: mockOnEscPress,
          enabled: true,
          isSessionActive: true,
          preventWhenDialogOpen: true,
          isDialogOpen: false,
        })
      );

      simulateEscPress();

      expect(mockOnEscPress).toHaveBeenCalled();
    });
  });

  describe('Debouncing', () => {
    it('debounces rapid key presses', () => {
      renderHook(() =>
        useEscShortcut({
          onEscPress: mockOnEscPress,
          enabled: true,
          isSessionActive: true,
        })
      );

      // Rapid fire 5 times
      for (let i = 0; i < 5; i++) {
        simulateEscPress();
      }

      // Should only trigger once due to debouncing
      expect(mockOnEscPress).toHaveBeenCalledTimes(1);
    });

    it('allows triggering after debounce period', () => {
      renderHook(() =>
        useEscShortcut({
          onEscPress: mockOnEscPress,
          enabled: true,
          isSessionActive: true,
        })
      );

      simulateEscPress();
      expect(mockOnEscPress).toHaveBeenCalledTimes(1);

      // Advance time past debounce period (300ms)
      jest.advanceTimersByTime(350);

      simulateEscPress();
      expect(mockOnEscPress).toHaveBeenCalledTimes(2);
    });
  });

  describe('Manual Trigger', () => {
    it('provides triggerEsc function', () => {
      const { result } = renderHook(() =>
        useEscShortcut({
          onEscPress: mockOnEscPress,
          enabled: true,
          isSessionActive: true,
        })
      );

      act(() => {
        result.current.triggerEsc();
      });

      expect(mockOnEscPress).toHaveBeenCalledTimes(1);
    });

    it('triggerEsc respects enabled state', () => {
      const { result } = renderHook(() =>
        useEscShortcut({
          onEscPress: mockOnEscPress,
          enabled: false,
          isSessionActive: true,
        })
      );

      act(() => {
        result.current.triggerEsc();
      });

      expect(mockOnEscPress).not.toHaveBeenCalled();
    });

    it('triggerEsc respects isSessionActive', () => {
      const { result } = renderHook(() =>
        useEscShortcut({
          onEscPress: mockOnEscPress,
          enabled: true,
          isSessionActive: false,
        })
      );

      act(() => {
        result.current.triggerEsc();
      });

      expect(mockOnEscPress).not.toHaveBeenCalled();
    });
  });

  describe('Cleanup', () => {
    it('removes event listener on unmount', () => {
      const addEventListenerSpy = jest.spyOn(window, 'addEventListener');
      const removeEventListenerSpy = jest.spyOn(window, 'removeEventListener');

      const { unmount } = renderHook(() =>
        useEscShortcut({
          onEscPress: mockOnEscPress,
          enabled: true,
          isSessionActive: true,
        })
      );

      expect(addEventListenerSpy).toHaveBeenCalledWith('keydown', expect.any(Function));

      unmount();

      expect(removeEventListenerSpy).toHaveBeenCalledWith('keydown', expect.any(Function));

      addEventListenerSpy.mockRestore();
      removeEventListenerSpy.mockRestore();
    });

    it('does not add listener when disabled', () => {
      const addEventListenerSpy = jest.spyOn(window, 'addEventListener');

      renderHook(() =>
        useEscShortcut({
          onEscPress: mockOnEscPress,
          enabled: false,
          isSessionActive: true,
        })
      );

      expect(addEventListenerSpy).not.toHaveBeenCalledWith('keydown', expect.any(Function));

      addEventListenerSpy.mockRestore();
    });
  });
});

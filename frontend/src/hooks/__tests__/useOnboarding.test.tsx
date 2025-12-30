/**
 * useOnboarding Hook Tests
 * Story 1A-7: First-Visit Onboarding Tooltip (AC1, AC4)
 *
 * Tests cover:
 * - First visit detection via localStorage
 * - Tooltip visibility control
 * - Dismissal and persistence
 * - Reset functionality
 */

import { renderHook, act } from '@testing-library/react';
import { useOnboarding } from '../useOnboarding';

// Mock localStorage
const mockLocalStorage = (() => {
  let store: Record<string, string> = {};
  return {
    getItem: jest.fn((key: string) => store[key] || null),
    setItem: jest.fn((key: string, value: string) => {
      store[key] = value;
    }),
    removeItem: jest.fn((key: string) => {
      delete store[key];
    }),
    clear: jest.fn(() => {
      store = {};
    }),
  };
})();

Object.defineProperty(window, 'localStorage', {
  value: mockLocalStorage,
});

describe('useOnboarding Hook', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockLocalStorage.clear();
  });

  describe('AC1: First Visit Detection', () => {
    it('shows onboarding when hasSeenOnboarding flag is not set', () => {
      mockLocalStorage.getItem.mockReturnValue(null);

      const { result } = renderHook(() => useOnboarding());

      expect(result.current.showOnboarding).toBe(true);
      expect(mockLocalStorage.getItem).toHaveBeenCalledWith('hasSeenOnboarding');
    });

    it('hides onboarding when hasSeenOnboarding flag is "true"', () => {
      mockLocalStorage.getItem.mockReturnValue('true');

      const { result } = renderHook(() => useOnboarding());

      expect(result.current.showOnboarding).toBe(false);
    });

    it('shows onboarding when hasSeenOnboarding flag is "false"', () => {
      mockLocalStorage.getItem.mockReturnValue('false');

      const { result } = renderHook(() => useOnboarding());

      expect(result.current.showOnboarding).toBe(true);
    });
  });

  describe('AC4: Dismissal Persistence', () => {
    it('dismissOnboarding sets flag and hides onboarding', () => {
      mockLocalStorage.getItem.mockReturnValue(null);

      const { result } = renderHook(() => useOnboarding());

      expect(result.current.showOnboarding).toBe(true);

      act(() => {
        result.current.dismissOnboarding();
      });

      expect(mockLocalStorage.setItem).toHaveBeenCalledWith('hasSeenOnboarding', 'true');
      expect(result.current.showOnboarding).toBe(false);
    });

    it('onboarding stays dismissed after dismissal', () => {
      mockLocalStorage.getItem.mockReturnValue(null);

      const { result, rerender } = renderHook(() => useOnboarding());

      act(() => {
        result.current.dismissOnboarding();
      });

      // Simulate localStorage now returning 'true'
      mockLocalStorage.getItem.mockReturnValue('true');

      rerender();

      expect(result.current.showOnboarding).toBe(false);
    });
  });

  describe('Reset Functionality (Task 1.4 optional)', () => {
    it('resetOnboarding clears flag and shows onboarding again', () => {
      mockLocalStorage.getItem.mockReturnValue('true');

      const { result } = renderHook(() => useOnboarding());

      expect(result.current.showOnboarding).toBe(false);

      act(() => {
        result.current.resetOnboarding();
      });

      expect(mockLocalStorage.removeItem).toHaveBeenCalledWith('hasSeenOnboarding');
      expect(result.current.showOnboarding).toBe(true);
    });
  });

  describe('Return type', () => {
    it('returns correct interface', () => {
      const { result } = renderHook(() => useOnboarding());

      expect(typeof result.current.showOnboarding).toBe('boolean');
      expect(typeof result.current.dismissOnboarding).toBe('function');
      expect(typeof result.current.resetOnboarding).toBe('function');
    });
  });

  describe('Edge Cases', () => {
    it('handles localStorage errors gracefully', () => {
      mockLocalStorage.getItem.mockImplementation(() => {
        throw new Error('localStorage not available');
      });

      // Should not throw, should default to showing onboarding
      const { result } = renderHook(() => useOnboarding());

      expect(result.current.showOnboarding).toBe(true);
    });

    it('handles setItem errors gracefully', () => {
      mockLocalStorage.getItem.mockReturnValue(null);
      mockLocalStorage.setItem.mockImplementation(() => {
        throw new Error('Storage quota exceeded');
      });

      const { result } = renderHook(() => useOnboarding());

      // Should not throw on dismiss
      expect(() => {
        act(() => {
          result.current.dismissOnboarding();
        });
      }).not.toThrow();
    });
  });
});

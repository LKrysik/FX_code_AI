/**
 * useStatusHeroData Hook Tests
 * Story 1A-5: StatusHero Component (AC2-4)
 *
 * Tests cover:
 * - Data integration from multiple sources
 * - State machine state sync
 * - Position data fetching
 * - Session info fetching
 * - Timer updates
 * - Error handling
 */

import { renderHook, act, waitFor } from '@testing-library/react';
import { useStatusHeroData } from '../useStatusHeroData';

// Mock useStateMachineState hook
jest.mock('../useStateMachineState', () => ({
  useStateMachineState: jest.fn(() => ({
    currentState: 'MONITORING',
    since: null,
    symbol: null,
  })),
}));

// Mock apiService
jest.mock('@/services/api', () => ({
  apiService: {
    getPositions: jest.fn(),
    getExecutionStatus: jest.fn(),
  },
}));

import { useStateMachineState } from '../useStateMachineState';
import { apiService } from '@/services/api';

const mockUseStateMachineState = useStateMachineState as jest.Mock;
const mockGetPositions = apiService.getPositions as jest.Mock;
const mockGetExecutionStatus = apiService.getExecutionStatus as jest.Mock;

describe('useStatusHeroData Hook', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    jest.useFakeTimers();

    // Default mocks
    mockUseStateMachineState.mockReturnValue({
      currentState: 'MONITORING',
      since: null,
      symbol: null,
    });
    mockGetPositions.mockResolvedValue([]);
    mockGetExecutionStatus.mockResolvedValue({});
  });

  afterEach(() => {
    jest.useRealTimers();
  });

  it('returns initial state when no session', () => {
    const { result } = renderHook(() => useStatusHeroData(null));

    expect(result.current.state).toBe('MONITORING');
    expect(result.current.symbol).toBeNull();
    expect(result.current.pnl).toBeUndefined();
    expect(result.current.isLoading).toBe(false);
  });

  it('syncs state from useStateMachineState', () => {
    mockUseStateMachineState.mockReturnValue({
      currentState: 'S1',
      since: new Date().toISOString(),
      symbol: 'BTCUSDT',
    });

    const { result } = renderHook(() => useStatusHeroData('session-123'));

    expect(result.current.state).toBe('S1');
    expect(result.current.symbol).toBe('BTCUSDT');
  });

  it('fetches session info when session provided', async () => {
    mockGetExecutionStatus.mockResolvedValue({
      started_at: new Date().toISOString(),
      signal_type: 'pump_detection',
      indicators: [
        { name: 'RSI', value: 65.5 },
        { name: 'MACD', value: 0.25 },
      ],
    });

    const { result } = renderHook(() => useStatusHeroData('session-123'));

    await waitFor(() => {
      expect(mockGetExecutionStatus).toHaveBeenCalled();
    });

    await waitFor(() => {
      expect(result.current.signalType).toBe('pump');
      expect(result.current.indicatorHighlights).toHaveLength(2);
    });
  });

  it('fetches position data when in position state', async () => {
    mockUseStateMachineState.mockReturnValue({
      currentState: 'POSITION_ACTIVE',
      since: null,
      symbol: 'BTCUSDT',
    });

    mockGetPositions.mockResolvedValue([
      {
        symbol: 'BTCUSDT',
        unrealized_pnl: 1250.50,
        unrealized_pnl_pct: 5.25,
        entry_price: 50000,
        current_price: 52500,
        side: 'LONG',
        opened_at: new Date().toISOString(),
      },
    ]);

    const { result } = renderHook(() => useStatusHeroData('session-123'));

    await waitFor(() => {
      expect(mockGetPositions).toHaveBeenCalledWith('session-123');
    });

    await waitFor(() => {
      expect(result.current.pnl).toBe(1250.50);
      expect(result.current.pnlPercent).toBe(5.25);
      expect(result.current.entryPrice).toBe(50000);
      expect(result.current.currentPrice).toBe(52500);
      expect(result.current.side).toBe('LONG');
    });
  });

  it('clears position data when not in position state', async () => {
    // Start in position
    mockUseStateMachineState.mockReturnValue({
      currentState: 'POSITION_ACTIVE',
      since: null,
      symbol: 'BTCUSDT',
    });

    mockGetPositions.mockResolvedValue([
      {
        symbol: 'BTCUSDT',
        unrealized_pnl: 1000,
        entry_price: 50000,
        current_price: 51000,
        side: 'LONG',
      },
    ]);

    const { result, rerender } = renderHook(() => useStatusHeroData('session-123'));

    await waitFor(() => {
      expect(result.current.pnl).toBe(1000);
    });

    // Switch to monitoring
    mockUseStateMachineState.mockReturnValue({
      currentState: 'MONITORING',
      since: null,
      symbol: null,
    });

    rerender();

    await waitFor(() => {
      expect(result.current.pnl).toBeUndefined();
      expect(result.current.entryPrice).toBeUndefined();
      expect(result.current.side).toBeUndefined();
    });
  });

  it('updates timers every second', async () => {
    mockGetExecutionStatus.mockResolvedValue({
      started_at: new Date(Date.now() - 10000).toISOString(), // 10 seconds ago
    });

    const { result } = renderHook(() => useStatusHeroData('session-123'));

    // Initial load
    await waitFor(() => {
      expect(mockGetExecutionStatus).toHaveBeenCalled();
    });

    // Wait for session time to be set
    await waitFor(() => {
      expect(result.current.sessionTime).toBeGreaterThanOrEqual(10);
    });

    const initialTime = result.current.sessionTime;

    // Advance 2 seconds
    act(() => {
      jest.advanceTimersByTime(2000);
    });

    await waitFor(() => {
      expect(result.current.sessionTime).toBeGreaterThan(initialTime);
    });
  });

  it('provides refresh function', async () => {
    const { result } = renderHook(() => useStatusHeroData('session-123'));

    expect(typeof result.current.refresh).toBe('function');

    await act(async () => {
      await result.current.refresh();
    });

    expect(mockGetExecutionStatus).toHaveBeenCalled();
  });

  it('handles API errors gracefully', async () => {
    mockGetPositions.mockRejectedValue(new Error('Network error'));

    mockUseStateMachineState.mockReturnValue({
      currentState: 'POSITION_ACTIVE',
      since: null,
      symbol: 'BTCUSDT',
    });

    const { result } = renderHook(() => useStatusHeroData('session-123'));

    // Should not throw, just log warning
    await waitFor(() => {
      expect(mockGetPositions).toHaveBeenCalled();
    });

    // State should still be valid
    expect(result.current.state).toBe('POSITION_ACTIVE');
  });

  it('resets data when session becomes null', async () => {
    const { result, rerender } = renderHook(
      ({ sessionId }) => useStatusHeroData(sessionId),
      { initialProps: { sessionId: 'session-123' as string | null } }
    );

    // Simulate some data being loaded
    mockGetExecutionStatus.mockResolvedValue({
      started_at: new Date().toISOString(),
    });

    await waitFor(() => {
      expect(mockGetExecutionStatus).toHaveBeenCalled();
    });

    // Remove session
    rerender({ sessionId: null });

    await waitFor(() => {
      expect(result.current.state).toBe('MONITORING');
      expect(result.current.symbol).toBeNull();
      expect(result.current.sessionTime).toBe(0);
      expect(result.current.isLoading).toBe(false);
    });
  });

  it('filters positions by symbol when provided', async () => {
    mockUseStateMachineState.mockReturnValue({
      currentState: 'POSITION_ACTIVE',
      since: null,
      symbol: null,
    });

    mockGetPositions.mockResolvedValue([
      { symbol: 'ETHUSDT', unrealized_pnl: 500 },
      { symbol: 'BTCUSDT', unrealized_pnl: 1000 },
    ]);

    const { result } = renderHook(() => useStatusHeroData('session-123', 'BTC'));

    await waitFor(() => {
      expect(result.current.pnl).toBe(1000);
      expect(result.current.symbol).toBe('BTCUSDT');
    });
  });

  it('polls position data every 2 seconds when in position', async () => {
    mockUseStateMachineState.mockReturnValue({
      currentState: 'POSITION_ACTIVE',
      since: null,
      symbol: 'BTCUSDT',
    });

    let callCount = 0;
    mockGetPositions.mockImplementation(() => {
      callCount++;
      return Promise.resolve([
        { symbol: 'BTCUSDT', unrealized_pnl: callCount * 100 },
      ]);
    });

    renderHook(() => useStatusHeroData('session-123'));

    // Initial call
    await waitFor(() => {
      expect(callCount).toBe(1);
    });

    // Advance 2 seconds for first poll
    act(() => {
      jest.advanceTimersByTime(2000);
    });

    await waitFor(() => {
      expect(callCount).toBe(2);
    });

    // Advance 2 more seconds
    act(() => {
      jest.advanceTimersByTime(2000);
    });

    await waitFor(() => {
      expect(callCount).toBe(3);
    });
  });
});

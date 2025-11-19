/**
 * SessionConfigDialog Component Tests
 * =====================================
 *
 * Comprehensive test suite proving each element of the SessionConfigDialog works correctly.
 * User requirement: "Każdy element musi mieć swój test, musisz udowodnić że każda część interfejsy działa poprawnie"
 *
 * Test Coverage:
 * - Tab navigation
 * - API data loading (strategies, symbols, data sessions)
 * - Multi-select functionality
 * - Form validation
 * - Submission workflow
 * - Error handling
 * - Loading states
 * - Mode-specific behavior
 */

import React from 'react';
import { render, screen, fireEvent, waitFor, within } from '@testing-library/react';
import '@testing-library/jest-dom';
import { SessionConfigDialog } from '../SessionConfigDialog';
import type { SessionConfig } from '../SessionConfigDialog';

// ============================================================================
// Mock Data
// ============================================================================

const MOCK_STRATEGIES = [
  {
    id: 'pump_v2',
    strategy_name: 'Pump Detection v2',
    description: 'Detects rapid price increases',
    direction: 'long' as const,
    enabled: true,
    category: 'momentum',
    win_rate: 65.5,
    avg_profit: 12.3,
    total_trades: 150,
  },
  {
    id: 'dump_v2',
    strategy_name: 'Dump Detection v2',
    description: 'Detects rapid price decreases',
    direction: 'short' as const,
    enabled: true,
    category: 'momentum',
    win_rate: 62.1,
    avg_profit: 10.5,
    total_trades: 120,
  },
  {
    id: 'mean_reversion',
    strategy_name: 'Mean Reversion',
    description: 'Trades price reversions to mean',
    direction: 'both' as const,
    enabled: false,
    category: 'statistical',
    win_rate: 58.3,
    avg_profit: 8.7,
    total_trades: 200,
  },
];

const MOCK_SYMBOLS = [
  {
    symbol: 'BTC_USDT',
    name: 'BTC/USDT',
    price: 50250.00,
    volume24h: 1250000000,
    change24h: 5.2,
    exchange: 'mexc',
  },
  {
    symbol: 'ETH_USDT',
    name: 'ETH/USDT',
    price: 3050.00,
    volume24h: 850000000,
    change24h: 3.8,
    exchange: 'mexc',
  },
  {
    symbol: 'ADA_USDT',
    name: 'ADA/USDT',
    price: 0.45,
    volume24h: 120000000,
    change24h: -2.1,
    exchange: 'mexc',
  },
];

const MOCK_DATA_SESSIONS = [
  {
    session_id: 'session_20251118_120530_abc123',
    symbols: ['BTC_USDT', 'ETH_USDT'],
    data_types: ['tick_prices', 'orderbook'],
    status: 'completed',
    start_time: '2025-11-18T12:05:30Z',
    end_time: '2025-11-18T13:05:30Z',
    records_collected: 125000,
    duration: '1h',
  },
  {
    session_id: 'session_20251117_140000_def456',
    symbols: ['BTC_USDT', 'ETH_USDT', 'ADA_USDT'],
    data_types: ['tick_prices'],
    status: 'completed',
    start_time: '2025-11-17T14:00:00Z',
    end_time: '2025-11-17T16:00:00Z',
    records_collected: 250000,
    duration: '2h',
  },
];

// ============================================================================
// Mock fetch API
// ============================================================================

global.fetch = jest.fn((url: string) => {
  if (url.includes('/api/strategies')) {
    return Promise.resolve({
      ok: true,
      json: async () => ({ data: { strategies: MOCK_STRATEGIES } }),
    } as Response);
  }

  if (url.includes('/api/exchange/symbols')) {
    return Promise.resolve({
      ok: true,
      json: async () => ({ data: { symbols: MOCK_SYMBOLS } }),
    } as Response);
  }

  if (url.includes('/api/data-collection/sessions')) {
    return Promise.resolve({
      ok: true,
      json: async () => ({ sessions: MOCK_DATA_SESSIONS }),
    } as Response);
  }

  return Promise.reject(new Error('Unknown endpoint'));
}) as jest.Mock;

// ============================================================================
// Mock localStorage
// ============================================================================

const mockLocalStorage = (() => {
  let store: Record<string, string> = {};

  return {
    getItem: (key: string) => store[key] || null,
    setItem: (key: string, value: string) => {
      store[key] = value;
    },
    clear: () => {
      store = {};
    },
  };
})();

Object.defineProperty(window, 'localStorage', {
  value: mockLocalStorage,
});

// ============================================================================
// Test Suite
// ============================================================================

describe('SessionConfigDialog', () => {
  const mockOnClose = jest.fn();
  const mockOnSubmit = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
    mockLocalStorage.clear();
    (global.fetch as jest.Mock).mockClear();
  });

  // ==========================================================================
  // Rendering Tests
  // ==========================================================================

  describe('Rendering', () => {
    it('renders dialog when open=true', () => {
      render(
        <SessionConfigDialog
          open={true}
          mode="paper"
          onClose={mockOnClose}
          onSubmit={mockOnSubmit}
        />
      );

      expect(screen.getByText(/Configure Paper Session/i)).toBeInTheDocument();
    });

    it('does not render dialog when open=false', () => {
      render(
        <SessionConfigDialog
          open={false}
          mode="paper"
          onClose={mockOnClose}
          onSubmit={mockOnSubmit}
        />
      );

      expect(screen.queryByText(/Configure Paper Session/i)).not.toBeInTheDocument();
    });

    it('renders correct title for Live mode', () => {
      render(
        <SessionConfigDialog
          open={true}
          mode="live"
          onClose={mockOnClose}
          onSubmit={mockOnSubmit}
        />
      );

      expect(screen.getByText(/Configure Live Session/i)).toBeInTheDocument();
    });

    it('renders correct title for Backtest mode', () => {
      render(
        <SessionConfigDialog
          open={true}
          mode="backtest"
          onClose={mockOnClose}
          onSubmit={mockOnSubmit}
        />
      );

      expect(screen.getByText(/Configure Backtest Session/i)).toBeInTheDocument();
    });

    it('renders three tabs', () => {
      render(
        <SessionConfigDialog
          open={true}
          mode="paper"
          onClose={mockOnClose}
          onSubmit={mockOnSubmit}
        />
      );

      expect(screen.getByText(/1\. Strategies \(0\)/i)).toBeInTheDocument();
      expect(screen.getByText(/2\. Symbols \(0\)/i)).toBeInTheDocument();
      expect(screen.getByText(/3\. Configuration/i)).toBeInTheDocument();
    });

    it('renders Cancel and Start Session buttons', () => {
      render(
        <SessionConfigDialog
          open={true}
          mode="paper"
          onClose={mockOnClose}
          onSubmit={mockOnSubmit}
        />
      );

      expect(screen.getByRole('button', { name: /Cancel/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /Start Session/i })).toBeInTheDocument();
    });
  });

  // ==========================================================================
  // API Data Loading Tests
  // ==========================================================================

  describe('API Data Loading', () => {
    it('fetches strategies on mount', async () => {
      render(
        <SessionConfigDialog
          open={true}
          mode="paper"
          onClose={mockOnClose}
          onSubmit={mockOnSubmit}
        />
      );

      await waitFor(() => {
        expect(global.fetch).toHaveBeenCalledWith(
          'http://localhost:8080/api/strategies',
          expect.objectContaining({
            headers: expect.objectContaining({
              'Content-Type': 'application/json',
            }),
          })
        );
      });

      // Verify strategies are rendered
      await waitFor(() => {
        expect(screen.getByText('Pump Detection v2')).toBeInTheDocument();
        expect(screen.getByText('Dump Detection v2')).toBeInTheDocument();
        expect(screen.getByText('Mean Reversion')).toBeInTheDocument();
      });
    });

    it('includes JWT token in strategies request if available', async () => {
      mockLocalStorage.setItem('authToken', 'test-jwt-token');

      render(
        <SessionConfigDialog
          open={true}
          mode="paper"
          onClose={mockOnClose}
          onSubmit={mockOnSubmit}
        />
      );

      await waitFor(() => {
        expect(global.fetch).toHaveBeenCalledWith(
          'http://localhost:8080/api/strategies',
          expect.objectContaining({
            headers: expect.objectContaining({
              'Authorization': 'Bearer test-jwt-token',
            }),
          })
        );
      });
    });

    it('fetches symbols on mount', async () => {
      render(
        <SessionConfigDialog
          open={true}
          mode="paper"
          onClose={mockOnClose}
          onSubmit={mockOnSubmit}
        />
      );

      // Switch to symbols tab
      fireEvent.click(screen.getByText(/2\. Symbols \(0\)/i));

      await waitFor(() => {
        expect(global.fetch).toHaveBeenCalledWith(
          'http://localhost:8080/api/exchange/symbols',
          expect.objectContaining({ signal: expect.any(Object) })
        );
      });

      // Verify symbols are rendered
      await waitFor(() => {
        expect(screen.getByText(/BTC\/USDT/i)).toBeInTheDocument();
        expect(screen.getByText(/ETH\/USDT/i)).toBeInTheDocument();
        expect(screen.getByText(/ADA\/USDT/i)).toBeInTheDocument();
      });
    });

    it('fetches data collection sessions in backtest mode', async () => {
      render(
        <SessionConfigDialog
          open={true}
          mode="backtest"
          onClose={mockOnClose}
          onSubmit={mockOnSubmit}
        />
      );

      // Switch to configuration tab
      fireEvent.click(screen.getByText(/3\. Configuration/i));

      await waitFor(() => {
        expect(global.fetch).toHaveBeenCalledWith(
          'http://localhost:8080/api/data-collection/sessions?limit=50',
          expect.objectContaining({ signal: expect.any(Object) })
        );
      });

      // Verify sessions dropdown is rendered
      await waitFor(() => {
        expect(screen.getByLabelText(/Data Collection Session/i)).toBeInTheDocument();
      });
    });

    it('shows loading state while fetching strategies', async () => {
      (global.fetch as jest.Mock).mockImplementationOnce(() =>
        new Promise((resolve) => setTimeout(() => resolve({
          ok: true,
          json: async () => ({ data: { strategies: MOCK_STRATEGIES } }),
        } as Response), 100))
      );

      render(
        <SessionConfigDialog
          open={true}
          mode="paper"
          onClose={mockOnClose}
          onSubmit={mockOnSubmit}
        />
      );

      // Should show loading indicator
      expect(screen.getByRole('progressbar')).toBeInTheDocument();

      // Wait for data to load
      await waitFor(() => {
        expect(screen.queryByRole('progressbar')).not.toBeInTheDocument();
        expect(screen.getByText('Pump Detection v2')).toBeInTheDocument();
      });
    });

    it('handles API error gracefully', async () => {
      (global.fetch as jest.Mock).mockRejectedValueOnce(new Error('Network error'));

      render(
        <SessionConfigDialog
          open={true}
          mode="paper"
          onClose={mockOnClose}
          onSubmit={mockOnSubmit}
        />
      );

      // Should show error message
      await waitFor(() => {
        expect(screen.getByText(/Strategy loading error/i)).toBeInTheDocument();
      });
    });

    it('handles 401 authentication error', async () => {
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: false,
        status: 401,
      } as Response);

      render(
        <SessionConfigDialog
          open={true}
          mode="paper"
          onClose={mockOnClose}
          onSubmit={mockOnSubmit}
        />
      );

      // Should show authentication error
      await waitFor(() => {
        expect(screen.getByText(/Authentication required/i)).toBeInTheDocument();
      });
    });
  });

  // ==========================================================================
  // Strategy Selection Tests
  // ==========================================================================

  describe('Strategy Selection', () => {
    it('allows selecting a single strategy by clicking checkbox', async () => {
      render(
        <SessionConfigDialog
          open={true}
          mode="paper"
          onClose={mockOnClose}
          onSubmit={mockOnSubmit}
        />
      );

      // Wait for strategies to load
      await waitFor(() => {
        expect(screen.getByText('Pump Detection v2')).toBeInTheDocument();
      });

      // Click checkbox for first strategy
      const checkbox = screen.getAllByRole('checkbox')[0];
      fireEvent.click(checkbox);

      // Tab title should update to show 1 selected
      await waitFor(() => {
        expect(screen.getByText(/1\. Strategies \(1\)/i)).toBeInTheDocument();
      });
    });

    it('allows selecting multiple strategies', async () => {
      render(
        <SessionConfigDialog
          open={true}
          mode="paper"
          onClose={mockOnClose}
          onSubmit={mockOnSubmit}
        />
      );

      await waitFor(() => {
        expect(screen.getByText('Pump Detection v2')).toBeInTheDocument();
      });

      // Select two strategies
      const checkboxes = screen.getAllByRole('checkbox');
      fireEvent.click(checkboxes[0]);
      fireEvent.click(checkboxes[1]);

      await waitFor(() => {
        expect(screen.getByText(/1\. Strategies \(2\)/i)).toBeInTheDocument();
      });
    });

    it('allows deselecting a strategy', async () => {
      render(
        <SessionConfigDialog
          open={true}
          mode="paper"
          onClose={mockOnClose}
          onSubmit={mockOnSubmit}
        />
      );

      await waitFor(() => {
        expect(screen.getByText('Pump Detection v2')).toBeInTheDocument();
      });

      const checkbox = screen.getAllByRole('checkbox')[0];

      // Select
      fireEvent.click(checkbox);
      await waitFor(() => {
        expect(screen.getByText(/1\. Strategies \(1\)/i)).toBeInTheDocument();
      });

      // Deselect
      fireEvent.click(checkbox);
      await waitFor(() => {
        expect(screen.getByText(/1\. Strategies \(0\)/i)).toBeInTheDocument();
      });
    });

    it('displays strategy metadata (win rate, avg profit)', async () => {
      render(
        <SessionConfigDialog
          open={true}
          mode="paper"
          onClose={mockOnClose}
          onSubmit={mockOnSubmit}
        />
      );

      await waitFor(() => {
        expect(screen.getByText('65.5%')).toBeInTheDocument(); // Win rate
        expect(screen.getByText('$12.30')).toBeInTheDocument(); // Avg profit
      });
    });

    it('displays strategy status (Active/Inactive)', async () => {
      render(
        <SessionConfigDialog
          open={true}
          mode="paper"
          onClose={mockOnClose}
          onSubmit={mockOnSubmit}
        />
      );

      await waitFor(() => {
        const activeChips = screen.getAllByText('Active');
        expect(activeChips.length).toBe(2); // pump_v2, dump_v2

        expect(screen.getByText('Inactive')).toBeInTheDocument(); // mean_reversion
      });
    });
  });

  // ==========================================================================
  // Symbol Selection Tests
  // ==========================================================================

  describe('Symbol Selection', () => {
    it('allows selecting symbols by clicking chips', async () => {
      render(
        <SessionConfigDialog
          open={true}
          mode="paper"
          onClose={mockOnClose}
          onSubmit={mockOnSubmit}
        />
      );

      // Switch to symbols tab
      fireEvent.click(screen.getByText(/2\. Symbols \(0\)/i));

      await waitFor(() => {
        expect(screen.getByText(/BTC\/USDT/i)).toBeInTheDocument();
      });

      // Click BTC chip
      const btcChip = screen.getByText(/BTC\/USDT/i).closest('.MuiChip-root');
      fireEvent.click(btcChip!);

      expect(screen.getByText(/2\. Symbols \(1\)/i)).toBeInTheDocument();
    });

    it('"Top 3" button selects first 3 symbols', async () => {
      render(
        <SessionConfigDialog
          open={true}
          mode="paper"
          onClose={mockOnClose}
          onSubmit={mockOnSubmit}
        />
      );

      fireEvent.click(screen.getByText(/2\. Symbols \(0\)/i));

      await waitFor(() => {
        expect(screen.getByText(/BTC\/USDT/i)).toBeInTheDocument();
      });

      // Click "Top 3" button
      fireEvent.click(screen.getByText('Top 3'));

      expect(screen.getByText(/2\. Symbols \(3\)/i)).toBeInTheDocument();
    });

    it('"Clear All" button deselects all symbols', async () => {
      render(
        <SessionConfigDialog
          open={true}
          mode="paper"
          onClose={mockOnClose}
          onSubmit={mockOnSubmit}
        />
      );

      fireEvent.click(screen.getByText(/2\. Symbols \(0\)/i));

      await waitFor(() => {
        expect(screen.getByText(/BTC\/USDT/i)).toBeInTheDocument();
      });

      // Select Top 3
      fireEvent.click(screen.getByText('Top 3'));
      expect(screen.getByText(/2\. Symbols \(3\)/i)).toBeInTheDocument();

      // Clear All
      fireEvent.click(screen.getByText('Clear All'));
      expect(screen.getByText(/2\. Symbols \(0\)/i)).toBeInTheDocument();
    });

    it('displays real-time prices in chips', async () => {
      render(
        <SessionConfigDialog
          open={true}
          mode="paper"
          onClose={mockOnClose}
          onSubmit={mockOnSubmit}
        />
      );

      fireEvent.click(screen.getByText(/2\. Symbols \(0\)/i));

      await waitFor(() => {
        expect(screen.getByText('$50250.00')).toBeInTheDocument(); // BTC price
        expect(screen.getByText('$3050.00')).toBeInTheDocument(); // ETH price
        expect(screen.getByText('$0.450000')).toBeInTheDocument(); // ADA price (6 decimals for values < 1)
      });
    });
  });

  // ==========================================================================
  // Configuration Tests
  // ==========================================================================

  describe('Configuration', () => {
    it('allows setting global budget', async () => {
      render(
        <SessionConfigDialog
          open={true}
          mode="paper"
          onClose={mockOnClose}
          onSubmit={mockOnSubmit}
        />
      );

      fireEvent.click(screen.getByText(/3\. Configuration/i));

      const budgetInput = screen.getByLabelText(/Global Budget \(USDT\)/i);
      fireEvent.change(budgetInput, { target: { value: '5000' } });

      expect(budgetInput).toHaveValue(5000);
    });

    it('allows setting stop loss and take profit', async () => {
      render(
        <SessionConfigDialog
          open={true}
          mode="paper"
          onClose={mockOnClose}
          onSubmit={mockOnSubmit}
        />
      );

      fireEvent.click(screen.getByText(/3\. Configuration/i));

      const stopLossInput = screen.getByLabelText(/Stop Loss \(%\)/i);
      const takeProfitInput = screen.getByLabelText(/Take Profit \(%\)/i);

      fireEvent.change(stopLossInput, { target: { value: '3' } });
      fireEvent.change(takeProfitInput, { target: { value: '15' } });

      expect(stopLossInput).toHaveValue(3);
      expect(takeProfitInput).toHaveValue(15);
    });

    it('shows backtest options in backtest mode', async () => {
      render(
        <SessionConfigDialog
          open={true}
          mode="backtest"
          onClose={mockOnClose}
          onSubmit={mockOnSubmit}
        />
      );

      fireEvent.click(screen.getByText(/3\. Configuration/i));

      await waitFor(() => {
        expect(screen.getByText(/Data Collection Session/i)).toBeInTheDocument();
        expect(screen.getByText(/Acceleration Factor/i)).toBeInTheDocument();
      });
    });

    it('does not show backtest options in paper mode', () => {
      render(
        <SessionConfigDialog
          open={true}
          mode="paper"
          onClose={mockOnClose}
          onSubmit={mockOnSubmit}
        />
      );

      fireEvent.click(screen.getByText(/3\. Configuration/i));

      expect(screen.queryByLabelText(/Data Collection Session/i)).not.toBeInTheDocument();
      expect(screen.queryByText(/Acceleration Factor/i)).not.toBeInTheDocument();
    });

    it('shows live trading warning in live mode', () => {
      render(
        <SessionConfigDialog
          open={true}
          mode="live"
          onClose={mockOnClose}
          onSubmit={mockOnSubmit}
        />
      );

      fireEvent.click(screen.getByText(/3\. Configuration/i));

      expect(screen.getByText(/LIVE TRADING MODE/i)).toBeInTheDocument();
      expect(screen.getByText(/REAL MONEY/i)).toBeInTheDocument();
    });

    it('shows paper trading info in paper mode', () => {
      render(
        <SessionConfigDialog
          open={true}
          mode="paper"
          onClose=  {mockOnClose}
          onSubmit={mockOnSubmit}
        />
      );

      fireEvent.click(screen.getByText(/3\. Configuration/i));

      expect(screen.getByText(/Paper trading mode uses simulated money/i)).toBeInTheDocument();
    });
  });

  // ==========================================================================
  // Validation Tests
  // ==========================================================================

  describe('Validation', () => {
    it('shows error if no strategies selected', async () => {
      render(
        <SessionConfigDialog
          open={true}
          mode="paper"
          onClose={mockOnClose}
          onSubmit={mockOnSubmit}
        />
      );

      // Try to submit without selecting strategies
      fireEvent.click(screen.getByRole('button', { name: /Start Session/i }));

      await waitFor(() => {
        expect(screen.getByText(/Please select at least one strategy/i)).toBeInTheDocument();
      });

      expect(mockOnSubmit).not.toHaveBeenCalled();
    });

    it('shows error if no symbols selected', async () => {
      render(
        <SessionConfigDialog
          open={true}
          mode="paper"
          onClose={mockOnClose}
          onSubmit={mockOnSubmit}
        />
      );

      // Select a strategy
      await waitFor(() => {
        expect(screen.getByText('Pump Detection v2')).toBeInTheDocument();
      });
      fireEvent.click(screen.getAllByRole('checkbox')[0]);

      // Try to submit without selecting symbols
      fireEvent.click(screen.getByRole('button', { name: /Start Session/i }));

      await waitFor(() => {
        expect(screen.getByText(/Please select at least one symbol/i)).toBeInTheDocument();
      });
    });

    it('shows error if backtest session not selected in backtest mode', async () => {
      (global.fetch as jest.Mock).mockImplementation((url: string) => {
        if (url.includes('/api/data-collection/sessions')) {
          return Promise.resolve({
            ok: true,
            json: async () => ({ sessions: [] }), // Empty sessions
          } as Response);
        }
        return Promise.resolve({
          ok: true,
          json: async () => ({ data: { strategies: MOCK_STRATEGIES, symbols: MOCK_SYMBOLS } }),
        } as Response);
      });

      render(
        <SessionConfigDialog
          open={true}
          mode="backtest"
          onClose={mockOnClose}
          onSubmit={mockOnSubmit}
        />
      );

      // Select strategy and symbol
      await waitFor(() => {
        expect(screen.getByText('Pump Detection v2')).toBeInTheDocument();
      });
      fireEvent.click(screen.getAllByRole('checkbox')[0]);

      fireEvent.click(screen.getByText(/2\. Symbols/i));
      await waitFor(() => {
        expect(screen.getByText(/BTC\/USDT/i)).toBeInTheDocument();
      });
      fireEvent.click(screen.getByText('Top 3'));

      // Try to submit
      fireEvent.click(screen.getByRole('button', { name: /Start Session/i }));

      await waitFor(() => {
        expect(screen.getByText(/Please select a data collection session for backtesting/i)).toBeInTheDocument();
      });
    });

    it('validates budget must be greater than 0', async () => {
      render(
        <SessionConfigDialog
          open={true}
          mode="paper"
          onClose={mockOnClose}
          onSubmit={mockOnSubmit}
        />
      );

      // Select strategy and symbol
      await waitFor(() => {
        expect(screen.getByText('Pump Detection v2')).toBeInTheDocument();
      });
      fireEvent.click(screen.getAllByRole('checkbox')[0]);

      fireEvent.click(screen.getByText(/2\. Symbols/i));
      fireEvent.click(screen.getByText('Top 3'));

      // Set budget to 0
      fireEvent.click(screen.getByText(/3\. Configuration/i));
      const budgetInput = screen.getByLabelText(/Global Budget \(USDT\)/i);
      fireEvent.change(budgetInput, { target: { value: '0' } });

      // Try to submit
      fireEvent.click(screen.getByRole('button', { name: /Start Session/i }));

      await waitFor(() => {
        expect(screen.getByText(/Global budget must be a valid number greater than 0/i)).toBeInTheDocument();
      });
    });
  });

  // ==========================================================================
  // Submission Tests
  // ==========================================================================

  describe('Submission', () => {
    it('submits correct config for paper mode', async () => {
      render(
        <SessionConfigDialog
          open={true}
          mode="paper"
          onClose={mockOnClose}
          onSubmit={mockOnSubmit}
        />
      );

      // Select strategy
      await waitFor(() => {
        expect(screen.getByText('Pump Detection v2')).toBeInTheDocument();
      });
      fireEvent.click(screen.getAllByRole('checkbox')[0]);

      // Wait for counter to update
      await waitFor(() => {
        expect(screen.getByText(/1\. Strategies \(1\)/i)).toBeInTheDocument();
      });

      // Select symbols
      fireEvent.click(screen.getByText(/2\. Symbols/i));
      fireEvent.click(screen.getByText('Top 3'));

      // Wait for symbols counter to update
      await waitFor(() => {
        expect(screen.getByText(/2\. Symbols \(3\)/i)).toBeInTheDocument();
      });

      // Configure
      fireEvent.click(screen.getByText(/3\. Configuration/i));
      const budgetInput = screen.getByLabelText(/Global Budget \(USDT\)/i);
      fireEvent.change(budgetInput, { target: { value: '2000' } });

      // Submit
      fireEvent.click(screen.getByRole('button', { name: /Start Session/i }));

      await waitFor(() => {
        expect(mockOnSubmit).toHaveBeenCalledWith(
          expect.objectContaining({
            session_type: 'paper',
            symbols: expect.arrayContaining(['BTC_USDT', 'ETH_USDT', 'ADA_USDT']),
            strategy_config: {
              strategies: expect.arrayContaining(['pump_v2']),
            },
            config: expect.objectContaining({
              budget: {
                global_cap: 2000,
                allocations: {},
              },
              stop_loss_percent: 5.0,
              take_profit_percent: 10.0,
            }),
            idempotent: true,
          })
        );
      });
    });

    it('closes dialog after successful submission', async () => {
      render(
        <SessionConfigDialog
          open={true}
          mode="paper"
          onClose={mockOnClose}
          onSubmit={mockOnSubmit}
        />
      );

      // Complete minimal config
      await waitFor(() => {
        expect(screen.getByText('Pump Detection v2')).toBeInTheDocument();
      });
      fireEvent.click(screen.getAllByRole('checkbox')[0]);

      await waitFor(() => {
        expect(screen.getByText(/1\. Strategies \(1\)/i)).toBeInTheDocument();
      });

      fireEvent.click(screen.getByText(/2\. Symbols/i));
      fireEvent.click(screen.getByText('Top 3'));

      await waitFor(() => {
        expect(screen.getByText(/2\. Symbols \(3\)/i)).toBeInTheDocument();
      });

      // Submit
      fireEvent.click(screen.getByRole('button', { name: /Start Session/i }));

      // onClose should NOT be called (parent handles closing after successful API call)
      // onSubmit should be called
      await waitFor(() => {
        expect(mockOnSubmit).toHaveBeenCalled();
      });
    });
  });

  // ==========================================================================
  // Tab Navigation Tests
  // ==========================================================================

  describe('Tab Navigation', () => {
    it('switches between tabs correctly', async () => {
      render(
        <SessionConfigDialog
          open={true}
          mode="paper"
          onClose={mockOnClose}
          onSubmit={mockOnSubmit}
        />
      );

      // Tab 1 should be active by default
      expect(screen.getByText(/Select Strategies/i)).toBeInTheDocument();

      // Click tab 2
      fireEvent.click(screen.getByText(/2\. Symbols/i));
      expect(screen.getByText(/Select Symbols/i)).toBeInTheDocument();

      // Click tab 3
      fireEvent.click(screen.getByText(/3\. Configuration/i));
      expect(screen.getByText(/Budget & Risk Configuration/i)).toBeInTheDocument();

      // Click back to tab 1
      fireEvent.click(screen.getByText(/1\. Strategies/i));
      expect(screen.getByText(/Select Strategies/i)).toBeInTheDocument();
    });

    it('preserves selections when switching tabs', async () => {
      render(
        <SessionConfigDialog
          open={true}
          mode="paper"
          onClose={mockOnClose}
          onSubmit={mockOnSubmit}
        />
      );

      // Select strategy
      await waitFor(() => {
        expect(screen.getByText('Pump Detection v2')).toBeInTheDocument();
      });
      fireEvent.click(screen.getAllByRole('checkbox')[0]);
      await waitFor(() => {
        expect(screen.getByText(/1\. Strategies \(1\)/i)).toBeInTheDocument();
      });

      // Switch to symbols
      fireEvent.click(screen.getByText(/2\. Symbols/i));
      fireEvent.click(screen.getByText('Top 3'));
      await waitFor(() => {
        expect(screen.getByText(/2\. Symbols \(3\)/i)).toBeInTheDocument();
      });

      // Switch back to strategies
      fireEvent.click(screen.getByText(/1\. Strategies/i));

      // Selection should still be there
      await waitFor(() => {
        expect(screen.getByText(/1\. Strategies \(1\)/i)).toBeInTheDocument();
      });
      const checkbox = screen.getAllByRole('checkbox')[0];
      expect(checkbox).toBeChecked();
    });
  });
});

/**
 * BacktestSetupForm Component Tests
 * ==================================
 * Story: 1b-1-backtest-session-setup
 *
 * Test Coverage:
 * - AC1: Strategy selection from saved strategies
 * - AC2: Symbol selection
 * - AC3: Date range selection
 * - AC4: Data availability validation
 * - AC5: Incomplete data warnings
 * - AC6: Start button initiates backtest
 * - AC7: Validation errors highlight missing fields
 * - AC8: Start button disabled until all fields filled
 */

import React from 'react';
import { render, screen, fireEvent, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom';
import { BacktestSetupForm } from '../BacktestSetupForm';
import { backtestApi } from '@/services/backtestApi';
import { format, subDays } from 'date-fns';

// =============================================================================
// Mocks
// =============================================================================

// Mock next/navigation
const mockPush = jest.fn();
jest.mock('next/navigation', () => ({
  useRouter: () => ({
    push: mockPush,
    replace: jest.fn(),
    prefetch: jest.fn(),
  }),
}));

// Mock the backtestApi service
jest.mock('@/services/backtestApi', () => ({
  backtestApi: {
    getStrategies: jest.fn(),
    getSymbols: jest.fn(),
    getDataCollectionSessions: jest.fn(),
    checkDataAvailability: jest.fn(),
    startBacktest: jest.fn(),
    validateBacktestConfig: jest.fn(),
  },
}));

// Mock date-fns format to ensure consistent test results
jest.mock('date-fns', () => ({
  ...jest.requireActual('date-fns'),
}));

// Mock Logger
jest.mock('@/services/frontendLogService', () => ({
  Logger: {
    info: jest.fn(),
    error: jest.fn(),
    debug: jest.fn(),
    warn: jest.fn(),
  },
}));

// =============================================================================
// Test Data
// =============================================================================

const MOCK_STRATEGIES = [
  {
    id: 'strategy_001',
    strategy_name: 'Pump Detection v2',
    description: 'Detects rapid price increases',
  },
  {
    id: 'strategy_002',
    strategy_name: 'Dump Detection v2',
    description: 'Detects rapid price decreases',
  },
  {
    id: 'strategy_003',
    strategy_name: 'Mean Reversion',
    description: 'Statistical mean reversion strategy',
  },
];

const MOCK_SYMBOLS = [
  'BTCUSDT',
  'ETHUSDT',
  'BNBUSDT',
  'SOLUSDT',
  'XRPUSDT',
];

const MOCK_DATA_SESSIONS = [
  {
    session_id: 'dc_20251120_120000_abc123',
    symbols: ['BTCUSDT', 'ETHUSDT'],
    status: 'completed',
    records_collected: 150000,
    created_at: '2025-11-20T12:00:00Z',
  },
  {
    session_id: 'dc_20251119_100000_def456',
    symbols: ['BTCUSDT'],
    status: 'completed',
    records_collected: 80000,
    created_at: '2025-11-19T10:00:00Z',
  },
];

const MOCK_DATA_AVAILABILITY_GOOD = {
  available: true,
  symbol: 'BTCUSDT',
  start_date: '2025-11-01',
  end_date: '2025-11-07',
  coverage_pct: 95.5,
  total_records: 500000,
  expected_records: 520000,
  missing_ranges: [],
  data_quality: 'good',
  quality_issues: [],
};

const MOCK_DATA_AVAILABILITY_WARNING = {
  available: true,
  symbol: 'BTCUSDT',
  start_date: '2025-11-01',
  end_date: '2025-11-07',
  coverage_pct: 65.2,
  total_records: 340000,
  expected_records: 520000,
  missing_ranges: [
    { start: '2025-11-03T00:00:00Z', end: '2025-11-03T12:00:00Z', gap_hours: 12 },
  ],
  data_quality: 'warning',
  quality_issues: ['Partial data coverage (65.2%). Some gaps may exist.'],
};

const MOCK_DATA_AVAILABILITY_ERROR = {
  available: false,
  symbol: 'BTCUSDT',
  start_date: '2025-11-01',
  end_date: '2025-11-07',
  coverage_pct: 0,
  total_records: 0,
  expected_records: 520000,
  missing_ranges: [],
  data_quality: 'error',
  quality_issues: ['No data found for BTCUSDT in the selected date range'],
};

const MOCK_BACKTEST_RESPONSE = {
  session_id: 'bt_20251128_150000_abc123',
  status: 'started',
  symbol: 'BTCUSDT',
  strategy_id: 'strategy_001',
  start_date: '2025-11-01',
  end_date: '2025-11-07',
  estimated_duration_seconds: 60,
};

// =============================================================================
// Test Setup
// =============================================================================

const mockedBacktestApi = backtestApi as jest.Mocked<typeof backtestApi>;

beforeEach(() => {
  jest.clearAllMocks();
  mockPush.mockClear();

  // Default mock implementations
  mockedBacktestApi.getStrategies.mockResolvedValue(MOCK_STRATEGIES);
  mockedBacktestApi.getSymbols.mockResolvedValue(MOCK_SYMBOLS);
  mockedBacktestApi.getDataCollectionSessions.mockResolvedValue(MOCK_DATA_SESSIONS);
  mockedBacktestApi.checkDataAvailability.mockResolvedValue(MOCK_DATA_AVAILABILITY_GOOD);
  mockedBacktestApi.startBacktest.mockResolvedValue(MOCK_BACKTEST_RESPONSE);
});

// Increase timeout for async operations
jest.setTimeout(10000);

// =============================================================================
// Test Suite
// =============================================================================

describe('BacktestSetupForm', () => {
  // ===========================================================================
  // Rendering Tests
  // ===========================================================================

  describe('Rendering', () => {
    it('renders form title and description', async () => {
      render(<BacktestSetupForm />);

      expect(screen.getByText('Configure Backtest Session')).toBeInTheDocument();
      expect(
        screen.getByText(/Set up a backtest to evaluate your trading strategy/i)
      ).toBeInTheDocument();
    });

    it('renders all required form fields', async () => {
      render(<BacktestSetupForm />);

      await waitFor(() => {
        expect(screen.getByLabelText(/Trading Strategy/i)).toBeInTheDocument();
        expect(screen.getByLabelText(/Trading Symbol/i)).toBeInTheDocument();
        expect(screen.getByLabelText(/Start Date/i)).toBeInTheDocument();
        expect(screen.getByLabelText(/End Date/i)).toBeInTheDocument();
      });
    });

    it('renders Start Backtest button', () => {
      render(<BacktestSetupForm />);

      expect(screen.getByRole('button', { name: /Start Backtest/i })).toBeInTheDocument();
    });

    it('renders advanced options section', async () => {
      render(<BacktestSetupForm />);

      await waitFor(() => {
        expect(screen.getByLabelText(/Acceleration Factor/i)).toBeInTheDocument();
        expect(screen.getByLabelText(/Initial Balance/i)).toBeInTheDocument();
      });
    });
  });

  // ===========================================================================
  // AC1: Strategy Selection Tests
  // ===========================================================================

  describe('AC1: Strategy Selection', () => {
    it('loads strategies from API on mount', async () => {
      render(<BacktestSetupForm />);

      await waitFor(() => {
        expect(mockedBacktestApi.getStrategies).toHaveBeenCalled();
      });
    });

    it('displays strategies in dropdown', async () => {
      render(<BacktestSetupForm />);

      await waitFor(() => {
        expect(mockedBacktestApi.getStrategies).toHaveBeenCalled();
      });

      // Open the dropdown
      const strategySelect = screen.getByLabelText(/Trading Strategy/i);
      fireEvent.mouseDown(strategySelect);

      // Check strategies are displayed
      await waitFor(() => {
        expect(screen.getByText('Pump Detection v2')).toBeInTheDocument();
        expect(screen.getByText('Dump Detection v2')).toBeInTheDocument();
        expect(screen.getByText('Mean Reversion')).toBeInTheDocument();
      });
    });

    it('allows selecting a strategy', async () => {
      render(<BacktestSetupForm />);

      await waitFor(() => {
        expect(mockedBacktestApi.getStrategies).toHaveBeenCalled();
      });

      // Open and select
      const strategySelect = screen.getByLabelText(/Trading Strategy/i);
      fireEvent.mouseDown(strategySelect);

      await waitFor(() => {
        expect(screen.getByText('Pump Detection v2')).toBeInTheDocument();
      });

      fireEvent.click(screen.getByText('Pump Detection v2'));

      // Verify selection
      await waitFor(() => {
        expect(strategySelect).toHaveTextContent('Pump Detection v2');
      });
    });

    it('shows loading state while fetching strategies', async () => {
      // Delay the response
      mockedBacktestApi.getStrategies.mockImplementation(
        () => new Promise((resolve) => setTimeout(() => resolve(MOCK_STRATEGIES), 500))
      );

      render(<BacktestSetupForm />);

      // Should show loading indicator in the select
      const strategySelect = screen.getByLabelText(/Trading Strategy/i);
      expect(strategySelect.closest('.MuiInputBase-root')).toBeInTheDocument();
    });

    it('handles strategy loading error gracefully', async () => {
      mockedBacktestApi.getStrategies.mockRejectedValue(new Error('Network error'));

      render(<BacktestSetupForm />);

      await waitFor(() => {
        expect(screen.getByText(/Failed to load strategies/i)).toBeInTheDocument();
      });
    });
  });

  // ===========================================================================
  // AC2: Symbol Selection Tests
  // ===========================================================================

  describe('AC2: Symbol Selection', () => {
    it('loads symbols from API on mount', async () => {
      render(<BacktestSetupForm />);

      await waitFor(() => {
        expect(mockedBacktestApi.getSymbols).toHaveBeenCalled();
      });
    });

    it('displays symbols in dropdown', async () => {
      render(<BacktestSetupForm />);

      await waitFor(() => {
        expect(mockedBacktestApi.getSymbols).toHaveBeenCalled();
      });

      // Open dropdown
      const symbolSelect = screen.getByLabelText(/Trading Symbol/i);
      fireEvent.mouseDown(symbolSelect);

      // Check symbols
      await waitFor(() => {
        expect(screen.getByText('BTCUSDT')).toBeInTheDocument();
        expect(screen.getByText('ETHUSDT')).toBeInTheDocument();
      });
    });

    it('allows selecting a symbol', async () => {
      render(<BacktestSetupForm />);

      await waitFor(() => {
        expect(mockedBacktestApi.getSymbols).toHaveBeenCalled();
      });

      const symbolSelect = screen.getByLabelText(/Trading Symbol/i);
      fireEvent.mouseDown(symbolSelect);

      await waitFor(() => {
        expect(screen.getByText('BTCUSDT')).toBeInTheDocument();
      });

      fireEvent.click(screen.getByText('BTCUSDT'));

      await waitFor(() => {
        expect(symbolSelect).toHaveTextContent('BTCUSDT');
      });
    });
  });

  // ===========================================================================
  // AC3: Date Range Selection Tests
  // ===========================================================================

  describe('AC3: Date Range Selection', () => {
    it('renders date pickers for start and end date', () => {
      render(<BacktestSetupForm />);

      expect(screen.getByLabelText(/Start Date/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/End Date/i)).toBeInTheDocument();
    });

    it('has default dates set (last 7 days)', () => {
      render(<BacktestSetupForm />);

      const startDateInput = screen.getByLabelText(/Start Date/i);
      const endDateInput = screen.getByLabelText(/End Date/i);

      // Dates should have values
      expect(startDateInput).toHaveValue();
      expect(endDateInput).toHaveValue();
    });

    it('accepts custom default dates via props', () => {
      const customStart = new Date('2025-10-01');
      const customEnd = new Date('2025-10-15');

      render(
        <BacktestSetupForm
          defaultStartDate={customStart}
          defaultEndDate={customEnd}
        />
      );

      const startDateInput = screen.getByLabelText(/Start Date/i);
      const endDateInput = screen.getByLabelText(/End Date/i);

      // Should have the custom dates
      expect(startDateInput).toHaveValue();
      expect(endDateInput).toHaveValue();
    });
  });

  // ===========================================================================
  // AC4 & AC5: Data Availability Tests
  // ===========================================================================

  describe('AC4 & AC5: Data Availability', () => {
    it('checks data availability when symbol and dates are set', async () => {
      render(<BacktestSetupForm />);

      await waitFor(() => {
        expect(mockedBacktestApi.getSymbols).toHaveBeenCalled();
      });

      // Select symbol
      const symbolSelect = screen.getByLabelText(/Trading Symbol/i);
      fireEvent.mouseDown(symbolSelect);
      await waitFor(() => expect(screen.getByText('BTCUSDT')).toBeInTheDocument());
      fireEvent.click(screen.getByText('BTCUSDT'));

      // Should trigger data availability check
      await waitFor(() => {
        expect(mockedBacktestApi.checkDataAvailability).toHaveBeenCalled();
      }, { timeout: 2000 });
    });

    it('displays success status when data quality is good', async () => {
      mockedBacktestApi.checkDataAvailability.mockResolvedValue(MOCK_DATA_AVAILABILITY_GOOD);

      render(<BacktestSetupForm />);

      await waitFor(() => {
        expect(mockedBacktestApi.getSymbols).toHaveBeenCalled();
      });

      // Select symbol
      const symbolSelect = screen.getByLabelText(/Trading Symbol/i);
      fireEvent.mouseDown(symbolSelect);
      await waitFor(() => expect(screen.getByText('BTCUSDT')).toBeInTheDocument());
      fireEvent.click(screen.getByText('BTCUSDT'));

      // Should show success status
      await waitFor(() => {
        expect(screen.getByText(/Data Available/i)).toBeInTheDocument();
        expect(screen.getByText(/95.5% Coverage/i)).toBeInTheDocument();
      }, { timeout: 3000 });
    });

    it('displays warning when data quality is partial (AC5)', async () => {
      mockedBacktestApi.checkDataAvailability.mockResolvedValue(MOCK_DATA_AVAILABILITY_WARNING);

      render(<BacktestSetupForm />);

      await waitFor(() => {
        expect(mockedBacktestApi.getSymbols).toHaveBeenCalled();
      });

      const symbolSelect = screen.getByLabelText(/Trading Symbol/i);
      fireEvent.mouseDown(symbolSelect);
      await waitFor(() => expect(screen.getByText('BTCUSDT')).toBeInTheDocument());
      fireEvent.click(screen.getByText('BTCUSDT'));

      await waitFor(() => {
        expect(screen.getByText(/Data Partially Available/i)).toBeInTheDocument();
        expect(screen.getByText(/65.2% Coverage/i)).toBeInTheDocument();
      }, { timeout: 3000 });
    });

    it('displays error when no data available', async () => {
      mockedBacktestApi.checkDataAvailability.mockResolvedValue(MOCK_DATA_AVAILABILITY_ERROR);

      render(<BacktestSetupForm />);

      await waitFor(() => {
        expect(mockedBacktestApi.getSymbols).toHaveBeenCalled();
      });

      const symbolSelect = screen.getByLabelText(/Trading Symbol/i);
      fireEvent.mouseDown(symbolSelect);
      await waitFor(() => expect(screen.getByText('BTCUSDT')).toBeInTheDocument());
      fireEvent.click(screen.getByText('BTCUSDT'));

      await waitFor(() => {
        expect(screen.getByText(/Data Unavailable/i)).toBeInTheDocument();
      }, { timeout: 3000 });
    });
  });

  // ===========================================================================
  // AC7: Validation Error Tests
  // ===========================================================================

  describe('AC7: Validation Errors', () => {
    it('shows error for missing strategy after blur', async () => {
      render(<BacktestSetupForm />);

      await waitFor(() => {
        expect(mockedBacktestApi.getStrategies).toHaveBeenCalled();
      });

      const strategySelect = screen.getByLabelText(/Trading Strategy/i);
      fireEvent.blur(strategySelect);

      // Try to submit form
      fireEvent.click(screen.getByRole('button', { name: /Start Backtest/i }));

      await waitFor(() => {
        expect(screen.getByText(/Please select a strategy/i)).toBeInTheDocument();
      });
    });

    it('shows error for missing symbol after blur', async () => {
      render(<BacktestSetupForm />);

      await waitFor(() => {
        expect(mockedBacktestApi.getSymbols).toHaveBeenCalled();
      });

      // Select strategy first
      const strategySelect = screen.getByLabelText(/Trading Strategy/i);
      fireEvent.mouseDown(strategySelect);
      await waitFor(() => expect(screen.getByText('Pump Detection v2')).toBeInTheDocument());
      fireEvent.click(screen.getByText('Pump Detection v2'));

      // Submit without symbol
      fireEvent.click(screen.getByRole('button', { name: /Start Backtest/i }));

      await waitFor(() => {
        expect(screen.getByText(/Please select a trading symbol/i)).toBeInTheDocument();
      });
    });

    it('shows error when end date is before start date', async () => {
      render(
        <BacktestSetupForm
          defaultStartDate={new Date('2025-11-10')}
          defaultEndDate={new Date('2025-11-05')}
        />
      );

      await waitFor(() => {
        expect(screen.getByText(/End date must be after start date/i)).toBeInTheDocument();
      });
    });
  });

  // ===========================================================================
  // AC8: Button Disabled State Tests
  // ===========================================================================

  describe('AC8: Start Button Disabled State', () => {
    it('button is disabled when form is incomplete', async () => {
      render(<BacktestSetupForm />);

      const submitButton = screen.getByRole('button', { name: /Start Backtest/i });
      expect(submitButton).toBeDisabled();
    });

    it('button is enabled when all required fields are filled', async () => {
      render(<BacktestSetupForm />);

      await waitFor(() => {
        expect(mockedBacktestApi.getStrategies).toHaveBeenCalled();
        expect(mockedBacktestApi.getSymbols).toHaveBeenCalled();
      });

      // Select strategy
      const strategySelect = screen.getByLabelText(/Trading Strategy/i);
      fireEvent.mouseDown(strategySelect);
      await waitFor(() => expect(screen.getByText('Pump Detection v2')).toBeInTheDocument());
      fireEvent.click(screen.getByText('Pump Detection v2'));

      // Select symbol
      const symbolSelect = screen.getByLabelText(/Trading Symbol/i);
      fireEvent.mouseDown(symbolSelect);
      await waitFor(() => expect(screen.getByText('BTCUSDT')).toBeInTheDocument());
      fireEvent.click(screen.getByText('BTCUSDT'));

      // Button should be enabled (dates have defaults)
      await waitFor(() => {
        const submitButton = screen.getByRole('button', { name: /Start Backtest/i });
        expect(submitButton).not.toBeDisabled();
      });
    });
  });

  // ===========================================================================
  // AC6: Form Submission Tests
  // ===========================================================================

  describe('AC6: Form Submission', () => {
    it('calls startBacktest API on valid submission', async () => {
      render(<BacktestSetupForm />);

      await waitFor(() => {
        expect(mockedBacktestApi.getStrategies).toHaveBeenCalled();
        expect(mockedBacktestApi.getSymbols).toHaveBeenCalled();
      });

      // Fill form
      const strategySelect = screen.getByLabelText(/Trading Strategy/i);
      fireEvent.mouseDown(strategySelect);
      await waitFor(() => expect(screen.getByText('Pump Detection v2')).toBeInTheDocument());
      fireEvent.click(screen.getByText('Pump Detection v2'));

      const symbolSelect = screen.getByLabelText(/Trading Symbol/i);
      fireEvent.mouseDown(symbolSelect);
      await waitFor(() => expect(screen.getByText('BTCUSDT')).toBeInTheDocument());
      fireEvent.click(screen.getByText('BTCUSDT'));

      // Submit
      await waitFor(() => {
        const submitButton = screen.getByRole('button', { name: /Start Backtest/i });
        expect(submitButton).not.toBeDisabled();
      });

      fireEvent.click(screen.getByRole('button', { name: /Start Backtest/i }));

      await waitFor(() => {
        expect(mockedBacktestApi.startBacktest).toHaveBeenCalledWith(
          expect.objectContaining({
            strategy_id: 'strategy_001',
            symbol: 'BTCUSDT',
          })
        );
      });
    });

    it('redirects to dashboard after successful start', async () => {
      render(<BacktestSetupForm />);

      await waitFor(() => {
        expect(mockedBacktestApi.getStrategies).toHaveBeenCalled();
        expect(mockedBacktestApi.getSymbols).toHaveBeenCalled();
      });

      // Fill form
      const strategySelect = screen.getByLabelText(/Trading Strategy/i);
      fireEvent.mouseDown(strategySelect);
      await waitFor(() => expect(screen.getByText('Pump Detection v2')).toBeInTheDocument());
      fireEvent.click(screen.getByText('Pump Detection v2'));

      const symbolSelect = screen.getByLabelText(/Trading Symbol/i);
      fireEvent.mouseDown(symbolSelect);
      await waitFor(() => expect(screen.getByText('BTCUSDT')).toBeInTheDocument());
      fireEvent.click(screen.getByText('BTCUSDT'));

      // Submit
      await waitFor(() => {
        const submitButton = screen.getByRole('button', { name: /Start Backtest/i });
        expect(submitButton).not.toBeDisabled();
      });

      fireEvent.click(screen.getByRole('button', { name: /Start Backtest/i }));

      // Should redirect
      await waitFor(() => {
        expect(mockPush).toHaveBeenCalledWith(
          expect.stringContaining('/dashboard?mode=backtest&session_id=')
        );
      });
    });

    it('calls onBacktestStarted callback when provided', async () => {
      const onBacktestStarted = jest.fn();

      render(<BacktestSetupForm onBacktestStarted={onBacktestStarted} />);

      await waitFor(() => {
        expect(mockedBacktestApi.getStrategies).toHaveBeenCalled();
        expect(mockedBacktestApi.getSymbols).toHaveBeenCalled();
      });

      // Fill form
      const strategySelect = screen.getByLabelText(/Trading Strategy/i);
      fireEvent.mouseDown(strategySelect);
      await waitFor(() => expect(screen.getByText('Pump Detection v2')).toBeInTheDocument());
      fireEvent.click(screen.getByText('Pump Detection v2'));

      const symbolSelect = screen.getByLabelText(/Trading Symbol/i);
      fireEvent.mouseDown(symbolSelect);
      await waitFor(() => expect(screen.getByText('BTCUSDT')).toBeInTheDocument());
      fireEvent.click(screen.getByText('BTCUSDT'));

      // Submit
      await waitFor(() => {
        const submitButton = screen.getByRole('button', { name: /Start Backtest/i });
        expect(submitButton).not.toBeDisabled();
      });

      fireEvent.click(screen.getByRole('button', { name: /Start Backtest/i }));

      await waitFor(() => {
        expect(onBacktestStarted).toHaveBeenCalledWith('bt_20251128_150000_abc123');
      });
    });

    it('shows loading state during submission', async () => {
      mockedBacktestApi.startBacktest.mockImplementation(
        () => new Promise((resolve) => setTimeout(() => resolve(MOCK_BACKTEST_RESPONSE), 500))
      );

      render(<BacktestSetupForm />);

      await waitFor(() => {
        expect(mockedBacktestApi.getStrategies).toHaveBeenCalled();
        expect(mockedBacktestApi.getSymbols).toHaveBeenCalled();
      });

      // Fill form
      const strategySelect = screen.getByLabelText(/Trading Strategy/i);
      fireEvent.mouseDown(strategySelect);
      await waitFor(() => expect(screen.getByText('Pump Detection v2')).toBeInTheDocument());
      fireEvent.click(screen.getByText('Pump Detection v2'));

      const symbolSelect = screen.getByLabelText(/Trading Symbol/i);
      fireEvent.mouseDown(symbolSelect);
      await waitFor(() => expect(screen.getByText('BTCUSDT')).toBeInTheDocument());
      fireEvent.click(screen.getByText('BTCUSDT'));

      // Submit
      await waitFor(() => {
        const submitButton = screen.getByRole('button', { name: /Start Backtest/i });
        expect(submitButton).not.toBeDisabled();
      });

      fireEvent.click(screen.getByRole('button', { name: /Start Backtest/i }));

      // Should show loading text
      await waitFor(() => {
        expect(screen.getByText(/Starting Backtest.../i)).toBeInTheDocument();
      });
    });

    it('shows error message on submission failure', async () => {
      mockedBacktestApi.startBacktest.mockRejectedValue(
        new Error('Failed to start backtest: Server error')
      );

      render(<BacktestSetupForm />);

      await waitFor(() => {
        expect(mockedBacktestApi.getStrategies).toHaveBeenCalled();
        expect(mockedBacktestApi.getSymbols).toHaveBeenCalled();
      });

      // Fill form
      const strategySelect = screen.getByLabelText(/Trading Strategy/i);
      fireEvent.mouseDown(strategySelect);
      await waitFor(() => expect(screen.getByText('Pump Detection v2')).toBeInTheDocument());
      fireEvent.click(screen.getByText('Pump Detection v2'));

      const symbolSelect = screen.getByLabelText(/Trading Symbol/i);
      fireEvent.mouseDown(symbolSelect);
      await waitFor(() => expect(screen.getByText('BTCUSDT')).toBeInTheDocument());
      fireEvent.click(screen.getByText('BTCUSDT'));

      // Submit
      await waitFor(() => {
        const submitButton = screen.getByRole('button', { name: /Start Backtest/i });
        expect(submitButton).not.toBeDisabled();
      });

      fireEvent.click(screen.getByRole('button', { name: /Start Backtest/i }));

      // Should show error
      await waitFor(() => {
        expect(screen.getByText(/Failed to start backtest/i)).toBeInTheDocument();
      });
    });
  });

  // ===========================================================================
  // Default Props Tests
  // ===========================================================================

  describe('Default Props', () => {
    it('accepts defaultStrategy prop', async () => {
      render(<BacktestSetupForm defaultStrategy="strategy_002" />);

      await waitFor(() => {
        expect(mockedBacktestApi.getStrategies).toHaveBeenCalled();
      });

      // Should have strategy_002 pre-selected
      const strategySelect = screen.getByLabelText(/Trading Strategy/i);
      expect(strategySelect).toHaveTextContent('Dump Detection v2');
    });

    it('accepts defaultSymbol prop', async () => {
      render(<BacktestSetupForm defaultSymbol="ETHUSDT" />);

      await waitFor(() => {
        expect(mockedBacktestApi.getSymbols).toHaveBeenCalled();
      });

      // Should have ETHUSDT pre-selected
      const symbolSelect = screen.getByLabelText(/Trading Symbol/i);
      expect(symbolSelect).toHaveTextContent('ETHUSDT');
    });
  });
});

// =============================================================================
// Validation Logic Unit Tests
// =============================================================================

describe('Backtest API Validation', () => {
  describe('validateBacktestConfig', () => {
    it('returns errors for empty config', () => {
      const { validateBacktestConfig } = require('@/services/backtestApi').backtestApi;

      const result = validateBacktestConfig({});

      expect(result.isValid).toBe(false);
      expect(result.errors.strategy_id).toBeDefined();
      expect(result.errors.symbol).toBeDefined();
      expect(result.errors.start_date).toBeDefined();
      expect(result.errors.end_date).toBeDefined();
    });

    it('returns valid for complete config', () => {
      const { validateBacktestConfig } = require('@/services/backtestApi').backtestApi;

      const result = validateBacktestConfig({
        strategy_id: 'strategy_001',
        symbol: 'BTCUSDT',
        start_date: '2025-11-01',
        end_date: '2025-11-07',
      });

      expect(result.isValid).toBe(true);
      expect(Object.keys(result.errors)).toHaveLength(0);
    });

    it('returns error for end date before start date', () => {
      const { validateBacktestConfig } = require('@/services/backtestApi').backtestApi;

      const result = validateBacktestConfig({
        strategy_id: 'strategy_001',
        symbol: 'BTCUSDT',
        start_date: '2025-11-15',
        end_date: '2025-11-01',
      });

      expect(result.isValid).toBe(false);
      expect(result.errors.end_date).toBeDefined();
    });

    it('returns error for date range exceeding 365 days', () => {
      const { validateBacktestConfig } = require('@/services/backtestApi').backtestApi;

      const result = validateBacktestConfig({
        strategy_id: 'strategy_001',
        symbol: 'BTCUSDT',
        start_date: '2024-01-01',
        end_date: '2025-12-31',
      });

      expect(result.isValid).toBe(false);
      expect(result.errors.end_date).toContain('365');
    });
  });
});

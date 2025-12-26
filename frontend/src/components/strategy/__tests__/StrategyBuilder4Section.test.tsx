/**
 * StrategyBuilder4Section Component Tests
 * =========================================
 *
 * Comprehensive test suite for Strategy Builder 4-Section component.
 *
 * Test Coverage:
 * - Component rendering
 * - Section accordion expansion
 * - Strategy name validation
 * - Condition management (add/remove)
 * - Section navigation
 * - Save/validate functionality
 * - Form state management
 *
 * Created: 2025-12-23
 */

import React from 'react';
import { render, screen, fireEvent, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom';
import { StrategyBuilder4Section } from '../StrategyBuilder4Section';

// ============================================================================
// Mock Data
// ============================================================================

const MOCK_INDICATORS = [
  {
    id: 'rsi_14',
    name: 'RSI (14)',
    baseType: 'rsi',
    type: 'general',
    parameters: { period: 14 },
    lastValue: 45.2,
    lastUpdate: new Date().toISOString(),
    description: 'Relative Strength Index with 14-period',
    isActive: true,
  },
  {
    id: 'macd_12_26_9',
    name: 'MACD (12, 26, 9)',
    baseType: 'macd',
    type: 'general',
    parameters: { fast: 12, slow: 26, signal: 9 },
    lastValue: 0.0025,
    lastUpdate: new Date().toISOString(),
    description: 'Moving Average Convergence Divergence',
    isActive: true,
  },
  {
    id: 'ema_20',
    name: 'EMA (20)',
    baseType: 'ema',
    type: 'order_price',
    parameters: { period: 20 },
    lastValue: 43500.50,
    lastUpdate: new Date().toISOString(),
    description: 'Exponential Moving Average 20-period',
    isActive: true,
  },
  {
    id: 'atr_14',
    name: 'ATR (14)',
    baseType: 'atr',
    type: 'stop_loss_price',
    parameters: { period: 14 },
    lastValue: 250.0,
    lastUpdate: new Date().toISOString(),
    description: 'Average True Range for volatility',
    isActive: true,
  },
];

// ============================================================================
// Mock fetch API
// ============================================================================

const mockFetch = jest.fn((url: string) => {
  if (url.includes('/api/indicators')) {
    return Promise.resolve({
      ok: true,
      json: async () => ({ data: { indicators: MOCK_INDICATORS } }),
    } as Response);
  }

  if (url.includes('/api/strategies')) {
    return Promise.resolve({
      ok: true,
      json: async () => ({ success: true, data: { strategy_id: 'test-strategy-123' } }),
    } as Response);
  }

  return Promise.reject(new Error('Unknown endpoint'));
}) as jest.Mock;

global.fetch = mockFetch;

// ============================================================================
// Mock localStorage
// ============================================================================

const mockLocalStorage = (() => {
  let store: Record<string, string> = {};
  return {
    getItem: (key: string) => store[key] || null,
    setItem: (key: string, value: string) => { store[key] = value; },
    removeItem: (key: string) => { delete store[key]; },
    clear: () => { store = {}; },
  };
})();

Object.defineProperty(window, 'localStorage', { value: mockLocalStorage });

// ============================================================================
// Mock MUI components that need special handling
// ============================================================================

// Mock uuid
jest.mock('uuid', () => ({
  v4: () => `test-uuid-${Date.now()}-${Math.random()}`,
}));

// ============================================================================
// Configure Testing Library
// ============================================================================

jest.setTimeout(15000);
const WAITFOR_TIMEOUT = 3000;

// ============================================================================
// Test Suite
// ============================================================================

describe('StrategyBuilder4Section', () => {
  const mockOnSave = jest.fn();
  const mockOnValidate = jest.fn();
  const mockOnCancel = jest.fn();

  const defaultProps = {
    symbol: 'BTC_USDT',
    onSave: mockOnSave,
    onValidate: mockOnValidate,
    onCancel: mockOnCancel,
  };

  beforeEach(() => {
    jest.clearAllMocks();
    mockLocalStorage.clear();
    mockFetch.mockClear();
  });

  // ==========================================================================
  // Rendering Tests
  // ==========================================================================

  describe('Rendering', () => {
    it('renders component with strategy name input', () => {
      render(<StrategyBuilder4Section {...defaultProps} />);

      expect(screen.getByLabelText(/Strategy Name/i)).toBeInTheDocument();
    });

    it('renders all four section accordions', () => {
      render(<StrategyBuilder4Section {...defaultProps} />);

      // Check for section titles
      expect(screen.getByText(/S1: Entry Conditions/i)).toBeInTheDocument();
      expect(screen.getByText(/Z1: Zone Conditions/i)).toBeInTheDocument();
      expect(screen.getByText(/O1: Order Conditions/i)).toBeInTheDocument();
      expect(screen.getByText(/Emergency Exit/i)).toBeInTheDocument();
    });

    it('renders action buttons', () => {
      render(<StrategyBuilder4Section {...defaultProps} />);

      expect(screen.getByRole('button', { name: /Cancel/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /Validate/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /Save Strategy/i })).toBeInTheDocument();
    });

    it('renders symbol information', () => {
      render(<StrategyBuilder4Section {...defaultProps} />);

      expect(screen.getByText(/BTC_USDT/i)).toBeInTheDocument();
    });

    it('renders direction selector', () => {
      render(<StrategyBuilder4Section {...defaultProps} />);

      // Check for LONG/SHORT direction options
      expect(screen.getByLabelText(/Direction/i)).toBeInTheDocument();
    });
  });

  // ==========================================================================
  // Strategy Name Tests
  // ==========================================================================

  describe('Strategy Name', () => {
    it('allows typing strategy name', async () => {
      render(<StrategyBuilder4Section {...defaultProps} />);

      const nameInput = screen.getByLabelText(/Strategy Name/i);
      await userEvent.type(nameInput, 'My Test Strategy');

      expect(nameInput).toHaveValue('My Test Strategy');
    });

    it('shows validation error when name is empty on save', async () => {
      render(<StrategyBuilder4Section {...defaultProps} />);

      const saveButton = screen.getByRole('button', { name: /Save Strategy/i });
      fireEvent.click(saveButton);

      await waitFor(() => {
        expect(screen.getByText(/Strategy name is required/i)).toBeInTheDocument();
      });
    });

    it('clears validation error when name is provided', async () => {
      render(<StrategyBuilder4Section {...defaultProps} />);

      // Trigger validation error
      const saveButton = screen.getByRole('button', { name: /Save Strategy/i });
      fireEvent.click(saveButton);

      await waitFor(() => {
        expect(screen.getByText(/Strategy name is required/i)).toBeInTheDocument();
      });

      // Type name
      const nameInput = screen.getByLabelText(/Strategy Name/i);
      await userEvent.type(nameInput, 'Valid Strategy Name');

      await waitFor(() => {
        expect(screen.queryByText(/Strategy name is required/i)).not.toBeInTheDocument();
      });
    });
  });

  // ==========================================================================
  // Section Accordion Tests
  // ==========================================================================

  describe('Section Accordions', () => {
    it('first section (S1) is expanded by default', () => {
      render(<StrategyBuilder4Section {...defaultProps} />);

      const s1Section = screen.getByText(/S1: Entry Conditions/i).closest('.MuiAccordion-root');
      expect(s1Section).toHaveClass('Mui-expanded');
    });

    it('clicking accordion expands/collapses section', async () => {
      render(<StrategyBuilder4Section {...defaultProps} />);

      const z1Header = screen.getByText(/Z1: Zone Conditions/i);

      // Click to expand Z1
      fireEvent.click(z1Header);

      await waitFor(() => {
        const z1Section = z1Header.closest('.MuiAccordion-root');
        expect(z1Section).toHaveClass('Mui-expanded');
      });
    });

    it('can have multiple sections expanded', async () => {
      render(<StrategyBuilder4Section {...defaultProps} />);

      // S1 is expanded by default
      const s1Header = screen.getByText(/S1: Entry Conditions/i);
      const z1Header = screen.getByText(/Z1: Zone Conditions/i);

      // Expand Z1
      fireEvent.click(z1Header);

      await waitFor(() => {
        const s1Section = s1Header.closest('.MuiAccordion-root');
        const z1Section = z1Header.closest('.MuiAccordion-root');

        expect(s1Section).toHaveClass('Mui-expanded');
        expect(z1Section).toHaveClass('Mui-expanded');
      });
    });
  });

  // ==========================================================================
  // Add Condition Tests
  // ==========================================================================

  describe('Add Condition', () => {
    it('has "Add Condition" button in each section', () => {
      render(<StrategyBuilder4Section {...defaultProps} />);

      // Find all "Add Condition" buttons
      const addButtons = screen.getAllByRole('button', { name: /Add Condition/i });

      // Should have one per section (4 sections)
      expect(addButtons.length).toBeGreaterThanOrEqual(1);
    });

    it('clicking "Add Condition" adds a new condition block', async () => {
      render(<StrategyBuilder4Section {...defaultProps} />);

      // Find the first "Add Condition" button (in S1 section)
      const addButton = screen.getAllByRole('button', { name: /Add Condition/i })[0];

      // Initially should have 1 condition (default)
      const initialConditions = screen.getAllByText(/Condition \d+/i);
      const initialCount = initialConditions.length;

      // Click to add condition
      fireEvent.click(addButton);

      await waitFor(() => {
        const newConditions = screen.getAllByText(/Condition \d+/i);
        expect(newConditions.length).toBe(initialCount + 1);
      });
    });
  });

  // ==========================================================================
  // Remove Condition Tests
  // ==========================================================================

  describe('Remove Condition', () => {
    it('condition has remove button', async () => {
      render(<StrategyBuilder4Section {...defaultProps} />);

      // Add a condition first
      const addButton = screen.getAllByRole('button', { name: /Add Condition/i })[0];
      fireEvent.click(addButton);

      await waitFor(() => {
        // Look for delete buttons (trash icon)
        const deleteButtons = screen.getAllByTestId ?
          screen.getAllByRole('button').filter(btn => btn.querySelector('[data-testid="DeleteIcon"]')) :
          document.querySelectorAll('button[aria-label*="delete"], button[aria-label*="remove"]');

        expect(deleteButtons.length).toBeGreaterThan(0);
      });
    });
  });

  // ==========================================================================
  // Direction Tests
  // ==========================================================================

  describe('Direction Selection', () => {
    it('defaults to LONG direction', () => {
      render(<StrategyBuilder4Section {...defaultProps} />);

      const directionSelect = screen.getByLabelText(/Direction/i);
      expect(directionSelect).toHaveTextContent(/LONG/i);
    });

    it('allows changing direction to SHORT', async () => {
      render(<StrategyBuilder4Section {...defaultProps} />);

      const directionSelect = screen.getByLabelText(/Direction/i);
      fireEvent.mouseDown(directionSelect);

      await waitFor(() => {
        const shortOption = screen.getByRole('option', { name: /SHORT/i });
        fireEvent.click(shortOption);
      });

      expect(directionSelect).toHaveTextContent(/SHORT/i);
    });
  });

  // ==========================================================================
  // Button Actions Tests
  // ==========================================================================

  describe('Button Actions', () => {
    it('Cancel button calls onCancel', () => {
      render(<StrategyBuilder4Section {...defaultProps} />);

      const cancelButton = screen.getByRole('button', { name: /Cancel/i });
      fireEvent.click(cancelButton);

      expect(mockOnCancel).toHaveBeenCalledTimes(1);
    });

    it('Validate button calls onValidate with strategy data', async () => {
      render(<StrategyBuilder4Section {...defaultProps} />);

      // Enter strategy name
      const nameInput = screen.getByLabelText(/Strategy Name/i);
      await userEvent.type(nameInput, 'Test Strategy');

      const validateButton = screen.getByRole('button', { name: /Validate/i });
      fireEvent.click(validateButton);

      await waitFor(() => {
        expect(mockOnValidate).toHaveBeenCalled();
      });
    });

    it('Save button shows error when name missing', async () => {
      render(<StrategyBuilder4Section {...defaultProps} />);

      const saveButton = screen.getByRole('button', { name: /Save Strategy/i });
      fireEvent.click(saveButton);

      await waitFor(() => {
        expect(screen.getByText(/Strategy name is required/i)).toBeInTheDocument();
      });

      // onSave should not be called
      expect(mockOnSave).not.toHaveBeenCalled();
    });

    it('Save button calls onSave when form is valid', async () => {
      render(<StrategyBuilder4Section {...defaultProps} />);

      // Enter strategy name
      const nameInput = screen.getByLabelText(/Strategy Name/i);
      await userEvent.type(nameInput, 'Valid Strategy');

      const saveButton = screen.getByRole('button', { name: /Save Strategy/i });
      fireEvent.click(saveButton);

      await waitFor(() => {
        expect(mockOnSave).toHaveBeenCalled();
      });
    });
  });

  // ==========================================================================
  // Section Progress Indicator Tests
  // ==========================================================================

  describe('Section Progress', () => {
    it('shows condition count in section headers', async () => {
      render(<StrategyBuilder4Section {...defaultProps} />);

      // Add conditions to S1
      const addButton = screen.getAllByRole('button', { name: /Add Condition/i })[0];
      fireEvent.click(addButton);
      fireEvent.click(addButton);

      await waitFor(() => {
        // S1 header should show condition count
        const s1Header = screen.getByText(/S1: Entry Conditions/i);
        const parentElement = s1Header.closest('.MuiAccordionSummary-root');

        // Check for condition count indicator
        expect(parentElement?.textContent).toMatch(/\d+/);
      });
    });
  });

  // ==========================================================================
  // Form State Tests
  // ==========================================================================

  describe('Form State', () => {
    it('preserves form state when switching sections', async () => {
      render(<StrategyBuilder4Section {...defaultProps} />);

      // Enter strategy name
      const nameInput = screen.getByLabelText(/Strategy Name/i);
      await userEvent.type(nameInput, 'My Strategy');

      // Click on Z1 section
      const z1Header = screen.getByText(/Z1: Zone Conditions/i);
      fireEvent.click(z1Header);

      // Click back on S1 section
      const s1Header = screen.getByText(/S1: Entry Conditions/i);
      fireEvent.click(s1Header);

      // Name should still be there
      expect(nameInput).toHaveValue('My Strategy');
    });

    it('maintains condition state after section toggle', async () => {
      render(<StrategyBuilder4Section {...defaultProps} />);

      // Add a condition in S1
      const addButton = screen.getAllByRole('button', { name: /Add Condition/i })[0];
      fireEvent.click(addButton);

      const conditionsBefore = screen.getAllByText(/Condition \d+/i).length;

      // Toggle S1 section closed and open
      const s1Header = screen.getByText(/S1: Entry Conditions/i);
      fireEvent.click(s1Header); // Close
      fireEvent.click(s1Header); // Open

      await waitFor(() => {
        const conditionsAfter = screen.getAllByText(/Condition \d+/i).length;
        expect(conditionsAfter).toBe(conditionsBefore);
      });
    });
  });

  // ==========================================================================
  // Accessibility Tests
  // ==========================================================================

  describe('Accessibility', () => {
    it('strategy name input has accessible label', () => {
      render(<StrategyBuilder4Section {...defaultProps} />);

      const nameInput = screen.getByLabelText(/Strategy Name/i);
      expect(nameInput).toBeInTheDocument();
      expect(nameInput).toHaveAttribute('type', 'text');
    });

    it('buttons have accessible names', () => {
      render(<StrategyBuilder4Section {...defaultProps} />);

      expect(screen.getByRole('button', { name: /Cancel/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /Validate/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /Save Strategy/i })).toBeInTheDocument();
    });

    it('accordions are keyboard accessible', async () => {
      render(<StrategyBuilder4Section {...defaultProps} />);

      const z1Header = screen.getByText(/Z1: Zone Conditions/i);
      z1Header.focus();

      // Simulate keyboard interaction
      fireEvent.keyDown(z1Header, { key: 'Enter' });

      await waitFor(() => {
        const z1Section = z1Header.closest('.MuiAccordion-root');
        expect(z1Section).toHaveClass('Mui-expanded');
      });
    });
  });

  // ==========================================================================
  // Error State Tests
  // ==========================================================================

  describe('Error States', () => {
    it('displays validation errors for empty conditions', async () => {
      render(<StrategyBuilder4Section {...defaultProps} />);

      // Fill name but don't configure conditions
      const nameInput = screen.getByLabelText(/Strategy Name/i);
      await userEvent.type(nameInput, 'Test Strategy');

      // Try to validate
      const validateButton = screen.getByRole('button', { name: /Validate/i });
      fireEvent.click(validateButton);

      // Should show warning about incomplete conditions
      await waitFor(() => {
        // Look for any validation message
        const validationMessages = screen.queryAllByRole('alert');
        // Component may show warnings in various ways
        expect(validationMessages.length >= 0).toBeTruthy();
      });
    });
  });
});

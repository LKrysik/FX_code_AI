/**
 * ConditionBlock Component Tests
 * ================================
 *
 * Tests for the ConditionBlock component that handles
 * individual condition configuration (indicator, operator, value).
 *
 * Test Coverage:
 * - Rendering with condition data
 * - Indicator selection
 * - Operator selection
 * - Value input
 * - Logic operator toggle
 * - Remove functionality
 * - Description generation
 *
 * Created: 2025-12-23
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom';
import { ConditionBlock } from '../ConditionBlock';
import type { Condition, IndicatorVariant, LogicOperator } from '@/types/strategy';

// ============================================================================
// Mock Data
// ============================================================================

const MOCK_INDICATORS: IndicatorVariant[] = [
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
    description: 'Exponential Moving Average',
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
    description: 'Average True Range',
    isActive: true,
  },
];

const createMockCondition = (overrides?: Partial<Condition>): Condition => ({
  id: 'test-condition-1',
  indicatorId: 'rsi_14',
  operator: '>',
  value: 30,
  logic: 'AND',
  ...overrides,
});

// ============================================================================
// Test Suite
// ============================================================================

describe('ConditionBlock', () => {
  const mockOnChange = jest.fn();
  const mockOnRemove = jest.fn();
  const mockOnLogicChange = jest.fn();

  const defaultProps = {
    condition: createMockCondition(),
    index: 0,
    availableIndicators: MOCK_INDICATORS,
    onChange: mockOnChange,
    onRemove: mockOnRemove,
  };

  beforeEach(() => {
    jest.clearAllMocks();
  });

  // ==========================================================================
  // Rendering Tests
  // ==========================================================================

  describe('Rendering', () => {
    it('renders condition with index', () => {
      render(<ConditionBlock {...defaultProps} />);

      expect(screen.getByText(/Condition 1/i)).toBeInTheDocument();
    });

    it('renders with correct index number', () => {
      render(<ConditionBlock {...defaultProps} index={2} />);

      expect(screen.getByText(/Condition 3/i)).toBeInTheDocument();
    });

    it('renders indicator selector', () => {
      render(<ConditionBlock {...defaultProps} />);

      expect(screen.getByLabelText(/Select Indicator/i)).toBeInTheDocument();
    });

    it('renders operator selector', () => {
      render(<ConditionBlock {...defaultProps} />);

      expect(screen.getByLabelText(/Operator/i)).toBeInTheDocument();
    });

    it('renders value input', () => {
      render(<ConditionBlock {...defaultProps} />);

      expect(screen.getByLabelText(/Value/i)).toBeInTheDocument();
    });

    it('renders delete button', () => {
      render(<ConditionBlock {...defaultProps} />);

      const deleteButton = document.querySelector('[data-testid="DeleteIcon"]');
      expect(deleteButton).toBeInTheDocument();
    });

    it('shows selected indicator value', () => {
      render(<ConditionBlock {...defaultProps} />);

      // RSI (14) should be selected
      expect(screen.getByText(/RSI \(14\)/i)).toBeInTheDocument();
    });
  });

  // ==========================================================================
  // Indicator Selection Tests
  // ==========================================================================

  describe('Indicator Selection', () => {
    it('shows all available indicators in dropdown', async () => {
      render(<ConditionBlock {...defaultProps} />);

      const indicatorSelect = screen.getByLabelText(/Select Indicator/i);
      fireEvent.mouseDown(indicatorSelect);

      await waitFor(() => {
        expect(screen.getByText('RSI (14)')).toBeInTheDocument();
        expect(screen.getByText('MACD (12, 26, 9)')).toBeInTheDocument();
        expect(screen.getByText('EMA (20)')).toBeInTheDocument();
        expect(screen.getByText('ATR (14)')).toBeInTheDocument();
      });
    });

    it('calls onChange when indicator selected', async () => {
      render(
        <ConditionBlock
          {...defaultProps}
          condition={createMockCondition({ indicatorId: '' })}
        />
      );

      const indicatorSelect = screen.getByLabelText(/Select Indicator/i);
      fireEvent.mouseDown(indicatorSelect);

      await waitFor(() => {
        const macdOption = screen.getByText('MACD (12, 26, 9)');
        fireEvent.click(macdOption);
      });

      expect(mockOnChange).toHaveBeenCalledWith(
        expect.objectContaining({
          indicatorId: 'macd_12_26_9',
        })
      );
    });

    it('displays indicator type chip', async () => {
      render(<ConditionBlock {...defaultProps} />);

      const indicatorSelect = screen.getByLabelText(/Select Indicator/i);
      fireEvent.mouseDown(indicatorSelect);

      await waitFor(() => {
        // Indicator types should be shown as chips
        const typeChips = screen.getAllByText(/entry_signal|order_price|stop_loss_price/i);
        expect(typeChips.length).toBeGreaterThan(0);
      });
    });
  });

  // ==========================================================================
  // Operator Selection Tests
  // ==========================================================================

  describe('Operator Selection', () => {
    it('shows all operator options', async () => {
      render(<ConditionBlock {...defaultProps} />);

      const operatorSelect = screen.getByLabelText(/Operator/i);
      fireEvent.mouseDown(operatorSelect);

      await waitFor(() => {
        expect(screen.getByText(/Greater than/i)).toBeInTheDocument();
        expect(screen.getByText(/Less than/i)).toBeInTheDocument();
        expect(screen.getByText(/Greater or equal/i)).toBeInTheDocument();
        expect(screen.getByText(/Less or equal/i)).toBeInTheDocument();
        expect(screen.getByText(/Equal to/i)).toBeInTheDocument();
      });
    });

    it('calls onChange when operator selected', async () => {
      render(<ConditionBlock {...defaultProps} />);

      const operatorSelect = screen.getByLabelText(/Operator/i);
      fireEvent.mouseDown(operatorSelect);

      await waitFor(() => {
        const lessOption = screen.getByRole('option', { name: /Less than/i });
        fireEvent.click(lessOption);
      });

      expect(mockOnChange).toHaveBeenCalledWith(
        expect.objectContaining({
          operator: '<',
        })
      );
    });

    it('operator is disabled when no indicator selected', () => {
      render(
        <ConditionBlock
          {...defaultProps}
          condition={createMockCondition({ indicatorId: '' })}
        />
      );

      const operatorSelect = screen.getByLabelText(/Operator/i).closest('.MuiInputBase-root');
      expect(operatorSelect).toHaveClass('Mui-disabled');
    });
  });

  // ==========================================================================
  // Value Input Tests
  // ==========================================================================

  describe('Value Input', () => {
    it('displays current value', () => {
      render(<ConditionBlock {...defaultProps} />);

      const valueInput = screen.getByLabelText(/Value/i);
      expect(valueInput).toHaveValue(30);
    });

    it('calls onChange when value changed', async () => {
      render(<ConditionBlock {...defaultProps} />);

      const valueInput = screen.getByLabelText(/Value/i);
      await userEvent.clear(valueInput);
      await userEvent.type(valueInput, '50');

      expect(mockOnChange).toHaveBeenCalledWith(
        expect.objectContaining({
          value: 50,
        })
      );
    });

    it('value is disabled when no indicator selected', () => {
      render(
        <ConditionBlock
          {...defaultProps}
          condition={createMockCondition({ indicatorId: '' })}
        />
      );

      const valueInput = screen.getByLabelText(/Value/i);
      expect(valueInput).toBeDisabled();
    });

    it('accepts decimal values', async () => {
      render(<ConditionBlock {...defaultProps} />);

      const valueInput = screen.getByLabelText(/Value/i);
      await userEvent.clear(valueInput);
      await userEvent.type(valueInput, '0.5');

      expect(mockOnChange).toHaveBeenCalledWith(
        expect.objectContaining({
          value: 0.5,
        })
      );
    });

    it('accepts negative values', async () => {
      render(<ConditionBlock {...defaultProps} />);

      const valueInput = screen.getByLabelText(/Value/i);
      await userEvent.clear(valueInput);
      await userEvent.type(valueInput, '-10');

      expect(mockOnChange).toHaveBeenCalledWith(
        expect.objectContaining({
          value: -10,
        })
      );
    });
  });

  // ==========================================================================
  // Remove Functionality Tests
  // ==========================================================================

  describe('Remove Functionality', () => {
    it('calls onRemove when delete button clicked', () => {
      render(<ConditionBlock {...defaultProps} />);

      const deleteButton = document.querySelector('[data-testid="DeleteIcon"]')?.closest('button');
      if (deleteButton) {
        fireEvent.click(deleteButton);
      }

      expect(mockOnRemove).toHaveBeenCalledTimes(1);
    });
  });

  // ==========================================================================
  // Logic Operator Tests
  // ==========================================================================

  describe('Logic Operator', () => {
    it('shows logic chip when not last condition', () => {
      render(
        <ConditionBlock
          {...defaultProps}
          isLastCondition={false}
          onLogicChange={mockOnLogicChange}
        />
      );

      // Should show AND chip
      expect(screen.getByText('AND')).toBeInTheDocument();
    });

    it('hides logic chip for last condition', () => {
      render(
        <ConditionBlock
          {...defaultProps}
          isLastCondition={true}
          onLogicChange={mockOnLogicChange}
        />
      );

      // Logic chip should not be visible in the condition header
      const conditionHeader = screen.getByText(/Condition 1/i).parentElement;
      const logicChip = conditionHeader?.querySelector('.MuiChip-root');
      // It may show logic chip elsewhere, but not in header area for last condition
      expect(conditionHeader?.textContent).not.toContain('AND');
    });

    it('clicking logic chip toggles between AND and OR', () => {
      render(
        <ConditionBlock
          {...defaultProps}
          logicType="AND"
          isLastCondition={false}
          onLogicChange={mockOnLogicChange}
        />
      );

      const andChip = screen.getByText('AND').closest('.MuiChip-root');
      if (andChip) {
        fireEvent.click(andChip);
      }

      expect(mockOnLogicChange).toHaveBeenCalledWith('OR');
    });

    it('displays correct color for AND chip', () => {
      render(
        <ConditionBlock
          {...defaultProps}
          logicType="AND"
          isLastCondition={false}
          onLogicChange={mockOnLogicChange}
        />
      );

      const andChip = screen.getByText('AND').closest('.MuiChip-root');
      expect(andChip).toHaveClass('MuiChip-colorPrimary');
    });

    it('displays correct color for OR chip', () => {
      render(
        <ConditionBlock
          {...defaultProps}
          logicType="OR"
          isLastCondition={false}
          onLogicChange={mockOnLogicChange}
        />
      );

      const orChip = screen.getByText('OR').closest('.MuiChip-root');
      expect(orChip).toHaveClass('MuiChip-colorSuccess');
    });
  });

  // ==========================================================================
  // Description Generation Tests
  // ==========================================================================

  describe('Description Generation', () => {
    it('generates description for configured condition', () => {
      render(<ConditionBlock {...defaultProps} />);

      expect(screen.getByText(/RSI \(14\) must be greater than 30/i)).toBeInTheDocument();
    });

    it('shows placeholder when no indicator selected', () => {
      render(
        <ConditionBlock
          {...defaultProps}
          condition={createMockCondition({ indicatorId: '' })}
        />
      );

      expect(screen.getByText(/Select an indicator/i)).toBeInTheDocument();
    });

    it('generates correct description for less than operator', () => {
      render(
        <ConditionBlock
          {...defaultProps}
          condition={createMockCondition({ operator: '<', value: 70 })}
        />
      );

      expect(screen.getByText(/RSI \(14\) must be less than 70/i)).toBeInTheDocument();
    });

    it('generates correct description for equal operator', () => {
      render(
        <ConditionBlock
          {...defaultProps}
          condition={createMockCondition({ operator: '==', value: 50 })}
        />
      );

      expect(screen.getByText(/RSI \(14\) must be equal to 50/i)).toBeInTheDocument();
    });

    it('adds NOT prefix for NOT logic', () => {
      render(
        <ConditionBlock
          {...defaultProps}
          logicType="NOT"
        />
      );

      expect(screen.getByText(/NOT RSI \(14\)/i)).toBeInTheDocument();
    });
  });

  // ==========================================================================
  // Indicator Details Tests
  // ==========================================================================

  describe('Indicator Details', () => {
    it('shows current indicator value', () => {
      render(<ConditionBlock {...defaultProps} />);

      expect(screen.getByText(/Current: 45.2/i)).toBeInTheDocument();
    });

    it('shows last update time', () => {
      render(<ConditionBlock {...defaultProps} />);

      expect(screen.getByText(/Updated:/i)).toBeInTheDocument();
    });

    it('toggles details section on expand click', async () => {
      render(<ConditionBlock {...defaultProps} />);

      // Find expand button
      const expandButton = document.querySelector('[data-testid="ExpandMoreIcon"]')?.closest('button');

      if (expandButton) {
        fireEvent.click(expandButton);

        await waitFor(() => {
          expect(screen.getByText(/Variant Details/i)).toBeInTheDocument();
        });
      }
    });

    it('shows indicator parameters in details', async () => {
      render(<ConditionBlock {...defaultProps} />);

      const expandButton = document.querySelector('[data-testid="ExpandMoreIcon"]')?.closest('button');

      if (expandButton) {
        fireEvent.click(expandButton);

        await waitFor(() => {
          expect(screen.getByText(/period=14/i)).toBeInTheDocument();
        });
      }
    });
  });

  // ==========================================================================
  // Empty State Tests
  // ==========================================================================

  describe('Empty State', () => {
    it('renders correctly with empty indicator', () => {
      render(
        <ConditionBlock
          {...defaultProps}
          condition={createMockCondition({ indicatorId: '' })}
        />
      );

      expect(screen.getByLabelText(/Select Indicator/i)).toBeInTheDocument();
      expect(screen.getByText(/Select an indicator/i)).toBeInTheDocument();
    });

    it('does not show indicator details when no indicator selected', () => {
      render(
        <ConditionBlock
          {...defaultProps}
          condition={createMockCondition({ indicatorId: '' })}
        />
      );

      expect(screen.queryByText(/Current:/i)).not.toBeInTheDocument();
    });
  });

  // ==========================================================================
  // Accessibility Tests
  // ==========================================================================

  describe('Accessibility', () => {
    it('indicator select has accessible label', () => {
      render(<ConditionBlock {...defaultProps} />);

      const indicatorSelect = screen.getByLabelText(/Select Indicator/i);
      expect(indicatorSelect).toBeInTheDocument();
    });

    it('operator select has accessible label', () => {
      render(<ConditionBlock {...defaultProps} />);

      const operatorSelect = screen.getByLabelText(/Operator/i);
      expect(operatorSelect).toBeInTheDocument();
    });

    it('value input has accessible label', () => {
      render(<ConditionBlock {...defaultProps} />);

      const valueInput = screen.getByLabelText(/Value/i);
      expect(valueInput).toBeInTheDocument();
    });

    it('delete button is keyboard accessible', () => {
      render(<ConditionBlock {...defaultProps} />);

      const deleteButton = document.querySelector('[data-testid="DeleteIcon"]')?.closest('button');
      expect(deleteButton).not.toBeNull();
      expect(deleteButton?.getAttribute('tabindex')).not.toBe('-1');
    });
  });
});

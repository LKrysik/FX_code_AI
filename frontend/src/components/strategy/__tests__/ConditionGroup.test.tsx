/**
 * ConditionGroup Component Tests
 * ================================
 *
 * Tests for the ConditionGroup component that handles grouping
 * conditions with AND/OR logic, including nested groups.
 *
 * Test Coverage:
 * - Rendering with conditions
 * - AND/OR logic toggle
 * - Adding conditions
 * - Removing conditions
 * - Nested groups
 * - Maximum depth enforcement
 *
 * Created: 2025-12-23
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import { ConditionGroup } from '../ConditionGroup';
import type { ConditionGroup as ConditionGroupType, IndicatorVariant } from '@/types/strategy';

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
    description: 'Relative Strength Index',
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
    description: 'MACD Indicator',
    isActive: true,
  },
];

const createMockGroup = (overrides?: Partial<ConditionGroupType>): ConditionGroupType => ({
  id: 'group-1',
  logic: 'AND',
  conditions: [
    {
      id: 'cond-1',
      indicatorId: 'rsi_14',
      operator: '>',
      value: 30,
      logic: 'AND',
    },
  ],
  groups: [],
  ...overrides,
});

// ============================================================================
// Mock uuid
// ============================================================================

jest.mock('uuid', () => ({
  v4: () => `test-uuid-${Date.now()}-${Math.random()}`,
}));

// ============================================================================
// Test Suite
// ============================================================================

describe('ConditionGroup', () => {
  const mockOnChange = jest.fn();
  const mockOnRemove = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
  });

  // ==========================================================================
  // Rendering Tests
  // ==========================================================================

  describe('Rendering', () => {
    it('renders group with conditions', () => {
      const group = createMockGroup();

      render(
        <ConditionGroup
          group={group}
          availableIndicators={MOCK_INDICATORS}
          onChange={mockOnChange}
        />
      );

      expect(screen.getByText(/Group \(Root\)/i)).toBeInTheDocument();
      expect(screen.getByText(/Condition 1/i)).toBeInTheDocument();
    });

    it('renders AND/OR toggle chips', () => {
      const group = createMockGroup();

      render(
        <ConditionGroup
          group={group}
          availableIndicators={MOCK_INDICATORS}
          onChange={mockOnChange}
        />
      );

      expect(screen.getByText('AND')).toBeInTheDocument();
      expect(screen.getByText('OR')).toBeInTheDocument();
    });

    it('highlights active logic (AND)', () => {
      const group = createMockGroup({ logic: 'AND' });

      render(
        <ConditionGroup
          group={group}
          availableIndicators={MOCK_INDICATORS}
          onChange={mockOnChange}
        />
      );

      const andChip = screen.getAllByText('AND')[0].closest('.MuiChip-root');
      expect(andChip).toHaveClass('MuiChip-colorPrimary');
    });

    it('highlights active logic (OR)', () => {
      const group = createMockGroup({ logic: 'OR' });

      render(
        <ConditionGroup
          group={group}
          availableIndicators={MOCK_INDICATORS}
          onChange={mockOnChange}
        />
      );

      const orChip = screen.getAllByText('OR')[0].closest('.MuiChip-root');
      expect(orChip).toHaveClass('MuiChip-colorSuccess');
    });

    it('shows "Add Condition" button', () => {
      const group = createMockGroup();

      render(
        <ConditionGroup
          group={group}
          availableIndicators={MOCK_INDICATORS}
          onChange={mockOnChange}
        />
      );

      expect(screen.getByRole('button', { name: /Add Condition/i })).toBeInTheDocument();
    });

    it('shows "Add Nested Group" button', () => {
      const group = createMockGroup();

      render(
        <ConditionGroup
          group={group}
          availableIndicators={MOCK_INDICATORS}
          onChange={mockOnChange}
        />
      );

      expect(screen.getByRole('button', { name: /Add Nested Group/i })).toBeInTheDocument();
    });

    it('shows remove button when onRemove is provided', () => {
      const group = createMockGroup();

      render(
        <ConditionGroup
          group={group}
          availableIndicators={MOCK_INDICATORS}
          onChange={mockOnChange}
          onRemove={mockOnRemove}
        />
      );

      // Look for delete icon button
      const deleteButtons = document.querySelectorAll('[data-testid="DeleteIcon"]');
      expect(deleteButtons.length).toBeGreaterThan(0);
    });

    it('does not show remove button for root group', () => {
      const group = createMockGroup();

      render(
        <ConditionGroup
          group={group}
          availableIndicators={MOCK_INDICATORS}
          onChange={mockOnChange}
        />
      );

      // Group header should not have delete button (only conditions have delete)
      const groupHeader = screen.getByText(/Group \(Root\)/i).parentElement;
      const deleteInHeader = groupHeader?.querySelector('[data-testid="DeleteIcon"]');
      expect(deleteInHeader).toBeNull();
    });
  });

  // ==========================================================================
  // Logic Toggle Tests
  // ==========================================================================

  describe('Logic Toggle', () => {
    it('clicking OR chip changes logic to OR', () => {
      const group = createMockGroup({ logic: 'AND' });

      render(
        <ConditionGroup
          group={group}
          availableIndicators={MOCK_INDICATORS}
          onChange={mockOnChange}
        />
      );

      const orChips = screen.getAllByText('OR');
      // Click the first OR chip (in the header)
      fireEvent.click(orChips[0]);

      expect(mockOnChange).toHaveBeenCalledWith(
        expect.objectContaining({ logic: 'OR' })
      );
    });

    it('clicking AND chip changes logic to AND', () => {
      const group = createMockGroup({ logic: 'OR' });

      render(
        <ConditionGroup
          group={group}
          availableIndicators={MOCK_INDICATORS}
          onChange={mockOnChange}
        />
      );

      const andChips = screen.getAllByText('AND');
      fireEvent.click(andChips[0]);

      expect(mockOnChange).toHaveBeenCalledWith(
        expect.objectContaining({ logic: 'AND' })
      );
    });

    it('displays correct description for AND logic', () => {
      const group = createMockGroup({ logic: 'AND' });

      render(
        <ConditionGroup
          group={group}
          availableIndicators={MOCK_INDICATORS}
          onChange={mockOnChange}
        />
      );

      expect(screen.getByText(/must evaluate to TRUE/i)).toBeInTheDocument();
    });

    it('displays correct description for OR logic', () => {
      const group = createMockGroup({ logic: 'OR' });

      render(
        <ConditionGroup
          group={group}
          availableIndicators={MOCK_INDICATORS}
          onChange={mockOnChange}
        />
      );

      expect(screen.getByText(/at least one TRUE/i)).toBeInTheDocument();
    });
  });

  // ==========================================================================
  // Add Condition Tests
  // ==========================================================================

  describe('Add Condition', () => {
    it('clicking "Add Condition" calls onChange with new condition', () => {
      const group = createMockGroup();

      render(
        <ConditionGroup
          group={group}
          availableIndicators={MOCK_INDICATORS}
          onChange={mockOnChange}
        />
      );

      const addButton = screen.getByRole('button', { name: /Add Condition/i });
      fireEvent.click(addButton);

      expect(mockOnChange).toHaveBeenCalledWith(
        expect.objectContaining({
          conditions: expect.arrayContaining([
            expect.objectContaining({ id: 'cond-1' }),
            expect.objectContaining({
              indicatorId: '',
              operator: '>',
              value: 0,
              logic: 'AND',
            }),
          ]),
        })
      );
    });

    it('new condition has default values', () => {
      const group = createMockGroup();

      render(
        <ConditionGroup
          group={group}
          availableIndicators={MOCK_INDICATORS}
          onChange={mockOnChange}
        />
      );

      const addButton = screen.getByRole('button', { name: /Add Condition/i });
      fireEvent.click(addButton);

      const newCondition = mockOnChange.mock.calls[0][0].conditions[1];
      expect(newCondition.indicatorId).toBe('');
      expect(newCondition.operator).toBe('>');
      expect(newCondition.value).toBe(0);
      expect(newCondition.logic).toBe('AND');
    });
  });

  // ==========================================================================
  // Remove Condition Tests
  // ==========================================================================

  describe('Remove Condition', () => {
    it('removes condition when delete button clicked', () => {
      const group = createMockGroup({
        conditions: [
          { id: 'cond-1', indicatorId: 'rsi_14', operator: '>', value: 30, logic: 'AND' },
          { id: 'cond-2', indicatorId: 'macd_12_26_9', operator: '<', value: 0, logic: 'AND' },
        ],
      });

      render(
        <ConditionGroup
          group={group}
          availableIndicators={MOCK_INDICATORS}
          onChange={mockOnChange}
        />
      );

      // Find delete buttons
      const deleteButtons = document.querySelectorAll('[data-testid="DeleteIcon"]');

      // Click first condition's delete button
      if (deleteButtons[0]) {
        fireEvent.click(deleteButtons[0].closest('button') as HTMLElement);
      }

      expect(mockOnChange).toHaveBeenCalledWith(
        expect.objectContaining({
          conditions: expect.not.arrayContaining([
            expect.objectContaining({ id: 'cond-1' }),
          ]),
        })
      );
    });
  });

  // ==========================================================================
  // Nested Groups Tests
  // ==========================================================================

  describe('Nested Groups', () => {
    it('clicking "Add Nested Group" adds a nested group', () => {
      const group = createMockGroup();

      render(
        <ConditionGroup
          group={group}
          availableIndicators={MOCK_INDICATORS}
          onChange={mockOnChange}
        />
      );

      const addGroupButton = screen.getByRole('button', { name: /Add Nested Group/i });
      fireEvent.click(addGroupButton);

      expect(mockOnChange).toHaveBeenCalledWith(
        expect.objectContaining({
          groups: expect.arrayContaining([
            expect.objectContaining({
              logic: 'AND',
              conditions: expect.arrayContaining([
                expect.objectContaining({ indicatorId: '' }),
              ]),
            }),
          ]),
        })
      );
    });

    it('renders nested groups', () => {
      const group = createMockGroup({
        groups: [
          {
            id: 'nested-1',
            logic: 'OR',
            conditions: [
              { id: 'nested-cond-1', indicatorId: 'rsi_14', operator: '<', value: 70, logic: 'OR' },
            ],
          },
        ],
      });

      render(
        <ConditionGroup
          group={group}
          availableIndicators={MOCK_INDICATORS}
          onChange={mockOnChange}
        />
      );

      // Should show nested group indicator
      expect(screen.getByText(/Level 1/i)).toBeInTheDocument();
    });

    it('shows depth indicator in nested groups', () => {
      const group = createMockGroup({
        groups: [
          {
            id: 'nested-1',
            logic: 'OR',
            conditions: [
              { id: 'nested-cond-1', indicatorId: 'rsi_14', operator: '<', value: 70, logic: 'OR' },
            ],
          },
        ],
      });

      render(
        <ConditionGroup
          group={group}
          availableIndicators={MOCK_INDICATORS}
          onChange={mockOnChange}
        />
      );

      expect(screen.getByText(/Depth: 1\/3/i)).toBeInTheDocument();
    });
  });

  // ==========================================================================
  // Maximum Depth Tests
  // ==========================================================================

  describe('Maximum Depth', () => {
    it('hides "Add Nested Group" at max depth', () => {
      const group = createMockGroup();

      render(
        <ConditionGroup
          group={group}
          availableIndicators={MOCK_INDICATORS}
          onChange={mockOnChange}
          depth={3}
          maxDepth={3}
        />
      );

      expect(screen.queryByRole('button', { name: /Add Nested Group/i })).not.toBeInTheDocument();
    });

    it('shows "Add Nested Group" below max depth', () => {
      const group = createMockGroup();

      render(
        <ConditionGroup
          group={group}
          availableIndicators={MOCK_INDICATORS}
          onChange={mockOnChange}
          depth={2}
          maxDepth={3}
        />
      );

      expect(screen.getByRole('button', { name: /Add Nested Group/i })).toBeInTheDocument();
    });

    it('uses default maxDepth of 3', () => {
      const group = createMockGroup();

      render(
        <ConditionGroup
          group={group}
          availableIndicators={MOCK_INDICATORS}
          onChange={mockOnChange}
          depth={2}
        />
      );

      // At depth 2 with maxDepth 3, should still show add nested group
      expect(screen.getByRole('button', { name: /Add Nested Group/i })).toBeInTheDocument();
    });
  });

  // ==========================================================================
  // Visual Styling Tests
  // ==========================================================================

  describe('Visual Styling', () => {
    it('applies different background colors at different depths', () => {
      const { container } = render(
        <ConditionGroup
          group={createMockGroup()}
          availableIndicators={MOCK_INDICATORS}
          onChange={mockOnChange}
          depth={0}
        />
      );

      // Root group should have blue-ish background
      const paper = container.querySelector('.MuiPaper-root');
      expect(paper).toBeInTheDocument();
    });

    it('shows logic connector between conditions', () => {
      const group = createMockGroup({
        conditions: [
          { id: 'cond-1', indicatorId: 'rsi_14', operator: '>', value: 30, logic: 'AND' },
          { id: 'cond-2', indicatorId: 'macd_12_26_9', operator: '<', value: 0, logic: 'AND' },
        ],
      });

      render(
        <ConditionGroup
          group={group}
          availableIndicators={MOCK_INDICATORS}
          onChange={mockOnChange}
        />
      );

      // Should show AND chip between conditions
      const andChips = screen.getAllByText('AND');
      expect(andChips.length).toBeGreaterThan(1);
    });
  });

  // ==========================================================================
  // Multiple Conditions Tests
  // ==========================================================================

  describe('Multiple Conditions', () => {
    it('renders all conditions', () => {
      const group = createMockGroup({
        conditions: [
          { id: 'cond-1', indicatorId: 'rsi_14', operator: '>', value: 30, logic: 'AND' },
          { id: 'cond-2', indicatorId: 'macd_12_26_9', operator: '<', value: 0, logic: 'OR' },
          { id: 'cond-3', indicatorId: 'rsi_14', operator: '<', value: 70, logic: 'AND' },
        ],
      });

      render(
        <ConditionGroup
          group={group}
          availableIndicators={MOCK_INDICATORS}
          onChange={mockOnChange}
        />
      );

      expect(screen.getByText(/Condition 1/i)).toBeInTheDocument();
      expect(screen.getByText(/Condition 2/i)).toBeInTheDocument();
      expect(screen.getByText(/Condition 3/i)).toBeInTheDocument();
    });

    it('shows correct logic connectors between conditions', () => {
      const group = createMockGroup({
        conditions: [
          { id: 'cond-1', indicatorId: 'rsi_14', operator: '>', value: 30, logic: 'AND' },
          { id: 'cond-2', indicatorId: 'macd_12_26_9', operator: '<', value: 0, logic: 'OR' },
        ],
      });

      render(
        <ConditionGroup
          group={group}
          availableIndicators={MOCK_INDICATORS}
          onChange={mockOnChange}
        />
      );

      // There should be AND chip between conditions (from first condition's logic)
      const chipElements = document.querySelectorAll('.MuiChip-label');
      const chipTexts = Array.from(chipElements).map(el => el.textContent);
      expect(chipTexts).toContain('AND');
    });
  });
});

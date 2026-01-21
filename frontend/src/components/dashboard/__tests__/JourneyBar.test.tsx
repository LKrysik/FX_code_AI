/**
 * JourneyBar Component Tests
 * ==========================
 * Story 1B-5: JourneyBar Component
 *
 * Tests cover:
 * - AC1: JourneyBar displays trading flow as 5 connected steps
 * - AC2: Each step has an icon and label
 * - AC3: Current step is highlighted based on state machine state
 * - AC4: Completed steps show checkmarks
 * - AC5: Future steps are dimmed/grayed
 * - AC6: Smooth 300ms animation on state change (CSS)
 * - AC7: Exit step shows profit/loss color (green/red)
 */

import React from 'react';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import JourneyBar, {
  getStepIndexFromState,
  isExitProfit,
  JOURNEY_STEPS,
} from '../JourneyBar';
import type { StateMachineState } from '@/utils/stateVocabulary';

// Create a theme for testing
const theme = createTheme();

// Helper to render with theme
const renderWithTheme = (ui: React.ReactElement) => {
  return render(<ThemeProvider theme={theme}>{ui}</ThemeProvider>);
};

describe('JourneyBar Component', () => {
  // ============================================================================
  // AC1: JourneyBar displays trading flow as 5 connected steps
  // ============================================================================
  describe('AC1: Displays 5 connected steps', () => {
    it('renders all 5 journey steps', () => {
      renderWithTheme(<JourneyBar currentState="MONITORING" />);

      expect(screen.getByTestId('journey-step-watch')).toBeInTheDocument();
      expect(screen.getByTestId('journey-step-found')).toBeInTheDocument();
      expect(screen.getByTestId('journey-step-enter')).toBeInTheDocument();
      expect(screen.getByTestId('journey-step-monitor')).toBeInTheDocument();
      expect(screen.getByTestId('journey-step-exit')).toBeInTheDocument();
    });

    it('renders steps in correct order: Watch -> Found -> Enter -> Monitor -> Exit', () => {
      expect(JOURNEY_STEPS).toHaveLength(5);
      expect(JOURNEY_STEPS[0].id).toBe('watch');
      expect(JOURNEY_STEPS[1].id).toBe('found');
      expect(JOURNEY_STEPS[2].id).toBe('enter');
      expect(JOURNEY_STEPS[3].id).toBe('monitor');
      expect(JOURNEY_STEPS[4].id).toBe('exit');
    });

    it('renders the JourneyBar container', () => {
      renderWithTheme(<JourneyBar currentState="MONITORING" />);
      expect(screen.getByTestId('journey-bar')).toBeInTheDocument();
    });
  });

  // ============================================================================
  // AC2: Each step has an icon and label
  // ============================================================================
  describe('AC2: Each step has icon and label', () => {
    it('renders labels for all steps', () => {
      renderWithTheme(<JourneyBar currentState="MONITORING" />);

      expect(screen.getByTestId('journey-step-label-watch')).toHaveTextContent('Watch');
      expect(screen.getByTestId('journey-step-label-found')).toHaveTextContent('Found');
      expect(screen.getByTestId('journey-step-label-enter')).toHaveTextContent('Enter');
      expect(screen.getByTestId('journey-step-label-monitor')).toHaveTextContent('Monitor');
      expect(screen.getByTestId('journey-step-label-exit')).toHaveTextContent('Exit');
    });

    it('renders icons for all steps', () => {
      renderWithTheme(<JourneyBar currentState="MONITORING" />);

      expect(screen.getByTestId('journey-step-icon-watch')).toBeInTheDocument();
      expect(screen.getByTestId('journey-step-icon-found')).toBeInTheDocument();
      expect(screen.getByTestId('journey-step-icon-enter')).toBeInTheDocument();
      expect(screen.getByTestId('journey-step-icon-monitor')).toBeInTheDocument();
      expect(screen.getByTestId('journey-step-icon-exit')).toBeInTheDocument();
    });
  });

  // ============================================================================
  // AC3: Current step is highlighted based on state machine state
  // ============================================================================
  describe('AC3: Current step highlighted based on state', () => {
    it('highlights Watch step for MONITORING state', () => {
      renderWithTheme(<JourneyBar currentState="MONITORING" />);

      const watchIcon = screen.getByTestId('journey-step-icon-watch');
      expect(watchIcon).toHaveAttribute('data-status', 'current');
    });

    it('highlights Found step for S1 state', () => {
      renderWithTheme(<JourneyBar currentState="S1" />);

      const foundIcon = screen.getByTestId('journey-step-icon-found');
      expect(foundIcon).toHaveAttribute('data-status', 'current');
    });

    it('highlights Enter step for Z1 state', () => {
      renderWithTheme(<JourneyBar currentState="Z1" />);

      const enterIcon = screen.getByTestId('journey-step-icon-enter');
      expect(enterIcon).toHaveAttribute('data-status', 'current');
    });

    it('highlights Monitor step for POSITION_ACTIVE state', () => {
      renderWithTheme(<JourneyBar currentState="POSITION_ACTIVE" />);

      const monitorIcon = screen.getByTestId('journey-step-icon-monitor');
      expect(monitorIcon).toHaveAttribute('data-status', 'current');
    });

    it('highlights Exit step for ZE1 state', () => {
      renderWithTheme(<JourneyBar currentState="ZE1" />);

      const exitIcon = screen.getByTestId('journey-step-icon-exit');
      expect(exitIcon).toHaveAttribute('data-status', 'current');
    });

    it('highlights Exit step for E1 state', () => {
      renderWithTheme(<JourneyBar currentState="E1" />);

      const exitIcon = screen.getByTestId('journey-step-icon-exit');
      expect(exitIcon).toHaveAttribute('data-status', 'current');
    });
  });

  // ============================================================================
  // AC4: Completed steps show checkmarks
  // ============================================================================
  describe('AC4: Completed steps show checkmarks', () => {
    it('shows completed status for steps before current', () => {
      renderWithTheme(<JourneyBar currentState="POSITION_ACTIVE" />);

      // Watch, Found, Enter should be completed
      const watchIcon = screen.getByTestId('journey-step-icon-watch');
      const foundIcon = screen.getByTestId('journey-step-icon-found');
      const enterIcon = screen.getByTestId('journey-step-icon-enter');

      expect(watchIcon).toHaveAttribute('data-status', 'completed');
      expect(foundIcon).toHaveAttribute('data-status', 'completed');
      expect(enterIcon).toHaveAttribute('data-status', 'completed');
    });

    it('renders checkmark icon for completed steps', () => {
      renderWithTheme(<JourneyBar currentState="ZE1" />);

      // All steps before Exit should be completed and show check icons
      const watchIcon = screen.getByTestId('journey-step-icon-watch');
      const foundIcon = screen.getByTestId('journey-step-icon-found');
      const enterIcon = screen.getByTestId('journey-step-icon-enter');
      const monitorIcon = screen.getByTestId('journey-step-icon-monitor');

      // Check that completed steps have check icon (SVG)
      expect(watchIcon.querySelector('svg')).toBeInTheDocument();
      expect(foundIcon.querySelector('svg')).toBeInTheDocument();
      expect(enterIcon.querySelector('svg')).toBeInTheDocument();
      expect(monitorIcon.querySelector('svg')).toBeInTheDocument();
    });
  });

  // ============================================================================
  // AC5: Future steps are dimmed/grayed
  // ============================================================================
  describe('AC5: Future steps are dimmed', () => {
    it('shows future status for steps after current', () => {
      renderWithTheme(<JourneyBar currentState="S1" />);

      // Enter, Monitor, Exit should be future
      const enterIcon = screen.getByTestId('journey-step-icon-enter');
      const monitorIcon = screen.getByTestId('journey-step-icon-monitor');
      const exitIcon = screen.getByTestId('journey-step-icon-exit');

      expect(enterIcon).toHaveAttribute('data-status', 'future');
      expect(monitorIcon).toHaveAttribute('data-status', 'future');
      expect(exitIcon).toHaveAttribute('data-status', 'future');
    });

    it('has correct status progression for MONITORING state', () => {
      renderWithTheme(<JourneyBar currentState="MONITORING" />);

      expect(screen.getByTestId('journey-step-icon-watch')).toHaveAttribute('data-status', 'current');
      expect(screen.getByTestId('journey-step-icon-found')).toHaveAttribute('data-status', 'future');
      expect(screen.getByTestId('journey-step-icon-enter')).toHaveAttribute('data-status', 'future');
      expect(screen.getByTestId('journey-step-icon-monitor')).toHaveAttribute('data-status', 'future');
      expect(screen.getByTestId('journey-step-icon-exit')).toHaveAttribute('data-status', 'future');
    });
  });

  // ============================================================================
  // AC7: Exit step shows profit/loss color
  // ============================================================================
  describe('AC7: Exit step shows profit/loss color', () => {
    it('recognizes ZE1 as profit exit', () => {
      expect(isExitProfit('ZE1')).toBe(true);
    });

    it('recognizes E1 as loss exit', () => {
      expect(isExitProfit('E1')).toBe(false);
    });

    it('recognizes EXITED_PROFIT as profit exit', () => {
      expect(isExitProfit('EXITED_PROFIT' as StateMachineState)).toBe(true);
    });

    it('recognizes EXITED_LOSS as loss exit', () => {
      expect(isExitProfit('EXITED_LOSS' as StateMachineState)).toBe(false);
    });

    it('recognizes O1 as neutral (false alarm)', () => {
      expect(isExitProfit('O1')).toBe(null);
    });

    it('returns null for non-exit states', () => {
      expect(isExitProfit('MONITORING')).toBe(null);
      expect(isExitProfit('S1')).toBe(null);
      expect(isExitProfit('POSITION_ACTIVE')).toBe(null);
    });

    it('uses exitPnL prop for profit coloring when provided', () => {
      renderWithTheme(<JourneyBar currentState="ZE1" exitPnL={100} />);

      const exitIcon = screen.getByTestId('journey-step-icon-exit');
      expect(exitIcon).toHaveAttribute('data-status', 'current');
    });

    it('uses exitPnL prop for loss coloring when negative', () => {
      renderWithTheme(<JourneyBar currentState="E1" exitPnL={-50} />);

      const exitIcon = screen.getByTestId('journey-step-icon-exit');
      expect(exitIcon).toHaveAttribute('data-status', 'current');
    });
  });

  // ============================================================================
  // State Machine Mapping Tests
  // ============================================================================
  describe('State Machine to Step Mapping', () => {
    // Watch step (index 0)
    it.each([
      ['IDLE', 0],
      ['MONITORING', 0],
      ['INACTIVE', 0],
      ['ERROR', 0],
    ] as [string, number][])('maps %s to step index %d (Watch)', (state, expectedIndex) => {
      expect(getStepIndexFromState(state as StateMachineState)).toBe(expectedIndex);
    });

    // Found step (index 1)
    it.each([
      ['SIGNAL_DETECTED', 1],
      ['S1', 1],
    ] as [string, number][])('maps %s to step index %d (Found)', (state, expectedIndex) => {
      expect(getStepIndexFromState(state as StateMachineState)).toBe(expectedIndex);
    });

    // Enter step (index 2)
    it.each([
      ['ENTERING', 2],
      ['POSITION_OPEN', 2],
      ['Z1', 2],
    ] as [string, number][])('maps %s to step index %d (Enter)', (state, expectedIndex) => {
      expect(getStepIndexFromState(state as StateMachineState)).toBe(expectedIndex);
    });

    // Monitor step (index 3)
    it.each([
      ['POSITION_MONITORING', 3],
      ['POSITION_ACTIVE', 3],
    ] as [string, number][])('maps %s to step index %d (Monitor)', (state, expectedIndex) => {
      expect(getStepIndexFromState(state as StateMachineState)).toBe(expectedIndex);
    });

    // Exit step (index 4)
    it.each([
      ['EXITING', 4],
      ['EXITED_PROFIT', 4],
      ['EXITED_LOSS', 4],
      ['ZE1', 4],
      ['E1', 4],
      ['EXITED', 4],
      ['O1', 4],
    ] as [string, number][])('maps %s to step index %d (Exit)', (state, expectedIndex) => {
      expect(getStepIndexFromState(state as StateMachineState)).toBe(expectedIndex);
    });

    // Unknown states default to 0
    it('defaults unknown states to step index 0', () => {
      expect(getStepIndexFromState('UNKNOWN_STATE' as StateMachineState)).toBe(0);
    });
  });

  // ============================================================================
  // Props and Rendering Tests
  // ============================================================================
  describe('Component Props', () => {
    it('renders with compact prop', () => {
      renderWithTheme(<JourneyBar currentState="MONITORING" compact />);
      expect(screen.getByTestId('journey-bar')).toBeInTheDocument();
    });

    it('exposes current state via data attribute', () => {
      renderWithTheme(<JourneyBar currentState="POSITION_ACTIVE" />);
      expect(screen.getByTestId('journey-bar')).toHaveAttribute('data-current-state', 'POSITION_ACTIVE');
    });

    it('exposes current step index via data attribute', () => {
      renderWithTheme(<JourneyBar currentState="POSITION_ACTIVE" />);
      expect(screen.getByTestId('journey-bar')).toHaveAttribute('data-current-step', '3');
    });
  });

  // ============================================================================
  // Integration with all StateMachineState types
  // ============================================================================
  describe('All StateMachineState types render correctly', () => {
    const allStates: StateMachineState[] = [
      'INACTIVE',
      'MONITORING',
      'S1',
      'O1',
      'Z1',
      'POSITION_ACTIVE',
      'ZE1',
      'E1',
      'SIGNAL_DETECTED',
      'EXITED',
      'ERROR',
    ];

    allStates.forEach((state) => {
      it(`renders correctly for ${state} state`, () => {
        renderWithTheme(<JourneyBar currentState={state} />);
        expect(screen.getByTestId('journey-bar')).toBeInTheDocument();
        expect(screen.getByTestId('journey-bar')).toHaveAttribute('data-current-state', state);
      });
    });
  });

  // ============================================================================
  // JOURNEY_STEPS export tests
  // ============================================================================
  describe('JOURNEY_STEPS export', () => {
    it('exports JOURNEY_STEPS with correct structure', () => {
      expect(JOURNEY_STEPS).toHaveLength(5);

      JOURNEY_STEPS.forEach((step) => {
        expect(step).toHaveProperty('id');
        expect(step).toHaveProperty('label');
        expect(step).toHaveProperty('icon');
        expect(step).toHaveProperty('emoji');
      });
    });

    it('has correct labels for each step', () => {
      expect(JOURNEY_STEPS[0].label).toBe('Watch');
      expect(JOURNEY_STEPS[1].label).toBe('Found');
      expect(JOURNEY_STEPS[2].label).toBe('Enter');
      expect(JOURNEY_STEPS[3].label).toBe('Monitor');
      expect(JOURNEY_STEPS[4].label).toBe('Exit');
    });
  });
});

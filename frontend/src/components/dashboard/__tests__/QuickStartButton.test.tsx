/**
 * QuickStartButton Component Tests
 * Story 1A-8: Quick Start Option
 *
 * Tests cover:
 * - AC1: Button visible on dashboard when no strategy active
 * - AC2: Clicking loads pre-configured pump detection strategy
 * - AC3: Strategy uses sensible defaults
 * - AC4: User sees confirmation and can start session
 * - AC5: Non-destructive (doesn't overwrite user's strategies)
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import QuickStartButton from '../QuickStartButton';
import { QUICK_START_STRATEGY } from '@/constants/quickStartStrategy';

const theme = createTheme();

const renderWithTheme = (component: React.ReactElement) => {
  return render(<ThemeProvider theme={theme}>{component}</ThemeProvider>);
};

describe('QuickStartButton Component', () => {
  describe('AC1: Button Visibility', () => {
    it('renders Quick Start button with correct label', () => {
      renderWithTheme(<QuickStartButton onQuickStart={jest.fn()} />);

      const button = screen.getByRole('button', { name: /quick start/i });
      expect(button).toBeInTheDocument();
    });

    it('renders as a prominent primary button', () => {
      renderWithTheme(<QuickStartButton onQuickStart={jest.fn()} />);

      const button = screen.getByRole('button', { name: /quick start/i });
      expect(button).toHaveClass('MuiButton-contained');
    });

    it('includes rocket emoji for visual appeal', () => {
      const { container } = renderWithTheme(<QuickStartButton onQuickStart={jest.fn()} />);

      expect(container.textContent).toMatch(/🚀/);
    });

    it('can be hidden via visible prop', () => {
      renderWithTheme(<QuickStartButton onQuickStart={jest.fn()} visible={false} />);

      const button = screen.queryByRole('button', { name: /quick start/i });
      expect(button).not.toBeInTheDocument();
    });
  });

  describe('AC2 & AC3: Strategy Loading', () => {
    it('calls onQuickStart with strategy when clicked', () => {
      const onQuickStart = jest.fn();
      renderWithTheme(<QuickStartButton onQuickStart={onQuickStart} />);

      const button = screen.getByRole('button', { name: /quick start/i });
      fireEvent.click(button);

      expect(onQuickStart).toHaveBeenCalledTimes(1);
      expect(onQuickStart).toHaveBeenCalledWith(
        expect.objectContaining({
          strategy_name: QUICK_START_STRATEGY.strategy_name,
          is_template: true,
        })
      );
    });

    it('strategy has sensible defaults (7% pump, 3x volume)', () => {
      const onQuickStart = jest.fn();
      renderWithTheme(<QuickStartButton onQuickStart={onQuickStart} />);

      fireEvent.click(screen.getByRole('button', { name: /quick start/i }));

      const strategy = onQuickStart.mock.calls[0][0];
      expect(strategy.sections.S1.conditions).toEqual(
        expect.arrayContaining([
          expect.objectContaining({ indicator: 'pump_magnitude_pct', operator: '>', value: 7 }),
          expect.objectContaining({ indicator: 'volume_surge_ratio', operator: '>', value: 3 }),
        ])
      );
    });
  });

  describe('AC4: User Feedback', () => {
    it('shows loading state when loading prop is true', () => {
      renderWithTheme(<QuickStartButton onQuickStart={jest.fn()} loading={true} />);

      const button = screen.getByRole('button', { name: /loading/i });
      expect(button).toBeDisabled();
    });

    it('button is disabled when disabled prop is true', () => {
      renderWithTheme(<QuickStartButton onQuickStart={jest.fn()} disabled={true} />);

      const button = screen.getByRole('button', { name: /quick start/i });
      expect(button).toBeDisabled();
    });
  });

  describe('AC5: Non-Destructive Behavior', () => {
    it('strategy is marked as template (is_template: true)', () => {
      const onQuickStart = jest.fn();
      renderWithTheme(<QuickStartButton onQuickStart={onQuickStart} />);

      fireEvent.click(screen.getByRole('button', { name: /quick start/i }));

      const strategy = onQuickStart.mock.calls[0][0];
      expect(strategy.is_template).toBe(true);
    });

    it('strategy name indicates it is a demo/template', () => {
      const onQuickStart = jest.fn();
      renderWithTheme(<QuickStartButton onQuickStart={onQuickStart} />);

      fireEvent.click(screen.getByRole('button', { name: /quick start/i }));

      const strategy = onQuickStart.mock.calls[0][0];
      expect(strategy.strategy_name.toLowerCase()).toMatch(/quick start|demo|template/);
    });
  });

  describe('Accessibility', () => {
    it('button is focusable', () => {
      renderWithTheme(<QuickStartButton onQuickStart={jest.fn()} />);

      const button = screen.getByRole('button', { name: /quick start/i });
      button.focus();
      expect(document.activeElement).toBe(button);
    });

    it('button can be activated with keyboard', () => {
      const onQuickStart = jest.fn();
      renderWithTheme(<QuickStartButton onQuickStart={onQuickStart} />);

      const button = screen.getByRole('button', { name: /quick start/i });
      button.focus();
      fireEvent.keyDown(button, { key: 'Enter' });

      // MUI Button responds to Enter key
      expect(onQuickStart).toHaveBeenCalled();
    });
  });
});

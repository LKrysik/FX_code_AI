/**
 * DataFreshnessWrapper Component Tests
 * Story BUG-008-3: Graceful Degradation UI
 *
 * Tests cover:
 * - AC3: "Updated X seconds ago" display
 * - AC4: Stale data visual indicators (opacity, badge)
 */

import React from 'react';
import { render, screen, act } from '@testing-library/react';
import '@testing-library/jest-dom';
import { DataFreshnessWrapper, FreshnessIndicator } from '../DataFreshnessWrapper';

// Mock useDataFreshness hook
jest.mock('@/hooks/useDataFreshness', () => ({
  useDataFreshness: jest.fn(),
}));

import { useDataFreshness } from '@/hooks/useDataFreshness';

const mockUseDataFreshness = useDataFreshness as jest.Mock;

describe('DataFreshnessWrapper Component', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('AC3: Updated X seconds ago display', () => {
    it('displays "Just now" for fresh data', () => {
      mockUseDataFreshness.mockReturnValue({
        formattedAge: 'Just now',
        ageSeconds: 2,
        isStale: false,
        isVeryStale: false,
        opacity: 1.0,
        showStaleBadge: false,
        lastUpdateTimestamp: Date.now() - 2000,
      });

      render(
        <DataFreshnessWrapper lastUpdateTime={Date.now() - 2000} title="Test Panel">
          <div>Content</div>
        </DataFreshnessWrapper>
      );

      expect(screen.getByText('Just now')).toBeInTheDocument();
    });

    it('displays "Updated Xs ago" for recent data', () => {
      mockUseDataFreshness.mockReturnValue({
        formattedAge: 'Updated 30s ago',
        ageSeconds: 30,
        isStale: false,
        isVeryStale: false,
        opacity: 1.0,
        showStaleBadge: false,
        lastUpdateTimestamp: Date.now() - 30000,
      });

      render(
        <DataFreshnessWrapper lastUpdateTime={Date.now() - 30000} title="Test Panel">
          <div>Content</div>
        </DataFreshnessWrapper>
      );

      expect(screen.getByText('Updated 30s ago')).toBeInTheDocument();
    });

    it('displays "Updated Xm ago" for minute-old data', () => {
      mockUseDataFreshness.mockReturnValue({
        formattedAge: 'Updated 5m ago',
        ageSeconds: 300,
        isStale: true,
        isVeryStale: true,
        opacity: 0.7,
        showStaleBadge: true,
        lastUpdateTimestamp: Date.now() - 300000,
      });

      render(
        <DataFreshnessWrapper lastUpdateTime={Date.now() - 300000} title="Test Panel">
          <div>Content</div>
        </DataFreshnessWrapper>
      );

      expect(screen.getByText('Updated 5m ago')).toBeInTheDocument();
    });

    it('displays "No data" when lastUpdateTime is null', () => {
      mockUseDataFreshness.mockReturnValue({
        formattedAge: 'No data',
        ageSeconds: Infinity,
        isStale: true,
        isVeryStale: true,
        opacity: 0.5,
        showStaleBadge: true,
        lastUpdateTimestamp: null,
      });

      render(
        <DataFreshnessWrapper lastUpdateTime={null} title="Test Panel">
          <div>Content</div>
        </DataFreshnessWrapper>
      );

      expect(screen.getByText('No data')).toBeInTheDocument();
    });
  });

  describe('AC4: Stale data visual indicators', () => {
    it('applies reduced opacity for stale data (>60s)', () => {
      mockUseDataFreshness.mockReturnValue({
        formattedAge: 'Updated 90s ago',
        ageSeconds: 90,
        isStale: true,
        isVeryStale: false,
        opacity: 0.7,
        showStaleBadge: false,
        lastUpdateTimestamp: Date.now() - 90000,
      });

      const { container } = render(
        <DataFreshnessWrapper lastUpdateTime={Date.now() - 90000}>
          <div>Content</div>
        </DataFreshnessWrapper>
      );

      // The wrapper div should have opacity style applied
      const wrapper = container.firstChild as HTMLElement;
      expect(wrapper).toHaveStyle({ opacity: '0.7' });
    });

    it('does not apply reduced opacity for fresh data', () => {
      mockUseDataFreshness.mockReturnValue({
        formattedAge: 'Updated 10s ago',
        ageSeconds: 10,
        isStale: false,
        isVeryStale: false,
        opacity: 1.0,
        showStaleBadge: false,
        lastUpdateTimestamp: Date.now() - 10000,
      });

      const { container } = render(
        <DataFreshnessWrapper lastUpdateTime={Date.now() - 10000}>
          <div>Content</div>
        </DataFreshnessWrapper>
      );

      const wrapper = container.firstChild as HTMLElement;
      expect(wrapper).toHaveStyle({ opacity: '1' });
    });

    it('shows STALE badge for very stale data (>120s)', () => {
      mockUseDataFreshness.mockReturnValue({
        formattedAge: 'Updated 3m ago',
        ageSeconds: 180,
        isStale: true,
        isVeryStale: true,
        opacity: 0.7,
        showStaleBadge: true,
        lastUpdateTimestamp: Date.now() - 180000,
      });

      render(
        <DataFreshnessWrapper lastUpdateTime={Date.now() - 180000}>
          <div>Content</div>
        </DataFreshnessWrapper>
      );

      expect(screen.getByText('STALE')).toBeInTheDocument();
    });

    it('does not show STALE badge when showStaleBadge prop is false', () => {
      mockUseDataFreshness.mockReturnValue({
        formattedAge: 'Updated 3m ago',
        ageSeconds: 180,
        isStale: true,
        isVeryStale: true,
        opacity: 0.7,
        showStaleBadge: true,
        lastUpdateTimestamp: Date.now() - 180000,
      });

      render(
        <DataFreshnessWrapper lastUpdateTime={Date.now() - 180000} showStaleBadge={false}>
          <div>Content</div>
        </DataFreshnessWrapper>
      );

      expect(screen.queryByText('STALE')).not.toBeInTheDocument();
    });

    it('does not apply opacity when applyOpacityDegradation is false', () => {
      mockUseDataFreshness.mockReturnValue({
        formattedAge: 'Updated 90s ago',
        ageSeconds: 90,
        isStale: true,
        isVeryStale: false,
        opacity: 0.7,
        showStaleBadge: false,
        lastUpdateTimestamp: Date.now() - 90000,
      });

      const { container } = render(
        <DataFreshnessWrapper lastUpdateTime={Date.now() - 90000} applyOpacityDegradation={false}>
          <div>Content</div>
        </DataFreshnessWrapper>
      );

      const wrapper = container.firstChild as HTMLElement;
      expect(wrapper).toHaveStyle({ opacity: '1' });
    });
  });

  describe('Header display options', () => {
    it('shows title in header when provided', () => {
      mockUseDataFreshness.mockReturnValue({
        formattedAge: 'Updated 10s ago',
        ageSeconds: 10,
        isStale: false,
        isVeryStale: false,
        opacity: 1.0,
        showStaleBadge: false,
        lastUpdateTimestamp: Date.now() - 10000,
      });

      render(
        <DataFreshnessWrapper lastUpdateTime={Date.now() - 10000} title="Indicators Panel">
          <div>Content</div>
        </DataFreshnessWrapper>
      );

      expect(screen.getByText('Indicators Panel')).toBeInTheDocument();
    });

    it('hides header when showHeader is false', () => {
      mockUseDataFreshness.mockReturnValue({
        formattedAge: 'Updated 10s ago',
        ageSeconds: 10,
        isStale: false,
        isVeryStale: false,
        opacity: 1.0,
        showStaleBadge: false,
        lastUpdateTimestamp: Date.now() - 10000,
      });

      render(
        <DataFreshnessWrapper lastUpdateTime={Date.now() - 10000} showHeader={false} title="Hidden Title">
          <div>Content</div>
        </DataFreshnessWrapper>
      );

      expect(screen.queryByText('Hidden Title')).not.toBeInTheDocument();
      expect(screen.queryByText('Updated 10s ago')).not.toBeInTheDocument();
    });

    it('compact mode hides title but shows age', () => {
      mockUseDataFreshness.mockReturnValue({
        formattedAge: 'Updated 10s ago',
        ageSeconds: 10,
        isStale: false,
        isVeryStale: false,
        opacity: 1.0,
        showStaleBadge: false,
        lastUpdateTimestamp: Date.now() - 10000,
      });

      render(
        <DataFreshnessWrapper lastUpdateTime={Date.now() - 10000} compact title="Hidden Title">
          <div>Content</div>
        </DataFreshnessWrapper>
      );

      expect(screen.queryByText('Hidden Title')).not.toBeInTheDocument();
      expect(screen.getByText('Updated 10s ago')).toBeInTheDocument();
    });
  });

  describe('Children rendering', () => {
    it('renders children correctly', () => {
      mockUseDataFreshness.mockReturnValue({
        formattedAge: 'Just now',
        ageSeconds: 0,
        isStale: false,
        isVeryStale: false,
        opacity: 1.0,
        showStaleBadge: false,
        lastUpdateTimestamp: Date.now(),
      });

      render(
        <DataFreshnessWrapper lastUpdateTime={Date.now()}>
          <div data-testid="child-content">Test Content</div>
        </DataFreshnessWrapper>
      );

      expect(screen.getByTestId('child-content')).toBeInTheDocument();
      expect(screen.getByText('Test Content')).toBeInTheDocument();
    });
  });
});

describe('FreshnessIndicator Component', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('displays formatted age', () => {
    mockUseDataFreshness.mockReturnValue({
      formattedAge: 'Updated 15s ago',
      ageSeconds: 15,
      isStale: false,
      isVeryStale: false,
      opacity: 1.0,
      showStaleBadge: false,
      lastUpdateTimestamp: Date.now() - 15000,
    });

    render(<FreshnessIndicator lastUpdateTime={Date.now() - 15000} />);
    expect(screen.getByText('Updated 15s ago')).toBeInTheDocument();
  });

  it('shows STALE badge when very stale', () => {
    mockUseDataFreshness.mockReturnValue({
      formattedAge: 'Updated 3m ago',
      ageSeconds: 180,
      isStale: true,
      isVeryStale: true,
      opacity: 0.7,
      showStaleBadge: true,
      lastUpdateTimestamp: Date.now() - 180000,
    });

    render(<FreshnessIndicator lastUpdateTime={Date.now() - 180000} />);
    expect(screen.getByText('STALE')).toBeInTheDocument();
  });

  it('hides badge when showBadge is false', () => {
    mockUseDataFreshness.mockReturnValue({
      formattedAge: 'Updated 3m ago',
      ageSeconds: 180,
      isStale: true,
      isVeryStale: true,
      opacity: 0.7,
      showStaleBadge: true,
      lastUpdateTimestamp: Date.now() - 180000,
    });

    render(<FreshnessIndicator lastUpdateTime={Date.now() - 180000} showBadge={false} />);
    expect(screen.queryByText('STALE')).not.toBeInTheDocument();
  });
});

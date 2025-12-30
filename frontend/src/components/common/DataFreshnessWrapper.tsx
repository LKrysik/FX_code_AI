'use client';

/**
 * DataFreshnessWrapper Component
 * ==============================
 * BUG-008-3: Wrapper component that displays data freshness indicators.
 *
 * STATUS: OPTIONAL UTILITY - Not currently used in production.
 * Existing components use useDataFreshness hook directly for more control.
 * This wrapper is available for future panels that need quick integration.
 *
 * Features:
 * - Shows "Updated X seconds ago" in header (AC3)
 * - Visual degradation (opacity 0.7) for stale data >60s (AC4)
 * - STALE badge for very old data >120s (AC4)
 *
 * When to use this vs useDataFreshness hook:
 * - Use DataFreshnessWrapper: When you want automatic visual treatment (opacity, badge, header)
 *   for an entire section with minimal code changes
 * - Use useDataFreshness hook: When you need fine-grained control over how freshness
 *   is displayed (custom styling, partial application, integration with existing UI)
 *
 * Current usage:
 * - IndicatorValuesPanel: Uses useDataFreshness hook directly (custom header integration)
 * - StateOverviewTable: Uses useDataFreshness hook directly (custom header integration)
 * - Future panels: Can use this wrapper for quick integration
 *
 * Usage:
 * ```tsx
 * <DataFreshnessWrapper lastUpdateTime={lastMessageTime} title="Indicators">
 *   <IndicatorPanel data={data} />
 * </DataFreshnessWrapper>
 * ```
 */

import React from 'react';
import { Box, Chip, Typography, SxProps, Theme } from '@mui/material';
import { Warning as WarningIcon } from '@mui/icons-material';
import { useDataFreshness } from '@/hooks/useDataFreshness';

export interface DataFreshnessWrapperProps {
  /** Content to wrap */
  children: React.ReactNode;
  /** Timestamp of last data update */
  lastUpdateTime: Date | number | string | null | undefined;
  /** Title to show in the freshness header */
  title?: string;
  /** Whether to show the title and freshness info */
  showHeader?: boolean;
  /** Additional sx props for the container */
  sx?: SxProps<Theme>;
  /** Whether to show STALE badge when very stale */
  showStaleBadge?: boolean;
  /** Whether to apply opacity degradation */
  applyOpacityDegradation?: boolean;
  /** Compact mode - show only the age, not the title */
  compact?: boolean;
}

export function DataFreshnessWrapper({
  children,
  lastUpdateTime,
  title,
  showHeader = true,
  sx,
  showStaleBadge = true,
  applyOpacityDegradation = true,
  compact = false,
}: DataFreshnessWrapperProps) {
  const {
    formattedAge,
    isStale,
    isVeryStale,
    opacity,
    showStaleBadge: shouldShowBadge,
  } = useDataFreshness(lastUpdateTime);

  const effectiveOpacity = applyOpacityDegradation ? opacity : 1.0;
  const displayBadge = showStaleBadge && shouldShowBadge;

  return (
    <Box
      sx={{
        position: 'relative',
        opacity: effectiveOpacity,
        transition: 'opacity 0.3s ease',
        ...sx,
      }}
    >
      {/* Freshness header */}
      {showHeader && (
        <Box
          sx={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            mb: compact ? 0.5 : 1,
            flexWrap: 'wrap',
            gap: 0.5,
          }}
        >
          {/* Title (optional) */}
          {!compact && title && (
            <Typography
              variant="subtitle2"
              color="text.secondary"
              sx={{ fontWeight: 500 }}
            >
              {title}
            </Typography>
          )}

          {/* Freshness indicator */}
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <Typography
              variant="caption"
              color={isStale ? 'warning.main' : 'text.secondary'}
              sx={{
                fontWeight: isStale ? 500 : 400,
              }}
            >
              {formattedAge}
            </Typography>

            {/* STALE badge for very old data */}
            {displayBadge && (
              <Chip
                icon={<WarningIcon sx={{ fontSize: 14 }} />}
                label="STALE"
                size="small"
                color="warning"
                sx={{
                  height: 20,
                  fontSize: '0.65rem',
                  fontWeight: 'bold',
                  '& .MuiChip-icon': { fontSize: 12 },
                }}
              />
            )}
          </Box>
        </Box>
      )}

      {/* Content */}
      {children}

      {/* Floating STALE badge (for when showHeader is false) */}
      {!showHeader && displayBadge && (
        <Chip
          icon={<WarningIcon sx={{ fontSize: 14 }} />}
          label="STALE"
          size="small"
          color="warning"
          sx={{
            position: 'absolute',
            top: 4,
            right: 4,
            height: 20,
            fontSize: '0.65rem',
            fontWeight: 'bold',
            zIndex: 1,
            '& .MuiChip-icon': { fontSize: 12 },
          }}
        />
      )}
    </Box>
  );
}

/**
 * Inline freshness indicator for compact display
 */
export function FreshnessIndicator({
  lastUpdateTime,
  showBadge = true,
}: {
  lastUpdateTime: Date | number | string | null | undefined;
  showBadge?: boolean;
}) {
  const { formattedAge, isStale, isVeryStale } = useDataFreshness(lastUpdateTime);

  return (
    <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
      <Typography
        variant="caption"
        color={isStale ? 'warning.main' : 'text.secondary'}
        sx={{ fontWeight: isStale ? 500 : 400 }}
      >
        {formattedAge}
      </Typography>
      {showBadge && isVeryStale && (
        <Chip
          label="STALE"
          size="small"
          color="warning"
          sx={{
            height: 16,
            fontSize: '0.6rem',
            fontWeight: 'bold',
          }}
        />
      )}
    </Box>
  );
}

export default DataFreshnessWrapper;

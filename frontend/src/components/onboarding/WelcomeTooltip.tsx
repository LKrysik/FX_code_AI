'use client';

/**
 * WelcomeTooltip Component
 * ========================
 * Story 1A-7: First-Visit Onboarding Tooltip
 *
 * A non-blocking welcome tooltip that appears on first dashboard visit.
 * Explains key dashboard areas without interrupting user interaction.
 *
 * AC2: Explains "This is your dashboard where signals appear"
 * AC3: Points to key areas (signals, status, indicators)
 * AC5: Non-blocking (floating, no backdrop)
 */

import React from 'react';
import {
  Paper,
  Box,
  Typography,
  Button,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  Fade,
  useTheme,
} from '@mui/material';
import {
  TrendingUp as SignalsIcon,
  Visibility as StateIcon,
  ShowChart as IndicatorsIcon,
  Celebration as WelcomeIcon,
} from '@mui/icons-material';

// ============================================================================
// TYPES
// ============================================================================

export interface WelcomeTooltipProps {
  /** Callback when user dismisses the tooltip */
  onDismiss: () => void;
  /** Whether the tooltip is visible */
  open: boolean;
  /** Optional anchor element for positioning (defaults to fixed position) */
  anchorEl?: HTMLElement | null;
}

// ============================================================================
// FEATURE LIST DATA
// ============================================================================

interface FeatureItem {
  icon: React.ReactNode;
  text: string;
}

const FEATURES: FeatureItem[] = [
  {
    icon: <SignalsIcon color="primary" />,
    text: 'Signals when the system detects opportunities',
  },
  {
    icon: <StateIcon color="primary" />,
    text: 'Current state of your trading strategy',
  },
  {
    icon: <IndicatorsIcon color="primary" />,
    text: 'Real-time indicator values and metrics',
  },
];

// ============================================================================
// COMPONENT
// ============================================================================

/**
 * WelcomeTooltip - First-visit onboarding tooltip
 *
 * @example
 * ```tsx
 * const { showOnboarding, dismissOnboarding } = useOnboarding();
 *
 * <WelcomeTooltip
 *   open={showOnboarding}
 *   onDismiss={dismissOnboarding}
 * />
 * ```
 */
export function WelcomeTooltip({
  onDismiss,
  open,
  anchorEl,
}: WelcomeTooltipProps): React.ReactElement | null {
  const theme = useTheme();

  if (!open) {
    return null;
  }

  return (
    <Fade in={open}>
      <Paper
        elevation={8}
        sx={{
          position: 'fixed',
          top: { xs: 80, md: 100 },
          right: { xs: 16, md: 24 },
          maxWidth: { xs: 300, sm: 340 },
          width: '100%',
          p: 3,
          borderRadius: 2,
          zIndex: theme.zIndex.tooltip,
          border: `1px solid ${theme.palette.divider}`,
          background: theme.palette.background.paper,
        }}
      >
        {/* Header */}
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
          <WelcomeIcon color="primary" sx={{ fontSize: 28 }} />
          <Typography variant="h6" component="h2" fontWeight={600}>
            Welcome to FX Agent AI!
          </Typography>
        </Box>

        {/* Description */}
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          This is your trading dashboard where you&apos;ll see:
        </Typography>

        {/* Feature List */}
        <List dense disablePadding sx={{ mb: 2 }}>
          {FEATURES.map((feature, index) => (
            <ListItem key={index} disableGutters sx={{ py: 0.5 }}>
              <ListItemIcon sx={{ minWidth: 36 }}>{feature.icon}</ListItemIcon>
              <ListItemText
                primary={feature.text}
                primaryTypographyProps={{
                  variant: 'body2',
                  color: 'text.primary',
                }}
              />
            </ListItem>
          ))}
        </List>

        {/* Quick Start Hint */}
        <Typography
          variant="body2"
          color="text.secondary"
          sx={{ mb: 2, fontStyle: 'italic' }}
        >
          Ready to start? Click &quot;Quick Start&quot; to load a template strategy!
        </Typography>

        {/* Dismiss Button */}
        <Button
          variant="contained"
          color="primary"
          size="medium"
          fullWidth
          onClick={onDismiss}
          sx={{
            textTransform: 'none',
            fontWeight: 600,
          }}
        >
          Got it!
        </Button>
      </Paper>
    </Fade>
  );
}

export default WelcomeTooltip;

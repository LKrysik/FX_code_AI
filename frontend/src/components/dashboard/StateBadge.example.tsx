'use client';

/**
 * STATEBADGE USAGE EXAMPLES
 *
 * This file demonstrates various use cases for the StateBadge component.
 */

import React from 'react';
import { Box, Paper, Typography, Stack, Divider } from '@mui/material';
import StateBadge from './StateBadge';

const StateBadgeExamples: React.FC = () => {
  // Example timestamp (5 minutes ago)
  const fiveMinutesAgo = new Date(Date.now() - 5 * 60 * 1000).toISOString();

  // Example timestamp (2 hours ago)
  const twoHoursAgo = new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString();

  return (
    <Box sx={{ p: 3, maxWidth: 1200, margin: '0 auto' }}>
      <Typography variant="h4" gutterBottom>
        StateBadge Component Examples
      </Typography>

      {/* Basic Usage - All States */}
      <Paper sx={{ p: 3, mb: 3 }}>
        <Typography variant="h6" gutterBottom>
          Basic Usage - All States
        </Typography>
        <Stack direction="row" spacing={2} flexWrap="wrap" gap={2}>
          <StateBadge state="INACTIVE" />
          <StateBadge state="MONITORING" />
          <StateBadge state="SIGNAL_DETECTED" />
          <StateBadge state="POSITION_ACTIVE" />
          <StateBadge state="EXITED" />
          <StateBadge state="ERROR" />
        </Stack>
      </Paper>

      {/* With Duration */}
      <Paper sx={{ p: 3, mb: 3 }}>
        <Typography variant="h6" gutterBottom>
          With Duration (Live Updates)
        </Typography>
        <Stack direction="row" spacing={2} flexWrap="wrap" gap={2}>
          <StateBadge
            state="MONITORING"
            since={fiveMinutesAgo}
            showDuration
          />
          <StateBadge
            state="SIGNAL_DETECTED"
            since={new Date(Date.now() - 30 * 1000).toISOString()}
            showDuration
          />
          <StateBadge
            state="POSITION_ACTIVE"
            since={twoHoursAgo}
            showDuration
          />
        </Stack>
      </Paper>

      {/* Size Variations */}
      <Paper sx={{ p: 3, mb: 3 }}>
        <Typography variant="h6" gutterBottom>
          Size Variations
        </Typography>

        <Box sx={{ mb: 2 }}>
          <Typography variant="body2" color="text.secondary" gutterBottom>
            Small
          </Typography>
          <StateBadge state="MONITORING" size="small" />
        </Box>

        <Box sx={{ mb: 2 }}>
          <Typography variant="body2" color="text.secondary" gutterBottom>
            Medium (Default)
          </Typography>
          <StateBadge state="SIGNAL_DETECTED" size="medium" />
        </Box>

        <Box sx={{ mb: 2 }}>
          <Typography variant="body2" color="text.secondary" gutterBottom>
            Large
          </Typography>
          <StateBadge state="POSITION_ACTIVE" size="large" />
        </Box>
      </Paper>

      {/* Pulsing Animation */}
      <Paper sx={{ p: 3, mb: 3 }}>
        <Typography variant="h6" gutterBottom>
          Pulsing Animation (SIGNAL_DETECTED only)
        </Typography>
        <Typography variant="body2" color="text.secondary" gutterBottom>
          The SIGNAL_DETECTED state automatically pulses to draw attention
        </Typography>
        <StateBadge
          state="SIGNAL_DETECTED"
          since={fiveMinutesAgo}
          showDuration
          size="large"
        />
      </Paper>

      {/* Real-world Use Cases */}
      <Paper sx={{ p: 3, mb: 3 }}>
        <Typography variant="h6" gutterBottom>
          Real-world Use Cases
        </Typography>

        <Divider sx={{ my: 2 }} />

        {/* Dashboard Header */}
        <Box sx={{ mb: 3 }}>
          <Typography variant="subtitle2" gutterBottom>
            Dashboard Header
          </Typography>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
            <Typography variant="body1">System Status:</Typography>
            <StateBadge
              state="MONITORING"
              since={twoHoursAgo}
              showDuration
            />
          </Box>
        </Box>

        <Divider sx={{ my: 2 }} />

        {/* Strategy Card */}
        <Box sx={{ mb: 3 }}>
          <Typography variant="subtitle2" gutterBottom>
            Strategy Card
          </Typography>
          <Box>
            <Typography variant="body2" color="text.secondary">
              BTC/USDT - Pump & Dump Detection
            </Typography>
            <StateBadge
              state="SIGNAL_DETECTED"
              since={new Date(Date.now() - 45 * 1000).toISOString()}
              showDuration
              size="small"
            />
          </Box>
        </Box>

        <Divider sx={{ my: 2 }} />

        {/* Position Monitor */}
        <Box sx={{ mb: 3 }}>
          <Typography variant="subtitle2" gutterBottom>
            Position Monitor Table Row
          </Typography>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
            <Typography variant="body2">ETH/USDT</Typography>
            <StateBadge
              state="POSITION_ACTIVE"
              since={new Date(Date.now() - 15 * 60 * 1000).toISOString()}
              showDuration
              size="small"
            />
            <Typography variant="body2" color="success.main">
              +2.3%
            </Typography>
          </Box>
        </Box>

        <Divider sx={{ my: 2 }} />

        {/* Error State */}
        <Box>
          <Typography variant="subtitle2" gutterBottom>
            Error Alert
          </Typography>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
            <StateBadge
              state="ERROR"
              since={new Date(Date.now() - 2 * 60 * 1000).toISOString()}
              showDuration
            />
            <Typography variant="body2" color="error">
              Connection to exchange lost
            </Typography>
          </Box>
        </Box>
      </Paper>

      {/* Code Examples */}
      <Paper sx={{ p: 3, bgcolor: 'grey.100' }}>
        <Typography variant="h6" gutterBottom>
          Code Examples
        </Typography>

        <Box component="pre" sx={{ fontSize: '0.85rem', overflow: 'auto' }}>
{`// Basic usage
<StateBadge state="MONITORING" />

// With duration
<StateBadge
  state="POSITION_ACTIVE"
  since={position.entryTime}
  showDuration
/>

// Custom size
<StateBadge
  state="SIGNAL_DETECTED"
  size="large"
/>

// Full featured
<StateBadge
  state="POSITION_ACTIVE"
  since={new Date().toISOString()}
  showDuration
  size="medium"
/>`}
        </Box>
      </Paper>
    </Box>
  );
};

export default StateBadgeExamples;

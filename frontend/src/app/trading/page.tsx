'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Box, CircularProgress, Typography } from '@mui/material';

/**
 * Live Trading Redirect Page
 * ===========================
 *
 * Redirects /trading → /dashboard?mode=live
 * This provides backward compatibility with legacy URLs
 */
export default function TradingRedirectPage() {
  const router = useRouter();

  useEffect(() => {
    // Redirect to unified dashboard with live mode
    router.replace('/dashboard?mode=live');
  }, [router]);

  return (
    <Box
      sx={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        minHeight: '100vh',
        gap: 2,
      }}
    >
      <CircularProgress />
      <Typography variant="body1" color="text.secondary">
        Redirecting to Live Trading...
      </Typography>
    </Box>
  );
}

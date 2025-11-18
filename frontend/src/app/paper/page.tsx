'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Box, CircularProgress, Typography } from '@mui/material';

/**
 * Paper Trading Redirect Page
 * ============================
 *
 * Redirects /paper → /dashboard?mode=paper
 * This provides a clean URL for paper trading access
 */
export default function PaperTradingRedirectPage() {
  const router = useRouter();

  useEffect(() => {
    // Redirect to unified dashboard with paper mode
    router.replace('/dashboard?mode=paper');
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
        Redirecting to Paper Trading...
      </Typography>
    </Box>
  );
}

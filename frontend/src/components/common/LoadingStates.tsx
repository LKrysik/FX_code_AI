'use client';

import React from 'react';
import { 
  Box, 
  CircularProgress, 
  Typography, 
  Skeleton,
  Card,
  CardContent,
  Grid
} from '@mui/material';

export const CenteredLoader: React.FC<{ message?: string }> = ({ message }) => (
  <Box sx={{ 
    display: 'flex', 
    flexDirection: 'column',
    alignItems: 'center', 
    justifyContent: 'center',
    minHeight: 200,
    gap: 2
  }}>
    <CircularProgress />
    {message && (
      <Typography variant="body2" color="text.secondary">
        {message}
      </Typography>
    )}
  </Box>
);

export const TableSkeleton: React.FC<{ rows?: number; cols?: number }> = ({ 
  rows = 5, 
  cols = 4 
}) => (
  <Box>
    {Array.from({ length: rows }).map((_, i) => (
      <Box key={i} sx={{ display: 'flex', gap: 2, mb: 1 }}>
        {Array.from({ length: cols }).map((_, j) => (
          <Skeleton key={j} variant="text" width={`${100/cols}%`} height={40} />
        ))}
      </Box>
    ))}
  </Box>
);

export const CardSkeleton: React.FC = () => (
  <Card>
    <CardContent>
      <Skeleton variant="text" width="60%" height={24} sx={{ mb: 1 }} />
      <Skeleton variant="text" width="40%" height={32} sx={{ mb: 2 }} />
      <Skeleton variant="rectangular" width="100%" height={60} />
    </CardContent>
  </Card>
);

export const DashboardSkeleton: React.FC = () => (
  <Grid container spacing={3}>
    {Array.from({ length: 4 }).map((_, i) => (
      <Grid item xs={12} md={3} key={i}>
        <CardSkeleton />
      </Grid>
    ))}
  </Grid>
);
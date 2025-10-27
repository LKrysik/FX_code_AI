import React from 'react';
import {
  Card,
  CardContent,
  CardActions,
  Typography,
  Chip,
  Box,
  Button,
  IconButton,
  Tooltip,
} from '@mui/material';
import {
  TrendingUp as TrendingUpIcon,
  Star as StarIcon,
  ContentCopy as ForkIcon,
  Visibility as ViewIcon,
  Info as InfoIcon,
} from '@mui/icons-material';

export interface TemplateData {
  id: string;
  name: string;
  description: string | null;
  category: string;
  author: string;
  is_featured: boolean;
  usage_count: number;
  success_rate: number | null;
  avg_return: number | null;
  tags: string[];
  created_at: string;
  updated_at: string;
}

interface TemplateCardProps {
  template: TemplateData;
  onUse: (templateId: string) => void;
  onView: (templateId: string) => void;
  onFork?: (templateId: string) => void;
}

/**
 * TemplateCard Component - Phase 2 Sprint 2
 *
 * Displays a single strategy template with:
 * - Template name and description
 * - Category badge
 * - Featured status
 * - Usage statistics
 * - Backtest performance (if available)
 * - Action buttons (Use, View, Fork)
 */
export const TemplateCard: React.FC<TemplateCardProps> = ({
  template,
  onUse,
  onView,
  onFork,
}) => {
  const getCategoryColor = (category: string): 'primary' | 'secondary' | 'success' | 'warning' | 'error' | 'info' => {
    const colorMap: Record<string, 'primary' | 'secondary' | 'success' | 'warning' | 'error' | 'info'> = {
      trend_following: 'primary',
      mean_reversion: 'secondary',
      breakout: 'success',
      momentum: 'warning',
      volatility: 'error',
      scalping: 'info',
      swing: 'primary',
      position: 'secondary',
      other: 'info',
    };
    return colorMap[category] || 'info';
  };

  const getCategoryLabel = (category: string): string => {
    const labelMap: Record<string, string> = {
      trend_following: 'Trend Following',
      mean_reversion: 'Mean Reversion',
      breakout: 'Breakout',
      momentum: 'Momentum',
      volatility: 'Volatility',
      scalping: 'Scalping',
      swing: 'Swing',
      position: 'Position',
      other: 'Other',
    };
    return labelMap[category] || category;
  };

  const formatPercentage = (value: number | null): string => {
    if (value === null) return 'N/A';
    return `${value >= 0 ? '+' : ''}${value.toFixed(2)}%`;
  };

  return (
    <Card
      sx={{
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        position: 'relative',
        border: template.is_featured ? '2px solid' : '1px solid',
        borderColor: template.is_featured ? 'warning.main' : 'divider',
        transition: 'all 0.2s',
        '&:hover': {
          boxShadow: 6,
          transform: 'translateY(-4px)',
        },
      }}
    >
      {/* Featured Badge */}
      {template.is_featured && (
        <Box
          sx={{
            position: 'absolute',
            top: 8,
            right: 8,
            zIndex: 1,
          }}
        >
          <Tooltip title="Featured Template">
            <StarIcon sx={{ color: 'warning.main', fontSize: 28 }} />
          </Tooltip>
        </Box>
      )}

      <CardContent sx={{ flexGrow: 1, pb: 1 }}>
        {/* Template Name */}
        <Typography variant="h6" component="h3" gutterBottom sx={{ pr: template.is_featured ? 4 : 0 }}>
          {template.name}
        </Typography>

        {/* Category Badge */}
        <Box sx={{ mb: 1 }}>
          <Chip
            label={getCategoryLabel(template.category)}
            color={getCategoryColor(template.category)}
            size="small"
          />
        </Box>

        {/* Description */}
        <Typography
          variant="body2"
          color="text.secondary"
          sx={{
            mb: 2,
            minHeight: '40px',
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            display: '-webkit-box',
            WebkitLineClamp: 2,
            WebkitBoxOrient: 'vertical',
          }}
        >
          {template.description || 'No description available'}
        </Typography>

        {/* Stats Section */}
        <Box
          sx={{
            display: 'flex',
            gap: 2,
            mb: 2,
            p: 1,
            bgcolor: 'background.default',
            borderRadius: 1,
          }}
        >
          {/* Usage Count */}
          <Box sx={{ flex: 1 }}>
            <Typography variant="caption" color="text.secondary" display="block">
              Uses
            </Typography>
            <Typography variant="body2" fontWeight="bold">
              {template.usage_count.toLocaleString()}
            </Typography>
          </Box>

          {/* Success Rate */}
          <Box sx={{ flex: 1 }}>
            <Typography variant="caption" color="text.secondary" display="block">
              Success
            </Typography>
            <Typography
              variant="body2"
              fontWeight="bold"
              color={template.success_rate && template.success_rate > 50 ? 'success.main' : 'text.primary'}
            >
              {template.success_rate !== null ? `${template.success_rate.toFixed(0)}%` : 'N/A'}
            </Typography>
          </Box>

          {/* Avg Return */}
          <Box sx={{ flex: 1 }}>
            <Typography variant="caption" color="text.secondary" display="block">
              Avg Return
            </Typography>
            <Typography
              variant="body2"
              fontWeight="bold"
              color={template.avg_return && template.avg_return > 0 ? 'success.main' : template.avg_return && template.avg_return < 0 ? 'error.main' : 'text.primary'}
            >
              {formatPercentage(template.avg_return)}
            </Typography>
          </Box>
        </Box>

        {/* Tags */}
        {template.tags && template.tags.length > 0 && (
          <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
            {template.tags.slice(0, 3).map((tag) => (
              <Chip key={tag} label={tag} size="small" variant="outlined" />
            ))}
            {template.tags.length > 3 && (
              <Chip label={`+${template.tags.length - 3}`} size="small" variant="outlined" />
            )}
          </Box>
        )}

        {/* Author */}
        <Typography variant="caption" color="text.secondary" display="block" sx={{ mt: 1 }}>
          by {template.author}
        </Typography>
      </CardContent>

      {/* Actions */}
      <CardActions sx={{ p: 2, pt: 0, justifyContent: 'space-between' }}>
        <Box sx={{ display: 'flex', gap: 1 }}>
          {/* Use Template Button */}
          <Button
            variant="contained"
            color="primary"
            size="small"
            startIcon={<TrendingUpIcon />}
            onClick={() => onUse(template.id)}
          >
            Use
          </Button>

          {/* View Details Button */}
          <Button
            variant="outlined"
            size="small"
            startIcon={<ViewIcon />}
            onClick={() => onView(template.id)}
          >
            View
          </Button>
        </Box>

        {/* Fork Button */}
        {onFork && (
          <Tooltip title="Fork Template">
            <IconButton size="small" onClick={() => onFork(template.id)} color="primary">
              <ForkIcon fontSize="small" />
            </IconButton>
          </Tooltip>
        )}
      </CardActions>
    </Card>
  );
};

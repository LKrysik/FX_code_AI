import React, { useState, useEffect } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  TextField,
  Box,
  Grid,
  Tabs,
  Tab,
  Chip,
  Typography,
  CircularProgress,
  Alert,
  InputAdornment,
} from '@mui/material';
import { Logger } from '@/services/frontendLogService';
import {
  Search as SearchIcon,
  Close as CloseIcon,
  Star as StarIcon,
  TrendingUp as TrendingUpIcon,
} from '@mui/icons-material';
import { TemplateCard, TemplateData } from './TemplateCard';

interface TemplateDialogProps {
  open: boolean;
  onClose: () => void;
  onSelectTemplate: (template: TemplateData) => void;
}

type TabValue = 'all' | 'featured' | 'popular' | 'category';

const CATEGORIES = [
  { value: 'trend_following', label: 'Trend Following' },
  { value: 'mean_reversion', label: 'Mean Reversion' },
  { value: 'breakout', label: 'Breakout' },
  { value: 'momentum', label: 'Momentum' },
  { value: 'volatility', label: 'Volatility' },
  { value: 'scalping', label: 'Scalping' },
  { value: 'swing', label: 'Swing' },
  { value: 'position', label: 'Position' },
  { value: 'other', label: 'Other' },
];

/**
 * TemplateDialog Component - Phase 2 Sprint 2
 *
 * Modal dialog for browsing and selecting strategy templates.
 *
 * Features:
 * - Tabs: All, Featured, Popular, By Category
 * - Search functionality
 * - Category filtering
 * - Template preview
 * - Usage statistics
 */
export const TemplateDialog: React.FC<TemplateDialogProps> = ({
  open,
  onClose,
  onSelectTemplate,
}) => {
  const [activeTab, setActiveTab] = useState<TabValue>('featured');
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);
  const [templates, setTemplates] = useState<TemplateData[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Fetch templates based on active tab and filters
  useEffect(() => {
    if (open) {
      fetchTemplates();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, activeTab, selectedCategory]);

  const fetchTemplates = async () => {
    setLoading(true);
    setError(null);

    try {
      let url = '/api/templates';

      if (activeTab === 'featured') {
        url += '/featured';
      } else if (activeTab === 'popular') {
        url += '/popular';
      } else if (activeTab === 'category' && selectedCategory) {
        url += `/category/${selectedCategory}`;
      }

      const response = await fetch(url);

      if (!response.ok) {
        throw new Error('Failed to fetch templates');
      }

      const data = await response.json();
      setTemplates(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
      setTemplates([]);
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = async () => {
    if (!searchQuery.trim()) {
      fetchTemplates();
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const params = new URLSearchParams({ q: searchQuery });
      if (selectedCategory) {
        params.append('category', selectedCategory);
      }

      const response = await fetch(`/api/templates/search?${params}`);

      if (!response.ok) {
        throw new Error('Search failed');
      }

      const data = await response.json();
      setTemplates(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Search error');
      setTemplates([]);
    } finally {
      setLoading(false);
    }
  };

  const handleUseTemplate = async (templateId: string) => {
    try {
      // Fetch full template details
      const response = await fetch(`/api/templates/${templateId}`);

      if (!response.ok) {
        throw new Error('Failed to load template');
      }

      const template = await response.json();

      // Track usage
      await fetch(`/api/templates/${templateId}/use`, { method: 'POST' });

      // Pass template to parent
      onSelectTemplate(template);
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to use template');
    }
  };

  const handleViewTemplate = async (templateId: string) => {
    // Track view action
    try {
      await fetch(`/api/templates/${templateId}/view`, { method: 'POST' });
    } catch (err) {
      Logger.error('TemplateDialog.viewTemplate', 'Failed to track view', { error: err });
    }

    // TODO: Open template details dialog
    Logger.debug('TemplateDialog.viewTemplate', 'View template', { templateId });
  };

  const handleForkTemplate = async (templateId: string) => {
    // TODO: Implement fork functionality
    Logger.debug('TemplateDialog.forkTemplate', 'Fork template', { templateId });
  };

  const handleTabChange = (_event: React.SyntheticEvent, newValue: TabValue) => {
    setActiveTab(newValue);
    setSearchQuery('');
  };

  const handleCategorySelect = (category: string) => {
    setSelectedCategory(selectedCategory === category ? null : category);
    setActiveTab('category');
  };

  const filteredTemplates = templates.filter((template) => {
    if (searchQuery && activeTab !== 'all') return true;
    if (!selectedCategory) return true;
    return template.category === selectedCategory;
  });

  return (
    <Dialog
      open={open}
      onClose={onClose}
      maxWidth="lg"
      fullWidth
      PaperProps={{
        sx: { height: '90vh' },
      }}
    >
      <DialogTitle>
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <Typography variant="h5">Strategy Templates</Typography>
          <Button onClick={onClose} color="inherit" startIcon={<CloseIcon />}>
            Close
          </Button>
        </Box>
      </DialogTitle>

      <DialogContent dividers>
        {/* Search Bar */}
        <Box sx={{ mb: 3 }}>
          <TextField
            fullWidth
            placeholder="Search templates by name, description, or tags..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            onKeyPress={(e) => {
              if (e.key === 'Enter') {
                handleSearch();
              }
            }}
            InputProps={{
              startAdornment: (
                <InputAdornment position="start">
                  <SearchIcon />
                </InputAdornment>
              ),
              endAdornment: searchQuery && (
                <InputAdornment position="end">
                  <Button size="small" onClick={handleSearch}>
                    Search
                  </Button>
                </InputAdornment>
              ),
            }}
          />
        </Box>

        {/* Tabs */}
        <Box sx={{ borderBottom: 1, borderColor: 'divider', mb: 2 }}>
          <Tabs value={activeTab} onChange={handleTabChange} variant="fullWidth">
            <Tab
              icon={<StarIcon />}
              iconPosition="start"
              label="Featured"
              value="featured"
            />
            <Tab
              icon={<TrendingUpIcon />}
              iconPosition="start"
              label="Popular"
              value="popular"
            />
            <Tab label="All Templates" value="all" />
            <Tab label="By Category" value="category" />
          </Tabs>
        </Box>

        {/* Category Filters (shown when "By Category" tab is active) */}
        {activeTab === 'category' && (
          <Box sx={{ mb: 3, display: 'flex', flexWrap: 'wrap', gap: 1 }}>
            {CATEGORIES.map((category) => (
              <Chip
                key={category.value}
                label={category.label}
                onClick={() => handleCategorySelect(category.value)}
                color={selectedCategory === category.value ? 'primary' : 'default'}
                variant={selectedCategory === category.value ? 'filled' : 'outlined'}
                sx={{ cursor: 'pointer' }}
              />
            ))}
          </Box>
        )}

        {/* Error Alert */}
        {error && (
          <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
            {error}
          </Alert>
        )}

        {/* Loading Spinner */}
        {loading && (
          <Box sx={{ display: 'flex', justifyContent: 'center', my: 4 }}>
            <CircularProgress />
          </Box>
        )}

        {/* Templates Grid */}
        {!loading && filteredTemplates.length > 0 && (
          <Grid container spacing={2}>
            {filteredTemplates.map((template) => (
              <Grid item xs={12} sm={6} md={4} key={template.id}>
                <TemplateCard
                  template={template}
                  onUse={handleUseTemplate}
                  onView={handleViewTemplate}
                  onFork={handleForkTemplate}
                />
              </Grid>
            ))}
          </Grid>
        )}

        {/* No Results */}
        {!loading && filteredTemplates.length === 0 && (
          <Box sx={{ textAlign: 'center', my: 4 }}>
            <Typography variant="h6" color="text.secondary" gutterBottom>
              No templates found
            </Typography>
            <Typography variant="body2" color="text.secondary">
              {searchQuery
                ? 'Try adjusting your search query or filters'
                : 'No templates available in this category'}
            </Typography>
          </Box>
        )}

        {/* Info Footer */}
        <Box sx={{ mt: 4, p: 2, bgcolor: 'background.default', borderRadius: 1 }}>
          <Typography variant="body2" color="text.secondary">
            <strong>Tip:</strong> Templates are pre-configured strategies that you can use as-is or customize.
            Click "Use" to load a template, "View" to see details, or "Fork" to create your own variation.
          </Typography>
        </Box>
      </DialogContent>

      <DialogActions sx={{ p: 2 }}>
        <Typography variant="caption" color="text.secondary" sx={{ flexGrow: 1, ml: 1 }}>
          {filteredTemplates.length} template{filteredTemplates.length !== 1 ? 's' : ''} available
        </Typography>
        <Button onClick={onClose} variant="outlined">
          Cancel
        </Button>
      </DialogActions>
    </Dialog>
  );
};

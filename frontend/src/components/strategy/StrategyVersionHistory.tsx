/**
 * Strategy Version History Component (SB-07)
 * ==========================================
 *
 * Manages version history for strategies with rollback capability.
 * Saves versions to localStorage automatically on each change.
 *
 * Features:
 * - Auto-save versions on strategy changes
 * - View version history list
 * - Compare versions (diff view)
 * - Rollback to previous versions
 * - Clear old versions (keep last N)
 *
 * Related: docs/UI_BACKLOG.md (SB-07)
 */

import React, { useState, useEffect, useCallback } from 'react';
import {
  Box,
  Paper,
  Typography,
  IconButton,
  Tooltip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  ListItemSecondaryAction,
  Chip,
  Alert,
  Divider,
  Badge,
} from '@mui/material';
import {
  History as HistoryIcon,
  Restore as RestoreIcon,
  Delete as DeleteIcon,
  Compare as CompareIcon,
  Save as SaveIcon,
  ExpandMore as ExpandIcon,
  ExpandLess as CollapseIcon,
  CheckCircle as CurrentIcon,
} from '@mui/icons-material';
import { Strategy5Section } from '@/types/strategy';

// ============================================================================
// Types
// ============================================================================

export interface StrategyVersion {
  id: string;
  timestamp: string;
  strategyData: Strategy5Section;
  label?: string;
  changeDescription?: string;
}

export interface StrategyVersionHistoryProps {
  strategyName: string;
  currentStrategy: Strategy5Section;
  onRestore: (version: StrategyVersion) => void;
  maxVersions?: number;
}

// ============================================================================
// Constants
// ============================================================================

const DEFAULT_MAX_VERSIONS = 20;
const STORAGE_KEY_PREFIX = 'strategy-versions-';

// ============================================================================
// Component
// ============================================================================

export const StrategyVersionHistory: React.FC<StrategyVersionHistoryProps> = ({
  strategyName,
  currentStrategy,
  onRestore,
  maxVersions = DEFAULT_MAX_VERSIONS,
}) => {
  const [versions, setVersions] = useState<StrategyVersion[]>([]);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [compareDialogOpen, setCompareDialogOpen] = useState(false);
  const [selectedVersion, setSelectedVersion] = useState<StrategyVersion | null>(null);
  const [expanded, setExpanded] = useState(false);

  const storageKey = `${STORAGE_KEY_PREFIX}${strategyName || 'unnamed'}`;

  // ========================================
  // Storage Functions
  // ========================================

  const loadVersions = useCallback(() => {
    try {
      const saved = localStorage.getItem(storageKey);
      if (saved) {
        const parsed = JSON.parse(saved);
        if (Array.isArray(parsed)) {
          setVersions(parsed);
        }
      }
    } catch (err) {
      console.warn('Failed to load strategy versions:', err);
    }
  }, [storageKey]);

  const saveVersions = useCallback((newVersions: StrategyVersion[]) => {
    try {
      // Keep only the most recent N versions
      const trimmed = newVersions.slice(0, maxVersions);
      localStorage.setItem(storageKey, JSON.stringify(trimmed));
      setVersions(trimmed);
    } catch (err) {
      console.warn('Failed to save strategy versions:', err);
    }
  }, [storageKey, maxVersions]);

  // Load versions on mount
  useEffect(() => {
    loadVersions();
  }, [loadVersions]);

  // ========================================
  // Public Methods (for parent component)
  // ========================================

  // Save a new version
  const saveVersion = useCallback((description?: string) => {
    const newVersion: StrategyVersion = {
      id: `v-${Date.now()}`,
      timestamp: new Date().toISOString(),
      strategyData: JSON.parse(JSON.stringify(currentStrategy)), // Deep copy
      changeDescription: description || 'Manual save',
    };

    const newVersions = [newVersion, ...versions];
    saveVersions(newVersions);

    console.log(`[StrategyVersionHistory] Version saved: ${newVersion.id}`);
    return newVersion;
  }, [currentStrategy, versions, saveVersions]);

  // ========================================
  // Handlers
  // ========================================

  const handleOpenDialog = () => {
    setDialogOpen(true);
  };

  const handleCloseDialog = () => {
    setDialogOpen(false);
    setSelectedVersion(null);
  };

  const handleRestore = (version: StrategyVersion) => {
    onRestore(version);
    handleCloseDialog();
  };

  const handleDelete = (versionId: string) => {
    const newVersions = versions.filter((v) => v.id !== versionId);
    saveVersions(newVersions);
  };

  const handleClearAll = () => {
    if (window.confirm('Are you sure you want to clear all version history?')) {
      saveVersions([]);
    }
  };

  const handleSaveNow = () => {
    saveVersion('Manual save from UI');
  };

  const handleCompare = (version: StrategyVersion) => {
    setSelectedVersion(version);
    setCompareDialogOpen(true);
  };

  // ========================================
  // Helpers
  // ========================================

  const formatTimestamp = (timestamp: string): string => {
    try {
      const date = new Date(timestamp);
      const now = new Date();
      const diffMs = now.getTime() - date.getTime();
      const diffMin = Math.floor(diffMs / 60000);
      const diffHours = Math.floor(diffMs / 3600000);
      const diffDays = Math.floor(diffMs / 86400000);

      if (diffMin < 1) return 'Just now';
      if (diffMin < 60) return `${diffMin}m ago`;
      if (diffHours < 24) return `${diffHours}h ago`;
      if (diffDays < 7) return `${diffDays}d ago`;

      return date.toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      });
    } catch {
      return timestamp;
    }
  };

  const getChangeSummary = (version: StrategyVersion): string => {
    const data = version.strategyData;
    const parts = [];

    const s1Count = data.s1_signal?.conditions?.length || 0;
    const z1Count = data.z1_entry?.conditions?.length || 0;
    const ze1Count = data.ze1_close?.conditions?.length || 0;
    const e1Count = data.emergency_exit?.conditions?.length || 0;

    parts.push(`S1:${s1Count}`);
    parts.push(`Z1:${z1Count}`);
    parts.push(`ZE1:${ze1Count}`);
    parts.push(`E1:${e1Count}`);

    return parts.join(', ');
  };

  // ========================================
  // Render
  // ========================================

  return (
    <>
      {/* Compact Trigger Button */}
      <Tooltip title="Version History (SB-07)">
        <Badge badgeContent={versions.length} color="primary" max={99}>
          <IconButton size="small" onClick={handleOpenDialog}>
            <HistoryIcon fontSize="small" />
          </IconButton>
        </Badge>
      </Tooltip>

      {/* Version History Dialog */}
      <Dialog
        open={dialogOpen}
        onClose={handleCloseDialog}
        maxWidth="sm"
        fullWidth
        PaperProps={{ sx: { maxHeight: '80vh' } }}
      >
        <DialogTitle>
          <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <HistoryIcon />
              <Typography variant="h6">Version History</Typography>
            </Box>
            <Chip
              label={`${versions.length} versions`}
              size="small"
              variant="outlined"
            />
          </Box>
        </DialogTitle>

        <DialogContent dividers>
          {versions.length === 0 ? (
            <Alert severity="info">
              No version history yet. Click "Save Version" to create a snapshot.
            </Alert>
          ) : (
            <List dense>
              {versions.map((version, index) => (
                <React.Fragment key={version.id}>
                  <ListItem
                    sx={{
                      backgroundColor: index === 0 ? 'action.hover' : 'transparent',
                      borderRadius: 1,
                    }}
                  >
                    <ListItemIcon sx={{ minWidth: 36 }}>
                      {index === 0 ? (
                        <CurrentIcon color="success" fontSize="small" />
                      ) : (
                        <Typography variant="caption" color="text.secondary">
                          #{versions.length - index}
                        </Typography>
                      )}
                    </ListItemIcon>
                    <ListItemText
                      primary={
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                          <Typography variant="body2" fontWeight={index === 0 ? 600 : 400}>
                            {formatTimestamp(version.timestamp)}
                          </Typography>
                          {index === 0 && (
                            <Chip label="Latest" size="small" color="success" />
                          )}
                        </Box>
                      }
                      secondary={
                        <Box>
                          <Typography variant="caption" color="text.secondary" display="block">
                            {version.changeDescription || 'No description'}
                          </Typography>
                          <Typography variant="caption" color="text.disabled">
                            {getChangeSummary(version)}
                          </Typography>
                        </Box>
                      }
                    />
                    <ListItemSecondaryAction>
                      <Tooltip title="Compare with current">
                        <IconButton
                          size="small"
                          onClick={() => handleCompare(version)}
                          disabled={index === 0}
                        >
                          <CompareIcon fontSize="small" />
                        </IconButton>
                      </Tooltip>
                      <Tooltip title="Restore this version">
                        <IconButton
                          size="small"
                          onClick={() => handleRestore(version)}
                          disabled={index === 0}
                        >
                          <RestoreIcon fontSize="small" />
                        </IconButton>
                      </Tooltip>
                      <Tooltip title="Delete">
                        <IconButton
                          size="small"
                          onClick={() => handleDelete(version.id)}
                          sx={{ color: 'error.main' }}
                        >
                          <DeleteIcon fontSize="small" />
                        </IconButton>
                      </Tooltip>
                    </ListItemSecondaryAction>
                  </ListItem>
                  {index < versions.length - 1 && <Divider variant="inset" component="li" />}
                </React.Fragment>
              ))}
            </List>
          )}
        </DialogContent>

        <DialogActions sx={{ justifyContent: 'space-between', px: 3 }}>
          <Box>
            {versions.length > 0 && (
              <Button
                color="error"
                size="small"
                onClick={handleClearAll}
                startIcon={<DeleteIcon />}
              >
                Clear All
              </Button>
            )}
          </Box>
          <Box sx={{ display: 'flex', gap: 1 }}>
            <Button
              variant="outlined"
              onClick={handleSaveNow}
              startIcon={<SaveIcon />}
            >
              Save Version
            </Button>
            <Button onClick={handleCloseDialog}>Close</Button>
          </Box>
        </DialogActions>
      </Dialog>

      {/* Compare Dialog */}
      <Dialog
        open={compareDialogOpen}
        onClose={() => setCompareDialogOpen(false)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <CompareIcon />
            <Typography variant="h6">Compare Versions</Typography>
          </Box>
        </DialogTitle>
        <DialogContent dividers>
          {selectedVersion && (
            <Box sx={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 2 }}>
              {/* Current Version */}
              <Paper variant="outlined" sx={{ p: 2 }}>
                <Typography variant="subtitle2" color="primary" gutterBottom>
                  Current Version
                </Typography>
                <Typography variant="body2" component="pre" sx={{ fontSize: '0.75rem', overflow: 'auto', maxHeight: 400 }}>
                  {JSON.stringify(currentStrategy, null, 2)}
                </Typography>
              </Paper>

              {/* Selected Version */}
              <Paper variant="outlined" sx={{ p: 2 }}>
                <Typography variant="subtitle2" color="secondary" gutterBottom>
                  Selected Version ({formatTimestamp(selectedVersion.timestamp)})
                </Typography>
                <Typography variant="body2" component="pre" sx={{ fontSize: '0.75rem', overflow: 'auto', maxHeight: 400 }}>
                  {JSON.stringify(selectedVersion.strategyData, null, 2)}
                </Typography>
              </Paper>
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          {selectedVersion && (
            <Button
              variant="contained"
              color="primary"
              onClick={() => {
                handleRestore(selectedVersion);
                setCompareDialogOpen(false);
              }}
              startIcon={<RestoreIcon />}
            >
              Restore This Version
            </Button>
          )}
          <Button onClick={() => setCompareDialogOpen(false)}>Close</Button>
        </DialogActions>
      </Dialog>
    </>
  );
};

export default StrategyVersionHistory;

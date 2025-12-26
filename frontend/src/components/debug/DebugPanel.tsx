/**
 * Debug Panel Component
 * =====================
 * Real-time WebSocket message viewer for development troubleshooting.
 *
 * Features:
 * - Toggle with Ctrl+Shift+D
 * - Last 50 messages with circular buffer
 * - Filterable by message type
 * - Collapsible without losing history
 * - Dev-only (not visible in production)
 *
 * Story: 0-4-debug-panel-foundation
 */

'use client';

import React, { useEffect, useMemo } from 'react';
import {
  Drawer,
  Box,
  Typography,
  IconButton,
  Chip,
  Divider,
  Paper,
  Tooltip,
  Stack,
} from '@mui/material';
import {
  Close as CloseIcon,
  Delete as DeleteIcon,
  BugReport as BugIcon,
  FilterList as FilterIcon,
} from '@mui/icons-material';
import { useDebugStore, getFilteredMessages, MESSAGE_TYPES, type MessageType } from '@/stores/debugStore';

// Color mapping for message types
const TYPE_COLORS: Record<string, string> = {
  market_data: '#4caf50',
  indicators: '#2196f3',
  signal: '#ff9800',
  signals: '#ff9800',
  session_status: '#9c27b0',
  session_update: '#9c27b0',
  strategy_status: '#00bcd4',
  strategy_update: '#00bcd4',
  health_check: '#8bc34a',
  comprehensive_health_check: '#8bc34a',
  data: '#607d8b',
  execution_result: '#e91e63',
  status: '#795548',
};

const getTypeColor = (type: string): string => TYPE_COLORS[type] || '#757575';

// Format timestamp for display
const formatTimestamp = (iso: string): string => {
  try {
    const date = new Date(iso);
    return date.toLocaleTimeString('en-US', {
      hour12: false,
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      fractionalSecondDigits: 3,
    });
  } catch {
    return iso;
  }
};

// JSON syntax highlighter (simple)
const SyntaxHighlightedJSON: React.FC<{ data: unknown }> = ({ data }) => {
  const formatted = useMemo(() => {
    try {
      return JSON.stringify(data, null, 2);
    } catch {
      return String(data);
    }
  }, [data]);

  return (
    <Box
      component="pre"
      sx={{
        margin: 0,
        padding: 1,
        fontSize: '11px',
        fontFamily: 'monospace',
        backgroundColor: '#1e1e1e',
        color: '#d4d4d4',
        borderRadius: 1,
        overflow: 'auto',
        maxHeight: 200,
        whiteSpace: 'pre-wrap',
        wordBreak: 'break-all',
      }}
    >
      {formatted}
    </Box>
  );
};

// Individual message item
const MessageItem: React.FC<{ message: { id: number; type: MessageType; stream?: string; timestamp: string; payload: unknown } }> = ({ message }) => {
  const [expanded, setExpanded] = React.useState(false);

  return (
    <Paper
      elevation={0}
      sx={{
        mb: 1,
        p: 1,
        backgroundColor: 'rgba(255,255,255,0.02)',
        border: '1px solid rgba(255,255,255,0.1)',
        borderLeft: `3px solid ${getTypeColor(message.type)}`,
        cursor: 'pointer',
      }}
      onClick={() => setExpanded(!expanded)}
    >
      <Stack direction="row" alignItems="center" spacing={1}>
        <Typography
          variant="caption"
          sx={{ fontFamily: 'monospace', color: 'text.secondary', minWidth: 85 }}
        >
          {formatTimestamp(message.timestamp)}
        </Typography>
        <Chip
          label={message.type}
          size="small"
          sx={{
            height: 20,
            fontSize: '10px',
            backgroundColor: getTypeColor(message.type),
            color: '#fff',
          }}
        />
        {message.stream && (
          <Typography variant="caption" sx={{ color: 'text.secondary' }}>
            [{message.stream}]
          </Typography>
        )}
      </Stack>
      {expanded && (
        <Box sx={{ mt: 1 }}>
          <SyntaxHighlightedJSON data={message.payload} />
        </Box>
      )}
    </Paper>
  );
};

// Filter chips component
const FilterChips: React.FC = () => {
  const { activeFilters, toggleFilter, clearFilters } = useDebugStore();
  const uniqueTypes = MESSAGE_TYPES;

  return (
    <Box sx={{ mb: 1 }}>
      <Stack direction="row" alignItems="center" spacing={0.5} sx={{ mb: 0.5 }}>
        <FilterIcon fontSize="small" sx={{ color: 'text.secondary' }} />
        <Typography variant="caption" sx={{ color: 'text.secondary' }}>
          Filters {activeFilters.size > 0 && `(${activeFilters.size})`}
        </Typography>
        {activeFilters.size > 0 && (
          <Chip
            label="Clear"
            size="small"
            onClick={clearFilters}
            sx={{ height: 18, fontSize: '10px' }}
          />
        )}
      </Stack>
      <Stack direction="row" flexWrap="wrap" gap={0.5}>
        {uniqueTypes.map(type => (
          <Chip
            key={type}
            label={type}
            size="small"
            onClick={() => toggleFilter(type)}
            sx={{
              height: 22,
              fontSize: '10px',
              backgroundColor: activeFilters.has(type) ? getTypeColor(type) : 'transparent',
              color: activeFilters.has(type) ? '#fff' : 'text.secondary',
              border: `1px solid ${getTypeColor(type)}`,
              '&:hover': {
                backgroundColor: getTypeColor(type),
                color: '#fff',
              },
            }}
          />
        ))}
      </Stack>
    </Box>
  );
};

// Main Debug Panel component
export const DebugPanel: React.FC = () => {
  const { isOpen, togglePanel, setOpen, messages, clearMessages, activeFilters } = useDebugStore();

  // Keyboard shortcut: Ctrl+Shift+D
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.ctrlKey && e.shiftKey && e.key === 'D') {
        e.preventDefault();
        togglePanel();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [togglePanel]);

  // Get filtered messages
  const filteredMessages = useMemo(() => {
    if (activeFilters.size === 0) return messages;
    return messages.filter(msg => activeFilters.has(msg.type));
  }, [messages, activeFilters]);

  return (
    <Drawer
      anchor="right"
      open={isOpen}
      onClose={() => setOpen(false)}
      variant="persistent"
      sx={{
        '& .MuiDrawer-paper': {
          width: 400,
          backgroundColor: '#121212',
          color: '#fff',
          borderLeft: '1px solid rgba(255,255,255,0.12)',
        },
      }}
    >
      {/* Header */}
      <Box
        sx={{
          p: 1.5,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          borderBottom: '1px solid rgba(255,255,255,0.12)',
        }}
      >
        <Stack direction="row" alignItems="center" spacing={1}>
          <BugIcon sx={{ color: '#ff9800' }} />
          <Typography variant="subtitle1" fontWeight="bold">
            Debug Panel
          </Typography>
          <Chip
            label={`${messages.length} msgs`}
            size="small"
            sx={{ height: 20, fontSize: '10px' }}
          />
        </Stack>
        <Stack direction="row" spacing={0.5}>
          <Tooltip title="Clear messages">
            <IconButton size="small" onClick={clearMessages} sx={{ color: 'text.secondary' }}>
              <DeleteIcon fontSize="small" />
            </IconButton>
          </Tooltip>
          <Tooltip title="Close (Ctrl+Shift+D)">
            <IconButton size="small" onClick={() => setOpen(false)} sx={{ color: 'text.secondary' }}>
              <CloseIcon fontSize="small" />
            </IconButton>
          </Tooltip>
        </Stack>
      </Box>

      {/* Filters */}
      <Box sx={{ p: 1.5, borderBottom: '1px solid rgba(255,255,255,0.12)' }}>
        <FilterChips />
      </Box>

      {/* Message List */}
      <Box
        sx={{
          flex: 1,
          overflow: 'auto',
          p: 1.5,
        }}
      >
        {filteredMessages.length === 0 ? (
          <Typography variant="body2" sx={{ color: 'text.secondary', textAlign: 'center', mt: 4 }}>
            No messages{activeFilters.size > 0 ? ' matching filters' : ''}.
            <br />
            <Typography variant="caption">
              WebSocket messages will appear here.
            </Typography>
          </Typography>
        ) : (
          filteredMessages.map(msg => <MessageItem key={msg.id} message={msg} />)
        )}
      </Box>

      {/* Footer */}
      <Box
        sx={{
          p: 1,
          borderTop: '1px solid rgba(255,255,255,0.12)',
          backgroundColor: 'rgba(0,0,0,0.3)',
        }}
      >
        <Typography variant="caption" sx={{ color: 'text.secondary' }}>
          Press Ctrl+Shift+D to toggle | Max 50 messages
        </Typography>
      </Box>
    </Drawer>
  );
};

export default DebugPanel;

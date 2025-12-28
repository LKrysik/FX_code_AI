/**
 * Chart Drawing Tools Component (D-01, D-02)
 * ==========================================
 *
 * Drawing tools for chart annotation:
 * - D-01: Fibonacci Retracement
 * - D-02: Rectangle Zones
 *
 * Features:
 * - Click and drag to draw
 * - Editable after drawing
 * - Delete individual drawings
 * - Clear all drawings
 * - Persist drawings to localStorage
 *
 * Related: docs/UI_BACKLOG.md (D-01, D-02)
 */

import React, { useState, useCallback, useEffect } from 'react';
import { Logger } from '@/services/frontendLogService';
import {
  Box,
  IconButton,
  Tooltip,
  Menu,
  MenuItem,
  ListItemIcon,
  ListItemText,
  Divider,
  Typography,
  Chip,
  Stack,
} from '@mui/material';
import {
  Timeline as FibonacciIcon,
  CropFree as RectangleIcon,
  Delete as DeleteIcon,
  Edit as EditIcon,
  Done as DoneIcon,
  Close as CancelIcon,
  HighlightOff as ClearAllIcon,
} from '@mui/icons-material';

// ============================================================================
// Types
// ============================================================================

export type DrawingMode = 'none' | 'fibonacci' | 'rectangle';

export interface FibonacciDrawing {
  id: string;
  type: 'fibonacci';
  startPrice: number;
  endPrice: number;
  startTime: number;
  endTime: number;
  levels: number[]; // 0, 0.236, 0.382, 0.5, 0.618, 0.786, 1
  color: string;
  visible: boolean;
}

export interface RectangleDrawing {
  id: string;
  type: 'rectangle';
  startPrice: number;
  endPrice: number;
  startTime: number;
  endTime: number;
  color: string;
  fillOpacity: number;
  visible: boolean;
  label?: string;
}

export type Drawing = FibonacciDrawing | RectangleDrawing;

export interface ChartDrawingToolsProps {
  symbol: string;
  onDrawingModeChange: (mode: DrawingMode) => void;
  drawings: Drawing[];
  onDrawingsChange: (drawings: Drawing[]) => void;
  activeDrawing: Partial<Drawing> | null;
  onActiveDrawingChange: (drawing: Partial<Drawing> | null) => void;
}

// ============================================================================
// Constants
// ============================================================================

const FIBONACCI_LEVELS = [0, 0.236, 0.382, 0.5, 0.618, 0.786, 1];

const FIBONACCI_COLORS = {
  main: '#ffd700', // Gold
  levels: {
    0: '#00ff00',     // Green - Start
    0.236: '#7cfc00', // LawnGreen
    0.382: '#ffff00', // Yellow
    0.5: '#ffa500',   // Orange
    0.618: '#ff6347', // Tomato
    0.786: '#ff4500', // OrangeRed
    1: '#ff0000',     // Red - End
  } as Record<number, string>,
};

const RECTANGLE_COLORS = [
  { name: 'Support', color: '#4caf50', fill: 'rgba(76, 175, 80, 0.15)' },
  { name: 'Resistance', color: '#f44336', fill: 'rgba(244, 67, 54, 0.15)' },
  { name: 'Zone', color: '#2196f3', fill: 'rgba(33, 150, 243, 0.15)' },
  { name: 'Custom', color: '#9c27b0', fill: 'rgba(156, 39, 176, 0.15)' },
];

// ============================================================================
// Component
// ============================================================================

export const ChartDrawingTools: React.FC<ChartDrawingToolsProps> = ({
  symbol,
  onDrawingModeChange,
  drawings,
  onDrawingsChange,
  activeDrawing,
  onActiveDrawingChange,
}) => {
  const [drawingMode, setDrawingMode] = useState<DrawingMode>('none');
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null);
  const [selectedRectColor, setSelectedRectColor] = useState(RECTANGLE_COLORS[0]);

  // ========================================
  // Storage
  // ========================================

  const storageKey = `chart-drawings-${symbol}`;

  // Load drawings from localStorage on mount
  useEffect(() => {
    try {
      const saved = localStorage.getItem(storageKey);
      if (saved) {
        const parsed = JSON.parse(saved);
        if (Array.isArray(parsed)) {
          onDrawingsChange(parsed);
        }
      }
    } catch (err) {
      Logger.warn('ChartDrawingTools.loadDrawings', { message: 'Failed to load drawings from localStorage', error: err });
    }
  }, [symbol, storageKey, onDrawingsChange]);

  // Save drawings to localStorage when they change
  useEffect(() => {
    try {
      localStorage.setItem(storageKey, JSON.stringify(drawings));
    } catch (err) {
      Logger.warn('ChartDrawingTools.saveDrawings', { message: 'Failed to save drawings to localStorage', error: err });
    }
  }, [drawings, storageKey]);

  // ========================================
  // Handlers
  // ========================================

  const handleDrawingModeClick = (mode: DrawingMode) => {
    const newMode = drawingMode === mode ? 'none' : mode;
    setDrawingMode(newMode);
    onDrawingModeChange(newMode);
    setAnchorEl(null);
  };

  const handleMenuOpen = (event: React.MouseEvent<HTMLElement>) => {
    setAnchorEl(event.currentTarget);
  };

  const handleMenuClose = () => {
    setAnchorEl(null);
  };

  const handleClearAll = () => {
    onDrawingsChange([]);
    handleMenuClose();
  };

  const handleDeleteDrawing = (id: string) => {
    onDrawingsChange(drawings.filter((d) => d.id !== id));
  };

  const handleToggleVisibility = (id: string) => {
    onDrawingsChange(
      drawings.map((d) =>
        d.id === id ? { ...d, visible: !d.visible } : d
      )
    );
  };

  const cancelActiveDrawing = () => {
    onActiveDrawingChange(null);
    setDrawingMode('none');
    onDrawingModeChange('none');
  };

  // ========================================
  // Render
  // ========================================

  const fibonacciCount = drawings.filter((d) => d.type === 'fibonacci').length;
  const rectangleCount = drawings.filter((d) => d.type === 'rectangle').length;

  return (
    <Box
      sx={{
        display: 'flex',
        alignItems: 'center',
        gap: 0.5,
        backgroundColor: 'rgba(30, 30, 30, 0.85)',
        borderRadius: 1,
        px: 0.5,
        py: 0.25,
      }}
    >
      {/* D-01: Fibonacci Retracement Tool */}
      <Tooltip title="Fibonacci Retracement (D-01)">
        <IconButton
          size="small"
          onClick={() => handleDrawingModeClick('fibonacci')}
          sx={{
            color: drawingMode === 'fibonacci' ? '#ffd700' : '#9ca3af',
            backgroundColor:
              drawingMode === 'fibonacci' ? 'rgba(255, 215, 0, 0.2)' : 'transparent',
            '&:hover': {
              backgroundColor:
                drawingMode === 'fibonacci'
                  ? 'rgba(255, 215, 0, 0.3)'
                  : 'rgba(255, 255, 255, 0.05)',
            },
          }}
        >
          <FibonacciIcon fontSize="small" />
        </IconButton>
      </Tooltip>

      {/* D-02: Rectangle Zone Tool */}
      <Tooltip title="Rectangle Zone (D-02)">
        <IconButton
          size="small"
          onClick={() => handleDrawingModeClick('rectangle')}
          sx={{
            color: drawingMode === 'rectangle' ? '#2196f3' : '#9ca3af',
            backgroundColor:
              drawingMode === 'rectangle' ? 'rgba(33, 150, 243, 0.2)' : 'transparent',
            '&:hover': {
              backgroundColor:
                drawingMode === 'rectangle'
                  ? 'rgba(33, 150, 243, 0.3)'
                  : 'rgba(255, 255, 255, 0.05)',
            },
          }}
        >
          <RectangleIcon fontSize="small" />
        </IconButton>
      </Tooltip>

      {/* Divider */}
      <Box
        sx={{
          width: 1,
          height: 20,
          backgroundColor: 'rgba(255, 255, 255, 0.1)',
          mx: 0.5,
        }}
      />

      {/* Drawing Count & Menu */}
      <Tooltip title="Manage Drawings">
        <Chip
          label={`${drawings.length}`}
          size="small"
          onClick={handleMenuOpen}
          sx={{
            height: 24,
            fontSize: '0.7rem',
            backgroundColor: drawings.length > 0 ? 'rgba(76, 175, 80, 0.2)' : 'transparent',
            color: drawings.length > 0 ? '#4caf50' : '#9ca3af',
            cursor: 'pointer',
            '&:hover': {
              backgroundColor: 'rgba(255, 255, 255, 0.1)',
            },
          }}
        />
      </Tooltip>

      {/* Drawings Menu */}
      <Menu
        anchorEl={anchorEl}
        open={Boolean(anchorEl)}
        onClose={handleMenuClose}
        PaperProps={{
          sx: {
            backgroundColor: '#2d2d2d',
            minWidth: 200,
          },
        }}
      >
        <Typography variant="caption" color="text.secondary" sx={{ px: 2, py: 1 }}>
          Drawings ({drawings.length})
        </Typography>
        <Divider sx={{ borderColor: 'rgba(255,255,255,0.1)' }} />

        {drawings.length === 0 ? (
          <MenuItem disabled>
            <Typography variant="body2" color="text.secondary">
              No drawings yet
            </Typography>
          </MenuItem>
        ) : (
          <>
            {/* Fibonacci Drawings */}
            {fibonacciCount > 0 && (
              <Typography
                variant="caption"
                color="text.secondary"
                sx={{ px: 2, pt: 1, display: 'block' }}
              >
                Fibonacci ({fibonacciCount})
              </Typography>
            )}
            {drawings
              .filter((d) => d.type === 'fibonacci')
              .map((drawing) => (
                <MenuItem key={drawing.id} dense>
                  <ListItemIcon sx={{ minWidth: 32 }}>
                    <FibonacciIcon fontSize="small" sx={{ color: '#ffd700' }} />
                  </ListItemIcon>
                  <ListItemText
                    primary={`${drawing.startPrice.toFixed(2)} → ${drawing.endPrice.toFixed(2)}`}
                    primaryTypographyProps={{ fontSize: '0.8rem' }}
                  />
                  <IconButton
                    size="small"
                    onClick={(e) => {
                      e.stopPropagation();
                      handleToggleVisibility(drawing.id);
                    }}
                    sx={{ color: drawing.visible ? '#4caf50' : '#666' }}
                  >
                    {drawing.visible ? <DoneIcon fontSize="small" /> : <CancelIcon fontSize="small" />}
                  </IconButton>
                  <IconButton
                    size="small"
                    onClick={(e) => {
                      e.stopPropagation();
                      handleDeleteDrawing(drawing.id);
                    }}
                    sx={{ color: '#f44336' }}
                  >
                    <DeleteIcon fontSize="small" />
                  </IconButton>
                </MenuItem>
              ))}

            {/* Rectangle Drawings */}
            {rectangleCount > 0 && (
              <Typography
                variant="caption"
                color="text.secondary"
                sx={{ px: 2, pt: 1, display: 'block' }}
              >
                Rectangles ({rectangleCount})
              </Typography>
            )}
            {drawings
              .filter((d) => d.type === 'rectangle')
              .map((drawing) => (
                <MenuItem key={drawing.id} dense>
                  <ListItemIcon sx={{ minWidth: 32 }}>
                    <RectangleIcon fontSize="small" sx={{ color: drawing.color }} />
                  </ListItemIcon>
                  <ListItemText
                    primary={(drawing as RectangleDrawing).label || 'Zone'}
                    secondary={`${drawing.startPrice.toFixed(2)} - ${drawing.endPrice.toFixed(2)}`}
                    primaryTypographyProps={{ fontSize: '0.8rem' }}
                    secondaryTypographyProps={{ fontSize: '0.7rem' }}
                  />
                  <IconButton
                    size="small"
                    onClick={(e) => {
                      e.stopPropagation();
                      handleToggleVisibility(drawing.id);
                    }}
                    sx={{ color: drawing.visible ? '#4caf50' : '#666' }}
                  >
                    {drawing.visible ? <DoneIcon fontSize="small" /> : <CancelIcon fontSize="small" />}
                  </IconButton>
                  <IconButton
                    size="small"
                    onClick={(e) => {
                      e.stopPropagation();
                      handleDeleteDrawing(drawing.id);
                    }}
                    sx={{ color: '#f44336' }}
                  >
                    <DeleteIcon fontSize="small" />
                  </IconButton>
                </MenuItem>
              ))}
          </>
        )}

        {drawings.length > 0 && (
          <>
            <Divider sx={{ borderColor: 'rgba(255,255,255,0.1)', my: 1 }} />
            <MenuItem onClick={handleClearAll}>
              <ListItemIcon>
                <ClearAllIcon fontSize="small" sx={{ color: '#f44336' }} />
              </ListItemIcon>
              <ListItemText primary="Clear All Drawings" />
            </MenuItem>
          </>
        )}
      </Menu>

      {/* Active Drawing Indicator */}
      {activeDrawing && (
        <Stack direction="row" spacing={0.5} alignItems="center" sx={{ ml: 1 }}>
          <Chip
            label={drawingMode === 'fibonacci' ? 'Drawing Fib...' : 'Drawing Zone...'}
            size="small"
            color="primary"
            variant="outlined"
            sx={{ height: 24, fontSize: '0.7rem' }}
          />
          <IconButton size="small" onClick={cancelActiveDrawing} sx={{ color: '#f44336' }}>
            <CancelIcon fontSize="small" />
          </IconButton>
        </Stack>
      )}

      {/* Drawing Mode Instructions */}
      {drawingMode !== 'none' && !activeDrawing && (
        <Typography
          variant="caption"
          color="text.secondary"
          sx={{ ml: 1, fontSize: '0.65rem' }}
        >
          Click & drag on chart
        </Typography>
      )}
    </Box>
  );
};

// ============================================================================
// Fibonacci Overlay Component (renders on canvas)
// ============================================================================

export interface FibonacciOverlayProps {
  drawing: FibonacciDrawing;
  chartWidth: number;
  chartHeight: number;
  priceToY: (price: number) => number;
  timeToX: (time: number) => number;
}

export const FibonacciOverlay: React.FC<FibonacciOverlayProps> = ({
  drawing,
  chartWidth,
  chartHeight,
  priceToY,
  timeToX,
}) => {
  if (!drawing.visible) return null;

  const startY = priceToY(drawing.startPrice);
  const endY = priceToY(drawing.endPrice);
  const startX = timeToX(drawing.startTime);
  const endX = timeToX(drawing.endTime);
  const priceRange = drawing.startPrice - drawing.endPrice;

  return (
    <svg
      style={{
        position: 'absolute',
        top: 0,
        left: 0,
        width: chartWidth,
        height: chartHeight,
        pointerEvents: 'none',
        zIndex: 50,
      }}
    >
      {/* Main trend line */}
      <line
        x1={startX}
        y1={startY}
        x2={endX}
        y2={endY}
        stroke={FIBONACCI_COLORS.main}
        strokeWidth={1}
        strokeDasharray="4,4"
      />

      {/* Fibonacci levels */}
      {FIBONACCI_LEVELS.map((level) => {
        const levelPrice = drawing.endPrice + priceRange * level;
        const y = priceToY(levelPrice);
        const color = FIBONACCI_COLORS.levels[level] || '#ffffff';

        return (
          <g key={level}>
            {/* Level line */}
            <line
              x1={0}
              y1={y}
              x2={chartWidth}
              y2={y}
              stroke={color}
              strokeWidth={1}
              opacity={0.6}
            />
            {/* Level label */}
            <text
              x={chartWidth - 80}
              y={y - 4}
              fill={color}
              fontSize={10}
              fontFamily="monospace"
            >
              {(level * 100).toFixed(1)}% ({levelPrice.toFixed(2)})
            </text>
          </g>
        );
      })}
    </svg>
  );
};

// ============================================================================
// Rectangle Overlay Component
// ============================================================================

export interface RectangleOverlayProps {
  drawing: RectangleDrawing;
  chartWidth: number;
  chartHeight: number;
  priceToY: (price: number) => number;
  timeToX: (time: number) => number;
}

export const RectangleOverlay: React.FC<RectangleOverlayProps> = ({
  drawing,
  chartWidth,
  chartHeight,
  priceToY,
  timeToX,
}) => {
  if (!drawing.visible) return null;

  const y1 = priceToY(Math.max(drawing.startPrice, drawing.endPrice));
  const y2 = priceToY(Math.min(drawing.startPrice, drawing.endPrice));
  const x1 = timeToX(Math.min(drawing.startTime, drawing.endTime));
  const x2 = timeToX(Math.max(drawing.startTime, drawing.endTime));

  const width = Math.abs(x2 - x1);
  const height = Math.abs(y2 - y1);

  return (
    <svg
      style={{
        position: 'absolute',
        top: 0,
        left: 0,
        width: chartWidth,
        height: chartHeight,
        pointerEvents: 'none',
        zIndex: 50,
      }}
    >
      {/* Rectangle fill */}
      <rect
        x={x1}
        y={y1}
        width={width}
        height={height}
        fill={drawing.color}
        fillOpacity={drawing.fillOpacity}
        stroke={drawing.color}
        strokeWidth={1}
      />

      {/* Label */}
      {drawing.label && (
        <text
          x={x1 + 4}
          y={y1 + 14}
          fill={drawing.color}
          fontSize={11}
          fontWeight="bold"
          fontFamily="sans-serif"
        >
          {drawing.label}
        </text>
      )}

      {/* Price labels */}
      <text
        x={x2 + 4}
        y={y1 + 12}
        fill={drawing.color}
        fontSize={10}
        fontFamily="monospace"
      >
        {Math.max(drawing.startPrice, drawing.endPrice).toFixed(2)}
      </text>
      <text
        x={x2 + 4}
        y={y2 - 4}
        fill={drawing.color}
        fontSize={10}
        fontFamily="monospace"
      >
        {Math.min(drawing.startPrice, drawing.endPrice).toFixed(2)}
      </text>
    </svg>
  );
};

export default ChartDrawingTools;

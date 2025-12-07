'use client';

import React from 'react';
import {
  Box,
  Paper,
  Typography,
  styled,
  alpha,
  Tooltip,
} from '@mui/material';

// ============================================================================
// TYPES
// ============================================================================

export type StateMachineState =
  | 'MONITORING'
  | 'SIGNAL_DETECTED'
  | 'POSITION_ACTIVE'
  | 'EXITED'
  | 'ERROR';

export interface StateMachineDiagramProps {
  currentState?: StateMachineState;
  onStateClick?: (state: StateMachineState) => void;
  showLabels?: boolean;
}

// ============================================================================
// STATE CONFIGURATION
// ============================================================================

interface StateNodeConfig {
  id: StateMachineState;
  label: string;
  shortLabel: string;
  description: string;
  color: string;
  x: number; // Position in SVG
  y: number;
}

const STATE_NODES: StateNodeConfig[] = [
  {
    id: 'MONITORING',
    label: 'MONITORING',
    shortLabel: 'Idle',
    description: 'System is actively scanning markets for pump/dump signals',
    color: '#4caf50',
    x: 100,
    y: 100,
  },
  {
    id: 'SIGNAL_DETECTED',
    label: 'SIGNAL_DETECTED',
    shortLabel: 'Pump Found',
    description: 'Pump signal detected - evaluating entry conditions',
    color: '#ff9800',
    x: 400,
    y: 100,
  },
  {
    id: 'POSITION_ACTIVE',
    label: 'POSITION_ACTIVE',
    shortLabel: 'In Trade',
    description: 'Active SHORT position - monitoring for dump end',
    color: '#f44336',
    x: 700,
    y: 100,
  },
  {
    id: 'EXITED',
    label: 'EXITED',
    shortLabel: 'Done',
    description: 'Position closed - ready for next signal',
    color: '#2196f3',
    x: 400,
    y: 300,
  },
  {
    id: 'ERROR',
    label: 'ERROR',
    shortLabel: 'Error',
    description: 'System error detected - requires attention',
    color: '#d32f2f',
    x: 100,
    y: 300,
  },
];

interface TransitionConfig {
  from: StateMachineState;
  to: StateMachineState;
  label: string;
  description: string;
  type: 'main' | 'timeout' | 'emergency' | 'return';
}

const TRANSITIONS: TransitionConfig[] = [
  {
    from: 'MONITORING',
    to: 'SIGNAL_DETECTED',
    label: 'S1',
    description: 'Pump detected: velocity spike + volume surge',
    type: 'main',
  },
  {
    from: 'SIGNAL_DETECTED',
    to: 'POSITION_ACTIVE',
    label: 'Z1',
    description: 'Entry conditions met: peak detected, SHORT at top',
    type: 'main',
  },
  {
    from: 'SIGNAL_DETECTED',
    to: 'EXITED',
    label: 'O1',
    description: 'Timeout: signal expired without entry',
    type: 'timeout',
  },
  {
    from: 'POSITION_ACTIVE',
    to: 'EXITED',
    label: 'ZE1 / E1',
    description: 'Exit: dump completed OR emergency stop',
    type: 'main',
  },
  {
    from: 'EXITED',
    to: 'MONITORING',
    label: '',
    description: 'Return to monitoring',
    type: 'return',
  },
  {
    from: 'ERROR',
    to: 'MONITORING',
    label: '',
    description: 'Recovery: error resolved, resume monitoring',
    type: 'return',
  },
];

// ============================================================================
// STYLED COMPONENTS
// ============================================================================

const DiagramContainer = styled(Paper)(({ theme }) => ({
  padding: theme.spacing(3),
  backgroundColor: theme.palette.background.paper,
  borderRadius: theme.shape.borderRadius,
  overflow: 'auto',
}));

const StateNode = styled('g', {
  shouldForwardProp: (prop) => prop !== 'active' && prop !== 'clickable'
})<{ active?: boolean; clickable?: boolean }>(({ theme, active, clickable }) => ({
  cursor: clickable ? 'pointer' : 'default',
  transition: 'all 0.3s ease',

  '&:hover rect, &:hover circle': clickable ? {
    filter: 'brightness(1.2)',
    strokeWidth: active ? '4' : '2',
  } : {},
}));

const TransitionPath = styled('g', {
  shouldForwardProp: (prop) => prop !== 'active'
})<{ active?: boolean }>(({ theme, active }) => ({
  transition: 'all 0.3s ease',
  opacity: active ? 1 : 0.6,

  '& path': {
    strokeWidth: active ? '3' : '2',
  },

  '& text': {
    opacity: active ? 1 : 0.8,
  },
}));

// ============================================================================
// HELPER FUNCTIONS
// ============================================================================

/**
 * Calculate SVG path for arrow between two points
 */
function createArrowPath(
  x1: number,
  y1: number,
  x2: number,
  y2: number,
  curved: boolean = false
): string {
  if (!curved) {
    return `M ${x1} ${y1} L ${x2} ${y2}`;
  }

  // Create curved path
  const midX = (x1 + x2) / 2;
  const midY = (y1 + y2) / 2;
  const offsetY = y2 > y1 ? 30 : -30;

  return `M ${x1} ${y1} Q ${midX} ${midY + offsetY} ${x2} ${y2}`;
}

/**
 * Calculate arrowhead points
 */
function createArrowhead(x: number, y: number, angle: number): string {
  const size = 10;
  const rad = (angle * Math.PI) / 180;

  const p1x = x - size * Math.cos(rad - Math.PI / 6);
  const p1y = y - size * Math.sin(rad - Math.PI / 6);
  const p2x = x - size * Math.cos(rad + Math.PI / 6);
  const p2y = y - size * Math.sin(rad + Math.PI / 6);

  return `M ${p1x} ${p1y} L ${x} ${y} L ${p2x} ${p2y}`;
}

/**
 * Calculate angle between two points
 */
function calculateAngle(x1: number, y1: number, x2: number, y2: number): number {
  return Math.atan2(y2 - y1, x2 - x1) * (180 / Math.PI);
}

/**
 * Get transition line color based on type
 */
function getTransitionColor(type: TransitionConfig['type'], active: boolean): string {
  if (active) {
    return type === 'emergency' ? '#d32f2f' : '#2196f3';
  }

  switch (type) {
    case 'main':
      return '#666';
    case 'timeout':
      return '#ff9800';
    case 'emergency':
      return '#d32f2f';
    case 'return':
      return '#9e9e9e';
    default:
      return '#666';
  }
}

// ============================================================================
// MAIN COMPONENT
// ============================================================================

const StateMachineDiagram: React.FC<StateMachineDiagramProps> = ({
  currentState,
  onStateClick,
  showLabels = true,
}) => {
  const handleStateClick = (stateId: StateMachineState) => {
    if (onStateClick) {
      onStateClick(stateId);
    }
  };

  const nodeRadius = 70;
  const nodeWidth = 140;
  const nodeHeight = 80;

  return (
    <DiagramContainer elevation={2}>
      <Box sx={{ mb: 2 }}>
        <Typography variant="h6" gutterBottom>
          State Machine Flow
        </Typography>
        <Typography variant="body2" color="text.secondary">
          MONITORING → S1 (pump detected) → Z1 (SHORT at peak) → ZE1/E1 (dump complete)
        </Typography>
      </Box>

      <svg
        width="900"
        height="450"
        viewBox="0 0 900 450"
        style={{ width: '100%', height: 'auto' }}
      >
        {/* Define arrow marker */}
        <defs>
          <marker
            id="arrowhead"
            markerWidth="10"
            markerHeight="10"
            refX="9"
            refY="3"
            orient="auto"
          >
            <polygon points="0 0, 10 3, 0 6" fill="#666" />
          </marker>
          <marker
            id="arrowhead-active"
            markerWidth="10"
            markerHeight="10"
            refX="9"
            refY="3"
            orient="auto"
          >
            <polygon points="0 0, 10 3, 0 6" fill="#2196f3" />
          </marker>
          <marker
            id="arrowhead-timeout"
            markerWidth="10"
            markerHeight="10"
            refX="9"
            refY="3"
            orient="auto"
          >
            <polygon points="0 0, 10 3, 0 6" fill="#ff9800" />
          </marker>
          <marker
            id="arrowhead-return"
            markerWidth="10"
            markerHeight="10"
            refX="9"
            refY="3"
            orient="auto"
          >
            <polygon points="0 0, 10 3, 0 6" fill="#9e9e9e" />
          </marker>
        </defs>

        {/* Draw transitions (arrows) */}
        {TRANSITIONS.map((transition, idx) => {
          const fromNode = STATE_NODES.find(n => n.id === transition.from);
          const toNode = STATE_NODES.find(n => n.id === transition.to);

          if (!fromNode || !toNode) return null;

          const startX = fromNode.x + (toNode.x > fromNode.x ? nodeWidth / 2 : 0);
          const startY = fromNode.y + (toNode.y > fromNode.y ? nodeHeight : nodeHeight / 2);
          const endX = toNode.x + (toNode.x > fromNode.x ? -nodeWidth / 2 : 0);
          const endY = toNode.y + (toNode.y > fromNode.y ? 0 : nodeHeight / 2);

          const curved = transition.type === 'timeout' || transition.type === 'return';
          const pathD = createArrowPath(startX, startY, endX, endY, curved);
          const color = getTransitionColor(transition.type, false);
          const marker = transition.type === 'timeout' ? 'arrowhead-timeout' :
                        transition.type === 'return' ? 'arrowhead-return' : 'arrowhead';

          const midX = (startX + endX) / 2;
          const midY = curved ? (startY + endY) / 2 + (endY > startY ? 30 : -30) : (startY + endY) / 2;

          return (
            <Tooltip
              key={idx}
              title={transition.description}
              arrow
              placement="top"
            >
              <TransitionPath>
                <path
                  d={pathD}
                  stroke={color}
                  strokeWidth="2"
                  fill="none"
                  markerEnd={`url(#${marker})`}
                  strokeDasharray={transition.type === 'return' ? '5,5' : 'none'}
                />
                {showLabels && transition.label && (
                  <text
                    x={midX}
                    y={midY - 5}
                    fontSize="14"
                    fontWeight="bold"
                    fill={color}
                    textAnchor="middle"
                  >
                    {transition.label}
                  </text>
                )}
              </TransitionPath>
            </Tooltip>
          );
        })}

        {/* Draw state nodes */}
        {STATE_NODES.map((node) => {
          const isActive = currentState === node.id;
          const isClickable = !!onStateClick;

          return (
            <Tooltip
              key={node.id}
              title={
                <Box>
                  <Typography variant="body2" sx={{ fontWeight: 'bold' }}>
                    {node.label}
                  </Typography>
                  <Typography variant="caption">
                    {node.description}
                  </Typography>
                </Box>
              }
              arrow
              placement="top"
            >
              <StateNode
                active={isActive}
                clickable={isClickable}
                onClick={() => isClickable && handleStateClick(node.id)}
              >
                {/* Node rectangle */}
                <rect
                  x={node.x - nodeWidth / 2}
                  y={node.y}
                  width={nodeWidth}
                  height={nodeHeight}
                  rx="8"
                  fill={alpha(node.color, isActive ? 0.25 : 0.1)}
                  stroke={node.color}
                  strokeWidth={isActive ? '3' : '2'}
                />

                {/* State label */}
                <text
                  x={node.x}
                  y={node.y + 30}
                  fontSize="14"
                  fontWeight="bold"
                  fill={node.color}
                  textAnchor="middle"
                >
                  {node.label}
                </text>

                {/* Short description */}
                {showLabels && (
                  <text
                    x={node.x}
                    y={node.y + 50}
                    fontSize="11"
                    fill="#999"
                    textAnchor="middle"
                  >
                    ({node.shortLabel})
                  </text>
                )}

                {/* Active indicator */}
                {isActive && (
                  <circle
                    cx={node.x + nodeWidth / 2 - 10}
                    cy={node.y + 10}
                    r="6"
                    fill={node.color}
                  >
                    <animate
                      attributeName="opacity"
                      values="1;0.3;1"
                      dur="1.5s"
                      repeatCount="indefinite"
                    />
                  </circle>
                )}
              </StateNode>
            </Tooltip>
          );
        })}
      </svg>

      {/* Legend */}
      {showLabels && (
        <Box sx={{ mt: 2, pt: 2, borderTop: '1px solid', borderColor: 'divider' }}>
          <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 1 }}>
            Transitions:
          </Typography>
          <Box sx={{ display: 'flex', gap: 3, flexWrap: 'wrap' }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <Box sx={{ width: 30, height: 2, bgcolor: '#666' }} />
              <Typography variant="caption">Main flow</Typography>
            </Box>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <Box sx={{ width: 30, height: 2, bgcolor: '#ff9800' }} />
              <Typography variant="caption">Timeout (O1)</Typography>
            </Box>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <Box
                sx={{
                  width: 30,
                  height: 2,
                  bgcolor: '#9e9e9e',
                  backgroundImage: 'repeating-linear-gradient(90deg, #9e9e9e, #9e9e9e 5px, transparent 5px, transparent 10px)',
                }}
              />
              <Typography variant="caption">Return to monitoring</Typography>
            </Box>
          </Box>
        </Box>
      )}
    </DiagramContainer>
  );
};

export default StateMachineDiagram;

/**
 * Session Configuration Dialog
 * ============================
 *
 * Dialog wrapper for SessionConfigMockup that integrates with dashboard pages.
 * Allows users to configure strategies, symbols, and session parameters before starting.
 *
 * Usage:
 * ```tsx
 * const [dialogOpen, setDialogOpen] = useState(false);
 *
 * <Button onClick={() => setDialogOpen(true)}>Start Session</Button>
 *
 * <SessionConfigDialog
 *   open={dialogOpen}
 *   onClose={() => setDialogOpen(false)}
 *   onConfirm={(config) => {
 *     // Use config to start session
 *     startSession(config);
 *   }}
 *   defaultMode="backtest"
 * />
 * ```
 *
 * TODO: This wraps the mockup component. Once SessionConfigMockup is fully implemented,
 * this dialog will provide production-ready session configuration.
 */

'use client';

import React from 'react';
import { Dialog, DialogContent, DialogTitle, IconButton, Box } from '@mui/material';
import { Close as CloseIcon } from '@mui/icons-material';
import SessionConfigMockup from './SessionConfigMockup';

interface SessionConfigDialogProps {
  open: boolean;
  onClose: () => void;
  onConfirm: (config: SessionConfig) => void;
  defaultMode?: 'live' | 'paper' | 'backtest';
}

export interface SessionConfig {
  mode: 'live' | 'paper' | 'backtest';
  strategies: string[];
  symbols: string[];
  config: {
    global_budget: number;
    max_position_size: number;
    stop_loss_percent: number;
    take_profit_percent: number;
    session_id?: string;  // For backtest mode
    acceleration_factor?: number;  // For backtest mode
    auto_start: boolean;
  };
}

/**
 * Dialog wrapper for session configuration.
 *
 * TODO: Once SessionConfigMockup is fully implemented with real APIs:
 * 1. Remove MOCKUP warnings
 * 2. Add loading states
 * 3. Add validation feedback
 * 4. Integrate with error handling
 */
export const SessionConfigDialog: React.FC<SessionConfigDialogProps> = ({
  open,
  onClose,
  onConfirm,
  defaultMode = 'paper',
}) => {
  const handleSessionStart = (config: any) => {
    // Transform mockup config to SessionConfig format
    const sessionConfig: SessionConfig = {
      mode: config.mode,
      strategies: config.strategies,
      symbols: config.symbols,
      config: {
        global_budget: config.config.global_budget,
        max_position_size: config.config.max_position_size,
        stop_loss_percent: config.config.stop_loss_percent,
        take_profit_percent: config.config.take_profit_percent,
        session_id: config.config.session_id,
        acceleration_factor: config.config.acceleration_factor,
        auto_start: config.config.auto_start,
      },
    };

    onConfirm(sessionConfig);
    onClose();
  };

  return (
    <Dialog
      open={open}
      onClose={onClose}
      maxWidth="lg"
      fullWidth
      PaperProps={{
        sx: {
          minHeight: '80vh',
          maxHeight: '90vh',
        },
      }}
    >
      <DialogTitle>
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <span>Configure Trading Session</span>
          <IconButton onClick={onClose} size="small">
            <CloseIcon />
          </IconButton>
        </Box>
      </DialogTitle>
      <DialogContent>
        <SessionConfigMockup
          onSessionStart={handleSessionStart}
          onCancel={onClose}
        />
      </DialogContent>
    </Dialog>
  );
};

export default SessionConfigDialog;

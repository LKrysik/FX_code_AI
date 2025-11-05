/**
 * InlineEdit Component
 *
 * Click-to-edit component with zero dialogs.
 * Click value → edit → Enter to save, Escape to cancel.
 *
 * @example
 * <InlineEdit
 *   value={position.stopLoss}
 *   onSave={(newValue) => updateStopLoss(position.id, newValue)}
 *   format="currency"
 *   min={0}
 *   max={position.entryPrice * 0.95}
 * />
 */

import React, { useState, useEffect, useRef, KeyboardEvent } from 'react';
import { Box, TextField, Typography, IconButton, CircularProgress } from '@mui/material';
import { Edit as EditIcon, Check as SaveIcon, Close as CancelIcon } from '@mui/icons-material';

export type InlineEditFormat = 'currency' | 'percentage' | 'number' | 'text';

interface InlineEditProps {
  value: number | string;
  onSave: (newValue: number | string) => Promise<void> | void;
  format?: InlineEditFormat;
  min?: number;
  max?: number;
  readOnly?: boolean;
  label?: string;
  precision?: number;  // Decimal places for numbers
  placeholder?: string;
  size?: 'small' | 'medium';
  color?: 'primary' | 'secondary' | 'success' | 'error' | 'warning' | 'info';
}

export const InlineEdit: React.FC<InlineEditProps> = ({
  value,
  onSave,
  format = 'text',
  min,
  max,
  readOnly = false,
  label,
  precision = 2,
  placeholder,
  size = 'small',
  color = 'primary',
}) => {
  const [isEditing, setIsEditing] = useState(false);
  const [editValue, setEditValue] = useState<string>(String(value));
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Sync with external value changes
  useEffect(() => {
    if (!isEditing) {
      setEditValue(String(value));
    }
  }, [value, isEditing]);

  // Auto-focus and select on edit
  useEffect(() => {
    if (isEditing && inputRef.current) {
      inputRef.current.focus();
      inputRef.current.select();
    }
  }, [isEditing]);

  const formatDisplay = (val: number | string): string => {
    if (typeof val === 'number') {
      switch (format) {
        case 'currency':
          return `$${val.toFixed(precision)}`;
        case 'percentage':
          return `${val.toFixed(precision)}%`;
        case 'number':
          return val.toLocaleString(undefined, {
            minimumFractionDigits: precision,
            maximumFractionDigits: precision
          });
        default:
          return String(val);
      }
    }
    return String(val);
  };

  const parseValue = (str: string): number | string => {
    if (format === 'text') {
      return str;
    }

    // Remove formatting characters
    const cleaned = str.replace(/[$,%\s,]/g, '');
    const parsed = parseFloat(cleaned);

    if (isNaN(parsed)) {
      throw new Error('Invalid number format');
    }

    return parsed;
  };

  const validateValue = (val: number): string | null => {
    if (typeof val !== 'number') return null;

    if (min !== undefined && val < min) {
      return `Value must be at least ${formatDisplay(min)}`;
    }

    if (max !== undefined && val > max) {
      return `Value must be at most ${formatDisplay(max)}`;
    }

    return null;
  };

  const handleSave = async () => {
    setError(null);
    setSaving(true);

    try {
      const parsedValue = parseValue(editValue);

      // Validate if it's a number
      if (typeof parsedValue === 'number') {
        const validationError = validateValue(parsedValue);
        if (validationError) {
          setError(validationError);
          setSaving(false);
          return;
        }
      }

      await onSave(parsedValue);
      setIsEditing(false);
    } catch (err: any) {
      console.error('Save failed:', err);
      setError(err.message || 'Failed to save');
    } finally {
      setSaving(false);
    }
  };

  const handleCancel = () => {
    setEditValue(String(value));
    setError(null);
    setIsEditing(false);
  };

  const handleKeyPress = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && !saving) {
      handleSave();
    }
    if (e.key === 'Escape') {
      handleCancel();
    }
  };

  // Display mode
  if (readOnly || !isEditing) {
    return (
      <Box
        sx={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: 0.5,
          cursor: readOnly ? 'default' : 'pointer',
          '&:hover .edit-icon': {
            opacity: readOnly ? 0 : 1
          },
          transition: 'all 0.2s',
        }}
        onClick={() => !readOnly && setIsEditing(true)}
      >
        {label && (
          <Typography variant="caption" color="text.secondary" sx={{ mr: 0.5 }}>
            {label}:
          </Typography>
        )}
        <Typography
          variant={size === 'small' ? 'body2' : 'body1'}
          fontWeight="bold"
          color={`${color}.main`}
        >
          {formatDisplay(value)}
        </Typography>
        {!readOnly && (
          <EditIcon
            className="edit-icon"
            fontSize="small"
            sx={{
              opacity: 0,
              transition: 'opacity 0.2s',
              color: 'action.disabled'
            }}
          />
        )}
      </Box>
    );
  }

  // Edit mode
  return (
    <Box sx={{ display: 'inline-flex', flexDirection: 'column', gap: 0.5 }}>
      <Box sx={{ display: 'inline-flex', alignItems: 'center', gap: 0.5 }}>
        <TextField
          inputRef={inputRef}
          value={editValue}
          onChange={(e) => setEditValue(e.target.value)}
          onKeyDown={handleKeyPress}
          size={size}
          type={format === 'text' ? 'text' : 'number'}
          disabled={saving}
          error={!!error}
          placeholder={placeholder}
          sx={{ width: 120 }}
          InputProps={{
            startAdornment: format === 'currency' ? '$' : undefined,
            endAdornment: format === 'percentage' ? '%' : undefined,
          }}
        />

        <IconButton
          size={size}
          onClick={handleSave}
          disabled={saving || !editValue}
          color="success"
        >
          {saving ? (
            <CircularProgress size={16} />
          ) : (
            <SaveIcon fontSize="small" />
          )}
        </IconButton>

        <IconButton
          size={size}
          onClick={handleCancel}
          disabled={saving}
          color="error"
        >
          <CancelIcon fontSize="small" />
        </IconButton>
      </Box>

      {error && (
        <Typography variant="caption" color="error" sx={{ ml: 1 }}>
          {error}
        </Typography>
      )}
    </Box>
  );
};

export default InlineEdit;

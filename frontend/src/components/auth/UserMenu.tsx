'use client';

import React, { useState } from 'react';
import {
  IconButton,
  Menu,
  MenuItem,
  Avatar,
  Typography,
  Box,
  Divider,
  ListItemIcon,
  ListItemText,
} from '@mui/material';
import {
  AccountCircle as AccountIcon,
  Logout as LogoutIcon,
  AdminPanelSettings as AdminIcon,
  Person as PersonIcon,
} from '@mui/icons-material';
import { useAuthStore, useHasPermission } from '@/stores';

export const UserMenu: React.FC = () => {
  const { user, logout } = useAuthStore();
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null);
  const open = Boolean(anchorEl);

  const hasAdminPermission = useHasPermission('admin_system');

  const handleClick = (event: React.MouseEvent<HTMLElement>) => {
    setAnchorEl(event.currentTarget);
  };

  const handleClose = () => {
    setAnchorEl(null);
  };

  const handleLogout = async () => {
    handleClose();
    await logout();
  };

  if (!user) {
    return null;
  }

  const getPermissionIcon = () => {
    if (hasAdminPermission) {
      return <AdminIcon color="error" />;
    }
    return <PersonIcon color="primary" />;
  };

  const getPermissionText = () => {
    if (hasAdminPermission) {
      return 'Administrator';
    }
    if (user.permissions.includes('execute_live_trading')) {
      return 'Premium Trader';
    }
    if (user.permissions.includes('execute_paper_trading')) {
      return 'Paper Trader';
    }
    return 'Basic User';
  };

  return (
    <>
      <IconButton
        onClick={handleClick}
        size="small"
        sx={{ ml: 2 }}
        aria-controls={open ? 'account-menu' : undefined}
        aria-haspopup="true"
        aria-expanded={open ? 'true' : undefined}
      >
        <Avatar sx={{ width: 32, height: 32, bgcolor: 'primary.main' }}>
          {user.username.charAt(0).toUpperCase()}
        </Avatar>
      </IconButton>

      <Menu
        anchorEl={anchorEl}
        id="account-menu"
        open={open}
        onClose={handleClose}
        onClick={handleClose}
        PaperProps={{
          elevation: 0,
          sx: {
            overflow: 'visible',
            filter: 'drop-shadow(0px 2px 8px rgba(0,0,0,0.32))',
            mt: 1.5,
            '& .MuiAvatar-root': {
              width: 32,
              height: 32,
              ml: -0.5,
              mr: 1,
            },
            '&:before': {
              content: '""',
              display: 'block',
              position: 'absolute',
              top: 0,
              right: 14,
              width: 10,
              height: 10,
              bgcolor: 'background.paper',
              transform: 'translateY(-50%) rotate(45deg)',
              zIndex: 0,
            },
          },
        }}
        transformOrigin={{ horizontal: 'right', vertical: 'top' }}
        anchorOrigin={{ horizontal: 'right', vertical: 'bottom' }}
      >
        <Box sx={{ px: 2, py: 1 }}>
          <Typography variant="subtitle1" fontWeight="bold">
            {user.username}
          </Typography>
          <Box sx={{ display: 'flex', alignItems: 'center', mt: 0.5 }}>
            {getPermissionIcon()}
            <Typography variant="body2" color="text.secondary" sx={{ ml: 0.5 }}>
              {getPermissionText()}
            </Typography>
          </Box>
          <Typography variant="caption" color="text.secondary">
            User ID: {user.user_id.slice(0, 8)}...
          </Typography>
        </Box>

        <Divider />

        <MenuItem onClick={handleClose}>
          <ListItemIcon>
            <AccountIcon fontSize="small" />
          </ListItemIcon>
          <ListItemText>Profile Settings</ListItemText>
        </MenuItem>

        {hasAdminPermission && (
          <MenuItem onClick={handleClose}>
            <ListItemIcon>
              <AdminIcon fontSize="small" />
            </ListItemIcon>
            <ListItemText>Admin Panel</ListItemText>
          </MenuItem>
        )}

        <Divider />

        <MenuItem onClick={handleLogout}>
          <ListItemIcon>
            <LogoutIcon fontSize="small" />
          </ListItemIcon>
          <ListItemText>Logout</ListItemText>
        </MenuItem>
      </Menu>
    </>
  );
};
"use client";

import React, { useState } from 'react';
import { Avatar, Menu, MenuItem, IconButton, ListItemIcon } from '@mui/material';
import Icon from './Icon';
import { LogOut } from 'lucide-react';
import { useAuth } from './AuthContext';

export default function UserMenu() {
  const { user, logout } = useAuth();
  const [anchorEl, setAnchorEl] = useState<HTMLElement | null>(null);
  const open = Boolean(anchorEl);

  if (!user) return null;

  const handleOpen = (e: React.MouseEvent<HTMLElement>) => setAnchorEl(e.currentTarget);
  const handleClose = () => setAnchorEl(null);

  return (
    <>
      <IconButton onClick={handleOpen} size="small" aria-label="User menu">
        <Avatar src={user.avatarUrl} alt={user.name} sx={{ width: 32, height: 32 }} />
      </IconButton>
      <Menu anchorEl={anchorEl} open={open} onClose={handleClose} onClick={handleClose}>
        <MenuItem onClick={logout}>
          <ListItemIcon>
            <Icon icon={LogOut} fontSize="small" />
          </ListItemIcon>
          Sign out
        </MenuItem>
      </Menu>
    </>
  );
}



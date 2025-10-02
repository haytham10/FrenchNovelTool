"use client";

import React from 'react';
import MuiIconButton, { type IconButtonProps as MuiIconButtonProps } from '@mui/material/IconButton';
import Tooltip from '@mui/material/Tooltip';

export type IconButtonProps = MuiIconButtonProps & {
  title?: string;
};

export default function IconButton({ title, children, ...props }: IconButtonProps) {
  const btn = <MuiIconButton color="inherit" {...props}>{children}</MuiIconButton>;
  return title ? <Tooltip title={title}>{btn}</Tooltip> : btn;
}



"use client";

/**
 * Reusable IconButton Component with accessibility features
 * Extends MUI IconButton with tooltip support and enhanced focus styles
 */

import React from 'react';
import MuiIconButton, { type IconButtonProps as MuiIconButtonProps } from '@mui/material/IconButton';
import Tooltip from '@mui/material/Tooltip';
import { styled } from '@mui/material/styles';

export type IconButtonProps = MuiIconButtonProps & {
  title?: string;
  tooltip?: string;
};

const StyledIconButton = styled(MuiIconButton)(({ theme }) => ({
  transition: 'all 0.2s ease',
  
  // Focus visible styles for accessibility
  '&:focus-visible': {
    outline: `3px solid ${theme.palette.primary.main}`,
    outlineOffset: '2px',
  },
  
  // Hover effect
  '&:hover': {
    backgroundColor: theme.palette.mode === 'dark' 
      ? 'rgba(255, 255, 255, 0.08)' 
      : 'rgba(0, 0, 0, 0.04)',
  },
}));

export default function IconButton({ 
  title, 
  tooltip,
  children, 
  'aria-label': ariaLabel,
  ...props 
}: IconButtonProps) {
  const tooltipTitle = tooltip || title;
  
  const button = (
    <StyledIconButton 
      color="inherit" 
      aria-label={ariaLabel || title}
      {...props}
    >
      {children}
    </StyledIconButton>
  );
  
  return tooltipTitle ? (
    <Tooltip title={tooltipTitle}>
      {button}
    </Tooltip>
  ) : button;
}

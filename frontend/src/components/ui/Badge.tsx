"use client";

/**
 * Reusable Badge Component for status indicators
 * Extends MUI Chip with custom variants
 */

import React from 'react';
import Chip, { type ChipProps } from '@mui/material/Chip';
import { styled } from '@mui/material/styles';

export type BadgeVariant = 'success' | 'error' | 'warning' | 'info' | 'default';

export interface BadgeProps extends Omit<ChipProps, 'color' | 'variant'> {
  variant?: BadgeVariant;
  dot?: boolean;
}

const StyledChip = styled(Chip)<{ badgevariant?: BadgeVariant }>(({ theme, badgevariant }) => {
  const getColors = () => {
    switch (badgevariant) {
      case 'success':
        return {
          backgroundColor: theme.palette.success.light,
          color: theme.palette.success.dark,
        };
      case 'error':
        return {
          backgroundColor: theme.palette.error.light,
          color: theme.palette.error.dark,
        };
      case 'warning':
        return {
          backgroundColor: theme.palette.warning.light,
          color: theme.palette.warning.dark,
        };
      case 'info':
        return {
          backgroundColor: theme.palette.info.light,
          color: theme.palette.info.dark,
        };
      default:
        return {
          backgroundColor: theme.palette.grey[200],
          color: theme.palette.text.primary,
        };
    }
  };

  return {
    ...getColors(),
    fontWeight: 500,
    fontSize: '0.75rem',
    
    // Focus visible for keyboard navigation
    '&:focus-visible': {
      outline: `2px solid ${theme.palette.primary.main}`,
      outlineOffset: '2px',
    },
  };
});

export default function Badge({ 
  variant = 'default',
  // dot prop reserved for future use (e.g., dot indicator badge)
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  dot: _dot = false,
  label,
  ...props 
}: BadgeProps) {
  return (
    <StyledChip
      label={label}
      size="small"
      badgevariant={variant}
      {...props}
    />
  );
}

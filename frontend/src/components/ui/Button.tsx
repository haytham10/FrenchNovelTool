"use client";

/**
 * Reusable Button Component with variants
 * Extends MUI Button with custom styling and accessibility features
 */

import React from 'react';
import MuiButton, { type ButtonProps as MuiButtonProps } from '@mui/material/Button';
import { styled } from '@mui/material/styles';
import CircularProgress from '@mui/material/CircularProgress';

export type ButtonVariant = 'primary' | 'secondary' | 'danger' | 'ghost';

export interface ButtonProps extends Omit<MuiButtonProps, 'variant'> {
  variant?: ButtonVariant;
  loading?: boolean;
  fullWidth?: boolean;
}

const StyledButton = styled(MuiButton, {
  shouldForwardProp: (prop) => prop !== 'loading',
})<{ loading?: boolean }>(({ theme, loading }) => ({
  position: 'relative',
  transition: 'all 0.3s ease',
  
  // Focus visible styles for accessibility
  '&:focus-visible': {
    outline: `3px solid ${theme.palette.primary.main}`,
    outlineOffset: '2px',
  },
  
  ...(loading && {
    pointerEvents: 'none',
  }),
}));

export default function Button({ 
  variant = 'primary', 
  loading = false,
  children,
  disabled,
  startIcon,
  ...props 
}: ButtonProps) {
  const getMuiVariant = (): MuiButtonProps['variant'] => {
    switch (variant) {
      case 'primary':
        return 'contained';
      case 'secondary':
        return 'outlined';
      case 'danger':
        return 'contained';
      case 'ghost':
        return 'text';
      default:
        return 'contained';
    }
  };

  const getColor = (): MuiButtonProps['color'] => {
    return variant === 'danger' ? 'error' : 'primary';
  };

  return (
    <StyledButton
      variant={getMuiVariant()}
      color={getColor()}
      disabled={disabled || loading}
      loading={loading}
      startIcon={loading ? undefined : startIcon}
      {...props}
    >
      {loading && (
        <CircularProgress 
          size={20} 
          sx={{ 
            position: 'absolute',
            left: '50%',
            marginLeft: '-10px',
          }} 
        />
      )}
      <span style={{ visibility: loading ? 'hidden' : 'visible' }}>
        {children}
      </span>
    </StyledButton>
  );
}

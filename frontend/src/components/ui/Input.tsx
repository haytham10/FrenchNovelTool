"use client";

/**
 * Reusable Input Component with error states and helper text
 * Extends MUI TextField with enhanced accessibility
 */

import React from 'react';
import TextField, { type TextFieldProps } from '@mui/material/TextField';
import { styled } from '@mui/material/styles';

export interface InputProps extends Omit<TextFieldProps, 'variant'> {
  variant?: 'outlined' | 'filled' | 'standard';
}

const StyledTextField = styled(TextField)(({ theme, error }) => ({
  // Focus visible styles for accessibility
  '& .MuiOutlinedInput-root': {
    '&.Mui-focused': {
      '& .MuiOutlinedInput-notchedOutline': {
        borderWidth: '2px',
      },
    },
    '&:focus-visible': {
      outline: `2px solid ${theme.palette.primary.main}`,
      outlineOffset: '2px',
    },
  },
  
  // Error state styling
  ...(error && {
    '& .MuiOutlinedInput-root': {
      '& .MuiOutlinedInput-notchedOutline': {
        borderColor: theme.palette.error.main,
      },
    },
  }),
}));

export default function Input({ 
  variant = 'outlined',
  error,
  helperText,
  ...props 
}: InputProps) {
  return (
    <StyledTextField
      variant={variant}
      error={error}
      helperText={helperText}
      inputProps={{
        'aria-invalid': error ? 'true' : 'false',
        'aria-describedby': helperText ? `${props.id}-helper-text` : undefined,
        ...props.inputProps,
      }}
      FormHelperTextProps={{
        id: `${props.id}-helper-text`,
        ...props.FormHelperTextProps,
      }}
      {...props}
    />
  );
}

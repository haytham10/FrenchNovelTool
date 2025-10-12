"use client";

/**
 * Reusable Select Component with accessibility features
 * Extends MUI Select with enhanced styling
 */

import React from 'react';
import MuiSelect, { type SelectProps as MuiSelectProps } from '@mui/material/Select';
import MenuItem from '@mui/material/MenuItem';
import FormControl from '@mui/material/FormControl';
import InputLabel from '@mui/material/InputLabel';
import FormHelperText from '@mui/material/FormHelperText';
import { styled } from '@mui/material/styles';

export interface SelectOption {
  value: string | number;
  label: string;
  disabled?: boolean;
}

export interface SelectProps extends Omit<MuiSelectProps, 'error'> {
  options: SelectOption[];
  label?: string;
  helperText?: string;
  error?: boolean;
  fullWidth?: boolean;
}

const StyledSelect = styled(MuiSelect)(({ theme, error }) => ({
  // Focus visible styles for accessibility
  '&.Mui-focused': {
    '& .MuiOutlinedInput-notchedOutline': {
      borderWidth: '2px',
    },
  },
  
  '&:focus-visible': {
    outline: `2px solid ${theme.palette.primary.main}`,
    outlineOffset: '2px',
  },
  
  // Error state styling
  ...(error && {
    '& .MuiOutlinedInput-notchedOutline': {
      borderColor: theme.palette.error.main,
    },
  }),
}));

export default function Select({
  options,
  label,
  helperText,
  error = false,
  fullWidth = false,
  id,
  ...props
}: SelectProps) {
  const selectId = id || `select-${label?.toLowerCase().replace(/\s+/g, '-')}`;
  const labelId = `${selectId}-label`;
  const helperTextId = `${selectId}-helper-text`;

  return (
    <FormControl fullWidth={fullWidth} error={error}>
      {label && <InputLabel id={labelId}>{label}</InputLabel>}
      <StyledSelect
        labelId={label ? labelId : undefined}
        id={selectId}
        label={label}
        error={error}
        inputProps={{
          'aria-invalid': error ? 'true' : 'false',
          'aria-describedby': helperText ? helperTextId : undefined,
        }}
        {...props}
      >
        {options.map((option) => (
          <MenuItem 
            key={option.value} 
            value={option.value}
            disabled={option.disabled}
          >
            {option.label}
          </MenuItem>
        ))}
      </StyledSelect>
      {helperText && (
        <FormHelperText id={helperTextId}>
          {helperText}
        </FormHelperText>
      )}
    </FormControl>
  );
}

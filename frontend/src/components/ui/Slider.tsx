"use client";

/**
 * Reusable Slider Component with accessibility features
 * Extends MUI Slider with enhanced styling
 */

import React from 'react';
import MuiSlider, { type SliderProps as MuiSliderProps } from '@mui/material/Slider';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import { styled } from '@mui/material/styles';

export interface SliderProps extends MuiSliderProps {
  label?: string;
  showValue?: boolean;
  valueFormatter?: (value: number) => string;
}

const StyledSlider = styled(MuiSlider)(({ theme }) => ({
  // Focus visible styles for accessibility
  '& .MuiSlider-thumb': {
    transition: 'all 0.2s ease',
    '&:focus-visible': {
      outline: `3px solid ${theme.palette.primary.main}`,
      outlineOffset: '2px',
      boxShadow: `0 0 0 8px ${
        theme.palette.mode === 'dark'
          ? 'rgba(255, 255, 255, 0.16)'
          : 'rgba(0, 0, 0, 0.16)'
      }`,
    },
    '&:hover': {
      boxShadow: `0 0 0 8px ${
        theme.palette.mode === 'dark'
          ? 'rgba(255, 255, 255, 0.16)'
          : 'rgba(0, 0, 0, 0.16)'
      }`,
    },
  },
  
  '& .MuiSlider-track': {
    transition: 'background-color 0.2s ease',
  },
  
  '& .MuiSlider-rail': {
    opacity: 0.28,
  },
}));

export default function Slider({
  label,
  showValue = false,
  valueFormatter,
  value,
  'aria-label': ariaLabel,
  ...props
}: SliderProps) {
  const formatValue = (val: number) => {
    if (valueFormatter) return valueFormatter(val);
    return val.toString();
  };

  const currentValue = Array.isArray(value) ? value[0] : value;

  return (
    <Box sx={{ width: '100%' }}>
      {(label || showValue) && (
        <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
          {label && (
            <Typography variant="body2" color="text.secondary">
              {label}
            </Typography>
          )}
          {showValue && currentValue !== undefined && (
            <Typography variant="body2" color="primary" fontWeight="medium">
              {formatValue(currentValue as number)}
            </Typography>
          )}
        </Box>
      )}
      <StyledSlider
        value={value}
        aria-label={ariaLabel || label}
        {...props}
      />
    </Box>
  );
}

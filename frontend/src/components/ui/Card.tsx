"use client";

/**
 * Reusable Card Container Component
 * Extends MUI Paper with consistent styling
 */

import React from 'react';
import Paper, { type PaperProps } from '@mui/material/Paper';
import { styled } from '@mui/material/styles';

export interface CardProps extends PaperProps {
  hover?: boolean;
}

const StyledPaper = styled(Paper, {
  shouldForwardProp: (prop) => prop !== 'hover',
})<{ hover?: boolean }>(({ theme, hover }) => ({
  transition: 'all 0.3s ease',
  
  ...(hover && {
    '&:hover': {
      transform: 'translateY(-2px)',
      boxShadow: theme.shadows[6],
    },
  }),
  
  // Focus within for keyboard navigation
  '&:focus-within': {
    outline: `2px solid ${theme.palette.primary.main}`,
    outlineOffset: '2px',
  },
}));

export default function Card({ 
  hover = false,
  elevation = 3,
  children,
  ...props 
}: CardProps) {
  return (
    <StyledPaper
      elevation={elevation}
      hover={hover}
      {...props}
    >
      {children}
    </StyledPaper>
  );
}

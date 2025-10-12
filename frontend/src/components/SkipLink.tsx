"use client";

/**
 * Skip to Main Content Link
 * Provides keyboard navigation shortcut for screen readers
 */

import React from 'react';
import { styled } from '@mui/material/styles';

const StyledLink = styled('a')(({ theme }) => ({
  position: 'absolute',
  top: '-100px',
  left: '0',
  zIndex: 9999,
  padding: theme.spacing(1, 2),
  backgroundColor: theme.palette.primary.main,
  color: theme.palette.primary.contrastText,
  textDecoration: 'none',
  fontWeight: 600,
  borderRadius: '0 0 4px 0',
  transition: 'top 0.3s ease',
  
  '&:focus': {
    top: '0',
    outline: `3px solid ${theme.palette.secondary.main}`,
    outlineOffset: '2px',
  },
}));

export default function SkipLink() {
  return (
    <StyledLink href="#main-content">
      Skip to main content
    </StyledLink>
  );
}

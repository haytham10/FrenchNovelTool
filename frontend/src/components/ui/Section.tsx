"use client";

/**
 * Reusable Section/Panel Component
 * Semantic container for organizing content sections
 */

import React from 'react';
import Box, { type BoxProps } from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import Divider from '@mui/material/Divider';
import { styled } from '@mui/material/styles';

export interface SectionProps extends BoxProps {
  title?: string;
  subtitle?: string;
  noDivider?: boolean;
  children: React.ReactNode;
}

const StyledSection = styled(Box)(({ theme }) => ({
  padding: theme.spacing(3),
  
  [theme.breakpoints.up('md')]: {
    padding: theme.spacing(4),
  },
}));

export default function Section({
  title,
  subtitle,
  noDivider = false,
  children,
  ...props
}: SectionProps) {
  return (
    <StyledSection component="section" {...props}>
      {(title || subtitle) && (
        <Box sx={{ mb: 3 }}>
          {title && (
            <Typography 
              variant="h5" 
              component="h2" 
              gutterBottom={!!subtitle}
              sx={{ fontWeight: 700 }}
            >
              {title}
            </Typography>
          )}
          {subtitle && (
            <Typography variant="body2" color="text.secondary">
              {subtitle}
            </Typography>
          )}
          {!noDivider && <Divider sx={{ mt: 2 }} />}
        </Box>
      )}
      {children}
    </StyledSection>
  );
}

// Export Panel as an alias for Section
export const Panel = Section;

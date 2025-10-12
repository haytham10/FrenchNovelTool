"use client";

/**
 * Reusable Skeleton Loaders
 * For showing loading states
 */

import React from 'react';
import MuiSkeleton, { type SkeletonProps as MuiSkeletonProps } from '@mui/material/Skeleton';
import Box from '@mui/material/Box';
import Card from './Card';

export type SkeletonProps = MuiSkeletonProps;

// Re-export MUI Skeleton with our defaults
export const Skeleton = MuiSkeleton;

// Card skeleton for loading card states
export interface CardSkeletonProps {
  count?: number;
  height?: number | string;
}

export function CardSkeleton({ count = 1, height = 200 }: CardSkeletonProps) {
  return (
    <>
      {Array.from({ length: count }).map((_, index) => (
        <Card key={index} sx={{ mb: 2 }}>
          <Box sx={{ p: 2 }}>
            <Skeleton variant="rectangular" height={height} />
            <Box sx={{ pt: 2 }}>
              <Skeleton width="60%" />
              <Skeleton width="40%" />
            </Box>
          </Box>
        </Card>
      ))}
    </>
  );
}

// Table skeleton for loading table states
export interface TableSkeletonProps {
  rows?: number;
  columns?: number;
}

export function TableSkeleton({ rows = 5, columns = 3 }: TableSkeletonProps) {
  return (
    <Box>
      {/* Header */}
      <Box sx={{ display: 'flex', gap: 2, mb: 2 }}>
        {Array.from({ length: columns }).map((_, index) => (
          <Skeleton key={`header-${index}`} variant="rectangular" height={40} sx={{ flex: 1 }} />
        ))}
      </Box>
      {/* Rows */}
      {Array.from({ length: rows }).map((_, rowIndex) => (
        <Box key={`row-${rowIndex}`} sx={{ display: 'flex', gap: 2, mb: 1 }}>
          {Array.from({ length: columns }).map((_, colIndex) => (
            <Skeleton key={`cell-${rowIndex}-${colIndex}`} height={60} sx={{ flex: 1 }} />
          ))}
        </Box>
      ))}
    </Box>
  );
}

// Text skeleton for loading text states
export interface TextSkeletonProps {
  lines?: number;
  width?: string | string[];
}

export function TextSkeleton({ lines = 3, width }: TextSkeletonProps) {
  const widths = Array.isArray(width) ? width : Array(lines).fill(width || '100%');
  
  return (
    <Box>
      {Array.from({ length: lines }).map((_, index) => (
        <Skeleton 
          key={index} 
          width={widths[index] || '100%'} 
          sx={{ mb: 0.5 }}
        />
      ))}
    </Box>
  );
}

export default Skeleton;

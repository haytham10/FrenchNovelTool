"use client";

import React from 'react';
import { Breadcrumbs as MUIBreadcrumbs, Link as MUILink, Typography } from '@mui/material';
import Link from 'next/link';

export type Crumb = { label: string; href?: string };

export default function Breadcrumbs({ items }: { items: Crumb[] }) {
  return (
    <MUIBreadcrumbs aria-label="breadcrumb" sx={{ my: 2 }}>
      {items.map((item, idx) =>
        idx === items.length - 1 ? (
          <Typography key={idx} color="text.primary">{item.label}</Typography>
        ) : (
          <MUILink key={idx} component={Link} href={item.href || '#'} underline="hover" color="inherit">
            {item.label}
          </MUILink>
        )
      )}
    </MUIBreadcrumbs>
  );
}



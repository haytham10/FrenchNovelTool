"use client";

import React from 'react';
import type { LucideIcon } from 'lucide-react';
import { SvgIcon, type SvgIconProps } from '@mui/material';

export type IconProps = Omit<SvgIconProps, 'component'> & {
  icon: LucideIcon;
  label?: string;
  strokeWidth?: number;
};

export default function Icon({ icon: Lucide, label, strokeWidth = 1.75, ...props }: IconProps) {
  const ariaProps = label ? { role: 'img', 'aria-label': label } : { 'aria-hidden': true };
  return (
    <SvgIcon {...ariaProps} {...props}>
      <Lucide strokeWidth={strokeWidth} />
    </SvgIcon>
  );
}



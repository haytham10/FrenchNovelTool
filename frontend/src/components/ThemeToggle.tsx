"use client";

import React, { useContext } from 'react';
import Icon from './Icon';
import IconButton from './IconButton';
import { Sun, Moon } from 'lucide-react';
import { ColorModeContext } from './Providers';

export default function ThemeToggle() {
  const { mode, toggle } = useContext(ColorModeContext);
  const isDark = mode === 'dark';
  return (
    <IconButton onClick={toggle} title={isDark ? 'Switch to light mode' : 'Switch to dark mode'} aria-label="Toggle theme">
      {isDark ? <Icon icon={Sun} fontSize="small" /> : <Icon icon={Moon} fontSize="small" />}
    </IconButton>
  );
}



"use client";

import React from 'react';
import { AppBar, Toolbar, Typography, Box, Button, Container, IconButton as MIconButton, Skeleton } from '@mui/material';
import Link from 'next/link';
import ThemeToggle from './ThemeToggle';
import Icon from './Icon';
import { BookOpenText, Search, HelpCircle } from 'lucide-react';
import CommandPalette from './CommandPalette';
import GlobalSearch from './GlobalSearch';
import UserMenu from './UserMenu';
import GoogleLoginButton from './GoogleLoginButton';
import HelpModal from './HelpModal';
import { useAuth } from './AuthContext';

export default function Header() {
  const [searchOpen, setSearchOpen] = React.useState(false);
  const [helpOpen, setHelpOpen] = React.useState(false);
  const { user, isAuthenticating } = useAuth();
  return (
    <AppBar position="sticky" color="transparent" elevation={0} sx={{ backdropFilter: 'blur(8px)' }}>
      <Container maxWidth="lg">
        <Toolbar disableGutters sx={{ display: 'flex', gap: 2, py: 1 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.25, mr: 'auto' }}>
            <Icon icon={BookOpenText} color="primary" />
            <Typography variant="h6" sx={{ fontWeight: 900, letterSpacing: '-0.02em' }} className="gradient-text">
              French Novel Tool
            </Typography>
          </Box>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <MIconButton color="inherit" onClick={() => setHelpOpen(true)} aria-label="Help">
              <Icon icon={HelpCircle} fontSize="small" />
            </MIconButton>
            {user && (
              <>
                <MIconButton color="inherit" onClick={() => setSearchOpen(true)} aria-label="Search">
                  <Icon icon={Search} fontSize="small" />
                </MIconButton>
                <Button component={Link} href="/history" color="inherit">History</Button>
                <Button component={Link} href="/settings" color="inherit">Settings</Button>
              </>
            )}
            {isAuthenticating ? (
              <Skeleton variant="circular" width={32} height={32} />
            ) : (
              user ? <UserMenu /> : <GoogleLoginButton />
            )}
            <ThemeToggle />
          </Box>
        </Toolbar>
      </Container>
      <CommandPalette />
      <GlobalSearch open={searchOpen} onClose={() => setSearchOpen(false)} />
      <HelpModal open={helpOpen} onClose={() => setHelpOpen(false)} />
    </AppBar>
  );
}



"use client";

import React, { useEffect, useMemo, useState } from 'react';
import { Dialog, DialogContent, TextField, List, ListItemButton, ListItemText, Box } from '@mui/material';
import { useRouter } from 'next/navigation';

type Command = { title: string; href: string };

const commands: Command[] = [
  { title: 'Home', href: '/' },
  { title: 'Coverage Tool', href: '/coverage' },
  { title: 'History', href: '/history' },
  { title: 'Settings', href: '/settings' },
];

export default function CommandPalette() {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState('');
  const router = useRouter();

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        setOpen((v) => !v);
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, []);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return commands;
    return commands.filter((c) => c.title.toLowerCase().includes(q));
  }, [query]);

  const go = (href: string) => {
    setOpen(false);
    setQuery('');
    router.push(href);
  };

  return (
    <Dialog open={open} onClose={() => setOpen(false)} fullWidth maxWidth="sm">
      <DialogContent>
        <TextField
          // eslint-disable-next-line jsx-a11y/no-autofocus
          autoFocus
          fullWidth
          placeholder="Type a command or search…"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          sx={{ mb: 2 }}
        />
        <List>
          {filtered.map((c) => (
            <ListItemButton key={c.href} onClick={() => go(c.href)}>
              <ListItemText primary={c.title} secondary={c.href} />
            </ListItemButton>
          ))}
          {filtered.length === 0 && (
            <Box sx={{ px: 2, py: 1, color: 'text.secondary' }}>No results</Box>
          )}
        </List>
      </DialogContent>
    </Dialog>
  );
}



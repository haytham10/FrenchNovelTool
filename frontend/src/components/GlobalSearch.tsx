"use client";

import React, { useMemo, useState } from 'react';
import { Dialog, DialogContent, TextField, List, ListItemButton, ListItemText, InputAdornment } from '@mui/material';
import Icon from './Icon';
import { Search } from 'lucide-react';
import { useRouter } from 'next/navigation';

type Item = { title: string; href: string };

const items: Item[] = [
  { title: 'Home', href: '/' },
  { title: 'Processing History', href: '/history' },
  { title: 'User Settings', href: '/settings' },
];

export default function GlobalSearch({ open, onClose }: { open: boolean; onClose: () => void }) {
  const [query, setQuery] = useState('');
  const router = useRouter();

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return items;
    return items.filter((i) => i.title.toLowerCase().includes(q));
  }, [query]);

  const go = (href: string) => {
    onClose();
    setQuery('');
    router.push(href);
  };

  return (
    <Dialog open={open} onClose={onClose} fullWidth maxWidth="sm">
      <DialogContent>
        <TextField
          autoFocus
          fullWidth
          placeholder="Search pages…"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          InputProps={{
            startAdornment: (
              <InputAdornment position="start">
                <Icon icon={Search} fontSize="small" />
              </InputAdornment>
            ),
          }}
          sx={{ mb: 2 }}
        />
        <List>
          {filtered.map((i) => (
            <ListItemButton key={i.href} onClick={() => go(i.href)}>
              <ListItemText primary={i.title} secondary={i.href} />
            </ListItemButton>
          ))}
        </List>
      </DialogContent>
    </Dialog>
  );
}



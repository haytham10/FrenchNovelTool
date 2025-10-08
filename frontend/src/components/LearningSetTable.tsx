'use client';

import React, { useMemo, useState } from 'react';
import {
  Box,
  Paper,
  TextField,
  InputAdornment,
  Typography,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TablePagination,
  Chip,
} from '@mui/material';
import { Search as SearchIcon } from '@mui/icons-material';
import type { LearningSetEntry } from '@/lib/api';

interface LearningSetTableProps {
  entries: LearningSetEntry[];
  loading?: boolean;
}

export default function LearningSetTable({ entries, loading = false }: LearningSetTableProps) {
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(25);

  const filteredEntries = useMemo(() => {
    if (!search.trim()) return entries;
    const query = search.toLowerCase().trim();
    return entries.filter((entry) =>
      entry.sentence_text.toLowerCase().includes(query) || String(entry.rank).includes(query)
    );
  }, [entries, search]);

  const paginatedEntries = useMemo(() => {
    const start = page * rowsPerPage;
    return filteredEntries.slice(start, start + rowsPerPage);
  }, [filteredEntries, page, rowsPerPage]);

  const handleChangePage = (_event: unknown, newPage: number) => {
    setPage(newPage);
  };

  const handleChangeRowsPerPage = (event: React.ChangeEvent<HTMLInputElement>) => {
    setRowsPerPage(parseInt(event.target.value, 10));
    setPage(0);
  };

  if (loading && entries.length === 0) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
        <Typography variant="body2" color="text.secondary">
          Building learning set...
        </Typography>
      </Box>
    );
  }

  if (entries.length === 0) {
    return (
      <Paper sx={{ p: 4, textAlign: 'center' }}>
        <Typography variant="body1" color="text.secondary">
          No sentences selected yet. Run Coverage mode to generate a learning set.
        </Typography>
      </Paper>
    );
  }

  return (
    <Box>
      <Box sx={{ mb: 2 }}>
        <TextField
          fullWidth
          size="small"
          placeholder="Search by rank or sentence..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          InputProps={{
            startAdornment: (
              <InputAdornment position="start">
                <SearchIcon fontSize="small" />
              </InputAdornment>
            ),
          }}
        />
      </Box>

      <TableContainer component={Paper} variant="outlined">
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell width="10%">
                <Typography variant="subtitle2" fontWeight={600}>
                  Rank
                </Typography>
              </TableCell>
              <TableCell>
                <Typography variant="subtitle2" fontWeight={600}>
                  Sentence
                </Typography>
              </TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {paginatedEntries.map((entry) => (
              <TableRow key={`learning-set-${entry.rank}-${entry.sentence_index ?? 'na'}`} hover>
                <TableCell>
                  <Typography variant="body2" fontWeight={500}>
                    {entry.rank}
                  </Typography>
                </TableCell>
                <TableCell>
                  <Typography variant="body2">{entry.sentence_text}</Typography>
                  <Box sx={{ display: 'flex', gap: 1, mt: 0.5, flexWrap: 'wrap' }}>
                    {typeof entry.token_count === 'number' && entry.token_count > 0 && (
                      <Chip label={`${entry.token_count} words`} size="small" color="default" />
                    )}
                    {typeof entry.new_word_count === 'number' && entry.new_word_count > 0 && (
                      <Chip label={`${entry.new_word_count} new words`} size="small" color="primary" />
                    )}
                  </Box>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>

      <TablePagination
        component="div"
        count={filteredEntries.length}
        page={page}
        onPageChange={handleChangePage}
        rowsPerPage={rowsPerPage}
        onRowsPerPageChange={handleChangeRowsPerPage}
        rowsPerPageOptions={[10, 25, 50, 100]}
      />

      <Box sx={{ mt: 2 }}>
        <Typography variant="caption" color="text.secondary">
          Showing {paginatedEntries.length} of {filteredEntries.length} sentences
          {search && ` (filtered from ${entries.length} total)`}
        </Typography>
      </Box>
    </Box>
  );
}

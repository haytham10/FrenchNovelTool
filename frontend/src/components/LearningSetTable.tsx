'use client';

import React, { useMemo, useState } from 'react';
import {
  Box,
  Paper,
  Typography,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Chip,
} from '@mui/material';
import type { LearningSetEntry } from '@/lib/api';

interface LearningSetTableProps {
  entries: LearningSetEntry[];
  loading?: boolean;
  disablePagination?: boolean;
  externalSearchQuery?: string;
  // optional slice indices when parent wants to control visible rows
  pageSliceStart?: number;
  pageSliceEnd?: number;
}

export default function LearningSetTable({ entries, loading = false, disablePagination = false, externalSearchQuery, pageSliceStart, pageSliceEnd }: LearningSetTableProps) {
  const [page] = useState(0);
  const [rowsPerPage] = useState(25);

  // If an externalSearchQuery is provided, use it to filter the entire entries list
  const activeSearch = externalSearchQuery ?? '';

  const filteredEntries = useMemo(() => {
    if (!activeSearch.trim()) return entries;
    const query = activeSearch.toLowerCase().trim();
    return entries.filter((entry) =>
      entry.sentence_text.toLowerCase().includes(query) || String(entry.rank).includes(query)
    );
  }, [entries, activeSearch]);

  const paginatedEntries = useMemo(() => {
    // If parent supplied explicit slice indices, use them to show the visible rows
    if (typeof pageSliceStart === 'number' && typeof pageSliceEnd === 'number') {
      return filteredEntries.slice(pageSliceStart, pageSliceEnd);
    }

    if (disablePagination) return filteredEntries;
    const start = page * rowsPerPage;
    return filteredEntries.slice(start, start + rowsPerPage);
  }, [filteredEntries, page, rowsPerPage, disablePagination, pageSliceStart, pageSliceEnd]);

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
			  <TableCell align='center' width="10%">
				<Typography variant="subtitle2" fontWeight={600}>
					Words
				</Typography>
			  </TableCell>
			  <TableCell align='center' width="15%">
				<Typography variant="subtitle2" fontWeight={600}>
					New Words
				</Typography>
			  </TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {paginatedEntries.map((entry) => (
              <TableRow key={`learning-set-${entry.rank}-${entry.sentence_index ?? 'na'}`} hover>
                <TableCell>
                  <Typography sx={{ color: 'text.secondary' }} variant="body2" fontWeight={500}>
                    {entry.rank}
                  </Typography>
                </TableCell>
                <TableCell>
                  <Typography variant="body2">{entry.sentence_text}</Typography>
                </TableCell>
				<TableCell align='center'>
				  <Chip label={`${entry.token_count}w`} size="small" color="default" />
				</TableCell>
				<TableCell align='center'>
				  <Chip label={`${entry.new_word_count}w`} size="small" color="primary" />
				</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>
    </Box>
  );
}

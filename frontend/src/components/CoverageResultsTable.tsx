'use client';

/**
 * Coverage Results Table - Display word-to-sentence assignments for Coverage mode
 */
import React, { useState, useMemo } from 'react';
import {
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Typography,
  Box,
  Chip,
  IconButton,
  Tooltip,
  TextField,
  InputAdornment,
  TablePagination,
  Stack,
} from '@mui/material';
import { Search, SwapHoriz } from '@mui/icons-material';
import type { CoverageAssignment } from '@/lib/api';

interface CoverageResultsTableProps {
  assignments: CoverageAssignment[];
  onSwap?: (assignment: CoverageAssignment) => void;
  loading?: boolean;
}

export default function CoverageResultsTable({
  assignments,
  onSwap,
  loading = false,
}: CoverageResultsTableProps) {
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(25);

  // Filter assignments based on search
  const filteredAssignments = useMemo(() => {
    if (!search.trim()) return assignments;
    
    const query = search.toLowerCase().trim();
    return assignments.filter((assignment) => 
      assignment.word_key.toLowerCase().includes(query) ||
      assignment.sentence_text.toLowerCase().includes(query) ||
      assignment.word_original?.toLowerCase().includes(query)
    );
  }, [assignments, search]);

  // Paginate
  const paginatedAssignments = useMemo(() => {
    const start = page * rowsPerPage;
    return filteredAssignments.slice(start, start + rowsPerPage);
  }, [filteredAssignments, page, rowsPerPage]);

  const handleChangePage = (_event: unknown, newPage: number) => {
    setPage(newPage);
  };

  const handleChangeRowsPerPage = (event: React.ChangeEvent<HTMLInputElement>) => {
    setRowsPerPage(parseInt(event.target.value, 10));
    setPage(0);
  };

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
        <Typography variant="body2" color="text.secondary">
          Loading assignments...
        </Typography>
      </Box>
    );
  }

  if (assignments.length === 0) {
    return (
      <Paper sx={{ p: 4, textAlign: 'center' }}>
        <Typography variant="body1" color="text.secondary">
          No assignments found. The coverage run may still be processing or failed.
        </Typography>
      </Paper>
    );
  }

  return (
    <Box>
      {/* Search bar */}
      <Box sx={{ mb: 2 }}>
        <TextField
          fullWidth
          size="small"
          placeholder="Search by word or sentence..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          InputProps={{
            startAdornment: (
              <InputAdornment position="start">
                <Search fontSize="small" />
              </InputAdornment>
            ),
          }}
        />
      </Box>

      {/* Table */}
      <TableContainer component={Paper} variant="outlined">
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell width="15%">
                <Typography variant="subtitle2" fontWeight={600}>
                  Word
                </Typography>
              </TableCell>
              <TableCell width="60%">
                <Typography variant="subtitle2" fontWeight={600}>
                  Assigned Sentence
                </Typography>
              </TableCell>
              <TableCell width="10%" align="center">
                <Typography variant="subtitle2" fontWeight={600}>
                  Score
                </Typography>
              </TableCell>
              <TableCell width="10%" align="center">
                <Typography variant="subtitle2" fontWeight={600}>
                  Index
                </Typography>
              </TableCell>
              <TableCell width="5%" align="center">
                <Typography variant="subtitle2" fontWeight={600}>
                  Actions
                </Typography>
              </TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {paginatedAssignments.map((assignment) => (
              <TableRow key={assignment.id} hover>
                <TableCell>
                  <Stack spacing={0.5}>
                    <Typography variant="body2" fontWeight={500}>
                      {assignment.word_key}
                    </Typography>
                    {assignment.word_original && assignment.word_original !== assignment.word_key && (
                      <Typography variant="caption" color="text.secondary">
                        ({assignment.word_original})
                      </Typography>
                    )}
                    {assignment.manual_edit && (
                      <Chip label="Manual" size="small" color="warning" sx={{ width: 'fit-content' }} />
                    )}
                  </Stack>
                </TableCell>
                <TableCell>
                  <Typography variant="body2">
                    {assignment.sentence_text}
                  </Typography>
                  {assignment.matched_surface && (
                    <Typography variant="caption" color="text.secondary" display="block">
                      Matched: {assignment.matched_surface}
                    </Typography>
                  )}
                </TableCell>
                <TableCell align="center">
                  <Typography variant="body2">
                    {assignment.sentence_score ? assignment.sentence_score.toFixed(2) : 'N/A'}
                  </Typography>
                </TableCell>
                <TableCell align="center">
                  <Typography variant="body2">
                    {assignment.sentence_index}
                  </Typography>
                </TableCell>
                <TableCell align="center">
                  {onSwap && (
                    <Tooltip title="Swap to different sentence">
                      <IconButton
                        size="small"
                        onClick={() => onSwap(assignment)}
                      >
                        <SwapHoriz fontSize="small" />
                      </IconButton>
                    </Tooltip>
                  )}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>

      {/* Pagination */}
      <TablePagination
        component="div"
        count={filteredAssignments.length}
        page={page}
        onPageChange={handleChangePage}
        rowsPerPage={rowsPerPage}
        onRowsPerPageChange={handleChangeRowsPerPage}
        rowsPerPageOptions={[10, 25, 50, 100]}
      />

      {/* Summary */}
      <Box sx={{ mt: 2 }}>
        <Typography variant="caption" color="text.secondary">
          Showing {paginatedAssignments.length} of {filteredAssignments.length} assignments
          {search && ` (filtered from ${assignments.length} total)`}
        </Typography>
      </Box>
    </Box>
  );
}

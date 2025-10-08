'use client';

/**
 * Filter Results Table - Display ranked sentences for Filter mode
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
  LinearProgress,
} from '@mui/material';
import { Search, Block, Star } from '@mui/icons-material';
import type { CoverageAssignment } from '@/lib/api';

interface FilterResultsTableProps {
  assignments: CoverageAssignment[];
  onExclude?: (assignment: CoverageAssignment) => void;
  loading?: boolean;
}

export default function FilterResultsTable({
  assignments,
  onExclude,
  loading = false,
}: FilterResultsTableProps) {
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(10);

  // Sort by score descending and filter
  const sortedAndFilteredAssignments = useMemo(() => {
    let filtered = [...assignments].sort((a, b) => 
      (b.sentence_score || 0) - (a.sentence_score || 0)
    );
    
    if (search.trim()) {
      const query = search.toLowerCase().trim();
      filtered = filtered.filter((assignment) => 
        assignment.sentence_text.toLowerCase().includes(query)
      );
    }
    
    return filtered;
  }, [assignments, search]);

  // Paginate
  const paginatedAssignments = useMemo(() => {
    const start = page * rowsPerPage;
    return sortedAndFilteredAssignments.slice(start, start + rowsPerPage);
  }, [sortedAndFilteredAssignments, page, rowsPerPage]);

  const handleChangePage = (_event: unknown, newPage: number) => {
    setPage(newPage);
  };

  const handleChangeRowsPerPage = (event: React.ChangeEvent<HTMLInputElement>) => {
    setRowsPerPage(parseInt(event.target.value, 10));
    setPage(0);
  };

  // Calculate sentence stats
  interface SentenceStats {
    avgWordCount: string;
    avgScore: string; // scaled to 5-point display
    minScore: string; // scaled
    maxScore: string; // scaled
    minScoreRaw: number;
    maxScoreRaw: number;
  }

  const sentenceStats = useMemo<SentenceStats | null>(() => {
    if (assignments.length === 0) return null;
    
    const wordCounts = assignments.map(a => 
      a.sentence_text.split(/\s+/).length
    );
    
    const avgWordCount = wordCounts.reduce((a, b) => a + b, 0) / wordCounts.length;
    const scores = assignments.map(a => a.sentence_score || 0);
    const avgScore = scores.reduce((a, b) => a + b, 0) / scores.length;

    // Keep raw min/max for visualization, but display scores scaled to 5.0
    const minRaw = Math.min(...scores);
    const maxRaw = Math.max(...scores);

    return {
      avgWordCount: avgWordCount.toFixed(1),
      // display on a 5-point scale with one decimal
      avgScore: (avgScore * 5).toFixed(1),
      minScore: (minRaw * 5).toFixed(1),
      maxScore: (maxRaw * 5).toFixed(1),
      // raw values for percent calculation
      minScoreRaw: minRaw,
      maxScoreRaw: maxRaw,
    };
  }, [assignments]);

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
        <Typography variant="body2" color="text.secondary">
          Loading results...
        </Typography>
      </Box>
    );
  }

  if (assignments.length === 0) {
    return (
      <Paper sx={{ p: 4, textAlign: 'center' }}>
        <Typography variant="body1" color="text.secondary">
          No sentences found. The filter run may still be processing or no sentences met the criteria.
        </Typography>
      </Paper>
    );
  }

  return (
    <Box>
      {/* Stats Summary */}
      {sentenceStats && (
        <Paper variant="outlined" sx={{ p: 2, mb: 2 }}>
          <Stack direction="row" spacing={3} flexWrap="wrap">
            <Box>
              <Typography variant="caption" color="text.secondary" display="block">
                Total Sentences
              </Typography>
              <Typography variant="h6" fontWeight={600}>
                {assignments.length}
              </Typography>
            </Box>
            <Box>
              <Typography variant="caption" color="text.secondary" display="block">
                Avg. Length
              </Typography>
              <Typography variant="h6" fontWeight={600}>
                {sentenceStats.avgWordCount} words
              </Typography>
            </Box>
            <Box>
              <Typography variant="caption" color="text.secondary" display="block">
                Avg. Score
              </Typography>
              <Typography variant="h6" fontWeight={600}>
                {sentenceStats.avgScore}
              </Typography>
            </Box>
            <Box>
              <Typography variant="caption" color="text.secondary" display="block">
                Score Range
              </Typography>
              <Typography variant="h6" fontWeight={600}>
                {sentenceStats.minScore} - {sentenceStats.maxScore}
              </Typography>
            </Box>
          </Stack>
        </Paper>
      )}

      {/* Search bar */}
      <Box sx={{ mb: 2 }}>
        <TextField
          fullWidth
          size="small"
          placeholder="Search sentences..."
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
              <TableCell width="8%">
                <Typography variant="subtitle2" fontWeight={600}>
                  Rank
                </Typography>
              </TableCell>
              <TableCell width="65%">
                <Typography variant="subtitle2" fontWeight={600}>
                  Sentence
                </Typography>
              </TableCell>
              <TableCell width="10%" align="center">
                <Typography variant="subtitle2" fontWeight={600}>
                  Score
                </Typography>
              </TableCell>
              <TableCell width="10%" align="center">
                <Typography variant="subtitle2" fontWeight={600}>
                  Length
                </Typography>
              </TableCell>
              <TableCell width="7%" align="center">
                <Typography variant="subtitle2" fontWeight={600}>
                  Actions
                </Typography>
              </TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {paginatedAssignments.map((assignment, idx) => {
              const wordCount = assignment.sentence_text.split(/\s+/).length;
              const rank = page * rowsPerPage + idx + 1;
              const score = assignment.sentence_score || 0;
          const scorePercent = sentenceStats
           ? ((score - sentenceStats.minScoreRaw) /
             ((sentenceStats.maxScoreRaw - sentenceStats.minScoreRaw) || 1)) * 100
           : 0;
              
              return (
                <TableRow key={assignment.id} hover>
                  <TableCell>
                    <Stack direction="row" alignItems="center" spacing={0.5}>
                      <Typography variant="body2" fontWeight={500}>
                        #{rank}
                      </Typography>
                      {rank <= 10 && (
                        <Star fontSize="small" color="warning" />
                      )}
                    </Stack>
                  </TableCell>
                  <TableCell>
                    <Typography variant="body2">
                      {assignment.sentence_text}
                    </Typography>
                  </TableCell>
                  <TableCell align="center">
                    <Box>
                      <Typography variant="body2" fontWeight={500}>
                        {(score * 5).toFixed(1)}
                      </Typography>
                      <LinearProgress 
                        variant="determinate" 
                        value={scorePercent} 
                        sx={{ mt: 0.5, height: 4, borderRadius: 2 }}
                      />
                    </Box>
                  </TableCell>
                  <TableCell align="center">
                    <Chip 
                      label={`${wordCount}w`} 
                      size="small"
                      color={wordCount === 4 ? 'success' : wordCount === 3 ? 'primary' : 'default'}
                    />
                  </TableCell>
                  <TableCell align="center">
                    {onExclude && (
                      <Tooltip title="Exclude from results">
                        <IconButton
                          size="small"
                          onClick={() => onExclude(assignment)}
                        >
                          <Block fontSize="small" />
                        </IconButton>
                      </Tooltip>
                    )}
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      </TableContainer>

      {/* Pagination */}
      <TablePagination
        component="div"
        count={sortedAndFilteredAssignments.length}
        page={page}
        onPageChange={handleChangePage}
        rowsPerPage={rowsPerPage}
        onRowsPerPageChange={handleChangeRowsPerPage}
        rowsPerPageOptions={[10, 25, 50, 100]}
      />
    </Box>
  );
}

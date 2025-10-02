'use client';

import React, { useEffect, useMemo, useState } from 'react';
import { Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Paper, TableSortLabel, TextField, Box, CircularProgress, Typography } from '@mui/material';
import { styled } from '@mui/material/styles';
import { useSnackbar } from 'notistack';
import Link from 'next/link';
import { fetchHistory, getApiErrorMessage } from '@/lib/api';
import type { HistoryEntry } from '@/lib/types';

type Order = 'asc' | 'desc';

const StyledTableCell = styled(TableCell)(({ theme }) => ({
  [`&.MuiTableCell-head`]: {
    backgroundColor: theme.palette.primary.main,
    color: theme.palette.common.white,
    fontWeight: 'bold',
  },
  [`&.MuiTableCell-body`]: {
    fontSize: 14,
  },
}));

const StyledTableRow = styled(TableRow)(({ theme }) => ({
  '&:nth-of-type(odd)': {
    backgroundColor: theme.palette.action.hover,
  },
  // hide last border
  '&:last-child td, &:last-child th': {
    border: 0,
  },
}));

export default function HistoryTable() {
  const [history, setHistory] = useState<HistoryEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [order, setOrder] = useState<Order>('desc');
  const [orderBy, setOrderBy] = useState<keyof HistoryEntry>('uploaded_at');
  const [filter, setFilter] = useState<string>('');
  const { enqueueSnackbar } = useSnackbar();

  useEffect(() => {
    const loadHistory = async () => {
      try {
        const data = await fetchHistory();
        setHistory(data);
      } catch (error) {
        const errorMessage = getApiErrorMessage(error, 'Failed to fetch history.');
        enqueueSnackbar(errorMessage, { variant: 'error' });
        setError(errorMessage);
      } finally {
        setLoading(false);
      }
    };
    loadHistory();
  }, [enqueueSnackbar]);

  const handleRequestSort = (
    _event: React.MouseEvent<unknown>,
    property: keyof HistoryEntry,
  ) => {
    const isAsc = orderBy === property && order === 'asc';
    setOrder(isAsc ? 'desc' : 'asc');
    setOrderBy(property);
  };

  const sortedHistory = useMemo(() => {
    const comparator = (a: HistoryEntry, b: HistoryEntry) => {
      if (orderBy === 'uploaded_at') {
        return order === 'asc' ? new Date(a.uploaded_at).getTime() - new Date(b.uploaded_at).getTime() : new Date(b.uploaded_at).getTime() - new Date(a.uploaded_at).getTime();
      } else if (orderBy === 'sentence_count') {
        return order === 'asc' ? a.sentence_count - b.sentence_count : b.sentence_count - a.sentence_count;
      } else if (orderBy === 'filename') {
        return order === 'asc' ? a.filename.localeCompare(b.filename) : b.filename.localeCompare(a.filename);
      } else if (orderBy === 'spreadsheet_url') {
        const aUrl = a.spreadsheet_url || '';
        const bUrl = b.spreadsheet_url || '';
        return order === 'asc' ? aUrl.localeCompare(bUrl) : bUrl.localeCompare(aUrl);
      } else if (orderBy === 'error_message') {
        const aError = a.error_message || '';
        const bError = b.error_message || '';
        return order === 'asc' ? aError.localeCompare(bError) : bError.localeCompare(aError);
      } else if (orderBy === 'status') {
        return order === 'asc' ? a.status.localeCompare(b.status) : b.status.localeCompare(a.status);
      }
      return 0;
    };
    const stabilizedThis = [...history];
    stabilizedThis.sort(comparator);
    return stabilizedThis;
  }, [history, order, orderBy]);

  const filteredHistory = useMemo(() => {
    if (!filter) return sortedHistory;
    return sortedHistory.filter(entry =>
      entry.filename.toLowerCase().includes(filter.toLowerCase()) ||
      (entry.spreadsheet_url && entry.spreadsheet_url.toLowerCase().includes(filter.toLowerCase())) ||
      (entry.error_message && entry.error_message.toLowerCase().includes(filter.toLowerCase()))
    );
  }, [sortedHistory, filter]);

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="200px">
        <CircularProgress />
        <Typography variant="body1" color="textSecondary" ml={2}>Loading history...</Typography>
      </Box>
    );
  }

  if (error) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="200px">
        <Typography variant="body1" color="error">Error: {error}</Typography>
      </Box>
    );
  }

  return (
    <Box>
      <TextField
        label="Filter history"
        variant="outlined"
        fullWidth
        value={filter}
        onChange={(e) => setFilter(e.target.value)}
        sx={{ mb: 2 }}
      />
      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow>
              <StyledTableCell>
                <TableSortLabel
                  active={orderBy === 'uploaded_at'}
                  direction={orderBy === 'uploaded_at' ? order : 'asc'}
                  onClick={(event) => handleRequestSort(event, 'uploaded_at')}
                >
                  Timestamp
                </TableSortLabel>
              </StyledTableCell>
              <StyledTableCell>
                <TableSortLabel
                  active={orderBy === 'filename'}
                  direction={orderBy === 'filename' ? order : 'asc'}
                  onClick={(event) => handleRequestSort(event, 'filename')}
                >
                  Filename
                </TableSortLabel>
              </StyledTableCell>
              <StyledTableCell>
                <TableSortLabel
                  active={orderBy === 'sentence_count'}
                  direction={orderBy === 'sentence_count' ? order : 'asc'}
                  onClick={(event) => handleRequestSort(event, 'sentence_count')}
                >
                  Sentences
                </TableSortLabel>
              </StyledTableCell>
              <StyledTableCell>
                <TableSortLabel
                  active={orderBy === 'spreadsheet_url'}
                  direction={orderBy === 'spreadsheet_url' ? order : 'asc'}
                  onClick={(event) => handleRequestSort(event, 'spreadsheet_url')}
                >
                  Spreadsheet URL
                </TableSortLabel>
              </StyledTableCell>
              <StyledTableCell>
                <TableSortLabel
                  active={orderBy === 'error_message'}
                  direction={orderBy === 'error_message' ? order : 'asc'}
                  onClick={(event) => handleRequestSort(event, 'error_message')}
                >
                  Error
                </TableSortLabel>
              </StyledTableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {filteredHistory.map((entry) => (
              <StyledTableRow key={entry.id}>
                <StyledTableCell>{new Date(entry.uploaded_at).toLocaleString()}</StyledTableCell>
                <StyledTableCell>{entry.filename}</StyledTableCell>
                <StyledTableCell>{entry.sentence_count}</StyledTableCell>
                <StyledTableCell>
                  {entry.spreadsheet_url ? (
                    <Link href={entry.spreadsheet_url} target="_blank" rel="noopener noreferrer">
                      View Sheet
                    </Link>
                  ) : (
                    'N/A'
                  )}
                </StyledTableCell>
                <StyledTableCell sx={{ color: 'error.main' }}>
                  {entry.error_message || 'N/A'}
                </StyledTableCell>
              </StyledTableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>
    </Box>
  );
}

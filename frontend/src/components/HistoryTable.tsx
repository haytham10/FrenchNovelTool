'use client';

import React, { useEffect, useMemo, useState } from 'react';
import { Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Paper, TableSortLabel, TextField, Box, CircularProgress, Typography, Tooltip } from '@mui/material';
import { styled } from '@mui/material/styles';
import { useSnackbar } from 'notistack';
import Link from 'next/link';
import { fetchHistory, getApiErrorMessage } from '@/lib/api';
import type { HistoryEntry } from '@/lib/types';
import { getHistoryStatus } from '@/lib/types';
import { useDebounce } from '@/lib/hooks';
import Icon from './Icon';
import IconButton from './IconButton';
import { CheckCircle, XCircle, Loader2, RefreshCw, Copy, Eye } from 'lucide-react';

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
  const [orderBy, setOrderBy] = useState<keyof HistoryEntry>('timestamp');
  const [filter, setFilter] = useState<string>('');
  const debouncedFilter = useDebounce(filter, 300);
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
      if (orderBy === 'timestamp') {
        return order === 'asc' ? new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime() : new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime();
      } else if (orderBy === 'processed_sentences_count') {
        return order === 'asc' ? a.processed_sentences_count - b.processed_sentences_count : b.processed_sentences_count - a.processed_sentences_count;
      } else if (orderBy === 'original_filename') {
        return order === 'asc' ? a.original_filename.localeCompare(b.original_filename) : b.original_filename.localeCompare(a.original_filename);
      } else if (orderBy === 'spreadsheet_url') {
        const aUrl = a.spreadsheet_url || '';
        const bUrl = b.spreadsheet_url || '';
        return order === 'asc' ? aUrl.localeCompare(bUrl) : bUrl.localeCompare(aUrl);
      } else if (orderBy === 'error_message') {
        const aError = a.error_message || '';
        const bError = b.error_message || '';
        return order === 'asc' ? aError.localeCompare(bError) : bError.localeCompare(aError);
      }
      return 0;
    };
    const stabilizedThis = [...history];
    stabilizedThis.sort(comparator);
    return stabilizedThis;
  }, [history, order, orderBy]);

  const filteredHistory = useMemo(() => {
    if (!debouncedFilter) return sortedHistory;
    return sortedHistory.filter(entry =>
      entry.original_filename.toLowerCase().includes(debouncedFilter.toLowerCase()) ||
      (entry.spreadsheet_url && entry.spreadsheet_url.toLowerCase().includes(debouncedFilter.toLowerCase())) ||
      (entry.error_message && entry.error_message.toLowerCase().includes(debouncedFilter.toLowerCase()))
    );
  }, [sortedHistory, debouncedFilter]);

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
              <StyledTableCell>Status</StyledTableCell>
              <StyledTableCell>
                <TableSortLabel
                  active={orderBy === 'timestamp'}
                  direction={orderBy === 'timestamp' ? order : 'asc'}
                  onClick={(event) => handleRequestSort(event, 'timestamp')}
                >
                  Timestamp
                </TableSortLabel>
              </StyledTableCell>
              <StyledTableCell>
                <TableSortLabel
                  active={orderBy === 'original_filename'}
                  direction={orderBy === 'original_filename' ? order : 'asc'}
                  onClick={(event) => handleRequestSort(event, 'original_filename')}
                >
                  Filename
                </TableSortLabel>
              </StyledTableCell>
              <StyledTableCell>
                <TableSortLabel
                  active={orderBy === 'processed_sentences_count'}
                  direction={orderBy === 'processed_sentences_count' ? order : 'asc'}
                  onClick={(event) => handleRequestSort(event, 'processed_sentences_count')}
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
              <StyledTableCell>Actions</StyledTableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {filteredHistory.map((entry) => {
              const status = getHistoryStatus(entry);
              return (
                <StyledTableRow key={entry.id}>
                  <StyledTableCell>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      {status === 'success' && <Icon icon={CheckCircle} color="success" fontSize="small" />}
                      {status === 'failed' && <Icon icon={XCircle} color="error" fontSize="small" />}
                      {status === 'processing' && <Icon icon={Loader2} color="primary" fontSize="small" />}
                      <Typography variant="body2" sx={{ 
                        color: status === 'success' ? 'success.main' : status === 'failed' ? 'error.main' : 'primary.main',
                        fontWeight: 500,
                        textTransform: 'capitalize'
                      }}>
                        {status}
                      </Typography>
                    </Box>
                  </StyledTableCell>
                  <StyledTableCell>{new Date(entry.timestamp).toLocaleString()}</StyledTableCell>
                  <StyledTableCell>{entry.original_filename}</StyledTableCell>
                  <StyledTableCell>{entry.processed_sentences_count}</StyledTableCell>
                  <StyledTableCell>
                    {entry.spreadsheet_url ? (
                      <Link href={entry.spreadsheet_url} target="_blank" rel="noopener noreferrer">
                        View Sheet
                      </Link>
                    ) : (
                      'N/A'
                    )}
                  </StyledTableCell>
                  <StyledTableCell>
                    {entry.error_message ? (
                      <Box>
                        <Typography variant="body2" color="error.main" sx={{ fontWeight: 500 }}>
                          {entry.error_message}
                        </Typography>
                        {entry.error_code && (
                          <Typography variant="caption" color="text.secondary">
                            Code: {entry.error_code}
                          </Typography>
                        )}
                        {entry.failed_step && (
                          <Typography variant="caption" color="text.secondary" display="block">
                            Failed at: {entry.failed_step}
                          </Typography>
                        )}
                      </Box>
                    ) : (
                      'N/A'
                    )}
                  </StyledTableCell>
                  <StyledTableCell>
                    <Box sx={{ display: 'flex', gap: 0.5 }}>
                      {status === 'failed' && entry.failed_step && (
                        <Tooltip title="Retry from failed step">
                          <IconButton 
                            size="small" 
                            color="primary"
                            onClick={() => enqueueSnackbar('Retry functionality coming soon', { variant: 'info' })}
                            aria-label="Retry processing"
                          >
                            <Icon icon={RefreshCw} fontSize="small" />
                          </IconButton>
                        </Tooltip>
                      )}
                      {entry.settings && (
                        <Tooltip title="Duplicate with same settings">
                          <IconButton 
                            size="small"
                            onClick={() => enqueueSnackbar('Duplicate functionality coming soon', { variant: 'info' })}
                            aria-label="Duplicate run"
                          >
                            <Icon icon={Copy} fontSize="small" />
                          </IconButton>
                        </Tooltip>
                      )}
                      <Tooltip title="View details">
                        <IconButton 
                          size="small"
                          onClick={() => enqueueSnackbar(`Details for ${entry.original_filename}`, { variant: 'info' })}
                          aria-label="View details"
                        >
                          <Icon icon={Eye} fontSize="small" />
                        </IconButton>
                      </Tooltip>
                    </Box>
                  </StyledTableCell>
                </StyledTableRow>
              );
            })}
          </TableBody>
        </Table>
      </TableContainer>
    </Box>
  );
}

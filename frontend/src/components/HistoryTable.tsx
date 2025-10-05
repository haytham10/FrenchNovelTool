'use client';

import React, { useMemo, useState, useEffect } from 'react';
import { Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Paper, TableSortLabel, TextField, Box, CircularProgress, Typography, Tooltip, TablePagination, Chip, Stack, Drawer, Divider, Button } from '@mui/material';
import { styled } from '@mui/material/styles';
import { useSnackbar } from 'notistack';
import Link from 'next/link';
import { useHistory, useRetryHistoryEntry, useExportToSheet } from '@/lib/queries';
import type { HistoryEntry } from '@/lib/types';
import { getHistoryStatus } from '@/lib/types';
import { useDebounce } from '@/lib/hooks';
import Icon from './Icon';
import IconButton from './IconButton';
import { CheckCircle, XCircle, Loader2, RefreshCw, Eye, Filter, Send, Calendar, Copy, ExternalLink, RotateCw } from 'lucide-react';
import ExportDialog from './ExportDialog';
import { useRouter } from 'next/navigation';
import HistoryDetailDialog from './HistoryDetailDialog';

type Order = 'asc' | 'desc';
type StatusFilter = 'all' | 'complete' | 'exported' | 'failed' | 'processing';

const StyledTableCell = styled(TableCell)(({ theme }) => ({
  [`&.MuiTableCell-head`]: {
    backgroundColor: theme.palette.primary.main,
    color: theme.palette.common.white,
    fontWeight: 'bold',
  },
  [`&.MuiTableCell-body`]: {
    fontSize: 14,
    // Improve dark mode contrast
    color: theme.palette.mode === 'dark' 
      ? 'rgba(255, 255, 255, 0.87)' 
      : theme.palette.text.primary,
    // Prevent overflow and remove scrollbars: truncate with ellipsis
    whiteSpace: 'nowrap',
    overflow: 'hidden',
    textOverflow: 'ellipsis',
    // Better spacing for body cells
    padding: '12px 16px',
    verticalAlign: 'middle',
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
  cursor: 'pointer',
  transition: 'all 0.2s ease',
  '&:hover': {
    backgroundColor: theme.palette.mode === 'dark' 
      ? 'rgba(255, 255, 255, 0.08)' 
      : 'rgba(0, 0, 0, 0.04)',
    transform: 'scale(1.002)',
  },
  '&:focus-visible': {
    outline: `2px solid ${theme.palette.primary.main}`,
    outlineOffset: '2px',
  },
}));

// Timestamp-specific cell: allow enough space and prevent truncation for dates
const TimestampCell = styled(StyledTableCell)(() => ({
  minWidth: 160,
  maxWidth: 240,
  whiteSpace: 'nowrap',
  overflow: 'visible',
  textOverflow: 'clip',
}));

// Add keyframes for spinning animation
const globalStyles = `
  @keyframes spin {
    from {
      transform: rotate(0deg);
    }
    to {
      transform: rotate(360deg);
    }
  }
`;

export default function HistoryTable() {
  const [order, setOrder] = useState<Order>('desc');
  const [orderBy, setOrderBy] = useState<keyof HistoryEntry>('timestamp');
  const [filter, setFilter] = useState<string>('');
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('all');
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(10);
  const [detailsDrawerOpen, setDetailsDrawerOpen] = useState(false);
  const [selectedEntry] = useState<HistoryEntry | null>(null);
  const [detailDialogOpen, setDetailDialogOpen] = useState(false);
  const [detailEntryId, setDetailEntryId] = useState<number | null>(null);
  const [dateRangeStart, setDateRangeStart] = useState<string>('');
  const [dateRangeEnd, setDateRangeEnd] = useState<string>('');
  const [exportDialogOpen, setExportDialogOpen] = useState(false);
  const [entryToExport, setEntryToExport] = useState<HistoryEntry | null>(null);
  const debouncedFilter = useDebounce(filter, 300);
  const { enqueueSnackbar } = useSnackbar();
  const router = useRouter();
  
  // Use React Query for data fetching
  const { data: history = [], isLoading: loading, error, refetch } = useHistory();
  const retryMutation = useRetryHistoryEntry();
  const exportMutation = useExportToSheet();

  // Auto-refresh when there are processing entries
  useEffect(() => {
    const hasProcessing = history.some(entry => getHistoryStatus(entry) === 'processing');
    if (!hasProcessing) return;

    const interval = setInterval(() => {
      refetch();
    }, 10000); // Refresh every 10 seconds when processing

    return () => clearInterval(interval);
  }, [history, refetch]);

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
    let filtered = sortedHistory;
    
    // Apply status filter
    if (statusFilter !== 'all') {
      filtered = filtered.filter(entry => getHistoryStatus(entry) === statusFilter);
    }
    
    // Apply date range filter
    if (dateRangeStart) {
      const startDate = new Date(dateRangeStart);
      filtered = filtered.filter(entry => new Date(entry.timestamp) >= startDate);
    }
    if (dateRangeEnd) {
      const endDate = new Date(dateRangeEnd);
      endDate.setHours(23, 59, 59, 999); // Include the entire end day
      filtered = filtered.filter(entry => new Date(entry.timestamp) <= endDate);
    }
    
    // Apply text filter
    if (!debouncedFilter) return filtered;
    return filtered.filter(entry =>
      entry.original_filename.toLowerCase().includes(debouncedFilter.toLowerCase()) ||
      (entry.spreadsheet_url && entry.spreadsheet_url.toLowerCase().includes(debouncedFilter.toLowerCase())) ||
      (entry.error_message && entry.error_message.toLowerCase().includes(debouncedFilter.toLowerCase()))
    );
  }, [sortedHistory, debouncedFilter, statusFilter, dateRangeStart, dateRangeEnd]);

  const handleChangePage = (_event: unknown, newPage: number) => {
    setPage(newPage);
  };

  const handleChangeRowsPerPage = (event: React.ChangeEvent<HTMLInputElement>) => {
    setRowsPerPage(parseInt(event.target.value, 10));
    setPage(0);
  };

  const handleViewDetails = (entry: HistoryEntry) => {
    setDetailEntryId(entry.id);
    setDetailDialogOpen(true);
  };

  const handleSendToSheets = (entry: HistoryEntry) => {
    setEntryToExport(entry);
    setExportDialogOpen(true);
  };

  const handleExport = async () => {
    if (!entryToExport) return;
    
    try {
      // For history entries, we don't have the sentences stored
      // In a real implementation, you would either:
      // 1. Store sentences in the history entry
      // 2. Re-process the file
      // For now, we'll show a message
      enqueueSnackbar('This feature requires storing processed sentences. Please reprocess the file to export.', { variant: 'info' });
      setExportDialogOpen(false);
    } catch {
      // Error is handled by the mutation
    }
  };

  const handleRetry = async (entry: HistoryEntry) => {
    try {
      const result = await retryMutation.mutateAsync(entry.id);
      enqueueSnackbar(result.message, { variant: 'info' });
      
      // Navigate to home with settings
      if (result.settings) {
        // Store settings in localStorage for the home page to use
        localStorage.setItem('retrySettings', JSON.stringify(result.settings));
        router.push('/');
      }
    } catch {
      // Error handled by mutation
    }
  };

  // Duplicate functionality removed from UI; keep code removed to avoid unused imports

  const handleCopyUrl = async (url: string) => {
    try {
      await navigator.clipboard.writeText(url);
      enqueueSnackbar('Link copied to clipboard', { variant: 'success' });
    } catch {
      enqueueSnackbar('Failed to copy link', { variant: 'error' });
    }
  };

  const handleClearAllFilters = () => {
    setFilter('');
    setStatusFilter('all');
    setDateRangeStart('');
    setDateRangeEnd('');
  };

  const hasActiveFilters = filter || statusFilter !== 'all' || dateRangeStart || dateRangeEnd;

  const setQuickDateRange = (days: number) => {
    const end = new Date();
    const start = new Date();
    start.setDate(start.getDate() - days);
    setDateRangeStart(start.toISOString().split('T')[0]);
    setDateRangeEnd(end.toISOString().split('T')[0]);
  };

  // Calculate summary statistics
  const summaryStats = useMemo(() => {
    const filtered = dateRangeStart || dateRangeEnd ? filteredHistory : history;
    return {
      total: filtered.length,
      complete: filtered.filter(e => getHistoryStatus(e) === 'complete').length,
      exported: filtered.filter(e => getHistoryStatus(e) === 'exported').length,
      failed: filtered.filter(e => getHistoryStatus(e) === 'failed').length,
      processing: filtered.filter(e => getHistoryStatus(e) === 'processing').length,
    };
  }, [filteredHistory, history, dateRangeStart, dateRangeEnd]);

  const hasProcessing = summaryStats.processing > 0;

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Focus search on '/' key
      if (e.key === '/' && !e.ctrlKey && !e.metaKey && !e.altKey) {
        const target = e.target as HTMLElement;
        // Don't trigger if already in an input
        if (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA') return;
        e.preventDefault();
        document.querySelector<HTMLInputElement>('input[aria-label="Search history entries"]')?.focus();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

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
      <Box display="flex" flexDirection="column" justifyContent="center" alignItems="center" minHeight="200px" gap={2}>
        <Typography variant="body1" color="error">Failed to load history</Typography>
        <IconButton onClick={() => refetch()} title="Retry">
          <Icon icon={RefreshCw} />
        </IconButton>
      </Box>
    );
  }

  return (
    <Box>
      {/* Add global styles for animations */}
      <style>{globalStyles}</style>
      
      {/* Summary Statistics Bar */}
      <Paper sx={{ p: 2.5, mb: 3, bgcolor: 'background.default', border: 1, borderColor: 'divider' }}>
        <Stack direction="row" spacing={3} flexWrap="wrap" alignItems="center" justifyContent="space-between">
          <Stack direction="row" spacing={3} flexWrap="wrap">
            <Box>
              <Typography variant="caption" color="text.secondary" display="block">
                Total Processed
              </Typography>
              <Typography variant="h6" fontWeight="bold">
                {summaryStats.total}
              </Typography>
            </Box>
            <Box>
              <Typography variant="caption" color="text.secondary" display="block">
                Exported
              </Typography>
              <Typography variant="h6" fontWeight="bold" sx={{ color: '#9c27b0' }}>
                {summaryStats.exported}
              </Typography>
            </Box>
            <Box>
              <Typography variant="caption" color="text.secondary" display="block">
                Complete
              </Typography>
              <Typography variant="h6" fontWeight="bold" color="success.main">
                {summaryStats.complete}
              </Typography>
            </Box>
            <Box>
              <Typography variant="caption" color="text.secondary" display="block">
                Failed
              </Typography>
              <Typography variant="h6" fontWeight="bold" color="error.main">
                {summaryStats.failed}
              </Typography>
            </Box>
            {summaryStats.processing > 0 && (
              <Box>
                <Typography variant="caption" color="text.secondary" display="block">
                  Processing
                </Typography>
                <Typography variant="h6" fontWeight="bold" color="primary.main">
                  {summaryStats.processing}
                </Typography>
              </Box>
            )}
          </Stack>
          <Stack direction="row" gap={1} alignItems="center">
            {hasProcessing && (
              <Tooltip title="Auto-refreshing every 10 seconds while processing">
                <Chip
                  icon={<Icon icon={Loader2} fontSize="small" />}
                  label="Auto-refresh"
                  size="small"
                  color="primary"
                  sx={{
                    '& .MuiChip-icon': {
                      animation: 'spin 1s linear infinite'
                    }
                  }}
                />
              </Tooltip>
            )}
            <Tooltip title="Refresh history">
              <IconButton onClick={() => refetch()} size="small" aria-label="Refresh history">
                <Icon icon={RotateCw} fontSize="small" />
              </IconButton>
            </Tooltip>
          </Stack>
        </Stack>
      </Paper>

      {/* Active Filters Display */}
      {hasActiveFilters && (
        <Box sx={{ mb: 2 }}>
          <Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap">
            <Typography variant="body2" color="text.secondary">
              Active filters:
            </Typography>
            {filter && (
              <Chip
                label={`Search: "${filter}"`}
                size="small"
                onDelete={() => setFilter('')}
              />
            )}
            {statusFilter !== 'all' && (
              <Chip
                label={`Status: ${statusFilter}`}
                size="small"
                onDelete={() => setStatusFilter('all')}
                sx={{ textTransform: 'capitalize' }}
              />
            )}
            {(dateRangeStart || dateRangeEnd) && (
              <Chip
                label={`Date: ${dateRangeStart || '...'} to ${dateRangeEnd || '...'}`}
                size="small"
                onDelete={() => {
                  setDateRangeStart('');
                  setDateRangeEnd('');
                }}
              />
            )}
            <Button
              size="small"
              variant="text"
              onClick={handleClearAllFilters}
              sx={{ ml: 1 }}
            >
              Clear all
            </Button>
          </Stack>
        </Box>
      )}

      {/* Search and Filter Controls */}
      <Paper sx={{ p: 2.5, mb: 3, bgcolor: 'background.default', border: 1, borderColor: 'divider' }}>
        <Stack spacing={2}>
          {/* Search */}
          <TextField
            label="Search history"
            variant="outlined"
            fullWidth
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            placeholder="Search by filename, URL, or error message... (Press / to focus)"
            aria-label="Search history entries"
            size="small"
          />
          
          {/* Filters Row */}
          <Stack direction="row" spacing={2} flexWrap="wrap" alignItems="center">
            {/* Status Filter */}
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, flexWrap: 'wrap' }}>
              <Icon icon={Filter} fontSize="small" />
              <Typography variant="body2" color="text.secondary" sx={{ mr: 0.5 }}>
                Status:
              </Typography>
              <Stack direction="row" spacing={0.5} sx={{ flexWrap: 'wrap', gap: 0.5 }}>
                <Chip
                  label={`All (${history.length})`}
                  onClick={() => setStatusFilter('all')}
                  color={statusFilter === 'all' ? 'primary' : 'default'}
                  variant={statusFilter === 'all' ? 'filled' : 'outlined'}
                  size="small"
                />
                <Chip
                  label={`Complete (${summaryStats.complete})`}
                  onClick={() => setStatusFilter('complete')}
                  color={statusFilter === 'complete' ? 'success' : 'default'}
                  variant={statusFilter === 'complete' ? 'filled' : 'outlined'}
                  icon={<Icon icon={CheckCircle} fontSize="small" />}
                  size="small"
                />
                <Chip
                  label={`Exported (${summaryStats.exported})`}
                  onClick={() => setStatusFilter('exported')}
                  sx={{
                    ...(statusFilter === 'exported' && {
                      bgcolor: '#9c27b0',
                      color: '#ffffff',
                      '& .MuiChip-icon': { color: '#ffffff' }
                    })
                  }}
                  variant={statusFilter === 'exported' ? 'filled' : 'outlined'}
                  icon={<Icon icon={Send} fontSize="small" />}
                  size="small"
                />
                <Chip
                  label={`Failed (${summaryStats.failed})`}
                  onClick={() => setStatusFilter('failed')}
                  color={statusFilter === 'failed' ? 'error' : 'default'}
                  variant={statusFilter === 'failed' ? 'filled' : 'outlined'}
                  icon={<Icon icon={XCircle} fontSize="small" />}
                  size="small"
                />
                {summaryStats.processing > 0 && (
                  <Chip
                    label={`Processing (${summaryStats.processing})`}
                    onClick={() => setStatusFilter('processing')}
                    color={statusFilter === 'processing' ? 'primary' : 'default'}
                    variant={statusFilter === 'processing' ? 'filled' : 'outlined'}
                    icon={<Icon icon={Loader2} fontSize="small" />}
                    size="small"
                  />
                )}
              </Stack>
            </Box>
          </Stack>

          {/* Date Range Filter */}
          <Stack direction="row" spacing={1.5} flexWrap="wrap" alignItems="center">
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <Icon icon={Calendar} fontSize="small" />
              <Typography variant="body2" color="text.secondary">
                Date Range:
              </Typography>
            </Box>
            
            {/* Quick Date Presets */}
            <Stack direction="row" spacing={0.5}>
              <Button
                size="small"
                variant="outlined"
                onClick={() => setQuickDateRange(0)}
                sx={{ textTransform: 'none', minWidth: 'auto', px: 1.5 }}
              >
                Today
              </Button>
              <Button
                size="small"
                variant="outlined"
                onClick={() => setQuickDateRange(7)}
                sx={{ textTransform: 'none', minWidth: 'auto', px: 1.5 }}
              >
                7 days
              </Button>
              <Button
                size="small"
                variant="outlined"
                onClick={() => setQuickDateRange(30)}
                sx={{ textTransform: 'none', minWidth: 'auto', px: 1.5 }}
              >
                30 days
              </Button>
            </Stack>
            
            <TextField
              label="Start Date"
              type="date"
              value={dateRangeStart}
              onChange={(e) => setDateRangeStart(e.target.value)}
              InputLabelProps={{ shrink: true }}
              size="small"
              sx={{ width: 150 }}
              aria-label="Start date"
            />
            <TextField
              label="End Date"
              type="date"
              value={dateRangeEnd}
              onChange={(e) => setDateRangeEnd(e.target.value)}
              InputLabelProps={{ shrink: true }}
              size="small"
              sx={{ width: 150 }}
              aria-label="End date"
            />
            <Typography variant="caption" color="text.secondary">
              ({Intl.DateTimeFormat().resolvedOptions().timeZone})
            </Typography>
            {(dateRangeStart || dateRangeEnd) && (
              <Button
                size="small"
                variant="text"
                onClick={() => {
                  setDateRangeStart('');
                  setDateRangeEnd('');
                }}
              >
                Clear
              </Button>
            )}
          </Stack>
        </Stack>
      </Paper>

      {/* Info for large datasets */}
      {filteredHistory.length > 100 && (
        <Box sx={{ mb: 2 }}>
          <Typography variant="body2" color="text.secondary">
            Showing {filteredHistory.length} entries. Use filters and pagination for better performance with large datasets.
          </Typography>
        </Box>
      )}
      
      <TableContainer
        component={Paper}
        sx={{
          overflowX: 'hidden',
          // hide native webkit scrollbar if it appears
          '&::-webkit-scrollbar': { display: 'none' },
        }}
      >
        <Table sx={{ tableLayout: 'fixed', width: '100%' }}>
          <TableHead>
            <TableRow>
              <StyledTableCell>Status</StyledTableCell>
              <TimestampCell>
                <TableSortLabel
                  active={orderBy === 'timestamp'}
                  direction={orderBy === 'timestamp' ? order : 'asc'}
                  onClick={(event) => handleRequestSort(event, 'timestamp')}
                  aria-label="Sort by timestamp"
                >
                  Timestamp
                </TableSortLabel>
              </TimestampCell>
              <StyledTableCell>
                <TableSortLabel
                  active={orderBy === 'original_filename'}
                  direction={orderBy === 'original_filename' ? order : 'asc'}
                  onClick={(event) => handleRequestSort(event, 'original_filename')}
                  aria-label="Sort by filename"
                >
                  Filename
                </TableSortLabel>
              </StyledTableCell>
              <StyledTableCell>
                <TableSortLabel
                  active={orderBy === 'processed_sentences_count'}
                  direction={orderBy === 'processed_sentences_count' ? order : 'asc'}
                  onClick={(event) => handleRequestSort(event, 'processed_sentences_count')}
                  aria-label="Sort by sentence count"
                >
                  Sentences
                </TableSortLabel>
              </StyledTableCell>
              <StyledTableCell>Credits</StyledTableCell>
              <StyledTableCell>
                <TableSortLabel
                  active={orderBy === 'spreadsheet_url'}
                  direction={orderBy === 'spreadsheet_url' ? order : 'asc'}
                  onClick={(event) => handleRequestSort(event, 'spreadsheet_url')}
                  aria-label="Sort by spreadsheet URL"
                >
                  Spreadsheet
                </TableSortLabel>
              </StyledTableCell>
              <StyledTableCell>
                <TableSortLabel
                  active={orderBy === 'error_message'}
                  direction={orderBy === 'error_message' ? order : 'asc'}
                  onClick={(event) => handleRequestSort(event, 'error_message')}
                  aria-label="Sort by error"
                >
                  Error
                </TableSortLabel>
              </StyledTableCell>
              <StyledTableCell>Actions</StyledTableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {filteredHistory
              .slice(page * rowsPerPage, page * rowsPerPage + rowsPerPage)
              .map((entry) => {
              const status = getHistoryStatus(entry);
              return (
                <StyledTableRow 
                  key={entry.id}
                  onClick={(e) => {
                    // Don't open details if clicking on action buttons or links
                    const target = e.target as HTMLElement;
                    if (target.closest('button') || target.closest('a')) {
                      return;
                    }
                    handleViewDetails(entry);
                  }}
                  tabIndex={0}
                  role="button"
                  aria-label={`View details for ${entry.original_filename}`}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' || e.key === ' ') {
                      e.preventDefault();
                      handleViewDetails(entry);
                    }
                  }}
                >
                  <StyledTableCell>
                    <Chip 
                      icon={
                        status === 'complete' ? <Icon icon={CheckCircle} fontSize="small" /> :
                        status === 'failed' ? <Icon icon={XCircle} fontSize="small" /> :
                        status === 'exported' ? <Icon icon={Send} fontSize="small" /> :
                        <Icon icon={Loader2} fontSize="small" />
                      }
                      label={status === 'complete' ? 'Complete' : status === 'exported' ? 'Exported' : status}
                      size="small"
                      sx={{ 
                        fontWeight: 600,
                        textTransform: 'capitalize',
                        ...(status === 'complete' && {
                          bgcolor: 'success.main',
                          color: 'success.contrastText',
                          '& .MuiChip-icon': { color: 'success.contrastText' }
                        }),
                        ...(status === 'failed' && {
                          bgcolor: 'error.main',
                          color: 'error.contrastText',
                          '& .MuiChip-icon': { color: 'error.contrastText' }
                        }),
                        ...(status === 'processing' && {
                          bgcolor: 'primary.main',
                          color: 'primary.contrastText',
                          '& .MuiChip-icon': { 
                            color: 'primary.contrastText',
                            animation: 'spin 1s linear infinite'
                          }
                        }),
                        ...(status === 'exported' && {
                          bgcolor: '#9c27b0',  // Purple color for exported
                          color: '#ffffff',
                          '& .MuiChip-icon': { color: '#ffffff' }
                        }),
                      }}
                    />
                  </StyledTableCell>
                  <TimestampCell>{new Date(entry.timestamp).toLocaleString()}</TimestampCell>
                  <StyledTableCell>{entry.original_filename}</StyledTableCell>
                  <StyledTableCell>{entry.processed_sentences_count}</StyledTableCell>
                  <StyledTableCell>
                    {entry.job_id ? (
                      <Typography variant="body2">{entry.job_id}</Typography>
                    ) : (
                      <Typography variant="caption" color="text.secondary">
                        N/A
                      </Typography>
                    )}
                  </StyledTableCell>
                  <StyledTableCell>
                    {entry.spreadsheet_url ? (
                      <Box sx={{ display: 'flex', gap: 0.5 }}>
                        <Tooltip title="Open spreadsheet in new tab">
                          <IconButton
                            size="small"
                            onClick={(e) => {
                              e.stopPropagation();
                              window.open(entry.spreadsheet_url!, '_blank', 'noopener,noreferrer');
                            }}
                            aria-label="Open spreadsheet"
                          >
                            <Icon icon={ExternalLink} fontSize="small" />
                          </IconButton>
                        </Tooltip>
                        <Tooltip title="Copy link to clipboard">
                          <IconButton
                            size="small"
                            onClick={(e) => {
                              e.stopPropagation();
                              handleCopyUrl(entry.spreadsheet_url!);
                            }}
                            aria-label="Copy spreadsheet link"
                          >
                            <Icon icon={Copy} fontSize="small" />
                          </IconButton>
                        </Tooltip>
                      </Box>
                    ) : (
                      <Typography variant="body2" color="text.secondary">
                        Not exported
                      </Typography>
                    )}
                  </StyledTableCell>
                  <StyledTableCell>
                    {entry.error_message ? (
                      <Tooltip 
                        title={
                          <Box>
                            <Typography variant="body2" fontWeight={600} gutterBottom>
                              Technical Details:
                            </Typography>
                            <Typography variant="body2">
                              {entry.error_message}
                            </Typography>
                            {entry.error_code && (
                              <Typography variant="caption" display="block" sx={{ mt: 1 }}>
                                Error Code: {entry.error_code}
                              </Typography>
                            )}
                            {entry.failed_step && (
                              <Typography variant="caption" display="block">
                                Failed Step: {entry.failed_step}
                              </Typography>
                            )}
                          </Box>
                        }
                        arrow
                        placement="left"
                      >
                        <Box sx={{ cursor: 'help' }}>
                          <Typography variant="body2" color="error.main" sx={{ fontWeight: 500 }}>
                            {entry.failed_step === 'normalize' ? '❌ AI processing failed' :
                             entry.failed_step === 'export' ? '❌ Export failed' :
                             entry.error_code?.includes('INVALID') ? '❌ Invalid file' :
                             entry.error_code?.includes('AUTH') ? '❌ Authentication error' :
                             '❌ Processing error'}
                          </Typography>
                          <Typography variant="caption" color="text.secondary" sx={{ fontStyle: 'italic' }}>
                            Hover for details
                          </Typography>
                        </Box>
                      </Tooltip>
                    ) : (
                      <Typography variant="body2" color="text.secondary">No errors</Typography>
                    )}
                  </StyledTableCell>
                  <StyledTableCell>
                    <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap' }}>
                      <Tooltip title="View details">
                        <IconButton 
                          size="small"
                          onClick={(e) => {
                            e.stopPropagation();
                            handleViewDetails(entry);
                          }}
                          aria-label="View details"
                        >
                          <Icon icon={Eye} fontSize="small" />
                        </IconButton>
                      </Tooltip>
                      {!entry.spreadsheet_url && status === 'complete' && (
                        <Tooltip title="Send to Google Sheets">
                          <IconButton 
                            size="small"
                            color="primary"
                            onClick={(e) => {
                              e.stopPropagation();
                              handleSendToSheets(entry);
                            }}
                            aria-label="Send to Google Sheets"
                          >
                            <Icon icon={Send} fontSize="small" />
                          </IconButton>
                        </Tooltip>
                      )}
                      {status === 'failed' && entry.failed_step && (
                        <Tooltip title="Retry from failed step">
                          <IconButton 
                            size="small" 
                            color="primary"
                            onClick={(e) => {
                              e.stopPropagation();
                              handleRetry(entry);
                            }}
                            aria-label="Retry processing"
                            disabled={retryMutation.isPending}
                          >
                            <Icon icon={RefreshCw} fontSize="small" />
                          </IconButton>
                        </Tooltip>
                      )}
                      {/* Duplicate action removed from inline actions to reduce UI clutter. */}
                    </Box>
                  </StyledTableCell>
                </StyledTableRow>
              );
            })}
          </TableBody>
        </Table>
      </TableContainer>
      
      {/* Pagination */}
      <TablePagination
        rowsPerPageOptions={[5, 10, 25, 50]}
        component="div"
        count={filteredHistory.length}
        rowsPerPage={rowsPerPage}
        page={page}
        onPageChange={handleChangePage}
        onRowsPerPageChange={handleChangeRowsPerPage}
      />

      {/* Details Drawer */}
      <Drawer
        anchor="right"
        open={detailsDrawerOpen}
        onClose={() => setDetailsDrawerOpen(false)}
        sx={{
          '& .MuiDrawer-paper': {
            width: { xs: '100%', sm: 500 },
            p: 3,
          },
        }}
      >
        {selectedEntry && (
          <Box>
            <Typography variant="h5" gutterBottom>
              Entry Details
            </Typography>
            <Divider sx={{ mb: 2 }} />
            
            <Box sx={{ mb: 3 }}>
              <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                Status
              </Typography>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                {getHistoryStatus(selectedEntry) === 'complete' && <Icon icon={CheckCircle} style={{ color: '#4caf50' }} />}
                {getHistoryStatus(selectedEntry) === 'exported' && <Icon icon={Send} style={{ color: '#9c27b0' }} />}
                {getHistoryStatus(selectedEntry) === 'failed' && <Icon icon={XCircle} style={{ color: '#f44336' }} />}
                {getHistoryStatus(selectedEntry) === 'processing' && <Icon icon={Loader2} style={{ color: '#2196f3' }} />}
                <Typography variant="body1" sx={{ 
                  color: getHistoryStatus(selectedEntry) === 'complete' ? '#4caf50' : 
                         getHistoryStatus(selectedEntry) === 'exported' ? '#9c27b0' : 
                         getHistoryStatus(selectedEntry) === 'failed' ? '#f44336' : '#2196f3',
                  fontWeight: 600,
                  textTransform: 'capitalize'
                }}>
                  {getHistoryStatus(selectedEntry)}
                </Typography>
              </Box>
            </Box>

            <Box sx={{ mb: 3 }}>
              <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                Filename
              </Typography>
              <Typography variant="body1">{selectedEntry.original_filename}</Typography>
            </Box>

            <Box sx={{ mb: 3 }}>
              <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                Timestamp
              </Typography>
              <Typography variant="body1">{new Date(selectedEntry.timestamp).toLocaleString()}</Typography>
            </Box>

            <Box sx={{ mb: 3 }}>
              <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                Processed Sentences
              </Typography>
              <Typography variant="body1">{selectedEntry.processed_sentences_count}</Typography>
            </Box>

            {selectedEntry.spreadsheet_url && (
              <Box sx={{ mb: 3 }}>
                <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                  Spreadsheet
                </Typography>
                <Link href={selectedEntry.spreadsheet_url} target="_blank" rel="noopener noreferrer">
                  <Button variant="outlined" size="small">
                    Open Sheet
                  </Button>
                </Link>
              </Box>
            )}

            {selectedEntry.settings && (
              <Box sx={{ mb: 3 }}>
                <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                  Settings Used
                </Typography>
                <Paper variant="outlined" sx={{ p: 2, bgcolor: 'action.hover' }}>
                  {selectedEntry.settings.sentence_length && (
                    <Typography variant="body2">
                      Sentence Length: {selectedEntry.settings.sentence_length} words
                    </Typography>
                  )}
                  {selectedEntry.settings.gemini_model && (
                    <Typography variant="body2">
                      Model: {selectedEntry.settings.gemini_model}
                    </Typography>
                  )}
                </Paper>
              </Box>
            )}

            {selectedEntry.error_message && (
              <Box sx={{ mb: 3 }}>
                <Typography variant="subtitle2" color="error.main" gutterBottom>
                  Error Details
                </Typography>
                <Paper variant="outlined" sx={{ p: 2, bgcolor: 'error.50', borderColor: 'error.main' }}>
                  <Typography variant="body2" color="error.main" gutterBottom>
                    <strong>Message:</strong> {selectedEntry.error_message}
                  </Typography>
                  {selectedEntry.error_code && (
                    <Typography variant="body2" color="error.main" gutterBottom>
                      <strong>Code:</strong> {selectedEntry.error_code}
                    </Typography>
                  )}
                  {selectedEntry.failed_step && (
                    <Typography variant="body2" color="error.main">
                      <strong>Failed at:</strong> {selectedEntry.failed_step}
                    </Typography>
                  )}
                </Paper>
              </Box>
            )}

            <Divider sx={{ my: 2 }} />
            
            <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
              {!selectedEntry.spreadsheet_url && getHistoryStatus(selectedEntry) === 'complete' && (
                <Button
                  variant="contained"
                  startIcon={<Icon icon={Send} />}
                  onClick={() => handleSendToSheets(selectedEntry)}
                >
                  Send to Sheets
                </Button>
              )}
              {getHistoryStatus(selectedEntry) === 'failed' && selectedEntry.failed_step && (
                <Button
                  variant="outlined"
                  startIcon={<Icon icon={RefreshCw} />}
                  onClick={() => {
                    handleRetry(selectedEntry);
                    setDetailsDrawerOpen(false);
                  }}
                  disabled={retryMutation.isPending}
                >
                  Retry
                </Button>
              )}
              {/* Duplicate action is available inline in the table row; removed duplicate button here */}
              <Button
                variant="text"
                onClick={() => setDetailsDrawerOpen(false)}
              >
                Close
              </Button>
            </Box>
          </Box>
        )}
      </Drawer>

      {/* Export Dialog for history entries */}
      {entryToExport && (
        <ExportDialog
          open={exportDialogOpen}
          onClose={() => {
            setExportDialogOpen(false);
            setEntryToExport(null);
          }}
          onExport={handleExport}
          loading={exportMutation.isPending}
          defaultSheetName={`${entryToExport.original_filename.replace('.pdf', '')} - Retry`}
        />
      )}

      {/* History Detail Dialog */}
      <HistoryDetailDialog
        entryId={detailEntryId}
        open={detailDialogOpen}
        onClose={() => {
          setDetailDialogOpen(false);
          setDetailEntryId(null);
        }}
      />
    </Box>
  );
}

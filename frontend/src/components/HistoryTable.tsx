'use client';

import React, { useMemo, useState } from 'react';
import { Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Paper, TableSortLabel, TextField, Box, CircularProgress, Typography, Tooltip, TablePagination, Chip, Stack, Drawer, Divider, Button } from '@mui/material';
import { styled } from '@mui/material/styles';
import { useSnackbar } from 'notistack';
import Link from 'next/link';
import { useHistory, useRetryHistoryEntry, useDuplicateHistoryEntry, useExportToSheet } from '@/lib/queries';
import type { HistoryEntry } from '@/lib/types';
import { getHistoryStatus } from '@/lib/types';
import { useDebounce } from '@/lib/hooks';
import Icon from './Icon';
import IconButton from './IconButton';
import { CheckCircle, XCircle, Loader2, RefreshCw, Copy, Eye, Filter, Send, Calendar } from 'lucide-react';
import ExportDialog from './ExportDialog';
import { useRouter } from 'next/navigation';

type Order = 'asc' | 'desc';
type StatusFilter = 'all' | 'success' | 'failed' | 'processing';

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
  const [order, setOrder] = useState<Order>('desc');
  const [orderBy, setOrderBy] = useState<keyof HistoryEntry>('timestamp');
  const [filter, setFilter] = useState<string>('');
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('all');
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(10);
  const [detailsDrawerOpen, setDetailsDrawerOpen] = useState(false);
  const [selectedEntry, setSelectedEntry] = useState<HistoryEntry | null>(null);
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
  const duplicateMutation = useDuplicateHistoryEntry();
  const exportMutation = useExportToSheet();

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
    setSelectedEntry(entry);
    setDetailsDrawerOpen(true);
  };

  const handleSendToSheets = (entry: HistoryEntry) => {
    setEntryToExport(entry);
    setExportDialogOpen(true);
  };

  const handleExport = async (_options: { sheetName: string; folderId?: string | null }) => {
    if (!entryToExport) return;
    
    try {
      // For history entries, we don't have the sentences stored
      // In a real implementation, you would either:
      // 1. Store sentences in the history entry
      // 2. Re-process the file
      // For now, we'll show a message
      enqueueSnackbar('This feature requires storing processed sentences. Please reprocess the file to export.', { variant: 'info' });
      setExportDialogOpen(false);
    } catch (_error) {
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
    } catch (_error) {
      // Error handled by mutation
    }
  };

  const handleDuplicate = async (entry: HistoryEntry) => {
    try {
      const result = await duplicateMutation.mutateAsync(entry.id);
      enqueueSnackbar(result.message, { variant: 'info' });
      
      // Navigate to home with settings
      if (result.settings) {
        // Store settings in localStorage for the home page to use
        localStorage.setItem('duplicateSettings', JSON.stringify(result.settings));
        router.push('/');
      }
    } catch (_error) {
      // Error handled by mutation
    }
  };

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
      {/* Search and Filter Controls */}
      <Box sx={{ mb: 3 }}>
        <TextField
          label="Search history"
          variant="outlined"
          fullWidth
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
          placeholder="Search by filename, URL, or error message..."
          sx={{ mb: 2 }}
        />
        
        {/* Date Range Filter */}
        <Box sx={{ display: 'flex', gap: 2, mb: 2, flexWrap: 'wrap', alignItems: 'center' }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <Icon icon={Calendar} fontSize="small" />
            <Typography variant="body2" color="text.secondary">
              Date Range:
            </Typography>
          </Box>
          <TextField
            label="Start Date"
            type="date"
            value={dateRangeStart}
            onChange={(e) => setDateRangeStart(e.target.value)}
            InputLabelProps={{ shrink: true }}
            size="small"
            sx={{ minWidth: 150 }}
          />
          <TextField
            label="End Date"
            type="date"
            value={dateRangeEnd}
            onChange={(e) => setDateRangeEnd(e.target.value)}
            InputLabelProps={{ shrink: true }}
            size="small"
            sx={{ minWidth: 150 }}
          />
          {(dateRangeStart || dateRangeEnd) && (
            <Button
              size="small"
              variant="text"
              onClick={() => {
                setDateRangeStart('');
                setDateRangeEnd('');
              }}
            >
              Clear Dates
            </Button>
          )}
        </Box>
        
        {/* Status Filter Chips */}
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, flexWrap: 'wrap', mb: 2 }}>
          <Icon icon={Filter} fontSize="small" />
          <Typography variant="body2" color="text.secondary">
            Status:
          </Typography>
          <Stack direction="row" spacing={1} sx={{ flexWrap: 'wrap', gap: 1 }}>
            <Chip
              label="All"
              onClick={() => setStatusFilter('all')}
              color={statusFilter === 'all' ? 'primary' : 'default'}
              variant={statusFilter === 'all' ? 'filled' : 'outlined'}
              size="small"
            />
            <Chip
              label="Success"
              onClick={() => setStatusFilter('success')}
              color={statusFilter === 'success' ? 'success' : 'default'}
              variant={statusFilter === 'success' ? 'filled' : 'outlined'}
              icon={<Icon icon={CheckCircle} fontSize="small" />}
              size="small"
            />
            <Chip
              label="Failed"
              onClick={() => setStatusFilter('failed')}
              color={statusFilter === 'failed' ? 'error' : 'default'}
              variant={statusFilter === 'failed' ? 'filled' : 'outlined'}
              icon={<Icon icon={XCircle} fontSize="small" />}
              size="small"
            />
            <Chip
              label="Processing"
              onClick={() => setStatusFilter('processing')}
              color={statusFilter === 'processing' ? 'primary' : 'default'}
              variant={statusFilter === 'processing' ? 'filled' : 'outlined'}
              icon={<Icon icon={Loader2} fontSize="small" />}
              size="small"
            />
          </Stack>
        </Box>

        {/* Info for large datasets */}
        {filteredHistory.length > 100 && (
          <Box sx={{ mb: 2 }}>
            <Typography variant="body2" color="text.secondary">
              Showing {filteredHistory.length} entries. Use filters and pagination for better performance with large datasets.
            </Typography>
          </Box>
        )}
      </Box>
      
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
            {filteredHistory
              .slice(page * rowsPerPage, page * rowsPerPage + rowsPerPage)
              .map((entry) => {
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
                    <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap' }}>
                      <Tooltip title="View details">
                        <IconButton 
                          size="small"
                          onClick={() => handleViewDetails(entry)}
                          aria-label="View details"
                        >
                          <Icon icon={Eye} fontSize="small" />
                        </IconButton>
                      </Tooltip>
                      {!entry.spreadsheet_url && status === 'success' && (
                        <Tooltip title="Send to Google Sheets">
                          <IconButton 
                            size="small"
                            color="primary"
                            onClick={() => handleSendToSheets(entry)}
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
                            onClick={() => handleRetry(entry)}
                            aria-label="Retry processing"
                            disabled={retryMutation.isPending}
                          >
                            <Icon icon={RefreshCw} fontSize="small" />
                          </IconButton>
                        </Tooltip>
                      )}
                      {entry.settings && (
                        <Tooltip title="Duplicate with same settings">
                          <IconButton 
                            size="small"
                            onClick={() => handleDuplicate(entry)}
                            aria-label="Duplicate run"
                            disabled={duplicateMutation.isPending}
                          >
                            <Icon icon={Copy} fontSize="small" />
                          </IconButton>
                        </Tooltip>
                      )}
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
                {getHistoryStatus(selectedEntry) === 'success' && <Icon icon={CheckCircle} color="success" />}
                {getHistoryStatus(selectedEntry) === 'failed' && <Icon icon={XCircle} color="error" />}
                {getHistoryStatus(selectedEntry) === 'processing' && <Icon icon={Loader2} color="primary" />}
                <Typography variant="body1" sx={{ 
                  color: getHistoryStatus(selectedEntry) === 'success' ? 'success.main' : 
                         getHistoryStatus(selectedEntry) === 'failed' ? 'error.main' : 'primary.main',
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
              {!selectedEntry.spreadsheet_url && getHistoryStatus(selectedEntry) === 'success' && (
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
              {selectedEntry.settings && (
                <Button
                  variant="outlined"
                  startIcon={<Icon icon={Copy} />}
                  onClick={() => {
                    handleDuplicate(selectedEntry);
                    setDetailsDrawerOpen(false);
                  }}
                  disabled={duplicateMutation.isPending}
                >
                  Duplicate
                </Button>
              )}
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
    </Box>
  );
}

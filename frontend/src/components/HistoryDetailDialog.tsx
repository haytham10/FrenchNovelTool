'use client';

/**
 * History Detail Dialog - View and export historical job results
 */
import React, { useState, useMemo } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Typography,
  Box,
  Chip,
  Stack,
  CircularProgress,
  Alert,
  IconButton,
  Tooltip,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Divider,
  TextField,
  Skeleton,
} from '@mui/material';
import { X, Download, ExternalLink, ChevronDown, CheckCircle, XCircle, Clock, RefreshCw, Copy, Search, Eye } from 'lucide-react';
import { useHistoryDetail, useHistoryChunks, useExportHistoryToSheets } from '@/lib/queries';
import { formatDistanceToNow } from 'date-fns';
import { useSnackbar } from 'notistack';
import Icon from './Icon';

interface HistoryDetailDialogProps {
  entryId: number | null;
  open: boolean;
  onClose: () => void;
}

export default function HistoryDetailDialog({
  entryId,
  open,
  onClose,
}: HistoryDetailDialogProps) {
  const { data: entry, isLoading, error } = useHistoryDetail(entryId);
  const { data: chunksData } = useHistoryChunks(entryId);
  const exportMutation = useExportHistoryToSheets();
  const { enqueueSnackbar } = useSnackbar();
  const [showSentences, setShowSentences] = useState(false);
  const [showChunks, setShowChunks] = useState(false);
  const [sentenceSearch, setSentenceSearch] = useState('');

  const handleExport = () => {
    if (entryId) {
      exportMutation.mutate({
        entryId,
        data: {
          sheetName: entry?.original_filename ? `${entry.original_filename} - Export` : undefined
        }
      });
    }
  };

  const handleOpenSheet = () => {
    const url = entry?.export_sheet_url || entry?.spreadsheet_url;
    if (url) {
      window.open(url, '_blank');
    }
  };

  const handleCopyUrl = async (url: string) => {
    try {
      await navigator.clipboard.writeText(url);
      enqueueSnackbar('Link copied to clipboard', { variant: 'success' });
    } catch {
      enqueueSnackbar('Failed to copy link', { variant: 'error' });
    }
  };

  // Filter and highlight sentences
  const filteredSentences = useMemo(() => {
    if (!entry?.sentences) return [];
    let filtered = entry.sentences;
    
    // Apply text search
    if (sentenceSearch) {
      filtered = filtered.filter((sentence) => 
        sentence.normalized?.toLowerCase().includes(sentenceSearch.toLowerCase()) ||
        sentence.original?.toLowerCase().includes(sentenceSearch.toLowerCase())
      );
    }


    return filtered;
  }, [entry?.sentences, sentenceSearch]);

  const getChunkStatusIcon = (status: string) => {
    switch (status) {
      case 'success':
        return <CheckCircle size={16} style={{ color: '#4caf50' }} />;
      case 'failed':
        return <XCircle size={16} style={{ color: '#f44336' }} />;
      case 'processing':
        return <CircularProgress size={16} />;
      case 'retry_scheduled':
        return <RefreshCw size={16} style={{ color: '#ff9800' }} />;
      default:
        return <Clock size={16} style={{ color: '#9e9e9e' }} />;
    }
  };

  const getChunkStatusColor = (status: string) => {
    switch (status) {
      case 'success':
        return 'success';
      case 'failed':
        return 'error';
      case 'processing':
        return 'info';
      case 'retry_scheduled':
        return 'warning';
      default:
        return 'default';
    }
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="lg" fullWidth>
      <DialogTitle>
        <Stack direction="row" alignItems="center" justifyContent="space-between">
          <Typography variant="h6">Processing History Detail</Typography>
          <IconButton onClick={onClose} size="small">
            <X />
          </IconButton>
        </Stack>
      </DialogTitle>

      <DialogContent>
        {isLoading && (
          <Stack spacing={3}>
            {/* File Information Skeleton */}
            <Box>
              <Skeleton variant="text" width={150} height={28} sx={{ mb: 2 }} />
              <Stack spacing={1}>
                <Stack direction="row" spacing={2}>
                  <Skeleton variant="text" width={150} height={24} />
                  <Skeleton variant="text" width={300} height={24} />
                </Stack>
                <Stack direction="row" spacing={2}>
                  <Skeleton variant="text" width={150} height={24} />
                  <Skeleton variant="text" width={200} height={24} />
                </Stack>
                <Stack direction="row" spacing={2}>
                  <Skeleton variant="text" width={150} height={24} />
                  <Skeleton variant="text" width={100} height={24} />
                </Stack>
              </Stack>
            </Box>

            <Divider />

            {/* Processing Settings Skeleton */}
            <Box>
              <Skeleton variant="text" width={180} height={28} sx={{ mb: 2 }} />
              <Stack spacing={1}>
                <Stack direction="row" spacing={2}>
                  <Skeleton variant="text" width={150} height={24} />
                  <Skeleton variant="text" width={120} height={24} />
                </Stack>
                <Stack direction="row" spacing={2}>
                  <Skeleton variant="text" width={150} height={24} />
                  <Skeleton variant="text" width={100} height={24} />
                </Stack>
              </Stack>
            </Box>

            <Divider />

            {/* Sentences Skeleton */}
            <Box>
              <Skeleton variant="rectangular" width="100%" height={300} />
            </Box>
          </Stack>
        )}

        {error && (
          <Alert severity="error">
            Failed to load history details. Please try again.
          </Alert>
        )}

        {entry && (
          <Stack spacing={3}>
            {/* Basic Info */}
            <Box>
              <Typography variant="subtitle1" fontWeight="bold" gutterBottom>
                File Information
              </Typography>
              <Stack spacing={1}>
                <Stack direction="row" spacing={2}>
                  <Typography variant="body2" color="text.secondary" sx={{ minWidth: 150 }}>
                    Filename:
                  </Typography>
                  <Typography variant="body2">{entry.original_filename}</Typography>
                </Stack>
                <Stack direction="row" spacing={2}>
                  <Typography variant="body2" color="text.secondary" sx={{ minWidth: 150 }}>
                    Processed:
                  </Typography>
                  <Typography variant="body2">
                    {formatDistanceToNow(new Date(entry.timestamp), { addSuffix: true })}
                  </Typography>
                </Stack>
                <Stack direction="row" spacing={2}>
                  <Typography variant="body2" color="text.secondary" sx={{ minWidth: 150 }}>
                    Sentences:
                  </Typography>
                  <Typography variant="body2">{entry.processed_sentences_count}</Typography>
                </Stack>
                {entry.exported_to_sheets && (
                  <Stack direction="row" spacing={2} alignItems="center">
                    <Typography variant="body2" color="text.secondary" sx={{ minWidth: 150 }}>
                      Export Status:
                    </Typography>
                    <Chip
                      label="Exported"
                      color="success"
                      size="small"
                      icon={<CheckCircle size={14} />}
                    />
                  </Stack>
                )}
              </Stack>
            </Box>

            <Divider />

            {/* Processing Settings */}
            {entry.settings && (
              <Box>
                <Typography variant="subtitle1" fontWeight="bold" gutterBottom>
                  Processing Settings
                </Typography>
                <Stack spacing={1}>
                  {entry.settings.sentence_length_limit && (
                    <Stack direction="row" spacing={2}>
                      <Typography variant="body2" color="text.secondary" sx={{ minWidth: 150 }}>
                        Sentence Length:
                      </Typography>
                      <Tooltip title="Maximum number of words allowed per normalized sentence" placement="top">
                        <Typography variant="body2">{entry.settings.sentence_length_limit} words</Typography>
                      </Tooltip>
                    </Stack>
                  )}
                  {entry.settings.gemini_model && (
                    <Stack direction="row" spacing={2}>
                      <Typography variant="body2" color="text.secondary" sx={{ minWidth: 150 }}>
                        Model:
                      </Typography>
                      <Tooltip title="AI model used for sentence normalization" placement="top">
                        <Typography variant="body2">{entry.settings.gemini_model}</Typography>
                      </Tooltip>
                    </Stack>
                  )}
                </Stack>
              </Box>
            )}

            <Divider />

            {/* Sentences */}
            <Accordion expanded={showSentences} onChange={() => setShowSentences(!showSentences)}>
              <AccordionSummary expandIcon={<ChevronDown />}>
                <Typography variant="subtitle1" fontWeight="bold">
                  Processed Sentences ({entry.sentences?.length || 0})
                </Typography>
              </AccordionSummary>
              <AccordionDetails>
                {entry.sentences && entry.sentences.length > 0 ? (
                  <Stack spacing={2}>
                    {/* Search and Filter Controls */}
                    <Stack direction="row" spacing={2} alignItems="center" flexWrap="wrap">
                      <TextField
                        placeholder="Search sentences..."
                        size="small"
                        value={sentenceSearch}
                        onChange={(e) => setSentenceSearch(e.target.value)}
                        InputProps={{
                          startAdornment: <Icon icon={Search} fontSize="small" style={{ marginRight: 8 }} />
                        }}
                        sx={{ flexGrow: 1, minWidth: 200 }}
                      />
                    </Stack>
                    
                    {filteredSentences.length > 0 ? (
                      <TableContainer component={Paper} variant="outlined" sx={{ maxHeight: 400, overflowX: 'hidden' }}>
                        <Table stickyHeader size="small">
                          <TableHead>
                            <TableRow>
                              <TableCell sx={{ width: 60 }}>#</TableCell>
                              <TableCell>
                                <Tooltip title="Normalized/cleaned sentence after AI processing">
                                  <span>Sentence</span>
                                </Tooltip>
                              </TableCell>
                              <TableCell sx={{ width: 60 }}>
                                <Tooltip title="Copy sentence">
                                  <span>Actions</span>
                                </Tooltip>
                              </TableCell>
                            </TableRow>
                          </TableHead>
                          <TableBody>
                            {filteredSentences.map((sentence) => {
                              const isDifferent = sentence.normalized !== sentence.original;
                              const actualIndex = entry.sentences.indexOf(sentence);
                              return (
                                <TableRow 
                                  key={actualIndex}
                                  sx={{
                                    ...(isDifferent && {
                                      bgcolor: 'action.hover'
                                    })
                                  }}
                                >
                                  <TableCell>{actualIndex + 1}</TableCell>
                                  <TableCell 
                                    sx={{ 
                                      ...(isDifferent && {
                                        fontWeight: 500,
                                        color: 'primary.main'
                                      }),
                                      wordBreak: 'break-word'
                                    }}
                                  >
                                    {sentence.normalized}
                                  </TableCell>
                                  <TableCell>
                                    <Tooltip title="Copy sentence">
                                      <IconButton
                                        size="small"
                                        onClick={() => handleCopyUrl(sentence.normalized)}
                                        aria-label="Copy sentence"
                                      >
                                        <Icon icon={Copy} fontSize="small" />
                                      </IconButton>
                                    </Tooltip>
                                  </TableCell>
                                </TableRow>
                              );
                            })}
                          </TableBody>
                        </Table>
                      </TableContainer>
                    ) : (
                      <Alert severity="info">
                        No sentences match your search criteria
                      </Alert>
                    )}
                    
                    {sentenceSearch && (
                      <Typography variant="caption" color="text.secondary">
                        Showing {filteredSentences.length} of {entry.sentences.length} sentences
                      </Typography>
                    )}
                  </Stack>
                ) : (
                  <Typography variant="body2" color="text.secondary">
                    No sentences available
                  </Typography>
                )}
              </AccordionDetails>
            </Accordion>

            {/* Chunk Details */}
            {chunksData && chunksData.chunks.length > 0 && (
              <Accordion expanded={showChunks} onChange={() => setShowChunks(!showChunks)}>
                <AccordionSummary expandIcon={<ChevronDown />}>
                  <Typography variant="subtitle1" fontWeight="bold">
                    Chunk Processing Details ({chunksData.chunks.length} chunks)
                  </Typography>
                </AccordionSummary>
                <AccordionDetails>
                  <TableContainer component={Paper} variant="outlined" sx={{ maxHeight: 300 }}>
                    <Table stickyHeader size="small">
                      <TableHead>
                        <TableRow>
                          <TableCell>Chunk</TableCell>
                          <TableCell>Pages</TableCell>
                          <TableCell>Status</TableCell>
                          <TableCell>
                            <Tooltip title="Number of processing attempts (current/maximum)">
                              <span>Attempts</span>
                            </Tooltip>
                          </TableCell>
                          <TableCell>Error</TableCell>
                        </TableRow>
                      </TableHead>
                      <TableBody>
                        {chunksData.chunks.map((chunk) => (
                          <TableRow key={chunk.id}>
                            <TableCell>#{chunk.chunk_id + 1}</TableCell>
                            <TableCell>
                              {chunk.start_page + 1}-{chunk.end_page + 1}
                              {chunk.has_overlap && (
                                <Tooltip title="This chunk has overlap with the previous chunk to maintain context continuity">
                                  <Chip label="Overlap" size="small" sx={{ ml: 1 }} />
                                </Tooltip>
                              )}
                            </TableCell>
                            <TableCell>
                              <Stack direction="row" spacing={1} alignItems="center">
                                {getChunkStatusIcon(chunk.status)}
                                <Chip
                                  label={chunk.status}
                                  size="small"
                                  color={getChunkStatusColor(chunk.status)}
                                  sx={{ textTransform: 'capitalize' }}
                                />
                              </Stack>
                            </TableCell>
                            <TableCell>
                              <Tooltip title={`This chunk has been attempted ${chunk.attempts} time(s) out of ${chunk.max_retries} maximum retries`}>
                                <Chip
                                  label={`${chunk.attempts}/${chunk.max_retries}`}
                                  size="small"
                                  color={chunk.attempts > 1 ? 'warning' : 'default'}
                                />
                              </Tooltip>
                            </TableCell>
                            <TableCell>
                              {chunk.last_error ? (
                                <Tooltip 
                                  title={
                                    <Box>
                                      <Typography variant="body2" fontWeight="bold">Error Details:</Typography>
                                      <Typography variant="body2">{chunk.last_error}</Typography>
                                      {chunk.last_error_code && (
                                        <Typography variant="caption" display="block" sx={{ mt: 1 }}>
                                          Code: {chunk.last_error_code}
                                        </Typography>
                                      )}
                                    </Box>
                                  }
                                >
                                  <Box sx={{ cursor: 'help', display: 'flex', alignItems: 'center', gap: 0.5 }}>
                                    <Typography variant="body2" color="error" noWrap sx={{ maxWidth: 200 }}>
                                      {chunk.last_error_code || 'Error'}
                                    </Typography>
                                    <Icon icon={Eye} fontSize="small" style={{ color: 'rgba(0,0,0,0.54)' }} />
                                  </Box>
                                </Tooltip>
                              ) : (
                                <Typography variant="body2" color="text.secondary">—</Typography>
                              )}
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </TableContainer>

                  {/* Chunk Summary */}
                  <Box mt={2}>
                    <Stack direction="row" spacing={2} flexWrap="wrap">
                      <Chip
                        icon={<CheckCircle size={14} />}
                        label={`${chunksData.chunks.filter(c => c.status === 'success').length} Successful`}
                        color="success"
                        size="small"
                      />
                      <Chip
                        icon={<XCircle size={14} />}
                        label={`${chunksData.chunks.filter(c => c.status === 'failed').length} Failed`}
                        color="error"
                        size="small"
                      />
                      {chunksData.chunks.filter(c => c.status === 'processing').length > 0 && (
                        <Chip
                          icon={<CircularProgress size={14} />}
                          label={`${chunksData.chunks.filter(c => c.status === 'processing').length} Processing`}
                          color="info"
                          size="small"
                        />
                      )}
                    </Stack>
                  </Box>
                </AccordionDetails>
              </Accordion>
            )}
          </Stack>
        )}
      </DialogContent>

      <DialogActions>
        <Stack direction="row" spacing={2} width="100%" justifyContent="space-between" flexWrap="wrap">
          <Box sx={{ display: 'flex', gap: 1 }}>
            {entry?.export_sheet_url || entry?.spreadsheet_url ? (
              <>
                <Tooltip title="Open spreadsheet in new tab">
                  <Button
                    startIcon={<ExternalLink />}
                    onClick={handleOpenSheet}
                    variant="outlined"
                  >
                    Open Sheet
                  </Button>
                </Tooltip>
                <Tooltip title="Copy spreadsheet link to clipboard">
                  <IconButton
                    onClick={() => handleCopyUrl(entry?.export_sheet_url || entry?.spreadsheet_url || '')}
                    aria-label="Copy spreadsheet link"
                  >
                    <Copy />
                  </IconButton>
                </Tooltip>
              </>
            ) : null}
          </Box>
          <Stack direction="row" spacing={1}>
            <Button onClick={onClose}>Close</Button>
            {entry && entry.sentences && entry.sentences.length > 0 && (
              <Tooltip title={entry.exported_to_sheets ? "Export to a new spreadsheet" : "Export to Google Sheets"}>
                <Button
                  startIcon={exportMutation.isPending ? <CircularProgress size={16} /> : <Download />}
                  onClick={handleExport}
                  variant="contained"
                  disabled={exportMutation.isPending}
                >
                  {entry.exported_to_sheets ? 'Re-export' : 'Export to Sheets'}
                </Button>
              </Tooltip>
            )}
          </Stack>
        </Stack>
      </DialogActions>
    </Dialog>
  );
}

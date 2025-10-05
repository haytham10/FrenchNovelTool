'use client';

/**
 * History Detail Dialog - View and export historical job results
 */
import React, { useState } from 'react';
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
} from '@mui/material';
import { X, Download, ExternalLink, ChevronDown, CheckCircle, XCircle, Clock, RefreshCw } from 'lucide-react';
import { useHistoryDetail, useHistoryChunks, useExportHistoryToSheets } from '@/lib/queries';
import { formatDistanceToNow } from 'date-fns';

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
  const [showSentences, setShowSentences] = useState(false);
  const [showChunks, setShowChunks] = useState(false);

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
          <Box display="flex" justifyContent="center" alignItems="center" minHeight="200px">
            <CircularProgress />
          </Box>
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
                      <Typography variant="body2">{entry.settings.sentence_length_limit} words</Typography>
                    </Stack>
                  )}
                  {entry.settings.gemini_model && (
                    <Stack direction="row" spacing={2}>
                      <Typography variant="body2" color="text.secondary" sx={{ minWidth: 150 }}>
                        Model:
                      </Typography>
                      <Typography variant="body2">{entry.settings.gemini_model}</Typography>
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
                  <TableContainer component={Paper} variant="outlined" sx={{ maxHeight: 400 }}>
                    <Table stickyHeader size="small">
                      <TableHead>
                        <TableRow>
                          <TableCell>#</TableCell>
                          <TableCell>Normalized</TableCell>
                          <TableCell>Original</TableCell>
                        </TableRow>
                      </TableHead>
                      <TableBody>
                        {entry.sentences.map((sentence, index) => (
                          <TableRow key={index}>
                            <TableCell>{index + 1}</TableCell>
                            <TableCell>{sentence.normalized}</TableCell>
                            <TableCell sx={{ color: 'text.secondary', fontSize: '0.875rem' }}>
                              {sentence.original}
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </TableContainer>
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
                          <TableCell>Attempts</TableCell>
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
                                <Tooltip title="Has overlap with previous chunk">
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
                                />
                              </Stack>
                            </TableCell>
                            <TableCell>
                              {chunk.attempts}/{chunk.max_retries}
                            </TableCell>
                            <TableCell>
                              {chunk.last_error ? (
                                <Tooltip title={chunk.last_error}>
                                  <Typography variant="body2" noWrap sx={{ maxWidth: 200 }}>
                                    {chunk.last_error_code || 'Error'}
                                  </Typography>
                                </Tooltip>
                              ) : (
                                '-'
                              )}
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </TableContainer>

                  {/* Chunk Summary */}
                  <Box mt={2}>
                    <Stack direction="row" spacing={2}>
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
        <Stack direction="row" spacing={2} width="100%" justifyContent="space-between">
          <Box>
            {entry?.export_sheet_url || entry?.spreadsheet_url ? (
                          <Button
                            startIcon={<ExternalLink />}
                            onClick={handleOpenSheet}
                            variant="outlined"
                          >
                            Open Sheet
                          </Button>
                        ) : null}
          </Box>
          <Stack direction="row" spacing={1}>
            <Button onClick={onClose}>Close</Button>
            {entry && entry.sentences && entry.sentences.length > 0 && (
              <Button
                startIcon={exportMutation.isPending ? <CircularProgress size={16} /> : <Download />}
                onClick={handleExport}
                variant="contained"
                disabled={exportMutation.isPending}
              >
                {entry.exported_to_sheets ? 'Re-export' : 'Export to Sheets'}
              </Button>
            )}
          </Stack>
        </Stack>
      </DialogActions>
    </Dialog>
  );
}

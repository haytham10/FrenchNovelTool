'use client';

import React from 'react';
import {
  Box,
  Typography,
  Stack,
  TextField,
  Button,
  FormControlLabel,
  Switch,
  Chip,
  Card,
  CardActionArea,
  CardContent,
  Checkbox,
  Radio,
  CircularProgress,
  Pagination,
  InputAdornment,
} from '@mui/material';
import {
  Search as SearchIcon,
  CloudUpload as CloudUploadIcon,
  Description as PdfIcon,
  TableChart as SheetsIcon,
} from '@mui/icons-material';
import { HistoryEntry } from '@/lib/types';

interface SelectSourceStepProps {
  isBatchMode: boolean;
  setIsBatchMode: (value: boolean) => void;
  selectedSourceIds: number[];
  sourceId: string;
  historySearch: string;
  setHistorySearch: (value: string) => void;
  filteredHistory: HistoryEntry[];
  loadingHistory: boolean;
  historyPage: number;
  setHistoryPage: (page: number) => void;
  historyPageSize: number;
  onToggleSourceSelection: (historyId: number) => void;
  onOpenImportDialog: () => void;
}

export default function SelectSourceStep({
  isBatchMode,
  setIsBatchMode,
  selectedSourceIds,
  sourceId,
  historySearch,
  setHistorySearch,
  filteredHistory,
  loadingHistory,
  historyPage,
  setHistoryPage,
  historyPageSize,
  onToggleSourceSelection,
  onOpenImportDialog,
}: SelectSourceStepProps) {
  const handleBatchModeToggle = () => {
    setIsBatchMode(!isBatchMode);
  };

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <Typography variant="h5" fontWeight={600} gutterBottom>
        Select Source{isBatchMode ? 's' : ''}
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
        {isBatchMode
          ? 'Select multiple novels for batch analysis (minimum 2 required)'
          : 'Choose a previously processed document or import from Google Sheets'}
      </Typography>

      {/* Batch Mode Toggle */}
      <Box sx={{ mb: 3, display: 'flex', alignItems: 'center', gap: 2 }}>
        <FormControlLabel
          control={
            <Switch
              checked={isBatchMode}
              onChange={handleBatchModeToggle}
              color="primary"
            />
          }
          label={
            <Box>
              <Typography variant="body1" fontWeight={600}>
                Batch Analysis Mode
              </Typography>
              <Typography variant="caption" color="text.secondary">
                Process multiple novels sequentially for maximum coverage efficiency
              </Typography>
            </Box>
          }
        />
        {isBatchMode && (
          <Chip
            label={`${selectedSourceIds.length} selected`}
            color={selectedSourceIds.length >= 2 ? 'success' : 'default'}
            size="small"
          />
        )}
      </Box>

      {/* Search & Import */}
      <Stack direction="row" spacing={2} sx={{ mb: 3 }}>
        <TextField
          fullWidth
          placeholder="Search by name or ID..."
          value={historySearch}
          onChange={(e) => setHistorySearch(e.target.value)}
          InputProps={{
            startAdornment: (
              <InputAdornment position="start">
                <SearchIcon />
              </InputAdornment>
            ),
          }}
        />
        <Button
          variant="outlined"
          startIcon={<CloudUploadIcon />}
          onClick={onOpenImportDialog}
          sx={{ flexShrink: 0 }}
        >
          Import from Sheets
        </Button>
      </Stack>

      {/* Source List */}
      <Box sx={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'auto', border: 1, borderColor: 'divider', borderRadius: 1, p: 2 }}>
        {loadingHistory ? (
          <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', py: 8 }}>
            <CircularProgress size={32} />
            <Typography variant="body1" sx={{ ml: 2 }}>Loading sources...</Typography>
          </Box>
        ) : filteredHistory.length === 0 ? (
          <Box sx={{ py: 8, textAlign: 'center' }}>
            <Typography variant="body1" color="text.secondary">
              {historySearch ? 'No matches found' : 'No source files available'}
            </Typography>
          </Box>
        ) : (
          <>
            <Stack spacing={2}>
              {filteredHistory.slice((historyPage - 1) * historyPageSize, historyPage * historyPageSize).map((h) => {
                const selected = isBatchMode
                  ? selectedSourceIds.includes(h.id)
                  : String(h.id) === sourceId;
                const date = new Date(h.timestamp).toLocaleDateString();
                const isFromSheets = h.original_filename?.includes('Google Sheets');

                return (
                  <Card
                    key={h.id}
                    variant="outlined"
                    sx={{
                      border: selected ? 2 : 1,
                      borderColor: selected ? 'primary.main' : 'divider',
                      bgcolor: selected ? 'action.selected' : 'background.paper',
                      transition: 'all 0.2s',
                      '&:hover': {
                        borderColor: 'primary.main',
                        boxShadow: 1,
                      },
                    }}
                  >
                    <CardActionArea onClick={() => onToggleSourceSelection(h.id)}>
                      <CardContent sx={{ p: 2, '&:last-child': { pb: 2 } }}>
                        <Box sx={{ display: 'flex', alignItems: 'flex-start', gap: 2 }}>
                          <Box sx={{ color: 'primary.main', mt: 0.5 }}>
                            {isFromSheets ? <SheetsIcon /> : <PdfIcon />}
                          </Box>
                          <Box sx={{ flex: 1, minWidth: 0 }}>
                            <Typography variant="body1" fontWeight={600} noWrap>
                              {h.original_filename || `Source #${h.id}`}
                            </Typography>
                            <Typography variant="body2" color="text.secondary" display="block">
                              ID #{h.id} • {h.processed_sentences_count} sentences • {date}
                            </Typography>
                          </Box>
                          {isBatchMode ? (
                            <Checkbox
                              checked={selected}
                              size="small"
                              sx={{ p: 0 }}
                            />
                          ) : (
                            <Radio
                              checked={selected}
                              size="small"
                              sx={{ p: 0 }}
                            />
                          )}
                        </Box>
                      </CardContent>
                    </CardActionArea>
                  </Card>
                );
              })}
            </Stack>

            {/* Pagination controls */}
            {filteredHistory.length > historyPageSize && (
              <Box sx={{ display: 'flex', justifyContent: 'center', mt: 2 }}>
                <Pagination
                  count={Math.ceil(filteredHistory.length / historyPageSize)}
                  page={historyPage}
                  onChange={(_, p) => setHistoryPage(p)}
                  color="primary"
                />
              </Box>
            )}
          </>
        )}
      </Box>
    </Box>
  );
}

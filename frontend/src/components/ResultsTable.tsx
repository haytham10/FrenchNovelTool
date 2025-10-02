import React, { useState, useRef, useEffect } from 'react';
import { Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Paper, TableSortLabel, TextField, Box, IconButton, Tooltip, Checkbox, Button, Stack, Chip, ToggleButtonGroup, ToggleButton, LinearProgress, Typography } from '@mui/material';
import { styled } from '@mui/material/styles';
import Icon from './Icon';
import { Edit2, Check, X, CheckSquare, AlertCircle } from 'lucide-react';
import { useDebounce } from '@/lib/hooks';

interface ResultsTableProps {
  sentences: string[];
  originalSentences?: string[];
  onSentencesChange?: (sentences: string[]) => void;
  onExportSelected?: (selectedIndices: number[]) => void;
}

type Order = 'asc' | 'desc';
type ViewMode = 'normalized' | 'original' | 'both';

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

const LONG_SENTENCE_THRESHOLD = 15; // words

export default function ResultsTable({ sentences, originalSentences = [], onSentencesChange, onExportSelected }: ResultsTableProps) {
  const [order, setOrder] = useState<Order>('asc');
  const [orderBy, setOrderBy] = useState<keyof { index: number; sentence: string }>('index');
  const [filter, setFilter] = useState<string>('');
  const debouncedFilter = useDebounce(filter, 300);
  const [editingIndex, setEditingIndex] = useState<number | null>(null);
  const [editValue, setEditValue] = useState<string>('');
  const editInputRef = useRef<HTMLInputElement>(null);
  const [selectedRows, setSelectedRows] = useState<Set<number>>(new Set());
  const [viewMode, setViewMode] = useState<ViewMode>('normalized');
  const [lastSelectedIndex, setLastSelectedIndex] = useState<number | null>(null);

  const handleRequestSort = (
    event: React.MouseEvent<unknown>,
    property: keyof { index: number; sentence: string },
  ) => {
    const isAsc = orderBy === property && order === 'asc';
    setOrder(isAsc ? 'desc' : 'asc');
    setOrderBy(property);
  };

  const sortedSentences = React.useMemo(() => {
    const stabilizedThis = sentences.map((el, index) => ({ index: index + 1, sentence: el }));
    const comparator = (a: { index: number; sentence: string }, b: { index: number; sentence: string }) => {
      if (orderBy === 'index') {
        return order === 'asc' ? a.index - b.index : b.index - a.index;
      } else {
        return order === 'asc' ? a.sentence.localeCompare(b.sentence) : b.sentence.localeCompare(a.sentence);
      }
    };
    stabilizedThis.sort(comparator);
    return stabilizedThis;
  }, [sentences, order, orderBy]);

  const filteredSentences = React.useMemo(() => {
    if (!debouncedFilter) return sortedSentences;
    return sortedSentences.filter(item =>
      item.sentence.toLowerCase().includes(debouncedFilter.toLowerCase())
    );
  }, [sortedSentences, debouncedFilter]);

  const startEdit = (index: number, sentence: string) => {
    setEditingIndex(index);
    setEditValue(sentence);
  };

  const saveEdit = () => {
    if (editingIndex !== null && onSentencesChange) {
      const newSentences = [...sentences];
      newSentences[editingIndex - 1] = editValue;
      onSentencesChange(newSentences);
    }
    setEditingIndex(null);
    setEditValue('');
  };

  const cancelEdit = () => {
    setEditingIndex(null);
    setEditValue('');
  };

  useEffect(() => {
    if (editingIndex !== null && editInputRef.current) {
      editInputRef.current.focus();
    }
  }, [editingIndex]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      saveEdit();
    } else if (e.key === 'Escape') {
      cancelEdit();
    }
  };

  const handleSelectAll = () => {
    if (selectedRows.size === filteredSentences.length) {
      setSelectedRows(new Set());
    } else {
      setSelectedRows(new Set(filteredSentences.map(s => s.index)));
    }
  };

  const handleRowSelect = (index: number, event: React.ChangeEvent<HTMLInputElement>) => {
    const newSelected = new Set(selectedRows);
    const nativeEvent = event.nativeEvent as MouseEvent;
    
    // Handle shift-click for range selection
    if (nativeEvent.shiftKey && lastSelectedIndex !== null) {
      const start = Math.min(lastSelectedIndex, index);
      const end = Math.max(lastSelectedIndex, index);
      for (let i = start; i <= end; i++) {
        if (filteredSentences.find(s => s.index === i)) {
          newSelected.add(i);
        }
      }
    } else {
      if (newSelected.has(index)) {
        newSelected.delete(index);
      } else {
        newSelected.add(index);
      }
    }
    
    setSelectedRows(newSelected);
    setLastSelectedIndex(index);
  };

  const handleApproveAll = () => {
    // Simply clear all selections, assuming all are approved
    setSelectedRows(new Set());
  };

  const handleExportSelectedClick = () => {
    if (onExportSelected) {
      onExportSelected(Array.from(selectedRows));
    }
  };

  const getWordCount = (text: string) => {
    return text.trim().split(/\s+/).length;
  };

  const isLongSentence = (text: string) => {
    return getWordCount(text) > LONG_SENTENCE_THRESHOLD;
  };

  const getSentenceToDisplay = (row: { index: number; sentence: string }) => {
    if (viewMode === 'original' && originalSentences.length > 0) {
      return originalSentences[row.index - 1] || row.sentence;
    }
    return row.sentence;
  };

  // Note: For optimal performance with >5k items, consider implementing
  // pagination or a virtualization library like @tanstack/react-virtual

  return (
    <Box>
      {/* Toolbar */}
      <Box sx={{ mb: 2, display: 'flex', gap: 2, flexWrap: 'wrap', alignItems: 'center' }}>
        <TextField
          label="Filter sentences"
          variant="outlined"
          size="small"
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
          sx={{ flex: '1 1 300px' }}
          aria-label="Filter sentences by text"
        />
        
        {originalSentences.length > 0 && (
          <ToggleButtonGroup
            value={viewMode}
            exclusive
            onChange={(_, newMode) => newMode && setViewMode(newMode)}
            size="small"
            aria-label="View mode"
          >
            <ToggleButton value="normalized" aria-label="View normalized">
              Normalized
            </ToggleButton>
            <ToggleButton value="original" aria-label="View original">
              Original
            </ToggleButton>
          </ToggleButtonGroup>
        )}
      </Box>

      {/* Bulk Actions */}
      {selectedRows.size > 0 && (
        <Paper sx={{ p: 2, mb: 2, bgcolor: 'primary.50', border: 1, borderColor: 'primary.main' }}>
          <Stack direction="row" spacing={2} alignItems="center" flexWrap="wrap">
            <Chip 
              label={`${selectedRows.size} selected`} 
              color="primary"
              onDelete={() => setSelectedRows(new Set())}
            />
            <Button
              size="small"
              variant="outlined"
              onClick={handleApproveAll}
              startIcon={<Icon icon={CheckSquare} fontSize="small" />}
            >
              Approve All
            </Button>
            {onExportSelected && (
              <Button
                size="small"
                variant="contained"
                onClick={handleExportSelectedClick}
              >
                Export Selected
              </Button>
            )}
          </Stack>
        </Paper>
      )}

      <TableContainer component={Paper} sx={{ maxHeight: 600 }}>
        <Table stickyHeader>
          <TableHead>
            <TableRow>
              <StyledTableCell padding="checkbox" sx={{ width: '60px' }}>
                <Checkbox
                  checked={selectedRows.size === filteredSentences.length && filteredSentences.length > 0}
                  indeterminate={selectedRows.size > 0 && selectedRows.size < filteredSentences.length}
                  onChange={handleSelectAll}
                  aria-label="Select all sentences"
                />
              </StyledTableCell>
              <StyledTableCell sx={{ width: '80px' }}>
                <TableSortLabel
                  active={orderBy === 'index'}
                  direction={orderBy === 'index' ? order : 'asc'}
                  onClick={(event) => handleRequestSort(event, 'index')}
                  aria-label="Sort by index"
                >
                  Index
                </TableSortLabel>
              </StyledTableCell>
              <StyledTableCell sx={{ width: 'calc(100% - 240px)' }}>
                <TableSortLabel
                  active={orderBy === 'sentence'}
                  direction={orderBy === 'sentence' ? order : 'asc'}
                  onClick={(event) => handleRequestSort(event, 'sentence')}
                  aria-label="Sort by sentence"
                >
                  Sentence
                </TableSortLabel>
              </StyledTableCell>
              <StyledTableCell sx={{ width: '100px' }}>Actions</StyledTableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {filteredSentences.map((row) => {
              const isEditing = editingIndex === row.index;
              const isSelected = selectedRows.has(row.index);
              const displaySentence = getSentenceToDisplay(row);
              const isLong = isLongSentence(displaySentence);
              const wordCount = getWordCount(displaySentence);
              
              return (
                <StyledTableRow 
                  key={row.index}
                  selected={isSelected}
                  sx={{
                    cursor: 'pointer',
                    '&.Mui-selected': {
                      bgcolor: 'primary.50',
                    },
                  }}
                >
                  <StyledTableCell padding="checkbox">
                    <Checkbox
                      checked={isSelected}
                      onChange={(e) => handleRowSelect(row.index, e)}
                      aria-label={`Select sentence ${row.index}`}
                    />
                  </StyledTableCell>
                  <StyledTableCell sx={{ width: '80px' }}>{row.index}</StyledTableCell>
                  <StyledTableCell sx={{ width: 'calc(100% - 240px)' }}>
                    <Box>
                      {isEditing ? (
                        <TextField
                          inputRef={editInputRef}
                          value={editValue}
                          onChange={(e) => setEditValue(e.target.value)}
                          onKeyDown={handleKeyDown}
                          fullWidth
                          multiline
                          size="small"
                          autoFocus
                          aria-label="Edit sentence"
                        />
                      ) : (
                        <>
                          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 0.5 }}>
                            {displaySentence}
                            {isLong && (
                              <Tooltip title={`Long sentence: ${wordCount} words`}>
                                <Box component="span">
                                  <Icon icon={AlertCircle} fontSize="small" color="warning" />
                                </Box>
                              </Tooltip>
                            )}
                          </Box>
                          {isLong && (
                            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mt: 0.5 }}>
                              <LinearProgress 
                                variant="determinate" 
                                value={Math.min((wordCount / 20) * 100, 100)} 
                                sx={{ flex: 1, height: 4, borderRadius: 2 }}
                                color={wordCount > 18 ? 'error' : 'warning'}
                              />
                              <Typography variant="caption" color="text.secondary">
                                {wordCount}w
                              </Typography>
                            </Box>
                          )}
                        </>
                      )}
                    </Box>
                  </StyledTableCell>
                  <StyledTableCell sx={{ width: '100px' }}>
                    {isEditing ? (
                      <Box sx={{ display: 'flex', gap: 0.5 }}>
                        <Tooltip title="Save (Enter)">
                          <IconButton size="small" onClick={saveEdit} color="success" aria-label="Save edit">
                            <Icon icon={Check} fontSize="small" />
                          </IconButton>
                        </Tooltip>
                        <Tooltip title="Cancel (Esc)">
                          <IconButton size="small" onClick={cancelEdit} color="error" aria-label="Cancel edit">
                            <Icon icon={X} fontSize="small" />
                          </IconButton>
                        </Tooltip>
                      </Box>
                    ) : (
                      <Tooltip title="Edit">
                        <IconButton size="small" onClick={() => startEdit(row.index, row.sentence)} aria-label={`Edit sentence ${row.index}`}>
                          <Icon icon={Edit2} fontSize="small" />
                        </IconButton>
                      </Tooltip>
                    )}
                  </StyledTableCell>
                </StyledTableRow>
              );
            })}
          </TableBody>
        </Table>
      </TableContainer>
      <Box sx={{ mt: 2, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Box sx={{ color: 'text.secondary', fontSize: '0.875rem' }}>
          Showing {filteredSentences.length} of {sentences.length} sentences
          {selectedRows.size > 0 && ` (${selectedRows.size} selected)`}
        </Box>
      </Box>
    </Box>
  );
}

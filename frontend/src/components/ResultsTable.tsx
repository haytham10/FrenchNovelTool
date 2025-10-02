import React, { useState, useRef, useEffect } from 'react';
import { Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Paper, TableSortLabel, TextField, Box, IconButton, Tooltip } from '@mui/material';
import { styled } from '@mui/material/styles';
import Icon from './Icon';
import { Edit2, Check, X } from 'lucide-react';
import { useDebounce } from '@/lib/hooks';

interface ResultsTableProps {
  sentences: string[];
  onSentencesChange?: (sentences: string[]) => void;
}

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

export default function ResultsTable({ sentences, onSentencesChange }: ResultsTableProps) {
  const [order, setOrder] = useState<Order>('asc');
  const [orderBy, setOrderBy] = useState<keyof { index: number; sentence: string }>('index');
  const [filter, setFilter] = useState<string>('');
  const debouncedFilter = useDebounce(filter, 300);
  const [editingIndex, setEditingIndex] = useState<number | null>(null);
  const [editValue, setEditValue] = useState<string>('');
  const editInputRef = useRef<HTMLInputElement>(null);

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

  // Note: For optimal performance with >5k items, consider implementing
  // pagination or a virtualization library like @tanstack/react-virtual

  return (
    <Box>
      <TextField
        label="Filter sentences"
        variant="outlined"
        fullWidth
        value={filter}
        onChange={(e) => setFilter(e.target.value)}
        sx={{ mb: 2 }}
        aria-label="Filter sentences by text"
      />
      <TableContainer component={Paper} sx={{ maxHeight: 600 }}>
        <Table stickyHeader>
          <TableHead>
            <TableRow>
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
              <StyledTableCell sx={{ width: 'calc(100% - 160px)' }}>
                <TableSortLabel
                  active={orderBy === 'sentence'}
                  direction={orderBy === 'sentence' ? order : 'asc'}
                  onClick={(event) => handleRequestSort(event, 'sentence')}
                  aria-label="Sort by sentence"
                >
                  Sentence
                </TableSortLabel>
              </StyledTableCell>
              <StyledTableCell sx={{ width: '80px' }}>Actions</StyledTableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {filteredSentences.map((row) => {
              const isEditing = editingIndex === row.index;
              return (
                <StyledTableRow key={row.index}>
                  <StyledTableCell sx={{ width: '80px' }}>{row.index}</StyledTableCell>
                  <StyledTableCell sx={{ width: 'calc(100% - 160px)' }}>
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
                      row.sentence
                    )}
                  </StyledTableCell>
                  <StyledTableCell sx={{ width: '80px' }}>
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
        </Box>
      </Box>
    </Box>
  );
}

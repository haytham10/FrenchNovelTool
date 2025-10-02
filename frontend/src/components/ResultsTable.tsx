import React, { useState } from 'react';
import { Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Paper, TableSortLabel, TextField, Box } from '@mui/material';
import { styled } from '@mui/material/styles';

interface ResultsTableProps {
  sentences: string[];
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

export default function ResultsTable({ sentences }: ResultsTableProps) {
  const [order, setOrder] = useState<Order>('asc');
  const [orderBy, setOrderBy] = useState<keyof { index: number; sentence: string }>('index');
  const [filter, setFilter] = useState<string>('');

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
    if (!filter) return sortedSentences;
    return sortedSentences.filter(item =>
      item.sentence.toLowerCase().includes(filter.toLowerCase())
    );
  }, [sortedSentences, filter]);

  return (
    <Box>
      <TextField
        label="Filter sentences"
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
                  active={orderBy === 'index'}
                  direction={orderBy === 'index' ? order : 'asc'}
                  onClick={(event) => handleRequestSort(event, 'index')}
                >
                  Index
                </TableSortLabel>
              </StyledTableCell>
              <StyledTableCell>
                <TableSortLabel
                  active={orderBy === 'sentence'}
                  direction={orderBy === 'sentence' ? order : 'asc'}
                  onClick={(event) => handleRequestSort(event, 'sentence')}
                >
                  Sentence
                </TableSortLabel>
              </StyledTableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {filteredSentences.map((row) => (
              <StyledTableRow key={row.index}>
                <StyledTableCell>{row.index}</StyledTableCell>
                <StyledTableCell>{row.sentence}</StyledTableCell>
              </StyledTableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>
    </Box>
  );
}

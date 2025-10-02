'use client';

import React, { useState } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  TextField,
  FormControl,
  FormControlLabel,
  RadioGroup,
  Radio,
  Typography,
  Box,
  Divider,
  Switch,
  Chip,
  Stack,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Select,
  MenuItem,
  InputLabel,
} from '@mui/material';
import Icon from './Icon';
import { Download, ChevronDown, Plus, Users, Link as LinkIcon } from 'lucide-react';
import DriveFolderPicker from './DriveFolderPicker';

interface ExportDialogProps {
  open: boolean;
  onClose: () => void;
  onExport: (options: ExportOptions) => void;
  defaultSheetName?: string;
  loading?: boolean;
}

export interface ExportOptions {
  sheetName: string;
  folderId?: string | null;
  folderName?: string | null;
  mode: 'new' | 'append';
  existingSheetId?: string;
  tabName?: string;
  createNewTab?: boolean;
  headers: string[];
  columnOrder: string[];
  sharing: {
    addCollaborators: boolean;
    collaboratorEmails: string[];
    publicLink: boolean;
  };
}

const DEFAULT_HEADERS = ['Index', 'Sentence'];
const DEFAULT_COLUMNS = ['index', 'sentence'];

export default function ExportDialog({
  open,
  onClose,
  onExport,
  defaultSheetName = 'French Novel Sentences',
  loading = false,
}: ExportDialogProps) {
  const [sheetName, setSheetName] = useState(defaultSheetName);
  const [mode, setMode] = useState<'new' | 'append'>('new');
  const [selectedFolderId, setSelectedFolderId] = useState<string | null>(null);
  const [selectedFolderName, setSelectedFolderName] = useState<string | null>(null);
  const [existingSheetId] = useState('');
  const [tabName, setTabName] = useState('Sheet1');
  const [createNewTab] = useState(true);
  const [headers, setHeaders] = useState<string[]>(DEFAULT_HEADERS);
  const [columnOrder] = useState<string[]>(DEFAULT_COLUMNS);
  const [addCollaborators, setAddCollaborators] = useState(false);
  const [collaboratorEmails, setCollaboratorEmails] = useState('');
  const [publicLink, setPublicLink] = useState(false);
  const [showAdvanced, setShowAdvanced] = useState(false);

  const handleFolderSelect = (folderId: string, folderName: string) => {
    setSelectedFolderId(folderId);
    setSelectedFolderName(folderName);
  };

  const handleExport = () => {
    const options: ExportOptions = {
      sheetName,
      folderId: selectedFolderId,
      folderName: selectedFolderName,
      mode,
      existingSheetId: mode === 'append' ? existingSheetId : undefined,
      tabName: mode === 'append' ? tabName : undefined,
      createNewTab: mode === 'append' ? createNewTab : undefined,
      headers,
      columnOrder,
      sharing: {
        addCollaborators,
        collaboratorEmails: collaboratorEmails.split(',').map(e => e.trim()).filter(e => e),
        publicLink,
      },
    };
    onExport(options);
  };

  const handleHeaderChange = (index: number, value: string) => {
    const newHeaders = [...headers];
    newHeaders[index] = value;
    setHeaders(newHeaders);
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth>
      <DialogTitle>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <Icon icon={Download} color="primary" />
          <Typography variant="h6">Export to Google Sheets</Typography>
        </Box>
      </DialogTitle>
      <DialogContent>
        {/* Basic Options */}
        <Box sx={{ mb: 3 }}>
          <FormControl component="fieldset" fullWidth>
            <Typography variant="subtitle2" gutterBottom>
              Export Mode
            </Typography>
            <RadioGroup value={mode} onChange={(e) => setMode(e.target.value as 'new' | 'append')}>
              <FormControlLabel
                value="new"
                control={<Radio />}
                label={
                  <Box>
                    <Typography variant="body2">Create new spreadsheet</Typography>
                    <Typography variant="caption" color="text.secondary">
                      Creates a fresh Google Sheets file
                    </Typography>
                  </Box>
                }
              />
              <FormControlLabel
                value="append"
                control={<Radio />}
                label={
                  <Box>
                    <Typography variant="body2">Append to existing spreadsheet</Typography>
                    <Typography variant="caption" color="text.secondary">
                      Add to an existing sheet or create a new tab
                    </Typography>
                  </Box>
                }
              />
            </RadioGroup>
          </FormControl>
        </Box>

        <TextField
          fullWidth
          label="Spreadsheet Name"
          value={sheetName}
          onChange={(e) => setSheetName(e.target.value)}
          sx={{ mb: 3 }}
          helperText="The name of the Google Sheets file"
          disabled={mode === 'append'}
        />

        {mode === 'append' && (
          <Box sx={{ mb: 3, p: 2, bgcolor: 'action.hover', borderRadius: 2 }}>
            <Typography variant="body2" color="text.secondary" gutterBottom>
              <strong>Note:</strong> Appending to existing sheets is coming soon. This feature will allow you to add results to an existing spreadsheet.
            </Typography>
            <TextField
              fullWidth
              label="Existing Sheet ID"
              placeholder="Enter the Google Sheets ID"
              sx={{ mt: 2, mb: 2 }}
              size="small"
              disabled
            />
            <FormControl fullWidth size="small" sx={{ mb: 2 }}>
              <InputLabel>Tab/Sheet</InputLabel>
              <Select value={createNewTab ? 'new' : tabName} disabled>
                <MenuItem value="new">
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <Icon icon={Plus} fontSize="small" />
                    Create new tab
                  </Box>
                </MenuItem>
                <MenuItem value="Sheet1">Sheet1 (existing)</MenuItem>
              </Select>
            </FormControl>
            {createNewTab && (
              <TextField
                fullWidth
                size="small"
                label="New Tab Name"
                value={tabName}
                onChange={(e) => setTabName(e.target.value)}
                disabled
              />
            )}
          </Box>
        )}

        <DriveFolderPicker 
          onFolderSelect={handleFolderSelect}
          selectedFolderName={selectedFolderName}
        />

        <Divider sx={{ my: 3 }} />

        {/* Advanced Options */}
        <Button
          fullWidth
          variant="text"
          onClick={() => setShowAdvanced(!showAdvanced)}
          endIcon={showAdvanced ? <ChevronDown /> : <ChevronDown />}
          sx={{ mb: 2, transform: showAdvanced ? 'none' : 'rotate(-90deg)' }}
        >
          Advanced Options
        </Button>

        {showAdvanced && (
          <Box>
            {/* Custom Headers */}
            <Accordion>
              <AccordionSummary expandIcon={<Icon icon={ChevronDown} fontSize="small" />}>
                <Typography variant="body2" fontWeight={600}>
                  Customize Headers & Columns
                </Typography>
              </AccordionSummary>
              <AccordionDetails>
                <Typography variant="caption" color="text.secondary" paragraph>
                  Customize the column headers in your exported spreadsheet.
                </Typography>
                {headers.map((header, index) => (
                  <TextField
                    key={index}
                    fullWidth
                    size="small"
                    label={`Column ${index + 1}`}
                    value={header}
                    onChange={(e) => handleHeaderChange(index, e.target.value)}
                    sx={{ mb: 2 }}
                  />
                ))}
              </AccordionDetails>
            </Accordion>

            {/* Sharing Options */}
            <Accordion sx={{ mt: 2 }}>
              <AccordionSummary expandIcon={<Icon icon={ChevronDown} fontSize="small" />}>
                <Typography variant="body2" fontWeight={600}>
                  Sharing Settings
                </Typography>
              </AccordionSummary>
              <AccordionDetails>
                <FormControlLabel
                  control={
                    <Switch
                      checked={publicLink}
                      onChange={(e) => setPublicLink(e.target.checked)}
                    />
                  }
                  label={
                    <Box>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        <Icon icon={LinkIcon} fontSize="small" />
                        <Typography variant="body2">Enable public link</Typography>
                      </Box>
                      <Typography variant="caption" color="text.secondary">
                        Anyone with the link can view
                      </Typography>
                    </Box>
                  }
                  sx={{ mb: 2 }}
                />

                <FormControlLabel
                  control={
                    <Switch
                      checked={addCollaborators}
                      onChange={(e) => setAddCollaborators(e.target.checked)}
                    />
                  }
                  label={
                    <Box>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        <Icon icon={Users} fontSize="small" />
                        <Typography variant="body2">Add collaborators</Typography>
                      </Box>
                      <Typography variant="caption" color="text.secondary">
                        Share with specific people
                      </Typography>
                    </Box>
                  }
                  sx={{ mb: 2 }}
                />

                {addCollaborators && (
                  <Box>
                    <TextField
                      fullWidth
                      size="small"
                      label="Collaborator Emails"
                      placeholder="email1@example.com, email2@example.com"
                      value={collaboratorEmails}
                      onChange={(e) => setCollaboratorEmails(e.target.value)}
                      helperText="Enter email addresses separated by commas"
                      multiline
                      rows={2}
                    />
                    <Box sx={{ mt: 1 }}>
                      <Typography variant="caption" color="text.secondary">
                        Note: Sharing features are coming soon
                      </Typography>
                    </Box>
                  </Box>
                )}
              </AccordionDetails>
            </Accordion>
          </Box>
        )}

        {/* Summary */}
        <Box sx={{ mt: 3, p: 2, bgcolor: 'primary.50', borderRadius: 2, border: 1, borderColor: 'primary.main' }}>
          <Typography variant="body2" fontWeight={600} gutterBottom>
            Export Summary
          </Typography>
          <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
            <Chip label={mode === 'new' ? 'New Sheet' : 'Append'} size="small" color="primary" />
            {selectedFolderName && <Chip label={selectedFolderName} size="small" variant="outlined" />}
            {publicLink && <Chip label="Public Link" size="small" variant="outlined" />}
            {addCollaborators && collaboratorEmails && (
              <Chip label={`${collaboratorEmails.split(',').length} Collaborators`} size="small" variant="outlined" />
            )}
          </Stack>
        </Box>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose} disabled={loading}>
          Cancel
        </Button>
        <Button onClick={handleExport} variant="contained" disabled={loading || !sheetName.trim()}>
          {loading ? 'Exporting...' : 'Export'}
        </Button>
      </DialogActions>
    </Dialog>
  );
}

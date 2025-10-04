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
  const [isPickerOpen, setIsPickerOpen] = useState(false);

  const handleFolderSelect = (folderId: string, folderName: string) => {
    setSelectedFolderId(folderId);
    setSelectedFolderName(folderName);
    setIsPickerOpen(false);
  };

  const handlePickerOpen = () => {
    setIsPickerOpen(true);
  };

  const handlePickerCancel = () => {
    setIsPickerOpen(false);
  };

  const handleClearFolder = () => {
    setSelectedFolderId(null);
    setSelectedFolderName(null);
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
    <Dialog 
      open={open && !isPickerOpen} 
      onClose={onClose} 
      maxWidth="md" 
      fullWidth
      aria-labelledby="export-dialog-title"
      aria-describedby="export-dialog-description"
      slotProps={{
        backdrop: {
          sx: { opacity: isPickerOpen ? 0 : undefined }
        }
      }}
    >
      <DialogTitle id="export-dialog-title">
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <Icon icon={Download} color="primary" />
          <Typography variant="h6">Export to Google Sheets</Typography>
        </Box>
        <Typography 
          id="export-dialog-description" 
          variant="body2" 
          color="text.secondary" 
          sx={{ mt: 1 }}
        >
          Configure your export settings and send your processed sentences to Google Sheets
        </Typography>
      </DialogTitle>
      <DialogContent sx={{ pt: 2 }}>
        {/* Basic Options */}
        <Box sx={{ mb: 3 }}>
          <FormControl component="fieldset" fullWidth>
            <Typography variant="subtitle2" gutterBottom fontWeight={600}>
              Export Destination
            </Typography>
            <RadioGroup 
              value={mode} 
              onChange={(e) => setMode(e.target.value as 'new' | 'append')}
              aria-label="Export destination mode"
            >
              <FormControlLabel
                value="new"
                control={<Radio />}
                label={
                  <Box>
                    <Typography variant="body2" fontWeight={500}>Create new spreadsheet</Typography>
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
                    <Typography variant="body2" fontWeight={500}>Append to existing spreadsheet</Typography>
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
          required
          error={!sheetName.trim() && mode === 'new'}
          aria-label="Spreadsheet name"
          inputProps={{
            'aria-required': mode === 'new',
            'aria-invalid': !sheetName.trim() && mode === 'new',
          }}
        />

        {mode === 'append' && (
          <Box sx={{ mb: 3, p: 2, bgcolor: 'action.hover', borderRadius: 2, border: 1, borderColor: 'divider' }}>
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
          onClearSelection={handleClearFolder}
          onPickerOpen={handlePickerOpen}
          onPickerCancel={handlePickerCancel}
        />

        <Divider sx={{ my: 3 }} />

        {/* Advanced Options */}
        <Button
          fullWidth
          variant="text"
          onClick={() => setShowAdvanced(!showAdvanced)}
          endIcon={<Icon icon={ChevronDown} sx={{ transform: showAdvanced ? 'rotate(180deg)' : 'none', transition: 'transform 0.2s' }} />}
          sx={{ 
            mb: 2,
            justifyContent: 'space-between',
            '&:focus-visible': {
              outline: '2px solid',
              outlineColor: 'primary.main',
              outlineOffset: '2px',
            },
          }}
          aria-expanded={showAdvanced}
          aria-label="Toggle advanced options"
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
        <Box sx={{ mt: 3, p: 2.5, bgcolor: 'primary.50', borderRadius: 2, border: 1, borderColor: 'primary.200' }}>
          <Typography variant="body2" fontWeight={600} gutterBottom sx={{ color: 'primary.main' }}>
            📊 Export Summary
          </Typography>
          <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap sx={{ mt: 1.5 }}>
            <Chip label={mode === 'new' ? 'New Sheet' : 'Append'} size="small" color="primary" />
            <Chip label={sheetName || 'Unnamed'} size="small" color="primary" variant="outlined" />
            {selectedFolderName && <Chip label={`📁 ${selectedFolderName}`} size="small" variant="outlined" />}
            {publicLink && <Chip label="🔗 Public Link" size="small" variant="outlined" />}
            {addCollaborators && collaboratorEmails && (
              <Chip label={`👥 ${collaboratorEmails.split(',').filter(e => e.trim()).length} Collaborators`} size="small" variant="outlined" />
            )}
          </Stack>
        </Box>
      </DialogContent>
      <DialogActions sx={{ px: 3, py: 2, gap: 1 }}>
        <Button 
          onClick={onClose} 
          disabled={loading}
          variant="outlined"
          sx={{
            '&:focus-visible': {
              outline: '2px solid',
              outlineColor: 'primary.main',
              outlineOffset: '2px',
            },
          }}
        >
          Cancel
        </Button>
        <Button 
          onClick={handleExport} 
          variant="contained" 
          disabled={loading || !sheetName.trim()}
          sx={{
            minWidth: 120,
            '&:focus-visible': {
              outline: '2px solid',
              outlineColor: 'primary.dark',
              outlineOffset: '2px',
            },
          }}
          aria-label={loading ? 'Exporting to Google Sheets' : 'Export to Google Sheets'}
        >
          {loading ? 'Exporting...' : 'Export'}
        </Button>
      </DialogActions>
    </Dialog>
  );
}

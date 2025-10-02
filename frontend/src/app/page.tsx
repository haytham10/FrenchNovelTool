"use client";

import React, { useState } from 'react';
import FileUpload from '@/components/FileUpload';
import ResultsTable from '@/components/ResultsTable';
import DriveFolderPicker from '@/components/DriveFolderPicker';
import { processPdf, exportToSheet, getApiErrorMessage } from '@/lib/api';
import { CircularProgress, Button, Typography, Box, TextField, Container } from '@mui/material';
import { useSnackbar } from 'notistack';
import UploadStepper from '@/components/UploadStepper';
import ResultsSkeleton from '@/components/ResultsSkeleton';
import EmptyState from '@/components/EmptyState';

export default function Home() {
  const [sentences, setSentences] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [loadingMessage, setLoadingMessage] = useState<string>('');
  const [sheetName, setSheetName] = useState<string>('French Novel Sentences');
  const [selectedFolderId, setSelectedFolderId] = useState<string | null>(null);
  const [selectedFolderName, setSelectedFolderName] = useState<string | null>(null);
  const { enqueueSnackbar } = useSnackbar();

  const handleFileUpload = async (files: File[]) => {
    setLoading(true);
    setLoadingMessage('Uploading and processing PDF(s)...');
    setSentences([]);

    let allProcessedSentences: string[] = [];

    try {
      for (const file of files) {
        setLoadingMessage(`Processing ${file.name}...`);
        const sentences = await processPdf(file);
        allProcessedSentences = allProcessedSentences.concat(sentences);
      }
      setSentences(allProcessedSentences);
      enqueueSnackbar('PDF(s) processed successfully!', { variant: 'success' });
    } catch (error) {
      enqueueSnackbar(
        getApiErrorMessage(error, 'An unexpected error occurred while processing the PDF(s).'),
        { variant: 'error' }
      );
    } finally {
      setLoading(false);
      setLoadingMessage('');
    }
  };

  const handleFolderSelect = (folderId: string, folderName: string) => {
    setSelectedFolderId(folderId);
    setSelectedFolderName(folderName);
    enqueueSnackbar(`Selected folder: ${folderName}`, { variant: 'info' });
  };

  const handleExport = async () => {
    if (sentences.length === 0) {
      enqueueSnackbar('Please process PDF file(s) first.', { variant: 'warning' });
      return;
    }

    setLoading(true);
    setLoadingMessage('Exporting to Google Sheets...');

    try {
      const spreadsheetUrl = await exportToSheet({
        sentences,
        sheetName,
        folderId: selectedFolderId,
      });
      window.open(spreadsheetUrl, '_blank');
      enqueueSnackbar('Exported to Google Sheets successfully!', { variant: 'success' });
    } catch (error) {
      enqueueSnackbar(
        getApiErrorMessage(error, 'An unexpected error occurred during the export.'),
        { variant: 'error' }
      );
    } finally {
      setLoading(false);
      setLoadingMessage('');
    }
  };

  return (
    <Box sx={{ minHeight: 'calc(100vh - 64px)', py: { xs: 4, md: 8 } }} className="hero-aura">
      <Container maxWidth="lg" sx={{ position: 'relative', zIndex: 1 }}>
        <Box sx={{ textAlign: 'center', mb: 6 }}>
          <Typography variant="h1" sx={{ mb: 1 }} className="gradient-text">Process French Novels with AI</Typography>
          <Typography variant="subtitle1" color="text.secondary">
            Upload PDFs, normalize sentences with Gemini, and export to Google Sheets.
          </Typography>
          <Box sx={{ mt: 3, display: 'flex', gap: 2, justifyContent: 'center' }}>
            <Button variant="contained" size="large">Upload PDF</Button>
            <Button variant="outlined" size="large" href="#how-it-works">How it works</Button>
          </Box>
        </Box>
        <Box className="card-gradient" sx={{ mb: 4 }}>
          <Box className="inner" sx={{ p: { xs: 2, md: 4 } }}>
          <UploadStepper activeStep={loading ? 1 : sentences.length ? 3 : 0} />
          <FileUpload onFileUpload={handleFileUpload} />
          {!loading && sentences.length === 0 && (
            <EmptyState />
          )}
          {loading && (
            <Box display="flex" flexDirection="column" alignItems="center" mt={4}>
              <CircularProgress />
              <Typography variant="body1" color="textSecondary" mt={2}>
                {loadingMessage}
              </Typography>
            </Box>
          )}
          </Box>
        </Box>
        {loading && (
          <Box className="card-gradient">
            <Box className="inner" sx={{ p: { xs: 2, md: 4 } }}>
              <ResultsSkeleton />
            </Box>
          </Box>
        )}
        {!loading && sentences.length > 0 && (
          <Box className="card-gradient">
            <Box className="inner" sx={{ p: { xs: 2, md: 4 } }}>
            <Box display="flex" justifyContent="space-between" alignItems="center" mb={4}>
              <Typography variant="h2" component="h2" color="textPrimary">
                Results
              </Typography>
              <Box>
                <TextField
                  label="Spreadsheet Name"
                  variant="outlined"
                  value={sheetName}
                  onChange={(e) => setSheetName(e.target.value)}
                  fullWidth
                  sx={{ mb: 2 }}
                />
                <DriveFolderPicker onFolderSelect={handleFolderSelect} selectedFolderName={selectedFolderName} />
                <Button 
                  onClick={handleExport}
                  variant="contained"
                  color="primary"
                  disabled={loading}
                  sx={{ mt: 2, width: '100%' }}
                >
                  Export to Google Sheets
                </Button>
              </Box>
            </Box>
            <ResultsTable sentences={sentences} />
            </Box>
          </Box>
        )}
      </Container>
    </Box>
  );
}
"use client";

import React, { useState } from 'react';
import FileUpload from '@/components/FileUpload';
import ResultsTable from '@/components/ResultsTable';
import NormalizeControls from '@/components/NormalizeControls';
import ExportDialog from '@/components/ExportDialog';
import { processPdf, exportToSheet, getApiErrorMessage } from '@/lib/api';
import { CircularProgress, Button, Typography, Box, Container } from '@mui/material';
import { useSnackbar } from 'notistack';
import UploadStepper from '@/components/UploadStepper';
import ResultsSkeleton from '@/components/ResultsSkeleton';
import EmptyState from '@/components/EmptyState';

import type { AdvancedNormalizationOptions } from '@/components/NormalizeControls';
import type { ExportOptions } from '@/components/ExportDialog';

export default function Home() {
  const [sentences, setSentences] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [loadingMessage, setLoadingMessage] = useState<string>('');
  const [sentenceLength, setSentenceLength] = useState<number>(12);
  const [advancedOptions, setAdvancedOptions] = useState<AdvancedNormalizationOptions>({
    geminiModel: 'balanced',
    ignoreDialogues: false,
    preserveQuotes: true,
    fixHyphenations: true,
    minSentenceLength: 3,
  });
  const [exportDialogOpen, setExportDialogOpen] = useState(false);
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

  const handleExport = async (options: ExportOptions) => {
    if (sentences.length === 0) {
      enqueueSnackbar('Please process PDF file(s) first.', { variant: 'warning' });
      return;
    }

    setLoading(true);
    setLoadingMessage('Exporting to Google Sheets...');

    try {
      const spreadsheetUrl = await exportToSheet({
        sentences,
        sheetName: options.sheetName,
        folderId: options.folderId,
      });
      setExportDialogOpen(false);
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
        {/* Hero Section */}
        <Box sx={{ textAlign: 'center', mb: 6 }}>
          <Typography variant="h1" sx={{ mb: 2 }} className="gradient-text">
            Process French Novels with AI
          </Typography>
          <Typography variant="h5" color="text.secondary" sx={{ mb: 4, maxWidth: '800px', mx: 'auto' }}>
            Upload PDFs, normalize sentences with Gemini, and export to Google Sheets.
          </Typography>
          <Box sx={{ display: 'flex', gap: 2, justifyContent: 'center', flexWrap: 'wrap', maxWidth: '500px', mx: 'auto' }}>
            <Box sx={{ flex: '1 1 auto', minWidth: '200px' }}>
              <FileUpload onFileUpload={handleFileUpload} disabled={loading} />
            </Box>
            <Button variant="outlined" size="large" href="#how-it-works" sx={{ minWidth: '150px' }}>
              How it works
            </Button>
          </Box>
        </Box>

        {/* Processing Stepper - Subdued */}
        <Box sx={{ mb: 4, opacity: 0.8 }}>
          <UploadStepper activeStep={loading ? 1 : sentences.length ? 3 : 0} />
        </Box>

        {/* Empty State */}
        {!loading && sentences.length === 0 && (
          <Box className="card-gradient" sx={{ mb: 4 }}>
            <Box className="inner" sx={{ p: { xs: 2, md: 4 } }}>
              <EmptyState />
            </Box>
          </Box>
        )}

        {/* Loading State */}
        {loading && (
          <Box className="card-gradient" sx={{ mb: 4 }}>
            <Box className="inner" sx={{ p: { xs: 2, md: 4 } }}>
              <Box display="flex" flexDirection="column" alignItems="center" py={6}>
                <CircularProgress size={48} />
                <Typography variant="h6" color="textSecondary" mt={3}>
                  {loadingMessage}
                </Typography>
              </Box>
            </Box>
          </Box>
        )}
        
        
        {/* Normalize Controls Section */}
        {!loading && sentences.length === 0 && (
          <Box className="card-gradient" sx={{ mb: 4 }}>
            <Box className="inner" sx={{ p: { xs: 2, md: 4 } }}>
              <NormalizeControls
                sentenceLength={sentenceLength}
                onSentenceLengthChange={setSentenceLength}
                disabled={loading}
                advancedOptions={advancedOptions}
                onAdvancedOptionsChange={setAdvancedOptions}
              />
              <Box sx={{ mt: 3 }}>
                <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                  <strong>Note:</strong> These settings will be applied during PDF processing.
                </Typography>
              </Box>
            </Box>
          </Box>
        )}
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
                <Button 
                  onClick={() => setExportDialogOpen(true)}
                  variant="contained"
                  color="primary"
                  disabled={loading}
                  size="large"
                >
                  Export to Google Sheets
                </Button>
              </Box>
              <ResultsTable sentences={sentences} />
            </Box>
          </Box>
        )}

        {/* Export Dialog */}
        <ExportDialog
          open={exportDialogOpen}
          onClose={() => setExportDialogOpen(false)}
          onExport={handleExport}
          loading={loading}
          defaultSheetName="French Novel Sentences"
        />
      </Container>
    </Box>
  );
}
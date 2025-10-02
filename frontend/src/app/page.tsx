"use client";

import React, { useState } from 'react';
import FileUpload from '@/components/FileUpload';
import ResultsTable from '@/components/ResultsTable';
import NormalizeControls from '@/components/NormalizeControls';
import ExportDialog from '@/components/ExportDialog';
import { getApiErrorMessage } from '@/lib/api';
import { useProcessPdf, useExportToSheet } from '@/lib/queries';
import { CircularProgress, Button, Typography, Box, Container, Paper, Divider, List, ListItem, ListItemText, LinearProgress } from '@mui/material';
import { useSnackbar } from 'notistack';
import UploadStepper from '@/components/UploadStepper';
import ResultsSkeleton from '@/components/ResultsSkeleton';
import Link from 'next/link';
import { useAuth } from '@/components/AuthContext';
import GoogleLoginButton from '@/components/GoogleLoginButton';
import { useProcessingStore } from '@/stores/useProcessingStore';
import Icon from '@/components/Icon';
import { Download } from 'lucide-react';

import type { ExportOptions } from '@/components/ExportDialog';

export default function Home() {
  const { user } = useAuth();
  const [exportDialogOpen, setExportDialogOpen] = useState(false);
  const { enqueueSnackbar } = useSnackbar();
  
  // Use Zustand store for processing state
  const {
    sentences,
    setSentences,
    loading,
    loadingMessage,
    setLoading,
    uploadProgress,
    setUploadProgress,
    sentenceLength,
    setSentenceLength,
    advancedOptions,
    setAdvancedOptions,
  } = useProcessingStore();
  
  // Use React Query for API calls
  const processPdfMutation = useProcessPdf();
  const exportMutation = useExportToSheet();

  const handleFileUpload = async (files: File[]) => {
    setLoading(true, 'Uploading and processing PDF(s)...');
    setSentences([]);

    let allProcessedSentences: string[] = [];

    try {
      for (const file of files) {
        setLoading(true, `Processing ${file.name}...`);
        setUploadProgress(0);
        
        const sentences = await processPdfMutation.mutateAsync({
          file,
          options: {
            onUploadProgress: (progress) => {
              setUploadProgress(progress);
            },
          },
        });
        
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
      setLoading(false, '');
      setUploadProgress(0);
    }
  };

  const handleExport = async (options: ExportOptions) => {
    if (sentences.length === 0) {
      enqueueSnackbar('Please process PDF file(s) first.', { variant: 'warning' });
      return;
    }

    setLoading(true, 'Exporting to Google Sheets...');

    try {
      const spreadsheetUrl = await exportMutation.mutateAsync({
        sentences,
        sheetName: options.sheetName,
        folderId: options.folderId,
      });
      setExportDialogOpen(false);
      window.open(spreadsheetUrl, '_blank');
    } catch (error) {
      enqueueSnackbar(
        getApiErrorMessage(error, 'An unexpected error occurred during the export.'),
        { variant: 'error' }
      );
    } finally {
      setLoading(false, '');
    }
  };

  return (
    <Box sx={{ minHeight: 'calc(100vh - 64px)', py: { xs: 4, md: 8 } }} className="hero-aura">
        <Container maxWidth="lg" sx={{ position: 'relative', zIndex: 1 }}>
          {/* Hero Section - Enhanced */}
        <Box sx={{ textAlign: 'center', mb: 6 }}>
          <Typography 
            variant="h1" 
            sx={{ 
              mb: 2,
              fontSize: { xs: '2.5rem', md: '3.5rem' },
              fontWeight: 700,
            }} 
            className="gradient-text"
          >
            Process French Novels with AI
          </Typography>
          <Typography 
            variant="h5" 
            color="text.secondary" 
            sx={{ 
              mb: 4, 
              maxWidth: '800px', 
              mx: 'auto',
              fontSize: { xs: '1.1rem', md: '1.3rem' },
              lineHeight: 1.6,
            }}
          >
            Upload PDFs, normalize sentences with Gemini AI, and export to Google Sheets.
            Fast, intelligent, and easy to use.
          </Typography>
          <Box sx={{ display: 'flex', gap: 2, justifyContent: 'center', flexWrap: 'wrap', maxWidth: '640px', mx: 'auto' }}>
            {user ? (
              <Box sx={{ flex: '1 1 auto', minWidth: '240px' }}>
                <FileUpload onFileUpload={handleFileUpload} disabled={loading} />
              </Box>
            ) : (
              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                <Typography variant="body1" color="text.secondary">
                  To process PDFs and export to your Google Sheets, please sign in with Google.
                </Typography>
                <Box sx={{ display: 'flex', justifyContent: 'center' }}>
                  <GoogleLoginButton />
                </Box>
              </Box>
            )}
            <Button 
              variant="outlined" 
              size="large" 
              href="#about" 
              sx={{ 
                minWidth: '150px',
                '&:focus-visible': {
                  outline: '3px solid',
                  outlineColor: 'primary.main',
                  outlineOffset: '2px',
                },
              }}
            >
              Learn more
            </Button>
          </Box>
        </Box>

        {/* Processing Stepper - Now sticky and subdued */}
        {(loading || sentences.length > 0) && (
          <UploadStepper activeStep={loading ? 1 : sentences.length ? 3 : 0} />
        )}

        {/* Empty State with Drag-and-Drop */}
        {!loading && sentences.length === 0 && user && (
          <Box className="card-gradient" sx={{ mb: 4 }}>
            <Box className="inner" sx={{ p: { xs: 2, md: 4 } }}>
              <FileUpload onFileUpload={handleFileUpload} disabled={loading} variant="dropzone" />
            </Box>
          </Box>
        )}

        {/* Loading State with Enhanced Visual Feedback */}
        {loading && (
          <Box className="card-gradient" sx={{ mb: 4 }}>
            <Box className="inner" sx={{ p: { xs: 2, md: 4 } }}>
              <Box 
                display="flex" 
                flexDirection="column" 
                alignItems="center" 
                py={6}
                sx={{
                  minHeight: '300px',
                  justifyContent: 'center',
                }}
              >
                <Box
                  sx={{
                    position: 'relative',
                    display: 'inline-flex',
                    mb: 3,
                  }}
                >
                  <CircularProgress 
                    size={56} 
                    thickness={4}
                    sx={{
                      color: 'primary.main',
                    }}
                  />
                  <Box
                    sx={{
                      position: 'absolute',
                      top: 0,
                      left: 0,
                      bottom: 0,
                      right: 0,
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                    }}
                  >
                    <Typography
                      variant="caption"
                      component="div"
                      color="primary"
                      fontWeight={600}
                    >
                      {uploadProgress > 0 && uploadProgress < 100 ? `${uploadProgress}%` : ''}
                    </Typography>
                  </Box>
                </Box>
                <Typography 
                  variant="h6" 
                  color="textPrimary" 
                  sx={{ 
                    fontWeight: 500,
                    mb: 1,
                  }}
                >
                  {loadingMessage}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Please wait while we process your file...
                </Typography>
                {uploadProgress > 0 && uploadProgress < 100 && (
                  <Box sx={{ width: '100%', maxWidth: 450, mt: 3 }}>
                    <LinearProgress 
                      variant="determinate" 
                      value={uploadProgress}
                      sx={{ 
                        height: 8, 
                        borderRadius: 4,
                        bgcolor: 'action.hover',
                        '& .MuiLinearProgress-bar': {
                          borderRadius: 4,
                        },
                      }}
                    />
                  </Box>
                )}
              </Box>
            </Box>
          </Box>
        )}
        
        
        {/* Normalize Controls Section - Always visible when not loading */}
        {!loading && user && (
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
                  <strong>Note:</strong> These settings will be applied during the next PDF processing.
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
        {!loading && user && sentences.length > 0 && (
          <Box className="card-gradient">
            <Box className="inner" sx={{ p: { xs: 2, md: 4 } }}>
              <Box 
                sx={{
                  display: 'flex', 
                  justifyContent: 'space-between', 
                  alignItems: 'center', 
                  mb: 3,
                  flexWrap: 'wrap',
                  gap: 2,
                }}
              >
                <Box>
                  <Typography 
                    variant="h2" 
                    component="h2" 
                    sx={{ 
                      fontSize: { xs: '1.75rem', md: '2.125rem' },
                      fontWeight: 600,
                      mb: 0.5,
                    }}
                  >
                    Results
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Review and export your processed sentences
                  </Typography>
                </Box>
                <Button 
                  onClick={() => setExportDialogOpen(true)}
                  variant="contained"
                  color="primary"
                  disabled={loading}
                  size="large"
                  startIcon={<Icon icon={Download} />}
                  sx={{
                    minWidth: 200,
                    fontWeight: 600,
                    boxShadow: 2,
                    '&:hover': {
                      boxShadow: 4,
                    },
                    '&:focus-visible': {
                      outline: '3px solid',
                      outlineColor: 'primary.dark',
                      outlineOffset: '2px',
                    },
                  }}
                  aria-label="Export results to Google Sheets"
                >
                  Export to Sheets
                </Button>
              </Box>
              <ResultsTable sentences={sentences} advancedOptions={advancedOptions} />
            </Box>
          </Box>
        )}

        {/* Export Dialog */}
        {user && (
          <ExportDialog
            open={exportDialogOpen}
            onClose={() => setExportDialogOpen(false)}
            onExport={handleExport}
            loading={loading}
            defaultSheetName="French Novel Sentences"
          />
        )}

        {/* Public About & Data Usage sections for transparency and verification */}
        <Box id="about" sx={{ mt: 6 }}>
          <Paper variant="outlined" sx={{ p: { xs: 2, md: 4 } }}>
            <Typography variant="h4" gutterBottom>
              About French Novel Tool
            </Typography>
            <Typography variant="body1" color="text.secondary" paragraph>
              French Novel Tool helps you process French-language PDF novels, intelligently split
              long sentences using Google Gemini, and export the results to your Google Sheets for
              study, editing, or sharing.
            </Typography>
            <Divider sx={{ my: 2 }} />
            <Typography variant="h5" gutterBottom>
              Why we request Google permissions
            </Typography>
            <List>
              <ListItem>
                <ListItemText
                  primary="Basic profile (email, name, picture)"
                  secondary="Used to identify your account and personalize your experience."
                />
              </ListItem>
              <ListItem>
                <ListItemText
                  primary="Google Drive/Sheets access"
                  secondary="Used only when you explicitly export results — to create or update a spreadsheet in your Google Drive."
                />
              </ListItem>
            </List>
            <Typography variant="h5" gutterBottom>
              How we handle your data
            </Typography>
            <List>
              <ListItem>
                <ListItemText
                  primary="We don’t sell your data"
                  secondary="Your information is used solely to provide the functionality you request."
                />
              </ListItem>
              <ListItem>
                <ListItemText
                  primary="You control access"
                  secondary="You can revoke Google access at any time from your Google Account settings."
                />
              </ListItem>
            </List>
            <Typography variant="body2" color="text.secondary">
              For full details, see our{' '}
              <Link href="/policy" style={{ textDecoration: 'underline' }}>Privacy Policy</Link>{' '}
              and{' '}
              <Link href="/terms" style={{ textDecoration: 'underline' }}>Terms of Service</Link>.
            </Typography>
          </Paper>
        </Box>

        {/* Footer links for policy/compliance */}
        <Box sx={{ mt: 6, textAlign: 'center' }}>
          <Typography variant="body2" color="text.secondary">
            Read our{' '}
            <Link href="/policy" style={{ textDecoration: 'underline' }}>
              Privacy Policy
            </Link>
            .
          </Typography>
        </Box>
        </Container>
      </Box>
  );
}
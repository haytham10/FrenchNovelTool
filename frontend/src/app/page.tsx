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
import { Download, BookOpenText, Zap, CheckCircle, Shield, User } from 'lucide-react';
import { fadeIn, float } from '@/lib/animations';

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

    // Open a blank tab immediately to avoid popup blockers
    const newTab = window.open('about:blank', '_blank');

    try {
      const spreadsheetUrl = await exportMutation.mutateAsync({
        sentences,
        sheetName: options.sheetName,
        folderId: options.folderId,
      });
      setExportDialogOpen(false);
      if (newTab) {
        newTab.location.href = spreadsheetUrl;
      }
    } catch (error) {
      if (newTab) newTab.close();
      enqueueSnackbar(
        getApiErrorMessage(error, 'An unexpected error occurred during the export.'),
        { variant: 'error' }
      );
    } finally {
      setLoading(false, '');
    }
  };

  return (
    <Box
      sx={{
        position: 'relative',
        minHeight: 'calc(100vh - 64px)',
        py: { xs: 4, md: 8 },
        overflow: 'visible',
        '&::before, &::after': {
          content: '""',
          position: 'absolute',
          pointerEvents: 'none',
          filter: 'blur(60px)',
          opacity: 0.6,
          zIndex: 0,
        },
        '&::before': {
          top: { xs: '-60px', md: '-80px' },
          left: { xs: '5%', md: '10%' },
          width: { xs: '200px', md: '260px' },
          height: { xs: '200px', md: '260px' },
          background: 'radial-gradient(closest-side, rgba(124,156,255,0.55), rgba(124,156,255,0) 70%)',
          animation: `${float} 9s ease-in-out infinite`,
        },
        '&::after': {
          top: { xs: '-20px', md: '-40px' },
          right: { xs: '5%', md: '15%' },
          width: { xs: '260px', md: '320px' },
          height: { xs: '260px', md: '320px' },
          background: 'radial-gradient(closest-side, rgba(6,182,212,0.45), rgba(6,182,212,0) 70%)',
          animation: `${float} 11s ease-in-out infinite`,
          animationDirection: 'reverse',
        },
      }}
    >
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
              <Paper 
                elevation={0}
                className="glass"
                sx={{ 
                  p: 4, 
                  mb: 2,
                  width: '100%',
                  maxWidth: '520px',
                  textAlign: 'center',
                  transition: 'all 300ms cubic-bezier(0.4, 0, 0.2, 1)',
                  '&:hover': {
                    transform: 'translateY(-2px)',
                    boxShadow: '0 12px 40px -8px rgba(59, 130, 246, 0.25)',
                  }
                }}
              >
                <Typography variant="h6" sx={{ mb: 2, fontWeight: 600 }}>
                  Ready to transform your French literature?
                </Typography>
                <Typography variant="body1" color="text.secondary" sx={{ mb: 3 }}>
                  Sign in with Google to start processing PDFs and exporting to your Google Sheets.
                </Typography>
                <GoogleLoginButton />
              </Paper>
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
                    animation: `${fadeIn} 0.4s ease-out`,
                    animationFillMode: 'both',
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
                    animation: `${fadeIn} 0.5s ease-out`,
                    animationFillMode: 'both',
                  }}
                >
                  {loadingMessage}
                </Typography>
                <Typography 
                  variant="body2" 
                  color="text.secondary"
                  sx={{
                    animation: `${fadeIn} 0.6s ease-out`,
                    animationFillMode: 'both',
                  }}
                >
                  Please wait while we process your file...
                </Typography>
                {uploadProgress > 0 && uploadProgress < 100 && (
                  <Box 
                    sx={{ 
                      width: '100%', 
                      maxWidth: 450, 
                      mt: 3,
                      animation: `${fadeIn} 0.7s ease-out`,
                      animationFillMode: 'both',
                    }}
                  >
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
          <Box 
            className="card-gradient"
            sx={{
              animation: `${fadeIn} 0.6s ease-out`,
              animationFillMode: 'both',
            }}
          >
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
          <Paper 
            elevation={3} 
            sx={{ 
              p: { xs: 3, md: 5 },
              background: 'linear-gradient(135deg, rgba(124,156,255,0.05) 0%, rgba(6,182,212,0.05) 100%)',
              border: 1,
              borderColor: 'divider',
            }}
          >
            <Box sx={{ textAlign: 'center', mb: 4 }}>
              <Typography variant="h3" gutterBottom fontWeight={700}>
                About French Novel Tool
              </Typography>
              <Typography variant="h6" color="text.secondary" sx={{ maxWidth: 800, mx: 'auto' }}>
                Transform how you read and study French literature with AI-powered sentence processing
              </Typography>
            </Box>
            
            <Box sx={{ display: 'flex', flexDirection: { xs: 'column', md: 'row' }, gap: 4, mb: 4 }}>
              <Paper 
                elevation={0}
                className="card-hover"
                sx={{ 
                  flex: 1, 
                  textAlign: 'center', 
                  p: 4, 
                  border: 1, 
                  borderColor: 'divider',
                  borderRadius: 3,
                  cursor: 'pointer',
                  '&:hover .feature-icon': {
                    transform: 'scale(1.1) rotate(5deg)',
                  }
                }}
              >
                <Box className="feature-icon" sx={{ 
                  transition: 'transform 300ms cubic-bezier(0.4, 0, 0.2, 1)',
                  display: 'inline-block'
                }}>
                  <Icon icon={BookOpenText} sx={{ fontSize: 56, color: 'primary.main', mb: 2 }} />
                </Box>
                <Typography variant="h6" gutterBottom fontWeight={600}>
                  Smart Processing
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Upload French PDF novels and let our AI intelligently split long, complex sentences into digestible chunks perfect for learning
                </Typography>
              </Paper>
              <Paper 
                elevation={0}
                className="card-hover"
                sx={{ 
                  flex: 1, 
                  textAlign: 'center', 
                  p: 4, 
                  border: 1, 
                  borderColor: 'divider',
                  borderRadius: 3,
                  cursor: 'pointer',
                  '&:hover .feature-icon': {
                    transform: 'scale(1.1) rotate(-5deg)',
                  }
                }}
              >
                <Box className="feature-icon" sx={{ 
                  transition: 'transform 300ms cubic-bezier(0.4, 0, 0.2, 1)',
                  display: 'inline-block'
                }}>
                  <Icon icon={Zap} sx={{ fontSize: 56, color: 'primary.main', mb: 2 }} />
                </Box>
                <Typography variant="h6" gutterBottom fontWeight={600}>
                  Powered by Gemini
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Leverages Google&apos;s Gemini AI to understand context and preserve meaning while normalizing sentence structure
                </Typography>
              </Paper>
              <Paper 
                elevation={0}
                className="card-hover"
                sx={{ 
                  flex: 1, 
                  textAlign: 'center', 
                  p: 4, 
                  border: 1, 
                  borderColor: 'divider',
                  borderRadius: 3,
                  cursor: 'pointer',
                  '&:hover .feature-icon': {
                    transform: 'scale(1.1) rotate(5deg)',
                  }
                }}
              >
                <Box className="feature-icon" sx={{ 
                  transition: 'transform 300ms cubic-bezier(0.4, 0, 0.2, 1)',
                  display: 'inline-block'
                }}>
                  <Icon icon={CheckCircle} sx={{ fontSize: 56, color: 'primary.main', mb: 2 }} />
                </Box>
                <Typography variant="h6" gutterBottom fontWeight={600}>
                  Seamless Export
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Export processed sentences directly to Google Sheets with one click for easy study, annotation, and sharing
                </Typography>
              </Paper>
            </Box>

            <Divider sx={{ my: 4 }} />
            
            <Box sx={{ mb: 4 }}>
              <Typography variant="h5" gutterBottom fontWeight={600}>
                Privacy & Permissions
              </Typography>
              <Typography variant="body1" color="text.secondary" paragraph>
                We take your privacy seriously. Here&apos;s exactly what we need access to and why:
              </Typography>
              <Box sx={{ display: 'flex', flexDirection: { xs: 'column', md: 'row' }, gap: 3 }}>
                <Paper variant="outlined" sx={{ p: 3, flex: 1 }}>
                  <Box sx={{ display: 'flex', alignItems: 'start', gap: 2 }}>
                    <Icon icon={User} color="primary" />
                    <Box>
                      <Typography variant="subtitle1" fontWeight={600} gutterBottom>
                        Basic Profile Information
                      </Typography>
                      <Typography variant="body2" color="text.secondary">
                        We request your email, name, and profile picture to identify your account and personalize your experience. This information is never shared with third parties.
                      </Typography>
                    </Box>
                  </Box>
                </Paper>
                <Paper variant="outlined" sx={{ p: 3, flex: 1 }}>
                  <Box sx={{ display: 'flex', alignItems: 'start', gap: 2 }}>
                    <Icon icon={Shield} color="primary" />
                    <Box>
                      <Typography variant="subtitle1" fontWeight={600} gutterBottom>
                        Google Drive & Sheets Access
                      </Typography>
                      <Typography variant="body2" color="text.secondary">
                        Required only when you explicitly choose to export results. We create or update spreadsheets in your Google Drive only when you request it.
                      </Typography>
                    </Box>
                  </Box>
                </Paper>
              </Box>
            </Box>

            <Box sx={{ bgcolor: 'action.hover', p: 3, borderRadius: 2, border: 1, borderColor: 'divider' }}>
              <Typography variant="h6" gutterBottom fontWeight={600}>
                Your Data, Your Control
              </Typography>
              <List>
                <ListItem>
                  <ListItemText
                    primary="We don't sell your data"
                    secondary="Your information is used solely to provide the functionality you request — nothing more."
                  />
                </ListItem>
                <ListItem>
                  <ListItemText
                    primary="Full transparency"
                    secondary="All processing is logged in your history, and you can review what was processed at any time."
                  />
                </ListItem>
                <ListItem>
                  <ListItemText
                    primary="Revocable access"
                    secondary="You can revoke Google access at any time from your Google Account settings."
                  />
                </ListItem>
              </List>
              <Typography variant="body2" color="text.secondary" sx={{ mt: 2 }}>
                For complete details, please review our{' '}
                <Link href="/policy" style={{ textDecoration: 'underline', fontWeight: 600 }}>Privacy Policy</Link>{' '}
                and{' '}
                <Link href="/terms" style={{ textDecoration: 'underline', fontWeight: 600 }}>Terms of Service</Link>.
              </Typography>
            </Box>
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
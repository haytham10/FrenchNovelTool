'use client';

import React from 'react';
import { Dialog, DialogTitle, DialogContent, DialogActions, Button, Typography, Box, Accordion, AccordionSummary, AccordionDetails, Chip, Divider } from '@mui/material';
import Icon from './Icon';
import { ChevronDown, AlertCircle, HelpCircle, Zap, FileText, Upload } from 'lucide-react';

interface HelpModalProps {
  open: boolean;
  onClose: () => void;
}

export default function HelpModal({ open, onClose }: HelpModalProps) {
  return (
    <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth>
      <DialogTitle>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <Icon icon={HelpCircle} color="primary" />
          <Typography variant="h6">How Normalization Works</Typography>
        </Box>
      </DialogTitle>
      <DialogContent>
        <Typography variant="body1" sx={{ mb: 3 }}>
          French Novel Tool uses Google Gemini AI to intelligently break down long sentences into shorter, more manageable chunks while preserving meaning and context.
        </Typography>

        <Divider sx={{ my: 3 }} />

        <Typography variant="h6" sx={{ mb: 2 }}>Common Issues & Solutions</Typography>

        <Accordion>
          <AccordionSummary expandIcon={<Icon icon={ChevronDown} fontSize="small" />}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <Icon icon={AlertCircle} fontSize="small" color="error" />
              <Typography>Google Drive Permission Error</Typography>
            </Box>
          </AccordionSummary>
          <AccordionDetails>
            <Typography variant="body2" color="text.secondary" paragraph>
              <strong>Problem:</strong> &quot;Access denied&quot; or &quot;Permission error&quot; when exporting to Sheets.
            </Typography>
            <Typography variant="body2" color="text.secondary" paragraph>
              <strong>Solution:</strong>
            </Typography>
            <Box component="ul" sx={{ mt: 1, pl: 2 }}>
              <li>Sign out and sign in again</li>
              <li>Make sure you granted all requested permissions</li>
              <li>Check that your Google account has Sheets access</li>
              <li>Try selecting a different folder or creating a new Sheet</li>
            </Box>
          </AccordionDetails>
        </Accordion>

        <Accordion>
          <AccordionSummary expandIcon={<Icon icon={ChevronDown} fontSize="small" />}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <Icon icon={AlertCircle} fontSize="small" color="error" />
              <Typography>OAuth Token Expired</Typography>
            </Box>
          </AccordionSummary>
          <AccordionDetails>
            <Typography variant="body2" color="text.secondary" paragraph>
              <strong>Problem:</strong> Session expired or &quot;Token invalid&quot; error.
            </Typography>
            <Typography variant="body2" color="text.secondary" paragraph>
              <strong>Solution:</strong>
            </Typography>
            <Box component="ul" sx={{ mt: 1, pl: 2 }}>
              <li>The app will automatically try to refresh your token</li>
              <li>If auto-refresh fails, you&apos;ll see a banner to reconnect</li>
              <li>Click &quot;Reconnect&quot; and re-authorize the app</li>
              <li>Your work progress will be preserved</li>
            </Box>
          </AccordionDetails>
        </Accordion>

        <Accordion>
          <AccordionSummary expandIcon={<Icon icon={ChevronDown} fontSize="small" />}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <Icon icon={AlertCircle} fontSize="small" color="warning" />
              <Typography>API Quota Exceeded</Typography>
            </Box>
          </AccordionSummary>
          <AccordionDetails>
            <Typography variant="body2" color="text.secondary" paragraph>
              <strong>Problem:</strong> &quot;Quota exceeded&quot; or rate limit errors.
            </Typography>
            <Typography variant="body2" color="text.secondary" paragraph>
              <strong>Solution:</strong>
            </Typography>
            <Box component="ul" sx={{ mt: 1, pl: 2 }}>
              <li>Wait a few minutes and try again</li>
              <li>Process smaller PDFs or split into multiple runs</li>
              <li>Check your Google API quotas in Google Cloud Console</li>
              <li>Consider upgrading your API quota limits if needed</li>
            </Box>
          </AccordionDetails>
        </Accordion>

        <Accordion>
          <AccordionSummary expandIcon={<Icon icon={ChevronDown} fontSize="small" />}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <Icon icon={Upload} fontSize="small" color="info" />
              <Typography>PDF Upload Failed</Typography>
            </Box>
          </AccordionSummary>
          <AccordionDetails>
            <Typography variant="body2" color="text.secondary" paragraph>
              <strong>Problem:</strong> PDF won&apos;t upload or processing fails.
            </Typography>
            <Typography variant="body2" color="text.secondary" paragraph>
              <strong>Solution:</strong>
            </Typography>
            <Box component="ul" sx={{ mt: 1, pl: 2 }}>
              <li>Check file size (max 50MB)</li>
              <li>Ensure it&apos;s a valid PDF file</li>
              <li>If it&apos;s a scanned PDF, OCR may be needed first</li>
              <li>Try converting the PDF to a newer format</li>
              <li>Check your internet connection</li>
            </Box>
          </AccordionDetails>
        </Accordion>

        <Divider sx={{ my: 3 }} />

        <Typography variant="h6" sx={{ mb: 2 }}>
          <Icon icon={Zap} fontSize="small" sx={{ mr: 1, verticalAlign: 'middle' }} />
          Best Practices
        </Typography>
        <Box component="ul" sx={{ mt: 1, pl: 2, color: 'text.secondary' }}>
          <li>Start with sentence length of 12 words for balanced results</li>
          <li>Prefer &quot;Balanced&quot; for literary texts to save cost; use &quot;Speed&quot; for quick tests. Try &quot;Lightning&quot; for very fast, low-cost previews (preview model).</li>
          <li style={{ color: '#ff9800', fontWeight: 700 }}>Quality mode: disabled. My wallet: crying.</li>
          <li>Enable &quot;Fix hyphenations&quot; for scanned books</li>
          <li>Review and edit results before exporting</li>
          <li>Keep your Google authorization current</li>
        </Box>

        <Divider sx={{ my: 3 }} />

        <Box sx={{ bgcolor: 'primary.50', p: 2, borderRadius: 2, border: 1, borderColor: 'primary.main' }}>
          <Typography variant="body2" sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
            <Icon icon={FileText} fontSize="small" />
            <strong>Processing Steps</strong>
          </Typography>
          <Box component="a" sx={{ mt: 1, listStyle: 'none' }}>
            <li><Chip label="1" size="small" sx={{ mr: 1 }} /> Upload: PDF is uploaded and validated</li>
            <li><Chip label="2" size="small" sx={{ mr: 1 }} /> Extract: Text is extracted from PDF</li>
            <li><Chip label="3" size="small" sx={{ mr: 1 }} /> Analyze: Gemini analyzes sentence structure</li>
            <li><Chip label="4" size="small" sx={{ mr: 1 }} /> Normalize: Sentences are split intelligently</li>
            <li><Chip label="5" size="small" sx={{ mr: 1 }} /> Export: Results saved to Google Sheets</li>
          </Box>
        </Box>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose} variant="contained">
          Got it
        </Button>
      </DialogActions>
    </Dialog>
  );
}

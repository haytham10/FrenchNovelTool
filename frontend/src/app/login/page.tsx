"use client";

import React, { useEffect } from 'react';
import { Box, Container, Typography, Paper } from '@mui/material';
import Link from 'next/link';
import { useRouter, useSearchParams } from 'next/navigation';
import { useAuth } from '@/components/AuthContext';
import GoogleLoginButton from '@/components/GoogleLoginButton';
import Icon from '@/components/Icon';
import { BookOpenText, CheckCircle, Zap, Shield } from 'lucide-react';

export default function LoginPage() {
  const { user } = useAuth();
  const router = useRouter();
  const searchParams = useSearchParams();
  const redirectTo = searchParams.get('redirect') || '/';

  useEffect(() => {
    if (user) {
      router.push(redirectTo);
    }
  }, [user, router, redirectTo]);

  if (user) {
    return null;
  }

  return (
    <Box sx={{ minHeight: 'calc(100vh - 64px)', py: { xs: 4, md: 8 } }} className="hero-aura">
      <Container maxWidth="md" sx={{ position: 'relative', zIndex: 1 }}>
        <Box sx={{ textAlign: 'center', mb: 6 }}>
          <Box sx={{ display: 'flex', justifyContent: 'center', mb: 3 }}>
            <Icon icon={BookOpenText} sx={{ fontSize: 64 }} color="primary" />
          </Box>
          <Typography variant="h1" sx={{ mb: 2, fontWeight: 700 }} className="gradient-text">
            Welcome to French Novel Tool
          </Typography>
          <Typography variant="h5" color="text.secondary" sx={{ mb: 4, lineHeight: 1.6 }}>
            Transform French literature into learnable content with AI-powered sentence processing and seamless Google Sheets integration
          </Typography>
        </Box>

        <Paper elevation={3} sx={{ p: { xs: 3, md: 5 }, mb: 4 }}>
          <Box sx={{ textAlign: 'center', mb: 3 }}>
            <Typography variant="h6" sx={{ mb: 3, fontWeight: 600 }}>
              Sign in with Google to get started
            </Typography>
            <GoogleLoginButton />
          </Box>

          <Box sx={{ mt: 4, pt: 4, borderTop: 1, borderColor: 'divider' }}>
            <Typography variant="body1" color="text.primary" sx={{ mb: 3, fontWeight: 600, textAlign: 'center' }}>
              What you&apos;ll get access to:
            </Typography>
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2.5 }}>
              <Box sx={{ display: 'flex', alignItems: 'start', gap: 2 }}>
                <Icon icon={Zap} color="primary" sx={{ fontSize: 28, flexShrink: 0 }} />
                <Box>
                  <Typography variant="body1" fontWeight={600} gutterBottom>
                    AI-Powered Sentence Normalization
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Upload PDF novels and let Google Gemini intelligently split long sentences into optimal learning chunks
                  </Typography>
                </Box>
              </Box>
              <Box sx={{ display: 'flex', alignItems: 'start', gap: 2 }}>
                <Icon icon={CheckCircle} color="primary" sx={{ fontSize: 28, flexShrink: 0 }} />
                <Box>
                  <Typography variant="body1" fontWeight={600} gutterBottom>
                    One-Click Export to Google Sheets
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Instantly export processed sentences to your Google Sheets for study, annotation, and collaboration
                  </Typography>
                </Box>
              </Box>
              <Box sx={{ display: 'flex', alignItems: 'start', gap: 2 }}>
                <Icon icon={Shield} color="primary" sx={{ fontSize: 28, flexShrink: 0 }} />
                <Box>
                  <Typography variant="body1" fontWeight={600} gutterBottom>
                    Secure & Private Processing
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Your files are processed securely. We only access your Google Drive when you explicitly export results
                  </Typography>
                </Box>
              </Box>
            </Box>
          </Box>
        </Paper>

        <Box sx={{ textAlign: 'center' }}>
          <Typography variant="body2" color="text.secondary">
            By signing in, you agree to our{' '}
            <Link href="/terms" style={{ textDecoration: 'underline', fontWeight: 600 }}>Terms of Service</Link>{' '}and{' '}
            <Link href="/policy" style={{ textDecoration: 'underline', fontWeight: 600 }}>Privacy Policy</Link>.
          </Typography>
        </Box>
      </Container>
    </Box>
  );
}

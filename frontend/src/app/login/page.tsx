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
          <Typography variant="h1" sx={{ mb: 2 }} className="gradient-text">
            Welcome to French Novel Tool
          </Typography>
          <Typography variant="h5" color="text.secondary" sx={{ mb: 4 }}>
            Process French novels with AI and export to Google Sheets
          </Typography>
        </Box>

        <Paper elevation={3} sx={{ p: { xs: 3, md: 5 }, mb: 4 }}>
          <Box sx={{ textAlign: 'center', mb: 3 }}>
            <Typography variant="h6" sx={{ mb: 3 }}>
              Sign in to get started
            </Typography>
            <GoogleLoginButton />
          </Box>

          <Box sx={{ mt: 4, pt: 4, borderTop: 1, borderColor: 'divider' }}>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
              By signing in, you get access to:
            </Typography>
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                <Icon icon={Zap} color="primary" fontSize="small" />
                <Typography variant="body2">
                  AI-powered sentence normalization with Google Gemini
                </Typography>
              </Box>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                <Icon icon={CheckCircle} color="primary" fontSize="small" />
                <Typography variant="body2">
                  Direct export to Google Sheets with one click
                </Typography>
              </Box>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                <Icon icon={Shield} color="primary" fontSize="small" />
                <Typography variant="body2">
                  Secure processing with your Google Drive
                </Typography>
              </Box>
            </Box>
          </Box>
        </Paper>

        <Box sx={{ textAlign: 'center' }}>
          <Typography variant="body2" color="text.secondary">
            By signing in, you agree to our{' '}
            <Link href="/terms" style={{ textDecoration: 'underline' }}>Terms of Service</Link>{' '}and{' '}
            <Link href="/policy" style={{ textDecoration: 'underline' }}>Privacy Policy</Link>.
          </Typography>
        </Box>
      </Container>
    </Box>
  );
}

import React, { useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import { Button, Box, Typography, Divider } from '@mui/material';
import Icon from './Icon';
import { Upload } from 'lucide-react';
import { bounce, pulse } from '@/lib/animations';

interface FileUploadProps {
  onFileUpload: (files: File[]) => void;
  disabled?: boolean;
  variant?: 'button' | 'dropzone';
}

export default function FileUpload({ onFileUpload, disabled = false, variant = 'button' }: FileUploadProps) {
  const onDrop = useCallback((acceptedFiles: File[]) => {
    onFileUpload(acceptedFiles);
  }, [onFileUpload]);

  const { getRootProps, getInputProps, isDragActive, open } = useDropzone({ 
    onDrop, 
    accept: { 'application/pdf': ['.pdf'] }, 
    multiple: true,
    noClick: variant === 'button',
    noKeyboard: variant === 'button',
    disabled
  });

  if (variant === 'dropzone') {
    return (
      <Box
        {...getRootProps()}
        sx={{
          position: 'relative',
          width: '100%',
          minHeight: '320px',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          border: '3px dashed',
          borderColor: isDragActive ? 'primary.main' : 'divider',
          borderRadius: 4,
          background: isDragActive 
            ? 'linear-gradient(135deg, rgba(124,156,255,0.08) 0%, rgba(6,182,212,0.08) 100%)' 
            : 'linear-gradient(135deg, rgba(124,156,255,0.02) 0%, rgba(6,182,212,0.02) 100%)',
          cursor: disabled ? 'not-allowed' : 'pointer',
          transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
          transform: isDragActive ? 'scale(1.01)' : 'scale(1)',
          boxShadow: isDragActive ? '0 12px 40px -8px rgba(59, 130, 246, 0.25)' : 'none',
          '&:hover:not([disabled])': {
            borderColor: 'primary.light',
            background: 'linear-gradient(135deg, rgba(124,156,255,0.05) 0%, rgba(6,182,212,0.05) 100%)',
            transform: 'scale(1.005)',
          },
          '&:focus-visible': {
            outline: '3px solid',
            outlineColor: 'primary.main',
            outlineOffset: '2px',
          },
        }}
        role="button"
        aria-label="Upload PDF files by clicking or dragging"
        tabIndex={disabled ? -1 : 0}
        onKeyDown={(e) => {
          if (!disabled && (e.key === 'Enter' || e.key === ' ')) {
            e.preventDefault();
            const input = e.currentTarget.querySelector('input');
            input?.click();
          }
        }}
      >
        <input {...getInputProps()} aria-label="PDF file input" />
        <Box sx={{ 
          display: 'flex', 
          flexDirection: 'column', 
          alignItems: 'center', 
          gap: 3,
          transition: 'all 0.3s ease',
          transform: isDragActive ? 'translateY(-4px)' : 'translateY(0)',
          animation: isDragActive ? `${bounce} 0.6s ease-in-out infinite` : 'none',
        }}>
          <Box sx={{ 
            display: 'inline-flex', 
            p: 4, 
            borderRadius: '50%', 
            background: isDragActive 
              ? 'linear-gradient(135deg, #3b82f6 0%, #06b6d4 100%)' 
              : 'linear-gradient(135deg, rgba(124,156,255,0.1) 0%, rgba(6,182,212,0.1) 100%)',
            border: 3,
            borderColor: isDragActive ? 'transparent' : 'divider',
            transition: 'all 0.3s ease',
            transform: isDragActive ? 'scale(1.15)' : 'scale(1)',
            animation: !isDragActive && !disabled ? `${pulse} 2s ease-in-out infinite` : 'none',
          }}>
            <Icon 
              icon={Upload} 
              sx={{ 
                fontSize: 56,
                transition: 'all 0.3s ease',
              }} 
              color={isDragActive ? 'inherit' : 'primary'}
              style={{ color: isDragActive ? '#fff' : undefined }}
            />
          </Box>
          <Typography 
            variant="h5" 
            sx={{ 
              fontWeight: 700,
              color: isDragActive ? 'primary.main' : 'text.primary',
              transition: 'color 0.3s ease',
            }}
          >
            {isDragActive ? 'Drop files here' : 'Upload French Novel PDF'}
          </Typography>
          <Typography 
            variant="body1" 
            color="text.secondary"
            sx={{ textAlign: 'center', maxWidth: '420px', lineHeight: 1.6 }}
          >
            {isDragActive ? 'Release to upload your file' : 'Drag and drop your PDF here, or click to browse'}
          </Typography>
          {!isDragActive && (
            <Box sx={{ 
              display: 'flex', 
              gap: 2, 
              alignItems: 'center',
              mt: 1,
              px: 3,
              py: 1,
              borderRadius: 2,
              bgcolor: 'action.hover',
            }}>
              <Typography variant="caption" color="text.secondary" fontWeight={500}>
                ✓ Large files supported
              </Typography>
              <Divider orientation="vertical" flexItem sx={{ bgcolor: 'divider' }} />
              <Typography variant="caption" color="text.secondary" fontWeight={500}>
                ✓ PDF format only
              </Typography>
            </Box>
          )}
        </Box>
      </Box>
    );
  }

  return (
    <Box
      {...getRootProps()}
      sx={{
        position: 'relative',
        display: 'inline-block',
        width: '100%',
      }}
    >
      <input {...getInputProps()} aria-label="PDF file input" />
      <Button
        variant="contained"
        size="large"
        disabled={disabled}
        onClick={open}
        startIcon={<Icon icon={Upload} />}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            open();
          }
        }}
        sx={{
          width: '100%',
          py: 2,
          px: 4,
          fontSize: '1.1rem',
          fontWeight: 600,
          position: 'relative',
          transition: 'all 0.3s ease',
          border: isDragActive ? '2px dashed' : 'none',
          borderColor: isDragActive ? 'primary.main' : 'transparent',
          transform: isDragActive ? 'scale(1.02)' : 'scale(1)',
          boxShadow: isDragActive ? 4 : 2,
          '&:hover': {
            transform: 'translateY(-2px)',
            boxShadow: 6,
          },
          '&:focus-visible': {
            outline: '3px solid',
            outlineColor: 'primary.main',
            outlineOffset: '2px',
          },
        }}
        aria-label="Upload PDF files by clicking or dragging"
      >
        {isDragActive ? 'Drop files here' : 'Upload PDF'}
      </Button>
      {isDragActive && (
        <Box
          sx={{
            position: 'absolute',
            inset: 0,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            pointerEvents: 'none',
            zIndex: 1,
          }}
        >
          <Typography
            variant="body2"
            sx={{
              backgroundColor: 'background.paper',
              px: 2,
              py: 1,
              borderRadius: 1,
              boxShadow: 2,
              fontWeight: 600,
            }}
          >
            Drop files to upload
          </Typography>
        </Box>
      )}
    </Box>
  );
}
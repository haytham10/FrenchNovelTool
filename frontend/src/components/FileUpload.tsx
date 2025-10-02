import React, { useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import { Button, Box, Typography } from '@mui/material';
import Icon from './Icon';
import { Upload } from 'lucide-react';

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
          minHeight: '300px',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          border: '3px dashed',
          borderColor: isDragActive ? 'primary.main' : 'divider',
          borderRadius: 3,
          bgcolor: isDragActive ? 'rgba(59, 130, 246, 0.08)' : 'background.paper',
          cursor: disabled ? 'not-allowed' : 'pointer',
          transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
          transform: isDragActive ? 'scale(1.02)' : 'scale(1)',
          boxShadow: isDragActive ? '0 8px 24px rgba(59, 130, 246, 0.15)' : 'none',
          '&:hover:not([disabled])': {
            borderColor: 'primary.light',
            bgcolor: 'action.hover',
            transform: 'scale(1.01)',
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
          gap: 2,
          transition: 'all 0.3s ease',
          transform: isDragActive ? 'translateY(-4px)' : 'translateY(0)',
          animation: isDragActive ? 'bounce 0.6s ease-in-out infinite' : 'none',
        }}>
          <Box sx={{ 
            display: 'inline-flex', 
            p: 3, 
            borderRadius: 4, 
            bgcolor: isDragActive ? 'primary.main' : 'action.hover',
            border: 2,
            borderColor: isDragActive ? 'primary.dark' : 'divider',
            transition: 'all 0.3s ease',
            transform: isDragActive ? 'scale(1.1)' : 'scale(1)',
            animation: !isDragActive && !disabled ? 'pulse 2s ease-in-out infinite' : 'none',
          }}>
            <Icon 
              icon={Upload} 
              sx={{ 
                fontSize: 48,
                transition: 'all 0.3s ease',
              }} 
              color={isDragActive ? 'inherit' : 'primary'}
              style={{ color: isDragActive ? '#fff' : undefined }}
            />
          </Box>
          <Typography 
            variant="h5" 
            sx={{ 
              fontWeight: 600,
              color: isDragActive ? 'primary.main' : 'text.primary',
              transition: 'color 0.3s ease',
            }}
          >
            {isDragActive ? 'Drop files here' : 'Get started by uploading a PDF'}
          </Typography>
          <Typography 
            variant="body1" 
            color="text.secondary"
            sx={{ textAlign: 'center', maxWidth: '400px' }}
          >
            {isDragActive ? 'Release to upload' : 'Click here or drag and drop your French novel PDF'}
          </Typography>
          {!isDragActive && (
            <Typography variant="caption" color="text.secondary" sx={{ mt: 1 }}>
              Supports multiple files • PDF format only
            </Typography>
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
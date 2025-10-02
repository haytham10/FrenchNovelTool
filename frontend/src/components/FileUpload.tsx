import React, { useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import { Button, Box, Typography } from '@mui/material';
import Icon from './Icon';
import { Upload } from 'lucide-react';

interface FileUploadProps {
  onFileUpload: (files: File[]) => void;
  disabled?: boolean;
}

export default function FileUpload({ onFileUpload, disabled = false }: FileUploadProps) {
  const onDrop = useCallback((acceptedFiles: File[]) => {
    onFileUpload(acceptedFiles);
  }, [onFileUpload]);

  const { getRootProps, getInputProps, isDragActive, open } = useDropzone({ 
    onDrop, 
    accept: { 'application/pdf': ['.pdf'] }, 
    multiple: true,
    noClick: true,
    noKeyboard: true,
    disabled
  });

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
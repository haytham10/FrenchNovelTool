"use client";

import React from 'react';
import { Box, Stepper, Step, StepLabel, Typography } from '@mui/material';
import { styled } from '@mui/material/styles';

const steps = [
  { label: 'Upload', eta: '~5s' },
  { label: 'Analyze', eta: '' },
  { label: 'Normalize', eta: '' },
  { label: 'Done', eta: '' }
];

const StickyStepperContainer = styled(Box)(({ theme }) => ({
  position: 'sticky',
  top: 64, // Assuming header height is 64px
  zIndex: 100,
  backgroundColor: theme.palette.mode === 'dark' ? 'rgba(15, 23, 42, 0.95)' : 'rgba(247, 248, 251, 0.95)',
  backdropFilter: 'blur(8px)',
  borderBottom: `1px solid ${theme.palette.divider}`,
  padding: theme.spacing(2, 0),
  marginBottom: theme.spacing(2),
  transition: 'all 0.3s ease',
}));

export default function UploadStepper({ activeStep }: { activeStep: number }) {
  return (
    <StickyStepperContainer>
      <Stepper 
        activeStep={activeStep} 
        alternativeLabel
        aria-label="Processing steps"
        sx={{
          '& .MuiStepLabel-root': {
            opacity: 0.7,
          },
          '& .MuiStepLabel-label.Mui-active': {
            opacity: 1,
            fontWeight: 600,
          },
          '& .MuiStepLabel-label.Mui-completed': {
            opacity: 0.9,
          },
          '& .MuiStepIcon-root': {
            fontSize: '1.75rem',
            '&.Mui-active': {
              color: 'primary.main',
            },
            '&.Mui-completed': {
              color: 'success.main',
            },
          },
        }}
      >
        {steps.map((step, index) => (
          <Step key={step.label}>
            <StepLabel 
              aria-label={`Step ${index + 1}: ${step.label}${index === activeStep ? ' (current)' : ''}`}
              StepIconComponent={({ active, completed }) => (
                <Box
                  sx={{
                    width: 32,
                    height: 32,
                    borderRadius: '50%',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    fontWeight: 600,
                    fontSize: '0.875rem',
                    backgroundColor: completed ? 'success.main' : active ? 'primary.main' : 'action.disabled',
                    color: completed || active ? 'common.white' : 'text.disabled',
                    transition: 'all 0.3s ease',
                  }}
                >
                  {index + 1}
                </Box>
              )}
            >
              <Box>
                {step.label}
                {step.eta && index === activeStep && (
                  <Typography variant="caption" display="block" sx={{ opacity: 0.6, mt: 0.5 }}>
                    ETA: {step.eta}
                  </Typography>
                )}
              </Box>
            </StepLabel>
          </Step>
        ))}
      </Stepper>
    </StickyStepperContainer>
  );
}



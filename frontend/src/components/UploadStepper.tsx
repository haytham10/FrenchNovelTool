"use client";

import React from 'react';
import { Box, Stepper, Step, StepLabel } from '@mui/material';

const steps = ['Upload', 'Analyze', 'Normalize', 'Done'];

export default function UploadStepper({ activeStep }: { activeStep: number }) {
  return (
    <Box sx={{ width: '100%', my: 2 }}>
      <Stepper 
        activeStep={activeStep} 
        alternativeLabel
        aria-label="Processing steps"
      >
        {steps.map((label, index) => (
          <Step key={label}>
            <StepLabel aria-label={`Step ${index + 1}: ${label}${index === activeStep ? ' (current)' : ''}`}>
              {label}
            </StepLabel>
          </Step>
        ))}
      </Stepper>
    </Box>
  );
}



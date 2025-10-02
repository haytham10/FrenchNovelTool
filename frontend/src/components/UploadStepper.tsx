"use client";

import React from 'react';
import { Box, Stepper, Step, StepLabel } from '@mui/material';

const steps = ['Upload', 'Analyze', 'Normalize', 'Done'];

export default function UploadStepper({ activeStep }: { activeStep: number }) {
  return (
    <Box sx={{ width: '100%', my: 2 }}>
      <Stepper activeStep={activeStep} alternativeLabel>
        {steps.map((label) => (
          <Step key={label}>
            <StepLabel>{label}</StepLabel>
          </Step>
        ))}
      </Stepper>
    </Box>
  );
}



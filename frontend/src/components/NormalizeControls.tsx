'use client';

import React, { useState } from 'react';
import { Box, Typography, Slider, Paper, Chip, Stack, FormControlLabel, Switch, Select, MenuItem, FormControl, Collapse, Button, TextField, Divider } from '@mui/material';
import Icon from './Icon';
import { Sliders, ChevronDown, ChevronUp } from 'lucide-react';

interface NormalizeControlsProps {
  sentenceLength: number;
  onSentenceLengthChange: (value: number) => void;
  disabled?: boolean;
  advancedOptions?: AdvancedNormalizationOptions;
  onAdvancedOptionsChange?: (options: AdvancedNormalizationOptions) => void;
}

export interface AdvancedNormalizationOptions {
  ignoreDialogues?: boolean;
  preserveQuotes?: boolean;
  fixHyphenations?: boolean;
  minSentenceLength?: number;
  geminiModel?: 'balanced' | 'quality' | 'speed';
  
}

const PRESETS = [
  { label: 'Short', value: 8 },
  { label: 'Medium', value: 12 },
  { label: 'Long', value: 16 },
];

const GEMINI_MODELS = [
  { value: 'balanced', label: 'Balanced', description: 'Best balance of speed and quality' },
  { value: 'quality', label: 'Quality', description: 'Highest quality, slower processing' },
  { value: 'speed', label: 'Speed', description: 'Fastest processing, good quality' },
];

export default function NormalizeControls({
  sentenceLength,
  onSentenceLengthChange,
  disabled = false,
  advancedOptions = {},
  onAdvancedOptionsChange,
}: NormalizeControlsProps) {
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [previewText, setPreviewText] = useState('');
  const [showPreview, setShowPreview] = useState(false);

  const handleAdvancedOptionChange = (key: keyof AdvancedNormalizationOptions, value: string | number | boolean) => {
    if (onAdvancedOptionsChange) {
      onAdvancedOptionsChange({ ...advancedOptions, [key]: value });
    }
  };

  const simulatePreview = (text: string) => {
    // Simple simulation for demo purposes
    if (!text.trim()) return '';
    const sentences = text.split(/[.!?]+/).filter(s => s.trim());
    return sentences.map((s, i) => `${i + 1}. ${s.trim().substring(0, sentenceLength * 5)}...`).join('\n');
  };

  return (
    <Paper 
      elevation={0} 
      sx={{ 
        p: { xs: 3, md: 4 }, 
        background: 'linear-gradient(135deg, rgba(124,156,255,0.03) 0%, rgba(6,182,212,0.03) 100%)',
        border: 1, 
        borderColor: 'divider',
        borderRadius: 3,
        position: 'relative',
        overflow: 'hidden',
        '&::before': {
          content: '""',
          position: 'absolute',
          top: 0,
          left: 0,
          right: 0,
          height: '4px',
          background: 'linear-gradient(90deg, #3b82f6 0%, #06b6d4 100%)',
        }
      }}
    >
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 3 }}>
        <Box sx={{ 
          p: 1.5, 
          borderRadius: 2, 
          bgcolor: 'primary.main',
          color: 'primary.contrastText',
          display: 'inline-flex'
        }}>
          <Icon icon={Sliders} sx={{ fontSize: 28 }} />
        </Box>
        <Box>
          <Typography variant="h6" fontWeight={700}>
            Normalization Settings
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Customize how AI processes your sentences
          </Typography>
        </Box>
      </Box>

      {/* Basic Controls */}
      <Box sx={{ mb: 4 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
          <Typography variant="subtitle1" fontWeight={700} sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            Target Sentence Length
          </Typography>
          <Chip 
            label={`${sentenceLength} words`} 
            color="primary" 
            size="medium"
            sx={{ 
              fontWeight: 700,
              fontSize: '1rem',
              px: 1,
            }}
          />
        </Box>
        <Slider
          value={sentenceLength}
          onChange={(_, value) => onSentenceLengthChange(value as number)}
          min={5}
          max={20}
          step={1}
          marks={[
            { value: 5, label: '5' },
            { value: 10, label: '10' },
            { value: 15, label: '15' },
            { value: 20, label: '20' },
          ]}
          disabled={disabled}
          valueLabelDisplay="auto"
          sx={{ 
            mt: 3,
            '& .MuiSlider-thumb': {
              width: 20,
              height: 20,
            },
            '& .MuiSlider-track': {
              height: 6,
            },
            '& .MuiSlider-rail': {
              height: 6,
            }
          }}
        />
      </Box>

      <Box sx={{ mb: 4 }}>
        <Typography variant="subtitle2" fontWeight={600} gutterBottom sx={{ mb: 1.5 }}>
          Quick Presets
        </Typography>
        <Stack direction="row" spacing={1} sx={{ flexWrap: 'wrap', gap: 1 }}>
          {PRESETS.map((preset) => (
            <Chip
              key={preset.value}
              label={`${preset.label} (${preset.value}w)`}
              onClick={() => onSentenceLengthChange(preset.value)}
              color={sentenceLength === preset.value ? 'primary' : 'default'}
              variant={sentenceLength === preset.value ? 'filled' : 'outlined'}
              disabled={disabled}
              clickable
              sx={{
                fontWeight: sentenceLength === preset.value ? 600 : 500,
                transition: 'all 200ms ease',
                '&:hover': {
                  transform: 'translateY(-2px)',
                  boxShadow: 2,
                }
              }}
            />
          ))}
        </Stack>
      </Box>

      {/* Gemini Model Selection */}
      {onAdvancedOptionsChange && (
        <Box sx={{ mb: 4 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
            <Typography variant="subtitle1" fontWeight={700}>
              AI Model Selection
            </Typography>
          </Box>
          <FormControl fullWidth>
              <Select
              value={advancedOptions.geminiModel || 'speed'}
              onChange={(e) => handleAdvancedOptionChange('geminiModel', e.target.value)}
              disabled={disabled}
              sx={{ 
                borderRadius: 2,
                '& .MuiOutlinedInput-notchedOutline': {
                  borderColor: 'divider',
                },
              }}
            >
              {GEMINI_MODELS.map((model) => (
                <MenuItem key={model.value} value={model.value} disabled={model.value === 'quality'}>
                  <Box>
                    <Typography variant="body1" fontWeight={600}>{model.label}</Typography>
                    <Typography variant="caption" color="text.secondary">{model.description}</Typography>
                  </Box>
                </MenuItem>
              ))}
            </Select>
          </FormControl>
          <Box sx={{ mt: 1 }}>
            <Typography variant="caption" sx={{ color: 'warning.main', fontWeight: 600 }}>
              Quality mode: disabled. My wallet: crying.
            </Typography>
          </Box>
        </Box>
      )}

      {/* Advanced Options Toggle */}
      {onAdvancedOptionsChange && (
        <>
          <Divider sx={{ my: 2 }} />
          <Button
            fullWidth
            variant="text"
            onClick={() => setShowAdvanced(!showAdvanced)}
            endIcon={showAdvanced ? <ChevronUp size={20} /> : <ChevronDown size={20} />}
            sx={{ mb: 2 }}
          >
            Advanced Options
          </Button>
          
          <Collapse in={showAdvanced}>
            <Stack spacing={2}>
              <FormControlLabel
                control={
                  <Switch
                    checked={advancedOptions.ignoreDialogues || false}
                    onChange={(e) => handleAdvancedOptionChange('ignoreDialogues', e.target.checked)}
                    disabled={disabled}
                  />
                }
                label={
                  <Box>
                    <Typography variant="body2">Ignore dialogues (—)</Typography>
                    <Typography variant="caption" color="text.secondary">
                      Skip normalizing dialogue sections marked with em dashes
                    </Typography>
                  </Box>
                }
              />
              
              <FormControlLabel
                control={
                  <Switch
                    checked={advancedOptions.preserveQuotes || false}
                    onChange={(e) => handleAdvancedOptionChange('preserveQuotes', e.target.checked)}
                    disabled={disabled}
                  />
                }
                label={
                  <Box>
                    <Typography variant="body2">Preserve quotes & punctuation</Typography>
                    <Typography variant="caption" color="text.secondary">
                      Keep original quotation marks and special punctuation
                    </Typography>
                  </Box>
                }
              />
              
              <FormControlLabel
                control={
                  <Switch
                    checked={advancedOptions.fixHyphenations || false}
                    onChange={(e) => handleAdvancedOptionChange('fixHyphenations', e.target.checked)}
                    disabled={disabled}
                  />
                }
                label={
                  <Box>
                    <Typography variant="body2">Fix hyphenations</Typography>
                    <Typography variant="caption" color="text.secondary">
                      Automatically rejoin words split across lines
                    </Typography>
                  </Box>
                }
              />
              
              <Box>
                <Typography variant="body2" gutterBottom>
                  Minimum sentence length
                </Typography>
                <TextField
                  type="number"
                  size="small"
                  fullWidth
                  value={advancedOptions.minSentenceLength || 3}
                  onChange={(e) => handleAdvancedOptionChange('minSentenceLength', parseInt(e.target.value))}
                  disabled={disabled}
                  inputProps={{ min: 1, max: sentenceLength }}
                  helperText="Sentences shorter than this will be merged"
                />
              </Box>
            </Stack>
          </Collapse>

          {/* Live Preview Section */}
          <Divider sx={{ my: 3 }} />
          <Button
            fullWidth
            variant="text"
            onClick={() => setShowPreview(!showPreview)}
            endIcon={showPreview ? <ChevronUp size={20} /> : <ChevronDown size={20} />}
            sx={{ mb: 2 }}
          >
            Live Preview
          </Button>
          
          <Collapse in={showPreview}>
            <Box>
              <Typography variant="body2" gutterBottom>
                Paste sample text to preview normalization:
              </Typography>
              <TextField
                multiline
                rows={4}
                fullWidth
                value={previewText}
                onChange={(e) => setPreviewText(e.target.value)}
                placeholder="Enter French text here to see how it will be split..."
                disabled={disabled}
                sx={{ mb: 2 }}
              />
              {previewText && (
                <Paper variant="outlined" sx={{ p: 2, bgcolor: 'action.hover' }}>
                  <Typography variant="caption" color="text.secondary" gutterBottom display="block">
                    Preview (approximate):
                  </Typography>
                  <Typography variant="body2" component="pre" sx={{ whiteSpace: 'pre-wrap', fontFamily: 'monospace' }}>
                    {simulatePreview(previewText)}
                  </Typography>
                </Paper>
              )}
            </Box>
          </Collapse>
        </>
      )}
    </Paper>
  );
}

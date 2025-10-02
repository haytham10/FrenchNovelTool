'use client';

import React, { useState } from 'react';
import { Box, Typography, Slider, Paper, Chip, Stack, FormControlLabel, Switch, Select, MenuItem, FormControl, InputLabel, Collapse, Button, TextField, Divider } from '@mui/material';
import Icon from './Icon';
import { Sliders, ChevronDown, ChevronUp, Sparkles } from 'lucide-react';

interface NormalizeControlsProps {
  sentenceLength: number;
  onSentenceLengthChange: (value: number) => void;
  disabled?: boolean;
  advancedOptions?: AdvancedNormalizationOptions;
  onAdvancedOptionsChange?: (options: AdvancedNormalizationOptions) => void;
}

export interface AdvancedNormalizationOptions {
  aiProvider?: 'gemini' | 'openai';
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

const AI_PROVIDERS = [
  { value: 'gemini', label: 'Google Gemini', description: 'Google\'s AI model' },
  { value: 'openai', label: 'OpenAI', description: 'OpenAI\'s GPT models' },
];

const GEMINI_MODELS = [
  { value: 'balanced', label: 'Balanced', description: 'Best balance of speed and quality' },
  { value: 'quality', label: 'Quality', description: 'Highest quality, slower processing' },
  { value: 'speed', label: 'Speed', description: 'Fastest processing, good quality' },
];

const MODEL_DESCRIPTIONS = {
  gemini: {
    balanced: 'Uses Gemini 2.0 Flash (balanced)',
    quality: 'Uses Gemini 2.0 Flash (quality mode)',
    speed: 'Uses Gemini 2.0 Flash (speed mode)',
  },
  openai: {
    balanced: 'Uses GPT-4o-mini (balanced)',
    quality: 'Uses GPT-4o (highest quality)',
    speed: 'Uses GPT-3.5-turbo (fastest)',
  },
};

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
    <Paper elevation={0} sx={{ p: 3, bgcolor: 'background.paper', border: 1, borderColor: 'divider' }}>
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
        <Icon icon={Sliders} color="primary" />
        <Typography variant="h6" fontWeight={600}>
          Normalization Settings
        </Typography>
      </Box>
      
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
        Configure how sentences are normalized. Adjust length, model, and advanced options for optimal results.
      </Typography>

      {/* Basic Controls */}
      <Box sx={{ mb: 3 }}>
        <Typography variant="subtitle2" gutterBottom>
          Target Length: <strong>{sentenceLength} words</strong>
        </Typography>
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
          sx={{ mt: 2 }}
        />
      </Box>

      <Box sx={{ mb: 3 }}>
        <Typography variant="subtitle2" gutterBottom>
          Quick Presets
        </Typography>
        <Stack direction="row" spacing={1} sx={{ mt: 1 }}>
          {PRESETS.map((preset) => (
            <Chip
              key={preset.value}
              label={`${preset.label} (${preset.value})`}
              onClick={() => onSentenceLengthChange(preset.value)}
              color={sentenceLength === preset.value ? 'primary' : 'default'}
              variant={sentenceLength === preset.value ? 'filled' : 'outlined'}
              disabled={disabled}
              clickable
            />
          ))}
        </Stack>
      </Box>

      {/* AI Provider Selection */}
      {onAdvancedOptionsChange && (
        <>
          <Box sx={{ mb: 3 }}>
            <FormControl fullWidth size="small">
              <InputLabel id="ai-provider-label">AI Provider</InputLabel>
              <Select
                labelId="ai-provider-label"
                value={advancedOptions.aiProvider || 'gemini'}
                onChange={(e) => handleAdvancedOptionChange('aiProvider', e.target.value)}
                disabled={disabled}
                label="AI Provider"
                startAdornment={<Icon icon={Sparkles} fontSize="small" sx={{ mr: 1 }} />}
              >
                {AI_PROVIDERS.map((provider) => (
                  <MenuItem key={provider.value} value={provider.value}>
                    <Box>
                      <Typography variant="body2" fontWeight={600}>{provider.label}</Typography>
                      <Typography variant="caption" color="text.secondary">{provider.description}</Typography>
                    </Box>
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          </Box>

          {/* Model Quality Selection */}
          <Box sx={{ mb: 3 }}>
            <FormControl fullWidth size="small">
              <InputLabel id="model-quality-label">Model Quality</InputLabel>
              <Select
                labelId="model-quality-label"
                value={advancedOptions.geminiModel || 'balanced'}
                onChange={(e) => handleAdvancedOptionChange('geminiModel', e.target.value)}
                disabled={disabled}
                label="Model Quality"
              >
                {GEMINI_MODELS.map((model) => (
                  <MenuItem key={model.value} value={model.value}>
                    <Box>
                      <Typography variant="body2" fontWeight={600}>{model.label}</Typography>
                      <Typography variant="caption" color="text.secondary">
                        {MODEL_DESCRIPTIONS[advancedOptions.aiProvider || 'gemini'][model.value as 'balanced' | 'quality' | 'speed']}
                      </Typography>
                    </Box>
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          </Box>
        </>
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

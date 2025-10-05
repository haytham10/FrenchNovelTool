/**
 * Processing Store - Manages PDF processing state
 */

import { create } from 'zustand';
import type { AdvancedNormalizationOptions } from '@/components/NormalizeControls';

interface ProcessingState {
  // Sentences state
  sentences: string[];
  setSentences: (sentences: string[]) => void;
  clearSentences: () => void;
  
  // Loading state
  loading: boolean;
  loadingMessage: string;
  setLoading: (loading: boolean, message?: string) => void;
  
  // Upload progress
  uploadProgress: number;
  setUploadProgress: (progress: number) => void;
  
  // Processing options
  sentenceLength: number;
  setSentenceLength: (length: number) => void;
  
  advancedOptions: AdvancedNormalizationOptions;
  setAdvancedOptions: (options: AdvancedNormalizationOptions) => void;
}

export const useProcessingStore = create<ProcessingState>((set) => ({
  // Initial state
  sentences: [],
  loading: false,
  loadingMessage: '',
  uploadProgress: 0,
  sentenceLength: 12,
  advancedOptions: {
    geminiModel: 'speed',
    ignoreDialogues: false,
    preserveQuotes: true,
    fixHyphenations: true,
    minSentenceLength: 3,
  },
  
  // Actions
  setSentences: (sentences) => set({ sentences }),
  clearSentences: () => set({ sentences: [] }),
  
  setLoading: (loading, message = '') => 
    set({ loading, loadingMessage: message, uploadProgress: loading ? 0 : 100 }),
  
  setUploadProgress: (progress) => set({ uploadProgress: progress }),
  
  setSentenceLength: (length) => set({ sentenceLength: length }),
  
  setAdvancedOptions: (options) => set({ advancedOptions: options }),
}));

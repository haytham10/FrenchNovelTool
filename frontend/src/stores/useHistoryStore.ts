/**
 * History Store - Manages processing history with optimistic updates
 */

import { create } from 'zustand';
import type { HistoryEntry } from '@/lib/types';

interface HistoryState {
  // History data
  history: HistoryEntry[];
  setHistory: (history: HistoryEntry[]) => void;
  
  // Optimistic operations
  addHistoryEntry: (entry: HistoryEntry) => void;
  removeHistoryEntry: (id: number) => void;
  
  // Loading state
  isLoading: boolean;
  setIsLoading: (loading: boolean) => void;
  
  // Error state
  error: string | null;
  setError: (error: string | null) => void;
}

export const useHistoryStore = create<HistoryState>((set) => ({
  // Initial state
  history: [],
  isLoading: false,
  error: null,
  
  // Actions
  setHistory: (history) => set({ history }),
  
  addHistoryEntry: (entry) => 
    set((state) => ({ history: [entry, ...state.history] })),
  
  removeHistoryEntry: (id) => 
    set((state) => ({ 
      history: state.history.filter((entry) => entry.id !== id) 
    })),
  
  setIsLoading: (loading) => set({ isLoading: loading }),
  
  setError: (error) => set({ error }),
}));

/**
 * Credit Store - Manages user credit state
 */

import { create } from 'zustand';
import type { CreditSummary } from '@/lib/types';

interface CreditState {
  credits: CreditSummary | null;
  setCredits: (credits: CreditSummary | null) => void;
  loading: boolean;
  setLoading: (loading: boolean) => void;
}

export const useCreditStore = create<CreditState>((set) => ({
  credits: null,
  loading: false,
  setCredits: (credits) => set({ credits }),
  setLoading: (loading) => set({ loading }),
}));

/**
 * Settings Store - Manages user settings
 */

import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { UserSettings } from '@/lib/api';

interface SettingsState extends UserSettings {
  // Actions
  updateSettings: (settings: Partial<UserSettings>) => void;
  resetSettings: () => void;
}

const defaultSettings: UserSettings = {
  sentence_length_limit: 12,
  default_folder_id: undefined,
  default_sheet_name_pattern: undefined,
};

export const useSettingsStore = create<SettingsState>()(
  persist(
    (set) => ({
      // Initial state
      ...defaultSettings,
      
      // Actions
      updateSettings: (settings) => 
        set((state) => ({ ...state, ...settings })),
      
      resetSettings: () => set(defaultSettings),
    }),
    {
      name: 'user-settings',
    }
  )
);

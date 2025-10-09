/**
 * Settings Store - Manages user settings
 */

import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';
import { UserSettings } from '@/lib/types';

interface SettingsState {
  settings: UserSettings;
  setSettings: (settings: Partial<UserSettings>) => void;
  loadSettings: (settings: UserSettings) => void;
}

export const useSettingsStore = create<SettingsState>()(
  persist(
    (set) => ({
      settings: {
        sentence_length_limit: 25,
        default_folder_id: undefined,
        default_sheet_name_pattern: '{filename}_{date}',
        default_wordlist_id: undefined,
      },
      setSettings: (newSettings) => set((state) => ({ settings: { ...state.settings, ...newSettings } })),
      loadSettings: (loadedSettings) => set({ settings: loadedSettings }),
    }),
    {
      name: 'user-settings-storage',
      storage: createJSONStorage(() => localStorage),
    }
  )
);

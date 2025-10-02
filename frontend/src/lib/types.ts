/**
 * Shared TypeScript types for the application
 */

export interface User {
  id: number;
  email: string;
  name: string;
  avatarUrl?: string;
}

export interface HistoryEntry {
  id: number;
  timestamp: string;
  original_filename: string;
  processed_sentences_count: number;
  spreadsheet_url?: string;
  error_message?: string;
  error_code?: string;
  failed_step?: 'upload' | 'extract' | 'analyze' | 'normalize' | 'export';
  settings?: {
    sentence_length?: number;
    gemini_model?: string;
    advanced_options?: Record<string, unknown>;
  };
}

// Derived status type
export type HistoryStatus = 'success' | 'failed' | 'processing';

// Helper to get status from history entry
export function getHistoryStatus(entry: HistoryEntry): HistoryStatus {
  if (entry.error_message) return 'failed';
  if (entry.spreadsheet_url) return 'success';
  return 'processing';
}

export interface UserSettings {
  sentence_length_limit: number;
  default_folder_id?: string;
  default_sheet_name_pattern?: string;
}

// Alias for consistency
export type ProcessingHistory = HistoryEntry;

export interface LoginResponse {
  access_token: string;
  refresh_token: string;
  user: User;
  has_sheets_access: boolean;
}

export interface ExportToSheetRequest {
  sentences: string[];
  sheetName: string;
  folderId?: string | null;
}

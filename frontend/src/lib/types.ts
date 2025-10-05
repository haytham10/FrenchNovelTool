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
  job_id?: number;  // Link to job for credit tracking
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
export type HistoryStatus = 'complete' | 'exported' | 'failed' | 'processing';

// Helper to get status from history entry
export function getHistoryStatus(entry: HistoryEntry): HistoryStatus {
  // Priority: failed > exported > complete > processing
  if (entry.error_message) return 'failed';
  if (entry.spreadsheet_url) return 'exported';
  // If there is no spreadsheet but the entry has processed sentences, mark as complete
  if (typeof entry.processed_sentences_count === 'number' && entry.processed_sentences_count > 0) return 'complete';
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

// Credit System Types

export interface CreditSummary {
  balance: number;
  granted: number;
  used: number;
  refunded: number;
  adjusted: number;
  month: string;
  next_reset: string;
}

export interface CreditLedgerEntry {
  id: number;
  user_id: number;
  month: string;
  delta_credits: number;
  reason: 'monthly_grant' | 'job_reserve' | 'job_final' | 'job_refund' | 'admin_adjustment';
  job_id?: number;
  pricing_version?: string;
  description?: string;
  timestamp: string;
}

export interface Job {
  id: number;
  user_id: number;
  history_id?: number;
  status: 'pending' | 'processing' | 'completed' | 'failed' | 'cancelled';
  original_filename: string;
  model: string;
  estimated_tokens?: number;
  actual_tokens?: number;
  estimated_credits: number;
  actual_credits?: number;
  pricing_version: string;
  pricing_rate: number;
  processing_settings?: Record<string, unknown>;
  created_at: string;
  started_at?: string;
  completed_at?: string;
  error_message?: string;
  error_code?: string;
}

export interface CostEstimate {
  model: string;
  model_preference: string;
  estimated_tokens: number;
  estimated_credits: number;
  pricing_rate: number;
  pricing_version: string;
  estimation_method: 'api' | 'heuristic';
  current_balance: number;
  allowed: boolean;
  message?: string;
}

export interface JobConfirmRequest {
  estimated_credits: number;
  model_preference: string;
  processing_settings?: Record<string, unknown>;
}

export interface JobConfirmResponse {
  job_id: number;
  status: string;
  estimated_credits: number;
  reserved: boolean;
  message: string;
}

export interface JobFinalizeRequest {
  actual_tokens: number;
  success: boolean;
  error_message?: string;
  error_code?: string;
}

export interface JobFinalizeResponse {
  job_id: number;
  status: string;
  estimated_credits: number;
  actual_credits: number;
  adjustment: number;
  refunded: boolean;
  refund_amount?: number;
  message: string;
}


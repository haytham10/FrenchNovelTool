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
  default_wordlist_id?: number;
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
  progress_percent?: number;
  current_step?: string;
  error_message?: string;
  chunk_results?: ChunkResult[];
  created_at: string;
  updated_at: string;
}

export interface Sentence {
  original: string;
  normalized?: string;
  token_count?: number;
}

export interface ChunkResult {
  chunk_id: number;
  status: 'success' | 'failed';
  sentences?: Sentence[];
  tokens?: number;
  error?: string;
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
}

// ============================================================================
// Vocabulary Coverage Tool Types
// ============================================================================

export interface WordList {
  id: number;
  owner_user_id: number | null;
  name: string;
  source_type: 'manual' | 'csv' | 'google_sheet';
  source_ref?: string | null;
  normalized_count: number;
  canonical_samples: string[];
  created_at: string;
  updated_at?: string;
  is_global_default: boolean;
}

export interface CoverageRun {
  id: number;
  user_id: number;
  mode: 'coverage' | 'filter' | 'batch';
  source_type: 'history' | 'job';
  source_id: number | null;
  source_ids?: number[];
  wordlist_id?: number;
  status: 'pending' | 'processing' | 'completed' | 'failed' | 'cancelled';
  progress_percent: number;
  stats_json: Record<string, unknown> | null;
  learning_set_json: Record<string, unknown>[] | null;
  config_json: Record<string, unknown> | null;
  created_at: string;
  started_at?: string | null;
  completed_at?: string | null;
  error_message?: string | null;
  celery_task_id?: string;
  learning_set?: LearningSetEntry[];
}

export interface CoverageAssignment {
  id: number;
  run_id: number;
  word_key: string;
  surface_form: string;
  sentence_text: string;
  sentence_index: number | null;
  source_id: number | null;
}

export interface LearningSetEntry {
  rank: number;
  sentence: string;
  new_words_covered: string[];
  all_matched_words: string[];
  sentence_index: number;
  token_count: number;
  new_word_count: number;
  score: number | null;
  source_id?: number;
  words?: string[]; // Added on frontend
}

export interface CoverageDiagnosis {
  total_words: number;
  covered_words: number;
  uncovered_words: number;
  coverage_percentage: number;
  recommendation: string;
  categories: {
    [key: string]: {
      description: string;
      count: number;
      sample_words: string[];
    };
  };
}

// (Removed misplaced property declaration)

// Detailed history for drill-down view
export interface HistoryDetail extends HistoryEntry {
  sentences: Array<{ normalized: string; original: string }>;
  chunk_ids: number[];
  chunks: ChunkDetail[];
  sentences_source?: 'snapshot' | 'live_chunks';
}

// Details for a single processing chunk
export interface ChunkDetail {
  id: number;
  job_id: number;
  chunk_id: number;
  start_page: number;
  end_page: number;
  page_count: number;
  has_overlap: boolean;
  status: 'pending' | 'processing' | 'success' | 'failed' | 'retry_scheduled';
  attempts: number;
  max_retries: number;
  last_error?: string;
  last_error_code?: string;
  processed_at?: string;
  created_at: string;
  updated_at?: string;
}

// PDF cost estimation response
export interface EstimatePdfResponse {
  page_count: number;
  file_size: number;
  image_count: number;
  estimated_tokens: number;
  estimated_credits: number;
  model: string;
  model_preference: string;
  pricing_rate: number;
  capped: boolean;
  warning?: string;
}

// Async PDF processing request
export interface ProcessPdfAsyncRequest {
  job_id: number;
  pdf_file: File;
  sentence_length_limit?: number;
  gemini_model?: string;
  ignore_dialogue?: boolean;
  preserve_formatting?: boolean;
  fix_hyphenation?: boolean;
  min_sentence_length?: number;
}

// Async PDF processing response
export interface ProcessPdfAsyncResponse {
  job_id: number;
  task_id: string;
  status: string;
  message: string;
}

// Job cancellation response
export interface CancelJobResponse {
  message: string;
  job_id: number;
  status: string;
}

// History export request
export interface ExportHistoryRequest {
  sheetName?: string;
  folderId?: string | null;
}


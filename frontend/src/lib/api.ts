/**
 * API client for backend communication
 */

import axios, { AxiosError } from 'axios';
import { getAccessToken, getRefreshToken, setTokens, clearTokens } from './auth';
import type { Job } from './types';

const _rawApiBase = (() => {
  const explicitBase = process.env.NEXT_PUBLIC_API_BASE_URL;
  const legacyUrl = process.env.NEXT_PUBLIC_API_URL;
  if (explicitBase) return explicitBase;
  if (legacyUrl) {
    return legacyUrl.replace(/\/+$/,'') + '/api/v1';
  }
  return 'http://localhost:5000/api/v1';
})();
const API_BASE_URL = (() => {
  if (/^https?:\/\//i.test(_rawApiBase)) return _rawApiBase;
  // If no scheme provided, default to https in production and http in dev
  const scheme = process.env.NODE_ENV === 'production' ? 'https://' : 'http://';
  return `${scheme}${_rawApiBase}`;
})();

// Create axios instance with default config
const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor to add auth token
api.interceptors.request.use((config) => {
  const token = getAccessToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Response interceptor to handle token refresh
api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config;
    
    // If 401 and we have a refresh token, try to refresh
    if (error.response?.status === 401 && getRefreshToken() && originalRequest) {
      try {
        const refreshToken = getRefreshToken();
        const response = await axios.post(`${API_BASE_URL}/auth/refresh`, {
          refresh_token: refreshToken,
        });
        
        const { access_token, refresh_token } = response.data;
        setTokens(access_token, refresh_token);
        
        // Retry original request with new token
        originalRequest.headers.Authorization = `Bearer ${access_token}`;
        return api(originalRequest);
      } catch (refreshError) {
        // Refresh failed, clear tokens
        clearTokens();
        throw refreshError;
      }
    }
    
    return Promise.reject(error);
  }
);

// Types
export interface User {
  id: number;
  email: string;
  name: string;
  picture?: string;
}

export interface LoginResponse {
  access_token: string;
  refresh_token: string;
  user: User;
  has_sheets_access: boolean;
}

export interface ProcessingHistory {
  id: number;
  job_id?: number;
  timestamp: string;
  original_filename: string;
  processed_sentences_count: number;
  spreadsheet_url?: string;
  error_message?: string;
  error_code?: string;
  failed_step?: 'upload' | 'extract' | 'analyze' | 'normalize' | 'export';
  settings?: {
    sentence_length_limit?: number;
    gemini_model?: string;
    advanced_options?: Record<string, unknown>;
  };
  exported_to_sheets?: boolean;
  export_sheet_url?: string;
}

export interface HistoryDetail extends ProcessingHistory {
  sentences: Array<{ normalized: string; original: string }>;
  chunk_ids: number[];
  chunks: ChunkDetail[];
  sentences_source?: 'snapshot' | 'live_chunks';
}

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

export interface UserSettings {
  sentence_length_limit: number;
  default_folder_id?: string;
  default_sheet_name_pattern?: string;
  // Optional ID of the default word list for vocabulary coverage
  default_wordlist_id?: number | null;
}

/**
 * Authentication APIs
 */

export async function loginWithGoogle(token?: string, code?: string): Promise<LoginResponse> {
  const response = await api.post('/auth/google', { token, code });
  return response.data;
}

export async function getCurrentUser(): Promise<User> {
  const response = await api.get('/auth/me');
  return response.data;
}

export async function refreshAccessToken(): Promise<LoginResponse> {
  const refreshToken = getRefreshToken();
  const response = await api.post('/auth/refresh', { refresh_token: refreshToken });
  return response.data;
}

/**
 * PDF Processing APIs
 */

export interface ProcessPdfOptions {
  onUploadProgress?: (progress: number) => void;
  jobId?: number; // Optional job ID for credit flow
}

export async function extractPdfText(file: File): Promise<{ text: string; page_count: number }> {
  const formData = new FormData();
  formData.append('pdf_file', file);
  
  const response = await api.post('/extract-pdf-text', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });
  
  return response.data;
}

export interface EstimatePdfRequest {
  file: File;
  model_preference?: 'balanced' | 'quality' | 'speed';
}

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

export async function estimatePdfCost(request: EstimatePdfRequest): Promise<EstimatePdfResponse> {
  const formData = new FormData();
  formData.append('pdf_file', request.file);
  
  if (request.model_preference) {
    formData.append('model_preference', request.model_preference);
  }
  
  const response = await api.post('/estimate-pdf', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });
  
  return response.data;
}

export async function processPdf(file: File, options?: ProcessPdfOptions): Promise<string[]> {
  const formData = new FormData();
  formData.append('pdf_file', file);
  
  if (options?.jobId) {
    formData.append('job_id', options.jobId.toString());
  }
  
  const response = await api.post('/process-pdf', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
    onUploadProgress: (progressEvent) => {
      if (options?.onUploadProgress && progressEvent.total) {
        const progress = Math.round((progressEvent.loaded * 100) / progressEvent.total);
        options.onUploadProgress(progress);
      }
    },
  });
  
  return response.data.sentences || [];
}

/**
 * Google Sheets Export APIs
 */

export interface ExportToSheetRequest {
  sentences: string[];
  sheetName: string;
  folderId?: string | null;
  mode?: 'new' | 'append';
  existingSheetId?: string;
  tabName?: string;
  createNewTab?: boolean;
  headers?: { name: string; enabled: boolean; order: number }[];
  columnOrder?: string[];
  sharing?: {
    addCollaborators?: boolean;
    collaboratorEmails?: string[];
    publicLink?: boolean;
  };
  sentenceIndices?: number[];
}

export async function exportToSheet(data: ExportToSheetRequest): Promise<string> {
  const response = await api.post('/export-to-sheet', data);
  return response.data.spreadsheet_url;
}

/**
 * History APIs
 */

export async function getProcessingHistory(): Promise<ProcessingHistory[]> {
  const response = await api.get('/history');
  return response.data || [];
}

// Alias for backward compatibility
export const fetchHistory = getProcessingHistory;

/**
 * Get detailed history entry with sentences and chunk information
 */
export async function getHistoryDetail(entryId: number): Promise<HistoryDetail> {
  const response = await api.get(`/history/${entryId}`);
  return response.data;
}

/**
 * Get chunk details for a history entry
 */
export async function getHistoryChunks(entryId: number): Promise<{ chunks: ChunkDetail[] }> {
  const response = await api.get(`/history/${entryId}/chunks`);
  return response.data;
}

/**
 * Refresh history snapshot from current JobChunk results
 */
export async function refreshHistoryFromChunks(entryId: number): Promise<{ 
  message: string; 
  sentences_count: number; 
  entry: HistoryDetail 
}> {
  const response = await api.post(`/history/${entryId}/refresh`);
  return response.data;
}

/**
 * Export history entry to Google Sheets
 */
export interface ExportHistoryRequest {
  sheetName?: string;
  folderId?: string | null;
}

export async function exportHistoryToSheets(entryId: number, data?: ExportHistoryRequest): Promise<{ 
  spreadsheet_url: string;
  sentences_source?: string;
  sentences_count?: number;
}> {
  const response = await api.post(`/history/${entryId}/export`, data || {});
  return response.data;
}

/**
 * Retry a failed history entry
 */
export async function retryHistoryEntry(entryId: number): Promise<{ message: string; entry_id: number; settings: Record<string, unknown> }> {
  const response = await api.post(`/history/${entryId}/retry`);
  return response.data;
}

/**
 * Duplicate a history entry with same settings
 */
export async function duplicateHistoryEntry(entryId: number): Promise<{ message: string; settings: Record<string, unknown>; original_filename: string }> {
  const response = await api.post(`/history/${entryId}/duplicate`);
  return response.data;
}

/**
 * Settings APIs
 */

export async function getUserSettings(): Promise<UserSettings> {
  const response = await api.get('/settings');
  return response.data;
}

export async function updateUserSettings(settings: Partial<UserSettings>): Promise<UserSettings> {
  // Backend route accepts POST for saving user settings
  const response = await api.post('/settings', settings);
  return response.data.settings || response.data;
}

// Aliases for backward compatibility
export const fetchSettings = getUserSettings;
export const saveSettings = updateUserSettings;

/**
 * Credit System APIs
 */

export interface CreditSummary {
  balance: number;
  granted: number;
  used: number;
  refunded: number;
  adjusted: number;
  month: string;
  next_reset: string;
}

export async function getCredits(): Promise<CreditSummary> {
  const response = await api.get('/credits/me');
  return response.data;
}

export interface CostEstimateRequest {
  text: string;
  model_preference: 'balanced' | 'quality' | 'speed';
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

export async function estimateCost(request: CostEstimateRequest): Promise<CostEstimate> {
  const response = await api.post('/credits/estimate', request);
  return response.data;
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

export async function startPdfProcessingJob(request: JobConfirmRequest): Promise<JobConfirmResponse> {
  const response = await api.post('/credits/jobs/confirm', request);
  return response.data;
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

export async function finalizeJob(jobId: number, request: JobFinalizeRequest): Promise<JobFinalizeResponse> {
  const response = await api.post(`/credits/jobs/${jobId}/finalize`, request);
  return response.data;
}

export async function getJob(jobId: number): Promise<Job> {
  const response = await api.get(`/credits/jobs/${jobId}`);
  return response.data;
}

export async function getJobs(params?: { limit?: number; status?: string }): Promise<Job[]> {
  const response = await api.get('/credits/jobs', { params });
  return response.data || [];
}

/**
 * Start async PDF processing
 */
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

export interface ProcessPdfAsyncResponse {
  job_id: number;
  task_id: string;
  status: string;
  message: string;
}

export async function processPdfAsync(request: ProcessPdfAsyncRequest): Promise<ProcessPdfAsyncResponse> {
  const formData = new FormData();
  formData.append('pdf_file', request.pdf_file);
  formData.append('job_id', request.job_id.toString());
  
  if (request.sentence_length_limit !== undefined) {
    formData.append('sentence_length_limit', request.sentence_length_limit.toString());
  }
  if (request.gemini_model) {
    formData.append('gemini_model', request.gemini_model);
  }
  if (request.ignore_dialogue !== undefined) {
    formData.append('ignore_dialogue', request.ignore_dialogue.toString());
  }
  if (request.preserve_formatting !== undefined) {
    formData.append('preserve_formatting', request.preserve_formatting.toString());
  }
  if (request.fix_hyphenation !== undefined) {
    formData.append('fix_hyphenation', request.fix_hyphenation.toString());
  }
  if (request.min_sentence_length !== undefined) {
    formData.append('min_sentence_length', request.min_sentence_length.toString());
  }
  
  const response = await api.post('/process-pdf-async', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });
  return response.data;
}

/**
 * Cancel a running job
 */
export interface CancelJobResponse {
  message: string;
  job_id: number;
  status: string;
}

export async function cancelJob(jobId: number): Promise<CancelJobResponse> {
  const response = await api.post(`/jobs/${jobId}/cancel`);
  return response.data;
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

export async function getCreditLedger(params?: { month?: string; limit?: number }): Promise<CreditLedgerEntry[]> {
  const response = await api.get('/credits/ledger', { params });
  return response.data || [];
}

/**
 * Error handling utility with user-friendly messages
 */

export function getApiErrorMessage(error: unknown, defaultMessage = 'An unexpected error occurred'): string {
  if (axios.isAxiosError(error)) {
    const axiosError = error as AxiosError<{ msg?: string; message?: string; error?: string; detail?: string }>;
    
    // Handle specific HTTP status codes with user-friendly messages
    if (axiosError.response) {
      const status = axiosError.response.status;
      const data = axiosError.response.data;
      
      // Extract error message from response
      const serverMessage = data?.msg || data?.message || data?.error || data?.detail;
      
      switch (status) {
        case 400:
          return serverMessage || 'Invalid request. Please check your input and try again.';
        case 401:
          return 'Your session has expired. Please log in again.';
        case 403:
          return 'You do not have permission to perform this action.';
        case 404:
          return 'The requested resource was not found.';
        case 413:
          return 'The file is too large. Please upload a smaller file.';
        case 422:
          return serverMessage || 'The data provided is invalid. Please check and try again.';
        case 429:
          return 'Too many requests. Please wait a moment and try again.';
        case 500:
          return 'A server error occurred. Please try again later.';
        case 502:
        case 503:
          return 'The service is temporarily unavailable. Please try again in a few moments.';
        case 504:
          return 'The request took too long to complete. Please try again.';
        default:
          return serverMessage || defaultMessage;
      }
    }
    
    // Network error (no response from server)
    if (axiosError.code === 'ERR_NETWORK' || axiosError.message.includes('Network Error')) {
      return 'Unable to connect to the server. Please check your internet connection.';
    }
    
    // Timeout error
    if (axiosError.code === 'ECONNABORTED') {
      return 'The request timed out. Please try again.';
    }
    
    // Other axios errors
    if (axiosError.message) {
      return axiosError.message;
    }
  }
  
  if (error instanceof Error) {
    return error.message;
  }
  
  return defaultMessage;
}

// ============================================================================
// Vocabulary Coverage Tool API
// ============================================================================

export interface WordList {
  id: number;
  owner_user_id: number | null;
  name: string;
  source_type: 'csv' | 'google_sheet' | 'manual';
  source_ref?: string | null;
  normalized_count: number;
  canonical_samples: string[];
  is_global_default: boolean;
  created_at: string;
  updated_at?: string;
}

export interface IngestionReport {
  original_count: number;
  normalized_count: number;
  duplicates: Array<{ word: string; normalized: string }>;
  multi_token_entries: Array<{ original: string; head_token: string }>;
  variants_expanded: number;
  anomalies: Array<{ word: string; issue: string }>;
}

export interface CoverageRun {
  id: number;
  user_id: number;
  mode: 'coverage' | 'filter' | 'batch';
  source_type: 'job' | 'history';
  source_id: number;
  source_ids?: number[];
  wordlist_id?: number;
  config_json: Record<string, unknown>;
  status: 'pending' | 'processing' | 'completed' | 'failed' | 'cancelled';
  progress_percent: number;
  stats_json: Record<string, unknown>;
  learning_set_json?: Record<string, unknown>[] | null;
  created_at: string;
  started_at?: string | null;
  completed_at?: string;
  error_message?: string;
  celery_task_id?: string;
}

export interface CoverageAssignment {
  id: number;
  coverage_run_id?: number;
  run_id?: number;
  word_original?: string;
  word_key: string;
  lemma?: string;
  matched_surface?: string;
  surface_form?: string;
  sentence_index: number | null;
  sentence_text: string;
  sentence_score?: number;
  conflicts?: Record<string, unknown>;
  manual_edit?: boolean;
  notes?: string;
  source_id?: number | null;
}

export interface LearningSetEntry {
  rank: number;
  sentence?: string;
  sentence_text?: string;
  new_words_covered?: string[];
  all_matched_words?: string[];
  sentence_index: number | null;
  token_count?: number | null;
  new_word_count?: number | null;
  score?: number | null;
  source_id?: number;
  words?: string[];
}

/**
 * List all word lists accessible to the user (global + user's own)
 */
export const listWordLists = async (): Promise<{ wordlists: WordList[] }> => {
  const response = await api.get('/wordlists');
  return response.data;
};

/**
 * Create a new word list from CSV file upload
 */
export const createWordListFromFile = async (
  file: File,
  name: string,
  foldDiacritics: boolean = true
): Promise<{ wordlist: WordList; ingestion_report: IngestionReport }> => {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('name', name);
  formData.append('fold_diacritics', foldDiacritics.toString());

  const response = await api.post('/wordlists', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });
  return response.data;
};

/**
 * Create a new word list from array of words
 */
export const createWordListFromWords = async (
  name: string,
  words: string[],
  sourceType: 'manual' | 'google_sheet' = 'manual',
  sourceRef?: string,
  foldDiacritics: boolean = true,
  includeHeader: boolean = true
): Promise<{ wordlist: WordList; ingestion_report: IngestionReport }> => {
  const response = await api.post('/wordlists', {
    name,
    source_type: sourceType,
    source_ref: sourceRef,
    words,
    fold_diacritics: foldDiacritics,
    include_header: includeHeader,
  });
  return response.data;
};

/**
 * Get details of a specific word list
 */
export const getWordList = async (wordlistId: number): Promise<WordList> => {
  const response = await api.get(`/wordlists/${wordlistId}`);
  return response.data;
};

/**
 * Update a word list (name only)
 */
export const updateWordList = async (
  wordlistId: number,
  name: string
): Promise<WordList> => {
  const response = await api.patch(`/wordlists/${wordlistId}`, { name });
  return response.data;
};

/**
 * Delete a word list
 */
export const deleteWordList = async (wordlistId: number): Promise<void> => {
  await api.delete(`/wordlists/${wordlistId}`);
};

/**
 * Refresh a word list from its source (re-populate words_json)
 */
export const refreshWordList = async (
  wordlistId: number
): Promise<{ wordlist: WordList; refresh_report: { status: string; word_count: number; source: string } }> => {
  const response = await api.post(`/wordlists/${wordlistId}/refresh`);
  return response.data;
};

/**
 * Import sentences from Google Sheets URL
 */
export const importSentencesFromSheets = async (
  sheetUrl: string
): Promise<{ history_id: number; sentence_count: number; filename: string }> => {
  const response = await api.post('/coverage/import-from-sheets', {
    sheet_url: sheetUrl,
  });
  return response.data;
};

/**
 * Get coverage run cost
 */
export const getCoverageCost = async (): Promise<{ cost: number; currency: string }> => {
  const response = await api.get('/coverage/cost');
  return response.data;
};

/**
 * Create and start a coverage run
 */
export const createCoverageRun = async (params: {
  mode: 'coverage' | 'filter' | 'batch';
  source_type: 'job' | 'history';
  source_id?: number;
  source_ids?: number[];
  wordlist_id?: number;
  config?: Record<string, unknown>;
}): Promise<{ coverage_run: CoverageRun; task_id: string; credits_charged: number }> => {
  const response = await api.post('/coverage/run', params);
  return response.data;
};

/**
 * Get coverage run status and results
 */
export const getCoverageRun = async (
  runId: number,
  page: number = 1,
  perPage: number = 50
): Promise<{
  coverage_run: CoverageRun;
  assignments: CoverageAssignment[];
  pagination: {
    page: number;
    per_page: number;
    total: number;
    pages: number;
  };
  learning_set?: LearningSetEntry[];
}> => {
  const response = await api.get(`/coverage/runs/${runId}`, {
    params: { page, per_page: perPage },
  });
  return response.data;
};

/**
 * Swap a word assignment to a different sentence (Coverage mode)
 */
export const swapCoverageAssignment = async (
  runId: number,
  wordKey: string,
  newSentenceIndex: number
): Promise<CoverageAssignment> => {
  const response = await api.post(`/coverage/runs/${runId}/swap`, {
    word_key: wordKey,
    new_sentence_index: newSentenceIndex,
  });
  return response.data;
};

/**
 * Export coverage run to Google Sheets
 */
export const exportCoverageRun = async (
  runId: number,
  sheetName: string,
  folderId?: string
): Promise<{ message: string; spreadsheet_id?: string; spreadsheet_url?: string }> => {
  const response = await api.post(`/coverage/runs/${runId}/export`, {
    sheet_name: sheetName,
    folder_id: folderId,
  });
  return response.data;
};

export const downloadCoverageRunCSV = async (runId: number): Promise<Blob> => {
  const response = await api.get(`/coverage/runs/${runId}/download`, {
    responseType: 'blob',
  });
  return response.data;
};

/**
 * Coverage diagnosis types
 */
export interface DiagnosisCategory {
  count: number;
  sample_words: string[];
  description: string;
}

export interface CoverageDiagnosis {
  total_words: number;
  covered_words: number;
  uncovered_words: number;
  coverage_percentage: number;
  categories: {
    not_in_corpus: DiagnosisCategory;
    only_in_long_sentences: DiagnosisCategory;
    only_in_short_sentences: DiagnosisCategory;
    in_valid_but_missed: DiagnosisCategory;
  };
  recommendation: string;
}

/**
 * Diagnose coverage run to identify why words are uncovered
 */
export const diagnoseCoverageRun = async (runId: number): Promise<CoverageDiagnosis> => {
  const response = await api.get(`/coverage/runs/${runId}/diagnosis`);
  return response.data;
};

export default api;

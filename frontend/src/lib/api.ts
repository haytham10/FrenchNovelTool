/**
 * API client for backend communication
 */

import axios, { AxiosError } from 'axios';
import { getAccessToken, getRefreshToken, setTokens, clearTokens } from './auth';

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
 * Export history entry to Google Sheets
 */
export interface ExportHistoryRequest {
  sheetName?: string;
  folderId?: string | null;
}

export async function exportHistoryToSheets(entryId: number, data?: ExportHistoryRequest): Promise<{ spreadsheet_url: string }> {
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
  const response = await api.put('/settings', settings);
  return response.data;
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
  const response = await api.get('/me/credits');
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
  const response = await api.post('/estimate', request);
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

export async function confirmJob(request: JobConfirmRequest): Promise<JobConfirmResponse> {
  const response = await api.post('/jobs/confirm', request);
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
  const response = await api.post(`/jobs/${jobId}/finalize`, request);
  return response.data;
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
  // Async processing fields
  celery_task_id?: string;
  progress_percent?: number;
  current_step?: string;
  total_chunks?: number;
  processed_chunks?: number;
  chunk_results?: Array<{
    chunk_id: number;
    sentences?: unknown[];
    tokens?: number;
    status: 'success' | 'failed';
    error?: string;
  }>;
  failed_chunks?: number[];
  retry_count?: number;
  max_retries?: number;
  is_cancelled?: boolean;
  cancelled_at?: string;
  cancelled_by?: number;
  processing_time_seconds?: number;
  gemini_api_calls?: number;
  gemini_tokens_used?: number;
  task_state?: {
    state: string;
    info: Record<string, unknown>;
  };
}

export async function getJob(jobId: number): Promise<Job> {
  const response = await api.get(`/jobs/${jobId}`);
  return response.data;
}

export async function getJobs(params?: { limit?: number; status?: string }): Promise<Job[]> {
  const response = await api.get('/jobs', { params });
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

export default api;

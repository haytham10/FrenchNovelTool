/**
 * API client for backend communication
 */

import axios, { AxiosError } from 'axios';
import {
  User,
  LoginResponse,
  HistoryEntry,
  HistoryDetail,
  ChunkDetail,
  UserSettings,
  CreditSummary,
  CreditLedgerEntry,
  CostEstimate,
  Job,
  JobConfirmRequest,
  JobConfirmResponse,
  JobFinalizeRequest,
  JobFinalizeResponse,
  WordList,
  CoverageRun,
  CoverageAssignment,
  LearningSetEntry,
  EstimatePdfResponse,
  ProcessPdfAsyncRequest,
  ProcessPdfAsyncResponse,
  CancelJobResponse,
  ExportHistoryRequest,
} from './types';
import { getAccessToken, getRefreshToken, setTokens, clearTokens } from './auth';

const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:5000/api/v1',
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
    const originalRequest = error.config as (typeof error.config) & { _retry?: boolean };
    
    // If 401 and we have a refresh token, try to refresh
    if (error.response?.status === 401 && getRefreshToken() && originalRequest && !originalRequest._retry) {
      originalRequest._retry = true;
      try {
        const refreshToken = getRefreshToken();
        const response = await axios.post(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:5000/api/v1'}/auth/refresh`, {
          refresh_token: refreshToken,
        });
        
        const { access_token, refresh_token } = response.data;
        setTokens(access_token, refresh_token);
        
        // Retry original request with new token
        if (originalRequest.headers) {
          originalRequest.headers.Authorization = `Bearer ${access_token}`;
        }
        return api(originalRequest);
      } catch (refreshError) {
        // Refresh failed, clear tokens
        clearTokens();
        window.location.href = '/login'; // Redirect to login
        throw refreshError;
      }
    }
    
    return Promise.reject(error);
  }
);

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

export async function getProcessingHistory(): Promise<{ history: HistoryEntry[] }> {
  const response = await api.get('/history');
  return response.data || { history: [] };
}

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

/**
 * Credit System APIs
 */

export async function getCredits(): Promise<CreditSummary> {
  const response = await api.get('/me/credits');
  return response.data;
}

export interface CostEstimateRequest {
  text: string;
  model_preference: 'balanced' | 'quality' | 'speed';
}

export async function estimateCost(request: CostEstimateRequest): Promise<CostEstimate> {
  const response = await api.post('/estimate', request);
  return response.data;
}

export async function confirmJob(request: JobConfirmRequest): Promise<JobConfirmResponse> {
  const response = await api.post('/jobs/confirm', request);
  return response.data;
}

export async function finalizeJob(jobId: number, request: JobFinalizeRequest): Promise<JobFinalizeResponse> {
  const response = await api.post(`/jobs/${jobId}/finalize`, request);
  return response.data;
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
export async function cancelJob(jobId: number): Promise<CancelJobResponse> {
  const response = await api.post(`/jobs/${jobId}/cancel`);
  return response.data;
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
// Vocabulary Coverage Endpoints
// ============================================================================

export const listWordLists = async (): Promise<{ wordlists: WordList[] }> => {
  const response = await api.get('/coverage/wordlists');
  return response.data;
};

export const createWordListFromWords = async (
  name: string,
  words: string[],
  foldDiacritics: boolean
): Promise<{ wordlist: WordList; report: Record<string, unknown> }> => {
  const response = await api.post('/coverage/wordlists/from-words', {
    name,
    words,
    fold_diacritics: foldDiacritics,
  });
  return response.data;
};

export const deleteWordList = async (wordlistId: number): Promise<{ message: string }> => {
  const response = await api.delete(`/coverage/wordlists/${wordlistId}`);
  return response.data;
};

export const createWordListFromFile = async (
  file: File,
  name: string,
  foldDiacritics: boolean
): Promise<{ wordlist: WordList; report: Record<string, unknown> }> => {
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

export const getCoverageCost = async (): Promise<{ cost: number }> => {
  const response = await api.get('/coverage/cost');
  return response.data;
};

export const getCoverageRun = async (
  runId: number
): Promise<{
  coverage_run: CoverageRun;
  assignments: CoverageAssignment[];
  learning_set: LearningSetEntry[];
}> => {
  const response = await api.get(`/coverage/runs/${runId}`);
  return response.data;
};

export const importSentencesFromSheets = async (
  sheetUrl: string
): Promise<{
  filename: string;
  sentence_count: number;
  history_id: number;
}> => {
  const response = await api.post('/coverage/import-from-sheets', { url: sheetUrl });
  return response.data;
};

export const createCoverageRun = async (params: {
  mode: 'coverage' | 'filter' | 'batch';
  source_type: 'history';
  source_id?: number;
  source_ids?: number[];
  wordlist_id?: number;
  config: Record<string, unknown>;
}): Promise<{ coverage_run: CoverageRun; credits_charged: number }> => {
  const response = await api.post('/coverage/run', params);
  return response.data;
};

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

export const diagnoseCoverageRun = async (runId: number): Promise<CoverageDiagnosis> => {
  const response = await api.get(`/coverage/runs/${runId}/diagnosis`);
  return response.data;
};

export default api;

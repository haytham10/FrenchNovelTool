/**
 * API client for backend communication
 */

import axios, { AxiosError } from 'axios';
import { getAccessToken, getRefreshToken, setTokens, clearTokens } from './auth';

// Support both variable names to match existing env files and Vercel config
const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL ||
  process.env.NEXT_PUBLIC_API_BASE_URL ||
  'http://localhost:5000/api/v1';

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
}

export async function processPdf(file: File, options?: ProcessPdfOptions): Promise<string[]> {
  const formData = new FormData();
  formData.append('pdf_file', file);
  
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

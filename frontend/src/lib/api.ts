/**
 * API client for backend communication
 */

import axios, { AxiosError } from 'axios';
import { getAccessToken, getRefreshToken, setTokens, clearTokens } from './auth';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:5000/api/v1';

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

export async function processPdf(file: File): Promise<string[]> {
  const formData = new FormData();
  formData.append('file', file);
  
  const response = await api.post('/process', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
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
 * Error handling utility
 */

export function getApiErrorMessage(error: unknown, defaultMessage = 'An unexpected error occurred'): string {
  if (axios.isAxiosError(error)) {
    const axiosError = error as AxiosError<{ msg?: string; message?: string; error?: string }>;
    
    // Extract error message from response
    if (axiosError.response?.data) {
      const data = axiosError.response.data;
      return data.msg || data.message || data.error || defaultMessage;
    }
    
    // Network error
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

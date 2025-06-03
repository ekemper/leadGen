// Base API Response Types
export interface ApiResponse<T = any> {
  status: 'success' | 'error';
  message?: string;
  data?: T;
  error?: {
    code: number;
    name: string;
    message: string;
  };
}

// Pagination
export interface PaginationMeta {
  page: number;
  limit: number;
  total: number;
  pages: number;
}

export interface PaginatedResponse<T> {
  data: T[];
  meta: PaginationMeta;
}

// Generic API Error
export interface ApiError {
  detail: string;
  type?: string;
  code?: number;
}

// FastAPI Validation Error
export interface ValidationError {
  loc: (string | number)[];
  msg: string;
  type: string;
}

export interface FastAPIError {
  detail: string | ValidationError[];
}

// Common Request/Response wrappers
export interface ListParams {
  page?: number;
  limit?: number;
  search?: string;
  sort_by?: string;
  sort_order?: 'asc' | 'desc';
}

// Health check response
export interface HealthResponse {
  status: string;
  timestamp: string;
  version?: string;
}

// Generic filters
export interface BaseFilters {
  page?: number;
  limit?: number;
  search?: string;
} 
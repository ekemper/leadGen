export const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:5001';
import { getRequestId } from '../utils/requestId';

function handleAuthError(response: Response) {
    // Only handle authentication errors, not other 401/403 responses
    if (response.status === 401 || response.status === 403) {
        const contentType = response.headers.get('content-type');
        if (contentType && contentType.includes('application/json')) {
            response.clone().json().then(data => {
                // Only clear tokens if it's an actual auth error
                const errorMessage = data.error?.message || data.message;
                if (errorMessage?.toLowerCase().includes('token') || 
                    errorMessage?.toLowerCase().includes('unauthorized') ||
                    errorMessage?.toLowerCase().includes('forbidden') ||
                    errorMessage?.toLowerCase().includes('user not found')) {
                    localStorage.clear();
                    sessionStorage.clear();
                    setTimeout(() => {
                        window.location.href = '/signin';
                    }, 1500);
                }
            }).catch(() => {
                // If we can't parse the response as JSON, assume it's an auth error
                localStorage.clear();
                sessionStorage.clear();
                setTimeout(() => {
                    window.location.href = '/signin';
                }, 1500);
            });
        }
    }
}

export function getAuthHeaders(): Record<string, string> {
    const token = localStorage.getItem('token');
    if (!token) {
        return {};
    }
    return {
        'Authorization': `Bearer ${token}`,
        'Accept': 'application/json',
        'Content-Type': 'application/json'
    };
}

const defaultHeaders: Record<string, string> = {
    'Accept': 'application/json',
    'Content-Type': 'application/json',
    'Origin': 'http://localhost:5173',
};

const defaultOptions: RequestInit = {
    credentials: 'include',
    mode: 'cors',
    headers: defaultHeaders,
};

function withRequestId(headers: Record<string, string>): Record<string, string> {
    return {
        ...headers,
        'X-Request-ID': getRequestId(),
    };
}

export const api = {
    get: async (endpoint: string, params?: any) => {
        const url = new URL(`${API_BASE_URL}${endpoint}`);
        if (params) {
            Object.entries(params).forEach(([key, value]) => {
                if (value !== undefined && value !== null) {
                    url.searchParams.append(key, String(value));
                }
            });
        }
        const headers = withRequestId(getAuthHeaders());
        const response = await fetch(url.toString(), {
            ...defaultOptions,
            method: 'GET',
            headers,
        });
        handleAuthError(response);
        const responseData = await response.json();
        
        if (!response.ok) {
            const errorMessage = responseData.error?.message || responseData.message || `HTTP error! status: ${response.status}`;
            throw new Error(errorMessage);
        }
        
        return responseData;
    },
    
    post: async (endpoint: string, data?: any) => {
        // Distinct logging for login requests
        if (endpoint.includes('/auth/login')) {
            console.log('[LOGIN REQUEST] endpoint:', endpoint);
            console.log('[LOGIN REQUEST] headers:', {
                'Content-Type': 'application/json',
                ...getAuthHeaders(),
            });
            console.log('[LOGIN REQUEST] body:', data);
        }
        const response = await fetch(`${API_BASE_URL}${endpoint}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                ...getAuthHeaders(),
            } as HeadersInit,
            body: JSON.stringify(data),
        });
        handleAuthError(response);
        const responseData = await response.json();
        if (!response.ok) {
            let errorMessage = '';
            if (typeof responseData.error === 'string') {
                errorMessage = responseData.error;
            } else if (responseData.error && typeof responseData.error === 'object') {
                errorMessage = responseData.error.message || JSON.stringify(responseData.error);
            } else {
                errorMessage = responseData.message || `HTTP error! status: ${response.status}`;
            }
            throw new Error(errorMessage);
        }
        return responseData;
    },

    put: async (endpoint: string, data: any) => {
        const headers = withRequestId(getAuthHeaders());
        const response = await fetch(`${API_BASE_URL}${endpoint}`, {
            ...defaultOptions,
            method: 'PUT',
            body: JSON.stringify(data),
            headers,
        });
        handleAuthError(response);
        const responseData = await response.json();
        
        if (!response.ok) {
            const errorMessage = responseData.error?.message || responseData.message || `HTTP error! status: ${response.status}`;
            throw new Error(errorMessage);
        }
        
        return responseData;
    },

    patch: async (endpoint: string, data: any) => {
        const headers = withRequestId(getAuthHeaders());
        const response = await fetch(`${API_BASE_URL}${endpoint}`, {
            ...defaultOptions,
            method: 'PATCH',
            body: JSON.stringify(data),
            headers,
        });
        handleAuthError(response);
        const responseData = await response.json();
        if (!response.ok) {
            const errorMessage = responseData.error?.message || responseData.message || `HTTP error! status: ${response.status}`;
            throw new Error(errorMessage);
        }
        return responseData;
    }
}; 
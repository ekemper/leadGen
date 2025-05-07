export const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:5001';
import { getRequestId } from '../utils/requestId';

function handleAuthError(response: Response) {
    // Only handle authentication errors, not other 401/403 responses
    if (response.status === 401 || response.status === 403) {
        const contentType = response.headers.get('content-type');
        if (contentType && contentType.includes('application/json')) {
            response.clone().json().then(data => {
                // Only clear tokens if it's an actual auth error
                if (data.message?.toLowerCase().includes('token') || 
                    data.message?.toLowerCase().includes('unauthorized') ||
                    data.message?.toLowerCase().includes('forbidden') ||
                    data.message?.toLowerCase().includes('user not found')) {
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

function getAuthHeaders(): Record<string, string> {
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
            throw new Error(responseData.error || responseData.message || `HTTP error! status: ${response.status}`);
        }
        
        return responseData;
    },
    
    post: async (endpoint: string, data: any) => {
        const headers = withRequestId(getAuthHeaders());
        const response = await fetch(`${API_BASE_URL}${endpoint}`, {
            ...defaultOptions,
            method: 'POST',
            body: JSON.stringify(data),
            headers,
        });
        handleAuthError(response);
        const responseData = await response.json();
        
        if (!response.ok) {
            throw new Error(responseData.error || responseData.message || `HTTP error! status: ${response.status}`);
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
            throw new Error(responseData.error || responseData.message || `HTTP error! status: ${response.status}`);
        }
        
        return responseData;
    }
}; 
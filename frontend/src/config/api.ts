export const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:5001';

function handleAuthError(response: Response) {
    if (response.status === 401 || response.status === 403) {
        // Clear tokens and session data
        localStorage.clear();
        sessionStorage.clear();
        // Optionally, clear cookies if you store tokens there
        setTimeout(() => {
            window.location.href = '/login';
        }, 1500);
    }
}

function getAuthHeaders(): Record<string, string> {
    const token = localStorage.getItem('token');
    return token ? { 'Authorization': `Bearer ${token}` } : {};
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
        
        const response = await fetch(url.toString(), {
            headers: {
                ...getAuthHeaders(),
            } as HeadersInit,
        });
        handleAuthError(response);
        const responseData = await response.json();
        
        if (!response.ok) {
            throw new Error(responseData.error || responseData.message || `HTTP error! status: ${response.status}`);
        }
        
        return responseData;
    },
    
    post: async (endpoint: string, data: any) => {
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
            throw new Error(responseData.error || responseData.message || `HTTP error! status: ${response.status}`);
        }
        
        return responseData;
    }
}; 
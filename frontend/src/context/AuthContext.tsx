import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { api } from '../config/api';
import { logger } from '../utils/logger';
import { UserResponse } from '../types/auth';

interface AuthContextType {
  user: UserResponse | null;
  token: string | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<void>;
  signup: (email: string, password: string, confirmPassword: string) => Promise<void>;
  logout: () => void;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

interface AuthProviderProps {
  children: ReactNode;
}

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const [user, setUser] = useState<UserResponse | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const isAuthenticated = !!token && !!user;

  // Initialize auth state from localStorage
  useEffect(() => {
    const initializeAuth = async () => {
      try {
        const storedToken = localStorage.getItem('token');
        if (storedToken) {
          setToken(storedToken);
          await fetchCurrentUser(storedToken);
        }
      } catch (error) {
        logger.logError(error as Error, { context: 'AuthContext initialization' });
        // Clear invalid token
        localStorage.removeItem('token');
        setToken(null);
        setUser(null);
      } finally {
        setIsLoading(false);
      }
    };

    initializeAuth();
  }, []);

  const fetchCurrentUser = async (authToken?: string) => {
    try {
      const currentToken = authToken || token;
      if (!currentToken) {
        throw new Error('No token available');
      }

      const userData = await api.get('/auth/me');
      setUser(userData);
    } catch (error) {
      logger.logError(error as Error, { context: 'Fetching current user' });
      throw error;
    }
  };

  const login = async (email: string, password: string) => {
    try {
      setIsLoading(true);
      const response = await api.post('/auth/login', { email, password });
      
      if (response.token && response.token.access_token) {
        const newToken = response.token.access_token;
        setToken(newToken);
        setUser(response.user);
        localStorage.setItem('token', newToken);
        
        console.info('User logged in successfully', { userId: response.user.id });
      } else {
        throw new Error('Invalid login response format');
      }
    } catch (error) {
      logger.logError(error as Error, { context: 'Login attempt', email });
      throw error;
    } finally {
      setIsLoading(false);
    }
  };

  const signup = async (email: string, password: string, confirmPassword: string) => {
    try {
      setIsLoading(true);
      await api.post('/auth/signup', {
        email,
        password,
        confirm_password: confirmPassword
      });
      
      console.info('User signed up successfully', { email });
      
      // After successful signup, automatically log in
      await login(email, password);
    } catch (error) {
      logger.logError(error as Error, { context: 'Signup attempt', email });
      throw error;
    } finally {
      setIsLoading(false);
    }
  };

  const logout = () => {
    setUser(null);
    setToken(null);
    localStorage.removeItem('token');
    sessionStorage.clear();
    console.info('User logged out');
  };

  const refreshUser = async () => {
    if (!token) {
      throw new Error('No token available for refresh');
    }
    await fetchCurrentUser();
  };

  const value: AuthContextType = {
    user,
    token,
    isLoading,
    isAuthenticated,
    login,
    signup,
    logout,
    refreshUser,
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}; 
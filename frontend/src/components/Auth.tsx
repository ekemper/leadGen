import React, { useState } from 'react';
import { api } from '../config/api';
import './Auth.css';

interface AuthProps {
  onAuthSuccess: (token: string) => void;
}

interface AuthResponse {
  token?: string;
  message?: string;
}

interface AuthError {
  error: string;
}

const Auth: React.FC<AuthProps> = ({ onAuthSuccess }) => {
  const [isLogin, setIsLogin] = useState(true);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [successMessage, setSuccessMessage] = useState('');

  const handleLogin = async (loginEmail: string, loginPassword: string) => {
    const loginResponse = await api.post('/api/auth/login', {
      email: loginEmail,
      password: loginPassword
    });

    if (loginResponse && loginResponse.status === 'success' && loginResponse.data?.token) {
      // Clear form
      setEmail('');
      setPassword('');
      setConfirmPassword('');
      
      // Update auth state - this will trigger redirection in App.tsx
      onAuthSuccess(loginResponse.data.token);
    } else {
      throw new Error(
        loginResponse?.error?.message ||
        loginResponse?.data?.message ||
        'Invalid login response from server'
      );
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setSuccessMessage('');
    setIsLoading(true);

    if (!isLogin && password !== confirmPassword) {
      setError('Passwords do not match');
      setIsLoading(false);
      return;
    }

    try {
      if (!isLogin) {
        // Handle Signup
        const signupResponse = await api.post('/api/auth/signup', {
          email,
          password,
          confirm_password: confirmPassword
        });

        if (signupResponse && signupResponse.status === 'success') {
          setSuccessMessage(signupResponse.data?.message);
          // Automatically log in after successful signup
          try {
            await handleLogin(email, password);
          } catch (loginError) {
            setError('Signup successful, but automatic login failed. Please log in manually.');
            setIsLogin(true);
            setPassword('');
            setConfirmPassword('');
          }
        } else {
          setError(signupResponse?.error?.message || signupResponse?.data?.message || 'Invalid signup response from server');
        }
      } else {
        // Handle Login
        await handleLogin(email, password);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An unexpected error occurred');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="auth-container">
      <form onSubmit={handleSubmit} className="auth-form">
        <h2>{isLogin ? 'Login' : 'Sign Up'}</h2>
        
        {error && <div className="error-message">{error}</div>}
        {successMessage && <div className="success-message">{successMessage}</div>}
        
        <div className="form-group">
          <label htmlFor="email">Email:</label>
          <input
            type="email"
            id="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            disabled={isLoading}
          />
        </div>

        <div className="form-group">
          <label htmlFor="password">Password:</label>
          <input
            type="password"
            id="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            disabled={isLoading}
            autoComplete="new-password"
          />
        </div>

        {!isLogin && (
          <div className="form-group">
            <label htmlFor="confirmPassword">Confirm Password:</label>
            <input
              type="password"
              id="confirmPassword"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              required
              disabled={isLoading}
              autoComplete="new-password"
            />
          </div>
        )}

        <button 
          type="submit" 
          className="submit-button"
          disabled={isLoading}
        >
          {isLoading ? 'Please wait...' : (isLogin ? 'Login' : 'Sign Up')}
        </button>

        <button
          type="button"
          className="toggle-button"
          onClick={() => {
            setIsLogin(!isLogin);
            setError('');
            setSuccessMessage('');
            setEmail('');
            setPassword('');
            setConfirmPassword('');
          }}
          disabled={isLoading}
        >
          {isLogin ? 'Need an account? Sign up' : 'Already have an account? Login'}
        </button>
      </form>
    </div>
  );
};

export default Auth; 
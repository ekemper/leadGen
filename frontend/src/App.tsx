import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import Auth from './components/Auth';
import Dashboard from './components/Dashboard';
import { api } from './config/api';
import './App.css';

const App: React.FC = () => {
  const [health, setHealth] = useState<{status: string} | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [token, setToken] = useState<string | null>(localStorage.getItem('token'));

  const handleAuthSuccess = (newToken: string) => {
    setToken(newToken);
    localStorage.setItem('token', newToken);
  };

  useEffect(() => {
    const checkHealth = async () => {
      try {
        const data = await api.get('/api/health');
        setHealth(data);
        setError(null);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'API Error');
        setHealth(null);
      }
    };

    // Initial check
    checkHealth();

    // Set up periodic health checks every 30 seconds
    const interval = setInterval(checkHealth, 30000);

    return () => clearInterval(interval);
  }, []);

  return (
    <Router>
      <div className="App">
        <Routes>
          <Route 
            path="/auth" 
            element={
              token ? (
                <Navigate to="/dashboard" replace />
              ) : (
                <Auth onAuthSuccess={handleAuthSuccess} />
              )
            } 
          />
          <Route 
            path="/dashboard" 
            element={
              token ? (
                <Dashboard />
              ) : (
                <Navigate to="/auth" replace />
              )
            } 
          />
          <Route 
            path="/" 
            element={
              token ? (
                <Navigate to="/dashboard" replace />
              ) : (
                <Navigate to="/auth" replace />
              )
            } 
          />
          {/* Add more routes as needed */}
        </Routes>

        {/* Health status indicator */}
        <div className="health-status">
          <div 
            className={`status-indicator ${
              error ? 'error' : health ? 'healthy' : 'loading'
            }`}
          />
          <span className="health-status-text">
            {error ? 'API Error' : health ? 'API Healthy' : 'Checking API...'}
          </span>
        </div>
      </div>
    </Router>
  );
};

export default App;

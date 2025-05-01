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
    api.get('/api/health')
      .then(data => setHealth(data))
      .catch(err => setError(err.message));
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

        {/* Health status section */}
        <div className="health-status">
          <h1>API Health Status</h1>
          {error ? (
            <div className="error">Error: {error}</div>
          ) : health ? (
            <div className="status">Status: {health.status}</div>
          ) : (
            <div>Loading...</div>
          )}
        </div>
      </div>
    </Router>
  );
};

export default App;

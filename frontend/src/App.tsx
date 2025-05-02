import React from 'react';
import { BrowserRouter as Router, Routes, Route, useNavigate } from 'react-router-dom';
import Sidebar from './components/Sidebar';
import Dashboard from './components/Dashboard';
import Campaigns from './components/Campaigns';
import Auth from './components/Auth';

const AuthWithRedirect: React.FC = () => {
  const navigate = useNavigate();
  const handleAuthSuccess = (token: string) => {
    console.log('Saving token to localStorage:', token);
    localStorage.setItem('token', token);
    navigate('/dashboard');
  };
  return <Auth onAuthSuccess={handleAuthSuccess} />;
};

const App: React.FC = () => {
  return (
    <Router>
      <div style={{ minHeight: '100vh', backgroundColor: '#1e1e1e' }}>
        <Sidebar />
        <main style={{ marginLeft: '250px', padding: '2rem' }}>
          <Routes>
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/campaigns" element={<Campaigns />} />
            <Route path="/login" element={<AuthWithRedirect />} />
            <Route path="/" element={<Dashboard />} />
          </Routes>
        </main>
      </div>
    </Router>
  );
};

export default App;

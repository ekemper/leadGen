import React, { useState } from 'react';
import { api } from '../config/api';
import { ToastContainer, toast } from 'react-toastify';
import 'react-toastify/dist/ReactToastify.css';
import { useNavigate } from 'react-router-dom';

const Campaigns: React.FC = () => {
  const [formData, setFormData] = useState({
    count: 10,
    fileName: "",
    totalRecords: 0,
    url: ""
  });
  const [isLoading, setIsLoading] = useState(false);
  const navigate = useNavigate();

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    const { name, value, type } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: type === 'checkbox' && e.target instanceof HTMLInputElement ? e.target.checked : value
    }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);

    try {
      const response = await api.post('/api/campaigns', formData);
      if (response.status === 'success') {
        toast.success(response.message || 'Campaign started successfully!');
      } else {
        toast.error(response.message || 'Failed to start campaign.');
        if (response.message && response.message.toLowerCase().includes('token is missing')) {
          setTimeout(() => navigate('/login'), 1500);
        }
      }
    } catch (error: any) {
      toast.error(error?.message || 'Failed to start campaign.');
      if (error?.message && error.message.toLowerCase().includes('token is missing')) {
        setTimeout(() => navigate('/login'), 1500);
      }
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div style={{ 
      marginLeft: '250px', // Account for sidebar width
      padding: '2rem',
      color: '#d4d4d4'
    }}>
      <ToastContainer position="top-right" autoClose={4000} hideProgressBar={false} newestOnTop closeOnClick pauseOnFocusLoss draggable pauseOnHover />
      <h1 style={{ fontSize: '1.5rem', marginBottom: '2rem' }}>Campaigns</h1>
      
      <form onSubmit={handleSubmit} style={{
        maxWidth: '600px',
        backgroundColor: '#2d2d2d',
        padding: '2rem',
        borderRadius: '8px'
      }}>
        <div style={{ marginBottom: '1.5rem' }}>
          <label style={{ display: 'block', marginBottom: '0.5rem' }}>
            File Name
          </label>
          <input
            type="text"
            name="fileName"
            value={formData.fileName}
            onChange={handleChange}
            required
            style={{
              width: '100%',
              padding: '0.5rem',
              backgroundColor: '#1e1e1e',
              border: '1px solid #333',
              borderRadius: '4px',
              color: '#d4d4d4'
            }}
          />
        </div>

        <div style={{ marginBottom: '1.5rem' }}>
          <label style={{ display: 'block', marginBottom: '0.5rem' }}>
            Total Records
          </label>
          <input
            type="number"
            name="totalRecords"
            value={formData.totalRecords}
            onChange={handleChange}
            min="1"
            required
            style={{
              width: '100%',
              padding: '0.5rem',
              backgroundColor: '#1e1e1e',
              border: '1px solid #333',
              borderRadius: '4px',
              color: '#d4d4d4'
            }}
          />
        </div>

        <div style={{ marginBottom: '1.5rem' }}>
          <label style={{ display: 'block', marginBottom: '0.5rem' }}>
            URL
          </label>
          <textarea
            name="url"
            value={formData.url}
            onChange={handleChange}
            required
            rows={3}
            style={{
              width: '100%',
              padding: '0.5rem',
              backgroundColor: '#1e1e1e',
              border: '1px solid #333',
              borderRadius: '4px',
              color: '#d4d4d4',
              resize: 'vertical'
            }}
          />
        </div>

        <button
          type="submit"
          disabled={isLoading}
          style={{
            padding: '0.75rem 1.5rem',
            backgroundColor: '#0d6efd',
            color: 'white',
            border: 'none',
            borderRadius: '4px',
            cursor: 'pointer',
            opacity: isLoading ? 0.7 : 1
          }}
        >
          {isLoading ? 'Starting...' : 'Start Campaign'}
        </button>
      </form>
    </div>
  );
};

export default Campaigns; 
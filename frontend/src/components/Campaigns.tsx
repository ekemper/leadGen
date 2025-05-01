import React, { useState } from 'react';
import { api } from '../config/api';

const Campaigns: React.FC = () => {
  const [formData, setFormData] = useState({
    count: 10,
    excludeGuessedEmails: true,
    excludeNoEmails: false,
    getEmails: true,
    searchUrl: "https://app.apollo.io/#/people?page=1&personLocations%5B%5D=United%20States&contactEmailStatusV2%5B%5D=verified&personSeniorities%5B%5D=owner&personSeniorities%5B%5D=founder&personSeniorities%5B%5D=c_suite&includedOrganizationKeywordFields%5B%5D=tags&includedOrganizationKeywordFields%5B%5D=name&personDepartmentOrSubdepartments%5B%5D=master_operations&personDepartmentOrSubdepartments%5B%5D=master_sales&sortAscending=false&sortByField=recommendations_score&contactEmailExcludeCatchAll=true&qOrganizationKeywordTags%5B%5D=SEO&qOrganizationKeywordTags%5B%5D=Digital%20Marketing&qOrganizationKeywordTags%5B%5D=Marketing"
  });
  const [isLoading, setIsLoading] = useState(false);
  const [message, setMessage] = useState('');

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value, type, checked } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value
    }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setMessage('');

    try {
      const response = await api.post('/api/fetch_apollo_leads', formData);
      setMessage(`Success! ${response.message}`);
    } catch (error) {
      setMessage(`Error: ${error instanceof Error ? error.message : 'Failed to fetch leads'}`);
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
      <h1 style={{ fontSize: '1.5rem', marginBottom: '2rem' }}>Campaigns</h1>
      
      <form onSubmit={handleSubmit} style={{
        maxWidth: '600px',
        backgroundColor: '#2d2d2d',
        padding: '2rem',
        borderRadius: '8px'
      }}>
        <div style={{ marginBottom: '1.5rem' }}>
          <label style={{ display: 'block', marginBottom: '0.5rem' }}>
            Search URL
          </label>
          <input
            type="text"
            name="searchUrl"
            value={formData.searchUrl}
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
            Number of Leads
          </label>
          <input
            type="number"
            name="count"
            value={formData.count}
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
          <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <input
              type="checkbox"
              name="excludeGuessedEmails"
              checked={formData.excludeGuessedEmails}
              onChange={handleChange}
            />
            Exclude Guessed Emails
          </label>
        </div>

        <div style={{ marginBottom: '1.5rem' }}>
          <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <input
              type="checkbox"
              name="excludeNoEmails"
              checked={formData.excludeNoEmails}
              onChange={handleChange}
            />
            Exclude Leads Without Emails
          </label>
        </div>

        <div style={{ marginBottom: '1.5rem' }}>
          <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <input
              type="checkbox"
              name="getEmails"
              checked={formData.getEmails}
              onChange={handleChange}
            />
            Fetch Emails
          </label>
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
          {isLoading ? 'Fetching...' : 'Fetch Leads'}
        </button>

        {message && (
          <div style={{ 
            marginTop: '1rem',
            padding: '0.75rem',
            backgroundColor: message.includes('Error') ? '#dc3545' : '#198754',
            borderRadius: '4px'
          }}>
            {message}
          </div>
        )}
      </form>
    </div>
  );
};

export default Campaigns; 
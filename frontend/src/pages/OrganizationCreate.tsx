import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';

const OrganizationCreate: React.FC = () => {
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const token = localStorage.getItem('token');
      const res = await fetch('/api/organizations', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ name, description }),
      });
      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.message || 'Failed to create organization');
      }
      const data = await res.json();
      navigate(`/organizations/${data.data.id}`);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-6 max-w-xl mx-auto">
      <h1 className="text-2xl font-bold mb-4">Create Organization</h1>
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-gray-700 font-medium mb-1">Name</label>
          <input
            className="border rounded px-2 py-1 w-full"
            value={name}
            onChange={e => setName(e.target.value)}
            required
            disabled={loading}
          />
        </div>
        <div>
          <label className="block text-gray-700 font-medium mb-1">Description</label>
          <textarea
            className="border rounded px-2 py-1 w-full"
            value={description}
            onChange={e => setDescription(e.target.value)}
            rows={3}
            disabled={loading}
          />
        </div>
        {error && <div className="text-red-500">{error}</div>}
        <button
          type="submit"
          className="btn btn-primary"
          disabled={loading}
        >
          {loading ? 'Creating...' : 'Create Organization'}
        </button>
      </form>
    </div>
  );
};

export default OrganizationCreate; 
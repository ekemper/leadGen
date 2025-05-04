import React, { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { api } from '../config/api';

interface Organization {
  id: string;
  name: string;
  description: string;
  created_at: string;
  updated_at: string;
}

const OrganizationsList: React.FC = () => {
  const [orgs, setOrgs] = useState<Organization[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [createName, setCreateName] = useState('');
  const [createDescription, setCreateDescription] = useState('');
  const [createError, setCreateError] = useState<string | null>(null);
  const [createLoading, setCreateLoading] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    fetchOrgs();
    // eslint-disable-next-line
  }, []);

  const fetchOrgs = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.get('/api/organizations');
      setOrgs(data.data);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    setCreateError(null);
    setCreateLoading(true);
    try {
      const data = await api.post('/api/organizations', {
        name: createName,
        description: createDescription,
      });
      setCreateName('');
      setCreateDescription('');
      navigate(`/organizations/${data.data.id}`);
    } catch (err: any) {
      setCreateError(err.message);
    } finally {
      setCreateLoading(false);
    }
  };

  return (
    <div className="p-6 max-w-2xl mx-auto">
      <h1 className="text-2xl font-bold mb-4">Organizations</h1>
      <form onSubmit={handleCreate} className="space-y-4 mb-8">
        <div>
          <label className="block text-gray-700 font-medium mb-1">Name</label>
          <input
            className="border rounded px-2 py-1 w-full"
            value={createName}
            onChange={e => setCreateName(e.target.value)}
            required
            disabled={createLoading}
          />
        </div>
        <div>
          <label className="block text-gray-700 font-medium mb-1">Description</label>
          <textarea
            className="border rounded px-2 py-1 w-full"
            value={createDescription}
            onChange={e => setCreateDescription(e.target.value)}
            rows={3}
            disabled={createLoading}
          />
        </div>
        {createError && <div className="text-red-500">{createError}</div>}
        <button
          type="submit"
          className="btn btn-primary"
          disabled={createLoading}
        >
          {createLoading ? 'Creating...' : 'Create Organization'}
        </button>
      </form>
      {loading ? (
        <div>Loading organizations...</div>
      ) : error ? (
        <div className="text-red-500">{error}</div>
      ) : orgs.length === 0 ? (
        <div className="text-gray-500 text-center">There are no orgs yet - please create one!</div>
      ) : (
        <ul className="divide-y divide-gray-200">
          {orgs.map((org) => (
            <li key={org.id} className="py-4 flex items-center justify-between">
              <div>
                <Link to={`/organizations/${org.id}`} className="text-lg font-medium text-blue-600 hover:underline">
                  {org.name}
                </Link>
                <div className="text-gray-500 text-sm">{org.description}</div>
              </div>
              <Link to={`/organizations/${org.id}`} className="text-blue-500 hover:underline text-sm">View</Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
};

export default OrganizationsList; 
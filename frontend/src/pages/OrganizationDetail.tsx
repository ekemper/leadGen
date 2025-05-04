import React, { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';

interface Organization {
  id: string;
  name: string;
  description: string;
  created_at: string;
  updated_at: string;
}

const OrganizationDetail: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const [org, setOrg] = useState<Organization | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [editField, setEditField] = useState<null | 'name' | 'description'>(null);
  const [editValue, setEditValue] = useState('');
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    const fetchOrg = async () => {
      setLoading(true);
      setError(null);
      try {
        const token = localStorage.getItem('token');
        const res = await fetch(`/api/organizations/${id}`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (!res.ok) throw new Error('Failed to fetch organization');
        const data = await res.json();
        setOrg(data.data);
      } catch (err: any) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };
    fetchOrg();
  }, [id]);

  const startEdit = (field: 'name' | 'description') => {
    setEditField(field);
    setEditValue(org ? org[field] : '');
  };

  const cancelEdit = () => {
    setEditField(null);
    setEditValue('');
  };

  const saveEdit = async () => {
    if (!org || !editField) return;
    setSaving(true);
    setError(null);
    try {
      const token = localStorage.getItem('token');
      const res = await fetch(`/api/organizations/${org.id}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ [editField]: editValue }),
      });
      if (!res.ok) throw new Error('Failed to update organization');
      const data = await res.json();
      setOrg(data.data);
      setEditField(null);
      setEditValue('');
    } catch (err: any) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      saveEdit();
    } else if (e.key === 'Escape') {
      cancelEdit();
    }
  };

  if (loading) return <div>Loading organization...</div>;
  if (error) return <div className="text-red-500">{error}</div>;
  if (!org) return <div>Organization not found.</div>;

  return (
    <div className="p-6 max-w-xl mx-auto">
      <h1 className="text-2xl font-bold mb-4">Organization Detail</h1>
      <div className="mb-4">
        <label className="block text-gray-700 font-medium">Name:</label>
        {editField === 'name' ? (
          <div className="flex gap-2 items-center">
            <input
              className="border rounded px-2 py-1 flex-1"
              value={editValue}
              onChange={e => setEditValue(e.target.value)}
              onKeyDown={handleKeyDown}
              autoFocus
              disabled={saving}
            />
            <button className="btn btn-primary" onClick={saveEdit} disabled={saving}>Save</button>
            <button className="btn btn-secondary" onClick={cancelEdit} disabled={saving}>Cancel</button>
          </div>
        ) : (
          <span className="inline-block cursor-pointer hover:underline" onClick={() => startEdit('name')}>
            {org.name || <span className="text-gray-400">(No name)</span>}
          </span>
        )}
      </div>
      <div className="mb-4">
        <label className="block text-gray-700 font-medium">Description:</label>
        {editField === 'description' ? (
          <div className="flex gap-2 items-center">
            <textarea
              className="border rounded px-2 py-1 flex-1"
              value={editValue}
              onChange={e => setEditValue(e.target.value)}
              onKeyDown={handleKeyDown}
              autoFocus
              disabled={saving}
              rows={2}
            />
            <button className="btn btn-primary" onClick={saveEdit} disabled={saving}>Save</button>
            <button className="btn btn-secondary" onClick={cancelEdit} disabled={saving}>Cancel</button>
          </div>
        ) : (
          <span className="inline-block cursor-pointer hover:underline" onClick={() => startEdit('description')}>
            {org.description || <span className="text-gray-400">(No description)</span>}
          </span>
        )}
      </div>
      <div className="mb-2 text-sm text-gray-500">ID: {org.id}</div>
      <div className="mb-2 text-sm text-gray-500">Created: {new Date(org.created_at).toLocaleString()}</div>
      <div className="mb-2 text-sm text-gray-500">Updated: {new Date(org.updated_at).toLocaleString()}</div>
    </div>
  );
};

export default OrganizationDetail; 
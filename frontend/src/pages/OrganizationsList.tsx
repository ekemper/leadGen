import React, { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { api } from '../config/api';
import Input from '../components/form/input/InputField';
import TextArea from '../components/form/input/TextArea';
import Label from '../components/form/Label';
import Button from '../components/ui/button/Button';

interface Organization {
  id: string;
  name: string;
  description: string;
  created_at: string;
  updated_at: string;
}

interface FormErrors {
  name?: string;
  description?: string;
}

const OrganizationsList: React.FC = () => {
  const [orgs, setOrgs] = useState<Organization[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [createName, setCreateName] = useState('');
  const [createDescription, setCreateDescription] = useState('');
  const [createError, setCreateError] = useState<string | null>(null);
  const [createLoading, setCreateLoading] = useState(false);
  const [formErrors, setFormErrors] = useState<FormErrors>({});
  const [showCreateForm, setShowCreateForm] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    fetchOrgs();
    // eslint-disable-next-line
  }, []);

  const validateForm = (): boolean => {
    const errors: FormErrors = {};
    
    if (!createName.trim()) {
      errors.name = 'Name is required';
    } else if (createName.trim().length < 3) {
      errors.name = 'Name must be at least 3 characters';
    }
    
    if (!createDescription.trim()) {
      errors.description = 'Description is required';
    }

    setFormErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const fetchOrgs = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.get('/api/organizations');
      setOrgs(data.data);
      // Show create form if no orgs exist
      setShowCreateForm(data.data.length === 0);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!validateForm()) {
      return;
    }

    setCreateError(null);
    setCreateLoading(true);
    try {
      const data = await api.post('/api/organizations', {
        name: createName,
        description: createDescription,
      });
      setCreateName('');
      setCreateDescription('');
      setFormErrors({});
      setShowCreateForm(false);
      await fetchOrgs(); // Refresh the list
    } catch (err: any) {
      setCreateError(err.message);
    } finally {
      setCreateLoading(false);
    }
  };

  const renderCreateForm = () => (
    <form onSubmit={handleCreate} className="space-y-4 mb-8">
      <div>
        <Label htmlFor="name">Name</Label>
        <Input
          id="name"
          type="text"
          value={createName}
          onChange={(e) => setCreateName(e.target.value)}
          disabled={createLoading}
          error={!!formErrors.name}
          hint={formErrors.name}
        />
      </div>
      <div>
        <Label htmlFor="description">Description</Label>
        <TextArea
          value={createDescription}
          onChange={(value) => setCreateDescription(value)}
          rows={3}
          disabled={createLoading}
          error={!!formErrors.description}
          hint={formErrors.description}
        />
      </div>
      {createError && <div className="text-red-500">{createError}</div>}
      <Button
        variant="primary"
        disabled={createLoading || !createName.trim() || !createDescription.trim()}
      >
        {createLoading ? 'Creating...' : 'Create Organization'}
      </Button>
    </form>
  );

  return (
    <div className="p-6 max-w-2xl mx-auto">
      <div className="flex justify-between items-center mb-4">
        <h1 className="text-2xl font-bold text-white">Organizations</h1>
        {orgs.length > 0 && (
          <Button
            variant="primary"
            onClick={() => setShowCreateForm(!showCreateForm)}
          >
            {showCreateForm ? 'Cancel' : 'Create Organization'}
          </Button>
        )}
      </div>

      {loading ? (
        <div className="text-gray-400">Loading organizations...</div>
      ) : error ? (
        <div className="text-red-500">{error}</div>
      ) : (
        <>
          {orgs.length === 0 ? (
            <div className="text-center">
              <h2 className="text-xl text-gray-400 mb-8">There are no orgs yet - please create one!</h2>
              {renderCreateForm()}
            </div>
          ) : (
            <>
              {showCreateForm && renderCreateForm()}
              <ul className="divide-y divide-gray-700">
                {orgs.map((org) => (
                  <li key={org.id} className="py-4 flex items-center justify-between">
                    <div>
                      <Link to={`/organizations/${org.id}`} className="text-lg font-medium text-blue-400 hover:text-blue-300 hover:underline">
                        {org.name}
                      </Link>
                      <div className="text-gray-400 text-sm">{org.description}</div>
                    </div>
                    <Link to={`/organizations/${org.id}`} className="text-blue-400 hover:text-blue-300 hover:underline text-sm">View</Link>
                  </li>
                ))}
              </ul>
            </>
          )}
        </>
      )}
    </div>
  );
};

export default OrganizationsList;
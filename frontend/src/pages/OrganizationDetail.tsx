import React, { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { api } from '../config/api';
import PageBreadcrumb from '../components/common/PageBreadCrumb';
import ComponentCard from '../components/common/ComponentCard';
import PageMeta from '../components/common/PageMeta';
import Button from '../components/ui/button/Button';
import Input from '../components/form/input/InputField';
import TextArea from '../components/form/input/TextArea';
import Label from '../components/form/Label';

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

const OrganizationDetail: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const [org, setOrg] = useState<Organization | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [editField, setEditField] = useState<null | 'name' | 'description'>(null);
  const [editValue, setEditValue] = useState('');
  const [saving, setSaving] = useState(false);
  const [formErrors, setFormErrors] = useState<FormErrors>({});

  useEffect(() => {
    const fetchOrg = async () => {
      setLoading(true);
      setError(null);
      try {
        const data = await api.get(`/api/organizations/${id}`);
        setOrg(data.data);
      } catch (err: any) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };
    fetchOrg();
  }, [id]);

  const validateField = (field: 'name' | 'description', value: string): boolean => {
    const errors: FormErrors = {};
    
    if (!value || !value.trim()) {
      errors[field] = `${field.charAt(0).toUpperCase() + field.slice(1)} is required`;
    } else if (field === 'name' && value.trim().length < 3) {
      errors[field] = 'Name must be at least 3 characters long';
    }
    
    setFormErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const startEdit = (field: 'name' | 'description') => {
    setEditField(field);
    setEditValue(org ? org[field] : '');
    setFormErrors({});
  };

  const cancelEdit = () => {
    setEditField(null);
    setEditValue('');
    setFormErrors({});
  };

  const saveEdit = async () => {
    if (!org || !editField) return;
    
    if (!validateField(editField, editValue)) {
      return;
    }

    const trimmedValue = editValue.trim();
    if (!trimmedValue) {
      setFormErrors({ [editField]: `${editField.charAt(0).toUpperCase() + editField.slice(1)} is required` });
      return;
    }

    setSaving(true);
    setError(null);
    try {
      const response = await api.put(`/api/organizations/${org.id}`, { [editField]: trimmedValue });
      if (response.data) {
        setOrg(response.data);
        setEditField(null);
        setEditValue('');
        setFormErrors({});
      } else {
        setError('Failed to update organization');
      }
    } catch (err: any) {
      setError(err.message || 'Failed to update organization');
    } finally {
      setSaving(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      saveEdit();
    } else if (e.key === 'Escape') {
      cancelEdit();
    }
  };

  if (loading) return <div className="text-gray-400">Loading organization...</div>;
  if (error) return <div className="text-red-500">{error}</div>;
  if (!org) return <div className="text-gray-400">Organization not found.</div>;

  return (
    <>
      <PageMeta
        title="Organization Details | LeadGen"
        description="View and edit organization details"
      />
      <PageBreadcrumb pageTitle="Organization Details" />
      <div className="space-y-5 sm:space-y-6">
        <ComponentCard title="Organization Information">
          <div className="space-y-6">
            <div>
              <Label htmlFor="name">Name</Label>
              {editField === 'name' ? (
                <div 
                  className="flex gap-2 items-center mt-2"
                  onKeyDown={handleKeyDown}
                >
                  <Input
                    id="name"
                    value={editValue}
                    onChange={(e) => {
                      setEditValue(e.target.value);
                      if (formErrors.name) {
                        setFormErrors({});
                      }
                    }}
                    disabled={saving}
                    error={!!formErrors.name}
                    hint={formErrors.name}
                  />
                  <Button
                    variant="primary"
                    onClick={saveEdit}
                    disabled={saving || !editValue.trim()}
                  >
                    {saving ? 'Saving...' : 'Save'}
                  </Button>
                  <Button
                    variant="outline"
                    onClick={cancelEdit}
                    disabled={saving}
                  >
                    Cancel
                  </Button>
                </div>
              ) : (
                <div 
                  className="mt-2 text-lg font-medium text-gray-800 dark:text-white/90 cursor-pointer hover:text-blue-500 dark:hover:text-blue-400"
                  onClick={() => startEdit('name')}
                >
                  {org.name || <span className="text-gray-400">(No name)</span>}
                </div>
              )}
            </div>

            <div>
              <Label htmlFor="description">Description</Label>
              {editField === 'description' ? (
                <div 
                  className="flex gap-2 items-center mt-2"
                  onKeyDown={handleKeyDown}
                >
                  <TextArea
                    value={editValue}
                    onChange={(value) => {
                      setEditValue(value);
                      if (formErrors.description) {
                        setFormErrors({});
                      }
                    }}
                    disabled={saving}
                    rows={3}
                    error={!!formErrors.description}
                    hint={formErrors.description}
                  />
                  <Button
                    variant="primary"
                    onClick={saveEdit}
                    disabled={saving || !editValue.trim()}
                  >
                    {saving ? 'Saving...' : 'Save'}
                  </Button>
                  <Button
                    variant="outline"
                    onClick={cancelEdit}
                    disabled={saving}
                  >
                    Cancel
                  </Button>
                </div>
              ) : (
                <div 
                  className="mt-2 text-gray-600 dark:text-gray-400 cursor-pointer hover:text-blue-500 dark:hover:text-blue-400"
                  onClick={() => startEdit('description')}
                >
                  {org.description || <span className="text-gray-400">(No description)</span>}
                </div>
              )}
            </div>

            <div className="pt-4 border-t border-gray-200 dark:border-gray-800">
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                <div>
                  <div className="text-sm font-medium text-gray-500 dark:text-gray-400">ID</div>
                  <div className="mt-1 text-sm text-gray-800 dark:text-white/90">{org.id}</div>
                </div>
                <div>
                  <div className="text-sm font-medium text-gray-500 dark:text-gray-400">Created</div>
                  <div className="mt-1 text-sm text-gray-800 dark:text-white/90">
                    {new Date(org.created_at).toLocaleString()}
                  </div>
                </div>
                <div>
                  <div className="text-sm font-medium text-gray-500 dark:text-gray-400">Last Updated</div>
                  <div className="mt-1 text-sm text-gray-800 dark:text-white/90">
                    {new Date(org.updated_at).toLocaleString()}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </ComponentCard>
      </div>
    </>
  );
};

export default OrganizationDetail; 
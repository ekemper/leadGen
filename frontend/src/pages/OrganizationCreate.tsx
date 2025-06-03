import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { OrganizationService } from '../services/organizationService';
import { OrganizationCreate } from '../types/organization';
import { toast } from 'react-toastify';
import PageBreadcrumb from '../components/common/PageBreadCrumb';
import ComponentCard from '../components/common/ComponentCard';
import PageMeta from '../components/common/PageMeta';
import Button from '../components/ui/button/Button';
import Input from '../components/form/input/InputField';
import TextArea from '../components/form/input/TextArea';
import Label from '../components/form/Label';

interface FormErrors {
  name?: string;
  description?: string;
}

const OrganizationCreatePage: React.FC = () => {
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [formErrors, setFormErrors] = useState<FormErrors>({});
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const validateForm = (): boolean => {
    const errors: FormErrors = {};
    
    if (!name.trim()) {
      errors.name = 'Name is required';
    } else if (name.trim().length < 3) {
      errors.name = 'Name must be at least 3 characters';
    }
    
    if (!description.trim()) {
      errors.description = 'Description is required';
    }

    setFormErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!validateForm()) {
      return;
    }

    setError(null);
    setLoading(true);
    try {
      const createData: OrganizationCreate = {
        name: name.trim(),
        description: description.trim(),
      };
      
      const data = await OrganizationService.createOrganization(createData);
      toast.success('Organization created successfully!');
      navigate(`/organizations/${data.id}`);
    } catch (err: any) {
      setError(err.message);
      toast.error(`Failed to create organization: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <PageMeta
        title="Create Organization | LeadGen"
        description="Create a new organization"
      />
      <PageBreadcrumb 
        pageTitle="Create Organization"
        items={[
          { label: 'Organizations', path: '/organizations' },
          { label: 'Create Organization' }
        ]}
      />
      <div className="space-y-5 sm:space-y-6">
        <ComponentCard title="Organization Information">
          {error && <div className="text-red-500 mb-4">{error}</div>}
          <form onSubmit={handleSubmit} className="space-y-6">
            <div>
              <Label htmlFor="name">Name *</Label>
              <Input
                id="name"
                value={name}
                onChange={(e) => {
                  setName(e.target.value);
                  if (formErrors.name) {
                    setFormErrors(prev => ({ ...prev, name: undefined }));
                  }
                }}
                disabled={loading}
                error={!!formErrors.name}
                hint={formErrors.name}
                placeholder="Enter organization name"
              />
            </div>

            <div>
              <Label htmlFor="description">Description *</Label>
              <TextArea
                value={description}
                onChange={(value) => {
                  setDescription(value);
                  if (formErrors.description) {
                    setFormErrors(prev => ({ ...prev, description: undefined }));
                  }
                }}
                disabled={loading}
                error={!!formErrors.description}
                hint={formErrors.description}
                placeholder="Enter organization description"
                rows={4}
              />
            </div>

            <div className="flex gap-3">
              <Button
                variant="primary"
                disabled={loading || !name.trim() || !description.trim()}
                onClick={() => handleSubmit({} as React.FormEvent)}
              >
                {loading ? 'Creating...' : 'Create Organization'}
              </Button>
              <Button
                variant="outline"
                onClick={() => navigate('/organizations')}
                disabled={loading}
              >
                Cancel
              </Button>
            </div>
          </form>
        </ComponentCard>
      </div>
    </>
  );
};

export default OrganizationCreatePage; 
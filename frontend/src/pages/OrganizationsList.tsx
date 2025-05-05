import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../config/api';
import Input from '../components/form/input/InputField';
import TextArea from '../components/form/input/TextArea';
import Label from '../components/form/Label';
import Button from '../components/ui/button/Button';
import PageBreadcrumb from '../components/common/PageBreadCrumb';
import ComponentCard from '../components/common/ComponentCard';
import PageMeta from '../components/common/PageMeta';
import {
  Table,
  TableBody,
  TableCell,
  TableHeader,
  TableRow,
} from '../components/ui/table';

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

  useEffect(() => {
    fetchOrgs();
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
      await api.post('/api/organizations', {
        name: createName,
        description: createDescription,
      });
      setCreateName('');
      setCreateDescription('');
      setFormErrors({});
      setShowCreateForm(false);
      await fetchOrgs();
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
    <>
      <PageMeta
        title="Organizations | LeadGen"
        description="Manage your organizations"
      />
      <PageBreadcrumb pageTitle="Organizations" />
      <div className="space-y-5 sm:space-y-6">
        <ComponentCard title="Organizations">
          <div className="flex justify-between items-center mb-4">
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
                  <h2 className="text-xl text-gray-400 mb-8">There are no organizations yet - please create one!</h2>
                  {renderCreateForm()}
                </div>
              ) : (
                <>
                  {showCreateForm && renderCreateForm()}
                  <div className="overflow-hidden rounded-xl border border-gray-200 bg-white dark:border-white/[0.05] dark:bg-white/[0.03]">
                    <div className="max-w-full overflow-x-auto">
                      <Table>
                        <TableHeader className="border-b border-gray-100 dark:border-white/[0.05]">
                          <TableRow>
                            <TableCell
                              isHeader
                              className="px-5 py-3 font-medium text-gray-500 text-start text-theme-xs dark:text-gray-400"
                            >
                              Name
                            </TableCell>
                            <TableCell
                              isHeader
                              className="px-5 py-3 font-medium text-gray-500 text-start text-theme-xs dark:text-gray-400"
                            >
                              Description
                            </TableCell>
                            <TableCell
                              isHeader
                              className="px-5 py-3 font-medium text-gray-500 text-start text-theme-xs dark:text-gray-400"
                            >
                              Created
                            </TableCell>
                          </TableRow>
                        </TableHeader>
                        <TableBody className="divide-y divide-gray-100 dark:divide-white/[0.05]">
                          {orgs.map((org) => (
                            <TableRow key={org.id}>
                              <TableCell className="px-5 py-4 sm:px-6 text-start">
                                <Link to={`/organizations/${org.id}`} className="font-medium text-black dark:text-white hover:text-blue-500 dark:hover:text-blue-400">
                                  {org.name}
                                </Link>
                              </TableCell>
                              <TableCell className="px-4 py-3 text-gray-500 text-start text-theme-sm dark:text-gray-400">
                                {org.description ? (
                                  <div className="max-w-md whitespace-pre-wrap break-words">
                                    {org.description.length > 100 
                                      ? `${org.description.substring(0, 100)}...` 
                                      : org.description}
                                  </div>
                                ) : (
                                  <span className="text-gray-400">(No description)</span>
                                )}
                              </TableCell>
                              <TableCell className="px-4 py-3 text-gray-500 text-start text-theme-sm dark:text-gray-400">
                                {new Date(org.created_at).toLocaleDateString()}
                              </TableCell>
                            </TableRow>
                          ))}
                        </TableBody>
                      </Table>
                    </div>
                  </div>
                </>
              )}
            </>
          )}
        </ComponentCard>
      </div>
    </>
  );
};

export default OrganizationsList;
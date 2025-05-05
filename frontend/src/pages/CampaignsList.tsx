import React, { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { api } from '../config/api';
import PageBreadcrumb from '../components/common/PageBreadCrumb';
import ComponentCard from '../components/common/ComponentCard';
import PageMeta from '../components/common/PageMeta';
import Button from '../components/ui/button/Button';
import Input from '../components/form/input/InputField';
import Label from '../components/form/Label';
import Checkbox from '../components/form/Checkbox';
import Table from '../components/tables/Table';
import TableHeader from '../components/tables/TableHeader';
import TableBody from '../components/tables/TableBody';
import TableRow from '../components/tables/TableRow';
import TableCell from '../components/tables/TableCell';
import Badge from '../components/ui/badge/Badge';

interface Campaign {
  id: string;
  created_at: string;
  organization_id: string | null;
  status: string;
  name: string;
  description: string;
}

interface Organization {
  id: string;
  name: string;
  description: string;
  created_at: string;
  updated_at: string;
}

interface FormErrors {
  searchUrl?: string;
  count?: string;
  name?: string;
  description?: string;
  organization_id?: string;
}

const CampaignsList: React.FC = () => {
  const navigate = useNavigate();
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [organizations, setOrganizations] = useState<Organization[]>([]);
  const [loading, setLoading] = useState(true);
  const [orgsLoading, setOrgsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [orgsError, setOrgsError] = useState<string | null>(null);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [formData, setFormData] = useState({
    count: 10,
    excludeGuessedEmails: true,
    excludeNoEmails: false,
    getEmails: true,
    searchUrl: "https://app.apollo.io/#/people?page=1&personLocations%5B%5D=United%20States&contactEmailStatusV2%5B%5D=verified&personSeniorities%5B%5D=owner&personSeniorities%5B%5D=founder&personSeniorities%5B%5D=c_suite&includedOrganizationKeywordFields%5B%5D=tags&includedOrganizationKeywordFields%5B%5D=name&personDepartmentOrSubdepartments%5B%5D=master_operations&personDepartmentOrSubdepartments%5B%5D=master_sales&sortAscending=false&sortByField=recommendations_score&contactEmailExcludeCatchAll=true&qOrganizationKeywordTags%5B%5D=SEO&qOrganizationKeywordTags%5B%5D=Digital%20Marketing&qOrganizationKeywordTags%5B%5D=Marketing",
    name: '',
    description: '',
    organization_id: ''
  });
  const [formErrors, setFormErrors] = useState<FormErrors>({});
  const [createLoading, setCreateLoading] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);

  useEffect(() => {
    fetchCampaigns();
    fetchOrganizations();
  }, []);

  const fetchOrganizations = async () => {
    setOrgsLoading(true);
    setOrgsError(null);
    try {
      const response = await api.get('/api/organizations');
      console.log('Organizations API response:', response);
      if (response && response.data) {
        setOrganizations(response.data);
      } else {
        console.error('Unexpected API response structure:', response);
        setOrgsError('Failed to load organizations: Unexpected response format');
      }
    } catch (err: any) {
      console.error('Error fetching organizations:', err);
      setOrgsError(err.message || 'Failed to load organizations');
    } finally {
      setOrgsLoading(false);
    }
  };

  const validateForm = (): boolean => {
    const errors: FormErrors = {};
    
    if (!formData.searchUrl.trim()) {
      errors.searchUrl = 'Search URL is required';
    }
    
    if (!formData.count || formData.count < 1) {
      errors.count = 'Count must be at least 1';
    }

    if (!formData.name.trim()) {
      errors.name = 'Name is required';
    }
    
    if (!formData.description.trim()) {
      errors.description = 'Description is required';
    }

    if (!formData.organization_id) {
      errors.organization_id = 'Organization is required';
    }

    setFormErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const fetchCampaigns = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await api.get('/api/campaigns');
      setCampaigns(response.data);
      // Show create form if no campaigns exist
      setShowCreateForm(response.data.length === 0);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => {
    const { name, value, type } = e.target;
    const checked = 'checked' in e.target ? e.target.checked : undefined;
    setFormData(prev => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value
    }));
    // Clear error when user starts typing
    if (formErrors[name as keyof FormErrors]) {
      setFormErrors(prev => ({ ...prev, [name]: undefined }));
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
      const response = await api.post('/api/campaigns', formData);
      // Redirect to the campaign detail page
      navigate(`/campaigns/${response.data.id}`);
    } catch (err: any) {
      setCreateError(err.message);
    } finally {
      setCreateLoading(false);
    }
  };

  const renderCreateForm = () => (
    <form onSubmit={handleCreate} className="space-y-4 mb-8">
      <div>
        <Label htmlFor="organization_id">Organization</Label>
        {orgsLoading ? (
          <div className="text-gray-400">Loading organizations...</div>
        ) : orgsError ? (
          <div className="text-red-500">{orgsError}</div>
        ) : organizations.length === 0 ? (
          <div className="text-gray-400">No organizations available. Please create an organization first.</div>
        ) : (
          <select
            id="organization_id"
            name="organization_id"
            value={formData.organization_id}
            onChange={handleChange}
            disabled={createLoading}
            className={`w-full px-3 py-2 border rounded-md ${
              formErrors.organization_id ? 'border-red-500' : 'border-gray-300'
            } focus:outline-none focus:ring-2 focus:ring-blue-500`}
          >
            <option value="">Select an organization</option>
            {organizations.map((org) => (
              <option key={org.id} value={org.id}>
                {org.name}
              </option>
            ))}
          </select>
        )}
        {formErrors.organization_id && (
          <p className="mt-1 text-sm text-red-500">{formErrors.organization_id}</p>
        )}
      </div>
      <div>
        <Label htmlFor="name">Campaign Name</Label>
        <Input
          id="name"
          name="name"
          type="text"
          value={formData.name}
          onChange={handleChange}
          disabled={createLoading}
          error={!!formErrors.name}
          hint={formErrors.name}
        />
      </div>
      <div>
        <Label htmlFor="description">Description</Label>
        <textarea
          id="description"
          name="description"
          value={formData.description}
          onChange={handleChange}
          disabled={createLoading}
          className={`w-full px-3 py-2 border rounded-md ${
            formErrors.description ? 'border-red-500' : 'border-gray-300'
          } focus:outline-none focus:ring-2 focus:ring-blue-500`}
          rows={4}
        />
        {formErrors.description && (
          <p className="mt-1 text-sm text-red-500">{formErrors.description}</p>
        )}
      </div>
      {createError && <div className="text-red-500">{createError}</div>}
      <Button
        variant="primary"
        disabled={createLoading || !formData.name.trim() || !formData.description.trim() || !formData.organization_id}
      >
        {createLoading ? 'Creating...' : 'Create Campaign'}
      </Button>
    </form>
  );

  return (
    <>
      <PageMeta
        title="Campaigns | LeadGen"
        description="Manage your lead generation campaigns"
      />
      <PageBreadcrumb pageTitle="Campaigns" />
      <div className="space-y-5 sm:space-y-6">
        <ComponentCard title="Campaigns">
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-xl font-semibold text-gray-800 dark:text-white/90">Campaigns</h2>
            {campaigns.length > 0 && (
              <Button
                variant="primary"
                onClick={() => setShowCreateForm(!showCreateForm)}
              >
                {showCreateForm ? 'Cancel' : 'New Campaign'}
              </Button>
            )}
          </div>

          {loading ? (
            <div className="text-gray-400">Loading campaigns...</div>
          ) : error ? (
            <div className="text-red-500">{error}</div>
          ) : (
            <>
              {campaigns.length === 0 ? (
                <div className="text-center">
                  <h2 className="text-xl text-gray-400 mb-8">There are no campaigns yet - create your first one!</h2>
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
                              Status
                            </TableCell>
                            <TableCell
                              isHeader
                              className="px-5 py-3 font-medium text-gray-500 text-start text-theme-xs dark:text-gray-400"
                            >
                              Created
                            </TableCell>
                            <TableCell
                              isHeader
                              className="px-5 py-3 font-medium text-gray-500 text-start text-theme-xs dark:text-gray-400"
                            >
                              Actions
                            </TableCell>
                          </TableRow>
                        </TableHeader>
                        <TableBody className="divide-y divide-gray-100 dark:divide-white/[0.05]">
                          {campaigns.map((campaign) => (
                            <TableRow key={campaign.id}>
                              <TableCell className="px-5 py-4 sm:px-6 text-start">
                                <Link
                                  to={`/campaigns/${campaign.id}`}
                                  className="text-blue-400 hover:text-blue-300 hover:underline"
                                >
                                  {campaign.name || `Campaign ${campaign.id}`}
                                </Link>
                              </TableCell>
                              <TableCell className="px-4 py-3 text-gray-500 text-start text-theme-sm dark:text-gray-400">
                                {campaign.description || '-'}
                              </TableCell>
                              <TableCell className="px-4 py-3 text-gray-500 text-start text-theme-sm dark:text-gray-400">
                                <Badge
                                  size="sm"
                                  color={
                                    campaign.status === "running"
                                      ? "success"
                                      : campaign.status === "pending"
                                      ? "warning"
                                      : "error"
                                  }
                                >
                                  {campaign.status || 'created'}
                                </Badge>
                              </TableCell>
                              <TableCell className="px-4 py-3 text-gray-500 text-start text-theme-sm dark:text-gray-400">
                                {new Date(campaign.created_at).toLocaleString()}
                              </TableCell>
                              <TableCell className="px-4 py-3 text-gray-500 text-start text-theme-sm dark:text-gray-400">
                                <Link
                                  to={`/campaigns/${campaign.id}`}
                                  className="text-blue-400 hover:text-blue-300 hover:underline"
                                >
                                  View
                                </Link>
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

export default CampaignsList; 
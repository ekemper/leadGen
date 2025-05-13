import React, { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { api } from '../config/api';
import PageBreadcrumb from '../components/common/PageBreadCrumb';
import ComponentCard from '../components/common/ComponentCard';
import PageMeta from '../components/common/PageMeta';
import Button from '../components/ui/button/Button';
import Input from '../components/form/input/InputField';
import Label from '../components/form/Label';
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
  status_message?: string;
  last_error?: string;
  job_status?: Record<string, any>;
  job_ids?: Record<string, string>;
}

interface Organization {
  id: string;
  name: string;
  description: string;
  created_at: string;
  updated_at: string;
}

interface FormErrors {
  fileName?: string;
  count?: string;
  name?: string;
  description?: string;
  organization_id?: string;
}

const getStatusColor = (status: string) => {
  switch (status) {
    case 'completed':
      return 'success';
    case 'created':
      return 'info';
    case 'fetching_leads':
    case 'enriching':
    case 'verifying_emails':
    case 'generating_emails':
      return 'warning';
    case 'failed':
      return 'error';
    default:
      return 'info';
  }
};

const getStatusLabel = (status: string) => {
  switch (status) {
    case 'created':
      return 'Created';
    case 'fetching_leads':
      return 'Fetching Leads';
    case 'leads_fetched':
      return 'Leads Fetched';
    case 'enriching':
      return 'Enriching Leads';
    case 'enriched':
      return 'Leads Enriched';
    case 'verifying_emails':
      return 'Verifying Emails';
    case 'emails_verified':
      return 'Emails Verified';
    case 'generating_emails':
      return 'Generating Emails';
    case 'completed':
      return 'Completed';
    case 'failed':
      return 'Failed';
    default:
      return status;
  }
};

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
    name: '',
    description: '',
    organization_id: '',
    fileName: 'motorcycle_dealers',
    totalRecords: 500,
    url: 'https://app.apollo.io/#/people?contactEmailStatusV2%5B%5D=verified&contactEmailExcludeCatchAll=true&personTitles%5B%5D=CEO&personTitles%5B%5D=Founder&personTitles%5B%5D=sales%20manager&personTitles%5B%5D=chief%20sales%20officer&personLocations%5B%5D=United%20States&sortAscending=false&sortByField=recommendations_score&page=1&qOrganizationKeywordTags%5B%5D=motorcycle%20dealership&qOrganizationKeywordTags%5B%5D=harley%20davidson&qOrganizationKeywordTags%5B%5D=motorcycle&qOrganizationKeywordTags%5B%5D=carsports&includedOrganizationKeywordFields%5B%5D=tags&includedOrganizationKeywordFields%5B%5D=name&personNotTitles%5B%5D=assistant%20sales%20manager',
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
      if (response && response.data && Array.isArray(response.data.organizations)) {
        setOrganizations(response.data.organizations);
      } else {
        console.error('Unexpected API response structure:', response);
        setOrganizations([]);
        setOrgsError('Failed to load organizations: Unexpected response format');
      }
    } catch (err: any) {
      console.error('Error fetching organizations:', err);
      setOrgsError(err.message || 'Failed to load organizations');
      setOrganizations([]);
    } finally {
      setOrgsLoading(false);
    }
  };

  const validateForm = (): boolean => {
    const errors: FormErrors = {};
    if (!formData.fileName.trim()) {
      errors.fileName = 'File Name is required';
    }
    if (!formData.totalRecords || formData.totalRecords < 1) {
      errors.count = 'Total Records must be at least 1';
    }
    if (formData.totalRecords > 1000) {
      errors.count = 'Total Records cannot exceed 1000';
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
      if (response && response.status === 'success' && response.data && Array.isArray(response.data.campaigns)) {
        setCampaigns(response.data.campaigns);
        setShowCreateForm(response.data.campaigns.length === 0);
      } else {
        setCampaigns([]);
        setShowCreateForm(true);
        setError(response?.error?.message || 'Failed to load campaigns');
      }
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
      <div>
        <Label htmlFor="fileName">File Name</Label>
        <Input
          id="fileName"
          name="fileName"
          type="text"
          value={formData.fileName}
          onChange={handleChange}
          disabled={createLoading}
          error={!!formErrors.fileName}
          hint={formErrors.fileName}
        />
      </div>
      <div>
        <Label htmlFor="totalRecords">Number of Leads</Label>
        <Input
          id="totalRecords"
          name="totalRecords"
          type="number"
          value={formData.totalRecords}
          onChange={handleChange}
          min="1"
          max="1000"
          disabled={createLoading}
          error={!!formErrors.count}
          hint={formErrors.count}
        />
      </div>
      {createError && <div className="text-red-500">{createError}</div>}
      <Button
        variant="primary"
        disabled={createLoading || !formData.name.trim() || !formData.description.trim() || !formData.organization_id || !formData.fileName.trim() || !formData.totalRecords}
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
                                  color={getStatusColor(campaign.status)}
                                >
                                  {getStatusLabel(campaign.status)}
                                </Badge>
                                {campaign.status_message && (
                                  <div className="text-xs text-gray-400 mt-1">
                                    {campaign.status_message}
                                  </div>
                                )}
                                {campaign.last_error && (
                                  <div className="text-xs text-red-400 mt-1">
                                    {campaign.last_error}
                                  </div>
                                )}
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
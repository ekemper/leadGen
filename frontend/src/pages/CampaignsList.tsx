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

interface Campaign {
  id: string;
  created_at: string;
  organization_id: string | null;
  status: string;
}

interface FormErrors {
  searchUrl?: string;
  count?: string;
  name?: string;
  description?: string;
}

const CampaignsList: React.FC = () => {
  const navigate = useNavigate();
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [formData, setFormData] = useState({
    count: 10,
    excludeGuessedEmails: true,
    excludeNoEmails: false,
    getEmails: true,
    searchUrl: "https://app.apollo.io/#/people?page=1&personLocations%5B%5D=United%20States&contactEmailStatusV2%5B%5D=verified&personSeniorities%5B%5D=owner&personSeniorities%5B%5D=founder&personSeniorities%5B%5D=c_suite&includedOrganizationKeywordFields%5B%5D=tags&includedOrganizationKeywordFields%5B%5D=name&personDepartmentOrSubdepartments%5B%5D=master_operations&personDepartmentOrSubdepartments%5B%5D=master_sales&sortAscending=false&sortByField=recommendations_score&contactEmailExcludeCatchAll=true&qOrganizationKeywordTags%5B%5D=SEO&qOrganizationKeywordTags%5B%5D=Digital%20Marketing&qOrganizationKeywordTags%5B%5D=Marketing",
    name: '',
    description: ''
  });
  const [formErrors, setFormErrors] = useState<FormErrors>({});
  const [createLoading, setCreateLoading] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);

  useEffect(() => {
    fetchCampaigns();
  }, []);

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

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    const { name, value, type, checked } = e.target;
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
        disabled={createLoading || !formData.name.trim() || !formData.description.trim()}
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
                  <ul className="divide-y divide-gray-700">
                    {campaigns.map((campaign) => (
                      <li key={campaign.id} className="py-4 flex items-center justify-between">
                        <div>
                          <div className="text-lg font-medium text-blue-400">
                            {campaign.name || `Campaign ${campaign.id}`}
                          </div>
                          <div className="text-gray-400 text-sm">
                            Created: {new Date(campaign.created_at).toLocaleString()}
                          </div>
                          <div className="text-gray-400 text-sm">
                            Status: {campaign.status || 'created'}
                          </div>
                        </div>
                        <Link to={`/campaigns/${campaign.id}`} className="text-blue-400 hover:text-blue-300 hover:underline text-sm">View</Link>
                      </li>
                    ))}
                  </ul>
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
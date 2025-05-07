import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { api } from '../config/api';
import { toast } from 'react-toastify';
import { CampaignStatus } from '../types/campaign';
import PageBreadcrumb from '../components/common/PageBreadCrumb';
import ComponentCard from '../components/common/ComponentCard';
import PageMeta from '../components/common/PageMeta';
import Button from '../components/ui/button/Button';
import Input from '../components/form/input/InputField';
import Label from '../components/form/Label';
import Checkbox from '../components/form/Checkbox';

interface Campaign {
  id: string;
  name: string;
  description: string;
  created_at: string;
  status: string;
  organization_id: string | null;
}

interface FormErrors {
  searchUrl?: string;
  count?: string;
}

interface CampaignStartParams {
  count: number;
  excludeGuessedEmails: boolean;
  excludeNoEmails: boolean;
  getEmails: boolean;
  searchUrl: string;
}

const CampaignDetail: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [campaign, setCampaign] = useState<Campaign | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showStartForm, setShowStartForm] = useState(false);
  const [formData, setFormData] = useState({
    count: 10,
    excludeGuessedEmails: true,
    excludeNoEmails: false,
    getEmails: true,
    searchUrl: "https://app.apollo.io/#/people?page=1&personLocations%5B%5D=United%20States&contactEmailStatusV2%5B%5D=verified&personSeniorities%5B%5D=owner&personSeniorities%5B%5D=founder&personSeniorities%5B%5D=c_suite&includedOrganizationKeywordFields%5B%5D=tags&includedOrganizationKeywordFields%5B%5D=name&personDepartmentOrSubdepartments%5B%5D=master_operations&personDepartmentOrSubdepartments%5B%5D=master_sales&sortAscending=false&sortByField=recommendations_score&contactEmailExcludeCatchAll=true&qOrganizationKeywordTags%5B%5D=SEO&qOrganizationKeywordTags%5B%5D=Digital%20Marketing&qOrganizationKeywordTags%5B%5D=Marketing"
  });
  const [formErrors, setFormErrors] = useState<FormErrors>({});
  const [startLoading, setStartLoading] = useState(false);
  const [startError, setStartError] = useState<string | null>(null);
  const [starting, setStarting] = useState(false);
  const [statusPolling, setStatusPolling] = useState<NodeJS.Timeout | null>(null);

  useEffect(() => {
    fetchCampaign();
    return () => {
      if (statusPolling) {
        clearInterval(statusPolling);
      }
    };
  }, [id]);

  const validateForm = (): boolean => {
    const errors: FormErrors = {};
    
    if (!formData.searchUrl.trim()) {
      errors.searchUrl = 'Search URL is required';
    }
    
    if (!formData.count || formData.count < 1) {
      errors.count = 'Count must be at least 1';
    }

    setFormErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const fetchCampaign = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await api.get(`/api/campaigns/${id}`);
      if (response.status === 'error') {
        toast.error(response.message);
        return;
      }
      setCampaign(response.data);
      
      // Start polling if campaign is in progress
      if (response.data.status === CampaignStatus.FETCHING_LEADS || 
          response.data.status === CampaignStatus.VERIFYING_EMAILS ||
          response.data.status === CampaignStatus.ENRICHING_LEADS ||
          response.data.status === CampaignStatus.GENERATING_EMAILS) {
        startStatusPolling();
      }
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const startStatusPolling = () => {
    if (statusPolling) {
      clearInterval(statusPolling);
    }
    
    const interval = setInterval(async () => {
      try {
        const response = await api.get(`/api/campaigns/${id}`);
        if (response.status === 'error') {
          clearInterval(interval);
          return;
        }
        
        setCampaign(response.data);
        
        // Stop polling if campaign is completed or failed
        if (response.data.status === CampaignStatus.COMPLETED || 
            response.data.status === CampaignStatus.FAILED) {
          clearInterval(interval);
          setStatusPolling(null);
          
          // Show appropriate toast message
          if (response.data.status === CampaignStatus.COMPLETED) {
            toast.success('Campaign completed successfully');
          } else {
            toast.error(`Campaign failed: ${response.data.status_error || 'Unknown error'}`);
          }
        }
      } catch (error) {
        console.error('Error polling campaign status:', error);
        clearInterval(interval);
        setStatusPolling(null);
      }
    }, 5000); // Poll every 5 seconds
    
    setStatusPolling(interval);
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
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

  const handleStart = async (params: CampaignStartParams) => {
    try {
      setStarting(true);
      const response = await api.post(`/api/campaigns/${id}/start`, params);
      
      if (response.status === 'error') {
        toast.error(response.message);
        return;
      }
      
      toast.success('Campaign started successfully');
      setCampaign(response.data);
      startStatusPolling();
    } catch (error) {
      console.error('Campaign start error:', error);
      toast.error('Failed to start campaign');
    } finally {
      setStarting(false);
    }
  };

  const renderStartForm = () => (
    <form onSubmit={(e) => {
      e.preventDefault();
      const formData = new FormData(e.currentTarget);
      handleStart({
        count: parseInt(formData.get('count') as string),
        excludeGuessedEmails: formData.get('excludeGuessedEmails') === 'true',
        excludeNoEmails: formData.get('excludeNoEmails') === 'true',
        getEmails: formData.get('getEmails') === 'true',
        searchUrl: formData.get('searchUrl') as string
      });
    }} className="space-y-4 mb-8">
      <div>
        <Label htmlFor="searchUrl">Search URL</Label>
        <Input
          id="searchUrl"
          name="searchUrl"
          type="text"
          value={formData.searchUrl}
          onChange={handleChange}
          disabled={starting}
          error={!!formErrors.searchUrl}
          hint={formErrors.searchUrl}
        />
      </div>
      <div>
        <Label htmlFor="count">Number of Leads</Label>
        <Input
          id="count"
          name="count"
          type="number"
          value={formData.count}
          onChange={handleChange}
          min="1"
          max="100"
          disabled={starting}
          error={!!formErrors.count}
          hint={formErrors.count}
        />
      </div>
      <div className="space-y-2">
        <Checkbox
          id="excludeGuessedEmails"
          name="excludeGuessedEmails"
          checked={formData.excludeGuessedEmails}
          onChange={handleChange}
          label="Exclude Guessed Emails"
          disabled={starting}
        />
        <Checkbox
          id="excludeNoEmails"
          name="excludeNoEmails"
          checked={formData.excludeNoEmails}
          onChange={handleChange}
          label="Exclude Leads Without Emails"
          disabled={starting}
        />
        <Checkbox
          id="getEmails"
          name="getEmails"
          checked={formData.getEmails}
          onChange={handleChange}
          label="Fetch Emails"
          disabled={starting}
        />
      </div>
      {startError && <div className="text-red-500">{startError}</div>}
      <Button
        variant="primary"
        disabled={starting || !formData.searchUrl.trim()}
      >
        {starting ? 'Starting...' : 'Start Campaign'}
      </Button>
    </form>
  );

  if (loading) {
    return (
      <div className="text-gray-400">Loading campaign...</div>
    );
  }

  if (error || !campaign) {
    return (
      <div className="text-red-500">{error || 'Campaign not found'}</div>
    );
  }

  return (
    <>
      <PageMeta
        title={`Campaign ${campaign.name} | LeadGen`}
        description="Campaign details and management"
      />
      <PageBreadcrumb 
        pageTitle={campaign.name || `Campaign ${campaign.id}`}
        items={[
          { label: 'Campaigns', path: '/campaigns' },
          { label: campaign.name || `Campaign ${campaign.id}` }
        ]}
      />
      <div className="space-y-5 sm:space-y-6">
        <ComponentCard title="Campaign Details">
          <div className="space-y-4">
            <div>
              <h2 className="text-xl font-semibold text-gray-800 dark:text-white/90">
                {campaign.name || `Campaign ${campaign.id}`}
              </h2>
              <p className="text-gray-400 mt-1">{campaign.description}</p>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <span className="text-gray-400">Created:</span>
                <span className="ml-2 text-gray-800 dark:text-white/90">
                  {new Date(campaign.created_at).toLocaleString()}
                </span>
              </div>
              <div>
                <span className="text-gray-400">Status:</span>
                <span className="ml-2 text-gray-800 dark:text-white/90">
                  {campaign.status || 'created'}
                </span>
              </div>
            </div>
          </div>
        </ComponentCard>

        {campaign.status === 'created' && (
          <ComponentCard title="Start Campaign">
            {showStartForm ? (
              renderStartForm()
            ) : (
              <div className="text-center">
                <p className="text-gray-400 mb-4">Ready to start generating leads?</p>
                <Button
                  variant="primary"
                  onClick={() => setShowStartForm(true)}
                >
                  Start Campaign
                </Button>
              </div>
            )}
          </ComponentCard>
        )}
      </div>
    </>
  );
};

export default CampaignDetail; 
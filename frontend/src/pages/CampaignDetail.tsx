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
            <div className="text-center">
              <Button
                variant="primary"
                onClick={async () => {
                  setStarting(true);
                  try {
                    const response = await api.post(`/api/campaigns/${campaign.id}/start`, {});
                    if (response.status === 'error') {
                      toast.error(response.message);
                      return;
                    }
                    toast.success('Campaign started successfully');
                    setCampaign(response.data);
                    startStatusPolling();
                  } catch (error) {
                    toast.error('Failed to start campaign');
                  } finally {
                    setStarting(false);
                  }
                }}
                disabled={starting}
              >
                {starting ? 'Starting...' : 'Start Campaign'}
              </Button>
            </div>
          </ComponentCard>
        )}
      </div>
    </>
  );
};

export default CampaignDetail; 
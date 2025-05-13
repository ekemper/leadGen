import React, { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { api } from '../config/api';
import { toast } from 'react-toastify';
import { CampaignStatus, Campaign } from '../types/campaign';
import PageBreadcrumb from '../components/common/PageBreadCrumb';
import ComponentCard from '../components/common/ComponentCard';
import PageMeta from '../components/common/PageMeta';
import Button from '../components/ui/button/Button';
import Badge from '../components/ui/badge/Badge';

type EditableCampaignFields = 'name' | 'description' | 'fileName' | 'totalRecords' | 'url';

const getStatusColor = (status: string) => {
  switch (status?.toLowerCase()) {
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
  switch (status?.toLowerCase()) {
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

const CampaignDetail: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const [campaign, setCampaign] = useState<Campaign | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [editMode, setEditMode] = useState<Record<EditableCampaignFields, boolean>>({} as Record<EditableCampaignFields, boolean>);
  const [editedFields, setEditedFields] = useState<Partial<Record<EditableCampaignFields, string | number>>>({});
  const [saveLoading, setSaveLoading] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [startLoading, setStartLoading] = useState(false);
  const [startError, setStartError] = useState<string | null>(null);

  useEffect(() => {
    fetchCampaign();
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
      // Reset edit mode and edited fields after fetch
      setEditMode({} as Record<EditableCampaignFields, boolean>);
      setEditedFields({});
      
      // Start polling if campaign is in progress
      /*
      if (response.data.status === CampaignStatus.FETCHING_LEADS || 
          response.data.status === CampaignStatus.VERIFYING_EMAILS ||
          response.data.status === CampaignStatus.ENRICHING_LEADS ||
          response.data.status === CampaignStatus.GENERATING_EMAILS) {
        startStatusPolling();
      }
      */
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  /*
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
  */

  // Helper to start editing a field
  const handleEdit = (field: EditableCampaignFields) => {
    setEditMode(prev => ({ ...prev, [field]: true }));
    setEditedFields(prev => ({ ...prev, [field]: campaign ? (campaign as any)[field] : undefined }));
  };

  // Helper to change a field value
  const handleFieldChange = (field: EditableCampaignFields, value: string | number) => {
    setEditedFields(prev => ({ ...prev, [field]: value }));
  };

  // Helper to save edits
  const handleSave = async () => {
    setSaveLoading(true);
    setSaveError(null);
    try {
      const response = await api.patch(`/api/campaigns/${id}`, editedFields);
      if (response.status === 'success') {
        toast.success('Campaign updated!');
        setEditMode({} as Record<EditableCampaignFields, boolean>);
        setEditedFields({});
        fetchCampaign();
      } else {
        setSaveError(response.message || 'Failed to update campaign.');
      }
    } catch (err: any) {
      setSaveError(err.message || 'Failed to update campaign.');
    } finally {
      setSaveLoading(false);
    }
  };

  // Helper to cancel edits
  const handleCancelEdit = () => {
    setEditMode({} as Record<EditableCampaignFields, boolean>);
    setEditedFields({});
    setSaveError(null);
  };

  // Helper to start the campaign
  const handleStartCampaign = async () => {
    setStartLoading(true);
    setStartError(null);
    try {
      const response = await api.post(`/api/campaigns/${id}/start`);
      if (response.status === 'success') {
        toast.success('Campaign started!');
        fetchCampaign();
      } else {
        setStartError(response.message || 'Failed to start campaign.');
        toast.error(response.message || 'Failed to start campaign.');
      }
    } catch (err: any) {
      setStartError(err.message || 'Failed to start campaign.');
      toast.error(err.message || 'Failed to start campaign.');
    } finally {
      setStartLoading(false);
    }
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

  // Debug: log campaign status
  console.log('Campaign status:', campaign.status);

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
      <ComponentCard title="Campaign Details">
        <div className="space-y-4">
          <div>
            {/* Editable Name */}
            <h2 className="text-xl font-semibold text-gray-800 dark:text-white/90 flex items-center gap-3">
              {editMode.name ? (
                <input
                  className="border rounded px-2 py-1 text-lg"
                  value={editedFields.name ?? (campaign as any).name}
                  onChange={e => handleFieldChange('name', e.target.value)}
                  autoFocus
                />
              ) : (
                <>
                  {campaign.status?.toUpperCase() === CampaignStatus.CREATED
                    ? <span onClick={() => handleEdit('name')} className="cursor-pointer hover:underline">{(campaign as any).name || `Campaign ${(campaign as any).id}`}</span>
                    : <span>{(campaign as any).name || `Campaign ${(campaign as any).id}`}</span>
                  }
                  {/* Status badge */}
                  <Badge size="sm" color={getStatusColor(campaign.status)}>
                    {getStatusLabel(campaign.status)}
                  </Badge>
                </>
              )}
            </h2>
            {/* Status message if present */}
            {campaign.status_message && (
              <div className="text-xs text-gray-400 mt-1">{campaign.status_message}</div>
            )}
            {/* Editable Description */}
            <p className="text-gray-400 mt-1">
              {editMode.description ? (
                <textarea
                  className="border rounded px-2 py-1 w-full"
                  value={editedFields.description ?? (campaign as any).description}
                  onChange={e => handleFieldChange('description', e.target.value)}
                  autoFocus
                />
              ) : (
                (campaign.status?.toUpperCase() === CampaignStatus.CREATED)
                  ? <span onClick={() => handleEdit('description')} className="cursor-pointer hover:underline">{(campaign as any).description}</span>
                  : <span>{(campaign as any).description}</span>
              )}
            </p>
          </div>
          <div className="grid grid-cols-2 gap-4">
            {/* Editable File Name */}
            <div>
              <span className="text-gray-400">File Name:</span>
              {editMode.fileName ? (
                <input
                  className="ml-2 border rounded px-2 py-1"
                  value={editedFields.fileName ?? campaign.fileName}
                  onChange={e => handleFieldChange('fileName', e.target.value)}
                  autoFocus
                />
              ) : (
                (campaign.status?.toUpperCase() === CampaignStatus.CREATED)
                  ? <span className="ml-2 cursor-pointer hover:underline" onClick={() => handleEdit('fileName')}>{campaign.fileName}</span>
                  : <span className="ml-2">{campaign.fileName}</span>
              )}
            </div>
            {/* Editable Total Records */}
            <div>
              <span className="text-gray-400">Total Records:</span>
              {editMode.totalRecords ? (
                <input
                  className="ml-2 border rounded px-2 py-1 w-24"
                  type="number"
                  min={1}
                  max={1000}
                  value={editedFields.totalRecords ?? campaign.totalRecords}
                  onChange={e => handleFieldChange('totalRecords', Number(e.target.value))}
                  autoFocus
                />
              ) : (
                (campaign.status?.toUpperCase() === CampaignStatus.CREATED)
                  ? <span className="ml-2 cursor-pointer hover:underline" onClick={() => handleEdit('totalRecords')}>{campaign.totalRecords}</span>
                  : <span className="ml-2">{campaign.totalRecords}</span>
              )}
            </div>
            {/* Editable URL */}
            <div className="col-span-2">
              <span className="text-gray-400">URL:</span>
              {editMode.url ? (
                <input
                  className="ml-2 border rounded px-2 py-1 w-full"
                  value={editedFields.url ?? campaign.url}
                  onChange={e => handleFieldChange('url', e.target.value)}
                  autoFocus
                />
              ) : (
                (campaign.status?.toUpperCase() === CampaignStatus.CREATED)
                  ? <span className="ml-2 cursor-pointer hover:underline" onClick={() => handleEdit('url')}>{campaign.url}</span>
                  : <span className="ml-2">{campaign.url}</span>
              )}
            </div>
          </div>
        </div>
        {/* Save/Cancel or Start Campaign Button */}
        {Object.keys(editedFields).length > 0 ? (
          <div className="mt-6 flex gap-2 items-center">
            <Button variant="primary" onClick={handleSave} disabled={saveLoading}>
              {saveLoading ? 'Saving...' : 'Save'}
            </Button>
            <Button variant="outline" onClick={handleCancelEdit} disabled={saveLoading}>
              Cancel
            </Button>
            {saveError && <span className="text-red-500 ml-2">{saveError}</span>}
          </div>
        ) : (
          campaign.status === CampaignStatus.CREATED && (
            <div className="mt-6 flex gap-2 items-center">
              <Button variant="primary" onClick={handleStartCampaign} disabled={startLoading}>
                {startLoading ? 'Starting...' : 'Start Campaign'}
              </Button>
              {startError && <span className="text-red-500 ml-2">{startError}</span>}
            </div>
          )
        )}
      </ComponentCard>
    </>
  );
};

export default CampaignDetail;
import React, { useEffect, useState, useRef } from 'react';
import { useParams } from 'react-router-dom';
import { api } from '../config/api';
import { toast } from 'react-toastify';
import { CampaignStatus, Campaign, CampaignLeadStats } from '../types/campaign';
import PageBreadcrumb from '../components/common/PageBreadCrumb';
import ComponentCard from '../components/common/ComponentCard';
import PageMeta from '../components/common/PageMeta';
import Button from '../components/ui/button/Button';
import Badge from '../components/ui/badge/Badge';
import { Table, TableHeader, TableBody, TableRow, TableCell, StripedTableBody } from '../components/ui/table';

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

// Helper to format URL for display: base URL on first line, each param on a new line
const formatUrlForDisplay = (url: string) => {
  const [base, paramString] = url.split('?', 2);
  let out = base;
  if (paramString) {
    const params = paramString.split('&');
    const alignSpan = `<span style=\"display:inline-block;width:4ch;\"></span>`;
    out += '<br />' + alignSpan + '?' + decodeURIComponent(params[0]) +
      (params.length > 1
        ? params.slice(1).map(p => '<br />' + alignSpan + '&amp;' + decodeURIComponent(p)).join('')
        : '');
  }
  return out;
};

const CampaignDetail: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const [campaign, setCampaign] = useState<Campaign | null>(null);
  const [leadStats, setLeadStats] = useState<CampaignLeadStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [editMode, setEditMode] = useState<Record<EditableCampaignFields, boolean>>({} as Record<EditableCampaignFields, boolean>);
  const [editedFields, setEditedFields] = useState<Partial<Record<EditableCampaignFields, string | number>>>({});
  const [saveLoading, setSaveLoading] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [startLoading, setStartLoading] = useState(false);
  const [startError, setStartError] = useState<string | null>(null);
  const pollingRef = useRef<NodeJS.Timeout | null>(null);

  // Helper to determine if campaign is in progress
  const isCampaignInProgress = (status: CampaignStatus | string | undefined) => {
    return [
      CampaignStatus.FETCHING_LEADS,
      CampaignStatus.VERIFYING_EMAILS,
      CampaignStatus.ENRICHING_LEADS,
      CampaignStatus.GENERATING_EMAILS
    ].includes(status as CampaignStatus);
  };

  // Helper to determine if campaign is past CREATED
  const isPastCreated = (status: CampaignStatus | string | undefined) => {
    return status && status !== CampaignStatus.CREATED;
  };

  useEffect(() => {
    fetchCampaign();
    fetchLeadStats();
    // Only start polling if campaign is in progress
    if (campaign && isCampaignInProgress(campaign.status)) {
      startLeadStatsPolling();
    } else {
      if (pollingRef.current) clearInterval(pollingRef.current);
    }
    return () => {
      if (pollingRef.current) clearInterval(pollingRef.current);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id, campaign?.status]);

  // Stop polling if campaign transitions to COMPLETED or FAILED
  useEffect(() => {
    if (campaign && [CampaignStatus.COMPLETED, CampaignStatus.FAILED].includes(campaign.status as CampaignStatus)) {
      if (pollingRef.current) clearInterval(pollingRef.current);
    }
  }, [campaign?.status]);

  const startLeadStatsPolling = () => {
    if (pollingRef.current) clearInterval(pollingRef.current);
    pollingRef.current = setInterval(() => {
      fetchLeadStats();
    }, 5000);
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
      setEditMode({} as Record<EditableCampaignFields, boolean>);
      setEditedFields({});
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const fetchLeadStats = async () => {
    try {
      const response = await api.get(`/api/campaigns/${id}/details`);
      if (response.status === 'success' && response.data.lead_stats) {
        setLeadStats(response.data.lead_stats);
      } else {
        setLeadStats(null);
      }
    } catch (err: any) {
      setLeadStats(null);
    }
  };

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
      {/* Two-column layout for details and stats */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 w-full">
        <div>
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
                      ? <span className="ml-2 cursor-pointer hover:underline text-gray-800 dark:text-white/90" onClick={() => handleEdit('fileName')}>{campaign.fileName}</span>
                      : <span className="ml-2 text-gray-800 dark:text-white/90">{campaign.fileName}</span>
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
                      ? <span className="ml-2 cursor-pointer hover:underline text-gray-800 dark:text-white/90" onClick={() => handleEdit('totalRecords')}>{campaign.totalRecords}</span>
                      : <span className="ml-2 text-gray-800 dark:text-white/90">{campaign.totalRecords}</span>
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
                      ? <span className="ml-2 cursor-pointer hover:underline text-gray-800 dark:text-white/90 whitespace-pre-line" onClick={() => handleEdit('url')} dangerouslySetInnerHTML={{__html: formatUrlForDisplay(campaign.url)}} />
                      : <span className="ml-2 text-gray-800 dark:text-white/90 whitespace-pre-line" dangerouslySetInnerHTML={{__html: formatUrlForDisplay(campaign.url)}} />
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
        </div>
        {/* Enrichment Stats Section */}
        {isPastCreated(campaign.status) && (
          <div>
            <ComponentCard title="Enrichment Stats">
              {leadStats ? (
                <div className="overflow-hidden rounded-2xl border border-gray-200 bg-white px-4 pb-3 pt-4 dark:border-gray-800 dark:bg-white/[0.03] sm:px-6">
                  <div className="max-w-full overflow-x-auto">
                    <Table>
                      <TableHeader className="border-gray-100 dark:border-gray-800 border-y">
                        <TableRow>
                          <TableCell isHeader className="py-3 font-medium text-gray-500 text-start text-theme-xs dark:text-gray-400">Metric</TableCell>
                          <TableCell isHeader className="py-3 font-medium text-gray-500 text-start text-theme-xs dark:text-gray-400">Value</TableCell>
                        </TableRow>
                      </TableHeader>
                      <StripedTableBody className="divide-y divide-gray-100 dark:divide-gray-800" stripeClassName="bg-gray-100 dark:bg-gray-900/30">
                        <TableRow>
                          <TableCell className="pl-4 sm:pl-6 py-3 font-medium text-gray-800 text-theme-sm dark:text-white/90">Total Leads Fetched</TableCell>
                          <TableCell className="pl-4 sm:pl-6 py-3 text-gray-500 text-theme-sm dark:text-gray-400">{leadStats.total_leads_fetched}</TableCell>
                        </TableRow>
                        <TableRow>
                          <TableCell className="pl-4 sm:pl-6 py-3 font-medium text-gray-800 text-theme-sm dark:text-white/90">Leads with Email</TableCell>
                          <TableCell className="pl-4 sm:pl-6 py-3 text-gray-500 text-theme-sm dark:text-gray-400">{leadStats.leads_with_email}</TableCell>
                        </TableRow>
                        <TableRow>
                          <TableCell className="pl-4 sm:pl-6 py-3 font-medium text-gray-800 text-theme-sm dark:text-white/90">Leads with Verified Email</TableCell>
                          <TableCell className="pl-4 sm:pl-6 py-3 text-gray-500 text-theme-sm dark:text-gray-400">{leadStats.leads_with_verified_email}</TableCell>
                        </TableRow>
                        <TableRow>
                          <TableCell className="pl-4 sm:pl-6 py-3 font-medium text-gray-800 text-theme-sm dark:text-white/90">Leads with Enrichment</TableCell>
                          <TableCell className="pl-4 sm:pl-6 py-3 text-gray-500 text-theme-sm dark:text-gray-400">{leadStats.leads_with_enrichment}</TableCell>
                        </TableRow>
                        <TableRow>
                          <TableCell className="pl-4 sm:pl-6 py-3 font-medium text-gray-800 text-theme-sm dark:text-white/90">Leads with Email Copy</TableCell>
                          <TableCell className="pl-4 sm:pl-6 py-3 text-gray-500 text-theme-sm dark:text-gray-400">{leadStats.leads_with_email_copy}</TableCell>
                        </TableRow>
                        <TableRow>
                          <TableCell className="pl-4 sm:pl-6 py-3 font-medium text-gray-800 text-theme-sm dark:text-white/90">Leads with Instantly Record</TableCell>
                          <TableCell className="pl-4 sm:pl-6 py-3 text-gray-500 text-theme-sm dark:text-gray-400">{leadStats.leads_with_instantly_record}</TableCell>
                        </TableRow>
                      </StripedTableBody>
                    </Table>
                  </div>
                  {leadStats.error_message && (
                    <div className="mt-2"><Badge color="error" size="sm">Error: {leadStats.error_message}</Badge></div>
                  )}
                </div>
              ) : (
                <div className="text-gray-400">No lead stats available.</div>
              )}
            </ComponentCard>
          </div>
        )}
      </div>
    </>
  );
};

export default CampaignDetail;
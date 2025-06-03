import React, { useEffect, useState, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { toast } from 'react-toastify';
import { campaignService } from '../services/campaignService';
import { CampaignStatus, CampaignResponse, CampaignLeadStats, InstantlyAnalytics, CampaignUpdate } from '../types/campaign';
import PageBreadcrumb from '../components/common/PageBreadCrumb';
import ComponentCard from '../components/common/ComponentCard';
import PageMeta from '../components/common/PageMeta';
import Button from '../components/ui/button/Button';
import Badge from '../components/ui/badge/Badge';
import { Table, TableHeader, TableRow, TableCell, StripedTableBody } from '../components/ui/table';
import LineChartOne from '../components/charts/line/LineChartOne';
import MonthlyTarget from '../components/ecommerce/MonthlyTarget';
import Input from '../components/form/input/InputField';
import TextArea from '../components/form/input/TextArea';

type EditableCampaignFields = 'name' | 'description' | 'fileName' | 'totalRecords' | 'url';

const getStatusColor = (status: string) => {
  switch (status?.toLowerCase()) {
    case 'completed':
      return 'success';
    case 'created':
      return 'info';
    case 'running':
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
    case 'running':
      return 'Running';
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
  const navigate = useNavigate();
  const [campaign, setCampaign] = useState<CampaignResponse | null>(null);
  const [leadStats, setLeadStats] = useState<CampaignLeadStats | null>(null);
  const [instantlyAnalytics, setInstantlyAnalytics] = useState<InstantlyAnalytics | null>(null);
  const [campaignLoading, setCampaignLoading] = useState(true);
  const [statsLoading, setStatsLoading] = useState(true);
  const [analyticsLoading, setAnalyticsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [editMode, setEditMode] = useState<Record<EditableCampaignFields, boolean>>({} as Record<EditableCampaignFields, boolean>);
  const [editedFields, setEditedFields] = useState<Partial<Record<EditableCampaignFields, string | number>>>({});
  const [saveLoading, setSaveLoading] = useState(false);
  const [startLoading, setStartLoading] = useState(false);
  const [deleteLoading, setDeleteLoading] = useState(false);
  const pollingRef = useRef<NodeJS.Timeout | null>(null);
  const statsPollingRef = useRef<NodeJS.Timeout | null>(null);
  const isInitialStatsLoad = useRef(true);

  // Helper to determine if campaign is in progress
  const isCampaignInProgress = (status: CampaignStatus | string | undefined) => {
    return status === CampaignStatus.RUNNING;
  };

  // Helper to determine if campaign is past CREATED
  const isPastCreated = (status: CampaignStatus | string | undefined) => {
    return status && status !== CampaignStatus.CREATED;
  };

  // Helper to determine if campaign can be started
  const canStartCampaign = (status: CampaignStatus | string | undefined) => {
    return status === CampaignStatus.CREATED;
  };

  // Helper to determine if campaign can be edited
  const canEditCampaign = (status: CampaignStatus | string | undefined) => {
    return status === CampaignStatus.CREATED || status === CampaignStatus.FAILED;
  };

  useEffect(() => {
    if (!id) {
      navigate('/campaigns');
      return;
    }
    
    fetchCampaign();
    fetchLeadStats();
  }, [id, navigate]);

  useEffect(() => {
    // Start polling if campaign is running
    if (campaign && isCampaignInProgress(campaign.status)) {
      startStatusPolling();
      startStatsPolling();
    } else {
      stopPolling();
    }

    return () => stopPolling();
  }, [campaign?.status]);

  const fetchCampaign = async () => {
    if (!id) return;
    
    setCampaignLoading(true);
    setError(null);
    try {
      const response = await campaignService.getCampaign(id);
      setCampaign(response.data);
    } catch (err: any) {
      console.error('Error fetching campaign:', err);
      setError(err.message);
      if (err.message?.toLowerCase().includes('not found')) {
        toast.error('Campaign not found');
        navigate('/campaigns');
      }
    } finally {
      setCampaignLoading(false);
    }
  };

  const fetchLeadStats = async () => {
    if (!id) return;
    
    // Only show loading on initial load, not during polling
    if (isInitialStatsLoad.current) {
      setStatsLoading(true);
    }
    
    try {
      const response = await campaignService.getCampaignStats(id);
      setLeadStats(response.data);
    } catch (err: any) {
      console.error('Error fetching lead stats:', err);
      // Don't set error state during polling to avoid UI flicker
      if (isInitialStatsLoad.current) {
        setError(err.message);
      }
    } finally {
      if (isInitialStatsLoad.current) {
        setStatsLoading(false);
        isInitialStatsLoad.current = false;
      }
    }
  };

  const fetchInstantlyAnalytics = async () => {
    if (!id) return;
    
    setAnalyticsLoading(true);
    try {
      const response = await campaignService.getInstantlyAnalytics(id);
      setInstantlyAnalytics(response.data);
    } catch (err: any) {
      console.error('Error fetching Instantly analytics:', err);
      toast.error('Failed to load Instantly analytics');
    } finally {
      setAnalyticsLoading(false);
    }
  };

  const startStatusPolling = () => {
    if (pollingRef.current) return; // Already polling
    
    pollingRef.current = setInterval(async () => {
      try {
        if (!id) return;
        const response = await campaignService.getCampaign(id);
        setCampaign(response.data);
        
        // Stop polling if campaign is no longer running
        if (!isCampaignInProgress(response.data.status)) {
          stopPolling();
        }
      } catch (err) {
        console.error('Error polling campaign status:', err);
      }
    }, 5000);
  };

  const startStatsPolling = () => {
    if (statsPollingRef.current) return; // Already polling
    
    statsPollingRef.current = setInterval(async () => {
      try {
        if (!id) return;
        const response = await campaignService.getCampaignStats(id);
        setLeadStats(response.data);
      } catch (err) {
        console.error('Error polling campaign stats:', err);
      }
    }, 10000);
  };

  const stopPolling = () => {
    if (pollingRef.current) {
      clearInterval(pollingRef.current);
      pollingRef.current = null;
    }
    if (statsPollingRef.current) {
      clearInterval(statsPollingRef.current);
      statsPollingRef.current = null;
    }
  };

  const handleStartCampaign = async () => {
    if (!id || !campaign) return;
    
    setStartLoading(true);
    try {
      const response = await campaignService.startCampaign(id);
      setCampaign(response.data);
      toast.success('Campaign started successfully!');
    } catch (err: any) {
      console.error('Error starting campaign:', err);
      toast.error(err.message || 'Failed to start campaign');
    } finally {
      setStartLoading(false);
    }
  };

  const handleDeleteCampaign = async () => {
    if (!id || !campaign) return;
    
    if (!confirm(`Are you sure you want to delete campaign "${campaign.name}"? This action cannot be undone.`)) {
      return;
    }
    
    setDeleteLoading(true);
    try {
      await campaignService.deleteCampaign(id);
      toast.success('Campaign deleted successfully!');
      navigate('/campaigns');
    } catch (err: any) {
      console.error('Error deleting campaign:', err);
      toast.error(err.message || 'Failed to delete campaign');
    } finally {
      setDeleteLoading(false);
    }
  };

  const handleEditField = (field: EditableCampaignFields) => {
    if (!campaign || !canEditCampaign(campaign.status)) return;
    
    setEditMode(prev => ({ ...prev, [field]: true }));
    setEditedFields(prev => ({ 
      ...prev, 
      [field]: field === 'totalRecords' ? campaign.totalRecords : campaign[field] 
    }));
  };

  const handleCancelEdit = (field: EditableCampaignFields) => {
    setEditMode(prev => ({ ...prev, [field]: false }));
    setEditedFields(prev => {
      const newFields = { ...prev };
      delete newFields[field];
      return newFields;
    });
  };

  const handleSaveField = async (field: EditableCampaignFields) => {
    if (!id || !campaign) return;
    
    const value = editedFields[field];
    if (value === undefined || value === null) return;
    
    setSaveLoading(true);
    try {
      const updateData: CampaignUpdate = {
        [field]: value
      };
      
      const response = await campaignService.updateCampaign(id, updateData);
      setCampaign(response.data);
      setEditMode(prev => ({ ...prev, [field]: false }));
      setEditedFields(prev => {
        const newFields = { ...prev };
        delete newFields[field];
        return newFields;
      });
      toast.success(`${field} updated successfully!`);
    } catch (err: any) {
      console.error(`Error updating ${field}:`, err);
      toast.error(err.message || `Failed to update ${field}`);
    } finally {
      setSaveLoading(false);
    }
  };

  const handleFieldChange = (field: EditableCampaignFields, value: string | number) => {
    setEditedFields(prev => ({ ...prev, [field]: value }));
  };

  const loading = campaignLoading || statsLoading || analyticsLoading;

  if (error || !campaign) {
    return null;
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
      {/* Campaign Overview Section */}
      <div className="mb-8">
        <ComponentCard title="Campaign Overview">
          {/* Top: Name, Created Date, Status, Description */}
          <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 mb-6">
            <div>
              <h1 className="text-2xl font-bold text-gray-800 dark:text-white mb-1">{campaign.name}</h1>
              <div className="flex items-center gap-2 mb-2">
                <Badge size="sm" color={getStatusColor(campaign.status)}>
                  {getStatusLabel(campaign.status)}
                </Badge>
                <span className="text-gray-500 dark:text-gray-300 text-sm">ID: {campaign.id}</span>
              </div>
              <div className="text-gray-600 dark:text-gray-300 text-sm mb-2">
                {campaign.description ? campaign.description : 'No description provided.'}
              </div>
            </div>
            <div className="flex flex-col md:items-end gap-1">
              <span className="text-gray-500 dark:text-gray-300 text-sm">Created: {new Date(campaign.created_at).toLocaleString()}</span>
            </div>
          </div>
          {/* Two-column grid for metrics */}
          {campaign.status !== CampaignStatus.CREATED && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* First row: Total Leads Enrolled & Total Emails Sent */}
              <div className="flex flex-col h-full justify-between">
                {/* Total Leads Enrolled Large Number Display */}
                {loading ? (
                  <div className="h-20 w-full bg-gray-200 dark:bg-gray-800 rounded animate-pulse mb-2"></div>
                ) : (
                  <div className="flex flex-col sm:flex-row sm:items-end gap-2 mb-2">
                    <div>
                      <div className="text-xs text-gray-500 dark:text-gray-400 uppercase tracking-wide mb-1">Total Leads Enrolled</div>
                      <div className="text-4xl font-extrabold text-gray-900 dark:text-white leading-none">
                        {instantlyAnalytics && instantlyAnalytics.leads_count !== null ? instantlyAnalytics.leads_count : '—'}
                      </div>
                    </div>
                    {/* Subtle upward trend line (sparkline) */}
                    {instantlyAnalytics && instantlyAnalytics.leads_count !== null && (
                      <div className="h-8 w-32 sm:w-40 ml-2 flex items-end">
                        <LineChartOne small inlineOnly oneSeriesOnly />
                      </div>
                    )}
                  </div>
                )}
              </div>
              <div className="flex flex-col h-full justify-between">
                {/* Total Emails Sent Progress Bar */}
                {loading ? (
                  <div className="h-20 w-full bg-gray-200 dark:bg-gray-800 rounded animate-pulse mb-2"></div>
                ) : (
                  <div className="mb-2">
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-xs text-gray-500 dark:text-gray-400 uppercase tracking-wide">Total Emails Sent</span>
                      <span className="text-xs font-semibold text-indigo-600 dark:text-indigo-300">
                        {instantlyAnalytics && instantlyAnalytics.emails_sent_count !== null && campaign.totalRecords
                          ? `${Math.round((instantlyAnalytics.emails_sent_count / campaign.totalRecords) * 100)}%`
                          : '--'}
                      </span>
                    </div>
                    <div className="w-full bg-indigo-100 dark:bg-indigo-900/30 rounded-full h-3">
                      <div
                        className="h-3 rounded-full bg-indigo-400 dark:bg-indigo-300 transition-all duration-500"
                        style={{ width: instantlyAnalytics && instantlyAnalytics.emails_sent_count !== null && campaign.totalRecords
                          ? `${Math.min(100, (instantlyAnalytics.emails_sent_count / campaign.totalRecords) * 100)}%`
                          : '0%' }}
                      ></div>
                    </div>
                    <div className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                      {instantlyAnalytics && instantlyAnalytics.emails_sent_count !== null
                        ? `${instantlyAnalytics.emails_sent_count.toLocaleString()} emails sent` : '--'}
                      {campaign.totalRecords ? ` of ${campaign.totalRecords.toLocaleString()} total` : ''}
                    </div>
                  </div>
                )}
              </div>
              {/* Second row: Reply Rate & Bounce Rate */}
              <div className="flex flex-col h-full justify-between">
                {/* Reply Rate Radial Gauge */}
                {loading ? (
                  <div className="rounded-2xl border border-gray-200 bg-gray-100 dark:border-gray-800 dark:bg-white/[0.03] py-8 px-4 w-full animate-pulse min-h-[220px]"></div>
                ) : (
                  instantlyAnalytics && instantlyAnalytics.reply_count !== null && instantlyAnalytics.emails_sent_count !== null ? (
                    <MonthlyTarget
                      value={Math.min(100, instantlyAnalytics.emails_sent_count > 0 ? (instantlyAnalytics.reply_count / instantlyAnalytics.emails_sent_count) * 100 : 0)}
                      color={(() => {
                        const rate = instantlyAnalytics.emails_sent_count > 0 ? (instantlyAnalytics.reply_count / instantlyAnalytics.emails_sent_count) * 100 : 0;
                        if (rate < 10) return ['#EF4444', '#F59E42']; // red to orange
                        if (rate < 20) return ['#F59E42', '#FACC15']; // orange to yellow
                        if (rate < 40) return ['#FACC15', '#22C55E']; // yellow to green
                        return ['#22C55E', '#16A34A']; // green shades
                      })()}
                      label="Reply Rate"
                      hideDropdown
                      hidePerformancePill
                      hideFooterStats
                      hideDescription
                      hideExtraText
                      minimalBackground
                      className="py-8 px-4"
                    />
                  ) : (
                    <div className="rounded-2xl border border-gray-200 bg-gray-100 dark:border-gray-800 dark:bg-white/[0.03] py-8 px-4 w-full flex items-center justify-center min-h-[220px] text-gray-400 dark:text-gray-600">No reply data</div>
                  )
                )}
              </div>
              <div className="flex flex-col h-full justify-between items-center">
                {/* Bounce Rate Card styled to match Reply Rate gauge */}
                {loading ? (
                  <div className="rounded-2xl border border-gray-200 bg-gray-100 dark:border-gray-800 dark:bg-white/[0.03] py-8 px-4 w-full animate-pulse min-h-[220px]"></div>
                ) : (
                  <div className="rounded-2xl border border-gray-200 bg-gray-100 dark:border-gray-800 dark:bg-white/[0.03] w-full flex flex-col items-center py-8 px-4">
                    <h3 className="text-lg font-semibold text-gray-800 dark:text-white/90 mb-4">Bounce Rate</h3>
                    {instantlyAnalytics && instantlyAnalytics.bounced_count !== null && instantlyAnalytics.emails_sent_count !== null ? (
                      (() => {
                        const bounceRate = instantlyAnalytics.emails_sent_count > 0 ? (instantlyAnalytics.bounced_count / instantlyAnalytics.emails_sent_count) * 100 : 0;
                        let pillColor = 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300';
                        let label = 'Good';
                        if (bounceRate > 10 && bounceRate <= 20) {
                          pillColor = 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-300';
                          label = 'Caution';
                        } else if (bounceRate > 20) {
                          pillColor = 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300';
                          label = 'Problem';
                        }
                        return (
                          <span className={`px-4 py-2 rounded-full font-semibold text-sm ${pillColor}`}>{`${bounceRate.toFixed(1)}% • ${label}`}</span>
                        );
                      })()
                    ) : (
                      <span className="px-4 py-2 rounded-full font-semibold text-sm bg-gray-100 text-gray-400 dark:bg-gray-900/30 dark:text-gray-500">No bounce data</span>
                    )}
                  </div>
                )}
              </div>
            </div>
          )}
        </ComponentCard>
      </div>
      {/* Two-column layout for details and stats */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 w-full">
        <div>
          <ComponentCard title="Lead Scraping Parameters">
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                {/* Editable File Name */}
                <div>
                  <span className="text-gray-400">File Name:</span>
                  {editMode.fileName ? (
                    <Input
                      type="text"
                      value={String(editedFields.fileName ?? campaign.fileName)}
                      onChange={e => handleFieldChange('fileName', e.target.value)}
                    />
                  ) : (
                    (campaign.status === CampaignStatus.CREATED)
                      ? <span className="ml-2 cursor-pointer hover:underline text-gray-800 dark:text-white/90" onClick={() => handleEditField('fileName')}>{campaign.fileName}</span>
                      : <span className="ml-2 text-gray-800 dark:text-white/90">{campaign.fileName}</span>
                  )}
                </div>
                {/* Editable Total Records */}
                <div>
                  <span className="text-gray-400">Total Records:</span>
                  {editMode.totalRecords ? (
                    <Input
                      type="number"
                      min="1"
                      max="1000"
                      value={String(editedFields.totalRecords ?? campaign.totalRecords)}
                      onChange={e => handleFieldChange('totalRecords', Number(e.target.value))}
                    />
                  ) : (
                    (campaign.status === CampaignStatus.CREATED)
                      ? <span className="ml-2 cursor-pointer hover:underline text-gray-800 dark:text-white/90" onClick={() => handleEditField('totalRecords')}>{campaign.totalRecords}</span>
                      : <span className="ml-2 text-gray-800 dark:text-white/90">{campaign.totalRecords}</span>
                  )}
                </div>
                {/* Editable URL */}
                <div className="col-span-2">
                  <span className="text-gray-400">URL:</span>
                  {editMode.url ? (
                    <TextArea
                      value={String(editedFields.url ?? campaign.url)}
                      onChange={value => handleFieldChange('url', value)}
                      rows={3}
                    />
                  ) : (
                    (campaign.status === CampaignStatus.CREATED)
                      ? <span className="ml-2 cursor-pointer hover:underline text-gray-800 dark:text-white/90 whitespace-pre-line" onClick={() => handleEditField('url')} dangerouslySetInnerHTML={{__html: formatUrlForDisplay(campaign.url)}} />
                      : <span className="ml-2 text-gray-800 dark:text-white/90 whitespace-pre-line" dangerouslySetInnerHTML={{__html: formatUrlForDisplay(campaign.url)}} />
                  )}
                </div>
              </div>
            </div>
            {/* Save/Cancel or Start Campaign Button */}
            {Object.keys(editedFields).length > 0 ? (
              <div className="mt-6 flex gap-2 items-center">
                <Button variant="primary" onClick={() => {
                  // Save all fields that have been edited
                  Object.keys(editedFields).forEach(field => {
                    handleSaveField(field as EditableCampaignFields);
                  });
                }} disabled={saveLoading}>
                  {saveLoading ? 'Saving...' : 'Save'}
                </Button>
                <Button variant="outline" onClick={() => {
                  // Cancel all edits
                  Object.keys(editedFields).forEach(field => {
                    handleCancelEdit(field as EditableCampaignFields);
                  });
                }} disabled={saveLoading}>
                  Cancel
                </Button>
              </div>
            ) : (
              <div className="mt-6 flex gap-2 items-center">
                {canStartCampaign(campaign.status) && (
                  <Button variant="primary" onClick={handleStartCampaign} disabled={startLoading}>
                    {startLoading ? 'Starting...' : 'Start Campaign'}
                  </Button>
                )}
                {/* Temporarily commenting out delete button until backend DELETE endpoint is implemented */}
                {/* {canEditCampaign(campaign.status) && (
                  <Button variant="outline" onClick={handleDeleteCampaign} disabled={deleteLoading}>
                    {deleteLoading ? 'Deleting...' : 'Delete Campaign'}
                  </Button>
                )} */}
                {isPastCreated(campaign.status) && (
                  <Button variant="outline" onClick={fetchInstantlyAnalytics} disabled={analyticsLoading}>
                    {analyticsLoading ? 'Loading...' : 'Load Instantly Analytics'}
                  </Button>
                )}
              </div>
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
      {/* Instantly Analytics Section */}
      <div className="mt-8">
        <ComponentCard title="Instantly Analytics (Raw)">
          <pre className="overflow-x-auto text-xs bg-gray-100 dark:bg-gray-900 rounded p-4 text-gray-800 dark:text-white">
            {instantlyAnalytics ? JSON.stringify(instantlyAnalytics, null, 2) : 'No Instantly analytics data.'}
          </pre>
        </ComponentCard>
      </div>
    </>
  );
};

export default CampaignDetail;
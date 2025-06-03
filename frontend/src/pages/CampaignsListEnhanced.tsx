import React, { useEffect, useState, useCallback } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { toast } from 'react-toastify';
import { campaignService, CampaignListParams } from '../services/campaignService';
import { OrganizationService } from '../services/organizationService';
import { CampaignResponse, CampaignCreate, CampaignStatus } from '../types/campaign';
import { OrganizationResponse } from '../types/organization';
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
import Select from '../components/form/Select';
import TextArea from '../components/form/input/TextArea';
import ErrorBoundary from '../components/common/ErrorBoundary';
import { CampaignCardSkeleton, TableSkeleton, FormSkeleton } from '../components/ui/skeleton/ContentSkeletons';
import { useError } from '../context/ErrorContext';
import { useNetwork } from '../context/NetworkContext';
import { useRetry } from '../hooks/useRetry';
import { useLoadingState } from '../hooks/useLoadingState';

interface FormErrors {
  fileName?: string;
  totalRecords?: string;
  name?: string;
  description?: string;
  organization_id?: string;
  url?: string;
}

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
    case 'completed':
      return 'Completed';
    case 'created':
      return 'Created';
    case 'running':
      return 'Running';
    case 'failed':
      return 'Failed';
    default:
      return status || 'Unknown';
  }
};

const CampaignsListEnhanced: React.FC = () => {
  const navigate = useNavigate();
  const { handleApiError, handleRetryableError } = useError();
  const { isOnline, executeWhenOnline } = useNetwork();
  
  // State management
  const [campaigns, setCampaigns] = useState<CampaignResponse[]>([]);
  const [organizations, setOrganizations] = useState<OrganizationResponse[]>([]);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedOrganization, setSelectedOrganization] = useState<string>('');
  const [selectedStatus, setSelectedStatus] = useState<string>('');
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(0);
  const [totalCampaigns, setTotalCampaigns] = useState(0);
  
  // Form state
  const [formData, setFormData] = useState<CampaignCreate>({
    name: '',
    description: '',
    organization_id: '',
    fileName: 'motorcycle_dealers',
    totalRecords: 500,
    url: 'https://app.apollo.io/#/people?contactEmailStatusV2%5B%5D=verified&contactEmailExcludeCatchAll=true&personTitles%5B%5D=CEO&personTitles%5B%5D=Founder&personTitles%5B%5D=sales%20manager&personTitles%5B%5D=chief%20sales%20officer&personLocations%5B%5D=United%20States&sortAscending=false&sortByField=recommendations_score&page=1&qOrganizationKeywordTags%5B%5D=motorcycle%20dealership&qOrganizationKeywordTags%5B%5D=harley%20davidson&qOrganizationKeywordTags%5B%5D=motorcycle&qOrganizationKeywordTags%5B%5D=carsports&includedOrganizationKeywordFields%5B%5D=tags&includedOrganizationKeywordFields%5B%5D=name&personNotTitles%5B%5D=assistant%20sales%20manager',
  });
  const [formErrors, setFormErrors] = useState<FormErrors>({});

  // Enhanced loading states
  const campaignsLoading = useLoadingState({ minLoadingTime: 300, debounceTime: 150 });
  const orgsLoading = useLoadingState({ minLoadingTime: 200, debounceTime: 100 });
  const createLoading = useLoadingState({ minLoadingTime: 500, debounceTime: 0 });

  // Retry mechanisms
  const fetchCampaignsWithRetry = useRetry(
    useCallback(async (params: CampaignListParams) => {
      return await campaignService.getCampaigns(params);
    }, []),
    {
      maxRetries: 3,
      onRetry: (attempt, error) => {
        toast.info(`Retrying to load campaigns... (${attempt}/3)`);
      },
      onMaxRetriesReached: (error) => {
        handleApiError(error, 'Failed to load campaigns after multiple attempts');
      }
    }
  );

  const fetchOrganizationsWithRetry = useRetry(
    useCallback(async () => {
      return await OrganizationService.getOrganizations();
    }, []),
    {
      maxRetries: 2,
      onRetry: (attempt, error) => {
        toast.info(`Retrying to load organizations... (${attempt}/2)`);
      }
    }
  );

  const createCampaignWithRetry = useRetry(
    useCallback(async (data: CampaignCreate) => {
      return await campaignService.createCampaign(data);
    }, []),
    {
      maxRetries: 2,
      retryCondition: (error) => {
        // Don't retry validation errors
        return error?.response?.status >= 500;
      }
    }
  );

  // Data fetching functions
  const fetchCampaigns = useCallback(async () => {
    try {
      const params: CampaignListParams = {
        page: currentPage,
        per_page: 10,
      };

      if (selectedOrganization) {
        params.organization_id = selectedOrganization;
      }
      if (selectedStatus) {
        params.status = selectedStatus;
      }

      const response = await campaignsLoading.withLoading(async () => {
        return await fetchCampaignsWithRetry.execute(params);
      });

      setCampaigns(response.data.campaigns);
      setTotalPages(response.data.pages);
      setTotalCampaigns(response.data.total);
      setShowCreateForm(response.data.campaigns.length === 0 && currentPage === 1);
    } catch (err: any) {
      handleApiError(err, 'Failed to load campaigns');
      setCampaigns([]);
      setShowCreateForm(true);
    }
  }, [currentPage, selectedOrganization, selectedStatus, campaignsLoading, fetchCampaignsWithRetry, handleApiError]);

  const fetchOrganizations = useCallback(async () => {
    try {
      const response = await orgsLoading.withLoading(async () => {
        return await fetchOrganizationsWithRetry.execute();
      });
      setOrganizations(response.data);
    } catch (err: any) {
      handleApiError(err, 'Failed to load organizations');
      setOrganizations([]);
    }
  }, [orgsLoading, fetchOrganizationsWithRetry, handleApiError]);

  // Form validation
  const validateForm = (): boolean => {
    const errors: FormErrors = {};
    if (!formData.fileName.trim()) {
      errors.fileName = 'File Name is required';
    }
    if (!formData.totalRecords || formData.totalRecords < 1) {
      errors.totalRecords = 'Total Records must be at least 1';
    }
    if (formData.totalRecords > 1000) {
      errors.totalRecords = 'Total Records cannot exceed 1000';
    }
    if (!formData.name.trim()) {
      errors.name = 'Name is required';
    }
    if (!formData.description?.trim()) {
      errors.description = 'Description is required';
    }
    if (!formData.organization_id) {
      errors.organization_id = 'Organization is required';
    }
    if (!formData.url.trim()) {
      errors.url = 'URL is required';
    }
    setFormErrors(errors);
    return Object.keys(errors).length === 0;
  };

  // Event handlers
  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => {
    const { name, value, type } = e.target;
    const checked = 'checked' in e.target ? e.target.checked : undefined;
    
    setFormData(prev => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : (name === 'totalRecords' ? Number(value) : value)
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

    if (!isOnline) {
      executeWhenOnline(async () => {
        await handleCreate(e);
      });
      return;
    }

    try {
      const response = await createLoading.withLoading(async () => {
        return await createCampaignWithRetry.execute(formData);
      });
      
      toast.success('Campaign created successfully!');
      navigate(`/campaigns/${response.data.id}`);
    } catch (err: any) {
      if (err?.response?.status < 500) {
        // Client error - show form validation
        handleApiError(err, 'Validation Error', false);
        toast.error(err.message || 'Please check your input and try again');
      } else {
        // Server error - offer retry
        handleRetryableError(err, () => handleCreate(e), 'Create Campaign');
      }
    }
  };

  const handleSearch = (value: string) => {
    setSearchTerm(value);
    setCurrentPage(1);
  };

  const handleOrganizationFilter = (value: string) => {
    setSelectedOrganization(value);
    setCurrentPage(1);
  };

  const handleStatusFilter = (value: string) => {
    setSelectedStatus(value);
    setCurrentPage(1);
  };

  const resetFilters = () => {
    setSearchTerm('');
    setSelectedOrganization('');
    setSelectedStatus('');
    setCurrentPage(1);
  };

  // Effects
  useEffect(() => {
    fetchCampaigns();
    fetchOrganizations();
  }, [fetchCampaigns, fetchOrganizations]);

  // Filter campaigns
  const filteredCampaigns = campaigns.filter(campaign => {
    const matchesSearch = !searchTerm || 
      campaign.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      (campaign.description?.toLowerCase().includes(searchTerm.toLowerCase()));
    return matchesSearch;
  });

  // Render functions
  const renderCreateForm = () => (
    <ErrorBoundary context="Campaign Create Form" fallback={
      <div className="text-center p-8">
        <p className="text-gray-500">Unable to load create form. Please refresh the page.</p>
        <Button variant="outline" onClick={() => window.location.reload()}>
          Refresh
        </Button>
      </div>
    }>
      <div className="rounded-2xl border border-gray-200 bg-white dark:border-gray-800 dark:bg-white/[0.03] max-w-2xl mx-auto mb-8">
        <div className="px-6 py-5">
          <h3 className="text-base font-medium text-gray-800 dark:text-white/90">Create Campaign</h3>
        </div>
        
        {orgsLoading.isLoading ? (
          <div className="p-6">
            <FormSkeleton fields={6} />
          </div>
        ) : (
          <form onSubmit={handleCreate} className="p-4 border-t border-gray-100 dark:border-gray-800 sm:p-6 space-y-6">
            <div>
              <Label htmlFor="organization_id">Organization</Label>
              {organizations.length === 0 ? (
                <div className="text-gray-400">No organizations available. Please create an organization first.</div>
              ) : (
                <Select
                  options={organizations.map((org) => ({ value: org.id, label: org.name }))}
                  placeholder="Select an organization"
                  onChange={(value: string) => handleChange({ target: { name: 'organization_id', value } } as any)}
                  defaultValue={formData.organization_id}
                  className={formErrors.organization_id ? 'error-state' : ''}
                />
              )}
              {formErrors.organization_id && (
                <p className="mt-1 text-sm text-error-500">{formErrors.organization_id}</p>
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
                disabled={createLoading.isLoading}
                error={!!formErrors.name}
                hint={formErrors.name}
                className="focus-ring"
              />
            </div>
            
            <div>
              <Label htmlFor="description">Description</Label>
              <TextArea
                value={formData.description || ''}
                onChange={(value: string) => handleChange({ target: { name: 'description', value } } as any)}
                disabled={createLoading.isLoading}
                error={!!formErrors.description}
                hint={formErrors.description}
                rows={6}
                className="focus-ring"
              />
            </div>
            
            <div>
              <Label htmlFor="fileName">File Name</Label>
              <Input
                id="fileName"
                name="fileName"
                type="text"
                value={formData.fileName}
                onChange={handleChange}
                disabled={createLoading.isLoading}
                error={!!formErrors.fileName}
                hint={formErrors.fileName}
                className="focus-ring"
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
                disabled={createLoading.isLoading}
                error={!!formErrors.totalRecords}
                hint={formErrors.totalRecords}
                className="focus-ring"
              />
            </div>
            
            <div>
              <Label htmlFor="url">URL</Label>
              <TextArea
                value={formData.url}
                onChange={(value: string) => handleChange({ target: { name: 'url', value } } as any)}
                disabled={createLoading.isLoading}
                error={!!formErrors.url}
                hint={formErrors.url}
                rows={3}
                className="focus-ring"
              />
            </div>
            
            <Button
              variant="primary"
              disabled={createLoading.isLoading || createLoading.isDebouncing || !formData.name.trim() || !formData.description?.trim() || !formData.organization_id || !formData.fileName.trim() || !formData.totalRecords || !formData.url.trim()}
              className="w-full"
            >
              {createLoading.isLoading ? 'Creating...' : createLoading.isDebouncing ? 'Preparing...' : 'Create Campaign'}
            </Button>
          </form>
        )}
      </div>
    </ErrorBoundary>
  );

  return (
    <ErrorBoundary context="Campaigns List" showDetails={process.env.NODE_ENV === 'development'}>
      <PageMeta
        title="Campaigns | LeadGen"
        description="Manage your lead generation campaigns"
      />
      <PageBreadcrumb 
        pageTitle="Campaigns"
        items={[{ label: 'Campaigns' }]}
      />

      <ComponentCard title="Campaigns">
        {!isOnline && (
          <div className="mb-4 p-3 bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg">
            <p className="text-sm text-yellow-800 dark:text-yellow-200">
              You're currently offline. Some features may be limited.
            </p>
          </div>
        )}

        {campaigns.length > 0 && (
          <div className="mb-6 flex flex-col sm:flex-row gap-4">
            <div className="flex-1">
              <Input
                type="text"
                placeholder="Search campaigns..."
                value={searchTerm}
                onChange={(e) => handleSearch(e.target.value)}
                className="focus-ring"
              />
            </div>
            <div className="flex gap-2">
              <Select
                options={[
                  { value: '', label: 'All Organizations' },
                  ...organizations.map(org => ({ value: org.id, label: org.name }))
                ]}
                placeholder="Filter by organization"
                onChange={handleOrganizationFilter}
                defaultValue={selectedOrganization}
              />
              <Select
                options={[
                  { value: '', label: 'All Statuses' },
                  { value: CampaignStatus.CREATED, label: 'Created' },
                  { value: CampaignStatus.RUNNING, label: 'Running' },
                  { value: CampaignStatus.COMPLETED, label: 'Completed' },
                  { value: CampaignStatus.FAILED, label: 'Failed' },
                ]}
                placeholder="Filter by status"
                onChange={handleStatusFilter}
                defaultValue={selectedStatus}
              />
              {(searchTerm || selectedOrganization || selectedStatus) && (
                <Button
                  variant="outline"
                  onClick={resetFilters}
                >
                  Clear Filters
                </Button>
              )}
            </div>
          </div>
        )}

        {campaignsLoading.isLoading ? (
          <TableSkeleton rows={5} columns={5} />
        ) : campaigns.length === 0 ? (
          <div className="text-center">
            <h2 className="text-xl text-gray-400 mb-8">There are no campaigns yet - create your first one!</h2>
            {renderCreateForm()}
          </div>
        ) : (
          <>
            {showCreateForm && renderCreateForm()}
            
            <Table>
              <TableHeader>
                <TableRow>
                  <TableCell>Name</TableCell>
                  <TableCell>Organization</TableCell>
                  <TableCell>Status</TableCell>
                  <TableCell>Records</TableCell>
                  <TableCell>Created</TableCell>
                  <TableCell>Actions</TableCell>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredCampaigns.map((campaign) => (
                  <TableRow key={campaign.id}>
                    <TableCell>
                      <div>
                        <div className="font-medium text-gray-900 dark:text-white">
                          {campaign.name}
                        </div>
                        {campaign.description && (
                          <div className="text-sm text-gray-500 dark:text-gray-400 truncate max-w-xs">
                            {campaign.description}
                          </div>
                        )}
                      </div>
                    </TableCell>
                    <TableCell>
                      <span className="text-sm text-gray-600 dark:text-gray-300">
                        {organizations.find(org => org.id === campaign.organization_id)?.name || 'N/A'}
                      </span>
                    </TableCell>
                    <TableCell>
                      <Badge size="sm" color={getStatusColor(campaign.status)}>
                        {getStatusLabel(campaign.status)}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <span className="text-sm text-gray-600 dark:text-gray-300">
                        {campaign.totalRecords || 0}
                      </span>
                    </TableCell>
                    <TableCell>
                      <span className="text-sm text-gray-600 dark:text-gray-300">
                        {new Date(campaign.created_at).toLocaleDateString()}
                      </span>
                    </TableCell>
                    <TableCell>
                      <Link
                        to={`/campaigns/${campaign.id}`}
                        className="text-blue-600 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-300 text-sm font-medium"
                      >
                        View Details
                      </Link>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>

            {/* Pagination */}
            {totalPages > 1 && (
              <div className="mt-6 flex items-center justify-between">
                <div className="text-sm text-gray-700 dark:text-gray-300">
                  Showing {((currentPage - 1) * 10) + 1} to {Math.min(currentPage * 10, totalCampaigns)} of {totalCampaigns} campaigns
                </div>
                <div className="flex gap-2">
                  <Button
                    variant="outline"
                    onClick={() => setCurrentPage(prev => Math.max(1, prev - 1))}
                    disabled={currentPage === 1 || campaignsLoading.isLoading}
                  >
                    Previous
                  </Button>
                  <Button
                    variant="outline"
                    onClick={() => setCurrentPage(prev => Math.min(totalPages, prev + 1))}
                    disabled={currentPage === totalPages || campaignsLoading.isLoading}
                  >
                    Next
                  </Button>
                </div>
              </div>
            )}
          </>
        )}

        {!showCreateForm && campaigns.length > 0 && (
          <div className="mt-6 flex justify-end">
            <Button
              variant="primary"
              onClick={() => setShowCreateForm(true)}
            >
              Create New Campaign
            </Button>
          </div>
        )}
      </ComponentCard>
    </ErrorBoundary>
  );
};

export default CampaignsListEnhanced; 
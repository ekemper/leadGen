import React, { useEffect, useState } from 'react';
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

const CampaignsList: React.FC = () => {
  const navigate = useNavigate();
  const [campaigns, setCampaigns] = useState<CampaignResponse[]>([]);
  const [organizations, setOrganizations] = useState<OrganizationResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [orgsLoading, setOrgsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [orgsError, setOrgsError] = useState<string | null>(null);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedOrganization, setSelectedOrganization] = useState<string>('');
  const [selectedStatus, setSelectedStatus] = useState<string>('');
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(0);
  const [totalCampaigns, setTotalCampaigns] = useState(0);
  const [formData, setFormData] = useState<CampaignCreate>({
    name: '',
    description: '',
    organization_id: '',
    fileName: 'motorcycle_dealers',
    totalRecords: 500,
    url: 'https://app.apollo.io/#/people?contactEmailStatusV2%5B%5D=verified&contactEmailExcludeCatchAll=true&personTitles%5B%5D=CEO&personTitles%5B%5D=Founder&personTitles%5B%5D=sales%20manager&personTitles%5B%5D=chief%20sales%20officer&personLocations%5B%5D=United%20States&sortAscending=false&sortByField=recommendations_score&page=1&qOrganizationKeywordTags%5B%5D=motorcycle%20dealership&qOrganizationKeywordTags%5B%5D=harley%20davidson&qOrganizationKeywordTags%5B%5D=motorcycle&qOrganizationKeywordTags%5B%5D=carsports&includedOrganizationKeywordFields%5B%5D=tags&includedOrganizationKeywordFields%5B%5D=name&personNotTitles%5B%5D=assistant%20sales%20manager',
  });
  const [formErrors, setFormErrors] = useState<FormErrors>({});
  const [createLoading, setCreateLoading] = useState(false);

  useEffect(() => {
    fetchCampaigns();
    fetchOrganizations();
  }, [currentPage, selectedOrganization, selectedStatus]);

  const fetchOrganizations = async () => {
    setOrgsLoading(true);
    setOrgsError(null);
    try {
      const response = await OrganizationService.getOrganizations();
      setOrganizations(response.data);
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

  const fetchCampaigns = async () => {
    setLoading(true);
    setError(null);
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

      const response = await campaignService.getCampaigns(params);
      setCampaigns(response.data.campaigns);
      setTotalPages(response.data.pages);
      setTotalCampaigns(response.data.total);
      setShowCreateForm(response.data.campaigns.length === 0 && currentPage === 1);
    } catch (err: any) {
      console.error('Error fetching campaigns:', err);
      setError(err.message);
      setCampaigns([]);
      setShowCreateForm(true);
    } finally {
      setLoading(false);
    }
  };

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

    setCreateLoading(true);
    try {
      const response = await campaignService.createCampaign(formData);
      toast.success('Campaign created successfully!');
      // Redirect to the campaign detail page
      navigate(`/campaigns/${response.data.id}`);
    } catch (err: any) {
      console.error('Error creating campaign:', err);
      toast.error(err.message || 'Failed to create campaign');
    } finally {
      setCreateLoading(false);
    }
  };

  const handleSearch = (value: string) => {
    setSearchTerm(value);
    setCurrentPage(1); // Reset to first page when searching
  };

  const handleOrganizationFilter = (value: string) => {
    setSelectedOrganization(value);
    setCurrentPage(1); // Reset to first page when filtering
  };

  const handleStatusFilter = (value: string) => {
    setSelectedStatus(value);
    setCurrentPage(1); // Reset to first page when filtering
  };

  const resetFilters = () => {
    setSearchTerm('');
    setSelectedOrganization('');
    setSelectedStatus('');
    setCurrentPage(1);
  };

  const filteredCampaigns = campaigns.filter(campaign => {
    const matchesSearch = !searchTerm || 
      campaign.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      (campaign.description?.toLowerCase().includes(searchTerm.toLowerCase()));
    return matchesSearch;
  });

  const renderPagination = () => {
    if (totalPages <= 1) return null;

    return (
      <div className="flex items-center justify-between mt-6">
        <div className="text-sm text-gray-500 dark:text-gray-400">
          Showing {((currentPage - 1) * 10) + 1} to {Math.min(currentPage * 10, totalCampaigns)} of {totalCampaigns} campaigns
        </div>
        <div className="flex items-center space-x-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setCurrentPage(prev => Math.max(1, prev - 1))}
            disabled={currentPage === 1}
          >
            Previous
          </Button>
          <span className="text-sm text-gray-500 dark:text-gray-400">
            Page {currentPage} of {totalPages}
          </span>
          <Button
            variant="outline"
            size="sm"
            onClick={() => setCurrentPage(prev => Math.min(totalPages, prev + 1))}
            disabled={currentPage === totalPages}
          >
            Next
          </Button>
        </div>
      </div>
    );
  };

  const renderCreateForm = () => (
    <div className="rounded-2xl border border-gray-200 bg-white dark:border-gray-800 dark:bg-white/[0.03] max-w-2xl mx-auto mb-8">
      <div className="px-6 py-5">
        <h3 className="text-base font-medium text-gray-800 dark:text-white/90">Create Campaign</h3>
      </div>
      <form onSubmit={handleCreate} className="p-4 border-t border-gray-100 dark:border-gray-800 sm:p-6 space-y-6">
        <div>
          <Label htmlFor="organization_id">Organization</Label>
          {orgsLoading ? (
            <div className="text-gray-400">Loading organizations...</div>
          ) : orgsError ? (
            <div className="text-red-500">{orgsError}</div>
          ) : organizations.length === 0 ? (
            <div className="text-gray-400">No organizations available. Please create an organization first.</div>
          ) : (
            <Select
              options={organizations.map((org) => ({ value: org.id, label: org.name }))}
              placeholder="Select an organization"
              onChange={(value: string) => handleChange({ target: { name: 'organization_id', value } } as any)}
              defaultValue={formData.organization_id}
              className={formErrors.organization_id ? 'border-error-500 focus:border-error-300 focus:ring-error-500/10 dark:border-error-500 dark:focus:border-error-800' : ''}
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
            disabled={createLoading}
            error={!!formErrors.name}
            hint={formErrors.name}
          />
        </div>
        <div>
          <Label htmlFor="description">Description</Label>
          <TextArea
            value={formData.description || ''}
            onChange={(value: string) => handleChange({ target: { name: 'description', value } } as any)}
            disabled={createLoading}
            error={!!formErrors.description}
            hint={formErrors.description}
            rows={6}
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
            error={!!formErrors.totalRecords}
            hint={formErrors.totalRecords}
          />
        </div>
        <div>
          <Label htmlFor="url">URL</Label>
          <TextArea
            value={formData.url}
            onChange={(value: string) => handleChange({ target: { name: 'url', value } } as any)}
            disabled={createLoading}
            error={!!formErrors.url}
            hint={formErrors.url}
            rows={3}
          />
        </div>
        <Button
          variant="primary"
          disabled={createLoading || !formData.name.trim() || !formData.description?.trim() || !formData.organization_id || !formData.fileName.trim() || !formData.totalRecords || !formData.url.trim()}
          className="w-full"
        >
          {createLoading ? 'Creating...' : 'Create Campaign'}
        </Button>
      </form>
    </div>
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

          {/* Search and Filter Controls */}
          {campaigns.length > 0 && (
            <div className="mb-6 space-y-4 md:space-y-0 md:flex md:items-end md:space-x-4">
              <div className="flex-1">
                <Label htmlFor="search">Search Campaigns</Label>
                <Input
                  id="search"
                  type="text"
                  placeholder="Search by name or description..."
                  value={searchTerm}
                  onChange={(e) => handleSearch(e.target.value)}
                />
              </div>
              <div className="w-full md:w-48">
                <Label htmlFor="org-filter">Filter by Organization</Label>
                <Select
                  options={[
                    { value: '', label: 'All Organizations' },
                    ...organizations.map(org => ({ value: org.id, label: org.name }))
                  ]}
                  defaultValue={selectedOrganization}
                  onChange={handleOrganizationFilter}
                  placeholder="All Organizations"
                />
              </div>
              <div className="w-full md:w-48">
                <Label htmlFor="status-filter">Filter by Status</Label>
                <Select
                  options={[
                    { value: '', label: 'All Statuses' },
                    { value: CampaignStatus.CREATED, label: 'Created' },
                    { value: CampaignStatus.RUNNING, label: 'Running' },
                    { value: CampaignStatus.COMPLETED, label: 'Completed' },
                    { value: CampaignStatus.FAILED, label: 'Failed' },
                  ]}
                  defaultValue={selectedStatus}
                  onChange={handleStatusFilter}
                  placeholder="All Statuses"
                />
              </div>
              {(searchTerm || selectedOrganization || selectedStatus) && (
                <Button
                  variant="outline"
                  onClick={resetFilters}
                >
                  Clear Filters
                </Button>
              )}
            </div>
          )}

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
                              Organization
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
                          {filteredCampaigns.map((campaign) => {
                            const organization = organizations.find(org => org.id === campaign.organization_id);
                            return (
                              <TableRow key={campaign.id}>
                                <TableCell className="px-5 py-4 sm:px-6 text-start">
                                  <Link
                                    to={`/campaigns/${campaign.id}`}
                                    className="text-blue-400 hover:text-blue-300 hover:underline font-medium"
                                  >
                                    {campaign.name}
                                  </Link>
                                </TableCell>
                                <TableCell className="px-4 py-3 text-gray-500 text-start text-theme-sm dark:text-gray-400">
                                  {campaign.description || '-'}
                                </TableCell>
                                <TableCell className="px-4 py-3 text-gray-500 text-start text-theme-sm dark:text-gray-400">
                                  {organization?.name || 'Unknown'}
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
                                  {campaign.status_error && (
                                    <div className="text-xs text-red-400 mt-1">
                                      {campaign.status_error}
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
                            );
                          })}
                        </TableBody>
                      </Table>
                    </div>
                  </div>
                  {renderPagination()}
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
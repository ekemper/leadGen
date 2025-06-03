import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { OrganizationService } from '../services/organizationService';
import { OrganizationResponse, OrganizationCreate } from '../types/organization';
import { toast } from 'react-toastify';
import Input from '../components/form/input/InputField';
import TextArea from '../components/form/input/TextArea';
import Label from '../components/form/Label';
import Button from '../components/ui/button/Button';
import PageBreadcrumb from '../components/common/PageBreadCrumb';
import ComponentCard from '../components/common/ComponentCard';
import PageMeta from '../components/common/PageMeta';
import {
  Table,
  TableBody,
  TableCell,
  TableHeader,
  TableRow,
} from '../components/ui/table';

interface FormErrors {
  name?: string;
  description?: string;
}

const OrganizationsList: React.FC = () => {
  const [orgs, setOrgs] = useState<OrganizationResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [createName, setCreateName] = useState('');
  const [createDescription, setCreateDescription] = useState('');
  const [createError, setCreateError] = useState<string | null>(null);
  const [createLoading, setCreateLoading] = useState(false);
  const [formErrors, setFormErrors] = useState<FormErrors>({});
  const [showCreateForm, setShowCreateForm] = useState(false);
  
  // Search and pagination state
  const [searchTerm, setSearchTerm] = useState('');
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [totalCount, setTotalCount] = useState(0);
  const itemsPerPage = 10;

  useEffect(() => {
    fetchOrgs();
  }, [currentPage, searchTerm]);

  const validateForm = (): boolean => {
    const errors: FormErrors = {};
    
    if (!createName.trim()) {
      errors.name = 'Name is required';
    } else if (createName.trim().length < 3) {
      errors.name = 'Name must be at least 3 characters';
    }
    
    if (!createDescription.trim()) {
      errors.description = 'Description is required';
    }

    setFormErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const fetchOrgs = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await OrganizationService.getOrganizations({
        page: currentPage,
        limit: itemsPerPage,
        search: searchTerm || undefined,
      });
      setOrgs(response.data);
      setTotalPages(Math.ceil(response.meta.total / itemsPerPage));
      setTotalCount(response.meta.total);
      setShowCreateForm(response.data.length === 0 && !searchTerm);
    } catch (err: any) {
      setError(err.message);
      toast.error(`Failed to load organizations: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = (value: string) => {
    setSearchTerm(value);
    setCurrentPage(1); // Reset to first page when searching
  };

  const handlePageChange = (page: number) => {
    setCurrentPage(page);
  };

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!validateForm()) {
      return;
    }

    setCreateError(null);
    setCreateLoading(true);
    try {
      const createData: OrganizationCreate = {
        name: createName.trim(),
        description: createDescription.trim(),
      };
      
      await OrganizationService.createOrganization(createData);
      setCreateName('');
      setCreateDescription('');
      setFormErrors({});
      setShowCreateForm(false);
      toast.success('Organization created successfully!');
      fetchOrgs();
    } catch (err: any) {
      setCreateError(err.message);
      toast.error(`Failed to create organization: ${err.message}`);
    } finally {
      setCreateLoading(false);
    }
  };

  const renderCreateForm = () => (
    <form onSubmit={handleCreate} className="space-y-4 mb-8">
      <div>
        <Label htmlFor="name">Name</Label>
        <Input
          id="name"
          type="text"
          value={createName}
          onChange={(e) => setCreateName(e.target.value)}
          disabled={createLoading}
          error={!!formErrors.name}
          hint={formErrors.name}
        />
      </div>
      <div>
        <Label htmlFor="description">Description</Label>
        <TextArea
          value={createDescription}
          onChange={(value) => setCreateDescription(value)}
          rows={3}
          disabled={createLoading}
          error={!!formErrors.description}
          hint={formErrors.description}
        />
      </div>
      {createError && <div className="text-red-500">{createError}</div>}
      <Button
        variant="primary"
        disabled={createLoading || !createName.trim() || !createDescription.trim()}
      >
        {createLoading ? 'Creating...' : 'Create Organization'}
      </Button>
    </form>
  );

  // Ensure orgs is always an array
  const safeOrgs = Array.isArray(orgs) ? orgs : [];

  return (
    <>
      <PageMeta
        title="Organizations | LeadGen"
        description="Manage your organizations"
      />
      <PageBreadcrumb pageTitle="Organizations" />
      <div className="space-y-5 sm:space-y-6">
        <ComponentCard title="Organizations">
          <div className="flex justify-between items-center mb-4">
            <div className="flex items-center gap-4">
              {safeOrgs.length > 0 && (
                <Button
                  variant="primary"
                  onClick={() => setShowCreateForm(!showCreateForm)}
                >
                  {showCreateForm ? 'Cancel' : 'Create Organization'}
                </Button>
              )}
              {safeOrgs.length > 0 && (
                <div className="flex items-center gap-2">
                  <Input
                    type="text"
                    placeholder="Search organizations..."
                    value={searchTerm}
                    onChange={(e) => handleSearch(e.target.value)}
                    className="w-64"
                  />
                  {searchTerm && (
                    <Button
                      variant="outline"
                      onClick={() => handleSearch('')}
                    >
                      Clear
                    </Button>
                  )}
                </div>
              )}
            </div>
            {totalCount > 0 && (
              <div className="text-sm text-gray-500">
                Showing {((currentPage - 1) * itemsPerPage) + 1} to {Math.min(currentPage * itemsPerPage, totalCount)} of {totalCount} organizations
              </div>
            )}
          </div>

          {loading ? (
            <div className="text-gray-400">Loading organizations...</div>
          ) : error ? (
            <div className="text-red-500">{error}</div>
          ) : (
            <>
              {safeOrgs.length === 0 ? (
                <div className="text-center">
                  {searchTerm ? (
                    <>
                      <h2 className="text-xl text-gray-400 mb-4">No organizations found for "{searchTerm}"</h2>
                      <Button
                        variant="outline"
                        onClick={() => handleSearch('')}
                      >
                        Clear Search
                      </Button>
                    </>
                  ) : (
                    <>
                      <h2 className="text-xl text-gray-400 mb-8">There are no organizations yet - please create one!</h2>
                      {renderCreateForm()}
                    </>
                  )}
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
                              Created
                            </TableCell>
                          </TableRow>
                        </TableHeader>
                        <TableBody className="divide-y divide-gray-100 dark:divide-white/[0.05]">
                          {safeOrgs.map((org) => (
                            <TableRow key={org.id}>
                              <TableCell className="px-5 py-4 sm:px-6 text-start">
                                <Link to={`/organizations/${org.id}`} className="font-medium text-black dark:text-white hover:text-blue-500 dark:hover:text-blue-400">
                                  {org.name}
                                </Link>
                              </TableCell>
                              <TableCell className="px-4 py-3 text-gray-500 text-start text-theme-sm dark:text-gray-400">
                                {org.description ? (
                                  <div className="max-w-md whitespace-pre-wrap break-words">
                                    {org.description.length > 100 
                                      ? `${org.description.substring(0, 100)}...` 
                                      : org.description}
                                  </div>
                                ) : (
                                  <span className="text-gray-400">(No description)</span>
                                )}
                              </TableCell>
                              <TableCell className="px-4 py-3 text-gray-500 text-start text-theme-sm dark:text-gray-400">
                                {new Date(org.created_at).toLocaleDateString()}
                              </TableCell>
                            </TableRow>
                          ))}
                        </TableBody>
                      </Table>
                    </div>
                  </div>
                  
                  {/* Pagination */}
                  {totalPages > 1 && (
                    <div className="flex justify-center items-center gap-2 mt-6">
                      <Button
                        variant="outline"
                        onClick={() => handlePageChange(currentPage - 1)}
                        disabled={currentPage === 1}
                      >
                        Previous
                      </Button>
                      
                      <div className="flex gap-1">
                        {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                          let pageNum;
                          if (totalPages <= 5) {
                            pageNum = i + 1;
                          } else if (currentPage <= 3) {
                            pageNum = i + 1;
                          } else if (currentPage >= totalPages - 2) {
                            pageNum = totalPages - 4 + i;
                          } else {
                            pageNum = currentPage - 2 + i;
                          }
                          
                          return (
                            <Button
                              key={pageNum}
                              variant={currentPage === pageNum ? "primary" : "outline"}
                              onClick={() => handlePageChange(pageNum)}
                              className="w-10 h-10"
                            >
                              {pageNum}
                            </Button>
                          );
                        })}
                      </div>
                      
                      <Button
                        variant="outline"
                        onClick={() => handlePageChange(currentPage + 1)}
                        disabled={currentPage === totalPages}
                      >
                        Next
                      </Button>
                    </div>
                  )}
                </>
              )}
            </>
          )}
        </ComponentCard>
      </div>
    </>
  );
};

export default OrganizationsList;
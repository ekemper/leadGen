import { api } from '../config/api';
import { 
  OrganizationResponse, 
  OrganizationCreate, 
  OrganizationUpdate 
} from '../types/organization';
import { PaginatedResponse, ListParams } from '../types/api';

export interface OrganizationFilters extends ListParams {
  search?: string;
}

export class OrganizationService {
  /**
   * Get list of organizations with optional filtering and pagination
   */
  static async getOrganizations(filters?: OrganizationFilters): Promise<PaginatedResponse<OrganizationResponse>> {
    const params = new URLSearchParams();
    
    if (filters?.page) params.append('page', filters.page.toString());
    if (filters?.limit) params.append('limit', filters.limit.toString());
    if (filters?.search) params.append('search', filters.search);
    if (filters?.sort_by) params.append('sort_by', filters.sort_by);
    if (filters?.sort_order) params.append('sort_order', filters.sort_order);

    const queryString = params.toString();
    const endpoint = queryString ? `/organizations?${queryString}` : '/organizations';
    
    return await api.get(endpoint);
  }

  /**
   * Get a specific organization by ID
   */
  static async getOrganization(id: string): Promise<OrganizationResponse> {
    return await api.get(`/organizations/${id}`);
  }

  /**
   * Create a new organization
   */
  static async createOrganization(data: OrganizationCreate): Promise<OrganizationResponse> {
    return await api.post('/organizations', data);
  }

  /**
   * Update an existing organization
   */
  static async updateOrganization(id: string, data: OrganizationUpdate): Promise<OrganizationResponse> {
    return await api.put(`/organizations/${id}`, data);
  }

  /**
   * Delete an organization
   */
  static async deleteOrganization(id: string): Promise<void> {
    await api.delete(`/organizations/${id}`);
  }
} 
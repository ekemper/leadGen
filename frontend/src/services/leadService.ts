import { API_BASE_URL } from '../config/api';
import { 
  LeadCreate, 
  LeadUpdate, 
  LeadResponse, 
  LeadListFilters,
  LeadSearchFilters 
} from '../types/lead';

class LeadService {
  private baseUrl = `${API_BASE_URL}/leads`;

  /**
   * Get authentication token from localStorage
   */
  private getAuthToken(): string | null {
    return localStorage.getItem('token');
  }

  /**
   * Create headers with authentication
   */
  private getHeaders(): HeadersInit {
    const token = this.getAuthToken();
    return {
      'Content-Type': 'application/json',
      ...(token && { Authorization: `Bearer ${token}` }),
    };
  }

  /**
   * Handle API response errors
   */
  private async handleResponse<T>(response: Response): Promise<T> {
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({
        detail: 'An error occurred'
      }));
      throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
    }
    return response.json();
  }

  /**
   * Build URL parameters from filters
   */
  private buildUrlParams(filters: LeadListFilters | LeadSearchFilters): URLSearchParams {
    const params = new URLSearchParams();
    
    if (filters.skip !== undefined) {
      params.append('skip', filters.skip.toString());
    }
    if (filters.limit !== undefined) {
      params.append('limit', filters.limit.toString());
    }
    if (filters.campaign_id) {
      params.append('campaign_id', filters.campaign_id);
    }
    if (filters.email) {
      params.append('email', filters.email);
    }
    if (filters.company) {
      params.append('company', filters.company);
    }

    // Additional search filters if provided
    if ('first_name' in filters && filters.first_name) {
      params.append('first_name', filters.first_name);
    }
    if ('last_name' in filters && filters.last_name) {
      params.append('last_name', filters.last_name);
    }
    if ('title' in filters && filters.title) {
      params.append('title', filters.title);
    }
    if ('has_email' in filters && filters.has_email !== undefined) {
      params.append('has_email', filters.has_email.toString());
    }
    if ('has_verification' in filters && filters.has_verification !== undefined) {
      params.append('has_verification', filters.has_verification.toString());
    }
    if ('has_enrichment' in filters && filters.has_enrichment !== undefined) {
      params.append('has_enrichment', filters.has_enrichment.toString());
    }

    return params;
  }

  /**
   * List leads with optional filtering
   */
  async listLeads(filters: LeadListFilters = {}): Promise<LeadResponse[]> {
    try {
      const params = this.buildUrlParams(filters);
      const url = `${this.baseUrl}${params.toString() ? `?${params.toString()}` : ''}`;
      
      const response = await fetch(url, {
        method: 'GET',
        headers: this.getHeaders(),
      });

      return this.handleResponse<LeadResponse[]>(response);
    } catch (error) {
      console.error('Error listing leads:', error);
      throw error;
    }
  }

  /**
   * Get a specific lead by ID
   */
  async getLead(leadId: string): Promise<LeadResponse> {
    try {
      const response = await fetch(`${this.baseUrl}/${leadId}`, {
        method: 'GET',
        headers: this.getHeaders(),
      });

      return this.handleResponse<LeadResponse>(response);
    } catch (error) {
      console.error(`Error getting lead ${leadId}:`, error);
      throw error;
    }
  }

  /**
   * Create a new lead
   */
  async createLead(leadData: LeadCreate): Promise<LeadResponse> {
    try {
      const response = await fetch(this.baseUrl, {
        method: 'POST',
        headers: this.getHeaders(),
        body: JSON.stringify(leadData),
      });

      return this.handleResponse<LeadResponse>(response);
    } catch (error) {
      console.error('Error creating lead:', error);
      throw error;
    }
  }

  /**
   * Update a lead
   */
  async updateLead(leadId: string, leadData: LeadUpdate): Promise<LeadResponse> {
    try {
      const response = await fetch(`${this.baseUrl}/${leadId}`, {
        method: 'PUT',
        headers: this.getHeaders(),
        body: JSON.stringify(leadData),
      });

      return this.handleResponse<LeadResponse>(response);
    } catch (error) {
      console.error(`Error updating lead ${leadId}:`, error);
      throw error;
    }
  }

  /**
   * Delete a lead
   */
  async deleteLead(leadId: string): Promise<void> {
    try {
      const response = await fetch(`${this.baseUrl}/${leadId}`, {
        method: 'DELETE',
        headers: this.getHeaders(),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({
          detail: 'An error occurred'
        }));
        throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
      }
    } catch (error) {
      console.error(`Error deleting lead ${leadId}:`, error);
      throw error;
    }
  }

  /**
   * Get leads filtered by campaign ID
   */
  async getLeadsByCampaign(campaignId: string, filters: Omit<LeadListFilters, 'campaign_id'> = {}): Promise<LeadResponse[]> {
    return this.listLeads({
      ...filters,
      campaign_id: campaignId
    });
  }

  /**
   * Search leads with advanced filtering
   */
  async searchLeads(searchFilters: LeadSearchFilters): Promise<LeadResponse[]> {
    try {
      const params = this.buildUrlParams(searchFilters);
      const url = `${this.baseUrl}${params.toString() ? `?${params.toString()}` : ''}`;
      
      const response = await fetch(url, {
        method: 'GET',
        headers: this.getHeaders(),
      });

      return this.handleResponse<LeadResponse[]>(response);
    } catch (error) {
      console.error('Error searching leads:', error);
      throw error;
    }
  }

  /**
   * Get leads with email addresses
   */
  async getLeadsWithEmail(campaignId?: string, filters: LeadListFilters = {}): Promise<LeadResponse[]> {
    const allLeads = await this.listLeads({
      ...filters,
      ...(campaignId && { campaign_id: campaignId })
    });
    
    return allLeads.filter(lead => lead.email && lead.email.trim() !== '');
  }

  /**
   * Get leads with verified emails
   */
  async getLeadsWithVerifiedEmail(campaignId?: string, filters: LeadListFilters = {}): Promise<LeadResponse[]> {
    const allLeads = await this.listLeads({
      ...filters,
      ...(campaignId && { campaign_id: campaignId })
    });
    
    return allLeads.filter(lead => 
      lead.email_verification && 
      Object.keys(lead.email_verification).length > 0
    );
  }

  /**
   * Get leads with enrichment data
   */
  async getLeadsWithEnrichment(campaignId?: string, filters: LeadListFilters = {}): Promise<LeadResponse[]> {
    const allLeads = await this.listLeads({
      ...filters,
      ...(campaignId && { campaign_id: campaignId })
    });
    
    return allLeads.filter(lead => 
      lead.enrichment_results && 
      Object.keys(lead.enrichment_results).length > 0
    );
  }

  /**
   * Get leads by company
   */
  async getLeadsByCompany(company: string, filters: Omit<LeadListFilters, 'company'> = {}): Promise<LeadResponse[]> {
    return this.listLeads({
      ...filters,
      company
    });
  }

  /**
   * Get lead statistics for a campaign
   */
  async getLeadStats(campaignId: string): Promise<{
    total: number;
    withEmail: number;
    withVerifiedEmail: number;
    withEnrichment: number;
    withEmailCopy: number;
    withInstantlyRecord: number;
  }> {
    try {
      const leads = await this.getLeadsByCampaign(campaignId);
      
      return {
        total: leads.length,
        withEmail: leads.filter(lead => lead.email && lead.email.trim() !== '').length,
        withVerifiedEmail: leads.filter(lead => 
          lead.email_verification && Object.keys(lead.email_verification).length > 0
        ).length,
        withEnrichment: leads.filter(lead => 
          lead.enrichment_results && Object.keys(lead.enrichment_results).length > 0
        ).length,
        withEmailCopy: leads.filter(lead => 
          lead.email_copy_gen_results && Object.keys(lead.email_copy_gen_results).length > 0
        ).length,
        withInstantlyRecord: leads.filter(lead => 
          lead.instantly_lead_record && Object.keys(lead.instantly_lead_record).length > 0
        ).length,
      };
    } catch (error) {
      console.error(`Error getting lead stats for campaign ${campaignId}:`, error);
      throw error;
    }
  }

  /**
   * Bulk create leads
   */
  async bulkCreateLeads(leadsData: LeadCreate[]): Promise<LeadResponse[]> {
    try {
      const promises = leadsData.map(leadData => this.createLead(leadData));
      const results = await Promise.allSettled(promises);
      
      const successfulLeads: LeadResponse[] = [];
      const errors: Error[] = [];
      
      results.forEach((result, index) => {
        if (result.status === 'fulfilled') {
          successfulLeads.push(result.value);
        } else {
          errors.push(new Error(`Failed to create lead ${index + 1}: ${result.reason}`));
        }
      });
      
      if (errors.length > 0) {
        console.warn('Some leads failed to create:', errors);
      }
      
      return successfulLeads;
    } catch (error) {
      console.error('Error bulk creating leads:', error);
      throw error;
    }
  }
}

export default new LeadService(); 
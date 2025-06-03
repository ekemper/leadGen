import { api } from '../config/api';
import { 
  CampaignResponse, 
  CampaignCreate, 
  CampaignUpdate, 
  CampaignStart,
  CampaignStatusResponse,
  CampaignLeadStats,
  InstantlyAnalytics
} from '../types/campaign';

export interface CampaignsListResponse {
  status: string;
  data: {
    campaigns: CampaignResponse[];
    total: number;
    page: number;
    per_page: number;
    pages: number;
  };
}

export interface CampaignDetailResponse {
  status: string;
  data: CampaignResponse;
}

export interface CampaignCreateResponse {
  status: string;
  data: CampaignResponse;
}

export interface CampaignUpdateResponse {
  status: string;
  data: CampaignResponse;
}

export interface CampaignDeleteResponse {
  status: string;
  message: string;
}

export interface CampaignStartResponse {
  status: string;
  data: CampaignResponse;
}

export interface CampaignStatsResponse {
  status: string;
  data: CampaignLeadStats;
}

export interface InstantlyAnalyticsResponse {
  status: string;
  data: InstantlyAnalytics;
}

export interface CampaignListParams {
  organization_id?: string;
  page?: number;
  per_page?: number;
  status?: string;
}

class CampaignService {
  /**
   * Get list of campaigns with optional filtering
   */
  async getCampaigns(params?: CampaignListParams): Promise<CampaignsListResponse> {
    return await api.get('/campaigns', params);
  }

  /**
   * Get a specific campaign by ID
   */
  async getCampaign(id: string): Promise<CampaignDetailResponse> {
    return await api.get(`/campaigns/${id}`);
  }

  /**
   * Create a new campaign
   */
  async createCampaign(campaignData: CampaignCreate): Promise<CampaignCreateResponse> {
    return await api.post('/campaigns', campaignData);
  }

  /**
   * Update an existing campaign
   */
  async updateCampaign(id: string, campaignData: CampaignUpdate): Promise<CampaignUpdateResponse> {
    return await api.put(`/campaigns/${id}`, campaignData);
  }

  /**
   * Delete a campaign
   */
  async deleteCampaign(id: string): Promise<CampaignDeleteResponse> {
    return await api.delete(`/campaigns/${id}`);
  }

  /**
   * Start campaign processing
   */
  async startCampaign(id: string, startData?: CampaignStart): Promise<CampaignStartResponse> {
    return await api.post(`/campaigns/${id}/start`, startData || {});
  }

  /**
   * Get campaign status
   */
  async getCampaignStatus(id: string): Promise<{ status: string; data: CampaignStatusResponse }> {
    return await api.get(`/campaigns/${id}/status`);
  }

  /**
   * Get detailed campaign information including stats
   */
  async getCampaignDetails(id: string): Promise<CampaignDetailResponse> {
    return await api.get(`/campaigns/${id}/details`);
  }

  /**
   * Get campaign lead statistics
   */
  async getCampaignStats(id: string): Promise<CampaignStatsResponse> {
    return await api.get(`/campaigns/${id}/leads/stats`);
  }

  /**
   * Get Instantly analytics for campaign
   */
  async getInstantlyAnalytics(id: string): Promise<InstantlyAnalyticsResponse> {
    return await api.get(`/campaigns/${id}/instantly/analytics`);
  }

  /**
   * Poll campaign status - useful for monitoring running campaigns
   */
  pollCampaignStatus(
    id: string, 
    callback: (status: CampaignStatusResponse) => void,
    errorCallback: (error: Error) => void,
    interval: number = 5000
  ): () => void {
    const pollInterval = setInterval(async () => {
      try {
        const response = await this.getCampaignStatus(id);
        callback(response.data);
      } catch (error) {
        errorCallback(error as Error);
      }
    }, interval);

    // Return a cleanup function
    return () => clearInterval(pollInterval);
  }

  /**
   * Poll campaign stats - useful for monitoring campaign progress
   */
  pollCampaignStats(
    id: string,
    callback: (stats: CampaignLeadStats) => void,
    errorCallback: (error: Error) => void,
    interval: number = 10000
  ): () => void {
    const pollInterval = setInterval(async () => {
      try {
        const response = await this.getCampaignStats(id);
        callback(response.data);
      } catch (error) {
        errorCallback(error as Error);
      }
    }, interval);

    // Return a cleanup function
    return () => clearInterval(pollInterval);
  }
}

export const campaignService = new CampaignService();
export default campaignService; 
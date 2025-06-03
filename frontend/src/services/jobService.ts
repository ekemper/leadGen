import { API_BASE_URL } from '../config/api';
import { 
  JobCreate, 
  JobUpdate, 
  JobResponse, 
  JobListFilters,
  JobStatus 
} from '../types/job';

class JobService {
  private baseUrl = `${API_BASE_URL}/jobs`;

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
   * List jobs with optional filtering
   */
  async listJobs(filters: JobListFilters = {}): Promise<JobResponse[]> {
    try {
      const params = new URLSearchParams();
      
      if (filters.skip !== undefined) {
        params.append('skip', filters.skip.toString());
      }
      if (filters.limit !== undefined) {
        params.append('limit', filters.limit.toString());
      }
      if (filters.status) {
        params.append('status', filters.status);
      }

      const url = `${this.baseUrl}${params.toString() ? `?${params.toString()}` : ''}`;
      
      const response = await fetch(url, {
        method: 'GET',
        headers: this.getHeaders(),
      });

      return this.handleResponse<JobResponse[]>(response);
    } catch (error) {
      console.error('Error listing jobs:', error);
      throw error;
    }
  }

  /**
   * Get a specific job by ID
   */
  async getJob(jobId: number): Promise<JobResponse> {
    try {
      const response = await fetch(`${this.baseUrl}/${jobId}`, {
        method: 'GET',
        headers: this.getHeaders(),
      });

      return this.handleResponse<JobResponse>(response);
    } catch (error) {
      console.error(`Error getting job ${jobId}:`, error);
      throw error;
    }
  }

  /**
   * Create a new job
   */
  async createJob(jobData: JobCreate): Promise<JobResponse> {
    try {
      const response = await fetch(this.baseUrl, {
        method: 'POST',
        headers: this.getHeaders(),
        body: JSON.stringify(jobData),
      });

      return this.handleResponse<JobResponse>(response);
    } catch (error) {
      console.error('Error creating job:', error);
      throw error;
    }
  }

  /**
   * Update a job
   */
  async updateJob(jobId: number, jobData: JobUpdate): Promise<JobResponse> {
    try {
      const response = await fetch(`${this.baseUrl}/${jobId}`, {
        method: 'PUT',
        headers: this.getHeaders(),
        body: JSON.stringify(jobData),
      });

      return this.handleResponse<JobResponse>(response);
    } catch (error) {
      console.error(`Error updating job ${jobId}:`, error);
      throw error;
    }
  }

  /**
   * Delete a job
   */
  async deleteJob(jobId: number): Promise<void> {
    try {
      const response = await fetch(`${this.baseUrl}/${jobId}`, {
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
      console.error(`Error deleting job ${jobId}:`, error);
      throw error;
    }
  }

  /**
   * Get jobs filtered by campaign ID
   */
  async getJobsByCampaign(campaignId: string, filters: Omit<JobListFilters, 'campaign_id'> = {}): Promise<JobResponse[]> {
    return this.listJobs({
      ...filters,
      campaign_id: campaignId
    });
  }

  /**
   * Get jobs by status
   */
  async getJobsByStatus(status: JobStatus, filters: Omit<JobListFilters, 'status'> = {}): Promise<JobResponse[]> {
    return this.listJobs({
      ...filters,
      status
    });
  }

  /**
   * Get running jobs (pending or processing)
   */
  async getRunningJobs(filters: JobListFilters = {}): Promise<JobResponse[]> {
    const allJobs = await this.listJobs(filters);
    return allJobs.filter(job => 
      job.status === JobStatus.PENDING || job.status === JobStatus.PROCESSING
    );
  }

  /**
   * Get completed jobs
   */
  async getCompletedJobs(filters: JobListFilters = {}): Promise<JobResponse[]> {
    return this.getJobsByStatus(JobStatus.COMPLETED, filters);
  }

  /**
   * Get failed jobs
   */
  async getFailedJobs(filters: JobListFilters = {}): Promise<JobResponse[]> {
    return this.getJobsByStatus(JobStatus.FAILED, filters);
  }
}

export default new JobService(); 
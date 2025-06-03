// Job Types based on backend schemas

export enum JobStatus {
  PENDING = 'pending',
  PROCESSING = 'processing',
  COMPLETED = 'completed',
  FAILED = 'failed',
  CANCELLED = 'cancelled',
  PAUSED = 'paused'
}

export enum JobType {
  FETCH_LEADS = 'FETCH_LEADS',
  ENRICH_LEAD = 'ENRICH_LEAD',
  CLEANUP_CAMPAIGN = 'CLEANUP_CAMPAIGN'
}

export interface JobBase {
  name: string;
  description?: string;
}

export interface JobCreate extends JobBase {}

export interface JobUpdate {
  status?: JobStatus;
  result?: string;
  error?: string;
}

export interface JobResponse extends JobBase {
  id: number;
  task_id: string;
  job_type: JobType;
  status: JobStatus;
  result?: string;
  error?: string;
  campaign_id?: string;
  created_at: string;
  updated_at?: string;
  completed_at?: string;
}

// Filter interfaces for API queries
export interface JobListFilters {
  skip?: number;
  limit?: number;
  status?: JobStatus;
  campaign_id?: string;
}

// API Response interfaces
export interface JobListResponse {
  jobs: JobResponse[];
  total?: number;
} 
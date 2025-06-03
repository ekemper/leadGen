// Lead Types based on backend schemas

export interface LeadBase {
  campaign_id: string;
  first_name?: string;
  last_name?: string;
  email?: string;
  phone?: string;
  company?: string;
  title?: string;
  linkedin_url?: string;
  source_url?: string;
  raw_data?: Record<string, any>;
  email_verification?: Record<string, any>;
  enrichment_results?: Record<string, any>;
  enrichment_job_id?: string;
  email_copy_gen_results?: Record<string, any>;
  instantly_lead_record?: Record<string, any>;
}

export interface LeadCreate extends LeadBase {}

export interface LeadUpdate {
  first_name?: string;
  last_name?: string;
  email?: string;
  phone?: string;
  company?: string;
  title?: string;
  linkedin_url?: string;
  source_url?: string;
  raw_data?: Record<string, any>;
  email_verification?: Record<string, any>;
  enrichment_results?: Record<string, any>;
  enrichment_job_id?: string;
  email_copy_gen_results?: Record<string, any>;
  instantly_lead_record?: Record<string, any>;
}

export interface LeadResponse extends LeadBase {
  id: string;
  created_at: string;
  updated_at: string;
}

// Filter interfaces for API queries
export interface LeadListFilters {
  skip?: number;
  limit?: number;
  campaign_id?: string;
  email?: string;
  company?: string;
}

// API Response interfaces
export interface LeadListResponse {
  leads: LeadResponse[];
  total?: number;
}

// Search and filtering options
export interface LeadSearchFilters extends LeadListFilters {
  first_name?: string;
  last_name?: string;
  title?: string;
  has_email?: boolean;
  has_verification?: boolean;
  has_enrichment?: boolean;
} 
// Campaign Types based on backend schemas

export enum CampaignStatus {
  CREATED = "created",
  RUNNING = "running", 
  COMPLETED = "completed",
  FAILED = "failed"
}

export interface CampaignBase {
  name: string;
  description?: string;
  organization_id: string;
  fileName: string;
  totalRecords: number;
  url: string;
}

export interface CampaignCreate extends CampaignBase {}

export interface CampaignUpdate {
  name?: string;
  description?: string;
  status?: CampaignStatus;
  status_message?: string;
  status_error?: string;
  organization_id?: string;
  fileName?: string;
  totalRecords?: number;
  url?: string;
  instantly_campaign_id?: string;
}

export interface CampaignInDB extends CampaignBase {
  id: string;
  status: CampaignStatus;
  status_message?: string;
  status_error?: string;
  created_at: string;
  updated_at: string;
  completed_at?: string;
  failed_at?: string;
  instantly_campaign_id?: string;
}

export interface CampaignResponse extends CampaignInDB {
  valid_transitions: CampaignStatus[];
}

export interface CampaignStart {
  status_message?: string;
}

export interface CampaignStatusUpdate {
  status: CampaignStatus;
  status_message?: string;
  status_error?: string;
  instantly_campaign_id?: string;
}

export interface CampaignStatusResponse {
  campaign_id: string;
  campaign_name: string;
  campaign_status: CampaignStatus;
}

// Legacy interface for backward compatibility
export interface Campaign extends CampaignResponse {
  job_ids?: {
    fetch_leads?: string;
    email_verification?: string;
    enrich_lead?: string;
    email_copy_generation?: string;
  };
}

// Legacy interfaces for backward compatibility
export interface CampaignStartParams {
  count: number;
  searchUrl: string;
}

export interface CampaignLeadStats {
  total_leads_fetched: number;
  leads_with_email: number;
  leads_with_verified_email: number;
  leads_with_enrichment: number;
  leads_with_email_copy: number;
  leads_with_instantly_record: number;
  error_message: string | null;
}

export interface InstantlyAnalytics {
  leads_count: number | null;
  contacted_count: number | null;
  emails_sent_count: number | null;
  open_count: number | null;
  link_click_count: number | null;
  reply_count: number | null;
  bounced_count: number | null;
  unsubscribed_count: number | null;
  completed_count: number | null;
  new_leads_contacted_count: number | null;
  total_opportunities: number | null;
  campaign_name: string | null;
  campaign_id: string | null;
  campaign_status: string | null;
  campaign_is_evergreen: boolean | null;
  error?: string;
} 
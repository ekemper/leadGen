export enum CampaignStatus {
  CREATED = 'CREATED',
  FETCHING_LEADS = 'FETCHING_LEADS',
  VERIFYING_EMAILS = 'VERIFYING_EMAILS',
  ENRICHING_LEADS = 'ENRICHING_LEADS',
  GENERATING_EMAILS = 'GENERATING_EMAILS',
  COMPLETED = 'COMPLETED',
  FAILED = 'FAILED'
}

export interface Campaign {
  id: string;
  name: string;
  status: CampaignStatus;
  status_error?: string;
  created_at: string;
  updated_at: string;
  job_ids?: {
    fetch_leads?: string;
    email_verification?: string;
    enrich_leads?: string;
    email_copy_generation?: string;
  };
  fileName: string;
  totalRecords: number;
  url: string;
  status_message?: string;
  description?: string;
}

export interface CampaignStartParams {
  count: number; // 1-1000
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
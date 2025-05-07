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
    verify_emails?: string;
    enrich_leads?: string;
    generate_emails?: string;
  };
}

export interface CampaignStartParams {
  count: number;
  excludeGuessedEmails: boolean;
  excludeNoEmails: boolean;
  getEmails: boolean;
  searchUrl: string;
} 
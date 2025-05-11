from enum import Enum

class CampaignStatus(str, Enum):
    """Enum for campaign status values."""
    CREATED = 'created'
    FETCHING_LEADS = 'fetching_leads'
    LEADS_FETCHED = 'leads_fetched'
    VERIFYING_EMAILS = 'verifying_emails'
    ENRICHING_LEADS = 'enriching_leads'
    GENERATING_EMAILS = 'generating_emails'
    COMPLETED = 'completed'
    FAILED = 'failed' 
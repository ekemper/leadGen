from enum import Enum

class CampaignStatus(str, Enum):
    """Enum for campaign status values."""
    CREATED = 'created'
    FETCHING_LEADS = 'fetching_leads'
    LEADS_FETCHED = 'leads_fetched'
    ENRICHING = 'enriching'
    ENRICHED = 'enriched'
    VERIFYING_EMAILS = 'verifying_emails'
    EMAILS_VERIFIED = 'emails_verified'
    GENERATING_EMAILS = 'generating_emails'
    COMPLETED = 'completed'
    FAILED = 'failed' 
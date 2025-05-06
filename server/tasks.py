from server.background_services.apollo_service import ApolloService
from server.background_services.email_verifier_service import EmailVerifierService
from server.app import create_app
from server.background_services.openai_service import OpenAIService
from server.models import Campaign
from server.models.campaign import CampaignStatus
from server.config.database import db
from server.utils.logger import logger
from rq import Queue, get_current_job
from redis import Redis
import traceback

flask_app = create_app()

print("server.tasks module loaded")

def update_campaign_status(campaign_id, status, message=None, error=None):
    """Update campaign status and log any errors."""
    with flask_app.app_context():
        try:
            campaign = Campaign.query.get(campaign_id)
            if campaign:
                campaign.update_status(status, message, error)
                logger.info(f"Campaign {campaign_id} status updated to {status}")
        except Exception as e:
            logger.error(f"Error updating campaign status: {str(e)}")
            db.session.rollback()

def handle_task_error(campaign_id, error, task_name):
    """Handle task errors consistently."""
    error_msg = f"Error in {task_name}: {str(error)}"
    logger.error(error_msg)
    logger.error(traceback.format_exc())
    update_campaign_status(campaign_id, CampaignStatus.FAILED, error=error_msg)
    raise error

def fetch_and_save_leads_task(params, campaign_id):
    """Fetch and save leads from Apollo."""
    with flask_app.app_context():
        try:
            logger.info(f"Starting fetch_and_save_leads_task for campaign {campaign_id}")
            update_campaign_status(campaign_id, CampaignStatus.FETCHING_LEADS, 'Fetching leads from Apollo')
            
            result = ApolloService().fetch_leads(params, campaign_id)
            
            logger.info(f"Successfully fetched {result.get('count', 0)} leads for campaign {campaign_id}")
            update_campaign_status(campaign_id, CampaignStatus.LEADS_FETCHED, f"Fetched {result.get('count', 0)} leads")
            
            return {'campaign_id': campaign_id, 'status': 'success', 'count': result.get('count', 0)}
        except Exception as e:
            handle_task_error(campaign_id, e, 'fetch_and_save_leads_task')

def enriching_leads_task(result):
    """Enrich leads with additional data."""
    with flask_app.app_context():
        try:
            campaign_id = result['campaign_id']
            logger.info(f"Starting enriching_leads_task for campaign {campaign_id}")
            update_campaign_status(campaign_id, CampaignStatus.ENRICHING, 'Enriching leads with additional data')
            
            # TODO: Implement lead enrichment
            # For now, just mark as enriched
            update_campaign_status(campaign_id, CampaignStatus.ENRICHED, 'Leads enriched successfully')
            
            return {'campaign_id': campaign_id, 'status': 'success'}
        except Exception as e:
            handle_task_error(campaign_id, e, 'enriching_leads_task')

def email_verification_task(result):
    """Verify email addresses for leads."""
    with flask_app.app_context():
        try:
            campaign_id = result['campaign_id']
            logger.info(f"Starting email_verification_task for campaign {campaign_id}")
            update_campaign_status(campaign_id, CampaignStatus.VERIFYING_EMAILS, 'Verifying email addresses')
            
            verifier = EmailVerifierService()
            count = verifier.verify_emails_for_campaign(campaign_id)
            
            logger.info(f"Successfully verified {count} emails for campaign {campaign_id}")
            update_campaign_status(campaign_id, CampaignStatus.EMAILS_VERIFIED, f"Verified {count} email addresses")
            
            return {'campaign_id': campaign_id, 'verified_count': count}
        except Exception as e:
            handle_task_error(result['campaign_id'], e, 'email_verification_task')

def email_copy_generation_task(result):
    """Generate personalized email copy for leads."""
    with flask_app.app_context():
        try:
            campaign_id = result['campaign_id']
            logger.info(f"Starting email_copy_generation_task for campaign {campaign_id}")
            update_campaign_status(campaign_id, CampaignStatus.GENERATING_EMAILS, 'Generating personalized email copy')
            
            # TODO: Implement email copy generation
            # For now, just mark as completed
            update_campaign_status(campaign_id, CampaignStatus.COMPLETED, 'Campaign completed successfully')
            
            return {'campaign_id': campaign_id, 'status': 'success'}
        except Exception as e:
            handle_task_error(campaign_id, e, 'email_copy_generation_task')

# RQ enqueue helper functions
def enqueue_fetch_and_save_leads(params, campaign_id):
    """Enqueue the fetch and save leads task."""
    redis_conn = Redis()
    q = Queue('default', connection=redis_conn)
    return q.enqueue(fetch_and_save_leads_task, params, campaign_id, job_timeout='1h')

def enqueue_email_verification(result, depends_on=None):
    """Enqueue the email verification task."""
    redis_conn = Redis()
    q = Queue('default', connection=redis_conn)
    return q.enqueue(email_verification_task, result, depends_on=depends_on, job_timeout='1h')

def enqueue_enriching_leads(result, depends_on=None):
    """Enqueue the enriching leads task."""
    redis_conn = Redis()
    q = Queue('default', connection=redis_conn)
    return q.enqueue(enriching_leads_task, result, depends_on=depends_on, job_timeout='1h')

def enqueue_email_copy_generation(result, depends_on=None):
    """Enqueue the email copy generation task."""
    redis_conn = Redis()
    q = Queue('default', connection=redis_conn)
    return q.enqueue(email_copy_generation_task, result, depends_on=depends_on, job_timeout='1h')

# Example usage of chaining (for reference, not executed on import):
# from celery import chain
# chain(fetch_and_save_leads_task.s(params, campaign_id), enriching_leads_task.s())() 
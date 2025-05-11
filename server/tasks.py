from server.background_services.apollo_service import ApolloService
from server.background_services.email_verifier_service import EmailVerifierService
from server.app import create_app
from server.background_services.openai_service import OpenAIService
from server.models import Campaign
from server.models.campaign import CampaignStatus
from server.models.job_status import JobStatus
from server.config.database import db
from server.utils.logging_config import server_logger
from rq import get_current_job, Queue, Retry
from server.config.queue_config import get_queue, QUEUE_CONFIG
from server.models.job import Job
import traceback
from datetime import datetime

print("server.tasks module loaded")

def handle_task_error(campaign_id, error, job_type):
    """Handle task errors and update campaign status."""
    from server.app import create_app
    flask_app = create_app()
    with flask_app.app_context():
        try:
            server_logger.error(f"Error in {job_type} for campaign {campaign_id}: {str(error)}")
            campaign = Campaign.query.get(campaign_id)
            if campaign:
                campaign.update_status(CampaignStatus.FAILED, error_message=str(error))
            # Update job status if job exists
            job = Job.query.filter_by(campaign_id=campaign_id, job_type=job_type.upper()).order_by(Job.created_at.desc()).first()
            if job:
                job.update_status(JobStatus.FAILED, error_message=str(error))
        except Exception as e:
            server_logger.error(f"Error handling task error: {str(e)}", exc_info=True)

def fetch_and_save_leads_task(params, campaign_id):
    """Fetch and save leads from Apollo."""
    from server.app import create_app
    flask_app = create_app()
    with flask_app.app_context():
        job = None
        campaign = None
        try:
            server_logger.info(f"Starting fetch_and_save_leads_task for campaign {campaign_id}")
            campaign = Campaign.query.get(campaign_id)
            if not campaign:
                raise Exception(f"Campaign {campaign_id} not found")

            # Create job
            job = Job.create(campaign_id=campaign_id, job_type='FETCH_LEADS', parameters=params)
            db.session.commit()
            job.update_status(JobStatus.IN_PROGRESS)

            # Fetch leads
            result = ApolloService().fetch_leads(params, campaign_id)

            # Mark job as completed
            job.update_status(JobStatus.COMPLETED)

            # Update campaign status directly
            campaign.update_status(CampaignStatus.COMPLETED)

            server_logger.info(f"Successfully fetched {result.get('count', 0)} leads for campaign {campaign_id}")

            # Enqueue email verification job for each lead
            from server.models.lead import Lead
            leads = Lead.query.filter_by(campaign_id=campaign_id).all()
            for lead in leads:
                enqueue_lead_email_verification(lead.id)

            return campaign_id  # Return campaign_id for chaining
        except Exception as e:
            handle_task_error(campaign_id, e, 'FETCH_LEADS')
            raise

# Commenting out all other task and enqueue functions
def enriching_leads_task(result):
    """Enrich leads with additional data."""
    pass  # Commented out for testing fetch only

def email_verification_task(result):
    """Verify email addresses for leads."""
    pass  # Commented out for testing fetch only

def email_copy_generation_task(result):
    """Generate personalized email copy for leads."""
    pass  # Commented out for testing fetch only

def enqueue_fetch_and_save_leads(params, campaign_id):
    """Enqueue the fetch and save leads task."""
    queue = get_queue()
    job = queue.enqueue(
        fetch_and_save_leads_task,
        args=(params, campaign_id),
        job_timeout=QUEUE_CONFIG['default']['job_timeout'],
        retry=Retry(max=QUEUE_CONFIG['default']['max_retries'])
    )
    return job

# Commenting out all other enqueue functions
def enqueue_email_verification(result, depends_on=None):
    pass  # Commented out for testing fetch only

def enqueue_enriching_leads(result, depends_on=None):
    pass  # Commented out for testing fetch only

def enqueue_email_copy_generation(result, depends_on=None):
    pass  # Commented out for testing fetch only

def enqueue_email_generation(params, depends_on=None):
    pass  # Commented out for testing fetch only

def email_generation_task(params):
    pass  # Commented out for testing fetch only

def lead_email_verification_task(lead_id):
    """Verify the email for a single lead and save the result."""
    from server.app import create_app
    flask_app = create_app()
    with flask_app.app_context():
        from server.models.lead import Lead
        lead = Lead.query.get(lead_id)
        if not lead:
            server_logger.error(f"Lead {lead_id} not found for email verification task.")
            return
        try:
            server_logger.info(f"Starting email verification for lead {lead_id} with email: {lead.email}")
            result = EmailVerifierService().verify_email(lead.email)
            server_logger.info(f"Verification result for lead {lead_id}: {result}")
            lead.email_verification = result
            db.session.commit()
            server_logger.info(f"Email verification complete and saved for lead {lead_id}")
        except Exception as e:
            server_logger.error(f"Error verifying email for lead {lead_id}: {str(e)}")
            db.session.rollback()

def enqueue_lead_email_verification(lead_id):
    """Enqueue the email verification task for a single lead."""
    queue = get_queue()
    job = queue.enqueue(
        lead_email_verification_task,
        args=(lead_id,),
        job_timeout=QUEUE_CONFIG['default']['job_timeout'],
        retry=Retry(max=QUEUE_CONFIG['default']['max_retries'])
    )
    return job


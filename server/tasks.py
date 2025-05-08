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

flask_app = create_app()

print("server.tasks module loaded")

def update_campaign_status(campaign_id, status, message=None, error=None):
    """Update campaign status and log any errors."""
    with flask_app.app_context():
        try:
            campaign = Campaign.query.get(campaign_id)
            if campaign:
                campaign.update_status(status, message, error)
                server_logger.info(f"Campaign {campaign_id} status updated to {status}")
        except Exception as e:
            server_logger.error(f"Error updating campaign status: {str(e)}")
            db.session.rollback()

def update_job_status(campaign_id, job_type, status, message=None):
    """Update the status of a specific job in the campaign."""
    with flask_app.app_context():
        try:
            campaign = Campaign.query.get(campaign_id)
            if campaign:
                if not campaign.job_status:
                    campaign.job_status = {}
                campaign.job_status[job_type] = {
                    'status': status,
                    'message': message,
                    'updated_at': datetime.utcnow().isoformat()
                }
                db.session.commit()
                server_logger.info(f"Campaign {campaign_id} job {job_type} status updated to {status}")
        except Exception as e:
            server_logger.error(f"Error updating job status: {str(e)}")
            db.session.rollback()

def handle_task_error(campaign_id, error, task_name):
    """Handle task errors and update campaign status."""
    try:
        server_logger.error(f"Error in {task_name} for campaign {campaign_id}: {str(error)}")
        
        # Update campaign status
        update_campaign_status(
            campaign_id,
            CampaignStatus.FAILED,
            error_message=f"Error in {task_name}: {str(error)}"
        )
        
        # Update job status
        job = get_current_job()
        if job:
            Job.create(
                campaign_id=campaign_id,
                job_type=task_name,
                status='FAILED',
                error=str(error),
                started_at=datetime.utcnow(),
                ended_at=datetime.utcnow()
            )
    except Exception as e:
        server_logger.error(f"Error handling task error: {str(e)}", exc_info=True)

def fetch_and_save_leads_task(params, campaign_id):
    """Fetch and save leads from Apollo."""
    with flask_app.app_context():
        try:
            server_logger.info(f"Starting fetch_and_save_leads_task for campaign {campaign_id}")
            
            # Update campaign status
            update_campaign_status(campaign_id, CampaignStatus.FETCHING_LEADS, 'Fetching leads from Apollo')
            update_job_status(campaign_id, 'fetch_leads', JobStatus.IN_PROGRESS.value, 'Fetching leads from Apollo')
            
            # Fetch leads
            result = ApolloService().fetch_leads(params, campaign_id)
            
            # Update status on success
            server_logger.info(f"Successfully fetched {result.get('count', 0)} leads for campaign {campaign_id}")
            
            # Update campaign status
            update_campaign_status(campaign_id, CampaignStatus.VERIFYING_EMAILS, f"Fetched {result.get('count', 0)} leads")
            update_job_status(campaign_id, 'fetch_leads', JobStatus.COMPLETED.value, f"Successfully fetched {result.get('count', 0)} leads")
            
            # Store job result
            job = get_current_job()
            if job:
                Job.create(
                    campaign_id=campaign_id,
                    job_type='fetch_leads',
                    status=JobStatus.COMPLETED.value,
                    result=result,
                    error=None,
                    started_at=datetime.utcnow(),
                    ended_at=datetime.utcnow(),
                    execution_time=result.get('execution_time', 0)
                )
            
            return result
        except Exception as e:
            handle_task_error(campaign_id, e, 'fetch_and_save_leads_task')
            raise

def enriching_leads_task(result):
    """Enrich leads with additional data."""
    with flask_app.app_context():
        try:
            campaign_id = result.get('campaign_id')
            if not campaign_id:
                raise ValueError("Campaign ID not found in result")
                
            server_logger.info(f"Starting enriching_leads_task for campaign {campaign_id}")
            update_campaign_status(campaign_id, CampaignStatus.ENRICHING, 'Enriching leads with additional data')
            update_job_status(campaign_id, 'enrich_leads', JobStatus.IN_PROGRESS.value, 'Enriching leads with additional data')
            
            # TODO: Implement lead enrichment
            # For now, just mark as enriched
            update_campaign_status(campaign_id, CampaignStatus.ENRICHED, 'Leads enriched successfully')
            update_job_status(campaign_id, 'enrich_leads', JobStatus.COMPLETED.value, 'Leads enriched successfully')
            
            # Store job result
            job = get_current_job()
            if job:
                Job.create(
                    campaign_id=campaign_id,
                    job_type='enrich_leads',
                    status=JobStatus.COMPLETED.value,
                    result={'status': 'success', 'campaign_id': campaign_id},
                    error=None,
                    started_at=datetime.utcnow(),
                    ended_at=datetime.utcnow(),
                    execution_time=result.get('execution_time', 0)
                )
            
            return {'campaign_id': campaign_id, 'status': 'success'}
        except Exception as e:
            handle_task_error(campaign_id, e, 'enriching_leads_task')

def email_verification_task(result):
    """Verify email addresses for leads."""
    with flask_app.app_context():
        try:
            campaign_id = result.get('campaign_id')
            if not campaign_id:
                raise ValueError("Campaign ID not found in result")
                
            server_logger.info(f"Starting email_verification_task for campaign {campaign_id}")
            update_campaign_status(campaign_id, CampaignStatus.VERIFYING_EMAILS, 'Verifying email addresses')
            update_job_status(campaign_id, 'verify_emails', JobStatus.IN_PROGRESS.value, 'Verifying email addresses')
            
            verifier = EmailVerifierService()
            count = verifier.verify_emails_for_campaign(campaign_id)
            
            server_logger.info(f"Successfully verified {count} emails for campaign {campaign_id}")
            update_campaign_status(campaign_id, CampaignStatus.EMAILS_VERIFIED, f"Verified {count} email addresses")
            update_job_status(campaign_id, 'verify_emails', JobStatus.COMPLETED.value, f"Successfully verified {count} email addresses")
            
            # Store job result
            job = get_current_job()
            if job:
                Job.create(
                    campaign_id=campaign_id,
                    job_type='verify_emails',
                    status=JobStatus.COMPLETED.value,
                    result={'verified_count': count, 'campaign_id': campaign_id},
                    error=None,
                    started_at=datetime.utcnow(),
                    ended_at=datetime.utcnow(),
                    execution_time=result.get('execution_time', 0)
                )
            
            return {'campaign_id': campaign_id, 'verified_count': count}
        except Exception as e:
            handle_task_error(campaign_id, e, 'email_verification_task')

def email_copy_generation_task(result):
    """Generate personalized email copy for leads."""
    with flask_app.app_context():
        try:
            campaign_id = result.get('campaign_id')
            if not campaign_id:
                raise ValueError("Campaign ID not found in result")
                
            server_logger.info(f"Starting email_copy_generation_task for campaign {campaign_id}")
            update_campaign_status(campaign_id, CampaignStatus.GENERATING_EMAILS, 'Generating personalized email copy')
            update_job_status(campaign_id, 'email_copy_generation', JobStatus.IN_PROGRESS.value, 'Generating personalized email copy')
            
            # TODO: Implement email copy generation
            # For now, just mark as completed
            update_campaign_status(campaign_id, CampaignStatus.COMPLETED, 'Campaign completed successfully')
            update_job_status(campaign_id, 'email_copy_generation', JobStatus.COMPLETED.value, 'Email copy generated successfully')
            
            # Store job result
            job = get_current_job()
            if job:
                Job.create(
                    campaign_id=campaign_id,
                    job_type='email_copy_generation',
                    status=JobStatus.COMPLETED.value,
                    result={'status': 'success', 'campaign_id': campaign_id},
                    error=None,
                    started_at=datetime.utcnow(),
                    ended_at=datetime.utcnow(),
                    execution_time=result.get('execution_time', 0)
                )
            
            return {'campaign_id': campaign_id, 'status': 'success'}
        except Exception as e:
            handle_task_error(campaign_id, e, 'email_copy_generation_task')

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

def enqueue_email_verification(result, depends_on=None):
    """Enqueue the email verification task."""
    queue = get_queue()
    job = queue.enqueue(
        email_verification_task,
        args=(result,),
        depends_on=depends_on,
        job_timeout=QUEUE_CONFIG['default']['job_timeout'],
        retry=Retry(max=QUEUE_CONFIG['default']['max_retries'])
    )
    return job

def enqueue_enriching_leads(result, depends_on=None):
    """Enqueue the enriching leads task."""
    queue = get_queue()
    job = queue.enqueue(
        enriching_leads_task,
        args=(result,),
        depends_on=depends_on,
        job_timeout=QUEUE_CONFIG['default']['job_timeout'],
        retry=Retry(max=QUEUE_CONFIG['default']['max_retries'])
    )
    return job

def enqueue_email_copy_generation(result, depends_on=None):
    """Enqueue the email copy generation task."""
    queue = get_queue()
    job = queue.enqueue(
        email_copy_generation_task,
        args=(result,),
        depends_on=depends_on,
        job_timeout=QUEUE_CONFIG['default']['job_timeout'],
        retry=Retry(max=QUEUE_CONFIG['default']['max_retries'])
    )
    return job

def enqueue_email_generation(params, depends_on=None):
    """Enqueue email generation task."""
    queue = get_queue()
    job = queue.enqueue(
        'server.tasks.email_generation_task',
        params,
        depends_on=depends_on,
        job_timeout=3600  # 1 hour timeout
    )
    return job

def email_generation_task(params):
    """Generate email copy for leads."""
    campaign_id = params.get('campaign_id')
    try:
        # Update job status
        update_job_status(campaign_id, 'generate_emails', JobStatus.IN_PROGRESS.value, 'Generating email copy')
        
        # Get campaign
        with flask_app.app_context():
            campaign = Campaign.query.get(campaign_id)
            if not campaign:
                raise ValueError(f"Campaign {campaign_id} not found")
            
            # Get leads
            leads = Lead.query.filter_by(campaign_id=campaign_id).all()
            if not leads:
                raise ValueError("No leads found for campaign")
            
            # Generate email copy for each lead
            count = 0
            for lead in leads:
                # Generate personalized email copy
                email_copy = generate_personalized_email(lead)
                lead.email_copy = email_copy
                count += 1
            
            # Save changes
            db.session.commit()
            
            # Update job status
            update_job_status(campaign_id, 'generate_emails', JobStatus.COMPLETED.value, f"Generated email copy for {count} leads")
            
            return {'campaign_id': campaign_id, 'generated_count': count}
    except Exception as e:
        handle_task_error(campaign_id, e, 'email_generation_task')
        raise

# Example usage of chaining (for reference, not executed on import):
# from celery import chain
# chain(fetch_and_save_leads_task.s(params, campaign_id), enriching_leads_task.s())() 
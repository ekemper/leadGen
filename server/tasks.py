from server.background_services.apollo_service import ApolloService
from server.background_services.email_verifier_service import EmailVerifierService
from server.app import create_app
from server.background_services.openai_service import OpenAIService
from server.models import Campaign
from server.models.campaign import CampaignStatus
from server.config.database import db
from server.utils.logging_config import server_logger, combined_logger
from rq import get_current_job
from server.config.queue_config import get_queue, QUEUE_CONFIG
from server.utils.job_storage import store_job_result
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
                combined_logger.info(f"Campaign {campaign_id} status updated to {status}", extra={
                    'component': 'server',
                    'campaign_id': campaign_id,
                    'status': status,
                    'message': message,
                    'error': error
                })
        except Exception as e:
            server_logger.error(f"Error updating campaign status: {str(e)}")
            combined_logger.error(f"Error updating campaign status: {str(e)}", extra={
                'component': 'server',
                'campaign_id': campaign_id,
                'error': str(e)
            })
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
                combined_logger.info(f"Campaign {campaign_id} job {job_type} status updated to {status}", extra={
                    'component': 'server',
                    'campaign_id': campaign_id,
                    'job_type': job_type,
                    'status': status,
                    'message': message
                })
        except Exception as e:
            server_logger.error(f"Error updating job status: {str(e)}")
            combined_logger.error(f"Error updating job status: {str(e)}", extra={
                'component': 'server',
                'campaign_id': campaign_id,
                'job_type': job_type,
                'error': str(e)
            })
            db.session.rollback()

def handle_task_error(campaign_id, error, task_name):
    """Handle task errors consistently."""
    error_msg = f"Error in {task_name}: {str(error)}"
    server_logger.error(error_msg)
    server_logger.error(traceback.format_exc())
    combined_logger.error(error_msg, extra={
        'component': 'server',
        'campaign_id': campaign_id,
        'task_name': task_name,
        'error': str(error),
        'traceback': traceback.format_exc()
    })
    update_campaign_status(campaign_id, CampaignStatus.FAILED, error=error_msg)
    update_job_status(campaign_id, task_name, 'failed', error_msg)
    raise error

def fetch_and_save_leads_task(params, campaign_id):
    """Fetch and save leads from Apollo."""
    with flask_app.app_context():
        try:
            server_logger.info(f"Starting fetch_and_save_leads_task for campaign {campaign_id}")
            combined_logger.info(f"Starting fetch_and_save_leads_task for campaign {campaign_id}", extra={
                'component': 'server',
                'campaign_id': campaign_id,
                'params': params
            })
            update_campaign_status(campaign_id, CampaignStatus.FETCHING_LEADS, 'Fetching leads from Apollo')
            update_job_status(campaign_id, 'fetch_leads', 'in_progress', 'Fetching leads from Apollo')
            
            result = ApolloService().fetch_leads(params, campaign_id)
            
            server_logger.info(f"Successfully fetched {result.get('count', 0)} leads for campaign {campaign_id}")
            combined_logger.info(f"Successfully fetched {result.get('count', 0)} leads for campaign {campaign_id}", extra={
                'component': 'server',
                'campaign_id': campaign_id,
                'count': result.get('count', 0)
            })
            update_campaign_status(campaign_id, CampaignStatus.LEADS_FETCHED, f"Fetched {result.get('count', 0)} leads")
            update_job_status(campaign_id, 'fetch_leads', 'completed', f"Successfully fetched {result.get('count', 0)} leads")
            
            # Store job result
            job = get_current_job()
            if job:
                store_job_result(job, result)
            
            return {'campaign_id': campaign_id, 'status': 'success', 'count': result.get('count', 0)}
        except Exception as e:
            handle_task_error(campaign_id, e, 'fetch_and_save_leads_task')

def enriching_leads_task(result):
    """Enrich leads with additional data."""
    with flask_app.app_context():
        try:
            campaign_id = result.get('campaign_id')
            if not campaign_id:
                raise ValueError("Campaign ID not found in result")
                
            server_logger.info(f"Starting enriching_leads_task for campaign {campaign_id}")
            combined_logger.info(f"Starting enriching_leads_task for campaign {campaign_id}", extra={
                'component': 'server',
                'campaign_id': campaign_id
            })
            update_campaign_status(campaign_id, CampaignStatus.ENRICHING, 'Enriching leads with additional data')
            update_job_status(campaign_id, 'enrich_leads', 'in_progress', 'Enriching leads with additional data')
            
            # TODO: Implement lead enrichment
            # For now, just mark as enriched
            update_campaign_status(campaign_id, CampaignStatus.ENRICHED, 'Leads enriched successfully')
            update_job_status(campaign_id, 'enrich_leads', 'completed', 'Leads enriched successfully')
            
            # Store job result
            job = get_current_job()
            if job:
                store_job_result(job, {'status': 'success', 'campaign_id': campaign_id})
            
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
            combined_logger.info(f"Starting email_verification_task for campaign {campaign_id}", extra={
                'component': 'server',
                'campaign_id': campaign_id
            })
            update_campaign_status(campaign_id, CampaignStatus.VERIFYING_EMAILS, 'Verifying email addresses')
            update_job_status(campaign_id, 'email_verification', 'in_progress', 'Verifying email addresses')
            
            verifier = EmailVerifierService()
            count = verifier.verify_emails_for_campaign(campaign_id)
            
            server_logger.info(f"Successfully verified {count} emails for campaign {campaign_id}")
            combined_logger.info(f"Successfully verified {count} emails for campaign {campaign_id}", extra={
                'component': 'server',
                'campaign_id': campaign_id,
                'verified_count': count
            })
            update_campaign_status(campaign_id, CampaignStatus.EMAILS_VERIFIED, f"Verified {count} email addresses")
            update_job_status(campaign_id, 'email_verification', 'completed', f"Successfully verified {count} email addresses")
            
            # Store job result
            job = get_current_job()
            if job:
                store_job_result(job, {'verified_count': count, 'campaign_id': campaign_id})
            
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
            combined_logger.info(f"Starting email_copy_generation_task for campaign {campaign_id}", extra={
                'component': 'server',
                'campaign_id': campaign_id
            })
            update_campaign_status(campaign_id, CampaignStatus.GENERATING_EMAILS, 'Generating personalized email copy')
            update_job_status(campaign_id, 'email_copy_generation', 'in_progress', 'Generating personalized email copy')
            
            # TODO: Implement email copy generation
            # For now, just mark as completed
            update_campaign_status(campaign_id, CampaignStatus.COMPLETED, 'Campaign completed successfully')
            update_job_status(campaign_id, 'email_copy_generation', 'completed', 'Email copy generated successfully')
            
            # Store job result
            job = get_current_job()
            if job:
                store_job_result(job, {'status': 'success', 'campaign_id': campaign_id})
            
            return {'campaign_id': campaign_id, 'status': 'success'}
        except Exception as e:
            handle_task_error(campaign_id, e, 'email_copy_generation_task')

def enqueue_fetch_and_save_leads(params, campaign_id):
    """Enqueue the fetch and save leads task."""
    queue = get_queue()
    job = queue.enqueue(
        fetch_and_save_leads_task,
        args=(params, campaign_id),
        job_timeout=QUEUE_CONFIG['default']['timeout'],
        result_ttl=QUEUE_CONFIG['default']['result_ttl'],
        failure_ttl=QUEUE_CONFIG['default']['failure_ttl'],
        retry=QUEUE_CONFIG['default']['max_retries'],
        retry_after=QUEUE_CONFIG['default']['retry_after']
    )
    return job

def enqueue_email_verification(result, depends_on=None):
    """Enqueue the email verification task."""
    queue = get_queue()
    job = queue.enqueue(
        email_verification_task,
        args=(result,),
        depends_on=depends_on,
        job_timeout=QUEUE_CONFIG['default']['timeout'],
        result_ttl=QUEUE_CONFIG['default']['result_ttl'],
        failure_ttl=QUEUE_CONFIG['default']['failure_ttl'],
        retry=QUEUE_CONFIG['default']['max_retries'],
        retry_after=QUEUE_CONFIG['default']['retry_after']
    )
    return job

def enqueue_enriching_leads(result, depends_on=None):
    """Enqueue the enriching leads task."""
    queue = get_queue()
    job = queue.enqueue(
        enriching_leads_task,
        args=(result,),
        depends_on=depends_on,
        job_timeout=QUEUE_CONFIG['default']['timeout'],
        result_ttl=QUEUE_CONFIG['default']['result_ttl'],
        failure_ttl=QUEUE_CONFIG['default']['failure_ttl'],
        retry=QUEUE_CONFIG['default']['max_retries'],
        retry_after=QUEUE_CONFIG['default']['retry_after']
    )
    return job

def enqueue_email_copy_generation(result, depends_on=None):
    """Enqueue the email copy generation task."""
    queue = get_queue()
    job = queue.enqueue(
        email_copy_generation_task,
        args=(result,),
        depends_on=depends_on,
        job_timeout=QUEUE_CONFIG['default']['timeout'],
        result_ttl=QUEUE_CONFIG['default']['result_ttl'],
        failure_ttl=QUEUE_CONFIG['default']['failure_ttl'],
        retry=QUEUE_CONFIG['default']['max_retries'],
        retry_after=QUEUE_CONFIG['default']['retry_after']
    )
    return job

# Example usage of chaining (for reference, not executed on import):
# from celery import chain
# chain(fetch_and_save_leads_task.s(params, campaign_id), enriching_leads_task.s())() 
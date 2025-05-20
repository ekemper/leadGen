from server.background_services.apollo_service import ApolloService
from server.background_services.email_verifier_service import EmailVerifierService
from server.background_services.openai_service import OpenAIService
from server.models import Campaign
from server.models.campaign import CampaignStatus
from server.models.job_status import JobStatus
from server.config.database import db
from server.utils.logging_config import app_logger
from rq import get_current_job, Queue, Retry
from server.config.queue_config import get_queue, QUEUE_CONFIG
from server.models.job import Job
import traceback
from datetime import datetime
from server.background_services.instantly_service import InstantlyService

print("server.tasks module loaded")

def handle_task_error(campaign_id, error, job_type):
    """Handle task errors and update campaign status."""
    from server.app import create_app
    flask_app = create_app()
    with flask_app.app_context():
        try:
            app_logger.error(f"Error in {job_type} for campaign {campaign_id}: {str(error)}")
            campaign = Campaign.query.get(campaign_id)
            if campaign:
                campaign.update_status(CampaignStatus.FAILED, error_message=str(error))
            # Update job status if job exists
            job = Job.query.filter_by(campaign_id=campaign_id, job_type=job_type.upper()).order_by(Job.created_at.desc()).first()
            if job:
                job.update_status(JobStatus.FAILED, error_message=str(error))
        except Exception as e:
            app_logger.error(f"Error handling task error: {str(e)}", exc_info=True)

def fetch_and_save_leads_task(params, campaign_id):
    """Fetch and save leads from Apollo."""
    from server.app import create_app
    flask_app = create_app()
    with flask_app.app_context():
        job = None
        campaign = None
        try:
            app_logger.info(f"Starting fetch_and_save_leads_task for campaign {campaign_id}")
            campaign = Campaign.query.get(campaign_id)
            if not campaign:
                raise Exception(f"Campaign {campaign_id} not found")

            # Create job
            job = Job.create(campaign_id=campaign_id, job_type='FETCH_LEADS', parameters=params)
            db.session.commit()
            job.update_status(JobStatus.IN_PROGRESS)

            # Fetch leads (pass job.id)
            result = ApolloService().fetch_leads(params, campaign_id)

            # Mark job as completed
            job.update_status(JobStatus.COMPLETED)

            # Update campaign status directly
            campaign.update_status(CampaignStatus.COMPLETED)

            app_logger.info(f"Successfully fetched {result.get('count', 0)} leads for campaign {campaign_id}")

            # Enqueue enrichment job for each lead
            from server.models.lead import Lead
            leads = Lead.query.filter_by(campaign_id=campaign_id).all()
            for lead in leads:
                enqueue_enrich_lead(lead.id)

            return campaign_id  # Return campaign_id for chaining
        except Exception as e:
            handle_task_error(campaign_id, e, 'FETCH_LEADS')
            raise

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

def enqueue_enrich_lead(lead_id, depends_on=None):
    queue = get_queue()
    job = queue.enqueue(
        enrich_lead_task,
        args=(lead_id,),
        depends_on=depends_on,
        job_timeout=QUEUE_CONFIG['default']['job_timeout'],
        retry=Retry(max=QUEUE_CONFIG['default']['max_retries'])
    )
    return job

def email_generation_task(params):
    pass  # Commented out for testing fetch only

def verify_lead_email(lead):
    """Helper to verify a lead's email and save the result."""
    from server.background_services.email_verifier_service import EmailVerifierService
    if not lead.email:
        result = {'status': 'skipped', 'reason': 'no email'}
        lead.email_verification = result
        db.session.commit()
        return result
    result = EmailVerifierService().verify_email(lead.email)
    lead.email_verification = result
    db.session.commit()
    return result

def enrich_lead_with_perplexity(lead):
    """Helper to enrich a lead with Perplexity and save the result."""
    from server.background_services.perplexity_service import PerplexityService
    result = PerplexityService().enrich_lead(lead)
    lead.enrichment_results = result
    db.session.commit()
    return result

def generate_lead_email_copy(lead, enrichment_result):
    """Helper to generate email copy for a lead and save the result."""
    from server.background_services.openai_service import OpenAIService
    response = OpenAIService().generate_email_copy(lead, enrichment_result)
    # Only store the generated content string
    lead.email_copy_gen_results = response.choices[0].message.content
    db.session.commit()
    return response.choices[0].message.content

def enrich_lead_task(lead_id):
    """Verify email, enrich with Perplexity, generate email copy, and create Instantly lead for a single lead."""
    from server.app import create_app
    flask_app = create_app()
    with flask_app.app_context():
        from server.models.lead import Lead
        lead = Lead.query.get(lead_id)
        job = None
        if not lead:
            app_logger.error(f"Lead {lead_id} not found for enrichment task.")
            return
        try:
            from server.models.job import Job
            from server.models.job_status import JobStatus
            job = Job.create(campaign_id=lead.campaign_id, job_type='ENRICH_LEAD', parameters={'lead_id': lead_id})
            db.session.commit()
            lead.enrichment_job_id = job.id
            db.session.commit()
            job.update_status(JobStatus.IN_PROGRESS)

            # 1. Email verification
            email_result = verify_lead_email(lead)
            email_success = email_result and email_result.get('result') == 'ok'
            error_details = {}
            if not email_success:
                error_details['email_verification'] = email_result
                job.result = {
                    'email_verification_success': False,
                    'enrichment_success': False,
                    'email_copy_success': False,
                    'instantly_success': False
                }
                job.error_details = error_details
                job.update_status(JobStatus.COMPLETED)
                return

            # 2. Enrichment
            enrichment_result = enrich_lead_with_perplexity(lead)
            enrichment_success = 'error' not in enrichment_result
            if not enrichment_success:
                error_details['enrichment'] = enrichment_result
                job.result = {
                    'email_verification_success': True,
                    'enrichment_success': False,
                    'email_copy_success': False,
                    'instantly_success': False
                }
                job.error_details = error_details
                job.update_status(JobStatus.COMPLETED)
                return

            # 3. Email copy generation
            try:
                email_copy_result = generate_lead_email_copy(lead, enrichment_result)
                email_copy_success = True
            except Exception as e:
                email_copy_success = False
                lead.email_copy_gen_results = None
                db.session.commit()
                error_details['email_copy'] = str(e)

            # 4. Instantly lead creation
            instantly_success = False
            instantly_result = None
            # Data checks for Instantly
            missing_fields = []
            if not lead.campaign_id:
                missing_fields.append('campaign_id')
            if not lead.email:
                missing_fields.append('email')
            if not lead.first_name:
                missing_fields.append('first_name')
            if not lead.email_copy_gen_results:
                missing_fields.append('email_copy_gen_results')
            if missing_fields:
                msg = f"Skipping Instantly lead creation for lead {lead.id} due to missing fields: {', '.join(missing_fields)}"
                app_logger.warning(msg)
                error_details['instantly'] = msg
            elif email_copy_success:
                try:
                    from server.background_services.instantly_service import InstantlyService
                    from server.models.campaign import Campaign
                    instantly_service = InstantlyService()
                    campaign = Campaign.query.get(lead.campaign_id)
                    instantly_campaign_id = campaign.instantly_campaign_id if campaign else None
                    instantly_result = instantly_service.create_lead(
                        campaign_id=instantly_campaign_id,
                        email=lead.email,
                        first_name=lead.first_name,
                        personalization=lead.email_copy_gen_results
                    )
                    instantly_success = not ('error' in instantly_result)
                    lead.instantly_lead_record = instantly_result
                    db.session.commit()
                except Exception as e:
                    error_details['instantly'] = str(e)
                    lead.instantly_lead_record = {'error': str(e)}
                    db.session.commit()
                    app_logger.error(f"Instantly lead creation failed for lead {lead.id}: {str(e)}")

            # Save overall job result
            job.result = {
                'email_verification_success': True,
                'enrichment_success': True,
                'email_copy_success': email_copy_success,
                'instantly_success': instantly_success
            }
            if error_details:
                job.error_details = error_details
            if instantly_result:
                job.result['instantly_result'] = instantly_result
            job.update_status(JobStatus.COMPLETED)
            app_logger.info(f"Lead {lead_id} enrichment, email copy, and Instantly lead creation complete.")
        except Exception as e:
            db.session.rollback()
            error_msg = f"Error in enrich_lead_task for lead {lead_id}: {str(e)}"
            app_logger.error(error_msg)
            if job:
                job.update_status(JobStatus.FAILED, error_message=error_msg)
            raise




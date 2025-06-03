import os
import json
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Union
from celery import Task
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from app.core.logger import get_logger
from app.workers.celery_app import celery_app
from app.core.database import get_db
from app.models.campaign import Campaign
from app.models.campaign_status import CampaignStatus
from app.models.job import Job, JobType, JobStatus
from app.models.lead import Lead
from app.core.config import get_redis_connection
from app.core.dependencies import (
    get_apollo_rate_limiter,
    get_email_verifier_rate_limiter,
    get_perplexity_rate_limiter,
    get_openai_rate_limiter,
    get_instantly_rate_limiter
)
from app.core.queue_manager import get_queue_manager
from app.core.circuit_breaker import ThirdPartyService

logger = get_logger(__name__)

@celery_app.task(bind=True, name="fetch_and_save_leads_task")
def fetch_and_save_leads_task(self, job_params: Dict[str, Any], campaign_id: str, job_id: int):
    """
    Background task to fetch and save leads from Apollo.
    
    Args:
        job_params: Dictionary containing fileName, totalRecords, url
        campaign_id: ID of the campaign
        job_id: ID of the job to track progress
    """
    db_gen = get_db()
    db: Session = next(db_gen)
    
    try:
        logger.info(f"Starting fetch_and_save_leads_task for campaign {campaign_id}, job {job_id}")
        
        # Update job status to processing
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            raise ValueError(f"Job {job_id} not found")
        
        job.status = JobStatus.PROCESSING
        job.task_id = self.request.id
        db.commit()
        
        # Get campaign
        campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
        if not campaign:
            raise ValueError(f"Campaign {campaign_id} not found")
        
        # Update task progress
        self.update_state(
            state="PROGRESS",
            meta={
                "current": 1,
                "total": 5,
                "status": "Initializing Apollo service"
            }
        )
        
        # Initialize Apollo service with rate limiting
        from app.background_services.apollo_service import ApolloService
        redis_client = get_redis_connection()
        apollo_rate_limiter = get_apollo_rate_limiter(redis_client)
        apollo_service = ApolloService(rate_limiter=apollo_rate_limiter)
        
        self.update_state(
            state="PROGRESS",
            meta={
                "current": 2,
                "total": 5,
                "status": "Fetching leads from Apollo"
            }
        )
        
        # Fetch leads using Apollo service
        result = apollo_service.fetch_leads(
            params=job_params,
            campaign_id=campaign_id,
            db=db
        )
        
        self.update_state(
            state="PROGRESS",
            meta={
                "current": 3,
                "total": 5,
                "status": "Saving leads to database"
            }
        )
        
        # Process and save leads
        leads_count = result.get('count', 0)
        
        self.update_state(
            state="PROGRESS",
            meta={
                "current": 4,
                "total": 5,
                "status": "Starting lead enrichment"
            }
        )
        
        # Trigger enrichment for each saved lead
        if leads_count > 0:
            logger.info(f"Triggering enrichment for {leads_count} leads in campaign {campaign_id}")
            # Get all leads for this campaign that were just created
            leads = db.query(Lead).filter(Lead.campaign_id == campaign_id).all()
            for lead in leads:
                # Queue individual lead enrichment task
                enrich_lead_task.delay(lead.id, campaign_id)
                logger.info(f"Queued enrichment task for lead {lead.id} ({lead.email})")
        
        self.update_state(
            state="PROGRESS",
            meta={
                "current": 5,
                "total": 5,
                "status": "Finalizing results"
            }
        )
        
        # Update job status to completed
        job.status = JobStatus.COMPLETED
        job.result = f"Successfully fetched {leads_count} leads and queued enrichment tasks"
        job.completed_at = datetime.utcnow()
        
        # Update campaign status (ensure it goes through RUNNING first)
        if campaign.status == CampaignStatus.CREATED:
            campaign.update_status(CampaignStatus.RUNNING, status_message="Processing leads")
        # Don't mark campaign as completed yet - wait for enrichment to finish
        campaign.update_status(
            CampaignStatus.RUNNING,
            status_message=f"Successfully fetched {leads_count} leads, enrichment in progress"
        )
        
        db.commit()
        
        logger.info(f"Completed fetch_and_save_leads_task for campaign {campaign_id}")
        
        return {
            "job_id": job_id,
            "campaign_id": campaign_id,
            "status": "completed",
            "leads_fetched": leads_count,
            "enrichment_queued": leads_count,
            "result": result
        }
        
    except Exception as e:
        logger.error(f"Error in fetch_and_save_leads_task: {str(e)}", exc_info=True)
        
        # Mark job as failed
        if 'job' in locals() and job:
            job.status = JobStatus.FAILED
            job.error = str(e)
            job.completed_at = datetime.utcnow()
            
        # Mark campaign as failed
        if 'campaign' in locals() and campaign:
            campaign.update_status(CampaignStatus.FAILED, status_error=str(e))
            
        db.commit()
        raise
        
    finally:
        db.close()

@celery_app.task(bind=True, name="enrich_lead_task")
def enrich_lead_task(self, lead_id: str, campaign_id: str):
    """
    Enrich a single lead with email verification, Perplexity enrichment, 
    email copy generation, and Instantly lead creation.
    
    Args:
        lead_id: ID of the lead to enrich
        campaign_id: ID of the campaign (for job tracking)
    """
    db_gen = get_db()
    db: Session = next(db_gen)
    
    try:
        logger.info(f"Starting enrich_lead_task for lead_id={lead_id}, campaign_id={campaign_id}")
        
        # Get the lead
        lead = db.query(Lead).filter(Lead.id == lead_id).first()
        if not lead:
            logger.error(f"Lead {lead_id} not found for enrichment task")
            return {"error": f"Lead {lead_id} not found"}
        
        # Create enrichment job for tracking
        enrichment_job = Job(
            campaign_id=campaign_id,
            name='ENRICH_LEAD',
            description=f'Enrich lead {lead.email}',
            job_type=JobType.ENRICH_LEAD,  # Updated to use singular form
            status=JobStatus.PROCESSING,
            task_id=self.request.id
        )
        db.add(enrichment_job)
        db.commit()
        db.refresh(enrichment_job)
        
        # Link the job to the lead
        lead.enrichment_job_id = enrichment_job.id
        db.commit()
        
        # Check if job should be processed based on circuit breaker status
        queue_manager = get_queue_manager(db)
        circuit_breaker = queue_manager.circuit_breaker
        
        should_process, reason = queue_manager.should_process_job(enrichment_job)
        if not should_process:
            logger.warning(f"Pausing job {enrichment_job.id} for lead {lead_id}: {reason}")
            enrichment_job.status = JobStatus.PAUSED
            enrichment_job.error = f"Job paused: {reason}"
            enrichment_job.completed_at = datetime.utcnow()
            db.commit()
            return {
                "lead_id": lead_id,
                "job_id": enrichment_job.id,
                "status": "paused",
                "reason": reason
            }
        
        error_details = {}
        
        # Step 1: Email Verification
        self.update_state(
            state="PROGRESS",
            meta={
                "current": 1,
                "total": 4,
                "status": f"Verifying email for {lead.email}"
            }
        )
        
        logger.info(f"Verifying email for lead {lead_id} ({lead.email})")
        email_success = False
        try:
            from app.background_services.email_verifier_service import EmailVerifierService
            redis_client = get_redis_connection()
            email_rate_limiter = get_email_verifier_rate_limiter(redis_client)
            email_service = EmailVerifierService(rate_limiter=email_rate_limiter)
            email_result = email_service.verify_email(lead.email)
            logger.info(f"Email verification result for lead {lead_id}: {email_result}")
            
            # Store verification result
            lead.email_verification = email_result
            email_success = email_result and email_result.get('result') == 'deliverable'
            if not email_success:
                error_details['email_verification'] = email_result
                logger.warning(f"Email verification failed for lead {lead_id}, proceeding with enrichment anyway")
        except Exception as e:
            error_details['email_verification'] = str(e)
            logger.error(f"Email verification error for lead {lead_id}: {str(e)}")
        
        # Step 2: Perplexity Enrichment
        self.update_state(
            state="PROGRESS",
            meta={
                "current": 2,
                "total": 4,
                "status": f"Enriching lead data for {lead.email}"
            }
        )
        
        logger.info(f"Enriching lead {lead_id} with Perplexity API")
        enrichment_success = False
        enrichment_result = {}
        try:
            from app.background_services.perplexity_service import PerplexityService
            redis_client = get_redis_connection()
            perplexity_rate_limiter = get_perplexity_rate_limiter(redis_client)
            perplexity_service = PerplexityService(rate_limiter=perplexity_rate_limiter)
            enrichment_result = perplexity_service.enrich_lead(lead)
            logger.info(f"Enrichment result for lead {lead_id}: {enrichment_result}")
            
            # Check for rate limiting in response
            if enrichment_result and enrichment_result.get('status') == 'rate_limited':
                circuit_breaker.record_failure(ThirdPartyService.PERPLEXITY, 
                                             enrichment_result.get('error', 'Rate limited'), 
                                             'rate_limit')
                # Pause this job and trigger circuit breaker
                enrichment_job.status = JobStatus.PAUSED
                enrichment_job.error = f"Paused due to Perplexity rate limit: {enrichment_result.get('error')}"
                enrichment_job.completed_at = datetime.utcnow()
                db.commit()
                return {
                    "lead_id": lead_id,
                    "job_id": enrichment_job.id,
                    "status": "paused",
                    "reason": "Perplexity rate limit exceeded"
                }
            else:
                circuit_breaker.record_success(ThirdPartyService.PERPLEXITY)
            
            # Store enrichment results
            lead.enrichment_results = enrichment_result
            enrichment_success = 'error' not in enrichment_result and enrichment_result.get('status') != 'rate_limited'
            if not enrichment_success:
                error_details['enrichment'] = enrichment_result
        except Exception as e:
            circuit_breaker.record_failure(ThirdPartyService.PERPLEXITY, str(e), 'exception')
            error_details['enrichment'] = str(e)
            logger.error(f"Enrichment error for lead {lead_id}: {str(e)}")
            enrichment_result = {'error': str(e)}
            lead.enrichment_results = enrichment_result
        
        # Step 3: Email Copy Generation
        self.update_state(
            state="PROGRESS",
            meta={
                "current": 3,
                "total": 4,
                "status": f"Generating email copy for {lead.email}"
            }
        )
        
        email_copy_success = False
        if enrichment_success:
            logger.info(f"Generating email copy for lead {lead_id}")
            try:
                from app.background_services.openai_service import OpenAIService
                redis_client = get_redis_connection()
                openai_rate_limiter = get_openai_rate_limiter(redis_client)
                openai_service = OpenAIService(rate_limiter=openai_rate_limiter, circuit_breaker=circuit_breaker)
                email_copy_result = openai_service.generate_email_copy(lead, enrichment_result)
                logger.info(f"Email copy generation result for lead {lead_id}: {email_copy_result}")
                
                # Check for rate limiting or circuit breaker response
                if email_copy_result and email_copy_result.get('status') in ['rate_limited', 'circuit_breaker_open']:
                    # For rate limits, the circuit breaker is already handled in the service
                    # For circuit breaker open, just skip and mark as failed
                    error_details['email_copy'] = f"OpenAI service unavailable: {email_copy_result.get('error', 'Service unavailable')}"
                    email_copy_success = False
                    
                    # If circuit breaker is open, pause this job
                    if email_copy_result.get('status') == 'circuit_breaker_open':
                        enrichment_job.status = JobStatus.PAUSED
                        enrichment_job.error = f"Paused due to OpenAI circuit breaker: {email_copy_result.get('error')}"
                        enrichment_job.completed_at = datetime.utcnow()
                        db.commit()
                        return {
                            "lead_id": lead_id,
                            "job_id": enrichment_job.id,
                            "status": "paused",
                            "reason": "OpenAI circuit breaker open"
                        }
                else:
                    # Normal success handling
                    email_copy_success = 'error' not in email_copy_result and email_copy_result.get('status') not in ['rate_limited', 'circuit_breaker_open']
                
                # Store email copy results
                lead.email_copy_gen_results = email_copy_result
            except Exception as e:
                error_details['email_copy'] = str(e)
                logger.error(f"Email copy generation failed for lead {lead_id}: {str(e)}")
                lead.email_copy_gen_results = {'error': str(e)}
        else:
            logger.warning(f"Skipping email copy generation for lead {lead_id} due to enrichment failure")
            error_details['email_copy'] = "Skipped due to enrichment failure"
        
        # Step 4: Instantly Lead Creation
        self.update_state(
            state="PROGRESS",
            meta={
                "current": 4,
                "total": 4,
                "status": f"Creating Instantly lead for {lead.email}"
            }
        )
        
        instantly_success = False
        instantly_result = {}
        
        # Check required fields for Instantly
        missing_fields = []
        if not lead.email:
            missing_fields.append('email')
        if not lead.first_name:
            missing_fields.append('first_name')
        if not email_copy_success:
            missing_fields.append('email_copy_gen_results')
        
        if missing_fields:
            msg = f"Skipping Instantly lead creation for lead {lead.id} due to missing fields: {', '.join(missing_fields)}"
            logger.warning(msg)
            error_details['instantly'] = msg
            lead.instantly_lead_record = {'error': msg}
        elif email_copy_success:
            logger.info(f"Creating Instantly lead for lead {lead_id}")
            try:
                from app.background_services.instantly_service import InstantlyService
                redis_client = get_redis_connection()
                instantly_rate_limiter = get_instantly_rate_limiter(redis_client)
                instantly_service = InstantlyService(rate_limiter=instantly_rate_limiter)
                
                # Get campaign for instantly_campaign_id
                campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
                instantly_campaign_id = campaign.instantly_campaign_id if campaign else None
                
                # Extract email content from OpenAI response
                email_content = ""
                if lead.email_copy_gen_results and 'choices' in lead.email_copy_gen_results:
                    try:
                        email_content = lead.email_copy_gen_results['choices'][0]['message']['content']
                    except (KeyError, IndexError, TypeError) as e:
                        logger.warning(f"Could not extract email content from OpenAI response for lead {lead_id}: {e}")
                        email_content = "Generated email content not available"
                
                instantly_result = instantly_service.create_lead(
                    campaign_id=instantly_campaign_id,
                    email=lead.email,
                    first_name=lead.first_name,
                    personalization=email_content
                )
                
                # Check for rate limiting in response
                if instantly_result and instantly_result.get('status') == 'rate_limited':
                    circuit_breaker.record_failure(ThirdPartyService.INSTANTLY, 
                                                 instantly_result.get('error', 'Rate limited'), 
                                                 'rate_limit')
                else:
                    circuit_breaker.record_success(ThirdPartyService.INSTANTLY)
                
                instantly_success = 'error' not in instantly_result and instantly_result.get('status') != 'rate_limited'
                lead.instantly_lead_record = instantly_result
                logger.info(f"Instantly lead creation result for lead {lead_id}: {instantly_result}")
            except Exception as e:
                circuit_breaker.record_failure(ThirdPartyService.INSTANTLY, str(e), 'exception')
                error_details['instantly'] = str(e)
                logger.error(f"Instantly lead creation failed for lead {lead_id}: {str(e)}")
                lead.instantly_lead_record = {'error': str(e)}
        
        # Commit all lead updates
        db.commit()
        
        # Update job with final results
        job_result = {
            'email_verification_success': email_success,
            'enrichment_success': enrichment_success,
            'email_copy_success': email_copy_success,
            'instantly_success': instantly_success
        }
        
        if instantly_result:
            # Ensure instantly_result is JSON serializable by converting it to a simple dict
            try:
                # Test JSON serialization and add to result
                serialized_instantly = json.dumps(instantly_result)
                job_result['instantly_result'] = json.loads(serialized_instantly)  # Ensure it's clean
            except (TypeError, ValueError) as e:
                logger.warning(f"Could not serialize instantly_result for lead {lead_id}: {str(e)}")
                job_result['instantly_result'] = {'error': f'Serialization failed: {str(e)}'}
        
        enrichment_job.result = json.dumps(job_result)
        if error_details:
            enrichment_job.error = json.dumps(error_details)
        enrichment_job.status = JobStatus.COMPLETED
        enrichment_job.completed_at = datetime.utcnow()

        try:
            db.commit()
        except Exception as db_error:
            logger.error(f"Database commit failed for lead {lead_id}: {str(db_error)}")
            db.rollback()
            # Try again with simpler result data
            enrichment_job.result = json.dumps({
                'email_verification_success': email_success,
                'enrichment_success': enrichment_success,
                'email_copy_success': email_copy_success,
                'instantly_success': instantly_success,
                'error': 'Full result data could not be stored due to serialization issue'
            })
            enrichment_job.error = json.dumps({'error': str(db_error)}) if not error_details else json.dumps(error_details)
            db.commit()
        
        logger.info(f"Lead {lead_id} enrichment complete. Results: {job_result}")
        
        return {
            "lead_id": lead_id,
            "job_id": enrichment_job.id,
            "status": "completed",
            "results": job_result
        }
        
    except Exception as e:
        logger.error(f"Error in enrich_lead_task for lead {lead_id}: {str(e)}", exc_info=True)
        
        try:
            # Rollback any pending transaction first
            db.rollback()
            
            # Mark job as failed if it was created
            if 'enrichment_job' in locals() and enrichment_job:
                enrichment_job.status = JobStatus.FAILED
                enrichment_job.error = str(e)
                enrichment_job.completed_at = datetime.utcnow()
                db.commit()
        except Exception as cleanup_error:
            logger.error(f"Error during cleanup for lead {lead_id}: {str(cleanup_error)}")
        
        raise
        
    finally:
        db.close()

@celery_app.task(bind=True, name="cleanup_campaign_jobs_task")
def cleanup_campaign_jobs_task(self, campaign_id: str, days: int):
    """
    Background task to clean up old jobs for a campaign.
    
    Args:
        campaign_id: ID of the campaign
        days: Number of days to keep jobs (older jobs will be deleted)
    """
    db_gen = get_db()
    db: Session = next(db_gen)
    
    try:
        logger.info(f"Starting cleanup_campaign_jobs_task for campaign {campaign_id}, days={days}")
        
        # Get campaign
        campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
        if not campaign:
            raise ValueError(f"Campaign {campaign_id} not found")
        
        # Update task progress
        self.update_state(
            state="PROGRESS",
            meta={
                "current": 1,
                "total": 3,
                "status": "Calculating cutoff date"
            }
        )
        
        # Calculate cutoff date
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        self.update_state(
            state="PROGRESS",
            meta={
                "current": 2,
                "total": 3,
                "status": "Finding jobs to delete"
            }
        )
        
        # Get jobs to delete (only completed or failed jobs older than cutoff)
        jobs_to_delete = (
            db.query(Job)
            .filter(
                Job.campaign_id == campaign_id,
                Job.created_at < cutoff_date,
                Job.status.in_([JobStatus.COMPLETED, JobStatus.FAILED])
            )
            .all()
        )
        
        self.update_state(
            state="PROGRESS",
            meta={
                "current": 3,
                "total": 3,
                "status": f"Deleting {len(jobs_to_delete)} jobs"
            }
        )
        
        # Delete jobs
        deleted_count = 0
        for job in jobs_to_delete:
            # Cancel any associated Celery tasks
            if job.task_id:
                try:
                    celery_app.control.revoke(job.task_id, terminate=True)
                except Exception as e:
                    logger.warning(f"Could not revoke task {job.task_id}: {str(e)}")
            
            db.delete(job)
            deleted_count += 1
        
        db.commit()
        
        logger.info(f"Completed cleanup_campaign_jobs_task for campaign {campaign_id}, deleted {deleted_count} jobs")
        
        return {
            "campaign_id": campaign_id,
            "status": "completed",
            "jobs_deleted": deleted_count,
            "cutoff_date": cutoff_date.isoformat(),
            "message": f"Successfully cleaned up {deleted_count} jobs older than {days} days"
        }
        
    except Exception as e:
        logger.error(f"Error in cleanup_campaign_jobs_task: {str(e)}", exc_info=True)
        db.rollback()
        raise
        
    finally:
        db.close()

# @celery_app.task(bind=True, name="process_campaign_leads_task")
# def process_campaign_leads_task(self, campaign_id: str, processing_type: str = "enrichment"):
    """
    Background task to process leads for a campaign (enrichment, email verification, etc.).
    
    Args:
        campaign_id: ID of the campaign
        processing_type: Type of processing (enrichment, email_verification, etc.)
    """
    db_gen = get_db()
    db: Session = next(db_gen)
    
    try:
        logger.info(f"Starting process_campaign_leads_task for campaign {campaign_id}, type={processing_type}")
        
        # Get campaign
        campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
        if not campaign:
            raise ValueError(f"Campaign {campaign_id} not found")
        
        # Create a job to track this processing
        processing_job = Job(
            campaign_id=campaign_id,
            name=f'PROCESS_LEADS_{processing_type.upper()}',
            description=f'Process leads for campaign {campaign.name} - {processing_type}',
            status=JobStatus.PROCESSING,
            task_id=self.request.id
        )
        db.add(processing_job)
        db.commit()
        db.refresh(processing_job)
        
        # Update task progress
        self.update_state(
            state="PROGRESS",
            meta={
                "current": 1,
                "total": 4,
                "status": f"Starting {processing_type} processing"
            }
        )
        
        # TODO: Implement actual lead processing logic
        # For now, this is a placeholder that simulates processing
        
        self.update_state(
            state="PROGRESS",
            meta={
                "current": 2,
                "total": 4,
                "status": f"Processing leads with {processing_type}"
            }
        )
        
        # Simulate processing time
        time.sleep(2)
        
        self.update_state(
            state="PROGRESS",
            meta={
                "current": 3,
                "total": 4,
                "status": "Updating lead records"
            }
        )
        
        # Mock processing results
        processed_count = 0  # TODO: Replace with actual processing count
        
        self.update_state(
            state="PROGRESS",
            meta={
                "current": 4,
                "total": 4,
                "status": "Finalizing processing"
            }
        )
        
        # Update job status
        processing_job.status = JobStatus.COMPLETED
        processing_job.result = f"Processed {processed_count} leads with {processing_type}"
        processing_job.completed_at = datetime.utcnow()
        db.commit()
        
        logger.info(f"Completed process_campaign_leads_task for campaign {campaign_id}")
        
        return {
            "campaign_id": campaign_id,
            "processing_type": processing_type,
            "status": "completed",
            "leads_processed": processed_count,
            "job_id": processing_job.id
        }
        
    except Exception as e:
        logger.error(f"Error in process_campaign_leads_task: {str(e)}", exc_info=True)
        
        # Mark job as failed if it was created
        if 'processing_job' in locals() and processing_job:
            processing_job.status = JobStatus.FAILED
            processing_job.error = str(e)
            processing_job.completed_at = datetime.utcnow()
            db.commit()
        
        raise
        
    finally:
        db.close()

@celery_app.task(name="campaign_health_check")
def campaign_health_check():
    """Health check task specifically for campaign operations."""
    db_gen = get_db()
    db: Session = next(db_gen)
    
    try:
        # Check database connectivity
        campaign_count = db.query(Campaign).count()
        job_count = db.query(Job).count()
        
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "campaign_count": campaign_count,
            "job_count": job_count,
            "service": "campaign_tasks"
        }
        
    except Exception as e:
        logger.error(f"Campaign health check failed: {str(e)}")
        return {
            "status": "unhealthy",
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e),
            "service": "campaign_tasks"
        }
        
    finally:
        db.close() 
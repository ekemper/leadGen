from server.models import Campaign, Job, Lead
from server.config.database import db
from server.background_services.apollo_service import ApolloService
from server.utils.logging_config import app_logger
from server.models.campaign import CampaignStatus
from server.utils.error_messages import CAMPAIGN_ERRORS, JOB_ERRORS
from sqlalchemy import text, func
from typing import Dict, Any, Optional, List
import threading
import json
from datetime import datetime, timedelta
import logging
import re
from server.api.schemas import CampaignSchema, CampaignCreateSchema, CampaignStartSchema, JobSchema
from server.tasks import enqueue_fetch_and_save_leads
from server.background_services.instantly_service import InstantlyService

logger = logging.getLogger(__name__)

class CampaignService:
    def __init__(self):
        self.apollo_service = ApolloService()
        self._campaign_locks = {}
        self._ensure_transaction()

    def _get_campaign_lock(self, campaign_id):
        """Get or create a lock for a campaign."""
        if campaign_id not in self._campaign_locks:
            self._campaign_locks[campaign_id] = threading.Lock()
        return self._campaign_locks[campaign_id]

    def _ensure_transaction(self):
        """Ensure we have an active transaction."""
        if not db.session.is_active:
            db.session.begin()

    def get_campaigns(self) -> List[Dict[str, Any]]:
        """Get all campaigns."""
        try:
            app_logger.info('Fetching all campaigns')
            self._ensure_transaction()
            
            campaigns = Campaign.query.order_by(Campaign.created_at.desc()).all()
            app_logger.info(f'Found {len(campaigns)} campaigns')
            
            campaign_list = []
            for campaign in campaigns:
                try:
                    campaign_dict = campaign.to_dict()
                    # Validate campaign data
                    errors = CampaignSchema().validate(campaign_dict)
                    if errors:
                        raise ValueError(f"Invalid campaign data: {errors}")
                        
                    # Get latest job status for each campaign
                    latest_job = Job.query.filter_by(campaign_id=campaign.id).order_by(Job.created_at.desc()).first()
                    if latest_job:
                        job_dict = latest_job.to_dict()
                        # Validate job data
                        errors = JobSchema().validate(job_dict)
                        if errors:
                            raise ValueError(f"Invalid job data: {errors}")
                        campaign_dict['latest_job'] = job_dict
                    campaign_list.append(campaign_dict)
                except Exception as e:
                    app_logger.error(f'Error converting campaign {campaign.id} to dict: {str(e)}', exc_info=True)
                    continue
            
            app_logger.info(f'Successfully converted {len(campaign_list)} campaigns to dict')
            return campaign_list
        except Exception as e:
            app_logger.error(f'Error getting campaigns: {str(e)}', exc_info=True)
            db.session.rollback()
            raise

    def get_campaign(self, campaign_id: str) -> Dict[str, Any]:
        """Get a single campaign by ID."""
        try:
            app_logger.info(f'Fetching campaign {campaign_id}')
            self._ensure_transaction()
            
            campaign = Campaign.query.get(campaign_id)
            if not campaign:
                app_logger.warning(f'Campaign {campaign_id} not found')
                return None
            
            campaign_dict = campaign.to_dict()
            # Validate campaign data
            errors = CampaignSchema().validate(campaign_dict)
            if errors:
                raise ValueError(f"Invalid campaign data: {errors}")
            
            # Get all jobs for this campaign
            # jobs = Job.query.filter_by(campaign_id=campaign_id).order_by(Job.created_at.desc()).all()
            # job_list = []
            # for job in jobs:
            #     job_dict = job.to_dict()
            #     # Validate job data
            #     errors = JobSchema().validate(job_dict)
            #     if errors:
            #         raise ValueError(f"Invalid job data: {errors}")
            #     job_list.append(job_dict)
            # campaign_dict['jobs'] = job_list
            campaign_dict['jobs'] = []
            
            app_logger.info(f'Successfully fetched campaign {campaign_id} (jobs are empty for now)')
            return campaign_dict
        except Exception as e:
            app_logger.error(f'Error getting campaign: {str(e)}', exc_info=True)
            db.session.rollback()
            raise

    def create_campaign(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new campaign."""
        try:
            # Validate input data
            errors = CampaignCreateSchema().validate(data)
            if errors:
                raise ValueError(f"Invalid campaign data: {errors}")
            campaign = Campaign(
                name=data['name'],
                description=data.get('description', ''),
                organization_id=data.get('organization_id'),
                status=CampaignStatus.CREATED,
                fileName=data['fileName'],
                totalRecords=data['totalRecords'],
                url=data['url']
            )
            
            db.session.add(campaign)
            db.session.commit()

            # Create Instantly campaign
            try:
                instantly_service = InstantlyService()
                instantly_response = instantly_service.create_campaign(name=campaign.name)
                instantly_campaign_id = instantly_response.get('id')
                if instantly_campaign_id:
                    campaign.instantly_campaign_id = instantly_campaign_id
                    db.session.commit()
                else:
                    app_logger.error(f"Instantly campaign creation failed: {instantly_response}")
            except Exception as e:
                app_logger.error(f"Error calling InstantlyService.create_campaign: {str(e)}")

            campaign_dict = campaign.to_dict()
            # Validate output data
            errors = CampaignSchema().validate(campaign_dict)
            if errors:
                raise ValueError(f"Invalid campaign data: {errors}")
                
            return campaign_dict
        except Exception as e:
            app_logger.error(f'Error creating campaign: {str(e)}', exc_info=True)
            db.session.rollback()
            raise

    def validate_search_url(self, url: str) -> bool:
        """Validate Apollo search URL."""
        logger.info(f"Validating search URL: {url}")
        
        if not url:
            logger.error(CAMPAIGN_ERRORS['INVALID_SEARCH_URL'])
            raise ValueError(CAMPAIGN_ERRORS['INVALID_SEARCH_URL'])
        
        if not isinstance(url, str):
            logger.error(CAMPAIGN_ERRORS['INVALID_SEARCH_URL'])
            raise ValueError(CAMPAIGN_ERRORS['INVALID_SEARCH_URL'])
        
        # Basic URL validation
        if not url.startswith('https://app.apollo.io/'):
            logger.error(CAMPAIGN_ERRORS['INVALID_SEARCH_URL'])
            raise ValueError(CAMPAIGN_ERRORS['INVALID_SEARCH_URL'])
        
        # Check for malicious URLs
        if re.search(r'[<>{}|\^~\[\]`]', url):
            logger.error(CAMPAIGN_ERRORS['MALICIOUS_URL'])
            raise ValueError(CAMPAIGN_ERRORS['MALICIOUS_URL'])
        
        return True

    def validate_count(self, count: int) -> bool:
        """Validate the count parameter."""
        logger.info(f"Validating count parameter: {count}")
        
        if not isinstance(count, int):
            logger.error(CAMPAIGN_ERRORS['INVALID_COUNT'])
            raise ValueError(CAMPAIGN_ERRORS['INVALID_COUNT'])
        
        if count <= 0:
            logger.error(CAMPAIGN_ERRORS['INVALID_COUNT'])
            raise ValueError(CAMPAIGN_ERRORS['INVALID_COUNT'])
        
        if count > 1000:
            logger.error(CAMPAIGN_ERRORS['INVALID_COUNT'])
            raise ValueError(CAMPAIGN_ERRORS['INVALID_COUNT'])
        
        return True

    def validate_job_result(self, result: Dict[str, Any]) -> bool:
        """Validate job result format."""
        if not isinstance(result, dict):
            raise ValueError("Job result must be a dictionary")
        return True

    def start_campaign(self, campaign_id: str) -> Dict[str, Any]:
        """Start a campaign."""
        try:
            logger.info(f"Starting campaign process for campaign_id={campaign_id}")

            campaign = Campaign.query.get(campaign_id)
            if not campaign:
                logger.error(f"Campaign {campaign_id} not found during start.")
                raise ValueError(f"Campaign {campaign_id} not found")

            if campaign.status != CampaignStatus.CREATED:
                logger.error(f"Cannot start campaign {campaign_id} in status {campaign.status}")
                raise ValueError(f"Cannot start campaign in {campaign.status} status")

            try:
                # Update campaign status to FETCHING_LEADS
                campaign.update_status(CampaignStatus.FETCHING_LEADS)
                logger.info(f"Campaign {campaign_id} status updated to FETCHING_LEADS")

                job_params = {
                    'fileName': campaign.fileName,
                    'totalRecords': campaign.totalRecords,
                    'url': campaign.url
                }
                logger.info(f"Creating fetch_leads job for campaign {campaign_id} with params: {job_params}")

                # Create fetch leads job
                fetch_leads_job = Job.create(
                    campaign_id=campaign_id,
                    job_type='FETCH_LEADS',
                    parameters=job_params
                )
                logger.info(f"Created fetch_leads job with id={fetch_leads_job.id} for campaign {campaign_id}")

                # Validate job data
                job_dict = fetch_leads_job.to_dict()
                errors = JobSchema().validate(job_dict)
                if errors:
                    logger.error(f"Invalid job data for job {fetch_leads_job.id}: {errors}")
                    raise ValueError(f"Invalid job data: {errors}")

                # Commit transaction
                db.session.commit()

                # Enqueue Apollo scraping and lead saving as a background job
                logger.info(f"Enqueuing fetch_and_save_leads_task for campaign {campaign_id}")
                enqueue_fetch_and_save_leads(job_params, campaign_id)

                # Return campaign data immediately
                campaign_dict = campaign.to_dict()
                # Validate campaign data
                errors = CampaignSchema().validate(campaign_dict)
                if errors:
                    logger.error(f"Invalid campaign data after enqueuing fetch leads for campaign {campaign_id}: {errors}")
                    raise ValueError(f"Invalid campaign data: {errors}")

                return campaign_dict

            except Exception as e:
                logger.error(f"Error starting campaign {campaign_id}: {str(e)}", exc_info=True)
                db.session.rollback()
                campaign.update_status(CampaignStatus.FAILED, error_message=str(e))
                db.session.commit()
                raise

        except Exception as e:
            logger.error(f"Error starting campaign (outer): {str(e)}", exc_info=True)
            raise

    def handle_job_completion(self, job_id: str, result: Dict[str, Any]) -> None:
        """Handle job completion and update campaign status."""
        try:
            logger.info(f"Handling completion for job {job_id}")
            
            # Start a new transaction
            db.session.begin_nested()
            
            # Get job and validate
            job = Job.query.get(job_id)
            if not job:
                error_msg = JOB_ERRORS['JOB_NOT_FOUND'].format(job_id=job_id)
                logger.error(error_msg)
                raise ValueError(error_msg)

            # Get campaign early to ensure it exists
            campaign = Campaign.query.get(job.campaign_id)
            if not campaign:
                error_msg = CAMPAIGN_ERRORS['CAMPAIGN_NOT_FOUND'].format(campaign_id=job.campaign_id)
                logger.error(error_msg)
                db.session.rollback()
                raise ValueError(error_msg)

            # Validate job result
            try:
                Job.validate_result(job.job_type, result)
            except ValueError as e:
                logger.error(f"Invalid job result format for job {job_id}: {str(e)}")
                job.status = 'FAILED'
                job.error = str(e)
                campaign.update_status(
                    CampaignStatus.FAILED,
                    error_message=str(e)
                )
                db.session.commit()
                return

            # Update job with result in a single transaction
            try:
                job.status = 'COMPLETED'
                job.result = result
                job.ended_at = datetime.utcnow()
                if job.started_at:
                    job.execution_time = (job.ended_at - job.started_at).total_seconds()
                
                # Update campaign status based on job type
                if job.status == 'COMPLETED':
                    campaign.update_status(CampaignStatus.COMPLETED)
                elif job.status == 'FAILED':
                    campaign.update_status(CampaignStatus.FAILED, error_message=job.error)
                
                # Commit the transaction
                db.session.commit()
                logger.info(f"Successfully handled completion for job {job_id}")
                
            except Exception as e:
                logger.error(f"Error updating job and campaign status: {str(e)}")
                db.session.rollback()
                
                # Set job and campaign to failed state
                try:
                    db.session.begin_nested()
                    job.status = 'FAILED'
                    job.error = str(e)
                    campaign.update_status(
                        CampaignStatus.FAILED,
                        error_message=f"Failed to update job status: {str(e)}"
                    )
                    db.session.commit()
                except Exception as inner_e:
                    logger.error(f"Error setting failure state: {str(inner_e)}")
                    db.session.rollback()
                raise
            
        except Exception as e:
            logger.error(f"Error handling job completion: {str(e)}", exc_info=True)
            db.session.rollback()
            raise


    def cleanup_campaign_jobs(self, campaign_id: str, days: int) -> Dict[str, Any]:
        """Clean up old jobs for a campaign."""
        try:
            logger.info(f"Cleaning up jobs for campaign {campaign_id} older than {days} days")

            # Get campaign with lock
            campaign = Campaign.query.with_for_update().get(campaign_id)
            if not campaign:
                error_msg = CAMPAIGN_ERRORS['CAMPAIGN_NOT_FOUND'].format(campaign_id=campaign_id)
                logger.error(error_msg)
                raise ValueError(error_msg)

            # Calculate cutoff date
            cutoff_date = datetime.utcnow() - timedelta(days=days)

            # Get jobs to delete
            jobs = Job.query.filter(
                Job.campaign_id == campaign_id,
                Job.created_at < cutoff_date,
                Job.status.in_(['completed', 'failed'])
            ).all()

            # Delete jobs
            for job in jobs:
                db.session.delete(job)

            # Commit changes
            db.session.commit()

            return {
                'message': f'Successfully cleaned up {len(jobs)} jobs',
                'jobs_deleted': len(jobs)
            }

        except Exception as e:
            db.session.rollback()
            error_msg = f"Error cleaning up campaign jobs: {str(e)}"
            logger.error(error_msg, exc_info=True)
            raise

    def update_campaign(self, campaign_id: str, update_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update campaign properties and return updated campaign."""
        campaign = Campaign.query.get(campaign_id)
        if not campaign:
            raise ValueError(f"Campaign {campaign_id} not found")
        for k, v in update_data.items():
            setattr(campaign, k, v)
        db.session.commit()
        return campaign.to_dict()

    def get_campaign_lead_stats(self, campaign_id: str) -> Dict[str, int]:
        """Return stats for a campaign's leads, with an optional error message."""
        try:
            total_leads = Lead.query.filter_by(campaign_id=campaign_id).count()
            leads_with_email = Lead.query.filter(Lead.campaign_id == campaign_id, Lead.email != None).count()
            leads_with_verified_email = Lead.query.filter(
                Lead.campaign_id == campaign_id,
                Lead.email_verification != None,
                Lead.email_verification.op('->>')('result') == 'ok'
            ).count()
            leads_with_enrichment = Lead.query.filter(
                Lead.campaign_id == campaign_id,
                Lead.enrichment_results != None
            ).count()
            leads_with_email_copy = Lead.query.filter(
                Lead.campaign_id == campaign_id,
                Lead.email_copy_gen_results != None
            ).count()
            leads_with_instantly_record = Lead.query.filter(
                Lead.campaign_id == campaign_id,
                Lead.instantly_lead_record != None
            ).count()
            return {
                'total_leads_fetched': total_leads,
                'leads_with_email': leads_with_email,
                'leads_with_verified_email': leads_with_verified_email,
                'leads_with_enrichment': leads_with_enrichment,
                'leads_with_email_copy': leads_with_email_copy,
                'leads_with_instantly_record': leads_with_instantly_record,
                'error_message': None
            }
        except Exception as e:
            error_str = f"Error in get_campaign_lead_stats for campaign {campaign_id}: {str(e)}"
            app_logger.error(error_str, exc_info=True)
            return {
                'total_leads_fetched': 0,
                'leads_with_email': 0,
                'leads_with_verified_email': 0,
                'leads_with_enrichment': 0,
                'leads_with_email_copy': 0,
                'leads_with_instantly_record': 0,
                'error_message': error_str
            }

    def get_campaign_instantly_analytics(self, campaign) -> dict:
        """
        Fetch and map Instantly analytics overview for a campaign.
        :param campaign: campaign dict (from to_dict())
        :return: dict with mapped analytics fields, or error
        """
        instantly_campaign_id = campaign.get('instantly_campaign_id')
        if not instantly_campaign_id:
            return {"error": "No Instantly campaign ID associated with this campaign."}
        instantly_service = InstantlyService()
        # Optionally, you could pass start_date, end_date, campaign_status from campaign or params
        analytics = instantly_service.get_campaign_analytics_overview(instantly_campaign_id)
        if 'error' in analytics:
            return {"error": analytics['error']}
        # Map Instantly analytics response to required fields
        mapped = {
            "leads_count": analytics.get("leads_count"),  # This may need to be mapped from another field
            "contacted_count": analytics.get("contacted_count"),  # This may need to be mapped from another field
            "emails_sent_count": analytics.get("emails_sent_count"),
            "open_count": analytics.get("open_count"),
            "link_click_count": analytics.get("link_click_count"),
            "reply_count": analytics.get("reply_count"),
            "bounced_count": analytics.get("bounced_count"),
            "unsubscribed_count": analytics.get("unsubscribed_count"),
            "completed_count": analytics.get("completed_count"),
            "new_leads_contacted_count": analytics.get("new_leads_contacted_count"),
            "total_opportunities": analytics.get("total_opportunities"),
            # Campaign status info
            "campaign_name": campaign.get("name"),
            "campaign_id": campaign.get("id"),
            "campaign_status": campaign.get("status"),
            "campaign_is_evergreen": analytics.get("is_evergreen", False),
        }
        # Fallbacks for missing fields
        if mapped["leads_count"] is None:
            mapped["leads_count"] = campaign.get("totalRecords")
        if mapped["contacted_count"] is None:
            mapped["contacted_count"] = analytics.get("new_leads_contacted_count")
        return mapped 
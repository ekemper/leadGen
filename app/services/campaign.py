from typing import Dict, Any, Optional, List
import re
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func
from fastapi import HTTPException, status

from app.models.campaign import Campaign
from app.models.campaign_status import CampaignStatus
from app.models.job import Job, JobStatus, JobType
from app.schemas.campaign import CampaignCreate, CampaignUpdate, CampaignStart
from app.core.logger import get_logger
from app.core.config import get_redis_connection
from app.core.dependencies import get_apollo_rate_limiter, get_instantly_rate_limiter
from app.core.circuit_breaker import ThirdPartyService, get_circuit_breaker

try:
    from app.background_services.apollo_service import ApolloService
except ImportError:
    ApolloService = None
    
try:
    from app.background_services.instantly_service import InstantlyService
except ImportError:
    InstantlyService = None


logger = get_logger(__name__)


class CampaignService:
    """Service for managing campaign business logic."""
    
    def __init__(self):
        """
        Initialize CampaignService with rate-limited services.
        Services are initialized with rate limiting if available.
        """
        try:
            if ApolloService:
                redis_client = get_redis_connection()
                apollo_rate_limiter = get_apollo_rate_limiter(redis_client)
                self.apollo_service = ApolloService(rate_limiter=apollo_rate_limiter)
            else:
                self.apollo_service = None
        except Exception as e:
            logger.warning(f"Failed to initialize ApolloService with rate limiting: {str(e)}")
            self.apollo_service = None
            
        try:
            if InstantlyService:
                redis_client = get_redis_connection()
                instantly_rate_limiter = get_instantly_rate_limiter(redis_client)
                self.instantly_service = InstantlyService(rate_limiter=instantly_rate_limiter)
            else:
                self.instantly_service = None
        except Exception as e:
            logger.warning(f"Failed to initialize InstantlyService with rate limiting: {str(e)}")
            self.instantly_service = None

    async def get_campaigns(self, db: Session, organization_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get all campaigns with latest job information, optionally filtered by organization."""
        try:
            if organization_id:
                logger.info(f'Fetching campaigns for organization {organization_id}')
                
                # Validate organization exists
                from app.models.organization import Organization
                organization = db.query(Organization).filter(
                    Organization.id == organization_id
                ).first()
                if not organization:
                    logger.warning(f'Organization {organization_id} not found during campaign fetch')
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Organization {organization_id} not found"
                    )
                
                campaigns = (
                    db.query(Campaign)
                    .filter(Campaign.organization_id == organization_id)
                    .order_by(Campaign.created_at.desc())
                    .all()
                )
            else:
                logger.info('Fetching all campaigns')
                campaigns = db.query(Campaign).order_by(Campaign.created_at.desc()).all()
            
            logger.info(f'Found {len(campaigns)} campaigns')
            
            campaign_list = []
            for campaign in campaigns:
                try:
                    campaign_dict = campaign.to_dict()
                    
                    # Get latest job status for each campaign
                    latest_job = (
                        db.query(Job)
                        .filter_by(campaign_id=campaign.id)
                        .order_by(Job.created_at.desc())
                        .first()
                    )
                    if latest_job:
                        campaign_dict['latest_job'] = {
                            'id': latest_job.id,
                            'status': latest_job.status.value,
                            'created_at': latest_job.created_at.isoformat() if latest_job.created_at else None,
                            'completed_at': latest_job.completed_at.isoformat() if latest_job.completed_at else None,
                            'error': latest_job.error
                        }
                    else:
                        campaign_dict['latest_job'] = None
                        
                    campaign_list.append(campaign_dict)
                except Exception as e:
                    logger.error(f'Error converting campaign {campaign.id} to dict: {str(e)}', exc_info=True)
                    continue
            
            logger.info(f'Successfully converted {len(campaign_list)} campaigns to dict')
            return campaign_list
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f'Error getting campaigns: {str(e)}', exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error fetching campaigns: {str(e)}"
            )

    async def get_campaign(self, campaign_id: str, db: Session) -> Dict[str, Any]:
        """Get a single campaign by ID."""
        try:
            logger.info(f'Fetching campaign {campaign_id}')
            
            campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
            if not campaign:
                logger.warning(f'Campaign {campaign_id} not found')
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Campaign {campaign_id} not found"
                )
            
            campaign_dict = campaign.to_dict()
            
            # Get all jobs for this campaign (empty for now as per original logic)
            campaign_dict['jobs'] = []
            
            logger.info(f'Successfully fetched campaign {campaign_id}')
            return campaign_dict
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f'Error getting campaign: {str(e)}', exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error fetching campaign: {str(e)}"
            )

    async def create_campaign(self, campaign_data: CampaignCreate, db: Session) -> Dict[str, Any]:
        """Create a new campaign with organization validation and global pause state checking."""
        try:
            logger.info(f'Creating campaign: {campaign_data.name}')
            
            # Validate organization exists
            from app.models.organization import Organization
            organization = db.query(Organization).filter(
                Organization.id == campaign_data.organization_id
            ).first()
            if not organization:
                logger.warning(f'Organization {campaign_data.organization_id} not found during campaign creation')
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Organization {campaign_data.organization_id} not found"
                )
            
            # Check global pause state - warn about service availability but allow creation
            circuit_breaker = get_circuit_breaker()
            required_services = [
                ThirdPartyService.APOLLO,
                ThirdPartyService.PERPLEXITY,
                ThirdPartyService.OPENAI,
                ThirdPartyService.INSTANTLY,
                ThirdPartyService.MILLIONVERIFIER
            ]
            
            unavailable_services = []
            for service in required_services:
                allowed, reason = circuit_breaker.should_allow_request(service)
                if not allowed:
                    unavailable_services.append(f"{service.value} ({reason})")
            
            # Create campaign regardless of service availability
            campaign = Campaign(
                name=campaign_data.name,
                description=campaign_data.description or '',
                organization_id=campaign_data.organization_id,
                status=CampaignStatus.CREATED,
                fileName=campaign_data.fileName,
                totalRecords=campaign_data.totalRecords,
                url=campaign_data.url
            )
            
            # Add status message if services are unavailable
            if unavailable_services:
                warning_msg = f"Campaign created successfully. Note: Some services are currently unavailable: {', '.join(unavailable_services)}. The campaign can be started once services recover."
                campaign.status_message = warning_msg
                logger.warning(f"Campaign {campaign_data.name} created with service availability warning: {warning_msg}")
            else:
                campaign.status_message = "Campaign created successfully. All services are available."
            
            db.add(campaign)
            db.commit()
            db.refresh(campaign)

            # Create Instantly campaign only if service is available
            if self.instantly_service and not any("instantly" in svc.lower() for svc in unavailable_services):
                try:
                    instantly_response = self.instantly_service.create_campaign(name=campaign.name)
                    instantly_campaign_id = instantly_response.get('id')
                    if instantly_campaign_id:
                        campaign.instantly_campaign_id = instantly_campaign_id
                        db.commit()
                        logger.info(f"Created Instantly campaign with ID: {instantly_campaign_id}")
                    else:
                        logger.error(f"Instantly campaign creation failed: {instantly_response}")
                except Exception as e:
                    logger.error(f"Error calling InstantlyService.create_campaign: {str(e)}")
                    # Update campaign status message to reflect Instantly service issue
                    campaign.status_message = f"{campaign.status_message} Warning: Instantly campaign creation failed."
                    db.commit()
            else:
                if not self.instantly_service:
                    logger.warning("InstantlyService not available, skipping campaign creation")
                else:
                    logger.warning("Instantly service is paused, skipping campaign creation")

            logger.info(f'Successfully created campaign {campaign.id}')
            return campaign.to_dict()
            
        except HTTPException:
            raise
        except Exception as e:
            db.rollback()
            logger.error(f'Error creating campaign: {str(e)}', exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error creating campaign: {str(e)}"
            )

    async def update_campaign(self, campaign_id: str, update_data: CampaignUpdate, db: Session) -> Dict[str, Any]:
        """Update campaign properties and return updated campaign."""
        try:
            campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
            if not campaign:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Campaign {campaign_id} not found"
                )
            
            # Update only provided fields
            update_dict = update_data.model_dump(exclude_unset=True)
            
            # Validate organization exists if organization_id is being updated
            if 'organization_id' in update_dict:
                from app.models.organization import Organization
                organization = db.query(Organization).filter(
                    Organization.id == update_dict['organization_id']
                ).first()
                if not organization:
                    logger.warning(f'Organization {update_dict["organization_id"]} not found during campaign update')
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Organization {update_dict['organization_id']} not found"
                    )
            
            for field, value in update_dict.items():
                setattr(campaign, field, value)
            
            db.commit()
            db.refresh(campaign)
            
            logger.info(f'Successfully updated campaign {campaign_id}')
            return campaign.to_dict()
            
        except HTTPException:
            raise
        except Exception as e:
            db.rollback()
            logger.error(f'Error updating campaign: {str(e)}', exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error updating campaign: {str(e)}"
            )

    async def start_campaign(self, campaign_id: str, start_data: CampaignStart, db: Session) -> Dict[str, Any]:
        """Start a campaign process with enhanced business rule validation."""
        try:
            logger.info(f"Starting campaign process for campaign_id={campaign_id}")

            campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
            if not campaign:
                logger.error(f"Campaign {campaign_id} not found during start.")
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Campaign {campaign_id} not found"
                )

            # Enhanced validation using the comprehensive validation method
            validation_results = self.validate_campaign_start_prerequisites(campaign)
            
            if not validation_results["can_start"]:
                error_details = {
                    "message": "Cannot start campaign due to validation failures",
                    "errors": validation_results["errors"],
                    "warnings": validation_results["warnings"],
                    "validation_details": validation_results["validation_details"]
                }
                
                # Log detailed validation failure
                logger.error(f"Campaign {campaign_id} start validation failed: {error_details}")
                
                # Return appropriate HTTP status based on the type of failure
                if any("paused" in error.lower() for error in validation_results["errors"]):
                    status_code = status.HTTP_409_CONFLICT  # Conflict due to paused state
                elif any("unavailable" in error.lower() for error in validation_results["errors"]):
                    status_code = status.HTTP_503_SERVICE_UNAVAILABLE  # Service unavailable
                else:
                    status_code = status.HTTP_400_BAD_REQUEST  # General validation error
                
                raise HTTPException(
                    status_code=status_code,
                    detail=error_details
                )

            # Log warnings if any (but allow campaign to start)
            if validation_results["warnings"]:
                logger.warning(f"Campaign {campaign_id} starting with warnings: {validation_results['warnings']}")

            # Validate URL and count (existing validation)
            self.validate_search_url(campaign.url)
            self.validate_count(campaign.totalRecords)

            # Update campaign status to RUNNING
            success_message = "Starting campaign process"
            if validation_results["warnings"]:
                success_message += f" (with warnings: {', '.join(validation_results['warnings'])})"
                
            campaign.update_status(CampaignStatus.RUNNING, success_message)
            db.commit()
            logger.info(f"Campaign {campaign_id} status updated to RUNNING")

            job_params = {
                'fileName': campaign.fileName,
                'totalRecords': campaign.totalRecords,
                'url': campaign.url
            }
            logger.info(f"Creating fetch_leads job for campaign {campaign_id} with params: {job_params}")

            # Create fetch leads job
            fetch_leads_job = Job(
                campaign_id=campaign_id,
                name='FETCH_LEADS',
                description=f'Fetch leads for campaign {campaign.name}',
                job_type=JobType.FETCH_LEADS,
                status=JobStatus.PENDING
            )
            db.add(fetch_leads_job)
            db.commit()
            db.refresh(fetch_leads_job)
            
            logger.info(f"Created fetch_leads job with id={fetch_leads_job.id} for campaign {campaign_id}")

            # Enqueue Apollo scraping and lead saving as a background job
            logger.info(f"Enqueuing fetch_and_save_leads_task for campaign {campaign_id}")
            from app.workers.campaign_tasks import fetch_and_save_leads_task
            task = fetch_and_save_leads_task.delay(job_params, campaign_id, fetch_leads_job.id)
            
            # Update job with task ID
            fetch_leads_job.task_id = task.id
            db.commit()

            logger.info(f'Successfully started campaign {campaign_id}')
            
            # Return campaign data with validation info
            campaign_dict = campaign.to_dict()
            campaign_dict['start_validation'] = {
                'warnings': validation_results["warnings"],
                'services_checked': list(validation_results["validation_details"].get("services", {}).keys())
            }
            
            return campaign_dict

        except HTTPException:
            raise
        except Exception as e:
            db.rollback()
            logger.error(f"Error starting campaign {campaign_id}: {str(e)}", exc_info=True)
            
            # Update campaign status to failed
            try:
                campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
                if campaign:
                    campaign.update_status(CampaignStatus.FAILED, status_error=str(e))
                    db.commit()
            except Exception as inner_e:
                logger.error(f"Error updating campaign status to failed: {str(inner_e)}")
            
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error starting campaign: {str(e)}"
            )

    def validate_search_url(self, url: str) -> bool:
        """Validate Apollo search URL."""
        logger.info(f"Validating search URL: {url}")
        
        if not url:
            error_msg = "Search URL is required"
            logger.error(error_msg)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_msg
            )
        
        if not isinstance(url, str):
            error_msg = "Search URL must be a string"
            logger.error(error_msg)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_msg
            )
        
        # Basic URL validation
        if not url.startswith('https://app.apollo.io/'):
            error_msg = "Invalid Apollo search URL format"
            logger.error(error_msg)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_msg
            )
        
        # Check for malicious URLs
        if re.search(r'[<>{}|\^~\[\]`]', url):
            error_msg = "URL contains invalid characters"
            logger.error(error_msg)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_msg
            )
        
        return True

    def validate_count(self, count: int) -> bool:
        """Validate the count parameter."""
        logger.info(f"Validating count parameter: {count}")
        
        if not isinstance(count, int):
            error_msg = "Count must be an integer"
            logger.error(error_msg)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_msg
            )
        
        if count <= 0:
            error_msg = "Count must be greater than 0"
            logger.error(error_msg)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_msg
            )
        
        if count > 1000:
            error_msg = "Count cannot exceed 1000"
            logger.error(error_msg)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_msg
            )
        
        return True

    async def cleanup_campaign_jobs(self, campaign_id: str, days: int, db: Session) -> Dict[str, Any]:
        """Clean up old jobs for a campaign using background task."""
        try:
            logger.info(f"Initiating cleanup for campaign {campaign_id} older than {days} days")

            # Get campaign to verify it exists
            campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
            if not campaign:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Campaign {campaign_id} not found"
                )

            # Queue cleanup task
            from app.workers.campaign_tasks import cleanup_campaign_jobs_task
            task = cleanup_campaign_jobs_task.delay(campaign_id, days)

            logger.info(f"Queued cleanup task {task.id} for campaign {campaign_id}")
            return {
                'message': f'Cleanup task queued for campaign {campaign_id}',
                'task_id': task.id,
                'status': 'queued'
            }

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error queueing cleanup task: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error queueing cleanup task: {str(e)}"
            )

    async def get_campaign_lead_stats(self, campaign_id: str, db: Session) -> "CampaignLeadStats":
        """Return stats for a campaign's leads."""
        try:
            # Check if campaign exists
            campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
            if not campaign:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Campaign {campaign_id} not found"
                )

            # Note: Lead model is not yet implemented in this FastAPI app
            # This is a placeholder that returns zero stats
            # TODO: Implement Lead model and actual lead statistics
            
            from app.schemas.campaign import CampaignLeadStats
            return CampaignLeadStats(
                total_leads_fetched=0,
                leads_with_email=0,
                leads_with_verified_email=0,
                leads_with_enrichment=0,
                leads_with_email_copy=0,
                leads_with_instantly_record=0,
                error_message=None
            )
            
        except HTTPException:
            raise
        except Exception as e:
            error_str = f"Error in get_campaign_lead_stats for campaign {campaign_id}: {str(e)}"
            logger.error(error_str, exc_info=True)
            from app.schemas.campaign import CampaignLeadStats
            return CampaignLeadStats(
                total_leads_fetched=0,
                leads_with_email=0,
                leads_with_verified_email=0,
                leads_with_enrichment=0,
                leads_with_email_copy=0,
                leads_with_instantly_record=0,
                error_message=error_str
            )

    async def get_campaign_instantly_analytics(self, campaign_id: str, db: Session) -> "InstantlyAnalytics":
        """Fetch and map Instantly analytics overview for a campaign."""
        try:
            # Get campaign
            campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
            if not campaign:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Campaign {campaign_id} not found"
                )
            
            campaign_dict = campaign.to_dict()
            instantly_campaign_id = campaign_dict.get('instantly_campaign_id')
            
            from app.schemas.campaign import InstantlyAnalytics
            
            if not instantly_campaign_id:
                return InstantlyAnalytics(
                    leads_count=campaign_dict.get("totalRecords"),
                    contacted_count=None,
                    emails_sent_count=None,
                    open_count=None,
                    link_click_count=None,
                    reply_count=None,
                    bounced_count=None,
                    unsubscribed_count=None,
                    completed_count=None,
                    new_leads_contacted_count=None,
                    total_opportunities=None,
                    campaign_name=campaign_dict.get("name"),
                    campaign_id=campaign_dict.get("id"),
                    campaign_status=campaign_dict.get("status"),
                    campaign_is_evergreen=False,
                    error="No Instantly campaign ID associated with this campaign."
                )
            
            # Fetch analytics from Instantly
            if not self.instantly_service:
                return InstantlyAnalytics(
                    leads_count=campaign_dict.get("totalRecords"),
                    contacted_count=None,
                    emails_sent_count=None,
                    open_count=None,
                    link_click_count=None,
                    reply_count=None,
                    bounced_count=None,
                    unsubscribed_count=None,
                    completed_count=None,
                    new_leads_contacted_count=None,
                    total_opportunities=None,
                    campaign_name=campaign_dict.get("name"),
                    campaign_id=campaign_dict.get("id"),
                    campaign_status=campaign_dict.get("status"),
                    campaign_is_evergreen=False,
                    error="InstantlyService not available"
                )
                
            analytics = self.instantly_service.get_campaign_analytics_overview(instantly_campaign_id)
            if 'error' in analytics:
                return InstantlyAnalytics(
                    leads_count=campaign_dict.get("totalRecords"),
                    contacted_count=None,
                    emails_sent_count=None,
                    open_count=None,
                    link_click_count=None,
                    reply_count=None,
                    bounced_count=None,
                    unsubscribed_count=None,
                    completed_count=None,
                    new_leads_contacted_count=None,
                    total_opportunities=None,
                    campaign_name=campaign_dict.get("name"),
                    campaign_id=campaign_dict.get("id"),
                    campaign_status=campaign_dict.get("status"),
                    campaign_is_evergreen=False,
                    error=analytics['error']
                )
            
            # Map Instantly analytics response to required fields
            return InstantlyAnalytics(
                leads_count=analytics.get("leads_count") or campaign_dict.get("totalRecords"),
                contacted_count=analytics.get("contacted_count") or analytics.get("new_leads_contacted_count"),
                emails_sent_count=analytics.get("emails_sent_count"),
                open_count=analytics.get("open_count"),
                link_click_count=analytics.get("link_click_count"),
                reply_count=analytics.get("reply_count"),
                bounced_count=analytics.get("bounced_count"),
                unsubscribed_count=analytics.get("unsubscribed_count"),
                completed_count=analytics.get("completed_count"),
                new_leads_contacted_count=analytics.get("new_leads_contacted_count"),
                total_opportunities=analytics.get("total_opportunities"),
                # Campaign status info
                campaign_name=campaign_dict.get("name"),
                campaign_id=campaign_dict.get("id"),
                campaign_status=campaign_dict.get("status"),
                campaign_is_evergreen=analytics.get("is_evergreen", False),
                error=None
            )
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error getting campaign analytics: {str(e)}", exc_info=True)
            from app.schemas.campaign import InstantlyAnalytics
            return InstantlyAnalytics(
                leads_count=None,
                contacted_count=None,
                emails_sent_count=None,
                open_count=None,
                link_click_count=None,
                reply_count=None,
                bounced_count=None,
                unsubscribed_count=None,
                completed_count=None,
                new_leads_contacted_count=None,
                total_opportunities=None,
                campaign_name=None,
                campaign_id=campaign_id,
                campaign_status=None,
                campaign_is_evergreen=False,
                error=f"Error fetching campaign analytics: {str(e)}"
            )

    # Campaign Pausing/Resuming Methods
    
    async def pause_campaign(self, campaign_id: str, reason: str, db: Session) -> Dict[str, Any]:
        """Pause a running campaign with reason tracking."""
        try:
            logger.info(f"Pausing campaign {campaign_id} with reason: {reason}")
            
            # Get campaign
            campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
            if not campaign:
                logger.warning(f"Campaign {campaign_id} not found during pause")
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Campaign {campaign_id} not found"
                )
            
            # Check if campaign can be paused
            if campaign.status != CampaignStatus.RUNNING:
                logger.warning(f"Cannot pause campaign {campaign_id} in status {campaign.status}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Cannot pause campaign in {campaign.status.value} status. Only running campaigns can be paused."
                )
            
            # Pause the campaign using the model method
            success = campaign.pause(reason)
            if not success:
                logger.error(f"Failed to pause campaign {campaign_id}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to pause campaign due to invalid state transition"
                )
            
            db.commit()
            logger.info(f"Successfully paused campaign {campaign_id}")
            
            return {
                "id": campaign.id,
                "status": campaign.status.value,
                "status_message": campaign.status_message,
                "message": f"Campaign {campaign_id} has been paused"
            }
            
        except HTTPException:
            raise
        except Exception as e:
            db.rollback()
            logger.error(f"Error pausing campaign {campaign_id}: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error pausing campaign: {str(e)}"
            )
    
    async def resume_campaign(self, campaign_id: str, db: Session) -> Dict[str, Any]:
        """Resume a paused campaign."""
        try:
            logger.info(f"Resuming campaign {campaign_id}")
            
            # Get campaign
            campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
            if not campaign:
                logger.warning(f"Campaign {campaign_id} not found during resume")
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Campaign {campaign_id} not found"
                )
            
            # Check if campaign can be resumed
            if campaign.status != CampaignStatus.PAUSED:
                logger.warning(f"Cannot resume campaign {campaign_id} in status {campaign.status}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Cannot resume campaign in {campaign.status.value} status. Only paused campaigns can be resumed."
                )
            
            # Check circuit breaker status before resuming
            circuit_breaker = get_circuit_breaker()
            
            # Check all services that this campaign might depend on
            required_services = [
                ThirdPartyService.APOLLO,      # For lead fetching
                ThirdPartyService.PERPLEXITY,  # For enrichment
                ThirdPartyService.OPENAI,      # For email copy
                ThirdPartyService.INSTANTLY,   # For lead creation
                ThirdPartyService.MILLIONVERIFIER  # For email verification
            ]
            
            blocked_services = []
            for service in required_services:
                allowed, reason = circuit_breaker.should_allow_request(service)
                if not allowed:
                    blocked_services.append((service.value, reason))
            
            if blocked_services:
                service_list = ", ".join([f"{svc} ({reason})" for svc, reason in blocked_services])
                error_msg = f"Cannot resume campaign: Required services are unavailable: {service_list}"
                logger.warning(error_msg)
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=error_msg
                )
            
            # Resume the campaign using the model method
            success = campaign.resume("Campaign resumed - services are available")
            if not success:
                logger.error(f"Failed to resume campaign {campaign_id}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to resume campaign due to invalid state transition"
                )
            
            db.commit()
            logger.info(f"Successfully resumed campaign {campaign_id}")
            
            return {
                "id": campaign.id,
                "status": campaign.status.value,
                "status_message": campaign.status_message,
                "message": f"Campaign {campaign_id} has been resumed"
            }
            
        except HTTPException:
            raise
        except Exception as e:
            db.rollback()
            logger.error(f"Error resuming campaign {campaign_id}: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error resuming campaign: {str(e)}"
            )
    
    async def pause_campaigns_for_service(self, service: ThirdPartyService, reason: str, db: Session) -> int:
        """Pause all running campaigns that depend on a specific service."""
        try:
            logger.info(f"Pausing campaigns dependent on service {service.value} due to: {reason}")
            
            # Get all running campaigns
            running_campaigns = (
                db.query(Campaign)
                .filter(Campaign.status == CampaignStatus.RUNNING)
                .all()
            )
            
            paused_count = 0
            for campaign in running_campaigns:
                try:
                    # All campaigns depend on all services for enrichment pipeline
                    # So we pause all running campaigns when any service goes down
                    pause_reason = f"Service {service.value} unavailable: {reason}"
                    success = campaign.pause(pause_reason)
                    
                    if success:
                        paused_count += 1
                        logger.info(f"Paused campaign {campaign.id} due to service {service.value} failure")
                    else:
                        logger.warning(f"Failed to pause campaign {campaign.id}")
                        
                except Exception as e:
                    logger.error(f"Error pausing individual campaign {campaign.id}: {str(e)}")
                    continue
            
            db.commit()
            logger.info(f"Successfully paused {paused_count} campaigns due to {service.value} service failure")
            return paused_count
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error pausing campaigns for service {service}: {str(e)}", exc_info=True)
            return 0
    
    def can_start_campaign(self, campaign: Campaign) -> tuple[bool, str]:
        """
        Enhanced validation to check if campaign can be started based on status, 
        circuit breaker state, and global pause conditions.
        Returns (can_start, reason).
        """
        # First check campaign model's built-in validation
        can_start, reason = campaign.can_be_started()
        if not can_start:
            return can_start, reason
        
        # Check if campaign is explicitly paused
        if campaign.status == CampaignStatus.PAUSED:
            return False, "Cannot start paused campaign - resume it first"
        
        # Additional circuit breaker and service availability checks
        try:
            circuit_breaker = get_circuit_breaker()
            
            # Check all services that campaigns depend on
            required_services = [
                ThirdPartyService.APOLLO,
                ThirdPartyService.PERPLEXITY,
                ThirdPartyService.OPENAI,
                ThirdPartyService.INSTANTLY,
                ThirdPartyService.MILLIONVERIFIER
            ]
            
            blocked_services = []
            critical_services_down = []
            
            for service in required_services:
                allowed, circuit_reason = circuit_breaker.should_allow_request(service)
                if not allowed:
                    service_info = f"{service.value} ({circuit_reason})"
                    blocked_services.append(service_info)
                    
                    # Apollo is critical for campaign start (fetch leads)
                    if service == ThirdPartyService.APOLLO:
                        critical_services_down.append(service_info)
            
            # If critical services are down, prevent starting
            if critical_services_down:
                return False, f"Cannot start campaign: Critical service unavailable: {', '.join(critical_services_down)}"
            
            # If any services are blocked, warn but allow (depending on configuration)
            if blocked_services:
                # For now, prevent starting if any required service is down
                # This can be made configurable in the future
                return False, f"Cannot start campaign: Required services unavailable: {', '.join(blocked_services)}"
            
            # Check global queue pause status
            is_globally_paused, pause_reason = self._check_global_pause_status()
            if is_globally_paused:
                return False, f"Cannot start campaign: System is in maintenance mode: {pause_reason}"
            
            return True, "Campaign can be started - all validations passed"
            
        except Exception as e:
            logger.error(f"Error checking campaign start conditions: {str(e)}")
            # If validation checks fail, be conservative and prevent starting
            return False, f"Cannot start campaign: Validation check failed: {str(e)}"

    def _check_global_pause_status(self) -> tuple[bool, str]:
        """
        Check if the system is in a global pause state that should prevent campaign starts.
        Returns (is_paused, reason).
        """
        try:
            circuit_breaker = get_circuit_breaker()
            
            # Check if too many services are down (e.g., more than 50%)
            all_services = list(ThirdPartyService)
            down_services = []
            
            for service in all_services:
                allowed, reason = circuit_breaker.should_allow_request(service)
                if not allowed:
                    down_services.append(service.value)
            
            # If more than half the services are down, consider it a global pause state
            if len(down_services) > len(all_services) / 2:
                return True, f"Too many services unavailable ({len(down_services)}/{len(all_services)}): {', '.join(down_services)}"
            
            # Check for specific critical service combinations
            apollo_down = ThirdPartyService.APOLLO in [s for s in all_services if not circuit_breaker.should_allow_request(s)[0]]
            instantly_down = ThirdPartyService.INSTANTLY in [s for s in all_services if not circuit_breaker.should_allow_request(s)[0]]
            
            if apollo_down and instantly_down:
                return True, "Both Apollo and Instantly services are down - cannot process campaign workflow"
            
            return False, "System is operational"
            
        except Exception as e:
            logger.error(f"Error checking global pause status: {str(e)}")
            # If check fails, assume not paused to avoid false positives
            return False, "Global pause check failed - assuming operational"

    def validate_campaign_start_prerequisites(self, campaign: Campaign) -> Dict[str, Any]:
        """
        Comprehensive validation of campaign start prerequisites.
        Returns detailed validation results for API responses.
        """
        try:
            results = {
                "can_start": False,
                "campaign_status_valid": False,
                "services_available": False,
                "global_state_ok": False,
                "validation_details": {},
                "warnings": [],
                "errors": []
            }
            
            # 1. Campaign status validation
            can_start_model, model_reason = campaign.can_be_started()
            results["campaign_status_valid"] = can_start_model
            results["validation_details"]["campaign_status"] = {
                "current_status": campaign.status.value,
                "can_start": can_start_model,
                "reason": model_reason
            }
            
            if not can_start_model:
                results["errors"].append(f"Campaign status issue: {model_reason}")
            
            # 2. Circuit breaker and service validation
            circuit_breaker = get_circuit_breaker()
            required_services = [
                ThirdPartyService.APOLLO,
                ThirdPartyService.PERPLEXITY,
                ThirdPartyService.OPENAI,
                ThirdPartyService.INSTANTLY,
                ThirdPartyService.MILLIONVERIFIER
            ]
            
            service_status = {}
            unavailable_services = []
            critical_unavailable = []
            
            for service in required_services:
                allowed, reason = circuit_breaker.should_allow_request(service)
                service_status[service.value] = {
                    "available": allowed,
                    "reason": reason if not allowed else "Available"
                }
                
                if not allowed:
                    unavailable_services.append(service.value)
                    if service == ThirdPartyService.APOLLO:  # Critical service
                        critical_unavailable.append(service.value)
            
            results["validation_details"]["services"] = service_status
            results["services_available"] = len(critical_unavailable) == 0
            
            if critical_unavailable:
                results["errors"].append(f"Critical services unavailable: {', '.join(critical_unavailable)}")
            if unavailable_services:
                if set(unavailable_services) - set(critical_unavailable):
                    results["warnings"].append(f"Some services unavailable: {', '.join(set(unavailable_services) - set(critical_unavailable))}")
            
            # 3. Global state validation
            is_globally_paused, pause_reason = self._check_global_pause_status()
            results["global_state_ok"] = not is_globally_paused
            results["validation_details"]["global_state"] = {
                "is_paused": is_globally_paused,
                "reason": pause_reason
            }
            
            if is_globally_paused:
                results["errors"].append(f"Global state issue: {pause_reason}")
            
            # 4. Overall determination
            results["can_start"] = (
                results["campaign_status_valid"] and 
                results["services_available"] and 
                results["global_state_ok"]
            )
            
            return results
            
        except Exception as e:
            logger.error(f"Error validating campaign start prerequisites: {str(e)}")
            return {
                "can_start": False,
                "campaign_status_valid": False,
                "services_available": False,
                "global_state_ok": False,
                "validation_details": {},
                "warnings": [],
                "errors": [f"Validation failed: {str(e)}"]
            }


 
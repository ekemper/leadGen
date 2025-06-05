from typing import Dict, Any, Optional, List
import re
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func
from fastapi import HTTPException, status

from app.models.campaign import Campaign
from app.models.campaign_status import CampaignStatus
from app.models.job import Job, JobStatus, JobType
from app.models.lead import Lead
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
    
    # Required services for campaign operations - all are critical
    REQUIRED_SERVICES = [
        ThirdPartyService.APOLLO,         # Lead fetching (FETCH_LEADS jobs)
        ThirdPartyService.PERPLEXITY,     # Lead enrichment (ENRICH_LEAD jobs)
        ThirdPartyService.OPENAI,         # Email copy generation (ENRICH_LEAD jobs)
        ThirdPartyService.INSTANTLY,      # Lead creation (ENRICH_LEAD jobs)
        ThirdPartyService.MILLIONVERIFIER # Email verification (ENRICH_LEAD jobs)
    ]
    
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
            for campaign in campaigns: #TODO: EK, why are we not doing a join beween jobs and campaigns, this should be done in sql 
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
            logger.info(f"Creating campaign: {campaign_data.name}")
            
            # Check organization exists
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
            
            # Check global circuit breaker state (simplified - no service-specific checks)
            circuit_breaker = get_circuit_breaker()
            circuit_breaker_open = not circuit_breaker.should_allow_request()
            
            # Create campaign regardless of circuit breaker state (can create, may not be startable)
            campaign = Campaign(
                name=campaign_data.name,
                description=campaign_data.description or '',
                organization_id=campaign_data.organization_id,
                status=CampaignStatus.CREATED,
                fileName=campaign_data.fileName,
                totalRecords=campaign_data.totalRecords,
                url=campaign_data.url
            )
            
            # Set status message based on circuit breaker state
            if circuit_breaker_open:
                warning_msg = "Campaign created successfully. Note: Circuit breaker is open - campaign cannot be started until services recover."
                campaign.status_message = warning_msg
                logger.warning(f"Campaign {campaign_data.name} created with circuit breaker open warning")
            else:
                campaign.status_message = "Campaign created successfully. All services are available."
            
            db.add(campaign)
            db.commit()
            db.refresh(campaign)

            # Create Instantly campaign only if circuit breaker is closed
            if self.instantly_service and not circuit_breaker_open:
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
                elif circuit_breaker_open:
                    logger.warning("Circuit breaker is open, skipping Instantly campaign creation")

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

            # Log warnings if any - warnings don't prevent campaign start
            # (errors would have already prevented reaching this point)
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
        """Clean up old jobs for a campaign."""
        try:
            logger.info(f"Cleaning up jobs older than {days} days for campaign {campaign_id}")
            
            from datetime import datetime, timedelta
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            # Get campaign to validate it exists
            campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
            if not campaign:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Campaign {campaign_id} not found"
                )
            
            # Delete old jobs
            deleted_count = db.query(Job).filter(
                Job.campaign_id == campaign_id,
                Job.created_at < cutoff_date
            ).delete()
            
            db.commit()
            
            logger.info(f"Cleaned up {deleted_count} jobs for campaign {campaign_id}")
            
            return {
                "campaign_id": campaign_id,
                "jobs_deleted": deleted_count,
                "cutoff_date": cutoff_date.isoformat(),
                "message": f"Deleted {deleted_count} jobs older than {days} days"
            }
            
        except HTTPException:
            raise
        except Exception as e:
            db.rollback()
            logger.error(f"Error cleaning up jobs for campaign {campaign_id}: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error cleaning up jobs: {str(e)}"
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

    def validate_campaign_start_prerequisites(self, campaign: Campaign) -> Dict[str, Any]:
        """
        Simplified validation of campaign start prerequisites using global circuit breaker only.
        Returns detailed validation results for API responses.
        """
        try:
            results = {
                "can_start": False,
                "campaign_status_valid": False,
                "circuit_breaker_closed": False,
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
            
            # 2. Global circuit breaker validation (simplified)
            circuit_breaker = get_circuit_breaker()
            circuit_breaker_closed = circuit_breaker.should_allow_request()
            
            results["circuit_breaker_closed"] = circuit_breaker_closed
            results["validation_details"]["circuit_breaker"] = {
                "state": "closed" if circuit_breaker_closed else "open",
                "reason": "Services available" if circuit_breaker_closed else "Circuit breaker is open - services unavailable"
            }
            
            if not circuit_breaker_closed:
                results["errors"].append("Circuit breaker is open - services unavailable")
            
            # 3. Overall determination (simplified)
            results["can_start"] = (
                results["campaign_status_valid"] and 
                results["circuit_breaker_closed"]
            )
            
            return results
            
        except Exception as e:
            logger.error(f"Error validating campaign start prerequisites: {str(e)}")
            return {
                "can_start": False,
                "campaign_status_valid": False,
                "circuit_breaker_closed": False,
                "validation_details": {},
                "warnings": [],
                "errors": [f"Validation failed: {str(e)}"]
            }


 
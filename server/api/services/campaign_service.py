from server.models import Campaign
from server.config.database import db
from server.background_services.apollo_service import ApolloService
from server.utils.logging_config import server_logger, combined_logger
from server.models.campaign import CampaignStatus
from typing import Dict, Any, Optional

class CampaignService:
    def __init__(self):
        self.apollo_service = ApolloService()

    def get_campaigns(self):
        """Get all campaigns."""
        try:
            server_logger.info('Fetching all campaigns')
            
            # Ensure we have a valid database session
            if not db.session.is_active:
                server_logger.warning('Database session was not active, creating new session')
                db.session.rollback()
            
            campaigns = Campaign.query.order_by(Campaign.created_at.desc()).all()
            server_logger.info(f'Found {len(campaigns)} campaigns')
            
            campaign_list = []
            for campaign in campaigns:
                try:
                    campaign_dict = campaign.to_dict()
                    campaign_list.append(campaign_dict)
                except Exception as e:
                    server_logger.error(f'Error converting campaign {campaign.id} to dict: {str(e)}', exc_info=True)
                    continue
            
            server_logger.info(f'Successfully converted {len(campaign_list)} campaigns to dict')
            return campaign_list
        except Exception as e:
            server_logger.error(f'Error getting campaigns: {str(e)}', exc_info=True)
            db.session.rollback()
            raise

    def get_campaign(self, campaign_id):
        """Get a single campaign by ID."""
        try:
            campaign = Campaign.query.get(campaign_id)
            if not campaign:
                return None
            return campaign.to_dict()
        except Exception as e:
            server_logger.error(f"Error getting campaign: {str(e)}")
            raise

    def create_campaign(self, name: str):
        """Create a new campaign with just a name."""
        try:
            if not name:
                raise ValueError("Name is required")

            campaign = Campaign(
                name=name,
                description="",  # Optional field
                organization_id=None,  # Optional field
                status=CampaignStatus.CREATED
            )
            db.session.add(campaign)
            db.session.commit()

            server_logger.info({
                'event': 'campaign_created',
                'campaign_id': campaign.id
            })

            return campaign.to_dict()
        except Exception as e:
            db.session.rollback()
            server_logger.error({
                'event': 'create_campaign_error',
                'message': 'Error occurred while creating campaign',
                'exception': str(e)
            })
            raise

    def start_campaign(self, campaign_id, params=None):
        """Start the lead generation process for an existing campaign."""
        try:
            # Import RQ enqueue helpers here to avoid circular import
            from server.tasks import enqueue_fetch_and_save_leads, enqueue_email_verification, enqueue_enriching_leads, enqueue_email_copy_generation

            # Verify campaign exists
            campaign = Campaign.query.get(campaign_id)
            if not campaign:
                raise ValueError(f"Campaign with id {campaign_id} not found")

            # Validate campaign status
            if campaign.status not in [CampaignStatus.CREATED, CampaignStatus.FAILED]:
                raise ValueError(f"Cannot start campaign in {campaign.status} status")

            # Update campaign status
            campaign.update_status(
                CampaignStatus.FETCHING_LEADS,
                "Starting lead generation process"
            )

            # Validate and prepare search parameters
            if not params:
                raise ValueError("Search parameters are required")

            search_params = {
                'count': int(params.get('count', 100)),
                'excludeGuessedEmails': bool(params.get('excludeGuessedEmails', True)),
                'excludeNoEmails': bool(params.get('excludeNoEmails', True)),
                'getEmails': bool(params.get('getEmails', True)),
                'searchUrl': str(params.get('searchUrl', ''))
            }

            # Validate required parameters
            if not search_params['searchUrl']:
                raise ValueError("Search URL is required")

            # Validate search URL
            if not search_params['searchUrl'].startswith('https://app.apollo.io/'):
                raise ValueError("Invalid Apollo.io search URL")

            # Validate count
            if search_params['count'] < 1 or search_params['count'] > 100:
                raise ValueError("Count must be between 1 and 100")

            # Kick off background task chain using RQ job dependencies
            server_logger.info({
                'event': 'trigger_rq_chain',
                'message': 'Starting lead generation process',
                'params': search_params,
                'campaign_id': campaign.id
            })

            try:
                # Enqueue the first job
                job1 = enqueue_fetch_and_save_leads(search_params, campaign.id)
                
                # Chain the next jobs using depends_on
                job2 = enqueue_email_verification({'campaign_id': campaign.id}, depends_on=job1)
                
                job3 = enqueue_enriching_leads({'campaign_id': campaign.id}, depends_on=job2)
                
                job4 = enqueue_email_copy_generation({'campaign_id': campaign.id}, depends_on=job3)

                # Update campaign with job IDs
                campaign.job_ids = {
                    'fetch_leads': job1.id,
                    'verify_emails': job2.id,
                    'enrich_leads': job3.id,
                    'generate_emails': job4.id
                }
                db.session.commit()

                server_logger.info({
                    'event': 'rq_chain_triggered',
                    'message': 'Lead generation process started successfully',
                    'campaign_id': campaign.id,
                    'job_ids': campaign.job_ids
                })

                return campaign.to_dict()

            except Exception as e:
                # If job enqueuing fails, update campaign status
                campaign.update_status(
                    CampaignStatus.FAILED,
                    f"Failed to start lead generation process: {str(e)}"
                )
                db.session.commit()
                raise

        except Exception as e:
            db.session.rollback()
            server_logger.error({
                'event': 'start_campaign_error',
                'message': 'Error occurred while starting campaign',
                'campaign_id': campaign_id,
                'exception': str(e)
            }, exc_info=True)
            raise

    def create_campaign_with_leads(self, params):
        """Create a campaign and immediately start the lead generation process."""
        try:
            # Create the campaign first
            campaign_data = self.create_campaign(params.get('name', 'New Campaign'))
            
            # Start the campaign
            return self.start_campaign(campaign_data['id'])
        except Exception as e:
            server_logger.error({
                'event': 'create_campaign_with_leads_error',
                'message': 'Error occurred while creating and starting campaign',
                'params': params,
                'exception': str(e)
            })
            raise 
from server.models import Campaign
from server.config.database import db
from server.background_services.apollo_service import ApolloService
from server.utils.logger import logger

class CampaignService:
    def __init__(self):
        self.apollo_service = ApolloService()

    def get_campaigns(self):
        """Get all campaigns."""
        try:
            campaigns = Campaign.query.order_by(Campaign.created_at.desc()).all()
            return [campaign.to_dict() for campaign in campaigns]
        except Exception as e:
            logger.error(f"Error getting campaigns: {str(e)}")
            raise

    def get_campaign(self, campaign_id):
        """Get a single campaign by ID."""
        try:
            campaign = Campaign.query.get(campaign_id)
            if not campaign:
                return None
            return campaign.to_dict()
        except Exception as e:
            logger.error(f"Error getting campaign: {str(e)}")
            raise

    def create_campaign(self):
        """Create a new campaign without starting the lead generation process."""
        try:
            campaign = Campaign()
            db.session.add(campaign)
            db.session.commit()

            campaign_data = {
                'id': campaign.id,
                'created_at': campaign.created_at.isoformat(),
                'status': 'created'
            }

            logger.info({
                'event': 'campaign_created',
                'campaign_id': campaign.id
            })

            return campaign_data
        except Exception as e:
            db.session.rollback()
            logger.error({
                'event': 'create_campaign_error',
                'message': 'Error occurred while creating campaign',
                'exception': str(e)
            })
            raise

    def start_campaign(self, campaign_id, params):
        """Start the lead generation process for an existing campaign."""
        try:
            # Import RQ enqueue helpers here to avoid circular import
            from server.tasks import enqueue_fetch_and_save_leads, enqueue_email_verification, enqueue_enriching_leads, enqueue_email_copy_generation

            # Verify campaign exists
            campaign = Campaign.query.get(campaign_id)
            if not campaign:
                raise ValueError(f"Campaign with id {campaign_id} not found")

            # Validate required parameters
            required_params = ['count', 'excludeGuessedEmails', 'excludeNoEmails', 'getEmails', 'searchUrl']
            for param in required_params:
                if param not in params:
                    raise ValueError(f"Missing required parameter: {param}")

            # Update campaign status
            campaign.status = 'starting'
            db.session.commit()

            # Kick off background task chain using RQ job dependencies
            logger.info({
                'event': 'trigger_rq_chain',
                'message': 'About to trigger fetch_and_save_leads_task -> email_verification_task -> enriching_leads_task -> email_copy_generation_task chain',
                'params': params,
                'campaign_id': campaign.id
            })

            # Enqueue the first job
            job1 = enqueue_fetch_and_save_leads(params, campaign.id)
            # Chain the next jobs using depends_on
            job2 = enqueue_email_verification({'campaign_id': campaign.id}, depends_on=job1)
            job3 = enqueue_enriching_leads({'campaign_id': campaign.id}, depends_on=job2)
            job4 = enqueue_email_copy_generation({'campaign_id': campaign.id}, depends_on=job3)

            logger.info({
                'event': 'rq_chain_triggered',
                'message': 'RQ chain (fetch_and_save_leads_task -> email_verification_task -> enriching_leads_task -> email_copy_generation_task) called',
                'params': params,
                'campaign_id': campaign.id
            })

            return {
                'id': campaign.id,
                'status': 'starting',
                'message': 'Campaign started successfully'
            }
        except Exception as e:
            db.session.rollback()
            logger.error({
                'event': 'start_campaign_error',
                'message': 'Error occurred while starting campaign',
                'campaign_id': campaign_id,
                'params': params,
                'exception': str(e)
            })
            raise

    def create_campaign_with_leads(self, params):
        """Create a campaign and immediately start the lead generation process."""
        try:
            # Create the campaign first
            campaign_data = self.create_campaign()
            
            # Start the campaign
            return self.start_campaign(campaign_data['id'], params)
        except Exception as e:
            logger.error({
                'event': 'create_campaign_with_leads_error',
                'message': 'Error occurred while creating and starting campaign',
                'params': params,
                'exception': str(e)
            })
            raise 
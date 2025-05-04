from server.models import Campaign
from server.config.database import db
from server.background_services.apollo_service import ApolloService
from server.utils.logger import logger

class CampaignService:
    def __init__(self):
        self.apollo_service = ApolloService()

    def create_campaign_with_leads(self, params):
        try:
            # Import RQ enqueue helpers here to avoid circular import
            from server.tasks import enqueue_fetch_and_save_leads, enqueue_email_verification, enqueue_enriching_leads, enqueue_email_copy_generation
            # Create a new campaign
            campaign = Campaign()
            db.session.add(campaign)
            db.session.commit()

            campaign_response = {
                'status': 'success',
                'message': f'Campaign {campaign.id} created.',
                'campaign_id': campaign.id
            }

            logger.info({
                'event': 'campaign_created',
                'campaign_id': campaign.id,
                'params': params
            })
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

            return campaign_response
        except Exception as e:
            db.session.rollback()
            logger.error({
                'event': 'create_campaign_with_leads_error',
                'message': 'Error occurred while creating campaign or fetching leads',
                'params': params,
                'exception': str(e)
            })
            raise e 
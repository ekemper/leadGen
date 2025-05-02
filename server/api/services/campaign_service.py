from server.models import Campaign
from server.config.database import db
from server.services.apollo_service import ApolloService
from server.utils.logger import logger

class CampaignService:
    def __init__(self):
        self.apollo_service = ApolloService()

    def create_campaign_with_leads(self, params):
        try:
            # Import here to avoid circular import
            from server.tasks import fetch_and_save_leads_task
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
            # Kick off background task
            logger.info({
                'event': 'trigger_celery_task',
                'message': 'About to trigger fetch_and_save_leads_task',
                'params': params,
                'campaign_id': campaign.id
            })
            fetch_and_save_leads_task.delay(params, campaign.id)
            logger.info({
                'event': 'celery_task_triggered',
                'message': 'fetch_and_save_leads_task.delay called',
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
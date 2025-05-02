from models import Campaign
from config.database import db
from services.apollo_service import ApolloService

class CampaignService:
    def __init__(self):
        self.apollo_service = ApolloService()

    def create_campaign_with_leads(self, params):
        try:
            # Create a new campaign
            campaign = Campaign()
            db.session.add(campaign)
            db.session.commit()

            # Fetch and save leads, associating them with the campaign
            fetch_result = self.apollo_service.fetch_leads(params, campaign_id=campaign.id)
            if fetch_result.get('status') != 'success':
                raise Exception(fetch_result.get('message', 'Failed to fetch or save leads'))

            return {
                'status': 'success',
                'message': f'Campaign {campaign.id} created and leads are being processed.',
                'campaign_id': campaign.id
            }
        except Exception as e:
            db.session.rollback()
            raise e 
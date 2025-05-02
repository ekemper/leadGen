from server.celery_instance import celery_app
from server.services.apollo_service import ApolloService

print("server.tasks module loaded")

@celery_app.task
def fetch_and_save_leads_task(params, campaign_id):
    print("Celery task started with:", params, campaign_id)
    ApolloService().fetch_leads(params, campaign_id) 
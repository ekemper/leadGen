from server.celery_instance import celery_app
from server.services.apollo_service import ApolloService

print("server.tasks module loaded")

@celery_app.task
def fetch_and_save_leads_task(params, campaign_id):
    print("Celery task started with:", params, campaign_id)
    ApolloService().fetch_leads(params, campaign_id)
    # Only return the campaign_id (small, serializable)
    return {'campaign_id': campaign_id}

@celery_app.task
def enriching_leads_task(result):
    campaign_id = result['campaign_id']
    print(f"enriching_leads_task: loading leads for campaign_id={campaign_id}")
    from server.models.lead import Lead
    from server.config.database import db
    # Query the DB for all leads with this campaign_id
    with db.session() as session:
        leads = session.query(Lead).filter_by(campaign_id=campaign_id).all()
        print(f"enriching_leads_task: found {len(leads)} leads for campaign {campaign_id}")
        # Stub: Add enrichment logic here
    return {'enriched': True, 'campaign_id': campaign_id, 'lead_count': len(leads)}

# Example usage of chaining (for reference, not executed on import):
# from celery import chain
# chain(fetch_and_save_leads_task.s(params, campaign_id), enriching_leads_task.s())() 
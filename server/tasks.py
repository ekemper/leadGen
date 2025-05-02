from server.celery_instance import celery_app
from server.services.apollo_service import ApolloService
from server.services.email_verifier_service import EmailVerifierService

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
    try:
        leads = db.session.query(Lead).filter_by(campaign_id=campaign_id).all()
        print(f"enriching_leads_task: found {len(leads)} leads for campaign {campaign_id}")
        from server.services.perplexity_service import PerplexityService
        perplexity_service = PerplexityService()
        enriched_leads = perplexity_service.enrich_leads(leads)
    finally:
        db.session.remove()
    return {'enriched': True, 'campaign_id': campaign_id, 'lead_count': len(enriched_leads)}

@celery_app.task
def email_verification_task(result):
    campaign_id = result['campaign_id']
    print(f"email_verification_task: verifying emails for campaign_id={campaign_id}")
    verifier = EmailVerifierService()
    count = verifier.verify_emails_for_campaign(campaign_id)
    print(f"email_verification_task: verified {count} leads for campaign {campaign_id}")
    return {'campaign_id': campaign_id, 'verified_count': count}

# Example usage of chaining (for reference, not executed on import):
# from celery import chain
# chain(fetch_and_save_leads_task.s(params, campaign_id), enriching_leads_task.s())() 
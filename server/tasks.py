from server.services.apollo_service import ApolloService
from server.services.email_verifier_service import EmailVerifierService
from server.app import create_app

flask_app = create_app()

print("server.tasks module loaded")

def fetch_and_save_leads_task(params, campaign_id):
    with flask_app.app_context():
        print("RQ job started with:", params, campaign_id)
        ApolloService().fetch_leads(params, campaign_id)
        return {'campaign_id': campaign_id}

def enriching_leads_task(result):
    with flask_app.app_context():
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

def email_verification_task(result):
    with flask_app.app_context():
        campaign_id = result['campaign_id']
        print(f"email_verification_task: verifying emails for campaign_id={campaign_id}")
        verifier = EmailVerifierService()
        count = verifier.verify_emails_for_campaign(campaign_id)
        print(f"email_verification_task: verified {count} leads for campaign {campaign_id}")
        return {'campaign_id': campaign_id, 'verified_count': count}

# RQ enqueue helpers
from rq import Queue
from redis import Redis

redis_conn = Redis()
rq_queue = Queue(connection=redis_conn)

def enqueue_fetch_and_save_leads(params, campaign_id, depends_on=None):
    return rq_queue.enqueue(fetch_and_save_leads_task, params, campaign_id, depends_on=depends_on)

def enqueue_enriching_leads(result, depends_on=None):
    return rq_queue.enqueue(enriching_leads_task, result, depends_on=depends_on)

def enqueue_email_verification(result, depends_on=None):
    return rq_queue.enqueue(email_verification_task, result, depends_on=depends_on)

# Example usage of chaining (for reference, not executed on import):
# from celery import chain
# chain(fetch_and_save_leads_task.s(params, campaign_id), enriching_leads_task.s())() 
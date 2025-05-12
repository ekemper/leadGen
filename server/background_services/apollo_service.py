import os
from apify_client import ApifyClient
from server.models.lead import Lead
from server.config.database import db
from typing import Dict, Any, List
from dotenv import load_dotenv
from server.utils.logging_config import server_logger
from server.models import Campaign
from server.models.campaign import CampaignStatus
import random
import time
from datetime import datetime

class ApolloService:
    """Service for interacting with the Apollo API."""
    
    def __init__(self):
        """Initialize the Apollo service."""
        load_dotenv()
        self.api_token = os.getenv('APIFY_API_TOKEN')
        if not self.api_token:
            raise ValueError("APIFY_API_TOKEN environment variable is not set")
        self.client = ApifyClient(self.api_token)
        self.actor_id = "supreme_coder/apollo-scraper"

    def _save_leads_to_db(self, leads_data: List[Dict[str, Any]], campaign_id: str) -> int:
        """
        Helper to save leads to the database session and commit.
        Returns the number of leads created.
        """
        created_count = 0
        for idx, result in enumerate(leads_data):
            try:
                server_logger.debug(f"[LEAD {idx}] Attempting to create Lead with data: {result}", extra={'component': 'server'})
                lead = Lead(
                    first_name=result.get('first_name', ''),
                    last_name=result.get('last_name', ''),
                    email=result.get('email', ''),
                    phone=result.get('phone', ''),
                    company=result.get('company', ''),
                    title=result.get('title', ''),
                    linkedin_url=result.get('linkedin_url', ''),
                    source_url=result.get('source_url', ''),
                    raw_data=result.get('raw_data', {}),
                    campaign_id=campaign_id
                )
                db.session.add(lead)
                created_count += 1
                server_logger.info(f"[LEAD {idx}] Lead added to session: {lead}", extra={'component': 'server'})
            except Exception as e:
                error_msg = f"[LEAD {idx}] Error saving lead: {str(e)}"
                server_logger.error(error_msg, extra={'component': 'server'})
        try:
            db.session.commit()
            server_logger.info(f"db.session.commit() called. {created_count} leads should be persisted.", extra={'component': 'server'})
        except Exception as e:
            server_logger.error(f"Error during db.session.commit: {str(e)}", extra={'component': 'server'})
        return created_count

    def fetch_leads(self, params: Dict[str, Any], campaign_id: str, job_id: str) -> Dict[str, Any]:
        """
        Start Apify actor run for lead fetching, set up webhook, and persist run/dataset IDs on the job.
        Args:
            params: Parameters for the Apollo API
            campaign_id: ID of the campaign to associate leads with
            job_id: ID of the job to persist Apify run/dataset IDs
        Returns:
            Dict with Apify run and dataset IDs
        """
        if not job_id:
            raise ValueError("job_id must be provided to fetch_leads for webhook payloadTemplate.")
        try:
            server_logger.info(f"[START fetch_leads] campaign_id={campaign_id} job_id={job_id}", extra={'component': 'server'})
            # Get campaign
            campaign = Campaign.query.get(campaign_id)
            server_logger.info(f"[AFTER Campaign.query.get] campaign={campaign}", extra={'component': 'server'})
            if not campaign:
                server_logger.error(f"Campaign {campaign_id} not found", extra={'component': 'server'})
                raise ValueError(f"Campaign {campaign_id} not found")

            # Update campaign status to FETCHING_LEADS before fetching
            campaign.update_status(CampaignStatus.FETCHING_LEADS, "Fetching leads from Apollo")
            db.session.commit()

            # --- Apify actor run block ---
            server_logger.info(f"[BEFORE ApifyClient actor call] actor_id={self.actor_id} with params: {params}", extra={'component': 'server'})
            webhook_url = os.getenv('APIFY_WEBHOOK_URL', 'http://localhost:5001/api/apify-webhook')
            payload_template = (
                '{'
                '"job_id": "' + job_id + '",'  # Inject job_id at webhook creation
                '"apify_run_id": {{resource.id}},'
                '"apify_dataset_id": {{resource.defaultDatasetId}},'
                '"eventType": "{{eventType}}",'
                '"eventData": {{eventData}},'
                '"resource": {{resource}}'
                '}'
            )
            webhook_payload = {
                "eventTypes": [
                    "ACTOR.RUN.CREATED",
                    "ACTOR.RUN.SUCCEEDED",
                    "ACTOR.RUN.FAILED",
                    "ACTOR.RUN.ABORTED",
                    "ACTOR.RUN.TIMED_OUT",
                    "ACTOR.RUN.RESURRECTED"
                ],
                "requestUrl": webhook_url,
                "payloadTemplate": payload_template,
                "idempotencyKey": f"{campaign_id}-{int(time.time())}"
            }
            run = self.client.actor(self.actor_id).call(
                run_input=params,
                webhooks=[webhook_payload]
            )
            apify_run_id = run.get("id")
            dataset_id = run.get("defaultDatasetId")
            if not dataset_id:
                raise Exception("No dataset ID returned from Apify actor run.")
            server_logger.info(f"[GOT apify_run_id] {apify_run_id}, [GOT dataset_id] {dataset_id}", extra={'component': 'server'})
            # Persist Apify run and dataset IDs on the job
            from server.models.job import Job
            job = Job.query.get(job_id)
            if job:
                job.apify_run_id = apify_run_id
                job.apify_dataset_id = dataset_id
                db.session.commit()
            return {
                'apify_run_id': apify_run_id,
                'apify_dataset_id': dataset_id
            }
        except Exception as e:
            db.session.rollback()
            error_msg = f"Error starting Apify actor run: {str(e)}"
            server_logger.error(error_msg, extra={'component': 'server'})
            if 'campaign' in locals() and campaign:
                campaign.update_status(
                    CampaignStatus.FAILED,
                    error_message=error_msg
                )
            raise

    def process_apify_webhook_event(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process Apify webhook event: fetch dataset, save leads, update job/campaign status.
        Args:
            event: The webhook event payload from Apify
        Returns:
            Dict with processing results
        """
        try:
            job_id = event.get('job_id')
            apify_run_id = event.get('apify_run_id')
            apify_dataset_id = event.get('apify_dataset_id')
            event_type = event.get('eventType')
            resource = event.get('resource', {})
            # Only process on SUCCEEDED event
            if event_type != 'ACTOR.RUN.SUCCEEDED':
                server_logger.info(f"[APIFY WEBHOOK] Ignoring event type: {event_type}", extra={'component': 'server'})
                return {'status': 'ignored', 'reason': f'eventType={event_type}'}
            # Find job and campaign
            from server.models.job import Job
            job = Job.query.get(job_id)
            if not job:
                server_logger.error(f"[APIFY WEBHOOK] Job not found: {job_id}", extra={'component': 'server'})
                return {'status': 'error', 'message': f'Job not found: {job_id}'}
            campaign_id = job.campaign_id
            campaign = Campaign.query.get(campaign_id)
            if not campaign:
                server_logger.error(f"[APIFY WEBHOOK] Campaign not found: {campaign_id}", extra={'component': 'server'})
                return {'status': 'error', 'message': f'Campaign not found: {campaign_id}'}
            # Fetch dataset from Apify
            dataset_items = []
            try:
                dataset_client = self.client.dataset(apify_dataset_id)
                dataset_items = dataset_client.list_items().items
                server_logger.info(f"[APIFY WEBHOOK] Retrieved {len(dataset_items)} items from Apify dataset {apify_dataset_id}", extra={'component': 'server'})
            except Exception as e:
                server_logger.error(f"[APIFY WEBHOOK] Error fetching dataset: {str(e)}", extra={'component': 'server'})
                return {'status': 'error', 'message': f'Error fetching dataset: {str(e)}'}
            # Save leads to DB
            created_count = self._save_leads_to_db(dataset_items, campaign_id)
            # Update job and campaign status
            job.status = 'COMPLETED'
            job.result = {'leads': [lead.get('email') for lead in dataset_items], 'total_count': created_count}
            job.completed_at = datetime.utcnow()
            db.session.commit()
            campaign.update_status(CampaignStatus.COMPLETED, f"Leads fetched and saved: {created_count}")
            db.session.commit()
            return {'status': 'success', 'created_count': created_count}
        except Exception as e:
            db.session.rollback()
            server_logger.error(f"[APIFY WEBHOOK] Exception: {str(e)}", extra={'component': 'server'})
            return {'status': 'error', 'message': str(e)} 
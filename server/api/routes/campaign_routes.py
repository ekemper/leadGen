from flask import Blueprint, request, jsonify
from server.models import Campaign
from server.api.services.campaign_service import CampaignService
from server.utils.logging_config import server_logger, combined_logger
from server.models.campaign_status import CampaignStatus
from server.models.job import Job

campaign_bp = Blueprint('campaign', __name__)

@campaign_bp.route('/campaigns', methods=['POST'])
def create_campaign():
    try:
        data = request.get_json()
        name = data.get('name')
        if not name:
            return jsonify({'error': 'Name is required'}), 400
        
        campaign = CampaignService().create_campaign(name)
        return jsonify(campaign.to_dict()), 201
    except Exception as e:
        server_logger.error(f"Error creating campaign: {str(e)}")
        combined_logger.error("Error creating campaign", extra={
            'component': 'server',
            'error': str(e)
        })
        return jsonify({'error': str(e)}), 500

@campaign_bp.route('/campaigns/<string:campaign_id>', methods=['GET'])
def get_campaign(campaign_id):
    try:
        campaign = CampaignService().get_campaign(campaign_id)
        if not campaign:
            return jsonify({'error': 'Campaign not found'}), 404
        return jsonify(campaign.to_dict())
    except Exception as e:
        server_logger.error(f"Error getting campaign {campaign_id}: {str(e)}")
        combined_logger.error(f"Error getting campaign {campaign_id}", extra={
            'component': 'server',
            'campaign_id': campaign_id,
            'error': str(e)
        })
        return jsonify({'error': str(e)}), 500

@campaign_bp.route('/campaigns/<string:campaign_id>/start', methods=['POST'])
def start_campaign(campaign_id):
    try:
        campaign = CampaignService().start_campaign(campaign_id)
        if not campaign:
            return jsonify({'error': 'Campaign not found'}), 404
        return jsonify(campaign.to_dict())
    except Exception as e:
        server_logger.error(f"Error starting campaign {campaign_id}: {str(e)}")
        combined_logger.error(f"Error starting campaign {campaign_id}", extra={
            'component': 'server',
            'campaign_id': campaign_id,
            'error': str(e)
        })
        return jsonify({'error': str(e)}), 500

@campaign_bp.route('/campaigns/<string:campaign_id>/results', methods=['GET'])
def get_campaign_results(campaign_id):
    try:
        campaign = CampaignService().get_campaign(campaign_id)
        if not campaign:
            return jsonify({'error': 'Campaign not found'}), 404
        jobs = Job.query.filter_by(campaign_id=campaign_id).all()
        results = [job.to_dict() for job in jobs]
        return jsonify({'jobs': results})
    except Exception as e:
        server_logger.error(f"Error getting campaign results for {campaign_id}: {str(e)}")
        combined_logger.error(f"Error getting campaign results for {campaign_id}", extra={
            'component': 'server',
            'campaign_id': campaign_id,
            'error': str(e)
        })
        return jsonify({'error': str(e)}), 500

@campaign_bp.route('/campaigns/<string:campaign_id>/cleanup', methods=['POST'])
def cleanup_campaign_jobs(campaign_id):
    try:
        data = request.get_json()
        days = data.get('days', 7)
        
        campaign = CampaignService().get_campaign(campaign_id)
        if not campaign:
            return jsonify({'error': 'Campaign not found'}), 404
        
        campaign.cleanup_old_jobs(days)
        return jsonify({'message': f'Successfully cleaned up jobs older than {days} days'})
    except Exception as e:
        server_logger.error(f"Error cleaning up campaign jobs for {campaign_id}: {str(e)}")
        combined_logger.error(f"Error cleaning up campaign jobs for {campaign_id}", extra={
            'component': 'server',
            'campaign_id': campaign_id,
            'error': str(e)
        })
        return jsonify({'error': str(e)}), 500 
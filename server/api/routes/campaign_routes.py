from flask import Blueprint, request, jsonify
from server.models import Campaign
from server.api.services.campaign_service import CampaignService
from server.utils.logging_config import server_logger
from server.models.campaign_status import CampaignStatus
from server.models.job import Job
from flask_jwt_extended import jwt_required

campaign_bp = Blueprint('campaign', __name__)

@campaign_bp.route('/campaigns', methods=['POST'])
def create_campaign():
    try:
        data = request.get_json()
        name = data.get('name')
        if not name:
            return jsonify({'status': 'error', 'message': 'Name is required'}), 400
        
        campaign = CampaignService().create_campaign(name)
        return jsonify({'status': 'success', 'data': campaign.to_dict()}), 201
    except Exception as e:
        server_logger.error(f"Error creating campaign: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@campaign_bp.route('/campaigns/<string:campaign_id>', methods=['GET'])
@jwt_required()
def get_campaign(campaign_id):
    """Get campaign details."""
    try:
        campaign = CampaignService().get_campaign(campaign_id)
        if not campaign:
            return jsonify({
                'status': 'error',
                'message': f'Campaign {campaign_id} not found'
            }), 404
        return jsonify({
            'status': 'success',
            'data': campaign.to_dict()
        })
    except Exception as e:
        server_logger.error(f"Error getting campaign: {str(e)}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': 'Internal server error'
        }), 500

@campaign_bp.route('/campaigns/<string:campaign_id>/start', methods=['POST'])
@jwt_required()
def start_campaign(campaign_id):
    """Start a campaign."""
    try:
        params = request.get_json()
        campaign = CampaignService().start_campaign(campaign_id, params)
        return jsonify({
            'status': 'success',
            'data': campaign
        })
    except ValueError as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 400
    except Exception as e:
        server_logger.error(f"Error starting campaign: {str(e)}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': 'Internal server error'
        }), 500

@campaign_bp.route('/campaigns/<string:campaign_id>/results', methods=['GET'])
def get_campaign_results(campaign_id):
    try:
        campaign = CampaignService().get_campaign(campaign_id)
        if not campaign:
            return jsonify({'status': 'error', 'message': 'Campaign not found'}), 404
        
        jobs = Job.query.filter_by(campaign_id=campaign_id).all()
        results = [job.to_dict() for job in jobs]
        return jsonify({'status': 'success', 'data': {'jobs': results}})
    except Exception as e:
        server_logger.error(f"Error getting campaign results for {campaign_id}: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@campaign_bp.route('/campaigns/<string:campaign_id>/cleanup', methods=['POST'])
def cleanup_campaign_jobs(campaign_id):
    try:
        data = request.get_json()
        days = data.get('days', 7)
        
        campaign = CampaignService().get_campaign(campaign_id)
        if not campaign:
            return jsonify({'status': 'error', 'message': 'Campaign not found'}), 404
        
        campaign.cleanup_old_jobs(days)
        return jsonify({
            'status': 'success',
            'message': f'Successfully cleaned up jobs older than {days} days'
        })
    except Exception as e:
        server_logger.error(f"Error cleaning up campaign jobs for {campaign_id}: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500 
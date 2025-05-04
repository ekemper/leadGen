from server.models import Organization
from server.config.database import db
from server.utils.logger import logger

class OrganizationService:
    def create_organization(self, data):
        try:
            org = Organization(
                name=data['name'],
                description=data.get('description')
            )
            db.session.add(org)
            db.session.commit()
            return org.to_dict()
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error creating organization: {str(e)}")
            raise

    def get_organization(self, org_id):
        org = Organization.query.get(org_id)
        return org.to_dict() if org else None

    def get_organizations(self):
        orgs = Organization.query.all()
        return [org.to_dict() for org in orgs]

    def update_organization(self, org_id, data):
        org = Organization.query.get(org_id)
        if not org:
            return None
        if 'name' in data:
            org.name = data['name']
        if 'description' in data:
            org.description = data['description']
        db.session.commit()
        return org.to_dict() 
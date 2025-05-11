import sys
import json
from server.tasks import fetch_and_save_leads_task
from server.app import create_app
from server.config.database import db
from server.api.services.campaign_service import CampaignService
from server.models.organization import Organization

# Default parameters as per campaign create form/backend
DEFAULT_CAMPAIGN_DATA = {
    "name": "Test Campaign",
    "description": "Test campaign created by script",
    "searchUrl": "https://app.apollo.io/#/people?page=1&personLocations%5B%5D=United%20States&contactEmailStatusV2%5B%5D=verified&personSeniorities%5B%5D=owner&personSeniorities%5B%5D=founder&personSeniorities%5B%5D=c_suite&includedOrganizationKeywordFields%5B%5D=tags&includedOrganizationKeywordFields%5B%5D=name&personDepartmentOrSubdepartments%5B%5D=master_operations&personDepartmentOrSubdepartments%5B%5D=master_sales&sortAscending=false&sortByField=recommendations_score&contactEmailExcludeCatchAll=true&qOrganizationKeywordTags%5B%5D=SEO&qOrganizationKeywordTags%5B%5D=Digital%20Marketing&qOrganizationKeywordTags%5B%5D=Marketing",
    "count": 10,
    "excludeGuessedEmails": True,
    "excludeNoEmails": True,
    "getEmails": True
}

def main():
    flask_app = create_app()
    with flask_app.app_context():
        # Create a new organization (if required)
        org = Organization.query.first()
        if not org:
            org = Organization(name="Test Org", description="Created by test script")
            db.session.add(org)
            db.session.commit()
        # Prepare campaign data
        campaign_data = dict(DEFAULT_CAMPAIGN_DATA)
        campaign_data["organization_id"] = org.id
        # Create campaign
        campaign_service = CampaignService()
        campaign = campaign_service.create_campaign(campaign_data)
        campaign_id = campaign["id"]
        params = {
            "searchUrl": campaign["searchUrl"],
            "count": campaign["count"],
            "excludeGuessedEmails": campaign["excludeGuessedEmails"],
            "excludeNoEmails": campaign["excludeNoEmails"],
            "getEmails": campaign["getEmails"]
        }
        try:
            print(f"Running fetch_and_save_leads_task with campaign_id={campaign_id} and params={params}")
            result = fetch_and_save_leads_task(params, campaign_id)
            print(f"Task result: {result}")
        except Exception as e:
            print(f"Exception: {e}")
            import traceback; traceback.print_exc()

if __name__ == "__main__":
    main() 
import sys
import json
from server.tasks import fetch_and_save_leads_task

# Example usage: python scripts/test_fetch_and_save_leads.py '{"searchUrl": "https://app.apollo.io/#/people?page=1&personLocations%5B%5D=United%20States&contactEmailStatusV2%5B%5D=verified&personSeniorities%5B%5D=owner&personSeniorities%5B%5D=founder&personSeniorities%5B%5D=c_suite&includedOrganizationKeywordFields%5B%5D=tags&includedOrganizationKeywordFields%5B%5D=name&personDepartmentOrSubdepartments%5B%5D=master_operations&personDepartmentOrSubdepartments%5B%5D=master_sales&sortAscending=false&sortByField=recommendations_score&contactEmailExcludeCatchAll=true&qOrganizationKeywordTags%5B%5D=SEO&qOrganizationKeywordTags%5B%5D=Digital%20Marketing&qOrganizationKeywordTags%5B%5D=Marketing", "count": 10, "excludeGuessedEmails": true, "excludeNoEmails": true, "getEmails": true}' 2c33fe8a-cddc-45ff-9545-2880a78c487c

def main():
    if len(sys.argv) != 3:
        print("Usage: python scripts/test_fetch_and_save_leads.py '<params_json>' <campaign_id>")
        sys.exit(1)
    params = json.loads(sys.argv[1])
    campaign_id = sys.argv[2]
    try:
        print(f"Running fetch_and_save_leads_task with campaign_id={campaign_id} and params={params}")
        result = fetch_and_save_leads_task(params, campaign_id)
        print(f"Task result: {result}")
    except Exception as e:
        print(f"Exception: {e}")
        import traceback; traceback.print_exc()

if __name__ == "__main__":
    main() 
import os
import json
from apify_client import ApifyClient
from dotenv import load_dotenv

# Load .env file
load_dotenv()

API_TOKEN = os.getenv("APIFY_API_TOKEN")
if not API_TOKEN:
    raise RuntimeError("APIFY_API_TOKEN not set in environment")

# Use the same params as your app
params = {
    "searchUrl": "https://app.apollo.io/#/people?page=1&personLocations%5B%5D=United%20States&contactEmailStatusV2%5B%5D=verified&personSeniorities%5B%5D=owner&personSeniorities%5B%5D=founder&personSeniorities%5B%5D=c_suite&includedOrganizationKeywordFields%5B%5D=tags&includedOrganizationKeywordFields%5B%5D=name&personDepartmentOrSubdepartments%5B%5D=master_operations&personDepartmentOrSubdepartments%5B%5D=master_sales&sortAscending=false&sortByField=recommendations_score&contactEmailExcludeCatchAll=true&qOrganizationKeywordTags%5B%5D=SEO&qOrganizationKeywordTags%5B%5D=Digital%20Marketing&qOrganizationKeywordTags%5B%5D=Marketing",
    "count": 10,
    "excludeGuessedEmails": True,
    "excludeNoEmails": True,
    "getEmails": True
}

client = ApifyClient(API_TOKEN)
actor_id = "supreme_coder/apollo-scraper"

print("Running Apify actor with params:")
print(json.dumps(params, indent=2))

run = client.actor(actor_id).call(run_input=params)
print("\nRaw run response:")
print(json.dumps(run, indent=2, default=str))

dataset_id = run.get("defaultDatasetId")
if not dataset_id:
    print("No dataset ID returned from Apify actor run.")
    exit(1)

results = list(client.dataset(dataset_id).iterate_items())
print(f"\nDataset results ({len(results)} items):")
print(json.dumps(results, indent=2, default=str)) 
# Apify Mock Integration Test

## Purpose
This test provides a full end-to-end integration test for the Apollo/ApolloService lead generation flow using the Apify mock client. It verifies:
- Campaign creation and starting via the API
- Lead ingestion from the mock Apify client
- Background enrichment jobs (Perplexity, OpenAI, Instantly)
- Correct job status and results for each lead
- Data integrity between the mock data and the database

## How the Mock is Enabled
The test sets the environment variable `USE_APIFY_CLIENT_MOCK=true` at runtime, ensuring the ApolloService uses the mock Apify client instead of the real one. This makes the test deterministic and independent of external Apify API calls.

## What the Test Asserts
- All leads from the mock data are ingested and present in the database
- For each lead:
  - An enrichment job (ENRICH_LEAD) is created and completes successfully
  - The lead has:
    - `enrichment_results` (from Perplexity)
    - `email_copy_gen_results` (from OpenAI/email copy)
    - `instantly_lead_record` (from Instantly)
  - The ENRICH_LEAD job result indicates success for all steps
  - The lead's core fields (name, email, company) match the mock data

## How to Run the Test
From the project root, run:

```sh
pytest server/tests/test_apify_mock_integration.py
```

No special setup is required; the test will always use the mock Apify client.

## Notes for Maintainers
- The test will print polling progress to stdio for both lead ingestion and job completion.
- The mock data is loaded from `server/background_services/mock-leads-data.csv` and used as the source of truth for assertions.
- The test has generous timeouts for background jobs (up to 240 seconds per lead) to accommodate real async processing.
- If you change the lead ingestion or enrichment pipeline, update this test and the mock data accordingly.
- This test is intended for CI and local development to ensure the full pipeline works as expected with deterministic data. 
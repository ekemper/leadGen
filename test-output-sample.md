===============================================
 RESET AND RUN CONCURRENT CAMPAIGNS TEST
===============================================
[INFO] This script will:
[INFO]   1. Validate environment and prerequisites
[INFO]   2. Truncate the combined.log file
[INFO]   3. Full rebuild Docker containers (down -v && up --build)
[INFO]   4. Truncate database tables (jobs, leads, campaigns, organizations, users)
[INFO]   5. Clear Redis cache
[INFO]   6. Run the concurrent campaigns flow test
[INFO]   7. Validate results

[WARNING] ⚠️  WARNING: This will DELETE ALL DATA in the specified database tables!
[WARNING] ⚠️  Make sure you're running this in a development environment!

Do you want to continue? (y/N): y

===============================================
 PHASE 1: ENVIRONMENT VALIDATION
===============================================
[STEP] Validating prerequisites...
[SUCCESS] Prerequisites validated
[STEP] Validating environment and container status...
[INFO] Found containers:
[INFO]   API: fastapi-k8-proto-api-1
[INFO]   PostgreSQL: fastapi-k8-proto-postgres-1
[INFO]   Redis: fastapi-k8-proto-redis-1
[STEP] Testing database connectivity...
Database connection successful
[STEP] Testing Redis connectivity...
Redis connection successful
[SUCCESS] Environment validation completed

===============================================
 PHASE 2: LOG FILE MANAGEMENT
===============================================
[STEP] Truncating log file: ./logs/combined.log
[SUCCESS] Log file truncated successfully

===============================================
 PHASE 3: CONTAINER REBUILD
===============================================
[STEP] Performing full Docker containers rebuild...
[INFO] Stopping and removing all containers, networks, and volumes...
WARN[0000] /home/ek/dev/fastapi-k8-proto/docker-compose.yml: the attribute `version` is obsolete, it will be ignored, please remove it to avoid potential confusion 
[+] Running 15/15
 ✔ Container fastapi-k8-proto-frontend-1  Removed                                                                                                                                                                                     0.4s 
 ✔ Container fastapi-k8-proto-flower-1    Removed                                                                                                                                                                                     0.5s 
 ✔ Container fastapi-k8-proto-worker-7    Removed                                                                                                                                                                                     2.4s 
 ✔ Container fastapi-k8-proto-worker-2    Removed                                                                                                                                                                                     2.8s 
 ✔ Container fastapi-k8-proto-worker-4    Removed                                                                                                                                                                                     2.9s 
 ✔ Container fastapi-k8-proto-worker-6    Removed                                                                                                                                                                                     2.6s 
 ✔ Container fastapi-k8-proto-worker-5    Removed                                                                                                                                                                                     3.0s 
 ✔ Container fastapi-k8-proto-worker-1    Removed                                                                                                                                                                                     2.9s 
 ✔ Container fastapi-k8-proto-worker-8    Removed                                                                                                                                                                                     3.0s 
 ✔ Container fastapi-k8-proto-worker-3    Removed                                                                                                                                                                                     3.0s 
 ✔ Container fastapi-k8-proto-api-1       Removed                                                                                                                                                                                    10.3s 
 ✔ Container fastapi-k8-proto-postgres-1  Removed                                                                                                                                                                                     0.3s 
 ✔ Container fastapi-k8-proto-redis-1     Removed                                                                                                                                                                                     0.4s 
 ✔ Volume fastapi-k8-proto_postgres_data  Removed                                                                                                                                                                                     0.0s 
 ✔ Network fastapi-k8-proto_default       Removed                                                                                                                                                                                     0.2s 
[INFO] Building and starting containers from scratch...
WARN[0000] /home/ek/dev/fastapi-k8-proto/docker-compose.yml: the attribute `version` is obsolete, it will be ignored, please remove it to avoid potential confusion 
Compose can now delegate builds to bake for better performance.
 To do so, set COMPOSE_BAKE=true.
[+] Building 5.6s (44/48)                                                                                                                                                                                             docker:desktop-linux
 => [flower internal] load build definition from Dockerfile.worker                                                                                                                                                                    0.0s
 => => transferring dockerfile: 596B                                                                                                                                                                                                  0.0s
 => [api internal] load build definition from Dockerfile.api                                                                                                                                                                          0.0s
 => => transferring dockerfile: 1.01kB                                                                                                                                                                                                0.0s
 => [worker internal] load build definition from Dockerfile.worker                                                                                                                                                                    0.0s
 => => transferring dockerfile: 596B                                                                                                                                                                                                  0.0s
 => [api internal] load metadata for docker.io/library/python:3.11-slim                                                                                                                                                               0.6s
 => [api internal] load .dockerignore                                                                                                                                                                                                 0.0s
 => => transferring context: 517B                                                                                                                                                                                                     0.0s
 => [worker internal] load .dockerignore                                                                                                                                                                                              0.0s
 => => transferring context: 517B                                                                                                                                                                                                     0.0s
 => [flower internal] load .dockerignore                                                                                                                                                                                              0.0s
 => => transferring context: 517B                                                                                                                                                                                                     0.0s
 => [worker 1/7] FROM docker.io/library/python:3.11-slim@sha256:dbf1de478a55d6763afaa39c2f3d7b54b25230614980276de5cacdde79529d0c                                                                                                      0.0s
 => => resolve docker.io/library/python:3.11-slim@sha256:dbf1de478a55d6763afaa39c2f3d7b54b25230614980276de5cacdde79529d0c                                                                                                             0.0s
 => [worker internal] load build context                                                                                                                                                                                              0.0s
 => => transferring context: 36.46kB                                                                                                                                                                                                  0.0s
 => [api internal] load build context                                                                                                                                                                                                 0.0s
 => => transferring context: 46.80kB                                                                                                                                                                                                  0.0s
 => [api  7/13] ADD https://raw.githubusercontent.com/vishnubob/wait-for-it/master/wait-for-it.sh /app/wait-for-it.sh                                                                                                                 0.2s
 => [flower internal] load build context                                                                                                                                                                                              0.0s
 => => transferring context: 36.46kB                                                                                                                                                                                                  0.0s
 => CACHED [api  5/13] RUN pip install --no-cache-dir -r requirements/prod.txt                                                                                                                                                        0.0s
 => [flower 6/7] COPY app/ ./app/                                                                                                                                                                                                     0.1s
 => CACHED [api 2/7] WORKDIR /app                                                                                                                                                                                                     0.0s
 => CACHED [api 3/7] RUN apt-get update && apt-get install -y     gcc     postgresql-client     && rm -rf /var/lib/apt/lists/*                                                                                                        0.0s
 => CACHED [flower 4/7] COPY requirements/ ./requirements/                                                                                                                                                                            0.0s
 => CACHED [flower 5/7] RUN pip install --no-cache-dir -r requirements/prod.txt                                                                                                                                                       0.0s
 => CACHED [api  4/13] COPY requirements/ ./requirements/                                                                                                                                                                             0.0s
 => [worker 7/7] RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app                                                                                                                                                      1.7s
 => CACHED [api  6/13] RUN pip install --no-cache-dir -r requirements/dev.txt                                                                                                                                                         0.0s
 => CACHED [api  7/13] ADD https://raw.githubusercontent.com/vishnubob/wait-for-it/master/wait-for-it.sh /app/wait-for-it.sh                                                                                                          0.0s
 => CACHED [api  8/13] RUN chmod +x /app/wait-for-it.sh                                                                                                                                                                               0.0s
 => [api  9/13] COPY app/ ./app/                                                                                                                                                                                                      0.1s
 => [api 10/13] COPY alembic/ ./alembic/                                                                                                                                                                                              0.1s
 => [api 11/13] COPY alembic.ini ./                                                                                                                                                                                                   0.1s
 => [api 12/13] COPY tests/ ./tests/                                                                                                                                                                                                  0.1s
 => [api 13/13] RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app                                                                                                                                                       2.6s
 => [worker] exporting to image                                                                                                                                                                                                       0.9s
 => => exporting layers                                                                                                                                                                                                               0.4s
 => => exporting manifest sha256:dc65193eb578f0356b800390f8e5d4ad3e904d38b022fed5c4233dc163b5361f                                                                                                                                     0.0s
 => => exporting config sha256:3b24f83f2e34ee4b5ef2656a642c1725337344b0efb13231c3b5e256a15a55cb                                                                                                                                       0.1s
 => => exporting attestation manifest sha256:688dabfbc0c50c7c426049832fb644b933a5a79d8a9088844a11712b072cc61a                                                                                                                         0.1s
 => => exporting manifest list sha256:21baa2816b7a56d6208f677441d3801256ad9e55f5a83cf7f98ec17838191f5d                                                                                                                                0.1s
 => => naming to docker.io/library/fastapi-k8-proto-worker:latest                                                                                                                                                                     0.0s
 => => unpacking to docker.io/library/fastapi-k8-proto-worker:latest                                                                                                                                                                  0.1s
 => [flower] exporting to image                                                                                                                                                                                                       0.9s
 => => exporting layers                                                                                                                                                                                                               0.3s
 => => exporting manifest sha256:35c4fb0f43f01c70cfd0e714064860598f6e514b6d935851cb88b33837a50155                                                                                                                                     0.1s
 => => exporting config sha256:9caf88fffad633fddc0c0863dcb160d51a51f86cdf2e7e4bc3bfd4c51e55ef3e                                                                                                                                       0.1s
 => => exporting attestation manifest sha256:3f64d55fe5f550d9f2e1b59a0ac39e63b3f51835205aae93481c1b2dc3fbef3b                                                                                                                         0.1s
 => => exporting manifest list sha256:6128d6ca913a8e236b854b2fd87052d37e143daa0566938e42bf1cf125b68725                                                                                                                                0.0s
 => => naming to docker.io/library/fastapi-k8-proto-flower:latest                                                                                                                                                                     0.0s
 => => unpacking to docker.io/library/fastapi-k8-proto-flower:latest                                                                                                                                                                  0.1s
 => [worker] resolving provenance for metadata file                                                                                                                                                                                   0.0s
 => [flower] resolving provenance for metadata file                                                                                                                                                                                   0.0s
 => [api] exporting to image                                                                                                                                                                                                          0.7s
 => => exporting layers                                                                                                                                                                                                               0.4s
 => => exporting manifest sha256:0d26b85cd742dd1825de192e02c6fdad8744a000650c87520945db5d483108dd                                                                                                                                     0.0s
 => => exporting config sha256:c9da0255703744c2011139157228646d3f9a5f118d593a8ea0ba90b64e7519f8                                                                                                                                       0.0s
 => => exporting attestation manifest sha256:6b8dd5523b6fb13c524c0862dd48d87052f392800e6e8fbe1c630efe7357c360                                                                                                                         0.0s
 => => exporting manifest list sha256:eba6a1578df5f128fdbaa0aae57b5b4a4c18baa8f0e9a6e631e902d692d7f5a7                                                                                                                                0.0s
 => => naming to docker.io/library/fastapi-k8-proto-api:latest                                                                                                                                                                        0.0s
 => => unpacking to docker.io/library/fastapi-k8-proto-api:latest                                                                                                                                                                     0.2s
 => [api] resolving provenance for metadata file                                                                                                                                                                                      0.0s
 => [frontend internal] load build definition from Dockerfile                                                                                                                                                                         0.0s
 => => transferring dockerfile: 582B                                                                                                                                                                                                  0.0s
 => WARN: FromAsCasing: 'as' and 'FROM' keywords' casing do not match (line 2)                                                                                                                                                        0.0s
 => WARN: FromAsCasing: 'as' and 'FROM' keywords' casing do not match (line 6)                                                                                                                                                        0.0s
 => WARN: FromAsCasing: 'as' and 'FROM' keywords' casing do not match (line 14)                                                                                                                                                       0.0s
 => [frontend internal] load metadata for docker.io/library/node:20-alpine                                                                                                                                                            0.3s
 => [frontend internal] load .dockerignore                                                                                                                                                                                            0.0s
 => => transferring context: 2B                                                                                                                                                                                                       0.0s
 => [frontend base 1/2] FROM docker.io/library/node:20-alpine@sha256:d3507a213936fe4ef54760a186e113db5188472d9efdf491686bd94580a1c1e8                                                                                                 0.0s
 => => resolve docker.io/library/node:20-alpine@sha256:d3507a213936fe4ef54760a186e113db5188472d9efdf491686bd94580a1c1e8                                                                                                               0.0s
 => [frontend internal] load build context                                                                                                                                                                                            0.1s
 => => transferring context: 72B                                                                                                                                                                                                      0.1s
 => CACHED [frontend base 2/2] WORKDIR /app                                                                                                                                                                                           0.0s
 => CACHED [frontend development 1/2] COPY package*.json ./                                                                                                                                                                           0.0s
 => CACHED [frontend development 2/2] RUN npm install                                                                                                                                                                                 0.0s
 => [frontend] exporting to image                                                                                                                                                                                                     0.1s
 => => exporting layers                                                                                                                                                                                                               0.0s
 => => exporting manifest sha256:72a1623a2a705690946861177ce8d6f1bfcdc7cc15b9033891e1489fc645a9f7                                                                                                                                     0.0s
 => => exporting config sha256:c083fa3e39e10a2512f239373880697a906de494c4a0dc716c6b723611c36b2a                                                                                                                                       0.0s
 => => exporting attestation manifest sha256:1e71d815a4900f583092ca79d86713196055bbe5b6e9253e7d7fa832f9f13ff3                                                                                                                         0.0s
 => => exporting manifest list sha256:55f1b9699a014cba7f667c4bbb46fd9eb649fbe3e3e1153b11e5389ecd54674f                                                                                                                                0.0s
 => => naming to docker.io/library/fastapi-k8-proto-frontend:latest                                                                                                                                                                   0.0s
 => => unpacking to docker.io/library/fastapi-k8-proto-frontend:latest                                                                                                                                                                0.0s
 => [frontend] resolving provenance for metadata file                                                                                                                                                                                 0.0s
[+] Running 6/6
 ✔ api                                      Built                                                                                                                                                                                     0.0s 
[+] Running 19/19                           Built                                                                                                                                                                                     0.0s 
 ✔ api                                      Built                                                                                                                                                                                     0.0s 
 ✔ flower                                   Built                                                                                                                                                                                     0.0s 
 ✔ frontend                                 Built                                                                                                                                                                                     0.0s 
 ✔ worker                                   Built                                                                                                                                                                                     0.0s 
 ✔ Network fastapi-k8-proto_default         Created                                                                                                                                                                                   0.0s 
 ✔ Volume "fastapi-k8-proto_postgres_data"  Created                                                                                                                                                                                   0.0s 
 ✔ Container fastapi-k8-proto-redis-1       Healthy                                                                                                                                                                                  13.5s 
 ✔ Container fastapi-k8-proto-postgres-1    Healthy                                                                                                                                                                                  13.5s 
 ✔ Container fastapi-k8-proto-worker-8      Started                                                                                                                                                                                  15.6s 
 ✔ Container fastapi-k8-proto-flower-1      Started                                                                                                                                                                                   2.9s 
 ✔ Container fastapi-k8-proto-api-1         Started                                                                                                                                                                                  13.5s 
 ✔ Container fastapi-k8-proto-worker-4      Started                                                                                                                                                                                  15.3s 
 ✔ Container fastapi-k8-proto-worker-5      Started                                                                                                                                                                                  15.0s 
 ✔ Container fastapi-k8-proto-worker-1      Started                                                                                                                                                                                  13.8s 
 ✔ Container fastapi-k8-proto-worker-6      Started                                                                                                                                                                                  14.4s 
 ✔ Container fastapi-k8-proto-worker-3      Started                                                                                                                                                                                  13.9s 
 ✔ Container fastapi-k8-proto-worker-2      Started                                                                                                                                                                                  14.1s 
 ✔ Container fastapi-k8-proto-worker-7      Started                                                                                                                                                                                  13.5s 
 ✔ Container fastapi-k8-proto-frontend-1    Started                                                                                                                                                                                  13.0s 
[STEP] Waiting for services to be healthy...
WARN[0000] /home/ek/dev/fastapi-k8-proto/docker-compose.yml: the attribute `version` is obsolete, it will be ignored, please remove it to avoid potential confusion 
[INFO] Updated container names after rebuild:
[INFO]   API: fastapi-k8-proto-api-1
[INFO]   PostgreSQL: fastapi-k8-proto-postgres-1
[INFO]   Redis: fastapi-k8-proto-redis-1
[SUCCESS] Containers rebuilt and started successfully

===============================================
 PHASE 4: DATABASE TABLE TRUNCATION
===============================================
[STEP] Truncating database tables...
[INFO] Executing SQL commands to truncate tables...
Database tables truncated successfully
[STEP] Verifying table truncation...
Table jobs: 0 rows (verified)
Table leads: 0 rows (verified)
Table campaigns: 0 rows (verified)
Table organizations: 0 rows (verified)
Table users: 0 rows (verified)
All specified tables are empty
[SUCCESS] Database tables truncated and verified

===============================================
 PHASE 5: REDIS CACHE CLEARING
===============================================
[STEP] Clearing Redis cache...
Redis cache cleared successfully
[STEP] Verifying Redis cache is empty...
Redis cache is empty (verified)
[SUCCESS] Redis cache cleared and verified

===============================================
 PHASE 6: TEST EXECUTION
===============================================
[STEP] Running concurrent campaigns flow test...
[INFO] Starting test execution...
[INFO] This may take several minutes to complete...
[INFO] Test output will be displayed in real-time below:

================== TEST OUTPUT START ==================
[Setup] Changed working directory to: /app

================================================================================
🚀 STARTING CONCURRENT CAMPAIGNS TEST WITH CIRCUIT BREAKER AWARENESS
📊 Testing normal campaign execution with automatic service failure detection
📊 Will stop gracefully and report clearly if circuit breaker triggers
📊 Focus: Happy path validation with robust service health monitoring
================================================================================

🔍 PRE-FLIGHT CHECK: Redis Availability
--------------------------------------------------
[MockApifyClient] Redis connectivity verified successfully
[MockApifyClient] Loading original dataset from: /app/app/background_services/smoke_tests/dataset_apollo-io-scraper_2025-05-21_19-33-02-963.json
[MockApifyClient] Successfully loaded 500 total records from file to Redis
[MockApifyClient] Created working dataset with 500 records
[MockApifyClient] Sample record keys: ['id', 'first_name', 'last_name', 'name', 'linkedin_url', 'title', 'email_status', 'photo_url', 'twitter_url', 'github_url', 'facebook_url', 'extrapolated_email_confidence', 'headline', 'email', 'organization_id', 'employment_history', 'state', 'city', 'country', 'organization', 'departments', 'subdepartments', 'seniority', 'functions', 'intent_strength', 'show_intent', 'email_domain_catchall', 'personal_emails', 'organization_name', 'organization_website_url', 'organization_linkedin_url', 'organization_founded_year', 'industry', 'estimated_num_employees', 'organization_raw_address', 'organization_street_address', 'organization_city', 'organization_state', 'organization_country', 'organization_postal_code']
[MockApifyClient] Sample email: tshoemaker@poconoharley.com

[DEBUG] Dataset status at start: {'status': 'loaded', 'total': 500, 'consumed': 500, 'remaining': 0, 'storage': 'redis'}

📋 PHASE 1: Authentication & Setup
--------------------------------------------------
[Auth] Signing up test user: testuser_c3mqxa36@hellacooltestingdomain.pizza
[Auth] Signing in test user: testuser_c3mqxa36@hellacooltestingdomain.pizza
[Auth] Got token: eyJhbGci...
[Org] Created organization with id: c22b089c-cde0-4ac4-99c1-162ba4507e6b

🔍 PHASE 2: Pre-Test Circuit Breaker Health Check
--------------------------------------------------
[Health Check] Verifying all services are healthy before starting test...
✅ All services healthy: 5/5 circuit breakers in 'closed' state
   🟢 PERPLEXITY: closed
   🟢 OPENAI: closed
   🟢 APOLLO: closed
   🟢 INSTANTLY: closed
   🟢 MILLIONVERIFIER: closed

📋 PHASE 3: Sequential Campaign Creation with Pop-Based Data
--------------------------------------------------
[Setup] Creating 10 campaigns sequentially...
[Setup] Creating 10 campaigns sequentially...

[Setup] === Setting up Campaign #1 ===
[Campaign #1] Creating campaign...
[Campaign #1] Created campaign with id: 49945eb4-ff65-4774-a771-d74cb085d92d
[Campaign #1] Starting campaign 49945eb4-ff65-4774-a771-d74cb085d92d...
[Campaign #1] Started campaign 49945eb4-ff65-4774-a771-d74cb085d92d
[Setup] Waiting for Campaign #1 FETCH_LEADS to complete...
[Polling #1] Starting to wait for FETCH_LEADS jobs (campaign 49945eb4-ff65-4774-a771-d74cb085d92d)
[Polling #1] Expecting 1 FETCH_LEADS job(s) to complete
[API] Fetched 1 total jobs for campaign 49945eb4-ff65-4774-a771-d74cb085d92d across 1 page(s)
[API] Fetched 6 total jobs for campaign 49945eb4-ff65-4774-a771-d74cb085d92d across 1 page(s)
[Polling #1] SUCCESS: 1 FETCH_LEADS job(s) completed after 10s
[API #1] Fetching all leads for campaign 49945eb4-ff65-4774-a771-d74cb085d92d...
[API #1] Successfully retrieved 5 leads
[Debug] Campaign #1 received 5 leads with 5 valid emails
[Setup] ✅ Campaign #1 ready with 5 leads (5 valid emails)

[Setup] === Setting up Campaign #2 ===
[Campaign #2] Creating campaign...
[Campaign #2] Created campaign with id: 75de7ae7-f97a-488e-8e8a-c10337350b98
[Campaign #2] Starting campaign 75de7ae7-f97a-488e-8e8a-c10337350b98...
[Campaign #2] Started campaign 75de7ae7-f97a-488e-8e8a-c10337350b98
[Setup] Waiting for Campaign #2 FETCH_LEADS to complete...
[Polling #2] Starting to wait for FETCH_LEADS jobs (campaign 75de7ae7-f97a-488e-8e8a-c10337350b98)
[Polling #2] Expecting 1 FETCH_LEADS job(s) to complete
[API] Fetched 1 total jobs for campaign 75de7ae7-f97a-488e-8e8a-c10337350b98 across 1 page(s)
[API] Fetched 11 total jobs for campaign 75de7ae7-f97a-488e-8e8a-c10337350b98 across 1 page(s)
[Polling #2] SUCCESS: 1 FETCH_LEADS job(s) completed after 10s
[API #2] Fetching all leads for campaign 75de7ae7-f97a-488e-8e8a-c10337350b98...
[API #2] Successfully retrieved 10 leads
[Debug] Campaign #2 received 10 leads with 10 valid emails
[Setup] ✅ Campaign #2 ready with 10 leads (10 valid emails)

[Setup] === Setting up Campaign #3 ===
[Campaign #3] Creating campaign...
[Campaign #3] Created campaign with id: 2d075653-74b7-4720-8696-a8bb6191f886
[Campaign #3] Starting campaign 2d075653-74b7-4720-8696-a8bb6191f886...
[Campaign #3] Started campaign 2d075653-74b7-4720-8696-a8bb6191f886
[Setup] Waiting for Campaign #3 FETCH_LEADS to complete...
[Polling #3] Starting to wait for FETCH_LEADS jobs (campaign 2d075653-74b7-4720-8696-a8bb6191f886)
[Polling #3] Expecting 1 FETCH_LEADS job(s) to complete
[API] Fetched 1 total jobs for campaign 2d075653-74b7-4720-8696-a8bb6191f886 across 1 page(s)
[API] Fetched 10 total jobs for campaign 2d075653-74b7-4720-8696-a8bb6191f886 across 1 page(s)
[Polling #3] SUCCESS: 1 FETCH_LEADS job(s) completed after 10s
[API #3] Fetching all leads for campaign 2d075653-74b7-4720-8696-a8bb6191f886...
[API #3] Successfully retrieved 9 leads
[Debug] Campaign #3 received 9 leads with 9 valid emails
[Setup] ✅ Campaign #3 ready with 9 leads (9 valid emails)

[Setup] === Setting up Campaign #4 ===
[Campaign #4] Creating campaign...
[Campaign #4] Created campaign with id: 4733313a-56f1-4d02-ab12-d4e463366f50
[Campaign #4] Starting campaign 4733313a-56f1-4d02-ab12-d4e463366f50...
[Campaign #4] Started campaign 4733313a-56f1-4d02-ab12-d4e463366f50
[Setup] Waiting for Campaign #4 FETCH_LEADS to complete...
[Polling #4] Starting to wait for FETCH_LEADS jobs (campaign 4733313a-56f1-4d02-ab12-d4e463366f50)
[Polling #4] Expecting 1 FETCH_LEADS job(s) to complete
[API] Fetched 1 total jobs for campaign 4733313a-56f1-4d02-ab12-d4e463366f50 across 1 page(s)
[API] Fetched 11 total jobs for campaign 4733313a-56f1-4d02-ab12-d4e463366f50 across 1 page(s)
[Polling #4] SUCCESS: 1 FETCH_LEADS job(s) completed after 10s
[API #4] Fetching all leads for campaign 4733313a-56f1-4d02-ab12-d4e463366f50...
[API #4] Successfully retrieved 10 leads
[Debug] Campaign #4 received 10 leads with 10 valid emails
[Setup] ✅ Campaign #4 ready with 10 leads (10 valid emails)

[Setup] === Setting up Campaign #5 ===
[Campaign #5] Creating campaign...
[Campaign #5] Created campaign with id: c5b2f798-923d-4026-8601-07cb0ba3b8c9
[Campaign #5] Starting campaign c5b2f798-923d-4026-8601-07cb0ba3b8c9...
[Campaign #5] Started campaign c5b2f798-923d-4026-8601-07cb0ba3b8c9
[Setup] Waiting for Campaign #5 FETCH_LEADS to complete...
[Polling #5] Starting to wait for FETCH_LEADS jobs (campaign c5b2f798-923d-4026-8601-07cb0ba3b8c9)
[Polling #5] Expecting 1 FETCH_LEADS job(s) to complete
[API] Fetched 1 total jobs for campaign c5b2f798-923d-4026-8601-07cb0ba3b8c9 across 1 page(s)
[API] Fetched 11 total jobs for campaign c5b2f798-923d-4026-8601-07cb0ba3b8c9 across 1 page(s)
[Polling #5] SUCCESS: 1 FETCH_LEADS job(s) completed after 10s
[API #5] Fetching all leads for campaign c5b2f798-923d-4026-8601-07cb0ba3b8c9...
[API #5] Successfully retrieved 10 leads
[Debug] Campaign #5 received 10 leads with 10 valid emails
[Setup] ✅ Campaign #5 ready with 10 leads (10 valid emails)

[Setup] === Setting up Campaign #6 ===
[Campaign #6] Creating campaign...
[Campaign #6] Created campaign with id: 052711d8-0ef4-4a94-9a4c-59cecf933c42
[Campaign #6] Starting campaign 052711d8-0ef4-4a94-9a4c-59cecf933c42...
[Campaign #6] Started campaign 052711d8-0ef4-4a94-9a4c-59cecf933c42
[Setup] Waiting for Campaign #6 FETCH_LEADS to complete...
[Polling #6] Starting to wait for FETCH_LEADS jobs (campaign 052711d8-0ef4-4a94-9a4c-59cecf933c42)
[Polling #6] Expecting 1 FETCH_LEADS job(s) to complete
[API] Fetched 1 total jobs for campaign 052711d8-0ef4-4a94-9a4c-59cecf933c42 across 1 page(s)
[API] Fetched 10 total jobs for campaign 052711d8-0ef4-4a94-9a4c-59cecf933c42 across 1 page(s)
[Polling #6] SUCCESS: 1 FETCH_LEADS job(s) completed after 10s
[API #6] Fetching all leads for campaign 052711d8-0ef4-4a94-9a4c-59cecf933c42...
[API #6] Successfully retrieved 9 leads
[Debug] Campaign #6 received 9 leads with 9 valid emails
[Setup] ✅ Campaign #6 ready with 9 leads (9 valid emails)

[Setup] === Setting up Campaign #7 ===
[Campaign #7] Creating campaign...
[Campaign #7] Created campaign with id: c2831e0f-06ba-452a-b15e-4258f58373ed
[Campaign #7] Starting campaign c2831e0f-06ba-452a-b15e-4258f58373ed...
[Campaign #7] Started campaign c2831e0f-06ba-452a-b15e-4258f58373ed
[Setup] Waiting for Campaign #7 FETCH_LEADS to complete...
[Polling #7] Starting to wait for FETCH_LEADS jobs (campaign c2831e0f-06ba-452a-b15e-4258f58373ed)
[Polling #7] Expecting 1 FETCH_LEADS job(s) to complete
[API] Fetched 1 total jobs for campaign c2831e0f-06ba-452a-b15e-4258f58373ed across 1 page(s)
[API] Fetched 9 total jobs for campaign c2831e0f-06ba-452a-b15e-4258f58373ed across 1 page(s)
[Polling #7] SUCCESS: 1 FETCH_LEADS job(s) completed after 10s
[API #7] Fetching all leads for campaign c2831e0f-06ba-452a-b15e-4258f58373ed...
[API #7] Successfully retrieved 8 leads
[Debug] Campaign #7 received 8 leads with 8 valid emails
[Setup] ✅ Campaign #7 ready with 8 leads (8 valid emails)

[Setup] === Setting up Campaign #8 ===
[Campaign #8] Creating campaign...
[Campaign #8] Created campaign with id: 6b5dea9c-2538-43cd-a1b8-e81a13377cb6
[Campaign #8] Starting campaign 6b5dea9c-2538-43cd-a1b8-e81a13377cb6...
[Campaign #8] Started campaign 6b5dea9c-2538-43cd-a1b8-e81a13377cb6
[Setup] Waiting for Campaign #8 FETCH_LEADS to complete...
[Polling #8] Starting to wait for FETCH_LEADS jobs (campaign 6b5dea9c-2538-43cd-a1b8-e81a13377cb6)
[Polling #8] Expecting 1 FETCH_LEADS job(s) to complete
[API] Fetched 1 total jobs for campaign 6b5dea9c-2538-43cd-a1b8-e81a13377cb6 across 1 page(s)
[API] Fetched 9 total jobs for campaign 6b5dea9c-2538-43cd-a1b8-e81a13377cb6 across 1 page(s)
[Polling #8] SUCCESS: 1 FETCH_LEADS job(s) completed after 10s
[API #8] Fetching all leads for campaign 6b5dea9c-2538-43cd-a1b8-e81a13377cb6...
[API #8] Successfully retrieved 8 leads
[Debug] Campaign #8 received 8 leads with 8 valid emails
[Setup] ✅ Campaign #8 ready with 8 leads (8 valid emails)

[Setup] === Setting up Campaign #9 ===
[Campaign #9] Creating campaign...
[Campaign #9] Created campaign with id: 244c6868-e09d-4731-9190-a168dfc4d1a1
[Campaign #9] Starting campaign 244c6868-e09d-4731-9190-a168dfc4d1a1...
[Campaign #9] Started campaign 244c6868-e09d-4731-9190-a168dfc4d1a1
[Setup] Waiting for Campaign #9 FETCH_LEADS to complete...
[Polling #9] Starting to wait for FETCH_LEADS jobs (campaign 244c6868-e09d-4731-9190-a168dfc4d1a1)
[Polling #9] Expecting 1 FETCH_LEADS job(s) to complete
[API] Fetched 1 total jobs for campaign 244c6868-e09d-4731-9190-a168dfc4d1a1 across 1 page(s)
[API] Fetched 10 total jobs for campaign 244c6868-e09d-4731-9190-a168dfc4d1a1 across 1 page(s)
[Polling #9] SUCCESS: 1 FETCH_LEADS job(s) completed after 10s
[API #9] Fetching all leads for campaign 244c6868-e09d-4731-9190-a168dfc4d1a1...
[API #9] Successfully retrieved 9 leads
[Debug] Campaign #9 received 9 leads with 9 valid emails
[Setup] ✅ Campaign #9 ready with 9 leads (9 valid emails)

[Setup] === Setting up Campaign #10 ===
[Campaign #10] Creating campaign...
[Campaign #10] Created campaign with id: 20898252-0d5e-4e6d-a609-dc9c66017ead
[Campaign #10] Starting campaign 20898252-0d5e-4e6d-a609-dc9c66017ead...
[Campaign #10] Started campaign 20898252-0d5e-4e6d-a609-dc9c66017ead
[Setup] Waiting for Campaign #10 FETCH_LEADS to complete...
[Polling #10] Starting to wait for FETCH_LEADS jobs (campaign 20898252-0d5e-4e6d-a609-dc9c66017ead)
[Polling #10] Expecting 1 FETCH_LEADS job(s) to complete
[API] Fetched 1 total jobs for campaign 20898252-0d5e-4e6d-a609-dc9c66017ead across 1 page(s)
[API] Fetched 10 total jobs for campaign 20898252-0d5e-4e6d-a609-dc9c66017ead across 1 page(s)
[Polling #10] SUCCESS: 1 FETCH_LEADS job(s) completed after 10s
[API #10] Fetching all leads for campaign 20898252-0d5e-4e6d-a609-dc9c66017ead...
[API #10] Successfully retrieved 9 leads
[Debug] Campaign #10 received 9 leads with 9 valid emails
[Setup] ✅ Campaign #10 ready with 9 leads (9 valid emails)

[Setup] ✅ All 10 campaigns created successfully!
[Validation] Campaign #1: 5 unique emails
[Validation] Campaign #2: 10 unique emails
[Validation] Campaign #3: 9 unique emails
[Validation] Campaign #4: 10 unique emails
[Validation] Campaign #5: 10 unique emails
[Validation] Campaign #6: 9 unique emails
[Validation] Campaign #7: 8 unique emails
[Validation] Campaign #8: 8 unique emails
[Validation] Campaign #9: 9 unique emails
[Validation] Campaign #10: 9 unique emails
[Validation] ✅ 87 total leads, all 87 emails unique across 10 campaigns

🔍 PHASE 4: Process Integrity Validation
--------------------------------------------------

[Validation] Validating process integrity for 10 campaigns...
[Validation] ✅ Campaign #1: 5 leads, 5 valid emails
[Validation] ✅ Campaign #2: 10 leads, 10 valid emails
[Validation] ✅ Campaign #3: 9 leads, 9 valid emails
[Validation] ✅ Campaign #4: 10 leads, 10 valid emails
[Validation] ✅ Campaign #5: 10 leads, 10 valid emails
[Validation] ✅ Campaign #6: 9 leads, 9 valid emails
[Validation] ✅ Campaign #7: 8 leads, 8 valid emails
[Validation] ✅ Campaign #8: 8 leads, 8 valid emails
[Validation] ✅ Campaign #9: 9 leads, 9 valid emails
[Validation] ✅ Campaign #10: 9 leads, 9 valid emails
[Validation] ✅ Process integrity validated:
[Validation]   - 10 campaigns processed successfully
[Validation]   - 87 total leads generated
[Validation]   - 87 unique emails (no duplicates)
[Validation]   - Lead distribution: 5-10 leads per campaign

🔍 Post-Creation Campaign Status: Campaign Status Summary
--------------------------------------------------
📊 Status Distribution (10 campaigns):
   🟢 RUNNING: 10

✅ Campaign Status Validation: All 10 campaigns in expected state

⚡ PHASE 5: Circuit Breaker-Aware Concurrent Job Monitoring
--------------------------------------------------
[Monitor] Starting enhanced monitoring with automatic circuit breaker detection
[Monitor] Will perform service health checks every 30 seconds during execution
[Monitor] Will also monitor campaign status for unexpected pauses
[Monitor] Test will stop gracefully if service failures are detected

[Monitor CB] Starting circuit breaker-aware monitoring for 10 campaigns
[Monitor CB] Circuit breaker checks will run every 30s
[API] Fetched 6 total jobs for campaign 49945eb4-ff65-4774-a771-d74cb085d92d across 1 page(s)
[Monitor CB] ✅ Campaign #1 completed all 5 jobs
[API] Fetched 11 total jobs for campaign 75de7ae7-f97a-488e-8e8a-c10337350b98 across 1 page(s)
[API] Fetched 10 total jobs for campaign 2d075653-74b7-4720-8696-a8bb6191f886 across 1 page(s)
[API] Fetched 11 total jobs for campaign 4733313a-56f1-4d02-ab12-d4e463366f50 across 1 page(s)
[API] Fetched 11 total jobs for campaign c5b2f798-923d-4026-8601-07cb0ba3b8c9 across 1 page(s)
[API] Fetched 10 total jobs for campaign 052711d8-0ef4-4a94-9a4c-59cecf933c42 across 1 page(s)
[API] Fetched 9 total jobs for campaign c2831e0f-06ba-452a-b15e-4258f58373ed across 1 page(s)
[Monitor CB] ✅ Campaign #7 completed all 8 jobs
[API] Fetched 9 total jobs for campaign 6b5dea9c-2538-43cd-a1b8-e81a13377cb6 across 1 page(s)
[API] Fetched 10 total jobs for campaign 244c6868-e09d-4731-9190-a168dfc4d1a1 across 1 page(s)
[API] Fetched 10 total jobs for campaign 20898252-0d5e-4e6d-a609-dc9c66017ead across 1 page(s)
[API] Fetched 11 total jobs for campaign 75de7ae7-f97a-488e-8e8a-c10337350b98 across 1 page(s)
[API] Fetched 10 total jobs for campaign 2d075653-74b7-4720-8696-a8bb6191f886 across 1 page(s)
[API] Fetched 11 total jobs for campaign 4733313a-56f1-4d02-ab12-d4e463366f50 across 1 page(s)
[API] Fetched 11 total jobs for campaign c5b2f798-923d-4026-8601-07cb0ba3b8c9 across 1 page(s)
[API] Fetched 10 total jobs for campaign 052711d8-0ef4-4a94-9a4c-59cecf933c42 across 1 page(s)
[API] Fetched 9 total jobs for campaign 6b5dea9c-2538-43cd-a1b8-e81a13377cb6 across 1 page(s)
[API] Fetched 10 total jobs for campaign 244c6868-e09d-4731-9190-a168dfc4d1a1 across 1 page(s)
[API] Fetched 10 total jobs for campaign 20898252-0d5e-4e6d-a609-dc9c66017ead across 1 page(s)
[API] Fetched 11 total jobs for campaign 75de7ae7-f97a-488e-8e8a-c10337350b98 across 1 page(s)
[API] Fetched 10 total jobs for campaign 2d075653-74b7-4720-8696-a8bb6191f886 across 1 page(s)
[API] Fetched 11 total jobs for campaign 4733313a-56f1-4d02-ab12-d4e463366f50 across 1 page(s)
[API] Fetched 11 total jobs for campaign c5b2f798-923d-4026-8601-07cb0ba3b8c9 across 1 page(s)
[API] Fetched 10 total jobs for campaign 052711d8-0ef4-4a94-9a4c-59cecf933c42 across 1 page(s)
[API] Fetched 9 total jobs for campaign 6b5dea9c-2538-43cd-a1b8-e81a13377cb6 across 1 page(s)
[API] Fetched 10 total jobs for campaign 244c6868-e09d-4731-9190-a168dfc4d1a1 across 1 page(s)
[API] Fetched 10 total jobs for campaign 20898252-0d5e-4e6d-a609-dc9c66017ead across 1 page(s)
[API] Fetched 11 total jobs for campaign 75de7ae7-f97a-488e-8e8a-c10337350b98 across 1 page(s)
[API] Fetched 10 total jobs for campaign 2d075653-74b7-4720-8696-a8bb6191f886 across 1 page(s)
[API] Fetched 11 total jobs for campaign 4733313a-56f1-4d02-ab12-d4e463366f50 across 1 page(s)
[API] Fetched 11 total jobs for campaign c5b2f798-923d-4026-8601-07cb0ba3b8c9 across 1 page(s)
[API] Fetched 10 total jobs for campaign 052711d8-0ef4-4a94-9a4c-59cecf933c42 across 1 page(s)
[API] Fetched 9 total jobs for campaign 6b5dea9c-2538-43cd-a1b8-e81a13377cb6 across 1 page(s)
[API] Fetched 10 total jobs for campaign 244c6868-e09d-4731-9190-a168dfc4d1a1 across 1 page(s)
[API] Fetched 10 total jobs for campaign 20898252-0d5e-4e6d-a609-dc9c66017ead across 1 page(s)
[API] Fetched 11 total jobs for campaign 75de7ae7-f97a-488e-8e8a-c10337350b98 across 1 page(s)
[API] Fetched 10 total jobs for campaign 2d075653-74b7-4720-8696-a8bb6191f886 across 1 page(s)
[API] Fetched 11 total jobs for campaign 4733313a-56f1-4d02-ab12-d4e463366f50 across 1 page(s)
[API] Fetched 11 total jobs for campaign c5b2f798-923d-4026-8601-07cb0ba3b8c9 across 1 page(s)
[API] Fetched 10 total jobs for campaign 052711d8-0ef4-4a94-9a4c-59cecf933c42 across 1 page(s)
[API] Fetched 9 total jobs for campaign 6b5dea9c-2538-43cd-a1b8-e81a13377cb6 across 1 page(s)
[API] Fetched 10 total jobs for campaign 244c6868-e09d-4731-9190-a168dfc4d1a1 across 1 page(s)
[API] Fetched 10 total jobs for campaign 20898252-0d5e-4e6d-a609-dc9c66017ead across 1 page(s)
[API] Fetched 11 total jobs for campaign 75de7ae7-f97a-488e-8e8a-c10337350b98 across 1 page(s)
[API] Fetched 10 total jobs for campaign 2d075653-74b7-4720-8696-a8bb6191f886 across 1 page(s)
[API] Fetched 11 total jobs for campaign 4733313a-56f1-4d02-ab12-d4e463366f50 across 1 page(s)
[API] Fetched 11 total jobs for campaign c5b2f798-923d-4026-8601-07cb0ba3b8c9 across 1 page(s)
[API] Fetched 10 total jobs for campaign 052711d8-0ef4-4a94-9a4c-59cecf933c42 across 1 page(s)
[API] Fetched 9 total jobs for campaign 6b5dea9c-2538-43cd-a1b8-e81a13377cb6 across 1 page(s)
[API] Fetched 10 total jobs for campaign 244c6868-e09d-4731-9190-a168dfc4d1a1 across 1 page(s)
[API] Fetched 10 total jobs for campaign 20898252-0d5e-4e6d-a609-dc9c66017ead across 1 page(s)

[Monitor CB] === Status Update (after 15s) ===
[Status] Campaigns: 2 complete, 1 processing, 0 failed / 10 total
[Status] Jobs: 22 complete, 0 failed / 87 total (25.3% complete)
[API] Fetched 11 total jobs for campaign 75de7ae7-f97a-488e-8e8a-c10337350b98 across 1 page(s)
[API] Fetched 10 total jobs for campaign 2d075653-74b7-4720-8696-a8bb6191f886 across 1 page(s)
[API] Fetched 11 total jobs for campaign 4733313a-56f1-4d02-ab12-d4e463366f50 across 1 page(s)
[API] Fetched 11 total jobs for campaign c5b2f798-923d-4026-8601-07cb0ba3b8c9 across 1 page(s)
[API] Fetched 10 total jobs for campaign 052711d8-0ef4-4a94-9a4c-59cecf933c42 across 1 page(s)
[API] Fetched 9 total jobs for campaign 6b5dea9c-2538-43cd-a1b8-e81a13377cb6 across 1 page(s)
[API] Fetched 10 total jobs for campaign 244c6868-e09d-4731-9190-a168dfc4d1a1 across 1 page(s)
[API] Fetched 10 total jobs for campaign 20898252-0d5e-4e6d-a609-dc9c66017ead across 1 page(s)
[API] Fetched 11 total jobs for campaign 75de7ae7-f97a-488e-8e8a-c10337350b98 across 1 page(s)
[API] Fetched 10 total jobs for campaign 2d075653-74b7-4720-8696-a8bb6191f886 across 1 page(s)
[API] Fetched 11 total jobs for campaign 4733313a-56f1-4d02-ab12-d4e463366f50 across 1 page(s)
[API] Fetched 11 total jobs for campaign c5b2f798-923d-4026-8601-07cb0ba3b8c9 across 1 page(s)
[API] Fetched 10 total jobs for campaign 052711d8-0ef4-4a94-9a4c-59cecf933c42 across 1 page(s)
[API] Fetched 9 total jobs for campaign 6b5dea9c-2538-43cd-a1b8-e81a13377cb6 across 1 page(s)
[API] Fetched 10 total jobs for campaign 244c6868-e09d-4731-9190-a168dfc4d1a1 across 1 page(s)
[API] Fetched 10 total jobs for campaign 20898252-0d5e-4e6d-a609-dc9c66017ead across 1 page(s)
[API] Fetched 11 total jobs for campaign 75de7ae7-f97a-488e-8e8a-c10337350b98 across 1 page(s)
[API] Fetched 10 total jobs for campaign 2d075653-74b7-4720-8696-a8bb6191f886 across 1 page(s)
[API] Fetched 11 total jobs for campaign 4733313a-56f1-4d02-ab12-d4e463366f50 across 1 page(s)
[API] Fetched 11 total jobs for campaign c5b2f798-923d-4026-8601-07cb0ba3b8c9 across 1 page(s)
[API] Fetched 10 total jobs for campaign 052711d8-0ef4-4a94-9a4c-59cecf933c42 across 1 page(s)
[API] Fetched 9 total jobs for campaign 6b5dea9c-2538-43cd-a1b8-e81a13377cb6 across 1 page(s)
[API] Fetched 10 total jobs for campaign 244c6868-e09d-4731-9190-a168dfc4d1a1 across 1 page(s)
[API] Fetched 10 total jobs for campaign 20898252-0d5e-4e6d-a609-dc9c66017ead across 1 page(s)
[API] Fetched 11 total jobs for campaign 75de7ae7-f97a-488e-8e8a-c10337350b98 across 1 page(s)
[API] Fetched 10 total jobs for campaign 2d075653-74b7-4720-8696-a8bb6191f886 across 1 page(s)
[API] Fetched 11 total jobs for campaign 4733313a-56f1-4d02-ab12-d4e463366f50 across 1 page(s)
[API] Fetched 11 total jobs for campaign c5b2f798-923d-4026-8601-07cb0ba3b8c9 across 1 page(s)
[API] Fetched 10 total jobs for campaign 052711d8-0ef4-4a94-9a4c-59cecf933c42 across 1 page(s)
[API] Fetched 9 total jobs for campaign 6b5dea9c-2538-43cd-a1b8-e81a13377cb6 across 1 page(s)
[API] Fetched 10 total jobs for campaign 244c6868-e09d-4731-9190-a168dfc4d1a1 across 1 page(s)
[API] Fetched 10 total jobs for campaign 20898252-0d5e-4e6d-a609-dc9c66017ead across 1 page(s)

[Monitor CB] Performing circuit breaker health check (after 31s)...
[Monitor CB] ⚠️  CRITICAL: 1 service(s) not in 'closed' state:
[Monitor CB]     OPENAI: half_open
[Monitor CB]       Pause info: {'paused_at': '2025-06-03T03:19:14.994894', 'service': 'openai', 'reason': 'circuit_breaker_open'}
[Monitor CB] ❌ STOPPING TEST: 64 jobs paused due to circuit breaker issues
[Monitor CB] Paused jobs by service: {'perplexity': 0, 'openai': 64, 'apollo': 0, 'instantly': 0, 'millionverifier': 0}

================================================================================
❌ TEST STOPPED: CIRCUIT BREAKER TRIGGERED
================================================================================

🔍 Circuit Breaker Status:
  ⚠️  OPENAI: half_open
      Reason: {'paused_at': '2025-06-03T03:19:14.994894', 'service': 'openai', 'reason': 'circuit_breaker_open'}
      Failures: 7/5

📊 Campaigns Paused: 1
  🛑 Campaign multiple_campaigns_affected_by_openai
      Message: Jobs paused due to openai circuit breaker in half_open state
      Reason: Circuit breaker half_open for openai: {'paused_at': '2025-06-03T03:19:14.994894', 'service': 'openai', 'reason': 'circuit_breaker_open'}

💡 This indicates a real service failure occurred during testing.
💡 Check service health and retry the test when services are restored.
================================================================================

🔍 Final Campaign Status Check (Post-Failure)
--------------------------------------------------

🔍 Post-Failure Campaign Status: Campaign Status Summary
--------------------------------------------------
📊 Status Distribution (10 campaigns):
   🟢 RUNNING: 10

================================================================================
🛑 TEST RESULT: SERVICE FAILURE DETECTED
================================================================================
📋 Summary:
  • Test execution was stopped due to circuit breaker activation
  • This indicates real service failures occurred during test execution
  • The test infrastructure is working correctly by detecting service issues
  • This is NOT a test failure - it's successful service failure detection

💡 Recommended Actions:
  1. Check service health and logs to identify the root cause
  2. Wait for services to recover and circuit breakers to close
  3. Retry the test once services are stable
================================================================================
[MockApifyClient] Reset working dataset to original state: 500 records available
[MockApifyClient] System reset for new test run
[Cleanup] Error during cleanup: (psycopg2.OperationalError) connection to server at "localhost" (::1), port 15432 failed: Connection refused
        Is the server running on that host and accepting TCP/IP connections?
connection to server at "localhost" (127.0.0.1), port 15432 failed: Connection refused
        Is the server running on that host and accepting TCP/IP connections?

(Background on this error at: https://sqlalche.me/e/20/e3q8)
=================== TEST OUTPUT END ===================

[SUCCESS] Test execution completed successfully

===============================================
 PHASE 7: RESULTS VALIDATION
===============================================
[STEP] Validating test results...
[STEP] Checking database for test data...
Campaigns created: 10
Leads created: 87
Jobs created: 97
Organizations created: 1
Users created: 1
Database validation successful
[SUCCESS] Results validation completed

===============================================
 EXECUTION SUMMARY
===============================================
[SUCCESS] 🎉 Concurrent campaigns test completed successfully!
[INFO] ✅ Log file truncated
[INFO] ✅ Containers rebuilt and started fresh
[INFO] ✅ Database tables cleared
[INFO] ✅ Redis cache cleared
[INFO] ✅ Test executed successfully
[INFO] ✅ Results validated

[INFO] Next steps:
[INFO]   - Review the test output above for detailed results
[INFO]   - Check logs/combined.log for application logs
[INFO]   - Use 'docker exec fastapi-k8-proto-api-1 python -c "from app.core.database import SessionLocal; ..."' to query test data

[SUCCESS] Reset and test execution completed successfully! 🚀
➜  fastapi-k8-proto git:(main) ✗ 
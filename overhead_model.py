'''
NOTES:
65k emails per month is the possible througput

so estimate 80k per month for infra load.

work back to the required service througput and cost

How many accounts for each service? 

rate limits for each service?

'''


goalSendingThroughput = 80000

apolloAttrition = 0.90 # 5% attrition rate
perplexityAttrition = 0.95 # 5% attrition rate
emailVerificationAttrition = 0.95 # 5% attrition rate
 
combinedAttrition = apolloAttrition * perplexityAttrition * emailVerificationAttrition

initialScrapingRequirement = goalSendingThroughput / combinedAttrition

# ---> basically we need to scrape 100k leads to get 80k emails per month

leadsScrapedPerMinute =  initialScrapingRequirement/30/24/60

#in batches of 500 that take 5min each at 60cents per run

numberOfActorRuns = initialScrapingRequirement/500 # per month

perMonthActorCost = numberOfActorRuns * 0.6

# estimate the load on the emailVerification service
emailCountToVerify = initialScrapingRequirement * apolloAttrition

# TODO: figure out the number of accounts neeed

emailsToEnrich = initialScrapingRequirement * emailVerificationAttrition

# Comprehensive results summary
print(f"""
=== LEAD GENERATION OVERHEAD MODEL RESULTS ===

Goal Sending Throughput: {goalSendingThroughput:,} emails/month

Attrition Rates:
  - Apollo: {(1-apolloAttrition)*100:.1f}%
  - Perplexity: {(1-perplexityAttrition)*100:.1f}%
  - Email Verification: {(1-emailVerificationAttrition)*100:.1f}%
  - Combined Attrition: {(1-combinedAttrition)*100:.1f}%

Scraping Requirements:
  - Initial Scraping Requirement: {initialScrapingRequirement:,.1f} leads/month
  - Leads Scraped Per Minute: {leadsScrapedPerMinute:.3f}

Actor Runs (Apify) in batches of 500 that take 5min each at 60cents per run
  - Number of Actor Runs: {numberOfActorRuns:.0f} runs/month
  - Cost Per Month: ${perMonthActorCost:.2f}

Email Verification Load:
  - Emails to Verify: {emailCountToVerify:,.0f} emails/month

Enrichment Load:
  - Leads to enrich: {emailsToEnrich:,.0f} leads/month

===============================================
""")


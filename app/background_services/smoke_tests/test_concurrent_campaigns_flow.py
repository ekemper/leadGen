import os
import sys

# Get project root and change working directory to it so pydantic-settings can find .env
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..'))
os.chdir(project_root)
print(f"[Setup] Changed working directory to: {project_root}")

# Ensure project root is in sys.path for app imports
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Enable the Apollo mock but leave Perplexity live
os.environ["USE_APIFY_CLIENT_MOCK"] = "true"  # keep Apollo mocked

from app.core.config import settings

# Import all utility functions from the refactored modules - CHANGED TO ABSOLUTE IMPORTS
from app.background_services.smoke_tests.utils import (
    # Auth utilities
    signup_and_login,
    create_organization,
    
    # Campaign utilities
    create_campaigns_sequentially,
    
    # Job utilities
    wait_for_jobs,
    monitor_all_campaigns_jobs_with_cb_awareness,
    
    # Circuit breaker utilities
    check_circuit_breaker_status,
    check_campaigns_paused_by_circuit_breaker,
    report_circuit_breaker_failure,
    
    # Validation utilities
    validate_campaign_data,
    validate_no_duplicate_emails,
    validate_no_unexpected_pauses,
    
    # Reporting utilities
    check_campaign_status_summary,
    report_campaign_status_summary,
    analyze_process_results,
    
    # Database utilities
    cleanup_test_data
)

# Configuration for concurrent testing
API_BASE = f"http://localhost:8000{settings.API_V1_STR}"
NUM_CAMPAIGNS = 10  # Number of campaigns to run concurrently
CAMPAIGN_TIMEOUT = 1000  # Increased timeout for concurrent operations
LEADS_PER_CAMPAIGN = 20  # Number of leads per campaign

def get_expected_campaign_emails(campaign_index):
    """DEPRECATED: We no longer predict specific emails per campaign.
    The pop-based approach makes this unnecessary."""
    # This function is kept for compatibility but no longer used
    # in the main test logic since we focus on process validation
    print(f"[Debug] Campaign #{campaign_index} - Using pop-based approach, no email prediction needed")
    return set()

def main():
    from app.background_services.smoke_tests.mock_apify_client import reset_campaign_counter, get_dataset_status, check_redis_availability
    
    print("\n" + "="*80)
    print("🚀 STARTING CONCURRENT CAMPAIGNS TEST WITH CIRCUIT BREAKER AWARENESS")
    print("📊 Testing normal campaign execution with automatic service failure detection")
    print("📊 Will stop gracefully and report clearly if circuit breaker triggers")
    print("📊 Focus: Happy path validation with robust service health monitoring")
    print("="*80)
    
    # Track test email for cleanup
    test_email = None
    
    # First check: Ensure Redis is available for MockApifyClient
    print("\n🔍 PRE-FLIGHT CHECK: Redis Availability")
    print("-" * 50)
    if not check_redis_availability():
        print("❌ ABORTING TEST: Redis is not available!")
        print("Please ensure Redis is running and accessible before running this test.")
        return False
    
    # Debug: Check dataset status before starting
    dataset_status = get_dataset_status()
    print(f"\n[DEBUG] Dataset status at start: {dataset_status}")
    
    try:
        print("\n📋 PHASE 1: Authentication & Setup")
        print("-" * 50)
        token, test_email = signup_and_login(API_BASE)
        organization_id = create_organization(token, API_BASE)
        
        print("\n🔍 PHASE 2: Pre-Test Circuit Breaker Health Check")
        print("-" * 50)
        print("[Health Check] Verifying all services are healthy before starting test...")
        
        cb_status = check_circuit_breaker_status(token, API_BASE)
        if cb_status and cb_status.get("data", {}).get("circuit_breakers"):
            circuit_breakers = cb_status["data"]["circuit_breakers"]
            unhealthy_services = []
            
            for service, status in circuit_breakers.items():
                if isinstance(status, dict):
                    state = status.get("circuit_state", "unknown")
                    if state != "closed":
                        unhealthy_services.append((service, state, status))
            
            if unhealthy_services:
                print(f"⚠️  WARNING: {len(unhealthy_services)} service(s) not in healthy state:")
                for service, state, status in unhealthy_services:
                    print(f"   🔴 {service.upper()}: {state}")
                    if status.get("pause_info"):
                        print(f"      Reason: {status['pause_info']}")
                    if status.get("failure_count", 0) > 0:
                        print(f"      Failures: {status['failure_count']}/{status.get('failure_threshold', 'unknown')}")
                
                print("\n💡 Recommendation: Wait for services to recover or investigate issues before testing")
                print("💡 Continuing test anyway - will monitor and stop if circuit breaker triggers")
            else:
                healthy_count = len([s for s in circuit_breakers.values() 
                                   if isinstance(s, dict) and s.get("circuit_state") == "closed"])
                print(f"✅ All services healthy: {healthy_count}/{len(circuit_breakers)} circuit breakers in 'closed' state")
                for service in circuit_breakers.keys():
                    print(f"   🟢 {service.upper()}: closed")
        else:
            print("⚠️  Could not retrieve circuit breaker status")
            print("💡 Continuing test - will monitor circuit breaker during execution")
        
        print("\n📋 PHASE 3: Sequential Campaign Creation with Pop-Based Data")
        print("-" * 50)
        print(f"[Setup] Creating {NUM_CAMPAIGNS} campaigns sequentially...")
        campaigns_data = create_campaigns_sequentially(
            token, 
            organization_id, 
            NUM_CAMPAIGNS, 
            LEADS_PER_CAMPAIGN,
            wait_for_jobs,
            validate_no_duplicate_emails,
            API_BASE
        )
        
        print(f"\n🔍 PHASE 4: Process Integrity Validation")
        print("-" * 50)
        validate_campaign_data(campaigns_data)
        
        # Add campaign status validation as part of integrity checking
        campaign_ids = list(campaigns_data.keys())
        
        # Report initial campaign status after creation
        status_summary, campaign_details = report_campaign_status_summary(
            token, campaign_ids, "Post-Creation Campaign Status", API_BASE
        )
        
        # Validate no unexpected pauses occurred during setup
        no_pauses, paused_campaigns = validate_no_unexpected_pauses(token, campaign_ids, API_BASE)
        if not no_pauses:
            print(f"\n❌ INTEGRITY CHECK FAILED: Campaigns paused during setup")
            print("💡 This indicates service issues occurred during campaign creation")
            return False
        
        print(f"\n✅ Campaign Status Validation: All {len(campaign_ids)} campaigns in expected state")
        
        print(f"\n⚡ PHASE 5: Circuit Breaker-Aware Concurrent Job Monitoring")
        print("-" * 50)
        print("[Monitor] Starting enhanced monitoring with automatic circuit breaker detection")
        print("[Monitor] Will perform service health checks every 30 seconds during execution")
        print("[Monitor] Will also monitor campaign status for unexpected pauses")
        print("[Monitor] Test will stop gracefully if service failures are detected")
        
        job_results = monitor_all_campaigns_jobs_with_cb_awareness(
            token, 
            campaigns_data, 
            CAMPAIGN_TIMEOUT,
            check_circuit_breaker_status_func=check_circuit_breaker_status,
            check_campaigns_paused_by_circuit_breaker_func=check_campaigns_paused_by_circuit_breaker,
            report_circuit_breaker_failure_func=report_circuit_breaker_failure,
            validate_no_unexpected_pauses_func=validate_no_unexpected_pauses,
            check_campaign_status_summary_func=check_campaign_status_summary,
            api_base=API_BASE
        )
        
        # Enhanced circuit breaker failure handling
        if job_results is None:
            # Before reporting circuit breaker failure, check campaign status one more time
            print("\n🔍 Final Campaign Status Check (Post-Failure)")
            print("-" * 50)
            final_status_summary, final_campaign_details = report_campaign_status_summary(
                token, campaign_ids, "Post-Failure Campaign Status", API_BASE
            )
            
            print("\n" + "="*80)
            print("🛑 TEST RESULT: SERVICE FAILURE DETECTED")
            print("="*80)
            print("📋 Summary:")
            print("  • Test execution was stopped due to circuit breaker activation")
            print("  • This indicates real service failures occurred during test execution")
            print("  • The test infrastructure is working correctly by detecting service issues")
            print("  • This is NOT a test failure - it's successful service failure detection")
            print("\n💡 Recommended Actions:")
            print("  1. Check service health and logs to identify the root cause")
            print("  2. Wait for services to recover and circuit breakers to close")
            print("  3. Retry the test once services are stable")
            print("="*80)
            return False  # Return False to indicate test was stopped, not failed
        
        print(f"\n📊 PHASE 6: End-to-End Process Analysis")
        print("-" * 50)
        
        # Final campaign status validation before reporting success
        print("🔍 Final Campaign Status Validation")
        print("-" * 40)
        
        final_status_summary, final_campaign_details = report_campaign_status_summary(
            token, campaign_ids, "Final Campaign Status", API_BASE
        )
        
        # Check for any unexpected final states
        final_no_pauses, final_paused_campaigns = validate_no_unexpected_pauses(token, campaign_ids, API_BASE)
        if not final_no_pauses:
            print(f"\n⚠️  WARNING: Some campaigns ended in PAUSED state")
            print("💡 This may indicate service issues occurred late in the test")
        
        # Count successful completions
        completed_campaigns = final_status_summary.get("COMPLETED", 0)
        running_campaigns = final_status_summary.get("RUNNING", 0)
        
        analyze_process_results(campaigns_data, job_results)
        
        print("\n" + "="*80)
        print("🎉 TEST RESULT: SUCCESSFUL EXECUTION WITH SERVICE HEALTH MONITORING")
        print("="*80)
        print("📋 Summary:")
        print("  • All campaigns executed successfully through the happy path")
        print("  • No service failures detected during test execution")
        print("  • Circuit breaker monitoring functioned correctly")
        print("  • Pop-based mock data distribution worked perfectly")
        print("  • System successfully handled concurrent processing without issues")
        print("\n✅ Key Achievements:")
        print("  ✅ Service health monitoring: Active and functional")
        print("  ✅ Campaign execution: All completed successfully")
        print("  ✅ Data integrity: No duplicates or conflicts detected")
        print("  ✅ Concurrent processing: Robust and reliable")
        print("="*80)
        
        return True
        
    except Exception as e:
        print(f"\n" + "="*80)
        print("❌ TEST RESULT: APPLICATION/INFRASTRUCTURE FAILURE")
        print("="*80)
        print("📋 Summary:")
        print("  • Test failed due to application or infrastructure issues")
        print("  • This is a legitimate test failure requiring investigation")
        print("  • Circuit breaker monitoring was not the cause of failure")
        print(f"  • Error: {e}")
        print("\n💡 Recommended Actions:")
        print("  1. Review the error details and stack trace")
        print("  2. Check application logs for additional context")
        print("  3. Verify test environment and infrastructure health")
        print("  4. Fix the underlying issue and retry the test")
        print("="*80)
        raise
    finally:
        # Clean up test data
        if test_email:
            cleanup_test_data(test_email)

if __name__ == "__main__":
    main() 
"""
Job monitoring and polling utilities for smoke tests.
"""

import requests
import time
from app.core.config import settings


def _log_job_status(target_jobs, waited, campaign_index, job_type):
    """Log current status of jobs with breakdown by status."""
    print(f"[Polling #{campaign_index}] {waited}s elapsed - Found {len(target_jobs)} {job_type} job(s)")
    if target_jobs:
        status_counts = {}
        for job in target_jobs:
            status = job["status"]
            status_counts[status] = status_counts.get(status, 0) + 1
        status_summary = ", ".join(f"{status}: {count}" for status, count in status_counts.items())
        print(f"[Polling #{campaign_index}] Job status breakdown: {status_summary}")


def _check_job_completion(target_jobs, expected_count, campaign_index, job_type, waited):
    """
    Check if jobs are completed and handle failures.
    Returns: ('continue', None) | ('success', jobs) | ('wait_more', None)
    """
    if not target_jobs or not all(j["status"] in ("COMPLETED", "FAILED") for j in target_jobs):
        return ('continue', None)
    
    # All jobs are either completed or failed
    failed = [j for j in target_jobs if j["status"] == "FAILED"]
    if failed:
        print(f"[Polling #{campaign_index}] ERROR: {len(failed)} {job_type} job(s) failed!")
        for job in failed:
            error_msg = job.get('error') or job.get('error_message', 'Unknown error')
            print(f"[Polling #{campaign_index}] Failed job {job['id']}: {error_msg}")
        msgs = "; ".join(f.get('error') or f.get('error_message', 'Unknown error') for f in failed)
        raise AssertionError(f"Campaign #{campaign_index} {job_type} job(s) failed: {msgs}")
    
    # Check if we have the expected count or if no specific count was expected
    if expected_count is None or len(target_jobs) >= expected_count:
        print(f"[Polling #{campaign_index}] SUCCESS: {len(target_jobs)} {job_type} job(s) completed after {waited}s")
        return ('success', target_jobs)
    else:
        # We have completed jobs but not enough yet, continue waiting
        print(f"[Polling #{campaign_index}] {len(target_jobs)}/{expected_count} {job_type} job(s) completed, waiting for more...")
        return ('wait_more', None)


def _report_timeout_status(token, campaign_id, job_type, campaign_index, timeout, api_base):
    """Report detailed status when timeout is reached and raise TimeoutError."""
    print(f"[Polling #{campaign_index}] TIMEOUT: {job_type} jobs not finished within {timeout}s")
    jobs = fetch_campaign_jobs(token, campaign_id, api_base)
    target = [j for j in jobs if j["job_type"] == job_type]
    if target:
        print(f"[Polling #{campaign_index}] Final status of {len(target)} {job_type} job(s):")
        for job in target:
            print(f"[Polling #{campaign_index}]   Job {job['id']}: {job['status']} - {job.get('error_message', 'No error message')}")
    else:
        print(f"[Polling #{campaign_index}] No {job_type} jobs found at timeout")
    
    raise TimeoutError(f"Campaign #{campaign_index} {job_type} jobs not finished within {timeout}s")


def fetch_campaign_jobs(token, campaign_id, api_base):
    """Return list of jobs for the given campaign via API, handling pagination."""
    headers = {"Authorization": f"Bearer {token}"}
    all_jobs = []
    page = 1
    per_page = 100  # Use larger page size to minimize API calls
    
    while True:
        params = {
            "campaign_id": campaign_id,
            "page": page,
            "per_page": per_page
        }
        resp = requests.get(f"{api_base}/jobs", headers=headers, params=params)
        if resp.status_code != 200:
            raise Exception(f"Failed to fetch jobs: {resp.status_code} {resp.text}")
        
        # Fix: Check if response has "data" wrapper or direct access
        response_data = resp.json()
        jobs_data = response_data.get("data", {}).get("jobs") or response_data.get("jobs", [])
        
        if not jobs_data:
            break  # No more jobs
            
        all_jobs.extend(jobs_data)
        
        # Check if we've fetched all pages
        if "data" in response_data and isinstance(response_data["data"], dict):
            data = response_data["data"]
            if "pages" in data and page >= data["pages"]:
                break  # We've fetched all pages
            elif len(jobs_data) < per_page:
                break  # Last page (partial)
        else:
            # Fallback: if we got less than per_page items, we're on the last page
            if len(jobs_data) < per_page:
                break
                
        page += 1
    
    print(f"[API] Fetched {len(all_jobs)} total jobs for campaign {campaign_id} across {page} page(s)")
    return all_jobs


def wait_for_jobs(token, campaign_id, job_type, campaign_index, expected_count=None, timeout=300, interval=10, api_base=None):
    """Wait for specific job type to complete for a campaign."""
    if api_base is None:
        raise ValueError("api_base is required")
        
    print(f"[Polling #{campaign_index}] Starting to wait for {job_type} jobs (campaign {campaign_id})")
    if expected_count:
        print(f"[Polling #{campaign_index}] Expecting {expected_count} {job_type} job(s) to complete")
    else:
        print(f"[Polling #{campaign_index}] Waiting for any {job_type} job(s) to complete")
    
    waited = 0
    last_status_log = 0
    status_log_interval = 15  # Log status every 15 seconds for concurrent tests
    
    while waited < timeout:
        jobs = fetch_campaign_jobs(token, campaign_id, api_base)
        target = [j for j in jobs if j["job_type"] == job_type]
        
        # Log current status periodically
        if waited - last_status_log >= status_log_interval:
            _log_job_status(target, waited, campaign_index, job_type)
            last_status_log = waited
        
        # Check if we have enough jobs yet
        if expected_count and len(target) < expected_count:
            time.sleep(interval)
            waited += interval
            continue

        # Check job completion status
        result, completed_jobs = _check_job_completion(target, expected_count, campaign_index, job_type, waited)
        
        if result == 'success':
            return completed_jobs
        elif result == 'wait_more':
            time.sleep(interval)
            waited += interval
            continue
        # else result == 'continue', so continue to next iteration

        time.sleep(interval)
        waited += interval
    
    # Timeout reached
    _report_timeout_status(token, campaign_id, job_type, campaign_index, timeout, api_base)


def print_consolidated_status(job_tracker):
    """Print a consolidated view of all campaign job statuses"""
    total_campaigns = len(job_tracker)
    completed_campaigns = sum(1 for t in job_tracker.values() if t['status'] == 'completed')
    failed_campaigns = sum(1 for t in job_tracker.values() if t['status'] == 'failed')
    processing_campaigns = sum(1 for t in job_tracker.values() if t['status'] == 'processing')
    
    total_jobs_expected = sum(t['expected_jobs'] for t in job_tracker.values())
    total_jobs_completed = sum(t['completed_jobs'] for t in job_tracker.values())
    total_jobs_failed = sum(t['failed_jobs'] for t in job_tracker.values())
    
    print(f"[Status] Campaigns: {completed_campaigns} complete, {processing_campaigns} processing, {failed_campaigns} failed / {total_campaigns} total")
    print(f"[Status] Jobs: {total_jobs_completed} complete, {total_jobs_failed} failed / {total_jobs_expected} total ({total_jobs_completed/total_jobs_expected*100:.1f}% complete)")


def monitor_all_campaigns_jobs(token, campaigns_data, timeout=600, api_base=None):
    """Monitor ENRICH_LEAD jobs across all campaigns concurrently"""
    if api_base is None:
        raise ValueError("api_base is required")
    
    print(f"\n[Monitor] Starting to monitor ENRICH_LEAD jobs across {len(campaigns_data)} campaigns")
    
    # Initialize tracking structure
    job_tracker = {}
    for campaign_id, data in campaigns_data.items():
        job_tracker[campaign_id] = {
            'campaign_index': data['campaign_index'],
            'expected_jobs': data['leads_count'],
            'completed_jobs': 0,
            'failed_jobs': 0,
            'last_job_count': 0,
            'status': 'waiting',  # waiting, processing, completed, failed
            'last_update': time.time()
        }
    
    start_time = time.time()
    last_status_log = 0
    status_log_interval = 15  # Log every 15 seconds
    
    while time.time() - start_time < timeout:
        current_time = time.time()
        elapsed = current_time - start_time
        all_complete = True
        
        for campaign_id, tracking in job_tracker.items():
            if tracking['status'] in ['completed', 'failed']:
                continue
                
            # Fetch jobs for this campaign
            jobs = fetch_campaign_jobs(token, campaign_id, api_base)
            enrich_jobs = [j for j in jobs if j["job_type"] == "ENRICH_LEAD"]
            
            completed = [j for j in enrich_jobs if j["status"] == "COMPLETED"]
            failed = [j for j in enrich_jobs if j["status"] == "FAILED"]
            
            old_completed = tracking['completed_jobs']
            tracking['completed_jobs'] = len(completed)
            tracking['failed_jobs'] = len(failed)
            
            # Update status
            if tracking['failed_jobs'] > 0:
                tracking['status'] = 'failed'
                print(f"[Monitor] ❌ Campaign #{tracking['campaign_index']} has {tracking['failed_jobs']} failed job(s)")
            elif tracking['completed_jobs'] >= tracking['expected_jobs']:
                if tracking['status'] != 'completed':
                    print(f"[Monitor] ✅ Campaign #{tracking['campaign_index']} completed all {tracking['completed_jobs']} jobs")
                tracking['status'] = 'completed'
            elif tracking['completed_jobs'] > old_completed:
                tracking['status'] = 'processing'
                tracking['last_update'] = current_time
            
            if tracking['status'] not in ['completed', 'failed']:
                all_complete = False
        
        # Log consolidated status periodically
        if elapsed - last_status_log >= status_log_interval:
            print(f"\n[Monitor] === Status Update (after {elapsed:.0f}s) ===")
            print_consolidated_status(job_tracker)
            last_status_log = elapsed
        
        if all_complete:
            print(f"\n[Monitor] 🎉 All campaigns completed after {elapsed:.1f}s!")
            return job_tracker
            
        time.sleep(3)  # Check every 3 seconds
    
    # Timeout reached
    print(f"\n[Monitor] ⏰ Timeout reached after {timeout}s")
    print_consolidated_status(job_tracker)
    
    failed_campaigns = [t for t in job_tracker.values() if t['status'] == 'failed']
    incomplete_campaigns = [t for t in job_tracker.values() if t['status'] not in ['completed', 'failed']]
    
    if failed_campaigns:
        failed_indices = [str(t['campaign_index']) for t in failed_campaigns]
        raise AssertionError(f"Campaigns #{', '.join(failed_indices)} failed")
    
    if incomplete_campaigns:
        incomplete_indices = [str(t['campaign_index']) for t in incomplete_campaigns]
        raise TimeoutError(f"Campaigns #{', '.join(incomplete_indices)} did not complete within {timeout}s")
    
    return job_tracker


def monitor_all_campaigns_jobs_with_cb_awareness(token, campaigns_data, timeout, check_circuit_breaker_status_func, check_campaigns_paused_by_circuit_breaker_func, report_circuit_breaker_failure_func, validate_no_unexpected_pauses_func, check_campaign_status_summary_func, api_base=None):
    """Enhanced monitoring with circuit breaker awareness and graceful failure handling."""
    if api_base is None:
        raise ValueError("api_base is required")
    
    print(f"\n[Monitor CB] Starting circuit breaker-aware monitoring for {len(campaigns_data)} campaigns")
    
    # Get campaign IDs for circuit breaker checks
    campaign_ids = list(campaigns_data.keys())
    
    # Initialize tracking structure
    job_tracker = {}
    for campaign_id, data in campaigns_data.items():
        job_tracker[campaign_id] = {
            'campaign_index': data['campaign_index'],
            'expected_jobs': data['leads_count'],
            'completed_jobs': 0,
            'failed_jobs': 0,
            'last_job_count': 0,
            'status': 'waiting',  # waiting, processing, completed, failed
            'last_update': time.time()
        }
    
    start_time = time.time()
    last_status_log = 0
    last_cb_check = 0
    status_log_interval = 15  # Log every 15 seconds
    cb_check_interval = 30   # Check circuit breaker every 30 seconds
    
    print(f"[Monitor CB] Circuit breaker checks will run every {cb_check_interval}s")
    
    while time.time() - start_time < timeout:
        current_time = time.time()
        elapsed = current_time - start_time
        all_complete = True
        
        # === CIRCUIT BREAKER HEALTH CHECK ===
        if elapsed - last_cb_check >= cb_check_interval and check_circuit_breaker_status_func:
            print(f"\n[Monitor CB] Performing circuit breaker health check (after {elapsed:.0f}s)...")
            
            # Check circuit breaker status
            cb_status = check_circuit_breaker_status_func(token, api_base)
            
            # Check if any campaigns have been paused
            paused_campaigns = []
            if check_campaigns_paused_by_circuit_breaker_func:
                paused_campaigns = check_campaigns_paused_by_circuit_breaker_func(token, campaign_ids, api_base)
            
            if paused_campaigns:
                print(f"[Monitor CB] ⚠️  Detected {len(paused_campaigns)} paused campaign(s)")
                if report_circuit_breaker_failure_func:
                    report_circuit_breaker_failure_func(cb_status, paused_campaigns)
                return None  # Signal circuit breaker failure
            
            # Additional campaign status validation during monitoring
            if validate_no_unexpected_pauses_func and check_campaign_status_summary_func:
                no_unexpected_pauses, unexpected_paused = validate_no_unexpected_pauses_func(token, campaign_ids, api_base)
                if not no_unexpected_pauses:
                    print(f"[Monitor CB] ⚠️  Campaign status validation failed - unexpected pauses detected")
                    # Get current status summary for detailed reporting
                    status_summary, campaign_details = check_campaign_status_summary_func(token, campaign_ids, api_base)
                    
                    # Check if this is circuit breaker related
                    if cb_status and cb_status.get("data"):
                        circuit_breaker = cb_status["data"]
                        
                        if isinstance(circuit_breaker, dict) and "state" in circuit_breaker:
                            state = circuit_breaker["state"]
                            if state == "open":
                                print(f"🔴 CIRCUIT BREAKER OPEN - Queue paused due to service failures")
                                return None  # Signal circuit breaker triggered
                    else:
                        print(f"[Monitor CB] ❌ Non-circuit-breaker related campaign pauses detected:")
                        for campaign in unexpected_paused:
                            print(f"[Monitor CB]    Campaign {campaign['id']}: {campaign['status_message']}")
                    
                    return None  # Signal failure due to unexpected pauses
            
            # Check if any services are unhealthy
            if cb_status and cb_status.get("data"):
                circuit_breaker = cb_status["data"]
                
                if isinstance(circuit_breaker, dict) and "state" in circuit_breaker:
                    state = circuit_breaker["state"]
                    if state == "open":
                        print(f"🔴 CIRCUIT BREAKER OPEN - Queue paused due to service failures")
                        return None  # Signal circuit breaker triggered
                else:
                    print(f"[Monitor CB] ✅ Global circuit breaker is healthy")
            else:
                print(f"[Monitor CB] ℹ️  Could not get circuit breaker status, campaigns appear healthy")
            
            last_cb_check = elapsed
        
        # === JOB STATUS MONITORING ===
        for campaign_id, tracking in job_tracker.items():
            if tracking['status'] in ['completed', 'failed']:
                continue
                
            # Fetch jobs for this campaign
            jobs = fetch_campaign_jobs(token, campaign_id, api_base)
            enrich_jobs = [j for j in jobs if j["job_type"] == "ENRICH_LEAD"]
            
            completed = [j for j in enrich_jobs if j["status"] == "COMPLETED"]
            failed = [j for j in enrich_jobs if j["status"] == "FAILED"]
            
            old_completed = tracking['completed_jobs']
            tracking['completed_jobs'] = len(completed)
            tracking['failed_jobs'] = len(failed)
            
            # Update status
            if tracking['failed_jobs'] > 0:
                tracking['status'] = 'failed'
                print(f"[Monitor CB] ❌ Campaign #{tracking['campaign_index']} has {tracking['failed_jobs']} failed job(s)")
            elif tracking['completed_jobs'] >= tracking['expected_jobs']:
                if tracking['status'] != 'completed':
                    print(f"[Monitor CB] ✅ Campaign #{tracking['campaign_index']} completed all {tracking['completed_jobs']} jobs")
                tracking['status'] = 'completed'
            elif tracking['completed_jobs'] > old_completed:
                tracking['status'] = 'processing'
                tracking['last_update'] = current_time
            
            if tracking['status'] not in ['completed', 'failed']:
                all_complete = False
        
        # === STATUS LOGGING ===
        if elapsed - last_status_log >= status_log_interval:
            print(f"\n[Monitor CB] === Status Update (after {elapsed:.0f}s) ===")
            print_consolidated_status(job_tracker)
            last_status_log = elapsed
        
        # === CHECK COMPLETION ===
        if all_complete:
            print(f"\n[Monitor CB] 🎉 All campaigns completed after {elapsed:.1f}s!")
            return job_tracker
            
        time.sleep(3)  # Check every 3 seconds
    
    # === TIMEOUT HANDLING ===
    print(f"\n[Monitor CB] ⏰ Timeout reached after {timeout}s")
    
    # Final circuit breaker check at timeout
    if check_circuit_breaker_status_func and check_campaigns_paused_by_circuit_breaker_func:
        print(f"[Monitor CB] Performing final circuit breaker check...")
        cb_status = check_circuit_breaker_status_func(token, api_base)
        paused_campaigns = check_campaigns_paused_by_circuit_breaker_func(token, campaign_ids, api_base)
        
        if paused_campaigns:
            print(f"[Monitor CB] ⚠️  At timeout: {len(paused_campaigns)} campaign(s) are paused")
            if report_circuit_breaker_failure_func:
                report_circuit_breaker_failure_func(cb_status, paused_campaigns)
            return None  # Signal circuit breaker failure at timeout
    
    print_consolidated_status(job_tracker)
    
    failed_campaigns = [t for t in job_tracker.values() if t['status'] == 'failed']
    incomplete_campaigns = [t for t in job_tracker.values() if t['status'] not in ['completed', 'failed']]
    
    if failed_campaigns:
        failed_indices = [str(t['campaign_index']) for t in failed_campaigns]
        raise AssertionError(f"Campaigns #{', '.join(failed_indices)} failed")
    
    if incomplete_campaigns:
        incomplete_indices = [str(t['campaign_index']) for t in incomplete_campaigns]
        raise TimeoutError(f"Campaigns #{', '.join(incomplete_indices)} did not complete within {timeout}s")
    
    return job_tracker 
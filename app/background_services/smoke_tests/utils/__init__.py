"""
Utility modules for smoke tests.

This package contains refactored utility functions from the concurrent campaigns test
to improve maintainability and code organization.
"""

# Import all utility functions for easy access
from .auth_utils import (
    random_email,
    random_password,
    signup_and_login,
    create_organization
)

from .campaign_utils import (
    create_campaign,
    start_campaign,
    create_campaigns_sequentially,
    get_all_leads
)

from .job_utils import (
    fetch_campaign_jobs,
    wait_for_jobs,
    monitor_all_campaigns_jobs,
    monitor_all_campaigns_jobs_with_cb_awareness,
    print_consolidated_status
)

from .circuit_breaker_utils import (
    check_circuit_breaker_status,
    check_campaigns_paused_by_circuit_breaker,
    report_circuit_breaker_failure
)

from .validation_utils import (
    validate_enrichment,
    assert_lead_enrichment,
    assert_lead_enrichment_simple,
    validate_campaign_data,
    validate_no_duplicate_emails,
    validate_no_unexpected_pauses
)

from .reporting_utils import (
    check_campaign_status_summary,
    report_campaign_status_summary,
    analyze_process_results,
    analyze_results
)

from .database_utils import (
    cleanup_test_data
)

__all__ = [
    # Auth utilities
    'random_email',
    'random_password', 
    'signup_and_login',
    'create_organization',
    
    # Campaign utilities
    'create_campaign',
    'start_campaign',
    'create_campaigns_sequentially',
    'get_all_leads',
    
    # Job utilities
    'fetch_campaign_jobs',
    'wait_for_jobs',
    'monitor_all_campaigns_jobs',
    'monitor_all_campaigns_jobs_with_cb_awareness',
    'print_consolidated_status',
    
    # Circuit breaker utilities
    'check_circuit_breaker_status',
    'check_campaigns_paused_by_circuit_breaker',
    'report_circuit_breaker_failure',
    
    # Validation utilities
    'validate_enrichment',
    'assert_lead_enrichment',
    'assert_lead_enrichment_simple',
    'validate_campaign_data',
    'validate_no_duplicate_emails',
    'validate_no_unexpected_pauses',
    
    # Reporting utilities
    'check_campaign_status_summary',
    'report_campaign_status_summary',
    'analyze_process_results',
    'analyze_results',
    
    # Database utilities
    'cleanup_test_data'
] 
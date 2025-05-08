"""Error message constants for the application.

This module contains all error message strings used throughout the application.
These constants can be imported and used in both application code and tests
to ensure consistent error messages and enable reliable error checking.
"""

# Campaign-related error messages
CAMPAIGN_ERRORS = {
    'CAMPAIGN_NOT_FOUND': 'Campaign {campaign_id} not found',
    'INVALID_STATUS': 'Invalid status: {status}',
    'INVALID_STATUS_TRANSITION': 'Invalid status transition from {current_status} to {new_status}',
    'INVALID_COUNT': 'Count must be a positive integer',
    'INVALID_SEARCH_URL': 'Invalid Apollo.io search URL',
    'MALICIOUS_URL': 'Invalid Apollo.io search URL',
    'NO_COMPLETED_JOBS': 'No completed job found for this campaign',
    'INVALID_TRANSITION': 'Invalid status transition from {current_status} to {new_status}',
    'INVALID_PARAMETERS': 'Invalid parameters: {details}'
}

# Job-related error messages
JOB_ERRORS = {
    'RESULT_CORRUPTED': 'Job result must be a dictionary',
    'RESULT_NOT_DICT': 'Job result must be a dictionary',
    'MISSING_REQUIRED_FIELD': 'Job result data is corrupted: missing required field {field}',
    'INVALID_FIELD_TYPE': 'Job result data is corrupted: {field} must be a {expected}',
    'INVALID_JOB_TYPE': 'Invalid job type: {job_type}',
    'JOB_NOT_FOUND': 'Job {job_id} not found',
    'JOB_ALREADY_STARTED': 'Job {job_id} has already been started',
    'JOB_ALREADY_COMPLETED': 'Job {job_id} has already been completed',
    'JOB_ALREADY_FAILED': 'Job {job_id} has already failed',
    'INVALID_STATUS': 'Invalid job status: {status}',
    'INVALID_TRANSITION': 'Invalid job status transition from {current_status} to {new_status}',
    'NO_COMPLETED_JOBS': 'No completed job found for this campaign'
}

# Lead-related error messages
LEAD_ERRORS = {
    'LEAD_NOT_FOUND': 'Lead not found',
    'EMAIL_REQUIRED': 'Email is required',
    'NAME_REQUIRED': 'Name is required',
    'COMPANY_REQUIRED': 'Company is required',
    'EMAIL_EXISTS': 'Lead with this email already exists'
}

# Organization-related error messages
ORG_ERRORS = {
    'ORG_NOT_FOUND': 'Organization not found',
    'NAME_REQUIRED': 'Name is required',
    'NAME_TOO_SHORT': 'Name must be at least 3 characters long',
    'DESCRIPTION_REQUIRED': 'Description is required'
}

# Authentication-related error messages
AUTH_ERRORS = {
    'INVALID_CREDENTIALS': 'Invalid email or password',
    'ACCOUNT_LOCKED': 'Account is locked due to too many failed attempts',
    'EMAIL_EXISTS': 'Email already registered',
    'PASSWORD_MISMATCH': 'Passwords do not match',
    'INVALID_EMAIL': 'Invalid email format',
    'PASSWORD_REQUIRED': 'Password is required',
    'EMAIL_REQUIRED': 'Email is required'
}

# Validation-related error messages
VALIDATION_ERRORS = {
    'ALL_FIELDS_REQUIRED': 'All fields are required',
    'INVALID_EMAIL_FORMAT': 'Invalid email format',
    'EMAIL_TOO_LONG': 'Email length exceeds maximum allowed'
}

# Database-related error messages
DB_ERRORS = {
    'TRANSACTION_ERROR': 'Database transaction error',
    'CONNECTION_ERROR': 'Database connection error',
    'QUERY_ERROR': 'Database query error'
}

# API-related error messages
API_ERRORS = {
    'INVALID_REQUEST': 'Invalid request',
    'UNAUTHORIZED': 'Unauthorized access',
    'FORBIDDEN': 'Forbidden access',
    'NOT_FOUND': 'Resource not found',
    'SERVER_ERROR': 'Internal server error'
}

# Export all error message dictionaries
__all__ = [
    'CAMPAIGN_ERRORS',
    'JOB_ERRORS',
    'LEAD_ERRORS',
    'ORG_ERRORS',
    'AUTH_ERRORS',
    'VALIDATION_ERRORS',
    'DB_ERRORS',
    'API_ERRORS'
] 
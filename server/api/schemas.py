from marshmallow import Schema, fields, validate, ValidationError
from datetime import datetime
from server.models.job_status import JobStatus

class ErrorSchema(Schema):
    """Schema for error responses."""
    code = fields.Int(required=True)
    name = fields.Str(required=True)
    message = fields.Str(required=True)

class ErrorResponseSchema(Schema):
    """Schema for error responses."""
    status = fields.Str(required=True)
    error = fields.Dict(keys=fields.Str(), values=fields.Str(), required=True)

class SuccessResponseSchema(Schema):
    """Schema for success responses."""
    status = fields.Str(required=True)
    data = fields.Dict(keys=fields.Str(), values=fields.Raw(), required=True)

class JobSchema(Schema):
    """Schema for job data."""
    id = fields.Str(required=True)
    campaign_id = fields.Str(required=True)
    job_type = fields.Str(required=True)
    status = fields.Str(required=True, validate=validate.OneOf([status.value for status in JobStatus]))
    result = fields.Dict(allow_none=True)
    error = fields.Str(allow_none=True)
    created_at = fields.DateTime(required=True)
    started_at = fields.DateTime(allow_none=True)
    ended_at = fields.DateTime(allow_none=True)
    execution_time = fields.Float(allow_none=True)
    parameters = fields.Dict(allow_none=True)
    error_message = fields.Str(allow_none=True)
    completed_at = fields.DateTime(allow_none=True)
    updated_at = fields.DateTime(allow_none=True)
    error_details = fields.Dict(allow_none=True)
    delay_reason = fields.Str(allow_none=True)

class CampaignSchema(Schema):
    """Schema for campaign data."""
    id = fields.Str(required=True)
    name = fields.Str(required=True)
    description = fields.Str(allow_none=True)
    status = fields.Str(required=True)
    status_message = fields.Str(allow_none=True)
    status_error = fields.Str(allow_none=True)
    created_at = fields.DateTime(required=True)
    updated_at = fields.DateTime(required=True)
    organization_id = fields.Str(allow_none=True)
    fileName = fields.Str(required=True)
    totalRecords = fields.Int(required=True)
    url = fields.Str(required=True)
    instantly_campaign_id = fields.Str(allow_none=True)
    jobs = fields.List(fields.Nested(JobSchema), required=False)

class CampaignCreateSchema(Schema):
    """Schema for campaign creation request."""
    name = fields.Str(required=True, validate=validate.Length(min=1))
    description = fields.Str(allow_none=True)
    fileName = fields.Str(required=True)
    totalRecords = fields.Int(required=True)
    url = fields.Str(required=True)
    organization_id = fields.Str(required=False, allow_none=True)

class CampaignStartSchema(Schema):
    """Schema for campaign start request."""
    # No fields required, as start is now a trigger only
    pass

class LeadSchema(Schema):
    """Schema for lead data."""
    id = fields.Str(required=True)
    campaign_id = fields.Str(required=True)
    first_name = fields.Str(required=True)
    last_name = fields.Str(required=True)
    email = fields.Email(required=True)
    phone = fields.Str(allow_none=True)
    company = fields.Str(allow_none=True)
    title = fields.Str(allow_none=True)
    linkedin_url = fields.Str(allow_none=True)
    source_url = fields.Str(allow_none=True)
    raw_data = fields.Dict(allow_none=True)
    created_at = fields.DateTime(required=True)
    updated_at = fields.DateTime(required=True)
    enrichment_results = fields.Dict(allow_none=True)
    email_copy_gen_results = fields.Raw(allow_none=True)
    instantly_lead_record = fields.Dict(allow_none=True)

class LeadCreateSchema(Schema):
    """Schema for lead creation requests."""
    campaign_id = fields.Str(required=True)
    first_name = fields.Str(required=True)
    last_name = fields.Str(required=True)
    email = fields.Email(required=True)
    phone = fields.Str(allow_none=True)
    company = fields.Str(allow_none=True)
    title = fields.Str(allow_none=True)
    linkedin_url = fields.Str(allow_none=True)
    source_url = fields.Str(allow_none=True)
    raw_data = fields.Dict(allow_none=True)

class LeadListSchema(Schema):
    """Schema for lead list responses."""
    status = fields.Str(required=True)
    data = fields.Dict(required=True, keys=fields.Str(), values=fields.List(fields.Nested(LeadSchema)))

class AuthSchema(Schema):
    """Schema for authentication requests."""
    email = fields.Email(required=True)
    password = fields.Str(required=True, validate=validate.Length(min=8))
    confirm_password = fields.Str(required=True, validate=validate.Length(min=8))

class LoginSchema(Schema):
    """Schema for login requests."""
    email = fields.Email(required=True)
    password = fields.Str(required=True)

class TokenSchema(Schema):
    """Schema for token responses."""
    token = fields.Str(required=True)
    expires_at = fields.DateTime(required=True)

class UserSchema(Schema):
    """Schema for user data."""
    id = fields.Str(required=True)
    email = fields.Email(required=True)
    created_at = fields.DateTime(required=True)
    updated_at = fields.DateTime(required=True)

class CampaignLeadStatsSchema(Schema):
    total_leads_fetched = fields.Int(required=True)
    leads_with_email = fields.Int(required=True)
    leads_with_verified_email = fields.Int(required=True)
    leads_with_enrichment = fields.Int(required=True)
    leads_with_email_copy = fields.Int(required=True)
    leads_with_instantly_record = fields.Int(required=True)
    error_message = fields.Str(allow_none=True) 
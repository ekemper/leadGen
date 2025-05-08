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

class CampaignCreateSchema(Schema):
    """Schema for campaign creation request."""
    name = fields.Str(required=True, validate=validate.Length(min=1))
    description = fields.Str(allow_none=True)

class CampaignStartSchema(Schema):
    """Schema for campaign start request."""
    searchUrl = fields.Str(required=True)
    count = fields.Int(required=True, validate=validate.Range(min=1, max=100))
    excludeGuessedEmails = fields.Bool(required=True)
    excludeNoEmails = fields.Bool(required=True)
    getEmails = fields.Bool(required=True)

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
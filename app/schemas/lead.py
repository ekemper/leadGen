from datetime import datetime
from typing import Optional, Any, Dict
from pydantic import BaseModel, Field

class LeadBase(BaseModel):
    campaign_id: str = Field(..., max_length=36, description="Campaign ID")
    first_name: Optional[str] = Field(None, max_length=100, description="First name")
    last_name: Optional[str] = Field(None, max_length=100, description="Last name")
    email: Optional[str] = Field(None, max_length=255, description="Email address")
    phone: Optional[str] = Field(None, max_length=50, description="Phone number")
    company: Optional[str] = Field(None, max_length=255, description="Company name")
    title: Optional[str] = Field(None, max_length=255, description="Job title")
    linkedin_url: Optional[str] = Field(None, max_length=255, description="LinkedIn URL")
    source_url: Optional[str] = Field(None, max_length=255, description="Source URL")
    raw_data: Optional[Dict[str, Any]] = Field(None, description="Raw data as JSON")
    email_verification: Optional[Dict[str, Any]] = Field(None, description="Email verification JSON")
    enrichment_results: Optional[Dict[str, Any]] = Field(None, description="Enrichment results JSON")
    enrichment_job_id: Optional[str] = Field(None, max_length=36, description="Enrichment job ID")
    email_copy_gen_results: Optional[Dict[str, Any]] = Field(None, description="Email copy gen results JSON")
    instantly_lead_record: Optional[Dict[str, Any]] = Field(None, description="Instantly lead record JSON")

class LeadCreate(LeadBase):
    pass

class LeadUpdate(BaseModel):
    first_name: Optional[str] = Field(None, max_length=100, description="First name")
    last_name: Optional[str] = Field(None, max_length=100, description="Last name")
    email: Optional[str] = Field(None, max_length=255, description="Email address")
    phone: Optional[str] = Field(None, max_length=50, description="Phone number")
    company: Optional[str] = Field(None, max_length=255, description="Company name")
    title: Optional[str] = Field(None, max_length=255, description="Job title")
    linkedin_url: Optional[str] = Field(None, max_length=255, description="LinkedIn URL")
    source_url: Optional[str] = Field(None, max_length=255, description="Source URL")
    raw_data: Optional[Dict[str, Any]] = Field(None, description="Raw data as JSON")
    email_verification: Optional[Dict[str, Any]] = Field(None, description="Email verification JSON")
    enrichment_results: Optional[Dict[str, Any]] = Field(None, description="Enrichment results JSON")
    enrichment_job_id: Optional[str] = Field(None, max_length=36, description="Enrichment job ID")
    email_copy_gen_results: Optional[Dict[str, Any]] = Field(None, description="Email copy gen results JSON")
    instantly_lead_record: Optional[Dict[str, Any]] = Field(None, description="Instantly lead record JSON")

class LeadResponse(LeadBase):
    id: str = Field(..., description="Lead ID")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    class Config:
        from_attributes = True 
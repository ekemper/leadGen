"""
Database verification helpers for comprehensive campaign API testing.

These helpers provide direct database access for verifying state changes
and ensuring API operations have the expected database effects.
"""

import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Union
from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.campaign import Campaign
from app.models.campaign_status import CampaignStatus
from app.models.job import Job, JobStatus, JobType
from app.core.database import Base
from app.models.lead import Lead


class DatabaseHelpers:
    """Database verification helpers for testing."""
    
    def __init__(self, db_session: Session):
        """Initialize with database session."""
        self.db_session = db_session
    
    def verify_campaign_in_db(self, campaign_id: str, expected_data: Dict[str, Any] = None) -> Campaign:
        """
        Verify campaign exists in database with expected values.
        
        Args:
            campaign_id: Campaign ID to verify
            expected_data: Dictionary of field->value pairs to verify
            
        Returns:
            Campaign object if found
            
        Raises:
            AssertionError: If campaign not found or values don't match
        """
        campaign = self.db_session.query(Campaign).filter(Campaign.id == campaign_id).first()
        assert campaign is not None, f"Campaign {campaign_id} not found in database"
        
        if expected_data:
            for field, expected_value in expected_data.items():
                actual_value = getattr(campaign, field, None)
                
                # Handle enum values
                if isinstance(actual_value, CampaignStatus):
                    actual_value = actual_value.value
                elif isinstance(actual_value, datetime):
                    # For datetime comparisons, convert to string if expected is string
                    if isinstance(expected_value, str):
                        actual_value = actual_value.isoformat()
                
                assert actual_value == expected_value, (
                    f"Campaign {campaign_id}: Expected {field}={expected_value}, "
                    f"got {actual_value}"
                )
        
        return campaign
    
    def verify_campaign_not_in_db(self, campaign_id: str) -> None:
        """
        Verify campaign was not created or was deleted.
        
        Args:
            campaign_id: Campaign ID that should not exist
            
        Raises:
            AssertionError: If campaign exists in database
        """
        campaign = self.db_session.query(Campaign).filter(Campaign.id == campaign_id).first()
        assert campaign is None, f"Campaign {campaign_id} should not exist in database but was found"
    
    def count_campaigns_in_db(self) -> int:
        """
        Count total campaigns in database.
        
        Returns:
            Number of campaigns in database
        """
        return self.db_session.query(Campaign).count()
    
    def verify_job_created_for_campaign(self, campaign_id: str, job_type: Union[JobType, str]) -> Job:
        """
        Verify background job was created for campaign.
        
        Args:
            campaign_id: Campaign ID to check jobs for
            job_type: Expected job type (JobType enum or string)
            
        Returns:
            Job object if found
            
        Raises:
            AssertionError: If job not found
        """
        # Convert string to JobType enum if needed
        if isinstance(job_type, str):
            job_type = JobType(job_type)
        
        job = (self.db_session.query(Job)
               .filter(Job.campaign_id == campaign_id)
               .filter(Job.job_type == job_type)
               .first())
        
        assert job is not None, (
            f"No job of type {job_type.value} found for campaign {campaign_id}"
        )
        
        return job
    
    def get_campaign_jobs_from_db(self, campaign_id: str) -> List[Job]:
        """
        Get all jobs for a campaign.
        
        Args:
            campaign_id: Campaign ID to get jobs for
            
        Returns:
            List of Job objects for the campaign
        """
        return (self.db_session.query(Job)
                .filter(Job.campaign_id == campaign_id)
                .order_by(Job.created_at)
                .all())
    
    def verify_campaign_status_in_db(self, campaign_id: str, expected_status: Union[CampaignStatus, str]) -> None:
        """
        Verify campaign status in database.
        
        Args:
            campaign_id: Campaign ID to check
            expected_status: Expected status (CampaignStatus enum or string)
            
        Raises:
            AssertionError: If status doesn't match
        """
        campaign = self.db_session.query(Campaign).filter(Campaign.id == campaign_id).first()
        assert campaign is not None, f"Campaign {campaign_id} not found in database"
        
        # Convert string to CampaignStatus enum if needed
        if isinstance(expected_status, str):
            expected_status = CampaignStatus(expected_status)
        
        assert campaign.status == expected_status, (
            f"Campaign {campaign_id}: Expected status {expected_status.value}, "
            f"got {campaign.status.value}"
        )
    
    def cleanup_test_data(self) -> Dict[str, int]:
        """
        Clean all test data from database.
        
        Returns:
            Dictionary with counts of deleted records
        """
        # Delete in correct order to avoid foreign key constraint violations
        # Jobs first, then leads, then campaigns
        jobs_deleted = self.db_session.query(Job).delete()
        leads_deleted = self.db_session.query(Lead).delete()
        campaigns_deleted = self.db_session.query(Campaign).delete()
        
        self.db_session.commit()
        
        return {
            "jobs_deleted": jobs_deleted,
            "leads_deleted": leads_deleted,
            "campaigns_deleted": campaigns_deleted
        }
    
    def create_test_campaign_in_db(self, data: Dict[str, Any]) -> Campaign:
        """
        Create campaign directly in database for testing.
        
        Args:
            data: Campaign data dictionary (must include organization_id)
            
        Returns:
            Created Campaign object
        """
        # organization_id is now required - must be provided in data
        if "organization_id" not in data:
            raise ValueError("organization_id is required for campaign creation")
            
        # Set defaults for required fields
        campaign_data = {
            "id": str(uuid.uuid4()),
            "name": "Test Campaign",
            "description": "Test Description",
            "status": CampaignStatus.CREATED,
            "fileName": "test.csv",
            "totalRecords": 100,
            "url": "https://test.com",
            "status_message": None,
            "status_error": None,
            "instantly_campaign_id": None,
            **data  # Override with provided data
        }
        
        campaign = Campaign(**campaign_data)
        self.db_session.add(campaign)
        self.db_session.commit()
        self.db_session.refresh(campaign)
        
        return campaign
    
    def create_test_job_in_db(self, campaign_id: str, job_data: Dict[str, Any] = None) -> Job:
        """
        Create job directly in database for testing.
        
        Args:
            campaign_id: Campaign ID to associate job with
            job_data: Optional job data overrides
            
        Returns:
            Created Job object
        """
        job_defaults = {
            "name": "Test Job",
            "description": "Test job description",
            "job_type": JobType.FETCH_LEADS,
            "status": JobStatus.PENDING,
            "campaign_id": campaign_id,
            "task_id": f"test-task-{uuid.uuid4()}",
            **(job_data or {})
        }
        
        job = Job(**job_defaults)
        self.db_session.add(job)
        self.db_session.commit()
        self.db_session.refresh(job)
        
        return job
    
    def verify_job_status_in_db(self, job_id: int, expected_status: Union[JobStatus, str]) -> Job:
        """
        Verify job status in database.
        
        Args:
            job_id: Job ID to check
            expected_status: Expected status (JobStatus enum or string)
            
        Returns:
            Job object
            
        Raises:
            AssertionError: If job not found or status doesn't match
        """
        job = self.db_session.query(Job).filter(Job.id == job_id).first()
        assert job is not None, f"Job {job_id} not found in database"
        
        # Convert string to JobStatus enum if needed
        if isinstance(expected_status, str):
            expected_status = JobStatus(expected_status)
        
        assert job.status == expected_status, (
            f"Job {job_id}: Expected status {expected_status.value}, "
            f"got {job.status.value}"
        )
        
        return job
    
    def verify_campaign_timestamps(self, campaign_id: str, check_updated: bool = True) -> Campaign:
        """
        Verify campaign timestamps are properly set.
        
        Args:
            campaign_id: Campaign ID to check
            check_updated: Whether to verify updated_at is recent
            
        Returns:
            Campaign object
            
        Raises:
            AssertionError: If timestamps are invalid
        """
        campaign = self.db_session.query(Campaign).filter(Campaign.id == campaign_id).first()
        assert campaign is not None, f"Campaign {campaign_id} not found in database"
        
        # Verify created_at exists
        assert campaign.created_at is not None, f"Campaign {campaign_id} missing created_at timestamp"
        
        # Verify updated_at exists
        assert campaign.updated_at is not None, f"Campaign {campaign_id} missing updated_at timestamp"
        
        # Verify updated_at >= created_at
        assert campaign.updated_at >= campaign.created_at, (
            f"Campaign {campaign_id}: updated_at ({campaign.updated_at}) "
            f"is before created_at ({campaign.created_at})"
        )
        
        if check_updated:
            # Verify updated_at is recent (within last 10 seconds)
            time_diff = datetime.utcnow().replace(tzinfo=timezone.utc) - campaign.updated_at.replace(tzinfo=timezone.utc)
            assert time_diff.total_seconds() < 10, (
                f"Campaign {campaign_id}: updated_at timestamp is not recent "
                f"(diff: {time_diff.total_seconds()} seconds)"
            )
        
        return campaign
    
    def get_campaign_by_field(self, field: str, value: Any) -> Optional[Campaign]:
        """
        Get campaign by any field value.
        
        Args:
            field: Field name to search by
            value: Value to search for
            
        Returns:
            Campaign object if found, None otherwise
        """
        return (self.db_session.query(Campaign)
                .filter(getattr(Campaign, field) == value)
                .first())
    
    def verify_no_orphaned_jobs(self) -> None:
        """
        Verify there are no jobs without valid campaign references.
        
        Raises:
            AssertionError: If orphaned jobs are found
        """
        orphaned_jobs = (self.db_session.query(Job)
                        .filter(Job.campaign_id.isnot(None))
                        .filter(~Job.campaign_id.in_(
                            self.db_session.query(Campaign.id)
                        ))
                        .all())
        
        assert len(orphaned_jobs) == 0, (
            f"Found {len(orphaned_jobs)} orphaned jobs with invalid campaign_id references"
        )
    
    def verify_lead_in_db(self, lead_id: str, expected_data: Dict[str, Any] = None) -> Lead:
        """
        Verify lead exists in database with expected values.
        Args:
            lead_id: Lead ID to verify
            expected_data: Dictionary of field->value pairs to verify
        Returns:
            Lead object if found
        Raises:
            AssertionError: If lead not found or values don't match
        """
        lead = self.db_session.query(Lead).filter(Lead.id == lead_id).first()
        assert lead is not None, f"Lead {lead_id} not found in database"
        if expected_data:
            for field, expected_value in expected_data.items():
                actual_value = getattr(lead, field, None)
                if hasattr(actual_value, 'isoformat') and isinstance(expected_value, str):
                    actual_value = actual_value.isoformat()
                assert actual_value == expected_value, (
                    f"Lead {lead_id}: Expected {field}={expected_value}, got {actual_value}"
                )
        return lead

    def verify_lead_not_in_db(self, lead_id: str) -> None:
        """
        Verify lead was not created or was deleted.
        Args:
            lead_id: Lead ID that should not exist
        Raises:
            AssertionError: If lead exists in database
        """
        lead = self.db_session.query(Lead).filter(Lead.id == lead_id).first()
        assert lead is None, f"Lead {lead_id} should not exist in database but was found"

    def count_leads_in_db(self) -> int:
        """
        Count total leads in database.
        Returns:
            Number of leads in database
        """
        return self.db_session.query(Lead).count()

    def cleanup_lead_test_data(self) -> Dict[str, int]:
        """
        Clean all test leads from database.
        Returns:
            Dictionary with counts of deleted records
        """
        leads_deleted = self.db_session.query(Lead).delete()
        self.db_session.commit()
        return {"leads_deleted": leads_deleted}

    def create_test_lead_in_db(self, data: Dict[str, Any]) -> Lead:
        """
        Create lead directly in database for testing.
        Args:
            data: Lead data dictionary (must include campaign_id)
        Returns:
            Created Lead object
        """
        if "campaign_id" not in data:
            raise ValueError("campaign_id is required for lead creation")
        lead_data = {
            "id": str(uuid.uuid4()),
            "first_name": "Test",
            "last_name": "Lead",
            "email": "testlead@example.com",
            "phone": "1234567890",
            "company": "TestCo",
            "title": "Tester",
            "linkedin_url": None,
            "source_url": None,
            "raw_data": None,
            "email_verification": None,
            "enrichment_results": None,
            "enrichment_job_id": None,
            "email_copy_gen_results": None,
            "instantly_lead_record": None,
            **data
        }
        lead = Lead(**lead_data)
        self.db_session.add(lead)
        self.db_session.commit()
        self.db_session.refresh(lead)
        return lead


# Convenience functions for backward compatibility and ease of use
def verify_campaign_in_db(db_session: Session, campaign_id: str, expected_data: Dict[str, Any] = None) -> Campaign:
    """Convenience function for campaign verification."""
    helper = DatabaseHelpers(db_session)
    return helper.verify_campaign_in_db(campaign_id, expected_data)


def verify_campaign_not_in_db(db_session: Session, campaign_id: str) -> None:
    """Convenience function for verifying campaign absence."""
    helper = DatabaseHelpers(db_session)
    return helper.verify_campaign_not_in_db(campaign_id)


def count_campaigns_in_db(db_session: Session) -> int:
    """Convenience function for counting campaigns."""
    helper = DatabaseHelpers(db_session)
    return helper.count_campaigns_in_db()


def cleanup_test_data(db_session: Session) -> Dict[str, int]:
    """Convenience function for cleaning test data."""
    helper = DatabaseHelpers(db_session)
    return helper.cleanup_test_data()


def create_test_campaign_in_db(db_session: Session, data: Dict[str, Any]) -> Campaign:
    """Convenience function for creating test campaigns."""
    helper = DatabaseHelpers(db_session)
    return helper.create_test_campaign_in_db(data)


def verify_lead_in_db(db_session, lead_id: str, expected_data: Dict[str, Any] = None) -> Lead:
    helper = DatabaseHelpers(db_session)
    return helper.verify_lead_in_db(lead_id, expected_data)


def verify_lead_not_in_db(db_session, lead_id: str) -> None:
    helper = DatabaseHelpers(db_session)
    return helper.verify_lead_not_in_db(lead_id)


def count_leads_in_db(db_session) -> int:
    helper = DatabaseHelpers(db_session)
    return helper.count_leads_in_db()


def cleanup_lead_test_data(db_session) -> Dict[str, int]:
    helper = DatabaseHelpers(db_session)
    return helper.cleanup_lead_test_data()


def create_test_lead_in_db(db_session, data: Dict[str, Any]) -> Lead:
    helper = DatabaseHelpers(db_session)
    return helper.create_test_lead_in_db(data) 
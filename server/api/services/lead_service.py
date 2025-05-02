import json
import os
from typing import List, Dict, Any, Optional, Tuple
from models.lead import Lead

class LeadService:
    def __init__(self, storage_file: str = 'leads.json'):
        self.storage_file = storage_file
        self._ensure_storage_file()

    def _ensure_storage_file(self):
        """Ensure the storage file exists and is valid JSON."""
        if not os.path.exists(self.storage_file):
            with open(self.storage_file, 'w') as f:
                json.dump([], f)

    def _read_leads(self) -> List[Dict[str, Any]]:
        """Read all leads from the storage file."""
        with open(self.storage_file, 'r') as f:
            return json.load(f)

    def _write_leads(self, leads: List[Dict[str, Any]]):
        """Write leads to the storage file."""
        with open(self.storage_file, 'w') as f:
            json.dump(leads, f, indent=2)

    def _is_duplicate(self, email: str, guid: Optional[str] = None) -> Tuple[bool, Optional[Lead], str]:
        """
        Check if a lead with the given email or GUID already exists.
        Returns a tuple of (is_duplicate, existing_lead, reason)
        """
        leads_data = self._read_leads()
        
        # First check for GUID match
        if guid:
            for lead_data in leads_data:
                if lead_data.get('guid') == guid:
                    return True, Lead.from_dict(lead_data), "A lead with this GUID already exists"
        
        # Then check for email match
        for lead_data in leads_data:
            if lead_data['email'].lower() == email.lower():
                return True, Lead.from_dict(lead_data), "A lead with this email already exists"
        
        return False, None, ""

    def get_all_leads(self) -> List[Lead]:
        """Get all leads."""
        leads_data = self._read_leads()
        return [Lead.from_dict(lead_data) for lead_data in leads_data]

    def get_lead(self, lead_id: str) -> Optional[Lead]:
        """Get a lead by ID or GUID."""
        leads_data = self._read_leads()
        for lead_data in leads_data:
            if lead_data.get('guid') == lead_id or lead_data.get('id') == lead_id:
                return Lead.from_dict(lead_data)
        return None

    def create_lead(self, lead_data: Dict[str, Any]) -> Tuple[Lead, bool, str]:
        """
        Create a new lead.
        Returns a tuple of (lead, is_duplicate, reason)
        """
        # Check for required fields
        email = lead_data.get('email', '')
        if not email:
            raise ValueError("Email is required for lead creation")

        # Check for duplicates
        guid = lead_data.get('guid')
        is_duplicate, existing_lead, reason = self._is_duplicate(email, guid)
        if is_duplicate:
            return existing_lead, True, reason

        # Create new lead
        lead = Lead(**lead_data)
        leads_data = self._read_leads()
        leads_data.append(lead.to_dict())
        self._write_leads(leads_data)
        return lead, False, ""

    def update_lead(self, lead_id: str, update_data: Dict[str, Any]) -> Optional[Lead]:
        """Update an existing lead."""
        leads_data = self._read_leads()
        for i, lead_data in enumerate(leads_data):
            if lead_data.get('guid') == lead_id or lead_data.get('id') == lead_id:
                # Check if email is being updated and if it would create a duplicate
                if 'email' in update_data:
                    email = update_data['email']
                    is_duplicate, _, reason = self._is_duplicate(email)
                    if is_duplicate:
                        raise ValueError(reason)

                # Update the lead data
                lead_data.update(update_data)
                lead_data['updated_at'] = Lead().created_at  # Update timestamp
                leads_data[i] = lead_data
                self._write_leads(leads_data)
                return Lead.from_dict(lead_data)
        return None

    def delete_lead(self, lead_id: str) -> bool:
        """Delete a lead by ID or GUID."""
        leads_data = self._read_leads()
        for i, lead_data in enumerate(leads_data):
            if lead_data.get('guid') == lead_id or lead_data.get('id') == lead_id:
                del leads_data[i]
                self._write_leads(leads_data)
                return True
        return False 
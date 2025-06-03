#!/usr/bin/env python3
"""
Smoke test for campaign flow - end-to-end testing
"""

import asyncio
import httpx
import json
import os
import sys
import time
from datetime import datetime
from typing import Dict, List, Any, Optional

# Add the app directory to Python path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from app.background_services.smoke_tests.utils.database_utils import (
    get_db_connection, execute_query, get_campaign_statistics, 
    cleanup_test_data, verify_database_integrity
)

# Configuration
API_BASE_URL = "http://localhost:8000"
TEST_USER_EMAIL = "test_campaign_user@example.com"
TEST_USER_PASSWORD = "testpass123"
TEST_ORGANIZATION_NAME = "Test Campaign Org"

class CampaignFlowTester:
    """End-to-end campaign flow tester."""
    
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=30.0)
        self.auth_token = None
        self.user_id = None
        self.organization_id = None
        self.campaign_ids = []
        
    async def cleanup(self):
        """Clean up resources."""
        if self.client:
            await self.client.aclose()
    
    async def setup_test_user(self) -> bool:
        """Set up test user and organization."""
        try:
            # Try to register user
            register_data = {
                "email": TEST_USER_EMAIL,
                "password": TEST_USER_PASSWORD,
                "full_name": "Test Campaign User"
            }
            
            response = await self.client.post(
                f"{API_BASE_URL}/api/v1/auth/signup",
                json=register_data
            )
            
            if response.status_code == 201:
                print("[Setup] User registered successfully")
            elif response.status_code == 400:
                print("[Setup] User already exists, continuing...")
            else:
                print(f"[Setup] Failed to register user: {response.status_code}")
                return False
            
            # Login to get auth token
            login_data = {
                "email": TEST_USER_EMAIL,
                "password": TEST_USER_PASSWORD
            }
            
            response = await self.client.post(
                f"{API_BASE_URL}/api/v1/auth/login",
                json=login_data
            )
            
            if response.status_code != 200:
                print(f"[Setup] Failed to login: {response.status_code}")
                return False
            
            login_result = response.json()
            self.auth_token = login_result["access_token"]
            self.user_id = login_result["user"]["id"]
            
            print(f"[Setup] Successfully logged in as user {self.user_id}")
            
            # Set up auth headers
            self.client.headers.update({
                "Authorization": f"Bearer {self.auth_token}"
            })
            
            # Create test organization
            org_data = {
                "name": TEST_ORGANIZATION_NAME,
                "description": "Test organization for campaign flow testing"
            }
            
            response = await self.client.post(
                f"{API_BASE_URL}/api/v1/organizations",
                json=org_data
            )
            
            if response.status_code == 201:
                org_result = response.json()
                self.organization_id = org_result["id"]
                print(f"[Setup] Created organization {self.organization_id}")
            elif response.status_code == 409:
                # Organization already exists, get it
                response = await self.client.get(f"{API_BASE_URL}/api/v1/organizations")
                if response.status_code == 200:
                    orgs = response.json()
                    for org in orgs:
                        if org["name"] == TEST_ORGANIZATION_NAME:
                            self.organization_id = org["id"]
                            print(f"[Setup] Using existing organization {self.organization_id}")
                            break
            
            if not self.organization_id:
                print("[Setup] Failed to create or find organization")
                return False
            
            return True
            
        except Exception as e:
            print(f"[Setup] Error: {e}")
            return False
    
    async def test_campaign_creation(self) -> bool:
        """Test campaign creation."""
        try:
            campaign_data = {
                "name": f"Test Campaign {datetime.now().strftime('%Y%m%d_%H%M%S')}",
                "description": "Automated test campaign",
                "organization_id": self.organization_id,
                "target_audience": "Software developers",
                "message_template": "Hello {name}, we have an exciting opportunity for you!",
                "status": "created"
            }
            
            response = await self.client.post(
                f"{API_BASE_URL}/api/v1/campaigns",
                json=campaign_data
            )
            
            if response.status_code != 201:
                print(f"[Campaign] Failed to create campaign: {response.status_code}")
                print(f"[Campaign] Response: {response.text}")
                return False
            
            campaign = response.json()
            campaign_id = campaign["id"]
            self.campaign_ids.append(campaign_id)
            
            print(f"[Campaign] Created campaign {campaign_id}: {campaign['name']}")
            
            # Verify campaign in database
            db_campaign = execute_query(
                "SELECT * FROM campaigns WHERE id = %s", 
                (campaign_id,)
            )
            
            if not db_campaign:
                print(f"[Campaign] ERROR: Campaign {campaign_id} not found in database")
                return False
            
            print(f"[Campaign] Campaign verified in database")
            return True
            
        except Exception as e:
            print(f"[Campaign] Error: {e}")
            return False
    
    async def test_campaign_workflow(self) -> bool:
        """Test complete campaign workflow."""
        try:
            if not self.campaign_ids:
                print("[Workflow] No campaigns available for testing")
                return False
            
            campaign_id = self.campaign_ids[0]
            
            # Start campaign
            response = await self.client.post(
                f"{API_BASE_URL}/api/v1/campaigns/{campaign_id}/start"
            )
            
            if response.status_code != 200:
                print(f"[Workflow] Failed to start campaign: {response.status_code}")
                return False
            
            print(f"[Workflow] Started campaign {campaign_id}")
            
            # Wait for campaign to process
            await asyncio.sleep(5)
            
            # Check campaign status
            response = await self.client.get(
                f"{API_BASE_URL}/api/v1/campaigns/{campaign_id}"
            )
            
            if response.status_code != 200:
                print(f"[Workflow] Failed to get campaign status: {response.status_code}")
                return False
            
            campaign = response.json()
            print(f"[Workflow] Campaign status: {campaign['status']}")
            
            # Verify in database
            db_campaign = execute_query(
                "SELECT * FROM campaigns WHERE id = %s", 
                (campaign_id,)
            )
            
            if db_campaign:
                print(f"[Workflow] Database status: {db_campaign[0]['status']}")
            
            return True
            
        except Exception as e:
            print(f"[Workflow] Error: {e}")
            return False
    
    async def test_lead_generation(self) -> bool:
        """Test lead generation functionality."""
        try:
            if not self.campaign_ids:
                print("[Leads] No campaigns available for testing")
                return False
            
            campaign_id = self.campaign_ids[0]
            
            # Get leads for campaign
            response = await self.client.get(
                f"{API_BASE_URL}/api/v1/campaigns/{campaign_id}/leads"
            )
            
            if response.status_code != 200:
                print(f"[Leads] Failed to get leads: {response.status_code}")
                return False
            
            leads = response.json()
            print(f"[Leads] Found {len(leads)} leads for campaign {campaign_id}")
            
            # Verify leads in database
            db_leads = execute_query(
                "SELECT COUNT(*) as count FROM leads WHERE campaign_id = %s", 
                (campaign_id,)
            )
            
            if db_leads:
                db_count = db_leads[0]['count']
                print(f"[Leads] Database shows {db_count} leads")
            
            return True
            
        except Exception as e:
            print(f"[Leads] Error: {e}")
            return False
    
    async def run_smoke_test(self) -> Dict[str, Any]:
        """Run complete smoke test."""
        print("=== Campaign Flow Smoke Test ===")
        print(f"API Base URL: {API_BASE_URL}")
        print(f"Test User: {TEST_USER_EMAIL}")
        print(f"Timestamp: {datetime.now().isoformat()}")
        print()
        
        results = {
            "timestamp": datetime.now().isoformat(),
            "api_base_url": API_BASE_URL,
            "tests": {},
            "database_stats": {},
            "overall_status": "unknown"
        }
        
        try:
            # Database integrity check
            print("[DB] Checking database integrity...")
            db_integrity = verify_database_integrity()
            results["database_stats"] = db_integrity
            
            if db_integrity["status"] != "healthy":
                print(f"[DB] Database integrity check failed: {db_integrity['message']}")
                results["overall_status"] = "failed"
                return results
            
            print("[DB] Database integrity verified")
            
            # Setup test user
            print("[Setup] Setting up test user...")
            setup_success = await self.setup_test_user()
            results["tests"]["setup"] = setup_success
            
            if not setup_success:
                results["overall_status"] = "failed"
                return results
            
            # Test campaign creation
            print("[Test] Testing campaign creation...")
            campaign_success = await self.test_campaign_creation()
            results["tests"]["campaign_creation"] = campaign_success
            
            # Test campaign workflow
            print("[Test] Testing campaign workflow...")
            workflow_success = await self.test_campaign_workflow()
            results["tests"]["campaign_workflow"] = workflow_success
            
            # Test lead generation
            print("[Test] Testing lead generation...")
            leads_success = await self.test_lead_generation()
            results["tests"]["lead_generation"] = leads_success
            
            # Final database stats
            final_stats = get_campaign_statistics()
            results["final_database_stats"] = final_stats
            
            # Determine overall status
            all_tests_passed = all([
                setup_success,
                campaign_success,
                workflow_success,
                leads_success
            ])
            
            results["overall_status"] = "passed" if all_tests_passed else "failed"
            
            print("\n=== Test Results ===")
            for test_name, passed in results["tests"].items():
                status = "PASS" if passed else "FAIL"
                print(f"{test_name}: {status}")
            
            print(f"\nOverall Status: {results['overall_status'].upper()}")
            
        except Exception as e:
            print(f"[Test] Unexpected error: {e}")
            results["overall_status"] = "error"
            results["error"] = str(e)
        
        finally:
            await self.cleanup()
        
        return results

async def main():
    """Main entry point."""
    tester = CampaignFlowTester()
    results = await tester.run_smoke_test()
    
    # Save results to file
    results_file = f"campaign_flow_test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\nResults saved to: {results_file}")
    
    # Exit with appropriate code
    if results["overall_status"] == "passed":
        sys.exit(0)
    else:
        sys.exit(1)

if __name__ == "__main__":
    # Database connectivity test
    print("Testing database connectivity...")
    db_url = f"postgresql://postgres:postgres@localhost:15432/lead_gen"
    try:
        conn = get_db_connection()
        print("✓ Database connection successful")
        conn.close()
    except Exception as e:
        print(f"✗ Database connection failed: {e}")
        sys.exit(1)
    
    # Run the test
    asyncio.run(main()) 
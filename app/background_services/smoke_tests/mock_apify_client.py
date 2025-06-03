import time
import json
import os
import random
import copy
import redis
from typing import Dict, Any, List

# Configuration constants
LEADS_PER_DATASET_CALL = 10  # Number of leads returned per dataset call

# Path to the original dataset
DATASET_PATH = os.path.join(os.path.dirname(__file__), 'dataset_apollo-io-scraper_2025-05-21_19-33-02-963.json')

# Redis keys for shared state
DATASET_LOADED_KEY = "mock_apify:dataset_loaded"
DATASET_ORIGINAL_KEY = "mock_apify:dataset_original"
DATASET_WORKING_KEY = "mock_apify:dataset_working"

def get_redis_connection() -> redis.Redis:
    """Get Redis connection for shared state across processes."""
    try:
        # Try to get Redis connection from app config if available
        try:
            from app.core.config import get_redis_connection as app_get_redis
            return app_get_redis()
        except ImportError:
            # Fallback to direct Redis connection
            return redis.Redis(
                host=os.getenv('REDIS_HOST', 'localhost'),
                port=int(os.getenv('REDIS_PORT', 6379)),
                db=int(os.getenv('REDIS_DB', 0)),
                decode_responses=True
            )
    except Exception as e:
        raise ConnectionError(f"Could not connect to Redis: {e}. Redis is required for MockApifyClient.")

def check_redis_availability() -> bool:
    """
    Check if Redis is available for MockApifyClient operations.
    Should be called at the beginning of tests to ensure Redis is ready.
    
    Returns:
        bool: True if Redis is available, False otherwise
    """
    try:
        redis_client = get_redis_connection()
        # Test Redis connectivity with a simple ping
        redis_client.ping()
        print(f"[MockApifyClient] Redis connectivity verified successfully")
        return True
    except Exception as e:
        print(f"[MockApifyClient] ERROR: Redis is not available: {e}")
        print(f"[MockApifyClient] Please ensure Redis is running and accessible")
        return False

def load_original_dataset():
    """Load the original dataset from file once and store in shared Redis storage."""
    redis_client = get_redis_connection()
    
    # Check if dataset is already loaded in Redis
    if redis_client.exists(DATASET_LOADED_KEY):
        print(f"[MockApifyClient] Dataset already loaded in Redis")
        return json.loads(redis_client.get(DATASET_ORIGINAL_KEY) or "[]")
    
    print(f"[MockApifyClient] Loading original dataset from: {DATASET_PATH}")
    try:
        with open(DATASET_PATH, 'r') as f:
            dataset = json.load(f)
        
        # Store in Redis
        redis_client.set(DATASET_ORIGINAL_KEY, json.dumps(dataset))
        redis_client.set(DATASET_WORKING_KEY, json.dumps(dataset))
        redis_client.set(DATASET_LOADED_KEY, "true")
        
        print(f"[MockApifyClient] Successfully loaded {len(dataset)} total records from file to Redis")
        print(f"[MockApifyClient] Created working dataset with {len(dataset)} records")
        
        # Check first few records for structure
        if dataset and len(dataset) > 0:
            first_record = dataset[0]
            print(f"[MockApifyClient] Sample record keys: {list(first_record.keys())}")
            print(f"[MockApifyClient] Sample email: {first_record.get('email', 'NO_EMAIL_FIELD')}")
        else:
            print(f"[MockApifyClient] WARNING: Dataset appears to be empty!")
        
        return dataset
        
    except Exception as e:
        print(f"[MockApifyClient] ERROR loading dataset: {e}")
        # Store empty dataset in Redis to prevent repeated load attempts
        redis_client.set(DATASET_ORIGINAL_KEY, json.dumps([]))
        redis_client.set(DATASET_WORKING_KEY, json.dumps([]))
        redis_client.set(DATASET_LOADED_KEY, "true")
        return []

def get_next_campaign_data(leads_count=LEADS_PER_DATASET_CALL):
    """
    Get the next available slice of leads using Redis-backed pop-based consumption.
    
    This approach uses Redis atomic operations to ensure that multiple worker
    processes can safely consume data without conflicts or duplicates.
    
    Args:
        leads_count: Number of leads to return (default: LEADS_PER_DATASET_CALL)
        
    Returns:
        List of lead dictionaries, or empty list if dataset is exhausted
    """
    redis_client = get_redis_connection()
    
    # Ensure dataset is loaded
    load_original_dataset()
    
    # Use Redis for thread-safe pop operations
    campaign_data = []
    
    # Use LPOP to atomically pop items from the working dataset list
    for _ in range(leads_count):
        # Try to pop an item from the working dataset
        item_json = redis_client.lpop(DATASET_WORKING_KEY + ":list")
        if item_json:
            try:
                lead = json.loads(item_json)
                campaign_data.append(copy.deepcopy(lead))
            except json.JSONDecodeError as e:
                print(f"[MockApifyClient] Error parsing lead from Redis: {e}")
                continue
        else:
            # No more items available
            break
    
    # Check if we need to initialize the list format
    if not campaign_data and redis_client.exists(DATASET_WORKING_KEY):
        # Convert from JSON array to Redis list format if needed
        working_data_json = redis_client.get(DATASET_WORKING_KEY)
        if working_data_json:
            try:
                working_data = json.loads(working_data_json)
                if working_data and isinstance(working_data, list):
                    # Convert to Redis list format
                    pipe = redis_client.pipeline()
                    pipe.delete(DATASET_WORKING_KEY + ":list")
                    for item in working_data:
                        pipe.lpush(DATASET_WORKING_KEY + ":list", json.dumps(item))
                    pipe.execute()
                    
                    # Clear the old JSON format
                    redis_client.delete(DATASET_WORKING_KEY)
                    
                    # Try again to pop items
                    for _ in range(leads_count):
                        item_json = redis_client.lpop(DATASET_WORKING_KEY + ":list")
                        if item_json:
                            try:
                                lead = json.loads(item_json)
                                campaign_data.append(copy.deepcopy(lead))
                            except json.JSONDecodeError:
                                continue
                        else:
                            break
            except json.JSONDecodeError:
                pass
    
    # Get remaining count
    remaining_count = redis_client.llen(DATASET_WORKING_KEY + ":list")
    
    # Log the results
    emails_provided = [lead.get('email') for lead in campaign_data]
    valid_emails = [email for email in emails_provided if email and email.strip()]
    
    print(f"[MockApifyClient] Popped {len(campaign_data)}/{leads_count} requested leads from Redis")
    print(f"[MockApifyClient] Working dataset remaining: {remaining_count} records")
    print(f"[MockApifyClient] Emails provided: {emails_provided}")
    print(f"[MockApifyClient] Valid emails: {len(valid_emails)}/{len(emails_provided)}")
    
    return campaign_data

def reset_dataset():
    """
    Reset the working dataset to original state for test isolation.
    
    This recreates the working dataset from the original loaded data.
    """
    redis_client = get_redis_connection()
    
    # Reset using Redis
    original_data_json = redis_client.get(DATASET_ORIGINAL_KEY)
    if original_data_json:
        original_data = json.loads(original_data_json)
        
        # Clear and rebuild the working list
        pipe = redis_client.pipeline()
        pipe.delete(DATASET_WORKING_KEY + ":list")
        for item in original_data:
            pipe.lpush(DATASET_WORKING_KEY + ":list", json.dumps(item))
        pipe.execute()
        
        # Also reset the JSON format
        redis_client.set(DATASET_WORKING_KEY, original_data_json)
        
        print(f"[MockApifyClient] Reset working dataset to original state: {len(original_data)} records available")
    else:
        print(f"[MockApifyClient] WARNING: Cannot reset - original dataset not loaded")

def get_dataset_status():
    """Get current dataset status for debugging."""
    redis_client = get_redis_connection()
    
    # Ensure dataset is loaded
    load_original_dataset()
    
    try:
        original_data_json = redis_client.get(DATASET_ORIGINAL_KEY)
        original_count = len(json.loads(original_data_json)) if original_data_json else 0
        remaining_count = redis_client.llen(DATASET_WORKING_KEY + ":list")
        consumed_count = original_count - remaining_count
        
        return {
            "status": "loaded" if redis_client.exists(DATASET_LOADED_KEY) else "not_loaded",
            "total": original_count,
            "consumed": consumed_count,
            "remaining": remaining_count,
            "storage": "redis"
        }
    except Exception as e:
        print(f"[MockApifyClient] Error getting dataset status from Redis: {e}")
        return {"status": "error", "error": str(e), "storage": "redis"}

class MockActor:
    def __init__(self, actor_id):
        self.actor_id = actor_id

    def call(self, run_input=None):
        # Simulate async process
        time.sleep(random.uniform(0.1, 0.3))
        
        # Return a mock dataset ID
        dataset_id = f"mock_dataset_{random.randint(1000, 9999)}"
        return {"defaultDatasetId": dataset_id}

class MockDataset:
    def __init__(self, dataset_id):
        self.dataset_id = dataset_id
        print(f"[MockDataset] Created dataset {dataset_id}")
    
    def iterate_items(self):
        """Get next available data slice using Redis-backed pop-based approach."""
        print(f"[MockDataset] Getting next data slice for dataset {self.dataset_id}")
        
        # Get next available data using the Redis-backed pop-based approach
        campaign_data = get_next_campaign_data(LEADS_PER_DATASET_CALL)
        
        print(f"[MockDataset] Returning {len(campaign_data)} leads for dataset {self.dataset_id}")
        
        return iter(campaign_data)

class MockApifyClient:
    def __init__(self, api_token=None):
        self.api_token = api_token
        self.actor_id = "mock/apollo-io-scraper"  # Mock actor ID
        print(f"[MockApifyClient] Initialized with api_token={'*' * 5 if api_token else None}")
        print(f"[MockApifyClient] Using mock actor_id: {self.actor_id}")
        # Load the dataset once when the client is instantiated
        load_original_dataset()
    
    def actor(self, actor_id):
        return MockActor(actor_id)

    def dataset(self, dataset_id):
        print(f"[MockApifyClient] Creating dataset {dataset_id}")
        return MockDataset(dataset_id)

def reset_campaign_counter():
    """
    Reset for test isolation - restores working dataset to original state.
    
    This function maintains backward compatibility while using the Redis-backed
    pop-based approach. It resets the working dataset to its original state.
    """
    reset_dataset()
    print(f"[MockApifyClient] System reset for new test run")

def get_mock_leads_data():
    """Get mock leads data using Redis-backed pop-based approach."""
    return get_next_campaign_data(LEADS_PER_DATASET_CALL)

__all__ = ["MockApifyClient", "get_mock_leads_data", "reset_campaign_counter", "get_next_campaign_data", "reset_dataset", "get_dataset_status", "check_redis_availability"] 
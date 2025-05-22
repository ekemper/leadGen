import time
import json
import os

# Load the mock leads data from the JSON file
mock_data_path = os.path.join(os.path.dirname(__file__), 'mock-leads-data.json')
with open(mock_data_path, 'r') as f:
    MOCK_LEADS_DATA = json.load(f)

class MockActor:
    def __init__(self, actor_id):
        self.actor_id = actor_id
    def call(self, run_input=None):
        # Simulate async process
        time.sleep(5)
        # Return a fake run object with a dataset id
        return {"defaultDatasetId": "mock-dataset-id"}

class MockDataset:
    def __init__(self, dataset_id):
        self.dataset_id = dataset_id
    def iterate_items(self):
        # Return the mock leads data
        return iter(MOCK_LEADS_DATA)

class MockApifyClient:
    def __init__(self, api_token=None):
        self.api_token = api_token
    def actor(self, actor_id):
        return MockActor(actor_id)
    def dataset(self, dataset_id):
        return MockDataset(dataset_id)

__all__ = ["MockApifyClient", "MOCK_LEADS_DATA"] 
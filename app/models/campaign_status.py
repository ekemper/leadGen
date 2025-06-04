import enum

# TODO: the paused status of the campaign should be removed
class CampaignStatus(str, enum.Enum):
    CREATED = "CREATED"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"     # New status for circuit breaker pausing
    COMPLETED = "COMPLETED"
    FAILED = "FAILED" 
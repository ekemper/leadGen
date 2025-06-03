import enum


class CampaignStatus(str, enum.Enum):
    CREATED = "CREATED"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"     # New status for circuit breaker pausing
    COMPLETED = "COMPLETED"
    FAILED = "FAILED" 
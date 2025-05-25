from enum import Enum

class JobStatus(str, Enum):
    """Enum for job status values."""
    PENDING = 'PENDING'
    STARTED = 'STARTED'
    IN_PROGRESS = 'IN_PROGRESS'
    RUNNING = 'RUNNING'
    COMPLETED = 'COMPLETED'
    FAILED = 'FAILED'
    DELAYED = 'DELAYED' 
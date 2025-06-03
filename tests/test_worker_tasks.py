import pytest
from unittest.mock import Mock, patch
from app.workers.tasks import process_job, health_check
from app.models.job import JobStatus

def test_health_check_task():
    """Test the health check task"""
    result = health_check()
    assert result["status"] == "healthy"
    assert "timestamp" in result

@patch('app.workers.tasks.SessionLocal')
def test_process_job_success(mock_session):
    """Test successful job processing"""
    # Mock database session and job
    mock_db = Mock()
    mock_job = Mock()
    mock_job.id = 1
    mock_job.status = JobStatus.PENDING
    
    mock_db.query.return_value.filter.return_value.first.return_value = mock_job
    mock_session.return_value = mock_db
    
    # Mock the task
    mock_task = Mock()
    mock_task.request.id = "test-task-id"
    
    # Test with mocked sleep to speed up test
    with patch('time.sleep'):
        with patch('random.random', return_value=0.5):  # Ensure no random failure
            result = process_job.apply(args=[1], task_id="test-task-id").get()
    
    assert result["job_id"] == 1
    assert result["status"] == "completed"
    assert mock_job.status == JobStatus.COMPLETED

@patch('app.workers.tasks.SessionLocal')
def test_process_job_not_found(mock_session):
    """Test processing non-existent job"""
    # Mock database session with no job found
    mock_db = Mock()
    mock_db.query.return_value.filter.return_value.first.return_value = None
    mock_session.return_value = mock_db
    
    # Test that it raises ValueError
    with pytest.raises(ValueError, match="Job .* not found"):
        process_job.apply(args=[999]).get() 
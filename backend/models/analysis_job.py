"""
Analysis Job model for tracking Celery tasks.
"""

from beanie import Document, Indexed, PydanticObjectId
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime
from enum import Enum


class JobStatus(str, Enum):
    """
    Enumeration for job status.
    """
    PENDING = "pending"
    STARTED = "started"
    RETRY = "retry"
    FAILURE = "failure"
    SUCCESS = "success"


class AnalysisJob(Document):
    """
    MongoDB document model for tracking analysis jobs.
    """
    
    # Job identification
    job_id: str  # Our custom job ID
    celery_task_id: Optional[str] = None  # Celery task ID
    report_id: PydanticObjectId  # Reference to the report
    
    # Analysis configuration
    options: Optional[Dict[str, Any]] = None
    estimated_completion: Optional[datetime] = None
    
    # Status and timing
    status: JobStatus = JobStatus.PENDING
    created_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # Progress tracking
    progress: int = Field(default=0, ge=0, le=100)
    current_step: Optional[str] = None
    total_steps: Optional[int] = None
    
    # Results and error handling
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    error_details: Optional[Dict[str, Any]] = None
    
    # Retry information
    retry_count: int = Field(default=0, ge=0)
    max_retries: int = Field(default=3, ge=0)
    
    # Worker information
    worker_name: Optional[str] = None
    worker_pid: Optional[int] = None
    
    class Settings:
        name = "analysis_jobs"
        indexes = [
            [("job_id", 1)],  # Unique index on job_id
            [("report_id", 1)],
            [("status", 1)],
            [("created_at", -1)],
            [("report_id", 1), ("status", 1)],
        ]
    
    def update_progress(self, progress: int, step: Optional[str] = None):
        """
        Update job progress.
        """
        self.progress = min(max(progress, 0), 100)
        if step:
            self.current_step = step
        self.updated_at = datetime.utcnow()
    
    def start_job(self, worker_name: Optional[str] = None, worker_pid: Optional[int] = None):
        """
        Mark job as started.
        """
        self.status = JobStatus.STARTED
        self.started_at = datetime.utcnow()
        self.worker_name = worker_name
        self.worker_pid = worker_pid
    
    def complete_job(self, result: Dict[str, Any]):
        """
        Mark job as completed with results.
        """
        self.status = JobStatus.SUCCESS
        self.completed_at = datetime.utcnow()
        self.progress = 100
        self.result = result
    
    def fail_job(self, error: str, error_details: Optional[Dict[str, Any]] = None):
        """
        Mark job as failed with error information.
        """
        self.status = JobStatus.FAILURE
        self.completed_at = datetime.utcnow()
        self.error = error
        self.error_details = error_details
    
    def retry_job(self):
        """
        Increment retry count and mark for retry.
        """
        self.retry_count += 1
        if self.retry_count < self.max_retries:
            self.status = JobStatus.RETRY
        else:
            self.fail_job("Maximum retries exceeded")
    
    def get_execution_time(self) -> Optional[float]:
        """
        Calculate execution time in seconds.
        """
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert job to dictionary for API responses.
        """
        return {
            "job_id": self.job_id,
            "report_id": str(self.report_id),
            "status": self.status.value,
            "progress": self.progress,
            "current_step": self.current_step,
            "total_steps": self.total_steps,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "execution_time": self.get_execution_time(),
            "result": self.result,
            "error": self.error,
            "retry_count": self.retry_count,
            "worker_name": self.worker_name,
        } 
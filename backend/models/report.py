"""
Report model for PCAP analysis reports.
"""

from beanie import Document, Indexed
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum


class ReportStatus(str, Enum):
    """
    Enumeration for report processing status.
    """
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class AnalysisResults(BaseModel):
    """
    Structure for analysis results data.
    """
    # Basic file information
    file_info: Dict[str, Any] = Field(default_factory=dict)
    
    # Traffic statistics
    traffic_stats: Dict[str, Any] = Field(default_factory=dict)
    
    # Top N statistics
    top_talkers: List[Dict[str, Any]] = Field(default_factory=list)
    top_conversations: List[Dict[str, Any]] = Field(default_factory=list)
    top_protocols: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Protocol analysis
    protocol_analysis: Dict[str, Any] = Field(default_factory=dict)
    
    # Network issues and diagnostics
    network_issues: List[Dict[str, Any]] = Field(default_factory=list)
    
    # TCP analysis
    tcp_analysis: Dict[str, Any] = Field(default_factory=dict)
    
    # DNS analysis
    dns_analysis: Dict[str, Any] = Field(default_factory=dict)
    
    # Flow diagram data
    flow_diagram: Optional[str] = None
    
    # Executive summary
    executive_summary: Dict[str, Any] = Field(default_factory=dict)
    
    # Processing metadata
    processing_time: Optional[float] = None
    analysis_timestamp: Optional[datetime] = None


class Report(Document):
    """
    MongoDB document model for PCAP analysis reports.
    """
    
    # Basic file information
    filename: Indexed(str)
    original_filename: str
    file_size: int
    file_hash: Optional[str] = None
    upload_path: str
    
    # Status and timing
    status: ReportStatus = ReportStatus.PENDING
    created_at: Indexed(datetime) = Field(default_factory=datetime.utcnow)
    updated_at: Indexed(datetime) = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # Analysis results
    analysis_results: Optional[AnalysisResults] = None
    
    # Error handling
    error_message: Optional[str] = None
    error_details: Optional[Dict[str, Any]] = None
    
    # Job tracking
    job_id: Optional[str] = None
    
    # Analysis configuration
    analysis_options: Optional[Dict[str, Any]] = None
    
    # User context (for future authentication)
    user_id: Optional[str] = None
    
    # Metadata
    tags: List[str] = Field(default_factory=list)
    notes: Optional[str] = None
    
    class Settings:
        name = "reports"
        indexes = [
            [("filename", 1)],
            [("status", 1)],
            [("created_at", -1)],
            [("updated_at", -1)],
            [("status", 1), ("created_at", -1)],
            [("job_id", 1)],
        ]
    
    def update_status(self, status: ReportStatus, error_message: Optional[str] = None):
        """
        Update the report status and timestamp.
        """
        self.status = status
        self.updated_at = datetime.utcnow()
        
        if status == ReportStatus.PROCESSING:
            self.started_at = datetime.utcnow()
        elif status == ReportStatus.COMPLETED:
            self.completed_at = datetime.utcnow()
        elif status == ReportStatus.FAILED:
            self.error_message = error_message
            self.completed_at = datetime.utcnow()
    
    def set_analysis_results(self, results: AnalysisResults):
        """
        Set the analysis results and update status.
        """
        self.analysis_results = results
        self.update_status(ReportStatus.COMPLETED)
    
    def get_processing_time(self) -> Optional[float]:
        """
        Calculate processing time in seconds.
        """
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert report to dictionary for API responses.
        """
        return {
            "id": str(self.id),
            "filename": self.filename,
            "original_filename": self.original_filename,
            "file_size": self.file_size,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "processing_time": self.get_processing_time(),
            "analysis_results": self.analysis_results.dict() if self.analysis_results else None,
            "error_message": self.error_message,
            "job_id": self.job_id,
            "tags": self.tags,
            "notes": self.notes,
        } 
"""
Report model for PCAP analysis results.
"""
from datetime import datetime
from typing import Dict, Any, Optional, List
from enum import Enum

from beanie import Document, Indexed
from pydantic import Field
from pymongo import IndexModel, ASCENDING, DESCENDING


class ReportStatus(str, Enum):
    """Status of a report."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Report(Document):
    """Report document for storing PCAP analysis results."""
    
    # Core identifiers - indexed for fast lookups
    job_id: str = Field(..., description="Unique job identifier")
    original_filename: str = Field(..., description="Original filename")
    
    # Status and timing - indexed for filtering and sorting
    status: ReportStatus = Field(default=ReportStatus.PENDING, description="Report status")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Last update timestamp")
    started_at: Optional[datetime] = Field(None, description="Analysis start time")
    completed_at: Optional[datetime] = Field(None, description="Analysis completion time")
    
    # File information
    file_path: str = Field(..., description="Path to the PCAP file")
    file_size: int = Field(..., description="File size in bytes")
    file_hash: Optional[str] = Field(None, description="SHA256 hash of the file")
    
    # Analysis results
    analysis_results: Optional[Dict[str, Any]] = Field(None, description="Analysis results")
    summary: Optional[Dict[str, Any]] = Field(None, description="Analysis summary")
    
    # Error handling
    error_message: Optional[str] = Field(None, description="Error message if failed")
    
    # Processing information
    processing_time: Optional[float] = Field(None, description="Processing time in seconds")
    analysis_options: Optional[Dict[str, Any]] = Field(None, description="Analysis configuration options")
    
    # Performance metrics for optimization
    total_packets: Optional[int] = Field(None, description="Total packets analyzed")
    duration: Optional[float] = Field(None, description="Capture duration in seconds")
    
    class Settings:
        name = "reports"
        
        # Define compound indexes for common query patterns
        indexes = [
            # Status and timing queries
            IndexModel([("status", ASCENDING), ("created_at", DESCENDING)]),
            IndexModel([("status", ASCENDING), ("updated_at", DESCENDING)]),
            
            # File size and performance queries
            IndexModel([("file_size", DESCENDING), ("created_at", DESCENDING)]),
            IndexModel([("total_packets", DESCENDING), ("created_at", DESCENDING)]),
            
            # Job lookup and status tracking - unique constraint on job_id
            IndexModel([("job_id", ASCENDING)], unique=True),
            IndexModel([("job_id", ASCENDING), ("status", ASCENDING)]),
            
            # Filename search
            IndexModel([("original_filename", ASCENDING)]),
            
            # Time-based queries for cleanup and reporting
            IndexModel([("created_at", DESCENDING)]),
            IndexModel([("completed_at", DESCENDING)]),
            
            # Performance analysis queries
            IndexModel([("status", ASCENDING), ("file_size", DESCENDING), ("processing_time", ASCENDING)]),
            
            # Hash-based deduplication
            IndexModel([("file_hash", ASCENDING)], sparse=True),
        ]
    
    def __str__(self) -> str:
        return f"Report({self.job_id}, {self.status}, {self.original_filename})"
    
    def __repr__(self) -> str:
        return self.__str__()
    
    @classmethod
    async def find_by_status(cls, status: ReportStatus, limit: int = 100) -> List["Report"]:
        """Find reports by status with optimized query."""
        return await cls.find(
            {"status": status}
        ).sort([("created_at", DESCENDING)]).limit(limit).to_list()
    
    @classmethod
    async def find_recent(cls, limit: int = 50) -> List["Report"]:
        """Find recent reports with optimized query."""
        return await cls.find_all().sort([("created_at", DESCENDING)]).limit(limit).to_list()
    
    @classmethod
    async def find_by_file_size_range(cls, min_size: int, max_size: int) -> List["Report"]:
        """Find reports by file size range."""
        return await cls.find({
            "file_size": {"$gte": min_size, "$lte": max_size}
        }).sort([("created_at", DESCENDING)]).to_list()
    
    @classmethod
    async def get_status_counts(cls) -> Dict[str, int]:
        """Get count of reports by status using aggregation."""
        pipeline = [
            {"$group": {"_id": "$status", "count": {"$sum": 1}}},
            {"$sort": {"_id": 1}}
        ]
        
        result = await cls.aggregate(pipeline).to_list()
        return {item["_id"]: item["count"] for item in result}
    
    @classmethod
    async def get_processing_stats(cls) -> Dict[str, Any]:
        """Get processing statistics using aggregation."""
        pipeline = [
            {"$match": {"status": "completed", "processing_time": {"$exists": True}}},
            {"$group": {
                "_id": None,
                "total_reports": {"$sum": 1},
                "avg_processing_time": {"$avg": "$processing_time"},
                "min_processing_time": {"$min": "$processing_time"},
                "max_processing_time": {"$max": "$processing_time"},
                "total_packets_processed": {"$sum": "$total_packets"},
                "total_bytes_processed": {"$sum": "$file_size"}
            }}
        ]
        
        result = await cls.aggregate(pipeline).to_list()
        return result[0] if result else {}
    
    @classmethod
    async def cleanup_old_reports(cls, older_than_days: int = 30) -> int:
        """Clean up old reports efficiently."""
        from datetime import timedelta
        
        cutoff_date = datetime.utcnow() - timedelta(days=older_than_days)
        
        # Use delete_many for efficient bulk deletion
        result = await cls.find({"created_at": {"$lt": cutoff_date}}).delete()
        return result.deleted_count if result else 0
    
    def update_processing_metrics(self):
        """Update processing metrics from analysis results."""
        if self.analysis_results:
            traffic_stats = self.analysis_results.get("traffic_stats", {})
            self.total_packets = traffic_stats.get("total_packets")
            self.duration = traffic_stats.get("duration")
            
            # Calculate processing time if not already set
            if not self.processing_time and self.started_at and self.completed_at:
                self.processing_time = (self.completed_at - self.started_at).total_seconds()
    
    async def save(self, *args, **kwargs):
        """Override save to update timestamps and metrics."""
        self.updated_at = datetime.utcnow()
        self.update_processing_metrics()
        return await super().save(*args, **kwargs)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert report to dictionary format for API responses."""
        return {
            "id": str(self.id),
            "job_id": self.job_id,
            "original_filename": self.original_filename,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "file_path": self.file_path,
            "file_size": self.file_size,
            "file_hash": self.file_hash,
            "analysis_results": self.analysis_results,
            "summary": self.summary,
            "error_message": self.error_message,
            "processing_time": self.processing_time,
            "analysis_options": self.analysis_options,
            "total_packets": self.total_packets,
            "duration": self.duration
        } 
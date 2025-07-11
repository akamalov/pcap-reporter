"""
Analysis Storage Service for MongoDB Operations.

This service provides a high-level interface for storing and retrieving
PCAP analysis results, managing reports and analysis jobs in MongoDB.
"""

import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union
from bson import ObjectId

# Import Beanie and MongoDB models
from beanie import PydanticObjectId
from motor.motor_asyncio import AsyncIOMotorClient

# Import models
from models.report import Report, ReportStatus
from models.analysis_job import AnalysisJob, JobStatus
from models.analysis_results import AnalysisResults

# Import database utilities
from core.database import get_database, init_db

logger = logging.getLogger(__name__)


class AnalysisStorageService:
    """Service for managing analysis results storage in MongoDB."""
    
    def __init__(self):
        """Initialize the storage service."""
        self.logger = logging.getLogger(__name__)
        self._db = None
        self._initialized = False
        
        # Performance tracking
        self._operation_count = 0
        self._total_operation_time = 0.0
        self._start_time = datetime.utcnow()
    
    async def initialize(self) -> None:
        """Initialize the storage service and database connection."""
        if self._initialized:
            return
            
        try:
            # Initialize database and Beanie ODM
            await init_db()
            self._db = await get_database()
            self._initialized = True
            
            self.logger.info("Analysis storage service initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize storage service: {e}")
            raise
    
    async def _ensure_connection(self) -> None:
        """Ensure database connection is active."""
        if not self._initialized:
            await self.initialize()
    
    async def _execute_in_transaction(self, operation_func, *args, **kwargs):
        """Execute an operation within a transaction context."""
        # For now, execute directly without transaction
        # In production, you might want to implement proper transaction handling
        return await operation_func(*args, **kwargs)
    
    def _track_operation(self, operation_time: float) -> None:
        """Track operation performance metrics."""
        self._operation_count += 1
        self._total_operation_time += operation_time
    
    # Report Management Methods
    
    async def create_report(
        self,
        job_id: str,
        original_filename: str,
        file_path: str,
        file_size: int,
        file_hash: Optional[str] = None,
        analysis_options: Optional[Dict[str, Any]] = None
    ) -> Report:
        """
        Create a new report record.
        
        Args:
            job_id: Unique job identifier
            original_filename: Original filename of the PCAP file
            file_path: Path to the stored PCAP file
            file_size: Size of the file in bytes
            file_hash: Optional SHA256 hash of the file
            analysis_options: Optional analysis configuration
            
        Returns:
            Created Report instance
        """
        start_time = time.time()
        await self._ensure_connection()
        
        try:
            report = Report(
                job_id=job_id,
                original_filename=original_filename,
                file_path=file_path,
                file_size=file_size,
                file_hash=file_hash,
                status=ReportStatus.PENDING,
                analysis_options=analysis_options
            )
            
            await report.insert()
            
            self.logger.info(f"Created report for job {job_id}: {report.id}")
            return report
            
        except Exception as e:
            self.logger.error(f"Failed to create report for job {job_id}: {e}")
            raise
        finally:
            self._track_operation(time.time() - start_time)
    
    async def get_report_by_id(self, report_id: str) -> Optional[Report]:
        """
        Retrieve a report by its ID.
        
        Args:
            report_id: Report ID to retrieve
            
        Returns:
            Report instance or None if not found
        """
        start_time = time.time()
        await self._ensure_connection()
        
        try:
            if not ObjectId.is_valid(report_id):
                return None
                
            report = await Report.get(report_id)
            return report
            
        except Exception as e:
            self.logger.error(f"Failed to retrieve report {report_id}: {e}")
            return None
        finally:
            self._track_operation(time.time() - start_time)
    
    async def get_report_by_job_id(self, job_id: str) -> Optional[Report]:
        """
        Retrieve a report by its job ID.
        
        Args:
            job_id: Job ID to search for
            
        Returns:
            Report instance or None if not found
        """
        start_time = time.time()
        await self._ensure_connection()
        
        try:
            report = await Report.find_one({"job_id": job_id})
            return report
            
        except Exception as e:
            self.logger.error(f"Failed to retrieve report by job ID {job_id}: {e}")
            return None
        finally:
            self._track_operation(time.time() - start_time)
    
    async def update_report_status(self, report_id: str, status: ReportStatus) -> Optional[Report]:
        """
        Update a report's status.
        
        Args:
            report_id: Report ID to update
            status: New status
            
        Returns:
            Updated Report instance or None if not found
        """
        start_time = time.time()
        await self._ensure_connection()
        
        try:
            report = await self.get_report_by_id(report_id)
            if not report:
                return None
                
            report.status = status
            if status == ReportStatus.COMPLETED:
                report.completed_at = datetime.utcnow()
            elif status == ReportStatus.PROCESSING:
                report.started_at = datetime.utcnow()
                
            await report.save()
            return report
            
        except Exception as e:
            self.logger.error(f"Failed to update report status {report_id}: {e}")
            raise
        finally:
            self._track_operation(time.time() - start_time)
    
    async def save_analysis_results(
        self, 
        report_id: str, 
        analysis_results: AnalysisResults
    ) -> Report:
        """
        Save complete analysis results to a report.
        
        Args:
            report_id: Report ID to update
            analysis_results: Complete analysis results
            
        Returns:
            Updated Report instance
            
        Raises:
            ValueError: If report not found
        """
        start_time = time.time()
        await self._ensure_connection()
        
        try:
            report = await self.get_report_by_id(report_id)
            if not report:
                raise ValueError(f"Report not found: {report_id}")
            
            # Convert AnalysisResults to dict format for storage
            results_dict = {
                "file_path": analysis_results.file_path,
                "file_size": analysis_results.file_size,
                "analysis_timestamp": analysis_results.analysis_timestamp,
                "traffic_stats": {
                    "total_packets": analysis_results.traffic_stats.total_packets,
                    "total_bytes": analysis_results.traffic_stats.total_bytes,
                    "duration": analysis_results.traffic_stats.duration,
                    "avg_packet_size": analysis_results.traffic_stats.avg_packet_size,
                    "packets_per_second": analysis_results.traffic_stats.packets_per_second,
                    "bytes_per_second": analysis_results.traffic_stats.bytes_per_second
                },
                "performance_metrics": {
                    "avg_latency": analysis_results.performance_metrics.avg_latency,
                    "max_latency": analysis_results.performance_metrics.max_latency,
                    "min_latency": analysis_results.performance_metrics.min_latency,
                    "packet_loss_rate": analysis_results.performance_metrics.packet_loss_rate,
                    "throughput_mbps": analysis_results.performance_metrics.throughput_mbps,
                    "jitter": analysis_results.performance_metrics.jitter,
                    "retransmission_rate": analysis_results.performance_metrics.retransmission_rate
                },
                "protocol_stats": {
                    "tcp_packets": analysis_results.protocol_stats.tcp_packets,
                    "udp_packets": analysis_results.protocol_stats.udp_packets,
                    "icmp_packets": analysis_results.protocol_stats.icmp_packets,
                    "http_sessions": analysis_results.protocol_stats.http_sessions,
                    "https_sessions": analysis_results.protocol_stats.https_sessions,
                    "dns_queries": analysis_results.protocol_stats.dns_queries,
                    "dhcp_packets": analysis_results.protocol_stats.dhcp_packets,
                    "arp_packets": analysis_results.protocol_stats.arp_packets,
                    "other_packets": analysis_results.protocol_stats.other_packets
                },
                "issues": [
                    {
                        "type": issue.type.value,
                        "severity": issue.severity.value,
                        "description": issue.description,
                        "affected_hosts": issue.affected_hosts,
                        "affected_protocols": issue.affected_protocols,
                        "recommendation": issue.recommendation,
                        "confidence": issue.confidence,
                        "first_seen": issue.first_seen,
                        "last_seen": issue.last_seen,
                        "count": issue.count
                    }
                    for issue in analysis_results.issues
                ],
                "top_conversations": [
                    {
                        "src_ip": conv.src_ip,
                        "dst_ip": conv.dst_ip,
                        "src_port": conv.src_port,
                        "dst_port": conv.dst_port,
                        "protocol": conv.protocol,
                        "packets_sent": conv.packets_sent,
                        "packets_received": conv.packets_received,
                        "bytes_sent": conv.bytes_sent,
                        "bytes_received": conv.bytes_received,
                        "duration": conv.duration,
                        "start_time": conv.start_time,
                        "end_time": conv.end_time
                    }
                    for conv in analysis_results.top_conversations
                ],
                "start_time": analysis_results.start_time,
                "end_time": analysis_results.end_time,
                "processing_time": analysis_results.processing_time,
                "analysis_options": analysis_results.analysis_options
            }
            
            # Add protocol analysis if present
            if analysis_results.protocol_analysis:
                results_dict["protocol_analysis"] = analysis_results.protocol_analysis
            
            # Add TCP analysis if present
            if analysis_results.tcp_analysis:
                results_dict["tcp_analysis"] = {
                    "total_connections": analysis_results.tcp_analysis.total_connections,
                    "successful_connections": analysis_results.tcp_analysis.successful_connections,
                    "failed_connections": analysis_results.tcp_analysis.failed_connections,
                    "avg_handshake_time": analysis_results.tcp_analysis.avg_handshake_time,
                    "max_handshake_time": analysis_results.tcp_analysis.max_handshake_time,
                    "retransmissions": analysis_results.tcp_analysis.retransmissions,
                    "duplicate_acks": analysis_results.tcp_analysis.duplicate_acks,
                    "zero_windows": analysis_results.tcp_analysis.zero_windows,
                    "reset_connections": analysis_results.tcp_analysis.reset_connections
                }
            
            # Add DNS analysis if present
            if analysis_results.dns_analysis:
                results_dict["dns_analysis"] = {
                    "total_queries": analysis_results.dns_analysis.total_queries,
                    "successful_queries": analysis_results.dns_analysis.successful_queries,
                    "failed_queries": analysis_results.dns_analysis.failed_queries,
                    "avg_response_time": analysis_results.dns_analysis.avg_response_time,
                    "max_response_time": analysis_results.dns_analysis.max_response_time,
                    "timeout_queries": analysis_results.dns_analysis.timeout_queries,
                    "nxdomain_responses": analysis_results.dns_analysis.nxdomain_responses,
                    "servfail_responses": analysis_results.dns_analysis.servfail_responses
                }
            
            # Update report
            report.analysis_results = results_dict
            report.status = ReportStatus.COMPLETED
            report.completed_at = datetime.utcnow()
            report.processing_time = analysis_results.processing_time
            
            await report.save()
            
            self.logger.info(f"Saved analysis results for report {report_id}")
            return report
            
        except Exception as e:
            self.logger.error(f"Failed to save analysis results for report {report_id}: {e}")
            raise
        finally:
            self._track_operation(time.time() - start_time)
    
    async def save_triage_results(
        self,
        report_id: str,
        triage_results: Dict[str, Any]
    ) -> Report:
        """
        Save triage analysis results to a report.
        
        Args:
            report_id: Report ID to update
            triage_results: Triage analysis results
            
        Returns:
            Updated Report instance
        """
        start_time = time.time()
        await self._ensure_connection()
        
        try:
            report = await self.get_report_by_id(report_id)
            if not report:
                raise ValueError(f"Report not found: {report_id}")
            
            # Initialize analysis_results if not present
            if not report.analysis_results:
                report.analysis_results = {}
            
            # Add triage results
            report.analysis_results.update(triage_results)
            report.status = ReportStatus.PROCESSING  # Partial completion
            
            await report.save()
            
            self.logger.info(f"Saved triage results for report {report_id}")
            return report
            
        except Exception as e:
            self.logger.error(f"Failed to save triage results for report {report_id}: {e}")
            raise
        finally:
            self._track_operation(time.time() - start_time)
    
    async def append_deep_inspection_results(
        self,
        report_id: str,
        deep_results: Dict[str, Any]
    ) -> Report:
        """
        Append deep inspection results to existing analysis results.
        
        Args:
            report_id: Report ID to update
            deep_results: Deep inspection results
            
        Returns:
            Updated Report instance
        """
        start_time = time.time()
        await self._ensure_connection()
        
        try:
            report = await self.get_report_by_id(report_id)
            if not report:
                raise ValueError(f"Report not found: {report_id}")
            
            # Initialize analysis_results if not present
            if not report.analysis_results:
                report.analysis_results = {}
            
            # Add deep inspection results
            report.analysis_results["deep_inspection"] = deep_results
            
            await report.save()
            
            self.logger.info(f"Appended deep inspection results for report {report_id}")
            return report
            
        except Exception as e:
            self.logger.error(f"Failed to append deep inspection results for report {report_id}: {e}")
            raise
        finally:
            self._track_operation(time.time() - start_time)
    
    # Analysis Job Management Methods
    
    async def create_analysis_job(
        self,
        job_id: str,
        report_id: Union[str, PydanticObjectId],
        options: Optional[Dict[str, Any]] = None,
        estimated_completion: Optional[datetime] = None
    ) -> AnalysisJob:
        """
        Create a new analysis job record.
        
        Args:
            job_id: Unique job identifier
            report_id: Associated report ID
            options: Analysis options
            estimated_completion: Estimated completion time
            
        Returns:
            Created AnalysisJob instance
            
        Raises:
            ValueError: If job ID already exists
        """
        start_time = time.time()
        await self._ensure_connection()
        
        try:
            # Check for duplicate job ID
            existing_job = await AnalysisJob.find_one({"job_id": job_id})
            if existing_job:
                raise ValueError(f"Job ID already exists: {job_id}")
            
            # Convert report_id to ObjectId if it's a string
            if isinstance(report_id, str):
                if not ObjectId.is_valid(report_id):
                    raise ValueError(f"Invalid report ID: {report_id}")
                report_id = PydanticObjectId(report_id)
            
            job = AnalysisJob(
                job_id=job_id,
                report_id=report_id,
                options=options,
                estimated_completion=estimated_completion,
                status=JobStatus.PENDING,
                progress=0
            )
            
            await job.insert()
            
            self.logger.info(f"Created analysis job {job_id} for report {report_id}")
            return job
            
        except Exception as e:
            self.logger.error(f"Failed to create analysis job {job_id}: {e}")
            raise
        finally:
            self._track_operation(time.time() - start_time)
    
    async def get_analysis_job_by_id(self, job_id: str) -> Optional[AnalysisJob]:
        """
        Retrieve an analysis job by its job ID.
        
        Args:
            job_id: Job ID to retrieve
            
        Returns:
            AnalysisJob instance or None if not found
        """
        start_time = time.time()
        await self._ensure_connection()
        
        try:
            job = await AnalysisJob.find_one({"job_id": job_id})
            return job
            
        except Exception as e:
            self.logger.error(f"Failed to retrieve analysis job {job_id}: {e}")
            return None
        finally:
            self._track_operation(time.time() - start_time)
    
    async def update_job_progress(
        self,
        job_id: str,
        progress: int,
        current_step: Optional[str] = None
    ) -> AnalysisJob:
        """
        Update analysis job progress.
        
        Args:
            job_id: Job ID to update
            progress: Progress percentage (0-100)
            current_step: Optional description of current step
            
        Returns:
            Updated AnalysisJob instance
            
        Raises:
            ValueError: If job not found
        """
        start_time = time.time()
        await self._ensure_connection()
        
        try:
            job = await self.get_analysis_job_by_id(job_id)
            if not job:
                raise ValueError(f"Job not found: {job_id}")
            
            job.progress = min(max(progress, 0), 100)
            if current_step:
                job.current_step = current_step
            
            # Auto-update status to started if progress > 0
            if progress > 0 and job.status == JobStatus.PENDING:
                job.status = JobStatus.STARTED
                job.started_at = datetime.utcnow()
            
            await job.save()
            
            self.logger.debug(f"Updated job {job_id} progress to {progress}%")
            return job
            
        except Exception as e:
            self.logger.error(f"Failed to update job progress {job_id}: {e}")
            raise
        finally:
            self._track_operation(time.time() - start_time)
    
    async def complete_analysis_job(
        self,
        job_id: str,
        results: Dict[str, Any]
    ) -> AnalysisJob:
        """
        Mark an analysis job as completed with results.
        
        Args:
            job_id: Job ID to complete
            results: Analysis results
            
        Returns:
            Updated AnalysisJob instance
            
        Raises:
            ValueError: If job not found
        """
        start_time = time.time()
        await self._ensure_connection()
        
        try:
            job = await self.get_analysis_job_by_id(job_id)
            if not job:
                raise ValueError(f"Job not found: {job_id}")
            
            job.status = JobStatus.SUCCESS
            job.progress = 100
            job.completed_at = datetime.utcnow()
            job.result = results
            
            await job.save()
            
            self.logger.info(f"Completed analysis job {job_id}")
            return job
            
        except Exception as e:
            self.logger.error(f"Failed to complete analysis job {job_id}: {e}")
            raise
        finally:
            self._track_operation(time.time() - start_time)
    
    async def fail_analysis_job(
        self,
        job_id: str,
        error_message: str,
        error_details: Optional[Dict[str, Any]] = None
    ) -> AnalysisJob:
        """
        Mark an analysis job as failed with error details.
        
        Args:
            job_id: Job ID to fail
            error_message: Error message
            error_details: Optional error details
            
        Returns:
            Updated AnalysisJob instance
            
        Raises:
            ValueError: If job not found
        """
        start_time = time.time()
        await self._ensure_connection()
        
        try:
            job = await self.get_analysis_job_by_id(job_id)
            if not job:
                raise ValueError(f"Job not found: {job_id}")
            
            job.status = JobStatus.FAILURE
            job.completed_at = datetime.utcnow()
            job.error = error_message
            job.error_details = error_details
            
            await job.save()
            
            self.logger.info(f"Failed analysis job {job_id}: {error_message}")
            return job
            
        except Exception as e:
            self.logger.error(f"Failed to fail analysis job {job_id}: {e}")
            raise
        finally:
            self._track_operation(time.time() - start_time)
    
    # Query Methods
    
    async def get_reports_by_status(self, status: ReportStatus, limit: int = 100) -> List[Report]:
        """
        Get reports filtered by status.
        
        Args:
            status: Report status to filter by
            limit: Maximum number of reports to return
            
        Returns:
            List of Report instances
        """
        start_time = time.time()
        await self._ensure_connection()
        
        try:
            reports = await Report.find_by_status(status, limit)
            return reports
            
        except Exception as e:
            self.logger.error(f"Failed to get reports by status {status}: {e}")
            return []
        finally:
            self._track_operation(time.time() - start_time)
    
    async def get_recent_reports(self, limit: int = 50) -> List[Report]:
        """
        Get recent reports ordered by creation time.
        
        Args:
            limit: Maximum number of reports to return
            
        Returns:
            List of Report instances
        """
        start_time = time.time()
        await self._ensure_connection()
        
        try:
            reports = await Report.find_recent(limit)
            return reports
            
        except Exception as e:
            self.logger.error(f"Failed to get recent reports: {e}")
            return []
        finally:
            self._track_operation(time.time() - start_time)
    
    async def get_reports_by_file_size_range(
        self,
        min_size: int,
        max_size: int,
        limit: int = 100
    ) -> List[Report]:
        """
        Get reports filtered by file size range.
        
        Args:
            min_size: Minimum file size in bytes
            max_size: Maximum file size in bytes
            limit: Maximum number of reports to return
            
        Returns:
            List of Report instances
        """
        start_time = time.time()
        await self._ensure_connection()
        
        try:
            reports = await Report.find(
                {"file_size": {"$gte": min_size, "$lte": max_size}}
            ).sort([("created_at", -1)]).limit(limit).to_list()
            
            return reports
            
        except Exception as e:
            self.logger.error(f"Failed to get reports by file size range: {e}")
            return []
        finally:
            self._track_operation(time.time() - start_time)
    
    async def get_analysis_performance_stats(self) -> Dict[str, Any]:
        """
        Get analysis performance statistics.
        
        Returns:
            Dictionary with performance statistics
        """
        start_time = time.time()
        await self._ensure_connection()
        
        try:
            # Aggregate completed reports
            pipeline = [
                {"$match": {"status": ReportStatus.COMPLETED.value, "processing_time": {"$exists": True}}},
                {"$group": {
                    "_id": None,
                    "total_completed_analyses": {"$sum": 1},
                    "avg_processing_time": {"$avg": "$processing_time"},
                    "min_processing_time": {"$min": "$processing_time"},
                    "max_processing_time": {"$max": "$processing_time"},
                    "avg_file_size": {"$avg": "$file_size"},
                    "total_bytes_processed": {"$sum": "$file_size"}
                }}
            ]
            
            result = await Report.aggregate(pipeline).to_list()
            
            if result:
                stats = result[0]
                stats.pop("_id", None)  # Remove the _id field
                return stats
            else:
                return {
                    "total_completed_analyses": 0,
                    "avg_processing_time": 0.0,
                    "min_processing_time": 0.0,
                    "max_processing_time": 0.0,
                    "avg_file_size": 0.0,
                    "total_bytes_processed": 0
                }
                
        except Exception as e:
            self.logger.error(f"Failed to get analysis performance stats: {e}")
            return {}
        finally:
            self._track_operation(time.time() - start_time)
    
    # Bulk Operations
    
    async def bulk_update_job_status(
        self,
        job_ids: List[str],
        new_status: JobStatus
    ) -> int:
        """
        Bulk update job statuses.
        
        Args:
            job_ids: List of job IDs to update
            new_status: New status to set
            
        Returns:
            Number of jobs updated
        """
        start_time = time.time()
        await self._ensure_connection()
        
        try:
            result = await AnalysisJob.find(
                {"job_id": {"$in": job_ids}}
            ).update_many({"$set": {"status": new_status.value}})
            
            self.logger.info(f"Bulk updated {result.modified_count} jobs to status {new_status}")
            return result.modified_count
            
        except Exception as e:
            self.logger.error(f"Failed to bulk update job statuses: {e}")
            return 0
        finally:
            self._track_operation(time.time() - start_time)
    
    async def cleanup_old_reports(self, days_old: int = 30) -> int:
        """
        Clean up old reports and associated jobs.
        
        Args:
            days_old: Age threshold in days
            
        Returns:
            Number of reports deleted
        """
        start_time = time.time()
        await self._ensure_connection()
        
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days_old)
            
            # Find old reports
            old_reports = await Report.find(
                {"created_at": {"$lt": cutoff_date}}
            ).to_list()
            
            deleted_count = 0
            
            for report in old_reports:
                # Delete associated jobs first
                await AnalysisJob.find({"report_id": report.id}).delete_many()
                
                # Delete the report
                await report.delete()
                deleted_count += 1
            
            self.logger.info(f"Cleaned up {deleted_count} old reports")
            return deleted_count
            
        except Exception as e:
            self.logger.error(f"Failed to cleanup old reports: {e}")
            return 0
        finally:
            self._track_operation(time.time() - start_time)
    
    # Utility Methods
    
    async def check_connection(self) -> bool:
        """
        Check if database connection is active.
        
        Returns:
            True if connected, False otherwise
        """
        try:
            await self._ensure_connection()
            
            # Try a simple operation
            await Report.find().limit(1).to_list()
            return True
            
        except Exception as e:
            self.logger.error(f"Database connection check failed: {e}")
            return False
    
    async def get_storage_metrics(self) -> Dict[str, Any]:
        """
        Get storage service performance metrics.
        
        Returns:
            Dictionary with storage metrics
        """
        uptime = (datetime.utcnow() - self._start_time).total_seconds()
        
        return {
            "operations_count": self._operation_count,
            "avg_operation_time": (
                self._total_operation_time / self._operation_count 
                if self._operation_count > 0 else 0.0
            ),
            "total_operation_time": self._total_operation_time,
            "uptime_seconds": uptime,
            "operations_per_second": self._operation_count / uptime if uptime > 0 else 0.0,
            "connection_pool_status": "active" if self._initialized else "inactive",
            "database_initialized": self._initialized
        } 
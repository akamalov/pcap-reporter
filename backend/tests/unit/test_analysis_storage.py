"""
Test suite for analysis results storage in MongoDB.

Tests the storage service that handles saving and retrieving
PCAP analysis results, managing analysis jobs, and report lifecycle.
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, List
from unittest.mock import AsyncMock, MagicMock, patch
from bson import ObjectId

# Import test helpers
from tests.fixtures.test_helpers import (
    create_sample_pcap_files, 
    get_test_pcap_path,
    create_mock_analysis_results,
    create_mock_triage_results
)

# Import models
from models.report import Report, ReportStatus
from models.analysis_job import AnalysisJob, JobStatus
from models.analysis_results import AnalysisResults, TrafficStats, PerformanceMetrics, NetworkIssue, SeverityLevel, IssueType

# Import the storage service we'll implement
from services.analysis_storage_service import AnalysisStorageService


class TestAnalysisStorageService:
    """Test suite for analysis storage service."""
    
    @pytest.fixture
    async def storage_service(self, mock_database):
        """Create storage service instance with mocked database."""
        with patch('services.analysis_storage_service.init_db') as mock_init, \
             patch('services.analysis_storage_service.get_database') as mock_get_db:
            
            mock_init.return_value = None
            mock_get_db.return_value = MagicMock()
            
            service = AnalysisStorageService()
            await service.initialize()
            return service
    
    @pytest.fixture
    async def sample_report_data(self):
        """Create sample report data for testing."""
        return {
            "job_id": "test-job-123",
            "original_filename": "test_traffic.pcap",
            "file_path": "/test/uploads/test_traffic.pcap",
            "file_size": 1024000,
            "file_hash": "abc123def456",
            "analysis_options": {
                "analysis_type": "comprehensive",
                "priority": "normal"
            }
        }
    
    @pytest.fixture
    async def sample_analysis_results(self):
        """Create sample analysis results for testing."""
        return create_mock_analysis_results()
    
    # Basic Storage Operations Tests
    
    @pytest.mark.asyncio
    async def test_storage_service_initialization(self, storage_service):
        """Test storage service initializes correctly."""
        assert storage_service is not None
        assert hasattr(storage_service, 'initialize')
        assert hasattr(storage_service, 'save_analysis_results')
        assert hasattr(storage_service, 'get_report_by_id')
        
    @pytest.mark.asyncio
    async def test_create_report_basic(self, storage_service, sample_report_data):
        """Test creating a basic report record."""
        report = await storage_service.create_report(**sample_report_data)
        
        assert report is not None
        assert isinstance(report, Report)
        assert report.job_id == sample_report_data["job_id"]
        assert report.original_filename == sample_report_data["original_filename"]
        assert report.status == ReportStatus.PENDING
        assert report.created_at is not None
        assert report.id is not None
        
    async def test_create_analysis_job(self, storage_service, sample_report_data):
        """Test creating an analysis job record."""
        # First create a report
        report = await storage_service.create_report(**sample_report_data)
        
        job_data = {
            "job_id": "celery-task-456",
            "report_id": report.id,
            "options": sample_report_data["analysis_options"],
            "estimated_completion": datetime.utcnow() + timedelta(minutes=30)
        }
        
        job = await storage_service.create_analysis_job(**job_data)
        
        assert job is not None
        assert isinstance(job, AnalysisJob)
        assert job.job_id == job_data["job_id"]
        assert job.report_id == report.id
        assert job.status == JobStatus.PENDING
        assert job.progress == 0
        
    async def test_save_analysis_results_complete(self, storage_service, sample_report_data, sample_analysis_results):
        """Test saving complete analysis results to a report."""
        # Create report first
        report = await storage_service.create_report(**sample_report_data)
        
        # Save analysis results
        updated_report = await storage_service.save_analysis_results(
            report_id=str(report.id),
            analysis_results=sample_analysis_results
        )
        
        assert updated_report.status == ReportStatus.COMPLETED
        assert updated_report.analysis_results is not None
        assert updated_report.completed_at is not None
        assert updated_report.processing_time is not None
        
        # Verify analysis results structure
        results = updated_report.analysis_results
        assert "traffic_stats" in results
        assert "performance_metrics" in results
        assert "protocol_stats" in results
        assert "issues" in results
        assert results["traffic_stats"]["total_packets"] > 0
        
    async def test_update_job_progress(self, storage_service, sample_report_data):
        """Test updating analysis job progress."""
        # Create report and job
        report = await storage_service.create_report(**sample_report_data)
        job = await storage_service.create_analysis_job(
            job_id="test-job-789",
            report_id=report.id,
            options={}
        )
        
        # Update progress
        updated_job = await storage_service.update_job_progress(
            job_id="test-job-789",
            progress=50,
            current_step="Processing packets..."
        )
        
        assert updated_job.progress == 50
        assert updated_job.current_step == "Processing packets..."
        assert updated_job.status == JobStatus.STARTED  # Should auto-update to started
        
    async def test_complete_analysis_job(self, storage_service, sample_report_data, sample_analysis_results):
        """Test completing an analysis job with results."""
        # Create report and job
        report = await storage_service.create_report(**sample_report_data)
        job = await storage_service.create_analysis_job(
            job_id="test-job-complete",
            report_id=report.id,
            options={}
        )
        
        # Complete the job
        completed_job = await storage_service.complete_analysis_job(
            job_id="test-job-complete",
            results=sample_analysis_results.dict()
        )
        
        assert completed_job.status == JobStatus.SUCCESS
        assert completed_job.progress == 100
        assert completed_job.completed_at is not None
        assert completed_job.result is not None
        
    async def test_fail_analysis_job(self, storage_service, sample_report_data):
        """Test failing an analysis job with error details."""
        # Create report and job
        report = await storage_service.create_report(**sample_report_data)
        job = await storage_service.create_analysis_job(
            job_id="test-job-fail",
            report_id=report.id,
            options={}
        )
        
        error_details = {
            "error_type": "FileCorrupted",
            "error_message": "PCAP file appears to be corrupted",
            "traceback": "Mock traceback here..."
        }
        
        # Fail the job
        failed_job = await storage_service.fail_analysis_job(
            job_id="test-job-fail",
            error_message="Analysis failed due to corrupted file",
            error_details=error_details
        )
        
        assert failed_job.status == JobStatus.FAILURE
        assert failed_job.error == "Analysis failed due to corrupted file"
        assert failed_job.error_details == error_details
        assert failed_job.completed_at is not None
        
    # Query and Retrieval Tests
    
    async def test_get_report_by_id(self, storage_service, sample_report_data):
        """Test retrieving a report by ID."""
        # Create report
        original_report = await storage_service.create_report(**sample_report_data)
        
        # Retrieve by ID
        retrieved_report = await storage_service.get_report_by_id(str(original_report.id))
        
        assert retrieved_report is not None
        assert retrieved_report.id == original_report.id
        assert retrieved_report.job_id == original_report.job_id
        assert retrieved_report.original_filename == original_report.original_filename
        
    async def test_get_report_by_job_id(self, storage_service, sample_report_data):
        """Test retrieving a report by job ID."""
        # Create report
        original_report = await storage_service.create_report(**sample_report_data)
        
        # Retrieve by job ID
        retrieved_report = await storage_service.get_report_by_job_id(sample_report_data["job_id"])
        
        assert retrieved_report is not None
        assert retrieved_report.job_id == sample_report_data["job_id"]
        assert retrieved_report.id == original_report.id
        
    async def test_get_analysis_job_by_id(self, storage_service, sample_report_data):
        """Test retrieving an analysis job by job ID."""
        # Create report and job
        report = await storage_service.create_report(**sample_report_data)
        original_job = await storage_service.create_analysis_job(
            job_id="test-retrieve-job",
            report_id=report.id,
            options={}
        )
        
        # Retrieve job
        retrieved_job = await storage_service.get_analysis_job_by_id("test-retrieve-job")
        
        assert retrieved_job is not None
        assert retrieved_job.job_id == "test-retrieve-job"
        assert retrieved_job.report_id == report.id
        
    async def test_get_reports_by_status(self, storage_service, sample_report_data):
        """Test retrieving reports filtered by status."""
        # Create multiple reports with different statuses
        report1 = await storage_service.create_report(**{**sample_report_data, "job_id": "job1"})
        report2 = await storage_service.create_report(**{**sample_report_data, "job_id": "job2"})
        
        # Update one to completed
        await storage_service.update_report_status(str(report2.id), ReportStatus.COMPLETED)
        
        # Query by status
        pending_reports = await storage_service.get_reports_by_status(ReportStatus.PENDING)
        completed_reports = await storage_service.get_reports_by_status(ReportStatus.COMPLETED)
        
        assert len(pending_reports) >= 1
        assert len(completed_reports) >= 1
        assert any(r.id == report1.id for r in pending_reports)
        assert any(r.id == report2.id for r in completed_reports)
        
    async def test_get_recent_reports(self, storage_service, sample_report_data):
        """Test retrieving recent reports with limit."""
        # Create multiple reports
        reports = []
        for i in range(5):
            report_data = {**sample_report_data, "job_id": f"job-{i}"}
            report = await storage_service.create_report(**report_data)
            reports.append(report)
        
        # Get recent reports
        recent_reports = await storage_service.get_recent_reports(limit=3)
        
        assert len(recent_reports) <= 3
        assert all(isinstance(r, Report) for r in recent_reports)
        # Should be ordered by creation time (most recent first)
        if len(recent_reports) > 1:
            assert recent_reports[0].created_at >= recent_reports[1].created_at
            
    # Advanced Query Tests
    
    async def test_get_reports_by_file_size_range(self, storage_service, sample_report_data):
        """Test querying reports by file size range."""
        # Create reports with different file sizes
        small_report = await storage_service.create_report(**{
            **sample_report_data, 
            "job_id": "small", 
            "file_size": 50000
        })
        large_report = await storage_service.create_report(**{
            **sample_report_data, 
            "job_id": "large", 
            "file_size": 5000000
        })
        
        # Query by size range
        large_files = await storage_service.get_reports_by_file_size_range(
            min_size=1000000,
            max_size=10000000
        )
        
        assert len(large_files) >= 1
        assert any(r.id == large_report.id for r in large_files)
        assert not any(r.id == small_report.id for r in large_files)
        
    async def test_get_analysis_performance_stats(self, storage_service, sample_report_data, sample_analysis_results):
        """Test retrieving analysis performance statistics."""
        # Create completed reports with different processing times
        for i, processing_time in enumerate([10.5, 25.3, 45.1]):
            report = await storage_service.create_report(**{
                **sample_report_data, 
                "job_id": f"perf-job-{i}"
            })
            
            # Mock processing time in results
            results_with_time = sample_analysis_results.copy()
            results_with_time.processing_time = processing_time
            
            await storage_service.save_analysis_results(
                report_id=str(report.id),
                analysis_results=results_with_time
            )
        
        # Get performance stats
        stats = await storage_service.get_analysis_performance_stats()
        
        assert "avg_processing_time" in stats
        assert "total_completed_analyses" in stats
        assert "avg_file_size" in stats
        assert stats["total_completed_analyses"] >= 3
        assert stats["avg_processing_time"] > 0
        
    # Error Handling and Edge Cases
    
    async def test_get_nonexistent_report(self, storage_service):
        """Test retrieving a non-existent report returns None."""
        fake_id = str(ObjectId())
        report = await storage_service.get_report_by_id(fake_id)
        assert report is None
        
    async def test_get_nonexistent_job(self, storage_service):
        """Test retrieving a non-existent job returns None."""
        job = await storage_service.get_analysis_job_by_id("nonexistent-job-id")
        assert job is None
        
    async def test_update_nonexistent_job_progress(self, storage_service):
        """Test updating progress for non-existent job raises appropriate error."""
        with pytest.raises(ValueError, match="Job not found"):
            await storage_service.update_job_progress(
                job_id="nonexistent-job",
                progress=50
            )
            
    async def test_save_results_to_nonexistent_report(self, storage_service, sample_analysis_results):
        """Test saving results to non-existent report raises appropriate error."""
        fake_id = str(ObjectId())
        with pytest.raises(ValueError, match="Report not found"):
            await storage_service.save_analysis_results(
                report_id=fake_id,
                analysis_results=sample_analysis_results
            )
            
    async def test_duplicate_job_id_handling(self, storage_service, sample_report_data):
        """Test handling of duplicate job IDs."""
        # Create first report and job
        report1 = await storage_service.create_report(**sample_report_data)
        job1 = await storage_service.create_analysis_job(
            job_id="duplicate-job-id",
            report_id=report1.id,
            options={}
        )
        
        # Try to create another job with same ID
        report2 = await storage_service.create_report(**{
            **sample_report_data, 
            "job_id": "different-job"
        })
        
        with pytest.raises(ValueError, match="Job ID already exists"):
            await storage_service.create_analysis_job(
                job_id="duplicate-job-id",
                report_id=report2.id,
                options={}
            )
    
    # Bulk Operations Tests
    
    async def test_bulk_update_job_status(self, storage_service, sample_report_data):
        """Test bulk updating job statuses."""
        # Create multiple jobs
        jobs = []
        for i in range(3):
            report = await storage_service.create_report(**{
                **sample_report_data, 
                "job_id": f"bulk-report-{i}"
            })
            job = await storage_service.create_analysis_job(
                job_id=f"bulk-job-{i}",
                report_id=report.id,
                options={}
            )
            jobs.append(job)
        
        job_ids = [f"bulk-job-{i}" for i in range(3)]
        
        # Bulk update to started status
        updated_count = await storage_service.bulk_update_job_status(
            job_ids=job_ids,
            new_status=JobStatus.STARTED
        )
        
        assert updated_count == 3
        
        # Verify updates
        for job_id in job_ids:
            job = await storage_service.get_analysis_job_by_id(job_id)
            assert job.status == JobStatus.STARTED
    
    async def test_cleanup_old_reports(self, storage_service, sample_report_data):
        """Test cleanup of old reports and associated jobs."""
        # Create old reports (simulate by setting created_at to past)
        old_date = datetime.utcnow() - timedelta(days=30)
        
        # This would require mocking the created_at field or using database operations
        # For now, test the interface exists
        assert hasattr(storage_service, 'cleanup_old_reports')
        
        # Test with 0 days to ensure no recent reports are deleted
        deleted_count = await storage_service.cleanup_old_reports(days_old=0)
        assert deleted_count >= 0  # Should not error
        
    # Integration with Analysis Results Tests
    
    async def test_storage_with_triage_results(self, storage_service, sample_report_data):
        """Test storing triage analysis results."""
        triage_results = create_mock_triage_results()
        
        # Create report
        report = await storage_service.create_report(**sample_report_data)
        
        # Save triage results
        updated_report = await storage_service.save_triage_results(
            report_id=str(report.id),
            triage_results=triage_results
        )
        
        assert updated_report.analysis_results is not None
        assert "triage_summary" in updated_report.analysis_results
        assert updated_report.status == ReportStatus.PROCESSING  # Partial completion
        
    async def test_storage_with_deep_inspection_results(self, storage_service, sample_report_data):
        """Test storing deep inspection results separately."""
        # Create report with triage results first
        report = await storage_service.create_report(**sample_report_data)
        triage_results = create_mock_triage_results()
        await storage_service.save_triage_results(str(report.id), triage_results)
        
        # Add deep inspection results
        deep_results = {
            "http_analysis": {"total_requests": 150, "avg_response_time": 0.25},
            "dns_analysis": {"total_queries": 45, "success_rate": 0.95},
            "tcp_analysis": {"total_streams": 20, "retransmission_rate": 0.02}
        }
        
        updated_report = await storage_service.append_deep_inspection_results(
            report_id=str(report.id),
            deep_results=deep_results
        )
        
        assert "deep_inspection" in updated_report.analysis_results
        assert updated_report.analysis_results["deep_inspection"]["http_analysis"]["total_requests"] == 150
        
    async def test_concurrent_storage_operations(self, storage_service, sample_report_data):
        """Test concurrent storage operations don't interfere."""
        # Create multiple reports concurrently
        tasks = []
        for i in range(5):
            report_data = {**sample_report_data, "job_id": f"concurrent-{i}"}
            task = storage_service.create_report(**report_data)
            tasks.append(task)
        
        # Execute concurrently
        reports = await asyncio.gather(*tasks)
        
        assert len(reports) == 5
        assert all(isinstance(r, Report) for r in reports)
        assert len(set(r.id for r in reports)) == 5  # All unique IDs
        
    # Database Connection and Transaction Tests
    
    async def test_storage_service_connection_handling(self, storage_service):
        """Test storage service handles database connections properly."""
        # Test that service can handle connection issues gracefully
        assert hasattr(storage_service, '_ensure_connection')
        
        # Test connection status
        is_connected = await storage_service.check_connection()
        assert isinstance(is_connected, bool)
        
    async def test_transaction_rollback_on_error(self, storage_service, sample_report_data):
        """Test that failed operations don't leave partial data."""
        # This test would need to mock database errors to verify rollback behavior
        # For now, ensure the interface exists for transaction handling
        assert hasattr(storage_service, '_execute_in_transaction')
        
        # Test normal operation completes successfully
        report = await storage_service.create_report(**sample_report_data)
        assert report is not None
        
    async def test_storage_service_performance_monitoring(self, storage_service):
        """Test that storage service provides performance metrics."""
        # Test performance monitoring capabilities
        metrics = await storage_service.get_storage_metrics()
        
        assert isinstance(metrics, dict)
        assert "operations_count" in metrics
        assert "avg_operation_time" in metrics
        assert "connection_pool_status" in metrics 
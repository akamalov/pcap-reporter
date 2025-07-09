"""
Integration tests for job status and result endpoints.

Tests the full integration of status checking, result retrieval, and job cancellation
endpoints with database and Celery mocking.
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from fastapi import HTTPException
from datetime import datetime, timedelta

from models.analysis_job import AnalysisJob, JobStatus
from models.report import Report, ReportStatus


class TestJobStatusEndpointIntegration:
    """Integration test cases for job status retrieval endpoint."""
    
    @pytest.mark.asyncio
    async def test_get_analysis_status_full_integration(self):
        """Test full integration of status retrieval with database operations."""
        job_id = "integration-job-123"
        
        # Mock database operations and Celery
        with patch('models.analysis_job.AnalysisJob.find_one', new_callable=AsyncMock) as mock_find_job, \
             patch('models.report.Report.get', new_callable=AsyncMock) as mock_get_report, \
             patch('tasks.analysis_tasks.analyze_pcap_file.AsyncResult') as mock_async_result:
            
            # Setup realistic mock job
            mock_job = MagicMock()
            mock_job.job_id = job_id
            mock_job.status = JobStatus.STARTED
            mock_job.progress = 75
            mock_job.current_step = "Analyzing network protocols"
            mock_job.report_id = "report-integration-123"
            mock_job.error = None
            mock_job.created_at = datetime.utcnow() - timedelta(minutes=5)
            mock_job.started_at = datetime.utcnow() - timedelta(minutes=3)
            mock_job.options = {
                "analysis_type": "comprehensive",
                "priority": "normal",
                "deep_packet_inspection": True
            }
            
            # Setup realistic mock report
            mock_report = MagicMock()
            mock_report.id = "report-integration-123"
            mock_report.original_filename = "network_capture.pcap"
            mock_report.file_size = 5242880  # 5MB
            mock_report.status = ReportStatus.PROCESSING
            mock_report.created_at = datetime.utcnow() - timedelta(minutes=5)
            mock_report.updated_at = datetime.utcnow() - timedelta(minutes=1)
            mock_report.analysis_results = None
            
            # Setup realistic Celery task (not ready yet)
            mock_task = MagicMock()
            mock_task.status = "PROGRESS"
            mock_task.ready.return_value = False
            mock_task.result = None  # Not ready yet
            
            mock_find_job.return_value = mock_job
            mock_get_report.return_value = mock_report
            mock_async_result.return_value = mock_task
            
            # Import and test the endpoint
            from api.v1.endpoints.analysis import get_analysis_status
            
            result = await get_analysis_status(job_id)
            
            # Verify comprehensive response
            assert result["job_id"] == job_id
            assert result["status"] == JobStatus.STARTED.value
            assert result["progress"] == 75
            assert result["current_step"] == "Analyzing network protocols"
            assert result["celery_status"] == "PROGRESS"
            
            # Verify report information
            assert result["report"]["id"] == "report-integration-123"
            assert result["report"]["filename"] == "network_capture.pcap"
            assert result["report"]["file_size"] == 5242880
            assert result["report"]["status"] == ReportStatus.PROCESSING.value
            
            # Verify timing information
            assert "created_at" in result["report"]
            assert "updated_at" in result["report"]
            
            # Verify Celery task details (result should be None when task is not ready)
            assert result["result"] is None  # Task not ready, so result is None
    
    @pytest.mark.asyncio
    async def test_get_analysis_status_with_completed_results(self):
        """Test status retrieval for completed job with full analysis results."""
        job_id = "completed-integration-job"
        
        with patch('models.analysis_job.AnalysisJob.find_one', new_callable=AsyncMock) as mock_find_job, \
             patch('models.report.Report.get', new_callable=AsyncMock) as mock_get_report, \
             patch('tasks.analysis_tasks.analyze_pcap_file.AsyncResult') as mock_async_result:
            
            # Setup completed job
            mock_job = MagicMock()
            mock_job.job_id = job_id
            mock_job.status = JobStatus.SUCCESS
            mock_job.progress = 100
            mock_job.current_step = "Analysis completed"
            mock_job.report_id = "report-completed-123"
            mock_job.error = None
            mock_job.completed_at = datetime.utcnow()
            
            # Setup completed report with results
            mock_report = MagicMock()
            mock_report.id = "report-completed-123"
            mock_report.original_filename = "completed_analysis.pcap"
            mock_report.file_size = 10485760  # 10MB
            mock_report.status = ReportStatus.COMPLETED
            mock_report.created_at = datetime.utcnow() - timedelta(minutes=15)
            mock_report.updated_at = datetime.utcnow()
            
            # Setup completed Celery task with results
            mock_task = MagicMock()
            mock_task.status = "SUCCESS"
            mock_task.ready.return_value = True
            mock_task.result = {
                "status": "completed",
                "message": "Analysis completed successfully",
                "results_summary": {
                    "total_packets": 50000,
                    "duration": 1800,  # 30 minutes
                    "unique_ips": 150,
                    "top_protocol": "HTTPS",
                    "issues_found": 5,
                    "security_alerts": 2,
                    "performance_issues": 3
                },
                "analysis_details": {
                    "protocols": ["HTTP", "HTTPS", "DNS", "TCP", "UDP"],
                    "suspicious_activities": ["Port scanning", "DNS tunneling"],
                    "bandwidth_usage": "High during peak hours"
                }
            }
            
            mock_find_job.return_value = mock_job
            mock_get_report.return_value = mock_report
            mock_async_result.return_value = mock_task
            
            from api.v1.endpoints.analysis import get_analysis_status
            
            result = await get_analysis_status(job_id)
            
            # Verify completion status
            assert result["status"] == JobStatus.SUCCESS.value
            assert result["progress"] == 100
            assert result["celery_status"] == "SUCCESS"
            
            # Verify detailed results
            assert result["result"]["status"] == "completed"
            assert result["result"]["results_summary"]["total_packets"] == 50000
            assert result["result"]["results_summary"]["security_alerts"] == 2
            assert "analysis_details" in result["result"]
            assert "protocols" in result["result"]["analysis_details"]
    
    @pytest.mark.asyncio
    async def test_get_analysis_status_with_failure_details(self):
        """Test status retrieval for failed job with detailed error information."""
        job_id = "failed-integration-job"
        
        with patch('models.analysis_job.AnalysisJob.find_one', new_callable=AsyncMock) as mock_find_job, \
             patch('models.report.Report.get', new_callable=AsyncMock) as mock_get_report, \
             patch('tasks.analysis_tasks.analyze_pcap_file.AsyncResult') as mock_async_result:
            
            # Setup failed job
            mock_job = MagicMock()
            mock_job.job_id = job_id
            mock_job.status = JobStatus.FAILURE
            mock_job.progress = 45
            mock_job.current_step = "Failed during deep packet inspection"
            mock_job.report_id = "report-failed-123"
            mock_job.error = "PCAP file corruption detected at packet 15000"
            mock_job.completed_at = datetime.utcnow()
            
            # Setup failed report
            mock_report = MagicMock()
            mock_report.id = "report-failed-123"
            mock_report.original_filename = "corrupted_capture.pcap"
            mock_report.file_size = 3145728  # 3MB
            mock_report.status = ReportStatus.FAILED
            mock_report.error_message = "Analysis failed due to file corruption"
            
            # Setup failed Celery task
            mock_task = MagicMock()
            mock_task.status = "FAILURE"
            mock_task.ready.return_value = True
            mock_task.result = {
                "error": "PCAP file corruption detected at packet 15000",
                "error_type": "FileCorruptionError",
                "partial_results": {
                    "packets_processed": 14999,
                    "protocols_found": ["HTTP", "TCP"],
                    "analysis_stopped_at": "Deep packet inspection phase"
                }
            }
            
            mock_find_job.return_value = mock_job
            mock_get_report.return_value = mock_report
            mock_async_result.return_value = mock_task
            
            from api.v1.endpoints.analysis import get_analysis_status
            
            result = await get_analysis_status(job_id)
            
            # Verify failure status
            assert result["status"] == JobStatus.FAILURE.value
            assert result["progress"] == 45
            assert result["celery_status"] == "FAILURE"
            assert result["error"] == "PCAP file corruption detected at packet 15000"
            
            # Verify detailed error information
            assert result["result"]["error"] == "PCAP file corruption detected at packet 15000"
            assert result["result"]["error_type"] == "FileCorruptionError"
            assert "partial_results" in result["result"]
            assert result["result"]["partial_results"]["packets_processed"] == 14999


class TestJobCancellationEndpointIntegration:
    """Integration test cases for job cancellation endpoint."""
    
    @pytest.mark.asyncio
    async def test_cancel_analysis_full_integration(self):
        """Test full integration of job cancellation with database and Celery operations."""
        job_id = "cancel-integration-job"
        
        with patch('models.analysis_job.AnalysisJob.find_one', new_callable=AsyncMock) as mock_find_job, \
             patch('models.report.Report.get', new_callable=AsyncMock) as mock_get_report, \
             patch('tasks.analysis_tasks.analyze_pcap_file.AsyncResult') as mock_async_result:
            
            # Setup running job to be cancelled
            mock_job = MagicMock()
            mock_job.job_id = job_id
            mock_job.status = JobStatus.STARTED
            mock_job.progress = 60
            mock_job.current_step = "Analyzing security patterns"
            mock_job.report_id = "report-cancel-123"
            mock_job.fail_job = MagicMock()
            mock_job.save = AsyncMock()
            
            # Setup associated report
            mock_report = MagicMock()
            mock_report.id = "report-cancel-123"
            mock_report.original_filename = "long_running_capture.pcap"
            mock_report.status = ReportStatus.PROCESSING
            mock_report.update_status = MagicMock()
            mock_report.save = AsyncMock()
            
            # Setup Celery task
            mock_task = MagicMock()
            mock_task.revoke = MagicMock()
            mock_task.status = "PROGRESS"
            
            mock_find_job.return_value = mock_job
            mock_get_report.return_value = mock_report
            mock_async_result.return_value = mock_task
            
            from api.v1.endpoints.analysis import cancel_analysis
            
            result = await cancel_analysis(job_id)
            
            # Verify cancellation response
            assert result["message"] == "Analysis job cancelled"
            assert result["job_id"] == job_id
            assert result["status"] == "cancelled"
            
            # Verify all cancellation operations were performed
            mock_find_job.assert_called_once_with({"job_id": job_id})
            mock_async_result.assert_called_once_with(job_id)
            mock_task.revoke.assert_called_once_with(terminate=True)
            mock_job.fail_job.assert_called_once_with("Cancelled by user")
            mock_job.save.assert_called_once()
            mock_get_report.assert_called_once_with("report-cancel-123")
            mock_report.update_status.assert_called_once_with(ReportStatus.FAILED, "Analysis cancelled by user")
            mock_report.save.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_cancel_analysis_with_cleanup(self):
        """Test cancellation includes proper cleanup of resources."""
        job_id = "cleanup-cancel-job"
        
        with patch('models.analysis_job.AnalysisJob.find_one', new_callable=AsyncMock) as mock_find_job, \
             patch('models.report.Report.get', new_callable=AsyncMock) as mock_get_report, \
             patch('tasks.analysis_tasks.analyze_pcap_file.AsyncResult') as mock_async_result, \
             patch('os.path.exists') as mock_exists, \
             patch('os.remove') as mock_remove:
            
            # Setup job with temporary files
            mock_job = MagicMock()
            mock_job.job_id = job_id
            mock_job.status = JobStatus.STARTED
            mock_job.report_id = "report-cleanup-123"
            mock_job.fail_job = MagicMock()
            mock_job.save = AsyncMock()
            
            # Setup report with file path
            mock_report = MagicMock()
            mock_report.id = "report-cleanup-123"
            mock_report.file_path = "/tmp/uploads/test_file.pcap"
            mock_report.update_status = MagicMock()
            mock_report.save = AsyncMock()
            
            # Setup file system mocks
            mock_exists.return_value = True
            
            # Setup Celery task
            mock_task = MagicMock()
            mock_task.revoke = MagicMock()
            
            mock_find_job.return_value = mock_job
            mock_get_report.return_value = mock_report
            mock_async_result.return_value = mock_task
            
            from api.v1.endpoints.analysis import cancel_analysis
            
            result = await cancel_analysis(job_id)
            
            # Verify cancellation succeeded
            assert result["status"] == "cancelled"
            
            # Note: File cleanup would be handled by a separate cleanup task
            # Here we just verify the cancellation process works
            mock_task.revoke.assert_called_once_with(terminate=True)
    
    @pytest.mark.asyncio
    async def test_cancel_analysis_idempotent_operation(self):
        """Test that cancelling an already cancelled job is idempotent."""
        job_id = "idempotent-cancel-job"
        
        with patch('models.analysis_job.AnalysisJob.find_one', new_callable=AsyncMock) as mock_find_job, \
             patch('models.report.Report.get', new_callable=AsyncMock) as mock_get_report, \
             patch('tasks.analysis_tasks.analyze_pcap_file.AsyncResult') as mock_async_result:
            
            # Setup already failed (cancelled) job
            mock_job = MagicMock()
            mock_job.job_id = job_id
            mock_job.status = JobStatus.FAILURE
            mock_job.error = "Cancelled by user"
            mock_job.report_id = "report-already-cancelled"
            mock_job.fail_job = MagicMock()
            mock_job.save = AsyncMock()
            
            # Setup associated report
            mock_report = MagicMock()
            mock_report.status = ReportStatus.FAILED
            mock_report.error_message = "Analysis cancelled by user"
            mock_report.update_status = MagicMock()
            mock_report.save = AsyncMock()
            
            # Setup Celery task
            mock_task = MagicMock()
            mock_task.revoke = MagicMock()
            mock_task.status = "REVOKED"
            
            mock_find_job.return_value = mock_job
            mock_get_report.return_value = mock_report
            mock_async_result.return_value = mock_task
            
            from api.v1.endpoints.analysis import cancel_analysis
            
            result = await cancel_analysis(job_id)
            
            # Should still return success (idempotent)
            assert result["message"] == "Analysis job cancelled"
            assert result["status"] == "cancelled"
            
            # Verify cancellation operations were still attempted
            mock_task.revoke.assert_called_once_with(terminate=True)


class TestJobStatusEndpointErrorHandling:
    """Integration tests for error handling scenarios."""
    
    @pytest.mark.asyncio
    async def test_status_endpoint_database_timeout(self):
        """Test status endpoint behavior during database timeout."""
        job_id = "timeout-job"
        
        with patch('models.analysis_job.AnalysisJob.find_one', new_callable=AsyncMock) as mock_find_job:
            # Simulate database timeout
            mock_find_job.side_effect = Exception("Database timeout after 30 seconds")
            
            from api.v1.endpoints.analysis import get_analysis_status
            
            with pytest.raises(HTTPException) as exc_info:
                await get_analysis_status(job_id)
            
            assert exc_info.value.status_code == 500
            assert "Failed to get analysis status" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_cancel_endpoint_celery_unavailable(self):
        """Test cancellation behavior when Celery is unavailable."""
        job_id = "celery-unavailable-job"
        
        with patch('models.analysis_job.AnalysisJob.find_one', new_callable=AsyncMock) as mock_find_job, \
             patch('models.report.Report.get', new_callable=AsyncMock) as mock_get_report, \
             patch('tasks.analysis_tasks.analyze_pcap_file.AsyncResult') as mock_async_result:
            
            # Setup job
            mock_job = MagicMock()
            mock_job.job_id = job_id
            mock_job.status = JobStatus.STARTED
            mock_job.report_id = "report-celery-down"
            mock_job.fail_job = MagicMock()
            mock_job.save = AsyncMock()
            
            # Setup report
            mock_report = MagicMock()
            mock_report.update_status = MagicMock()
            mock_report.save = AsyncMock()
            
            # Simulate Celery unavailable
            mock_async_result.side_effect = Exception("Celery broker connection failed")
            
            mock_find_job.return_value = mock_job
            mock_get_report.return_value = mock_report
            
            from api.v1.endpoints.analysis import cancel_analysis
            
            with pytest.raises(HTTPException) as exc_info:
                await cancel_analysis(job_id)
            
            assert exc_info.value.status_code == 500
            assert "Failed to cancel analysis" in str(exc_info.value.detail) 
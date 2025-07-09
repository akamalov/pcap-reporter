"""
Unit tests for job status and result endpoints.

Tests the status checking, result retrieval, and job cancellation endpoints
using Test-Driven Development principles.
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from fastapi import HTTPException
from datetime import datetime, timedelta

from models.analysis_job import AnalysisJob, JobStatus
from models.report import Report, ReportStatus


class TestJobStatusEndpoint:
    """Test cases for job status retrieval endpoint."""
    
    @pytest.mark.asyncio
    async def test_get_analysis_status_success(self):
        """Test successful status retrieval for existing job."""
        job_id = "test-job-123"
        
        # Mock analysis job
        mock_job = MagicMock()
        mock_job.job_id = job_id
        mock_job.status = JobStatus.STARTED
        mock_job.progress = 45
        mock_job.current_step = "Analyzing packets"
        mock_job.report_id = "report-456"
        mock_job.error = None
        
        # Mock report
        mock_report = MagicMock()
        mock_report.id = "report-456"
        mock_report.original_filename = "test.pcap"
        mock_report.file_size = 1024000
        mock_report.status = ReportStatus.PROCESSING
        mock_report.created_at = datetime.utcnow()
        mock_report.updated_at = datetime.utcnow()
        
        # Mock Celery task
        mock_task = MagicMock()
        mock_task.status = "PROGRESS"
        mock_task.ready.return_value = False
        mock_task.result = {"progress": 45, "message": "Analyzing packets"}
        
        with patch('models.analysis_job.AnalysisJob.find_one', new_callable=AsyncMock) as mock_find_job, \
             patch('models.report.Report.get', new_callable=AsyncMock) as mock_get_report, \
             patch('tasks.analysis_tasks.analyze_pcap_file.AsyncResult') as mock_async_result:
            
            mock_find_job.return_value = mock_job
            mock_get_report.return_value = mock_report
            mock_async_result.return_value = mock_task
            
            from api.v1.endpoints.analysis import get_analysis_status
            
            result = await get_analysis_status(job_id)
            
            # Verify response structure
            assert result["job_id"] == job_id
            assert result["status"] == JobStatus.STARTED.value
            assert result["progress"] == 45
            assert result["current_step"] == "Analyzing packets"
            assert result["celery_status"] == "PROGRESS"
            assert result["report"]["id"] == "report-456"
            assert result["report"]["filename"] == "test.pcap"
            assert result["report"]["file_size"] == 1024000
            assert result["report"]["status"] == ReportStatus.PROCESSING.value
            assert "created_at" in result["report"]
            assert "updated_at" in result["report"]
            
            # Verify mocks were called
            mock_find_job.assert_called_once_with({"job_id": job_id})
            mock_get_report.assert_called_once_with("report-456")
            mock_async_result.assert_called_once_with(job_id)
    
    @pytest.mark.asyncio
    async def test_get_analysis_status_completed_job(self):
        """Test status retrieval for completed job with results."""
        job_id = "completed-job-789"
        
        # Mock completed analysis job
        mock_job = MagicMock()
        mock_job.job_id = job_id
        mock_job.status = JobStatus.SUCCESS
        mock_job.progress = 100
        mock_job.current_step = "Analysis complete"
        mock_job.report_id = "report-789"
        mock_job.error = None
        
        # Mock completed report
        mock_report = MagicMock()
        mock_report.id = "report-789"
        mock_report.original_filename = "completed.pcap"
        mock_report.file_size = 2048000
        mock_report.status = ReportStatus.COMPLETED
        mock_report.created_at = datetime.utcnow() - timedelta(minutes=10)
        mock_report.updated_at = datetime.utcnow()
        
        # Mock completed Celery task
        mock_task = MagicMock()
        mock_task.status = "SUCCESS"
        mock_task.ready.return_value = True
        mock_task.result = {
            "status": "completed",
            "message": "Analysis completed successfully",
            "results_summary": {
                "total_packets": 15000,
                "duration": 300,
                "unique_ips": 50,
                "top_protocol": "HTTP",
                "issues_found": 3,
                "security_alerts": 1
            }
        }
        
        with patch('models.analysis_job.AnalysisJob.find_one', new_callable=AsyncMock) as mock_find_job, \
             patch('models.report.Report.get', new_callable=AsyncMock) as mock_get_report, \
             patch('tasks.analysis_tasks.analyze_pcap_file.AsyncResult') as mock_async_result:
            
            mock_find_job.return_value = mock_job
            mock_get_report.return_value = mock_report
            mock_async_result.return_value = mock_task
            
            from api.v1.endpoints.analysis import get_analysis_status
            
            result = await get_analysis_status(job_id)
            
            # Verify completion status
            assert result["status"] == JobStatus.SUCCESS.value
            assert result["progress"] == 100
            assert result["celery_status"] == "SUCCESS"
            assert result["result"] is not None
            assert result["result"]["status"] == "completed"
            assert result["result"]["results_summary"]["total_packets"] == 15000
    
    @pytest.mark.asyncio
    async def test_get_analysis_status_failed_job(self):
        """Test status retrieval for failed job with error details."""
        job_id = "failed-job-456"
        
        # Mock failed analysis job
        mock_job = MagicMock()
        mock_job.job_id = job_id
        mock_job.status = JobStatus.FAILURE
        mock_job.progress = 30
        mock_job.current_step = "Failed during packet analysis"
        mock_job.report_id = "report-456"
        mock_job.error = "File corruption detected"
        
        # Mock failed report
        mock_report = MagicMock()
        mock_report.id = "report-456"
        mock_report.original_filename = "corrupted.pcap"
        mock_report.file_size = 512000
        mock_report.status = ReportStatus.FAILED
        mock_report.created_at = datetime.utcnow() - timedelta(minutes=5)
        mock_report.updated_at = datetime.utcnow()
        
        # Mock failed Celery task
        mock_task = MagicMock()
        mock_task.status = "FAILURE"
        mock_task.ready.return_value = True
        mock_task.result = {"error": "File corruption detected"}
        
        with patch('models.analysis_job.AnalysisJob.find_one', new_callable=AsyncMock) as mock_find_job, \
             patch('models.report.Report.get', new_callable=AsyncMock) as mock_get_report, \
             patch('tasks.analysis_tasks.analyze_pcap_file.AsyncResult') as mock_async_result:
            
            mock_find_job.return_value = mock_job
            mock_get_report.return_value = mock_report
            mock_async_result.return_value = mock_task
            
            from api.v1.endpoints.analysis import get_analysis_status
            
            result = await get_analysis_status(job_id)
            
            # Verify failure status
            assert result["status"] == JobStatus.FAILURE.value
            assert result["progress"] == 30
            assert result["celery_status"] == "FAILURE"
            assert result["error"] == "File corruption detected"
            assert result["result"]["error"] == "File corruption detected"
    
    @pytest.mark.asyncio
    async def test_get_analysis_status_job_not_found(self):
        """Test status retrieval for non-existent job."""
        job_id = "nonexistent-job-999"
        
        with patch('models.analysis_job.AnalysisJob.find_one', new_callable=AsyncMock) as mock_find_job:
            mock_find_job.return_value = None
            
            from api.v1.endpoints.analysis import get_analysis_status
            
            with pytest.raises(HTTPException) as exc_info:
                await get_analysis_status(job_id)
            
            assert exc_info.value.status_code == 404
            assert "Analysis job not found" in str(exc_info.value.detail)
            
            mock_find_job.assert_called_once_with({"job_id": job_id})
    
    @pytest.mark.asyncio
    async def test_get_analysis_status_report_not_found(self):
        """Test status retrieval when associated report is missing."""
        job_id = "orphaned-job-111"
        
        # Mock analysis job without report
        mock_job = MagicMock()
        mock_job.job_id = job_id
        mock_job.status = JobStatus.PENDING
        mock_job.report_id = "missing-report-111"
        
        with patch('models.analysis_job.AnalysisJob.find_one', new_callable=AsyncMock) as mock_find_job, \
             patch('models.report.Report.get', new_callable=AsyncMock) as mock_get_report:
            
            mock_find_job.return_value = mock_job
            mock_get_report.return_value = None
            
            from api.v1.endpoints.analysis import get_analysis_status
            
            with pytest.raises(HTTPException) as exc_info:
                await get_analysis_status(job_id)
            
            assert exc_info.value.status_code == 404
            assert "Associated report not found" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_get_analysis_status_database_error(self):
        """Test status retrieval when database error occurs."""
        job_id = "error-job-222"
        
        with patch('models.analysis_job.AnalysisJob.find_one', new_callable=AsyncMock) as mock_find_job:
            mock_find_job.side_effect = Exception("Database connection failed")
            
            from api.v1.endpoints.analysis import get_analysis_status
            
            with pytest.raises(HTTPException) as exc_info:
                await get_analysis_status(job_id)
            
            assert exc_info.value.status_code == 500
            assert "Failed to get analysis status" in str(exc_info.value.detail)


class TestJobCancellationEndpoint:
    """Test cases for job cancellation endpoint."""
    
    @pytest.mark.asyncio
    async def test_cancel_analysis_success(self):
        """Test successful cancellation of running job."""
        job_id = "running-job-333"
        
        # Mock running analysis job
        mock_job = MagicMock()
        mock_job.job_id = job_id
        mock_job.status = JobStatus.STARTED
        mock_job.report_id = "report-333"
        mock_job.fail_job = MagicMock()
        mock_job.save = AsyncMock()
        
        # Mock associated report
        mock_report = MagicMock()
        mock_report.update_status = MagicMock()
        mock_report.save = AsyncMock()
        
        # Mock Celery task
        mock_task = MagicMock()
        mock_task.revoke = MagicMock()
        
        with patch('models.analysis_job.AnalysisJob.find_one', new_callable=AsyncMock) as mock_find_job, \
             patch('models.report.Report.get', new_callable=AsyncMock) as mock_get_report, \
             patch('tasks.analysis_tasks.analyze_pcap_file.AsyncResult') as mock_async_result:
            
            mock_find_job.return_value = mock_job
            mock_get_report.return_value = mock_report
            mock_async_result.return_value = mock_task
            
            from api.v1.endpoints.analysis import cancel_analysis
            
            result = await cancel_analysis(job_id)
            
            # Verify response
            assert result["message"] == "Analysis job cancelled"
            assert result["job_id"] == job_id
            assert result["status"] == "cancelled"
            
            # Verify cancellation actions
            mock_find_job.assert_called_once_with({"job_id": job_id})
            mock_async_result.assert_called_once_with(job_id)
            mock_task.revoke.assert_called_once_with(terminate=True)
            mock_job.fail_job.assert_called_once_with("Cancelled by user")
            mock_job.save.assert_called_once()
            mock_get_report.assert_called_once_with("report-333")
            mock_report.update_status.assert_called_once_with(ReportStatus.FAILED, "Analysis cancelled by user")
            mock_report.save.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_cancel_analysis_job_not_found(self):
        """Test cancellation of non-existent job."""
        job_id = "nonexistent-cancel-job"
        
        with patch('models.analysis_job.AnalysisJob.find_one', new_callable=AsyncMock) as mock_find_job:
            mock_find_job.return_value = None
            
            from api.v1.endpoints.analysis import cancel_analysis
            
            with pytest.raises(HTTPException) as exc_info:
                await cancel_analysis(job_id)
            
            assert exc_info.value.status_code == 404
            assert "Analysis job not found" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_cancel_analysis_already_completed(self):
        """Test cancellation of already completed job."""
        job_id = "completed-cancel-job"
        
        # Mock completed analysis job
        mock_job = MagicMock()
        mock_job.job_id = job_id
        mock_job.status = JobStatus.SUCCESS
        mock_job.report_id = "report-completed"
        mock_job.fail_job = MagicMock()
        mock_job.save = AsyncMock()
        
        # Mock associated report
        mock_report = MagicMock()
        mock_report.update_status = MagicMock()
        mock_report.save = AsyncMock()
        
        # Mock Celery task
        mock_task = MagicMock()
        mock_task.revoke = MagicMock()
        
        with patch('models.analysis_job.AnalysisJob.find_one', new_callable=AsyncMock) as mock_find_job, \
             patch('models.report.Report.get', new_callable=AsyncMock) as mock_get_report, \
             patch('tasks.analysis_tasks.analyze_pcap_file.AsyncResult') as mock_async_result:
            
            mock_find_job.return_value = mock_job
            mock_get_report.return_value = mock_report
            mock_async_result.return_value = mock_task
            
            from api.v1.endpoints.analysis import cancel_analysis
            
            result = await cancel_analysis(job_id)
            
            # Should still return success (idempotent operation)
            assert result["message"] == "Analysis job cancelled"
            assert result["job_id"] == job_id
            assert result["status"] == "cancelled"
            
            # Verify cancellation was attempted anyway
            mock_task.revoke.assert_called_once_with(terminate=True)
    
    @pytest.mark.asyncio
    async def test_cancel_analysis_no_associated_report(self):
        """Test cancellation when associated report is missing."""
        job_id = "orphaned-cancel-job"
        
        # Mock analysis job without report
        mock_job = MagicMock()
        mock_job.job_id = job_id
        mock_job.status = JobStatus.STARTED
        mock_job.report_id = "missing-report"
        mock_job.fail_job = MagicMock()
        mock_job.save = AsyncMock()
        
        # Mock Celery task
        mock_task = MagicMock()
        mock_task.revoke = MagicMock()
        
        with patch('models.analysis_job.AnalysisJob.find_one', new_callable=AsyncMock) as mock_find_job, \
             patch('models.report.Report.get', new_callable=AsyncMock) as mock_get_report, \
             patch('tasks.analysis_tasks.analyze_pcap_file.AsyncResult') as mock_async_result:
            
            mock_find_job.return_value = mock_job
            mock_get_report.return_value = None  # Report not found
            mock_async_result.return_value = mock_task
            
            from api.v1.endpoints.analysis import cancel_analysis
            
            result = await cancel_analysis(job_id)
            
            # Should still succeed (job cancelled even if report missing)
            assert result["message"] == "Analysis job cancelled"
            assert result["job_id"] == job_id
            assert result["status"] == "cancelled"
            
            # Verify job was cancelled but report update was skipped
            mock_task.revoke.assert_called_once_with(terminate=True)
            mock_job.fail_job.assert_called_once_with("Cancelled by user")
            mock_job.save.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_cancel_analysis_database_error(self):
        """Test cancellation when database error occurs."""
        job_id = "error-cancel-job"
        
        with patch('models.analysis_job.AnalysisJob.find_one', new_callable=AsyncMock) as mock_find_job:
            mock_find_job.side_effect = Exception("Database connection failed")
            
            from api.v1.endpoints.analysis import cancel_analysis
            
            with pytest.raises(HTTPException) as exc_info:
                await cancel_analysis(job_id)
            
            assert exc_info.value.status_code == 500
            assert "Failed to cancel analysis" in str(exc_info.value.detail)


class TestJobResultsEndpoint:
    """Test cases for retrieving detailed job results."""
    
    @pytest.mark.asyncio
    async def test_get_job_results_success(self):
        """Test successful retrieval of completed job results."""
        # This test is for a potential new endpoint to get detailed results
        # Currently covered by get_analysis_status, but could be separate
        pass
    
    @pytest.mark.asyncio
    async def test_get_job_results_pagination(self):
        """Test pagination of job results when there are many jobs."""
        # This would be for listing multiple jobs with pagination
        pass
    
    @pytest.mark.asyncio
    async def test_get_job_results_filtering(self):
        """Test filtering job results by status, date, etc."""
        # This would be for filtering job lists
        pass 
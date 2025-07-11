"""
Unit tests for reports endpoint - Job Status/Result functionality.
Test-Driven Development approach for Step 1.4 of Phase 1.
"""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient
from httpx import AsyncClient
from datetime import datetime, timedelta
from typing import Dict, Any

from main import app
from models.report import Report, ReportStatus
from models.analysis_job import AnalysisJob, JobStatus


class TestReportsEndpoint:
    """Test cases for reports endpoint using TDD."""
    
    @pytest.mark.asyncio
    async def test_get_report_success(self):
        """Test successful report retrieval."""
        # Mock report data
        mock_report = MagicMock()
        mock_report.id = "report_123"
        mock_report.original_filename = "test.pcap"
        mock_report.file_size = 1024
        mock_report.status = ReportStatus.COMPLETED
        mock_report.created_at = datetime.utcnow()
        mock_report.updated_at = datetime.utcnow()
        mock_report.completed_at = datetime.utcnow()
        mock_report.processing_time = 125.5
        mock_report.to_dict.return_value = {
            "report_id": "report_123",
            "filename": "test.pcap",
            "file_size": 1024,
            "status": "completed",
            "created_at": "2024-01-01T00:00:00Z",
            "completed_at": "2024-01-01T00:02:05Z",
            "processing_time": 125.5
        }
        
        with patch('api.v1.endpoints.reports.Report.get', return_value=mock_report):
            async with AsyncClient(app=app, base_url="http://test") as client:
                response = await client.get("/api/v1/reports/report_123")
            
            assert response.status_code == 200
            result = response.json()
            
            # Check required fields
            assert result["report_id"] == "report_123"
            assert result["filename"] == "test.pcap"
            assert result["file_size"] == 1024
            assert result["status"] == "completed"
            assert "created_at" in result
            assert "processing_time" in result
    
    @pytest.mark.asyncio
    async def test_get_report_not_found(self):
        """Test report retrieval when report doesn't exist."""
        with patch('api.v1.endpoints.reports.Report.get', return_value=None):
            async with AsyncClient(app=app, base_url="http://test") as client:
                response = await client.get("/api/v1/reports/nonexistent")
            
            assert response.status_code == 404
            result = response.json()
            assert "detail" in result
            assert "Report not found" in result["detail"]
    
    @pytest.mark.asyncio
    async def test_get_report_pending_status(self):
        """Test report retrieval for pending job."""
        # Mock pending report
        mock_report = MagicMock()
        mock_report.id = "report_123"
        mock_report.original_filename = "test.pcap"
        mock_report.status = ReportStatus.PENDING
        mock_report.created_at = datetime.utcnow()
        mock_report.updated_at = datetime.utcnow()
        mock_report.completed_at = None
        mock_report.processing_time = None
        mock_report.to_dict.return_value = {
            "report_id": "report_123",
            "filename": "test.pcap",
            "status": "pending",
            "created_at": "2024-01-01T00:00:00Z",
            "completed_at": None,
            "processing_time": None
        }
        
        with patch('api.v1.endpoints.reports.Report.get', return_value=mock_report):
            async with AsyncClient(app=app, base_url="http://test") as client:
                response = await client.get("/api/v1/reports/report_123")
            
            assert response.status_code == 200
            result = response.json()
            
            assert result["status"] == "pending"
            assert result["completed_at"] is None
            assert result["processing_time"] is None
    
    @pytest.mark.asyncio
    async def test_get_report_failed_status(self):
        """Test report retrieval for failed job."""
        # Mock failed report
        mock_report = MagicMock()
        mock_report.id = "report_123"
        mock_report.original_filename = "test.pcap"
        mock_report.status = ReportStatus.FAILED
        mock_report.error_message = "Analysis failed due to corrupted file"
        mock_report.created_at = datetime.utcnow()
        mock_report.updated_at = datetime.utcnow()
        mock_report.completed_at = datetime.utcnow()
        mock_report.to_dict.return_value = {
            "report_id": "report_123",
            "filename": "test.pcap",
            "status": "failed",
            "error_message": "Analysis failed due to corrupted file",
            "created_at": "2024-01-01T00:00:00Z",
            "completed_at": "2024-01-01T00:01:30Z"
        }
        
        with patch('api.v1.endpoints.reports.Report.get', return_value=mock_report):
            async with AsyncClient(app=app, base_url="http://test") as client:
                response = await client.get("/api/v1/reports/report_123")
            
            assert response.status_code == 200
            result = response.json()
            
            assert result["status"] == "failed"
            assert "error_message" in result
            assert result["error_message"] == "Analysis failed due to corrupted file"
    
    @pytest.mark.asyncio
    async def test_get_report_processing_status(self):
        """Test report retrieval for processing job."""
        # Mock processing report
        mock_report = MagicMock()
        mock_report.id = "report_123"
        mock_report.original_filename = "test.pcap"
        mock_report.status = ReportStatus.PROCESSING
        mock_report.created_at = datetime.utcnow()
        mock_report.updated_at = datetime.utcnow()
        mock_report.started_at = datetime.utcnow()
        mock_report.completed_at = None
        mock_report.to_dict.return_value = {
            "report_id": "report_123",
            "filename": "test.pcap",
            "status": "processing",
            "created_at": "2024-01-01T00:00:00Z",
            "started_at": "2024-01-01T00:00:10Z",
            "completed_at": None
        }
        
        with patch('api.v1.endpoints.reports.Report.get', return_value=mock_report):
            async with AsyncClient(app=app, base_url="http://test") as client:
                response = await client.get("/api/v1/reports/report_123")
            
            assert response.status_code == 200
            result = response.json()
            
            assert result["status"] == "processing"
            assert "started_at" in result
            assert result["completed_at"] is None
    
    @pytest.mark.asyncio
    async def test_get_report_results_success(self):
        """Test successful report results retrieval."""
        # Mock completed report with results
        mock_report = MagicMock()
        mock_report.id = "report_123"
        mock_report.original_filename = "test.pcap"
        mock_report.status = ReportStatus.COMPLETED
        mock_report.completed_at = datetime.utcnow()
        mock_report.analysis_results = MagicMock()
        mock_report.analysis_results.dict.return_value = {
            "summary": {"total_packets": 1000, "duration": 60.5},
            "top_talkers": [{"ip": "192.168.1.1", "packets": 500}],
            "protocols": {"TCP": 70, "UDP": 20, "ICMP": 10}
        }
        mock_report.get_processing_time.return_value = 125.5
        
        with patch('api.v1.endpoints.reports.Report.get', return_value=mock_report):
            async with AsyncClient(app=app, base_url="http://test") as client:
                response = await client.get("/api/v1/reports/report_123/results")
            
            assert response.status_code == 200
            result = response.json()
            
            # Check required fields
            assert result["report_id"] == "report_123"
            assert result["filename"] == "test.pcap"
            assert result["status"] == "completed"
            assert "completed_at" in result
            assert result["processing_time"] == 125.5
            assert "results" in result
            assert "summary" in result["results"]
            assert result["results"]["summary"]["total_packets"] == 1000
    
    @pytest.mark.asyncio
    async def test_get_report_results_not_completed(self):
        """Test report results retrieval for non-completed job."""
        # Mock pending report
        mock_report = MagicMock()
        mock_report.id = "report_123"
        mock_report.status = ReportStatus.PENDING
        
        with patch('api.v1.endpoints.reports.Report.get', return_value=mock_report):
            async with AsyncClient(app=app, base_url="http://test") as client:
                response = await client.get("/api/v1/reports/report_123/results")
            
            assert response.status_code == 400
            result = response.json()
            assert "detail" in result
            assert "not completed" in result["detail"].lower()
    
    @pytest.mark.asyncio
    async def test_get_report_results_no_results(self):
        """Test report results retrieval when no results available."""
        # Mock completed report without results
        mock_report = MagicMock()
        mock_report.id = "report_123"
        mock_report.status = ReportStatus.COMPLETED
        mock_report.analysis_results = None
        
        with patch('api.v1.endpoints.reports.Report.get', return_value=mock_report):
            async with AsyncClient(app=app, base_url="http://test") as client:
                response = await client.get("/api/v1/reports/report_123/results")
            
            assert response.status_code == 404
            result = response.json()
            assert "detail" in result
            assert "results not found" in result["detail"].lower()
    
    @pytest.mark.asyncio
    async def test_list_reports_success(self):
        """Test successful report listing."""
        # Mock reports list
        mock_reports = [
            MagicMock(to_dict=lambda: {"report_id": "report_1", "filename": "test1.pcap", "status": "completed"}),
            MagicMock(to_dict=lambda: {"report_id": "report_2", "filename": "test2.pcap", "status": "pending"})
        ]
        
        mock_query = MagicMock()
        mock_query.sort.return_value = mock_query
        mock_query.skip.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.to_list = AsyncMock(return_value=mock_reports)
        
        mock_count_query = MagicMock()
        mock_count_query.count = AsyncMock(return_value=2)
        
        with patch('api.v1.endpoints.reports.Report.find') as mock_find:
            # Set up the mock to return different instances for the two calls
            mock_find.side_effect = [mock_query, mock_count_query]
            
            async with AsyncClient(app=app, base_url="http://test") as client:
                response = await client.get("/api/v1/reports/")
            
            assert response.status_code == 200
            result = response.json()
            
            # Check structure
            assert "reports" in result
            assert "pagination" in result
            assert len(result["reports"]) == 2
            assert result["pagination"]["total"] == 2
            assert result["pagination"]["limit"] == 50  # Default limit
            assert result["pagination"]["offset"] == 0
    
    @pytest.mark.asyncio
    async def test_list_reports_with_status_filter(self):
        """Test report listing with status filter."""
        # Mock filtered reports
        mock_reports = [
            MagicMock(to_dict=lambda: {"report_id": "report_1", "filename": "test1.pcap", "status": "completed"})
        ]
        
        mock_query = MagicMock()
        mock_query.sort.return_value = mock_query
        mock_query.skip.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.to_list = AsyncMock(return_value=mock_reports)
        
        mock_count_query = MagicMock()
        mock_count_query.count = AsyncMock(return_value=1)
        
        with patch('api.v1.endpoints.reports.Report.find') as mock_find:
            mock_find.side_effect = [mock_query, mock_count_query]
            
            async with AsyncClient(app=app, base_url="http://test") as client:
                response = await client.get("/api/v1/reports/?status=completed")
            
            assert response.status_code == 200
            result = response.json()
            
            assert len(result["reports"]) == 1
            assert result["reports"][0]["status"] == "completed"
    
    @pytest.mark.asyncio
    async def test_list_reports_with_pagination(self):
        """Test report listing with pagination."""
        # Mock paginated reports
        mock_reports = [
            MagicMock(to_dict=lambda: {"report_id": "report_3", "filename": "test3.pcap", "status": "pending"})
        ]
        
        mock_query = MagicMock()
        mock_query.sort.return_value = mock_query
        mock_query.skip.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.to_list = AsyncMock(return_value=mock_reports)
        
        mock_count_query = MagicMock()
        mock_count_query.count = AsyncMock(return_value=10)
        
        with patch('api.v1.endpoints.reports.Report.find') as mock_find:
            mock_find.side_effect = [mock_query, mock_count_query]
            
            async with AsyncClient(app=app, base_url="http://test") as client:
                response = await client.get("/api/v1/reports/?limit=5&offset=2")
            
            assert response.status_code == 200
            result = response.json()
            
            assert result["pagination"]["limit"] == 5
            assert result["pagination"]["offset"] == 2
            assert result["pagination"]["total"] == 10
            assert result["pagination"]["has_more"] == True
    
    @pytest.mark.asyncio
    async def test_list_reports_invalid_status(self):
        """Test report listing with invalid status filter."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/api/v1/reports/?status=invalid_status")
        
        assert response.status_code == 400
        result = response.json()
        assert "detail" in result
        assert "Invalid status" in result["detail"]
    
    @pytest.mark.asyncio
    async def test_get_report_summary_success(self):
        """Test successful report summary retrieval."""
        # Mock report with summary data
        mock_report = MagicMock()
        mock_report.id = "report_123"
        mock_report.original_filename = "test.pcap"
        mock_report.file_size = 1024
        mock_report.status = ReportStatus.COMPLETED
        mock_report.created_at = datetime.utcnow()
        mock_report.updated_at = datetime.utcnow()
        mock_report.get_processing_time.return_value = 125.5
        
        with patch('api.v1.endpoints.reports.Report.get', return_value=mock_report):
            async with AsyncClient(app=app, base_url="http://test") as client:
                response = await client.get("/api/v1/reports/report_123/summary")
            
            assert response.status_code == 200
            result = response.json()
            
            # Check required fields
            assert result["report_id"] == "report_123"
            assert result["filename"] == "test.pcap"
            assert result["file_size"] == 1024
            assert result["status"] == "completed"
            assert "created_at" in result
            assert "updated_at" in result
            assert result["processing_time"] == 125.5
    
    @pytest.mark.asyncio
    async def test_delete_report_success(self):
        """Test successful report deletion."""
        # Mock report and analysis job
        mock_report = MagicMock()
        mock_report.id = "report_123"
        mock_report.job_id = "job_123"
        mock_report.delete = AsyncMock()
        
        mock_analysis_job = MagicMock()
        mock_analysis_job.delete = AsyncMock()
        
        with patch('api.v1.endpoints.reports.Report.get', return_value=mock_report), \
             patch('api.v1.endpoints.reports.AnalysisJob.find_one', return_value=mock_analysis_job):
            
            async with AsyncClient(app=app, base_url="http://test") as client:
                response = await client.delete("/api/v1/reports/report_123")
            
            assert response.status_code == 200
            result = response.json()
            
            assert result["message"] == "Report deleted successfully"
            assert result["report_id"] == "report_123"
            
            # Verify delete methods were called
            mock_analysis_job.delete.assert_called_once()
            mock_report.delete.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_delete_report_not_found(self):
        """Test report deletion when report doesn't exist."""
        with patch('api.v1.endpoints.reports.Report.get', return_value=None):
            async with AsyncClient(app=app, base_url="http://test") as client:
                response = await client.delete("/api/v1/reports/nonexistent")
            
            assert response.status_code == 404
            result = response.json()
            assert "detail" in result
            assert "Report not found" in result["detail"]


class TestJobStatusRetrievalMCPTool:
    """Test cases specifically for the get_analysis_report MCP tool functionality."""
    
    @pytest.mark.asyncio
    async def test_get_analysis_report_pending_job(self):
        """Test MCP tool for pending job status."""
        # Mock pending job
        mock_report = MagicMock()
        mock_report.id = "report_123"
        mock_report.job_id = "job_123"
        mock_report.status = ReportStatus.PENDING
        mock_report.to_dict.return_value = {
            "report_id": "report_123",
            "job_id": "job_123",
            "status": "pending",
            "created_at": "2024-01-01T00:00:00Z",
            "progress": 0
        }
        
        with patch('api.v1.endpoints.reports.Report.get', return_value=mock_report):
            async with AsyncClient(app=app, base_url="http://test") as client:
                response = await client.get("/api/v1/reports/report_123")
            
            assert response.status_code == 200
            result = response.json()
            
            # MCP tool should return job status information
            assert result["status"] == "pending"
            assert "job_id" in result
            assert "created_at" in result
    
    @pytest.mark.asyncio
    async def test_get_analysis_report_completed_job(self):
        """Test MCP tool for completed job with results."""
        # Mock completed job
        mock_report = MagicMock()
        mock_report.id = "report_123"
        mock_report.job_id = "job_123"
        mock_report.status = ReportStatus.COMPLETED
        mock_report.analysis_results = {"summary": {"total_packets": 1000}}
        mock_report.to_dict.return_value = {
            "report_id": "report_123",
            "job_id": "job_123",
            "status": "completed",
            "created_at": "2024-01-01T00:00:00Z",
            "completed_at": "2024-01-01T00:02:00Z",
            "processing_time": 120.0,
            "analysis_results": {"summary": {"total_packets": 1000}}
        }
        
        with patch('api.v1.endpoints.reports.Report.get', return_value=mock_report):
            async with AsyncClient(app=app, base_url="http://test") as client:
                response = await client.get("/api/v1/reports/report_123")
            
            assert response.status_code == 200
            result = response.json()
            
            # MCP tool should return complete job information
            assert result["status"] == "completed"
            assert "completed_at" in result
            assert "processing_time" in result
            assert "analysis_results" in result
    
    @pytest.mark.asyncio
    async def test_get_analysis_report_failed_job(self):
        """Test MCP tool for failed job."""
        # Mock failed job
        mock_report = MagicMock()
        mock_report.id = "report_123"
        mock_report.job_id = "job_123"
        mock_report.status = ReportStatus.FAILED
        mock_report.error_message = "PCAP file is corrupted"
        mock_report.to_dict.return_value = {
            "report_id": "report_123",
            "job_id": "job_123",
            "status": "failed",
            "error_message": "PCAP file is corrupted",
            "created_at": "2024-01-01T00:00:00Z",
            "completed_at": "2024-01-01T00:01:00Z"
        }
        
        with patch('api.v1.endpoints.reports.Report.get', return_value=mock_report):
            async with AsyncClient(app=app, base_url="http://test") as client:
                response = await client.get("/api/v1/reports/report_123")
            
            assert response.status_code == 200
            result = response.json()
            
            # MCP tool should return error information
            assert result["status"] == "failed"
            assert "error_message" in result
            assert result["error_message"] == "PCAP file is corrupted"
    
    @pytest.mark.asyncio
    async def test_get_analysis_report_nonexistent_job(self):
        """Test MCP tool for non-existent job ID."""
        with patch('api.v1.endpoints.reports.Report.get', return_value=None):
            async with AsyncClient(app=app, base_url="http://test") as client:
                response = await client.get("/api/v1/reports/nonexistent_job")
            
            assert response.status_code == 404
            result = response.json()
            
            # MCP tool should return appropriate error
            assert "detail" in result
            assert "Report not found" in result["detail"]


class TestReportResponseStructure:
    """Test cases for report response structure validation."""
    
    @pytest.mark.asyncio
    async def test_report_response_structure(self):
        """Test that report response has correct structure."""
        # Mock report with all fields
        mock_report = MagicMock()
        mock_report.id = "report_123"
        mock_report.to_dict.return_value = {
            "report_id": "report_123",
            "filename": "test.pcap",
            "file_size": 1024,
            "status": "completed",
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:02:00Z",
            "completed_at": "2024-01-01T00:02:00Z",
            "processing_time": 120.0,
            "job_id": "job_123",
            "analysis_results": {"summary": {"total_packets": 1000}}
        }
        
        with patch('api.v1.endpoints.reports.Report.get', return_value=mock_report):
            async with AsyncClient(app=app, base_url="http://test") as client:
                response = await client.get("/api/v1/reports/report_123")
            
            assert response.status_code == 200
            result = response.json()
            
            # Check required fields
            required_fields = ["report_id", "filename", "file_size", "status", "created_at"]
            for field in required_fields:
                assert field in result, f"Missing required field: {field}"
            
            # Check field types
            assert isinstance(result["report_id"], str)
            assert isinstance(result["filename"], str)
            assert isinstance(result["file_size"], int)
            assert isinstance(result["status"], str)
            assert isinstance(result["created_at"], str)
            
            # Check optional fields when present
            if "processing_time" in result:
                assert isinstance(result["processing_time"], (int, float))
            if "analysis_results" in result:
                assert isinstance(result["analysis_results"], dict) 
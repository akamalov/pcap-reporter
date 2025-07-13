"""
Unit tests for analysis job submission endpoint.
Test-Driven Development approach - tests written first.
"""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock, mock_open
from fastapi.testclient import TestClient
from httpx import AsyncClient
import tempfile
import os
from datetime import datetime
import uuid
from io import BytesIO

from main import app
from models.report import Report, ReportStatus
from models.analysis_job import AnalysisJob, JobStatus
from services.validation_service import ValidationService


class TestAnalysisJobSubmission:
    """Test cases for analysis job submission endpoint using TDD."""
    
    @pytest.mark.asyncio
    async def test_submit_analysis_job_success(self):
        """Test successful analysis job submission."""
        # Mock file content
        pcap_content = b'\xd4\xc3\xb2\xa1' + b'\x00' * 20  # Minimal PCAP header
        
        # Create a mock file
        mock_file = MagicMock()
        mock_file.filename = "test.pcap"
        mock_file.read = AsyncMock(return_value=pcap_content)
        mock_file.seek = AsyncMock()
        
        # Mock validation service
        mock_validation_service = MagicMock()
        mock_validation_service.validate_file_extension.return_value = True
        mock_validation_service.validate_file_size.return_value = {"valid": True}
        mock_validation_service.validate_pcap_file = AsyncMock(return_value={"valid": True})
        mock_validation_service.comprehensive_file_validation = AsyncMock(return_value={
            "valid": True,
            "validation_id": "test_validation_123",
            "security_score": "clean",
            "file_type": "pcap",
            "validation_time": 0.05
        })
        mock_validation_service.validate_analysis_options.return_value = {
            "valid": True,
            "options": {"analysis_type": "comprehensive", "priority": "normal"}
        }
        mock_validation_service.estimate_completion_time.return_value = 300
        
        # Mock database operations
        mock_report = MagicMock()
        mock_report.id = "report_123"
        mock_report.insert = AsyncMock()
        mock_report.save = AsyncMock()
        
        mock_analysis_job = MagicMock()
        mock_analysis_job.insert = AsyncMock()
        mock_analysis_job.save = AsyncMock()
        
        # Mock Celery task
        mock_task = MagicMock()
        mock_task.id = "task_123"
        
        with patch('api.v1.endpoints.analysis.get_validation_service', return_value=mock_validation_service), \
             patch('api.v1.endpoints.analysis.Report', return_value=mock_report), \
             patch('api.v1.endpoints.analysis.AnalysisJob', return_value=mock_analysis_job), \
             patch('api.v1.endpoints.analysis.analyze_pcap_file.delay', return_value=mock_task), \
             patch('api.v1.endpoints.analysis.calculate_file_hash', return_value="hash123"), \
             patch('builtins.open', mock_open()), \
             patch('os.makedirs'), \
             patch('os.path.join', return_value="/tmp/test.pcap"), \
             patch('uuid.uuid4') as mock_uuid:
            
            mock_uuid.return_value.hex = "unique_id_123"
            
            # Create form data
            files = {"file": ("test.pcap", BytesIO(pcap_content), "application/octet-stream")}
            data = {"analysis_type": "comprehensive", "priority": "normal"}
            
            async with AsyncClient(app=app, base_url="http://test") as client:
                response = await client.post("/api/v1/analysis/submit", files=files, data=data)
            
            assert response.status_code == 200
            result = response.json()
            
            # Check required fields
            assert "job_id" in result
            assert result["status"] == "pending"
            assert result["filename"] == "test.pcap"
            assert result["file_size"] == len(pcap_content)
            assert "created_at" in result
            assert "estimated_completion" in result
            assert result["analysis_type"] == "comprehensive"
            assert result["priority"] == "normal"
    
    @pytest.mark.asyncio
    async def test_submit_analysis_job_invalid_file_type(self):
        """Test job submission with invalid file type."""
        # Mock file content
        text_content = b'this is not a pcap file'
        
        # Mock validation service
        mock_validation_service = MagicMock()
        mock_validation_service.validate_file_extension.return_value = False
        
        with patch('api.v1.endpoints.analysis.get_validation_service', return_value=mock_validation_service):
            
            # Create form data with invalid file type
            files = {"file": ("test.txt", BytesIO(text_content), "text/plain")}
            data = {"analysis_type": "comprehensive", "priority": "normal"}
            
            async with AsyncClient(app=app, base_url="http://test") as client:
                response = await client.post("/api/v1/analysis/submit", files=files, data=data)
            
            assert response.status_code == 400
            result = response.json()
            
            assert "detail" in result
            assert "error" in result["detail"]
            assert result["detail"]["error"] == "Invalid file type"
            assert "supported_types" in result["detail"]
    
    @pytest.mark.asyncio
    async def test_submit_analysis_job_file_too_large(self):
        """Test job submission with file too large."""
        # Mock large file content
        large_content = b'x' * (200 * 1024 * 1024)  # 200MB file
        
        # Mock validation service
        mock_validation_service = MagicMock()
        mock_validation_service.validate_file_extension.return_value = True
        mock_validation_service.validate_file_size.return_value = False
        
        with patch('api.v1.endpoints.analysis.get_validation_service', return_value=mock_validation_service):
            
            # Create form data with large file
            files = {"file": ("large.pcap", BytesIO(large_content), "application/octet-stream")}
            data = {"analysis_type": "comprehensive", "priority": "normal"}
            
            async with AsyncClient(app=app, base_url="http://test") as client:
                response = await client.post("/api/v1/analysis/submit", files=files, data=data)
            
            assert response.status_code == 413
            result = response.json()
            
            assert "detail" in result
            assert "error" in result["detail"]
            assert result["detail"]["error"] == "File too large"
            assert "max_size" in result["detail"]
            assert "received_size" in result["detail"]
    
    @pytest.mark.asyncio
    async def test_submit_analysis_job_no_file(self):
        """Test job submission without file."""
        # Submit without file
        data = {"analysis_type": "comprehensive", "priority": "normal"}
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post("/api/v1/analysis/submit", data=data)
        
        assert response.status_code == 400
        result = response.json()
        
        assert "detail" in result
        assert "No file provided" in result["detail"]
    
    @pytest.mark.asyncio
    async def test_submit_analysis_job_corrupted_file(self):
        """Test job submission with corrupted PCAP file."""
        # Mock corrupted file content
        corrupted_content = b'corrupted pcap data'
        
        # Mock validation service
        mock_validation_service = MagicMock()
        mock_validation_service.validate_file_extension.return_value = True
        mock_validation_service.validate_file_size.return_value = {"valid": True}
        mock_validation_service.validate_pcap_file = AsyncMock(return_value={
            "valid": False,
            "error": "Invalid PCAP format"
        })
        
        with patch('api.v1.endpoints.analysis.get_validation_service', return_value=mock_validation_service):
            
            # Create form data with corrupted file
            files = {"file": ("corrupted.pcap", BytesIO(corrupted_content), "application/octet-stream")}
            data = {"analysis_type": "comprehensive", "priority": "normal"}
            
            async with AsyncClient(app=app, base_url="http://test") as client:
                response = await client.post("/api/v1/analysis/submit", files=files, data=data)
            
            assert response.status_code == 400
            result = response.json()
            
            assert "detail" in result
            assert "error" in result["detail"]
            assert result["detail"]["error"] == "Invalid PCAP file"
    
    @pytest.mark.asyncio
    async def test_submit_analysis_job_with_options(self):
        """Test job submission with analysis options."""
        # Mock file content
        pcap_content = b'\xd4\xc3\xb2\xa1' + b'\x00' * 20  # Minimal PCAP header
        
        # Mock validation service
        mock_validation_service = MagicMock()
        mock_validation_service.validate_file_extension.return_value = True
        mock_validation_service.validate_file_size.return_value = {"valid": True}
        mock_validation_service.validate_pcap_file = AsyncMock(return_value={"valid": True})
        mock_validation_service.comprehensive_file_validation = AsyncMock(return_value={
            "valid": True,
            "validation_id": "test_validation_123",
            "security_score": "clean",
            "file_type": "pcap",
            "validation_time": 0.05
        })
        mock_validation_service.validate_analysis_options.return_value = {
            "valid": True,
            "options": {"analysis_type": "security_focused", "priority": "high"}
        }
        mock_validation_service.estimate_completion_time.return_value = 180  # Faster for high priority
        
        # Mock database operations
        mock_report = MagicMock()
        mock_report.id = "report_123"
        mock_report.insert = AsyncMock()
        mock_report.save = AsyncMock()
        
        mock_analysis_job = MagicMock()
        mock_analysis_job.insert = AsyncMock()
        mock_analysis_job.save = AsyncMock()
        
        # Mock Celery task
        mock_task = MagicMock()
        mock_task.id = "task_123"
        
        with patch('api.v1.endpoints.analysis.get_validation_service', return_value=mock_validation_service), \
             patch('api.v1.endpoints.analysis.Report', return_value=mock_report), \
             patch('api.v1.endpoints.analysis.AnalysisJob', return_value=mock_analysis_job), \
             patch('api.v1.endpoints.analysis.analyze_pcap_file.delay', return_value=mock_task), \
             patch('api.v1.endpoints.analysis.calculate_file_hash', return_value="hash123"), \
             patch('builtins.open', mock_open()), \
             patch('os.makedirs'), \
             patch('os.path.join', return_value="/tmp/test.pcap"), \
             patch('uuid.uuid4') as mock_uuid:
            
            mock_uuid.return_value.hex = "unique_id_123"
            
            # Create form data with options
            files = {"file": ("test.pcap", BytesIO(pcap_content), "application/octet-stream")}
            data = {"analysis_type": "security_focused", "priority": "high"}
            
            async with AsyncClient(app=app, base_url="http://test") as client:
                response = await client.post("/api/v1/analysis/submit", files=files, data=data)
            
            assert response.status_code == 200
            result = response.json()
            
            # Check options are reflected in response
            assert result["analysis_type"] == "security_focused"
            assert result["priority"] == "high"
    
    @pytest.mark.asyncio
    async def test_submit_analysis_job_invalid_options(self):
        """Test job submission with invalid analysis options."""
        # Mock file content
        pcap_content = b'\xd4\xc3\xb2\xa1' + b'\x00' * 20  # Minimal PCAP header
        
        # Mock validation service
        mock_validation_service = MagicMock()
        mock_validation_service.validate_file_extension.return_value = True
        mock_validation_service.validate_file_size.return_value = {"valid": True}
        mock_validation_service.validate_pcap_file = AsyncMock(return_value={"valid": True})
        mock_validation_service.comprehensive_file_validation = AsyncMock(return_value={
            "valid": True,
            "validation_id": "test_validation_123",
            "security_score": "clean",
            "file_type": "pcap",
            "validation_time": 0.05
        })
        mock_validation_service.validate_analysis_options.return_value = {
            "valid": False,
            "errors": ["Invalid analysis type", "Invalid priority level"]
        }
        
        with patch('api.v1.endpoints.analysis.get_validation_service', return_value=mock_validation_service):
            
            # Create form data with invalid options
            files = {"file": ("test.pcap", BytesIO(pcap_content), "application/octet-stream")}
            data = {"analysis_type": "invalid_type", "priority": "invalid_priority"}
            
            async with AsyncClient(app=app, base_url="http://test") as client:
                response = await client.post("/api/v1/analysis/submit", files=files, data=data)
            
            assert response.status_code == 400
            result = response.json()
            
            assert "detail" in result
            assert "error" in result["detail"]
            assert result["detail"]["error"] == "Invalid analysis options"
            assert "errors" in result["detail"]
    
    @pytest.mark.asyncio
    async def test_submit_analysis_job_response_structure(self):
        """Test that job submission response has correct structure."""
        # Mock file content
        pcap_content = b'\xd4\xc3\xb2\xa1' + b'\x00' * 20  # Minimal PCAP header
        
        # Mock validation service
        mock_validation_service = MagicMock()
        mock_validation_service.validate_file_extension.return_value = True
        mock_validation_service.validate_file_size.return_value = {"valid": True}
        mock_validation_service.validate_pcap_file = AsyncMock(return_value={"valid": True})
        mock_validation_service.comprehensive_file_validation = AsyncMock(return_value={
            "valid": True,
            "validation_id": "test_validation_123",
            "security_score": "clean",
            "file_type": "pcap",
            "validation_time": 0.05
        })
        mock_validation_service.validate_analysis_options.return_value = {
            "valid": True,
            "options": {"analysis_type": "comprehensive", "priority": "normal"}
        }
        mock_validation_service.estimate_completion_time.return_value = 300
        
        # Mock database operations
        mock_report = MagicMock()
        mock_report.id = "report_123"
        mock_report.insert = AsyncMock()
        mock_report.save = AsyncMock()
        
        mock_analysis_job = MagicMock()
        mock_analysis_job.insert = AsyncMock()
        mock_analysis_job.save = AsyncMock()
        
        # Mock Celery task
        mock_task = MagicMock()
        mock_task.id = "task_123"
        
        with patch('api.v1.endpoints.analysis.get_validation_service', return_value=mock_validation_service), \
             patch('api.v1.endpoints.analysis.Report', return_value=mock_report), \
             patch('api.v1.endpoints.analysis.AnalysisJob', return_value=mock_analysis_job), \
             patch('api.v1.endpoints.analysis.analyze_pcap_file.delay', return_value=mock_task), \
             patch('api.v1.endpoints.analysis.calculate_file_hash', return_value="hash123"), \
             patch('builtins.open', mock_open()), \
             patch('os.makedirs'), \
             patch('os.path.join', return_value="/tmp/test.pcap"), \
             patch('uuid.uuid4') as mock_uuid:
            
            mock_uuid.return_value.hex = "unique_id_123"
            
            # Create form data
            files = {"file": ("test.pcap", BytesIO(pcap_content), "application/octet-stream")}
            data = {"analysis_type": "comprehensive", "priority": "normal"}
            
            async with AsyncClient(app=app, base_url="http://test") as client:
                response = await client.post("/api/v1/analysis/submit", files=files, data=data)
            
            assert response.status_code == 200
            result = response.json()
            
            # Check required fields
            required_fields = ["job_id", "status", "filename", "file_size", "created_at", "estimated_completion", "analysis_type", "priority"]
            for field in required_fields:
                assert field in result, f"Missing required field: {field}"
            
            # Check field types
            assert isinstance(result["job_id"], str)
            assert isinstance(result["status"], str)
            assert isinstance(result["filename"], str)
            assert isinstance(result["file_size"], int)
            assert isinstance(result["created_at"], str)
            assert isinstance(result["estimated_completion"], str)
            assert isinstance(result["analysis_type"], str)
            assert isinstance(result["priority"], str)
            
            # Check status value
            assert result["status"] == "pending"
    
    @pytest.mark.asyncio
    async def test_legacy_upload_endpoint(self):
        """Test legacy upload endpoint for backward compatibility."""
        # Mock file content
        pcap_content = b'\xd4\xc3\xb2\xa1' + b'\x00' * 20  # Minimal PCAP header
        
        # Mock validation service
        mock_validation_service = MagicMock()
        mock_validation_service.validate_file_extension.return_value = True
        mock_validation_service.validate_file_size.return_value = {"valid": True}
        mock_validation_service.validate_pcap_file = AsyncMock(return_value={"valid": True})
        mock_validation_service.comprehensive_file_validation = AsyncMock(return_value={
            "valid": True,
            "validation_id": "test_validation_123",
            "security_score": "clean",
            "file_type": "pcap",
            "validation_time": 0.05
        })
        mock_validation_service.validate_analysis_options.return_value = {
            "valid": True,
            "options": {"analysis_type": "comprehensive", "priority": "normal"}
        }
        mock_validation_service.estimate_completion_time.return_value = 300
        
        # Mock database operations
        mock_report = MagicMock()
        mock_report.id = "report_123"
        mock_report.insert = AsyncMock()
        mock_report.save = AsyncMock()
        
        mock_analysis_job = MagicMock()
        mock_analysis_job.insert = AsyncMock()
        mock_analysis_job.save = AsyncMock()
        
        # Mock Celery task
        mock_task = MagicMock()
        mock_task.id = "task_123"
        
        with patch('api.v1.endpoints.analysis.get_validation_service', return_value=mock_validation_service), \
             patch('api.v1.endpoints.analysis.Report', return_value=mock_report), \
             patch('api.v1.endpoints.analysis.AnalysisJob', return_value=mock_analysis_job), \
             patch('api.v1.endpoints.analysis.analyze_pcap_file.delay', return_value=mock_task), \
             patch('api.v1.endpoints.analysis.calculate_file_hash', return_value="hash123"), \
             patch('builtins.open', mock_open()), \
             patch('os.makedirs'), \
             patch('os.path.join', return_value="/tmp/test.pcap"), \
             patch('uuid.uuid4') as mock_uuid:
            
            mock_uuid.return_value.hex = "unique_id_123"
            
            # Use legacy upload endpoint
            files = {"file": ("test.pcap", BytesIO(pcap_content), "application/octet-stream")}
            
            async with AsyncClient(app=app, base_url="http://test") as client:
                response = await client.post("/api/v1/analysis/upload", files=files)
            
            assert response.status_code == 200
            result = response.json()
            
            # Should have same structure as submit endpoint
            assert "job_id" in result
            assert result["status"] == "pending"
            assert result["filename"] == "test.pcap"
            assert result["analysis_type"] == "comprehensive"  # Default
            assert result["priority"] == "normal"  # Default


class TestAnalysisJobValidation:
    """Test cases for analysis job validation."""
    
    def test_validate_file_extension_valid(self):
        """Test file extension validation for valid extensions."""
        validation_service = ValidationService()
        
        valid_filenames = ["test.pcap", "capture.pcapng", "network.cap"]
        for filename in valid_filenames:
            assert validation_service.validate_file_extension(filename) == True
    
    def test_validate_file_extension_invalid(self):
        """Test file extension validation for invalid extensions."""
        validation_service = ValidationService()
        
        invalid_filenames = ["test.txt", "file.exe", "image.jpg", "doc.pdf"]
        for filename in invalid_filenames:
            assert validation_service.validate_file_extension(filename) == False
    
    def test_validate_file_size_within_limit(self):
        """Test file size validation within limits."""
        validation_service = ValidationService()
        
        # Test various sizes within the limit (100MB default)
        valid_sizes = [1024, 1024*1024, 50*1024*1024, 100*1024*1024]
        for size in valid_sizes:
            assert validation_service.validate_file_size(size) == True
    
    def test_validate_file_size_exceeds_limit(self):
        """Test file size validation exceeding limits."""
        validation_service = ValidationService()
        
        # Test sizes exceeding the limit
        invalid_sizes = [101*1024*1024, 200*1024*1024, 500*1024*1024]
        for size in invalid_sizes:
            assert validation_service.validate_file_size(size) == False
    
    def test_validate_analysis_options_valid(self):
        """Test analysis options validation for valid options."""
        validation_service = ValidationService()
        
        valid_options = [
            {"analysis_type": "comprehensive", "priority": "normal"},
            {"analysis_type": "security_focused", "priority": "high"},
            {"analysis_type": "performance", "priority": "low"}
        ]
        
        for options in valid_options:
            result = validation_service.validate_analysis_options(options)
            assert result["valid"] == True
            assert "options" in result
    
    def test_validate_analysis_options_invalid(self):
        """Test analysis options validation for invalid options."""
        validation_service = ValidationService()
        
        invalid_options = [
            {"analysis_type": "invalid_type", "priority": "normal"},
            {"analysis_type": "comprehensive", "priority": "invalid_priority"},
            {"analysis_type": "invalid_type", "priority": "invalid_priority"}
        ]
        
        for options in invalid_options:
            result = validation_service.validate_analysis_options(options)
            assert result["valid"] == False
            assert "errors" in result 
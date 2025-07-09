"""
Integration tests for analysis job submission endpoint.
Tests the actual HTTP endpoint behavior with validation service.
"""
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from io import BytesIO


class TestAnalysisJobSubmissionIntegration:
    """Integration tests for analysis job submission endpoint."""
    
    @pytest.mark.asyncio
    async def test_submit_analysis_job_success(self):
        """Test successful analysis job submission with all validations."""
        from services.validation_service import ValidationService
        
        # Mock validation service methods
        with patch.object(ValidationService, 'validate_file_extension') as mock_ext, \
             patch.object(ValidationService, 'validate_file_size') as mock_size, \
             patch.object(ValidationService, 'validate_pcap_file', new_callable=AsyncMock) as mock_pcap, \
             patch.object(ValidationService, 'validate_analysis_options') as mock_options, \
             patch.object(ValidationService, 'estimate_completion_time') as mock_estimate:
            
            # Setup mocks
            mock_ext.return_value = True
            mock_size.return_value = True
            mock_pcap.return_value = {"valid": True, "file_type": "pcap"}
            mock_options.return_value = {
                "valid": True,
                "options": {
                    "analysis_type": "comprehensive",
                    "priority": "normal",
                    "deep_packet_inspection": True,
                    "protocol_analysis": True,
                    "security_analysis": True,
                    "performance_analysis": True,
                    "generate_report": True
                }
            }
            mock_estimate.return_value = 300  # 5 minutes
            
            # Create a mock file
            file_content = b'\xd4\xc3\xb2\xa1' + b'\x00' * 100  # Valid PCAP magic + padding
            
            # Mock the file upload
            mock_file = MagicMock()
            mock_file.filename = "test.pcap"
            mock_file.read = AsyncMock(return_value=file_content)
            mock_file.seek = AsyncMock()
            
            # Mock database operations
            with patch('models.report.Report') as mock_report_class, \
                 patch('models.analysis_job.AnalysisJob') as mock_job_class, \
                 patch('tasks.analysis_tasks.analyze_pcap_file') as mock_task, \
                 patch('os.makedirs'), \
                 patch('builtins.open'), \
                 patch('api.v1.endpoints.analysis.calculate_file_hash') as mock_hash:
                
                # Setup database mocks
                mock_report = MagicMock()
                mock_report.id = "report123"
                mock_report_class.return_value = mock_report
                mock_report.insert = AsyncMock()
                mock_report.save = AsyncMock()
                
                mock_job = MagicMock()
                mock_job_class.return_value = mock_job
                mock_job.insert = AsyncMock()
                mock_job.save = AsyncMock()
                
                # Setup task mock
                mock_celery_task = MagicMock()
                mock_celery_task.id = "task123"
                mock_task.delay.return_value = mock_celery_task
                
                mock_hash.return_value = "abc123"
                
                # Import and test the endpoint
                from api.v1.endpoints.analysis import submit_analysis_job
                from core.config import get_settings
                from services.validation_service import get_validation_service
                
                settings = get_settings()
                validation_service = get_validation_service()
                
                result = await submit_analysis_job(
                    file=mock_file,
                    analysis_type="comprehensive",
                    priority="normal",
                    settings=settings,
                    validation_service=validation_service
                )
                
                # Verify response structure
                assert "job_id" in result
                assert result["status"] == "pending"
                assert result["filename"] == "test.pcap"
                assert result["file_size"] == len(file_content)
                assert "created_at" in result
                assert "estimated_completion" in result
                assert result["analysis_type"] == "comprehensive"
                assert result["priority"] == "normal"
                
                # Verify mocks were called
                mock_ext.assert_called_once()
                mock_size.assert_called_once()
                mock_pcap.assert_called_once()
                mock_options.assert_called_once()
                mock_estimate.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_submit_analysis_job_invalid_file_extension(self):
        """Test job submission with invalid file extension."""
        from services.validation_service import ValidationService
        from fastapi import HTTPException
        
        # Mock validation service to return invalid extension
        with patch.object(ValidationService, 'validate_file_extension') as mock_ext:
            mock_ext.return_value = False
            
            # Create a mock file with invalid extension
            mock_file = MagicMock()
            mock_file.filename = "test.txt"
            mock_file.read = AsyncMock(return_value=b"some content")
            
            # Import endpoint
            from api.v1.endpoints.analysis import submit_analysis_job
            from core.config import get_settings
            from services.validation_service import get_validation_service
            
            settings = get_settings()
            validation_service = get_validation_service()
            
            # Test should raise HTTPException
            with pytest.raises(HTTPException) as exc_info:
                await submit_analysis_job(
                    file=mock_file,
                    analysis_type="comprehensive",
                    priority="normal",
                    settings=settings,
                    validation_service=validation_service
                )
            
            assert exc_info.value.status_code == 400
            assert "Invalid file type" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_submit_analysis_job_file_too_large(self):
        """Test job submission with file too large."""
        from services.validation_service import ValidationService
        from fastapi import HTTPException
        
        # Mock validation service
        with patch.object(ValidationService, 'validate_file_extension') as mock_ext, \
             patch.object(ValidationService, 'validate_file_size') as mock_size:
            
            mock_ext.return_value = True
            mock_size.return_value = False  # File too large
            
            # Create a mock large file
            large_content = b"x" * (100 * 1024 * 1024 + 1)  # > 100MB
            mock_file = MagicMock()
            mock_file.filename = "large.pcap"
            mock_file.read = AsyncMock(return_value=large_content)
            
            # Import endpoint
            from api.v1.endpoints.analysis import submit_analysis_job
            from core.config import get_settings
            from services.validation_service import get_validation_service
            
            settings = get_settings()
            validation_service = get_validation_service()
            
            # Test should raise HTTPException
            with pytest.raises(HTTPException) as exc_info:
                await submit_analysis_job(
                    file=mock_file,
                    analysis_type="comprehensive",
                    priority="normal",
                    settings=settings,
                    validation_service=validation_service
                )
            
            assert exc_info.value.status_code == 413
            assert "File too large" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_submit_analysis_job_invalid_pcap(self):
        """Test job submission with invalid PCAP file."""
        from services.validation_service import ValidationService
        from fastapi import HTTPException
        
        # Mock validation service
        with patch.object(ValidationService, 'validate_file_extension') as mock_ext, \
             patch.object(ValidationService, 'validate_file_size') as mock_size, \
             patch.object(ValidationService, 'validate_pcap_file', new_callable=AsyncMock) as mock_pcap:
            
            mock_ext.return_value = True
            mock_size.return_value = True
            mock_pcap.return_value = {
                "valid": False,
                "error": "Invalid PCAP magic number"
            }
            
            # Create a mock invalid PCAP file
            invalid_content = b"invalid pcap content"
            mock_file = MagicMock()
            mock_file.filename = "invalid.pcap"
            mock_file.read = AsyncMock(return_value=invalid_content)
            mock_file.seek = AsyncMock()
            
            # Import endpoint
            from api.v1.endpoints.analysis import submit_analysis_job
            from core.config import get_settings
            from services.validation_service import get_validation_service
            
            settings = get_settings()
            validation_service = get_validation_service()
            
            # Test should raise HTTPException
            with pytest.raises(HTTPException) as exc_info:
                await submit_analysis_job(
                    file=mock_file,
                    analysis_type="comprehensive",
                    priority="normal",
                    settings=settings,
                    validation_service=validation_service
                )
            
            assert exc_info.value.status_code == 400
            assert "Invalid PCAP file" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_submit_analysis_job_invalid_options(self):
        """Test job submission with invalid analysis options."""
        from services.validation_service import ValidationService
        from fastapi import HTTPException
        
        # Mock validation service
        with patch.object(ValidationService, 'validate_file_extension') as mock_ext, \
             patch.object(ValidationService, 'validate_file_size') as mock_size, \
             patch.object(ValidationService, 'validate_pcap_file', new_callable=AsyncMock) as mock_pcap, \
             patch.object(ValidationService, 'validate_analysis_options') as mock_options:
            
            mock_ext.return_value = True
            mock_size.return_value = True
            mock_pcap.return_value = {"valid": True, "file_type": "pcap"}
            mock_options.return_value = {
                "valid": False,
                "errors": ["Invalid analysis_type. Must be one of: ['comprehensive', 'security_focused', 'performance_focused', 'basic']"]
            }
            
            # Create a mock file
            file_content = b'\xd4\xc3\xb2\xa1' + b'\x00' * 100
            mock_file = MagicMock()
            mock_file.filename = "test.pcap"
            mock_file.read = AsyncMock(return_value=file_content)
            mock_file.seek = AsyncMock()
            
            # Import endpoint
            from api.v1.endpoints.analysis import submit_analysis_job
            from core.config import get_settings
            from services.validation_service import get_validation_service
            
            settings = get_settings()
            validation_service = get_validation_service()
            
            # Test should raise HTTPException
            with pytest.raises(HTTPException) as exc_info:
                await submit_analysis_job(
                    file=mock_file,
                    analysis_type="invalid_type",
                    priority="normal",
                    settings=settings,
                    validation_service=validation_service
                )
            
            assert exc_info.value.status_code == 400
            assert "Invalid analysis options" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_submit_analysis_job_no_file(self):
        """Test job submission without file."""
        from fastapi import HTTPException
        
        # Import endpoint
        from api.v1.endpoints.analysis import submit_analysis_job
        from core.config import get_settings
        from services.validation_service import get_validation_service
        
        settings = get_settings()
        validation_service = get_validation_service()
        
        # Test with None file
        with pytest.raises(HTTPException) as exc_info:
            await submit_analysis_job(
                file=None,
                analysis_type="comprehensive",
                priority="normal",
                settings=settings,
                validation_service=validation_service
            )
        
        assert exc_info.value.status_code == 400
        assert "No file provided" in str(exc_info.value.detail)
        
        # Test with file without filename
        mock_file = MagicMock()
        mock_file.filename = None
        
        with pytest.raises(HTTPException) as exc_info:
            await submit_analysis_job(
                file=mock_file,
                analysis_type="comprehensive",
                priority="normal",
                settings=settings,
                validation_service=validation_service
            )
        
        assert exc_info.value.status_code == 400
        assert "No file provided" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_submit_analysis_job_with_custom_options(self):
        """Test job submission with custom analysis options."""
        from services.validation_service import ValidationService
        
        # Mock validation service methods
        with patch.object(ValidationService, 'validate_file_extension') as mock_ext, \
             patch.object(ValidationService, 'validate_file_size') as mock_size, \
             patch.object(ValidationService, 'validate_pcap_file', new_callable=AsyncMock) as mock_pcap, \
             patch.object(ValidationService, 'validate_analysis_options') as mock_options, \
             patch.object(ValidationService, 'estimate_completion_time') as mock_estimate:
            
            # Setup mocks for security-focused analysis
            mock_ext.return_value = True
            mock_size.return_value = True
            mock_pcap.return_value = {"valid": True, "file_type": "pcap"}
            mock_options.return_value = {
                "valid": True,
                "options": {
                    "analysis_type": "security_focused",
                    "priority": "high",
                    "deep_packet_inspection": True,
                    "protocol_analysis": True,
                    "security_analysis": True,
                    "malware_detection": True,
                    "intrusion_detection": True,
                    "vulnerability_scan": True,
                    "performance_analysis": False,
                    "generate_report": True
                }
            }
            mock_estimate.return_value = 180  # 3 minutes for high priority
            
            # Create a mock file
            file_content = b'\xd4\xc3\xb2\xa1' + b'\x00' * 100
            mock_file = MagicMock()
            mock_file.filename = "security_test.pcap"
            mock_file.read = AsyncMock(return_value=file_content)
            mock_file.seek = AsyncMock()
            
            # Mock database operations
            with patch('models.report.Report') as mock_report_class, \
                 patch('models.analysis_job.AnalysisJob') as mock_job_class, \
                 patch('tasks.analysis_tasks.analyze_pcap_file') as mock_task, \
                 patch('os.makedirs'), \
                 patch('builtins.open'), \
                 patch('api.v1.endpoints.analysis.calculate_file_hash') as mock_hash:
                
                # Setup mocks
                mock_report = MagicMock()
                mock_report.id = "report456"
                mock_report_class.return_value = mock_report
                mock_report.insert = AsyncMock()
                mock_report.save = AsyncMock()
                
                mock_job = MagicMock()
                mock_job_class.return_value = mock_job
                mock_job.insert = AsyncMock()
                mock_job.save = AsyncMock()
                
                mock_celery_task = MagicMock()
                mock_celery_task.id = "task456"
                mock_task.delay.return_value = mock_celery_task
                
                mock_hash.return_value = "def456"
                
                # Import and test the endpoint
                from api.v1.endpoints.analysis import submit_analysis_job
                from core.config import get_settings
                from services.validation_service import get_validation_service
                
                settings = get_settings()
                validation_service = get_validation_service()
                
                result = await submit_analysis_job(
                    file=mock_file,
                    analysis_type="security_focused",
                    priority="high",
                    settings=settings,
                    validation_service=validation_service
                )
                
                # Verify response structure for custom options
                assert result["analysis_type"] == "security_focused"
                assert result["priority"] == "high"
                assert "options" in result  # Should have custom options
                assert result["options"]["malware_detection"] == True
                assert result["options"]["performance_analysis"] == False 
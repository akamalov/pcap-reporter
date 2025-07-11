"""
Simplified storage service tests for TDD.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from services.analysis_storage_service import AnalysisStorageService


class TestStorageServiceSimple:
    """Simplified storage service tests."""
    
    @pytest.mark.asyncio
    async def test_service_creation(self):
        """Test that storage service can be created."""
        service = AnalysisStorageService()
        assert service is not None
        assert hasattr(service, 'initialize')
        assert hasattr(service, 'create_report')
        assert hasattr(service, 'save_analysis_results')
    
    @pytest.mark.asyncio
    async def test_service_initialization_mocked(self):
        """Test service initialization with mocked database."""
        with patch('services.analysis_storage_service.init_db') as mock_init, \
             patch('services.analysis_storage_service.get_database') as mock_get_db:
            
            mock_init.return_value = None
            mock_get_db.return_value = MagicMock()
            
            service = AnalysisStorageService()
            await service.initialize()
            
            assert service._initialized is True
            mock_init.assert_called_once()
            mock_get_db.assert_called_once()
    
    @pytest.mark.asyncio 
    async def test_ensure_connection_calls_initialize(self):
        """Test that _ensure_connection calls initialize when needed."""
        with patch('services.analysis_storage_service.init_db') as mock_init, \
             patch('services.analysis_storage_service.get_database') as mock_get_db:
            
            mock_init.return_value = None
            mock_get_db.return_value = MagicMock()
            
            service = AnalysisStorageService()
            assert service._initialized is False
            
            await service._ensure_connection()
            
            assert service._initialized is True
            mock_init.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_track_operation_metrics(self):
        """Test that operation metrics are tracked."""
        service = AnalysisStorageService()
        
        initial_count = service._operation_count
        initial_time = service._total_operation_time
        
        service._track_operation(0.5)
        
        assert service._operation_count == initial_count + 1
        assert service._total_operation_time == initial_time + 0.5
    
    @pytest.mark.asyncio
    async def test_get_storage_metrics(self):
        """Test storage metrics retrieval."""
        service = AnalysisStorageService()
        
        # Track some operations
        service._track_operation(0.1)
        service._track_operation(0.2)
        
        metrics = await service.get_storage_metrics()
        
        assert isinstance(metrics, dict)
        assert "operations_count" in metrics
        assert "avg_operation_time" in metrics
        assert "total_operation_time" in metrics
        assert "uptime_seconds" in metrics
        assert "operations_per_second" in metrics
        assert "connection_pool_status" in metrics
        assert "database_initialized" in metrics
        
        assert metrics["operations_count"] == 2
        assert abs(metrics["avg_operation_time"] - 0.15) < 0.001  # (0.1 + 0.2) / 2
        assert abs(metrics["total_operation_time"] - 0.3) < 0.001
        assert metrics["database_initialized"] is False
    
    @pytest.mark.asyncio
    async def test_check_connection_with_mocked_db(self):
        """Test connection checking with mocked database."""
        with patch('services.analysis_storage_service.init_db') as mock_init, \
             patch('services.analysis_storage_service.get_database') as mock_get_db, \
             patch('services.analysis_storage_service.Report') as mock_report:
            
            mock_init.return_value = None
            mock_get_db.return_value = MagicMock()
            
            # Mock successful find operation chain
            mock_find_result = MagicMock()
            mock_limit_result = MagicMock()
            mock_limit_result.to_list = AsyncMock(return_value=[])
            mock_find_result.limit.return_value = mock_limit_result
            mock_report.find.return_value = mock_find_result
            
            service = AnalysisStorageService()
            
            result = await service.check_connection()
            
            assert result is True
    
    @pytest.mark.asyncio
    async def test_check_connection_failure(self):
        """Test connection checking when database fails."""
        with patch('services.analysis_storage_service.init_db') as mock_init:
            
            # Make initialization fail
            mock_init.side_effect = Exception("Database connection failed")
            
            service = AnalysisStorageService()
            
            result = await service.check_connection()
            
            assert result is False 
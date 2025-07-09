"""
Integration tests for health check endpoint.
Tests the actual HTTP endpoint behavior.
"""
import pytest
from unittest.mock import patch, AsyncMock
import json


class TestHealthEndpointIntegration:
    """Integration tests for health endpoint."""
    
    @pytest.mark.asyncio
    async def test_health_endpoint_structure(self):
        """Test that health endpoint returns correct structure."""
        # Import here to avoid import issues
        from services.health_service import get_health_status
        
        # Get health status
        response = await get_health_status()
        
        # Check required fields
        required_fields = ["status", "timestamp", "version", "services", "uptime"]
        for field in required_fields:
            assert field in response, f"Missing required field: {field}"
        
        # Check services structure
        assert "services" in response
        services = response["services"]
        required_services = ["database", "redis", "celery"]
        for service in required_services:
            assert service in services, f"Missing service: {service}"
        
        # Check status values
        assert response["status"] in ["healthy", "unhealthy"]
        for service_status in services.values():
            assert service_status in ["healthy", "unhealthy"]
    
    @pytest.mark.asyncio
    async def test_health_endpoint_with_all_services_healthy(self):
        """Test health endpoint when all services are healthy."""
        from services.health_service import HealthService
        
        # Mock all service checks to return healthy
        with patch.object(HealthService, 'check_database_health', new_callable=AsyncMock) as mock_db, \
             patch.object(HealthService, 'check_redis_health', new_callable=AsyncMock) as mock_redis, \
             patch.object(HealthService, 'check_celery_health', new_callable=AsyncMock) as mock_celery:
            
            mock_db.return_value = {"status": "healthy"}
            mock_redis.return_value = {"status": "healthy"}
            mock_celery.return_value = {"status": "healthy", "workers": 2}
            
            from services.health_service import get_health_status
            response = await get_health_status()
            
            # Check overall status
            assert response["status"] == "healthy"
            
            # Check individual services
            assert response["services"]["database"] == "healthy"
            assert response["services"]["redis"] == "healthy"
            assert response["services"]["celery"] == "healthy"
            
            # Should not have errors
            assert "errors" not in response
            
            # Should have worker count
            assert "celery_workers" in response
            assert response["celery_workers"] == 2
    
    @pytest.mark.asyncio
    async def test_health_endpoint_with_database_unhealthy(self):
        """Test health endpoint when database is unhealthy."""
        from services.health_service import HealthService
        
        # Mock database as unhealthy, others healthy
        with patch.object(HealthService, 'check_database_health', new_callable=AsyncMock) as mock_db, \
             patch.object(HealthService, 'check_redis_health', new_callable=AsyncMock) as mock_redis, \
             patch.object(HealthService, 'check_celery_health', new_callable=AsyncMock) as mock_celery:
            
            mock_db.return_value = {"status": "unhealthy", "error": "Database connection failed"}
            mock_redis.return_value = {"status": "healthy"}
            mock_celery.return_value = {"status": "healthy"}
            
            from services.health_service import get_health_status
            response = await get_health_status()
            
            # Check overall status
            assert response["status"] == "unhealthy"
            
            # Check individual services
            assert response["services"]["database"] == "unhealthy"
            assert response["services"]["redis"] == "healthy"
            assert response["services"]["celery"] == "healthy"
            
            # Should have errors
            assert "errors" in response
            assert "Database connection failed" in response["errors"]
    
    @pytest.mark.asyncio
    async def test_health_endpoint_with_redis_unhealthy(self):
        """Test health endpoint when Redis is unhealthy."""
        from services.health_service import HealthService
        
        # Mock Redis as unhealthy, others healthy
        with patch.object(HealthService, 'check_database_health', new_callable=AsyncMock) as mock_db, \
             patch.object(HealthService, 'check_redis_health', new_callable=AsyncMock) as mock_redis, \
             patch.object(HealthService, 'check_celery_health', new_callable=AsyncMock) as mock_celery:
            
            mock_db.return_value = {"status": "healthy"}
            mock_redis.return_value = {"status": "unhealthy", "error": "Redis connection failed"}
            mock_celery.return_value = {"status": "healthy"}
            
            from services.health_service import get_health_status
            response = await get_health_status()
            
            # Check overall status
            assert response["status"] == "unhealthy"
            
            # Check individual services
            assert response["services"]["database"] == "healthy"
            assert response["services"]["redis"] == "unhealthy"
            assert response["services"]["celery"] == "healthy"
            
            # Should have errors
            assert "errors" in response
            assert "Redis connection failed" in response["errors"]
    
    @pytest.mark.asyncio
    async def test_health_endpoint_with_celery_unhealthy(self):
        """Test health endpoint when Celery is unhealthy."""
        from services.health_service import HealthService
        
        # Mock Celery as unhealthy, others healthy
        with patch.object(HealthService, 'check_database_health', new_callable=AsyncMock) as mock_db, \
             patch.object(HealthService, 'check_redis_health', new_callable=AsyncMock) as mock_redis, \
             patch.object(HealthService, 'check_celery_health', new_callable=AsyncMock) as mock_celery:
            
            mock_db.return_value = {"status": "healthy"}
            mock_redis.return_value = {"status": "healthy"}
            mock_celery.return_value = {"status": "unhealthy", "error": "No active Celery workers"}
            
            from services.health_service import get_health_status
            response = await get_health_status()
            
            # Check overall status
            assert response["status"] == "unhealthy"
            
            # Check individual services
            assert response["services"]["database"] == "healthy"
            assert response["services"]["redis"] == "healthy"
            assert response["services"]["celery"] == "unhealthy"
            
            # Should have errors
            assert "errors" in response
            assert "No active Celery workers" in response["errors"]
    
    @pytest.mark.asyncio
    async def test_health_endpoint_uptime_calculation(self):
        """Test that uptime is calculated correctly."""
        from services.health_service import get_health_status
        
        response = await get_health_status()
        
        # Check uptime field exists and is a number
        assert "uptime" in response
        assert isinstance(response["uptime"], (int, float))
        assert response["uptime"] >= 0
    
    @pytest.mark.asyncio
    async def test_health_endpoint_timestamp_format(self):
        """Test that timestamp is in correct ISO format."""
        from services.health_service import get_health_status
        
        response = await get_health_status()
        
        # Check timestamp field exists and is properly formatted
        assert "timestamp" in response
        timestamp = response["timestamp"]
        assert isinstance(timestamp, str)
        assert timestamp.endswith("Z")  # UTC timezone indicator
        
        # Should be parseable as ISO format
        from datetime import datetime
        parsed_time = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        assert parsed_time is not None 